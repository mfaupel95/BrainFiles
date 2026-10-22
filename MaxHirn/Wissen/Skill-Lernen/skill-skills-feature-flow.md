---
name: skill-skills-feature-flow
description: Trockenlauf des Skills skills:feature-flow — vollständiger Feature-Entwicklungszyklus von Scope über Code/Review bis Commit und Dokumentation; 9 Schritte mit Checkpoints.
metadata:
  type: reference
---

**Zweck:** Einen Feature-Entwicklungszyklus von Anfang bis Ende strukturiert durchführen — Scope → Plan → Execute → Review → Commit → Dokumentation.

**Wann nutzen:** `/feature-flow <Beschreibung>` für neues Feature; `/feature-flow <step>` um direkt in einen Schritt einzusteigen. Oder automatisch wenn ein Feature-Auftrag ankommt.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~5 Seiten. Vollständiger Workflow-Guide mit 9 klar definierten Schritten.

**Gelernt — Schritte:**

| Step | Name | Kernaufgabe |
|---|---|---|
| 1 | Scope & Context | Thema klären, Dateien identifizieren |
| 2 | Plan | Phasen, Komponenten, State-Entscheidungen |
| 3 | Plan Confirm | Offene Punkte klären (AskUserQuestion) |
| 4 | Execute | Code schreiben, 4-Prinzipien-Monitor |
| 5 | Review | Selbstreview + Human-Review-Guide in einem Dokument |
| 6 | Iterate | Feedback einarbeiten, Fixes |
| 7 | Commit Plan | Commits nach Bedeutungseinheiten aufteilen |
| 8 | Commit Apply | `git add <files>` → `git commit` pro Einheit |
| 9 | Document | Patch Note / Research Note / Feature Spec (alle optional) |

**Kern-Muster:**
- Jeder Schritt endet mit `⛔ Weiter oder verfeinern?` — Nutzer steuert das Tempo
- Step 5 Review: Selbstreview inline in Human-Guide, keine separate Tabelle
- Dokumentation (Step 9) entspricht dem `worklog`-Skill — nutzt `docs/_inbox/{patch,research,spec,scratch}/`
- Verknüpft mit: `daily` (Eingang), `worklog` (Ausgang), `feature-flow-superpowers` (superpowers-Variante)

**4 Prinzipien (Karpathy) für Execute/Review:**
1. Think Before Coding — Annahmen benennen
2. Simplicity First — Nur angefordertes Minimum
3. Surgical Changes — Jede Zeile muss mit Auftrag verbunden sein
4. Goal-Driven — Kein "Fertig" ohne Verifikation

**Anti-Pattern-Checkliste** (13 Punkte im Skill): single-use Helfer, Cross-cutting-Changes, prop→state via useEffect, TODO-Flut, unabgestimmte Konventionen

**Grenzen:** Guide, kein Automat — Checkpoints sind explizit, der Nutzer setzt das Tempo.
