# Rust-Migration des Handels-Stacks — Design-Spezifikation

**Datum:** 2026-09-19
**Status:** Genehmigt (Ziel-Ort `nautilus-rust` im BrainFiles-Repo)

## Zweck

Die Python-Handels-Spuren mittelfristig auf Rust umstellen, wo technisch
sinnvoll — mit der Zwei-Ebenen-Architektur: **das Modell schlaegt vor, die
Engine entscheidet, die Grenze erzwingt der Linker, nicht Policy.**

Gegenstand dieser Spezifikation sind die noch fehlenden Bausteine des
Implementierungsplans `docs/plans/2026-09-19-python-zu-rust-migration.md`,
korrigiert um den tatsaechlichen Ist-Stand. Die fertigen, gruenen Crates
(quant-signal, quant-strategy, quant-alpha) bleiben unveraendert; diese Spec
beschreibt die Luecken und den finalen Ziel-Ort.

## Ziel-Ort (korrigiert)

Der Plan schrieb `Werkstatt/omnitrade`. Die Arbeit liegt nachweislich in
`Agenten/Handel/nautilus-rust` — Teil des BrainFiles-Hauptrepos (origin
mfaupel95/BrainFiles, Zweig master, Cargo.toml versioniert). **Kein Umzug**
nach `Werkstatt/omnitrade`; dies haette keinen betrieblichen Mehrwert und
wuerde einen nur in `nautilus-rust` lauffaehigen Stand zerlegen.

`Documents/github/nautilus_trader` ist das offizielle NautilusTrader-Repo
(Skill-Vendor-Quelle) — dient nur als Abhaengigkeits-Quelle der
`nautilus-*-Crates` (0.64), wird nicht Ziel eigener Commits.

## Ist-Stand (verifiziert gruen)

| Crate | Inhalt | Tests |
|---|---|---|
| `quant-signal` | `RankedWeight{instrument_id, weight}`, `BookEvidence`, `RankedBook`, `is_dollar_neutral(tol)` (1e-9) | 2 gruen |
| `quant-strategy` | `t_stat`, `has_demonstrated_skill` (t>=2.0, folds>=2), Seam-Guards Defekt 2/3, Nautilus-Demo-Backtest | 7 gruen |
| `quant-alpha` | candle-MLP + `fit_and_write_book` -> `ranked_book.json` | **0 Tests** (laeuft, kein `#[cfg(test)]`) |

Architektur-Lauf bewiesen: `quant-alpha && quant-strategy` verweigert
sachgemaess (t=1.75 < 2.0) — Engine entscheidet.

## Zu bauende Deltas

### Areal 1: `quant-planes` (neues Workspace-Mitglied)

- **Rolle:** Ebenen-Grenze linker-erzwungen verifizieren.
- **Konsumiert:** nur `Cargo.lock` (serde) und `quant-signal` (Schema).
- **Interface:** CLI `quant-planes` — liest `Cargo.lock`, baut fuer jede
  Workspace-Crate die transitive Abhaengigkeitsmenge ueber die
  `dependencies`-Felder, prueft:
  - `quant-alpha` enthaelt KEIN `nautilus-*`-Crate im Graphen.
  - `quant-strategy` enthaelt KEIN `candle-*`-Crate im Graphen.
  - `quant-signal` haengt nur von `serde` ab (Plane-neutral).
- **Exit:** 0 = sauber, 1 = Verstoss (Nennung der verletzenden Crate).
- **Tests:** `alpha_plane_has_no_nautilus`, `strategy_plane_has_no_candle`
  (lesen denselben `Cargo.lock` wie die CLI).

### Areal 2: `EvidenceGate`/`Verdict` in `quant-strategy`

- **Rolle:** das versprochene, aber bisher nur als freie Funktionen
  existierende Urteils-Interface public machen.
- **Interface:**
  `EvidenceGate::decide(&BookEvidence) -> Verdict` mit
  `Verdict::{Admit, Refuse { reason: String }}`.
  Die bestehenden Module-Konstanten `MIN_EVIDENCE_T = 2.0` und
  `MIN_EVIDENCE_FOLDS = 2` werden darin gekapselt (nicht Config — eine
  Strategie, die ihre eigene Evidenz-Bar senken kann, hat keine).
