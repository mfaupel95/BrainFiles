# Omnitrade Rust Workspace — Setup & Integration (geprueft und ergaenzt)

**Stand:** 30.09.2026, alles nachgemessen in `Agenten/Handel/nautilus-rust`
**Werkzeuge:** cargo 1.98.1 (797e8a9bc 2026-08-05), rustc 1.98.1

> Diese Fassung ersetzt die Vorlage vom 29.09.2026 (Claude Haiku 4.5). Die
> Crate-Beschreibungen der Vorlage stimmen; die Abschnitte *Python-Binding
> (PyO3)*, *HTTP-API*, *Docker* und *Integration in Handelszentrale* sind
> dagegen **Entwuerfe, kein Bestand** — fuer keinen davon gibt es eine Datei im
> Baum (gemessen: kein Treffer fuer `pyo3|maturin|actix|axum|rocket`, kein
> Dockerfile, kein `setup.py`/`pyproject.toml`). Alles unten ist mit echtem Lauf
> belegt; die Ausgaben stehen im Wortlaut.

---

## Workspace-Struktur (gemessen)

Fuenf Crates, 826 Zeilen Rust, ein Workspace ohne `[workspace.dependencies]` —
jede Crate pinnt ihre Abhaengigkeiten selbst:

| Crate | Quellen | Zeilen | Ebene / Aufgabe |
|---|---|---|---|
| `quant-signal` | src/lib.rs | 93 | **Neutrale Grenze** zwischen Research und Execution: `RankedBook`, `BookEvidence`, `RankedWeight`, `is_dollar_neutral()`. Haengt nur von `serde` ab — kein `nautilus-*`, kein `candle-*` |
| `quant-alpha` | src/main.rs, src/cross_panel.rs, src/lib.rs | 186 | **Modell-Ebene** (`candle-core/-nn` 0.11): MLP linear→tanh→linear, AdamW, synthetische Daten; schreibt `ranked_book.json`. `CrossPanel::fingerprint()` (SHA-256) und `required_periods(effekt, se)` |
| `quant-strategy` | src/main.rs, src/evidence.rs, src/lib.rs | 352 | **Ausfuehrungs-Ebene** (`nautilus-backtest/-model/-trading` 0.64): liest `ranked_book.json`, bildet den t-Wert SELBST, `EvidenceGate::decide()`, Seam-Guards fuer Instrument-IDs und Zielgroessen |
| `quant-planes` | src/main.rs | 113 | **Grenzpruefer**: liest `Cargo.lock`, verbietet `quant-alpha -> nautilus-*` und `quant-strategy -> candle-*`; Exit 1 bei Verstoss |
| `omnitrade-risk` | src/lib.rs | 82 | **Risiko**: `RiskLimits::check()`, `groessenfaktor(halbierung, drawdown)`, `kill_switch(Verdict)` |

`target/` ist Build-Ausgabe (4,8 GB, nicht versioniert). Der Workspace liegt IM
BrainFiles-Repo (16 verfolgte Dateien) und hat **kein eigenes `.git`**.

---

## Bauen und Testen (echte Laeufe)

```bash
cd Agenten/Handel/nautilus-rust
cargo build --workspace     # Finished `dev` profile in 16.29s
cargo test  --workspace     # 20 Tests, 6 Test-Binaries, 0 failed
```

Testverteilung: `omnitrade-risk` 3, `quant-alpha` 3 (cross_panel), `quant-planes`
2 (Ebenen-Grenze), `quant-signal` 2 (Dollar-Neutralitaet), `quant-strategy` 3
(Evidence-Gate) + 7 (Seam-Guards gegen die Fuenf Seam-Defekte). Doc-Tests: 0.

---

## Die Programme laufen — und das Gate lehnt ab (Ausgabe im Wortlaut)

```bash
./target/debug/quant-alpha.exe      # schreibt ranked_book.json
# quant-alpha: Buch geschrieben, 2 Gewichte, dollar-neutral: true
# quant-alpha: Panel-Fingerprint bcd372116d7d161d..., Perioden-Bedarf Some(1)

./target/debug/quant-strategy.exe   # liest ranked_book.json
# quant-strategy: Buch gelesen, 2 Gewichte, dollar-neutral: true
#   evidence: net=3.500 bps, n=2000, se=2.000, folds=5, positive=2
#   t = 1.75 (Huerde 2.0)
#   book state   book has no demonstrated skill: t = 1.75 below 2.0 floor
#   rebalances   0
#   positions    0 opened at the venue

./target/debug/quant-planes.exe
# quant-planes: 0 violations (Ebenen-Grenze sauber)
```

