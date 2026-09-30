---
name: aufgabenliste-pflegen
description: Use when TASKS.md geaendert wird oder eine Aufgabe endet.
version: 0.1.0
author: Hermes Agent
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Aufgaben, TASKS.md, BrainFiles, Editieren]
---

# Aufgabenliste pflegen (`MaxHirn/Archiv/TASKS.md`)

## When to Use

- "als Task eintragen", "was ist offen", "fass die offenen Punkte zusammen"
- am Ende JEDER Aufgabe (stehende Regel, siehe unten)
- Sammelauftrag, Sitzungsabschluss, Betriebsrunde: Aufgaben nachziehen
- eine Aufgabe ist erledigt (`## Erledigt`), oder ihr Titel behauptet etwas, das
  eine Messung widerlegt hat

Die Datei ist die EINE offene-punkte-Liste des Hauses,
CRLF, und waechst zwischen zwei Sitzungen um Dutzende Eintraege. Sie wird oft per
Skript geaendert - genau dort verschwindet still ein Eintrag, wenn die Ersetzung
zu grob greift.

## Board oder Liste

Das Haus hat zwei Aufgabenorte, und sie duerfen sich nicht ueberschneiden:

- **Kanban-Board** (Skill `kanban-board`, ein Board je Arbeitsart): Arbeit, die
  mehrere Profile parallel ausfuehren, die auf Review oder Wiederholung wartet,
  oder die einen Betriebsprozess startet.
- **Diese Liste:** was eine ENTSCHEIDUNG von Max braucht, sowie Inhalte der
  Schutzstufe 0. Kartentexte auf dem Board liegen als Klartext in `kanban.db`
  (unter `Agenten/`, also in der Sicherung) - Bescheide, Schluessel und
  Zugangsdaten gehoeren hierher, nicht dorthin.

## Stehende Regel (Max)

Am Ende jeder Aufgabe gehoeren die **nicht angefassten** Punkte und jede offene
**Entscheidung von Max** als Task in die Liste - nicht nur der eigene Auftrag.
Dazu: was absichtlich liegen blieb (Fremdarbeit, laufende Prozesse, generierte
Dateien) und was noch eine Entscheidung braucht. Danach committen.

## Ablauf

1. **Frisch lesen, nie aus dem Kopf ergaenzen.** `grep -n "^## "` zeigt die
   Abschnitte, ein Zeilenfenster die ersten Eintraege. Die hoechste vergebene
   Nummer bestimmt die neue - **Nummern nie wiederverwenden**, auch nicht fuer
   geloeschte.
   **Und lesen und schreiben gehoeren in DENSELBEN Aufruf.** Zwischen einem
   Blick von vorhin und dem Schreiben liegen in diesem Baum Minuten, in denen
   eine parallele Sitzung Eintraege einfuegt: Zeilenindizes aus einem frueheren
   Aufruf zeigen dann auf einen anderen Block, und der wird beim Ersetzen
   zerschnitten (Text des Nachbarn weg, `Zuletzt:` mitten im Absatz). Der
   Schreibvorgang liest die Datei deshalb selbst ein, sucht den Block ueber SEIN
   eigenes Merkmal (`- [ ] **T-0NN — ` bzw. der Titel, nicht ein Zeilenindex),
   ersetzt und schreibt zurueck - und druckt den Block danach plus den Anfang des
   folgenden Eintrags zur Kontrolle.
   Ist die Datei beim Lesen **juenger als eine Minute**, schreibt gerade eine
   andere Sitzung: Sekunden messen, kurz warten, dann neu einlesen. Ein
   Sekunden-Blick unterscheidet 'ruhig' von 'mitten im Schreiben' - die
   Minutenangabe aus einem frueheren Befehl tut das nicht.
2. **Byte-sicher schreiben** (CRLF erhalten):

```python
with open(PFAD, "rb") as f:
    text = f.read().decode("utf-8")
nl = "\r\n" if "\r\n" in text else "\n"
assert text.count(anker) == 1
neu = ...                                   # jeder Ersatz mit `nl` gebaut
text = text.replace(anker, neu, 1)
with open(PFAD, "wb") as f:
    f.write(text.encode("utf-8"))
```

3. **Anker = Blockgrenze, nicht Kastenstellung.** Der Block endet beim NAECHSTEN
   `- [ ]` ODER `- [x]`. Ein Ausblick nur auf `- [ ] **` schluckt den folgenden
   ERLEDIGTEN Block und loescht ihn mit.

