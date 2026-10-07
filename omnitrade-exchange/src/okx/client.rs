//! OKX WebSocket v5 streaming client (public market data).
//!
//! Candles live on the `/business` endpoint, order books on `/public`, so the client
//! opens one connection per endpoint that has subscriptions.

use std::time::Duration;

use async_trait::async_trait;
use futures_util::{SinkExt, StreamExt};
use omnitrade_core::Candle;
use serde_json::json;
use tokio::sync::{mpsc, watch};
use tokio::task::JoinHandle;
use tokio_tungstenite::tungstenite::Message;
use tracing::{info, warn};

use crate::credentials::Network;
use crate::error::ExchangeError;
use crate::okx::router::OkxRouter;
use crate::traits::{DepthUpdate, ExchangeInfo, ExchangeStream};

const RAW_CHANNEL_CAPACITY: usize = 100;
/// OKX closes connections that stay silent for 30 s; a text `ping` keeps them open.
const PING_INTERVAL: Duration = Duration::from_secs(20);

/// Production WebSocket endpoints.
pub const PUBLIC_URL: &str = "wss://ws.okx.com:8443/ws/v5/public";
/// Production WebSocket endpoint for candles.
pub const BUSINESS_URL: &str = "wss://ws.okx.com:8443/ws/v5/business";
/// Demo-trading WebSocket endpoints.
pub const DEMO_PUBLIC_URL: &str = "wss://wspap.okx.com:8443/ws/v5/public";
/// Demo-trading WebSocket endpoint for candles.
pub const DEMO_BUSINESS_URL: &str = "wss://wspap.okx.com:8443/ws/v5/business";

/// Maps an interval string to OKX's channel suffix (`1m`, `1H`, `1D`, ...).
pub(crate) fn interval_code(interval: &str) -> Option<&'static str> {
    match interval {
        "1m" => Some("1m"),
        "3m" => Some("3m"),
        "5m" => Some("5m"),
        "15m" => Some("15m"),
        "30m" => Some("30m"),
        "1h" => Some("1H"),
        "2h" => Some("2H"),
        "4h" => Some("4H"),
        "1d" => Some("1D"),
        "1w" => Some("1W"),
        _ => None,
    }
}

/// OKX instruments are `BASE-QUOTE` (e.g. `BTC-USDT`).
fn validate_symbol(symbol: &str) -> Result<String, ExchangeError> {
    let upper = symbol.to_uppercase();
    match upper.split_once('-') {
        Some((base, quote)) if !base.is_empty() && !quote.is_empty() && !quote.contains('-') => {
            Ok(upper)
        }
        _ => Err(ExchangeError::SubscriptionFailed {
            symbol: symbol.to_string(),
            reason: "OKX-Symbole haben die Form BASE-QUOTE, z. B. BTC-USDT".to_string(),
        }),
    }
}

/// Streaming client for OKX market data.
pub struct OkxClient {
    public_url: String,
    business_url: String,
    public_subs: Vec<String>,
    business_subs: Vec<String>,
    router: Option<OkxRouter>,
    raw_tx: mpsc::Sender<String>,
    tasks: Vec<JoinHandle<()>>,
    router_task: Option<JoinHandle<Result<(), ExchangeError>>>,
    shutdown_tx: Option<watch::Sender<bool>>,
    is_connected: bool,
}

impl OkxClient {
    /// Creates a client for production endpoints.
    pub fn new() -> Self {
        Self::with_urls(PUBLIC_URL, BUSINESS_URL)
    }

    /// Creates a client whose endpoints match the network (`Testnet` = demo trading).
    pub fn for_network(network: Network) -> Self {
        match network {
            Network::Testnet => Self::with_urls(DEMO_PUBLIC_URL, DEMO_BUSINESS_URL),
            Network::Mainnet => Self::new(),
        }
    }

