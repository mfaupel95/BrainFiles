# Edge messen und die Echtheit einer Statistik pruefen

Ausloeser: „welche Spur ist die beste?", „hat die Trefferquote einen Sinn?",
„woher kommen die ganzen Runden?", „eine Spur sieht super aus, ist aber
falsch", oder wenn eine Spur ungewoehnlich gute Zahlen zeigt.

Werkzeug: `Agenten/Handel/spur_audit.py` (liest nur; `--historie` laedt
fehlende Kerzen nach). Tests `Agenten/Handel/tests/test_spur_audit.py`.
Es liest die Spurliste aus `dauerlauf.SPUREN`, die Ein-/Ausstiegszuordnung aus
`journalpaarung` und den Aufrufertakt aus `dauerlauf.TAKT_MAX_MINUTEN` -
**keine eigenen Zahlen**, sonst waere die Schwelle eine Behauptung.

## Frage 0: erzeugt die Spur ihr Signal ueberhaupt?

**Vor Frage 1 steht die Herkunft der Einstiege.** Eine Spur, deren Einstiege
aus einem FREMDEN Journal gelesen werden, hat kein eigenes Signal: ihre
Statistik misst das Signal der anderen Spur, und die Frage „hat diese Spur
Edge" laeuft auf „hat der fremde Lauf Edge" hinaus.

Gemessen: drei Naute-Arme buchten Einstiege aus dem Journal der kopier-Spur -
Solana-Memecoin-Kaeufe - und legten sie als BTC-Proxy an. Das Signal gehoert
einem anderen Markt als die Position; Auswertung, Excess und Trefferquote
der Arme sind Kennzahlen ueber die kopier-Regel, nicht ueber die Arme. Die
Arme erzeugen keine Signale, also trifft sie auch die Frage nicht, ob ihr
Signal etwas voraussagt.

**Woran man es erkennt:** im `handeln.py` steht kein Aufruf, der eine Richtung
oder ein Signal berechnet, sondern ein Lesezugriff auf ein fremdes Journal
(`aktion=eroeffnen`-Zeilen eines anderen Ordners). Wer eine solche Spur
umstellt, baut eine neue Spur daneben und laesst die alte unberuehrt
laufen - sie hat offene Positionen und einen Buchstand, und ein Umbau
waehrend des Betriebs ist eine Aenderung an einer Position, die gerade laeuft.

**Originalstrategien eines Fremdpakets findet man NICHT im installierten
Rad** - ein Wheel enthaelt keine Beispiele. Der Weg ist die Quelle des
Pakets: bei NautechSystems liegen die verdrahtenden Beispiele unter
`examples/backtest/`, die eigentliche Strategie unter `docs/tutorials/`
(dort das Beispiel importieren). Fehlt der Git-Klon im Haus, wird er vom
Upstream geholt; die Werkzeugpfade der Beispiele (Elternordner) stimmen dann
nicht, das ist aber nur Verdrahtung.

## Die zwei Fragen, in dieser Reihenfolge

1. **Ist die Statistik ueberhaupt echt?** Erst danach lohnt die Edge-Frage.
2. **Hat die Spur Edge?** Also: verdient sie mehr, als das Instrument ueber
   dieselbe Zeit getragen haette?

Die Reihenfolge ist nicht Formsache: eine falsche Statistik beantwortet
Frage 2 mit einer Zahl, die stimmt und nichts bedeutet.

## Frage 1: die drei Alarme

Alle drei sind aus dem Journal allein lesbar, ohne Kursdaten - genau deshalb
sind sie der erste Schritt und nicht der zweite.

**a) Haltedauer im Takt des Aufrufers.** Faellt der Median der Haltedauer
unter das Doppelte des Aufrufertakts, sind die Runden Zyklen, keine
Handelsentscheidungen: ein echter Marktausstieg braucht Stunden bis Tage.
Schwelle aus dem Aufrufertakt, nicht aus einer eigenen Zahl. Gemessen: ein
Journal mit Median 0,25 h bei 0,25-h-Takt und 101 von 123 Runden unter einer
Stunde.

**b) Ein Instrument traegt die Mehrheit aller Runden.** Ein Streuportfolio
kann das nicht. Gemessen: 87 von 161 Runden auf einem einzigen Paar.

**c) Identische Einstiegspreise je (Instrument, Tag).** Ein Marktkurs ist
zweimal am Tag nie auf sechs Nachkommastellen gleich. Das heisst: die Spur hat
einen Preis UEBERNOMMEN statt geholt - ein Snapshot als Einstieg, und bei
steigendem Markt liegt das Ziel dann schon beim Kauf erfuellt.
**Geprueft wird nur, wo dieselbe Position am Tag mehrfach eroeffnet wurde** -
sonst waere ein Einmalkauf schon ein Alarm.

