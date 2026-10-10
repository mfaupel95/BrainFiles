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

    def test_familie_mit_hoeherer_grenze_laesst_ab_globalem_hebel_zu(self):
        # Wie live (handeln.kandidaten): rohstoff max_hebel 10 ist Obergrenze,
        # zugelassen wird ab dem globalen max_hebel 5 (Auftrag Max 10.10.2026).
        w = dict(self.W, familien={"rohstoff": {"max_hebel": 10}})
        aus = rt.kandidaten_schritt(
            [self._wert(kategorie="rohstoff", mae_long=0.13, mae_short=0.13)], w)
        self.assertTrue(aus)
        self.assertTrue(all(5 <= a["deckel"] < 10 for a in aus))

    def test_inaktive_familie_schliesst_aus(self):
        w = dict(self.W, familien={"krypto": {"aktiv": False}})
        self.assertEqual(rt.kandidaten_schritt([self._wert()], w), [])


class TestFix1TagesKerzeLaeuft(unittest.TestCase):
    def test_laufende_tageskerze_geht_nicht_in_mae_ein(self):
        universum = [{"instId": "AAA-X", "basis": "AAA", "kategorie": "krypto"}]
        k4 = _aufwaerts(150)
        zeit = k4[149][0]                       # 24,83 Tage
        k1d = [[d * 86_400_000, 100.0, 101.0, 99.0, 100.0, 1.0] for d in range(60)]
        # Die Kerze des Tages 24 (ts 24d <= zeit) laeuft noch: ihr Tief liegt
        # in der Zukunft von 'zeit'.
        k1d[24] = [24 * 86_400_000, 100.0, 101.0, 10.0, 50.0, 1.0]
        werte = rt.rangliste_schritt(universum, {"AAA-X": k4}, {"AAA-X": k1d},
                                     {"AAA-X": 5e6}, zeit)
        self.assertLess(werte[0]["mae_long"], 0.05)


class TestFix3Fenster300(unittest.TestCase):
    def test_kennzahlen_sehen_hoechstens_300_kerzen(self):
        from unittest import mock
        universum = [{"instId": "AAA-X", "basis": "AAA", "kategorie": "krypto"}]
        k4 = _aufwaerts(600)
        gesehen = []
        original = rt.auswahl.kennzahlen
        with mock.patch.object(rt.auswahl, "kennzahlen",
                               side_effect=lambda k: gesehen.append(len(k))
                               or original(k)):
            rt.rangliste_schritt(universum, {"AAA-X": k4}, {"AAA-X": []},
                                 {"AAA-X": 5e6}, k4[-1][0])
        self.assertEqual(gesehen, [300])


class TestFix4UmsatzPunktInZeit(unittest.TestCase):
    def test_umsatz_kommt_aus_den_letzten_24h_kerzen(self):
        universum = [{"instId": "AAA-X", "basis": "AAA", "kategorie": "krypto"}]
        k4 = [[i * VIER_H, 100.0, 100.1, 99.9, 100.0, 100.0] for i in range(150)]
        werte = rt.rangliste_schritt(
            universum, {"AAA-X": k4}, {"AAA-X": []}, {"AAA-X": 999.0},
            k4[-1][0], ctval_je_inst={"AAA-X": 2.0})
        # 6 Kerzen * 100 Kontrakte * ctVal 2 * Kurs 100
        self.assertAlmostEqual(werte[0]["umsatz"], 120_000.0)


if __name__ == "__main__":
    unittest.main()