    /// Creates a client for custom endpoints (tests).
    pub fn with_urls(public_url: impl Into<String>, business_url: impl Into<String>) -> Self {
        let (raw_tx, raw_rx) = mpsc::channel(RAW_CHANNEL_CAPACITY);
        Self {
            public_url: public_url.into(),
            business_url: business_url.into(),
            public_subs: Vec::new(),
            business_subs: Vec::new(),
            router: Some(OkxRouter::new(raw_rx)),
            raw_tx,
            tasks: Vec::new(),
            router_task: None,
            shutdown_tx: None,
            is_connected: false,
        }
    }

    /// Subscribe messages sent on the `/public` endpoint after connecting.
    pub fn public_subscriptions(&self) -> &[String] {
        &self.public_subs
    }

    /// Subscribe messages sent on the `/business` endpoint after connecting.
    pub fn business_subscriptions(&self) -> &[String] {
        &self.business_subs
    }

    async fn open(
        &mut self,
        url: String,
        subs: Vec<String>,
        mut shutdown: watch::Receiver<bool>,
    ) -> Result<(), ExchangeError> {
        let (ws, _) = tokio_tungstenite::connect_async(&url).await.map_err(|e| {
            ExchangeError::ConnectionFailed {
                url: url.clone(),
                reason: e.to_string(),
            }
        })?;
        info!("Connected to OKX WebSocket at '{url}'");
        let (mut write, mut read) = ws.split();
        for sub in subs {
            write.send(Message::Text(sub.into())).await.map_err(|e| {
                ExchangeError::ConnectionFailed {
                    url: url.clone(),
                    reason: format!("subscribe failed: {e}"),
                }
            })?;
        }
        let raw_tx = self.raw_tx.clone();
        self.tasks.push(tokio::spawn(async move {
            let mut ping = tokio::time::interval(PING_INTERVAL);
            loop {
                tokio::select! {
                    _ = shutdown.changed() => {
                        let _ = write.close().await;
                        break;
                    }
                    _ = ping.tick() => {
                        if write.send(Message::Text("ping".into())).await.is_err() {
                            break;
                        }
                    }
                    msg = read.next() => match msg {
                        Some(Ok(Message::Text(text))) => {
                            if text.as_str() == "pong" {
                                continue;
                            }
                            if raw_tx.send(text.to_string()).await.is_err() {
                                break;
                            }
                        }
                        Some(Ok(Message::Ping(payload))) => {
                            let _ = write.send(Message::Pong(payload)).await;
                        }
                        Some(Ok(Message::Close(_))) | None => {
                            info!("OKX WebSocket closed");
                            break;
                        }
                        Some(Ok(_)) => {}
                        Some(Err(err)) => {
                            warn!("OKX WebSocket read error: {err}");
                            break;
                        }
                    }
                }
            }
        }));
        Ok(())
    }
}

impl Default for OkxClient {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ExchangeStream for OkxClient {
    async fn connect(&mut self) -> Result<(), ExchangeError> {
        if self.is_connected || self.router.is_none() {
            return Err(ExchangeError::ConnectionFailed {
                url: self.public_url.clone(),
                reason: "client is already connected".to_string(),
            });
        }
        let (shutdown_tx, shutdown_rx) = watch::channel(false);
        self.shutdown_tx = Some(shutdown_tx);

        let endpoints = [
            (self.public_url.clone(), self.public_subs.clone()),
            (self.business_url.clone(), self.business_subs.clone()),
        ];
        for (url, subs) in endpoints {
            if subs.is_empty() {
                continue;
            }
            if let Err(err) = self.open(url, subs, shutdown_rx.clone()).await {
                self.disconnect().await?;
                return Err(err);
            }
        }

        if let Some(mut router) = self.router.take() {
            self.router_task = Some(tokio::spawn(async move { router.run().await }));
        }
        self.is_connected = true;
        Ok(())
    }

