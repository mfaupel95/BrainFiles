# klassik_sr_breaks

Support/Resistance-Breaks (LuxAlgo-Pine `sr-breaks.pine`)

**Regel:** Long beim Schluss ueber der letzten bestaetigten Pivot-Resistance (Break mit
Volumen-OSZ > 20 oder Bull-Wick), Short beim Schluss unter der Pivot-Support; Ausstieg beim
Break in die Gegenrichtung.

Instrumente BTC/ETH/SOL-USDT-SWAP auf 4H, Papier, kein Live-Zweig. Risiko 5 USD je Position,
3 Plaetze, Stop 3.0 %, Ziel 2.0 R. Rechnung: `Agenten/Handel/klassik_regeln.py` (Pivot 15/15,
Volumen-EMA 5/10, Schwelle 20), Buch: `spur_buch.py`. Angelegt 02.10.2026.
