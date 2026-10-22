---
name: skill-workflow-authoring
description: Trockenlauf des Skills workflow-authoring — Workflow-Skript-API (pipeline/parallel/agent/phase/log), Qualitätsmuster (adversarial-verify, judge-panel, loop-until-dry), Resume; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Workflow-Skript authoren — multi-agent Orchestrierung mit deterministischer Kontrollstruktur.

**Lauf:** 2026-10-22, trockenlauf.

**Wann nutzen:** Umfangreiche parallele Arbeit (umfangreiche Suche, Migrationen, Review-Dimensionen), die ein einzelner Kontext nicht halten kann — nicht für einfache Aufgaben.

**Pflicht-Prefix:**
```js
export const meta = {
  name: 'workflow-name',         // pure literal
  description: 'one-line',
  phases: [{ title: 'Phase1' }], // titels exact = phase()-Aufrufe
}
```

**Hauptfunktionen:**
| Funktion | Bedeutung |
|---|---|
| `pipeline(items, s1, s2, ...)` | **Default**: kein Barrier zwischen Stages; A in Stage 3 während B in Stage 1 |
| `parallel(thunks)` | **Barrier**: wartet auf alle, bevor return; nur wenn cross-item context nötig |
| `agent(prompt, opts?)` | Subagent spawnen; ohne schema → Text; mit schema → validiertes Objekt |
| `phase(title)` | Neue Phase-Gruppe für Fortschrittsanzeige |
| `log(message)` | Narrator-Zeile über der Fortschrittsanzeige |

**`agent()`-Optionen:**
- `label`: Anzeigename
- `schema`: JSON Schema → StructuredOutput-Tool erzwungen
- `phase`: explizit Phase-Gruppe zuweisen (in pipeline/parallel wichtig)
- `effort`: 'low'/'medium'/'high'/'xhigh'/'max' — Modell-Reasoning
- `isolation: 'worktree'`: eigener Git-Worktree — teuer, nur wenn parallele Dateiänderungen
- `model`: Modell-Override — weglassen wenn unsicher

**Barrier nur wenn:**
1. Cross-item Dedup über alle Stage-N-1-Ergebnisse nötig
2. Early-Exit bei 0 Funden (Skip teurer Stage)
3. Stage N's Prompt referenziert "the other findings"

**Smell-Test:** `const a = await parallel(…); const b = transform(a); const c = await parallel(b.map(…))` → transform braucht keinen Barrier → pipeline mit transform inside stage!

**Qualitätsmuster:**
- **Adversarial Verify:** 3 unabhängige Skeptiker pro Fund, jeder soll widerlegen. Survives wenn ≥2 nicht widerlegen.
- **Judge Panel:** N unabhängige Ansätze (MVP-first, risk-first, ...) → parallel bewerten → Synthese aus Gewinner.
- **Loop-until-dry:** K konsekutive Runden ohne neue Funde → Stop. `seen`-Set (nicht `confirmed`!) für Dedup.
- **Multi-modal Sweep:** Parallel-Agents jeweils blind mit anderem Such-Winkel.
- **Completeness Critic:** Letzte Stage fragt "was fehlt?" → neue Runde.

**Verboten in Scripts:** `Date.now()`, `Math.random()`, `new Date()` — brechen Resume! Timestamps via `args` reinreichen.

**Resume:** `Workflow({scriptPath, resumeFromRunId})` — gleiche (prompt, opts)-Paare werden gecacht. Vor Diagnose eines leeren Ergebnisses: `<transcriptDir>/journal.jsonl` lesen.

**Limits:** 16 parallele Agents (CPU-abhängig), 1000 Agents total, 4096 Items pro parallel()/pipeline().

**`budget`-API:** `budget.total`, `budget.spent()`, `budget.remaining()` — für Loop-until-budget-Pattern.
