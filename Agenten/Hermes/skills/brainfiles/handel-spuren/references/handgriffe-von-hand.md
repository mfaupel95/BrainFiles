# Handgriffe von Hand: Positionen aendern sich ausserhalb der Spur

Max schliesst, verkleinert und stockt Positionen in der Boersen-App auf.
Eine Live-Spur muss das verkraften, ohne zu luegen. Drei Regeln, alle am
22.09.2026 an xperp gebaut und im laufenden Betrieb belegt.

## 1. Eine handgeschlossene Position ist KEIN Geist ohne Ergebnis

Eine Position, die es an der Boerse nicht mehr gibt, ist ein Geist - aber
wenn ein Mensch sie geschlossen hat, existiert sehr wohl ein Ergebnis, nur
nicht im eigenen Journal (das hat meist gar keine G+V-Spalte).

- `okxf.geschlossene_position(inst, seit_ms)` liest
  `/api/v5/account/positions-history` (`realizedPnl`, `closeTotalPos`,
  `uTime`). `seit_ms` = Eroeffnungszeitpunkt der Buchposition; aeltere
  Schliessungen desselben Instruments gehoeren zu einer frueheren Runde.
- Erloes = Einsatz + realizedPnl, ANTEILIG gerechnet, wenn die Boerse
  groesser stand als das Buch (`Buchkontrakte / closeTotalPos`) - sonst
  zaehlt die Runde Gewinne, die ihr nicht gehoeren.
- Ohne Boersensatz (kein Eintrag, Netzfehler, unlesbare Zahl): NEUTRAL
  buchen, also den Einsatz zurueck. Nie ein Ergebnis erfinden.

**Die Falle, die das kostet** (xperp, 21.09./22.09.2026): Die Ausbuchung
schrieb `margin_usd = 0.00`. Die Wachen lesen die schliessen-Zeile als
ERLOES - die handgeschlossene Position zaehlte damit als **Totalverlust in
Hoehe ihres Einsatzes**. Bei HBAR waren das -16,84 USD in genau der
Drawdown-Kurve, aus der der Kill-Switch liest. Drei spaetere Handschluesse
(BZ, CL, CRCL = 97 USD Einsatz) haetten den Deckel 100 gerissen und die
Spur flachgestellt und gesperrt - ohne einen echten Verlust.

## 2. Die GROESSE wird geprueft, nicht nur die Existenz

Ein Handgriff aendert die Kontraktzahl, ohne dass eine Position
verschwindet. Gemessen: CL Buch 20 / Boerse 19, BZ 208 / 727, HBAR 9,4 / 47,1.

Der gefaehrliche Fall ist ein zu KLEINES Buch: der Ausstieg schloesse nur
den Buchteil und liesse den Rest **unbewacht** an der Boerse stehen.

`bueche_groessen_abgleichen(z, w)` zieht das Buch auf die Boersenkontrakt-
zahl - in beide Richtungen, mit Journalzeile `aktion=anpassen`,
`grund=handanpassung`. Unangetastet bleiben Stop, Ziel und Einstieg (die
Handelsentscheidung bleibt die der Spur), es wird KEINE Order geschickt,
und die Buchhaltung der Runde bleibt unberuehrt: die kommt aus der
eroeffnen-Zeile im Journal, nicht aus dem Zustand. Die neue Aktion ist fuer
den Rundenleser unsichtbar (er kennt nur eroeffnen/funding/schliessen) -
so entsteht aus einem Handgriff keine erfundene Runde.

## 3. Eine Entschuldigung darf nicht ewig gelten

Die Geisterpruefung entschuldigt eine fehlende Position, wenn ihre Order
gefuellt ist (Wettlauf Order -> Position, HBAR 21.09.2026). Diese Order
bleibt aber FUER IMMER `accFillSz > 0` - auch nachdem ein Mensch die
Position laengst geschlossen hat. BZ, CL und CRCL blieben so zwei Zyklen
lang Karteileichen: an der Boerse weg, im Buch mit Platz, Stop und Ziel,
und jeder neue Einstieg war blockiert.