Zusaetzlich, weil billig: das Ergebnis **je Score-Band** ausweisen. Steigt der
Score und faellt das Ergebnis, ist es kein Signal, sondern ein Preisfehler, der
die schwachen Kandidaten staerker trifft.

## Frage 2: Excess, nicht Trefferquote

**Die Excess-Rendite ist die einzige Kennzahl, die die Frage beantwortet:**
Rundenergebnis MINUS der Marktbewegung desselben Instruments ueber dieselbe
Zeit (BUY & HOLD aus den gespeicherten Kerzen), Seite beachtet (short =
vorzeichenumgekehrt).

- **positiv** - die Spur verdient mehr, als das Instrument getragen haette
- **nahe 0** - die Spur IST die Marktbewegung; sie hat keinen eigenen Vorteil
- **negativ** - die Runden weglassen

Zwei Trefferquoten koennen weit auseinanderliegen und dieselbe Bilanz haben: je
langer gehaltene Verlierer gegenueber schnell geschlossenen Gewinnern. Eine
Auswertung, die NUR die Trefferquote nennt, ist eine Auswertung ohne
Gegenprobe. Bei fehlender Basislinie wird das Ergebnis als solches benannt
(`ohne Basislinie`), nicht durch eine Waehrungs- oder Instrumentenluecke
gefuellt.

## Frage 2b: der Excess NACH der Gebuehr der eigenen Boerse

