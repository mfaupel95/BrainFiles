"""Tests fuer waisen-wache.py - ohne Netz, ohne echten Cron, ohne echtes Kraken.

Das Modul wird per Pfad geladen und MERKDATEI auf einen Temp-Pfad gebogen;
`messen` wird durch eine Attrappe ersetzt. So laeuft das ORIGINAL, aber es geht
kein Aufruf an die Boerse und kein Schreiben in den echten cache/.
"""

import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKRIPT = Path(__file__).resolve().parent / "waisen-wache.py"


def lade():
    spec = importlib.util.spec_from_file_location("waisen_wache_test", str(SKRIPT))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def waise(txid, paar="SUIEUR", menge=30.69, preis=0.814):
    return {"txid": txid, "paar": paar, "menge": menge, "preis": preis,
            "muenze": "SUI", "lage": "WAISE", "waise": True}


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.w = lade()
        self.w.MERKDATEI = os.path.join(self.tmp.name, "waisen-wache.json")
        self.antwort = ([], None)          # (waisen, fehler)
        self.w.messen = lambda: self.antwort

    def lauf(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.w.main(list(args))
        return buf.getvalue(), rc


class MeldungTest(Basis):
    def test_ohne_waisen_und_ohne_vorgeschichte_schweigt(self):
        text, rc = self.lauf()
        self.assertEqual(text, "")
        self.assertEqual(rc, 0)

    def test_neue_waise_wird_sofort_gemeldet(self):
        self.antwort = ([waise("OU3PX6-4ITGR-NO2W5E")], None)
        text, _ = self.lauf()
        self.assertIn("OU3PX6-4ITGR-NO2W5E", text)
        self.assertIn("SHORT", text)
        self.assertIn("waisen_stops.py --stornieren", text)

    def test_zweiter_lauf_wiederholt_nichts(self):
        # Der Kern der Wache: dieselbe Lage darf nicht alle 30 Minuten melden.
        self.antwort = ([waise("O1")], None)
        self.assertIn("O1", self.lauf()[0])
        self.assertEqual(self.lauf()[0], "")

    def test_nach_sechs_stunden_erinnert_es_wieder(self):
        self.antwort = ([waise("O1")], None)
        self.lauf()
        alt = self.w._lies()
        alt["gemeldet"]["O1"] = (datetime.now(timezone.utc)
                                 - timedelta(hours=7)).isoformat()
        self.w._schreib(alt)
        text, _ = self.lauf()
        self.assertIn("Erinnerung", text)
        self.assertIn("O1", text)

    def test_verschwinden_meldet_einmal_erledigt(self):
        self.antwort = ([waise("O1")], None)
        self.lauf()
        self.antwort = ([], None)
        text, _ = self.lauf()
        self.assertIn("keine Waisen-Stops mehr", text)
        self.assertEqual(self.lauf()[0], "")

    def test_messfehler_wird_gemeldet_aber_nicht_wiederholt(self):
        self.antwort = ([], "HTTPError: 503")
        text, rc = self.lauf()
        self.assertIn("konnte nicht messen", text)
        self.assertIn("keine Entwarnung", text)
        self.assertEqual(self.lauf()[0], "")
        self.assertEqual(rc, 0)

    def test_deckel_bei_fuenf_zeilen(self):
        self.antwort = ([waise("O%d" % i) for i in range(1, 9)], None)
        text, _ = self.lauf()
        self.assertIn("O5", text)
        self.assertNotIn("O6 ", text)
        self.assertIn("und 3 weitere", text)

    def test_alles_meldet_auch_unveraendert(self):
        self.antwort = ([waise("O1")], None)
        self.lauf()
        self.assertEqual(self.lauf()[0], "")
        text, _ = self.lauf("--alles")
        self.assertIn("O1", text)

    def test_merkdatei_wird_geschrieben(self):
        self.antwort = ([waise("O1")], None)
        self.lauf()
        self.assertTrue(os.path.exists(self.w.MERKDATEI))
        self.assertEqual(list(self.w._lies()["gemeldet"]), ["O1"])


class SicherheitTest(Basis):
    def test_storniert_nie(self):
        # Ein Waechter, der an einem echten Konto Orders loescht, ist selbst ein
        # Risiko: die Wache darf keinen Storno-Weg enthalten.
        quelle = SKRIPT.read_text(encoding="utf-8")
        kopf = quelle.split('"""', 2)[2]        # Docstring ausblenden
        for verboten in ("order_stornieren", "stornieren(", "CancelOrder",
                         "_add_order"):
            self.assertNotIn(verboten, kopf)

    def test_rechnet_ueber_das_werkzeug_statt_nachzubauen(self):
        quelle = SKRIPT.read_text(encoding="utf-8")
        self.assertIn("waisen_stops.py", quelle)
        self.assertIn("modul.lage(kraken, stops)", quelle)


if __name__ == "__main__":
    unittest.main()