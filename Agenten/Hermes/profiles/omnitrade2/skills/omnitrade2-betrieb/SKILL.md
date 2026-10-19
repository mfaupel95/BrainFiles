---
name: omnitrade2-betrieb
description: "Use when omnitrade2: bauen, Backtests, Engine-Fixes."
category: brainfiles
---

# Omnitrade2 (Rust-Workspace, mfaupel95/omnitrade2)

## Wann
Alles im Klon `Werkstatt/omnitrade2` (Junction → O:): bauen, Backtests mit
DSL-Skripten fahren, Engine-/CLI-Fixes, Marktdaten ziehen, Ergebnisse belegen.
Abgrenzung: der aeltere Fork `Werkstatt/omnitrade` (mfaupel95/omnitrade) ist
der operativ verdrahtete Rust-Lauf; die Haus-Spuren in `Agenten/Handel/` sind
`handel-spuren`.

## Repo-Grundlagen
- `origin` = `mfaupel95/omnitrade2` (AGPL-3.0), `upstream` = `jackby03/omnitrade`
  (nur lesen, nie pushen). Arbeitszweig `main`.
- Crates: `omnitrade-core` (Typen, Ringpuffer, SMA/EMA/RSI/Volatility),
  `omnitrade-exchange` (Binance/Bybit, WebSocket+REST), `omnitrade-engine`
  (Matching, Paper, PnL), `omnitrade-script` (DSL: token/parser/evaluator),
  `omnitrade-cli` (backtest/live), `omnitrade-ui` (egui).
- Binaries: `target/debug/omnitrade-cli.exe`, `omnitrade-ui.exe`.

## Backtest fahren (Standardweg)
1. Daten: Binance public klines (kein Key), 1000 Kerzen/Abruf, Pagination
   ueber `startTime`; CSV-Kopf `timestamp_ms,open,high,low,close,volume`.
2. Strategie als DSL-Datei `.omni` schreiben.
3. `./target/debug/omnitrade-cli.exe backtest --script strategien/x.omni
   --data daten/y.csv --initial-balance 200000 --fee-rate 0.001
   --slippage-bps 5 --quantity 0.1`
4. Belegen: `OMNI_TRACE=1` gibt je Close eine Zeile; Konsistenzprobe
   `total_pnl == final_balance − initial_balance`.

## Strategie-Evaluation (der erprobte Ablauf)
Systematisch und ehrlich pruefen — nie eine Strategie in einem einzigen
Fenster bewerten. Reihenfolge und Entscheidungsregeln:
1. **DSL-Faehigkeiten inventarisieren**, bevor man baut: welche Funktionen
   kann der Evaluator (omnitrade-script)? Stand: close/volume/sma/rsi/ema/
   highest/lowest/atr, Variablen, &&/||. Kein offset/exit/cash — `sell()`
   flippt. Ein Breakout braucht highest()/lowest() EXCLUSIVE der aktuellen
   Kerze (sonst ist close>highest() immer false, 0 Trades).
2. **Mehrere Familien bauen** (3-6), nicht eine: Meanreversion, Trendfolge-
   Kreuz, Momentum, Breakout. Je Variante eine .omni-Datei.
3. **Sweep ueber Jahre** (5.7+ Jahre, ~47k Kerzen), Metriken Total PnL,
   Trades, Win Rate, Max Drawdown. Weniger als ~30-100 Trades je Lauf:
   Unterschiede sind Rauschen, kein Signal.
4. **Stops testen** (fix ~5 % und ATR-adaptiv), je Richtung in GETRENNTEN
   ifs mit `stop_loss(...)` VOR `buy()`/`sell()` (evaluate() returned beim
   ersten Signal).
5. **Frequenz testen** (1h vs 1d) — die groesste Einzelerkenntnis: auf 1h
   fressen Flip-Kosten jede Trendfolge, auf 1d atmet sie.
6. **Asset-Konsistenz** (BTC/ETH/SOL, gleiche nominale Groesse ueber
   --quantity): unterschiedliche Vorzeichen je Asset = kein belegbarer Edge.
7. **Out-of-Sample**: Zeit-Split (timestamp_ms >= 1609459200000 = 2021).
8. **Ehrliche Bewertung**: Rendite/Jahr UND Trades-Zahl ausweisen.
   ~0.5 %/Jahr oder weniger = kein handelbarer Edge.

Erst wenn 1-7 alle positiv UND Rendite >= ~1 %/Jahr: naechster Schritt
(Papier, Portfolio).

## Engine-/CLI-Fixes (Verifikation vor Meldung)
- `cargo test -p omnitrade-engine --lib`, `cargo test -p omnitrade-cli
  --bin omnitrade-cli`, `cargo clippy --all-targets -- -D warnings` (0),
  dann `cargo build --workspace`.
- Commit + Push auf `main` (`origin`), nur eigene Pfade stagen; laufende
  UI/Prozesse vor dem Build beachten (Falle unten).

## Fallen (kosten Zeit)
- **`cargo test` baut NUR das Test-Binary** — Backtest-Laeufe mit
  `./target/debug/omnitrade-cli.exe` nach Code-Aenderungen laufen sonst mit
  dem ALTEN Binary weiter. Nach jeder Aenderung erst `cargo build -p
  omnitrade-cli`.
- **Stops/TP/Trailing im DSL** werden seit f180342 im Backtest ausgefuehrt.
  DSL-Falle: `evaluate()` returned beim ERSTEN Signal — `stop_loss(...)`/
  `take_profit(...)` muessen VOR dem `buy()`/`sell()` im Block stehen.
- **patch-Werkzeug verweigert Pfade unter `Werkstatt/`** (Junction → O:).
  Edits per Python-Heredoc im Terminal (read → replace → write, Anchor-Count
  asserten), danach per Suche verifizieren.
- **Laufende `omnitrade-ui.exe` sperrt `target/debug/omnitrade-ui.exe`** —
  Build bricht mit "Zugriff verweigert (os error 5)". Prozess per PID killen
  (`taskkill /PID <pid> /F`), neu bauen, neu starten.
- **Backtest rechnet Futures-Stil:** Equity = Balance + Unrealized. Ein Close
  MUSS ueber `close_position_at()` laufen; ein roher Gegenseiten-Order erzeugt
  einen Phantom-Schenkel.
- **Drawdown ist Sizing-getrieben:** 1 BTC auf 200k Konto ergibt ~59 %
  DD-Artefakt. Mit `--quantity` skalieren.
- **Indikator-Warmup:** die Schleife ueberspringt Kerzen, bis die Indikatoren
  bereit sind. Keine Trades in den ersten N Kerzen erwarten.
- **Hand-Nachrechnung der Buchhaltung in Python driftet.** Wahrheit aus dem
  Instrumentierten Code holen (`OMNI_TRACE`), nie aus einer Reimplementierung.

## Ablage
- `daten/*.csv` und `strategien/*.omni` sind Arbeitsmaterial: Strategien
  versionieren, Daten-CSVs regenerierbar lassen (nicht committen).
