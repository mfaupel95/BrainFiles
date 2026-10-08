# Trailing-Stop an gehebelten Positionen: Geometrie, nicht Filter

Gilt fuer jeden Auftrag der Form "Stop-Loss nachziehen und anpassen" und fuer
jede Trailing-Regel, die an eine Ausstiegsgeometrie gebunden wird.

## 1. Das Auftragskriterium ist fast immer die falsche Achse

Ein Auftrag kann eine **Bandzahl aus geschlossenen Runden** als Auswahl
nennen ("alle Spuren mit 1-3 Takeprofit", "Spuren mit Quote ueber 50 %",
"ab 2R verdienen"). Als Filter auf einen **Zustand einer offenen Position**
ist sie fast immer unbrauchbar. Warum:

| Groesse | Gehoert zu | Wird gemessen an |
|---|---|---|
| R (Vielfaches), Trefferquote, Excess | AUSSTIEGSGEOMETRIE | geschlossenen Runden |
| Einstieg, Stop, aktueller Kurs | ZUSTAND EINER OFFENEN POSITION | dem Buch und der Boerse |

Zwei Spuren mit 1,5R- und 2,0R-Ziel, beide mit 5 % Stop, stehen bei +1,6R an
**verschiedenen** Punkten ihrer Geometrie und bekommen bei einem an den
Zustand gebundenen Mechanismus trotzdem **denselben** Stop. Ein Filter auf
`ziel_r` haette sie beide behandelt und die Zahl beteuert, es sei gezielt
gewesen — es war Zufall.

**Die Regel:** ein R-Band, eine Quote, ein Excess sind *Merkmale des
Ergebnisses*. Ein Mechanismus, der eine OFFENE Position veraendert, haengt am
*Buch*. Also das Kriterium aus dem Auftrag als **Mass fuer die Relevanz**
beantworten (welche Spuren haben überhaupt 1-3R-Geometrie, wie viele Runden,
welche Boerse) und den Mechanismus an das Buch haengen.

Gegenprobe, die billig ist und die Achse beweist: dieselbe Position zweimal mit
verschiedenem `ziel_r` in der Wache rechnen. Bekommt sie denselben Stop, haengt
der Mechanismus nicht am Ziel. Steht das im Auftrag, ist es der Befund, den man
dem Auftraggeber vorlegt — nicht der Punkt, an dem man die Aufgabe abklemmt.

## 2. Warum ueberhaupt trailingen: was der feste Stop verschenkt

Eine Position mit 5 % Stop und 2R-Ziel gibt bei 0,4R Kursgewinn nichts her und
riskiert den vollen Stop. Der Trailing-Stop wandert mit dem Preis und wandelt
das Vollrisiko in einen Teilgewinn. Das ist der einzige Grund fuer die ganze
Einrichtung — und er ist an **Runden mit Teilgewinn** messbar, nicht an
geschlossenen Runden.

## 3. Die vier Schranken (alle muessen greifen, keine ersetzt eine andere)

1. **Trigger.** Erst wenn die Position so weit im Plus ist, dass ihr Stop vom
   Verlust zum moeglichen Gewinn geworden ist. Als Anteil des Stop-Abstands
   (`trigger_r`), nicht als Prozentsatz — der Stop ist je Position anders
   breit, und ein fester Prozentsatz ist bei 1 % Stop zu frueh und bei 12 %
   zu spaet.
2. **Nur in die schuetzende Richtung.** Long: nach oben. Short: nach unten.
   Ein Stop, der naeher am Einstieg laege als der alte, ist eine Verlockung,
   kein Schutz — nie zurueckziehen, auch nicht nach einem Auslaufen.
3. **Nie ueber die Liquidationsmarke.** `liq < stop < einstieg` (Long,
   spiegelbildlich Short). Der Abstand der Marke ist `1/hebel` minus/plus
   Wartungsmarge; die Rechnung gehoert VOR den Einstieg, nicht danach. Bei 6x
   liegt die Marke rund 16 % entfernt, bei 12x rund 8 % — an der Grenze wird
   ein 5-%-Stop unerreichbar, und die Spur verliert ihren Notaus.
