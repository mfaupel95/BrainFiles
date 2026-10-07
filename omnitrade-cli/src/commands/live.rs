//! Live trading command handler.
//!
//! Orchestrates live trading setup: initializes exchange connections,
//! instantiates RiskGuard, and delegates to the live_loop.

use crate::grid_loop::{grid_loop, GridLiveConfig};
use crate::kill_switch;
use crate::live_loop::{live_loop, LiveConfig};
use omnitrade_exchange::{credentials, BinanceClient, Keystore, Network};
use omnitrade_risk::guard::RiskGuard;
use omnitrade_script::GridConfig;
use std::path::Path;
use std::time::Duration;
use tracing::info;

/// Abstand der Fill-Abfragen im Grid-Betrieb.
const GRID_POLL_SECS: u64 = 5;
/// Tick-Size-Annahme (BTCUSDT-artig); abweichende Symbole lehnt die Börse ab.
const GRID_PRICE_DECIMALS: u32 = 2;
/// Step-Size-Annahme (BTCUSDT-artig); abweichende Symbole lehnt die Börse ab.
const GRID_QTY_DECIMALS: u32 = 5;

/// Handles the live trading command.
///
/// Currently supports script-based trading only.
/// Grid-Betrieb (`--grid-config`) läuft nur auf dem Testnet.
/// Sets up exchange connections and starts the live trading event loop.
/// Returns error if setup fails; the live loop itself handles individual
/// order placement errors gracefully.
///
/// # Errors
/// Returns error if network parsing fails, file I/O fails,
/// or Binance connection/credential issues occur.
pub async fn handle_live(
    script_path: Option<&Path>,
    grid_config_path: Option<&Path>,
    symbol: &str,
    network_str: &str,
    initial_capital: f64,
    order_quantity: f64,
) -> Result<(), Box<dyn std::error::Error>> {
    // Validate that either script or grid is specified
    if script_path.is_none() && grid_config_path.is_none() {
        return Err("Error: either --script or --grid-config must be provided".into());
    }

    // Parse network string
    let network = match network_str {
        "testnet" => Network::Testnet,
        "mainnet" => Network::Mainnet,
        other => {
            return Err(format!("Invalid network: {}. Use 'testnet' or 'mainnet'", other).into())
        }
    };

    // Mainnet safety gate: require explicit environment variable
    if network == Network::Mainnet && std::env::var("OMNITRADE_MAINNET_APPROVED").is_err() {
        return Err(
            "Error: Mainnet trading requires OMNITRADE_MAINNET_APPROVED environment variable"
                .into(),
        );
    }

    // Gesetzter Not-Aus verhindert den Start (fail closed).
    let kill_file = kill_switch::default_path();
    if kill_switch::is_engaged(&kill_file) {
        return Err(format!(
            "Not-Aus ist gesetzt ({}). Aufheben mit: omnitrade-cli kill --reset",
            kill_file.display()
        )
        .into());
    }

    // Initialize risk guard with appropriate limits
    let mut risk_guard = match network {
        Network::Testnet => RiskGuard::testnet(),
        Network::Mainnet => RiskGuard::mainnet(),
    };

    info!("Starting live trading on {} (symbol: {})", network, symbol);
    info!("Initial capital: {}", initial_capital);

    // Handle script-based trading
    if let Some(script_path) = script_path {
        info!("Using strategy script: {}", script_path.display());
        info!("Script-based trading mode enabled");

        let creds = load_credentials(network)?;
        let trading_creds = creds.clone();

        // Two clients, one per role: the stream client owns the WebSocket
        // connection (connect() takes &mut self), the trading client places
        // orders (takes &self). BinanceClient is not Clone, so each role gets
        // its own instance built from the same credentials.
        let mut stream_client = BinanceClient::for_network(network);
        stream_client.set_credentials(creds)?;
        let mut trading_client = BinanceClient::new();
        trading_client.set_credentials(trading_creds)?;

        // Run the live loop
        let script_str = script_path.to_string_lossy().to_string();
        let config = LiveConfig {
            script_path: &script_str,
            symbol,
            network,
            initial_capital,
            order_quantity,
            kill_file: &kill_file,
        };
        live_loop(&config, stream_client, trading_client, &mut risk_guard).await?;

        info!("Live trading loop completed gracefully");
    } else if let Some(grid_path) = grid_config_path {
        info!("Grid trading mode: {}", grid_path.display());

        // Wie die Skript-Schleife: Mainnet bleibt gesperrt, bis Phase-3-Gates stehen.
        if network == Network::Mainnet {
            return Err("Grid-Live auf Mainnet ist gesperrt (nur Testnet)".into());
        }

        let grid = GridConfig::from_json(&std::fs::read_to_string(grid_path)?)
            .map_err(|e| format!("Grid-Konfiguration ungültig: {e}"))?;

        let mut trading_client = BinanceClient::new();
        trading_client.set_credentials(load_credentials(network)?)?;

        let config = GridLiveConfig {
            grid: &grid,
            symbol,
            initial_capital,
            kill_file: &kill_file,
            poll_interval: Duration::from_secs(GRID_POLL_SECS),
            price_decimals: GRID_PRICE_DECIMALS,
            qty_decimals: GRID_QTY_DECIMALS,
        };
        grid_loop(&config, trading_client, &mut risk_guard).await?;

        info!("Grid-Lauf beendet");
    }

    Ok(())
}

/// Zugänge: Keystore (getrennt je Netzwerk) hat Vorrang, Umgebungsvariablen
/// nur als Fallback für Läufe ohne Credential Manager.
fn load_credentials(
    network: Network,
) -> Result<credentials::ApiCredentials, Box<dyn std::error::Error>> {
    let creds = if Keystore::credentials_exist("binance", network) {
        Keystore::load_credentials("binance", network).map_err(|e| format!("Keystore: {e}"))?
    } else {
        let api_key = std::env::var("BINANCE_API_KEY").map_err(|_| {
            "Keine Zugänge: weder Keystore-Eintrag omnitrade/binance/<netzwerk> noch BINANCE_API_KEY"
        })?;
        let api_secret = std::env::var("BINANCE_API_SECRET")
            .map_err(|_| "BINANCE_API_SECRET environment variable not set")?;
        credentials::ApiCredentials::new(api_key, api_secret, network)
    };
    Ok(creds)
}
