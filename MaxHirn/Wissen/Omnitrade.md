---
id: 20260929-omnitrade
title: 'omnitrade — Live-Lauf auf OKX-Demo mit Anzeige'
tags: [handel, betrieb]
created: 2026-09-29
updated: 2026-09-29
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

Immer aus dem omnitrade-Ordner, nicht aus `Agenten/Handel`:

```
cd /d %USERPROFILE%\Documents\BrainFiles\Werkstatt\omnitrade && cargo run -q -p omnitrade-cli -- live --exchange okx --network testnet --symbol BTCUSDC --script strategien/ema_cross_20_50.omni --status-file status/live.json
```

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

`omnitrade-ui` (eigenes egui-Fenster im Repo) ist bisher ein leeres Gerüst
ohne Datenzufuhr; es zeigt nichts an.

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
