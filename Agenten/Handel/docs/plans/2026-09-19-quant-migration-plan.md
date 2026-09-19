# Rust-Migration des Handels-Stacks — Implementierungsplan

**Ziel:** Die fehlenden Bausteine der Rust-Migration bauen: Ebenen-Grenze
(`quant-planes`), `EvidenceGate`/`Verdict`-Interface, `quant-alpha`-Erweiterung
(Fingerprint/required_periods), Risiko-/Sizing-Logik (`omnitrade-risk`), und
den Plan-Doc auf den Ist-Stand korrigieren.

**Architektur:** Zwei Ebenen in einem Cargo-Workspace, ohne geteilte
Abhaengigkeit. Die Alpha-Ebene (Modell/Urteil) schreibt eine `RankedBook`-JSON
mit Zielgewichten (Summe 0) plus `BookEvidence`. Die Execution-Ebene (Engine)
liest diese Datei, bildet ihre eigene t-Statistik und wendet ihren eigenen
Boden an. Die Grenze ist eine Eigenschaft des Artefakts: `quant-planes`
prueft transitiv ueber `Cargo.lock`, dass `quant-alpha` kein `nautilus-*`- und
`quant-strategy` kein `candle-*`-Crate im Graphen hat.

**Tech-Stack:** Rust 1.98 (vorhanden), Cargo-Workspace
`Agenten/Handel/nautilus-rust` (vorhanden, 3 Crates). Nautilus-Rust-Crates
0.64.0 fuer die Execution-Ebene, `candle-core`/`candle-nn` 0.11.0 fuer die
Alpha-Ebene. `serde`/`serde_json` fuer das Schema.

## Projektweite Anforderungen (gelten fuer jede Aufgabe)

- **Zwei Ebenen, linker-erzwungen:** `quant-alpha` haengt von KEINEM
  `nautilus-*`-Crate ab; `quant-strategy` haengt von KEINEM `candle-*`-Crate
  ab. Ein Verstoss ist ein Build-Fehler, kein Review-Kommentar.
- **Ehrlichkeit statt Assertion:** Kennzahlen aus dem Panel ableiten, nie als
  Literale. `required_periods()` gibt `None` bei falsch gerichtetem Effekt
  zurueck. `CrossPanel::fingerprint()` (SHA-256) macht Drift attribuierbar.
- **Kein Live-Handel:** Alles Papier/Backtest. `--live` wird verweigert.
- **Bedingung 4 bleibt:** Journal und Zustand werden nach jedem Zyklus nach
  `Q:\Handel_Journal\<spur>` gespiegelt.
- **Tests schreiben nie in echte Spurenordner** (Tempdateien + Modulwaechter).
- **Deutsche Bezeichner und Meldungen** wie im Haus.
- **Keine Credentials:** `test_credentials.py` und `run_okx_paper_node.py`
  enthalten Zugangsdaten — Werte nie uebernehmen, nie ausgeben, nie committen.
- **Ziel-Ort:** `Agenten/Handel/nautilus-rust` im BrainFiles-Repo (master).
  `omnitrade-risk` wird hier im Workspace angelegt (nicht im
  `Werkstatt/omnitrade`-Fork — vermeidet die shallow-Fork-Push-Falle).

## Dateistruktur

| Datei | Verantwortung |
|---|---|
| `nautilus-rust/quant-planes/` (neu) | Ebenen-Grenze transitiv ueber `Cargo.lock` pruefen |
| `nautilus-rust/quant-strategy/src/evidence.rs` (neu) | `EvidenceGate`/`Verdict`-Interface |
| `nautilus-rust/quant-strategy/src/lib.rs` (neu) | `evidence`-Modul exportieren |
| `nautilus-rust/quant-alpha/src/cross_panel.rs` (neu) | `CrossPanel`, `fingerprint()`, `required_periods()` |
| `nautilus-rust/quant-alpha/src/lib.rs` (neu) | `cross_panel`-Modul exportieren |
| `nautilus-rust/omnitrade-risk/` (neu) | Risiko-/Sizing-Logik (Position Limits, Drawdown, Kill-Switch) |
| `nautilus-rust/Cargo.toml` (aendern) | members um `quant-planes`, `omnitrade-risk` erweitern |
| `docs/plans/2026-09-19-python-zu-rust-migration.md` (aendern) | Ziel-Ort + Ist-Stand korrigieren |

