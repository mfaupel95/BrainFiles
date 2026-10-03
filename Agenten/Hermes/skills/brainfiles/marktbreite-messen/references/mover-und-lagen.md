# Wer bewegt sich - und traegt die Bewegung noch?

`breite.py` sagt, OB der Markt oben ist: wie viele Paare stehen ueber ihrer
EMA200. Das ist der **Zustand**. Es beantwortet nicht die zweite Frage: **was
bewegt sich darin, und ist die Bewegung noch getragen.**

Gemessener Anlass: ein Token mit +129 % in 30 Tagen, 1,1 % unter dem
90-Tage-Hoch. Die Breite meldete an diesem Tag 89,7 % und damit "Trend intakt".
Die Tageskerze zeigte: das Volumen ist vom 9,9-fachen auf das 1,7-fache des
Median gefallen. Zwei Aussagen ueber dasselbe Ding - und die zweite ist die
wichtigere. Eine Breite, die nur zaehlt, WER ueber der Linie steht, kann nicht
sehen, dass die Kaeufer weggehen.

## Werkzeug

`Agenten/Werkzeuge/topmover.py` (oeffentliche OKX-Schnittstelle, kein
Schluessel, rein lesend, nur abgeschlossene Tageskerzen):

    python Agenten/Werkzeuge/topmover.py                  # Lage aller Paare
    python Agenten/Werkzeuge/topmover.py --kriterien      # nur Kandidaten
    python Agenten/Werkzeuge/topmover.py --paares=NIGHT-USDT,BTC-USDT
    python Agenten/Werkzeuge/topmover.py --json           # Maschinenform
    python Agenten/Werkzeuge/topmover.py --schwelle 5     # Ausbruch ab 5x

Tests: `Agenten/Werkzeuge/tests/test_topmover.py` (25, ohne Netz - die Naht
ist `hole()`, `lage()` ist eine reine Funktion).

## Der Traeger kommt VOR dem Kurs

Die Reihenfolge der Pruefung ist die Aussage: **erst das Volumen, dann der
Kurs.** Ein Kurs ohne Volumen ist eine Zahl, ein Kurs mit Volumen ist ein
Signal. Deshalb rechnet die Lage ueber `volumen_faktor` und nicht ueber
`pct_30t`.

- **Volumen gegen den 30-Tage-MEDIAN, nicht gegen gestern.** "Heute 2x
  gestern" sagt nichts - gestern kann 0,2x Median gewesen sein, und die
  Verdopplung liegt trotzdem unter dem Median. Nur `x,x * Median` ist eine Zahl
  mit Bedeutung.
- **Der Median schliesst HEUTE aus.** Sonst hebt viel Volumen die eigene
  Messlatte (Rueckkopplung): die Bezugsgroesse wandert mit dem heutigen Tag.
- **Nur abgeschlossene Kerzen.** In der OKX-Antwort ist das `confirm == "1"`.
  Ein Tageshoch aus einer halben Kerze ist die haeufigste Falschaussage in
  solchen Werkzeugen - sie macht den Abstand zum Hoch zu klein.
- **Das Hoch kommt aus den Tageshighs**, nicht aus den Schlusskursen. Aus
  Schlusskursen gemessen meldet ein Instrument am echten Hoch eines, das 30 %
  darunterliegt.

## Die fuenf Lagen

| Lage | Bedingung | Aussage |
|---|---|---|
| `ausbruch` | ueber dem 90T-Hoch, Volumen ueber der Schwelle | Trend setzt sich fort |
| `getragen` | ueber EMA200, Volumen 1,5x - Schwelle | gesunde Bewegung |
| `ueberdehnt` | ueber EMA200, Volumen < 1,5x, aber < 2 % vom Hoch | hohes Chance-Risiko, duenner Traeger |
| `ballon` | ueber EMA200, Volumen < 1,5x, weiter vom Hoch | der Kaeufer geht weg |
| `schwach` | unter EMA200 | kein Kandidat |

`ueberdehnt` ist eine **eigene** Lage und nicht "nur ballon": hohes
Chance-Risiko bei duennem Traeger ist ein eigener Befund mit eigener Vorsicht.

