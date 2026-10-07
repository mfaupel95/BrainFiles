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
use std::path::Path;
use std::time::Duration;
use thiserror::Error;
use tracing::{error, info, trace, warn};

use crate::kill_switch;

/// Maximale Anzahl Kerzen, die für die Skript-Auswertung vorgehalten werden.
const MAX_CANDLE_BUFFER: usize = 500;

/// Quote-Währung, deren Bestand als Konto-Equity für den RiskGuard dient.
const QUOTE_ASSET: &str = "USDT";

/// Errors that can occur during live trading loop execution.
#[derive(Debug, Error)]
pub enum LiveLoopError {
    /// File I/O error reading the strategy script.
    #[error("Script file error: {0}")]
    ScriptFileError(#[from] std::io::Error),

    /// Exchange connection or trading error.
    #[error("Exchange error: {0}")]
    ExchangeError(String),

    /// Risk guard rejection.
    #[error("Risk guard rejection: {0}")]
    RiskViolation(String),

    /// Network validation error.
    #[error("Network validation error: {0}")]
    NetworkError(String),
}

/// Laufzeit-Parameter eines Live-Laufs.
#[derive(Debug, Clone)]
pub struct LiveConfig<'a> {
    /// Pfad zum .omni-Strategieskript.
    pub script_path: &'a str,
    /// Handelssymbol (z. B. "BTCUSDT").
    pub symbol: &'a str,
    /// Netzwerk (Testnet oder Mainnet).
    pub network: Network,
    /// Startkapital als Referenz für Drawdown und Tagesverlust.
    pub initial_capital: f64,
    /// Menge je Market-Order (Basiswährung).
    pub order_quantity: f64,
    /// Flag-Datei des Not-Aus; ist sie gesetzt, stoppt die Schleife.
    pub kill_file: &'a Path,
}

