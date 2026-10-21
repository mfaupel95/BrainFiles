# Kein Vorschlag - spur1

## Priorisierte Empfehlungen (LLM)

1. Parameter vorerst nicht ändern (nur 18 Runden), da die Basisdaten noch zu unvollständig sind.
2. Stop-Verluste (-3,37) sind deutlich höher als Gewinne; prüfen Sie, ob die Stop-Einstellungen zu eng sind.
3. Das mittlere Zielgewinn (15,58) ist solide, aber die hohe Abbruchquote durch Stopps verschlechtert den Netto-GV drastisch.

Datum: 2026-09-17

Grund: nur 5 OOS-Runden (>= 20 noetig)

## Baseline-Kennzahlen

| Fenster | netto_gv_je_runde | n | max_drawdown |
|---|---|---|---|
| 120-150 | 0.0000 | 0 | 0.0000 |
| 150-180 | -6.3569 | 3 | 19.0708 |
| 180-210 | 0.0000 | 0 | 0.0000 |
| 210-240 | -0.4798 | 3 | 8.1560 |
| 240-270 | 17.3908 | 3 | 0.0000 |
| 270-300 | -7.4763 | 3 | 22.4290 |
| 300-330 | 7.1164 | 6 | 16.5518 |
| Aggregat | 2.8851 | 18 | 27.2268 |
