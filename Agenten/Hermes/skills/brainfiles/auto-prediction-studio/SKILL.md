---
name: auto-prediction-studio
description: "Das Auto-Prediction-Studio (Vite :5173, Control Plane :4100) lokal starten und den Codex-Preflight pruefen."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Auto-Prediction, Studio, Codex, Preflight, Prediction-Market, BrainFiles]
    related_skills: [befund-zu-fix]
---

# Auto-Prediction-Studio starten

Repo: `Agenten/Handel/OpenAlice/workspaces/workspaces/auto-prediction-modest-birch-bridge`
(Fork `mfaupel95/Auto-Prediction`, Upstream `TraderAlice/Auto-Prediction`). Bot-Profil:
`hermes -p auto-prediction chat`.

## Start

1. Laeuft schon etwas auf `:5173` oder `:4100`? Dann zuerst beenden, sonst weicht Vite auf
   einen anderen Port aus.
2. `pwsh -File Werkstatt/auto-prediction-studio/studio-start.ps1` (Wurzel-relativ).
   Das Skript setzt `CODEX_HOME=%USERPROFILE%\.codex-harness` und `npm_execpath` auf den Shim
   `Werkstatt/auto-prediction-studio/pnpmshim.js` (Grund: `pnpm.exe` kann `node` nicht laden,
   Issue #119).
3. Pruefen: `http://127.0.0.1:5173/` liefert 200, im Log steht
   `control-plane http://127.0.0.1:4100`.

## Preflight (kostet kein Modellbudget)

- Studio -> Agent operations -> beim Profil `CODEX · gpt-5.6-terra` auf **Preflight**.
  Erwartet: `USABLE · Codex app-server recognized the configured ChatGPT account`.
- Discover-Seite (In-Process, `CODEX_RESPONSES`) bleibt mit HTTP 403 gesperrt (Issue #118).
  Das ist kein Login-Fehler.

## Fallen

- **`~/.codex/config.toml` nutzt OmniRoute** -> der App-Server meldet `account: null`
  ("did not expose a ChatGPT account"). Darum das eigene `CODEX_HOME`, Login einmalig:
  `CODEX_HOME=%USERPROFILE%\.codex-harness codex login` (ChatGPT, nicht API-Schluessel).
- **CRLF in `projects/fixtures/`** zerstoert die Hash-Pruefung (`fixture hash mismatch`,
  Control Plane stuerzt ab). Abhilfe: PR #117 (`-text`), lokal Dateien auf Commit-Stand.
- Auth-Dateien (`auth.json`, `.env`) nie lesen oder ausgeben.

## Grenzen

- Scans, manuelle Laeufe und aktive Kampagnen verbrauchen Modellbudget: nur auf
  ausdrueckliche Freigabe. Vorschau und pausierte Kampagne sind kostenlos.
- Harness ist rein forschend (`PROPOSE_ONLY`), kein Handel, kein Wertetransfer.
- Nichts committen oder pushen ohne Auftrag.
