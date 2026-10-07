import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_ruecktest as rt  # noqa: E402

VIER_H = 14_400_000


def _aufwaerts(n, start=100.0, schritt=1.0, ts0=0, bar_ms=VIER_H):
    aus = []
    for i in range(n):
        p = start + i * schritt
        aus.append([ts0 + i * bar_ms, p, p * 1.001, p * 0.999, p, 1000.0])
    return aus


class TestSchnittBis(unittest.TestCase):
    def test_schnitt_bis_laesst_zukunft_weg(self):
        k = _aufwaerts(10, ts0=0, bar_ms=1000)
        geschnitten = rt.schnitt_bis(k, zeit_ms=4500)
        self.assertEqual(len(geschnitten), 5)
        self.assertTrue(all(r[0] <= 4500 for r in geschnitten))


class TestRanglisteSchritt(unittest.TestCase):
    def test_zu_kurze_historie_wird_ausgelassen(self):
        universum = [{"instId": "AAA-X", "basis": "AAA", "kategorie": "krypto"}]
        werte = rt.rangliste_schritt(
            universum, {"AAA-X": _aufwaerts(5)}, {"AAA-X": _aufwaerts(5)},
            {"AAA-X": 5_000_000.0}, zeit_ms=4 * VIER_H)
        self.assertEqual(werte, [])

    def test_ausreichende_historie_liefert_punkte_und_familie(self):
        universum = [{"instId": "AAA-X", "basis": "AAA", "kategorie": "krypto"}]
        k4 = _aufwaerts(150)
        k1 = _aufwaerts(60, bar_ms=86_400_000)
        werte = rt.rangliste_schritt(
            universum, {"AAA-X": k4}, {"AAA-X": k1},
            {"AAA-X": 5_000_000.0}, zeit_ms=k4[-1][0])
        self.assertEqual(len(werte), 1)
        self.assertEqual(werte[0]["kategorie"], "krypto")
        self.assertIn("long", werte[0]["punkte"])

    def test_kein_vorgriff_auf_spaetere_kerzen(self):
        universum = [{"instId": "AAA-X", "basis": "AAA", "kategorie": "krypto"}]
        k4 = _aufwaerts(300)
        k1 = _aufwaerts(100, bar_ms=86_400_000)
        fruehe = rt.rangliste_schritt(
            universum, {"AAA-X": k4}, {"AAA-X": k1},
            {"AAA-X": 5_000_000.0}, zeit_ms=k4[149][0])
        # Dieselben Daten, aber die Zukunft hinter 149 wird verfaelscht:
        k4_manip = k4[:150] + [[r[0], 1.0, 1.0, 1.0, 1.0, 1.0] for r in k4[150:]]
        manip = rt.rangliste_schritt(
            universum, {"AAA-X": k4_manip}, {"AAA-X": k1},
            {"AAA-X": 5_000_000.0}, zeit_ms=k4[149][0])
        self.assertEqual(fruehe[0]["punkte"], manip[0]["punkte"])


class TestKandidatenSchritt(unittest.TestCase):
    W = {"familien": {}, "min_umsatz_24h_usd": 3_000_000.0, "max_hebel": 5}

    def _wert(self, **kw):
        w = {"basis": "AAA", "instId": "AAA-X", "kategorie": "krypto",
             "punkte": {"long": 90.0, "short": 10.0, "grid": 0.0},
             "vola": 0.5, "vola_tor": 1.2, "umsatz": 5_000_000.0,
             "mae_long": 0.03, "mae_short": 0.03}
        w.update(kw)
        return w

    def test_vola_ueber_tor_wird_ausgeschlossen(self):
        self.assertEqual(rt.kandidaten_schritt([self._wert(vola=5.0)], self.W), [])

    def test_passender_wert_erscheint_als_long_kandidat(self):
        aus = rt.kandidaten_schritt([self._wert()], self.W)
        longs = [a for a in aus if a["seite"] == "long"]
        self.assertEqual(longs[0]["basis"], "AAA")
        self.assertGreaterEqual(longs[0]["deckel"], 5)

    def test_zu_kleiner_hebel_deckel_schliesst_aus(self):
        self.assertEqual(
            rt.kandidaten_schritt([self._wert(mae_long=0.5, mae_short=0.5)],
                                  self.W), [])

    def test_inaktive_familie_schliesst_aus(self):
        w = dict(self.W, familien={"krypto": {"aktiv": False}})
        self.assertEqual(rt.kandidaten_schritt([self._wert()], w), [])


if __name__ == "__main__":
    unittest.main()
