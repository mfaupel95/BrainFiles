r"""Schattenarm 'eth' der Squeeze-Spur (03.10.2026, Auftrag Max).

Startet den normalen squeeze-Zyklus mit HANDEL_BUCH=eth: Wachen
(wachen.eth.json), Zustand und Journal tragen das Suffix, die Spiegelung
zeigt auf Q:\Handel_Journal\squeeze_eth.

Der Hauptarm laeuft unveraendert weiter auf BTC/ETH/SOL und bleibt die
Vergleichsgrundlage; dieser Arm steht fest auf ETH-USDC. Beide bleiben
Papier (handel_erlaubt=false, kein Orderweg).

Die Bus-Meldung traegt dieser Walker selbst (handel/squeeze_eth) und ruft den
KERN _main() - nicht main(), das wuerde den Lauf ein zweites Mal kapseln und
als 'handel/squeeze' melden.

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

import ereignis         # noqa: E402
import handeln         # noqa: E402


def main():
    # EIGENE Bus-Meldung (handel/squeeze_eth), Muster wie spiegel_knapp:
    # handeln._main() statt handeln.main(), sonst meldet der Arm als
    # 'handel/squeeze' und der Schattenarm laeuft unsichtbar mit.
    with ereignis.lauf("handel/squeeze_eth"):
        return handeln._main()


if __name__ == "__main__":
    sys.exit(main())
