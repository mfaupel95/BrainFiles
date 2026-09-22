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
