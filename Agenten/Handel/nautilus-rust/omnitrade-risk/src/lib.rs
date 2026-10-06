//! omnitrade-risk — Sizing/Drawdown/Kill-Switch.
//!
//! Die Risiko-/Sizing-Logik der Execution-Ebene. Konsumiert das
//! `Verdict`-Urteil aus `quant-strategy` als Kill-Switch-Signal; die
//! Evidenz-Entscheidung selbst bleibt in `quant-strategy`.

use quant_strategy::evidence::Verdict;

/// Eine Order-Anfrage, die der Risiko-Check prueft.
#[derive(Debug, Clone, Default)]
pub struct OrderRequest {
    pub units: u64,
    pub name: String,
}

/// Ein Risiko-Verstoss.
#[derive(Debug)]
pub struct RiskViolation(pub String);

/// Risiko-/Sizing-Limits. Die Zahlen kommen aus der `wachen.json` der Spur.
#[derive(Debug, Clone, Default)]
pub struct RiskLimits {
    pub max_units_per_name: u64,
    pub drawdown_halbierung_usd: f64,
}

impl RiskLimits {
    /// Prueft eine Order gegen die Limits.
    pub fn check(&self, req: &OrderRequest) -> Result<(), RiskViolation> {
        if req.units > self.max_units_per_name {
            return Err(RiskViolation(format!(
                "Order {}: {} units > max {}",
                req.name, req.units, self.max_units_per_name
            )));
        }
        Ok(())
    }

    /// Drawdown-Halbierung: je naeher der Drawdown an der Schwelle, desto
    /// kleiner die Groesse. Faktor < 1.0 unterhalb der Schwelle.
    pub fn groessenfaktor(drawdown_halbierung_usd: f64, drawdown: f64) -> f64 {
        if drawdown_halbierung_usd <= 0.0 {
            return 1.0;
        }
        if drawdown >= drawdown_halbierung_usd {
            return 0.0;
        }
        // linear von 1.0 (drawdown=0) auf 0.0 (drawdown=Schwelle)
        1.0 - (drawdown / drawdown_halbierung_usd)
    }
}

/// Kill-Switch: ein `Verdict::Refuse` blockiert die Order.
pub fn kill_switch(verdict: &Verdict) -> bool {
    matches!(verdict, Verdict::Refuse { .. })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_order_over_max_units() {
        let limits = RiskLimits {
            max_units_per_name: 3,
            ..Default::default()
        };
        let req = OrderRequest {
            units: 4,
            ..Default::default()
        };
        assert!(limits.check(&req).is_err());
    }

    #[test]
    fn drawdown_halving_reduces_size() {
        // drawdown_halbierung_usd = 1.0 * buch_risiko
        let factor = RiskLimits::groessenfaktor(36.0, 30.0); // drawdown 30 < 36
        assert!(factor < 1.0);
    }

    #[test]
    fn admits_order_within_limits() {
        let limits = RiskLimits {
            max_units_per_name: 3,
            ..Default::default()
        };
        let req = OrderRequest {
            units: 2,
            ..Default::default()
        };
        assert!(limits.check(&req).is_ok());
    }
}
