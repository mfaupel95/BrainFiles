# Befund: Backtest-Varianten unter `daten/backtest/`

Stand: 214214ed vom 13.10.2026

## Warum diese Datei

Am 13.10.2026 sollten die Test-, Probe- und Varianten-Ordner unter
`daten/backtest/` aufgeraeumt werden. Vorher wurden sie verglichen und
gesichert, damit beim Aufraeumen nichts verloren geht.

**Ergebnis der Pruefung: die Ordner werden NICHT aufgeraeumt.** Sie sind
kein Muell, sondern der Backtest-Bestaend, den `auswertung_alle.backtest_stand()`
liest: je Spur gewinnt der Lauf mit den meisten Journal-Zeilen und erscheint
im Leitstand-Reiter *Backtest*. Wer die Ordner verschiebt, nimmt dem Leitstand
seine Messgrundlage (`kein Lauf`) - der Befund steht unten bei *Folgen*.

## Wie gerechnet wurde

Nicht mit einer eigenen PnL-Formel, sondern mit den Hausfunktionen
`auswertung_alle.runden_indikator()` (paart kauf/verkauf ueber
`journalpaarung`, nimmt bei skalierten Positionen die letzte Kaufzeile)
und `auswertung_alle.kennzahlen()` (Gebuehr, Treffer, Median, Gruende).
Eine Eigenbau-Formel lieferte zuerst Werte, die der Hausmessung um Faktor
~1000 widersprachen - genau die zweite Wahrheit, die es nicht geben darf.

`Ergebnis` ist der G/V in USD aus dem Buch; `je Runde` = Ergebnis / Runden;
`offen` = Positionen ohne Ausstieg am Journalende.

## Alle 63 Varianten

