# Eine bestehende Spur pruefen, haerten und messbar machen

Ausloeser: „Suche nach Luecken oder Optimierungspotential", „Code optimieren",
„mach X sichtbar", „setze die Empfehlung um" - und jedes Durchsehen einer
Spur, die laeuft, aber deren Ergebnisse niemand zerlegt. Beleg: Omniquant und
Spiegel, 13.09.2026 - ein Review fand fuenf echte Fehler in einer Spur, die im
Dauerlauf als „(papier) ok" stand.

## Der Ablauf in fuenf Phasen

### 1. Auftrag einordnen - was heisst hier „fertig"?

Vier Auftragsarten, vier Definitionen:

- **Feature umsetzen** -> Mechanik + Test + echter Lauf + Doku.
- **Code optimieren / Luecken suchen** -> gefundener Befund + Fix + ein Test,
  der den Befund festhaelt. Ein Review ohne Test ist eine Meinung.
- **Sichtbar machen** -> eine Quelle, mehrere Anzeigen; jede gerendert.
- **Fakt eintragen** (Kostenregel, neue Grenze) -> NUR dokumentieren, keine
  Werte aendern. Ein Doku-Auftrag, der Zahlen umlegt, ist ein anderer Auftrag -
  und braucht eine eigene Entscheidung.

### 2. Die ganze Datei lesen, dann verdaechtigen

Nicht querlesen: die Datei in zwei, drei `read_file`-Aufrufen ganz holen, erst
danach Hypothesen bilden. Die Muster unten findet man nicht, wenn man nach
einem Stichwort sucht - sie stehen dort, wo niemand hinschaut.

### 3. Verdachtsmuster (Checkliste)

Jedes Muster ist in dieser Sitzung real aufgetreten; das Muster bleibt, der
Einzelfall ist austauschbar.

1. **Toter Code mit Docstring-Behauptung.** `_kostenfaktor()` war definiert,
   nie gerufen - und der Docstring von `_ergebnis()` behauptete, der Einstieg
   sei damit eingepreist. War er nicht: das Buch rechnete eine Kostenseite
   statt zwei, um 0,25 % je Trade zu optimistisch, genau bei der Kernfrage.
   Pruefung: jede Funktion der Datei mit `search_files` suchen und die Aufrufer
   zaehlen; jede Behauptung im Docstring muss durch Code gedeckt sein.
