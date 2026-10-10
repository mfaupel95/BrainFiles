---
name: nautilus-okx-handel
description: "OKX-Paper-Node in NautilusTrader aufsetzen/reparieren."
category: brainfiles
---

# NautilusTrader OKX-Node (Demo/Paper)

## Wann
OKX-Paper-/Demo-Node in NautilusTrader aufsetzen, starten, Credentials oder
Region prüfen, eine Order-Aufgabe testen — alles, was den lokalen
Nautilus-Knoten gegen die OKX-API betrifft. Abgrenzung: scanner/xperp/orb sind
`handel-spuren`; OKX-Wallet/Onchain sind die `okx-*`-Bundled-Skills.

## Kernkonfiguration (bewährt, Stand Nautilus 1.231)
- OKX kennt nur **DEMO** und **LIVE** — kein „paper“. `environment` ist
  `OKXEnvironment.DEMO` (Demo-Key) bzw. `LIVE` (Live-Key); `region` ist das
  Enum `OKXRegion` (EEA), nie der String `"us"`.
- **Demo-Key → Region EEA** (`my.okx.com` / `eea.okx.com`). Ein GLOBAL-Aufruf
  mit einem EEA-Key liefert 50119 („API key doesn't exist“).
- `load_spreads=False` für EEA DEMO — der Spread-Endpoint antwortet dort mit
  404, und BTC-Quotes brauchen keine Spreads.
- **Factories vor `node.build()` registrieren** (`OKXLiveDataClientFactory`,
  `OKXLiveExecClientFactory` unter Venue „OKX“), sonst
  „No LiveDataClientFactory“.
- Credentials als **ein** vollständiger Satz aus einer Quelle lesen
  (`HKCU\Environment`), nie Registry-Werte mit Prozess-Umgebung mischen.
- Paper-Client-Order-IDs müssen **alphanumerisch** sein.
- `nautilus_trader` ist nicht global installiert — der Node läuft aus einem
  eigenen `.venv` (nicht das Handel-venv der scanner/xperp-Spuren).

## Fallen (OKX-API)
- `50110` — öffentliche IP fehlt in der API-Key-Whitelist. Im Portal eintragen
  oder Whitelist deaktivieren.
- `50101` — „APIKey does not match current environment“: Key gegen falsches
  environment verwendet (Demo-Key auf Live-Endpunkt).
- `403 code 1010` ohne `User-Agent`-Header; mit `Mozilla/5.0` kommt die echte
  Antwort (z. B. 50110) statt eines Geoblock-Fehlschlusses.
- Fehlende Quotes („node.run() – verbinde …“ und danach nichts): ungelöst —
  nicht als funktionierend dokumentieren, bis ein Quote nachweislich ankommt.

## Ablage (Kostenfalle)
- Lauffähiger Node-Code gehört nach `Agenten/Handel/` (versioniert, in der
  Sicherung nach G:), **nicht** in die Werkstatt — die wird geleert und ist von
  der Sicherung ausgeschlossen; dort angelegte Arbeit ist weg.
- Verlust-Recovery: `O:\Werkstatt\` ist die Zweitkopie und hält oft den
  überlebenden Git-Klon inkl. `.venv`. `G:`/`Q:` enthalten **keine**
  Werkstatt-Inhalte (nur MaxHirn/Agenten).