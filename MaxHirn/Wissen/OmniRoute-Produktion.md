---
id: 20260907-omniroute-produktion
title: 'OmniRoute-Produktion'
tags: [betrieb, werkzeuge, omniroute]
created: 2026-09-07
updated: 2026-09-08
related: [20260831-python-versionen, 20260830-verbindungen]
summary: 'Der OmniRoute-Quell-Klon (Werkstatt/OmniRoute) ist als Produktions-Router installiert und verifiziert; der Umstieg gegen die globale npm-Instanz ist vorbereitet, aber noch nicht vollzogen.'
---

# OmniRoute-Produktion

Stand 07.09.2026. Der OmniRoute-Router laeuft als **globale npm-Installation**
(`omniroute serve`, Port 20128) und wird von allen Agenten benutzt (Hermes,
Claude Code, Codex). Zusaetzlich ist der **Quell-Klon**
`Werkstatt/OmniRoute/` (Branch `release/v3.8.51`) als Produktions-Kandidat
vorbereitet.

## Quell-Installation (abgeschlossen 07.09.2026)

- `npm install`: 2518 Pakete, `.env` aus `.env.example` erzeugt (47 Keys).
- Native Module verifiziert (`libxmljs2`, `onnxruntime-node` laden; node-gyp
  brauchte MSVC — installiert).
- Smoke-Test + `npm run omniroute:verify`:
  **Gateway PASS, Catalog PASS (1940 Modelle), Pools/Allocations/Status PASS.**
  Der Quell-Klon ist damit nachweislich produktionsfaehig, inkl. Kernmodule.
- **5 Install-Skripte** sind von `allow-scripts` uebersprungen (playwright,
  bun, libxmljs2, onnxruntime-node, opencode-ai). Die nativen laden auch ohne;
  die restlichen sind optionale Dev-/Browser-Module. **Blockieren nichts.**

## Umstieg Global -> Quell (vorbereitet, NICHT vollzogen)

**Entscheidung steht noch aus**, und zwar: WANN. Es gibt keinen technischen
Hinderungsgrund mehr. Aber Quell und global teilen sich
`~/.omniroute/storage.sqlite` — **nie beide gleichzeitig laufen lassen.**

Abwaegeung (Vor-/Nachteile): Fuer Quell spricht eine zentrale git-versionierte
Code-Quelle, update/patch unter Kontrolle (`git pull` + `npm install` statt
`npm update -g`), debugbarer Stacktrace, Konsistenz mit dem Rest des Systems
unter `BrainFiles/`. Dagegen: kurzes Betriebsfenster beim Umschalten (Router
muss stoppen; Agents sind kurz unterbrochen), mehr eigene Wartung nach
Updates.

Wechsel-Skript: `Werkstatt/Projekte/OmniRoute/omniroute-quell-produktion.ps1`
(bricht ab, wenn Port 20128 belegt ist → schuetzt die laufende Instanz vor
Doppelstart; startet sonst Quell-`npm run start`, wartet auf Port, laesst
`omniroute:verify` laufen). **Wichtig: Nur ausfuehren, wenn keine
Hermes-Agenten am Router arbeiten.**

**Produktions-Build (Stand 08.09.2026):** `npm run build` erfolgreich, BUILD_ID
vorhanden, Standalone-Bundle in `.build/next/standalone` komplett
(node_modules, sqlite-vec, Compression-Worker, LLMLingua co-located). Der
Umstieg ist damit buildseitig fertig — es fehlt nur noch der Start des
Quell-Routers, sobald der Router frei ist (Hermes durch).

## Betriebsregeln

- **Never zwei OmniRoute-Instanzen auf derselben SQLite.** Quell und global
  teilen `~/.omniroute/storage.sqlite`.
- Quell-Produktion startet per `npm run start` aus dem Quell-Klon (kein
  separates build noetig; bundelt selbst, `bundler=production`).
- `npm run dev` braucht Schreibplatz fuer `.build/` (Turbopack-Cache); bei
  vollem Datentraeger bricht es mit os error 112 ab.