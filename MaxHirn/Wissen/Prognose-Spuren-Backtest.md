---
id: prognose-spuren-backtest
title: Backtest der vier Prognose-Spuren (21.09.2026)
tags: [handel]
created: 2026-09-21
updated: 2026-09-21
related: [[Handelsregeln]], [[Archiv-Trading-Skills]], [[Routinen]]
summary: Erster langer Backtest der vier Prognose-Spuren auf echten Kerzen. Nur die Long-Seite von macd_mtf und squeeze traegt ueber 7000 Stunden; short ist bei allen vier negativ.
---

# Backtest der vier Prognose-Spuren (21.09.2026)

**Werkzeug:** `Agenten/Handel/backtest_prognose.py` (Treiber), `bt_lang.py`
(Serienlauf ueber beide Seiten). Beide fahren die Spuren **selbst** - `signal()`,
`pruefe_einstieg()` und `pruefe_ausstiege()` werden aus `<spur>/handeln.py` ueber
den Pfad geladen. Kein Nachbau: eine Nachbildung wuerde die Nachbildung
optimieren. Die Laeufe schreiben nichts in die Spurenordner (`SCHREIBEN=False`).

**Daten:** OKX `history-candles` (blaettert mit `after` rueckwaerts, weiter als die
1440 Stunden des oeffentlichen Endpunkts), 7000 Stundenkerzen ab 04.12.2025.
**Gebuehr:** 0,10 % je Seite (OKX Spot Taker) - die vier `wachen.json` tragen
keine Gebuehr, sie ist Parameter des Backtests und immer als netto ausgewiesen.

## Ergebnis Langlauf (7000 h, 0,10 %/Seite, netto je Runde)

| Spur | Seite | Runden | Quote | netto/Runde | Summe | max. Ruecklauf | Median-Dauer |
|---|---|---|---|---|---|---|---|
| macd_mtf | long | 62 | 48,4 % | **+2,28 %** | +141,18 | −63,51 | 182 h |
| macd_mtf | beide | 94 | 43,6 % | +1,37 % | +129,09 | −86,23 | 125 h |
| macd_mtf | short | 71 | 35,2 % | −0,19 % | −13,44 | −192,63 | 134 h |
| squeeze | long | 60 | 45,0 % | **+1,57 %** | +94,09 | −67,15 | 222 h |
| squeeze | beide | 80 | 43,8 % | +1,20 % | +95,93 | −45,17 | 174 h |
| squeeze | short | 66 | 28,8 % | −1,28 % | −84,57 | −132,03 | 171 h |
| wavetrend | long | 121 | 33,9 % | −0,30 % | −36,33 | −180,58 | 126 h |
| wavetrend | beide | 139 | 32,4 % | −0,51 % | −70,23 | −176,97 | 128 h |
| wavetrend | short | 99 | 31,3 % | −0,77 % | −75,73 | −166,47 | 171 h |
| supertrend | long | 94 | 29,8 % | −1,11 % | −104,32 | −140,14 | 84 h |
| supertrend | beide | 187 | 29,4 % | −0,84 % | −156,52 | −168,85 | 88 h |
| supertrend | short | 93 | 29,0 % | −0,56 % | −52,20 | −108,90 | 96 h |

Kurzfenster zum Vergleich (2000 h ab 30.06.2026, sonst gleich): macd_mtf 15 Runden
60 % +3,27 %, squeeze 13 / 38 % +0,12 %, supertrend 145 / 32 % −0,67 %,
wavetrend 22 / 18 % −2,81 %. Das Kurzfenster war ein reiner Aufwaertsmarkt
(BTC +44,7 %) und ist damit die freundlichere Zahl - der Langlauf ist der Massstab.

## Was das heisst, und was nicht

- **Die Short-Seite ist bei allen vier negativ**, auch ueber 7000 Stunden. Das
  Kurzfenster allein haette das nicht gezeigt (dort 0 % Treffer, klar erklaerbar
  durch den Aufwaertsmarkt) - erst der lange Lauf trennt Marktlage von Schwaeche.
- **Traegt nur long:** macd_mtf-long (+2,28 %/Runde bei 48 % Treffern) und
  squeeze-long (+1,57 % bei 45 %). wavetrend und supertrend sind auf beiden
  Seiten negativ; bei ihnen ist der Indikator der Deckel, nicht der Parameter.
