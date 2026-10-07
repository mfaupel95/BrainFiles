//! OKX connector: WebSocket v5 market data and REST trading (demo or production).
//!
//! `Network::Testnet` selects OKX **demo trading** (separate demo API keys, REST header
//! `x-simulated-trading: 1`, `wspap` WebSocket hosts).

pub mod client;
pub mod klines;
pub mod rest;
pub mod router;
pub mod signing;

pub use client::OkxClient;
pub use rest::OkxRestClient;
pub use router::OkxRouter;
pub use signing::OkxSigner;
