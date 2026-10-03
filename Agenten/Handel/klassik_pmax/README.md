# klassik_pmax

PMax Explorer (Pine-Vorlage `pmax-explorer.pine`)

**Regel:** MAvg (EMA10 auf hl2) kreuzt ueber PMax = Long, darunter = Short; Ausstieg beim
Gegenkreuz. PMax ist SuperTrend-artig: `MAvg -/+ 3.0 x ATR(10)` (Wilder), longStop steigt nur,
shortStop faellt nur. Acht MA-Typen ueber `ma_typ` waehlbar (SMA/EMA/WMA/TMA/VAR/WWMA/ZLEMA/TSF),
`atr_wechsel=false` nutzt `sma(tr, 10)` statt des ATR — beides wie die Vorlage.

Instrumente BTC/ETH/SOL-USDT-SWAP auf 4H, Papier, kein Live-Zweig. Risiko 5 USD je Position,
3 Plaetze, Stop 3.0 %, Ziel 2.0 R. Rechnung: `Agenten/Handel/klassik_regeln.py`, Buch:
`spur_buch.py`. Angelegt 02.10.2026.