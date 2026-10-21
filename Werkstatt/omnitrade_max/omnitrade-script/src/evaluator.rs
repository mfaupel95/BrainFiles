//! Strategy DSL script evaluator for `omnitrade-script`.
//!
//! Evaluates AST statements and expressions against historical candle data
//! to emit trading signals (`Signal::Buy`, `Signal::Sell`, `Signal::Hold`).

use std::collections::HashMap;

use omnitrade_core::{Candle, Ema, Rsi, Sma};

use crate::ast::{BinaryOp, Expr, Signal, Stmt};
use crate::error::ScriptError;
use crate::order_intent::{EvaluatorState, OrderIntent};

/// Evaluator for strategy scripts.
///
/// Maintains variable state across statement evaluations.
#[derive(Debug)]
pub struct Evaluator {
    /// Environment map storing variable bindings.
    pub variables: HashMap<String, f64>,
    /// Current order intent tracking TP/SL/Trailing.
    current_intent: OrderIntent,
}

impl Default for Evaluator {
    fn default() -> Self {
        Self::new()
    }
}

impl Evaluator {
    /// Creates a new `Evaluator` with empty variable bindings.
    pub fn new() -> Self {
        Self {
            variables: HashMap::new(),
            current_intent: OrderIntent::default(),
        }
    }

    /// Returns the current order intent.
    pub fn current_intent(&self) -> &OrderIntent {
        &self.current_intent
    }

    /// Evaluates a sequence of strategy statements against market candle data.
    ///
    /// # Errors
    /// Returns [`ScriptError::EvalError`] if `candles` is empty or runtime evaluation fails.
    pub fn evaluate(&mut self, stmts: &[Stmt], candles: &[Candle]) -> Result<Signal, ScriptError> {
        if candles.is_empty() {
            return Err(ScriptError::EvalError {
                message: "candles dataset cannot be empty".to_string(),
            });
        }

        for stmt in stmts {
            if let Some(signal) = self.eval_stmt(stmt, candles)? {
                return Ok(signal);
            }
        }

        Ok(Signal::Hold)
    }

    /// Evaluates statements and returns complete OrderIntent with risk parameters.
    ///
    /// Processes all statements (including risk parameters) before returning.
    /// Trailing stop triggers are evaluated after all statements execute.
    ///
    /// # Errors
    /// Returns [`ScriptError::EvalError`] if `candles` is empty or runtime evaluation fails.
    pub fn evaluate_extended(
        &mut self,
        stmts: &[Stmt],
        candles: &[Candle],
        state: &mut EvaluatorState,
    ) -> Result<OrderIntent, ScriptError> {
        if candles.is_empty() {
            return Err(ScriptError::EvalError {
                message: "candles dataset cannot be empty".to_string(),
            });
        }

        // Process all statements without breaking on first signal
        for stmt in stmts {
            self.eval_stmt(stmt, candles)?;
        }

        // Check trailing stop if configured (after all statements processed)
        if let Some(trailing_pct) = self.current_intent.trailing_pct {
            let current_price = candles.last().map(|c| c.close).unwrap_or(0.0);
            if state.update_and_check_trailing(current_price, trailing_pct) {
                self.current_intent.signal = Signal::Sell;
            }
        }

        Ok(self.current_intent.clone())
    }

    fn eval_stmt(
        &mut self,
        stmt: &Stmt,
        candles: &[Candle],
    ) -> Result<Option<Signal>, ScriptError> {
        match stmt {
            Stmt::Assign { name, value } => {
                let val = self.eval_expr(value, candles)?;
                self.variables.insert(name.clone(), val);
                Ok(None)
            }
            Stmt::If {
                condition,
                then_block,
                else_block,
            } => {
                let cond_val = self.eval_expr(condition, candles)?;
                if cond_val != 0.0 {
                    self.eval_block(then_block, candles)
                } else if let Some(else_stmts) = else_block {
                    self.eval_block(else_stmts, candles)
                } else {
                    Ok(None)
                }
            }
            Stmt::SignalBuy => {
                self.current_intent.signal = Signal::Buy;
                Ok(Some(Signal::Buy))
            }
            Stmt::SignalSell => {
                self.current_intent.signal = Signal::Sell;
                Ok(Some(Signal::Sell))
            }
            Stmt::StopLoss(expr) => {
                let price = self.eval_expr(expr, candles)?;
                self.current_intent.stop_loss = Some(price);
                Ok(None)
            }
            Stmt::TakeProfit(expr) => {
                let price = self.eval_expr(expr, candles)?;
                self.current_intent.take_profit = Some(price);
                Ok(None)
            }
            Stmt::TrailingStop(expr) => {
                let pct = self.eval_expr(expr, candles)?;
                self.current_intent.trailing_pct = Some(pct);
                Ok(None)
            }
            Stmt::ExprStmt(expr) => {
                self.eval_expr(expr, candles)?;
                Ok(None)
            }
        }
    }

