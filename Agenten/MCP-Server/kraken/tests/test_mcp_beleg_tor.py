"""Tests fuer das Tor im Kraken-MCP (kraken_mcp.py).

Beweist, dass der MCP ohne Beleg NICHT ausfuehren kann, dass er mit Beleg
ausfuehrt, den Beleg dabei verbraucht - und dass die alten Wege zu sind:

  * `kraken_order_aufgeben(echt_ausfuehren=True)` wird abgelehnt
  * `kraken_order_stornieren("all")` wird abgelehnt (Schutz-Stop!)
  * ohne Beleg wird `_privat` (der Netzaufruf) GAR NICHT gerufen

Kein Netz: `_privat` ist durch einen Recorder ersetzt, der Beleg-Ordner ist
ein Temp-Ordner.

Aufruf aus dem MCP-Server-Ordner:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -t tests
"""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest

SERVER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp(prefix="mcp-tor-")


def _vorbereiten():
    """Temp-Handel-Ordner: Kopien der Tor-Module + Stub-Fenster + Spur-Wachen."""
    quelle = os.path.join(os.path.dirname(os.path.dirname(SERVER)), "Handel",
                          "freigabebeleg.py")
    shutil.copy(quelle, os.path.join(TMP, "freigabebeleg.py"))
    with open(os.path.join(TMP, "fenster_antwort.json"), "w", encoding="utf-8") as f:
        json.dump({"offen": True}, f)
    with open(os.path.join(TMP, "freigabefenster.py"), "w", encoding="utf-8") as f:
        f.write("import json, os\n"
                "def offen(spur):\n"
                "    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),\n"
                "                     'fenster_antwort.json')\n"
                "    return json.load(open(p, encoding='utf-8')).get('offen', False)\n")
    spur = os.path.join(TMP, "spur1")
    os.makedirs(spur, exist_ok=True)
    with open(os.path.join(spur, "wachen.json"), "w", encoding="utf-8") as f:
        json.dump({"handel_erlaubt": True}, f)
    os.environ["MAXHIRN_HANDEL"] = TMP
    spec = importlib.util.spec_from_file_location(
        "kraken_mcp_unter_test", os.path.join(SERVER, "kraken_mcp.py"))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


km = _vorbereiten()


class TorTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        self.aufrufe = []
        self.echt = km._privat
        km._privat = lambda methode, **p: (self.aufrufe.append((methode, p)) or
                                           {"txid": ["TX-1"], "descr": {"order": "buy 0.001 XBTEUR"}})
        self.addCleanup(setattr, km, "_privat", self.echt)
        b = km._beleg_modul()
        for name in os.listdir(b.CACHE) if os.path.isdir(b.CACHE) else []:
            os.remove(os.path.join(b.CACHE, name))
        os.makedirs(b.CACHE, exist_ok=True)

    def _beleg(self, seite="buy", paar="XBTEUR", menge=0.001, preis=60000.0):
        b = km._beleg_modul()
        r = b.schreibe("spur1", seite, paar, menge, preis, "Test")
        self.assertTrue(r.get("kennung"), r)
        return r

    def test_order_aufgeben_kann_nicht_mehr_echt(self):
        r = km.kraken_order_aufgeben("XBTEUR", "buy", "0.001", preis="60000",
                                     echt_ausfuehren=True)
        self.assertEqual(r["modus"], "abgelehnt")
        self.assertEqual(self.aufrufe, [], "kein Netzaufruf bei abgelehnter Order")

    def test_order_aufgeben_prueft_weiter(self):
        r = km.kraken_order_aufgeben("XBTEUR", "buy", "0.001", preis="60000")
        self.assertIn("nur geprueft", r["modus"])
        self.assertEqual(self.aufrufe[0][1].get("validate"), "true")

    def test_ohne_beleg_keine_ausfuehrung(self):
        r = km.kraken_order_mit_beleg("spur1", "000000", "XBTEUR", "buy", "0.001",
                                      preis="60000", echt_ausfuehren=True)
        self.assertEqual(r["modus"], "abgelehnt")
        self.assertEqual(self.aufrufe, [], "ohne Beleg darf nichts gesendet werden")

    def test_mit_beleg_wird_ausgefuehrt_und_verbraucht(self):
        modul = km._beleg_modul()
        b = self._beleg()
        r = km.kraken_order_mit_beleg("spur1", b["kennung"], "XBTEUR", "buy",
                                      "0.001", preis="60000", echt_ausfuehren=True)
        self.assertIn("wirklich aufgegeben", r["modus"])
        methode, parameter = self.aufrufe[0]
        self.assertEqual(methode, "AddOrder")
        self.assertNotIn("validate", parameter, "echte Order ohne Pruefmodus")
        # Der Beleg ist EINMALIG.
        ok, grund = modul.pruefe(b["kennung"], "spur1", "buy", "XBTEUR", 0.001, 60000)
        self.assertFalse(ok)
        self.assertIn("verbraucht", grund)
        p = os.path.join(modul.CACHE, "spur1.ausgefuehrt.jsonl")
        self.assertTrue(os.path.exists(p), "jede MCP-Ausfuehrung wird protokolliert")

    def test_trockenlauf_verbraucht_den_beleg_nicht(self):
        modul = km._beleg_modul()
        b = self._beleg()
        r = km.kraken_order_mit_beleg("spur1", b["kennung"], "XBTEUR", "buy",
                                      "0.001", preis="60000")
        self.assertIn("nur geprueft", r["modus"])
        self.assertEqual(self.aufrufe[0][1].get("validate"), "true")
        ok, grund = modul.pruefe(b["kennung"], "spur1", "buy", "XBTEUR", 0.001, 60000)
        self.assertTrue(ok, grund)

    def test_falsches_paar_wird_abgelehnt(self):
        b = self._beleg()
        r = km.kraken_order_mit_beleg("spur1", b["kennung"], "ETHEUR", "buy",
                                      "0.001", preis="60000", echt_ausfuehren=True)
        self.assertEqual(r["modus"], "abgelehnt")
        self.assertEqual(self.aufrufe, [])

    def test_groessere_menge_wird_abgelehnt(self):
        b = self._beleg(menge=0.001)
        r = km.kraken_order_mit_beleg("spur1", b["kennung"], "XBTEUR", "buy",
                                      "0.5", preis="60000", echt_ausfuehren=True)
        self.assertEqual(r["modus"], "abgelehnt")
        self.assertIn("Menge", r["grund"])

    def test_uebersicht_ist_lesend(self):
        b = self._beleg()
        r = km.kraken_beleg_uebersicht()
        self.assertEqual(r["anzahl"], 1)
        self.assertEqual(r["belege"][0]["kennung"], b["kennung"])
        self.assertEqual(self.aufrufe, [], "die Uebersicht ruft nichts ab")

    def test_sammelstorno_ist_gesperrt(self):
        r = km.kraken_order_stornieren("all")
        self.assertEqual(r["storniert"], 0)
        self.assertIn("Sammelstorno", r["abgelehnt"])
        self.assertEqual(self.aufrufe, [], "der Schutz-Stop darf nicht mitgehen")

    def test_einzelstorno_geht(self):
        km.kraken_order_stornieren("TX-9")
        self.assertEqual(self.aufrufe[0], ("CancelOrder", {"txid": "TX-9"}))

    def test_ohne_offenes_fenster_kein_beleg(self):
        """Gegenprobe zum Kern: das Fenster ist Bedingung, nicht Beiwerk."""
        p = os.path.join(TMP, "fenster_antwort.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"offen": False}, f)
        try:
            b = km._beleg_modul()
            r = b.schreibe("spur1", "buy", "XBTEUR", 0.001, 60000.0, "Test")
            self.assertFalse(r.get("ok"))
            ok, grund = b.pruefe("egal", "spur1", "buy", "XBTEUR", 0.001, 60000)
            self.assertFalse(ok)
        finally:
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"offen": True}, f)


if __name__ == "__main__":
    unittest.main()