```python
# richtig - beide Kastenstellungen
re.compile(r"- \[[ x]\] \*\*T-067.*?(?=\r?\n- \[[ x]\] \*\*|\Z)", re.S)
```

4. **Nach JEDEM Schreiben die Nummernmenge vergleichen.**

```python
ids = lambda t: set(re.findall(r"- \[[ x]\] \*\*(T-\d+)", t))
assert ids(neu) - ids(alt) == set(), sorted(ids(alt) - ids(neu))
```

   **Beim VERSCHIEBEN (Offen -> Erledigt) die Mengen sortiert vergleichen,
   nicht als Folge.** Ein verschobener Block ist derselbe Eintrag an anderer
   Stelle; `re.findall(...)` liefert ihn in Dokumentreihenfolge, der Vergleich
   `==` schlaegt also bei einem KORREKTEN Verschieben fehl und verleitet zur
   'Reparatur' eines richtigen Zustands.

```python
assert sorted(re.findall(MUSTER, neu)) == sorted(re.findall(MUSTER, alt))
```

   Fehlt etwas: wortgleich aus `git show HEAD:MaxHirn/Archiv/TASKS.md`
   zurueckholen, nicht neu formulieren.
   **Und die Abschnitte gegenpruefen** - die Nummernmenge allein merkt nicht, dass
   eine Ueberschrift weg ist. Ein Umbau-Skript baut die Datei neu zusammen, und
   wer dabei `kopf + eintraege + "## Erledigt"` schreibt, verliert `## Offen`
   stillschweigend: die Eintraege sind alle da, die Liste hat nur keinen
   offenen Abschnitt mehr, und die naechste Sitzung zaehlt alles als erledigt.

```python
assert [z for z in ("## Offen", "## Erledigt") if z in neu] == ["## Offen", "## Erledigt"]
```

   Gleich nach dem Schreiben `grep -n "^## "` laufen lassen und mit dem Stand
   davor vergleichen.
5. **`git diff --numstat` muss plausibel sein.** Ein ersetzter eigener Block zeigt
   Insertions UND Deletions - mehr Deletions als der neue Block Zeilen hat heisst:
   es ist Fremdtext mitgegangen.
