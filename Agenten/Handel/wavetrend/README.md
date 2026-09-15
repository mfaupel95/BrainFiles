# wavetrend - Umkehr im ueberzogenen Bereich

Papier-Spur auf genau einem Indikator: `wavetrend()` aus
`../ti_indikatoren.py`. Kein Orderpfad, kein Broker-Aufruf.
`wachen.json` traegt `handel_erlaubt: false`; `--live` verweigert mit genau
einem Grund, in dem das Wort Freigabefenster NICHT vorkommt.

## Die Idee - und was sie NICHT ist

Der LazyBear-WaveTrend ist ein geglaetteter Oszillator um die Null.
Diese Spur ist **Mean-Reversion, nicht Trendfolge**: sie kauft, wenn der
Oszillator tief im ueberverkauften Bereich nach oben dreht, und verkauft
spiegelbildlich oben. Wer sie wie eine Trendspur liest, erwartet das
Gegenteil dessen, was sie tut.

Die Zone ist Teil des Signals, nicht Zierde. Eine Kreuzung um die Null
herum ist Rauschen; erst jenseits von +/- 40 ist die Bewegung so weit
gelaufen, dass eine Gegenbewegung wahrscheinlicher wird als ihre
Fortsetzung.

## Das Signal

| Seite | Bedingung |
|---|---|
| LONG  | `wt1[i-1] <= wt2[i-1]` und `wt1[i] > wt2[i]` (Kreuzung von unten) UND `wt1[i] < -40` |
| SHORT | `wt1[i-1] >= wt2[i-1]` und `wt1[i] < wt2[i]` (Kreuzung von oben) UND `wt1[i] > 40` |

`wt2` ist der 4er-SMA von `wt1` - die Kreuzung ist also `wt1` gegen seinen
eigenen kurzen Mittelwert.

Zeitrahmen 1H, Instrumente BTC-USDT, ETH-USDT, SOL-USDT.

## Groesse, Stop, Ziel

Risiko-normiert, alle Zahlen aus `wachen.json`:

```
stop_pct  = ATR / Kurs * 100, gezwungen in [pflicht_stop_prozent_min, ..max]
nominal   = risiko_je_position_usd / (stop_pct / 100)
nominal   = min(nominal, max_pro_trade_usd)
nominal  *= ratschen.groessenfaktor(ruecklauf, wachen)
ziel      = einstieg +/- ziel_r_vielfaches * stop_abstand
```

Die Drawdown-Ratsche kommt aus `../ratschen.py`, ueber den Pfad geladen.

## Dateien

| Datei | Inhalt |
|---|---|
| `handeln.py` | Der Zyklus: Kerzen, Signal, Ein- und Ausstiege, Journal, Zustand, Spiegelung |
| `wachen.json` | Alle Tore, jede nicht offensichtliche Zahl mit `_`-Kommentarfeld |
| `handelsjournal.csv` | Jede Buchung, entsteht beim ersten Papierlauf |
| `zustand.json` | Offene Positionen und `letzter_lauf` (der Herzschlag) |
| `tests/test_wavetrend.py` | 20 Tests, ohne Netz |

## Aufruf

```
python handeln.py --vorschau   was waere dran, schreibt NICHTS
python handeln.py --papier     ein Papierzyklus mit Journal
python handeln.py --wachen     die Bedingungen als Momentaufnahme
python handeln.py --live       verweigert, nennt den Grund
```

## Bedingung 4: Journal ausser Haus

Nach jedem Zyklus gehen Journal und Zustand nach `journal_zweitziel`
(`Q:\Handel_Journal\wavetrend`).

## Tests

```
cd tests
..\..\scanner\.venv\Scripts\python.exe -m unittest test_wavetrend -v
```

Die Fixture ist eine langsame Welle mit einer schnelleren Ueberlagerung.
Das ist Absicht: die langsame traegt `wt1` in die ueberzogenen Zonen, die
schnelle erzeugt zusaetzlich Kreuzungen in der Mitte. Der Test prueft
beides - das Signal muss in der Zone feuern und in der Mitte schweigen.
Wo ein Test die Spiegelung beruehrt, zeigt `journal_zweitziel` auf einen
Temp-Ordner, nie auf `Q:`.
