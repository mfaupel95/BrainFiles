//! Live trading command handler.
//!
//! Orchestrates live trading setup: initializes exchange connections,
//! instantiates RiskGuard, and delegates to the live_loop.

use crate::live_loop::live_loop;
use omnitrade_exchange::{credentials, BinanceClient, Network};
use omnitrade_risk::guard::RiskGuard;
use std::path::Path;
use tracing::info;

/// Handles the live trading command.
///
/// Currently supports script-based trading only.
/// Grid-based trading will be implemented in a future phase.
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
    if network == Network::Mainnet
        && std::env::var("OMNITRADE_MAINNET_APPROVED").is_err() {
            return Err(
                "Error: Mainnet trading requires OMNITRADE_MAINNET_APPROVED environment variable"
                    .into(),
            );
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

        // Load credentials from environment
        let api_key = std::env::var("BINANCE_API_KEY")
            .map_err(|_| "BINANCE_API_KEY environment variable not set")?;
        let api_secret = std::env::var("BINANCE_API_SECRET")
            .map_err(|_| "BINANCE_API_SECRET environment variable not set")?;

        let creds_network = match network {
            Network::Testnet => credentials::Network::Testnet,
            Network::Mainnet => credentials::Network::Mainnet,
        };

        let creds = credentials::ApiCredentials::new(api_key, api_secret, creds_network);
        let trading_creds = creds.clone();

        // Two clients, one per role: the stream client owns the WebSocket
        // connection (connect() takes &mut self), the trading client places
        // orders (takes &self). BinanceClient is not Clone, so each role gets
        // its own instance built from the same credentials.
        let mut stream_client = BinanceClient::new();
        stream_client.set_credentials(creds)?;
        let mut trading_client = BinanceClient::new();
        trading_client.set_credentials(trading_creds)?;

        // Run the live loop
        let script_str = script_path.to_string_lossy().to_string();
        live_loop(
            &script_str,
            symbol,
            network,
            initial_capital,
            stream_client,
            trading_client,
            &mut risk_guard,
        )
        .await?;

        info!("Live trading loop completed gracefully");
    } else if grid_config_path.is_some() {
        info!("Grid trading mode requested");
        return Err("Grid-based live trading not yet implemented - use --script for now".into());
    }

    Ok(())
}
