//! quant-strategy — EvidenceGate/Verdict.
//!
//! Die Evidenz-Huerde der Execution-Ebene. Liest die vom Produzenten
//! GEMESSENEN Werte (`BookEvidence`) und bildet das Urteil SELBST — kein
//! t, kein p, kein "admissible" kommt ueber die Grenze. Die Huerde ist eine
//! kompilierte Konstante, kein Config-Feld: eine Strategie, die ihre eigene
//! Evidenz-Huerde senken kann, hat keine.
//!
//! Die Werte sind ueber Umgebungsvariablen konfigurierbar (T-258):
//!   MIN_EVIDENCE_T      — t-Schwelle (Vorgabe 2.0)
//!   MIN_EVIDENCE_FOLDS  — Mindest-Folds (Vorgabe 2)
//! Ohne die Variablen gilt die kompilierte Vorgabe.

use quant_signal::BookEvidence;
use std::env;

/// Die Evidenz-Huerde. Vorgabe 2.0, ueber MIN_EVIDENCE_T aenderbar.
pub fn min_evidence_t() -> f64 {
    env::var("MIN_EVIDENCE_T")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(2.0)
}

/// Mindestens zwei Folds, um Skill von Regime zu trennen.
/// Vorgabe 2, ueber MIN_EVIDENCE_FOLDS aenderbar.
pub fn min_evidence_folds() -> usize {
    env::var("MIN_EVIDENCE_FOLDS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(2)
}

/// Urteil der Engine ueber ein Buch.
pub enum Verdict {
    Admit,
    Refuse { reason: String },
}

/// Das Evidence-Gate: entscheidet, ob ein Buch demonstrierte Faehigkeit hat.
pub struct EvidenceGate;

impl EvidenceGate {
    pub fn decide(ev: &BookEvidence) -> Verdict {
        let min_t = min_evidence_t();
        let min_folds = min_evidence_folds();
        if ev.folds < min_folds {
            return Verdict::Refuse {
                reason: format!("{} fold(s), need {}", ev.folds, min_folds),
            };
        }
        let t = if ev.se_bps <= 0.0 { 0.0 } else { ev.net_bps / ev.se_bps };
        if t < min_t {
            return Verdict::Refuse {
                reason: format!("t = {:.2} below {:.1} floor", t, min_t),
            };
        }
        Verdict::Admit
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use quant_signal::BookEvidence;

    #[test]
    fn refuses_book_below_t_floor() {
        let ev = BookEvidence { net_bps: 3.477, n: 84, se_bps: 7.0, folds: 3, positive_folds: 2 };
        // t = 3.477 / 7.0 = 0.497 < 2.0
        assert!(matches!(EvidenceGate::decide(&ev), Verdict::Refuse { .. }));
    }

    #[test]
    fn admits_book_above_t_floor() {
        let ev = BookEvidence { net_bps: 9.945, n: 84, se_bps: 3.0, folds: 3, positive_folds: 2 };
        // t = 3.315 > 2.0
        assert!(matches!(EvidenceGate::decide(&ev), Verdict::Admit));
    }

    #[test]
    fn refuses_single_fold() {
        let ev = BookEvidence { net_bps: 9.945, n: 84, se_bps: 3.0, folds: 1, positive_folds: 1 };
        assert!(matches!(EvidenceGate::decide(&ev), Verdict::Refuse { .. }));
    }

    #[test]
    fn default_values_are_compiled_in() {
        // Ohne Umgebungsvariablen gilt die kompilierte Vorgabe.
        assert_eq!(min_evidence_t(), 2.0);
        assert_eq!(min_evidence_folds(), 2);
    }

    #[test]
    fn admits_book_at_exact_floor() {
        // t = 2.0 genau an der Grenze -> Admit (>=, nicht >).
        let ev = BookEvidence { net_bps: 6.0, n: 84, se_bps: 3.0, folds: 2, positive_folds: 2 };
        assert!(matches!(EvidenceGate::decide(&ev), Verdict::Admit));
    }
}