Regel: die Fuellung zaehlt nur in einem Grace-Fenster nach dem Eroeffnen
(`_GEIST_FUELLUNG_GRACE_MIN = 10` Minuten). Ohne Eroeffnungszeit bleibt es
konservativ (nicht ausbuchen) - eine echte Position ohne Buch liefe
unbewacht, das wiegt schwerer als eine Karteileiche.

## 3a. Die Geisterpruefung kennt nur ZWEI Zustaende - ein Verkauf ist der DRITTE

Der teuerste Befund dieser Klasse entsteht, wenn ein Mensch ueber Nacht **verkauft**
(Stops setzen und liegen lassen, dann weg), statt eine Position zu schliessen.
Gemessen: vier echte Live-Positionen wurden zwischen 19:37 und 06:04 von Hand
verkauft. Die Boerse fuehrte die Ergebnisse die ganze Zeit (`STRK realizedPnl
+70,76 USD`, `SOL +0,96`, `QUANT -18,47`) - aber das Buch buchte jede Position
als `grund="buchbereinigung_geist"` mit **Erloes 0.00**.

Die Mechanik dahinter: `bueche_geister_aus` liest `if groesse is not None and
abs(groesse) >= 1e-9` - **da oder weg**. Der Zustand "die war da und ist kleiner
geworden, weil verkauft wurde" faellt durch. Dazu kommt die **Reihenfolge** in
`buche_abgleich`: die Geisterpruefung loescht zuerst, und `bueche_groessen_abgleichen`
zieht erst DANACH das Buch auf die Boersengroesse. Bei einer auf null gelaufenen
Position war die Groesse schon weg - die zweite Stufe konnte nichts mehr
angleichen.

**Der Verkauf braucht einen KURS, und der steht nicht dort, wo man ihn sucht.**
`/account/positions-history` liefert `avgPx: None`, weshalb der Ergebniszugriff
(`_geist_erloes`) ins Leere laeuft und neutral bucht. Der Ausfuehrungspreis steht
ausschliesslich in `/api/v5/trade/fills` (`fillPx`, `fillSz`, `side`, `ts`). Die
Faelle aus einer Nacht lagen in **mehreren Wellen** (STRK ueber 122.484 Stueck in
drei Fenstern) - der mengengewichtete Kurs aller Fuellungen ist die richtige
Zahl, der letzte Fill allein waere geraten.

**Die Reihenfolge ist der Fix, nicht die Existenz der Funktion.** Ein Abgleich,
der nach der Geisterpruefung laeuft, kann den Verlust nicht mehr heilen. Jede
Buchhaltungsstufe, die eine Position aus dem Buch entfernt, gehoert **vor** jede
Stufe, die sie anpassen wuerde - und beide duerfen nie dieselbe Frage stellen.

Drei Faelle, die vorher keiner konnte:

| Buch | Boerse | Verkauf bezeugt | Buchung |
|---|---|---|---|
| 8.033 | 0 | ja | **verkauf** zum echten Kurs, Position raus |
| 8.033 | 5.000 | ja | **verkauf** 3.033, Rest bleibt im Buch |
| 334 | 0 | nein | Geist - neutral, **als neutral benannt** |

- **Ein Verkauf braucht den Kurs; ohne Zeugen wird nichts behauptet.** Die
  Alternative zum Neutral-Buchen ist nicht "ungefaehr", sondern geraten.
- **Ein Grund `handanpassung` ist kein Verkauf.** Er zieht die MENGE nach und
  laesst die Kapitalkurve unveraendert - der Erloes fehlt dort fuer immer. Wer
  eine Preisfrage mit einer Mengenfrage beantwortet, verliert das Ergebnis.
- **Die Nettokurve darf den Verlust nicht schoenen, aber auch nicht erfinden:**
  eine Korrektur an den ALTEN Geist-Zeilen bleibt eine eigene, benannte
  Arbeit - die Funktion repariert den Pfad, nicht die Vergangenheit.

## 3b. Eine verkaufte Position: der Erloes gehoert in `nominal_usd`, in `margin_usd` die Margin

