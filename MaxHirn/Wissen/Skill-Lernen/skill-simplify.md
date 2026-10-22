---
name: skill-simplify
description: Trockenlauf des Skills simplify — Code-Qualitäts-Review (Reuse, Simplification, Efficiency, Altitude) per 4 parallele Agents, dann Fixes anwenden; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Kein Bug-Hunt, sondern Code-Qualität: Reuse, Simplification, Efficiency, Altitude — dann Fixes anwenden.

**Lauf:** 2026-10-22, trockenlauf.

**Aufruf:** `/simplify` oder Skill `simplify` — analysiert den aktuellen Diff.

**Ablauf:**
1. **Phase 0:** `git diff @{upstream}...HEAD` (ggf. + `git diff HEAD` für uncommittete Änderungen)
2. **Phase 1:** 4 parallele Review-Agents starten:
   - **Reuse** — re-implementiert etwas, das schon existiert?
   - **Simplification** — redundanter State, Copy-Paste, tiefes Nesting, toter Code?
   - **Efficiency** — redundante Berechnungen, sequentielle unabhängige I/O, Closures die große Scopes halten?
   - **Altitude** — fixt es die Wurzel oder nur ein Symptom? Spezialfälle auf gemeinsamer Infrastruktur sind ein Warnsignal.
3. **Phase 2:** Befunde deduplizieren, Fixes direkt anwenden. Skips begründen.

**Wann überspringen:** Fix würde beabsichtigtes Verhalten ändern; Änderungen weit außerhalb des Diffs nötig; False Positive.

**Unterschied zu /code-review:** simplify = Qualität; code-review = Korrektheit.