- **Entscheidung (verstanden, nicht erneut fragend):** `Verdict` liegt in
  `quant-strategy` (Engine-Ebene), NICHT in `quant-signal`. Schemata bleiben
  Plane-neutral (kommentiert in lib.rs) — Urteile gehoeren der Engine.
- **Tests:** `refuses_below_t_floor`, `admits_above_t_floor`,
  `refuses_single_fold` (die drei aus dem Plan, auf den Ist-Code angepasst).

### Areal 3: `quant-alpha` erweitern

- **Rolle:** fehlende Kern-Features aus dem Plan nachtragen.
- **Interface:** `CrossPanel` (Assets, beide Matrizen, Spec, Horizont),
  `fingerprint() -> String` (SHA-256 ueber die serialisierten Felder),
  `required_periods(effekt, se) -> Option<u64>` — `None` bei falsch
  gerichtetem Effekt (negativ kann durch Warten nicht signifikant werden).
- **Held:** keine `nautilus-*`-Abhaengigkeit (durch `quant-planes` erzwungen).
- **Tests:** `fingerprint_changes_with_panel`,
  `required_periods_none_for_wrong_direction`.

### Areal 4: `omnitrade-risk` (Sizing/Drawdown/Kill-Switch)

- **Rolle:** Risiko-/Sizing-Logik aus Python nach Rust.
- **Konsumiert:** `Verdict` aus `quant-strategy`
  (Pfad-Dependency, da `omnitrade-risk` im BrainFiles-Workspace liegt).
- **Interface:** `RiskLimits::check(&OrderRequest) -> Result<(), RiskViolation>`
  — Position Limits, Drawdown-Halbierung, Kill-Switch. Zahlen aus der
  `wachen.json` der Spur (Risiko je Position, max. Positionen, Buchrisiko,
  Drawdown-Schwelle).
- **Tests:** `rejects_order_over_max_units`,
  `drawdown_halving_reduces_size`.
- **Anmerkung:** `omnitrade-risk` liegt im `Werkstatt/omnitrade`-Fork;
  der Fork-Abgleich (shallow -> `git fetch --unshallow upstream`) gilt vor
  jedem Push. Alternativ kann die Crate direkt im `nautilus-rust`-Workspace
  angelegt werden; Entscheidung im Implementierungsplan.

### Areal 5: Plan-Doc korrigieren

`docs/plans/2026-09-19-python-zu-rust-migration.md`: Ziel-Ort auf
`nautilus-rust` reparieren, Ist-Stand-Schema von Aufgabe 1 als gueltig
anerkennen, Checkboxen auf den tatsaechlichen Fortschritt setzen.

## Nicht-Migrationsliste (bleibt Python, unveraendert)

`dauerlauf.py` (Orchestrator), `handelszentrale.py` (GUI), `freigabe.py`
(Freigabekette), `llm_lokal.py` (Ollama-Zugang, Rust ruft via HTTP),
`backtest_urteile.py`. Kein Live-Handel — alles Papier/Backtest, `--live`
wird verweigert. Bedingung 4 (Journal/Spiegelung nach `Q:\Handel_Journal`)
bleibt. Keine Credentials; `test_credentials.py`/`run_okx_paper_node.py`
nie lesen, ausgeben, committen.

## Erfolgskriterien

- Alle Tests gruen (signal 2, strategy 7+neue, alpha +fingerprint/req_periods,
  planes 2, risk neu).
- `quant-planes` meldet `0 violations`.
- `cargo run -p quant-alpha && cargo run -p quant-strategy` verweigert weiter
  sachgemaess (t=1.75 < 2.0); der Admit-Pfad ist per Test abgedeckt.

## Review-Needs

Diese Spezifikation wird dem Nutzer zur Pruefung vorgelegt; erst nach
Zustimmung folgt der Implementierungsplan (writing-plans).