# Spur-Optimierung: der Hebel war nie eingestellt

*04.10.2026 · Auftrag Max: „Handel-spur-Optimierung" · Befund: `replay.py --setzen` wirkte nicht*

## Der Befund in einem Satz

Die Optimierungssuche des Hauses hat neunmal **dieselbe** Rechnung gefahren und
„kein Hebel" gemeldet — nicht weil keiner da ist, sondern weil der Schalter, der
ihn einstellen soll, stillschweigend verworfen wurde.

## Wie es auffiel

Auftrag war, die Handelsspuren zu optimieren. `kosten_wendepunkt.py` zeigte, dass
**vier Spuren dieselbe Ausstiegsgeometrie fahren**:

    squeeze, wavetrend, macd_mtf, supertrend
      pflicht_stop_prozent_min = 5.0
      ziel_r_vielfaches        = 2.0

Das sind keine vier optimierten Spuren, das ist eine Einstellung, viermal kopiert.
Also: Geometrie messen. Zwei Läufe, dieselbe Spur, `squeeze`:

| Aufruf | Ausstiege | Treffer | G/V je Runde |
|---|---|---|---|
| `--setzen pflicht_stop_prozent_min=5.0 --setzen ziel_r_vielfaches=2.0` | 529 | 26,5 % | −1,015 |
| `--setzen pflicht_stop_prozent_min=3.0 --setzen ziel_r_vielfaches=1.5` | 529 | 26,5 % | −1,015 |

**Bitgleiche Zahlen für zwei verschiedene Geometrien.** Das ist der Moment, in dem
ein Werkzeug als defekt gilt.

## Die Ursache

`replay.py` hatte zwei Namen für dasselbe:

* `lauf_c` und `lauf_feed` (Familien B und C) nehmen `setzen=`
* `lauf_a`, `lauf_mehrzeitrahmen`, `lauf_eigene_rechnung` (Familien A und D)
  nehmen **`wachen_patch=`**

In `main()` stand an der Aufrufstelle kein Patch. Für `squeeze` — eine Kerzenspur
der Familie A — **`--setzen` lief ins Leere**, ohne Fehlermeldung. Die
Wachen-Kopie enthielt nach dem Lauf weiterhin `Stop 5.0 / Ziel 2.0` und
`_backtest_gesetzt = None`.

Drei Aufrufstellen sind jetzt verdrahtet (`replay.py` Zeilen 1797, 1812, 1847).

## Der Gegenbeweis

Nach dem Fix, derselbe Vergleich:

| Geometrie | Ausstiege | Treffer | G/V je Runde | nach 0,10 % Gebühr |
|---|---|---|---|---|
| 5,0 % / 2,0R (heute) | 529 | 26,5 % | −1,015 | −1,215 |
| 3,0 % / 1,5R | 670 | 37,0 % | −0,524 | −0,724 |

Zwei verschiedene Geometrien, zwei verschiedene Ergebnisse.

## Und was die Messung danach sagt

**Verdikt: verworfen.** Beide Geometrien sind über 529 bzw. 670 Ausstiege
**deutlich negativ** — nicht knapp negativ, sondern rund −0,5 bis −1,0 USD je
Runde. `squeeze` hat im getesteten Bereich (Stop 3/5/7 %, Ziel 1,5/2/3R) **keine
tragfähige Ausstiegsgeometrie**.

Das ist ein *gemessenes* „verworfen", kein „nicht entschieden": die Stichprobe ist
mit 529 Ausstiegen gross genug, und der Skill verlangt 30 je Hälfte.

## Die Lehre

Der Optimierungs-Skill warnt: *„Ein geratener Name wirkt nicht: alle Kandidaten
sind identisch und die Suche meldet 'kein Hebel', obwohl nie etwas verändert
wurde."* Das ist genau hier eingetreten — nur nicht durch einen **geratenen**
Namen, sondern durch einen **falsch benannten**, der beim Aufruf still verschwand.

Die Regel daraus: **ein Schalter, dessen Wirkung niemand geprüft hat, ist kein
Schalter.** Vor jeder Suche zwei Kandidaten fahren und die Kennzahlen vergleichen
— wenn sie gleich sind, ist nicht der Markt schuld, sondern das Werkzeug.

## Nebenbefunde, ungeprueft

* `replay.py` liest fuer `BTC-USDC` dieselbe Reihe wie fuer `BTC-USDT`
  (50.422 Kerzen). Der Backtest misst USDT-Daten, die Spur handelt USDC — bei
  BTC unter 0,1 % Abstand, dokumentierte Naeherung.
* `optimieren.py` puffert die gesamte Ausgabe bis zum Ende: 24 Monate x 9
  Kandidaten liefen 13 Minuten ohne ein einziges Byte. Als Werkzeug fuer
  Zwischenentscheidungen unbrauchbar.
* Vier Tests der Replay-Suite sind rot (`test_replay`, 106 Tests). Der Vergleich
  gegen HEAD lief in dieser Sitzung nicht zu Ende — **die Vorbestandlichkeit ist
  nicht belegt**.