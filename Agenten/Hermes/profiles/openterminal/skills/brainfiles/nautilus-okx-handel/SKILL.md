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
- Fehlende Quotes („node.run() – verbinde …“ und danach nichts) haben zwei
  geklaerte Ursachen: (1) der **Data-Client darf KEINE Zugangsdaten** bekommen —
  mit Schluessel meldet er sich zusaetzlich am privaten business-Websocket an
  und schlaegt bei IP-Whitelist-Fehler komplett fehl, oeffentliche Quotes
  inklusive; (2) der **Order-Client ist opt-in** — sonst wartet der Kernel 60 s
  auf ihn und keine Strategie startet, kein Abo. Belegbar sauberer Pfad:
  Data-Client ohne Credentials, Order-Client opt-in, `test_gui_quote_pfad.py`
  mit ankommenden Quote-Ticks.

## Ablage (Kostenfalle)
- Lauffähiger Node-Code gehört nach `Agenten/Handel/` (versioniert, in der
  Sicherung nach G:), **nicht** in die Werkstatt — die wird geleert und ist von
  der Sicherung ausgeschlossen; dort angelegte Arbeit ist weg.
- Die Node-Historie (eigenes `.git`) liegt ausser Haus im privaten
  GitHub-Repo `mfaupel95/nautilus` (Remote `origin`, Zweig `master`); nach
  jeder Aenderung am Node **committen UND pushen** — robocopy nimmt `.git`
  generell aus (`/XD .git`), ungepushte Commits existieren also nur auf
  diesem Rechner. `.gitignore` mit `set-okx-env.ps1`, `*.env`, `*.key`,
  `*.pem` niemals lockern: ein einmal committeter Schluessel bleibt im
  Verlauf und verlangt History-Rewrite.
- Verlust-Recovery: `O:\Werkstatt\` ist die Zweitkopie und hält oft den
  überlebenden Git-Klon inkl. `.venv`. `G:`/`Q:` enthalten **keine**
  Werkstatt-Inhalte (nur MaxHirn/Agenten).