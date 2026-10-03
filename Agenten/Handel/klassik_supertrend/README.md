# klassik_supertrend

Supertrend Explorer (Pine-Vorlage `supertrend-explorer.pine`)

**Regel:** SuperTrend auf hl2 mit `ATR(10) x 3.0` (Wilder, `up` nur verlaengert solange
`close[1]` darueber lag): Wechsel der Linie von short auf long = Long-Einstieg, von long auf
short = Short-Einstieg; Ausstieg beim Gegenwechsel. `atr_wechsel=false` nutzt `sma(tr, 10)`
wie `changeATR=false` der Vorlage.

Instrumente BTC/ETH/SOL-USDT-SWAP auf 4H, Papier, kein Live-Zweig. Risiko 5 USD je Position,
3 Plaetze, Stop 3.0 %, Ziel 2.0 R. Rechnung: `Agenten/Handel/klassik_regeln.py`, Buch:
`spur_buch.py`. Angelegt 02.10.2026.