    /// Führt alle Statements eines Blocks aus und liefert das erste Signal zurück.
    /// Kein Abbruch beim ersten Signal, sonst gingen `stop_loss(..)`/`take_profit(..)`
    /// hinter `buy()` im selben Block verloren.
    fn eval_block(
        &mut self,
        block: &[Stmt],
        candles: &[Candle],
    ) -> Result<Option<Signal>, ScriptError> {
        let mut first = None;
        for s in block {
            if let Some(sig) = self.eval_stmt(s, candles)? {
                first.get_or_insert(sig);
            }
        }
        Ok(first)
    }

    /// Evaluates an AST expression to a 64-bit floating point value.
    ///
    /// # Errors
    /// Returns [`ScriptError`] if variables/functions are missing, or arithmetic fails.
    pub fn eval_expr(&mut self, expr: &Expr, candles: &[Candle]) -> Result<f64, ScriptError> {
        match expr {
            Expr::Number(n) => Ok(*n),
            Expr::Identifier(name) => self
                .variables
                .get(name)
                .copied()
                .ok_or_else(|| ScriptError::UndefinedVariable { name: name.clone() }),
            Expr::Negate(inner) => {
                let val = self.eval_expr(inner, candles)?;
                Ok(-val)
            }
            Expr::BinaryOp { left, op, right } => match op {
                BinaryOp::And => {
                    let l_val = self.eval_expr(left, candles)?;
                    if l_val == 0.0 {
                        Ok(0.0)
                    } else {
                        let r_val = self.eval_expr(right, candles)?;
                        Ok(if r_val != 0.0 { 1.0 } else { 0.0 })
                    }
                }
                BinaryOp::Or => {
                    let l_val = self.eval_expr(left, candles)?;
                    if l_val != 0.0 {
                        Ok(1.0)
                    } else {
                        let r_val = self.eval_expr(right, candles)?;
                        Ok(if r_val != 0.0 { 1.0 } else { 0.0 })
                    }
                }
                _ => {
                    let l_val = self.eval_expr(left, candles)?;
                    let r_val = self.eval_expr(right, candles)?;
                    match op {
                        BinaryOp::Add => Ok(l_val + r_val),
                        BinaryOp::Sub => Ok(l_val - r_val),
                        BinaryOp::Mul => Ok(l_val * r_val),
                        BinaryOp::Div => {
                            if r_val == 0.0 {
                                Err(ScriptError::EvalError {
                                    message: "division by zero".to_string(),
                                })
                            } else {
                                Ok(l_val / r_val)
                            }
                        }
                        BinaryOp::Gt => Ok(if l_val > r_val { 1.0 } else { 0.0 }),
                        BinaryOp::Lt => Ok(if l_val < r_val { 1.0 } else { 0.0 }),
                        BinaryOp::Gte => Ok(if l_val >= r_val { 1.0 } else { 0.0 }),
                        BinaryOp::Lte => Ok(if l_val <= r_val { 1.0 } else { 0.0 }),
                        BinaryOp::Eq => Ok(if l_val == r_val { 1.0 } else { 0.0 }),
                        BinaryOp::Neq => Ok(if l_val != r_val { 1.0 } else { 0.0 }),
                        BinaryOp::And | BinaryOp::Or => unreachable!(),
                    }
                }
            },
            Expr::FunctionCall { name, args } => self.eval_function_call(name, args, candles),
        }
    }

