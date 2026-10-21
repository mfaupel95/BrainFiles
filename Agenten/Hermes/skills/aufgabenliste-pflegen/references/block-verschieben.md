# Einen Block verschieben (Offen -> Erledigt)

Wann: ein Eintrag wird abgehakt und nach `## Erledigt` gezogen, oder ein
neuer Eintrag entsteht in der Erledigt-Liste. Das Umhaengen ist der
fehleranfaelligste Vorgang an der Datei, weil dabei zwei Marken (Blockgrenze
und Kastenstellung) und zwei Orte (Abschnitt und Kastenstellung) zusammen
passen muessen - und jeder Fehler im Diff harmlos aussieht.

## Die vier Fehler, die alle dasselbe Skript machten

Sie gehoeren zusammen, weil sie alle aus derselben Ungenauigkeit kommen: der
Schnitt wird ueber ein MERKMAL gesucht, das an mehreren Stellen steht.

### 1. Der Abschnittsname steht auch im Vorabentext

`rest.find("## Erledigt")` trifft zuerst die ERWAHNUNG in der `## Regeln`-Liste
("Erledigtes nach `## Erledigt` verschieben"), nicht die Ueberschrift. Der
Block landet mitten in den Regeln, und die Liste sieht danach vollstaendig aus,
weil ihr eigener Aufzaehlungspunkt mitverschoben wurde - im Test fiel das erst
auf, als die Zeile nur noch „verschieben**, mit Datum. Nicht loeschen" lautete.

**Ueberschriften ueber ihre EIGENE ZEILE suchen, nie ueber den blossen Namen:**

```python
m = re.search(r"(?m)^## Erledigt\r?$", rest)
assert m, "Ueberschrift nicht gefunden"
j = m.end() + len(NL)          # erst HINTER dem Zeilenende einsetzen
```

Dieselbe Falle gilt fuer `## Offen` und jeden anderen Abschnittsnamen, den
der Regeltext einmal erwaehnt.

### 2. `rfind` auf ein Blockmerkmal trifft den FREMDEN Nachbarn

`start = t.rfind("- [ ] **", 0, i)` liefert den naechsten beliebigen
Eintraeg davor. Ist der gesuchte Eintrag zwischenzeitlich verschoben worden
(eine parallele Sitzung sortiert um), ist das ein voellig anderer Task -
gemessen traf der Schnitt einen Nachbarblock mitsamt 28 fremden LF-Zeilen, und
`ende` lief ins Leere, weil dort kein Folgeblock in OFFENER Kastenstellung
stand.

**Am Zeilenanfang der gesuchten Nummer ansetzen:**

```python
i = t.find("**T-315 ")
start = t.rfind("\n", 0, i) + 1        # Zeilenanfang, nicht der vorige Marker
```

**Den herausgeschnittenen Block pruefen, BEVOR er irgendwohin gesetzt wird:**

```python
ende = t.find(NL + NL + "- [", i)       # beide Kastenstellungen
block = t[start:ende]
assert "T-315" in block and "fremdes_stichwort" not in block
```

### 3. `-- [x]` statt `- [x]` nimmt den Block aus der Liste

Der Tippfehler verdoppelt den Bindestrich, und jedes Zaehlmuster
(`- \[[ x]\] \*\*T-`) verliert den Block. Er steht dann an perfekter Stelle in
der Datei und wird trotzdem weder gezaehlt noch verschoben - der naechste
Schnitt findet ihn nicht mehr.

**Deshalb den eingefuegten Block mit dem Zaehlmuster gegenpruefen, nicht mit
einem Blich auf die Zeile:**

```python
assert len(re.findall(r"(?m)^- \[x\]   \*\*T-315", t)) == 1
```

### 4. Die Absatzgrenze muss ZWEI Kastenstellungen tragen

`t.find(NL + "- [ ] **", i)` liefert `-1`, wenn auf den Block ein ERLEDIGTER
Eintrag folgt (`- [x] **T-0…`). Der Block frisst dann die halbe Restdatei
(1328 Zeilen im gemessenen Fall) und der naechste Versuch schneidet daran
weiter.

Besser am naechsten beliebigen Kasten-Marker schneiden:

```python
m = re.search(r"(?m)^- \[[ xX]\]", t[i + 1:])
ende = i + 1 + m.start() if m else len(t)
```

