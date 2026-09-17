---
id: 20260917-beobachtungslog
title: 'Beobachtungslog — Skill-Verbesserung aus echter Arbeit'
tags: [betrieb, ki-agenten]
created: 2026-09-17
updated: 2026-09-17
related:
  - id: 20260917-task-observer-metaskill
  - id: 20260902-skill-bibliothek
summary: 'Verzeichnis mit einer Markdown-Datei je beobachtetem Skill-Verbesserungsbedarf, gepflegt vom Skill beobachtungslog — schlanker Eigenbau statt des fremden Task-Observer-Meta-Skills.'
---

# Beobachtungslog

Dieses Verzeichnis (`log/`) enthält eine Markdown-Datei je Beobachtung —
eine Korrektur, eine Lücke oder ein wiederkehrendes Muster, das ein
bestehender oder fehlender Skill nicht abdeckt. Gepflegt vom Skill
[[beobachtungslog]] (`Agenten/Hermes/skills/brainfiles/beobachtungslog/`).

**Entstehung:** Bewertung des fremden Claude-Meta-Skills „Task Observer /
One Skill to Rule Them All" (Eoghan Henn, rebelytics.com, CC BY 4.0) am
17.09.2026, siehe [[Task-Observer-Metaskill]]. Übernommen wurde nur das
Prinzip und das Dateiformat, nicht die 11.076-Token-Hauptdatei mit
Vor-jedem-Tool-Aufruf-Zwang — das hätte der Skill-Ausmist-Linie vom
11.09.2026 widersprochen.

**Format:** `log/JJJJMMTT-HHMMSS-slug.md`, Frontmatter mit `id`, `title`,
`status` (`open`/`actioned`/`declined`/`parked`), `skill`,
`proposes_skill`, `date`, `session_context`; Body als
Beobachtung → Vorschlag → Prinzip. Details und Schreibregeln im Skill
selbst, nicht hier verdoppelt.

**Nicht zu verwechseln mit** `Wissen/Wiederholbare-Aufgaben.md` (fertige,
bereits gebaute Skills und ihre Herkunft) — dieses Verzeichnis ist die
Werkbank *davor*: offene, noch unentschiedene Beobachtungen.
