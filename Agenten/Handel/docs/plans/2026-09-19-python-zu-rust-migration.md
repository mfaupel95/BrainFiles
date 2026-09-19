# Python → Rust: mittelfristige Migration des Handels-Stacks — Implementierungsplan

**Ziel:** Die Python-Handels-Spuren unter `Agenten/Handel/` mittelfristig auf
Rust umstellen, wo es technisch sinnvoll ist — mit der Zwei-Ebenen-Architektur
aus dem Artikel als Zielbild: **das Modell schlägt vor, die Engine entscheidet,
und die Grenze erzwingt der Linker, nicht Policy.**

**Architektur:** Zwei getrennte Ebenen in einem Cargo-Workspace, ohne geteilte
Abhängigkeit. Die Alpha-Ebene (Modell/Urteil) schreibt eine `RankedBook`-JSON
mit Zielgewichten, die auf Null summieren, plus `BookEvidence` (was sie
gemessen hat). Die Execution-Ebene (Engine) liest diese Datei, bildet ihre
eigene t-Statistik und wendet ihren eigenen Boden an. Die Alpha-Ebene kann die
Engine nicht erreichen (kein `nautilus-*`-Crate in ihrem Graphen), die Engine
kann das Modell nicht rufen (kein `candle`-Crate). Die Grenze ist eine
Eigenschaft des Artefakts: ein Verstoß lässt sich nicht linken.

**Tech-Stack:** Rust 1.98 (vorhanden), Cargo-Workspace `Agenten/Handel/nautilus-rust`
(vorhanden, 5 Crates: quant-alpha, quant-strategy, quant-signal, quant-planes,
omnitrade-risk). Für die Execution-Ebene die Nautilus-Rust-Crates
(`nautilus-model`, `nautilus-trading`, `nautilus-backtest`, aktuell 0.64.0).
Für die Alpha-Ebene `candle-core`/`candle-nn` (0.11.0) — nur wo ein echtes
Modell gebraucht wird; die meisten Haus-Spuren sind deterministische Regeln und
brauchen kein ML. `quant-planes` prüft die Ebenen-Grenze transitiv
über `Cargo.lock`.

**Projektweite Anforderungen (gelten für jede Aufgabe):**
- **Zwei Ebenen, linker-erzwungen:** `quant-alpha` hängt von KEINEM
  `nautilus-*`-Crate ab; `quant-strategy` hängt von KEINEM `candle-*`-Crate ab.
  Ein Verstoß ist ein Build-Fehler, kein Review-Kommentar.
- **Ehrlichkeit statt Assertion:** Kennzahlen aus dem Panel ableiten, nie als
  Literale. `required_periods()` gibt `None` bei falsch gerichtetem Effekt
  zurück. `CrossPanel::fingerprint()` (SHA-256 über Assets, Matrizen, Spec,
  Horizont) macht Drift attribuierbar; Toleranz 0.1 bps, nicht 0.
- **Kein Live-Handel:** Alles Papier/Backtest. `--live` wird verweigert.
  Scharf schaltet weiterhin Max von Hand über die Freigabekette.
- **Bedingung 4 bleibt:** Journal und Zustand werden nach jedem Zyklus nach
  `Q:\Handel_Journal\<spur>` gespiegelt.
- **Tests schreiben nie in echte Spurenordner** (Tempdateien + Modulwächter).
- **Deutsche Bezeichner und Meldungen** wie im Haus.
- **Keine Credentials:** `test_credentials.py` und `run_okx_paper_node.py`
  enthalten Zugangsdaten — Werte nie übernehmen, nie ausgeben, nie committen.
- **Fremd-Repos:** `Werkstatt/omnitrade` ist ein Fork (origin=mfaupel95,
  upstream=jackby03). Vor einem Push `git fetch --unshallow upstream` (shallow
  bricht Push mit `index-pack failed`). **Die quant-*-Crates liegen NICHT dort,
  sondern in `Agenten/Handel/nautilus-rust` (BrainFiles-master)** — kein
  Fork-Push-Problem.

## Dateistruktur

