"""Die eine Gebuehrenzahl fuer Backtest und Angleichung von handeln.py.

0,05 % OKX Taker bei Volumen < 10.000, gemessen 02.09.2026 (Handelsregeln.md).
Identisch in scanner/handeln.py - test_kosten_gleich.py prueft das.
"""

GEBUEHR_PCT = 0.0005
