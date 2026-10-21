"""Tests fuer telemetrie.py: Ereignisse nach tracking-plan.yaml, wirft nie.

Alle Tests schreiben nach TELEMETRIE_DIR (Wegwerfordner), nie in den echten Ordner.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import telemetrie  # noqa: E402


class TelemetrieTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(telemetrie, "WURZEL", self.tmp.name)
        p.start()
        self.addCleanup(p.stop)
        self.journal = os.path.join(HANDEL, "xperp", "handelsjournal.csv")  # wird nie angelegt

    def _zeilen(self):
        out = []
        for name in sorted(os.listdir(self.tmp.name)):
            with open(os.path.join(self.tmp.name, name), encoding="utf-8") as f:
                out += [json.loads(z) for z in f if z.strip()]
        return out

    def test_track_schreibt_eine_zeile_mit_attribution(self):
        r = telemetrie.ereignis(telemetrie.STOERUNG_ERKANNT, "kraken",
                                art="herzschlag_alt", flachgestellt=True)
        self.assertEqual(r, "datei")
        z, = self._zeilen()
        self.assertEqual(z["event"], "stoerung.erkannt")
        self.assertEqual(z["group_spur"], "kraken")
        self.assertIsNone(z["group_position"])
        self.assertEqual(z["user_id"], "max")
        self.assertNotIn("_fehlt", z)

    def test_fehlende_pflicht_property_markiert_statt_zu_werfen(self):
        telemetrie.ereignis(telemetrie.POSITION_NACHGEZOGEN, "x", pos_id="p1")
        z, = self._zeilen()
        self.assertEqual(sorted(z["_fehlt"]), ["quelle", "stufe"])

    def test_unbekannter_name_wird_markiert(self):
        telemetrie.ereignis("foo.bar")
        z, = self._zeilen()
        self.assertTrue(z["_unbekannt"])

    def test_aus_schreibt_nichts(self):
        with mock.patch.object(telemetrie, "AUS", True):
            self.assertEqual(telemetrie.nutzer("papier"), "aus")
        self.assertEqual(self._zeilen(), [])

    def test_totes_ziel_wirft_nicht(self):
        datei = os.path.join(self.tmp.name, "datei")
        open(datei, "w").close()
        with mock.patch.object(telemetrie, "WURZEL", os.path.join(datei, "unter")):
            self.assertEqual(telemetrie.nutzer("papier"), "nichts")

    def test_group_traegt_eltern(self):
        telemetrie.position("xperp-1", "xperp")
        z, = self._zeilen()
        self.assertEqual((z["group_type"], z["group_id"], z["parent_group_id"]),
                         ("position", "xperp-1", "xperp"))

    def test_ausstiegsart(self):
        f = telemetrie.ausstiegsart
        self.assertEqual(
            [f("herzschlag_alt"), f("stop"), f("ziel 1.2"), f("trailing"),
             f("handanpassung"), f("macd_mtf+skaliert"), f(None)],
            ["stoerung", "stop", "ziel", "trailing", "manuell", "signal", "signal"])

    def test_haken_eroeffnet(self):
        p = {"pos_id": "p1", "nominal": 100.0, "stop_pct": 3.0,
             "einstieg": 50.0, "ziel": 55.0}
        self.assertEqual(telemetrie.eroeffnet(self.journal, p, "papier", "BTC", "long"), "datei")
        pos, ev = self._zeilen()
        self.assertEqual(pos["group_type"], "position")
        self.assertEqual(ev["event"], "position.eroeffnet")
        self.assertEqual(ev["group_spur"], "xperp")
        self.assertEqual(ev["properties"]["ziel_abstand_pct"], 10.0)
        self.assertNotIn("_fehlt", ev)   # hebel ist optional

    def test_haken_geschlossen(self):
        p = {"pos_id": "p1", "inst": "BTC", "nominal": 200.0,
             "mfe_pct": 1.5, "mae_pct": -0.5}
        telemetrie.geschlossen(self.journal, p, "papier", "stop 3.0", -4.0, "2.0")
        ev, = self._zeilen()
        e = ev["properties"]
        self.assertEqual((e["ausstiegsart"], e["ergebnis_usd"], e["ergebnis_pct"], e["haltetage"]),
                         ("stop", -4.0, -2.0, 2.0))
        self.assertNotIn("_fehlt", ev)

    def test_haken_ueberspringt_fremde_journale(self):
        fremd = os.path.join(self.tmp.name, "x", "handelsjournal.csv")
        self.assertEqual(telemetrie.eroeffnet(fremd, {"pos_id": "p"}, "papier", "B", "long"), "fremd")
        self.assertEqual(telemetrie.geschlossen(fremd, {}, "papier", "stop", 0, 0), "fremd")
        self.assertEqual(self._zeilen(), [])

    def test_haken_ueberspringt_tests_ordner_und_tiefere_pfade(self):
        for teil in (("tests",), ("xperp", "unter")):
            pfad = os.path.join(HANDEL, *teil, "handelsjournal.csv")
            self.assertEqual(
                telemetrie.eroeffnet(pfad, {"pos_id": "p"}, "papier", "B", "long"), "fremd")
        self.assertEqual(self._zeilen(), [])

    def test_haken_lauf_beendet(self):
        self.assertEqual(telemetrie.lauf_beendet(self.journal, "ok", 1.234, "papier"), "datei")
        ev, = self._zeilen()
        self.assertEqual(ev["event"], "lauf.beendet")
        self.assertEqual(ev["group_spur"], "xperp")
        self.assertEqual(ev["properties"], {"ergebnis": "ok", "dauer_s": 1.234, "modus": "papier"})
        self.assertNotIn("_fehlt", ev)
        fremd = os.path.join(self.tmp.name, "x", "handelsjournal.csv")
        self.assertEqual(telemetrie.lauf_beendet(fremd, "ok", 1, "papier"), "fremd")

    def test_haken_signal(self):
        self.assertEqual(telemetrie.signal(self.journal, "BTC", "long"), "datei")
        telemetrie.signal(self.journal, "ETH", "short", "einstieg_abgelehnt")
        a, b = self._zeilen()
        self.assertEqual((a["event"], a["properties"]["abgelehnt_von"]), ("signal.erkannt", "keine"))
        self.assertEqual(b["properties"]["abgelehnt_von"], "einstieg_abgelehnt")
        self.assertNotIn("_fehlt", a)
        fremd = os.path.join(self.tmp.name, "x", "handelsjournal.csv")
        self.assertEqual(telemetrie.signal(fremd, "BTC", "long"), "fremd")

    def test_haken_stoerung(self):
        telemetrie.stoerung("kraken", "herzschlag_alt", dauer_s=5400)
        ev, = self._zeilen()
        self.assertEqual(ev["event"], "stoerung.erkannt")
        self.assertEqual(ev["properties"]["flachgestellt"], False)
        self.assertNotIn("_fehlt", ev)

    def test_haken_wirft_bei_kaputter_position_nicht(self):
        self.assertIn(telemetrie.eroeffnet(self.journal, None, "papier", "B", "long"),
                      ("nichts",))
        self.assertIn(telemetrie.geschlossen(self.journal, None, "papier", "stop", 1, 1),
                      ("nichts",))


if __name__ == "__main__":
    unittest.main()
