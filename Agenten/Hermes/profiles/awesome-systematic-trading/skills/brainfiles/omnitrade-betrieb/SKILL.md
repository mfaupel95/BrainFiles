---
name: omnitrade-betrieb
description: "Use when omnitrade: bauen, Backtests, Engine-Fixes."
category: brainfiles
---

# Omnitrade (Rust-Workspace, privater Fork)

## Wann
Alles im Klon `Werkstatt/omnitrade` (Junction → O:): bauen, Backtests mit
DSL-Skripten fahren, Engine-/CLI-Fixes, Marktdaten ziehen, Ergebnisse belegen.
Abgrenzung: die Haus-Spuren in `Agenten/Handel/` sind `handel-spuren`;
Nautilus ist `nautilus-okx-handel`.

## Repo-Grundlagen
- Privater Fork `mfaupel95/omnitrade` (AGPL-3.0, Original `jackby03/omnitrade`):
  `origin` = privater Fork, `upstream` = Original. Arbeitszweig `main`
  (`max/risk-und-binance` ist hineingemergt); keine weiteren Zweige anlegen.
- Crates: `omnitrade-engine` (account, matching), `omnitrade-cli`
  (backtest.rs, main.rs, args.rs), `omnitrade-script` (DSL: token/parser/
  evaluator), `omnitrade-ui` (egui).
- Binaries: `target/debug/omnitrade-cli.exe` (backtest/validate/live/kill),
  `omnitrade-ui.exe`.

## Backtest fahren (Standardweg)
1. Daten: Binance public klines (kein Key), 1000 Kerzen/Abruf, Pagination
   ueber `startTime`; CSV-Kopf `timestamp_ms,open,high,low,close,volume`
   (Rezept in `references/backtest-dsl.md`).
2. Strategie als DSL-Datei `.omni` schreiben (Grammatik siehe references).
3. `./target/debug/omnitrade-cli.exe backtest --script strategien/x.omni
   --data daten/y.csv --initial-balance 200000 --fee-rate 0.001
   --slippage-bps 5 --quantity 0.1`
4. Belegen: `OMNI_TRACE=1` gibt je Close eine Zeile (Seite, Kurs, PnL,
   Balance); Konsistenzprobe: `total_pnl == final_balance − initial_balance`.
   Weicht es ab, ist eine Position offen geblieben oder ein Phantom-Schenkel
   entstanden — Ergebnis NICHT als korrekt melden.

## Strategie-Evaluation (der erprobte Ablauf)
Systematisch und ehrlich pruefen — nie eine Strategie in einem einzigen
Fenster bewerten. Reihenfolge und Entscheidungsregeln:

1. **DSL-Faehigkeiten inventarisieren**, bevor man baut: welche Funktionen
   kann der Evaluator (omnitrade-script)? Stand: close/volume/sma/rsi/ema/
   highest/lowest/atr, Variablen, &&/||. Kein offset/exit/cash — `sell()`
   flippt. Ein Breakout braucht highest()/lowest() EXCLUSIVE der aktuellen
   Kerze (sonst ist close>highest() immer false, 0 Trades).
2. **Mehrere Familien bauen** (3-6), nicht eine: Meanreversion,
   Trendfolge-Kreuz, Momentum, Breakout. Je Variante eine .omni-Datei.
3. **Sweep ueber Jahre** (5.7+ Jahre, ~47k Kerzen), Metriken Total PnL,
   Trades, Win Rate, Max Drawdown. Weniger als ~30-100 Trades je Lauf:
   Unterschiede sind Rauschen, kein Signal.
4. **Stops testen** (fix ~5 % und ATR-adaptiv), je Richtung in GETRENNTEN
   ifs mit `stop_loss(...)` VOR `buy()`/`sell()` (evaluate() returned beim
   ersten Signal). Bausteine, die je Familie das Vorzeichen drehen, sind
   nicht robust.
5. **Frequenz testen** (1h vs 1d) — die groesste Einzelerkenntnis: auf 1h
   fressen Flip-Kosten jede Trendfolge, auf 1d atmet sie. Frequenz pruefen
   BEVOR man eine Strategie verwirft.
6. **Asset-Konsistenz** (BTC/ETH/SOL, gleiche nominale Groesse ueber
   --quantity): unterschiedliche Vorzeichen je Asset = kein belegbarer
   Edge. Konsistenz ueber 3 Assets = nicht zufaellig.
