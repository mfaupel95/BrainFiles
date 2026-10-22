---
name: skill-superpowers-subagent-driven-development
description: Trockenlauf des Skills superpowers:subagent-driven-development — Plan per frischem Implementer-Subagenten je Task, Task-Review nach jedem, finales Branch-Review am Ende; Ledger überlebt Komprimierung.
metadata:
  type: reference
---

**Zweck:** Plan mit maximaler Qualitätssicherung ausführen: ein frischer Subagent je Task + Task-Review + finales Branch-Review. Teurer als `executing-plans`, besser bei langen Plänen oder wenn jede Task ein Review-Gate braucht.

**Wann nutzen:** Plan vorhanden, Tasks weitgehend unabhängig, Partner will Subagenten; sonst `executing-plans`.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~15 Seiten. Detailliertester superpowers-Skill — vollständige Orchestrierungs-Anleitung.

**Gelernt — Gesamt-Ablauf:**

**Setup:**
1. Git-Worktree prüfen/erstellen (`using-git-worktrees`)
2. `sdd-workspace PLAN_FILE` → Workspace + Ledger
3. Plan + Spec lesen, Todos anlegen
4. Pre-flight-Scan: Konflikte zwischen Tasks

**Task-Schleife:**

| Schritt | Inhalt |
|---|---|
| 1. Implementer dispatchen | `task-brief` ausführen; frischer Subagent mit Brief + Report-Pfad |
| 2. Report verarbeiten | DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED |
| 3. Task-Review | `review-package` + Task-Reviewer-Subagent; Spec + Qualität beide prüfen |
| 4. Fix-Loop | Max. 5 Runden; R1-3 = selber Implementer; R4-5 = frischer auf besserem Modell |
| 5. Task abschließen | Ledger-Zeile, Todo complete |

**Fix-Loop — Breaker bei Runde 5:**
- Reviewer falsch → parken mit Ruling
- Real, nichts baut drauf → parken mit Ruling
- Real, load-bearing → Ruling + in nächste Task-Dispatch tragen; Stopp nur wenn kein Weg vorwärts

**Modell-Wahl:**
- Mechanische 1-2-Datei-Tasks → billigstes Modell
- Integration/Urteil → Standard
- Architektur, finales Review → fähigstes Modell
- Fix-Loop R4-5 → eine Stufe höher als feststeckender Implementer

**Wichtige Regeln:**
- Keine parallelen Implementer-Subagenten (Konflikte)
- Kleine gleichartige Tasks batchen (ein Subagent, ein Diff)
- Reviewer nie mit vorurteilenden Direktiven dispatchen ("do not flag X")
- Controller fixiert nie selbst — Kontext bleibt sauber
- Ledger = Überlebender der Komprimierung; Todos = Live-View

**Finales Review:**
- `review-package PLAN_FILE MERGE_BASE HEAD`
- Fähigstes Modell; zeigt auf Ledger-Deferred-Minors
- Nur EIN Fix-Subagent für alle Befunde, dann EIN Scoped-Re-Review

**Abschluss:** Alle Rulings aus dem Ledger in Finalnachricht sammeln ("Rulings I made"), dann Workspace löschen, `finishing-a-development-branch`.

**Grenzen:** Teurer als `executing-plans` (frischer Kontext je Task + je Review). Bei extrem engem Budget `executing-plans` vorziehen.