| Variante | Runden | Treffer % | Ergebnis USD | je Runde | Einsatz USD | offen |
|---|---:|---:|---:|---:|---:|---:|
| gitter/t295 | - | - | 0 Runden | - | - | 0 |
| klassik_sma/t_probe | - | - | kein Buch | - | - | 0 |
| klassik_sma/t_probe_laufb | - | - | kein Buch | - | - | 0 |
| klassik_sr_breaks/t_probe_laufb | - | - | kein Buch | - | - | 0 |
| klassik_supertrend/ganz | - | - | kein Buch | - | - | 0 |
| macd_mtf/probe_alt | 11 | 36.4 | 177.81 | 16.165 | 11700 | 4 |
| macd_mtf/probe_neu | 11 | 36.4 | 177.81 | 16.165 | 11700 | 4 |
| macd_mtf/regime_studie | 752 | 22.5 | -122197.89 | -162.497 | 908363 | 3 |
| macd_mtf/t_d4d15b9a_baseline | 752 | 22.5 | -122197.89 | -162.497 | 908363 | 3 |
| mosaic/ganz | 3 | 66.7 | 15.00 | 5.000 | 300 | 0 |
| mosaic/t_mosaic_14t | 1 | 100.0 | 10.00 | 10.000 | 100 | 2 |
| mosaic/t_mosaic_14t_genau | - | - | kein Buch | - | - | 0 |
| mosaic/t_mosaic_z1.5 | 1 | 100.0 | 7.50 | 7.500 | 100 | 2 |
| mosaic/t_mosaic_z2.0 | 1 | 100.0 | 10.00 | 10.000 | 100 | 2 |
| mosaic/t_mosaic_z3.0 | - | - | 0 Runden | - | - | 3 |
| nautilus_emacross/ganz | - | - | kein Buch | - | - | 0 |
| orb/x | - | - | kein Buch | - | - | 0 |
| prophet_signal/t_probe_laufb | - | - | kein Buch | - | - | 0 |
| squeeze/2109_5pct_2R | 1183 | 30.6 | -5990.03 | -5.063 | 175262 | 4 |
| squeeze/ganz | - | - | kein Buch | - | - | 0 |
| squeeze/grundlinie | 595 | 41.3 | -561.64 | -0.944 | 131001 | 4 |
| squeeze/heute_3pct_1.5R | 1969 | 40.1 | -907.14 | -0.461 | 424253 | 4 |
| squeeze/lauf | - | - | kein Buch | - | - | 0 |
| squeeze/probe_alt | 44 | 38.6 | -27.71 | -0.630 | 10833 | 4 |
| squeeze/probe_neu | 44 | 38.6 | -27.71 | -0.630 | 10833 | 4 |
| squeeze/regime_studie | 1964 | 40.0 | -1077.77 | -0.549 | 423253 | 3 |
| squeeze/squeeze_0b7345f2 | 75 | 44.0 | 1028.67 | 13.716 | 16500 | 4 |
| squeeze/squeeze_23c378d2 | 51 | 25.5 | 967.93 | 18.979 | 12667 | 4 |
| squeeze/squeeze_7ddb88dd | 22 | 27.3 | 324.63 | 14.756 | 3100 | 4 |
| squeeze/squeeze_860f0e9a | 37 | 37.8 | -298.60 | -8.070 | 5000 | 4 |
| squeeze/squeeze_94d8d395 | 60 | 31.7 | 1482.66 | 24.711 | 13667 | 4 |
| squeeze/squeeze_aafe47ad | 33 | 36.4 | 13.69 | 0.415 | 4300 | 4 |
| squeeze/squeeze_be8ba6bd | 16 | 18.8 | -453.51 | -28.344 | 1929 | 4 |
| squeeze/squeeze_df7fa710 | 24 | 33.3 | -503.46 | -20.977 | 3071 | 4 |
| squeeze/squeeze_e729ea3b | 16 | 25.0 | -57.40 | -3.587 | 1571 | 4 |
| squeeze/t_d4d15b9a_baseline | 1964 | 40.0 | -1077.77 | -0.549 | 423253 | 4 |
| squeeze/t_d4d15b9a_smoke | 4 | 0.0 | -16.39 | -4.097 | 667 | 4 |
| supertrend/probe_alt | 131 | 32.8 | -46.63 | -0.356 | 13100 | 2 |
| supertrend/probe_neu | 131 | 32.8 | -46.63 | -0.356 | 13100 | 2 |
| supertrend/regime_studie | 857 | 35.1 | 157.11 | 0.183 | 84899 | 2 |
| supertrend/t_d4d15b9a_baseline | 857 | 35.1 | 157.11 | 0.183 | 84899 | 2 |
| trendwende_btc/t_probe_laufb | - | - | kein Buch | - | - | 0 |
| wavetrend/grundlinie | 40 | 20.0 | -723.25 | -18.081 | 8700 | 4 |
| wavetrend/probe_alt | 23 | 30.4 | -116.39 | -5.060 | 4500 | 4 |
| wavetrend/probe_neu | 23 | 30.4 | -116.39 | -5.060 | 4500 | 4 |
| wavetrend/regime_studie | 1870 | 30.3 | -16398.51 | -8.769 | 287110 | 4 |
| wavetrend/t_d4d15b9a_baseline | 1870 | 30.3 | -16398.51 | -8.769 | 287110 | 4 |
| wavetrend/wavetrend_0b7345f2 | 107 | 43.0 | -1795.95 | -16.785 | 26100 | 4 |
| wavetrend/wavetrend_23c378d2 | 62 | 17.7 | -111.68 | -1.801 | 15150 | 4 |
| wavetrend/wavetrend_7ddb88dd | 36 | 5.6 | -688.52 | -19.126 | 6500 | 4 |
| wavetrend/wavetrend_860f0e9a | 47 | 34.0 | -405.67 | -8.631 | 9400 | 4 |
| wavetrend/wavetrend_94d8d395 | 80 | 26.2 | 307.30 | 3.841 | 19350 | 4 |
| wavetrend/wavetrend_aafe47ad | 40 | 20.0 | -723.25 | -18.081 | 8700 | 4 |
| wavetrend/wavetrend_be8ba6bd | 21 | 23.8 | -514.55 | -24.502 | 3357 | 4 |
| wavetrend/wavetrend_df7fa710 | 25 | 36.0 | -109.37 | -4.375 | 3857 | 4 |
| wavetrend/wavetrend_e729ea3b | 19 | 15.8 | -475.19 | -25.010 | 2714 | 4 |
| xperp/ganz | 39 | 43.6 | 78.75 | 2.019 | 14033 | 0 |
| xperp/lage | - | - | kein Buch | - | - | 0 |
| xperp/t01de | 27 | 40.7 | 39.67 | 1.469 | 9714 | 0 |
| xperp/t02 | 2 | 50.0 | 8.42 | 4.210 | 786 | 0 |
| xperp/test | 80 | 98.8 | 618.51 | 7.731 | 39185 | 0 |
| xperp/test_grid | - | - | kein Buch | - | - | 0 |
| xperp/test_lage | - | - | kein Buch | - | - | 0 |

## Je Spur der beste Lauf (nach Ergebnis je Runde)

