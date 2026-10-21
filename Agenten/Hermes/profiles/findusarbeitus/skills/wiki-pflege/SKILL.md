---
name: wiki-pflege
description: Use when eine Lehre dauerhaft festgehalten wird.
---

# Wiki pflegen — der Lernspeicher der Agenten

`MaxHirn/Wiki/` ist der Speicher fuer alles, was das ARBEITEN betrifft: Fallen,
Merksaetze, Betriebsstand, offene Punkte. `Wissen/` gehoert Max (Profil, Fristen,
Vertraege, Hardware). Auch erreichbar als `O:\Wiki` (Junction auf den Vault-Ordner).

Einstieg immer ueber `MaxHirn/Wiki/INDEX.md` — dort steht jede Seite mit Zweck.

## Wann lesen

Vor einer Aufgabe aus Betrieb, Handel oder Werkzeugen: die passende Seite oeffnen
(`Lektionen/`, `Betrieb/`, `Handel/`, `Werkzeuge/`). Sie nennt den gemessenen Stand
und die Falle, die schon einmal Zeit gekostet hat.

## Wann schreiben

Am Ende jeder Aufgabe eine Minute Rueckschau:

- Was hat laenger gedauert als erwartet, und warum?
- Welche **Annahme** war falsch (nicht: welcher Tippfehler)?
- Was wuerde eine frische Sitzung hier falsch machen?

Treffer werden **ungefragt** abgelegt, die Ablage in einem Satz gemeldet. Ein leerer
Lauf ist ein gueltiges Ergebnis.

## Ablage-Entscheidung

| Was | Wohin |
|---|---|
| Lehre/Merksatz mit Nachweis | `Wiki/Lektionen/` oder passende Rubrik — bestehende Seite **erweitern**, nicht danebenlegen |
| Verfahren zum Abarbeiten | Skill unter `Agenten/Hermes/skills/` — **verweist** auf die Wiki-Seite, wiederholt sie nicht |
| Zahl/Befund zu Max | `Wissen/` (Skill `notiz`) und `Wissen/INDEX.md` nachziehen |
| Ausgabe eines einzelnen Laufs | `Werkstatt/` |
| offener Punkt, der auf Max wartet | `Wiki/Offen/Entscheidungen.md` |
| Zugangsdaten | nirgends hier — `Wissen/Zugaenge.md`, Stufe 0 |

## Hausformat

Kopf wie im Vault (YAML): `id: JJJJMMTT-kurzname`, `title`, `tags`, `created`,
`updated`, `related: ['[[Andere Seite]]']`, `summary` (ein Satz).
Dann: **Regel zuerst**, Begruendung, und ein Abschnitt mit dem Befehl oder der Datei,
mit dem die Aussage nachpruefbar ist. Eine Seite, die man nicht nachrechnen kann, ist
beim naechsten Mal wertlos.

## Harte Regeln

1. **Beleg oder nichts** — Zahlen mit Datum und Herkunft (Datei, Befehl, Journal).
2. **Keine Zugangsdaten** — auch nicht gekuerzt.
3. **Veraltetes berichtigen, nicht ergaenzen** — Zahl ersetzen, `updated` ziehen; die
   Historie liegt in Git.
4. **Nach jeder neuen Seite** den Eintrag in `Wiki/INDEX.md` im SELBEN Arbeitsschritt
   nachziehen (wie bei `Wissen/INDEX.md`).
5. **LF-Zeilenenden**, keine absoluten Nutzerpfade in den Seiten (Portabilitaet).
6. Textdateien byte-sicher schreiben (`open(pfad,'rb')`, Zeilenende aus dem ROHEN Text
   ableiten, `open(pfad,'wb')`), danach `git diff --numstat` pruefen.
7. Neue Unterordner in `MaxHirn/Wiki/` brauchen die Freigabe in `.gitignore`
   (`!MaxHirn/Wiki/**/*.md`) — sonst sind sie unsichtbar; Gegenprobe
   `git check-ignore -v <pfad>`.
