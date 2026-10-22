---
name: skill-dataviz
description: Trockenlauf des Skills dataviz — Design-System-agnostische Visualisierungsmethodik; Farbvalidierung per Skript; 7-Schritt-Prozedur; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Korrekte Datenvisualisierungen nach einer Prozedur erzeugen — Farbe zuletzt, Validator-Skript immer.

**Wann nutzen:** Vor jedem Chart, Dashboard, Plot — egal in welchem Medium oder Framework.

**Lauf:** 2026-10-22, trockenlauf.

**7 Schritte (Reihenfolge wichtig — Farbe kommt zuletzt):**
1. Form wählen (Magnitude / Identität / Polarität / Einzelzahl / Zeitreihe?) → `choosing-a-form.md`
2. Farbe nach Funktion zuweisen (Kategorisch/Sequentiell/Divergierend/Status)
3. **Palette validieren** — `node scripts/validate_palette.js "<hex,...>" --mode light` → nie per Augenmaß
4. Mark-Specs anwenden (4px gerundete Enden, 2px Linien, 2px Flächen-Gap)
5. Hover-Ebene ergänzen (Crosshair+Tooltip, Hit-Targets >Mark)
6. Accessibility-Pass (Legende ≥2 Serien, Direkt-Labels ≤4, Dark Mode, Tabellen-View)
7. Rendern und ansehen — Layout/Label-Kollisionen visuell prüfen

**Validierungs-Kriterien (Farbpalette):**
- CVD Delta E ≥ 8 (OKLab ×100) — Minimum 6–8 nur mit sekundärer Kodierung
- Normal-Vision-Floor < 15 → hartes FAIL
- Contrast WARN → Pflicht: Labels oder Tabellen-View

**Unveränderliche Regeln:**
- Kategorische Farben in fester Reihenfolge, nie zyklisch
- Keine Dual-Achsen-Charts
- Farbe folgt der Entität, nicht dem Rang
- Text trägt nie die Serienfarbe — nur Tinte-Tokens
- Status-Farben (gut/Warnung/ernst/kritisch) niemals für Datenserien

**Design-System-Kopplung:** Methodik invariant; nur Ramps, Kategorienreihenfolge, Sequentiell-Farbton, Divergierend-Paar, Status-Palette, Oberflächen austauschen → `references/palette.md` ist die Referenzinstanz.

**Unterschied zu data:create-viz / data:data-visualization:** Dataviz ist die tiefste Designmethodik (Validator, Accessibility, Anti-Pattern-Katalog); die data-Skills sind ausführungsorientiert.