4. **Mindestabstand zum Kurs.** Ein Stop, der zu nah am Markt liegt, wird vom
   naechsten Tick erreicht. Der Abstand gehoert gegen die **Volatilitaet des
   Instruments** geprueft, nicht gegen eine schoene runde Zahl.

## 4. Der Stop folgt dem HOCHSTAND, nicht dem Kurs

Wichtigste Einzelregel: der neue Stop wird aus dem **Hochstand** gerechnet,
nicht aus dem aktuellen Kurs. Sonst zieht ein Ruecksetzer den Stop wieder
zurueck, und am Ende ist der Trailing schaedlicher als keiner, weil er
irgendwann trotzdem ausloest. Der Hochstand wandert nur in die Bewegungsrichtung
des Hochs (long: nur hoeher).

## 5. Reihenfolge vor dem Verdrahten

1. **Buch gegen Boerse, und zwar je MENGE.** Eine Position, die an der
   Boerse in **mehreren** Schutzauftraegen liegt (die Menge aufgeteilt, weil
   nachtraeglich nachgesetzt wurde), kann man nicht trailingen: der engste
   feuert zuerst, die anderen bleiben als Waisen zurueck. **Erst zusammenfuehren,
   dann trailingen.** Summe der Stop-Mengen gegen die Buchmenge halten — ein
   Treffer genuegt nicht, `reduceOnly` + Gegenrichtung + eine Ausloesung sind
   die Bedingungen fuer „geschuetzt". Messbar auch als **Stop-Deckungsgrad**:
   gedeckte Kontrakte / Buchmenge. Ein Beispiel mit voller Deckung (Summe
   stimmt) und drei Stops ist trotzdem kein Trailing-Fall.
2. **Kennung vorhanden?** Der Mechanismus verlangt die Auftragskennung in der
   Position (`stop_id`). Fehlt sie, ist zuerst der fehlende Stop zu setzen
   (`xperp/stopdeckung.py`, `mosaic/stops_nachziehen.py`) — kein Mechanismus
   erfindet einen Stop.
3. **Traegt der Weg ueberhaupt ein Nachziehen?** Es gibt (a) `amend` am
   bestehenden Auftrag, (b) Storno + neu setzen. Nur (a) ist brauchbar: bei (b)
   gibt es zwischen beiden Aktionen ein Fenster OHNE Schutz. Fehlt (a) im Weg,
   laut sagen statt (b) zu nehmen.

**Die Deckungspruefung laedt ihr Modul selbst — der Test muss die NAHT setzen,
   nicht den Aufrufer patchen.** `stopdeckung.deckung()` ruft intern
   `_okxf()` und laedt damit das ECHTE okxf (Netzaufruf), solange
   `stopdeckung.okxf` nicht gesetzt ist. Ein Test, der nur `handeln.okxf`
   durch eine Attrappe ersetzt, laesst die Deckungspruefung trotzdem an die
   echte Boerse gehen — der Fehler erscheint als Testfehler, nicht als
   Netzaufruf. Fix: in der Verdrahtung VOR dem Aufruf
   `stopdeckung.okxf = okxf` setzen (das okxf der Spur), damit `deckung()`
   die Attrappe benutzt. Regel: ein Helfer, der ein Modul per Name laedt,
   braucht eine explizite Naht, die der Test setzt — patchen des Aufrufers
   reicht nicht.

## 6. Beleg der Boersenroute ohne Geld zu bewegen — und was der Beleg BEWEIST

Route unbekannt (etwa weil sie kein Haus-Modul hat) und echte Position offen:
**den bestehenden Stop auf seinen EXAKT GLEICHEN Wert zurueckschreiben** und
danach die offenen Schutzauftraegereerneut abfragen. Das ist der einzige Weg,
eine Schreib-Route an einem gefuellten Konto zu pruefen, und er ist
ungefaehrlich, weil der ausloesende Vorgang identisch bleibt. Ein **Fehlversuch
braucht trotzdem kein Geld**: eine Kennung, die es nicht gibt, und ein
fachliches Feld (statt einer Fremdmarke) belegen, dass die Route existiert —
ein `401`/`404` wuerde nur zeigen, dass der Pfad fehlt.

**Zwei Fehler, die derselbe Beleg machen kann — beide sind die schlimmere
Haelfte.**

