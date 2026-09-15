# macd_mtf - Trendfolge nur bei Einigkeit

Papier-Spur auf genau einem Indikator: `macd_mtf()` aus
`../ti_indikatoren.py`. Kein Orderpfad, kein Broker-Aufruf.
`wachen.json` traegt `handel_erlaubt: false`; `--live` verweigert mit genau
einem Grund, in dem das Wort Freigabefenster NICHT vorkommt.

## Die Idee

Ein MACD auf einem einzelnen Zeitrahmen dreht oft gegen den uebergeordneten
Trend - und genau diese Drehungen kosten Geld. `macd_mtf()` rechnet denselben
MACD auf drei Zeitrahmen (Faktor 1, 4 und 16, gebaut mit
`zu_hoeherem_zeitrahmen()`) und gehandelt wird nur, wenn ALLE DREI dieselbe
Richtung zeigen. Das ist die ganze These der Spur: Einigkeit als Filter.

Der zweite Teil ist der Ausloeser. Einigkeit allein sagt nur, dass ein Trend
besteht - nicht, wann man einsteigt. Deshalb muss zusaetzlich das Histogramm
des schnellsten Zeitrahmens in der letzten Kerze drehen.

## Das Signal

| Seite | Bedingung |
|---|---|
| LONG  | Ausrichtung aller drei Zeitraeume `+1` UND `hist[i] > hist[i-1]` (1er-Rahmen) |
| SHORT | Ausrichtung aller drei Zeitraeume `-1` UND `hist[i] < hist[i-1]` (1er-Rahmen) |

Ausrichtung `0` zaehlt nicht als Einigkeit: ein Histogramm exakt auf der
Null ist keine Richtung.

Zeitrahmen 1H als Basis - die hoeheren entstehen daraus, es wird kein
zweiter Abruf gemacht. Instrumente BTC-USDT, ETH-USDT.

## Wie viele Kerzen noetig sind

Der 16er-Rahmen braucht `16 * (26 + 9) = 560` Basiskerzen, bevor er
ueberhaupt eine Ausrichtung nennt. Darunter steht dort `None`, `einig` ist
`False`, und die Spur handelt nicht.

**Gemessen am 15.09.2026, und das ist der wichtige Teil:** `okx.kerzen()`
liefert hoechstens 300 Kerzen je Abruf. Mit `mindest_kerzen: 300`, so wie es
jetzt in `wachen.json` steht, erreicht der 16er-Rahmen seine Ausrichtung
also NIE - die Spur laeuft, schreibt Herzschlag und Spiegelung, eroeffnet
aber nichts. Wer sie scharf stellen will, muss die Kerzen aus mehreren
Abrufen zusammensetzen oder `mindest_kerzen` auf `>= 560` heben. Der Wert
steht bewusst so da und ist in `wachen.json` kommentiert, statt still
weggerechnet zu werden.

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
| `handeln.py` | Der Zyklus: Kerzen, Signal, Ein- und Ausstiege, Journal, Zustand, Spiegelung |
| `wachen.json` | Alle Tore, jede nicht offensichtliche Zahl mit `_`-Kommentarfeld |
| `handelsjournal.csv` | Jede Buchung, entsteht beim ersten Papierlauf |
| `zustand.json` | Offene Positionen und `letzter_lauf` (der Herzschlag) |
| `tests/test_macd_mtf.py` | 22 Tests, ohne Netz |

## Aufruf

```
python handeln.py --vorschau   was waere dran, schreibt NICHTS
python handeln.py --papier     ein Papierzyklus mit Journal
python handeln.py --wachen     die Bedingungen als Momentaufnahme
python handeln.py --live       verweigert, nennt den Grund
```

## Bedingung 4: Journal ausser Haus

Nach jedem Zyklus gehen Journal und Zustand nach `journal_zweitziel`
(`Q:\Handel_Journal\macd_mtf`).

## Tests

```
cd tests
..\..\scanner\.venv\Scripts\python.exe -m unittest test_macd_mtf -v
```

Die Fixture ist ein gerader Trend ueber 800 Kerzen, der am Ende quadratisch
beschleunigt. Der gerade Teil bringt alle drei Zeitrahmen auf dieselbe
Ausrichtung, die Beschleunigung dreht das Histogramm. Getestet wird
ausdruecklich auch der Fall "alle einig, aber das Histogramm dreht nicht" -
dort darf nichts feuern. Der Basispreis liegt bei 1000, damit auch 800
fallende Kerzen den Kurs nicht unter null druecken.
