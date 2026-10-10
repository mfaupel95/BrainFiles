import sys
import unittest
from pathlib import Path
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_ruecktest as rt  # noqa: E402

H = 3_600_000
VIER_H = 4 * H
IID = "AAA-USD_UM_XPERP-310620"
INSTR = {"instId": IID, "ctVal": "1", "lotSz": "1", "minSz": "1",
         "tickSz": "0.01", "lever": "20"}
UNIVERSUM = [{"instId": IID, "basis": "AAA", "kategorie": "krypto"}]
N4 = 160

W = {"stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0,
     "einstieg_atr_abschlag": 0.0, "wartungsmarge": 0.005,
     "max_margin_je_anlauf_usd": 80.0, "max_margin_gesamt_usd": 600.0,
     "max_hebel": 5, "risiko_je_anlauf_usd": 7.5, "max_offene_anlaeufe": 4,
     "gebuehr_taker": 0.0005, "trigger_modus": "signal",
     "abklingzeit_tage": 3, "freitag_stopp_utc": None, "familien": {},
     "min_umsatz_24h_usd": 3_000_000.0,
     "trailing_stop_prozent": 0.4, "trailing_trigger_r": 1.0,
     "trailing_abstand_floor_pct": 0.25, "trailing_min_hub_r": 0.25,
     "trailing_max_halten_pct": 5.0}

WERTE = [{"basis": "AAA", "instId": IID, "kategorie": "krypto",
          "punkte": {"long": 90.0, "short": 10.0, "grid": 0.0},
          "vola": 0.5, "vola_tor": 1.2, "umsatz": 5e6, "mae_long": 0.03,
          "mae_short": 0.03}]


def _long_pos():
    return {"inst": "AAA-X", "seite": "long", "einstieg": 100.0,
            "stop": 90.0, "ziel": 200.0, "liq": 80.0, "stop_id": "ruecktest",
            "kontrakte": 1}


class TestTrailingSchalter(unittest.TestCase):
    KERZE = [0, 109.0, 111.0, 108.0, 110.0, 1.0]

    def test_aus_zieht_den_stop_nicht_nach(self):
        p = _long_pos()
        rt.pruefe_ausstieg_1h(p, self.KERZE, {**W, "trailing_aktiv": False})
        self.assertEqual(p["stop"], 90.0)
        self.assertNotIn("stop_nachgezogen", p)

    def test_an_zieht_den_stop_nach(self):
        p = _long_pos()
        rt.pruefe_ausstieg_1h(p, self.KERZE, {**W, "trailing_aktiv": True})
        self.assertGreater(p["stop"], 90.0)

    def test_ohne_schluessel_wie_bisher_an(self):
        p = _long_pos()
        rt.pruefe_ausstieg_1h(p, self.KERZE, W)
        self.assertGreater(p["stop"], 90.0)


def _k4():
    return [[i * VIER_H, 100.0, 101.0, 99.0, 100.0, 1000.0] for i in range(N4)]


def _k1d():
    return [[i * 86_400_000, 100.0, 101.0, 99.0, 100.0, 1000.0]
            for i in range(60)]


def _k1h(ab_stunde, kurs_danach):
    aus = []
    for i in range(N4 * 4):
        p = 100.0 if i < ab_stunde else kurs_danach
        aus.append([i * H, 100.0, max(p, 100.0) + 0.01, min(p, 100.0) - 0.01,
                    p, 250.0])
    return aus


def _raster(satz):
    return {IID: [[h * H, satz] for h in range(0, N4 * 4, 4)]}


class TestWerteCache(unittest.TestCase):
    def setUp(self):
        self.aufrufe = []

        def fake_rangliste(*args, **kwargs):
            self.aufrufe.append(args[4])        # der Stand (zeit_ms)
            return WERTE

        for p in (
                mock.patch.object(rt.okxf, "auf_tick",
                                  side_effect=lambda i, x: x),
                mock.patch.object(rt, "rangliste_schritt",
                                  side_effect=fake_rangliste),
                mock.patch.object(
                    rt.indikatoren, "lage",
                    return_value={"signal": "long", "grund": "T",
                                  "atr": 2.0, "kurs": 100.0}),
                mock.patch.object(rt.bot, "pruefpflicht",
                                  return_value={"traegt": True,
                                                "hebel_traegt": True})):
            p.start()
            self.addCleanup(p.stop)

    def _lauf(self, **kw):
        return rt.simuliere(
            UNIVERSUM, {IID: _k4()}, {IID: _k1h(402, 115.0)},
            {IID: _k1d()}, _raster(0.0001), {IID: 5e6}, {"AAA": INSTR}, W,
            start_ms=100 * VIER_H, end_ms=104 * VIER_H, **kw)

    def test_cache_liefert_dieselben_runden_ohne_neuberechnung(self):
        ohne = self._lauf()
        self.assertEqual(len(self.aufrufe), 5)           # Schritte 100..104
        cache = {(t - 1) * VIER_H: WERTE for t in range(100, 105)}
        self.aufrufe.clear()
        mit = self._lauf(werte_cache=cache)
        self.assertEqual(mit, ohne)
        self.assertEqual(self.aufrufe, [])               # nichts neu gerechnet

    def test_fehlender_stand_im_cache_ist_laut(self):
        with self.assertRaises(KeyError):
            self._lauf(werte_cache={})


if __name__ == "__main__":
    unittest.main()
