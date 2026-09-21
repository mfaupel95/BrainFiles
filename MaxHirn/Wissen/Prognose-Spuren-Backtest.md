---
id: prognose-spuren-backtest
title: Backtest der vier Prognose-Spuren (21.09.2026)
tags: [Handel, Backtest, Prognose, Indikatoren]
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
