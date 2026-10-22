---
name: skill-superpowers-using-superpowers
description: Trockenlauf des Skills superpowers:using-superpowers — Meta-Skill; relevante Skills VOR jeder Aktion laden; Rationalisierungen erkennen; Priorität Prozess-Skills vor Implementierungs-Skills; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Sicherstellen dass relevante Skills immer zuerst geladen werden, bevor irgendetwas getan wird.

**Wann nutzen:** Automatisch bei Sitzungsstart geladen (SessionStart-Hook). Definiert das Grundverhalten.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~1 Seite. Meta-Skill — steuert alle anderen.

**Gelernt — Kernregel:**

Skills VOR jeder Aktion laden — auch vor Rückfragen, Codebase-Erkundung, Dateilesen. Bei 1% Chance = laden.

**Priorität:**
1. Nutzer-Instruktionen (CLAUDE.md etc.) — oberste Priorität
2. Prozess-Skills (brainstorming, systematic-debugging) — zuerst
3. Implementierungs-Skills (frontend-design etc.) — danach

Beispiele:
- "Lass uns X bauen" → `superpowers:brainstorming` zuerst
- "Behebe diesen Bug" → `superpowers:systematic-debugging` zuerst

**Red Flags (alle = Rationalisierung, STOPP):**

| Gedanke | Wirklichkeit |
|---|---|
| "Nur eine einfache Frage" | Fragen sind Aufgaben — Skills prüfen |
| "Ich kenne diesen Skill" | Skills entwickeln sich — aktuelle Version laden |
| "Skill ist übertrieben" | Einfaches wird komplex |
| "Ich mache nur schnell X" | Skills zuerst |

**Platform-Adaptation:** Claude Code → `references/claude-code-tools.md` im Skill-Verzeichnis.

**Grenzen:** Gilt nicht für Subagenten (SUBAGENT-STOP-Marker im Skill). Nutzer-Instruktionen können Skills überschreiben.
