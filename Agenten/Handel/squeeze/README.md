# squeeze - Volatilitaetskompression loest sich

Papier-Spur auf genau einem Indikator: `squeeze_momentum()` aus
`../ti_indikatoren.py`. Kein Orderpfad, kein Broker-Aufruf.
`wachen.json` traegt `handel_erlaubt: false`; `--live` verweigert mit
genau einem Grund, in dem das Wort Freigabefenster NICHT vorkommt -
so fragt der Dauerlauf keine Freigabe an, die nichts oeffnen kann.

## Die Idee

Der LazyBear-Squeeze vergleicht Bollinger-Baender mit dem Keltner-Kanal.
Liegen die Baender INNERHALB des Kanals, presst sich die Volatilitaet
zusammen (`squeeze_an = True`). Loest sich diese Kompression, folgt die
Bewegung meist der Richtung des Moments. Genau dieser eine Uebergang ist
das Signal - nicht der Squeeze selbst und nicht das Moment allein.

## Das Signal

| Seite | Bedingung |
|---|---|
| LONG  | `squeeze_an[i-1]` war True, `squeeze_an[i]` ist False, UND `momentum[i] > momentum[i-1] > 0` |
| SHORT | `squeeze_an[i-1]` war True, `squeeze_an[i]` ist False, UND `momentum[i] < momentum[i-1] < 0` |

Beide Haelften sind noetig: die Kompression muss sich loesen (sonst ist es
kein Ausbruch), und das Moment muss in die Handelsrichtung zeigen und dabei
zunehmen (sonst ist es ein Ausbruch gegen die eigene Position).

Zeitrahmen 1H, Instrumente BTC-USDT, ETH-USDT, SOL-USDT.

## Groesse, Stop, Ziel

Risiko-normiert, nichts davon steht im Code:

```
stop_pct  = ATR / Kurs * 100, gezwungen in [pflicht_stop_prozent_min, ..max]
nominal   = risiko_je_position_usd / (stop_pct / 100)
nominal   = min(nominal, max_pro_trade_usd)
nominal  *= ratschen.groessenfaktor(ruecklauf, wachen)
ziel      = einstieg +/- ziel_r_vielfaches * stop_abstand
```

Stop UND Ziel entstehen aus demselben Prozentsatz. Stuende im Journal ein
Stop-Preis, der nicht zu `stop_pct` passt, waere die Groesse gegen eine
andere Zahl gerechnet als der Ausstieg.

Die Drawdown-Ratsche kommt aus `../ratschen.py`, ueber den Pfad geladen -
nicht ueber `sys.path`, damit nicht entscheidet, wer vorher was eingefuegt hat.

## Dateien

| Datei | Inhalt |
|---|---|
| `handeln.py` | Der Zyklus: Kerzen, Signal, Ein- und Ausstiege, Journal, Zustand, Spiegelung |
| `wachen.json` | Alle Tore und Zahlen. Jede nicht offensichtliche traegt ein `_`-Kommentarfeld mit der Herleitung |
| `handelsjournal.csv` | Jede Buchung, entsteht beim ersten Papierlauf |
| `zustand.json` | Offene Positionen und `letzter_lauf` (der Herzschlag) |
| `tests/test_squeeze.py` | 20 Tests, ohne Netz |

## Aufruf

```
python handeln.py --vorschau   was waere dran, schreibt NICHTS
python handeln.py --papier     ein Papierzyklus mit Journal
python handeln.py --wachen     die Bedingungen als Momentaufnahme
python handeln.py --live       verweigert, nennt den Grund
```

`--vorschau` schreibt bewusst weder Zustand noch Journal noch Spiegelung:
sonst setzte jeder Vorschau-Lauf einen frischen Herzschlag.

## Bedingung 4: Journal ausser Haus

Nach jedem Zyklus gehen Journal und Zustand nach `journal_zweitziel`
(`Q:\Handel_Journal\squeeze`). Ein fehlendes Ziel ist kein Fehler des Laufs;
der Stand steht im Zustand unter `journal_zweitziel_ok` / `_info`.

## Tests

```
cd tests
..\..\scanner\.venv\Scripts\python.exe -m unittest test_squeeze -v
```

Kein Netz noetig - die Kerzen entstehen im Test. Geprueft wird, dass das
Signal genau an der gebauten Stelle feuert und nirgends sonst, dass Stop und
Ziel 1:2 stehen, dass `max_pro_trade_usd` haelt, dass `--vorschau` keine
Datei anlegt und dass ein Zyklus ohne Kerzen oder ohne Verbindung nicht
abstuerzt. Wo ein Test die Spiegelung beruehrt, zeigt `journal_zweitziel`
auf einen Temp-Ordner - nie auf `Q:`.
