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

## Der Gegenbeweis, und eine Korrektur an mir selbst

Nach dem Fix, mit der **Hausfunktion** `kosten_wendepunkt.kennzahlen()` — nicht
mit einer Zeilenzählung:

| Geometrie | Runden | Treffer | G/V gesamt | je Runde |
|---|---|---|---|---|
| **3,0 % / 1,5R** | 1007 | 39,0 % | −75,74 | **−0,074** |
| 3,0 % / 3,0R | 779 | 21,8 % | −312,16 | −0,384 |
| 5,0 % / 2,0R (heute) | 579 | 28,0 % | −464,18 | −0,803 |
| 7,0 % / 1,5R | 428 | 31,8 % | −616,00 | −1,439 |

**Die 3-%-Geometrie kostet 0,074 USD je Runde statt 0,803 — rund zehnmal weniger.**
Das ist keine Optimierung, das ist die Abstellung einer Fehlstellung.

### Der Fix wirkt, zweifalt belegt

Vier Laeufe wurden ueber die Zeit hinweg gestartet, in der der Fix eingebaut
wurde. Die Wachen-Kopie ist dabei **kein Beweis**: `lauf_a` wendet den Patch auf
das W-Dict im Speicher an (`replay.py` 794) und **schreibt ihn nicht in die
Kopie** — die Kopie zeigt deshalb immer die Ausgangswerte. Der Docstring sagt
ausdruecklich „so setzt der Optimierer …": die Faehigkeit war da, die Verdrahtung
fehlte.

Die Beweiskette ist die Geometrie selbst:

| Lauf | Geometrie aufgerufen | Ergebnis | gelesen als |
|---|---|---|---|
| `rp_basis` | 5,0 / 2,0 | 579 Runden, −0,803 | Grundlinie |
| `rp_s3_15` | 3,0 / 1,5 | 579 Runden, **−0,803** | **vor dem Fix — bitgleich zur Grundlinie** |
| `rp_s3_30` | 3,0 / 3,0 | 779 Runden, −0,384 | nach dem Fix |
| `rp_s7_15` | 7,0 / 1,5 | 428 Runden, −1,439 | nach dem Fix |
| `fx_a` | 3,0 / 1,5 | 1007 Runden, −0,074 | nach dem Fix |

**Dieselbe Geometrie (3,0/1,5) liefert vor dem Fix exakt die Grundlinie und nach
dem Fix ein voellig anderes Ergebnis.** Damit ist der Fehler in beide Richtungen
gemessen: er wurde gefunden und er ist weg.

### Was ich zuruecknehme

Ein Zwischenstand nannte **−1,015** und **−0,524** USD je Runde. Beide Zahlen
sind falsch und zwar zweifach:

1. **Ich habe Rohzeilen gezaehlt statt Runden.** `EINSTIEG`/`AUSSTIEG`-
   Zeilen sind keine Runden; die Paarung macht daraus 579, nicht 1181.
2. **Ich habe eine Datei ausgewertet, die noch geschrieben wurde.** Der Lauf
   lief im Hintergrund; mein Zwischenstand las einen Teilstand.

Die Hausfunktion rechnet die Paarung, die Zwangsschluesse und die Marke; eine
gezaehlte Zeile tut das nicht. **Die Lehre ist nicht die Zahl, sondern die
Reihenfolge: bei einem Hintergrundlauf erst rechnen, wenn der Prozess beendet
ist — eine geschriebene Datei ist kein fertiges Ergebnis.**

## Und was die Messung danach sagt

**Verdikt: die heutige Einstellung ist verworfen.** 5,0 % / 2,0R kostet 0,803
USD je Runde ueber 579 Runden; 3,0 % / 1,5R kostet 0,074 ueber 1007 Runden.
Das ist kein „nicht entschieden" — die Stichprobe traegt die 30-Ausstiege-
Schwelle je Haelfte reissich.

**Die beste gefundene Geometrie bleibt leicht negativ** (−0,074 USD je Runde vor
Gebuehr). Sie traegt also noch nicht — aber sie ist zehnmal nah an der Nulllinie,
und ob die uebrigen sieben Kandidaten unter 0,0 % liegen, ist gemessen **nicht**
entschieden: der Optimierer lief bis zum Ende dieser Sitzung nicht durch.

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