6. **Committen** mit namentlichem Pfad (`git add -- MaxHirn/Archiv/TASKS.md`),
   zusammen mit der Aenderung, zu der die Aufgabe gehoert.
   Liegt in DERSELBEN Datei schon fremde, noch nicht committete Arbeit (bei einer
   geteilten Liste der Normalfall), laesst sich nicht nach Pfad trennen. Dann
   alles committen und die uebernommenen FREMDEN Eintraege in der Commit-Meldung
   namentlich nennen ("Mitgenommen, weil in derselben Datei: T-179 ..., T-180
   ..."). Ohne diesen Satz steht fremde Arbeit spaeter unter dem eigenen Namen,
   und der naechste Leser sucht einen Autor, den es nicht gibt.

## Eintragsform

```
- [ ] **T-0NN — Kurztitel**
      Kontext: was gemessen/gebaut wurde, MIT Belegen (Zahlen, Pfade, Kommandos)
      Naechster Schritt: die EINE naechste Handlung, oder die offene Entscheidung
      Angelegt: JJJJ-MM-TT · Zuletzt: JJJJ-MM-TT
      Betrifft: <Pfade>
```

- **Eigene Aufgaben auf den gemessenen Stand ziehen** (Titel darf sich aendern),
  mit einer datierten `KORREKTUR`-Zeile, die sagt, was vorher behauptet wurde und
  warum es falsch war - der Irrtum ist die nuetzliche Information, nicht die
  Korrektur allein.
- **Fremde Aufgaben nur ergaenzen:** alten Text stehen lassen, einen datierten
  `BELEG <datum>`-Absatz anhaengen. Sonst gehen fremde Begruendung und fremder
  Kontext verloren, und der Autor sieht seine Aufgabe umgeschrieben.
- **Erledigtes** wandert nach `## Erledigt` und behaelt den Belegsatz (was es
  gezeigt hat, nicht "fertig"). Dort steht `- [x]`, in `## Offen` `- [ ]` -
  **die Kastenstellung entscheidet nicht, der ABSCHNITT tut es.** Wer nach der
  Klammer filtert, haelt den ganzen Erledigt-Block fuer offene Arbeit; nach dem
  Abschnitt filtern (oder beide Klammerformen im Ausblick zulassen, siehe
  Anker-Regel) und beim Einsortieren die Kastenstellung des Zielabschnitts
  setzen. Der erledigte Eintrag nennt das GEMESSENE Ergebnis - auch wenn die
  Aufgabe selbst gegenstandslos war ("nichts zu tun, weil X schon nicht mehr
  existiert") gehoert genau das mit Beleg hinein, nicht der urspruengliche Auftrag
text.
- **Ein Eintrag, der auf eine ENTSCHEIDUNG wartet (`- [?]`), endet MIT der
  Entscheidung.** Solche Bloecke tragen `Wartet auf: Max - …`. Beim Schliessen den
  `Naechster Schritt`/`Wartet auf`-Absatz durch die datierte Entscheidung ersetzen
  (`Entschieden JJJJ-MM-TT (Max): …`), `- [x]` setzen, nach `## Erledigt` ziehen.
  Fiel sie GEGEN die Aufgabe, steht genau das drin („bewusst ohne X") - bleibt der
  alte Auftragstext stehen, liest die naechste Sitzung den Punkt als offen und
  schlaegt ihn erneut vor. Dieselbe Entscheidung gehoert ZUSAETZLICH in die
  Fachnotiz, an die Stelle, die den Gegenstand beschreibt (mit Datum): dort wird
  sie gefunden, wo die Sache besprochen wird, nicht in der Aufgabenliste.
- Ein Titel verspricht ein ERGEBNIS, kein Vorgehen: "PF_XBTUSD ist mit 141 USD
  nicht handelbar" ist eine Aufgabe, "Kontraktgroesse pruefen" ist eine Notiz.

## Werkzeuge

Beide liegen im Skill und werden von hier aus gestartet - nicht nachbauen:

- `scripts/doppelte_nummern.py` (nur lesend, jederzeit lauffaehig): meldet
  hoechste Nummer, naechste freie Nummern, doppelte Nummern, fehlende Abschnitte
  und die Blockzahl. **Rueckgabe 1, sobald eine Nummer doppelt ist** - also als
  Tor vor dem Committen nutzen, nicht als Blick. Zaun-bewusst: Zeilen innerhalb
  eines Code-Zauns (die Format-Vorlage) zaehlen nicht als Eintrag.
  `python Agenten/Hermes/skills/aufgabenliste-pflegen/scripts/doppelte_nummern.py --ruhig`
- `scripts/erledigen.py`: zieht EINEN Eintrag byte-genau nach `## Erledigt`,
  hakt ihn ab, haengt den Belegsatz an, legt `TASKS.md.bak-JJJJMMTT` an.
  Es prueft vor dem Schreiben (Nummer genau einmal, steht in `## Offen`, noch
  nicht abgehakt, Abschnitte unveraendert, Nummernmenge gleich) und danach die
  Zeilenenden. `--trocken` nennt nur die Zielzeile, ohne zu schreiben.
  `python .../scripts/erledigen.py T-0NN "**Erledigt JJJJ-MM-TT.** was gemessen wurde" --trocken`
  **Seine Sicherung ist TAGES-genau** (`TASKS.md.bak-JJJJMMTT`, nur das Datum):
  ein zweiter Lauf am selben Tag ueberschreibt die Sicherung des ersten mit dem
  schon geaenderten Stand. Wer den Zustand VOR der ersten Aenderung des Tages
  braucht, kopiert ihn vorher selbst weg; der zweite Rueckweg ist
  `git show HEAD:MaxHirn/Archiv/TASKS.md`. Mehrere Eintraege am selben Tag also
  in EINEM Aufruf schliessen, nicht in mehreren Laeufen nacheinander.
  Es nimmt **nur `- [ ]`** an. Ein Eintrag in anderer Kastenstellung - der
  Wartestatus `- [?]` („Wartet auf: Max") - wird ueber den Byte-Weg nach Schritt 2
  bis 5 geschlossen; die Meldung dieses Werkzeugs lautet dann irrefuehrend „ist
  schon abgehakt" und meint „nicht `- [ ]`", nicht „bereits erledigt".

Die Format-Vorlage steht in `## Eintragsformat` und traegt `T-0NN` - niemals eine echte Nummer, sonst zaehlt sie als zweiter Eintrag.

## Fallen

- **Die hoechste Nummer NIE aus dem Gedaechtnis nehmen.** Die eigene
  Memory-Notiz nennt einen Stand von gestern ("hoechste am 24.09.: T-056");
  gemessen am 29.09.2026 stand die Datei bei T-159, und die aus dem Kopf
  gewaehlte Nummer war doppelt vergeben. Immer messen:

```bash
grep -oE "T-[0-9]+" MaxHirn/Archiv/TASKS.md | sort -u -t- -k2 -n | tail -3
```

  **Kein Muster mit fester Stellenzahl.** Ein `T-1[0-9][0-9]` findet nur
  dreistellige Nummern mit fuehrender 1 und liefert ab T-200 stillschweigend die
  falsche hoechste Nummer (und in einem zweistelligen Nummernkreis `T-99` gar
  keine) - das Ergebnis sieht wie ein Messwert aus und ist ein Artefakt des
  Musters. Immer `T-[0-9]+` und numerisch sortieren (`sort -t- -k2 -n`), nicht
  alphabetisch: `T-99` steht sonst hinter `T-100`.
  **Dieselbe Falle in der Gegenrichtung:** ein zu enges Muster
  (`grep -o 'T-0[0-9][0-9]'`) blendet alles ab `T-100` aus, und die Antwort
  "diese Eintraege sind verschwunden" ist dann ein Artefakt der Suche, kein
  Befund - ein Fehlalarm, der eine Suche nach einem Loeschvorgang ausloest.
  Vor JEDER Verlustmeldung mit dem weiten Muster nachzaehlen und gegen
  `git show HEAD:MaxHirn/Archiv/TASKS.md` halten; erst wenn beide dasselbe
  sagen, fehlt wirklich etwas.

  Danach die gewaehlte Nummer gegen die ganze Datei pruefen
  (`grep -c "\*\*T-160"`), nicht nur gegen den offenen Abschnitt.
- **Dasselbe Misstrauen gilt fuer jeden erinnerten BEFEHL.** Ein Unterbefehl oder
  ein Flag, das in dieser Sitzung niemand aufgerufen hat, ist eine Vermutung, kein
  Beleg: `--help` des Werkzeugs einmal laufen lassen, BEVOR der Name in Skill,
  Notiz, Memory oder in einer Anweisung an Max landet — dort liest er sich wie
  eine Hausregel und wird geglaubt (belegt: eine Memory-Notiz nannte ein
  Aufraeumkommando mit zwei erfundenen Schaltern). Steht die falsche Angabe schon
  irgendwo, korrigieren statt stehen lassen. Gilt genauso fuer Werkzeugnamen,
  Pfade und Zahlen aus dem Kopf.
- **Die Liste waechst zwischen zwei Blicken.** Vor dem Eintragen erneut lesen -
  eine parallele Sitzung haengt zwanzig Eintraege an, und die gewaehlte Nummer ist
  dann doppelt vergeben.
- **`write_file` verweigert die Datei** (kein vollstaendiger Lesevorgang dieser
  Sitzung) - ueber den Byte-Weg schreiben, nicht die Datei komplett neu setzen.
- **Ein Sichtfenster (`sed -n '1,40p'`) zeigt nur den Kopf.** Die eigene Aufgabe
  steht weiter unten: erst `grep -n "T-0NN"` suchen, dann Vorgaenger- und
  Nachfolgerblock lesen, bevor ersetzt wird.
- **Zeilenenden sind CRLF.** `open(..., "w")` dreht die Datei auf LF und erzeugt
  einen Ganzdatei-Diff; Gegenprobe `git diff --numstat`.
- **Und der ANKER traegt dieselben Enden.** Ein mehrzeiliger Suchtext, dessen
  Zeilen mit `\n` verbunden sind, trifft in einer CRLF-Datei NICHTS - der Block
  bleibt unveraendert stehen, und ohne `assert text.count(anker) == 1` sieht das
  wie ein geglueckter Lauf aus. Suchtext aus den ZEILEN bauen und mit `nl`
  verbinden (`nl.join([...])`), nie als dreifaches Anfuehrungszeichen mit LF
  hineinschreiben. Gelesen wird per `open(PFAD, encoding="utf-8", newline="")`
  (Enden bleiben erhalten) oder `"rb"` - Textmodus OHNE `newline=""`
  normalisiert still auf `\n` und macht damit jeden mehrzeiligen Anker
  unauffindbar.
- **Beim Byte-Schreiben NIE pauschal `\n` durch `\r\n` ersetzen.** Die Datei
  traegt schon `\r\n`; ein `d.replace(b"\n", b"\r\n")` auf diesem Inhalt macht
  daraus `\r\r\n` und damit JEDE Zeile zu einer Aenderung. Der Diff zeigt dann
  Insertions in Hoehe der Gesamtzeilenzahl, und der Schaden faellt erst nach dem
  Schreiben auf. Regel: `nl` EINMAL aus dem Rohinhalt ableiten und nur beim
  BAUEN neuer Zeilen verwenden; fertigen Text unveraendert kodieren. Direkter
  Nachweis nach dem Schreiben:

```python
d = open(PFAD, "rb").read()
assert d.count(b"\r\r") == 0, "Zeilenenden verdoppelt - sofort reparieren"
```

  Reparatur ist moeglich ohne Inhaltsverlust: `d.replace(b"\r\r\n", b"\r\n")`
  schreiben, dann `git diff --numstat` erneut pruefen - es muessen nur die
  eigenen Zeilen uebrig bleiben.
- **Der Einfuege-Weg hat dieselbe Falle, nur leiser.** Ein fertiger Block aus
  einem dreifachen Anfuehrungszeichen (`"""..."""`) traegt LF-Zeilen, waehrend
  die Datei CRLF hat - das Ergebnis sind gemischte Zeilenenden. Der Diff sieht
  harmlos aus (79 Insertions), ein Werkzeug, das die Mehrheit zaehlt, arbeitet ab
  da aber auf der falschen Sorte. Regel: JEDE eingefuegte Zeile mit `nl` bauen
  (`block.replace("\n", nl)`), nicht nur die Trennzeilen zwischen den Bloecken.
  Gegenprobe nicht nur auf `\r\r`:

```python
d = open(PFAD, "rb").read()
crlf = d.count(b"\r\n"); lf = d.count(b"\n") - crlf
assert lf == 0, "gemischte Zeilenenden: %d LF-only" % lf
```

  Reparatur ohne Inhaltsverlust, beide Schritte in dieser Reihenfolge:
  `d.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")`.
- **Die Altersregel ist unbrauchbar, solange eine parallele Sitzung laeuft.**
  Die Datei wird zeitweise alle 2-3 Minuten angefasst; ein Zehn-Minuten-Fenster
  kann nach einigen Minuten Warten eintreten (beobachtet: 10,5 min Ruhe nach
  5 min Warten), ist aber kein Verlass und darf nicht als Freibrief gelten.
  Verlaesslich ist eine KOLLISIONSSPERRE in den Schreibvorgang: `mtime` und Groesse nach dem LESEN
  merken, unmittelbar vor dem Schreiben erneut messen und bei Abweichung NICHT
  schreiben - die Datei wird komplett neu gesetzt, ein gleichzeitiger Schreiber
  waere sonst verloren. Das Fenster schrumpft damit von Minuten auf Millisekunden.
- **Die Nachbarsitzung vergibt Nummern weiter, waehrend man plant.** Aus der
  geplanten T-195 wurde binnen Minuten eine fremde Nummer. Statt von Hand
  nachzuziehen die ganze Gruppe beim Schreiben um den Versatz
  `(hoechste + 1) - geplante_erste` verschieben - und zwar VOR dem Einsetzen,
  damit auch QUERVERWEISE in den Texten stimmen. Zwei Durchgaenge mit Platzhalter,
  sonst verschiebt der zweite Lauf die schon verschobenen Nummern erneut:

```python
for n in range(195, 200): text = text.replace("T-%03d" % n, "\x00%d\x00" % n)
for n in range(195, 200): text = text.replace("\x00%d\x00" % n, "T-%03d" % (n + versatz))
```
- **Eine parallele Sitzung kann NUMMERN UMNUMMERIEREN, nicht nur anhaengen.**
  Eine Nummer, die vor Minuten frei war, kann inzwischen von einem umbenannten
  FREMDEN Eintrag belegt sein - die Liste waechst nicht nur, sie wird auch
  umgeschrieben. Deshalb unmittelbar VOR dem Schreiben die Nummernmenge messen
  und unmittelbar DANACH auf Doppelungen pruefen:

```bash
grep -oE '^\s*- \[[ x]\] \*\*T-[0-9]{3}' MaxHirn/Archiv/TASKS.md \
  | grep -oE 'T-[0-9]{3}' | sort | uniq -d
```

  Kommt die eigene Nummer doppelt: den eigenen Block auf die naechsten freien
  Nummern ziehen (der fremde Eintrag bleibt unangetastet), byte-genau ueber den
  eindeutigen TITEL ersetzt - nicht ueber die Nummer, sonst trifft die Ersetzung
  den fremden Eintrag mit.
- **Doppelte Nummern: Einzelfall melden, Haeufung umbauen.** Vereinzelt (eine
  Kollision) den fremden Eintrag NICHT anfassen - er ist gerade in Arbeit -
  sondern melden und die naechste freie Nummer nehmen. Sind es aber viele
  (zehn und mehr sind vorgekommen, eine Nummer dreifach belegt, "T-101"
  bezeichnet drei verschiedene Punkte), ist die Liste nicht mehr benutzbar und
  der Umbau die richtige Antwort. Dann gilt: der **juengere** Eintrag weicht,
  der aeltere behaelt seine Nummer, damit Verweise in aelteren Notizen gueltig
  bleiben; die neuen Nummern fortlaufend ab der hoechsten vergeben; Sicherung
  (`TASKS.md.bak-JJJJMMTT`) vor dem Schreiben.
- **Datum zuerst MESSEN, dann sortieren.** Die Eintraege tragen nicht EIN
  Format: `Angelegt 27.09.2026 · Zuletzt ...`, `Angelegt: 27.09.2026` und
  `Angelegt 2026-09-29` stehen nebeneinander. Ein Sortier- oder Gruppier-Muster
  auf nur eines davon (`Angelegt (\d{2})\.(\d{2})\.(\d{4})`) findet die
  anderen nicht, sie fallen auf einen Platzhalter und rutschen ans ENDE der
  Liste - die Sortierung sieht danach richtig aus und ist es nicht.

```bash
grep -oE "Angelegt:? ?[0-9.-]+" MaxHirn/Archiv/TASKS.md | sort | uniq -c
```

  Erst dieses Ergebnis entscheidet ueber das Muster; Eintraege ohne erkennbares
  Datum vor dem Schreiben einzeln nachtragen.
- **Ein offener Code-Zaun versteckt ganze Abschnitte.** Jede Vorlage braucht
  Oeffner UND Schliesser; die Zahl der Zaun-Zeilen muss gerade sein
  (`grep -c '^```' MaxHirn/Archiv/TASKS.md`). Ein nie geschlossener Zaun im
  `## Eintragsformat` hat 380 Zeilen offene Liste als CODE erscheinen lassen -
  ein Pruefer, der Zaeune beachtet, sah 31 Eintraege nicht und meldete eine
  Blockzahl, die niemand nachvollziehen konnte. Symptom ist eine ZAHL, die nicht
  stimmt; die Ursache ist Struktur. Nach jedem Umbau deshalb zaehlen und die
  Zaun-Zeilen einzeln ansehen, bevor Zahlen diskutiert werden.
- **Der erste Treffer eines Abschnittsnamens ist nicht die Ueberschrift.**
  `## Erledigt` kommt in dieser Datei ZWEIMAL vor: einmal als echte Ueberschrift,
  einmal als Wort im Regeltext weiter oben. Ein Einfuege-Skript, das seine
  offene Liste mit `text.split("## Erledigt")[0]` bildet, haelt damit den
  REGELTEXT fuer die Liste, findet 0 offene Eintraege und laesst seine eigene
  Gegenprobe scheitern (oder, schlimmer, sie geht durch und hat nichts
  geprueft). Abschnittsgrenzen ueber die Zeilen suchen, die es wirklich gibt:
  `text.find("\n## Offen")` fuer den Anfang, `text.rfind("\n## Erledigt")` fuer
  das Ende. Und die offene Liste zusaetzlich ueber die KASTENSTELLUNG zaehlen —
  `alt.count("- [ ] ")` gegen `neu.count("- [ ] ")` muss um genau die Zahl der
  eingefuegten Eintraege steigen; diese eine Zeile faengt sowohl ein
  fehlgeschlagenes Einfuegen als auch einen falsch gefundenen Abschnitt.
- **Ein Block, der beim Schreiben zerschnitten wurde, wird aus `HEAD`
  wiederhergestellt** und dann neu ergaenzt - nicht aus dem Gedaechtnis neu
  formuliert, und nicht einfach der eigene Text vor den Rest gesetzt.

## Nachweis

- `doppelte_nummern.py` gibt 0 zurueck (jede Nummer genau einmal, beide
  Abschnitte vorhanden) - der Beleg ist der Exit-Code, nicht die Ausgabe.

- Abschnitte vor/nach dem Schreiben gleich (`grep -n "^## "`).
- Nummernmenge vor/nach dem Schreiben gleich (plus die neuen).
- `git diff --numstat` zeigt nur die gewollten Zeilen der eigenen Bloecke.
- Nach dem Push: `git show origin/master:MaxHirn/Archiv/TASKS.md | grep -c "T-0NN"`.
