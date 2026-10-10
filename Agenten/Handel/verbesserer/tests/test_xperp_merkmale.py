import json
import sys
import unittest
from pathlib import Path
from tempfile import mkdtemp
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_merkmale as xm  # noqa: E402
import xperp_ruecktest as rt  # noqa: E402

S = rt.SCHRITT_MS
UNI = [{"instId": "A-X", "basis": "A", "kategorie": "krypto"}]
K4 = {"A-X": [[i * S, 1.0, 2.0, 0.5, 1.5, 10.0] for i in range(10)]}
K1D = {"A-X": [[i * 86_400_000, 1.0, 2.0, 0.5, 1.5, 10.0] for i in range(5)]}
CT = {"A-X": 1.0}
WERT = [{"instId": "A-X", "punkte": {"long": 1.0, "short": 2.0},
         "mae_long": 0.03}]


class TestStaende(unittest.TestCase):
    def test_raster_ist_t_minus_vier_stunden(self):
        self.assertEqual(xm.staende(10 * S, 12 * S),
                         [9 * S, 10 * S, 11 * S])

    def test_ein_schritt(self):
        self.assertEqual(xm.staende(5 * S, 5 * S), [4 * S])


class TestHash(unittest.TestCase):
    def test_gleiche_daten_gleicher_hash(self):
        a = xm.daten_hash(UNI, K4, K1D, CT, [1, 2])
        b = xm.daten_hash(UNI, K4, K1D, CT, [1, 2])
        self.assertEqual(a, b)

    def test_neue_kerze_andert_den_hash(self):
        k4 = {"A-X": K4["A-X"] + [[10 * S, 1.0, 2.0, 0.5, 1.5, 10.0]]}
        self.assertNotEqual(xm.daten_hash(UNI, K4, K1D, CT, [1, 2]),
                            xm.daten_hash(UNI, k4, K1D, CT, [1, 2]))

    def test_anderer_schlusskurs_andert_den_hash(self):
        k4 = {"A-X": K4["A-X"][:-1] + [[9 * S, 1.0, 2.0, 0.5, 9.9, 10.0]]}
        self.assertNotEqual(xm.daten_hash(UNI, K4, K1D, CT, [1, 2]),
                            xm.daten_hash(UNI, k4, K1D, CT, [1, 2]))

    def test_geaenderte_kerze_in_der_mitte_andert_den_hash(self):
        k4 = {"A-X": [list(k) for k in K4["A-X"]]}
        k4["A-X"][4][4] = 9.9           # Anzahl und Raender bleiben gleich
        self.assertNotEqual(xm.daten_hash(UNI, K4, K1D, CT, [1, 2]),
                            xm.daten_hash(UNI, k4, K1D, CT, [1, 2]))

    def test_anderer_code_stempel_andert_den_hash(self):
        a = xm.daten_hash(UNI, K4, K1D, CT, [1, 2])
        with mock.patch.object(xm, "_code_stempel", return_value="anders"):
            b = xm.daten_hash(UNI, K4, K1D, CT, [1, 2])
        self.assertNotEqual(a, b)

    def test_code_stempel_ist_stabil_und_nicht_leer(self):
        self.assertTrue(xm._code_stempel())
        self.assertEqual(xm._code_stempel(), xm._code_stempel())

    def test_anderes_raster_andert_den_hash(self):
        self.assertNotEqual(xm.daten_hash(UNI, K4, K1D, CT, [1, 2]),
                            xm.daten_hash(UNI, K4, K1D, CT, [1, 2, 3]))

    def test_leeres_instrument_stuerzt_nicht(self):
        xm.daten_hash(UNI, {"A-X": []}, {"A-X": []}, CT, [1])


class TestSpeicher(unittest.TestCase):
    def setUp(self):
        self.pfad = Path(mkdtemp()) / "m.json"

    def test_rundreise_mit_ganzzahligen_schluesseln(self):
        xm.speichern(self.pfad, "h1", {5: WERT, 9: WERT})
        self.assertEqual(xm.laden(self.pfad, "h1"), {5: WERT, 9: WERT})

    def test_falscher_hash_ist_ein_fehlschlag(self):
        xm.speichern(self.pfad, "h1", {5: WERT})
        self.assertIsNone(xm.laden(self.pfad, "h2"))

    def test_fehlende_datei(self):
        self.assertIsNone(xm.laden(self.pfad, "h1"))

    def test_kaputte_datei_ist_ein_fehlschlag_kein_absturz(self):
        self.pfad.write_text("{kaputt", "utf-8")
        self.assertIsNone(xm.laden(self.pfad, "h1"))


class TestHoleOderBaue(unittest.TestCase):
    def setUp(self):
        self.pfad = Path(mkdtemp()) / "m.json"
        self.aufrufe = []

        def fake(universum, k4, k1d, umsatz, stand, ctval_je_inst=None):
            self.aufrufe.append(stand)
            return WERT

        p = mock.patch.object(rt, "rangliste_schritt", side_effect=fake)
        p.start()
        self.addCleanup(p.stop)

    def test_zweiter_aufruf_kommt_aus_dem_cache(self):
        staende = [2 * S, 3 * S]
        m1, aus1 = xm.hole_oder_baue(self.pfad, UNI, K4, K1D, CT, staende)
        self.assertFalse(aus1)
        self.assertEqual(self.aufrufe, staende)
        self.aufrufe.clear()
        m2, aus2 = xm.hole_oder_baue(self.pfad, UNI, K4, K1D, CT, staende)
        self.assertTrue(aus2)
        self.assertEqual(self.aufrufe, [])
        self.assertEqual(m1, m2)

    def test_neue_daten_bauen_neu(self):
        xm.hole_oder_baue(self.pfad, UNI, K4, K1D, CT, [2 * S])
        self.aufrufe.clear()
        k4 = {"A-X": K4["A-X"] + [[10 * S, 1.0, 2.0, 0.5, 1.5, 10.0]]}
        _, aus = xm.hole_oder_baue(self.pfad, UNI, k4, K1D, CT, [2 * S])
        self.assertFalse(aus)
        self.assertEqual(self.aufrufe, [2 * S])

    def test_cache_ohne_alle_staende_wird_neu_gebaut(self):
        xm.hole_oder_baue(self.pfad, UNI, K4, K1D, CT, [2 * S])
        self.aufrufe.clear()
        _, aus = xm.hole_oder_baue(self.pfad, UNI, K4, K1D, CT,
                                   [2 * S, 3 * S])
        self.assertFalse(aus)


class TestCtval(unittest.TestCase):
    def test_ctval_je_instrument(self):
        self.assertEqual(
            xm.ctval_je_inst(UNI, {"A": {"ctVal": "0.1"}}), {"A-X": 0.1})

    def test_instrument_ohne_stammdaten_wird_ausgelassen(self):
        self.assertEqual(xm.ctval_je_inst(UNI, {}), {})


if __name__ == "__main__":
    unittest.main()