**Die Reihenfolge entscheidet:** `ausbruch` wird VOR den Volumen-Laegen
geprueft. Ein Instrument ueber dem Hoch mit Volumen ist ein Ausbruch, kein
Ballon - die Volumenregel darf den Durchbruch nicht zurücksortieren.

## Kein Kandidat ist eine Lage, keine Zahl

Zu wenig Historie liefert `zustand=None` mit einem **Grund, der die Zahl
nennt** ("nur 150 Kerzen, EMA braucht 200"), nicht `0`. Dasselbe gilt fuer ein
fehlbares Instrument: die Rueckgabe traegt den **Namen**, sonst steht in der
Liste ein `?` und niemand weiss, welches gemeint war. Und `kandidat()`
behandelt eine fehlende Lage als **keinen** Kandidaten - sonst kauft man den
Unsinn, weil die Zahl nicht da war.

## ATR ist die Einheit fuer JEDE Prozentangabe

`atr14_pct` steht in jeder Zeile, weil ohne sie jedes "%-Ziel" eine Ausrede
ist: bei 8,3 % ATR liegt ein -20 %-Stop **innerhalb** der normalen
Tagesspanne. Die ATR ist damit die Pruefgroesse fuer jedes Stop-, Ziel- und
Abstandsargument, das man diskutiert - sie gehoert neben die Zahl, nicht in
eine Fussnote.

## Eine Ampel aus der Rendite ist eine FALSCHE Information

"+129 % in 30 Tagen" ist bei BTC (+4 %) ein Kauf und bei einem Memecoin eine
Warnung. Was unterscheidet, ist der Traeger und der Abstand zum Hoch. Deshalb
jede Zahl mit ihrer Groesse und jede Lage mit ihrer **Begruendung** - die
Begruendung steht in einer Fusszeile (`begruendungen()`), weil sie nicht in
eine Spalte passt und eine Lage ohne Grund ein Etikett ist.

## Tests, die sich selbst pruefen

Der Median-Ausschluss brauchte **zwei** Gegenproben-Iterationen, und beide
Fehlfassungen waren LEHRREICHER als die erste:

- **Drei Ausreiser verschieben den Median eines 30er-Fensters nicht.** Bei 27
  einheitlichen Werten liegen die beiden mittleren weiterhin bei 1000. Wer drei
  hohe Tage setzt, baut einen Test, der beim Fehler GRUEN bleibt.
- **Der Fehler wandert die Messlatte erst, wenn die Mehrheit des Fensters
  betroffen ist.** Also die Haelfte der Tage veraendern und beide Mediane
  ausrechnen (gemessen: 16000 mit, 1000 ohne).
- **Danach die eigene Erwartung nachrechnen.** Wer die Erwartung nach dem
  Umbau der Daten nicht neu bestimmt, prueft die alte Annahme - bei
  "alle Tage 1000" neben selbst gesetzten 30000ern ist sie falsch.

Merksatz: **die Erwartung eines Tests wird beim Aendern der Daten neu
GESCHRIEBEN, nicht mitgenommen.** Sonst testet der Test die alte Annahme.

Ausserdem: `1,0x Median` ist **"wie immer", nicht "Traeger da"**. Ohne Test
haelt man jedes gleichmaessig wachsende Instrument fuer ein Signal.

## Die Listenpflege

Ein doppelter Eintrag in der Paarliste erzeugt eine doppelte Zeile UND einen
doppelten Kandidaten in der Fusszeile. `test_paare_ohne_doppelte` faengt das -
und die Liste wird am besten aus einem Parse gehaelt, nicht per Textersatz
(dort stand derselbe Eintrag zweimal, weil ein Austausch den anderen
zurueckbrachte).

## Abgrenzung

- Breite/Regime ueber viele Paare: `marktbreite-messen` (dieses Blatt).
- Ein einzelner Wert mit Quelle und Zeitstempel: `markt-recherche`.
- Was das HAUS daraus handelt: `handel-spuren` - eine Lage ist ein Befund,
  keine Order. Ein Kandidat dieser Liste ist ohne Freigabekette kein Kauf.
