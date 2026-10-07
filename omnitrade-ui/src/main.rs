//! Main application entry point for `omnitrade-ui`.
//!
//! Usage: `omnitrade-ui [SYMBOL] [testnet|mainnet]` (defaults: `BTCUSDT`, `testnet`).
//! The GUI only consumes public market data; it never places orders.

use std::sync::{Arc, RwLock};

use omnitrade_exchange::Network;
use omnitrade_ui::feed::spawn_feed;
use omnitrade_ui::{OmniTradeApp, UIState};

fn parse_network(arg: Option<&str>) -> Result<Network, String> {
    match arg {
        None | Some("testnet") => Ok(Network::Testnet),
        Some("mainnet") => Ok(Network::Mainnet),
        Some(other) => Err(format!("Unbekanntes Netzwerk '{other}' (testnet|mainnet)")),
    }
}

fn main() -> eframe::Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let symbol = args
        .first()
        .map(|s| s.to_uppercase())
        .unwrap_or_else(|| "BTCUSDT".to_string());
    let network = match parse_network(args.get(1).map(String::as_str)) {
        Ok(n) => n,
        Err(msg) => {
            eprintln!("{msg}");
            std::process::exit(2);
        }
    };

    let state = Arc::new(RwLock::new(UIState::new()));
    if let Err(e) = spawn_feed(Arc::clone(&state), symbol.clone(), network) {
        eprintln!("Feed konnte nicht gestartet werden: {e}");
        std::process::exit(1);
    }
    let app = OmniTradeApp::with_symbol(state, symbol);

    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1280.0, 800.0])
            .with_title("omnitrade"),
        ..Default::default()
    };

    eframe::run_native("omnitrade", options, Box::new(|_cc| Ok(Box::new(app))))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_network() {
        assert_eq!(parse_network(None), Ok(Network::Testnet));
        assert_eq!(parse_network(Some("mainnet")), Ok(Network::Mainnet));
        assert!(parse_network(Some("foo")).is_err());
    }
}
