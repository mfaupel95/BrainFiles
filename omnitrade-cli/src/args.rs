//! Command-line argument definitions and parsing for `omnitrade-cli`.

use clap::{Parser, Subcommand};
use std::path::PathBuf;

/// Command line arguments for `omnitrade-cli`.
#[derive(Debug, Parser, PartialEq)]
#[command(
    name = "omnitrade-cli",
    version,
    about = "Headless CLI runner for omnitrade"
)]
pub struct CliArgs {
    /// Subcommand to execute.
    #[command(subcommand)]
    pub command: Commands,
}

/// Available subcommands for `omnitrade-cli`.
#[derive(Debug, Subcommand, PartialEq)]
pub enum Commands {
    /// Run a backtest using a strategy script and market data.
    Backtest {
        /// Path to the strategy script.
        #[arg(long, value_name = "PATH")]
        script: PathBuf,

        /// Path to the market data file.
        #[arg(long, value_name = "PATH")]
        data: PathBuf,

        /// Initial account balance.
        #[arg(long, value_name = "AMOUNT", default_value_t = 10000.0)]
        initial_balance: f64,

        /// Trading fee rate.
        #[arg(long, value_name = "RATE", default_value_t = 0.001)]
        fee_rate: f64,

        /// Slippage in basis points.
        #[arg(long, value_name = "BPS", default_value_t = 5.0)]
        slippage_bps: f64,
    },
    /// Validate a strategy script for syntax and structural correctness.
    Validate {
        /// Path to the strategy script.
        #[arg(long, value_name = "PATH")]
        script: PathBuf,
    },
    /// Execute live trading on Binance with a strategy script or grid config.
    ///
    /// Connects to a live exchange, subscribes to market data, and places orders
    /// based on strategy signals OR grid configuration (mutually exclusive).
    /// Enforces risk limits via RiskGuard.
    /// Testnet by default; mainnet requires explicit flag.
    Live {
        /// Path to the strategy script (.omni file). Mutually exclusive with --grid-config.
        #[arg(long, value_name = "PATH")]
        script: Option<PathBuf>,

        /// Path to grid config file (JSON). Mutually exclusive with --script.
        #[arg(long, value_name = "PATH")]
        grid_config: Option<PathBuf>,

        /// Trading symbol (e.g., "BTCUSDT").
        #[arg(long, value_name = "SYMBOL")]
        symbol: String,

        /// Network: "testnet" or "mainnet".
        #[arg(long, value_name = "NETWORK", default_value = "testnet")]
        network: String,

        /// Initial account balance for trading.
        #[arg(long, value_name = "AMOUNT")]
        initial_capital: Option<f64>,
    },
    /// Emergency kill switch to halt all trading operations.
    ///
    /// Stops a running live trading process and closes all open positions.
    /// This is a safety mechanism and should be used when risk limits are breached
    /// or market conditions require immediate halt.
    Kill,
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::Parser;

    #[test]
    fn test_parse_backtest_all_flags() {
        // Arrange
        let args = vec![
            "omnitrade-cli",
            "backtest",
            "--script",
            "/path/to/script.omni",
            "--data",
            "/path/to/data.csv",
            "--initial-balance",
            "5000.0",
            "--fee-rate",
            "0.002",
            "--slippage-bps",
            "10.0",
        ];

        // Act
        let parsed = CliArgs::try_parse_from(args)
            .expect("Should successfully parse backtest command with all flags");

        // Assert
        if let Commands::Backtest {
            script,
            data,
            initial_balance,
            fee_rate,
            slippage_bps,
        } = parsed.command
        {
            assert_eq!(script, PathBuf::from("/path/to/script.omni"));
            assert_eq!(data, PathBuf::from("/path/to/data.csv"));
            assert!((initial_balance - 5000.0).abs() < f64::EPSILON);
            assert!((fee_rate - 0.002).abs() < f64::EPSILON);
            assert!((slippage_bps - 10.0).abs() < f64::EPSILON);
        } else {
            unreachable!("Expected Commands::Backtest variant");
        }
    }

