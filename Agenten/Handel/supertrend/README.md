# supertrend - Richtungswechsel mit der Linie als Stop

Papier-Spur auf genau einem Indikator: `supertrend()` aus
`../xperp/indikatoren.py` - importiert, nicht nachgebaut. Kein Orderpfad,
kein Broker-Aufruf. `wachen.json` traegt `handel_erlaubt: false`; `--live`
verweigert mit genau einem Grund, in dem das Wort Freigabefenster NICHT
vorkommt.

## Die Idee

Der SuperTrend legt Baender im Abstand `faktor * ATR` um den Kerzenmittel-
punkt und zieht sie nur in Trendrichtung nach, nie zurueck. Diese Sperre ist
der ganze Indikator: ohne sie zappelt er mit jedem Ausreisser und liefert
doppelt so viele Signale wie er soll.

Gehandelt wird der Wechsel der Richtung - nicht der Trend selbst.

## Das Signal

| Seite | Bedingung |
|---|---|
| LONG  | Richtung wechselt von `-1` auf `+1` |
| SHORT | Richtung wechselt von `+1` auf `-1` |

Parameter `n=10`, `faktor=3.0`. Zeitrahmen 4H, Instrumente BTC-USDT,
ETH-USDT, SOL-USDT.

## Die Besonderheit: die Linie IST der Stop

Anders als die drei Schwesterspuren hat diese einen zweiten Ausstieg. Der
SuperTrend-WERT ist zugleich der Trailing-Stop: kreuzt der Schluss die Linie
(oder kippt die Richtung), wird mit Grund `trailing` geschlossen - auch dann,
wenn weder der feste Stop noch das Ziel erreicht ist.

Damit hat eine Position drei Ausgaenge:

| Grund | Wann |
|---|---|
| `stop` | fester Stop aus dem Pflichtrahmen |
| `ziel` | `ziel_r_vielfaches` mal Stop-Abstand erreicht |
| `trailing` | Schluss kreuzt die SuperTrend-Linie / Richtung kippt |

Der feste Stop bleibt trotzdem noetig: er ist die Zahl, gegen die die
Positionsgroesse gerechnet wird, und er greift auch dann, wenn der Kurs in
einer Kerze durch die Linie springt.

## Groesse, Stop, Ziel

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
| `handeln.py` | Der Zyklus: Kerzen, Signal, Ein- und Ausstiege inkl. Trailing, Journal, Zustand, Spiegelung |
| `wachen.json` | Alle Tore, jede nicht offensichtliche Zahl mit `_`-Kommentarfeld |
| `handelsjournal.csv` | Jede Buchung, entsteht beim ersten Papierlauf |
| `zustand.json` | Offene Positionen und `letzter_lauf` (der Herzschlag) |
| `tests/test_supertrend.py` | 25 Tests, ohne Netz |

## Aufruf

```
python handeln.py --vorschau   was waere dran, schreibt NICHTS
python handeln.py --papier     ein Papierzyklus mit Journal
python handeln.py --wachen     die Bedingungen als Momentaufnahme
python handeln.py --live       verweigert, nennt den Grund
```

## Bedingung 4: Journal ausser Haus

Nach jedem Zyklus gehen Journal und Zustand nach `journal_zweitziel`
(`Q:\Handel_Journal\supertrend`).

## Tests

```
cd tests
..\..\scanner\.venv\Scripts\python.exe -m unittest test_supertrend -v
```

Die Fixture ist ein Trend, der bei Kerze 300 scharf dreht; bei 303 Kerzen
liegt der Richtungswechsel des SuperTrend genau auf der letzten - ausgemessen,
nicht geraten. Zusaetzlich zu den fuenf Pflichtpunkten wird der Trailing-Stop
eigens geprueft: er greift, wenn die Richtung kippt, und er greift NICHT,
solange der Trend traegt. Wo ein Test die Spiegelung beruehrt, zeigt
`journal_zweitziel` auf einen Temp-Ordner, nie auf `Q:`.
