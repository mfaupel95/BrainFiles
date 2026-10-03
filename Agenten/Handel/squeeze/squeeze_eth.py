r"""Schattenarm 'eth' der Squeeze-Spur (03.10.2026, Auftrag Max).

Startet den normalen squeeze-Zyklus mit HANDEL_BUCH=eth: Wachen
(wachen.eth.json), Zustand und Journal tragen das Suffix, die Spiegelung
zeigt auf Q:\Handel_Journal\squeeze_eth.

Der Hauptarm laeuft unveraendert weiter auf BTC/ETH/SOL und bleibt die
Vergleichsgrundlage; dieser Arm steht fest auf ETH-USDC. Beide bleiben
Papier (handel_erlaubt=false, kein Orderweg).

Warum das keine Streuung ist und trotzdem etwas misst: ETH und BTC sind
hoch korreliert. Wer die Regel auf beiden Maerkten misst, sieht nicht zwei
Gewinne, sondern ob die Regel Coin-spezifisch oder generell ist.

Aufruf wie handeln.py:  python squeeze_eth.py --papier|--vorschau|--wachen
"""
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
# VOR dem Import: der Kern liest HANDEL_BUCH beim Laden.
os.environ["HANDEL_BUCH"] = "eth"

import handeln  # noqa: E402

if __name__ == "__main__":
    sys.exit(handeln._main())
