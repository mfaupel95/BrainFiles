---
name: skill-agent-protocols-git-workflow-and-versioning
description: Git als Sicherheitsnetz — Trunk-Based Development, atomare Commits, Change-Summary-Muster, Worktrees für parallele Agenten.
metadata:
  type: reference
---

**Zweck:** Vollständiges Git-Workflow-Protokoll: Trunk-Based Development (main immer deploybar, Feature-Branches max. 1–3 Tage), fünf Commit-Prinzipien (early/often, atomic, descriptive, separate concerns, ~100 Zeilen), Worktrees für parallele Agenten, Pre-Commit-Hygiene.

**Wann nutzen:** Immer — jede Codeänderung läuft über Git.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. Besonders wertvoll: Change-Summary-Muster mit "DIDN'T TOUCH"-Abschnitt zeigt Scope-Disziplin explizit. Worktree-Workflow für parallele Agenten deckt sich mit der BrainFiles-Regel (`.worktrees/<name>`). Commit-Typen (feat/fix/refactor/test/docs/chore) als Konvention.

**Gelernt:** Das "DIDN'T TOUCH"-Muster aus dem Skill ist direkt auf BrainFiles-Sitzungen anwendbar — beim nächsten Commit mit mehreren Bereichen explizit melden was absichtlich nicht angefasst wurde. DORA-Forschung als Quelle für Trunk-Based Development genannt — kurze Zweige (1–3 Tage) sind kein Stil, sondern gemessene Praxis.

**Grenzen:** Setzt GitHub-Flow voraus. BrainFiles nutzt `maks_master` statt `main`, und die Mehrfachsitzungs-Regeln (Fremdarbeit-Einziehen, kein Stash) gehen über diesen Skill hinaus — sie stehen in der Wurzel-CLAUDE.md.
