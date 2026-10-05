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

## 6. Beleg der Börsenroute ohne Geld zu bewegen

Route unbekannt (etwa weil sie kein Haus-Modul hat) und echte Position offen:
**den bestehenden Stop auf seinen EXAKT GLEICHEN Wert zurueckschreiben** und
danach die offenen Schutzauftraege erneut abfragen. Rueckcode `0` plus
unveraenderte Liste (gleiche Kennung, gleiche Marke, gleiche Menge) belegt die
Route ohne eine einzige Order. Das ist der einzige Weg, eine Schreib-Route an
einem gefuellten Konto zu pruefen — und er ist ungefahrlich, weil der
ausloesende Vorgang identisch bleibt. Ein **Fehlversuch braucht trotzdem kein
Geld**: eine Kennung, die es nicht gibt, und ein fachliches Feld (statt einer
Fremdmarke) belegen, dass die Route existiert — ein `401`/`404` wuerde nur
zeigen, dass der Pfad fehlt.

Steht kein Weg mit `amend` zur Verfuegung, ist der Trailing eine neue
Boersen-Anbindung und gehoert als solche beurteilt: Signatur, Takt, Schluessel
und **eine Fehlerbehandlung, die den alten Stop stehen laesst**. Ein
Fehlgeschlagener Versuch darf nie auf "dann storniere und setze neu" fallen —
das erzeugt den doppelten Stop, den die Buchbereinigung erst wochenlang spaeter
aufraeumt.