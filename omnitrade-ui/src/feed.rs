//! Background market-data feed: streams Binance candles and depth into [`UIState`].
//!
//! The feed is strictly read-only (public market data); the GUI never places orders.

use std::sync::{Arc, RwLock};
use std::thread::JoinHandle;
use std::time::Duration;

use omnitrade_exchange::{
    fetch_depth_snapshot, fetch_klines, BinanceClient, ExchangeError, ExchangeStream, Network,
};

use crate::state::UIState;

const CANDLE_INTERVAL: &str = "1m";
const HISTORY_CANDLES: usize = 200;
const DEPTH_SNAPSHOT_LEVELS: usize = 100;
const RECONNECT_DELAY: Duration = Duration::from_secs(5);

/// Starts the feed on a dedicated thread with its own Tokio runtime.
///
/// The thread reconnects after stream errors and runs until the process exits.
pub fn spawn_feed(
    state: Arc<RwLock<UIState>>,
    symbol: String,
    network: Network,
) -> std::io::Result<JoinHandle<()>> {
    std::thread::Builder::new()
        .name("omnitrade-feed".to_string())
        .spawn(move || {
            let runtime = match tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
            {
                Ok(rt) => rt,
                Err(e) => {
                    log(&state, format!("Feed konnte nicht starten: {e}"));
                    return;
                }
            };
            runtime.block_on(async {
                loop {
                    match run_session(&state, &symbol, network).await {
                        Ok(()) => log(&state, "Stream beendet, verbinde neu".to_string()),
                        Err(e) => log(&state, format!("Stream-Fehler: {e}, verbinde neu")),
                    }
                    set_connected(&state, false);
                    tokio::time::sleep(RECONNECT_DELAY).await;
                }
            });
        })
}

/// One connection lifetime: subscribe, connect and forward events until a channel closes.
async fn run_session(
    state: &Arc<RwLock<UIState>>,
    symbol: &str,
    network: Network,
) -> Result<(), ExchangeError> {
    load_history(state, symbol, network).await;

    let mut client = BinanceClient::for_network(network);
    let mut candles = client.subscribe_candles(symbol, CANDLE_INTERVAL).await?;
    let mut depth = client.subscribe_depth(symbol).await?;
    client.connect().await?;

    load_depth_snapshot(state, symbol, network).await;
    set_connected(state, true);
    log(
        state,
        format!("Verbunden: {symbol} ({network}), {CANDLE_INTERVAL}-Kerzen + Depth"),
    );

    loop {
        tokio::select! {
            candle = candles.recv() => match candle {
                Some(c) => with_state(state, |s| s.update_candle(symbol, c)),
                None => break,
            },
            update = depth.recv() => match update {
                Some(u) => with_state(state, |s| {
                    if let Err(e) = s.apply_depth(symbol, u.timestamp_ms, &u.bids, &u.asks) {
                        s.push_log(format!("Ungültiges Depth-Update verworfen: {e}"));
                    }
                }),
                None => break,
            },
        }
    }

    let _ = client.disconnect().await;
    Ok(())
}

/// Seeds the chart with recent candles; the stream only delivers closed candles.
async fn load_history(state: &Arc<RwLock<UIState>>, symbol: &str, network: Network) {
    match fetch_klines(network, symbol, CANDLE_INTERVAL, HISTORY_CANDLES).await {
        Ok(candles) => {
            let count = candles.len();
            with_state(state, |s| {
                s.set_candles(symbol, candles);
                s.push_log(format!("{count} historische Kerzen geladen"));
            });
        }
        Err(e) => log(state, format!("Historie nicht geladen: {e}")),
    }
}

/// Seeds the order book; the stream only carries changes, so unchanged levels would be missing.
async fn load_depth_snapshot(state: &Arc<RwLock<UIState>>, symbol: &str, network: Network) {
    match fetch_depth_snapshot(network, symbol, DEPTH_SNAPSHOT_LEVELS).await {
        Ok(snap) => with_state(state, |s| {
            if let Err(e) = s.set_orderbook_snapshot(symbol, &snap.bids, &snap.asks) {
                s.push_log(format!("Order-Book-Snapshot verworfen: {e}"));
            }
        }),
        Err(e) => log(state, format!("Order-Book-Snapshot nicht geladen: {e}")),
    }
}

fn with_state(state: &Arc<RwLock<UIState>>, f: impl FnOnce(&mut UIState)) {
    let mut guard = state
        .write()
        .unwrap_or_else(|poisoned| poisoned.into_inner());
    f(&mut guard);
}

fn set_connected(state: &Arc<RwLock<UIState>>, connected: bool) {
    with_state(state, |s| s.set_connected(connected));
}

fn log(state: &Arc<RwLock<UIState>>, line: String) {
    with_state(state, |s| s.push_log(line));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_log_and_connected_helpers_update_state() {
        // Arrange
        let state = Arc::new(RwLock::new(UIState::new()));

        // Act
        set_connected(&state, true);
        log(&state, "hallo".to_string());

        // Assert
        let guard = state.read().expect("lock");
        assert!(guard.is_connected());
        assert_eq!(guard.log.back().map(String::as_str), Some("hallo"));
    }
}
