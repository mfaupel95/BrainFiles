# Tor-Regeln pruefen, bevor eine Schwelle bewegt wird

Wann: ein Auftrag wie „erlaubte Volatilitaet erhoehen", „die Tore sind zu
streng", „mehr Runden erzeugen", oder wenn eine Zahl in einer `wachen.json`
anders sein soll.

**Eine Schwelle ist erst dann der Hebel, wenn gezaehlt ist, wie viele Kandidaten
sie HEUTE abweist.** Ohne diese Zaehlung aendert man eine Zahl, die niemanden
bremst, und meldet eine Verbesserung, die keine ist.

## Prozedur

1. **Was weist die Spur ueberhaupt ab?** Die Spur fuehrt ein
   Ablehnungsprotokoll - nach GRUND zaehlen, nicht lesen:

   ```bash
   tail -n 200 <spur>/ablehnungen.csv | awk -F, '{print $NF}' | sort | uniq -c | sort -rn
   ```

   Die letzte Spalte ist der Grund. Vorsicht bei Zaehlzeilen wie
   `nicht mehr erreicht`: das ist KEIN Ablehnungsgrund, sondern die Zahl der
   Maerkte, die der Lauf in diesem Zyklus nicht mehr erreicht hat.
2. **Die eigene Auswertung fahren, nicht den Code lesen.** `scanner/scan.py`,
   `prognose.py` und die `--vorschau` der Spur drucken je Kandidat die Kennzahl
   UND die Tor-Spalte (`JA` / `-`). Die Verteilung der Kennzahl gegen die
   Schwelle stellen: liegen die JA-Kandidaten weit unter der Grenze, ist sie
   nicht der Blocker (gemessen: JA-Kandidaten bei `volatilitaet_pa` 0,67-1,18
   gegen eine Grenze von 1,2).
3. **Verschieben und DIESELBE Messung wiederholen - die Wirkung als Zahl
   nennen.** Ein ehrliches Ergebnis darf „null neue Kandidaten" sein:
   von drei Maerkten im neu erlaubten Band erreichte keiner die naechste
   Schwelle (Score 60) - die Aenderung wirkt also erst, wenn ein Kandidat auch
   die naechste Huerde schafft. Das gehoert in die Antwort, nicht die blosse
   Zeile „Grenze erhoeht".
4. **An allen Stellen aendern, an denen dieselbe Kennzahl dasselbe Tor ist**, je
   Stelle datiert vermerken und mit `git diff --numstat` je Datei pruefen
   (spur-`wachen.json` UND der Marktscanner `prognose.json` fuehren dieselbe
   Grenze; beide im selben Commit).

## Pitfalls

- **Nicht jede Zahl in der `wachen.json` ist ein bindendes Tor.** Guthaben,
  Freigabefenster und Score binden meist zuerst. Vor jeder Schwellenaenderung die
  Sperrzeilen der Spur lesen (`sperrgruende.py`, die eigene `--vorschau`) und den
  BINDENDEN Grund benennen - sonst wird die falsche Zahl optimiert.
- **Ein Buchdeckel ist kein Kontodeckel.** `max_gesamt_usd` begrenzt die Summe
  der OFFENEN Positionen im Buch, nicht das freie Guthaben bei der Boerse. Eine
  Spur ohne eigenes Guthaben-Tor laeuft bei gebundenem Konto in jeden Kandidaten
  und bekommt `insufficient balance` zurueck (Scanner 02.10.2026: 442 von 444 USDC
  gebunden, 1,76 frei, kein Tor vorhanden). Das Tor gehoert in `pruefe_einstiege`,
  liest das Konto EINmal je Zyklus (nicht je Kandidat) und lehnt mit EINEM
  Ereignis je Waehrung ab - ein volles Konto schreibt sonst 18 Zeilen, die sich
  wie 18 verschiedene Ablehnungen lesen.
- **Die Quote gehoert aus dem INSTRUMENT, nicht aus einer Konstanten.** Ein
  Abruf, der eine feste Waehrung nennt (`guthaben_usdt()`), liefert 0,0 und sieht
  wie ein leeres Konto aus, wenn das Konto eine andere Quote fuehrt. `okx.quote(inst)`
  plus `guthaben(ccy)` haelt beides zusammen; ein Altname bleibt als Altname.
  Merksatz: ein Abruf, der eine Waehrung nennt, die es nicht gibt, ist kein
  leeres Konto, sondern ein falscher Abruf.
- **Eine Waehrung auf dem Kontostand ist noch kein Handelsweg.** Vor jeder
  Umstellung auf eine andere Quote zuerst zaehlen, ob die Boerse in dieser Quote
 ueberhaupt Paare fuehrt (`public/instruments`, `quoteCcy` zaehlen). Gemessen
 02.10.2026 auf dem OKX-EEA-Konto: 438 USDC, 0,00 USDT, 0,0003 EURC - und NULL
 EURC-Spotpaare bei 408 USDT- und 298 USDC-Paaren. Ein `universum.quotes`, das
 beide Waehrungen nennt, laesst die Spur Werte bewerten und vorschlagen, die das
 Konto nicht bezahlen kann.
- **Eine Schwelle in einem Universum-Filter zaehlt JE QUOTE.** Senkt man sie
 nicht, weil "das Feld kleiner wird", sondern weil die Zahl gilt, gilt sie pro
 Waehrung - ein Feld mit zwei Quotes verliert die Haelflfte seiner Paare, ohne
 dass jemand die Zeile liest. Nebenher die Zahl Paare je Quote bei 3, 1, 0,5, 0,2
 Mio messen und die gewaehlte Grenze als Zahl nennen.
- **Zwei Groessen gehoeren zusammen: Volatilitaetsgrenze und Stop.** Ist die
  Tagesspanne eines Instruments groesser als der Stop der Spur, wird der Stop
  zum Rauschen. Eine Grenze anheben, ohne den Stop mitzuziehen, verschiebt nur,
  WELCHER Verlust eintritt - die Geometrie (Break-even gegen Trefferquote) ist
  deshalb Teil der Entscheidung, nicht ein spaeterer Feinschliff.
- **Ein Kennzahl-Wert ohne Einheit und Bezug ist nicht vergleichbar.** Vor dem
  Vergleich angeben, worauf die Zahl sich bezieht (Jahresvolatilitaet gegen
  Tagesspanne gegen Stop-Prozent) - zwei Zahlen mit gleichem Namen und
  verschiedenem Bezug sehen wie ein Widerspruch aus und sind keiner.
- **Nach jeder Schwellenaenderung die Suite der Spur laufen lassen**, nicht nur
  die geaenderte Zahl ansehen: Tests, die eine feste Anzahl oder einen festen
  Kandidaten einfrieren, gehen dabei kaputt und zeigen, dass irgendwo eine zweite
  Wahrheit steht.
