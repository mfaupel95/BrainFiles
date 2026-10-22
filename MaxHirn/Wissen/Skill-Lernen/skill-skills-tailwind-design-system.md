---
name: skill-skills-tailwind-design-system
description: Trockenlauf des Skills skills:tailwind-design-system — Design System für Tailwind CSS + Next.js; Phase 0–6 von Design-Prompting bis laufendem Audit.
metadata:
  type: reference
---

**Zweck:** Design-System-Aufbau und -Pflege für Tailwind CSS + Next.js Projekte — von Null bis fortlaufendem Compliance-Check.

**Wann nutzen:** Bei Neuprojekten, Refactoring bestehender UI, oder regelmäßigen Design-System-Audits.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~4 Seiten. Vollständiger Phase-Guide mit Entscheidungspunkten.

**Gelernt — 6 Phasen:**

| Phase | Name | Inhalt |
|---|---|---|
| 0 | Design Prompting | Prompt für KI-Design-Tool erstellen (nur Neu-Projekte) |
| 1 | Style Audit | Alle Klassen scannen: Farben, Typo, Abstände, Radien, Schatten |
| 2 | Color Tokens | hex → Tailwind-Palette → semantische Token in `globals.css` |
| 3 | Typography Tokens | Nummerierungs-Schema (hero01 > heading01 > body01 > caption01) |
| 4 | UI Components | Wiederholte Muster (≥3x) → Shared Components |
| 5 | Migration | Token einführen, Klassen ersetzen, nach jedem Schritt Build prüfen |
| 6 | Review/Audit | Fortlaufend: raw Tailwind-Farben, arbitrary values, neue Kandidaten |

**Kern-Entscheidungen (mit User abstimmen):**
- Color-Naming: `brand-hover` vs `brand-accent`?
- Typo-Nummerierung: 01=größte oder 01=kleinste?
- Background-Naming: `background-*` vs `base-*` vs `canvas-*`?
- Nur semantische Token oder auch Komponenten-Token?

**Tailwind v4-Besonderheiten:**
- Font-Size-Namespace: `--text-*` (NICHT `--font-size-*`)
- `extendTailwindMerge` nötig wenn Custom-Font-Size-Token mit `text-*`-Prefix → sonst falsches Merging
- Kein `var(--text-6xl)` in Werten — raw Werte direkt

**className-Formatierung (>6 Klassen):**
```tsx
className={['layout', 'size', 'visual', 'typo', 'state'].join(' ')}
```
`cn()` nur bei bedingten Klassen oder externem className-Merge.

**Komponenten-Kandidaten:** SectionLabel, SectionTitle, FormInput, FormTextarea, Button, FormCheckbox, Card, Accordion, ChatBubble, TabBar, FloatingIndicator — alle nach `app/_components/ui/`.

**Grenzen:** Fokus auf Tailwind v4 + Next.js. Phase 0 nur für Projekte ohne UI.