---

### Aufgabe 1: `quant-planes` — die Ebenen-Grenze

**Dateien:**
- Neu: `nautilus-rust/quant-planes/Cargo.toml`
- Neu: `nautilus-rust/quant-planes/src/main.rs`
- Aendern: `nautilus-rust/Cargo.toml` (members)

**Interfaces:**
- Konsumiert: `Cargo.lock` (serde_json) — kein `quant-signal`-Import noetig,
  die Workspace-Mitgliedsliste kommt aus dem Lockfile.
- Produziert: CLI `quant-planes` — Exit 0 = sauber, Exit 1 = Verstoss.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**
  ```rust
  // quant-planes/src/main.rs
  #[cfg(test)]
  mod tests {
      use super::*;

      #[test]
      fn alpha_plane_has_no_nautilus() {
          let deps = alpha_deps();
          assert!(!deps.iter().any(|d| d.starts_with("nautilus-")),
              "quant-alpha darf kein nautilus-*-Crate haben, hatte: {:?}",
              deps.iter().filter(|d| d.starts_with("nautilus-")).collect::<Vec<_>>());
      }

      #[test]
      fn strategy_plane_has_no_candle() {
          let deps = strategy_deps();
          assert!(!deps.iter().any(|d| d.starts_with("candle-")),
              "quant-strategy darf kein candle-*-Crate haben, hatte: {:?}",
              deps.iter().filter(|d| d.starts_with("candle-")).collect::<Vec<_>>());
      }
  }
  ```
- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cargo test -p quant-planes` — Erwartet: FAIL (Crate existiert noch nicht).
- [ ] **Schritt 3: Minimale Implementierung**
  ```rust
  // quant-planes/Cargo.toml
  [package]
  name = "quant-planes"
  version.workspace = true
  edition.workspace = true
  license.workspace = true

  [dependencies]
  serde = { version = "1", features = ["derive"] }
  serde_json = "1"
  ```
  ```rust
  // quant-planes/src/main.rs
  use serde::Deserialize;
  use std::collections::{HashMap, HashSet};
  use std::path::Path;

  #[derive(Deserialize)]
  struct LockPackage {
      name: String,
      dependencies: Vec<String>,
  }

  #[derive(Deserialize)]
  struct LockFile {
      package: Vec<LockPackage>,
  }

  /// Baut die transitive Abhaengigkeitsmenge einer Crate aus Cargo.lock.
  fn transitive_deps(lock: &LockFile, root: &str) -> HashSet<String> {
      let mut by_name: HashMap<&str, &LockPackage> = HashMap::new();
      for p in &lock.package {
          by_name.insert(p.name.as_str(), p);
      }
      let mut seen = HashSet::new();
      let mut stack = vec![root.to_string()];
      while let Some(name) = stack.pop() {
          if !seen.insert(name.clone()) {
              continue;
          }
          if let Some(p) = by_name.get(name.as_str()) {
              for d in &p.dependencies {
                  stack.push(d.clone());
              }
          }
      }
      seen
  }

  fn alpha_deps() -> HashSet<String> {
      let lock = read_lock();
      transitive_deps(&lock, "quant-alpha")
  }

  fn strategy_deps() -> HashSet<String> {
      let lock = read_lock();
      transitive_deps(&lock, "quant-strategy")
  }

  fn read_lock() -> LockFile {
      let raw = std::fs::read_to_string("Cargo.lock").expect("Cargo.lock lesen");
      serde_json::from_str(&raw).expect("Cargo.lock parsen")
  }

  fn main() {
      let lock = read_lock();
      let alpha = transitive_deps(&lock, "quant-alpha");
      let strategy = transitive_deps(&lock, "quant-strategy");

      let mut violations = Vec::new();
      for d in &alpha {
          if d.starts_with("nautilus-") {
              violations.push(format!("quant-alpha -> {}", d));
          }
      }
      for d in &strategy {
          if d.starts_with("candle-") {
              violations.push(format!("quant-strategy -> {}", d));
          }
      }

      if violations.is_empty() {
          println!("quant-planes: 0 violations (Ebenen-Grenze sauber)");
          std::process::exit(0);
      } else {
          for v in &violations {
              eprintln!("quant-planes: VERSTOSS {}", v);
          }
          std::process::exit(1);
      }
  }
  ```
  **Hinweis:** `Cargo.lock` ist JSON (nicht TOML) — serde_json parst es direkt.
  Der Test liest dieselbe `Cargo.lock`-Datei wie die CLI (relativ zum
  Workspace-Root, wo `cargo test` laeuft).
- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cargo test -p quant-planes` — Erwartet: PASS.
- [ ] **Schritt 5: Committen**
  `git add Agenten/Handel/nautilus-rust/quant-planes Agenten/Handel/nautilus-rust/Cargo.toml Agenten/Handel/nautilus-rust/Cargo.lock && git commit -m "quant-planes: Ebenen-Grenze transitiv ueber Cargo.lock"`

