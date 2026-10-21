---
name: skill-agent-sdk-dev-new-sdk-app
description: Trockenlauf des Skills agent-sdk-dev:new-sdk-app — geführter Setup-Wizard für neue Claude Agent SDK Apps (TypeScript oder Python), mit Versions-Check, Codeverifizierung und Verifier-Agent.
metadata:
  type: reference
---

**Zweck:** Interaktiver Setup-Wizard für neue Claude Agent SDK Anwendungen. Stellt fünf Fragen nacheinander (Sprache, Projektname, Agententyp, Startpunkt, Tooling), prüft aktuelle Paketversionen auf npm/PyPI, erstellt alle Projektdateien, verifiziert den Code (TypeScript: `tsc --noEmit` bis fehlerfrei; Python: Syntax), startet abschließend den passenden Verifier-Agent (`agent-sdk-verifier-ts` oder `agent-sdk-verifier-py`).

**Wann nutzen:** Immer wenn eine neue Agent SDK App von Grund auf aufgebaut werden soll — noch kein Projekt vorhanden, noch kein SDK installiert.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~5 Seiten. Fünf Fragen-Phasen, dann Setup-Plan, dann Implementierung, dann Verifikation, dann Getting-Started-Guide.

Erzeugte Dateien je Sprache:
- **TypeScript:** `package.json` (type: "module", typecheck-Script), `tsconfig.json`, `index.ts` oder `src/index.ts`, `.env.example`, `.gitignore`; optional `.claude/`
- **Python:** `requirements.txt` oder `poetry init`, `main.py`, `.env.example`, `.gitignore`

Versions-Quellen:
- TypeScript: https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk
- Python: https://pypi.org/project/claude-agent-sdk/

**Gelernt:** Skill hat starke Außenwirkung (Dateien, Pakete, Netz, Subagent) → immer Trockenlauf in skill-lernen. Besonderheit: "ALWAYS USE LATEST VERSIONS" — npm/PyPI werden vor jeder Installation live abgefragt. TypeScript-Verifikation gilt erst als abgeschlossen wenn `tsc --noEmit` nullfehlerfrei läuft. Fragen-Reihenfolge ist festgelegt; ein bereits übergebenes Argument überspringt die zugehörige Frage (z. B. Projektname aus Skill-Argument).

**Grenzen:** Nur für neue Projekte, nicht für bestehende SDK-Apps. Benötigt Internetzugang (docs.claude.com, npm, PyPI). Kein Betrieb ohne ANTHROPIC_API_KEY.
