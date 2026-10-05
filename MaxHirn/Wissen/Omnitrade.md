---
id: 20260929-omnitrade
title: 'omnitrade — Live-Lauf auf OKX-Demo mit Anzeige'
tags: [handel, betrieb]
created: 2026-09-29
updated: 2026-10-04
related: [20260902-handelsregeln]
summary: 'Anleitung: omnitrade (Rust) im OKX-Demo laufen lassen und in der Handelszentrale verfolgen; Schlüssel, EEA-Region, Ordergröße, Fallen.'
---

# omnitrade — Live-Lauf auf OKX-Demo mit Anzeige

Stand 29.09.2026. omnitrade ist die Rust-Handelsmaschine in
`Werkstatt/omnitrade` (Repo `mfaupel95/omnitrade`, Zweig `main`). Sie liest
1-Minuten-Kerzen über WebSocket, lässt ein `.omni`-Skript entscheiden und
ordert per REST. Angezeigt wird der Lauf im Reiter **„omnitrade“** der
Handelszentrale. Nur Demo-Geld; für Echtgeld gelten die [[Handelsregeln]].

## Einmalig: Schlüssel

Demo-Schlüssel im OKX-**Demo**-Konto anlegen (Live-Schlüssel gehen dort nicht)
und als Benutzervariablen setzen, danach **neues Terminal** öffnen:

```
setx OKX_DEMO_API_KEY "<key>" && setx OKX_DEMO_API_SECRET "<secret>" && setx OKX_DEMO_API_PASSPHRASE "<passphrase>" && setx OKX_REGION eea
```

- **`OKX_REGION=eea` ist Pflicht**, weil das Konto ein EU-Konto ist. Dessen
  Schlüssel gelten nur auf `eea.okx.com`; der globale Host antwortet
  `50119 API key doesn't exist`.
- Für Echtgeld hieße das Präfix `OKX_LIVE_API_…` (nur mit `--network mainnet`).
- Prüfen ohne Handel (liest nur das Guthaben):
  `cargo test -q -p omnitrade-exchange --lib live_demo_balance_readable -- --ignored --nocapture`

## Starten

Immer aus dem omnitrade-Ordner, nicht aus `Agenten/Handel`. PowerShell (`cd /d` gibt es dort nicht, `&&` geht in PowerShell 7):

```
cd $env:USERPROFILE\Documents\BrainFiles\Werkstatt\omnitrade; cargo run -q -p omnitrade-cli -- live --exchange okx --network testnet --symbol BTCUSDC --script strategien/ema_cross_20_50.omni --status-file status/live.json
```

- **Kerzenlänge:** `--interval 1h` (Standard `1m`; auch `15m`, `4h`, `1d`). Auf OKX laden die letzten 300 geschlossenen Kerzen vorab, lange Indikatoren (EMA 200) laufen also sofort. Backtest (Gebühr 0,1 %, `daten/`, 30.09.2026): auf 1h verlieren Trendfolger durchweg, im Plus lagen nur RSI-Varianten (`rsi30_stop5`, `rsi_25`); auf 1d gewinnen Trendfolger (`ema_atr_stop`, `ema_cross_50_200`). 1m ist nicht getestet und mit Gebühren aussichtslos.
- **Paar BTCUSDC**, nicht BTCUSDT: Das EU-Demo hat USD, USDC, BTC, ETH und XRP,
  aber kein USDT.
- **Ordergröße:** `--initial-capital` (Standard **500**) je Position, nur
  Long. Ein Kauf setzt das Kapital ein, wenn keine Position offen ist; ein
  Verkauf schließt 99,8 % der Position. Weitere Signale in dieselbe Richtung
  werden ignoriert.
- Die Strategie braucht erst genug Kerzen; bei `ema_cross_20_50` vergeht
  rund eine Stunde bis zum ersten möglichen Signal.
- Nur **ein** Lauf zur Zeit: Zwei Läufe ordern doppelt und schreiben in
  dieselbe Statusdatei.

## Anzeige

Handelszentrale öffnen (aus `Agenten/Handel`):

```
scanner\.venv\Scripts\pythonw.exe handelszentrale.py
```

Der Reiter „omnitrade“ liest `Werkstatt/omnitrade/status/live.json` (anderer
Pfad über `OMNITRADE_STATUS`): Zustand, Börse, Netz, Kerzen, letzter Kurs,
Signal, Orders. Schnellblick ohne Fenster: `python omnitrade_bridge.py`.
Die Anzeige liest nur und steuert nichts.

**Eigenes Fenster `omnitrade-ui`** (egui): links Kerzenchart (letzte 100),
rechts oben Zustandszusammenfassung, rechts unten die letzten Orders. Liest
dieselbe Statusdatei einmal pro Sekunde, nur lesend. Aus dem omnitrade-Ordner:

```
cargo run -q -p omnitrade-ui
```

