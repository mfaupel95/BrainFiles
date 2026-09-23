r"""Schattenarm 'weit' der OmniQuant-Spur (24.09.2026, Auftrag Max).

Startet den normalen omniquant-Zyklus, aber mit HANDEL_BUCH=weit: Wachen
(wachen.weit.json), Zustand, Journal und der gelesene Prognose-Bericht
(neuester_weit.json) tragen dann das Suffix, und die Spiegelung zeigt auf
Q:\Handel_Journal\omniquant_weit. Das Hauptbuch bleibt unveraendert und ist
die Vergleichsgrundlage.

Der Unterschied zum Hauptarm sind allein die PROGNOSE-TORE: dieser Arm liest
die weiche Fassung (prognose.weit.json, angelegt am selben Tag), weil die
strenge Fassung am 23.09.2026 bei 71 geprueften Maerkten 0 Treffer hatte - kein
Rauschen, sondern ein Ruecksetzer-Kaeufer in einem Markt ohne Ruecksetzer. Hier
entstehen Papierrunden, damit die Frage 'traegt die Prognose nach Kosten?'
endlich an echten Runden gemessen wird statt an Zwangsschluessen.

Beide Arme bleiben Papier (handel_erlaubt=false, kein Orderweg).

Die Bus-Meldung traegt dieser Walker selbst (handel/omniquant_weit) und ruft
den OMNIMANT-KERN _main() - nicht main(), das wuerde den Lauf doppelt kapseln.

Aufruf wie handeln.py:  python omniquant_weit.py --papier|--vorschau|--wachen
"""

import os
import sys

os.environ["HANDEL_BUCH"] = "weit"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import handeln          # noqa: E402
import ereignis         # noqa: E402

assert os.path.basename(handeln.__file__).startswith("handeln")


def main():
    with ereignis.lauf("handel/omniquant_weit"):
        return handeln._main()


if __name__ == "__main__":
    raise SystemExit(main())
