---
name: skill-adaptive-agent-skill-review
description: Trockenlauf des Skills adaptive-agent:skill-review - prüft Skills auf Veraltung und Lücken, ändert nichts.
metadata:
  type: reference
---

**Zweck:** Periodische Pflege aller Skills: Inventur, Abgleich mit Gedächtnis-Notizen, Prüfung auf veraltete Pfade und Befehle, Suche nach wiederkehrenden Abläufen ohne Skill, Zusammenlegung von Dubletten, Bericht als Tabelle. Ändert Skills und committet.

**Wann nutzen:** Nach einer Serie von Aufgaben über mehrere Skills, bei veralteten Schritten, etwa alle zwei Wochen.

**Lauf:** 2026-10-21, trockenlauf, Aufgabe: `skill-lernen/SKILL.md` auf Klarheit, Lücken und Widersprüche prüfen. Nichts geändert, nichts committet.

**Ergebnis:**
- Der Skill ist für eine Inventur über alle Skills gebaut. Die Pflegeaufgabe selbst (Schritte 1 bis 5) lief nicht, nur das Lesen der Zieldatei.
- Der Skill passt schlecht zu einem Trockenlauf: Er verlangt Änderungen und einen Commit. Die Trockenlauf-Regel aus `skill-lernen` ist deshalb nötig, damit er nicht schreibt.

**Gelernt:** Der Pflege-Skill nimmt an, dass Skills Dateien und Git-Verlauf haben. Die Plugin-Skills liegen aber im Plugin-Cache, nicht in einem Repo. Der Commit-Schritt greift dort nicht.

**Grenzen:** Der Lauf war eine Lese- und Bewertungsübung. Die Ergebnisse von `skill-lernen` wurden nicht gegen den Stand des Repos geprüft.