Die Verkaufsbuchung `buche_verkaeufe_aus_boerse` schreibt `erloes = preis * menge` in BEIDE Felder — `nominal_usd` (richtig, das ist der Nennwert) UND `margin_usd` (falsch). Die Rundenleser rechnen `ergebnis = margin_usd(schliessen) − margin_usd(eroeffnen)` (`runden_xperp` in `auswertung_alle.py`) — die Auswertung liest das Margin-Feld der schliessen-Zeile als Erloes. Eine einzige so geschriebene Zeile erzeugt einen Phantomgewinn in der Groessenordnung des NENNWERTS: XAU 96 Kontrakte @ 4150 -> "Erloes" 398.419 USD gegen ~22 USD Einstiegs-Margin -> +398k in `kennzahlen_fuer` und damit in Handelszentrale, Tagesbericht und Strategiekennzahlen, waehrend die Boerse einen PnL im Dollar-Bereich bezeugt.

Regel fuer jeden Schreibpfad einer schliessen-Zeile: `margin_usd` traegt die Margin der Position (das Kapital, das beim Schliessen zurueckfliesst), `nominal_usd` den Nennwert des Verkaufs. Vor dem Einbau die Feldbedeutung gegen die `runden_*`-Funktionen in `auswertung_alle.py` lesen — die sind die Wahrheit darueber, welches Feld die Auswertung als Erloes liest.

**Erkennen:** zwei Auswertungen mit verschiedenen Rechenbasen zeigen den Schaden an. `spur_audit` rechnet Runden PROZENTUAL aus den Preisen (p1/p0−1) und ist gegen falsch befuellte Betragsfelder immun; `auswertung_alle.kennzahlen_fuer` rechnet mit den Betragsfeldern der Zeile. Meldet einer eine absurde Zahl und der andere normal, ist ein Feld vergiftet — nicht der Handel. Der `grund` der Zeile ist der Wegweiser zum Schreiber: `grep` auf den Grund findet die Funktion, die das Feld falsch befuellt. Diagnose in dieser Reihenfolge: (1) `kennzahlen_fuer` mit `n`/`ergebnis` ausgeben, (2) Journalzeilen mit |Betrag| > 1000 listen — preis/stop/ziel sind Preise und normal, verdaechtig sind die Betragsfelder, (3) die eine Zeile -> `grund` -> Schreiber gefunden.

## 4. Ein reparierter Schreibpfad repariert die ALTEN Zeilen nicht

Der Code ist die halbe Miete. Was er bisher falsch geschrieben hat, steht
weiter in den Journalen und wirkt weiter - eine Wache, die nur den Code
prueft, sieht es nie. Nach JEDEM Fix an einem Schreibpfad:

1. die bestehenden Dateien nach Zeilen aus dem alten Pfad absuchen
   (`grep` auf den Grund/das Merkmal, hier `buchbereinigung_geist`),
2. ein **Nachzieh-Werkzeug** bauen (Vorschau ist Standard, `--anwenden`
   schreibt, vorher eine Kopie `handelsjournal.bak-JJJJMMTT.csv`),
3. eine **Routine** daraufsetzen (Cron ohne Modell, leere Ausgabe = nichts
   senden), damit der Fall nicht wieder von Hand auffallen muss.

Regeln fuer das Werkzeug:

- **Mit DERSELBEN Paarungsregel lesen wie der Verbraucher** (hier die FIFO-
  Paarung aus `wachen_xperp.runden_aus_journal`: eroeffnen = Einsatz,
  schliessen = Erloes, je Instrument in Reihenfolge). Eine nachgebaute
  Paarung korrigiert auf einen Wert, den hinterher niemand verrechnet.
- **Nur den einen Wert ersetzen.** Keine Zeile loeschen, keine andere Zahl
  anfassen - das Journal bleibt die Wahrheit.
- **Der Korrekturwert ist NEUTRAL (Einsatz zurueck), nicht "das echte
  Ergebnis".** Bei diesen Zeilen stand die Position in Wahrheit noch (sie
  wurde am selben Abend zurueckgebucht) - ein Boersenergebnis gibt es dazu
  nicht. Ein erfundenes Ergebnis waere derselbe Fehler in der anderen
  Richtung.
- **Kaputte Zeile = Merkmal UND Wert** (`grund = buchbereinigung_geist`
  und Erloes genau 0.00). Nur das Merkmal zu pruefen trifft auch einen
  echten Stop, der wirklich 0 zurueckgab.
