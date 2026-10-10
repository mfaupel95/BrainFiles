"""Tests: ein Boersenfehler im Buchabgleich darf den Zyklus nicht abbrechen.

ANLASS (Review 09.10.2026): `lauf()` ruft `buche_abgleich` VOR Kill-Switch und
Herzschlag-Notausstieg. `wartende_auftraege` fing Fehler von `okxf.order_stand`
nicht ab; die Ausnahme lief durch `lauf()` und uebersprang den Kill.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPUR.parent))
sys.path.insert(0, str(SPUR))

import handeln as h                                                  # noqa: E402

assert h.__file__.startswith(str(SPUR)), "falsches handeln: %s" % h.__file__


class AbgleichStufe(unittest.TestCase):
    def test_ausnahme_wird_zum_standardwert(self):
        def kaputt():
            raise RuntimeError("OKX-Schluessel fehlen")
        self.assertEqual(h._abgleich_stufe("x", kaputt), 0)
        self.assertEqual(h._abgleich_stufe("x", kaputt, standard=[]), [])

    def test_normalfall_reicht_ergebnis_durch(self):
        self.assertEqual(h._abgleich_stufe("x", lambda a, b=1: a + b, 2, b=3), 5)


class AbgleichBrichtNichtAb(unittest.TestCase):
    def test_order_stand_wirft_abgleich_laeuft_durch(self):
        z = {"positionen": [], "wartende": [
            {"inst": "XRP-USD_UM_XPERP-310404", "ord_id": "1", "kontrakte": 1}]}
        w = {}
        with patch.object(h.okxf, "order_stand",
                          side_effect=RuntimeError("Netz weg")), \
             patch.object(h, "buche_verkaeufe_aus_boerse", return_value=0), \
             patch.object(h, "bueche_geister_aus", return_value=0), \
             patch.object(h, "bueche_fremde_positionen_uebernehmen",
                          return_value=0), \
             patch.object(h, "bueche_groessen_abgleichen", return_value=[]), \
             patch.object(h, "bueche_stopdeckung", return_value=([], True)):
            stand = h.buche_abgleich(z, w, live=True, still=True)
        self.assertEqual(stand["wartende"], 0)
        self.assertEqual(len(z["wartende"]), 1)       # Buch unberuehrt

    def test_stopdeckung_wirft_standard_ist_leere_deckung(self):
        with patch.object(h, "wartende_auftraege", return_value=0), \
             patch.object(h, "buche_verkaeufe_aus_boerse", return_value=0), \
             patch.object(h, "bueche_geister_aus", return_value=0), \
             patch.object(h, "bueche_fremde_positionen_uebernehmen",
                          return_value=0), \
             patch.object(h, "bueche_groessen_abgleichen", return_value=[]), \
             patch.object(h, "bueche_stopdeckung",
                          side_effect=RuntimeError("x")):
            stand = h.buche_abgleich({"positionen": []}, {}, True, still=True)
        self.assertEqual(stand["deckung"], 0)
        self.assertFalse(stand["deckung_abfrage"])


if __name__ == "__main__":
    unittest.main()
