"""Tests fuer telemetrie.py: Adapter von spur_buch.py auf tracking.py.

Jeder Test arbeitet mit einer eigenen Wegwerf-Datenbank, nie mit der echten tracking.db.
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import telemetrie  # noqa: E402
import tracking  # noqa: E402


class TelemetrieTest(unittest.TestCase):
    def setUp(self):
        # tracking.py schliesst seine SQLite-Verbindungen nicht explizit; unter
        # Windows haelt die Datei dann kurz, daher ignore_cleanup_errors.
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        alt = tracking._DB_PFAD
        self.addCleanup(setattr, tracking, "_DB_PFAD", alt)
        self.db = Path(self.tmp.name) / "t.db"
        tracking.init_tracking(self.db)
        self.journal = os.path.join(HANDEL, "xperp", "handelsjournal.csv")  # wird nie angelegt

    def _events(self):
        con = sqlite3.connect(str(self.db))
        try:
            return [(e, json.loads(p)) for e, p in
                    con.execute("SELECT event, properties FROM events ORDER BY id")]
        finally:
            con.close()

    def test_ausstiegsgrund_ist_erstes_wort(self):
        f = telemetrie.ausstiegsgrund
        self.assertEqual([f("stop 3.0"), f("Ziel"), f("macd_mtf+skaliert x"),
                          f("herzschlag_alt"), f(None), f("")],
                         ["stop", "ziel", "macd_mtf+skaliert", "herzschlag_alt",
                          "unbekannt", "unbekannt"])

    def test_eroeffnet(self):
        p = {"nominal": 100.0, "stop": 48.5, "ziel": 55.0, "einstieg": 50.0}
        self.assertEqual(telemetrie.eroeffnet(self.journal, p, "papier", "BTC", "long", "mittel"), "ok")
        (name, e), = self._events()
        self.assertEqual(name, "position.eroeffnet")
        self.assertEqual((e["spur_name"], e["instrument"], e["richtung"], e["is_paper"],
                          e["risikostufe"], e["nominal_eur"], e["stop_kurs"], e["ziel_kurs"]),
                         ("xperp", "BTC", "long", True, "mittel", 100.0, 48.5, 55.0))
        self.assertNotIn("hebel", e)

    def test_geschlossen_short_vorzeichenrichtig(self):
        p = {"inst": "BTC", "seite": "short", "nominal": 200.0, "einstieg": 50.0}
        telemetrie.geschlossen(self.journal, p, "live", "stop 3.0", -4.0, 52.0, "2.0", "hoch")
        (name, e), = self._events()
        self.assertEqual(name, "zyklus.abgeschlossen")
        self.assertEqual((e["ausstiegsgrund"], e["ergebnis_eur"], e["ergebnis_pct"],
                          e["haltedauer_stunden"], e["is_paper"], e["richtung"],
                          e["ausstieg_kurs"]),
                         ("stop", -4.0, -2.0, 48.0, False, "short", 52.0))

    def test_signal_lauf_stoerung(self):
        telemetrie.signal_ausgewaehlt(self.journal, "ETH", "long", "papier")
        telemetrie.lauf_fehlgeschlagen(self.journal, 1.234, "papier", "mittel")
        telemetrie.stoerung("kraken", "herzschlag_alt", dauer_s=5400)
        (a, ea), (b, eb), (c, ec) = self._events()
        self.assertEqual((a, ea["spur_name"], ea["instrument"]), ("signal.ausgewaehlt", "xperp", "ETH"))
        self.assertEqual((b, eb["dauer_s"], eb["risikostufe"]), ("lauf.fehlgeschlagen", 1.234, "mittel"))
        self.assertEqual((c, ec["spur_name"], ec["art"], ec["flachgestellt"]),
                         ("stoerung.erkannt", "kraken", "herzschlag_alt", False))

    def test_konfiguriert_und_nachgezogen(self):
        wachen = os.path.join(HANDEL, "gitter", "wachen.json")   # wird nie angelegt
        self.assertEqual(telemetrie.konfiguriert(wachen, "freigabe.backtest"), "ok")
        fremd = os.path.join(self.tmp.name, "gitter", "wachen.json")
        self.assertEqual(telemetrie.konfiguriert(fremd, "x"), "fremd")
        tracking.track_position_nachgezogen("xperp", "BTC", 90.0, 95.0, False,
                                            hoch_r=1.5, pos_id="p1")
        (a, ea), (b, eb) = self._events()
        self.assertEqual((a, ea["spur_name"], ea["geaendertes_feld"]),
                         ("spur.konfiguriert", "gitter", "freigabe.backtest"))
        self.assertEqual((b, eb["stop_alt"], eb["stop_neu"], eb["quelle"], eb["pos_id"]),
                         ("position.nachgezogen", 90.0, 95.0, "trailing", "p1"))

    def test_fremde_journale_werden_uebersprungen(self):
        for teil in (("tests",), ("xperp", "unter")):
            pfad = os.path.join(HANDEL, *teil, "handelsjournal.csv")
            self.assertEqual(telemetrie.eroeffnet(pfad, {}, "papier", "B", "long"), "fremd")
        fremd = os.path.join(self.tmp.name, "x", "handelsjournal.csv")
        self.assertEqual(telemetrie.geschlossen(fremd, {}, "papier", "stop", 0, 1, 0), "fremd")
        self.assertEqual(telemetrie.lauf_fehlgeschlagen(fremd, 1, "papier"), "fremd")
        self.assertEqual(telemetrie.signal_ausgewaehlt(fremd, "B", "long", "papier"), "fremd")
        self.assertEqual(self._events(), [])

    def test_aus_schreibt_nichts(self):
        with mock.patch.object(telemetrie, "AUS", True):
            self.assertEqual(telemetrie.stoerung("x", "herzschlag_alt"), "aus")
        self.assertEqual(self._events(), [])

    def test_kaputte_position_wirft_nicht(self):
        self.assertEqual(telemetrie.eroeffnet(self.journal, None, "papier", "B", "long"), "nichts")
        self.assertEqual(telemetrie.geschlossen(self.journal, None, "papier", "stop", 1, 1, 1), "nichts")

    def test_testlauf_schreibt_nur_in_ausdruecklich_angegebene_db(self):
        # setUp hat init_tracking(self.db) gerufen -> geschrieben wird
        tracking.track("x.y", {"a": 1})
        self.assertEqual(len(self._events()), 1)
        # ohne ausdrueckliche DB (Standardpfad) wird unter Test NICHT geschrieben
        with mock.patch.object(tracking, "_EXPLIZIT", False):
            tracking.track("x.z", {"a": 2})
        self.assertEqual(len(self._events()), 1)

    def test_unter_test_erkennt_testlaeufe_aber_keine_produktion(self):
        for argv0, erwartet in (("tests/test_x.py", True), ("python -m unittest", True),
                                ("C:/x/unittest/__main__.py", True), ("__main__.py", True),
                                ("dauerlauf.py", False), ("handeln.py", False), ("", False)):
            with mock.patch.object(sys, "argv", [argv0]):
                self.assertEqual(tracking._unter_test(), erwartet, argv0)

    def test_kaputtes_tracking_wirft_nicht(self):
        with mock.patch.object(tracking, "track_stoerung_erkannt", side_effect=RuntimeError("x")):
            self.assertEqual(telemetrie.stoerung("x", "herzschlag_alt"), "nichts")


if __name__ == "__main__":
    unittest.main()
