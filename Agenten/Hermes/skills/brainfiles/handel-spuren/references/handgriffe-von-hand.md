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