- **Die Gebuehr ist die empfindlichste Groesse.** Bei 0,10 %/Seite frisst eine
  Runde 0,20 %; macd_mtf-long hat brutto rund +2,48 %. Wer die Gebuehr auf 0,20 %
  je Seite stellt, halbiert den Vorsprung - dieselbe Rechnung, die
  `kosten_wendepunkt.py` fuer die laufenden Buecher macht.
- **Kein Freigabe-Nachweis.** Es ist ein Backtest ohne Slippage und ohne
  Teilfuellungen; die Spuren bleiben Papier. Die Zahlen sagen nur, WO eine
  Optimierung sinnvoll ansetzt: an der Long-Seite von macd_mtf und squeeze, nicht
  an allen vier Indikatoren gleichzeitig.
- **Ruecklauf beachten:** macd_mtf-long −63,51 und wavetrend −180,58 auf
  2000 Einheiten - die Drawdown-Ratsche ist bei diesen Spuren kein Beiwerk.

## Nachweis

```bash
cd Agenten/Handel && python bt_lang.py     # Serienlauf, schreibt bt_lang.json/.txt
```

## Varianten-Studie (21.09.2026, abends): was den Langlauf verbessert

**Treiber:** `Agenten/Handel/bt_varianten_fast.py` (Indikator-Arrays einmal je
Instrument vorrechnen, Einstieg/Ausstieg weiter aus `<spur>/handeln.py` ueber den
Pfad) und `bt_oos.py` (Halbierung). Rein lesend, `SCHREIBEN=False`, Journal
abgefangen. Alle 22 Varianten mit Zahlen: `Werkstatt/backtest-optimierung-2026-09-21.md`
(Durchgangsware, nicht der Massstab). Fenster und Kosten wie oben: 7000 h, long,
netto 0,10 %/Seite.

| Spur | Variante | Runden | Quote | netto/Runde | Summe | max. Ruecklauf |
|---|---|---|---|---|---|---|
| macd_mtf | BASE (Stand) | 62 | 48,4 % | +2,277 % | +141,18 | -63,51 |
| macd_mtf | **hist1+4** | 54 | **51,9 %** | **+2,787 %** | **+150,50** | **-54,82** |
| macd_mtf | fakt(1,4,8) | 81 | 37,0 % | +0,117 % | +9,49 | -171,39 |
| macd_mtf | macd(5,35,5) | 63 | 41,3 % | +1,006 % | +63,36 | -103,76 |
| macd_mtf | ziel R=3 | 46 | 41,3 % | +3,382 % | +155,56 | -61,29 |
| macd_mtf | stop 3-15 | 127 | 44,9 % | +0,868 % | +110,23 | -78,70 |
| squeeze | BASE (Stand) | 60 | 45,0 % | +1,568 % | +94,09 | -67,15 |
| squeeze | laenge30 | 44 | 50,0 % | +2,531 % | +111,38 | -64,31 |
| squeeze | kc1.2 | 48 | 47,9 % | +2,076 % | +99,65 | -77,18 |
| squeeze | laenge15 | 76 | 39,5 % | +0,538 % | +40,87 | -121,38 |

Die reproduzierte BASE stimmt Zeichen fuer Zeichen mit dem Langlauf oben
(macd_mtf-long +2,277/+141,18/-63,51; squeeze-long +1,568/+94,09/-67,15) - die
Vorberechnung ist also nicht die Ursache der Zahlen.

**OOS-Stabilitaet** (Halbierung 0-3500 / 3500-7000 h):

| Variante | H1 netto/Runde | H1 Quote | H2 netto/Runde | H2 Quote |
|---|---|---|---|---|
| macd BASE | +1,047 % | 40,0 % | +1,783 % | 47,8 % |
| macd hist1+4 | +1,693 % | 46,2 % | +2,590 % | 52,6 % |
| squeeze BASE | +1,611 % | 46,2 % | +3,293 % | 52,6 % |
| squeeze laenge30 | +4,704 % | 63,6 % | +3,380 % | 54,5 % |

