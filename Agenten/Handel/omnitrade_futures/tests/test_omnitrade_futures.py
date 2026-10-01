"""Tests fuer die omnitrade_futures-Spur: Vertrag, Adapter, Trailing.

Ohne Netz und ohne Schluessel - der Futures-Weg wird mit einer Aufzeichnungs-
Attrappe gestellt. Was geprueft wird: die SPUR regelt (wachen lesbar, Live
gesperrt), der Adapter haelt die spur_buch-Schnittstelle ein, und das Trailing
zieht den Stop nur NACH OBEN und laesst bei Scheitern den alten Stop stehen.
"""

import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
for p in (HANDEL, os.path.join(HANDEL, "scanner"), HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import spur_buch as buch                                    # noqa: E402
import weg                                                  # noqa: E402


class WachenTest(unittest.TestCase):
    def test_wachen_lesbar_und_regeln(self):
        w = buch.lade_wachen(buch.pfade(HIER)[0])
        self.assertEqual(w["boerse"], "kraken_futures")
        self.assertEqual(w["hebel"], 7.0)            # Max: "hebel x7 fuer den anfang"
        self.assertFalse(w["handel_erlaubt"])        # Papier zuerst, immer
        self.assertFalse(w["freigabe"]["erfuellt"])
        self.assertEqual(w["instrument"], "PF_SOLUSD")
        self.assertGreaterEqual(float(w["mindest_guthaben"]), 25.0)

    def test_wachen_hat_trailing(self):
        w = buch.lade_wachen(buch.pfade(HIER)[0])
        self.assertGreater(float(w["trailing_stop_prozent"]), 0.0)


class WegTest(unittest.TestCase):
    def test_hebel_als_zahl_und_sicherer_ausfall(self):
        self.assertEqual(weg.setze_hebel({"hebel": 7}), 7.0)
        self.assertEqual(weg.setze_hebel({"hebel": "x"}), 1.0)   # nie raten
        self.assertEqual(weg.setze_hebel({}), 1.0)

    def test_menge_fuer_ganze_kontrakte(self):
        menge, fehler = weg.menge_fuer("PF_SOLUSD", 130.0, 117.0)
        self.assertEqual((menge, fehler), (1.0, ""))
        menge, fehler = weg.menge_fuer("PF_SOLUSD", 50.0, 117.0)
        self.assertEqual(menge, 0.0)
        self.assertTrue(fehler)

    def test_schnittstelle_vollstaendig(self):
        for name in ("markt_kauf", "markt_verkauf", "algo_stop_setzen",
                     "algo_stornieren", "gefuellte_menge", "guthaben_waehrung",
                     "letzter_kurs", "menge_fuer", "schluessel_vorhanden",
                     "demo_modus", "stop_nachziehen"):
            self.assertTrue(callable(getattr(weg, name, None)), name)


class _AttrappeWeg:
    """Zeichnet auf, was spur_buch an der Boerse tut."""

    def __init__(self, scheitert=False):
        self.nachgezogen = []
        self.verkauft = []
        self.storniert = []
        self.scheitert = scheitert

    def stop_nachziehen(self, order_id, inst, menge, stop_preis):
        if self.scheitert:
            raise RuntimeError("editorder abgelehnt")
        self.nachgezogen.append((order_id, inst, stop_preis))
        return "EDIT-%d" % (len(self.nachgezogen),)

    def algo_stornieren(self, inst, order_id):
        self.storniert.append(order_id)

    def markt_verkauf(self, inst, menge):
        self.verkauft.append(inst)


def _position(stop):
    return {"inst": "SOL-USDC", "venue_inst": "PF_SOLUSD", "seite": "long",
            "modus": "live", "stop": stop, "stop_id": "STP-1", "ziel": 999.0,
            "einstieg": 100.0, "nominal": 117.0, "menge": 1.0,
            "stop_pct": 1.5, "pos_id": "p1", "eroeffnet_zeit": "x"}


class TrailingTest(unittest.TestCase):
    def _lauf(self, scheitert=False):
        weg_ = _AttrappeWeg(scheitert=scheitert)
        w = {"trailing_stop_prozent": 0.03}
        z = {"positionen": [_position(stop=98.5)]}
        with tempfile.TemporaryDirectory() as tmp:
            buch.pruefe_ausstiege(z, {"SOL-USDC": 120.0}, w,
                                  os.path.join(tmp, "j.csv"),
                                  live=True, weg=weg_)
        return weg_, z["positionen"][0]

    def test_stop_wird_nach_oben_gezogen(self):
        weg_, p = self._lauf()
        self.assertEqual(len(weg_.nachgezogen), 1)
        self.assertAlmostEqual(p["stop"], 120.0 * 0.97)   # 116.4 > 98.5
        self.assertEqual(p["stop_id"], "EDIT-1")
        self.assertEqual(weg_.verkauft, [])               # keine Ausstiegsorder

    def test_stop_wird_nie_gesenkt(self):
        weg_, p = self._lauf()
        # Kurs unter dem alten Stop: der neue Preis laege tiefer - kein Aufruf.
        self.assertGreater(p["stop"], 98.5)
        weg2, p2 = _AttrappeWeg(), None
        w = {"trailing_stop_prozent": 0.03}
        z = {"positionen": [_position(stop=98.5)]}
        with tempfile.TemporaryDirectory() as tmp:
            buch.pruefe_ausstiege(z, {"SOL-USDC": 90.0}, w,
                                  os.path.join(tmp, "j.csv"),
                                  live=True, weg=weg2)
        # 90 < Stop 98.5: der Stop haette gereissen - kein Trailing davor.
        self.assertEqual(weg2.nachgezogen, [])

    def test_scheitern_laesst_alten_stop_stehen(self):
        weg_, p = self._lauf(scheitert=True)
        self.assertAlmostEqual(p["stop"], 98.5)           # unveraendert
        self.assertEqual(p["stop_id"], "STP-1")           # geschuetzt bleibt


if __name__ == "__main__":
    unittest.main()
