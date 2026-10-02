Scanner-Befund 03.10.2026: die 124 Runden im Journal sind KEIN Beleg
=================================================================

BEFUND
------
Der Scanner wurde als mit Abstand beste Spur gefuehrt:

    124 Runden, +17,49 % auf den Einsatz, 85 % Trefferquote,
    Median +18,60 %, t = 15,3 - die einzige Spur mit belegtem Vorteil.

Das war kein Signal. Es war ein Rechenfehler im Einstiegspreis.

URSACHE (belegt, nicht vermutet)
--------------------------------
vorschlaege() in handeln.py nahm den Einstieg aus dem TAGESBERICHT
(bewertung.bewerten -> preis = schluss[-1] der 1D-Kerze). Der Bericht
ist ein Snapshot vom Vortag. Am 19.09. war er zwei Tage alt:

    Bericht 2026-09-17 05:30   AVAX-USDT  7,531
    Markt 19.09. 02:50        AVAX-USDT  8,535 - 8,747

Der Einstieg lag 12 % UNTER dem Markt. Daraus folgt:

  * Ziel = Einstieg + 2 x Stop  lag beim KAUF bereits im Markt
  * der naechste Zyklus (15 min spaeter) verkaufte im Ziel mit ~15 %
  * AVAX wurde alle 15 min neu gekauft und verkauft, weil das Ziel
    sofort wieder erfuellt war
  * 82 Runden an einem einzigen Tag, Summe +1866 % an diesem Tag

Drei unabhaengige Belege, dass es kein echter Handel war:

  1. 97 von 105 Ziel-Ausstiegen kamen nach 0,25 h. Ein echter
     Marktausstieg braucht Tage; das sind Zyklenabstaende.
  2. 81 von 123 Runden betrafen EIN Instrument (AVAX-USDT), alle mit
     100 % Trefferquote. Ein Streuportfolio kann das nicht.
  3. Score 60-69 war mit +18,78 % Mean deutlich besser als Score 80+
     (-0,46 %). Ein Signal, das mit hoeherer Ueberzeugung schlechter
     wird, ist kein Signal.

BILANZ DER EHRLICHEN RUNDEN (Haltedauer >= 6 h)
-----------------------------------------------
    ehrlich (>=6h)   n= 16   Treffer  38 %   Mittel  +1,99 %   Median -6,07 %
    Schein  (<6h)   n=107   Treffer  93 %   Mittel +19,22 %   Median +21,10 %

Der Scanner war auch ehrlich nicht die beste Spur: +1,99 % Mean bei
38 % Treffer ist statistisch nichts (n=16). Er lag auf dem Niveau von
xperp (t=1,3) und moondev_topmovers (t=1,9).

WAS DAMIT FALSCH IST
-------------------
  * strategie_kennzahlen.py meldete fuer den Scanner t = 15,3. Diese
    Zahl beschreibt den Rechenfehler, nicht das Signal.
  * Die Freigabe des Scanners stuetzte sich unter anderem auf diese
    Runden. Bedingung 1 (Netto-positiv) ist seit dem 19.09. per
    Auftrag Max entfallen; die uebrigen Kriterien bleiben - aber die
    Zahl 124 belegt nichts mehr.
  * Jede Aussage der Form "der Scanner ist die beste Spur" ist
    zurueckgenommen.

FIX (03.10.2026)
----------------
  * handeln.marktkurs(inst) ist die EINE Stelle, die den Kurs holt.
  * vorschlaege() benutzt den Jetzt-Kurs als Einstieg; Stop und Ziel
    (2:1) werden daraus gerechnet.
  * KEIN Rueckfall auf den Berichtspreis: ein alter Preis als
    Einstieg IST der Fehler.
  * Ein nicht abrufbarer Kurs ist eine Ablehnung ("Kurs nicht
    abrufbar"), keine Ausnahme - ein toter Markt darf den Zyklus
    nicht abbrechen.
  * Tests: scanner/tests/test_einstieg_ist_marktkurs.py (4),
    test_ablehnungen.BilligeToreTest (3). Gegenprobe belegt: mit
    zurueckgesetztem Code fallen 3 von 4.
  * Laufzeit wirkt sofort (Spur-Skripte startet der Dauerlauf je
    Zyklus neu); kein Neustart noetig.

Was die offenen 5 Positionen betrifft: ihre Einstiege stammen teils
noch aus der Fehlerzeit (Phantom-Abstaende bis -5,4 % beim Einstieg
gegenueber Markt). Sie sind im Buch mit zu niedrigem Einstieg
gefuehrt. Sie NICHT eigenmaechtig angefasst - buchbereinigung ist
Sache des Live-Laufs.

Belege: Agenten/Handel/scanner/tests/test_einstieg_ist_marktkurs.py,
Handelsregeln.md Abschnitt Marktscanner, Wiki Handel/Lektionen.md