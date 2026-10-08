import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_ruecktest as rt  # noqa: E402


def _runde(gv, grund, kategorie="krypto", funding=0.0, geschlossen=1000):
    return {"inst": "AAA-X", "basis": "AAA", "seite": "long",
            "kategorie": kategorie, "einstieg": 100.0, "ausstieg": 100.0,
            "grund": grund, "gv": gv, "funding_summe": funding,
            "eroeffnet_ts": 0, "geschlossen_ts": geschlossen}


class TestBericht(unittest.TestCase):
    def test_leere_rundenliste(self):
        b = rt.bericht([])
        self.assertEqual(b["anzahl_runden"], 0)
        self.assertEqual(b["gv_gesamt"], 0.0)

    def test_summen_und_zaehlung_je_grund(self):
        b = rt.bericht([_runde(10.0, "ziel"), _runde(-5.0, "stop"),
                        _runde(-20.0, "LIQUIDATION")])
        self.assertEqual(b["anzahl_runden"], 3)
        self.assertAlmostEqual(b["gv_gesamt"], -15.0)
        self.assertEqual(b["runden_je_grund"],
                         {"ziel": 1, "stop": 1, "LIQUIDATION": 1})

    def test_je_familie_aufgeschluesselt(self):
        b = rt.bericht([_runde(10.0, "ziel"),
                        _runde(5.0, "ziel", kategorie="aktie")])
        self.assertEqual(b["je_familie"]["krypto"]["n"], 1)
        self.assertEqual(b["je_familie"]["aktie"]["gv"], 5.0)

    def test_funding_anteil_am_gesamtergebnis(self):
        b = rt.bericht([_runde(10.0, "ziel", funding=2.0),
                        _runde(-1.0, "stop", funding=-0.5)])
        self.assertAlmostEqual(b["funding_gesamt"], 1.5)

    def test_groesster_ruecklauf_nach_schliesszeit_sortiert(self):
        runden = [_runde(5.0, "ziel", geschlossen=3),
                  _runde(10.0, "ziel", geschlossen=1),
                  _runde(-30.0, "stop", geschlossen=2)]
        # Kurve nach Zeit: 10 -> -20 -> -15, Hoechststand 10, Tief -20.
        self.assertAlmostEqual(rt.bericht(runden)["groesster_ruecklauf_usd"], 30.0)

    def test_kein_ruecklauf_bei_nur_gewinnen(self):
        b = rt.bericht([_runde(1.0, "ziel", geschlossen=1),
                        _runde(2.0, "ziel", geschlossen=2)])
        self.assertEqual(b["groesster_ruecklauf_usd"], 0.0)

    def test_liquidationsanteil_wird_ausgewiesen(self):
        b = rt.bericht([_runde(-20.0, "LIQUIDATION"), _runde(5.0, "ziel")])
        self.assertAlmostEqual(b["liquidationsanteil"], 0.5)

    def test_trefferquote_ziel_gegen_stop_und_liquidation(self):
        b = rt.bericht([_runde(5.0, "ziel"), _runde(5.0, "ziel"),
                        _runde(-5.0, "stop"), _runde(-9.0, "LIQUIDATION")])
        self.assertAlmostEqual(b["trefferquote"], 0.5)



class TestZeitfenster(unittest.TestCase):
    def test_fenster_endet_am_juengsten_datenpunkt(self):
        k = {"A": [[0, 1, 1, 1, 1, 1], [86_400_000 * 10, 1, 1, 1, 1, 1]],
             "B": [[0, 1, 1, 1, 1, 1], [86_400_000 * 8, 1, 1, 1, 1, 1]]}
        start, ende = rt.zeitfenster(k, tage=4)
        self.assertEqual(ende, 86_400_000 * 10)
        self.assertEqual(start, 86_400_000 * 6)

    def test_ohne_daten_ist_das_fenster_leer(self):
        self.assertEqual(rt.zeitfenster({"A": []}, tage=4), (0, -1))


class TestGewinnquote(unittest.TestCase):
    def test_gewinnquote_zaehlt_positive_runden_auch_ueber_trailing_stop(self):
        b = rt.bericht([_runde(5.0, "ziel"), _runde(2.0, "trailing_stop"),
                        _runde(-5.0, "stop"), _runde(-9.0, "LIQUIDATION")])
        self.assertAlmostEqual(b["gewinnquote"], 0.5)
        self.assertAlmostEqual(b["trefferquote"], 0.25)


if __name__ == "__main__":
    unittest.main()
