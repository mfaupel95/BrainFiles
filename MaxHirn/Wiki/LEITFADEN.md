---
id: 20260921-wiki-leitfaden
title: 'Wiki — Leitfaden'
tags: [betrieb, wiki]
created: 2026-09-21
updated: 2026-09-21
related: ['[[INDEX]]', '[[Wissen/Schutzregeln]]']
summary: 'Was ins Wiki gehoert, was nicht, und wie eine Seite aussieht — die Arbeitsanweisung fuer den Lernspeicher der Agenten.'
---

# Wiki — Leitfaden

## Wozu

`Wissen/` sammelt, was **Max** betrifft. Das Wiki sammelt, was das **Arbeiten**
betrifft: Fallen, Merksaetze, Betriebsstand, offene Punkte. Zweck ist kurz:
**derselbe Fehler wird nicht zweimal gemacht.** Wenn eine Sitzung eine Stunde
gekostet hat, steht die Ursache danach hier — in einem Absatz, nicht in einem Chat.

## Ablage-Entscheidung

| Was ist entstanden | Wohin |
|---|---|
| Falle/Lehre mit Merksatz | Wiki-Seite unter `Lektionen/` oder passender Rubrik |
| Verfahren, das abgearbeitet wird | Skill unter `../Agenten/Hermes/skills/` — **verweist** auf die Wiki-Seite |
| Zahl, Messung, Zustand zu Max | `Wissen/` (Skill `notiz`) und `Wissen/INDEX.md` nachziehen |
| Ausgabe eines einzelnen Laufs, Zwischenstand | `../Werkstatt/` |
| offener Punkt, der auf Max wartet | `Offen/Entscheidungen.md`, sofort |
| Zugangsdaten | **nirgends hier** — `Wissen/Zugaenge.md`, Stufe 0, nie ausgeben |

## Hausformat einer Seite

```markdown
---
id: JJJJMMTT-kurzname
title: 'Titel'
tags: [rubrik]
created: JJJJMMTT
updated: JJJJMMTT
related: ['[[Andere Seite]]']
summary: 'Ein Satz: wofuer diese Seite da ist.'
---
```

Danach: kurze Abschnitte, **Regel zuerst**, dann Begruendung, dann „Nachweis" mit
dem Befehl oder Pfad, mit dem die Aussage nachpruefbar ist. Eine Seite, die man
nicht nachrechnen kann, ist beim naechsten Mal wertlos.

## Harte Regeln

1. **Beleg oder nichts.** Zahlen nur mit Datum und Herkunft (Datei, Befehl, Journal).
2. **Keine Zugangsdaten, keine Schluesselwerte** — auch nicht gekuerzt.
3. **Veraltetes wird berichtigt, nicht ergaenzt.** Steht eine Zahl nicht mehr, wird
   sie ersetzt und `updated` gezogen; die Historie liegt in Git.
4. **Titel ohne Floskeln**, Rubrik im Pfad statt im Namen.
5. **Deutsch**, LF-Zeilenenden, keine absoluten Nutzerpfade (Portabilitaet).
6. **Nach jeder neuen Seite:** Eintrag in [INDEX.md](INDEX.md) im selben Arbeitsschritt.
7. **Der Skill wiederholt nicht.** Steht das Verfahren im Skill, nennt er die
   Wiki-Seite; die Zahlen stehen hier.

## Woher die Lehren kommen

Beim Beenden einer Aufgabe eine Minute Rueckschau halten und drei Fragen stellen:

- Was hat **laenger gedauert als erwartet**, und warum?
- Welche **Annahme war falsch** (nicht: welcher Tippfehler war es)?
- Was wuerde eine **frische Sitzung** hier falsch machen?

Treffer werden abgelegt. Ein leerer Lauf ist ein gueltiges Ergebnis — dann steht
nichts an.