    fn eval_function_call(
        &mut self,
        name: &str,
        args: &[Expr],
        candles: &[Candle],
    ) -> Result<f64, ScriptError> {
        match name {
            "close" => {
                if !args.is_empty() {
                    return Err(ScriptError::EvalError {
                        message: "close() expects 0 arguments".to_string(),
                    });
                }
                candles
                    .last()
                    .map(|c| c.close)
                    .ok_or_else(|| ScriptError::EvalError {
                        message: "candles dataset cannot be empty".to_string(),
                    })
            }
            "volume" => {
                if !args.is_empty() {
                    return Err(ScriptError::EvalError {
                        message: "volume() expects 0 arguments".to_string(),
                    });
                }
                candles
                    .last()
                    .map(|c| c.volume)
                    .ok_or_else(|| ScriptError::EvalError {
                        message: "candles dataset cannot be empty".to_string(),
                    })
            }
            "sma" => {
                let period = self.eval_period_arg("sma", args, candles)?;
                let mut indicator = Sma::new(period)?;
                let mut res = None;
                for c in candles {
                    res = indicator.update(c.close);
                }
                res.ok_or_else(|| ScriptError::EvalError {
                    message: format!(
                        "insufficient candles ({}) for sma with period {period}",
                        candles.len()
                    ),
                })
            }
            "rsi" => {
                let period = self.eval_period_arg("rsi", args, candles)?;
                let mut indicator = Rsi::new(period)?;
                let mut res = None;
                for c in candles {
                    res = indicator.update(c.close);
                }
                res.ok_or_else(|| ScriptError::EvalError {
                    message: format!(
                        "insufficient candles ({}) for rsi with period {period}",
                        candles.len()
                    ),
                })
            }
            "ema" => {
                let period = self.eval_period_arg("ema", args, candles)?;
                let mut indicator = Ema::new(period)?;
                let mut res = None;
                for c in candles {
                    res = indicator.update(c.close);
                }
                res.ok_or_else(|| ScriptError::EvalError {
                    message: format!(
                        "insufficient candles ({}) for ema with period {period}",
                        candles.len()
                    ),
                })
            }
            _ => Err(ScriptError::UndefinedFunction {
                name: name.to_string(),
            }),
        }
    }

