---
name: skill-agent-protocols-code-review-and-quality
description: Strukturierter Code-Review entlang fünf Achsen (Korrektheit, Lesbarkeit, Architektur, Sicherheit, Performance) mit Schwere-Labeln für Befunde.
metadata:
  type: reference
---

**Zweck:** Gibt einen vollständigen Review-Prozess vor: Kontext verstehen → Tests zuerst lesen → Implementierung entlang fünf Achsen prüfen → Befunde mit Schwere labeln (Critical/Nit/Optional/FYI) → Toten Code identifizieren.

**Wann nutzen:** Vor jedem Merge, nach KI-generiertem Code, nach Bugfixes, beim Refactoring.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht. Kein PR vorhanden.

**Ergebnis:** Skill vollständig geladen. Enthält fünf-Achsen-Checkliste, PR-Größenregeln (~100 Zeilen ideal, >1000 aufteilen), Splitting-Strategien, Schwere-Label-System, Multi-Modell-Review-Muster und Hinweise zu totem Code. Kernregel: Approve wenn die Änderung den Gesamtzustand verbessert, auch wenn nicht perfekt.

**Gelernt:** Schwere-Label-System (Critical/Nit/Optional/FYI) ist direkt auf die eigenen Code-Reviews mit `/code-review` übertragbar. Multi-Modell-Pattern (Modell A schreibt, Modell B reviewed) entspricht dem Zusammenspiel Claude Code + Hermes-Bot.

**Grenzen:** PR-Größenregeln und GitHub-Review-Prozess setzen ein Git-Hosting-Workflow voraus. Im lokalen Einzelarbeitsbaum greift stattdessen der `/code-review`-Skill direkt.
