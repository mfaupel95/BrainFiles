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

# Routing-Worklist

Macht aus dem Routing-Plan eine ausfuehrbare Worklist: eine Liste von
Arbeitseinheiten, die ein Downstream-Task abarbeiten kann, ohne den Plan zu
lesen.

## Die eine Regel, die alles erklaert

**Quelle der Wahrheit ist `MaxHirn/Archiv/TASKS.md`, nicht der Routing-Plan.**

Gemessen am 04.10.2026: TASKS.md hat **170 offene Punkte**, der Plan trug
**123**. 47 davon gingen im Plan verloren. Zwei belegte Ursachen:

1. `routing_plan_bauen.py` liest als Kopfzeile nur `- [ ] **T-NNN — Titel**`
   (Geviertstrich). TASKS.md traegt aber drei Schreibweisen: 146 Geviertstrich,
   46 ASCII-Bindestrich, 1 untermittelt (T-064, ohne schliessende `**`).
   Wer nur die Hausform kennt, verliert die anderen 47 - dieselbe Fehlerklasse
   wie T-332 (`doppelte_nummern.py` uebersah 26 Eintraege und meldete gruen).
2. T-064s Kopfzeile bricht nach `REST traegt` ab und hat kein schliessendes
   `**`. Kein Muster mit `\*\*$` liest sie.

Deshalb liest dieses Werkzeug die Felder aus TASKS.md und uebernimmt aus dem
Plan nur das, was der Plan wirklich weiss: **Welle** (Reihenfolge),
**Assignee** (Profilwahl) und **Aufwand**. Fehlt ein Punkt im Plan, traegt die
Worklist ihn trotzdem - aus TASKS.md, mit Querverweis-Rechnung als Welle. Der
Plan-Mangel wird als BEFUND gemeldet, nie still ersetzt.

## Die drei Werkzeuge

| Datei | Wofuer | Exit |
|---|---|---|
| `routing_worklist_bauen.py` | TASKS.md + optional Plan -> `worklist.json` (+ `.md`) | 0 |
| `routing_worklist_pruefen.py` | prueft die Worklist gegen TASKS.md | 0 = belegt, 1 = rot |
| `routing_worklist_gegenprobe.py` | baut Verletzungen ein, der Pruefer muss rot werden | 0 = alle erkannt |
| `test_routing_worklist.py` | 18 Tests (unittest) | 0 |

## Welche Fassung versioniert wird und welche nicht

- `MaxHirn/Archiv/ROUTING_WORKLIST.**md**` ist versioniert (die Whitelist in
  `.gitignore` gibt `!MaxHirn/Archiv/*.md` frei) - das ist die Fassung, die ein
  Mensch liest.
- `MaxHirn/Archiv/ROUTING_WORKLIST.json` wird **nicht** versioniert: es trifft
  die Sammelregel `*` in `.gitignore`, weil die Whitelist nur `*.md`
  freigibt. Das passt zur Hausregel: die JSON ist ein Laufzeitstand und aus
  dem Bauwerkzeug in Sekunden regenerierbar. Ein versioniertes
  Arbeitsergebnis, das ein `git add -A` einsammelt, ohne je gelesen zu
  werden, waere ein zweiter Wahrheitsstand.

Pruefen, welche Datei die Regel trifft:

```
git check-ignore -v MaxHirn/Archiv/ROUTING_WORKLIST.json
```

## Aufruf

```
cd Agenten/Werkzeuge/routing-plan
python routing_worklist_bauen.py MaxHirn/Archiv/TASKS.md \
    MaxHirn/Archiv/ROUTING_WORKLIST.json \
    --plan MaxHirn/Archiv/ROUTING_PLAN_2026-10-04.md \
    --markdown MaxHirn/Archiv/ROUTING_WORKLIST.md

python routing_worklist_pruefen.py MaxHirn/Archiv/TASKS.md \
    MaxHirn/Archiv/ROUTING_WORKLIST.json \
    --plan MaxHirn/Archiv/ROUTING_PLAN_2026-10-04.md

python routing_worklist_gegenprobe.py MaxHirn/Archiv/TASKS.md \
    MaxHirn/Archiv/ROUTING_WORKLIST.json

python -m unittest test_routing_worklist
```