---

### Aufgabe 2: `EvidenceGate`/`Verdict` in `quant-strategy`

**Dateien:**
- Neu: `nautilus-rust/quant-strategy/src/evidence.rs`
- Neu: `nautilus-rust/quant-strategy/src/lib.rs`
- Aendern: `nautilus-rust/quant-strategy/src/main.rs` (auf das Modul umstellen)

**Interfaces:**
- Konsumiert: `quant_signal::BookEvidence` (aus Aufgabe 1 des Ist-Stands).
- Produziert: `EvidenceGate::decide(&BookEvidence) -> Verdict` mit
  `Verdict::{Admit, Refuse { reason: String }}`. Konstanten
  `MIN_EVIDENCE_T = 2.0`, `MIN_EVIDENCE_FOLDS = 2` als Modul-Konstanten.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**
  ```rust
  // quant-strategy/src/evidence.rs
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
  }
  ```
- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cargo test -p quant-strategy` — Erwartet: FAIL (evidence.rs existiert nicht).
- [ ] **Schritt 3: Minimale Implementierung**
  ```rust
  // quant-strategy/src/evidence.rs
  use quant_signal::BookEvidence;

  /// Die Evidenz-Huerde. Kompiliert, nicht konfigurierbar.
  pub const MIN_EVIDENCE_T: f64 = 2.0;
  /// Mindestens zwei Folds, um Skill von Regime zu trennen.
  pub const MIN_EVIDENCE_FOLDS: usize = 2;

  /// Urteil der Engine ueber ein Buch.
  pub enum Verdict {
      Admit,
      Refuse { reason: String },
  }

  /// Das Evidence-Gate: entscheidet, ob ein Buch demonstrierte Faehigkeit hat.
  pub struct EvidenceGate;

  impl EvidenceGate {
      pub fn decide(ev: &BookEvidence) -> Verdict {
          if ev.folds < MIN_EVIDENCE_FOLDS {
              return Verdict::Refuse {
                  reason: format!("{} fold(s), need {}", ev.folds, MIN_EVIDENCE_FOLDS),
              };
          }
          let t = if ev.se_bps <= 0.0 { 0.0 } else { ev.net_bps / ev.se_bps };
          if t < MIN_EVIDENCE_T {
              return Verdict::Refuse {
                  reason: format!("t = {:.2} below {:.1} floor", t, MIN_EVIDENCE_T),
              };
          }
          Verdict::Admit
      }
  }
  ```
  ```rust
  // quant-strategy/src/lib.rs
  pub mod evidence;
  ```
  Dann `main.rs` umstellen: die lokalen `t_stat`/`has_demonstrated_skill`/
  `MIN_EVIDENCE_T`/`MIN_EVIDENCE_FOLDS` durch `evidence::EvidenceGate::decide`
  ersetzen. Der `t_stat`-Aufruf fuer die Ausgabe bleibt (oder wird aus
  `decide` abgeleitet); die Huerden-Konstanten kommen aus `evidence`.
- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cargo test -p quant-strategy` — Erwartet: PASS (7 alte + 3 neue).
- [ ] **Schritt 5: Committen**
  `git add Agenten/Handel/nautilus-rust/quant-strategy && git commit -m "quant-strategy: EvidenceGate/Verdict-Interface (t-Floor, Fold-Minimum)"`

---

### Aufgabe 3: `quant-alpha` — `CrossPanel`, `fingerprint()`, `required_periods()`

**Dateien:**
- Neu: `nautilus-rust/quant-alpha/src/cross_panel.rs`
- Neu: `nautilus-rust/quant-alpha/src/lib.rs`
- Aendern: `nautilus-rust/quant-alpha/src/main.rs` (Modul einbinden)