1. **Ein Erfolgscode belegt die Faehigkeit, nicht die Wirkung.** Eine Route kann
   `ok` liefern und dabei etwas voellig anderes tun als beabsichtigt. Deshalb
   gehoert **zwei** Abfragen in den Beleg: den Aufruf und danach den
   Auftragsbestand. Ein Rueckcode ohne die zweite Abfrage ist halb gemessen.
2. **Die richtige Frage ist die KENNUNG, nicht der Preis.** Vergleichbar sind
   Preis, Menge und Status — aber ein Weg, der den alten Auftrag aufhebt und
   einen neuen mit **neuer Kennung** erzeugt, hat nicht geaendert, sondern
   storniert und neu gesetzt. Das sieht im Ergebnis aus wie ein Amend (gleiche
   Menge, gleicher Preis, alte Position geschuetzt) und ist genau das Fenster
   OHNE Schutz, das der Trailing nicht haben darf. **Bleibt die Kennung nicht
   erhalten, ist die Route fuer einen Trailing unbrauchbar** — unabhaengig
   davon, was sie zurueckmeldet.

Daraus die Probe-Regel: **die Probe laeuft an einem Auftrag, der zu KEINER
Buchposition gehoert** (Staub, ein stehen gebliebener Rest). An einem Auftrag
mit echtem Deckel kann derselbe Aufruf eine Position entschaerfen, weil die
alte Kennung im Buch steht und die neue dort unbekannt ist. Vorher die Menge
gegen jede Buchposition halten und den Auftrag mit **keiner** Uebereinstimmung
waehlen — das ist der Nachweis, dass die Probe nichts angeruehrt hat.

Steht kein Weg mit `amend` zur Verfuegung, ist der Trailing eine neue
Boersen-Anbindung und gehoert als solche beurteilt: Signatur, Takt, Schluessel
und **eine Fehlerbehandlung, die den alten Stop stehen laesst**. Ein
Fehlgeschlagener Versuch darf nie auf "dann storniere und setze neu" fallen —
das erzeugt den doppelten Stop, den die Buchbereinigung erst wochenlang spaeter
aufraeumt.

**Ein Weg, der den Stop nicht aendern kann, ist ein BEFUND und kein Bauteil.**
Dann wird nichts halb verdrahtet: `nachziehen()` verweigert eine Route ohne
`stop_nachziehen` ausdruecklich, und das Ergebnis ist ein vermerkter Task mit
der gemessenen Route — nicht eine Verdrahtung, die im Betrieb still vorbeilauft.
Weil die Rechnung boersenunabhaengig ist, ist das der guenstige Ausgang: der
Weg kommt fertig, sobald die Spur auf einer Boerse mit Amend handelt, und es ist
nur noch eine Bindezeile.

## 7. Rechnung und Verdrahtung sind zwei Dateien, nicht eine

Die Rechnung gehoert in EIN Modul fuer alle Spuren (`Handel/trailing.py`),
weil sie ohne Netzzugriff testbar ist und nur `einstieg`, `stop`, `seite` und
`kurs` braucht. Der Boersenaufruf gehoert an den Weg der Spur. Die
Verdrahtung sitzt in `pruefe_ausstiege` bzw. `zyklus` — an der STELLE, an der
jede Position ohnehin geprueft wird, und im **Live-Zweig**, denn ein
Papierlauf aendert keinen Boersen-Auftrag.

**Drei Felder und ihre Vorgabe.** `trailing_aktiv` fehlt in der Wache = es
passiert nichts. Ohne diese Schranke wuerde jede Spur durch ein vergessenes
Feld ploetzlich nachziehen. Die beiden Zahlen (`halten_pct`, `trigger_r`) sind
Hauswerte, keine Messung — `neu()` liefert sie als Wachen-Feldersatz, und ein
Test prueft ihre FORM, nicht ihren Betrag.

**Drei Blockwaende, jede mit Journalzeile statt stummer Auslassung.** Kein
Aktiv-Feld, mehr als eine Stop-Kennung, keine Kennung. Der Grund gehoert in die
Datei: das ist der einzige Weg, auf dem die Naechste erkennt, dass hier ein
Werkzeug fehlt und nicht ein Rechenfehler.