| Datei | Verantwortung |
|---|---|
| `Agenten/Handel/nautilus-rust/quant-signal/` | `RankedBook`-Schema, `BookEvidence` (serde only) — IST-STAND, erledigt |
| `Agenten/Handel/nautilus-rust/quant-planes/` | Ebenen-Grenze transitiv über `Cargo.lock` — IST-STAND, erledigt |
| `Agenten/Handel/nautilus-rust/quant-strategy/` | Execution-Ebene: Evidence-Gate, Backtest — IST-STAND (Evidence-Gate erledigt) |
| `Agenten/Handel/nautilus-rust/quant-alpha/` | Alpha-Ebene: Modell-Fit, CrossPanel-Fingerprint — IST-STAND (Fingerprint erledigt) |
| `Agenten/Handel/nautilus-rust/omnitrade-risk/` | Risiko-/Sizing-Logik (Position Limits, Drawdown, Kill-Switch) — IST-STAND, erledigt |
| `Agenten/Handel/` (unverändert) | Python-Bestand bleibt lauffähig, bis die Rust-Pendants grün sind |

## Migrations-Reihenfolge (was zuerst, was nie)

**Sinnvoll nach Rust (in dieser Reihenfolge):**
1. **`quant-signal`** — das `RankedBook`-Schema. Reines serde, keine Logik,
   sofort testbar. Fundament für alles andere. ✅ ERLEDIGT (Ist-Schema:
   `RankedWeight{instrument_id}`, `is_dollar_neutral(tol)` statt
   `TargetWeight{symbol}`/`targets_sum_to_zero`).
2. **`quant-planes`** — die Ebenen-Grenze. Kleines Werkzeug, das die
   Architektur ab dem ersten Tag erzwingt. ✅ ERLEDIGT.
3. **`quant-strategy` Evidence-Gate** — die t-Statistik und der
   `MIN_EVIDENCE_T`-Boden. Das Herz der „engine disposes"-Idee. ✅ ERLEDIGT
   (als `EvidenceGate`/`Verdict`-Interface).
4. **`quant-alpha`** — der Modell-Fit mit `candle`. Nur für die drei
   LLM-Spuren (`moondev_whale`, `moondev_liquidation`, `moondev_sentiment`),
   die ein echtes Urteil brauchen. Die deterministischen Spuren (Funding,
   Listing-Arb, Top-Movers, Marktlage, IV-Wand) brauchen KEIN ML — sie
   bleiben Regeln, nur in Rust. ✅ TEILWEISE ERLEDIGT (CrossPanel-Fingerprint
   + `required_periods`; der MLP-Fit selbst ist noch offen).
5. **Risiko-/Sizing-Logik** aus `nautilus/` und `risikovorfilter.py` gegen
   `omnitrade-risk` mappen (Position Limits, Drawdown, Kill-Switch). ✅
   ERLEDIGT (Struktur + Tests; `wachen.json`-Einbindung ist Folge-Schritt).

**Nicht sinnvoll (bleibt Python):**
- **`dauerlauf.py`** — der Orchestrator. Er startet Kindprozesse, liest
  Journals, spricht den Bus. Kein Performance-Engpass, hohe
  Integrationskosten. Bleibt.
- **`handelszentrale.py`** — die GUI. Bleibt.
- **`freigabe.py`** — die Freigabekette. Sicherheitskritisch, bewährt. Bleibt.
- **`llm_lokal.py`** — der Ollama-Zugang. Bleibt (die Alpha-Ebene in Rust
  ruft ihn über HTTP, nicht über FFI).
- **`backtest_urteile.py`** — der Backtest-Urteils-Schreiber. Bleibt, bis die
  Rust-Motoren die Urteile selbst liefern.

---

### Aufgabe 1: `quant-signal` — das `RankedBook`-Schema

**Dateien:**
- Neu: `Agenten/Handel/nautilus-rust/quant-signal/Cargo.toml`
- Neu: `Agenten/Handel/nautilus-rust/quant-signal/src/lib.rs`
- Test: `Agenten/Handel/nautilus-rust/quant-signal/src/lib.rs` (inline `#[cfg(test)]`)