**Der Excess allein entscheidet nichts - er wird gegen die Gebuehr der
Boerse gestellt, auf der die Spur handelt.** Das ist die eine Spalte, die
ueber „welche Spur darf live" entscheidet: `excess% - 2 x 100 x
gebuehr_taker` aus der `wachen.json` derselben Spur (der Faktor 2 x 100
steht dazwischen, weil `gebuehr_taker` ein Bruch JE SEITE ist und eine
Runde Kauf + Verkauf ist).

Gemessen ueber alle Spuren mit Live-Pfad: der rohe Excess ist ueberall
nahe null (2,44 % Ergebnis -> 0,01 % Excess; 6,56 % -> 0,04 %), und nach
der Gebuehr bleiben nur sieben von fuenfzehn Spuren positiv. Die beiden mit
1,20 % je Runde (Kraken-Spot) landen bei **-0,97 %** und **-1,19 %** - das
ist keine schlechte Serie, das ist eine Struktur, die nichts anderes kann
als zu verlieren, egal wie gut das Signal ist.

**Merksatz:** dieselbe Spur kann auf OKX-Perp (0,05 % je Seite) einen
positiven und auf Kraken-Spot (0,60 %) einen negativen Gebuehren-Excess
haben. Die Gebuehr gehoert darum an die **Boerse der Position**, nicht an
den Namen im Verzeichnis.

**Drei Spalten, die man gemeinsam liest:** `excess%` (Vorteil gegenueber dem
Halten), `nach Gebuehr` (tragfaehig ja/nein) und `n` (belastbar ja/nein).
Eine Spur mit `nach Gebuehr = +1,42 %` und `n = 2` ist kein Kandidat - sie
ist eine Beobachtung, und die Freigabe gehoert auf eine Zahl, die man tragen
kann. **Ab unter 15 Runden ist die Zeile eine Andeutung, und die Sperrfrist
der Spur laeuft weiter, statt sie zu ersetzen.**

### Was aus einem negativen Gebuehren-Excess folgt

Abschalten ist die eine Folge, aber die **keine Position schliesst** - eine
bestehende Position zu schliessen ist eine Order und gehoert in die
Freigabekette. Abgeschaltet wird die ZULASSUNG (`freigabe.erfuellt` false
mit datiertem Vermerk und Grund), damit keine neuen dazukommen; die
offenen Positionen laufen ihren Stop und Ziel zu. Und: eine Spur ohne
Orderpfad kann die bessere Strategie sein und trotzdem nie live werden -
die Gebuehren-Spalte beantwortet die Frage nicht, wenn der Weg fehlt.

## Die vier Fallen, die sich beim Bauen solcher Messungen zeigen

### 1. Die Auswahl-Verzerrung - die gefaehrlichste

**Jede Kennzahl, die nur fuer eine TEILMENGE berechenbar ist, meldet den
Teil als das Ganze.** Der Mechanismus: eine kurze Runde hat oft keine volle
Kerze in ihrem Zeitfenster, also keine Basislinie - und genau die kurzen Runden
sind die Scheinrunden. Das Werkzeug misst damit nur die sauberen Runden und
sieht danach gut aus. Gemessen: 11,9 % Excess ueber alle Runden, davon +16,6 %
auf den Runden unter einer Stunde und +1,5 % auf den uebrigen.

Das ist dieselbe Verzerrung wie ein falscher Einstiegspreis, nur eine Ebene
tiefer, und sie faellt nicht auf, weil das Ergebnis plausibel aussieht.

**Gegenmassnahme:** jede Kennzahl nennt die Zahl der gemessenen UND die Zahl
der ausgeschlossenen Runden, und der Excess wird **getrennt nach der
Eigenschaft ausgewiesen, die den Verdacht traegt** (hier Haltedauer). Weichen
die Gruppen um mehr als fuenf Prozentpunkte voneinander ab, ist die
Gesamtzahl ein Befund ueber die Auswahl, nicht ueber die Spur.

### 2. Eine Basislinie, die fehlt, ist eine stille Luecke

Kein Edge messen zu koennen ist kein Befund gegen die Spur - es ist eine
Luecke in der Messung, und sie erscheint von allein nicht. Sie wird sichtbar
erst, wenn man sie verlangt: jede Runde, die keine Basislinie bekommen kann,
wird gezaehlt und benannt.

**Ein Mapping muss Basiswerte kennen, nicht Schreibweisen.** Gemessen trugen
die Journale 110 verschiedene Instrumentnamen fuer 66 Basiswerte - dieselbe
Position erscheint als Spot-, Kontrakt-, Swap- und Krakenname. Ein Mapping,
das nur die Namen enthaelt, die einmal getippt wurden, ist eine Liste von
Beobachtungen und beantwortet die Frage fuer alles andere mit „kein Paar".
Also erst auf den Basiswert reduzieren (OKX-Kontrakt, `-SWAP`, `/EUR`,
Kraken-X-Praefix), dann nach einem Paar fragen. Nach dem Reduzieren von 14 auf
45 Kerzenreihen stieg die Basislinien-Deckung von 6 auf 222 Runden.

**Ein Instrument ohne Historie bleibt eine Luecke und bekommt KEIN
Ersatzinstrument.** Aktien-ETPs und Pump-Token haben keine belastbare Reihe;
eine Basislinie aus einem aehnlichen Markt waere erfunden, und sie schaet
besser aus als sie ist, ohne dass man es sieht.

### 3. Eine leere Spalte ist keine Feststellung

**Nicht jede Spur fuehrt das Instrument in derselben Spalte.** Gemessen: eine
Spur fuehrt `paar`, eine zusaetzlich `symbol` (Kopier-Signal-Kuerzel), eine
dritte nur `inst`. Blind `inst` gelesen sieht man eine leere Spalte und meldet
„alle 54 Runden auf EIN Instrument" - ein Befund aus dem Nichts, weil es gar
kein Instrument gibt. Also die **besetzte** Spalte suchen und ohne belegtes
Feld ueberhaupt keinen Befund erzeugen.

Zweite Form derselben Sache: ein Zaehler, der Tupel zaehlt statt Zeilen, und
ein Streuungsanteil, der sich auf die Gesamtzahl statt auf die gemessenen Zeilen
teilt.

### 4. Eine Regel, die auf einen Fall passt, zerschneidet die anderen

**Jede Normalisierung braucht eine Beschraenkung, nicht nur ein Muster.**
Gemessen: eine feste Abschneidung der letzten drei Zeichen (`[:-3]`, gedacht
fuer Krakens `EUR`) machte aus `CASHCAT` -> `CASH`, `META` -> `MA`,
`RENDER` -> `REN`, `UNITREE` -> `UNITR` - und eine Regex auf „irgendwelche vier
Endbuchstaben“ zerschnitt den OKX-Kontraktnamen `HBAR-USD_UM_XPERP-310815` zu
`H`. Beides sieht harmlos aus und trifft still die falschen Instrumente.

**Also restriktiv formulieren: nur eine ECHTE Waehrung am Ende abschneiden**
(`USDC`, `USDT`, `USD`, `EUR`), alles andere unveraendert lassen. Und `lstrip`
ist bei Praefixen (`X`) fast immer falsch, weil es die Zeichen des Basiswerts
mitfrisst: `XXBTZEUR` wird zu `BTZ` statt zu `BTC`. Bei einer ungewoehnlichen
Namensform (doppeltes X, angehaengtes Z) ist eine kleine Tabelle ehrlicher als
eine Regel.

## Zwei Fehler, die erst die Tests zeigten

**Der Wert in einer Textspalte steht im Token DANACH.** `score 64.7` ist nicht
`score=64.7`. Ein Test, der nur auf `=` oder `:` prueft, liest nie einen Score -
und die Umkehrung des Scores bleibt ungeprueft, waehrend man sie fuer geprueft
haelt.

**Eine Kerze fuer beide Seiten ergibt 0,0 % Marktbewegung.** Liegt das Fenster
zwischen zwei Kerzen und nimmt man fuer Ein- und Ausstieg dieselbe letzte
vorhandene Kerze, ist die Basislinie exakt null, und jede Spur schaet besser
aus als sie ist. Richtig: Einstieg = letzte Kerze VOR`t0`, Ausstieg = LETZTE
Kerze IM Fenster, und ohne eine Kerze im Fenster gibt es keine Basislinie
statt einer geratenen.

## Wenn die Zahl zurueckfaellt: die Entscheidung faellt mit

Der Audit kann **die eigene Empfehlung** widerlegen, die auf derselben Zahl
aufgebaut war. Dann gilt: die Empfehlung zuruecknehmen **und jede daraus
abgeleitete Aenderung mit** — ohne Rueckfrage, weil sie keine eigene
Entscheidung war, sondern eine Folge. Datierte Begruendung in die Datei
(`_…_vermerk`), und **offene Positionen bleiben unangetastet** (eine
niedrigere Obergrenze schliesst keine Position).

Gemessen: die schoenste Kennzahl des Hauses (`t = 15,42`, 85 % Treffer,
+17,49 %) war ein Rechenfehler — der Einstiegspreis war je (Instrument, Tag)
uebernommen statt geholt, 87 von 161 Runden lagen auf EINEM Instrument, und
der Excess **zerfiel um 15 Prozentpunkte** zwischen den Runden unter und ueber
einer Stunde (+16,64 % gegen +1,52 %). Auf dieser Zahl war nicht nur eine
Empfehlung gebaut, sondern ein haeltbarer Eingriff (Budget und Platzzahl
erhoeht); beide gingen zurueck, die Empfehlung wurde im Bericht ausdruecklich
als zurueckgenommen benannt.

**Merksatz: eine richtig gerechnete Zahl aus falscher Eingabe ist die
GEFAEHRLICHERE Falschaussage**, weil sie den Anschein einer Messung traegt.
Der Selbsttest jeder Kennzahl aus einer fremden Zahlenspalte ist die Frage:
**traegt sie sich, wenn man sie in zwei Haelften teilt?** Eine Differenz um
15 Prozentpunkte zwischen den Haelften derselben Stichprobe heisst: die Zahl
misst die Auswahl, nicht die Spur — und sie ist damit als Befund ueber die
Auswahl zu schreiben, nicht als Befund ueber die Spur.

## Die Regel fuer den Aufbau

**Die erste Zahl, die man aus dieser Messung zieht, ist nicht „welche Spur
ist die beste", sondern „welche Spur ist ueberhaupt fuer Geld geeignet"** -
also der Gebuehren-Excess. Eine Rangliste nach `mean%` fuehrt zur falschen
Spur: die groesste Ergebniszahl trägt haeufig die teuerste Boerse. Und die
Ordnung der Fragen lautet: erst Echtheit, dann Excess, dann Gebuehren-Excess,
erst danach darf ueber live entschieden werden.

**Jede Regel dieser Messung muss fallen, wenn man sie abschaltet.** Ein Test,
der die Regel prueft, ist wertlos, wenn er auch mit der Regel ausgeschaltet
gruen bleibt - das ist der Zustand, in dem die Fehlerklasse entstanden ist.
Zwei Beispiele, die erst eine eigene Gegenprobe brauchten: eine Preis-
Vergleichsregel, die auch nach dem Runden auf zwei Stellen noch griff (die
Gegenprobe muss die RELATIVE Abweichung sehen, nicht die Nachkommastellen),
und eine Streuungsmessung, die auf drei belastbare Zeilen warten muss, sonst
waere jede frisch angelegte Ein-Instrument-Spur sofort ein Alarm.

Und **die Reihenfolge der Arbeit**: erst die Basislinie fuer die Instrumente
BESCHAFFEN, dann messen. Ein Befund, der auf einer fehlenden Datengrundlage
beruht, ist kein Befund - und die Korrektur der Grundlage ist billiger als jede
Auswertung, die man darauf aufsetzt.