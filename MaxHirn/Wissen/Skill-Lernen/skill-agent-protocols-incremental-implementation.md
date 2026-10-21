---
name: skill-agent-protocols-incremental-implementation
description: In dünnen vertikalen Scheiben bauen — Implement→Test→Verify→Commit, Scope-Disziplin, Feature-Flags für unfertige Arbeit.
metadata:
  type: reference
---

**Zweck:** Execution-Disziplin für große Features: Increment-Zyklus (Implement→Test→Verify→Commit), drei Slicing-Strategien (Vertikal/Contract-First/Risk-First), fünf Implementation-Regeln (Simplicity First, Scope Discipline, One Thing at a Time, Compilable, Rollback-Friendly).

**Wann nutzen:** Jede Mehrfach-Datei-Änderung, neue Features aus Task-Breakdown, Refactoring, sobald man versucht ist >100 Zeilen vor dem nächsten Test zu schreiben.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. Besonders wertvoll: "NOTICED BUT NOT TOUCHING"-Muster als explizite Scope-Disziplin — nennt was bewusst nicht angefasst wurde. Risk-First-Slicing für unsichere Teile zuerst direkt auf Handels-Features anwendbar.

**Gelernt:** "Drei ähnliche Zeilen sind besser als eine vorschnelle Abstraktion" — konkrete Regel gegen Over-Engineering. Rule 0.5 (Scope Discipline: nur was der Task verlangt) ist die Implementierungs-Entsprechung zur BrainFiles-Bereichsregel. Feature-Flags für unfertige Merges decken sich mit dem BrainFiles-Zweigsystem (Merge nur nach PR-Abschluss).

**Grenzen:** Commit-Syntax und npm-Befehle sind Node-spezifisch. Für Python/PowerShell gilt dasselbe Prinzip, nur andere Testbefehle.
