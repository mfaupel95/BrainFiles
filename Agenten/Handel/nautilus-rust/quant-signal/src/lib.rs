//! quant-signal — PLANE_NEUTRAL.
//!
//! Das gemeinsame Schema zwischen Research- und Execution-Ebene.
//! Haengt nur von serde ab — keine nautilus-*, keine candle-*.
//!
//! Was ueber die Grenze geht: Zielgewichte (Summe = 0) plus die vom
//! Produzenten GEMESSENEN Evidenz-Werte. Keine Schlussfolgerungen
//! (kein t, kein p, kein "admissible") — die bildet die Engine selbst.

use serde::{Deserialize, Serialize};

/// Ein Zielgewicht fuer ein Instrument. Summe ueber alle Eintraege = 0
/// (dollar-neutral). Plain number, kein Modell, kein Score.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RankedWeight {
    /// Venue-qualifizierte Instrument-ID, z. B. "BTC-USDT-SWAP.OKX".
    pub instrument_id: String,
    /// Zielgewicht, Summe ueber das Buch = 0.
    pub weight: f64,
}

/// Was der Produzent gemessen hat — Messwerte, keine Urteile.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BookEvidence {
    pub net_bps: f64,
    pub n: usize,
    pub se_bps: f64,
    pub folds: usize,
    pub positive_folds: usize,
}

/// Das Ranked Book, das die Research-Ebene schreibt und die
/// Execution-Ebene liest.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RankedBook {
    pub weights: Vec<RankedWeight>,
    pub evidence: BookEvidence,
}

impl RankedBook {
    /// Prueft, dass die Gewichte (nahezu) zu null summieren.
    pub fn is_dollar_neutral(&self, tol: f64) -> bool {
        let s: f64 = self.weights.iter().map(|w| w.weight).sum();
        s.abs() <= tol
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dollar_neutral_book_passes() {
        let book = RankedBook {
            weights: vec![
                RankedWeight {
                    instrument_id: "A.OKX".into(),
                    weight: 0.5,
                },
                RankedWeight {
                    instrument_id: "B.OKX".into(),
                    weight: -0.5,
                },
            ],
            evidence: BookEvidence {
                net_bps: 10.0,
                n: 100,
                se_bps: 2.0,
                folds: 5,
                positive_folds: 3,
            },
        };
        assert!(book.is_dollar_neutral(1e-9));
    }

    #[test]
    fn non_neutral_book_fails() {
        let book = RankedBook {
            weights: vec![RankedWeight {
                instrument_id: "A.OKX".into(),
                weight: 0.5,
            }],
            evidence: BookEvidence {
                net_bps: 10.0,
                n: 100,
                se_bps: 2.0,
                folds: 5,
                positive_folds: 3,
            },
        };
        assert!(!book.is_dollar_neutral(1e-9));
    }
}