## Die gemeinsame Regel

**Nach JEDEM Verschieben den Block anhand seines Kastenmarkers suchen, nicht
anhand der Absatzgrenzen, mit denen er herausgeschnitten wurde.** Der Schnitt
darf eine falsche Grenze liefern; die Gegenprobe darf sich darauf nicht
verlassen.

## Mehrere Bloecke: rueckwaerts entfernen, Snapshot vergleichen

Wer MEHRERE Eintraege in einem Zug verschiebt, sammelt zuerst alle
Match-Positionen auf dem ORIGINAL-Text und entfernt sie dann nacheinander.
Das ist der Fehler: nach der ersten Entfernung wandern alle spaeteren
Positionen, und der zweite `text[:m.start()] + text[m.end():]` schneidet an
einer verschobenen Stelle - er nimmt den FALSCHEN (Nachbar-)Block mit. Die
Nummernmenge faellt dann um genau die mitgenommenen fremden Nummern, und das
Gate meldet 'Nummernmenge geaendert', ohne zu sagen wo.

**Zwei Regeln, beide Pflicht:**

1. **Rueckwaerts entfernen** - ueber die gespeicherten Start-Positionen
   absteigend sortieren, damit fruehere Entfernungen die spaeteren Positionen
   nicht verschieben:

```python
for num in sorted(NUMMERN, key=lambda n: gefunden[n].start(), reverse=True):
    m = gefunden[num]
    text = text[:m.start()] + text[m.end():]
```

2. **Die Nummernmenge gegen eine SNAPSHOT-Variable des Originals vergleichen,
   nicht gegen den modifizierten `text`.** Nach dem Entfernen ist `text` nicht
   mehr das Original; `ids(neu) == ids(text)` schlaegt dann falsch fehl, weil
   die entfernten Bloecke in `text` fehlen. Vor dem ersten Eingriff
   `original = text` merken und die Gegenprobe gegen `original` fahren.

   Und das Zaehlmuster muss `[ \t]*` zwischen Klammer und `**` zulassen: ein
   Eintrag mit drei Leerzeichen (`- [ ]   **T-324`) faellt aus einem
   Ein-Leerzeichen-Muster, matcht nach dem Verschieben (das die Einrueckung
   normalisiert) aber doch - der Vergleich meldet dann 'Nummernmenge geaendert'
   fuer einen korrekten Zustand. Dasselbe Muster wie im Anker verwenden.

## Gegenproben-Kette

Weil alle vier Fehler erst NACH dem Schreiben auffielen, gehoerte jeder
Einzelgriff unter eine eigene Assert-Zeile. Sie hat jeden abgefangen, bevor
etwas auf der Platte lag - und beim dritten Versuch war die Datei bereits
zweimal in einem Zwischenstand gelandet, den nur `git show HEAD:` zurueckholte.

```python
t2 = open(PFAD, "rb").read().decode("utf-8")
k = t2.find("**T-315")
m = re.search(r"(?m)^## Erledigt\r?$", t2)
assert t2.find("## Erledigt") < k, "Block nicht in der Erledigt-Liste"
assert t2[m.end() + 2:].startswith("- [x]   **T-315"), "nicht direkt danach"
assert len(re.findall(r"\*\*T-315\s*[—-]", t2)) == 1, "Doppel-/Fehlanlage"
assert "## Regeln" in t2 and "- **Erledigtes nach" in t2, "Vorabentext zerlegt"
assert not [n for n in ids if ids.count(n) > 1], "doppelte Nummer"
```

Der Hauspruefer `scripts/doppelte_nummern.py` deckt die letzten beiden ab, aber
nur die Zahlen - **die drei Listenkoennen er fuehrt er nicht.** Ein Block, der
in der Regelliste steht, zaehlt dort als eigener Eintrag und faellt deshalb
durch.

## Und wenn es doch passiert ist

Ein zerlegter Vorabentext wird aus `git show HEAD:MaxHirn/Archiv/TASKS.md`
uebernommen und mit dem richtigen Block erneut besetzt - nicht aus dem
Gedaechtnis formuliert. Die Regelzeile steht in `HEAD` vollstaendig; sie ist
beim Verschieben nur zerschnitten worden.
