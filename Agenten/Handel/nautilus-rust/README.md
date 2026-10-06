# nautilus-rust — die Quant-Ebene als Lehrstueck

Fuenf kleine Rust-Crates unter `Agenten/Handel/nautilus-rust` mit einer harten
Ebenen-Grenze: das Modell (`quant-alpha`) kann keine Order aufgeben, die
Ausfuehrung (`quant-strategy`) kennt kein Modell. `quant-planes` prueft die
Grenze ueber die transitiven Abhaengigkeiten aus `Cargo.lock`.

Stand 06.10.2026. Werkzeugkette: **cargo 1.98.1, stable-x86_64-pc-windows-msvc**
(`rustup show active-toolchain`). Ausfuehrliche Einordnung:
`MaxHirn/Wiki/Handel/nautilus-rust-Quant-Ebene.md`.

## Die fuenf Crates

| Crate | Ebene | Rolle |
|---|---|---|
| `quant-signal` | neutral | `RankedBook`, `BookEvidence`, `RankedWeight` — nur `serde` |
| `quant-alpha` | Modell | `candle`-MLP, schreibt `ranked_book.json` |
| `quant-strategy` | Ausfuehrung | liest das Buch, `EvidenceGate::decide()` (Huerde `MIN_EVIDENCE_T = 2.0`, kompiliert) |
| `quant-planes` | Grenzpruefer | kein `quant-alpha -> nautilus-*`, kein `quant-strategy -> candle-*` |
| `omnitrade-risk` | Risiko | `RiskLimits::check()`, `groessenfaktor()`, `kill_switch(Verdict)` |

## Bauen (reproduzierbar)

```text
cd Agenten/Handel/nautilus-rust
cargo build --workspace    # ~25 s dev, einmalig; Cargo.lock ist versioniert
cargo test  --workspace    # 20 Tests in 6 Binaries, 0 failed
```

`Cargo.lock` liegt im Repo — ein zweiter Bau auf derselben Toolchain
reproduziert dasselbe Artefakt. Das Pruefskript faehrt alles in einem Rutsch:

```text
& 'Agenten/Handel/nautilus-rust/pruefen.ps1'   # PowerShell
./Agenten/Handel/nautilus-rust/pruefen.ps1     # bash (pwsh)
```

Exit 0 nur, wenn fmt check, build, alle Tests UND die drei Programme sauber
durchlaufen; jeder Ausfall bricht mit Exit 1 und sichtbarem Fehler ab.

## Starten

Reihenfolge ist der Ablauf: erst die Research-Ebene, dann die Ausfuehrung,
dann der Grenzpruefer.

```text
cd Agenten/Handel/nautilus-rust
./target/debug/quant-alpha.exe        # schreibt ranked_book.json (2 Gewichte, dollar-neutral)
./target/debug/quant-strategy.exe     # bildet t = 1.75 < Huerde 2.0 -> lehnt ab, 0 rebalances
./target/debug/quant-planes.exe       # 0 violations (Ebenen-Grenze sauber)
```

Erwartete Ausgabe (gemessen 06.10.2026):

```text
quant-alpha: Buch geschrieben, 2 Gewichte, dollar-neutral: true
quant-strategy: t = 1.75 (Huerde 2.0)
  book state   book has no demonstrated skill: t = 1.75 below 2.0 floor
  rebalances   0
quant-planes: 0 violations (Ebenen-Grenze sauber)
```

Der abgelehnte Fall ist der Kern des Lehrstuecks: die Huerde ist eine
kompilierte Konstante, kein Config-Feld.

## Was es NICHT ist

- **kein Handelssystem** — die Evidenzwerte sind hart eingetragen
  (`net_bps 3.5, se_bps 2.0, folds 5`, im Code als Demo markiert); kein
  Walk-Forward, keine echten Daten, kein Orderweg.
- **keine Python-Bibliothek** — kein `pyo3`/`maturin`, kein HTTP-Server,
  kein Dockerfile.
- **nicht die Risikologik der Haus-Spuren** — `omnitrade-risk` hier ist eine
  Miniatur; das echte Crate liegt in `Werkstatt/omnitrade/omnitrade-risk`.
- **kein eigenes ProjectAtlas-Projekt moeglich** — der Projektstamm wird an
  die naechste Git-Wurzel gebunden (`BrainFiles`), ein Projekt innerhalb
  eines Repos verweigert ProjectAtlas (T-257).
