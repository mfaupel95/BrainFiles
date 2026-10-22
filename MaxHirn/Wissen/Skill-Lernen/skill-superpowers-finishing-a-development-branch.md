---
name: skill-superpowers-finishing-a-development-branch
description: Trockenlauf des Skills superpowers:finishing-a-development-branch — nach grüner Test-Suite Branch-Umgebung erkennen, Optionen vorlegen, gewählte Option ausführen, Worktree bereinigen.
metadata:
  type: reference
---

**Zweck:** Entwicklungs-Branch sauber abschließen: Tests laufen lassen, Merge-/PR-/Keep-Entscheidung dem User überlassen, Worktree bereinigen.

**Wann nutzen:** Am Ende von `executing-plans` oder nach jeder abgeschlossenen Implementierung auf einem Feature-Branch.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~4 Seiten. Klarer 6-Schritt-Ablauf mit Rationalierungsfallen-Tabelle.

**Gelernt — 6 Schritte:**

| Schritt | Inhalt |
|---|---|
| 1. Tests | Volle Suite laufen — grün = weiter, rot = Stopp + Fehlerbericht |
| 2. Umgebung erkennen | `GIT_DIR` vs `GIT_COMMON`: Normal-Repo / Named-Branch-Worktree / Detached-HEAD |
| 3. Basis-Branch bestimmen | Aus Plan, Gespräch oder Branch-Upstream; bei Unklarheit fragen |
| 4. Menü vorlegen | Normal: 3 Optionen; Detached HEAD: 2 Optionen — exakt so wie im Skill |
| 5. Option ausführen | Merge lokal / PR erstellen / so lassen |
| 6. Worktree bereinigen | Nur für Option 1 und explizites Verwerfen |

**Menü (Normal-Repo):**
```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
```

**Cleanup-Logik:**
- `GIT_DIR == GIT_COMMON` → kein Worktree, nichts zu bereinigen
- Worktree unter `.worktrees/` oder `worktrees/` → superpowers-eigentümer → `git worktree remove` + `prune`
- Removal verweigert (uncommitted files) → User fragen, niemals `--force`
- Anderer Pfad → Host-Umgebung besitzt den Workspace → stehen lassen

**Verwerfen:** Nur auf explizite Anfrage. Erfordert das Wort `discard` als Bestätigung — "yeah, get rid of it" zählt nicht.

**Häufige Rationalisierungen:**
- "Tests haben vorhin gepasst" → Suite auf dem Baum laufen, der integriert wird
- "Sie wollen es offensichtlich gemergt haben" → Menü vorlegen, warten
- "PR ist oben, Worktree ist Müll" → Worktree bleibt bis zur Landung des PRs
- "Merged-Result schlägt fehl — ist wahrscheinlich flaky" → Stopp, kein Push, untersuchen

**Grenzen:** Erfordert grüne Tests vor der Menüanzeige. Verwerfen nur auf explizites `discard`-Keyword.
