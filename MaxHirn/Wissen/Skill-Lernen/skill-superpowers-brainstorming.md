---
name: skill-superpowers-brainstorming
description: Trockenlauf des Skills superpowers:brainstorming — strukturiertes Anforderungs-Gespräch vor dem Bauen; Was-und-Warum klären bevor etwas entsteht.
metadata:
  type: reference
---

**Zweck:** Herausfinden was wirklich gewollt ist, bevor etwas gebaut wird. Gespräch führen, Annahmen sichtbar machen, Designentscheidungen vor dem Bau klären.

**Wann nutzen:** Vor jeder nicht-trivialen Implementierung. Pflichtaufruf bei "Lass uns X bauen" — erst brainstorming, dann writing-plans, dann implementation.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~4 Seiten. Kernstück des superpowers-Workflows.

**Gelernt — Kernstruktur:**

**Erste Nachricht (exakt zwei Teile):**
1. Opt-out-Angebot: "Wenn du lieber direkt loslegst, sag Bescheid"
2. Eine offene Frage nach einem konkreten Moment/Bild

Danach: je eine Frage pro Nachricht — niemals Liste, niemals Prozessjargon.

**Gesprächsziel: Abdecken ohne zu skripten:**
- Was ist das, was macht es besonders?
- Warum jetzt, wie sieht Erfolg aus?
- Ziele, Nicht-Ziele, Anti-Ziele (Was wäre Misserfolg trotz technischer Funktion?)
- Vorbilder: was gesehen, geliebt, gehasst?
- Aktueller Stand, bisherige Versuche
- Die Details, die wirklich wichtig sind

**Größeneinschätzung:**

| Größe | Beschreibung | Nächster Schritt |
|---|---|---|
| Kurze klare Aufgabe | Anfrage selbst | Einfach machen |
| Kleine Änderung | Im Chat | Normaler Workflow |
| Projekt mit Design | Schriftliches Designdokument | superpowers:writing-plans |

**Designdokument** (wenn nötig):
- Ablage: `docs/superpowers/specs/YYYY-MM-DD-<thema>-design.md`
- Inhalt: Absicht+Warum, Ziele/Nicht-Ziele/Anti-Ziele, Constraints, Wie-Entscheidungen, Was dem Builder überlassen
- Builder-Check: Subagent mit `builder-check-prompt.md` dispatchen
- Ergebnis: "Bereits beantwortet" / "Kleines" (selbst entscheiden) / "Ihres" (User fragen)

**Hard Gate:** Nichts wird gebaut bis das vollständige Design genehmigt ist. Bauen = Code schreiben, Scaffolding, Dependencies installieren, Projekte anlegen.

**Visueller Begleiter:** Browser-Tab für Mockups anbieten — aber nur beim ersten passenden Moment, nie upfront. Angebot als eigene Nachricht ohne weiteren Inhalt.

**Rot-Fahnen:**
- Optionen anbieten statt fragen → Optionen steuern, erst beschreiben lassen
- "Sinnvolle Defaults ausfüllen" → OK, aber laut aussprechen
- "Sie sagten 'klingt gut' zur Idee" → Genehmigung deckt nur was gezeigt wurde
- Spike weitergebaut → Behalten = neuer Antrag, zurück durch den Gate

**Spike-Modus:** Wenn User schnell ausprobieren will, aus dem Weg gehen. Spike = keine Tests, nicht bulletproof, kein Plan/Implementation/Review. Was gelernt wurde zurück ins Gespräch bringen.

**Grenzen:** Braucht Gesprächspartner. Ohne Rückmeldung keine Annäherung ans Ziel — Skill ist ein Gesprächsführungs-Werkzeug, kein Analyse-Tool.
