---
id: 20260930-nautilus-rust-quant-ebene
title: 'nautilus-rust — die Quant-Ebene als Lehrstueck (5 Crates, 826 Zeilen)'
tags: [handel, werkzeuge, rust, atlas]
created: 2026-09-30
updated: 2026-10-08
related: [20260930-omnitrade-spur, 20260924-backtest-fundament]
summary: 'Agenten/Handel/nautilus-rust: fuenf kleine Rust-Crates mit einer harten Ebenen-Grenze (Modell ohne nautilus, Ausfuehrung ohne candle). Gebaut, 20 Tests gruen, drei Programme laufen — das Evidence-Gate lehnt das Demo-Buch korrekt ab. Ein ProjectAtlas ist hier nicht moeglich (kein eigenes .git).'
---

# nautilus-rust — die Quant-Ebene als Lehrstueck

Stand 30.09.2026. Ort: `Agenten/Handel/nautilus-rust` (im BrainFiles-Repo
versioniert, 16 Dateien, **kein eigenes `.git`**). Werkzeuge: cargo 1.98.1.

Die Seite beschreibt, was dort wirklich steht — nicht, was ein Setup-Guide
behauptet. Anlass: eine Vorlage („OMNITRADE-RUST-GUIDE.md", Claude Haiku,
29.09.2026) beschrieb den Workspace im Kern richtig, aber vier Abschnitte darin
waren **Entwuerfe ohne Datei** (PyO3, HTTP-API, Docker, Zentrale-Anschluss). Die
geprueffte Fassung liegt unter `Werkstatt/Ablage/Guides/OMNITRADE-RUST-GUIDE.md`
(Sicherung der Vorlage daneben, `.bak-20260930`).

## Die fuenf Crates und ihre Grenze

| Crate | Zeilen | Ebene |
|---|---|---|
| `quant-signal` | 93 | neutrale Grenze: `RankedBook`, `BookEvidence`, `RankedWeight`, nur `serde` |
| `quant-alpha` | 186 | Modell-Ebene (`candle`), schreibt `ranked_book.json`, `CrossPanel::fingerprint()` |
| `quant-strategy` | 352 | Ausfuehrungs-Ebene (`nautilus-*` 0.64), liest das Buch, `EvidenceGate::decide()` |
| `quant-planes` | 113 | Grenzpruefer ueber `Cargo.lock`: kein `quant-alpha -> nautilus-*`, kein `quant-strategy -> candle-*` |
| `omnitrade-risk` | 82 | `RiskLimits::check()`, `groessenfaktor()`, `kill_switch(Verdict)` |

Der Gedanke dahinter ist die **harte Ebenen-Grenze**: das Modell (Alpha) kann
keine Order aufgeben, die Ausfuehrung (Strategy) kennt kein Modell. `quant-planes`
prueft das nicht per Konvention, sondern ueber die transitiven Abhaengigkeiten aus
`Cargo.lock` — und der Test `alpha_plane_has_no_nautilus` faellt, sobald jemand
die Grenze aufweicht.

## Was gemessen ist (30.09.2026)

```
cargo build --workspace   # Finished dev in 16.29s
cargo test  --workspace   # 20 Tests in 6 Binaries, 0 failed
```

Die drei Programme laufen und geben aus:

- `quant-alpha.exe` schreibt `ranked_book.json` (2 Gewichte, dollar-neutral).
- `quant-strategy.exe` liest es, bildet den t-Wert selbst:
  `net 3.5 bps / se 2.0 = t 1.75` gegen die **kompilierte** Huerde 2.0 →
  `book has no demonstrated skill`, `rebalances 0`, `positions 0`.
- `quant-planes.exe` → `0 violations (Ebenen-Grenze sauber)`.

Der abgelehnte Fall ist der interessante: die Huerde ist eine Konstante im Code
(`MIN_EVIDENCE_T`), kein Config-Feld — eine Strategie, die ihre eigene
Evidenz-Huerde senken kann, hat keine.

## Was es NICHT ist

- **kein Handelssystem.** Die Evidenzwerte sind hart eingetragen
  (`net_bps 3.5, se_bps 2.0, folds 5`) und im Code als Demo markiert; es gibt
  kein Walk-Forward, keine echten Daten, keinen Orderweg.
- **keine Bibliothek fuer Python.** Kein `pyo3`, kein `maturin`, kein
  `setup.py`; kein HTTP-Server, kein Dockerfile (gemessen per grep/find).
- **nicht die Risikologik der Haus-Spuren.** `nautilus-rust/omnitrade-risk` ist
  eine Miniatur mit anderer API; das echte Crate liegt in
  `Werkstatt/omnitrade/omnitrade-risk` (limits, kill_switch, leverage_guard,
  guard). Die Namen sind gleich, die Crates nicht.

## ProjectAtlas: hier nicht moeglich

Ein eigener Atlas scheitert nicht an Bequemlichkeit, sondern an der Regel des
Werkzeugs: der Projektstamm wird an die naechste Git-Wurzel gebunden (hier
`BrainFiles`), ein Projekt INNERHALB eines Repos wird verweigert. Gemessen:

```
verification_incomplete: invalid input: ProjectAtlas config
'.../nautilus-rust/.projectatlas/config.toml' resolves project root
'...\Agenten\Handel\nautilus-rust' outside selected project root '...\BrainFiles'
```

Der angelegte `.projectatlas`-Ordner wurde danach wieder entfernt. Ohne eigenes
`.git` bleibt gezieltes Lesen — fuenf Dateien, eine je Crate (Tabelle oben). Der
Atlas von `Werkstatt/omnitrade` (188 Dateien, `scan.status: verified`) ist davon
unberuehrt.

## Lehre

Ein Setup-Guide, den ein Sprachmodell geschrieben hat, ist eine **Hypothese**:
die Crate-Beschreibungen stimmten, die Anschluss-Abschnitte waren nie gebaut.
Wer danach baut, baut Luft. Reihenfolge, die traegt: Baum messen (`grep` nach dem
behaupteten Framework), bauen, testen, die Programme einmal wirklich laufen
lassen — und erst dann einordnen. Dieselbe Regel wie bei Kennzahlen aus
Fremd-Dokumenten: das Dokument ist Prosa, der Lauf ist der Beleg.