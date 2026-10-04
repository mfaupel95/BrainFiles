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

### Die Geometrie ist gemessen, nicht gewaehlt

`pflicht_stop_prozent_min` 3,0 % und `ziel_r_vielfaches` 1,5 (Auftrag Max
04.10.2026, „squeeze 3/1,5"). Grundlage ist der Backtest-Vergleich von vier
Geometrien ueber dieselbe Historie, gerechnet mit `kosten_wendepunkt.kennzahlen()`:

| Stop / Ziel | Runden | Treffer | G/V je Runde |
|---|---|---|---|
| **3,0 % / 1,5R** | 1007 | 39,0 % | **−0,074 USD** |
| 3,0 % / 3,0R | 779 | 21,8 % | −0,384 USD |
| 5,0 % / 2,0R (vorher) | 579 | 28,0 % | −0,803 USD |
| 7,0 % / 1,5R | 428 | 31,8 % | −1,439 USD |

Die neue Geometrie kostet rund zehnmal weniger je Runde **bei 1,7x so vielen
Runden** — sie ist damit auch der Datenspender, nicht nur die billigere Wahl.
Beleg und Fehlgeschichte (der `--setzen`-Schalter lief ins Leere) stehen in
`MaxHirn/Wiki/Handel/Spur-Optimierung-Setzer-Befund.md`.

**Offen bleibt:** auch die beste Geometrie ist vor Gebuehr leicht negativ.
Sie traegt noch nicht; belegt ist nur, dass die alte deutlich schlechter war.

**Der Deckel folgt dem Stop.** `max_pro_trade_usd` muss mindestens
`risiko_je_position_usd / pflicht_stop_prozent_min` sein, sonst schrumpft das
Risiko je Position still: bei 5,0 USD Risiko und 3 % Stop sind das 166,67 USD,
der Deckel steht auf 170. Mit dem alten Deckel 150 waeren es 4,50 statt 5,00
USD geworden — der Test `deckel_traegt_das_risiko` faellt genau darauf.

**Geaenderte Geometrie wirkt auch auf OFFENE Positionen.** `skalieren.skaliere()`
rechnet bei jeder Vergroesserung Stop und Ziel neu aus dem aktuellen `stop_pct`
und `r` — ein neues Squeeze-Signal auf demselben Instrument zieht die offene
Position also auf die neue Geometrie nach (belegt: BTC-USDC, 04.10. 10:04 UTC,
`stop_pct` 5,00 -> 3,00). Offene Positionen **ohne** weitere Skalierung laufen
unter ihrem alten Stand weiter. Die naechste Auswertung ist gemischt und
deshalb kein Beweis der Wirkung.

Die Drawdown-Ratsche kommt aus `../ratschen.py`, ueber den Pfad geladen -
nicht ueber `sys.path`, damit nicht entscheidet, wer vorher was eingefuegt hat.

## Dateien

| Datei | Inhalt |
|---|---|
| `handeln.py` | Der Zyklus: Kerzen, Signal, Ein- und Ausstiege, Journal, Zustand, Spiegelung |
| `wachen.json` | Alle Tore und Zahlen. Jede nicht offensichtliche traegt ein `_`-Kommentarfeld mit der Herleitung |
| `handelsjournal.csv` | Jede Buchung, entsteht beim ersten Papierlauf |
| `zustand.json` | Offene Positionen und `letzter_lauf` (der Herzschlag) |
| `tests/test_squeeze.py` | 21 Tests, ohne Netz |

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
Ziel im Verhaeltnis `ziel_r_vielfaches` **aus der Wache** stehen (nicht gegen
eine im Test verdrahtete Zahl - sonst waere die Suite bei jeder Umstellung
rot, ohne dass etwas kaputt waere), dass `max_pro_trade_usd` das Risiko
traegt, dass `--vorschau` keine Datei anlegt und dass ein Zyklus ohne Kerzen
oder ohne Verbindung nicht abstuerzt. Wo ein Test die Spiegelung beruehrt, zeigt `journal_zweitziel`
auf einen Temp-Ordner - nie auf `Q:`.
