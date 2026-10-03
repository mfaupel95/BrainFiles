"""Die Durchsetzung des Basis-Deckels: neue Einstiege binden.

Regel: Ist eine Basis ueber dem Deckel, bekommt sie KEINEN neuen
Einstieg mehr. Bestehende Positionen laufen weiter - sie zu schliessen waere
eine Order und gehoert in die Freigabekette.

Der Aufrufer haengt das an `sperren_live()` in spur_buch und an den
signal-executor. Beide sind Wege, auf denen ECHTE Orders entstehen -
genau dort gehoert die Schranke hin, nicht in eine Anzeige.

WARUM NICHT IN DER SIGNALBERECHNUNG
-----------------------------------
Weil das ein Tor ist und kein Filter. Eine Spur, die ein Signal sieht und
es nicht handelt, sieht fuer tot aus - der stille-spuren-wache wuerde
sie als tot melden, ohne zu wissen warum. Hier wird der Einstieg abgelehnt
und protokolliert, die Spur laeuft weiter und sieht gesund aus.
"""

import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = HIER
if HANDEL not in sys.path:
    sys.path.append(HANDEL)

import basis_deckel  # noqa: E402


def ueber_dem_deckel(inst):
    """(gesperrt, grund) fuer EIN Instrument."""
    try:
        basen, _gesamt, _ = basis_deckel.lage()
    except Exception as e:                                   # noqa: BLE001
        # Ein Ausfall des Deckels ist kein Freibrief.
        return True, ("Basis-Deckel nicht lesbar (%s) - kein neuer Einstieg "
                      "in eine Basis, deren Anteil unbekannt ist"
                      % str(e)[:80])
    b = None
    try:
        import risiko_beitrag
        b = risiko_beitrag.basisform(inst)
    except Exception:                                        # noqa: BLE001
        pass
    if b is None or b not in basen:
        # Eine Basis, die noch gar nicht im Buch ist, kann den Deckel nicht
        # reissen - sie hat 0 % von 0 %.
        return False, ""
    e = basen[b]
    if not e["ueber"]:
        return False, ""
    return True, ("Basis-Deckel: %s traegt %.1f %% des Kapitals (Grenze %.0f %%) "
                  "- kein neuer Einstieg; bestehende Positionen laufen weiter"
                  % (b, e["anteil"], basis_deckel.DECKEL_PROZENT))