**Interfaces:**
- Konsumiert: nichts Neues (nur stdlib + `sha2` fuer SHA-256).
- Produziert: `CrossPanel::new(assets, matrix_a, matrix_b)`,
  `CrossPanel::fingerprint() -> String` (SHA-256 ueber serialisierte Felder),
  `required_periods(effekt: f64, se: f64) -> Option<u64>`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**
  ```rust
  // quant-alpha/src/cross_panel.rs
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
  ```
- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cargo test -p quant-alpha` — Erwartet: FAIL (cross_panel.rs existiert nicht).
- [ ] **Schritt 3: Minimale Implementierung**
  ```rust
  // quant-alpha/Cargo.toml — sha2 hinzufuegen
  // [dependencies]
  // sha2 = "0.10"
  ```
  ```rust
  // quant-alpha/src/cross_panel.rs
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
          Self { assets, matrix_a, matrix_b }
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
  ```
  ```rust
  // quant-alpha/src/lib.rs
  pub mod cross_panel;
  ```
  `main.rs` einbinden: `use quant_alpha::cross_panel::{CrossPanel, required_periods};`
  (oder `mod cross_panel;` je nach Struktur). Der bestehende
  `fit_and_write_book` bleibt unveraendert.
- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cargo test -p quant-alpha` — Erwartet: PASS (3 neue).
- [ ] **Schritt 5: Committen**
  `git add Agenten/Handel/nautilus-rust/quant-alpha && git commit -m "quant-alpha: CrossPanel-Fingerprint + required_periods"`

---

### Aufgabe 4: `omnitrade-risk` — Sizing/Drawdown/Kill-Switch

**Dateien:**
- Neu: `nautilus-rust/omnitrade-risk/Cargo.toml`
- Neu: `nautilus-rust/omnitrade-risk/src/lib.rs`
- Aendern: `nautilus-rust/Cargo.toml` (members)

**Interfaces:**
- Konsumiert: `quant_strategy::evidence::Verdict` (aus Aufgabe 2).
- Produziert: `RiskLimits::check(&OrderRequest) -> Result<(), RiskViolation>`,
  `RiskLimits::groessenfaktor(drawdown_halbierung_usd, drawdown) -> f64`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**
  ```rust
  // omnitrade-risk/src/lib.rs
  #[cfg(test)]
  mod tests {
      use super::*;

      #[test]
      fn rejects_order_over_max_units() {
          let limits = RiskLimits { max_units_per_name: 3, ..Default::default() };
          let req = OrderRequest { units: 4, ..Default::default() };
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
          let limits = RiskLimits { max_units_per_name: 3, ..Default::default() };
          let req = OrderRequest { units: 2, ..Default::default() };
          assert!(limits.check(&req).is_ok());
      }
  }
  ```
- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cargo test -p omnitrade-risk` — Erwartet: FAIL (Crate existiert nicht).
- [ ] **Schritt 3: Minimale Implementierung**
  ```rust
  // omnitrade-risk/Cargo.toml
  [package]
  name = "omnitrade-risk"
  version.workspace = true
  edition.workspace = true
  license.workspace = true

  [dependencies]
  quant-strategy = { path = "../quant-strategy" }
  ```
  ```rust
  // omnitrade-risk/src/lib.rs
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
  ```
  **Hinweis:** `Verdict` wird hier nur als Kill-Switch-Signal konsumiert —
  die eigentliche Evidenz-Entscheidung bleibt in `quant-strategy`. Die
  `wachen.json`-Werte (Risiko je Position, max. Positionen, Buchrisiko,
  Drawdown-Schwelle) werden als `RiskLimits`-Felder uebernommen; die
  konkrete JSON-Einbindung ist ein Folge-Schritt, hier reicht die
  Struktur + Tests.
- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cargo test -p omnitrade-risk` — Erwartet: PASS (3 neue).
- [ ] **Schritt 5: Committen**
  `git add Agenten/Handel/nautilus-rust/omnitrade-risk Agenten/Handel/nautilus-rust/Cargo.toml Agenten/Handel/nautilus-rust/Cargo.lock && git commit -m "omnitrade-risk: Sizing/Drawdown/Kill-Switch (Verdict-Konsum)"`

---

### Aufgabe 5: Plan-Doc korrigieren