/// Main async actor-style loop for live trading.
///
/// # Returns
/// `Ok(())` if loop completes gracefully, or `Err(LiveLoopError)` on fatal error.
///
/// # Error Handling
/// Non-fatal errors (individual order rejections, risk violations) are logged but
/// do not halt the loop. The loop continues monitoring for new signals.
pub async fn live_loop(
    config: &LiveConfig<'_>,
    mut exchange_stream: impl ExchangeStream,
    exchange_trading: impl ExchangeTrading,
    risk_guard: &mut RiskGuard,
) -> Result<(), LiveLoopError> {
    let LiveConfig {
        script_path,
        symbol,
        network,
        initial_capital,
        order_quantity,
        kill_file,
    } = *config;

    // Validate network (testnet-first, mainnet requires explicit opt-in)
    if network == Network::Mainnet {
        return Err(LiveLoopError::NetworkError(
            "Mainnet trading requires additional Phase 3 safety gates".to_string(),
        ));
    }

    // Load and validate script file
    let script_content = fs::read_to_string(script_path)?;

    if order_quantity <= 0.0 {
        return Err(LiveLoopError::ExchangeError(
            "Order-Menge muss positiv sein".to_string(),
        ));
    }

    // Abonnieren muss VOR connect() geschehen: connect() übergibt den Router
    // an die Verbindung, danach scheitert subscribe_candles.
    let mut candle_rx = exchange_stream
        .subscribe_candles(symbol, "1m")
        .await
        .map_err(|e| LiveLoopError::ExchangeError(e.to_string()))?;

    exchange_stream
        .connect()
        .await
        .map_err(|e| LiveLoopError::ExchangeError(e.to_string()))?;
    info!("Verbunden mit Binance ({:?})", network);

    // Candle buffer for script evaluation (auf MAX_CANDLE_BUFFER begrenzt)
    let mut candle_buffer: Vec<Candle> = Vec::new();

    // Not-Aus wird bei jeder Kerze und im Sekundentakt geprüft, damit er auch
    // bei ruhigem Markt wirkt.
    let mut kill_check = tokio::time::interval(Duration::from_secs(1));

    // Main event loop: process each candle as it arrives
    loop {
        let candle = tokio::select! {
            received = candle_rx.recv() => match received {
                Some(candle) => candle,
                None => break,
            },
            _ = kill_check.tick() => {
                if kill_switch::is_engaged(kill_file) {
                    return halt_trading(&exchange_trading, symbol, &mut exchange_stream).await;
                }
                continue;
            }
        };
        if kill_switch::is_engaged(kill_file) {
            return halt_trading(&exchange_trading, symbol, &mut exchange_stream).await;
        }
        candle_buffer.push(candle.clone());
        if candle_buffer.len() > MAX_CANDLE_BUFFER {
            let overflow = candle_buffer.len() - MAX_CANDLE_BUFFER;
            candle_buffer.drain(..overflow);
        }
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

        let order_req = OrderRequest::market(symbol.to_string(), side, order_quantity);
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

/// Storniert alle offenen Orders des Symbols. Fremde Symbole bleiben unberührt.
///
/// Einzelne Fehler werden geloggt und brechen den Vorgang nicht ab.
pub(crate) async fn cancel_open_orders(exchange_trading: &impl ExchangeTrading, symbol: &str) {
    error!("Not-Aus ausgelöst: keine neuen Orders, storniere offene Orders");
    match exchange_trading.get_open_orders().await {
        Ok(orders) => {
            for order in orders.into_iter().filter(|o| o.symbol == symbol) {
                if let Err(e) = exchange_trading
                    .cancel_order(&order.id.to_string(), &order.symbol)
                    .await
                {
                    warn!("Stornierung von Order {} fehlgeschlagen: {}", order.id, e);
                }
            }
        }
        Err(e) => warn!("Offene Orders nicht abrufbar: {}", e),
    }
}

/// Not-Aus: storniert offene Orders des Symbols und trennt die Verbindung.
///
/// Bestände werden bewusst nicht verkauft.
async fn halt_trading(
    exchange_trading: &impl ExchangeTrading,
    symbol: &str,
    exchange_stream: &mut impl ExchangeStream,
) -> Result<(), LiveLoopError> {
    cancel_open_orders(exchange_trading, symbol).await;
    exchange_stream
        .disconnect()
        .await
        .map_err(|e| LiveLoopError::ExchangeError(e.to_string()))
}

/// Helper: Place order after passing risk guard checks.
///
/// Creates a mock Order from the request, checks it against RiskGuard,
/// and if approved, submits to the exchange.
pub(crate) async fn place_order_with_risk_check(
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

    // Echter Kontostand (Quote-Währung) statt fester Startsumme, sonst bleiben
    // Drawdown- und Tagesverlust-Limits wirkungslos. Schlägt der Abruf fehl,
    // wird die Order abgelehnt (fail closed).
    let balances = exchange_trading
        .get_balance()
        .await
        .map_err(|e| LiveLoopError::ExchangeError(format!("Kontostand: {e}")))?;
    let equity = balances
        .balances
        .get(QUOTE_ASSET)
        .map(|b| b.free + b.locked)
        .unwrap_or(0.0);
    let account = SimpleAccount {
        initial: initial_capital,
        current: equity,
        pnl: equity - initial_capital,
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
    use async_trait::async_trait;
    use omnitrade_core::OrderType;
    use omnitrade_exchange::{Account, AccountBalance, DepthUpdate, ExchangeError};
    use std::collections::HashMap;
    use std::path::PathBuf;
    use std::sync::{Arc, Mutex};
    use tokio::sync::mpsc;

    const BUY_BELOW_40K: &str = "if close() < 40000 { buy() }";

    type Log = Arc<Mutex<Vec<String>>>;

    /// Stream-Mock: liefert vorbereitete Kerzen und protokolliert die Aufrufreihenfolge.
    struct MockStream {
        candles: Vec<Candle>,
        log: Log,
    }

    #[async_trait]
    impl ExchangeStream for MockStream {
        async fn connect(&mut self) -> Result<(), ExchangeError> {
            self.log.lock().expect("log").push("connect".into());
            Ok(())
        }

        async fn subscribe_candles(
            &mut self,
            _symbol: &str,
            _interval: &str,
        ) -> Result<mpsc::Receiver<Candle>, ExchangeError> {
            self.log.lock().expect("log").push("subscribe".into());
            let (tx, rx) = mpsc::channel(self.candles.len().max(1));
            for c in self.candles.drain(..) {
                tx.try_send(c).expect("channel capacity");
            }
            Ok(rx)
        }

        async fn subscribe_depth(
            &mut self,
            _symbol: &str,
        ) -> Result<mpsc::Receiver<DepthUpdate>, ExchangeError> {
            Err(ExchangeError::ChannelClosed)
        }

        async fn disconnect(&mut self) -> Result<(), ExchangeError> {
            self.log.lock().expect("log").push("disconnect".into());
            Ok(())
        }
    }

    /// Trading-Mock: konfigurierbarer Kontostand, protokolliert platzierte Orders.
    struct MockTrading {
        usdt: Option<f64>,
        placed: Arc<Mutex<Vec<OrderRequest>>>,
        cancelled: Arc<Mutex<Vec<String>>>,
    }

    #[async_trait]
    impl ExchangeTrading for MockTrading {
        async fn place_order(
            &self,
            req: &OrderRequest,
        ) -> Result<omnitrade_core::Order, ExchangeError> {
            self.placed.lock().expect("placed").push(req.clone());
            Ok(omnitrade_core::Order {
                id: 1,
                symbol: req.symbol.clone(),
                side: req.side,
                order_type: OrderType::Market,
                time_in_force: TimeInForce::GTC,
                price: 0.0,
                stop_price: 0.0,
                quantity: req.quantity,
                filled_quantity: req.quantity,
                status: OrderStatus::Filled,
                created_at_ms: 0,
                updated_at_ms: 0,
                trailing_highest_price: None,
            })
        }

        async fn cancel_order(&self, order_id: &str, _symbol: &str) -> Result<(), ExchangeError> {
            self.cancelled
                .lock()
                .expect("cancelled")
                .push(order_id.to_string());
            Ok(())
        }

        async fn get_open_orders(&self) -> Result<Vec<omnitrade_core::Order>, ExchangeError> {
            Ok(vec![omnitrade_core::Order {
                id: 77,
                symbol: "BTCUSDT".to_string(),
                side: Side::Buy,
                order_type: OrderType::Limit,
                time_in_force: TimeInForce::GTC,
                price: 1.0,
                stop_price: 0.0,
                quantity: 1.0,
                filled_quantity: 0.0,
                status: OrderStatus::New,
                created_at_ms: 0,
                updated_at_ms: 0,
                trailing_highest_price: None,
            }])
        }

        async fn get_balance(&self) -> Result<Account, ExchangeError> {
            match self.usdt {
                Some(free) => Ok(Account {
                    balances: HashMap::from([(
                        "USDT".to_string(),
                        AccountBalance { free, locked: 0.0 },
                    )]),
                }),
                None => Err(ExchangeError::ChannelClosed),
            }
        }
    }

    struct Harness {
        script: PathBuf,
        log: Log,
        placed: Arc<Mutex<Vec<OrderRequest>>>,
        cancelled: Arc<Mutex<Vec<String>>>,
        kill: PathBuf,
    }

    impl Harness {
        fn new(name: &str, script: &str) -> Self {
            let path = std::env::temp_dir().join(format!(
                "omnitrade-liveloop-{}-{name}.omni",
                std::process::id()
            ));
            fs::write(&path, script).expect("write script");
            Self {
                script: path,
                log: Arc::default(),
                placed: Arc::default(),
                cancelled: Arc::default(),
                kill: std::env::temp_dir().join(format!(
                    "omnitrade-liveloop-{}-{name}.kill",
                    std::process::id()
                )),
            }
        }

        async fn run(
            &self,
            closes: &[f64],
            usdt: Option<f64>,
            network: Network,
            quantity: f64,
        ) -> Result<(), LiveLoopError> {
            let candles = closes
                .iter()
                .enumerate()
                .map(|(i, &p)| Candle::new(i as u64 * 60_000, p, p + 1.0, p - 1.0, p, 100.0))
                .collect();
            let stream = MockStream {
                candles,
                log: self.log.clone(),
            };
            let trading = MockTrading {
                usdt,
                placed: self.placed.clone(),
                cancelled: self.cancelled.clone(),
            };
            let script = self.script.to_string_lossy().to_string();
            let config = LiveConfig {
                script_path: &script,
                symbol: "BTCUSDT",
                network,
                initial_capital: 1000.0,
                order_quantity: quantity,
                kill_file: &self.kill,
            };
            let mut guard = RiskGuard::testnet();
            live_loop(&config, stream, trading, &mut guard).await
        }
    }

    impl Drop for Harness {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.script);
            let _ = fs::remove_file(&self.kill);
        }
    }

    #[tokio::test]
    async fn buy_signal_places_market_order_with_configured_quantity() {
        // Arrange
        let h = Harness::new("buy", BUY_BELOW_40K);

        // Act
        let result = h
            .run(&[35000.0], Some(1000.0), Network::Testnet, 0.002)
            .await;

        // Assert
        assert!(result.is_ok());
        let placed = h.placed.lock().expect("placed");
        assert_eq!(placed.len(), 1);
        assert_eq!(placed[0].symbol, "BTCUSDT");
        assert!(matches!(placed[0].side, Side::Buy));
        assert!((placed[0].quantity - 0.002).abs() < f64::EPSILON);
    }

    #[tokio::test]
    async fn subscribes_before_connect_and_disconnects_at_end() {
        // Arrange
        let h = Harness::new("order", BUY_BELOW_40K);

        // Act
        let result = h
            .run(&[45000.0], Some(1000.0), Network::Testnet, 0.001)
            .await;

        // Assert
        assert!(result.is_ok());
        assert_eq!(
            *h.log.lock().expect("log"),
            vec!["subscribe", "connect", "disconnect"]
        );
    }

    #[tokio::test]
    async fn engaged_kill_switch_blocks_orders_cancels_open_orders_and_disconnects() {
        let h = Harness::new("kill", BUY_BELOW_40K);
        kill_switch::engage(&h.kill).expect("engage");

        h.run(&[30_000.0], Some(1000.0), Network::Testnet, 0.001)
            .await
            .expect("halt is a graceful end");

        assert!(h.placed.lock().expect("placed").is_empty());
        assert_eq!(*h.cancelled.lock().expect("cancelled"), vec!["77"]);
        assert_eq!(
            h.log.lock().expect("log").last().map(String::as_str),
            Some("disconnect")
        );
    }

    #[tokio::test]
    async fn without_kill_switch_nothing_is_cancelled() {
        let h = Harness::new("nokill", BUY_BELOW_40K);

        h.run(&[30_000.0], Some(1000.0), Network::Testnet, 0.001)
            .await
            .expect("run");

        assert_eq!(h.placed.lock().expect("placed").len(), 1);
        assert!(h.cancelled.lock().expect("cancelled").is_empty());
    }

    #[tokio::test]
    async fn hold_signal_places_no_order() {
        // Arrange
        let h = Harness::new("hold", BUY_BELOW_40K);

        // Act
        let result = h
            .run(&[45000.0], Some(1000.0), Network::Testnet, 0.001)
            .await;

        // Assert
        assert!(result.is_ok());
        assert!(h.placed.lock().expect("placed").is_empty());
    }

    #[tokio::test]
    async fn balance_failure_blocks_order_fail_closed() {
        // Arrange
        let h = Harness::new("nobalance", BUY_BELOW_40K);

        // Act
        let result = h.run(&[35000.0], None, Network::Testnet, 0.001).await;

        // Assert
        assert!(result.is_ok(), "Einzelfehler beenden die Schleife nicht");
        assert!(h.placed.lock().expect("placed").is_empty());
    }

    #[tokio::test]
    async fn oversized_order_is_rejected_by_risk_guard_and_loop_continues() {
        // Arrange: 1.0 BTC * 35000 > 10000 USDT Testnet-Limit
        let h = Harness::new("oversize", BUY_BELOW_40K);

        // Act
        let result = h
            .run(&[35000.0, 35000.0], Some(1000.0), Network::Testnet, 1.0)
            .await;

        // Assert
        assert!(result.is_ok());
        assert!(h.placed.lock().expect("placed").is_empty());
        assert_eq!(
            h.log.lock().expect("log").last().map(String::as_str),
            Some("disconnect")
        );
    }

    #[tokio::test]
    async fn mainnet_is_rejected_before_any_exchange_call() {
        // Arrange
        let h = Harness::new("mainnet", BUY_BELOW_40K);

        // Act
        let result = h
            .run(&[35000.0], Some(1000.0), Network::Mainnet, 0.001)
            .await;

        // Assert
        assert!(matches!(result, Err(LiveLoopError::NetworkError(_))));
        assert!(h.log.lock().expect("log").is_empty());
    }

    #[tokio::test]
    async fn non_positive_quantity_is_rejected() {
        // Arrange
        let h = Harness::new("qty", BUY_BELOW_40K);

        // Act
        let zero = h.run(&[35000.0], Some(1000.0), Network::Testnet, 0.0).await;
        let negative = h
            .run(&[35000.0], Some(1000.0), Network::Testnet, -1.0)
            .await;

        // Assert
        assert!(matches!(zero, Err(LiveLoopError::ExchangeError(_))));
        assert!(matches!(negative, Err(LiveLoopError::ExchangeError(_))));
        assert!(h.log.lock().expect("log").is_empty());
    }

    #[tokio::test]
    async fn missing_script_file_returns_script_file_error() {
        // Arrange
        let h = Harness::new("missing", BUY_BELOW_40K);
        fs::remove_file(&h.script).expect("remove script");

        // Act
        let result = h
            .run(&[35000.0], Some(1000.0), Network::Testnet, 0.001)
            .await;

        // Assert
        assert!(matches!(result, Err(LiveLoopError::ScriptFileError(_))));
    }

    #[test]
    fn test_live_loop_error_display() {
        let err = LiveLoopError::ScriptFileError(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "file not found",
        ));
        assert!(err.to_string().contains("Script file error"));
    }
}