7. **Out-of-Sample**: Zeit-Split (timestamp_ms >= 1609459200000 = 2021),
   In-Sample vs. ungesehenes Fenster. Kein Zusammenbruch OOS = robust;
   OOS positiv allein heisst noch nicht profitabel.
8. **Ehrliche Bewertung**: Rendite/Jahr UND Trades-Zahl ausweisen.
   ~0.5 %/Jahr oder weniger = kein handelbarer Edge (nach Steuern/Spread
   real negativ). Kein Parameter-Tuning bis zur Anpassung — Datenumfang
   ist der Hebel, nicht die Parameter.

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
  dem ALTEN Binary weiter und liefern still die alten Zahlen. Nach jeder
  Aenderung erst `cargo build -p omnitrade-cli`.
- **Stops/TP/Trailing im DSL** werden seit f180342 im Backtest ausgefuehrt
  (Niveaus aus dem OrderIntent beim Oeffnen; ein Stop gewinnt gegen das
  Signal derselben Kerze; Trailing ratchet je Seite). DSL-Falle:
  `evaluate()` returned beim ERSTEN Signal — `stop_loss(...)`/`take_profit(...)`
  muessen VOR dem `buy()`/`sell()` im Block stehen, sonst werden sie nie
  ausgewertet. Messung (0.1 BTC, 6 Monate): Stop 5 % best, TP kappt die grossen
  Gewinner. Sweep-Befunde (Belege fuer den Workflow oben): alle Familien auf
  1h negativ; EMA50/200 1d +10106 (16 Trades, DD 5.1 %), konsistent ueber
  BTC/ETH/SOL (+10106/+10715/+12669), OOS 2017-20 +497 — aber ~0.5 %/Jahr,
  nicht handelbar. Einziger positiver Kandidat des Stacks.

- **patch-Werkzeug verweigert Pfade unter `Werkstatt/`** (Junction → O:).
  Edits per Python-Heredoc im Terminal (read → replace → write, Anchor-Count
  asserten), danach per Suche (search_files) verifizieren.
- **Laufende `omnitrade-ui.exe` sperrt `target/debug/omnitrade-ui.exe`** —
  Build bricht mit "Zugriff verweigert (os error 5)". Prozess per PID killen
  (`taskkill /PID <pid> /F`), neu bauen, neu starten (Hintergrund-Task).
- **Signatur/Struct erweitern (z. B. `BacktestConfig::new`, clap-Feld):**
  erst ALLE Call-Sites greppen (`grep -rn "Symbol" omnitrade-cli/src/`),
  auch Tests. Ein neues clap-Feld bricht jede `if let Commands::Backtest
  {...}`-Destruktur mit E0027 — alle Muster um das Feld ergaenzen.
- **Backtest rechnet Futures-Stil:** Equity = Balance + Unrealized,
  Positionen zum Einstieg bewertet. Ein Close MUSS ueber
  `close_position_at()` laufen (realisiert PnL in die Balance, entfernt die
  Position); ein roher Gegenseiten-Order erzeugt einen Phantom-Schenkel
  (doppelte Equity-Zaehlung). Die alte `close_position(sym, side)` entfernt
  ohne Cash-Buchung — unbenutzt, nie dafuer verwenden.
- **Drawdown ist bei dieser Buchfuehrung Sizing-getrieben:** 1 BTC auf 200k
  Konto ergibt ~59 % DD-Artefakt (Equity kollabiert nach jedem Long-Einstieg
  auf Cash-Niveau). Mit `--quantity` skalieren — PnL und DD skalieren linear.
- **Indikator-Warmup:** die Schleife ueberspringt Kerzen, bis die Indikatoren
  bereit sind (EvalError = kein Signal). Keine Trades in den ersten N Kerzen
  erwarten; ein Backtest mit `ema(20)` bricht NICHT mehr ab.
- **Hand-Nachrechnung der Buchhaltung in Python driftet** (Cash-Buchung der
  Short-Schluesse ist fehleranfaellig, PnL wird absurd). Wahrheit aus dem
  Instrumentierten Code holen (`OMNI_TRACE`), nie aus einer
  Reimplementierung.

## Ablage
- `daten/*.csv` und `strategien/*.omni` sind Arbeitsmaterial: Strategien
  versionieren, Daten-CSVs regenerierbar lassen (nicht committen).
- Skript-Operatoren und DSL-Details: `references/backtest-dsl.md`.
