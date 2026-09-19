//! Cross-Section-Panel mit Fingerprint und Perioden-Bedarf.

use sha2::{Digest, Sha256};

/// Ein Cross-Section-Panel: Assets mit zwei Matrizen (z. B. Renditen und
/// Volatilitaeten). Der Fingerprint macht Drift attribuierbar.
pub struct CrossPanel {
    pub assets: Vec<String>,
    pub matrix_a: Vec<f64>,
    pub matrix_b: Vec<f64>,
}

impl CrossPanel {
    pub fn new(assets: Vec<String>, matrix_a: Vec<f64>, matrix_b: Vec<f64>) -> Self {
        Self {
            assets,
            matrix_a,
            matrix_b,
        }
    }

    /// SHA-256 ueber die serialisierten Felder — aendert sich das Panel,
    /// aendert sich der Fingerprint.
    pub fn fingerprint(&self) -> String {
        let mut hasher = Sha256::new();
        for a in &self.assets {
            hasher.update(a.as_bytes());
            hasher.update(b"\x00");
        }
        for v in &self.matrix_a {
            hasher.update(v.to_le_bytes());
        }
        for v in &self.matrix_b {
            hasher.update(v.to_le_bytes());
        }
        format!("{:x}", hasher.finalize())
    }
}

/// Wie viele Perioden braucht ein Effekt, um signifikant zu werden?
/// `None` bei falsch gerichtetem Effekt (negativ kann durch Warten nicht
/// signifikant werden).
pub fn required_periods(effekt: f64, se: f64) -> Option<u64> {
    if effekt <= 0.0 || se <= 0.0 {
        return None;
    }
    // t = effekt / (se / sqrt(n)) >= 2.0  =>  n >= (2.0 * se / effekt)^2
    let n = (2.0 * se / effekt).powi(2);
    Some(n.ceil() as u64)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fingerprint_changes_with_panel() {
        let a = CrossPanel::new(vec!["A".into()], vec![1.0], vec![2.0]);
        let b = CrossPanel::new(vec!["A".into()], vec![1.0], vec![3.0]);
        assert_ne!(a.fingerprint(), b.fingerprint());
    }

    #[test]
    fn required_periods_none_for_wrong_direction() {
        // negativer Effekt kann durch Warten nicht signifikant werden
        assert!(required_periods(-0.5, 0.1).is_none());
    }

    #[test]
    fn required_periods_some_for_positive_effect() {
        // positiver Effekt braucht endlich viele Perioden
        assert!(required_periods(0.5, 0.1).is_some());
    }
}
