//! Risk management layer for Omnitrade trading.
//!
//! Provides centralized risk controls including position limits, drawdown monitoring,
//! and emergency kill-switch functionality. All risk checks are enforced before order execution.

pub mod error;
pub mod guard;
pub mod kill_switch;
pub mod limits;

pub use error::{RiskError, RiskViolation};
pub use guard::RiskGuard;
pub use kill_switch::KillSwitch;
pub use limits::RiskLimits;
