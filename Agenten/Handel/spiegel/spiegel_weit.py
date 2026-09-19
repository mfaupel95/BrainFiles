"""Schattenbuch 'weit' der Spiegel-Spur (V1 Ausstiegsgeometrie, 18.09.2026).

Startet den normalen spiegel-Zyklus, aber mit HANDEL_BUCH=weit: alle
fuenf Buchdateien (Wachen, verfolgte, Zustand, Journal, Ablehnungen)
tragen dann das Suffix .weit, das journal_zweitziel dieser Wachen zeigt
auf Q:\\Handel_Journal\\spiegel_weit. Das Hauptbuch bleibt unveraendert
und ist die Vergleichsgrundlage.

Die Bus-Meldung traegt dieser Walker selbst (handel/spiegel_weit) und
ruft den SPIEGEL-KERN _main() - nicht main(), das wuerde den Lauf ein
zweites Mal kapseln.

Aufruf wie spiegel.py:  python spiegel_weit.py --papier|--vorschau|--wachen
"""

import os
import sys

os.environ["HANDEL_BUCH"] = "weit"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spiegel          # noqa: E402
import ereignis         # noqa: E402


def main():
    with ereignis.lauf("handel/spiegel_weit"):
        return spiegel._main()


if __name__ == "__main__":
    raise SystemExit(main())