**Dateien:**
- Aendern: `docs/plans/2026-09-19-python-zu-rust-migration.md`

**Interfaces:**
- Konsumiert: nichts (reine Doku).
- Produziert: korrigierter Plan, der den Ist-Stand und den Ziel-Ort
  `nautilus-rust` widerspiegelt.

- [ ] **Schritt 1: Ziel-Ort reparieren**
  Alle Vorkommen von `Werkstatt/omnitrade` (als Ziel der quant-Crates) auf
  `Agenten/Handel/nautilus-rust` aendern. Die Dateistruktur-Tabelle und die
  Migrations-Reihenfolge entsprechend anpassen.
- [ ] **Schritt 2: Ist-Stand anerkennen**
  Aufgabe 1 (quant-signal): das reale Schema (`RankedWeight{instrument_id}`,
  `is_dollar_neutral(tol)`) als gueltig markieren, nicht `TargetWeight`/
  `targets_sum_to_zero` fordern.
- [ ] **Schritt 3: Checkboxen setzen**
  Die erledigten Aufgaben (1, 3, 4-Kern) als abgehakt markieren; die neuen
  Deltas (quant-planes, EvidenceGate, alpha-Erweiterung, omnitrade-risk) als
  offen eintragen.
- [ ] **Schritt 4: Diff pruefen**
  `git diff docs/plans/2026-09-19-python-zu-rust-migration.md` — nur die
  gewollten Aenderungen, keine Ganzdatei-Rewrite (LF/CRLF beachten).
- [ ] **Schritt 5: Committen**
  `git add docs/plans/2026-09-19-python-zu-rust-migration.md && git commit -m "docs(handel): Migrationsplan auf Ist-Stand/Ziel nautilus-rust korrigiert"`

---

## Self-Review

**Spezifikations-Abdeckung:**
- quant-planes (Ebenen-Grenze): Aufgabe 1.
- EvidenceGate/Verdict in quant-strategy: Aufgabe 2.
- quant-alpha fingerprint/required_periods: Aufgabe 3.
- omnitrade-risk (Sizing/Drawdown/Kill-Switch): Aufgabe 4.
- Plan-Doc-Korrektur: Aufgabe 5.
- Ziel-Ort `nautilus-rust`: projektweite Anforderung + Aufgabe 5.

**Platzhalter-Scan:** Keine TBD/TODO. Jede Aufgabe hat echten Testcode und
echte Implementierung. `CrossPanel` wird in Aufgabe 3 definiert und dort
verwendet. `Verdict` wird in Aufgabe 2 definiert und von Aufgabe 4 konsumiert.

**Typ-Konsistenz:** `BookEvidence` (Ist-Stand quant-signal) wird von Aufgabe 2
konsumiert — Feldnamen `net_bps`, `n`, `se_bps`, `folds`, `positive_folds`
stimmen mit dem Ist-Code ueberein. `Verdict::{Admit, Refuse{reason}}` (Aufgabe 2)
wird von Aufgabe 4 (`kill_switch`) konsumiert. `RiskLimits`/`OrderRequest`
(Aufgabe 4) sind in sich konsistent.

**Offene Punkte (Entscheidung Max):**
1. **`omnitrade-risk` im nautilus-rust-Workspace** (statt Fork) — hier
   entschieden, vermeidet die shallow-Fork-Push-Falle.
2. **`wachen.json`-Einbindung** in `omnitrade-risk` ist ein Folge-Schritt
   (Struktur + Tests zuerst); die konkrete JSON-Parsing-Einbindung folgt,
   wenn die Crate an eine echte Spur angeschlossen wird.

## Uebergabe

Nach dem Speichern dem Nutzer die Auswahl anbieten:
1. **Delegierte Ausfuehrung (empfohlen):** pro Aufgabe ein frischer Subagent
   (delegate_task), Review zwischen den Aufgaben, schnelle Iteration.
2. **Inline-Ausfuehrung:** Aufgaben in der Session mit dem Skill
   executing-plans abarbeiten, Batch-Checkpoints zum Review.

Adaptiert aus obra/superpowers (Fork mfaupel95/superpowers), 16.09.2026.
Architekturprinzipien aus https://vadim.blog/nautilustrader-candle-rust-ai-trading-stack/
(„the model proposes, the engine disposes, and the boundary is enforced by the
linker rather than by policy").