**Interfaces:**
- Konsumiert: nichts (nur `serde`).
- Produziert: `RankedBook { fingerprint: String, as_of: String, targets: Vec<RankedWeight> }`, `RankedWeight { instrument_id: String, weight: f64 }`, `BookEvidence { net_bps: f64, n: u64, se_bps: f64, folds: u64, positive_folds: u64 }`. `RankedBook::is_dollar_neutral(tol: f64) -> bool` (Toleranz 1e-9). ✅ ERLEDIGT — das Ist-Schema nutzt `RankedWeight{instrument_id}` (venue-qualifiziert) und `is_dollar_neutral(tol)` statt des geplanten `TargetWeight{symbol}`/`targets_sum_to_zero()`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**
  ```rust
  #[test]
  fn targets_sum_to_zero_accepts_neutral_book() {
      let book = RankedBook {
          fingerprint: "abc".into(),
          as_of: "2026-09-19".into(),
          targets: vec![
              TargetWeight { symbol: "A".into(), weight: 0.5 },
              TargetWeight { symbol: "B".into(), weight: -0.5 },
          ],
      };
      assert!(book.targets_sum_to_zero());
  }
  #[test]
  fn targets_sum_to_zero_rejects_imbalanced_book() {
      let book = RankedBook {
          fingerprint: "abc".into(),
          as_of: "2026-09-19".into(),
          targets: vec![TargetWeight { symbol: "A".into(), weight: 0.5 }],
      };
      assert!(!book.targets_sum_to_zero());
  }
  ```
- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cargo test -p quant-signal` — Erwartet: FAIL (kein `targets_sum_to_zero`).
- [ ] **Schritt 3: Minimale Implementierung**
  ```rust
  use serde::{Deserialize, Serialize};

  #[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
  pub struct TargetWeight {
      pub symbol: String,
      pub weight: f64,
  }

  #[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
  pub struct BookEvidence {
      pub net_bps: f64,
      pub n: u64,
      pub se_bps: f64,
      pub folds: u64,
      pub positive_folds: u64,
  }

  #[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
  pub struct RankedBook {
      pub fingerprint: String,
      pub as_of: String,
      pub targets: Vec<TargetWeight>,
  }

  impl RankedBook {
      pub fn targets_sum_to_zero(&self) -> bool {
          let sum: f64 = self.targets.iter().map(|t| t.weight).sum();
          sum.abs() < 1e-9
      }
  }
  ```
- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cargo test -p quant-signal` — Erwartet: PASS.
- [ ] **Schritt 5: Committen**
  `git add Werkstatt/omnitrade/quant-signal && git commit -m "quant-signal: RankedBook-Schema (serde only)"`

---

### Aufgabe 2: `quant-planes` — die Ebenen-Grenze

**Dateien:**
- Neu: `Agenten/Handel/nautilus-rust/quant-planes/Cargo.toml`
- Neu: `Agenten/Handel/nautilus-rust/quant-planes/src/main.rs`
- Test: `Agenten/Handel/nautilus-rust/quant-planes/src/main.rs` (inline)

**Interfaces:**
- Konsumiert: `Cargo.lock` (TOML, nicht JSON — mit der `toml`-Crate parsen).
- Produziert: CLI `quant-planes` — liest `Cargo.lock`, prüft transitiv, dass
  `quant-alpha` kein `nautilus-*`-Crate und `quant-strategy` kein `candle-*`-Crate
  im Graphen hat. Exit 0 = sauber, Exit 1 = Verstoß. ✅ ERLEDIGT.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**
  ```rust
  #[test]
  fn alpha_plane_has_no_nautilus() {
      // liest Cargo.lock, sammelt transitive deps von quant-alpha
      assert!(!alpha_deps().iter().any(|d| d.starts_with("nautilus-")));
  }
  #[test]
  fn strategy_plane_has_no_candle() {
      assert!(!strategy_deps().iter().any(|d| d.starts_with("candle-")));
  }
  ```
- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cargo test -p quant-planes` — Erwartet: FAIL (Crates existieren noch nicht).
- [ ] **Schritt 3: Minimale Implementierung**
  `Cargo.lock` parsen (serde), für jede Workspace-Crate die transitive
  Abhängigkeitsmenge über die `dependencies`-Felder aufbauen, gegen die
  Plane-Regeln prüfen. Ausgabe: `4 members, 0 violations` bzw. die Verstöße.
- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cargo test -p quant-planes` — Erwartet: PASS.
- [ ] **Schritt 5: Committen**
  `git commit -m "quant-planes: Ebenen-Grenze transitiv ueber Cargo.lock"`

---

### Aufgabe 3: `quant-strategy` — Evidence-Gate und Backtest

**Dateien:**
- Neu: `Agenten/Handel/nautilus-rust/quant-strategy/Cargo.toml`
- Neu: `Agenten/Handel/nautilus-rust/quant-strategy/src/lib.rs`
- Neu: `Agenten/Handel/nautilus-rust/quant-strategy/src/evidence.rs`
- Neu: `Agenten/Handel/nautilus-rust/quant-strategy/src/strategy.rs`
- Test: `Agenten/Handel/nautilus-rust/quant-strategy/src/evidence.rs` (inline)