Das ist der interessante Teil: das Demo-Buch wird **abgelehnt**, weil
`net_bps 3.5 / se_bps 2.0 = t 1.75` die kompilierte Huerde `MIN_EVIDENCE_T = 2.0`
nicht erreicht. Der Gate arbeitet also im echten Lauf, und die Huerde ist eine
Konstante, kein Config-Feld (Absicht: eine Strategie, die ihre eigene
Evidenz-Huerde senken kann, hat keine).

---

## Was NICHT im Baum ist (gegen die Vorlage)

| Abschnitt der Vorlage | Befund |
|---|---|
| Python-Binding via PyO3 | kein `pyo3` in irgendeinem `Cargo.toml`, kein `maturin`, kein `setup.py` |
| Alternative HTTP-API | kein `actix-web`/`axum`/`rocket`, kein Port, kein Server |
| Docker | kein `Dockerfile`, kein `docker-compose.yml` |
| Integration in Handelszentrale | kein Orchestrator, keine Bruecke — die Vorlage beschreibt einen Bauplan |
| "Build-Output: lib*.rlib" | existiert (`target/debug/deps/libomnitrade_risk-*.rlib`), ist aber Build-Ausgabe, keine Schnittstelle |

Ebenso: die Evidenzwerte in `quant-alpha` sind **hart eingetragen**
(`net_bps 3.5, se_bps 2.0, folds 5, positive_folds 2`) und im Code als Demo
markiert ("In einem echten Build waeren das out-of-sample Folds"). Es gibt kein
Walk-Forward und keine echten Daten — aus diesem Workspace ist kein Handelssignal
ableitbar.

---

## Bezug zum eigentlichen Projekt

Der Workspace ist ein **Lehrstueck** (fuenf kleine Crates, synthetische Daten).
Das echte Rust-Projekt ist `Werkstatt/omnitrade` — 7 Crates
(`omnitrade-core/-exchange/-engine/-script/-cli/-ui/-risk`), AGPL-3.0, Fork
`mfaupel95/omnitrade`, laeuft als Papier-Spur (`Agenten/Handel/omnitrade`).
Dessen `omnitrade-risk` ist die reife Fassung (limits, kill_switch,
leverage_guard, guard, error) — die gleichnamige Crate hier ist eine
eigenstaendige Miniatur mit anderer API (`RiskLimits` statt Guard-Module).

Verwechslungsgefahr: `Agenten/Handel/nautilus-rust/omnitrade-risk` (dieser
Workspace) und `Werkstatt/omnitrade/omnitrade-risk` (echter Agent) sind
verschiedene Crates.

---

## Auffinden fuer Agenten (ProjectAtlas)

Ein eigener ProjectAtlas ist fuer diesen Workspace **nicht moeglich**, und zwar
nicht aus Bequemlichkeit, sondern per Regel des Werkzeugs: ProjectAtlas bindet
den Projektstamm an die naechste Git-Wurzel (hier `BrainFiles`) und verweigert
ein Projekt INNERHALB eines Repos. Gemessene Meldung:

```
verification_incomplete: invalid input: ProjectAtlas config
'.../nautilus-rust/.projectatlas/config.toml' resolves project root
'...\\Agenten\\Handel\\nautilus-rust' outside selected project root
'...\\BrainFiles'
```

Ohne eigenes `.git` bleibt also nur gezieltes Lesen — die fuenf Einstiegspunkte
stehen in der Tabelle oben, je Crate eine Datei. Der Atlas von
`Werkstatt/omnitrade` (188 Dateien, 31 Ordner, `scan.status: verified`) ist
davon unberuehrt.

---

## Was absichtlich nicht angefasst wurde

- kein Code geaendert, kein Commit in diesem Workspace
- `target/` (4,8 GB) und `Cargo.lock` unveraendert
- `Werkstatt/omnitrade` nicht angefasst (dort nur Atlas-Pflege: `target-live`
  ausgeschlossen, Zwecke gesetzt)
- die Entwuerfe der Vorlage (PyO3, HTTP, Docker, Zentrale-Anschluss) wurden
  NICHT gebaut

## Offene Entscheidungen

1. Soll der Workspace ein eigenes Repo werden (dann ist ein Atlas moeglich) oder
   Lehrstueck bleiben?
2. Falls daraus ein Signalweg werden soll: echte Folds statt hart eingetragener
   Evidenz — Anschluss an `Agenten/Handel/historie_binance.py` und `replay.py`.
3. Anschluss an den echten `omnitrade-risk` pruefen, statt die Miniatur zu
   erweitern.