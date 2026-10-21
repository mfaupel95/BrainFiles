//! Live trading event loop for executing strategies against real-time market data.
//!
//! Connects to an exchange WebSocket stream, subscribes to candle updates,
//! evaluates a strategy script against each candle, checks risk limits,
//! and places orders via the exchange trading interface.

use omnitrade_core::{Candle, OrderStatus, Side, TimeInForce};
use omnitrade_exchange::{Account, ExchangeStream, ExchangeTrading, Network, OrderRequest};
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
/// Quote-Währungen für Symbole ohne Trennzeichen (`BTCUSDT`), längere zuerst, damit
/// z. B. `USDT` vor `USD` und `BNB` erkannt wird.
const KNOWN_QUOTES: [&str; 10] = [
    "FDUSD", "USDT", "USDC", "BUSD", "TUSD", "USD", "EUR", "BTC", "ETH", "BNB",
];

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
    /// Deckel für die Position, die dieser Lauf selbst aufbaut (Quote-Währung).
    /// Auf Mainnet Pflicht und höchstens [`MAINNET_HARD_CAP`].
    pub max_notional: Option<f64>,
}

/// Fest verdrahteter Höchstwert des Deckels auf Mainnet (Quote-Währung, z. B. USD).
/// Er lässt sich nur per Code-Änderung anheben, nie per Argument.
pub const MAINNET_HARD_CAP: f64 = 100.0;

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
        max_notional,
    } = *config;

    // Mainnet nur mit gültigem Deckel (testnet-first, echtes Geld braucht eine Grenze).
    if network == Network::Mainnet && !valid_mainnet_cap(max_notional) {
        return Err(LiveLoopError::NetworkError(format!(
            "Mainnet trading requires a max notional between 0 and {MAINNET_HARD_CAP}"
        )));
    }
    if let Some(cap) = max_notional {
        if !cap.is_finite() || cap <= 0.0 {
            return Err(LiveLoopError::NetworkError(format!(
                "Invalid max notional: {cap}"
            )));
        }
    }
    let mut exposure = max_notional.map(ExposureLimit::new);

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
        match place_order_guarded(
            &exchange_trading,
            risk_guard,
            &order_req,
            candle.close,
            initial_capital,
            exposure.as_mut(),
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

/// Zerlegt ein Börsensymbol in (Basis, Quote): `BTC-USDT`, `BTC/USD` oder `BTCUSDT`.
pub(crate) fn split_symbol(symbol: &str) -> Option<(String, String)> {
    let upper = symbol.to_uppercase();
    if let Some((base, quote)) = upper.split_once(['-', '/']) {
        return (!base.is_empty() && !quote.is_empty() && !quote.contains(['-', '/']))
            .then(|| (base.to_string(), quote.to_string()));
    }
    KNOWN_QUOTES.iter().find_map(|quote| {
        upper
            .strip_suffix(quote)
            .filter(|base| !base.is_empty())
            .map(|base| (base.to_string(), (*quote).to_string()))
    })
}

/// Eigenkapital des Handelspaars: Quote-Bestand plus Basis-Bestand zum aktuellen Preis
/// (jeweils frei + gesperrt). Nur das Quote-Guthaben zu zählen ließe jeden Kauf wie
/// einen Verlust in Höhe des Kaufpreises aussehen.
pub(crate) fn pair_equity(account: &Account, base: &str, quote: &str, price: f64) -> f64 {
    let total = |asset: &str| {
        account
            .balances
            .get(asset)
            .map_or(0.0, |b| b.free + b.locked)
    };
    total(quote) + total(base) * price
}

/// Prüft einen Positionsdeckel für die Position, die ein Lauf selbst aufbaut.
///
/// Bestände, die schon vor dem Lauf im Konto lagen, zählen nicht dazu und werden nie
/// verkauft: Beim ersten Check wird der Basis-Bestand als Ausgangspunkt gemerkt, der
/// Lauf darf nur darüber hinaus kaufen und höchstens das Gekaufte wieder verkaufen.
#[derive(Debug, Clone, PartialEq)]
pub(crate) struct ExposureLimit {
    cap: f64,
    start_base: Option<f64>,
}

impl ExposureLimit {
    pub(crate) fn new(cap: f64) -> Self {
        Self {
            cap,
            start_base: None,
        }
    }

    /// `held_base` ist der aktuelle Gesamtbestand (frei + gesperrt) der Basis-Währung.
    pub(crate) fn check(
        &mut self,
        side: Side,
        quantity: f64,
        price: f64,
        held_base: f64,
    ) -> Result<(), String> {
        let start = *self.start_base.get_or_insert(held_base);
        let run_base = (held_base - start).max(0.0);
        match side {
            Side::Buy => {
                let after = (run_base + quantity) * price;
                if after > self.cap {
                    return Err(format!(
                        "Positionsdeckel überschritten: {after:.2} > {:.2}",
                        self.cap
                    ));
                }
            }
            Side::Sell => {
                // Toleranz 1 % der Ordermenge: Gebühren in der Basis-Währung lassen den
                // Bestand leicht unter der gekauften Menge liegen.
                if quantity > run_base + quantity * 0.01 {
                    return Err(format!(
                        "Verkauf {quantity} übersteigt die in diesem Lauf gekaufte Menge {run_base}"
                    ));
                }
            }
        }
        Ok(())
    }
}

/// `true`, wenn der Deckel für Mainnet gesetzt, endlich, positiv und unter dem Höchstwert liegt.
pub(crate) fn valid_mainnet_cap(cap: Option<f64>) -> bool {
    cap.is_some_and(|c| c.is_finite() && c > 0.0 && c <= MAINNET_HARD_CAP)
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
    place_order_guarded(
        exchange_trading,
        risk_guard,
        order_req,
        current_price,
        initial_capital,
        None,
    )
    .await
}

/// Wie [`place_order_with_risk_check`], zusätzlich mit optionalem Positionsdeckel.
pub(crate) async fn place_order_guarded(
    exchange_trading: &impl ExchangeTrading,
    risk_guard: &mut RiskGuard,
    order_req: &OrderRequest,
    current_price: f64,
    initial_capital: f64,
    exposure: Option<&mut ExposureLimit>,
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

    // Echter Kontostand statt fester Startsumme, sonst bleiben Drawdown- und
    // Tagesverlust-Limits wirkungslos. Schlägt der Abruf fehl oder lässt sich das
    // Symbol nicht zerlegen, wird die Order abgelehnt (fail closed).
    if !current_price.is_finite() || current_price <= 0.0 {
        return Err(LiveLoopError::RiskViolation(format!(
            "ungültiger Preis {current_price} für die Eigenkapital-Bewertung"
        )));
    }
    let (base, quote) = split_symbol(&order_req.symbol).ok_or_else(|| {
        LiveLoopError::ExchangeError(format!(
            "Symbol {} lässt sich nicht in Basis/Quote zerlegen",
            order_req.symbol
        ))
    })?;
    let balances = exchange_trading
        .get_balance()
        .await
        .map_err(|e| LiveLoopError::ExchangeError(format!("Kontostand: {e}")))?;
    let equity = pair_equity(&balances, &base, &quote, current_price);

    if let Some(limit) = exposure {
        let held = balances
            .balances
            .get(&base)
            .map_or(0.0, |b| b.free + b.locked);
        limit
            .check(order_req.side, order_req.quantity, current_price, held)
            .map_err(LiveLoopError::RiskViolation)?;
    }
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
        /// Gehaltene BTC (Basis-Bestand); 0 = kein Eintrag im Konto.
        btc: f64,
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
                Some(free) => {
                    let mut balances =
                        HashMap::from([("USDT".to_string(), AccountBalance { free, locked: 0.0 })]);
                    if self.btc > 0.0 {
                        balances.insert(
                            "BTC".to_string(),
                            AccountBalance {
                                free: self.btc,
                                locked: 0.0,
                            },
                        );
                    }
                    Ok(Account { balances })
                }
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
        cap: Option<f64>,
    }

    impl Harness {
        fn with_cap(mut self, cap: f64) -> Self {
            self.cap = Some(cap);
            self
        }

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
                cap: None,
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
                btc: 0.0,
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
                max_notional: self.cap,
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

    fn trading_with(usdt: f64, btc: f64) -> MockTrading {
        MockTrading {
            usdt: Some(usdt),
            btc,
            placed: Arc::default(),
            cancelled: Arc::default(),
        }
    }

    #[tokio::test]
    async fn bought_coins_do_not_look_like_a_drawdown_to_the_risk_guard() {
        // Arrange: 5 % Drawdown-Limit, Referenzpreis 50_000.
        let mut guard = RiskGuard::new(omnitrade_risk::RiskLimits::new(
            1_000_000_000.0,
            5.0,
            1_000_000_000.0,
        ));
        let req = OrderRequest::market("BTCUSDT".into(), Side::Buy, 0.0001);

        // Act: erste Order bei 10_000 USDT setzt die Spitze.
        place_order_with_risk_check(
            &trading_with(10_000.0, 0.0),
            &mut guard,
            &req,
            50_000.0,
            10_000.0,
        )
        .await
        .expect("first order passes");
        // Nach einem Kauf: 5_000 USDT + 0.1 BTC (= 5_000 USDT) bleiben 10_000 Eigenkapital.
        let after_buy = place_order_with_risk_check(
            &trading_with(5_000.0, 0.1),
            &mut guard,
            &req,
            50_000.0,
            10_000.0,
        )
        .await;

        // Assert: ohne Bewertung der BTC sähe der Guard 50 % Drawdown und lehnte ab.
        assert!(after_buy.is_ok(), "{after_buy:?}");
    }

    #[tokio::test]
    async fn real_loss_is_still_blocked_after_valuing_holdings() {
        // Arrange
        let mut guard = RiskGuard::new(omnitrade_risk::RiskLimits::new(
            1_000_000_000.0,
            5.0,
            1_000_000_000.0,
        ));
        let req = OrderRequest::market("BTCUSDT".into(), Side::Buy, 0.0001);
        place_order_with_risk_check(
            &trading_with(10_000.0, 0.0),
            &mut guard,
            &req,
            50_000.0,
            10_000.0,
        )
        .await
        .expect("first order passes");

        // Act: Preis fällt auf 40_000, 5_000 USDT + 0.1 BTC = 9_000, also 10 % Drawdown.
        let res = place_order_with_risk_check(
            &trading_with(5_000.0, 0.1),
            &mut guard,
            &req,
            40_000.0,
            10_000.0,
        )
        .await;

        // Assert
        assert!(
            matches!(res, Err(LiveLoopError::RiskViolation(_))),
            "{res:?}"
        );
    }

    #[test]
    fn split_symbol_handles_all_exchange_notations() {
        let pair = |b: &str, q: &str| Some((b.to_string(), q.to_string()));
        assert_eq!(split_symbol("BTCUSDT"), pair("BTC", "USDT"));
        assert_eq!(split_symbol("btcusdc"), pair("BTC", "USDC"));
        assert_eq!(split_symbol("ETHBTC"), pair("ETH", "BTC"));
        assert_eq!(split_symbol("BNBUSDT"), pair("BNB", "USDT"));
        assert_eq!(split_symbol("USDCUSDT"), pair("USDC", "USDT"));
        assert_eq!(split_symbol("BTC-USDT"), pair("BTC", "USDT"));
        assert_eq!(split_symbol("btc/usd"), pair("BTC", "USD"));
        assert_eq!(split_symbol("BTCEUR"), pair("BTC", "EUR"));
    }

    #[test]
    fn split_symbol_rejects_unsplittable_input() {
        for bad in [
            "",
            "USDT",
            "BTC-",
            "-USDT",
            "A-B-C",
            "BTCXYZ",
            "BTC/USD/EUR",
        ] {
            assert_eq!(split_symbol(bad), None, "{bad}");
        }
    }

    #[test]
    fn pair_equity_values_base_holdings_at_price() {
        // Arrange
        let account = Account {
            balances: HashMap::from([
                (
                    "USDT".to_string(),
                    AccountBalance {
                        free: 5_000.0,
                        locked: 1_000.0,
                    },
                ),
                (
                    "BTC".to_string(),
                    AccountBalance {
                        free: 0.1,
                        locked: 0.05,
                    },
                ),
                (
                    "ETH".to_string(),
                    AccountBalance {
                        free: 99.0,
                        locked: 0.0,
                    },
                ),
            ]),
        };

        // Act & Assert: fremde Assets (ETH) zählen nicht, gesperrte Bestände schon.
        assert!((pair_equity(&account, "BTC", "USDT", 50_000.0) - 13_500.0).abs() < 1e-9);
        assert!((pair_equity(&account, "SOL", "USDT", 50_000.0) - 6_000.0).abs() < 1e-9);
    }

    #[tokio::test]
    async fn invalid_price_or_symbol_is_rejected_fail_closed() {
        // Arrange
        let mut guard = RiskGuard::testnet();
        let ok = OrderRequest::market("BTCUSDT".into(), Side::Buy, 0.0001);
        let bad_symbol = OrderRequest::market("FOO".into(), Side::Buy, 0.0001);
        let trading = trading_with(10_000.0, 0.0);

        // Act & Assert
        for price in [0.0, -1.0, f64::NAN, f64::INFINITY] {
            let res = place_order_with_risk_check(&trading, &mut guard, &ok, price, 1000.0).await;
            assert!(
                matches!(res, Err(LiveLoopError::RiskViolation(_))),
                "{price}"
            );
        }
        let res =
            place_order_with_risk_check(&trading, &mut guard, &bad_symbol, 50_000.0, 1000.0).await;
        assert!(
            matches!(res, Err(LiveLoopError::ExchangeError(_))),
            "{res:?}"
        );
        assert!(trading.placed.lock().expect("placed").is_empty());
    }

    #[tokio::test]
    async fn loss_limit_uses_equity_at_run_start_not_declared_capital() {
        // Arrange: deklariertes Startkapital 10_000, das Konto hält aber 93_000.
        let limits = omnitrade_risk::RiskLimits::new(1_000_000_000.0, 100.0, 2_000.0);
        let mut guard = RiskGuard::new(limits).with_run_baseline();
        let req = OrderRequest::market("BTCUSDT".into(), Side::Buy, 0.0001);
        place_order_with_risk_check(
            &trading_with(93_000.0, 0.0),
            &mut guard,
            &req,
            50_000.0,
            10_000.0,
        )
        .await
        .expect("first order sets the baseline");

        // Act: 3_000 Verlust seit Laufbeginn (> 2_000), obwohl 90_000 weit über 10_000 liegt.
        let res = place_order_with_risk_check(
            &trading_with(90_000.0, 0.0),
            &mut guard,
            &req,
            50_000.0,
            10_000.0,
        )
        .await;

        // Assert
        assert!(
            matches!(res, Err(LiveLoopError::RiskViolation(_))),
            "{res:?}"
        );
    }

    #[test]
    fn exposure_cap_limits_what_the_run_builds_up() {
        // Arrange: Deckel 200, Preis 100 → höchstens 2 Einheiten Position aus diesem Lauf.
        let mut limit = ExposureLimit::new(200.0);

        // Act & Assert
        assert!(limit.check(Side::Buy, 1.0, 100.0, 5.0).is_ok());
        assert!(
            limit.check(Side::Buy, 1.0, 100.0, 6.0).is_ok(),
            "zweite Einheit: 200"
        );
        let over = limit.check(Side::Buy, 1.0, 100.0, 7.0);
        assert!(
            matches!(&over, Err(m) if m.contains("Positionsdeckel")),
            "{over:?}"
        );
    }

    #[test]
    fn exposure_cap_ignores_preexisting_holdings_and_never_sells_them() {
        // Arrange: das Konto hält schon 5 Einheiten, bevor der Lauf beginnt.
        let mut limit = ExposureLimit::new(150.0);

        // Act & Assert: Kaufen zählt ab dem Startbestand, nicht ab 0.
        assert!(limit.check(Side::Buy, 1.0, 100.0, 5.0).is_ok());
        // Verkaufen vor dem ersten Kauf: Lauf besitzt nichts, der Bestand bleibt tabu.
        let mut fresh = ExposureLimit::new(150.0);
        let sell = fresh.check(Side::Sell, 1.0, 100.0, 5.0);
        assert!(
            matches!(&sell, Err(m) if m.contains("übersteigt")),
            "{sell:?}"
        );
        // Nach dem Kauf (Bestand 6) darf die gekaufte Einheit zurück, nicht mehr.
        assert!(limit.check(Side::Sell, 1.0, 100.0, 6.0).is_ok());
        assert!(limit.check(Side::Sell, 2.0, 100.0, 6.0).is_err());
    }

    #[test]
    fn exposure_cap_sell_tolerates_fee_shortfall() {
        // Arrange: 0.001 gekauft, Gebühr in der Basis → Bestand nur 0.000999.
        let mut limit = ExposureLimit::new(1_000.0);
        limit.check(Side::Buy, 0.001, 50_000.0, 1.0).expect("buy");

        // Act & Assert
        assert!(limit.check(Side::Sell, 0.001, 50_000.0, 1.000999).is_ok());
    }

    #[test]
    fn mainnet_cap_validation() {
        assert!(valid_mainnet_cap(Some(20.0)));
        assert!(valid_mainnet_cap(Some(MAINNET_HARD_CAP)));
        for bad in [
            None,
            Some(0.0),
            Some(-1.0),
            Some(MAINNET_HARD_CAP + 0.01),
            Some(f64::NAN),
            Some(f64::INFINITY),
        ] {
            assert!(!valid_mainnet_cap(bad), "{bad:?}");
        }
    }

    #[tokio::test]
    async fn mainnet_with_cap_above_hard_limit_is_rejected_before_any_exchange_call() {
        // Arrange
        let h = Harness::new("mainnet-over", BUY_BELOW_40K).with_cap(MAINNET_HARD_CAP + 1.0);

        // Act
        let result = h
            .run(&[35000.0], Some(1000.0), Network::Mainnet, 0.001)
            .await;

        // Assert
        assert!(matches!(result, Err(LiveLoopError::NetworkError(_))));
        assert!(h.log.lock().expect("log").is_empty());
    }

    #[tokio::test]
    async fn mainnet_with_valid_cap_runs_and_blocks_orders_over_the_cap() {
        // Arrange: Deckel 20, Order 0.001 BTC @ 35000 = 35 > 20 → blockiert, kein Aufruf an die Börse.
        let h = Harness::new("mainnet-cap", BUY_BELOW_40K).with_cap(20.0);

        // Act
        let result = h
            .run(&[35000.0], Some(1000.0), Network::Mainnet, 0.001)
            .await;

        // Assert
        assert!(result.is_ok(), "{result:?}");
        assert!(
            h.placed.lock().expect("placed").is_empty(),
            "Order über Deckel darf nicht raus"
        );
    }

    #[tokio::test]
    async fn testnet_cap_allows_orders_within_the_cap() {
        // Arrange: Deckel 50, Order 0.001 @ 35000 = 35 ≤ 50.
        let h = Harness::new("testnet-cap", BUY_BELOW_40K).with_cap(50.0);

        // Act
        let result = h
            .run(&[35000.0], Some(1000.0), Network::Testnet, 0.001)
            .await;

        // Assert
        assert!(result.is_ok(), "{result:?}");
        assert_eq!(h.placed.lock().expect("placed").len(), 1);
    }

    #[tokio::test]
    async fn non_positive_cap_is_rejected_even_on_testnet() {
        let h = Harness::new("cap-zero", BUY_BELOW_40K).with_cap(0.0);
        let result = h
            .run(&[35000.0], Some(1000.0), Network::Testnet, 0.001)
            .await;
        assert!(matches!(result, Err(LiveLoopError::NetworkError(_))));
    }
}
