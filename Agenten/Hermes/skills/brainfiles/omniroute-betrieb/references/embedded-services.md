# Eingebettete Dienste des Routers (cliproxy, 9router, mux, bifrost, dario)

OmniRoute startet Sidecars selbst (`ServiceSupervisor`, Registry
`src/lib/services/bootstrap.ts` im Quell-Klon). Fuer Hermes relevant ist
**cliproxy** (CLIProxyAPI, Port **8317**): die `claude`-Verbindung faellt bei
einem 429 auf ihn zurueck (`UPSTREAM_PROXY: claude native failed (429),
retrying via CLIProxyAPI`). Laeuft er nicht, stirbt dieser Rueckfallweg mit
`ECONNREFUSED 127.0.0.1:8317` — das sieht wie ein Provider-Ausfall aus, ist aber
ein fehlender Sidecar.

## Zustand und Lebenszyklus per API

Auth wie bei den uebrigen Management-Pfaden
(`Authorization: Bearer $HERMES_CUSTOM_127_0_0_1_20128_API_KEY`).

| Zweck | Aufruf |
|---|---|
| Zustand | `GET /api/services/cliproxy/status` -> `state`, `health`, `pid`, `installedVersion`, `latestVersion`, `autoStart`, `providerExpose` |
| Installieren | `POST /api/services/cliproxy/install`, Rumpf `{"version":"latest"}` -> `{ok,installedVersion,installPath}` (wenige Sekunden) |
| Starten / Stoppen | `POST /api/services/cliproxy/start` / `.../stop` |
| Autostart | `POST /api/services/cliproxy/auto-start`, Rumpf `{"enabled":true}` (Rumpf ist Pflicht, sonst `invalid_type` auf `enabled`) |
| Modelle als `cliproxyapi/*` anbieten | `POST /api/services/cliproxy/provider-expose`, Rumpf `{"enabled":true}` -> 204 |
| Konten des Dienstes | `GET /api/services/cliproxy/accounts` -> `{state, accounts[]}` |

## Fallen

- **Installieren heisst nicht „laeuft", und Starten heisst nicht „bedient".**
  Ein frisch gestarteter cliproxy ohne hinterlegtes Claude-Konto antwortet auf
  jeden `claude/*`-Aufruf mit `400 unknown provider for model <name>` — vorher
  stand dort `502 ECONNREFUSED 8317`. Der Zustand ist damit NICHT besser, nur
  ein anderer Fehler. **Erst das Konto, dann starten**; fehlt es, den Dienst
  gestoppt lassen und das als offenen Schritt melden, statt „repariert" zu
  behaupten. Ein gestoppter Dienst aendert nichts am Verhalten von vorher.
- **„not_installed" ist eine eigene Wahrheit als das Binary.** Liegt der
  Binary unter `~/.omniroute/bin/cliproxyapi-<version>/` (aeltere Installation)
  und fehlt die Zeile `version_manager WHERE tool='cliproxy'`, meldet die
  Status-API `state: unknown` / `not_installed` — der Supervisor startet ihn
  dann nach jedem Routerstart NICHT, und der 8317-Rueckfallweg ist dauerhaft
  tot, ohne dass ein Log das als Fehler ausweist. `install` mit `latest` legt
  die Zeile an. Nach einem Router-Start mit 502/ECONNREFUSED auf
  claude-Verbindungen also `/api/services/cliproxy/status` mitpruefen.
- **Der Rueckfallweg ist Verstaerkung, kein Ersatz.** Primaerpfad der
  `claude`-Verbindung ist das eigene OAuth-Konto; 8317 wird nur bei 429
  gezogen. „8317 down" ist deshalb kein Grund, die Verbindung oder den
  Modellnamen zu verdaechtigen — der 429 davor ist der eigentliche Anlass.
- Der Dienst schreibt seine Daten nach `$DATA_DIR` = `~/.omniroute`
  (Default), Logs des Routers liegen unter
  `~/.omniroute/logs/quell-produktion/`.
