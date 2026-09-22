"""Tests fuer den Freigabe-Beleg (Agenten/Handel/freigabebeleg.py).

Der Beleg ist das Tor, durch das der Kraken-MCP ueberhaupt eine echte Order
ausfuehren darf. Diese Tests muessen ohne Netz laufen und DUERFEN NIE in echte
Dateien schreiben: das Modul wird in einen Temp-Ordner kopiert (es leitet
seinen Ablageort aus der eigenen Datei ab), das Freigabefenster und die
wachen.json werden durch Stubs ersetzt.

Aufruf aus dem MCP-Server-Ordner:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -t tests
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

SERVER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUELLE = os.path.join(os.path.dirname(os.path.dirname(SERVER)), "Handel",
                      "freigabebeleg.py")


class BelegTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="beleg-test-")
        # Das echte Modul in den Temp-Ordner kopieren: es rechnet CACHE aus
        # seinem eigenen Pfad, damit schreibt jeder Test in den Temp-Ordner.
        shutil.copy(QUELLE, os.path.join(cls.tmp, "freigabebeleg.py"))
        # Freigabefenster als Stub - der echte schreibt in den echten Ordner.
        cls.fenster_offen = False
        with open(os.path.join(cls.tmp, "freigabefenster.py"), "w",
                  encoding="utf-8") as f:
            f.write(
                "def offen(spur):\n"
                "    import json, os\n"
                "    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),\n"
                "              'fenster_antwort.json'), encoding='utf-8') as fh:\n"
                "        return json.load(fh).get('offen', False)\n"
                "def oeffnen(spur, stunden=12):\n"
                "    raise RuntimeError('oeffnen ist hier verboten')\n")
        cls._fenster_setzen(False)
        spec = importlib.util.spec_from_file_location(
            "beleg_unter_test", os.path.join(cls.tmp, "freigabebeleg.py"))
        cls.b = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.b)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def _fenster_setzen(cls, offen):
        with open(os.path.join(cls.tmp, "fenster_antwort.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"offen": bool(offen)}, f)
        cls.fenster_offen = bool(offen)

    def setUp(self):
        self._fenster_setzen(False)
        for name in os.listdir(self.b.CACHE) if os.path.isdir(self.b.CACHE) else []:
            os.remove(os.path.join(self.b.CACHE, name))
        # wachen.json der Spur stubben: handel_erlaubt umschaltbar.
        self.spur = "testspur"
        spur_ordner = os.path.join(self.b.HIER, self.spur)
        os.makedirs(spur_ordner, exist_ok=True)
        self.wachen = os.path.join(spur_ordner, "wachen.json")
        self._handel_erlaubt(True)

    def _handel_erlaubt(self, wert):
        with open(self.wachen, "w", encoding="utf-8") as f:
            json.dump({"handel_erlaubt": wert}, f)

    def test_ohne_offenes_fenster_kein_beleg(self):
        """Der Kernsatz des Tors: ein Chat kann sich keine Erlaubnis geben."""
        self._fenster_setzen(False)
        r = self.b.schreibe(self.spur, "buy", "XBTEUR", 0.001, 60000, "Test")
        self.assertFalse(r.get("ok"))
        self.assertIn("Freigabefenster", r["grund"])
        self.assertIsNone(self.b.lies(self.spur))

    def test_ohne_handel_erlaubt_kein_beleg(self):
        self._fenster_setzen(True)
        self._handel_erlaubt(False)
        r = self.b.schreibe(self.spur, "buy", "XBTEUR", 0.001, 60000, "Test")
        self.assertFalse(r.get("ok"))
        self.assertIn("handel_erlaubt", r["grund"])

    def test_beleg_bei_offenem_fenster(self):
        self._fenster_setzen(True)
        b = self.b.schreibe(self.spur, "buy", "xbteur", 0.001, 60000.0, "Einstieg")
        self.assertEqual(b["spur"], self.spur)
        self.assertEqual(b["paar"], "XBTEUR")
        self.assertEqual(b["seite"], "buy")
        self.assertTrue(b["kennung"])
        self.assertIsNone(b["verbraucht"])
        self.assertTrue(os.path.exists(self.b.datei(self.spur)))

    def test_zweiter_beleg_ersetzt_den_ersten(self):
        self._fenster_setzen(True)
        a = self.b.schreibe(self.spur, "buy", "XBTEUR", 0.001, 60000, "A")
        c = self.b.schreibe(self.spur, "buy", "XBTEUR", 0.002, 61000, "C")
        self.assertNotEqual(a["kennung"], c["kennung"])
        ok, grund = self.b.pruefe(c["kennung"], self.spur, "buy", "XBTEUR", 0.002, 61000)
        self.assertTrue(ok, grund)

    def test_pruefe_lehnt_alles_nicht_passende_ab(self):
        self._fenster_setzen(True)
        b = self.b.schreibe(self.spur, "buy", "XBTEUR", 0.001, 60000, "Einstieg")
        k = b["kennung"]
        faelle = [
            ("falsche Kennung", "000000", "buy", "XBTEUR", 0.001, 60000),
            ("falsche Seite", k, "sell", "XBTEUR", 0.001, 60000),
            ("falsches Paar", k, "buy", "ETHEUR", 0.001, 60000),
            ("Menge zu gross", k, "buy", "XBTEUR", 0.01, 60000),
            ("Preis zu hoch", k, "buy", "XBTEUR", 0.001, 70000),
        ]
        for name, kennung, seite, paar, menge, preis in faelle:
            with self.subTest(fall=name):
                ok, grund = self.b.pruefe(kennung, self.spur, seite, paar, menge, preis)
                self.assertFalse(ok, "%s haette abgelehnt werden muessen" % name)
                self.assertTrue(grund)
        ok, grund = self.b.pruefe(k, self.spur, "buy", "XBTEUR", 0.001, 60000)
        self.assertTrue(ok, grund)

    def test_abgelaufener_beleg_ist_abgesagt(self):
        self._fenster_setzen(True)
        b = self.b.schreibe(self.spur, "buy", "XBTEUR", 0.001, 60000, "Einstieg",
                            gueltig_sekunden=-5)
        ok, grund = self.b.pruefe(b["kennung"], self.spur, "buy", "XBTEUR", 0.001, 60000)
        self.assertFalse(ok)
        self.assertIn("abgelaufen", grund)

    def test_verbrauchter_beleg_gilt_nicht_mehr(self):
        self._fenster_setzen(True)
        b = self.b.schreibe(self.spur, "buy", "XBTEUR", 0.001, 60000, "Einstieg")
        self.assertTrue(self.b.verbrauche(self.spur, b["kennung"], "TX1"))
        ok, grund = self.b.pruefe(b["kennung"], self.spur, "buy", "XBTEUR", 0.001, 60000)
        self.assertFalse(ok)
        self.assertIn("verbraucht", grund)

    def test_kaputte_datei_ist_abgesagt(self):
        """Fail-closed: eine unlesbare Datei ist eine Absage, keine Ausnahme."""
        os.makedirs(self.b.CACHE, exist_ok=True)
        with open(self.b.datei(self.spur), "w", encoding="utf-8") as f:
            f.write("{kaputt")
        ok, grund = self.b.pruefe("egal", self.spur, "buy", "XBTEUR", 0.001, 60000)
        self.assertFalse(ok)
        self.assertIn("kein Beleg", grund)

    def test_uebersicht_zeigt_nur_gueltige(self):
        self._fenster_setzen(True)
        gueltig = self.b.schreibe(self.spur, "buy", "XBTEUR", 0.001, 60000, "A")
        zweite = os.path.join(self.b.HIER, "zweite")
        os.makedirs(zweite, exist_ok=True)
        with open(os.path.join(zweite, "wachen.json"), "w", encoding="utf-8") as f:
            json.dump({"handel_erlaubt": True}, f)
        self.b.schreibe("zweite", "sell", "ETHEUR", 0.01, None, "B",
                        gueltig_sekunden=-1)
        offen = self.b.offene()
        self.assertEqual([o["kennung"] for o in offen], [gueltig["kennung"]])
        self.b.verbrauche(self.spur, gueltig["kennung"], "TX")
        self.assertEqual(self.b.offene(), [])

    def test_protokoll_haelt_die_ausfuehrung_fest(self):
        self._fenster_setzen(True)
        self.b.protokolliere(self.spur, {"beleg": "abc", "echt": True, "menge": "0.001"})
        p = os.path.join(self.b.CACHE, "%s.ausgefuehrt.jsonl" % self.spur)
        with open(p, encoding="utf-8") as f:
            zeilen = [json.loads(z) for z in f if z.strip()]
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0]["beleg"], "abc")
        self.assertIn("zeit", zeilen[0])


if __name__ == "__main__":
    unittest.main()