Ohne `--plan` baut das Werkzeug die Worklist allein aus TASKS.md: die Welle
kommmt dann aus den Querverweisen im Text, das Profil aus dem Plan fehlt und
wird als `default` gesetzt (`profil_aus_plan: false` sagt das je Item).

## Felder eines Items

| Feld | Bedeutung |
|---|---|
| `id` | stabile ID (`T-123`), genau einmal in der Worklist |
| `titel` | Titel aus TASKS.md |
| `beschreibung` | der Blocktext, fuer einen Menschen lesbar gekuerzt |
| `abnahmekriterium` | der `Naechster Schritt` des Hauses |
| `abnahmekriterium_herkunft` | `explicit` / `derived_kontext` / `derived_titel` |
| `assignee` | Profil aus dem Plan, sonst `default` |
| `profil_aus_plan` | stand das Profil wirklich im Plan? |
| `bucket` | `PARALLEL` (Welle 1) oder `ORDERED` (Welle > 1) |
| `welle` | Ausfuehrungsreihenfolge |
| `welle_herkunft` | `plan` oder `querverweis` |
| `status` | `offen` / `wartet auf Max` / `blockiert` / `in Arbeit` |
| `aufwand` | `S`/`M`/`L` aus dem Plan |
| `kopf_untermittelt` | `true`, wenn TASKS.md an dieser Zeile `**` vergaess |
| `quelle_zeile` | Zeile in TASKS.md - Nachweis, woher der Punkt stammt |

## Buckets

- **PARALLEL** = Welle 1: kein Querverweis zwischen den Punkten, beliebig
  startbar.
- **ORDERED** = Welle > 1: der Punkt verweist auf einen Punkt einer frueheren
  Welle und muss danach laufen. Der Pruefer ist streng - ein `ORDERED` mit
  Welle <= 1 ist rot.

`items` steht in der **Quell-Reihenfolge aus TASKS.md**, nicht in der
Ausfuehrungsreihenfolge. Die Reihenfolge steht in `welle` + `bucket`.

## Abnahmekriterium: `explicit` oder `derived`

Ein Item ohne `Naechster Schritt` bekommt eins, das als abgeleitet markiert
ist (`derived_kontext` aus dem Kontext, sonst `derived_titel`). Ein als
Abnahmekriterium ausgegebener Kontext waere sonst eine Behauptung, die der
Eintrag nicht traegt - der Pruefer verlangt darum eine offengelegte Herkunft
und weist eine unbekannte Herkunft ab.

Stand 04.10.2026: `explicit` 154, `derived_kontext` 13, `derived_titel` 2.

## Leerfall

TASKS.md ohne offene Punkte -> leere Worklist, Exit 0, Befund
`leerfall: no open items - nothing to execute`. Der Pruefer verlangt diesen
Befund; fehlt er, ist die Pruefung rot - sonst noeppt ein Downstream nicht
erkennbar, weil eine leere Liste wie ein Fehler aussieht.

## Befunde (nicht Fehler)

Die Worklist kann gruen sein und trotzdem etwas melden. Zwei gemessene:

- `plan_unvollstaendig`: 47 offene Punkte fehlen im Routing-Plan. Die Worklist
  traegt sie, der Ausfuehrungsplan des Plans nicht. **Gehoert eine eigene
  Karte**, nicht diese hier - der Plan-Bauer ist ein anderer Auftrag.
- `kopf_untermittelt`: T-064 (Zeile 2591) traegt eine Kopfzeile ohne
  schliessende `**`. Mitgelesen, damit der Punkt nicht still verschwindet;
  zu reparieren ist TASKS.md, und die gehoert zum Bereich `wissen` - dieses
  Werkzeug schreibt sie nicht.

## Zwei Fallen, die den Bau gebremst haben

1. **Ein Verweis am Dateiende.** `python "$TMPDIR/x.py"` scheitert unter
   Windows mit `can't open file 'C:\tmp\x.py'` - der Interpreter ist ein
   natives Programm und bildet den MSYS-Pfad nicht ab. Alle Skriptpfade hier
   sind C:-Pfade.
2. **Zwei Zaehlweisen fuer dieselbe Sache.** Bauer und Pruefer meldeten erst
   47 und 46 fehlende Punkte. Zwei Stellen, die dieselbe Zahl an zwei Orten
   zaehlen, driften. Der Pruefer importiert jetzt `plan_wellen()` aus dem
   Bauer - die Zahl gibt es nur noch einmal.
