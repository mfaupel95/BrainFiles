---
name: skill-maxhirn-marktbriefing
description: Trockenlauf des Skills MaxHirn:marktbriefing - beschreibt die Quellen eines Marktbriefings (traderhub-Boards, Einheiten, Prüfungen) und stellt fest, dass der Lern-Ablauf keinen Marktbezug hat.
metadata:
  type: reference
---

**Zweck:** Ein Bildschirm mit geprüften Marktzahlen: Zinsen, Makro, Sektorrotation und Einzelwerte. Keine Prognose, kein Handelsvorschlag. Handelt nichts, versendet nichts.

**Wann nutzen:** Bei „Marktüberblick“, „Marktlage“ oder als Routine. Ablage nur im Routinelauf oder auf ausdrücklichen Wunsch.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, welche Quellen ein Briefing brauchte, und feststellen, ob der Lern-Ablauf einen Marktbezug hat. Keine Marktdaten abgerufen, nichts geschrieben.

**Ergebnis:**

Quellen eines Briefings (laut Skill):
- `traderhub board get --board macro` für Zinsen, Makro und Stimmung
- `traderhub board get --board movers` für Gewinner, Verlierer und Screener-Listen
- `traderhub board rotation` für Sektorrotation
- optional Kalender, Fed-Daten und Terminstruktur, nur auf Wunsch

Pflichtprüfungen: `meta` lesen (`origin`, `stale`), Stand (`asOf`) nennen, Einheiten umrechnen. Prozentangaben liegen teils als Bruch vor, OECD-Reihen in Prozentpunkten.

Marktbezug des Lern-Ablaufs: keiner. Die Lernnotizen beschreiben Skills, keine Märkte. Der Skill passt nicht zum Ziel des Laufs und wird deshalb nur dokumentiert.

Ein Nebenbefund: Der Skill verweist auf die Notiz `Marktlage-August-2026`. Ob sie noch existiert, wurde nicht geprüft.

**Gelernt:** Ein Skill mit Zeitplan-Bezug und Ablagepflicht braucht bei einem Trockenlauf besondere Vorsicht: Er soll Daten lesen, aber nichts festschreiben. Hier wurde nur die Beschreibung ausgewertet.

**Grenzen:** Keine Daten abgerufen. Die Einheitenregeln sind aus dem Skill übernommen und nicht gegen echte Ausgaben geprüft.
