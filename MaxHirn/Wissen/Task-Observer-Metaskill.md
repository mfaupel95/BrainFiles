---
id: 20260917-task-observer-metaskill
title: 'Task-Observer — Meta-Skill zur Skill-Selbstverbesserung (Bewertung)'
tags: [ki-agenten, betrieb]
created: 2026-09-17
updated: 2026-09-17
related:
  - id: 20260902-skill-bibliothek
summary: 'Fremdes Claude-Meta-Skill "One Skill to Rule Them All" (rebelytics, CC BY 4.0): beobachtet Sitzungen, protokolliert Verbesserungs-/Neuvorschläge für Skills in einem Observation-Log, mit Wochenrunde. Baut auf Claude-eigenen Konzepten auf (<available_skills>, skill-creator) — für Hermes nicht 1:1 übertragbar. Adoption ist offene Entscheidung, siehe Kanban-Task.'
---

# Task-Observer — Meta-Skill zur Skill-Selbstverbesserung

Max hat am 17.09.2026 vier Dateien angehängt (`README-2.md`, `SKILL.md`,
`USER-GUIDE.md`) des Projekts **"One Skill to Rule Them All" / task-observer**
von Eoghan Henn ([rebelytics.com](https://rebelytics.com), Repo
[github.com/rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all),
Lizenz CC BY 4.0). Diese Notiz hält fest, was es ist und warum die
Übernahme in Hermes eine offene Entscheidung ist statt eine Selbstläufer-Installation.

## Was es tut

Ein Meta-Skill, der während jeder Sitzung mitläuft und drei Dinge sucht:

1. **Neue Skill-Kandidaten** — wiederkehrende Arbeitsmuster, die noch kein
   Skill abdeckt.
2. **Verbesserungen an bestehenden Skills** — Korrekturen des Nutzers,
   verletzte Regeln, bessere Workflows als die dokumentierten.
3. **Eigene blinde Flecken** — der Beobachter beobachtet auch sich selbst.

Ergebnis ist ein **Observation-Log** (`skill-observations/observation-log/`,
ein Markdown-File pro Beobachtung mit YAML-Frontmatter: `status`, `skill`,
`type`, `siblings_checked` u. a.), plus eine **Wochenrunde**, die offene
Beobachtungen gegen die ganze Skill-Bibliothek gegenprüft und Änderungen
als Entwürfe in `skill-updates/` ablegt — nie automatisch installiert.
Cross-cutting Principles (Regeln, die für mehrere Skills gelten) landen in
einer separaten Datei. Autor berichtet 7 Monate Eigenbetrieb, 1300+
Beobachtungen über 75 Skills.

## Warum nicht einfach installieren

**Baut auf Claude-spezifischen Mechanismen auf**, die es in Hermes so nicht
gibt: `<available_skills>`-Block, der eingebaute `skill-creator`-Skill,
Cowork-Shared-Folder mit `request_cowork_directory`. Der Autor selbst stuft
andere Plattformen als „potentially compatible with caveats" ein und nennt
Hermes nur als Anwenderbericht, nicht als getestete Zielumgebung.

**Token-Kosten widersprechen der laufenden Linie in diesem System.** Die
Hauptdatei `SKILL.md` allein umfasst **11.076 Tokens** (immer geladen, wenn
der Skill aktiv ist) plus sieben Referenzdateien on-demand. Am 11.09.2026
wurde die Hauptbibliothek gezielt von 127 auf 48 Skills gekürzt und die
OKX-Skill-Beschreibungen von 375–1000 auf ~120 Zeichen gekürzt, um die
Dauerlast von ~4.380 auf ~1.248 Tokens je Anfrage zu senken (siehe
Memory-Eintrag „SKILL-AUSMISTEN"). Ein Meta-Skill, der laut eigener
Aktivierungsregel **vor jedem einzelnen Tool-Aufruf** greifen soll
(„invoke this skill before the FIRST tool call of any session ... however
simple the opener looks"), liefe dem direkt entgegen.

**Hermes hat bereits einen Curator-Mechanismus** (`hermes curator usage`,
`hermes curator list-archived`, `hermes curator restore`,
Selbstverbesserungs-Cron `skill-usage-report` montags 09:30) — ein anderes,
leichteres Werkzeug für einen ähnlichen Zweck (welche Skills laufen leer,
welche werden oft gebraucht), aber ohne das Beobachtungs-/Vorschlagsformat
des Task-Observers.

## Was übertragbar wäre, ohne den ganzen Meta-Skill zu installieren

- Das **Prinzip** (Beobachtungen aus echter Arbeit sammeln statt Skills nur
  reaktiv zu pflegen) lässt sich als eigener, schlanker Haus-Skill nachbauen
  — mit Hermes-Aktivierung über `skill_manage`/`SOUL.md` statt
  `<available_skills>`-Matching.
- Das **Dateiformat** (ein Markdown pro Beobachtung, Frontmatter mit
  `status`/`skill`/`resolved`) ist plattformneutral und günstig zu
  übernehmen, auch ohne den 11k-Token-Aktivierungsblock.

## Entscheidung

Noch offen — siehe Kanban-Task „Task-Observer-Meta-Skill bewerten". Bis zur
Entscheidung: **nicht installiert**, diese Notiz ist reine
Wissenserfassung des Attachments.
