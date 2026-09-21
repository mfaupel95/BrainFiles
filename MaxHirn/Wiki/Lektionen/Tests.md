---
id: 20260921-tests
title: 'Lektionen — Tests'
tags: [lektion, tests]
created: 2026-09-21
updated: 2026-09-21
related: ['[[Handel/Lektionen]]', '[[Lektionen/Git-und-Textdateien]]']
summary: 'Tests, die in echte Datenordner schreiben; Modulwaechter als Gegenmittel; Reihenfolge der sys.path-Eintraege; Tests, die nichts pruefen.'
---

# Tests

## 1. Ein Test darf nie in einen echten Zielpfad schreiben

**Regel.** Jede Testklasse, die eine Funktion mit Journal-/Zustandsaufruf direkt prueft,
setzt `SCHREIBEN = False`, patcht Wachen- und Journalpfade auf einen Tempordner **und**
baut einen Modulwaechter: `setUpModule` merkt Dateiliste und Groessen des echten
Spurordners, `tearDownModule` vergleicht.

**Warum.** Drei belegte Faelle:

- Die Suiten von `spiegel` und `omniquant` behielten das ECHTE `journal_zweitziel`
  (`Q:\Handel_Journal\<spur>`) — jeder Testlauf ueberschrieb die Ausser-Haus-Kopie mit
  Tempdaten, Zustand 13.816 → 222 Byte, alle Tests gruen. Bedingung 4 still verletzt.
- `moondev_funding`-Tests buchten 16 Zeilen ins echte Journal.
- Nach jedem Lauf der Spurentests meldet `spiegelstand.py` kurzzeitig Abweichungen
  (`scanner/ablehnungen.csv`, `orbk/zustand.json`) — die Tests laufen in die echten
  Ordner, Q: zieht erst im naechsten Zyklus nach. **Das heilt von selbst**; bleibt eine
  Abweichung ueber zwei Zyklen, ist es ein echter Befund.

**Gegenprobe nach jeder Suite:** `Agenten/Handel/spiegelstand.py` muss byte-gleich melden.

## 2. `sys.path` — Reihenfolge entscheidet, welches Modul geladen wird

**Regel.** Die eigene Spur ZULETZT einfuegen und absichern:

```python
sys.path.insert(0, SPUR)
...
assert h.__file__.startswith(str(SPUR))
```

**Warum.** `for p in (SPUR, HANDEL, scanner): sys.path.insert(0, p)` stellt `scanner`
nach vorne — der Test laedt dann `scanner/handeln.py` statt der eigenen Spur und ist
gruen, ohne die eigene Spur zu beruehren. Gleichnamige Module gibt es mehrfach
(`gitter/grid.py` neben `Handel/grid.py`, `handeln.py` in jeder Spur).

**Testaufruf-Falle.** Spurtestsuiten nur aus `<spur>/tests` heraus starten
(`python -m unittest test_<spur>`); aus dem Spurenordner scheitert `discover` mit
„Start directory is not importable", und `-m unittest tests.test_x` zieht das falsche
`handeln.py`.

## 3. Ein Test, der nichts prueft, ist schlimmer als keiner

**Belegter Fall (16.09.2026).** `bewertung.bewerten(kerzen, richtung="long", gewichte=None)`
— ein Test uebergab sein Gewichte-Dict POSITIONELL; es landete in `richtung`, rutschte
still in den `long`-Zweig, und `66.7 == 66.7` war gruen. Seitdem wirft `bewerten()` bei
unbekannter Richtung `ValueError`.

**Regel.** Optionale Argumente als Keyword uebergeben und in der Funktion pruefen, ob der
Wert ueberhaupt der erwartete Typ ist. Ein Test an einem festen Beispielwert darf nicht
an einem festen Datum haengen — `test_risikovorfilter` hatte ein hartes `JETZT =
2026-09-17`; als der Vorfilter mit echtem `jetzt` rechnete, war das 12-h-Fenster leer.

## 4. Tests, die an Namen statt an Regeln haengen, brechen beim Aufraeumen

**Belegter Fall.** Der Bus-Test `test_skillkatalog` prueft `apple-notes`; als die
Skill-Bibliothek entdoppelt wurde, fiel er. Richtig ist die Pruefung der REGEL
(„jeder nicht ladbare Eintrag fehlt in der Faehigkeitsliste und steht in der
Schlusszeile").

## 5. Laufender Stand

Agenten/Handel, `discover -s tests -t tests`: **418 Tests, 2 vorbestehende rote**
(21.09.2026) — `test_risikovorfilter.EinbauTest` (festes Datum, s. o.) und
`test_telegram_freigabe.WiedervorlageImLaufTest` (rechnet mit einer offenen ANFRAGE,
bekommt seit AUTO_FREIGABE aber eine offene FREIGABE). Vor jeder Aussage
„durch die Aenderung rot" per A/B gegen `HEAD` gegenpruefen.