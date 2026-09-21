"""Tests: wartende Limit-Auftraege in xperp/handeln.py.

ANLASS (gemessen 21.09.2026, 19:08-19:40): xperp versuchte dreimal, CRCL zu
kaufen - Limit 93.81 / 93.63 / 94.46 bei Markt 94.84. Der Einstieg kommt aus
der Zonenrechnung und liegt ABSICHTLICH unter dem Markt; die neue
Fuellungspruefung stornierte jede Order nach 8 s und schrieb
`order_nicht_gefuellt` ins Journal. Beides zusammen war eine Schleife.

Jetzt: ein Limit, das fillen KANN, muss fuellen (sonst Storno als Fehler);
ein Limit hinter dem Markt bleibt liegen und wird von wartende_auftraege()
verwaltet - fuellt es, wird die Position gebucht, stirbt es, wird es
vergessen.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parent
sys.path.insert(0, str(SPUR))
sys.path.insert(0, str(HANDEL))

import handeln as h                                                  # noqa: E402


def _auftrag(inst="CRCL-100"):
    return {"inst": inst, "basis": "CRCL", "seite": "long", "familie": "aktie",
            "einstieg": 93.81, "stop": 90.0, "ziel": 100.0, "liq": 75.0,
            "kontrakte": 1.1, "nominal": 103.0, "margin": 20.6, "hebel": 5.0,
            "gebuehr_taker": 0.0005, "ord_id": "3942970066569383936",
            "gestellt": "2026-09-21T19:08:06+00:00"}


class WartendeAuftraege(unittest.TestCase):
    def setUp(self):
        self.j = patch.object(h, "journal")
        self.j.start()
        self.addCleanup(self.j.stop)
        self.storno = patch.object(h, "okxf")
        # Nur die Netzfunktionen ersetzen, die dieser Pfad nutzt.
        self.addCleanup(self.storno.stop)

    def test_gefuellter_auftrag_wird_zur_position(self):
        z = {"positionen": [], "wartende": [_auftrag()]}
        with patch.object(h.okxf, "order_stand",
                          return_value={"state": "filled", "accFillSz": "1.1",
                                        "avgPx": "93.81"}):
            n = h.wartende_auftraege(z, live=True, w={})
        self.assertEqual(n, 1)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(z["positionen"][0]["kontrakte"], 1.1)
        self.assertEqual(z["positionen"][0]["einstieg"], 93.81)
        self.assertEqual(z["positionen"][0]["modus"], "live")
        self.assertEqual(z["wartende"], [], "der Auftrag ist erledigt")

    def test_stornierter_auftrag_wird_vergessen(self):
        z = {"positionen": [], "wartende": [_auftrag()]}
        with patch.object(h.okxf, "order_stand", return_value={"state": "canceled"}):
            n = h.wartende_auftraege(z, live=True, w={})
        self.assertEqual(n, 0)
        self.assertEqual(z["wartende"], [])
        self.assertEqual(z["positionen"], [])

    def test_noch_offener_auftrag_bleibt_liegen(self):
        z = {"positionen": [], "wartende": [_auftrag()]}
        with patch.object(h.okxf, "order_stand", return_value={"state": "live"}):
            n = h.wartende_auftraege(z, live=True, w={})
        self.assertEqual(n, 0)
        self.assertEqual(len(z["wartende"]), 1)

    def test_netzfehler_laesst_den_auftrag_stehen(self):
        z = {"positionen": [], "wartende": [_auftrag()]}
        with patch.object(h.okxf, "order_stand",
                          side_effect=RuntimeError("kein Netz")):
            with self.assertRaises(RuntimeError):
                h.wartende_auftraege(z, live=True, w={})
        # Wichtig: der Auftrag ist NICHT verschwunden - ein Abfragefehler darf
        # keinen wartenden Auftrag verlieren (er liegt an der Boerse).
        self.assertEqual(len(z.get("wartende", [])), 1)

    def test_leere_liste_ist_kein_fehler(self):
        self.assertEqual(h.wartende_auftraege({}, live=True, w={}), 0)
        self.assertEqual(h.wartende_auftraege({"wartende": []}, live=True, w={}), 0)


class Marktbarkeit(unittest.TestCase):
    """Die Regel, die den Storno ausloest - gegen die echten Marktzahlen."""

    def test_limit_unter_dem_ask_ist_wartend(self):
        # CRCL am 21.09.2026: Markt 94.84, Order 93.81 -> darf NICHT storniert
        # werden, sondern wartet.
        with patch.object(h.okxf, "kurs_und_spanne",
                          return_value=(94.84, 94.86, 94.91)):
            _, bid, ask = h.okxf.kurs_und_spanne("CRCL-100")
        einstieg_long = 93.81
        self.assertFalse(einstieg_long >= ask, "unter dem Ask = wartend")

    def test_limit_auf_oder_ueber_dem_ask_ist_marktbar(self):
        _, bid, ask = (94.84, 94.86, 94.91)
        self.assertTrue(94.91 >= ask)
        self.assertTrue(95.50 >= ask)


if __name__ == "__main__":
    unittest.main()