- **Wiederholbar**: nach dem Lauf findet ein zweiter Lauf nichts mehr.

Regel fuer die Routine (gilt fuer jedes Werkzeug, das eine GANZE Datei neu
schreibt): **Ruhe-Bedingung gegen den Schreiber.** Ein Journal, das juenger
als ein paar Minuten ist, wird NICHT angefasst - das Werkzeug liest und
schreibt die komplette Datei, mitten in einen laufenden Zyklus liefe eine
frisch angehaengte Zeile verloren. Ein Zyklus dauert Sekunden bis Minuten,
der Takt der Routine ist Stunden: Warten kostet nichts.

Nachweis, den ein solcher Nachzieher liefern muss:

- genau EINE Zeile unterscheidet sich von der Sicherung (`Compare-Object`),
  Zeilenzahl unveraendert,
- der zweite Lauf meldet "keine kaputten Zeilen gefunden",
- die Kurve VOR und NACH: hier Ruecklauf 81,95 -> 65,11 (Luft zum Kill-Deckel
  100 damit 34,89 statt 18,05),
- die Wache laeuft gegen die echten Buecher und schweigt,
- `spiegelstand.py` byte-gleich (die Korrektur muss auch nach Q:).

## Nachweis-Muster

1. Trockenlauf gegen die Boerse, ohne zu schreiben: Buch und
   `/account/positions` je Position gegenueberstellen und die Abweichungen
   ausgeben.
2. Erst danach den echten Zyklus laufen lassen (die Spur-Skripte startet
   der Dauerlauf JEDEN Zyklus als Kindprozess - Codeaenderungen wirken
   sofort, nur `dauerlauf.py` braucht einen Neustart).
3. Die neuen Journalzeilen einzeln vorlesen: Einsatz, zurueck, Grund.
4. Die Drawdown-Kurve VOR und NACH vergleichen. Der Beweis ist die Zahl:
   71,14 -> 81,95 statt 168,22.
5. `spiegelstand.py` laufen lassen (Bedingung 4).

## Was der Test mitbringen muss, wenn Buchhaltung geaendert wird

Drei Punkte, die sich beim Bauen einer Verkaufsbuchung als Kosten zeigten - sie
sind allgemein, nicht nur fuer diese Funktion:

- **Der Testfall ist der echte Schadensfall, nicht der Normalfall.** Ein Test
  gegen die echten Zahlen einer verlorenen Nacht (Buchmenge, Boersenrest,
  Fuellungskurs) deckt die Einstufung ab, die eine frisch gebaute Fassung
  zuerst falsch hatte: eine GANGZ verkaufte Position hat an der Boerse `0`, und
  ein Test der auf den Restbestand stellt (`boerse > 0` heisst Teilverkauf) -
  genau das fehlt bei `0`. Ohne Fuellungen bleibt sie Geist, obwohl die Boerse
  den Verkauf bezeugt hat. **Die Einstufung entscheidet sich am ZEUGEN, nicht
  am Restbestand.**
- **Ein Test, der den Boersenzugang braucht, prueft den Buchpfad nicht.** Die
  Attrappe muss am MODUL gesetzt werden, das der Aufrufer importiert - und
  funktioniert das nur, wenn der Aufrufer den Namen im Funktionsrumpf bindet
  (`import x as y` dort, nicht auf Modulebene). Sonst antwortet die echte
  Boerse, der Test vergleicht gegen seine eigene Attrappe und meldet eine
  fremde Zahl (gemessen 0,0567 statt 0,0537).
- **Ein Netzausfall darf nicht als leerer Plan durchgehen.** `plan()` ohne
  `try` wirft durch; mit leerer Liste meldet der Aufrufer "alles stimmt". Der
  Rückgabewert "Boerse nicht erreichbar" muss **ausdruecklich** vom leeren Plan
  unterscheidbar sein, sonst liest der Aufrufer den Ausfall als Bestaetigung.

Und die Gegenprobe wie immer: den Kernfix zuruecknehmen und schauen, **genau
welcher** Test rot wird. Ein Test, der bei zurueckgenommenem Fix gruen bleibt,
prueft nichts.

