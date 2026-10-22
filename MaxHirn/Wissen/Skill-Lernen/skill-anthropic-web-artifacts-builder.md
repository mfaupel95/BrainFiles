---
name: skill-anthropic-web-artifacts-builder
description: Trockenlauf des Skills anthropic-skills:web-artifacts-builder — React+TS+Vite+Parcel+Tailwind+shadcn/ui zu einem einzigen bundle.html für Claude-Artifacts bündeln.
metadata:
  type: reference
---

**Zweck:** Vollwertige React-Apps als einzelne HTML-Datei für Claude-Artifacts bauen. Nicht für schnelle Inline-HTML-Artifacts — sondern wenn React-Komponenten, TypeScript, shadcn/ui oder komplexere Interaktivität gebraucht wird.

**Wann nutzen:** Wenn ein Artifact React-Komponenten, TypeScript oder shadcn/ui-Komponenten braucht und eine einfache HTML-Datei nicht reicht.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. Sehr kurz (~1 Seite). Klarer Prozess.

**Gelernt — Stack:**
- React 18 + TypeScript + Vite
- Tailwind CSS 3.4.1 + shadcn/ui (40+ Komponenten vorinstalliert)
- Parcel für Bundling → `bundle.html` (alles inline: JS, CSS, Dependencies)
- Path-Aliases (`@/`) konfiguriert

**Prozess:**
1. `bash scripts/init-artifact.sh <project-name>` — Projekt anlegen
2. Code bearbeiten (App.tsx etc.)
3. `bash scripts/bundle-artifact.sh` → erzeugt `bundle.html`
4. `bundle.html` als Artifact teilen
5. (Optional) testen — NICHT upfront, spart Latenz

**Design-Warnung:** "AI slop" vermeiden: kein übermäßiges centered layout, keine lila Gradienten, keine uniformen rounded corners, kein Inter-Font.

**Grenzen:** Braucht bash + Node 18+. Nur für claude.ai-Artifacts gedacht. Für einfache Seiten ohne React-Overhead → direkt HTML schreiben (artifact-design-Skill).