| Spur | bester Lauf | je Runde USD | Runden | Treffer % |
|---|---|---:|---:|---:|
| macd_mtf | macd_mtf/probe_neu | 16.165 | 11 | 36.4 |
| mosaic | mosaic/t_mosaic_z2.0 | 10.000 | 1 | 100.0 |
| squeeze | squeeze/squeeze_94d8d395 | 24.711 | 60 | 31.7 |
| supertrend | supertrend/t_d4d15b9a_baseline | 0.183 | 857 | 35.1 |
| wavetrend | wavetrend/wavetrend_94d8d395 | 3.841 | 80 | 26.2 |
| xperp | xperp/test | 7.731 | 80 | 98.8 |

## Ohne auswertbares Buch (16)

Diese Ordner tragen nur eine `wachen.json` (Parameter-Ablage aus
`replay.py --setzen`) oder ein leeres Journal. Sie sind winzig und
stoeren nichts - kein Grund zum Loeschen.

- `gitter/t295` (62 Zeilen)
- `klassik_sma/t_probe` (kein Journal)
- `klassik_sma/t_probe_laufb` (kein Journal)
- `klassik_sr_breaks/t_probe_laufb` (kein Journal)
- `klassik_supertrend/ganz` (kein Journal)
- `mosaic/t_mosaic_14t_genau` (kein Journal)
- `mosaic/t_mosaic_z3.0` (3 Zeilen)
- `nautilus_emacross/ganz` (kein Journal)
- `orb/x` (kein Journal)
- `prophet_signal/t_probe_laufb` (kein Journal)
- `squeeze/ganz` (kein Journal)
- `squeeze/lauf` (kein Journal)
- `trendwende_btc/t_probe_laufb` (kein Journal)
- `xperp/lage` (kein Journal)
- `xperp/test_grid` (kein Journal)
- `xperp/test_lage` (kein Journal)

## Befunde

1. **Die Parameter-Suchen finden nichts.** `squeeze/optimierung.json`
   (11.10.2026) fuehrt 12 Kandidaten, `ueberlebt: []` - kein einziger
   besteht die 4-Fenster-Pruefung, mehrere fallen schon an
   "weniger als 2 auswertbare Fenster". `wavetrend/optimierung.json`
   ebenso. Die Spuren `squeeze` und `swap` sind deshalb seit 10.10.2026
   aus dem Dauerlauf - das ist bereits geschehen, hier nur der Beleg.

2. **Positiv aussehende Einzelfenster sind kein Fund.** Die Ordner
   `squeeze_0b7345f2` (+1028.67 USD), `squeeze_94d8d395` (+1482.66) und
   `squeeze_23c378d2` (+967.93) tragen je EIN Fenster mit 16-75 Runden.
   Die 4-Fenster-Pruefung derselben Geometrien verwirft alle. Wer nur
   diese drei Ordner liest, haelt squeeze fuer profitabel.

3. **Das Kraken-Gebuehrenmass steht in den Wachen, nicht im Journal.**
   Die Indikator- und Klassik-Buecher schreiben BRUTTO (keine Kosten in
   der Zeile). Die Zahlen hier sind deshalb brutto; netto je Runde liegt
   bei OKX 0,10 %/Seite um rund 0,2 % des Einsatzes tiefer, bei Kraken
   Spot (0,60 %/Seite) um rund 1,2 %.

## Folgen eines Aufraeumens (geprueft, nicht vermutet)

- `auswertung_alle.backtest_stand(spur)` liest `daten/backtest/<spur>/<lauf>/`
  und waehlt den Lauf mit den MEISTEN Zeilen. Ohne die Unterordner meldet
  der Leitstand `kein Lauf` - die Backtest-Spalte waere leer.
- `kerzenschluss_bias.journale()` globt `daten/backtest/*/*/*.csv`; ein
  zusaetzliches Archiv-Level (`_archiv/<spur>/<lauf>/`) passt noch, ein
  flacheres (`<spur>/<lauf>` unterhalb der Wurzel) nicht mehr.
- `optimieren.py` schreibt `daten/backtest/<spur>/optimierung.json`;
  `leitstand_optimieren.py` liest genau diesen Pfad.

Deshalb: **stehen lassen.** Die 63 Ordner belegen rund 13 MB - kein
Ressourcenproblem. Die echten Platzfresser liegen woanders (siehe
`daten/backtest/VARIANTEN-VERGLEICH-20261013.json` und den Bericht an Max).

## Rohdaten

Maschinenlesbar daneben: `daten/backtest/VARIANTEN-VERGLEICH-20261013.json`
(Parameter, Kennzahlen, Paarungsstand, Gruende je Variante).
