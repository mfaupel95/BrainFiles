"""Die Risiko-Beitrag-Wache an ihren Regeln, nicht am heutigen Haus.

Der Teststand am 03.10.2026: 79 Positionen, 572,56 USD Gesamtrisiko, BTC
mit 2958,30 USD in 26 Positionen ueber 20 Spuren. Diese Zahlen sind NICHT
der Test - sie sind der Anlass. Geprueft wird, was gelten soll:

  1. Ein Instrument wird auf seine BASIS gebuendelt. Fuenf Schreibweisen
     von BTC sind EINE Wette; wer sie getrennt zaehlt, zaehlt eine
     Position fuenffach.
  2. Das Risiko einer Position ist der Abstand Einstieg/Stop auf das
     Nominal - nicht der Nominalwert selbst.
  3. Eine Position OHNE Stop ist nicht risikofrei, sie ist der ganze
     Einsatz. Sie wird als Befund gemeldet, nicht als Zahl uebersehen.
  4. Die Wache meldet eine VERAENDERUNG und schweigt sonst. Eine Wache,
     die bei jedem Lauf dasselbe sagt, wird abgeschaltet und damit blind.
"""
import importlib.util
import json
import os
import tempfile
import unittest

WURZEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", "..", ".."))
KERN = os.path.join(WURZEL, "Agenten", "Handel", "risiko_beitrag.py")
WACH = os.path.join(WURZEL, "Agenten", "Hermes", "scripts", "risiko-wache.py")


def lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rb = lade(KERN, "risiko_beitrag")


class BasisTest(unittest.TestCase):
    # 1 -------------------------------------------------------------
    def test_fuenf_schreibweisen_sind_eine_basis(self):
        formen = ["BTC-USDT-SWAP", "BTC-USDC", "BTC-USDT", "XBT-USD",
                  "BTC-USD_UM_XPERP-310704"]
        basis = {rb.basisform(f) for f in formen}
        # XBT ist BTC. Kraken fuehrt Bitcoin unter dem Kuerzel XBT; ohne diese
        # Zuordnung gehoeren die xperp-Positionen zur Basis "XBT", und der
        # Basis-Deckel sperrte BTC-USDT-SWAP, liess XBT-USD aber durch -
        # ein Deckel, den man mit einem anderen Namen umgeht (04.10.2026).
        self.assertEqual(basis, {"BTC"},
                         "alle fuenf Schreibweisen sind EINE Basis")

    def test_verschiedene_bleiben_verschieden(self):
        self.assertNotEqual(rb.basisform("ETH-USDT-SWAP"),
                            rb.basisform("SOL-USDT-SWAP"))

    def test_leeres_instrument_wird_kein_absturz(self):
        self.assertTrue(rb.basisform(None))
        self.assertTrue(rb.basisform(""))


class RisikoRechnungTest(unittest.TestCase):
    def setUp(self):
        self.ord = tempfile.mkdtemp()
        self._alt = rb.HANDEL
        rb.HANDEL = self.ord

    def tearDown(self):
        rb.HANDEL = self._alt

    def spur(self, name, positionen, wachen=None):
        ordner = os.path.join(self.ord, name)
        os.makedirs(ordner, exist_ok=True)
        with open(os.path.join(ordner, "zustand.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"positionen": positionen}, fh)
        with open(os.path.join(ordner, "wachen.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(wachen or {"waehrung": "USD"}, fh)

    # 2 -------------------------------------------------------------
    def test_risiko_ist_abstand_zum_stop(self):
        self.spur("a", [{"inst": "BTC-USDT", "seite": "long",
                         "einstieg": 100.0, "stop": 95.0, "nominal": 1000.0}])
        b = rb.beitrag_der_spur("a", os.path.join(self.ord, "a"))
        self.assertAlmostEqual(b["risiko"], 50.0, places=6,
                               msg="5 % von 1000 USD")

    # 3 -------------------------------------------------------------
    def test_position_ohne_stop_ist_der_ganze_einsatz(self):
        self.spur("b", [{"inst": "BTC-USDT", "seite": "long",
                         "einstieg": 100.0, "stop": 0.0, "nominal": 500.0}])
        b = rb.beitrag_der_spur("b", os.path.join(self.ord, "b"))
        self.assertAlmostEqual(b["risiko"], 500.0, places=6)
        self.assertIn("OHNE STOP", b["positionen"][0]["marke"])

    # 4 -------------------------------------------------------------
    def test_wache_meldet_einmal_und_dann_still(self):
        w = lade(WACH, "risiko_wache")
        self.spur("c", [{"inst": "BTC-USDT", "seite": "long", "einstieg": 100.0,
                         "stop": 90.0, "nominal": 1000.0}])
        w.rb.HANDEL = self.ord
        merk = os.path.join(self.ord, "merk.json")
        w.MERK = merk
        import io
        from contextlib import redirect_stdout
        b1, b2 = io.StringIO(), io.StringIO()
        with redirect_stdout(b1):
            w.main()
        with redirect_stdout(b2):
            w.main()
        self.assertNotEqual(b1.getvalue().strip(), "", "der erste Lauf meldet")
        self.assertEqual(b2.getvalue().strip(), "",
                         "der zweite Lauf schweigt - sonst wird die Wache "
                         "abgeschaltet")

    # 4b - und die Gegenprobe dazu
    def test_gegenprobe_ohne_merkdatei_meldet_wieder(self):
        w = lade(WACH, "risiko_wache")
        self.spur("d", [{"inst": "BTC-USDT", "seite": "long", "einstieg": 100.0,
                         "stop": 90.0, "nominal": 1000.0}])
        w.rb.HANDEL = self.ord
        w.MERK = os.path.join(self.ord, "merk2.json")
        import io
        from contextlib import redirect_stdout
        b1, b2 = io.StringIO(), io.StringIO()
        with redirect_stdout(b1):
            w.main()
        os.remove(w.MERK)          # die Merkdatei ist weg
        with redirect_stdout(b2):
            w.main()
        self.assertNotEqual(b2.getvalue().strip(), "",
                            "ohne Merkdatei ist alles neu - das muss melden")


if __name__ == "__main__":
    unittest.main()