Anderer Pfad: als erstes Argument oder über `OMNITRADE_STATUS`. Das Fenster
zeigt nur, was der Lauf schreibt; ohne Lauf steht dort „feed: no status file“.

**Konfig für Hermes:** `Agenten/Handel/hermes-omnitrade-config.json` (Stand
04.10.2026) fasst Pfade, Modus (OKX-Testnet, kein Echtgeld), Schlüssel-Namen
und die Erlaubt-/Verboten-Liste für Hermes zusammen. Sie dokumentiert nur;
kein Programm liest sie.

## Beenden

Strg+C im Terminal, oder `taskkill /IM omnitrade-cli.exe /F`.

## Fallen

- **Harter Abbruch** (taskkill, geschlossene Shell) lässt `state: running` in
  der Statusdatei stehen; die Handelszentrale meldet das erst nach 5 Minuten
  als „veraltet“.
- **Keine Neuverbindung:** Reißt der OKX-Socket ab, endet der Lauf; neu starten.
- **Binance-Weg** im Live-Lauf ist kaputt (verbindet vor dem Abonnieren, das
  lehnt der Client ab). Nur OKX benutzen.
- Nach `setx` wirkt nichts im alten Terminal. Ein Tippfehler im
  Variablennamen (z. B. `OKX_DAMO_…`) führt zu „environment variable not set“.

## Lauf vom 30.09.2026 (ausgefuehrt, Beleg)

- **Vorbedingung erfuellt:** `OKX_DEMO_API_KEY`, `OKX_DEMO_API_SECRET`,
  `OKX_DEMO_API_PASSPHRASE` und `OKX_REGION=eea` sind als Benutzervariablen gesetzt
  (nur Existenz und Laenge geprueft, Werte nie ausgegeben). Vorabprobe ohne Handel
  gruen: `cargo test -q -p omnitrade-exchange --lib live_demo_balance_readable -- --ignored --nocapture`.
- **Guthaben des Demo-Kontos** (gelesen, nichts gehandelt): USD 100.000, USDC 100.000,
  BTC 1, ETH 10, XRP 50.000, ETC 5, USDG 100.000 - alle frei, nichts gesperrt.
- **Lauf gestartet** 30.09.2026 07:00 aus `Werkstatt/omnitrade` mit den Schaltern
  dieser Anleitung; PID **76116**, Log `Werkstatt/omnitrade/logs/live-20260930-0700.log`.
- **Anzeige:** Handelszentrale laeuft (aus `Agenten/Handel`) und liest
  `status/live.json` im Reiter "omnitrade"; Schnellblick ohne Fenster
  `scanner\.venv\Scripts\python.exe omnitrade_bridge.py` -> `ok: true`,
  `state: running`, Kerzen wachsen, `orders_placed: 0`.
- **Einordnung:** `orders_placed: 0` kurz nach dem Start ist der Normalfall -
  `ema_cross_20_50` braucht rund eine Stunde Kerzen bis zum ersten moeglichen Signal.
- **Nur ein Lauf:** vor dem Start geprueft, dass kein `omnitrade-cli.exe` laeuft
  (Zaehlung = 1, der eigene). Zwei Laeufe ordern doppelt und schreiben in dieselbe
  Statusdatei.

## Indikatoren und Strategien (30.09.2026)

- **Neu in `.omni`:** `macd/macd_signal/macd_hist(schnell, langsam, signal)`, `bb_lower/bb_mid/bb_upper(periode, faktor)`, `stoch_k(n)`, `adx/plus_di/minus_di(n)`. Code: `omnitrade-script/src/extra.rs`. Neue Strategien in `strategien/`: macd_trend, bollinger_pullback, bollinger_meanrev, stoch_pullback, adx_trend, adx_macd.
- **Messlatte ist Buy-and-Hold**, nicht null. Auf Tageskerzen (BTC, feste Menge 0,1, Gebuehr 0,1 %, Slippage 5 bp) schlagen nur `adx_macd` (9958 gegen 5953) und `ema_cross_50_200` (10106) die volle Reihe; Mean-Reversion (Bollinger, Stochastik) verliert auf ungesehenen Daten.
- **Walk-forward je Jahr, BTC 1d (PnL-Differenz je Jahr):** `adx_macd` ist in allen 10 Jahren positiv (Minimum +50), verliert aber in starken Bullenjahren gegen Buy-and-Hold (2017, 2020, 2023, 2024) und gewinnt in Baeren-/Seitwaertsjahren (2018, 2022, 2025, 2026). `ema_cross_50_200` schwankt stark (2021 -971, 2024 +5124). Grobe Rechnung (Differenz kumulierter Laeufe), keine Neuoptimierung je Fenster.
- **MoonDev-Strategien:** die Zahlen dort sind Modellprosa, nachgemessen verlieren sie gegen Buy-and-Hold (siehe `Wiki/Werkzeuge/MoonDev-GUI-und-RBI.md`); nichts uebernommen.

## Pine-Strategien aus Wiki/handel (30.09.2026)

