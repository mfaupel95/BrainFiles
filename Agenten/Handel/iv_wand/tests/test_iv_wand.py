"""Tests fuer die IV-Wand-Spur - ohne Netz.

Geprueft wird die Rechnung, die diese Spur ausmacht: aus Open Interest und
Verfall die Wand bestimmen, daraus die Richtung ableiten und das Ziel als
MARKTPUNKT durch das Buch fuehren. Die Abrufe werden ersetzt
(`options_quelle`, `spot_quelle`), damit der Test nicht an OKX haengt.

Der Ordner-Waechter (setUpModule/tearDownModule) verhindert, dass ein Test in
den echten Spurenordner schreibt - das ist beim Bau der ersten Bot-Spur einmal
passiert.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
for p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln as h  # noqa: E402
import spur_buch as buch  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py: %s" % h.__file__

JETZT = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


def _offen(paare):
    return [{"instId": i, "oiUsd": v} for i, v in paare]


def _uebersicht(paare):
    return [{"instId": i, "markVol": v} for i, v in paare]


class WandTest(unittest.TestCase):
    def test_naechster_verfall_zaehlt_nicht_mit(self):
        # Ein Verfall in 2 Tagen faellt aus dem Fenster (7 bis 45 Tage).
        offen = _offen([("BTC-USD-260918-90000-C", "900000000"),
                        ("BTC-USD-261016-70000-C", "500000000")])
        wand = h.wand_bauen(offen, [], JETZT)
        self.assertEqual(wand["strike"], 70000.0)

    def test_call_und_put_desselben_strikes_zaehlen_zusammen(self):
        offen = _offen([("BTC-USD-261016-70000-C", "400000000"),
                        ("BTC-USD-261016-70000-P", "400000000"),
                        ("BTC-USD-261016-80000-C", "500000000")])
        wand = h.wand_bauen(offen, [], JETZT)
        self.assertEqual(wand["strike"], 70000.0)
        self.assertAlmostEqual(wand["oi_usd"], 800000000.0)

    def test_iv_wird_gemittelt(self):
        offen = _offen([("BTC-USD-261016-70000-C", "1"),
                        ("BTC-USD-261016-70000-P", "1")])
        uebersicht = _uebersicht([("BTC-USD-261016-70000-C", 0.40),
                                  ("BTC-USD-261016-70000-P", 0.60)])
        wand = h.wand_bauen(offen, uebersicht, JETZT)
        self.assertAlmostEqual(wand["iv_pct"], 50.0, places=6)

    def test_ohne_daten_keine_wand(self):
        self.assertIsNone(h.wand_bauen([], [], JETZT))

    def test_verfall_lesen(self):
        # OKX-Verfall ist 08:00 UTC. JETZT steht auf 12:00 UTC desselben Tages,
        # also bleiben 6 Tage und 20 Stunden - nicht glatte 7.
        self.assertAlmostEqual(h.tage_bis("260923", JETZT), 6.8333, places=3)
        self.assertIsNone(h.tage_bis("kaputt", JETZT))

    def test_strike_aus_instid(self):
        self.assertEqual(h.strike_aus("BTC-USD-260925-79000-C"),
                         (79000.0, "260925", "C"))
        self.assertIsNone(h.strike_aus("BTC-USDT"))


class RegelTest(unittest.TestCase):
    def _d(self, spot, wand):
        return {"spot": spot, "wand": {"strike": wand}}

    def test_unter_der_wand_ist_long(self):
        # Spot 70000, Wand 72000 -> 2,9 % darunter.
        self.assertEqual(h.signal(self._d(70000.0, 72000.0), {"max_abstand_pct": 5.0}),
                         "long")

    def test_ueber_der_wand_ist_short(self):
        self.assertEqual(h.signal(self._d(74000.0, 72000.0), {"max_abstand_pct": 5.0}),
                         "short")

    def test_zu_weit_weg_kein_signal(self):
        self.assertIsNone(h.signal(self._d(60000.0, 72000.0), {"max_abstand_pct": 5.0}))

    def test_genau_auf_der_wand_kein_signal(self):
        self.assertIsNone(h.signal(self._d(72000.0, 72000.0), {"max_abstand_pct": 5.0}))

    def test_ziel_ist_die_wand(self):
        self.assertEqual(h.ziel(self._d(70000.0, 72000.0), {}), 72000.0)


class BuchTest(unittest.TestCase):
    """Der Buchweg mit einem Marktziel - gegen einen Temp-Ordner."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (buch.SCHREIBEN, h.options_quelle, h.spot_quelle)
        buch.SCHREIBEN = True
        w = json.load(open(os.path.join(SPUR, "wachen.json"), encoding="utf-8"))
        w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")
        with open(os.path.join(self.tmp.name, "wachen.json"), "w",
                  encoding="utf-8") as f:
            json.dump(w, f)
        h.spot_quelle = lambda w_: 70000.0
        h.options_quelle = lambda w_: {
            "offen": _offen([("BTC-USD-261016-72000-C", "900000000")]),
            "uebersicht": _uebersicht([("BTC-USD-261016-72000-C", 0.42)])}

    def tearDown(self):
        buch.SCHREIBEN, h.options_quelle, h.spot_quelle = self.alt
        self.tmp.cleanup()

    def test_ziel_ist_der_wandstrike_nicht_das_vielfache(self):
        buch.zyklus(self.tmp.name, h.daten_holen, h.signal, "papier",
                    "test", ziel=h.ziel)
        with open(os.path.join(self.tmp.name, "zustand.json"), encoding="utf-8") as f:
            z = json.load(f)
        (p,) = z["positionen"]
        self.assertEqual(p["seite"], "long")
        self.assertAlmostEqual(p["ziel"], 72000.0, places=6)
        self.assertAlmostEqual(p["einstieg"], 70000.0, places=6)

    def test_vorschau_schreibt_nichts(self):
        buch.zyklus(self.tmp.name, h.daten_holen, h.signal, "vorschau",
                    "test", ziel=h.ziel)
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name,
                                                    "handelsjournal.csv")))

    def test_ziel_hinter_dem_einstieg_wird_abgelehnt(self):
        # Ein long mit Ziel UNTER dem Einstieg ist kein Handel.
        self.assertIsNone(buch.einstieg({"positionen": []}, "BTC-USDT", "long",
                                        70000.0, {"risiko_je_position_usd": 5.0,
                                                  "max_pro_trade_usd": 100.0,
                                                  "stop_prozent": 4.0,
                                                  "pflicht_stop_prozent_min": 3.0,
                                                  "pflicht_stop_prozent_max": 8.0},
                                        1.0, "test", ziel_preis=69000.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