**Ein nicht ausgeloester Trailing schreibt KEINE Journalzeile.** Sonst waende
sich die Auswertung mit jedem Zyklus: die Spur stuende in jedem Lauf mit 47
offenen Positionen auf "trailing", ohne dass sich etwas bewegt haette. Nur ein
tatsaechlicher `amend` erzeugt eine Zeile.

## 8. Vier Verdrahtungsfehler, die erst der echte Lauf fand

Alle vier waren unsichtbar, bis ein Lauf oder ein Test die Frage stellte — kein
Fehlerfall ist beim Lesen aufgefallen.

1. **Eine Funktion, die mal ein Tupel und mal ein Dict zurueckgibt.** Sie zwingt
   jeden Aufrufer zu `isinstance(...)`; der erste Test tat genau das und tarnte
   sieben echte Fehler als Testfehler. **Konvention: eine Rechnung gibt
   IMMER `(ergebnis, grund)` zurueck**, auch im Erfolgsfall.
2. **Der Aufrufer wird von einer Signaturaenderung nicht mitgezogen.** Nach dem
   Umbruch `kandidat` -> Tupel brach der Aufrufer mit `tuple indices must be
   integers`. Hausregel gilt hier uneingeschraenkt: nach einer Umbruch-Signatur
   **jede** Aufrufstelle pruefen, nicht nur die umgebaute.
3. **Dieselbe Buchposition fuehrt die Menge unter verschiedenen Namen.** xperp
   fuehrt Kontrakte unter `kontrakte`, die Buch-Spuren unter `menge`, Kraken
   unter `menge`. Nur `menge` zu lesen hiesse: der Trailing griffe bei xperp
   nie, und es faelle nicht auf — der Weg sagt "keine Menge in der Position"
   und die Spur laeuft weiter. Die Felder nacheinander probieren und im
   Fehlerfall die **geprueften** nennen.
4. **Ein Fuehlgroessen-Feld, das nur bei Aenderung geschrieben wird.** Der erste
   Aufrufer liest es und bekommt `KeyError` bei der ersten Position. Ein
   Fuehlwert wird immer geschrieben.

Dazu eine Signaturfrage, die man nicht raten sollte: die Wege nehmen
**unterschiedlich viele** Parameter. Die Aufloesung ist nicht die
Signatur-Injektion im Aufrufer, sondern die Feststellung, dass **die Menge
nicht in den Auftrag gehoert** — sie steckt bereits im Algo-Auftrag an der
Boerse, `amend-algos` aendert nur den Ausloesepreis. Damit sind es ueberall
drei: `(kennung, inst, preis)`.

## 9. Der Vertragstest, der findet, was Lesen nicht findet

Die Binde-Funktion setzt jede Seam ueber einen **Namen**. Ein fehlender Name
crasht nicht beim Binden, sondern beim ersten Kursabruf im Live-Zweig — also
nach dem Freigabefenster. Ein Test, der die vollstaendige Funktionsliste beider
Wege gegeneinander haelt (`hasattr` je Name), findet es davor. Er traegt
zusaetzlich die **Negativ-Aussage**: der Spotweg darf `hebel_setzen` NICHT
haben, sonst waere der ganze gehebelte Aufbau ueberfluessig.

Ein zweiter Test traegt die Schutzrichtung: **Buch-Stop und Boersen-Stop
müssen derselbe sein.** Ein Trailing, das nur im Buch wandert, laesst einen
spaeteren Zyklus zu einem Preis verkaufen, den es an der Boerse nicht gibt.

## 10. Der Auftrag "anpassen bei Gelegenheit" hat keine eigene Bedeutung

"Bei Gelegenheit anpassen" ist keine Anweisung an eine Zahl — das Treffen der
Vorgaben ist der **optimierbare** Teil, und es ist nicht getan, wenn der
Trailing verdrahtet ist. Die Reihenfolge: erst die Geometrie bauen, dann
mindestens 30 Runden je Arm messen, dann suchen. Eine Verlegung um einen Tick
kostet eine Order und bringt nichts — deshalb `min_hub_r` als eigene
Schranke und nicht als Nebenbedingung des Trigger.

Und derselbe Satz wie beim Einstieg: **der Trailing verbessert nicht die Spur,
er veraendert nur, wie viel eine bereits gelaufene Position heraushaelt.**
Die Substanzfrage beantwortet der Excess, der Trailing ist Ausfuehrung.