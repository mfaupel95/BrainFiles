---
name: skill-skills-feature-flow-superpowers
description: Trockenlauf des Skills skills:feature-flow-superpowers — feature-flow + explizite superpowers-Skill-Aufrufe je Schritt; TDD-first, verification-before-completion als Pflicht.
metadata:
  type: reference
---

**Zweck:** Superpowers-integrierter Feature-Zyklus. Identisch zu `skills:feature-flow`, aber jeder Schritt verweist auf konkrete superpowers-Skills.

**Wann nutzen:** Wenn superpowers-Plugin installiert ist und man den vollständigen Workflow mit expliziter Methodik durchführen will. Sonst `skills:feature-flow`.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~5 Seiten. Orchestrator für alle superpowers-Skills im Feature-Kontext.

**Gelernt — Kernunterschiede zu feature-flow:**

| Aspekt | feature-flow | feature-flow-superpowers |
|---|---|---|
| Design-Entscheidungen | 4 Karpathy-Prinzipien | 4 Prinzipien (bleibt) |
| Implementierung | Freie Wahl | TDD-first (test-driven-development) |
| Verifikation | typecheck/lint | verification-before-completion |
| Plan schreiben | frei | writing-plans |
| Review | inline | requesting-code-review + verification |
| Feedback | inline | receiving-code-review |
| Branch abschließen | git commit | finishing-a-development-branch |

**Superpowers-Zuordnung je Schritt:**
- Step 1 → `brainstorming`
- Step 2 → `writing-plans`
- Step 4 → `executing-plans`, `test-driven-development`, `subagent-driven-development`, `dispatching-parallel-agents`, `using-git-worktrees`, `systematic-debugging`
- Step 5 → `requesting-code-review`, `verification-before-completion`
- Step 6 → `receiving-code-review`
- Step 8 → `finishing-a-development-branch`
- Step 9 → `writing-skills` (wenn Research → Skill wird)

**Konflikt-Auflösung 4-Prinzipien vs. TDD:**
- "Wie bauen?" → 4 Prinzipien (Simplicity-first)
- "Wie schreiben?" → TDD (Test-first)
- "Fertig?" → verification-before-completion (Evidence-first)

**Grenzen:** Setzt superpowers-Plugin voraus. Ohne es → pure `feature-flow` nutzen. Superpowers-Aufrufe sind Empfehlung, nicht Zwang — bei Mismatch überspringen + begründen.
