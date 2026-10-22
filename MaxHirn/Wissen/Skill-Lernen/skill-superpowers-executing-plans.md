---
name: skill-superpowers-executing-plans
description: Trockenlauf des Skills superpowers:executing-plans — Plan aufgabenweise inline ausführen; TDD je Schritt, Ledger für Entscheidungen, eine finale Review am Ende.
metadata:
  type: reference
---

**Zweck:** Plan aus `writing-plans` aufgabenweise im selben Kontext ausführen (kein Subagent je Task). Jede Aufgabe durch TDD verifiziert, Abweichungen als "Rulings" im Ledger festgehalten.

**Wann nutzen:** Plan vorhanden, User wählt inline-Ausführung; oder kein Subagent-Tool verfügbar.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~6 Seiten. Dichtester superpowers-Skill — vollständiger Implementierungs-Workflow.

**Gelernt — Kern-Mechanik:**

**Setup (einmalig):**
1. Git-Worktree erstellen/prüfen (`using-git-worktrees`)
2. Workspace: `sdd-workspace PLAN_FILE` → `<repo>/.superpowers/sdd/<plan-basename>/`
3. Ledger: `progress.md` — erste Zeile = Plan-Pfad als Identität
4. Plan + Spec lesen, Todo je Aufgabe anlegen
5. `test-driven-development` laden (Pflicht vor Task 1)
6. Pre-flight-Scan: geteilte Schnittstellen zwischen Aufgaben prüfen

**Task-Schleife:**

| Schritt | Inhalt |
|---|---|
| 1. task-start | Brief lesen (nicht aus Erinnerung!), BASE-Commit notieren |
| 2. Schritte ausführen | TDD-Reihenfolge: Test schreiben → scheitern sehen → implementieren → bestehen |
| 3. Expected prüfen | Plan-Output mit realem Output vergleichen; Abweichung = Ruling |
| 4. Ruling-Mechanismus | Konflikt/Fehler im Plan → `Task N: Ruling: <was> — <warum> — <Kosten wenn falsch>` |
| 5. Completion Contract | Alle Tests liefen, Outputs verglichen, alle Abweichungen geleddgert |
| 6. task-done | Skript läuft Tests, schreibt bei Erfolg ins Ledger |

**Vier Stopps** (nur diese unterbrechen die Ausführung):
1. Irreversible/destruktive Operation
2. Sicherheitssensitive Aktion
3. Seiteneffekte außerhalb des Worktrees (merge, push zu shared branch, publish)
4. Plan so kaputt, dass jeder Weg vorwärts ein Raten ist

**Finale Review:**
- `review-package PLAN_FILE MERGE_BASE HEAD` ausführen
- Subagent auf fähigstem Modell dispatchen mit `requesting-code-review`
- Befunde re-graden (nach Wirkung, nicht nach Spec-Schweigen)
- Critical/Important → Ein Fix-Pass (je Fix: Test RED→GREEN + Suite grün)
- Minor → Ledger als "deferred", niemals in Fix-Pass

**Ledger-Format:**
```
# SDD ledger — plan: <pfad>
Task 1: complete (commits abc..def, tests: npm test → 8/8 pass)
Task 2: Ruling: install_hook → installHook — Tippfehler in Brief — Kosten: eine Umbenennung
Final: fixed hardcoded interval — test_interval RED→GREEN, suite 12/12
Final: minor (deferred): README fehlt Usage-Beispiel
```

**Abschluss:** Workspace löschen (git-History ist jetzt der Record), dann `finishing-a-development-branch`.

**Häufige Rationalisierungen → Wirklichkeit:**
- "Ich erinnere mich was Task N sagt" → Erinnerung ist Zusammenfassung. Brief hat genaue Werte.
- "Test wird schon passen" → Nie gesehen scheitern = beweist nichts
- "Minor auch schnell fixen" → Jeder Minor = Test+Fix+Suite, nicht bestellt
- "Eigenes Diff reicht" → Gleicher Autor, gleiche blinden Flecken

**Grenzen:** Erfordert vollständigen Plan aus `writing-plans`. Langer Plan → spätere Tasks laufen auf komprimiertem Kontext.
