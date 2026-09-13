//! Live trading event loop for executing strategies against real-time market data.
//!
//! Connects to an exchange WebSocket stream, subscribes to candle updates,
//! evaluates a strategy script against each candle, checks risk limits,
//! and places orders via the exchange trading interface.

use omnitrade_core::{Candle, OrderStatus, Side, TimeInForce};
use omnitrade_exchange::{ExchangeStream, ExchangeTrading, Network, OrderRequest};
use omnitrade_risk::guard::RiskGuard;
use omnitrade_script::compile_and_run;
use std::fs;
use thiserror::Error;
use tracing::{info, trace, warn};

/// Errors that can occur during live trading loop execution.
#[allow(dead_code)]
#[derive(Debug, Error)]
pub enum LiveLoopError {
    /// File I/O error reading the strategy script.
    #[error("Script file error: {0}")]
    ScriptFileError(#[from] std::io::Error),

    /// Script parsing or compilation error.
    #[error("Script compilation error: {0}")]
    ScriptCompilationError(String),

    /// Exchange connection or trading error.
    #[error("Exchange error: {0}")]
    ExchangeError(String),

    /// Risk guard rejection.
    #[error("Risk guard rejection: {0}")]
    RiskViolation(String),

    /// Channel receive error when waiting for market data.
    #[error("Market data channel error")]
    ChannelError,

    /// Network validation error.
    #[error("Network validation error: {0}")]
    NetworkError(String),
}

/// Main async actor-style loop for live trading.
///
/// # Arguments
/// - `script_path`: Path to the .omni strategy script file
/// - `symbol`: Trading symbol (e.g., "BTCUSDT")
/// - `network`: Network designation (Testnet or Mainnet)
/// - `initial_capital`: Starting account balance for trading
/// - `exchange_stream`: Implementation of ExchangeStream trait
/// - `exchange_trading`: Implementation of ExchangeTrading trait
/// - `risk_guard`: RiskGuard instance for risk validation
///
/// # Returns
/// `Ok(())` if loop completes gracefully, or `Err(LiveLoopError)` on fatal error.
///
/// # Error Handling
/// Non-fatal errors (individual order rejections, risk violations) are logged but
/// do not halt the loop. The loop continues monitoring for new signals.
#[allow(dead_code)]
pub async fn live_loop(
    script_path: &str,
    symbol: &str,
    network: Network,
    initial_capital: f64,
    mut exchange_stream: impl ExchangeStream,
    exchange_trading: impl ExchangeTrading,
    risk_guard: &mut RiskGuard,
) -> Result<(), LiveLoopError> {
    // Validate network (testnet-first, mainnet requires explicit opt-in)
    if network == Network::Mainnet {
        return Err(LiveLoopError::NetworkError(
            "Mainnet trading requires additional Phase 3 safety gates".to_string(),
        ));
    }

    // Load and validate script file
    let script_content = fs::read_to_string(script_path)?;

    // Connect to exchange WebSocket
    exchange_stream
        .connect()
        .await
        .map_err(|e| LiveLoopError::ExchangeError(e.to_string()))?;
    info!("Connected to Binance Testnet");

    // Subscribe to candle stream
    let mut candle_rx = exchange_stream
        .subscribe_candles(symbol, "1m")
        .await
        .map_err(|e| LiveLoopError::ExchangeError(e.to_string()))?;

    // Initialize candle buffer for script evaluation
    let mut candle_buffer: Vec<Candle> = Vec::new();

    // Main event loop: process each candle as it arrives
    while let Some(candle) = candle_rx.recv().await {
        candle_buffer.push(candle.clone());
        trace!("Evaluating candle: {:?}", candle);

        // Evaluate strategy script against accumulated candles
        let signal = match compile_and_run(&script_content, &candle_buffer) {
            Ok(sig) => sig,
            Err(e) => {
                warn!("Script evaluation error for {}: {}", symbol, e);
                continue;
            }
        };

        // Skip if no signal
        if signal == omnitrade_script::Signal::Hold {
            continue;
        }

        // Determine order side from signal
        let side = match signal {
            omnitrade_script::Signal::Buy => Side::Buy,
            omnitrade_script::Signal::Sell => Side::Sell,
            omnitrade_script::Signal::Hold => continue,
        };

        // Create order request (market order, fixed quantity for now)
        let order_req = OrderRequest::market(symbol.to_string(), side, 1.0);
        info!("Placing order: {:?}", order_req);

        // Place order and check risk guard
        match place_order_with_risk_check(
            &exchange_trading,
            risk_guard,
            &order_req,
            candle.close,
            initial_capital,
        )
        .await
        {
            Ok(order) => {
                info!("Order filled: {:?}", order);
            }
            Err(e) => {
                warn!("Order rejected by RiskGuard: {}", e);
                // Continue loop; do not halt on single order failure
            }
        }
    }

    // Graceful disconnect
    exchange_stream
        .disconnect()
        .await
        .map_err(|e| LiveLoopError::ExchangeError(e.to_string()))?;

    Ok(())
}

/// Helper: Place order after passing risk guard checks.
///
/// Creates a mock Order from the request, checks it against RiskGuard,
/// and if approved, submits to the exchange.
#[allow(dead_code)]
async fn place_order_with_risk_check(
    exchange_trading: &impl ExchangeTrading,
    risk_guard: &mut RiskGuard,
    order_req: &OrderRequest,
    current_price: f64,
    initial_capital: f64,
) -> Result<omnitrade_core::Order, LiveLoopError> {
    // Create mock order for risk checking
    let mock_order = omnitrade_core::Order {
        id: 0,
        symbol: order_req.symbol.clone(),
        side: order_req.side,
        order_type: order_req.order_type.clone(),
        time_in_force: TimeInForce::GTC,
        price: order_req.price.unwrap_or(current_price),
        stop_price: 0.0,
        quantity: order_req.quantity,
        filled_quantity: 0.0,
        status: OrderStatus::New,
        created_at_ms: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64,
        updated_at_ms: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64,
        trailing_highest_price: None,
    };

    // Minimal AccountInfo implementation for risk checking
    struct SimpleAccount {
        initial: f64,
        current: f64,
        pnl: f64,
    }

    impl omnitrade_risk::guard::AccountInfo for SimpleAccount {
        fn total_equity(&self) -> f64 {
            self.current
        }

        fn total_pnl(&self) -> f64 {
            self.pnl
        }

        fn initial_balance(&self) -> f64 {
            self.initial
        }
    }

    let account = SimpleAccount {
        initial: initial_capital,
        current: initial_capital,
        pnl: 0.0,
    };

    // Check risk guard
    risk_guard
        .check_order(&mock_order, &account, current_price)
        .map_err(|e| LiveLoopError::RiskViolation(e.to_string()))?;

    // Risk check passed; submit order to exchange
    exchange_trading
        .place_order(order_req)
        .await
        .map_err(|e| LiveLoopError::ExchangeError(e.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_live_loop_error_display() {
        let err = LiveLoopError::ScriptFileError(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "file not found",
        ));
        assert!(err.to_string().contains("Script file error"));
    }
}