    #[test]
    fn test_parse_backtest_default_values() {
        // Arrange
        let args = vec![
            "omnitrade-cli",
            "backtest",
            "--script",
            "script.omni",
            "--data",
            "data.csv",
        ];

        // Act
        let parsed = CliArgs::try_parse_from(args)
            .expect("Should successfully parse backtest command with default flags");

        // Assert
        if let Commands::Backtest {
            script,
            data,
            initial_balance,
            fee_rate,
            slippage_bps,
        } = parsed.command
        {
            assert_eq!(script, PathBuf::from("script.omni"));
            assert_eq!(data, PathBuf::from("data.csv"));
            assert!((initial_balance - 10000.0).abs() < f64::EPSILON);
            assert!((fee_rate - 0.001).abs() < f64::EPSILON);
            assert!((slippage_bps - 5.0).abs() < f64::EPSILON);
        } else {
            unreachable!("Expected Commands::Backtest variant");
        }
    }

    #[test]
    fn test_parse_validate_command() {
        // Arrange
        let args = vec!["omnitrade-cli", "validate", "--script", "strategy.omni"];

        // Act
        let parsed =
            CliArgs::try_parse_from(args).expect("Should successfully parse validate command");

        // Assert
        if let Commands::Validate { script } = parsed.command {
            assert_eq!(script, PathBuf::from("strategy.omni"));
        } else {
            unreachable!("Expected Commands::Validate variant");
        }
    }

    #[test]
    fn test_parse_kill_command() {
        // Arrange
        let args = vec!["omnitrade-cli", "kill"];

        // Act
        let parsed = CliArgs::try_parse_from(args).expect("Should successfully parse kill command");

        // Assert
        assert!(
            matches!(parsed.command, Commands::Kill),
            "Expected Commands::Kill variant"
        );
    }

    #[test]
    fn test_missing_required_argument_returns_error() {
        // Arrange
        let args = vec!["omnitrade-cli", "backtest", "--script", "script.omni"];

        // Act
        let result = CliArgs::try_parse_from(args);

        // Assert
        assert!(
            result.is_err(),
            "Expected error due to missing --data argument"
        );
    }

    #[test]
    fn test_parse_live_command_with_script() {
        // Arrange
        let args = vec![
            "omnitrade-cli",
            "live",
            "--script",
            "strategy.omni",
            "--symbol",
            "BTCUSDT",
        ];

        // Act
        let parsed = CliArgs::try_parse_from(args)
            .expect("Should successfully parse live command with script");

        // Assert
        if let Commands::Live {
            script,
            grid_config,
            symbol,
            network,
            initial_capital,
        } = parsed.command
        {
            assert_eq!(script, Some(PathBuf::from("strategy.omni")));
            assert_eq!(grid_config, None);
            assert_eq!(symbol, "BTCUSDT");
            assert_eq!(network, "testnet");
            assert_eq!(initial_capital, None);
        } else {
            unreachable!("Expected Commands::Live variant");
        }
    }

    #[test]
    fn test_parse_live_command_with_grid_config() {
        // Arrange
        let args = vec![
            "omnitrade-cli",
            "live",
            "--grid-config",
            "grid.json",
            "--symbol",
            "BTCUSDT",
        ];

        // Act
        let parsed = CliArgs::try_parse_from(args)
            .expect("Should successfully parse live command with grid config");

        // Assert
        if let Commands::Live {
            script,
            grid_config,
            symbol,
            network,
            initial_capital,
        } = parsed.command
        {
            assert_eq!(script, None);
            assert_eq!(grid_config, Some(PathBuf::from("grid.json")));
            assert_eq!(symbol, "BTCUSDT");
            assert_eq!(network, "testnet");
            assert_eq!(initial_capital, None);
        } else {
            unreachable!("Expected Commands::Live variant");
        }
    }

    #[test]
    fn test_parse_live_command_all_flags() {
        // Arrange
        let args = vec![
            "omnitrade-cli",
            "live",
            "--script",
            "strategy.omni",
            "--symbol",
            "ETHUSDT",
            "--network",
            "testnet",
            "--initial-capital",
            "5000.0",
        ];

        // Act
        let parsed = CliArgs::try_parse_from(args)
            .expect("Should successfully parse live command with all flags");

        // Assert
        if let Commands::Live {
            script,
            grid_config,
            symbol,
            network,
            initial_capital,
        } = parsed.command
        {
            assert_eq!(script, Some(PathBuf::from("strategy.omni")));
            assert_eq!(grid_config, None);
            assert_eq!(symbol, "ETHUSDT");
            assert_eq!(network, "testnet");
            assert_eq!(initial_capital, Some(5000.0));
        } else {
            unreachable!("Expected Commands::Live variant");
        }
    }
}
