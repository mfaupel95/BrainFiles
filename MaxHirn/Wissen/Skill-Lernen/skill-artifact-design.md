---
name: skill-artifact-design
description: Trockenlauf des Skills artifact-design — Seitenvertrag, Designprozess, Fundamentals und Prozess für alle Artifacts; Pflichtlektüre vor jedem Artifact-Publish.
metadata:
  type: reference
---

**Zweck:** Verbindliche Regeln für jeden Artifact-Publish — Format, Skeleton, Responsive, Themes, Typografie, Prozess.

**Wann nutzen:** Vor JEDEM Artifact-Publish, auch für skill-instruierte Markdown-Dateien.

**Lauf:** 2026-10-22, trockenlauf.

**Seitenvertrag (unveränderlich):**
- Format: immer `.html`; `.md` nur wenn Skill es explizit verlangt
- Kein eigenes `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` — Skeleton wird automatisch eingefügt
- `<title>` an oberster Stelle (nur erste 8 KB gescannt)
- `<meta name="claude:viewport-fit-sides" content="cover">` — nur zusammen mit beiden `max()` Guttern
- Externe Skripte: NUR cdnjs, jsdelivr, unpkg, tailwind-CDN, jquery; Stylesheets: NUR fonts.googleapis.com
- Bibliotheken mit exakter Version, mindestens 2 Wochen alt, UMD-Build

**Pflicht-Designprozess:**
1. Design-Plan als `:root`-Block in die Datei — 4–6 Farb-Tokens, 2+ Schrift-Tokens, Layout-Konzept
2. Alle Farb- und Schrift-Entscheidungen aus diesen Tokens ableiten
3. Optional: einmal `ArtifactCheck` / Preview → ein Korrekturpass → publizieren; kein zweites Mal

**Fundamentals (Auswahl):**
- Beide Themes (light/dark) vollständig: alle Tokens auf `:root`, dark nur in Media Query + `[data-theme]`
- `body` immer mit explizitem `background` aus Token (nie transparent)
- Seiten-Gutter: `padding-left: max(16px, env(safe-area-inset-left, 0px))`
- Kein `100vh` für Einseiter — stattdessen `height: 100%` auf html + body
- `font-variant-numeric: tabular-nums` bei Spalten mit Zahlen
- Seite bei Ladezeit vollständig sichtbar — kein `opacity: 0` auf Hauptinhalt

**Anti-AI-Design-Warnung:** Diese Cluster vermeiden: warmes Creme #F4F1EA + Serif + Terrakotta; Near-Black + Acid-Green; Inter/Space Grotesk als Standardwahl; Emoji als Abschnittsmarker; alles zentriert; `rounded-lg` überall.

**Titel-Regel:** Kurze Nomenklatur (2–4 Wörter), kein Erklärungsanhang nach Bindestrich/Doppelpunkt. Beschreibung in `description`-Parameter, nicht im `<title>`.
