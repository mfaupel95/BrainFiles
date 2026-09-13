//! Portfolio account state tracking with simultaneous long + short support.
//! PHASE 5 BREAKING CHANGE: HashMap<(String, Side), Position> enables hedging.

use std::collections::HashMap;

use omnitrade_core::{Position, Side};

use crate::error::EngineError;
use crate::fill::OrderFill;

/// Position key: (symbol, side) tuple enables long + short simultaneously.
type PositionKey = (String, Side);

/// Tracks portfolio state: cash balance, long/short positions, and fees.
/// **BREAKING CHANGE**: `positions` now uses `HashMap<(String, Side), Position>`.
#[derive(Debug, Clone, PartialEq)]
pub struct AccountState {
    /// Available cash balance.
    pub balance: f64,
    /// Starting balance for PnL calculation.
    pub initial_balance: f64,
    /// Open positions by (symbol, side). Supports Long and Short simultaneously.
    pub positions: HashMap<PositionKey, Position>,
    /// Running fee total paid across all fills.
    pub total_fees_paid: f64,
}

impl AccountState {
    /// Constructs a new [`AccountState`]. Errors if `initial_balance < 0.0` or NaN.
    pub fn new(initial_balance: f64) -> Result<Self, EngineError> {
        if initial_balance < 0.0 || initial_balance.is_nan() {
            return Err(EngineError::InvalidFieldValue {
                field: "initial_balance",
                reason: "initial_balance cannot be negative or NaN",
            });
        }
        Ok(Self {
            balance: initial_balance,
            initial_balance,
            positions: HashMap::new(),
            total_fees_paid: 0.0,
        })
    }

    /// Applies an execution fill. Buy -> Long position, Sell -> Short position.
    /// Errors if balance is inadequate.
    pub fn apply_fill(&mut self, fill: &OrderFill) -> Result<(), EngineError> {
        match fill.side {
            Side::Buy => self.apply_buy_fill(fill),
            Side::Sell => self.apply_sell_fill(fill),
        }
    }

    fn apply_buy_fill(&mut self, fill: &OrderFill) -> Result<(), EngineError> {
        let required = fill.notional() + fill.fee;
        if self.balance < required {
            return Err(EngineError::InsufficientBalance {
                required,
                available: self.balance,
            });
        }
        self.balance -= required;
        self.total_fees_paid += fill.fee;

        let key = (fill.symbol.clone(), Side::Buy);
        self.positions
            .entry(key)
            .and_modify(|pos| {
                let total_notional = pos.entry_price * pos.quantity + fill.notional();
                let total_qty = pos.quantity + fill.fill_quantity;
                pos.entry_price = total_notional / total_qty;
                pos.quantity = total_qty;
            })
            .or_insert_with(|| {
                Position::new(
                    fill.symbol.clone(),
                    Side::Buy,
                    fill.fill_price,
                    fill.fill_quantity,
                )
            });
        Ok(())
    }

    fn apply_sell_fill(&mut self, fill: &OrderFill) -> Result<(), EngineError> {
        let net_cash = fill.notional() - fill.fee;
        if self.balance + net_cash < 0.0 {
            return Err(EngineError::InsufficientBalance {
                required: (fill.fee - fill.notional()).max(0.0),
                available: self.balance,
            });
        }
        self.balance += net_cash;
        self.total_fees_paid += fill.fee;

        let key = (fill.symbol.clone(), Side::Sell);
        self.positions
            .entry(key)
            .and_modify(|pos| {
                let total_notional = pos.entry_price * pos.quantity + fill.notional();
                let total_qty = pos.quantity + fill.fill_quantity;
                pos.entry_price = total_notional / total_qty;
                pos.quantity = total_qty;
            })
            .or_insert_with(|| {
                Position::new(
                    fill.symbol.clone(),
                    Side::Sell,
                    fill.fill_price,
                    fill.fill_quantity,
                )
            });
        Ok(())
    }

    /// Returns a reference to a specific position (symbol, side).
    #[must_use]
    pub fn get_position(&self, symbol: &str, side: Side) -> Option<&Position> {
        self.positions.get(&(symbol.to_string(), side))
    }

    /// Returns all open positions for a symbol (both long and short).
    #[must_use]
    pub fn get_all_positions_for_symbol(&self, symbol: &str) -> Vec<&Position> {
        self.positions
            .iter()
            .filter_map(
                |((sym, _), pos)| {
                    if sym == symbol {
                        Some(pos)
                    } else {
                        None
                    }
                },
            )
            .collect()
    }

    /// Closes a position. Returns error if position doesn't exist.
    pub fn close_position(&mut self, symbol: &str, side: Side) -> Result<(), EngineError> {
        let key = (symbol.to_string(), side);
        if self.positions.remove(&key).is_none() {
            return Err(EngineError::SymbolNotFound {
                symbol: symbol.to_string(),
            });
        }
        Ok(())
    }

    /// Updates unrealized PnL for a position at current market price. Errors if not found.
    pub fn update_unrealized_pnl(
        &mut self,
        symbol: &str,
        side: Side,
        current_price: f64,
    ) -> Result<(), EngineError> {
        let key = (symbol.to_string(), side);
        if let Some(pos) = self.positions.get_mut(&key) {
            pos.mark_to_market(current_price);
            Ok(())
        } else {
            Err(EngineError::SymbolNotFound {
                symbol: symbol.to_string(),
            })
        }
    }

    /// Calculates total account equity (balance + unrealized PnL sum).
    #[must_use]
    pub fn total_equity(&self) -> f64 {
        let unrealized_sum: f64 = self.positions.values().map(|p| p.unrealized_pnl).sum();
        self.balance + unrealized_sum
    }

    /// Calculates total PnL since account creation.
    #[must_use]
    pub fn total_pnl(&self) -> f64 {
        self.total_equity() - self.initial_balance
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::fill::OrderFill;

    #[test]
    fn test_phase5_long_and_short_coexist() {
        let mut acc = AccountState::new(200_000.0).expect("account");
        let buy = OrderFill::new(
            1,
            "BTCUSDT".to_string(),
            Side::Buy,
            50_000.0,
            1.0,
            0.0,
            "USDT".to_string(),
            1000,
            true,
        );
        let sell = OrderFill::new(
            2,
            "BTCUSDT".to_string(),
            Side::Sell,
            51_000.0,
            2.0,
            0.0,
            "USDT".to_string(),
            2000,
            false,
        );
        acc.apply_fill(&buy).expect("buy");
        acc.apply_fill(&sell).expect("sell");
        assert!(acc.get_position("BTCUSDT", Side::Buy).is_some());
        assert!(acc.get_position("BTCUSDT", Side::Sell).is_some());
        assert_eq!(acc.get_all_positions_for_symbol("BTCUSDT").len(), 2);
    }
}
