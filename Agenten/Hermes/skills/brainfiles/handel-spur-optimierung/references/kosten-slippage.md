# Kosten messen statt annehmen (Slippage, Tiefe, Ausfuehrbarkeit)

Warum das eine eigene Messung braucht: bei Spuren mit kleinen Positionen in
duenen Maerkten ist die Kostenschaetzung im Wachenbuch (`slippage_pct`,
`gebuehr_pct`) oft der groesste Einzelposten — groesser als jede
Parameteraenderung. Eine Auswertung, die VOR Kosten nahe null und NACH Kosten
deutlich negativ steht, wird von dieser Annahme beherrscht. Wer dann Parameter
dreht, optimiert das Modell, nicht den Markt.

## Verfahren

1. **Stichprobe aus dem eigenen Journal.** Die juengsten Einstiege der Spur
   (Token/Instrument + Preis). Nur Zeilen, die ein Handel SIND — `zyklus`-,
   `quotes`-, `funding`- und `rollover`-Zeilen nicht mitzaehlen.
2. **Tiefe live holen, nicht schaetzen.** Fuer Krypto-Pools liefert
   `https://api.dexscreener.com/latest/dex/tokens/<adresse>` ohne Schluessel die
   Pools eines Tokens; genommen wird der mit der groessten
   `liquidity.usd`, dazu `priceUsd` und `marketCap`/`fdv`. Fuer Boersen-Spuren
   mit Orderbuch stattdessen die Orderbuchtiefe in der Naehe des Mid.
3. **Preiseinfluss rechnen (Constant Product).** Ein Kauf belastet die
   Quote-Seite, ein Verkauf ebenso:

       Round-Trip-Verlust in Prozent ~ 2 x Ordergroesse / Quote-Tiefe * 100
       (Quote-Tiefe = liquidity.usd / 2)

   Das ist der Kurveneinfluss OHNE Gebuehr, ohne Prioritaet und ohne MEV — die
   kommen oben drauf, nicht unten ab.
4. **Groessenleiter statt einer Zahl.** Immer mehrere Ordergroessen rechnen
   (z. B. 50/100/500) und Median, p25, p75 berichten. Der Median sagt, was der
   Normalfall kostet; die Perzentile zeigen, wie schief die Verteilung ist.
5. **Verteilung der Tiefe mitberichten.** Median und p10 der Pool-Tiefe und der
   Anteil der Pools unter einem Vielfachen der Ordergroesse (z. B. unter dem
   5-fachen).
6. **Gegen die Annahme stellen.** Das Ergebnis der eigenen Zahl aus dem
   Wachenbuch gegenueberstellen und das Urteil benennen: „zu streng", „in der
   Naehe", „zu freundlich".

## Was die Zahl bedeutet — und was nicht

- **Ein toter Pool ist kein teurer Pool.** Tiefe unter dem Mehrfachen der
  Ordergroesse heisst nicht „hohe Slippage", sondern **kein Fill**. Solche
  Kopien gehoeren als NICHT AUSFUEHRBAR gezaehlt (Gate), nicht mit dem
  Wachen-Satz bepreist. Wer sie mitrechnet, mischt zwei Dinge: Kosten und
  Nichthandelbarkeit.
- **Die Annahme beschreibt oft den Rand, nicht den Median.** Eine runde Zahl
  wie 3 % je Seite ist meist als Sicherheitszuschlag fuer den schlimmsten Fall
  gedacht. Gemessen liegt der Median bei kleinen Orders oft weit darunter — die
  Folge ist, dass das Buch SCHLECHTER aussieht, als es war. Das Urteil kann
  gleich bleiben („traegt nicht"), die Aussage „wie schlimm" war trotzdem vom
  Modell gepraegt.
- **Die Messung ist eine Jetzt-Messung.** Die Tiefe wird zum Messzeitpunkt
  geholt, nicht zum Einstiegszeitpunkt. Fuer die Frage „ist die Annahme zu
  freundlich" reicht das (Pools werden nicht nachtraeglich tiefer); fuer
  „was hat diese Runde gekostet" nicht.
- **Der ZEITVERSATZ ist ein eigener Messblock, nicht Teil der Slippage.**
  Gemessen wird die Luecke zwischen dem Vorbild-Trade und unserer Buchung
  (`Handel/zeitversatz_messen.py --anzahl N --json`, reine Standardbibliothek):
  je Kopie die Zeit des Vorbilds (`trade_zeit` im Vorbild-Feed) gegen unsere
  Journalzeit, ausgewertet in STUFEN (0-5, 5-15, 15-30, 30-60, 60-180,
  180-720 Minuten) mit Rundenzahl, Median und p75 des Versatzes je Stufe. Zwei
  Fallen: (1) **Ein konstanter Faktor in JEDER Zeile ist gesetzt, nicht
  gemessen** — bucht eine Spur `preis_vorbild * 1.05`, stehen in jeder Zeile
  dieselben 5 %; das ist eine Annahme der Spur und darf nie als Messwert ins
  Urteil, erst nachrechnen und dann als Annahme kennzeichnen. (2) Ohne
  Vorbild-Zeit in der Kopie ist der Versatz nicht rekonstruierbar — fehlt das
  Feld, das sagen statt schaetzen. Der Lauf gehoert als duenne Cron-Huelle nach
  `Agenten/Hermes/scripts/` und schreibt in eine Sammeldatei (Laufzeitdatei,
  nicht versioniert), damit ueber Tage eine Verteilung entsteht statt einer
  Momentaufnahme.

## Werkzeugmuster

Ein Skript in der Spurendatei (`<spur>/slippage_messen.py`) mit
`--anzahl`, `--groessen` und `--json`; reine Standardbibliothek (urllib),
Ergebnis als Tabelle plus Gegenuberstellung der Wachen-Annahme. Die Rechnung
und der Journal-Leser gehoeren in Tests ohne Netz (Pool-Daten ersetzen): der
Messwert aendert sich mit dem Markt, die Rechenregel nicht.
