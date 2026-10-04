# Routing-Plan aus TASKS.md

Baut aus `MaxHirn/Archiv/TASKS.md` einen Routing-Plan: jedes offene Element
genau einmal, mit Quelleile, Definition of Done, Blockern, Aufwand,
zugewiesenem Profil und einer Wellen-Reihenfolge.

## Aufruf

```
python Agenten/Werkzeuge/routing-plan/routing_plan_bauen.py <tasks.md> <ziel.md>
python Agenten/Werkzeuge/routing-plan/routing_plan_pruefen.py <tasks.md> <plan.md>
python Agenten/Werkzeuge/routing-plan/gegenprobe.py <tasks.md> <plan.md>
```

Beispiel:

```
python Agenten/Werkzeuge/routing-plan/routing_plan_bauen.py ^
  MaxHirn/Archiv/TASKS.md MaxHirn/Archiv/ROUTING_PLAN.md
```

## Was "offen" heisst

Alle Eintraege im Abschnitt `## Offen`, die NICHT `[x]` tragen — also auch
`[ ]`, `[~]`, `[?]` und `[!]`. Ein `[x]` unter `Offen` wird gezählt, aber
nicht als offen geführt: im Haus wandert er erst später nach `## Erledigt`.

## Dateiwahl

Liegt am Ziel schon ein Plan, wird ein NEUER mit Datum im Namen geschrieben
(`ROUTING_PLAN_YYYY-MM-DD.md`). Ein Plan, der seinen Vorgänger ohne Spur
ersetzt, ist bei 119 offenen Punkten nicht mehr von einem neuen zu unterscheiden.

## Die sechs Bestandteile

| Abschnitt | Inhalt |
|---|---|
| (a) | gewählte tasks.md + ein Satz Begründung + Zahlenstand |
| (b) | nummerierte Tabelle aller offenen Punkte (8 Spalten) |
| (c) | Wellen 1..n, jede als `parallel` oder `sequenziell` gekennzeichnet |
| (d) | Leerzustand — steht IMMER da, auch wenn nichts offen ist |
| (e) | die ersten 3 Dispatches mit Assignee und Blocker |

## Was die Felder wirklich sind

- **Definition of Done** — der `Naechster Schritt` des Eintrags. Fehlt er,
  wird der Kontext benutzt und als solcher gekennzeichnet
  (`[aus Kontext abgeleitet …]`). Erfunden wird nichts.
- **Blocker** — Statuszeichen `[?]`/`[!]` und das Hausfeld `Wartet auf`.
  Sonst `keine`.
- **Aufwand S/M/L** — aus Textlänge, Zeilenzahl des nächsten Schritts,
  Max-Abhängigkeit und Zahl der Querverweise gerechnet, nicht geschätzt.
- **Profil** — gewichtet: ein Dateipfad im `Betrifft:` zählt 5, ein Wort im
  Fließtext 2-3. Ohne jeden Beleg `default`, mit dem Zusatz
  „nur der Titel, kein Pfad-Beleg" — nie still.

## Prüfung

`routing_plan_pruefen.py` behauptet nichts, es belegt: Zeilenenden wie die
Quelle, genau eine Zeile je offenem Eintrag, keine erledigte ID im Plan,
keine leere Pflichtspalte, Aufwand aus {S,M,L}, Assignee aus dem Roster,
Abschnitte (a)-(e) genau einmal als Überschrift, Wellen mit korrekter
Kennzeichnung. Exit 0 = grün, Exit 1 = rot mit Begründung.

`gegenprobe.py` verletzt den Plan sechs Mal (Zeile weg, Zeile doppelt, DoD
leer, fremder Assignee, Welle falsch gekennzeichnet, Abschnitt auf falscher
Ebene) und verlangt jedes Mal einen roten Lauf. Ein Prüfer, der immer grün
sagt, ist schlechter als keiner — die Gegenprobe ist deshalb Pflicht, nicht
Kür.

## Bekannte Grenzen

- 13 der 119 offenen Einträge nennen keinen `Naechsten Schritt`; deren DoD
  ist als Kontext abgeleitet und im Plan als solche markiert.
- Die Welle leitet sich allein aus `T-NNN`-Querverweisen im Text. Ein
  Eintrag ohne Querverweis landet in Welle 1 und startbar.
- Wellen werden oben auf 6 begrenzt, damit eine Kette von Zitaten keine
  siebte Ebene erzeugt; ein Kreis verhindert dabei die Auflösung.