# Strategie-Kennzahlen (Formelblatt von Max, 29.09.2026)

Max hat `strategie_metrics.py` geschickt (Kennzahlen, Freigabe-Profile,
Risiko-Steuerung). Die Datei liegt jetzt als `Agenten/Handel/strategie_metrics.py`
und laeuft (Selbsttest + Demo mit dem Haus-venv `Agenten/Handel/.venv`, das als
einziges numpy und pandas traegt).

## Was das Blatt ans Haus anschliesst

| Aus dem Blatt | Im Haus vorher | Wert |
|---|---|---|
| `expectancy()` mit **t-Statistik** | nur die Regel „unter 8 Runden ist es ein Befund" | Die t-Statistik macht daraus eine ZAHL: ist der Vorteil von 0 unterscheidbar oder Rauschen |
| `stop_from_mae()` | Stop als feste Prozentzahl (Pflicht-Stop 5 %) | datengetriebener Stop: 90-%-Quantil des groessten Zwischenverlusts der GEWINNER |
| `drawdown_throttle()` | Ratsche halbiert ab der Schwelle | HIER NICHT uebernommen (siehe unten) |
| `position_size_cvar()` | risikonormiert ueber `stop_pct` | Kandidat, noch nicht eingebaut |
| `var_historical` / `cvar_historical` | fehlte ganz | braucht Tagesrenditen (siehe unten) |

## Was NICHT uebernommen ist - und warum

Das Blatt rechnet **zeitbasiert** (Tagesrenditen, 365 Perioden im Jahr: Sharpe,
Sortino, Calmar, VaR/CVaR, CAGR). Das Haus fuehrt **Runden**, keine Tageswerte.
Eine Umrechnung von Runden auf Tagesrenditen waere eine Erfindung, deshalb
stehen diese Kennzahlen im Haus nicht - das ist kein Versehen, sondern die
Grenze der eigenen Daten. Wer sie will, muss zuerst eine taegliche Kapitalkurve
je Spur fuehren.

Ebenfalls bewusst nicht uebernommen: `drawdown_throttle()` wuerde die
Haus-Ratsche (`Agenten/Handel/ratschen.py`) ersetzen. Die Ratsche ist geprueft,
in jeder Spur verdrahtet und hat eine Herleitung (1,0 x Buchrisiko);
ein linearer Faktor 1,0 -> 0,0 zwischen halbem und ganzem Limit ist eine
ANDERE Regel und gehoert nicht nebenbei umgestellt. Kandidat fuer einen
eigenen Auftrag mit Gegenprobe.

## Das neue Werkzeug

`Agenten/Handel/strategie_kennzahlen.py` (venv: `Agenten/Handel/.venv`):

```
cd Agenten/Handel
.venv/Scripts/python.exe strategie_kennzahlen.py             # alle Spuren mit Buch
.venv/Scripts/python.exe strategie_kennzahlen.py scanner kraken
```

Es holt die Runden ueber `auswertung_alle.runden_fuer()` - die Zuordnung
Spur -> Rechenweg liegt dort und wird hier NICHT nachgebaut.

### Zahlen vom 29.09.2026 (Auszug)

| Spur | echte Runden | Zwangsschl. | Treffer | Erwartung | PF | t-Stat |
|---|---|---|---|---|---|---|
| scanner | 125 | 36 | 84,8 % | +16,08 USD | 17,64 | **15,33** |
| xperp | 24 | 50 | 45,8 % | +9,54 USD | 3,01 | 1,33 |
| orbk | 15 | 0 | 60,0 % | +5,35 USD | 2,24 | 1,32 |
| moondev_topmovers | 20 | 0 | 65,0 % | +3,06 USD | 2,37 | 1,90 |
| kraken | 5 | **46** | 40,0 % | +0,86 EUR | 1,54 | 0,38 |
| swap | 5 | 8 | 20,0 % | -2,29 USD | 0,30 | -1,13 |

Lesart: **nur der scanner hat einen statistisch belegten Vorteil** (t = 15,3).
xperp, orbk und moondev_topmovers liegen mit t zwischen 1,3 und 1,9 im Bereich
„noch nicht unterscheidbar". kraken hat fuenf echte Runden gegen 46
Zwangsschluesse - die Zahl beschreibt dort den Herzschlag, nicht die Strategie.
swap ist negativ (t = -1,13).

## Befund: die MAE wird nicht gefuehrt

Der Stop-Vorschlag aus `stop_from_mae` setzt voraus, dass im Journal steht, wie
weit eine Position ins Minus lief. Das tut es nicht: der scanner schreibt bei
Ausstiegen mit Grund `ziel` durchweg `mae_pct = 0.0000`, echte Werte stehen nur
bei `stop`, `herzschlag_alt` und den Buchhaltungs-Korrekturen; die uebrigen
Spuren haben die Spalte gar nicht. Ein Stop aus dieser Spalte waere 0 % - das
Werkzeug sagt deshalb „MAE ungefuehrt" statt eine Null als Messwert auszugeben
(T-119).

## Drei Fallen aus dem Formelblatt selbst

Klein, aber sie kosten Zeit, wenn man sie nicht kennt:

1. `Sortino` **ohne** MAR-Abzug und mit der Standardabweichung NUR der
   Verlusttage ist die verbreitete falsche Fassung. Richtig ist die
   Downside-Deviation ueber ALLE Perioden mit `min(0, r - MAR)` - das Blatt hat
   das korrigiert.
2. `VaR`: das Quantil gehoert auf `1 - alpha`; die verbreitete Fassung dreht es
   um und macht den VaR bei hoeherem Konfidenzniveau kleiner.
3. `MAE` ist richtungsabhaengig: bei Short ist es `hoch - einstieg`, nicht
   `einstieg - tief`. Wer das verwechselt, misst den MFE.
