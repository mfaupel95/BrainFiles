# nautilus_emacross — der EMA-Cross aus nautilus_trader

## Was das ist

Die Originalstrategie des Projekts `nautechsystems/nautilus_trader`, aus
`develop/docs/tutorials/ema_cross.py`. Der Quelltext steht **wörtlich** im
Kopf von `handeln.py` — der Port ist damit prüfbar, nicht behauptet.

Die Regel, unverändert:

```python
if fast_ema.value >= slow_ema.value:      # 10 >= 20
    if flat:   buy()
    elif short: close_all_positions(); buy()
else:
    if flat:   sell()
    elif long:  close_all_positions(); sell()
```

Parameter aus `examples/backtest/crypto_ema_cross_ethusdt_trade_ticks.py`:
`fast_ema_period=10`, `slow_ema_period=20`, `trade_size=0.10`.

## Warum sie als eigene Spur und nicht als Umbau

Die drei Arme `nautilus`, `nautilus_kraken` und `nautilus_kraken_futures`
lesen ihre Einstiege aus dem Journal der **kopier**-Spur — das sind
Solana-Memecoin-Käufe — und buchen sie als **BTC-Proxy**. Das ist keine
Strategie, sondern ein Umweg: das Signal gehört einem anderen Markt als
die Position. Gemessen am 03.10.2026: 6, 4 und 2 Runden, alle auf einem
Instrument, Excess 0,09 %, 1,08 % und ohne Basislinie.

Diese Spur rechnet auf **eigenen Kerzen ihres eigenen Instruments**. Sie
ist der Vergleich, nicht deren Ersatz. Die drei alten Arme bleiben
unangetastet, bis Max verglichen hat.

## Zwei Abweichungen vom Original — beide bewusst

**1. Kein Schutz-Stop im Original.** Die Originalfassung dreht die
Position per Market-Order pro Bar und hat keinen Schutz-Stop am Markt. In
einem Haus mit echter Börse und mit T-273 („Position ohne Schutz") ist das
nicht übernehmbar. Diese Spur hält deshalb `stop_pct` und `ziel_r` aus der
Wachen; der Ausstieg am Kreuz läuft über `zusatz_ausstieg` mit dem Grund
`emacross`, damit er im Journal als **Handelsentscheidung** steht und nicht
als Zwangsschluss zählt.

**2. Kerzen statt Ticks.** Das Original läuft auf 250 **Ticks**
(`ETHUSDT.BINANCE-250-TICK-LAST-INTERNAL`). Ticks sind hier nicht
verfügbar; diese Spur rechnet auf abgeschlossenen **1H-Kerzen**. Das ist
ein anderes Signal und damit eine andere Strategie. Deshalb ist diese Spur
**kein Maß für das Original**, sondern die Frage, ob die Regel auf unseren
Daten etwas bringt.

## Stand und Freigabe

| | |
|---|---|
| Orderweg | **keiner** |
| `handel_erlaubt` | false |
| `freigabe.erfuellt` | false |
| `trigger_modus` | signal |
| Runden | **0** (angelegt 03.10.2026) |
| Stop | 6 % — **ohne Datengrundlage**, aus der ATR-Nähe gesetzt |
| Journal | `handelsjournal.csv`, Spiegelung nach `Q:\Handel_Journal\nautilus_emacross` |

Der Stop-Wert ist eine Annahme, keine Messung. Die MAE-Spalte ist
inzwischen in 33 Spuren vorhanden — erst wenn hier genug Runden liegen,
wird der Stop aus den Daten gesetzt.

## Tests

```
cd Agenten/Handel/nautilus_emacross/tests
PYTHONPATH="$PWD/../.." ../../scanner/.venv/Scripts/python.exe -m unittest test_emacross
```

8 Tests, kein Netz. Sie prüfen die Regel gegen den **Originaltext**:
der EMA-Seed ist der SMA der ersten n Werte (nicht der erste Wert),
alpha = 2/(n+1), long und short kommen beide vor, ohne Kreuz kein Auftrag,
zu wenige Kerzen ergeben kein Signal. Der Test `test_gegenprobe_long_only_faellt_durch`
stellt die Regel auf, die die drei alten Arme fahren — sie darf hier nicht
durchkommen.