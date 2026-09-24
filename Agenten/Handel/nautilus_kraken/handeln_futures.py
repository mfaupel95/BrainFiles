"""Launcher der Kraken-Futures-Variante (PF_XBTUSD, USD, Hebel).

Setzt die Umgebungsvariablen, die handeln.py fuer die Futures-Variante
braucht, und ruft den gemeinsamen Zyklus _main() auf. Getrennte
Zustand/Journal-Dateien (Suffix .futures), damit Spot und Futures nicht
denselben Zustand teilen.

Die Bus-Meldung traegt dieser Walker selbst (handel/nautilus_kraken_futures)
und ruft den KERN _main() - nicht main(), das wuerde den Lauf ein zweites
Mal kapseln (Muster der Spiegel-Schattenbuecher).

Aufruf wie handeln.py:  python handeln_futures.py --papier|--vorschau|--wachen
"""

import os
import sys

os.environ["KRAKEN_PRODUKT"] = "futures"
os.environ["KRAKEN_WACHEN"] = "wachen.futures.json"
os.environ["KRAKEN_SUFFIX"] = ".futures"
os.environ["KRAKEN_BUS_NAME"] = "handel/nautilus_kraken_futures"
os.environ["KRAKEN_SPUR_NAME"] = "nautilus_kraken_futures"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import handeln          # noqa: E402
import ereignis         # noqa: E402


def main():
    with ereignis.lauf("handel/nautilus_kraken_futures"):
        return handeln._main()


if __name__ == "__main__":
    raise SystemExit(main())
