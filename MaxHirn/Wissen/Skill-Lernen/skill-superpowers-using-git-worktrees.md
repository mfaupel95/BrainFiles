---
name: skill-superpowers-using-git-worktrees
description: Trockenlauf des Skills superpowers:using-git-worktrees — isolierten Workspace erstellen; zuerst natives Tool (EnterWorktree), dann git-Fallback; Submodul-Guard; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Vor jeder Implementierung isolierten Git-Worktree einrichten, damit `master` nicht direkt beschrieben wird.

**Wann nutzen:** Start von SDD, executing-plans, finishing-a-development-branch — immer wenn Implementierung beginnt.

**Lauf:** 2026-10-23, trockenlauf plus Praxisabgleich, Aufgabe: letzte Worktree-Übergabe mit PR-Abschluss und Bereinigung abgleichen.

**Ergebnis:** Der vorherige Lauf war ein Trockenlauf; der Abgleich mit der realen Übergabe ergänzt die Isolation-Regeln um eine Abschlussprüfung: Status und Diff jedes Worktrees frisch lesen, nur nachweislich abgeschlossene PR-Arbeit entfernen und fremde/uncommittete Pfade liegen lassen. Ein sauberer Hauptzweig allein beweist nicht, dass alle Arbeit übernommen wurde.

**Gelernt — Ablauf:**

**Schritt 0: Isolation erkennen**
```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
```
- `GIT_DIR != GIT_COMMON` → bereits im Worktree → zu Schritt 2 springen
- Submodul-Guard: `git rev-parse --show-superproject-working-tree` — gibt Pfad zurück = Submodul = normales Repo behandeln

**Schritt 1a: Natives Tool (bevorzugt)**
- `EnterWorktree` / `/worktree` / `--worktree` vorhanden? → nutzen, kein manuelles `git worktree add`
- Natives Tool managt Verzeichnis, Branch, Cleanup — Bypass erzeugt Phantomzustand

**Schritt 1b: Git-Fallback (nur wenn kein natives Tool)**

Priorität für Verzeichnis:
1. Nutzer-Instruktionen (immer Vorrang)
2. `.worktrees/` vorhanden → nutzen
3. `worktrees/` vorhanden → nutzen
4. Keines → `.worktrees/` anlegen

Safety: `git check-ignore -q .worktrees` — nicht ignoriert → erst in .gitignore eintragen + committen

```bash
git worktree add "$path" -b "$BRANCH_NAME"
```

Sandbox-Fehler → vor Ort arbeiten, Partner informieren.

**Schritt 2: Projekt-Setup** (npm install / cargo build / pip install je nach Projekttyp)

**Schritt 3: Baseline-Tests** — schlagen fehl → melden + fragen ob fortfahren

**Wichtige Regeln:**
- CLAUDE.md-Einstellung: `git worktree add .worktrees/<name> -b <agent>/<thema> master` (Zweig-Regel)
- Nie `git worktree add` wenn natives Tool verfügbar
- Phantomzustand (nicht im Harness sichtbar) ist das häufigste Problem

**Grenzen:** Sandbox kann `git worktree add` blockieren → Fallback vor Ort arbeiten.

**Praxislehre:** Vor Merge/Push jeden lokalen Worktree gegen PR, Branch und Remote vergleichen. Nach Merge erneut `git worktree list`, Branch-Status und uncommittierte Dateien prüfen; nur den erledigten eigenen Worktree entfernen. Gesicherte Zwischenstands-Refs und fremde Ordner nicht als eigene Altlast behandeln.