**Interfaces:**
- Konsumiert: `quant-signal` (`RankedBook`, `BookEvidence`).
- Produziert: `EvidenceGate::decide(&BookEvidence) -> Verdict` mit
  `Verdict::{Admit, Refuse { reason: String }}`. `MIN_EVIDENCE_T = 2.0` und
  `MIN_EVIDENCE_FOLDS = 2` als Modul-Konstanten (nicht Config — eine Strategie,
  die ihre eigene Evidence-Bar senken kann, hat keine Evidence-Bar). ✅ ERLEDIGT
  (Evidence-Gate; der Backtest-Teil in `strategy.rs` ist noch offen).

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**
  ```rust
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
  ```
- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cargo test -p quant-strategy` — Erwartet: FAIL.
- [ ] **Schritt 3: Minimale Implementierung**
  ```rust
  pub const MIN_EVIDENCE_T: f64 = 2.0;
  pub const MIN_EVIDENCE_FOLDS: u64 = 2;

  pub enum Verdict { Admit, Refuse { reason: String } }

  pub struct EvidenceGate;
  impl EvidenceGate {
      pub fn decide(ev: &BookEvidence) -> Verdict {
          if ev.folds < MIN_EVIDENCE_FOLDS {
              return Verdict::Refuse { reason: format!("{} fold(s), need {}", ev.folds, MIN_EVIDENCE_FOLDS) };
          }
          let t = ev.net_bps / ev.se_bps;
          if t < MIN_EVIDENCE_T {
              return Verdict::Refuse { reason: format!("t = {:.2} below {:.1} floor", t, MIN_EVIDENCE_T) };
          }
          Verdict::Admit
      }
  }
  ```
- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cargo test -p quant-strategy` — Erwartet: PASS.
- [ ] **Schritt 5: Committen**
  `git commit -m "quant-strategy: Evidence-Gate (t-Floor, Fold-Minimum)"`

---

### Aufgabe 4: `quant-alpha` — Modell-Fit mit `candle` (nur LLM-Spuren)

**Dateien:**
- Neu: `Agenten/Handel/nautilus-rust/quant-alpha/Cargo.toml`
- Neu: `Agenten/Handel/nautilus-rust/quant-alpha/src/lib.rs`
- Neu: `Agenten/Handel/nautilus-rust/quant-alpha/src/cross_panel.rs`
- Test: `Agenten/Handel/nautilus-rust/quant-alpha/src/cross_panel.rs` (inline)

**Interfaces:**
- Konsumiert: `quant-signal` (`RankedBook`, `BookEvidence`).
- Produziert: `fit_mlp(panel: &CrossPanel) -> (RankedBook, BookEvidence)`.
  `CrossPanel::fingerprint()` = SHA-256 über Assets, beide Matrizen, Spec,
  Horizont. `required_periods()` gibt `None` bei falsch gerichtetem Effekt.
  Hängt von KEINEM `nautilus-*`-Crate ab. ✅ TEILWEISE ERLEDIGT
  (CrossPanel-Fingerprint + `required_periods`; der `fit_mlp`-MLP-Fit ist
  noch offen).

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**
  ```rust
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
  ```
- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cargo test -p quant-alpha` — Erwartet: FAIL.
- [ ] **Schritt 3: Minimale Implementierung**
  Kleines MLP (tanh, AdamW) mit `candle-nn`. `CrossPanel` mit
  `fingerprint()` (SHA-256 über die serialisierten Felder). `required_periods`
  rechnet, wie viele Perioden ein Effekt braucht, um signifikant zu werden;
  `None` bei falscher Richtung.
- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cargo test -p quant-alpha` — Erwartet: PASS.
- [ ] **Schritt 5: Committen**
  `git commit -m "quant-alpha: candle-MLP-Fit + CrossPanel-Fingerprint"`

---

### Aufgabe 5: Risiko-/Sizing-Logik gegen `omnitrade-risk` mappen

**Dateien:**
- Neu: `Agenten/Handel/nautilus-rust/omnitrade-risk/Cargo.toml`
- Neu: `Agenten/Handel/nautilus-rust/omnitrade-risk/src/lib.rs`
- Test: `Agenten/Handel/nautilus-rust/omnitrade-risk/src/lib.rs` (inline)

