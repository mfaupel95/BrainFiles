//! # omnitrade-cli
//!
//! Headless command-line interface for backtesting strategies and running
//! automated integration tests without a GUI.

mod args;
mod backtest;
mod commands;
mod live_loop;

use args::{CliArgs, Commands};
use backtest::{run_backtest, BacktestConfig};
use clap::Parser;
use commands::{handle_kill, handle_live};

/// Initialize structured logging with environment-based filtering.
fn init_tracing() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    init_tracing();

    let args = CliArgs::parse();

    match args.command {
        Commands::Backtest {
            script,
            data,
            initial_balance,
            fee_rate,
            slippage_bps,
        } => {
            let config = BacktestConfig::new(script, data, initial_balance, fee_rate, slippage_bps);

            let result = run_backtest(&config)?;
            println!("=== Backtest Results ===");
            println!("Total PnL:       {:.2}", result.total_pnl);
            println!("Final Balance:   {:.2}", result.final_balance);
            println!("Total Trades:    {}", result.total_trades);
            println!("Win Rate:        {:.2}%", result.win_rate * 100.0);
            println!("Max Drawdown:    {:.2}%", result.max_drawdown * 100.0);
        }
        Commands::Validate { script } => {
            let script_content = std::fs::read_to_string(&script)?;
            let tokens = omnitrade_script::tokenize(&script_content)?;
            let _stmts = omnitrade_script::parse(&tokens)?;
            println!("Script validation successful: {:?}", script);
        }
        Commands::Live {
            script,
            grid_config,
            symbol,
            network,
            initial_capital,
        } => {
            let capital = initial_capital.unwrap_or(1000.0);
            handle_live(
                script.as_deref(),
                grid_config.as_deref(),
                &symbol,
                &network,
                capital,
            )
            .await?;
        }
        Commands::Kill => {
            handle_kill()?;
        }
    }

    Ok(())
}