    /// Must be called *before* [`connect()`](Self::connect). Only confirmed candles arrive.
    async fn subscribe_candles(
        &mut self,
        symbol: &str,
        interval: &str,
    ) -> Result<mpsc::Receiver<Candle>, ExchangeError> {
        let symbol = validate_symbol(symbol)?;
        let code = interval_code(interval).ok_or_else(|| ExchangeError::SubscriptionFailed {
            symbol: symbol.clone(),
            reason: format!("Intervall '{interval}' wird von OKX nicht unterstützt"),
        })?;
        let router = self
            .router
            .as_mut()
            .ok_or_else(|| ExchangeError::SubscriptionFailed {
                symbol: symbol.clone(),
                reason: "cannot subscribe after connection has been established".to_string(),
            })?;
        let rx = router.register_candle_channel(&symbol);
        self.business_subs.push(
            json!({"op": "subscribe", "args": [{"channel": format!("candle{code}"), "instId": symbol}]})
                .to_string(),
        );
        Ok(rx)
    }

    /// Must be called *before* [`connect()`](Self::connect). The first message per
    /// instrument is a snapshot, later ones are deltas (size 0 removes a level).
    async fn subscribe_depth(
        &mut self,
        symbol: &str,
    ) -> Result<mpsc::Receiver<DepthUpdate>, ExchangeError> {
        let symbol = validate_symbol(symbol)?;
        let router = self
            .router
            .as_mut()
            .ok_or_else(|| ExchangeError::SubscriptionFailed {
                symbol: symbol.clone(),
                reason: "cannot subscribe after connection has been established".to_string(),
            })?;
        let rx = router.register_depth_channel(&symbol);
        self.public_subs.push(
            json!({"op": "subscribe", "args": [{"channel": "books", "instId": symbol}]})
                .to_string(),
        );
        Ok(rx)
    }

    async fn disconnect(&mut self) -> Result<(), ExchangeError> {
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(true);
        }
        for task in self.tasks.drain(..) {
            let _ = tokio::time::timeout(Duration::from_millis(500), task).await;
        }
        self.is_connected = false;
        if let Some(task) = self.router_task.take() {
            let _ = tokio::time::timeout(Duration::from_millis(500), task).await;
        }
        Ok(())
    }
}

impl ExchangeInfo for OkxClient {
    fn name(&self) -> &str {
        "OKX"
    }

    fn supported_intervals(&self) -> &[&str] {
        &["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1w"]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn candles_go_to_business_and_books_to_public() {
        // Arrange
        let mut client = OkxClient::new();

        // Act
        client
            .subscribe_candles("btc-usdt", "1h")
            .await
            .expect("candles");
        client.subscribe_depth("ETH-USDT").await.expect("depth");

        // Assert
        let candle: serde_json::Value =
            serde_json::from_str(&client.business_subscriptions()[0]).expect("json");
        assert_eq!(candle["op"], "subscribe");
        assert_eq!(candle["args"][0]["channel"], "candle1H");
        assert_eq!(candle["args"][0]["instId"], "BTC-USDT");
        let book: serde_json::Value =
            serde_json::from_str(&client.public_subscriptions()[0]).expect("json");
        assert_eq!(book["args"][0]["channel"], "books");
        assert_eq!(book["args"][0]["instId"], "ETH-USDT");
        assert_eq!(client.public_subscriptions().len(), 1);
        assert_eq!(client.business_subscriptions().len(), 1);
    }

    #[tokio::test]
    async fn rejects_bad_symbol_and_interval() {
        // Arrange
        let mut client = OkxClient::new();

        // Act & Assert
        assert!(client.subscribe_candles("BTCUSDT", "1m").await.is_err());
        assert!(client.subscribe_depth("BTC/USDT").await.is_err());
        assert!(client.subscribe_candles("BTC-USDT", "7m").await.is_err());
        assert!(client.business_subscriptions().is_empty());
        assert!(client.public_subscriptions().is_empty());
    }

    #[test]
    fn for_network_selects_matching_endpoints_and_info() {
        // Act
        let demo = OkxClient::for_network(Network::Testnet);
        let prod = OkxClient::for_network(Network::Mainnet);

        // Assert
        assert_eq!(demo.public_url, DEMO_PUBLIC_URL);
        assert_eq!(demo.business_url, DEMO_BUSINESS_URL);
        assert_eq!(prod.public_url, PUBLIC_URL);
        assert_eq!(prod.name(), "OKX");
        assert!(prod.supported_intervals().contains(&"1h"));
    }
}