    fn eval_period_arg(
        &mut self,
        func_name: &str,
        args: &[Expr],
        candles: &[Candle],
    ) -> Result<usize, ScriptError> {
        if args.len() != 1 {
            return Err(ScriptError::EvalError {
                message: format!("{func_name}() expects 1 argument"),
            });
        }
        let period_f = self.eval_expr(&args[0], candles)?;
        if period_f <= 0.0 || period_f.is_nan() {
            return Err(ScriptError::EvalError {
                message: format!("invalid period for {func_name}: {period_f}"),
            });
        }
        Ok(period_f as usize)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::lexer::tokenize;
    use crate::parser::parse;

    fn helper_candles(prices: &[f64]) -> Vec<Candle> {
        prices
            .iter()
            .enumerate()
            .map(|(i, &p)| Candle::new(i as u64 * 1000, p, p + 1.0, p - 1.0, p, 100.0))
            .collect()
    }

    #[test]
    fn test_evaluate_rsi_buy_signal() {
        // Arrange: create script and candle data where RSI < 30
        let code = "if rsi(14) < 30 { buy() }";
        let tokens = tokenize(code).expect("tokenization should succeed");
        let stmts = parse(&tokens).expect("parsing should succeed");
        let mut prices = vec![100.0; 5];
        for i in 1..=15 {
            prices.push(100.0 - (i as f64 * 4.0));
        }
        let candles = helper_candles(&prices);
        let mut evaluator = Evaluator::new();

        // Act
        let signal = evaluator
            .evaluate(&stmts, &candles)
            .expect("evaluation should succeed");

        // Assert
        assert_eq!(signal, Signal::Buy);
    }

    #[test]
    fn test_evaluate_sma_cross_signal() {
        // Arrange
        let code = "if sma(10) > sma(20) { buy() } else { sell() }";
        let tokens = tokenize(code).expect("tokenization should succeed");
        let stmts = parse(&tokens).expect("parsing should succeed");

        let prices: Vec<f64> = (1..=30).map(|i| i as f64 * 10.0).collect();
        let candles = helper_candles(&prices);
        let mut evaluator = Evaluator::new();

        // Act
        let signal = evaluator
            .evaluate(&stmts, &candles)
            .expect("evaluation should succeed");

        // Assert
        assert_eq!(signal, Signal::Buy);
    }

    #[test]
    fn test_evaluate_variable_binding() {
        // Arrange
        let code = "x = close(); if x > 50000 { sell() }";
        let tokens = tokenize(code).expect("tokenization should succeed");
        let stmts = parse(&tokens).expect("parsing should succeed");
        let candles = vec![Candle::new(1000, 51000.0, 52000.0, 50000.0, 51000.0, 10.0)];
        let mut evaluator = Evaluator::new();

        // Act
        let signal = evaluator
            .evaluate(&stmts, &candles)
            .expect("evaluation should succeed");

        // Assert
        assert_eq!(signal, Signal::Sell);
        assert_eq!(evaluator.variables.get("x"), Some(&51000.0));
    }

    #[test]
    fn test_evaluate_undefined_function() {
        // Arrange
        let code = "foo(1)";
        let tokens = tokenize(code).expect("tokenization should succeed");
        let stmts = parse(&tokens).expect("parsing should succeed");
        let candles = helper_candles(&[100.0]);
        let mut evaluator = Evaluator::new();

        // Act
        let result = evaluator.evaluate(&stmts, &candles);

        // Assert
        assert_eq!(
            result,
            Err(ScriptError::UndefinedFunction {
                name: "foo".to_string()
            })
        );
    }

    #[test]
    fn test_evaluate_division_by_zero() {
        // Arrange
        let code = "x = 10 / 0";
        let tokens = tokenize(code).expect("tokenization should succeed");
        let stmts = parse(&tokens).expect("parsing should succeed");
        let candles = helper_candles(&[100.0]);
        let mut evaluator = Evaluator::new();

        // Act
        let result = evaluator.evaluate(&stmts, &candles);

        // Assert
        assert!(matches!(result, Err(ScriptError::EvalError { .. })));
    }

    #[test]
    fn test_evaluate_empty_candle_slice() {
        // Arrange
        let code = "buy()";
        let tokens = tokenize(code).expect("tokenization should succeed");
        let stmts = parse(&tokens).expect("parsing should succeed");
        let candles: Vec<Candle> = vec![];
        let mut evaluator = Evaluator::new();

        // Act
        let result = evaluator.evaluate(&stmts, &candles);

        // Assert
        assert!(matches!(result, Err(ScriptError::EvalError { .. })));
    }

    #[test]
    fn test_evaluate_short_circuit_and_or() {
        // Arrange: 0 && undefined_var should not fail with UndefinedVariable
        let code1 = "if 0 && undefined_var { buy() }";
        let code2 = "if 1 || undefined_var { buy() }";
        let tokens1 = tokenize(code1).expect("tokenization should succeed");
        let tokens2 = tokenize(code2).expect("tokenization should succeed");
        let stmts1 = parse(&tokens1).expect("parsing should succeed");
        let stmts2 = parse(&tokens2).expect("parsing should succeed");
        let candles = helper_candles(&[100.0]);
        let mut evaluator = Evaluator::new();

        // Act & Assert
        let sig1 = evaluator
            .evaluate(&stmts1, &candles)
            .expect("short circuit AND");
        assert_eq!(sig1, Signal::Hold);

        let sig2 = evaluator
            .evaluate(&stmts2, &candles)
            .expect("short circuit OR");
        assert_eq!(sig2, Signal::Buy);
    }

    #[test]
    fn test_evaluate_extended_with_stop_loss() {
        // Arrange
        let code = "buy(); stop_loss(90.0); take_profit(110.0)";
        let tokens = tokenize(code).expect("tokenization should succeed");
        let stmts = parse(&tokens).expect("parsing should succeed");
        let candles = helper_candles(&[100.0]);
        let mut evaluator = Evaluator::new();
        let mut state = EvaluatorState::new(100.0);

        // Act
        let intent = evaluator
            .evaluate_extended(&stmts, &candles, &mut state)
            .expect("extended evaluation should succeed");

        // Assert
        assert_eq!(intent.signal, Signal::Buy);
        assert_eq!(intent.stop_loss, Some(90.0));
        assert_eq!(intent.take_profit, Some(110.0));
    }

    #[test]
    fn test_stop_loss_and_take_profit_after_signal_inside_if_block() {
        // Arrange
        let code = "if close() > 0 { buy(); stop_loss(90.0); take_profit(110.0) }";
        let tokens = tokenize(code).expect("tokenization should succeed");
        let stmts = parse(&tokens).expect("parsing should succeed");
        let candles = helper_candles(&[100.0]);
        let mut evaluator = Evaluator::new();
        let mut state = EvaluatorState::new(100.0);

        // Act
        let intent = evaluator
            .evaluate_extended(&stmts, &candles, &mut state)
            .expect("extended evaluation should succeed");

        // Assert
        assert_eq!(intent.signal, Signal::Buy);
        assert_eq!(intent.stop_loss, Some(90.0));
        assert_eq!(intent.take_profit, Some(110.0));
    }

    #[test]
    fn test_evaluate_extended_with_trailing_stop() {
        // Arrange
        let code = "buy(); trailing_stop(0.05)";
        let tokens = tokenize(code).expect("tokenization should succeed");
        let stmts = parse(&tokens).expect("parsing should succeed");
        let prices = vec![100.0, 105.0, 110.0, 109.0];
        let candles = helper_candles(&prices);
        let mut evaluator = Evaluator::new();
        let mut state = EvaluatorState::new(100.0);

        // Act
        let intent = evaluator
            .evaluate_extended(&stmts, &candles, &mut state)
            .expect("extended evaluation should succeed");

        // Assert: current price 109 < highest 110 * (1 - 0.05) = 104.5, so no trigger
        assert_eq!(intent.signal, Signal::Buy);
        assert_eq!(intent.trailing_pct, Some(0.05));
    }
}