2. **Feldnamen gegen die Schreiberseite pruefen.** Eine GUI-Fusszeile las drei
   Felder, die es im Zustand nie gibt (dauerhaft „?" und „0 USD", Kill-Switch
   auf „frei" auch bei gerissenem Deckel). Pruefung: jedes gelesene Feld gegen
   den Schreiber suchen - nicht gegen die Erinnerung.
3. **Zu enge Ausnahmeklasse.** `except ValueError` um
   `datetime.fromisoformat(...)` plus Subtraktion: ein Zeitstempel ohne Zone
   wirft TypeError, die Ausnahme faengt ihn nicht, der Zyklus stirbt.
   Pruefung: was kann dieser Ausdruck werfen (TypeError, KeyError,
   AttributeError, ZeroDivisionError)?
4. **Parameter ohne Wirkung.** `_nominal(inst, kurs)` ignorierte beide
   Argumente; `schliesse(..., live)` nutzte `live` nie. Sieht wie Logik aus,
   ist Attrappe - und suggeriert beim naechsten Lesen eine Rechnung.
   Dieselbe Familie: **ein Argument, das im FALSCHEN Parameter landet**, weil es
   positionell uebergeben wurde. Signatur `bewerten(kerzen, richtung="long",
   gewichte=None)`, Aufruf `bewerten(k, g)` -> `g` wird zur RICHTUNG, die
   Gewichte kommen nie an. Gefaehrlich wird das erst mit einem stillen Zweig:
   `if richtung == "short": ... else: <long>` schluckt jeden fremden Wert, die
   Funktion rechnet unveraendert weiter, und ein Test, der genau diesen Aufruf
   macht, bleibt gruen, ohne etwas zu pruefen (Score 66.7 == 66.7).
   Zwei Gegenmittel, beide noetig: Konfiguration IMMER als Keyword uebergeben
   (`gewichte=g`), und die Funktion bei unbekanntem Wert SCHEITERN lassen
   (`raise ValueError`) statt still den Standardzweig zu nehmen. Pruefung:
   jede Aufrufstelle der Funktion ansehen - positionelle Argumente ab Stelle 2
   sind der Verdacht, und ein `else` ohne Bedingung ist der Verstecker.
5. **Fehlender Deckel.** Ein Short-Erloes konnte negativ werden (mehr Verlust
   als Einsatz) -> `max(0.0, ...)` gegen die Liquidation. Pruefung: welcher
   Wert kann ueber den Einsatz hinauslaufen?
6. **Daten fehlen fuer die spaetere Messung.** Ausstiegszeilen ohne Score/C-R,
   Positionen ohne Buchgewinne/-verluste. Was beim Ausstieg nicht im Journal
   steht, ist fuer die Kalibrierung verloren. Pruefung: koennte eine Auswertung
   die Frage des Auftrags ueberhaupt beantworten?
7. **Kein Symmetrie-Test.** Der wichtigste Test eines Buchs fehlte: eine
   Position ohne Kursbewegung muss ein Minus von rund 2k ergeben. Ohne ihn
   misst man Wunschzahlen.
8. **Der Ausstiegspfad kennt den Boersen-Stop nicht.** Ein Notausstieg, der
   mit der Order zum Handelsplatz geht, hat ein eigenes Leben: die Kennung
   (`algoId`/`txid`) muss am Einstieg ins Buch (sonst ist er nie stornierbar),
   jeder Ausstieg muss ihn zuerst stornieren, und ein gescheiterter eigener
   Verkauf ist kein Grund aufzugeben, sondern der Anlass nachzusehen, ob der
   Boersen-Stop laengst gefuellt hat (`stop_details`/`vol_exec` > 0 -> Ausstieg
   `stop (boerse)` mit dem Stoppreis buchen). Sonst entstehen zwei stille
   Schaeden: eine Karteileiche im Buch (Position am Markt weg, hier noch offen)
   und ein verwaister Stop, der eine SPAETERE Position desselben Instruments
   unerwartet verkauft. Pruefung je Spur: `grep -n "stop_setzen\|order_stornieren"
   <spur>/handeln.py` und dann jede Aufrufstelle im Ausstiegs- und Notausstiegs-
   pfad; die Aufruf-REIHENFOLGE ist Teil des Tests (storno vor verkauf).
9. **Eine Anzeige ohne Waechter.** Ein `ok`-Zyklus im Dauerlauf sagt nichts
   ueber eine GUI-Zeile. Angezeigte Werte brauchen einen eigenen Test als
   reine Funktion (`fuss_texte(z, w)`) plus einen Quelltext-Test, der
   erfundene Feldnamen im Anzeigecode verbietet.
10. **Ein Routing-Feld, das eine ZWISCHENLAGERUNG nicht ueberlebt.** Die Spur
   holt beim Sammeln ein Feld, das den gehandelten Gegenstand bestimmt (hier:
   den handelbaren Kontrakt `handels_instId`/`handels_instr` je Reihe), legt das
   Ergebnis aber schlank ab - nur die Felder der Anzeige. Nach dem Einlesen
   greift der Rueckfall im Verbraucher, und der zeigt auf den Wert von VOR dem
   Umbau: der Fix wirkt nur auf den ersten Lauf, die Spur laeuft still wieder in
   den alten Fehler (Messfehler an der Boerse inklusive). Pruefung: die
   schreibende und die lesende Stelle des Zwischenlagers nebeneinander halten -
   jedes Feld, das der Verbraucher liest, muss im Schreibpfad stehen. Der Test
   dazu faehrt den Verbraucher mit einem Stand aus der DATEI, nicht mit einem im
   Speicher gebauten Dict; ein Test mit dem Feld direkt im Argument bleibt gruen.
   Zwei Sicherungen gehoeren dazu: ein Stand aus altem Schema wird VERWORFEN
   statt bis zum Ablauf zu gelten (sonst schleppt er den Fehler zwei Stunden
   weiter), und der Rueckfall darf nie auf den unbrauchbaren Wert zeigen - ohne
   den richtigen Gegenstand entsteht KEIN Vorschlag, mit Begruendung im Log.
11. **Eine Anzeige, die den leeren Fall verschweigt.** Eine Sperrliste, die nur
   im Fehlerfall gedruckt wird (`if g: print("gesperrt durch: …")`), sieht bei
   leerer Liste wie ein abgebrochener Lauf aus - und der Dauerlauf parst genau
   diese Zeile. Immer drucken, leer als `nichts`. Zweite Haelfte desselben
   Musters: die Anzeige nennt den Gegenstand, auf den gehandelt wird (das
   gehandelte Instrument, den gehandelten Kontrakt), nicht den Zwischennamen,
   aus dem er abgeleitet wurde - sonst liest sich die Vorschau, als wuerde der
   unbrauchbare Wert gehandelt.

### 4. Fix-Disziplin

- `.bak-JJJJMMTT` fuer jede angefasste Datei - auch Journal und Zustand, wenn
  ein Lauf sie beruehren kann.
- Ein Fix = ein Test, der den Befund festhaelt; der Test nennt im Docstring
  den Befund, nicht die Loesung.
- Bestehende Tests sind das Sicherheitsnetz: laufen sie nach einem Umbau
  unveraendert durch, war die neue Signatur wirklich kompatibel. Muessen Tests
  angepasst werden, ist das ein Befund - kein Detail.
- Werte in `wachen.json` bleiben unangetastet, solange der Auftrag sie nicht
  ausdruecklich aendert (eine geaenderte Grenze ist eine Strategieaenderung).
- Neue Ausgabezeilen gegen die Meldeliste des Dauerlaufs pruefen
  (`verkauf`, `stop`, `KILL`, `gesperrt`, `ausstieg`) - sonst wird der
  Regelzyklus laut.

### 5. Messbar machen - die Kernfrage stellen

Ein Buch ohne Auswertung ist eine Meinung. Beim Pruefen immer fragen: **kann
jemand aus dem Journal beantworten, ob das getragen hat?** Wenn nein, gehoeren
felder in den Lauf (Score, Richtung, Haltedauer, Buchgewinne) - waehrend die
Position laeuft, nicht nachtraeglich. Und die Auswertung wird an EINER Stelle
gerechnet und ueberall angezeigt.

## Nachweis-Kette (nichts davon weglassen)

1. Eigene Suite UND die Nachbarsuiten (`Handel/tests`).
2. Bus-E2E, wenn Bus oder Tagesbericht beruehrt sind.
3. Ein ECHTER Lauf mit echten Daten - ein Trockenlauf mit Testdaten zeigt
   nicht, ob die Mechanik im Bestand funktioniert.
4. Bei Sichtbarkeit: den Bericht rendern und die Zeile ZEIGEN, nicht
   beschreiben.
5. Bei Formataenderungen: eine Zeile der echten Datei danach ansehen
   (Journal-Kopf, Zustand) - nicht nur den Test.
6. Laufzeitgrenze beachten: die Spur selbst greift im naechsten Zyklus
   (Unterprozess), eine GUI und `dauerlauf.py` brauchen einen Neustart.

## Abgrenzung

- Der NEUBAU einer Spur steht in `references/neue-spur-ende-zu-ende.md`.
- Das DEUTEN eines Ergebnisses („das heisst, wir haetten X gewonnen?")
  steht in `references/buchergebnis-pruefen.md`. Dieses Blatt hier ist der
  Weg dorthin: pruefen, fixen, messbar machen.