**Zweites Fenster, unabhaengig (4H-Kerzen).** Dieselben vier Varianten auf
`daten/backtest_kerzen/*_4H.json` (je 2379 Kerzen ab 21.08.2025 - ein anderer
Zeitraum als der 1H-Langlauf). Die Vorberechnung wurde dort an Stichproben
gegen die schrittweise Rechnung der Spur geprueft (25/25 Treffer je Spur):

| Variante | Runden | Quote | netto/Runde | Summe | max. Ruecklauf |
|---|---|---|---|---|---|
| macd BASE | 38 | 52,6 % | +3,357 % | +127,58 | -49,10 |
| macd hist1+4 | 27 | 59,3 % | +4,232 % | +114,27 | -29,22 |
| squeeze BASE | 36 | 38,9 % | +1,070 % | +38,53 | -64,84 |
| squeeze laenge30 | 11 | 63,6 % | +5,204 % | +57,25 | -18,75 |

Der Charakter bleibt, die Deutung wird schaerfer: `hist1+4` verbessert auch hier
Quote (+6,7 pp), Wert je Runde und Ruecklauf - aber bei 27 statt 38 Runden ist
die Summe kleiner. **Der Filter macht die einzelne Runde besser, nicht den
Ertrag groesser.** `laenge30` bleibt mit 11 Runden zu duenn.

**Fahrweise gegengeprueft.** `Agenten/Handel/bt_opt/verify_equivalence.py` stellt
das vorberechnete Signal dem der Spur selbst gegenueber: macd_mtf 1200 Schritte,
squeeze 2700 Schritte, je 0 Abweichung im Long-Signal und 0 Abweichung im
Einstieg, Urteil **gleichwertig** (nachgefahren 21.09.2026). Damit ist die
Einstiegslogik-Kopie in `bt_varianten_fast.py` belegt und nicht behauptet - die
Varianten-Zahlen stammen aus derselben Mechanik wie die Spur.

**Befund:**


- **Traegt: macd_mtf `hist1+4`.** Das Histogramm muss zusaetzlich zum 1er- auch im
  4er-Zeitrahmen steigen. Quote 48,4 -> 51,9 %, netto/Runde +2,28 -> +2,79 %,
  Summe +141 -> +150, Ruecklauf -63,5 -> -54,8, und beides auf beiden Haelften
  (sowie auf dem 4H-Fenster). Es ist eine Bestaetigungs-Bedingung am SELBEN
  Indikator, kein neuer Parameter - damit kein Overfit im Sinne der Hausmethodik.
  Preis dafuer: weniger Runden (62 -> 54; auf 4H 38 -> 27).
- **Parameter-Knoepfe tragen nicht.** `ziel R=3` zeigt zwar +3,38 %/Runde, aber
  bei nur 46 Runden und 41 % Quote; `ziel R=1,5` und `stop min4` erhoehen die
  Rundenzahl, ohne den Vorsprung zu halten; `stop max15` ist wirkungslos
  (identisch zu BASE). Kein Stop-/Ziel-Knopf hebt den Stand robust.
- **Faktor- und MACD-Varianten verschlechtern** die Long-Seite durchweg: mehr
  Runden, niedrigere Quote, tieferer Ruecklauf. Der Indikator selbst ist der
  Deckel, nicht seine Fensterlaenge.
- **squeeze `laenge30`** schlaegt BASE auf beiden Haelften (netto/Runde +2,53 %,
  Quote 50 %), aber bei nur 44 statt 60 Runden (H2 nur 11) - zu duenn belegt fuer
  eine Empfehlung.

**Offen (Entscheidung Max):** `hist1+4` ist ein Eingriff in die Signallogik von
`macd_mtf/handeln.py` (bzw. ein Feld `hist_mehrere` in `macd_mtf/wachen.json`).
Die Spur laeuft Papier mit `handel_erlaubt=false`; ein Umbau braucht einen Test
in `macd_mtf/tests/` und danach einen frischen Langlauf als Gegenprobe.

**Nachweis:**

```bash
cd Agenten/Handel
python bt_varianten_fast.py --json bt_varianten_fast.json   # 22 Varianten, 7000 h long
python bt_oos.py                                            # Halbierung H1/H2
```