Sechs TradingView-Skripte (`MaxHirn/Wiki/handel/*.pine`: SMA 20/50, EMA 12/26, MACD-Kreuz, RSI-Mean-Reversion, Bollinger-Breakout, Donchian 20/10) liegen als `strategien/pine_*.omni` vor. Dafuer neu: `prev(ausdruck)` (Ausdruck auf der Reihe ohne die letzte Kerze) - Kreuzen = `a > b && prev(a) <= prev(b)`; ohne das kaufte jede Kerze im Zustand neu (Stop/TP-Churn, Gebuehren fressen alles).

- **Backtest ist Long/Short**, der Live-Lauf Long-only (Spot): `sell()` eroeffnet im Backtest eine Short-Gegenposition. Fuer live-gleiche Zahlen `OMNI_LONG_ONLY=1` setzen. Long/Short-Endstaende sind unzuverlaessig (RSI-Skript: 94.941 aus 10.000 bei 0,05 BTC - Buchungsartefakt der Shorts), Max-Drawdown-Werte ebenfalls (55 % bei 0,05 BTC/10.000 USD unmoeglich). Bislang genannte Backtest-Zahlen fuer `sell()`-Strategien stammen aus dem Long/Short-Modus.
- **stop_loss/take_profit gehoeren in den if-Block vor `buy()`/`sell()`** - die Auswertung endet beim ersten Signal, spaeter stehende Stops werden nicht gelesen.
- Ergebnis (Long-only, 0,05 BTC, Start 10.000; Buy-and-Hold 12.980): BTC 1d voll: adx_macd 13.982, Pine-Skripte 9.670-10.548. BTC 1d ungesehen (B&H 11.232): adx_macd 11.311, Pine 10.000-10.474. ETH 1d (B&H 11.469): adx_macd 14.111, Pine 8.183-10.140. BTC 1h 6 Monate (B&H 10.771): adx_macd 10.622, bollinger_breakout 10.422, Rest 9.546-10.214. **Keines der sechs schlaegt adx_macd oder Buy-and-Hold; nichts auf die Live-Spur gelegt.**

## Laeufe starten und live vorbereiten (30.09.2026)

**Start aller Testnet-Laeufe:** `omnitrade-laeufe.cmd liste` zeigt Tabelle, `start <name>|alle [--trocken]` startet fehlende Laeufe (Agenten/Handel/omnitrade_start.py; Namen dort in `LAEUFE`). Je Lauf eine Statusdatei `status/live_<strategie>_<symbol>.json`, 1h, 500 USD, OKX-Demo. Programm-Vorzug: `target-live/release` (eigener Build, ohne Sperre durch laufende Laeufe), dann `target/release`, `target/debug`. Neubau: `CARGO_TARGET_DIR=<omnitrade>/target-live cargo build --release -p omnitrade-cli`.

**Doppelstart-Schutz:** entscheidet die Kommandozeile der laufenden `omnitrade-cli.exe` (`--status-file status/live_X_Y.json`), erst danach Statusdatei+PID. Grund (Fehler beim Bau am 30.09.): ein Duplikat ueberschrieb die Statusdatei, der naechste Start hielt den echten Lauf fuer tot und startete noch eins - beide sofort beendet, keine Order. Das Alter der Datei zaehlt nie (1h-Kerzen: bis 1 h alt).

**Gestartet:** rsi30_stop5 und adx_macd, je BTCUSDC/ETHUSDC. Die sechs `pine_*` sind startklar, laufen aber nicht (Backtest: keine schlaegt adx_macd oder Buy-and-Hold).

**Echtes Konto (OKX mainnet) - Stand: gesperrt.** `live_loop.rs` bricht bei `--network mainnet` mit "requires additional Phase 3 safety gates" ab; der Zweig ist absichtlich zu. Vor einer Freigabe (Max entscheidet, Claude legt keine Order):
1. Mehrwochen-Testnet mit Ergebnis ueber Buy-and-Hold und Gebuehren (Auswertung: `omnitrade-auswertung`).
2. Bekannte Schwaechen beheben: Socket-Neuverbindung, harter Abbruch laesst `state: running`, ungeklaert ob `stop_loss()` live als Boersenorder ankommt (sonst kein Schutz bei Ausfall).
3. Eigener OKX-Live-Key, nur Handel, **keine Abhebung**, IP-Whitelist; Umgebungsvariablen `OKX_LIVE_API_KEY/_SECRET/_PASSPHRASE`, EU-Konto `OKX_REGION=eea`. Nie in Chat oder Datei.
4. Limits: `RiskGuard::mainnet()` (omnitrade-risk/src/limits.rs) pruefen, Startkapital klein (z. B. 50-100 USD), ein Symbol, eine Strategie; Kill-Switch `omnitrade-cli kill` vorher testen.
5. Code-Gate bewusst oeffnen (eigene Aenderung + Test), erst dann `--network mainnet`.
