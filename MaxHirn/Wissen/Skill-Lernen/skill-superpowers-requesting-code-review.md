---
name: skill-superpowers-requesting-code-review
description: Trockenlauf des Skills superpowers:requesting-code-review — Subagent für Code-Review dispatchen; präziser Kontext statt Session-History; Critical/Important vor Weiterarbeit beheben.
metadata:
  type: reference
---

**Zweck:** Code-Review-Subagenten mit präzisem Kontext dispatchen, um Probleme zu finden bevor sie eskalieren.

**Wann nutzen:** Nach jeder Task in SDD, nach Feature-Fertigstellung, vor Merge; optional beim Feststecken oder vor Refactoring.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~2 Seiten. Kompakter 3-Schritt-Prozess.

**Gelernt — Ablauf:**

**1. Git-SHAs ermitteln:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # oder: git merge-base origin/main HEAD
HEAD_SHA=$(git rev-parse HEAD)
```

**2. `general-purpose`-Subagent dispatchen** mit Template aus `code-reviewer.md`:
- `{DESCRIPTION}` — kurze Zusammenfassung was gebaut wurde
- `{PLAN_OR_REQUIREMENTS}` — was es tun soll
- `{BASE_SHA}` / `{HEAD_SHA}` — Diff-Grenzen

**3. Feedback verarbeiten:**
- Critical → sofort beheben
- Important → vor Weiterarbeit beheben
- Minor → für später notieren
- Bei falschem Feedback: technisch widersprechen

**Kern-Prinzip:** Reviewer-Subagent bekommt präzis zugeschnittenen Kontext, nie die Session-History. Diff + Bewertung leben im Kontext des Subagenten; nur Befunde kommen zurück.

**Rationalisierungen → Wirklichkeit:**
- "Ich reviewe das Diff selbst" → Koordinator verbrennt Kontext; Subagent dispatchen
- "Reviewer braucht meine Session-History" → Präziser Kontext reicht; History ablenkt

**Grenzen:** Erfordert Subagenten-Tool. Template in `code-reviewer.md` im selben Skill-Verzeichnis.
