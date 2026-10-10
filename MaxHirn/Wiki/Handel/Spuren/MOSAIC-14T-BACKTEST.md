# mosaic — 14-Tage-Backtest (19.09.–03.10.2026) mit Urteil

> Stand: 06.10.2026. Auftrag Max 05.10.2026 ("auf 14 tage backtest zur
> anpassung der geometrie und auswertung mit urteil"). Datenquelle Binance
> (Proxy für OKX/Kraken, `daten/historie/*_5M.json`), Lauf
> `replay.py --spur mosaic --lauf t_mosaic_14t --max-kerzen 19392`
> (Warmlauf 15360 + 14 Tage Handel = 4032 5M-Kerzen).

## Ergebnis

| Lauf | Einstiege | Geschlossen | Ergebnis | Treffer |
|---|---|---|---|---|
| ziel 1.5R | 3 (alle 19.09.) | 1 (SOL) | +8,98 USD | 100 % |
| **ziel 2.0R (Ist)** | **3 (alle 19.09.)** | **1 (SOL)** | **+10,71 USD** | **100 %** |
| ziel 3.0R | 3 | 0 | offen | — |

Die drei Einstiege (BTC 81474 / ETH 2644 / SOL 112,11) entstanden **alle am
19.09.** — nur an diesem Tag erfüllten alle drei Instrumente gleichzeitig
Bias long + Nachfragezone + BOS. Danach nie wieder im Fenster.

- SOL traf das Ziel (2R) nach 8 Tagen bei 123,32: **+10,71 USD** (Kauf 112,11).
- BTC und ETH standen nach 14 Tagen **noch offen** (Ziel 2R nicht erreicht).

## Urteil: Geometrie NICHT anpassen — Signalhäufigkeit ist der Engpass

**n=1 geschlossene Runde in 14 Tagen.** Eine Geometrie-Anpassung (Stop-Band,
Ziel-R) an einer einzigen Runde wäre Überanpassung an Rauschen — der
Parameter-Scan zeigt: 1.5R/2R/3R ändern nur, wann SOL rauskommt, nicht die
Anzahl der Einstiege. Die Geometrie bleibt unverändert (ATR-Stop 5–12 %,
Ziel 2R, Signal-Wechsel-Gatter).

Der messbare Engpass ist die **Signalhäufigkeit**: in 14 Tagen genau ein
Setup-Tag. Über die volle Historie (125 Tage, 5M-Basis) zählt die Kette
30/20/24 Setup-Tage je Instrument (BTC/ETH/SOL) — rund 1 Setup alle 4–6
Tage. Dazu kommt die lange Haltedauer (SOL 8 Tage bis Ziel), dadurch sind
die Plätze oft belegt und neue Signale blockiert.

## Konsequenz für den Live-Betrieb (okx_perp, Hebel 6)

- Die Geometrie trägt die Live-Zahlen unverändert (Stop vor Liquidation
  gemessen: 16,17 % Abstand bei 6x gegen Stop 5–12 %).
- Mit seltenen Setups und 3 Instrumenten ist das Buch meist fast leer —
  das ist nicht der Fehler der Spur, sondern ihre Natur.
- Die 60 USD Margin je Trade (Auftrag Max 05.10.2026, Commit 27b03a98)
  ergeben bei 6x einen Nennwert von 360 USD je Einstieg; der Gesamtdeckel
  400 bleibt.
- Punkt 4 des Auftrags ("SOL-Orders mitnehmen"): die 9 offenen SOLEUR-Orders
  an Kraken (Stops/TPs/Limit) bleiben unangetastet — Boersenabgleich
  meldet sie als fremd und fasst sie nicht an. Die 3 Buchpositionen
  (BTC/ETH/SOL, boerse=kraken) sind gedeckt (Stops `OL2N6C…`, `OJHLDO…`,
  `O5CFAP…`).

## Wie nachmessen

```bash
cd Agenten/Handel
MAXHIRN_ROUTINE=1 scanner/.venv/Scripts/python.exe replay.py --spur mosaic --lauf t_mosaic_14t --max-kerzen 19392
```

Achtung: `--fenster 14` bedeutet 14 **5M-Kerzen** (70 min), nicht 14 Tage —
der Replay braucht mindestens `mindest_kerzen` (300, ×48 für die 4H-Reihe =
15360 Warmlauf) plus das gewünschte Handelsfenster. Siehe
`MaxHirn/Wiki/Handel/Backtest-Fundament.md`.
