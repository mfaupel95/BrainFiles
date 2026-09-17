---
id: 20260917-000001
title: Fremde README-Anhänge landen unsortiert in Agenten/Hermes/attachments
status: open
skill: [brainfiles-auftrag]
proposes_skill: []
date: 2026-09-17
session_context: >
  Über mehrere Sitzungen (NautilusTrader-README, moon-dev-ai-agents-README,
  task-observer-Anhänge, public-apis-README) hat Max READMEs/SKILL.md
  fremder Projekte per @file: angehängt, mit der Bitte "Wissen hinzufügen"
  oder "installiere nach Anleitung". Jedes Mal wurde die Datei manuell
  gelesen, bewertet und die Erkenntnis von Hand in eine neue Wissen/-Notiz
  übertragen — kein Skill kennt diesen Schritt als eigenes Muster.
---

**Beobachtung:** Angehängte Dateien liegen unter
`Agenten/Hermes/attachments/` (Hermes-Anhangsordner), das ist ein
Laufzeitordner ohne Bezug zu `Wissen/`. Der Übertrag "lesen, bewerten,
als Notiz nach Wissen/ + INDEX.md eintragen, ggf. Kanban-Task für offene
Entscheidungen" wiederholt sich identisch, unabhängig vom Thema des
Anhangs (Trading-Framework, Meta-Skill, API-Liste).

**Vorschlag:** `brainfiles-auftrag` um einen kurzen Abschnitt "Anhänge
verarbeiten" ergänzen: (1) Anhang lesen, (2) gegen bestehende
Wissen/-Notizen prüfen (Duplikat? Ergänzung?), (3) neue Notiz mit
Frontmatter + INDEX.md-Eintrag im selben Schritt, (4) bei offener
Entscheidung (Adoption/Installation eines Fremdprojekts) einen
Kanban-Task anlegen statt die Entscheidung nur im Chat zu diskutieren —
das war bei task-observer bereits nötig und hat sich bewährt.

**Prinzip:** Ein wiederkehrendes Eingabemuster ("Nutzer hängt Fremd-Doku
an, will sie im System verankert sehen") verdient eine benannte
Prozedur, sobald es zum dritten Mal auftritt — unabhängig vom Fachinhalt
des jeweiligen Anhangs. Die Prozedur gehört zum bestehenden
Auftrags-Skill, nicht zu einem neuen: es ist keine neue Fachdomäne,
sondern ein Präfix vor der ohnehin gültigen Nachweis-Kette.
