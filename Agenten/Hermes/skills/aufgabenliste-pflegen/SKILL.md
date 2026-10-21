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

   **Und zwischen Kastenstellung und `**` darf MEHR als ein Leerzeichen stehen.**
   Die Hausform ist nicht stabil: es gibt `- [ ] **T-338` und daneben
   `- [ ]   **T-336` (drei Leerzeichen, von fremder Hand). Ein Anker mit genau
   EINEM Leerzeichen ueberspringt den Block mit der abweichenden Einrueckung -
   und die Grenze rutscht auf den NAECHSTEN Treffer, sodass der ausgeschnittene
   Bereich den fremden Nachbarn mitnimmt. Regel: `[ \t]*` zwischen Klammer und
   `**` zulassen, und den Treffer gegen die BLOCKZAHL pruefen, nicht nur gegen
   `len(matches) == 1`.

```python
# findet beide Einrueckungen
re.compile(r"(?m)^- \[[ x?]\][ \t]*\*\*(T-\d+)")
```

   **Und die Kastenstellung im Anker ist `[ x?]`, nicht `[ x]`.** Wartende
   Eintraege (`- [?]`, „Wartet auf: Max") fallen sonst aus jeder Suche - wer
   nach „den offenen mit Entscheidungsbedarf" sucht, uebersieht genau die
   Eintraege, die darauf warten.

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
   **Eine Ausnahme gibt es, und sie muss benannt sein: das ENTFERNEN eines
   Eintrags verletzt die Gleichheit absichtlich.** Wird ein Eintrag entfernt statt
   nach `## Erledigt` gezogen (typisch: ein Auftrag, den dieselbe Sitzung
   angelegt und dieselbe Sitzung erledigt hat), faellt die Nummernmenge genau um
   diese eine Nummer - die Regel „vorher/nachher gleich" ist dann falsch und
   schlaegt fehl. Fuer diesen Fall gilt die Ersatzaussage: **genau eine Nummer
   weniger, keine andere Verschiebung**, `ids(neu) - ids(alt) == {entfernte}` und
   `ids(alt) - ids(neu) == {entfernte}`. Wer den Check unveraendert laesst,
   haelt einen korrekten Zustand fuer kaputt und beginnt zu „reparieren".
   Nach dem Entfernen trotzdem beide Abschnitte und den Diff pruefen:
   `git diff --numstat` muss reine Loeschungen zeigen (0 Insertions), und die
   Kopfzeile des Nachfolger-Eintrags muss unveraendert dastehen.
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
   **Der namentliche `git add` allein genuegt NICHT.** Er merkt nur vor; der
   anschliessende `git commit` OHNE Pfadangabe committet den GANZEN Index —
   also auch alles, was eine parallele Sitzung oder eine Routine Sekunden
   vorher vorgemerkt hat. Deshalb zwei Blicke, die Pflicht sind:

```bash
git diff --cached --numstat    # VOR dem Commit LESEN, nicht nur ausfuehren
git commit -m "..."
git show HEAD --stat           # NACH dem Commit: steht hier ein fremder Pfad?
```

   Steht im `--cached`-Ergebnis oder im `--stat` ein Pfad, den man nicht kennt,
   ist er fremd. Dann mit EIGENEM Index committen (`GIT_INDEX_FILE=<scratch>/idx_x`
   + `git read-tree HEAD` + `git add <eigene pfade>` + `git commit`), und danach
   `unset GIT_INDEX_FILE` plus dieselben Pfade im ECHTEN Index nachziehen.
   **Die Deletions sind das Warnsignal:** mehr Loeschungen als der eigene Block
   Zeilen hat heisst immer, dass Fremdtext mitgegangen ist. Belegt: ein
   TASKS-Commit meldete `2 files changed, 15 insertions(+), 382 deletions(-)` —
   die 382 Loeschungen waren eine fremde Datei, die eine Aufraeum-PR entfernt und
   eine Routine Minuten vorher gerade wiederhergestellt hatte. Der eigene Commit
   loeschte sie ein ZWEITES Mal, ohne dass das Wort „Loeschung" in der Meldung
   stand.
   **Ruecknahme einer mitgefahrenen Loeschung: FOLGE-Commit, nie `--amend`.**
   Die Datei liegt meist noch auf der Platte (`git add <pfad>` holt sie zurueck),
   und ein Umschreiben der Historie trifft in diesem Baum fremde Arbeit im
   geteilten Index.
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
  Tor vor dem Committen nutzen, nicht als Blick. **Ein Tor wirkt nur in einem
  EIGENEN Aufruf.** In einer Sammelkette (`gate; git add …; git commit …`) laeuft
  der Commit trotz Exit 1 weiter - die doppelte Nummer ist dann committet, bevor
  sie jemand sieht, und es braucht einen Folge-Commit. Also: Gate fahren, `$?`
  lesen, und erst im NAECHSTEN Aufruf stagen und committen. Zaun-bewusst: Zeilen innerhalb
  eines Code-Zauns (die Format-Vorlage) zaehlen nicht als Eintrag.
  `cd "$HERMES_HOME/../.." && python Agenten/Hermes/skills/aufgabenliste-pflegen/scripts/doppelte_nummern.py --ruhig`
  **Der Pfad ist ein SCHALTER, kein positionales Argument:** `--pfad
  MaxHirn/Archiv/TASKS.md`. Die Form `doppelte_nummern.py
  MaxHirn/Archiv/TASKS.md` bricht mit `unrecognized arguments` ab — die Meldung
  liest sich wie ein fehlendes Argument, nicht wie eine falsche Schreibweise, und
  wer die Zeile als Ergebnis deutet, haelt das Gate fuer kaputt. Ohne `--pfad`
  nimmt das Skript die Vorgabe (die Datei des Hauses).
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
  **Und es findet nur Eintraege unter `## Offen`.** Eine parallele Sitzung kann
  einen Task in einem EIGENEN `## T-NNN`-Abschnitt NACH `## Erledigt` anlegen
  (am Dateiende) — dann meldet erledigen.py „steht nicht in '## Offen'" und
  verweigert. Das ist kein fehlender Eintrag, sondern ein falsch platzierter:
  ueber den Byte-Weg schliessen (`- [ ]` -> `- [x]`), ohne ihn zu verschieben —
  das Aufraeumen der Struktur ist ein eigener Auftrag, nicht Teil des
  Schliessens.
  **Und die Meldung kann auch heissen: eine parallele Sitzung hat den Task
  SCHON erledigt.** Bevor man einen „steht nicht in '## Offen'"-Fehlschlag als
  Strukturproblem deutet, `grep -n "T-0NN"` ueber die ganze Datei: steht der
  Eintrag bereits als `- [x]` unter `## Erledigt`, ist die Aufgabe fertig und
  der Fehlschlag korrekt — nichts nachziehen, nichts verschieben, nur
  verifizieren und weiter. Ein zweiter erledigen-Lauf auf einen schon
  erledigten Task ist eine Doppelarbeit, die den Belegsatz ueberschreibt.

Die Nummer gehoert MIT Praefix: `erledigen.py 206` meldet „206 kommt 0x vor“ —
das liest sich wie ein fehlender Eintrag, ist aber die falsche Argumentform
(`T-206`).

Die Format-Vorlage steht in `## Eintragsformat` und traegt `T-0NN` - niemals eine echte Nummer, sonst zaehlt sie als zweiter Eintrag.

## Fallen

- **Ein Nummernmuster muss die HAUSFORM lesen, sonst zaehlt es null.** Die
  Kopfzeile lautet `- [ ] **T-NNN \u2014 Titel` - ein **Em-Dash** steht direkt
  hinter der Nummer. Ein Muster mit `\*\*` NACH der Nummer
  (`\*\*(T-\d+)\*\*`) trifft hier **0** Eintraege; `max()` auf dieser leeren
  Menge bricht ab, und der Fehler liest sich wie ein kaputtes Skript statt wie
  ein zu enges Muster. **Das Muster vor dem Lauf gegen die echte Datei messen**,
  nicht die Trefferzahl glauben:
```python
print(len(re.findall(r"- \[[ x]\] \*\*(T-\d+)", t)))     # 326
print(len(re.findall(r"- \[[ x]\] \*\*(T-\d+)\*\*", t)))  # 0
```
  `(-\w+)` ist das Muster, das sich in \u00dcberarbeitungen als Klassen-tauglich
  bewiesen hat; die Kastenstellung gehoert dazu (`[ x]` und `[?]`, nicht nur
  `[ x]`), sonst fallen wartende Eintraege aus der Zaehlung.
- **Die LF-Gegenprobe vergleicht VORHER mit NACHHER, nicht mit einer alten Zahl.**
  Der Einbau-Vorfall: die Datei trug 18 LF-only aus fremder Hand (die bleiben
  duerfen), und der Check verglich gegen die vor dem Skript gespeicherte Zahl
  \u2014 fehlgeschlagen mit „eigene LF eingeschlichen", ohne zu sagen **wo**. Die
  richtige Aussage ist ein Vergleich zweier gleich gebauter Texte:
```python
lf = lambda a: a.count("\n") - a.count("\r\n")
assert lf(neu) == lf(text)          # 18 -> 18
```
  **Und jede Zeile, die der eigene Vorgang baut, traegt `nl`** - auch der
  Trenner zwischen Kopfzeile und Block. Ein nacktes `"\n"` an dieser Stelle war
  genau die eine eingeschlichene LF (18 -> 19); der Block selbst war korrekt,
  der Diff sah harmlos aus, und nur die Bilanz fand es. Bei einer Datei mit
  fremden LF-Zeilen ist die LF-Bilanz die einzige Probe, die eine eingeschlichene
  LF zuordnet \u2014 `assert lf == 0` waere hier falsch und wuerde einen richtigen
  Zustand als kaputt melden.
- **Ein alter Block-Replace laeuft ueber die neue Zuweisung, wenn er weiter
  unten steht.** Wer denselben Wert zweimal setzt (zuerst im if/else, dann nach
  dem Block) hat die korrigierte Fassung stillschweigend wieder verworfen, und
  der Fix tut nichts. Nach zwei Zuweisungen auf dieselbe Variable im selben
  Skript: `grep -n "<name> =" <datei>` und zaehlen, welche uebrig bleiben soll.
- **Bevor ein Eintrag eine LUECKE behauptet ("X fehlt", "keine Wache", "nicht vorhanden"), die Luecke im Baum pruefen** - `scripts/`, `cron/jobs.json`, `git log -- <pfad>`. Eine parallele Sitzung oder fruehere Arbeit kann sie schon geschlossen haben; ein falscher "fehlt"-Eintrag wird zur Aufgabe, die eine zweite Sitzung dann "loest" und dabei die vorhandene Loesung ueberschreibt oder dupliziert. Belegt: ein Eintrag "es gibt KEINE Junction-Wache" stand, waehrend `junction-wache.py` seit Tagen committet war und den Verlust schon gemeldet hatte - die Korrektur kostete einen Folge-Commit und einen falschen T-400. Wer eine Luecke eintragen will, sucht zuerst nach dem Artefakt (Datei, Cron-Eintrag, Commit), nicht nach dem Gefuehl.
- **Die hoechste Nummer NIE aus dem Gedaechtnis nehmen.** Die eigene
  Memory-Notiz nennt einen Stand von gestern ("hoechste am 24.09.: T-056");
  gemessen am 29.09.2026 stand die Datei bei T-159, und die aus dem Kopf
  gewaehlte Nummer war doppelt vergeben. Immer messen:

```bash
grep -oE "T-[0-9]+" MaxHirn/Archiv/TASKS.md | sort -u -t- -k2 -n | tail -3
```

  **Und die Nummer, die dabei herauskommt, ist nicht immer frei — sie kann der
  eigene Text sein.** Ein Verweis im `Erledigt`-Belegsatz ("Folgeaufgabe
  T-368") zaehlt im weiten Muster mit, obwohl es gar keinen Eintrag mit dieser
  Nummer gibt. Vor dem Anlegen gegen die EINTRAGSFORM pruefen, nicht gegen die
  blosse Ziffer:

```bash
grep -cE "^- \[[ x]\] \*\*T-368" MaxHirn/Archiv/TASKS.md   # 0 = Nummer ist frei
```

  Sonst weicht man auf eine hoehere Nummer aus, die niemand braucht, und der
  Querverweis im Belegsatz zeigt auf die falsche Aufgabe.
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
- **Das generische `patch`-Werkzeug ist fuer diese Datei der falsche Weg.** Es
  passt Aenderungen fuzzy an, verschiebt dabei die EINRUECKUNG des Ersatzblocks
  und frisst in einer Liste die Nachbarzeile (beobachtet: zweimal am selben
  Block, das zweite Mal schlimmer - erst verrutscht, dann eine Zeile weg und
  `Angelegt/Zuletzt` mitten im Absatz). Nach dem ERSTEN verrutschten Ergebnis
  nicht weiterflicken: den Block per Zeilenindex in Python ersetzen
  (Zeilen lesen, `i`/`j` ueber das Blockmerkmal finden, `zeilen[i:j+1] = neu`),
  mit CRLF-Zaehler und `git diff --numstat` nachpruefen und den Block danach
  ausdrucken.
- **Das fuzzy `patch`-Werkzeug korrumpiert auch Code-Dateien (nicht nur
  TASKS.md) - in zwei Formen.** (1) STRING-LITERALE: bei einem Python-Test
  wurde `self.assertIn("leeres Ziel", text)` in mehreren Versuchen zu
  `"leereseres Ziel"`, `"le"leeres Ziel"` und `"letIn("leeres Ziel"` verhunzt -
  der Matcher dupliziert und verschiebt Zeichen INNERHALB der
  Anfuehrungszeichen. (2) EINRUECKUNG: ein Ersatzblock mit ungleichmaessigen
  Spaces wird um +4 Spaces verschoben und erzeugt `IndentationError` - zwei
  Reparaturversuche scheitern erneut, weil jeder weitere patch auf dieselbe
  Datei es schlimmer macht. Beide Formen sind dasselbe Abbruchsignal: ab dem
  ERSTEN korrumpierten String ODER dem ersten IndentationError nicht
  weiterpatchen, sondern die Datei komplett neu schreiben. Der Weg um den
  `write_file`-Schutz (Datei gilt als 'partial view', wenn sie mit
  offset/limit gelesen wurde): Inhalt nach
  `Agenten/Hermes/cache/scratch/<name>_fix.py` schreiben, dann `cp` ueber das
  Ziel, und mit `py_compile` pruefen. Ein patch, der einen String-Tippfehler
  oder eine IndentationError einfuehrt, ist ein Abbruchsignal, kein
  Reparaturversuch.
- **`write_file` verweigert die Datei** (kein vollstaendiger Lesevorgang dieser
  Sitzung) - ueber den Byte-Weg schreiben, nicht die Datei komplett neu setzen.
- **Python wertet `open(p, "wb")` aus, BEVOR der Schreibausdruck gebaut ist.**
  `open(p,'wb').write(b.replace(anker, anker + block))` kuerzt die Datei auf null
  Bytes, wenn der Ausdruck danach scheitert (typisch: bytes + str, Groessen-
  assert, Tippfehler im Variablennamen). Payload ZUERST in eine Variable bauen,
  `assert neu != b` plus Groessen-Delta pruefen, `open(...,'wb')` erst in der
  allerletzten Zeile. War die Datei vor dem Fehlversuch sauber gegen HEAD
  (`git status --porcelain <pfad>` leer), heilt `git checkout HEAD -- <pfad>`;
  der Pruefer (`doppelte_nummern.py`) muss danach gruen sein. War sie es NICHT,
  ist der Verlust endgueltig - dann ist die parallele Arbeit gemeldet, nicht
  heimlich ersetzt.
  **Der Ausweg aus dem Null-Byte-Zustand ist `git show HEAD:<pfad>`, und der
  Umweg dorthin lohnt sich:** `git show HEAD:MaxHirn/Archiv/TASKS.md > <datei>`
  schreibt die Datei byte-genau (inklusive CRLF) zurueck, danach
  `git diff --numstat <pfad>` - leer heisst "byte-identisch mit HEAD", das ist
  der Beweis, und `doppelte_nummern.py` muss gruen sein. **Ein leeres
  `git diff` ist hier das ERWUENSCHTE Ergebnis, nicht ein Fehlerzeichen.**
  Wer stattdessen die letzte Sicherung (.bak) zurueckholt, verliert alles, was
  seitdem committet wurde.
  **Und danach in Skriptdateien, nicht in Heredocs.** Der Schreibvorgang gehoert
  nach `Agenten/Hermes/cache/scratch/<zweck>.py` und wird mit
  `python -m py_compile <datei>` geprueft, BEVOR er laeuft. Ein Tippfehler im
  Variablennamen ist dann ein Syntaxfehler VOR dem ersten `open()` und wird
  gemeldet, ohne dass die Datei je gekuerzt wurde - im Heredoc ist er ein
  Laufzeitfehler HINTER dem `open()`. Zwei Korrekturen an derselben Datei in
  einem Zug (Payload bauen, dann `open` als letzte Zeile) sind Pflicht, sobald
  ein erster Versuch gescheitert ist: die zweite Korrektur trifft denselben Weg.
  Der Scratch-Pfad ist zugleich der Weg um `$TMPDIR` herum: `python /tmp/x.py`
  scheitert unter Windows mit `can't open file 'C:\tmp\x.py'`, weil das native
  Python `$TMPDIR` nicht auf `/tmp` abbildet - ein C:-Pfad funktioniert.
  **Nach dem Schreiben immer die EIGENEN Zeilen gegen die fremden zaehlen, nicht
  die ganze Datei:** `roh.count(b"\n") - roh.count(b"\r\n")` vor und nach dem
  Vorgang muss GLEICH sein, sonst hat der eigene Block Zeilenenden eingeschlichen
  (siehe naechster Punkt). Gesamtzeilenzahl gleich ist dafuer keine Probe - eine
  faelschlich gebaute Korrektur kann beide Zahl und Inhalt verschieben, ohne
  dass ein globaler Zaehler es zeigt.
- **Eine gemischte Datei ist der NORMALZUSTAND, kein Abbruchgrund.** Beim Byte-Schreiben zuerst `roh.count(b"\r\n")` gegen `roh.count(b"\n")` stellen und daraus das **dominante** Ende ableiten (`crlf > lf_gesamt - crlf`); ein Skript, das bei Mischung abbricht, verhindert genau den Fall, den man kennt — und der haeufigste ist. Voraussetzung ist nur, dass der Schnitt **nichts normalisiert**: der neue Block bekommt das dominante Ende, alle bestehenden Zeilen bleiben unangetastet. Die Vorpruefung „Datei ist gemischt, also riskant" ist damit eine Pruefung ohne Aussage — der Beweis ist `git diff --numstat` (reine Einfuegungen, 0 Loeschungen), nicht die Vorpruefung. Ein Skript, das misst und dann **trotzdem abbricht**, traegt eine Regel in sich, die es nie pruefen wollte: lieber messen und den Diff sprechen lassen.

- **Ein Sichtfenster (`sed -n '1,40p'`) zeigt nur den Kopf.** Die eigene Aufgabe
  steht weiter unten: erst `grep -n "T-0NN"` suchen, dann Vorgaenger- und
  Nachfolgerblock lesen, bevor ersetzt wird.
- **Zeilenenden sind CRLF.** `open(..., "w")` dreht die Datei auf LF und erzeugt
  einen Ganzdatei-Diff; Gegenprobe `git diff --numstat`.
  **Und die Sorte wird an BYTES gemessen, nicht an einer Ausgabe.** Eine
  Ansicht (`sed`, `cat -A`, Editor, ein Diff-Fenster) kann das `^M` verschlucken
  und eine CRLF-Datei wie eine LF-Datei zeigen; eine Byte-Zaehlung nicht:
  `r.count(b"\r\n")` gegen `r.count(b"\n") - r.count(b"\r\n")`. Eine
  Vorpruefung, die die falsche Sorte erwartet (`assert b.count(b"\r\n") == 0`),
  bricht den Schreibvorgang ab, obwohl die Datei gesund ist - erst zaehlen,
  dann `nl` waehlen.
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
  Gegenprobe nicht nur auf `\r\r` - und **nicht** `assert lf == 0`: eine
  parallele Sitzung hat in dieser Datei schon LF-Zeilen hinterlassen, die
  bleiben duerfen. Richtig ist, dass der eigene Vorgang **keine neuen**
  einfuegt:

```python
vor = open(PFAD, "rb").read()
lf_vor = vor.count(b"\n") - vor.count(b"\r\n")
# ... Text bauen, Bytes kodieren ...
assert nb.count(b"\n") - nb.count(b"\r\n") == lf_vor, "eigene LF-Zeilen eingeschlichen"
assert nb.count(b"\r\r") == 0
```

  Reparatur ohne Inhaltsverlust, beide Schritte in dieser Reihenfolge:
  `d.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")`.
  **Und der EINFUEGEORT ist keine Zeilengrenze.** Wer ihn per
  `j = text.find("\n## Offen")` bzw. `text.find("\n- [ ] **T-")` sucht, hat den Index
  des `\n` - das Zeichen DAVOR ist in einer CRLF-Datei das `\r`. Ein
  `text[:j] + nl + block` setzt damit ein ZWEITES `\r` und erzeugt `\r\r\n` plus eine
  LF-only-Zeile; die Gegenprobe meldet `CRCR 1 | LF-only 1`, obwohl der Block richtig
  dasteht und der Diff harmlos aussieht. Richtig ist, HINTER dem `\n` einzusetzen und
  die Zeilenschuld selbst zu tragen:
  `neu = text[:j+1] + block.replace("\n", nl) + nl + text[j+1:]` - und die drei Zahlen
  vor dem Schreiben asserten (`\r\r` == 0, LF-only == 0, Kaesten `- [ ] ` genau +1 je
  neuem Eintrag), nicht erst danach nachsehen.
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
  **Die Kollision trifft auch den EIGENEN neuen Eintrag - und dann erst nach dem
  Schreiben.** Der Gang: hoechste Nummer gemessen, zwei eigene Eintraege
  darunter eingetragen, Gate gefahren - und das Gate meldet `DOPPELT`, weil eine
  parallele Sitzung in den Minuten dazwischen SELBST dreie neue Nummern vergeben
  hat (gemessen: eigene T-343/T-344 gegen fremde T-343/T-344/T-345, dieselben
  Zahlen, anderer Inhalt). Deshalb gilt die Reihenfolge: **Gate NACH dem
  Schreiben ist Pflicht, nicht Nachsorge**, und die Korrektur ist eine
  UMBENENNUNG ueber den eindeutigen TITEL, nicht ueber die Nummer:

```python
kopf = "- [ ] **T-343 — <eigener Titel>"
i = t.index(kopf); j = t.index("<Anfang des naechsten Blocks>", i)
t = t[:i] + block_mit_neuer_nummer + t[j:]      # nur die Zahl im eigenen Block
```

  Der fremde Eintrag mit derselben Nummer bleibt unangetastet, und sein Inhalt
  entscheidet, wessen Nummer gilt - hier behielt der fremde (er war aelter),
  also wanderte der eigene auf die naechsten freien Nummern **ueber der
  fremdenhoehe**, nicht darunter. Zwei eigene Bloecke wandern gemeinsam und
  bekommen eine gemeinsame Endnummer, sonst zerfallen sie ueber die fremde
  Nummerfolge. **Im Blocktext mitgeschleppte Querverweise auf die eigenen
  Nummern** (im Kontext, im `Betrifft:`) mitziehen - sonst zeigt der
  umbenannte Block auf eine fremde Nummer. Gegenprobe nach der Umbenennung:
  das Gate erneut, und der Blick auf den Block, ob der Fremde wirklich
  unveraendert dasteht.
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
- **Der `## Offen`-Abschnitt sammelt erledigte Eintraege an — die Zahl der
  Bloecke ist NICHT die Zahl der offenen Aufgaben.** Gemessen: 143 Bloecke im
  Abschnitt, davon 22 mit `- [x]` (fertig, aber nie nach `## Erledigt` gezogen).
  Wer die Blockzahl als „so viele offene Punkte" berichtet, gibt eine zu hohe
  Zahl weiter und uebersieht, dass Aufraeumarbeit ansteht. Richtig zaehlen:

```python
# je Kastenstellung getrennt, im Offen-Bereich
print(bereich.count("- [ ] "), bereich.count("- [x]"), bereich.count("- [?]"))
```

  Beim Zusammenfassen fuer Max die ECHTEN offenen nennen und die liegen
  gebliebenen `- [x]` als eigenen Aufraeumpunkt anbieten - nicht mitzaehlen und
  nicht stillschweigend nach `## Erledigt` schieben (das ist ein eigener Auftrag,
  weil dabei Nummern und Abschnitte gegenprueft werden muessen).
- **Der erste Treffer eines Abschnittsnamens ist nicht die Ueberschrift — und
  derselbe Abschnittsname kann DREIMAL vorkommen.** `## Erledigt` steht zweimal
  (echte Ueberschrift plus eine Erwaehnung im Regeltext weiter oben);
  `## Offen` kann ebenso zweimal vorkommen, und zwar als **Vorlage** ganz vorn
  UND als echte Liste weiter unten. Ein Einfuege-Skript, das seine offene Liste
  mit `text.split("## Erledigt")[0]` bildet, haelt damit den REGELTEXT fuer die
  Liste, findet 0 offene Eintraege und laesst seine eigene Gegenprobe scheitern
  (oder, schlimmer, sie geht durch und hat nichts geprueft). Ein Skript, das
  `text.find("## Offen")` nimmt, landet in der VORLAGE: der Eintrag wird
  geschrieben und niemand sieht ihn, weil die Liste unveraendert bleibt.
  Abschnittsgrenzen ueber die Zeilen suchen, die es wirklich gibt:
  `text.find("\n## Offen")` fuer den Anfang, `text.rfind("\n## Erledigt")` fuer
  das Ende — und **alle** Vorkommen zaehlen (`text.count(...)`), dann das
  RICHTige nehmen: die Ueberschrift, unter der Eintraege stehen, nicht die
  frueheste. Die Wahl ist damit begruendbar statt geraten.
  **Dritte Form: zwei ECHTE Listen.** Eine parallele Sitzung kann ihren eigenen
  `## Offen`-Block VORN voranstellen, waehrend die alte Liste unveraendert weiter
  unten steht - beide mit Eintraegen. `doppelte_nummern.py` meldet dann trotzdem
  „beide Abschnitte vorhanden“ und ist gruen (es prueft nur das VORHANDENSEIN),
  die Doppelung ist also ein Struktur-Befund, kein Grund fuer einen Umbau. Neue
  Eintraege gehoeren in den OBEREN Block, direkt vor seinen ersten Eintrag
  (`i = text.index("## Offen")`, `j = text.index("- [ ] **T-", i)`, Einsetzen
  hinter `j`) — dort stehen die neuesten, und `erledigen.py` findet sie ebenfalls.
  Den doppelten Kopf im Bericht nennen, nicht stillschweigend entfernen: das
  Aufraeumen der Struktur ist ein eigener Auftrag, weil dabei Nummern und
  Abschnitte gegenzupruefen sind.
  **Und die REIHENFOLGE der Abschnitte ist nicht stabil.** Eine parallele
  Sitzung kann `## Erledigt` UEBER `## Offen` ziehen (gemessen: Erledigt bei
  Position 508, Offen bei 3109). Ein Schnitt `text[offen:erledigt]` mit
  `offen > erledigt` ist dann LEER, jede Regex darauf findet still nichts und
  meldet „0 Eintraege" — ein Befund, der nie geprueft wurde. Vor dem Schnitt
  beide Positionen suchen und `min`/`max` nehmen (oder ueber die Liste der
  Ueberschriften arbeiten), nie die Reihenfolge voraussetzen. Und die offene
  Liste zusaetzlich ueber die KASTENSTELLUNG zaehlen —
  `alt.count("- [ ] ")` gegen `neu.count("- [ ] ")` muss um genau die Zahl der
  eingefuegten Eintraege steigen; diese eine Zeile faengt sowohl ein
  fehlgeschlagenes Einfuegen als auch einen falsch gefundenen Abschnitt.
- **Eine schon COMMITTETE Doppelnummer wird im Folge-Commit geradegezogen, nie
  durch Umschreiben der Historie.** Nur die eigene Nummer aendern (Anker = der
  eindeutige Titel, nicht die Nummer), danach das Gate erneut fahren; die
  Commit-Meldung nennt die Doppelung und dass nur die Nummer wechselte. Ein
  `--amend` oder force-push trifft in diesem Baum fremde Arbeit im selben Index.
- **Ein Block, der beim Schreiben zerschnitten wurde, wird aus `HEAD`
  wiederhergestellt** und dann neu ergaenzt - nicht aus dem Gedaechtnis neu
  formulieren, und nicht einfach der eigene Text vor den Rest gesetzt.
- **Ein eigener Block wird in EINEM Zug ersetzt, nie in zwei Index-Schritten.**
  Wer erst `block.split(nl)`, dann `zeilen.insert(1, beleg)`, dann spaeter
  `zeilen.pop()` fahrt, verliert dazwischen Zeilen: das `pop()` entfernt die
  Zeile, die gerade eingefuegt wurde, nicht die alte - das Ergebnis ist ein
  Block, in dem eine Zeile fehlt, und die Datei ist byte-kleiner, obwohl der
  Schnitt auf die richtigen Zeilen zeigte. Der Block wird fertig gebaut (Kopf +
  Beleg + Kontext + Naechster Schritt + Betrifft) und in einem Rutsch
  eingesetzt; jede Umordnung ist ein Neuschreiben des Blocks, kein Verschieben
  von Teilstuecken. Gegenprobe: **Zeilenzahl des neuen Blocks muss
  Zeilenzahl des alten plus eigene Zeilen sein**, und `git diff --numstat` muss
  reine Insertions zeigen (eine Zeile Loeschung ist die Kopfzeile, die mit
  `[ ]` auf `[x]` wechselt - mehr Loeschungen bedeuten Fremdtext).

## Überholte Tasks systematisch finden

Ein Task, der eine Zahl oder einen Zustand nennt („Kraken 0,71 EUR frei",
„Provider codex hat keine aktiven Keys"), kann überholt sein — die Zahl hat sich
geändert, ohne dass jemand den Task geschlossen hat. Die Prüfung ist die
Messung gegen die Wirklichkeit, **nicht das Alter**: ein Task, der 100 Tage alt
ist, kann noch aktuell sein; ein Task, der eine Woche alt ist, kann überholt sein.

**Verfahren:**
1. Alle offenen Blöcke mit Zahlen extrahieren (Muster: `\b\d{2,7}\s*(?:Einträge|Dateien|Zeilen|GB|MB|Tests|Runden|Commits)`).
2. Jede genannte Zahl gegen die aktuelle Wirklichkeit messen (API-Aufruf,
   `git ls-files`, `Get-ChildItem`, Datenbankabfrage).
3. Stimmt die Zahl nicht mehr: Task als überholt schließen, mit Beleg
   („gemessen heute: X, Task sagte Y").
4. Stimmt die Zahl: Task bleibt offen, auch wenn er alt ist.

**Fallen:**
- **Ein relativer Pfad ohne Kontext ist kein Befund.** Die meisten Blöcke
  nennen `wachen.json` ohne Spur-Ordner — ein Pfad-Check ohne den
  übergeordneten Ordner erzeugt Dutzende Fehlalarme. Erst die Verengung auf
  *genannte Zahlen gegen die Wirklichkeit* liefert belastbare Treffer.
- **Das Alter sortiert, es beweist nicht.** Eine Liste nach `Angelegt`-Datum
  sortiert zeigt die aeltesten zuerst, aber „alt" heißt nicht „überholt".
  Die Reihenfolge ist ein Kandidaten-Filter, kein Ergebnis.
- **Ein Beleg gehört VOR die Strukturzeilen (`Angelegt`/`Betrifft`), nicht
  hinter sie.** Der Block endet mit `Betrifft:`, ein Anhängen danach landet
  außerhalb der Struktur. Einfügestelle: vor der ERSTEN `Angelegt`-Zeile
  innerhalb des Blocks.
- **Die Gegenprobe für die Einfügestelle muss INNERHALB des Blocks sein.**
  `neu.index("BELEG") < neu.index("Angelegt")` über die ganze Datei findet
  das erste Vorkommen — das kann ein fremder Block sein. Richtig: den neuen
  Block extrahieren und darin prüfen.
- **`Assert` ist PowerShell-Syntax, nicht Python.** Ein Python-Skript mit
  `Assert ma, "..."` bricht mit `SyntaxError: invalid syntax` ab. In Python
  heißt es `assert` (klein). Bei Fehlversuchen mit `Assert` zuerst die Syntax
  prüfen, nicht den Logikfehler suchen.
- **`erledigen.py` nimmt nur `- [ ]` an.** Ein Eintrag in anderer Kastenstellung
  (`- [?]`, `- [!]`) wird über den Byte-Weg geschlossen. Die Meldung
  „ist schon abgehakt" meint „nicht `- [ ]`", nicht „bereits erledigt".

## Block verschieben (Offen -> Erledigt)

Der fehleranfaelligste Vorgang an der Datei. Vier Fehler treten gehaeuft
miteinander auf, weil der Schnitt ueber ein MERKMAL laeuft, das an mehreren
Stellen steht:

1. `find("## Erledigt")` trifft die ERWAHNUNG im Vorabentext der `## Regeln`-
   Liste, nicht die Ueberschrift - Ueberschriften ueber `(?m)^## .*$` suchen.
2. `rfind("- [ ] **", 0, i)` trifft den FREMDEN Nachbarn - am Zeilenanfang der
   gesuchten Nummer ansetzen (`t.rfind("\n", 0, i) + 1`).
3. `-- [x]` statt `- [x]` nimmt den Block aus jedem Zaehlmuster - den
   eingefuegten Block mit dem Zaehlmuster gegenpruefen, nicht ansehen.
4. Eine Absatzgrenze auf `- [ ] ` greift nicht, wenn ein ERLEDIGTER Block
   folgt - am naechsten beliebigen Kasten-Marker schneiden.

**Gemeinsame Regel: nach jedem Verschieben den Block anhand seines
Kastenmarkers suchen, nicht anhand der Absatzgrenzen, mit denen er
herausgeschnitten wurde.** Der Schnitt darf eine falsche Grenze liefern, die
Gegenprobe nicht.

**Beim Verschieben die Original-Bloecke ZUERST aus dem Text entfernen, dann die
neuen einfuegen.** Wer nur die neuen Eintraege nach `## Erledigt` einsetzt, ohne
die alten aus `## Offen` zu loeschen, hat die verschobenen Eintraege doppelt -
die Nummernmenge waechst um genau die verschobene Zahl, und das Gate meldet
nichts, weil jede Nummer noch einmal vorkommt. Die Bloecke rueckwaerts loeschen
(ueber die gespeicherten Match-Positionen), damit die Positionen nicht wandern.

**Die Nummernmenge gegen eine SNAPSHOT-Variable des Originals vergleichen, nicht
gegen den modifizierten Text.** Nach dem Entfernen der Bloecke ist `text` nicht
mehr das Original; `ids(neu) == ids(text)` schlaegt dann falsch fehl. Vor dem
ersten Eingriff `original = text` merken und die Gegenprobe gegen `original`
fahren.

**Das Zaehlmuster muss `[ \t]*` zwischen Klammer und `**` zulassen.** Ein
Eintrag mit drei Leerzeichen (`- [ ]   **T-324`) faellt aus einem
Ein-Leerzeichen-Muster; nach dem Verschieben (das die Einrueckung normalisiert)
matcht er dann doch, und der Vergleich meldet 'Nummernmenge geaendert', obwohl
nur die Einrueckung abwich. Dasselbe Muster wie im Anker verwenden.

Die Gegenproben-Kette (Abschnitt, Kastenstellung, Fundstelle, Vorabentext,
Nummernmenge) und der Ablauf bei bereits zerlegtem Vorabentext stehen in
`references/block-verschieben.md`.

## Nachweis

- `doppelte_nummern.py` gibt 0 zurueck (jede Nummer genau einmal, beide
  Abschnitte vorhanden) - der Beleg ist der Exit-Code, nicht die Ausgabe.

- Abschnitte vor/nach dem Schreiben gleich (`grep -n "^## "`).
- Nummernmenge vor/nach dem Schreiben gleich (plus die neuen).
- `git diff --numstat` zeigt nur die gewollten Zeilen der eigenen Bloecke.
- Nach dem Push: `git show origin/master:MaxHirn/Archiv/TASKS.md | grep -c "T-0NN"`.