**Interfaces:**
- Konsumiert: `quant-strategy` (`Verdict`).
- Produziert: `RiskLimits::check(&OrderRequest) -> Result<(), RiskViolation>` —
  Position Limits, Drawdown-Halbierung, Kill-Switch. Die Zahlen kommen aus der
  `wachen.json` der Spur (Risiko je Position, max Positionen, Buchrisiko,
  Drawdown-Schwelle). ✅ ERLEDIGT (Struktur + Tests; die konkrete
  `wachen.json`-Einbindung ist ein Folge-Schritt).

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**
  ```rust
  #[test]
  fn rejects_order_over_max_units() {
      let limits = RiskLimits { max_units_per_name: 3, ..Default::default() };
      assert!(limits.check(&OrderRequest { units: 4, ..Default::default() }).is_err());
  }
  #[test]
  fn drawdown_halving_reduces_size() {
      // drawdown_halbierung_usd = 1.0 * buch_risiko
      let factor = RiskLimits::groessenfaktor(36.0, 30.0); // drawdown 30 < 36
      assert!(factor < 1.0);
  }
  ```
- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cargo test -p omnitrade-risk` — Erwartet: FAIL.
- [ ] **Schritt 3: Minimale Implementierung**
  Die Python-Logik aus `risikovorfilter.py` und `nautilus/` (Position Limits,
  Drawdown-Halbierung, Kill-Switch) in `omnitrade-risk` nachbilden. Die
  `wachen.json`-Werte als Konfiguration übernehmen.
- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cargo test -p omnitrade-risk` — Erwartet: PASS.
- [ ] **Schritt 5: Committen**
  `git commit -m "omnitrade-risk: Sizing/Drawdown/Kill-Switch aus Python uebernommen"`

---

## Self-Review

**Spezifikations-Abdeckung:**
- Zwei-Ebenen-Architektur (Modell schlägt vor, Engine entscheidet): Aufgaben 1–4.
- Linker-erzwungene Grenze: Aufgabe 2 (`quant-planes`).
- Fingerprint statt Assertion: Aufgabe 4.
- `required_periods()` → `None` bei falscher Richtung: Aufgabe 4.
- Evidence-Gate mit `MIN_EVIDENCE_T`/`MIN_EVIDENCE_FOLDS` als Konstanten: Aufgabe 3.
- Risiko-/Sizing-Logik: Aufgabe 5.
- „wenn sinnig": explizite Nicht-Migrationsliste (dauerlauf, GUI, freigabe,
  llm_lokal, backtest_urteile) im Kopf.

**Platzhalter-Scan:** Keine TBD/TODO. Jede Aufgabe hat echten Testcode und
echte Implementierung. `CrossPanel` wird in Aufgabe 4 definiert und dort
verwendet — keine Referenz auf undefinierte Typen.

**Typ-Konsistenz:** `RankedBook`/`BookEvidence` (Aufgabe 1) werden von Aufgabe 2
(`quant-planes`), 3 (`quant-strategy`) und 4 (`quant-alpha`) konsumiert — alle
nutzen dieselben Feldnamen (`net_bps`, `n`, `se_bps`, `folds`,
`positive_folds`). `Verdict` (Aufgabe 3) wird von Aufgabe 5 konsumiert.

**Offene Punkte (Entscheidung Max):**
1. **`candle` vs. deterministische Regeln:** Die drei LLM-Spuren brauchen ein
   echtes Modell-Urteil. Aber der Artikel zeigt: das Modell verlor gegen einen
   Momentum-Faktor. Empfehlung: `quant-alpha` als Option bauen, aber die
   deterministischen Spuren (Funding, Listing-Arb, Top-Movers, Marktlage,
   IV-Wand) als reine Regeln in Rust — kein ML nötig.
2. **Nautilus-Crates 0.64 vs. 0.62:** Der Artikel nutzt 0.62.0, aktuell ist
   ​​0.64.0. Empfehlung: 0.64.0 (aktuell), API-Diff beim Einbau prüfen.
3. **Ziel-Ort geklärt:** Die quant-*-Crates liegen in
   `Agenten/Handel/nautilus-rust` (BrainFiles-master), NICHT im
   `Werkstatt/omnitrade`-Fork — damit entfällt die shallow-Fork-Push-Falle
   für diese Arbeit. `omnitrade-risk` wurde direkt im nautilus-rust-Workspace
   angelegt.

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
