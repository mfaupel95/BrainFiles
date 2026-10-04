# Routing-Plan aus TASKS.md

Baut aus `MaxHirn/Archiv/TASKS.md` einen Routing-Plan: jedes offene Element
genau einmal, mit Quelleile, Definition of Done, Blockern, Aufwand,
zugewiesenem Profil und einer Wellen-Reihenfolge.

## Aufruf

```
python Agenten/Werkzeuge/routing-plan/routing_plan_bauen.py <tasks.md> <ziel.md>
python Agenten/Werkzeuge/routing-plan/routing_plan_pruefen.py <tasks.md> <plan.md>
python Agenten/Werkzeuge/routing-plan/routing_plan_unabhaengig.py <tasks.md> <plan.md>
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

## Der Titel-Trenner ist uneinheitlich — die Kopfregel steht in EINER Datei

Gemessen am 04.10.2026 an den 192 Einträgen im Abschnitt `## Offen` von
`TASKS.md` (192 Statuszeichen-Zeilen, 171 davon offen):

| Form | Anzahl |
|---|---|
| `- [ ] **T-NNN — Titel**` (Gevrierstrich, schließendes `**`) | 146 |
| `- [ ] **T-NNN - Titel**` (ASCII-Bindestrich, schließendes `**`) | 46 |
| Titel bricht ohne schließendes `**` um | 10 (darunter T-064) |

`kopfformen.py` ist die **eine** Kopfregel des Hauses: ein Trenner-Satz
(`—` / `–` / `-`) als Zeichenmenge, ein Titel, der ohne `**` umbrechen darf.
`routing_plan_bauen.py` und `routing_plan_pruefen.py` importieren sie —
ein zweites Muster in einer der Dateien wäre eine zweite Wahrheit.

**Warum das der entscheidende Punkt ist:** `VERDAECHTIG` in derselben Datei
benennt jede Zeile, die wie ein Eintrag *aussieht*, aber von keinem Muster
erfasst wird. Ein stillschweigend nicht gelesener Eintrag fällt auf **beiden**
Seiten weg — im Plan *und* in der Liste der offenen Punkte — und die
Zahlengleichheit `123 == 123` meldet einen unvollstaendigen Plan grün. Genau
so sind am 04.10.2026 47 offene Punkte verschwunden, weil der Prüfer die
Enge des Builders **teilte**: er prüfte die Lücke nicht, er übernahm sie.
Seitdem gilt: der Bauer bricht mit `Abbruch` ab, der Prüfer meldet rot.

Gegenbeweis, gemessen (siehe Test `GegenprobeOhneFixTest`): die alte enge
Regel liest 125 offene Punkte, die breite 171 — **46 gehen verloren**, und
genau diese 46 führt der alte Prüfer als „nicht offen / erfunden".

Tests: `python Agenten/Werkzeuge/tests/test_routing_kopfformen.py` (17).
Sie bauen echte Temp-Dateien, fassen `TASKS.md` nie an und enthalten einen
Test, der verlangt, dass das **alte** Muster an ASCII-Bindestrich und
Umbruch-Titel scheitert — sonst prüft die Suite nur, dass die neue Regel
funktioniert, nicht dass die alte zu eng war.

**Regel: Builder und Prüfer dürfen nie dieselbe Enge teilen, wenn der Prüfer
die Vollständigkeit behaupten soll.** `routing_plan_unabhaengig.py` ist der
Gegenweg: eigener Zählweg, eigene Markdown-Prüfung, kein Import des
Hausprüfers — aber derselbe `VERDAECHTIG`-Blick, damit auch dort kein
Eintrag lautlos verschwindet.

## Dateiwahl

Liegt am Ziel schon ein Plan, wird ein NEUER mit Datum im Namen geschrieben
(`ROUTING_PLAN_YYYY-MM-DD.md`). Ein Plan, der seinen Vorgänger ohne Spur
ersetzt, ist bei 119 offenen Punkten nicht mehr von einem neuen zu unterscheiden.

Ein zweiter Lauf am selben Tag schreibt `_YYYY-MM-DD-2`, `-3` … dahinter; ohne
diese Kette überschriebe der zweite Lauf den ersten des Tages. Der Plan ohne
Datum im Namen (`ROUTING_PLAN.md`) bleibt als erster Stand im Repo liegen — **gültig
ist die datierte Fassung mit dem grünen Prüferstand**, nie die undatierte. Der
Plan nennt seinen eigenen Erzeugungstag (`Erzeugt am …`), nicht die Schreibzeit.

## Wohin damit: nicht basic-memory

**basic-memory ist keine Hauskonvention für Plan-Dokumente** (gemessen 04.10.2026):

- Das basic-memory-Projekt zeigt auf `C:\Users\faupe\basic-memory`, nicht ins
  BrainFiles; dort liegen vier Automatik-Notizen (`automatik/laeufe/`,
  `automatik/proben/`), kein Hausdokument.
- Es ist kein Git-Repo und steht in keinem Sicherungslauf (`sichern.ps1` hat
  keinen Eintrag dafür) — eine Kopie wäre die einzige Fassung ohne Historie.
- Die Hausregel in `MaxHirn/AGENTS.md` schreibt stattdessen vor: *eine Zahl, ein
  Befund, ein Zustand* → Notiz unter `Wissen/`, *ein offener Punkt* →
  `Archiv/TASKS.md`. Beides ist erfüllt: die Quelle ist `TASKS.md`, der Plan
  steht daneben.

Die Karte, die diesen Schritt beauftragt hat, nannte basic-memory nur als
Möglichkeit („if it is the house convention"). Die Antwort ist damit belegt und
nein — es wird keine Kopie geschrieben. Ein Grund, an basic-memory zu denken,
wäre ein Abruf über die Profil-Grenze hinweg (Bot `basic-memory`), nicht der
Notizenspeicher.

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
Ebene) **und prüft vier Mal die Quelle**: eine gültige ASCII-Kopfzeile und
ein gültiger Umbruch-Titel müssen gelesen werden, eine Kopfform, die kein
Muster kennt, muss den Bauer zum Abbruch und beide Prüfer zum roten Lauf
bringen. Ein Prüfer, der immer grün sagt, ist schlechter als keiner — die
Gegenprobe ist deshalb Pflicht, nicht Kür.

Zwei Fehlerklassen sind dabei am 04.10.2026 real passiert und deshalb
ausdrücklich abgesichert: die Mutation `fremder_assignee` suchte einen
festen Namen (`markt-recherche`), der in einer Attrappe gar nicht vorkommt —
die Mutation blieb leer, der Prüfer blieb grün. Und `mutieren()` zerlegte
den Plan an `\r\n`, obwohl der Builder CRLF nur schreibt, *weil* die Quelle
CRLF trägt; eine LF-Attrappe ergab eine leere Zeilenliste und einen
IndexError. Beide nehmen jetzt den Zeilenendungs-Charakter aus der Datei
bzw. einen echten Roster-Namen aus dem Plan.

## Bekannte Grenzen

- 13 der 119 offenen Einträge nennen keinen `Naechsten Schritt`; deren DoD
  ist als Kontext abgeleitet und im Plan als solche markiert.
- Die Welle leitet sich allein aus `T-NNN`-Querverweisen im Text. Ein
  Eintrag ohne Querverweis landet in Welle 1 und startbar.
- Wellen werden oben auf 6 begrenzt, damit eine Kette von Zitaten keine
  siebte Ebene erzeugt; ein Kreis verhindert dabei die Auflösung.