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

N4 = 160


def _k4():
    return [[i * VIER_H, 100.0, 101.0, 99.0, 100.0, 1000.0] for i in range(N4)]


def _k1d():
    return [[i * 86_400_000, 100.0, 101.0, 99.0, 100.0, 1000.0]
            for i in range(60)]


def _k1h(ab_stunde, kurs_danach):
    """Flache 1H-Reihe; ab 'ab_stunde' faellt/steigt der Kurs auf kurs_danach."""
    aus = []
    for i in range(N4 * 4):
        p = 100.0 if i < ab_stunde else kurs_danach
        aus.append([i * H, 100.0, max(p, 100.0) + 0.01, min(p, 100.0) - 0.01,
                    p, 250.0])
    return aus


def _raster(satz, schritt_h=4):
    return {IID: [[h * H, satz] for h in range(0, N4 * 4, schritt_h)]}


class TestSimuliere(unittest.TestCase):
    def setUp(self):
        for p in (
                mock.patch.object(rt.okxf, "auf_tick",
                                  side_effect=lambda i, x: x),
                mock.patch.object(
                    rt, "rangliste_schritt",
                    return_value=[{"basis": "AAA", "instId": IID,
                                   "kategorie": "krypto",
                                   "punkte": {"long": 90.0, "short": 10.0,
                                              "grid": 0.0},
                                   "vola": 0.5, "vola_tor": 1.2,
                                   "umsatz": 5e6, "mae_long": 0.03,
                                   "mae_short": 0.03}]),
                mock.patch.object(
                    rt.indikatoren, "lage",
                    return_value={"signal": "long", "grund": "T",
                                  "atr": 2.0, "kurs": 100.0}),
                mock.patch.object(rt.bot, "pruefpflicht",
                                  return_value={"traegt": True,
                                                "hebel_traegt": True})):
            p.start()
            self.addCleanup(p.stop)

    def _lauf(self, k1h, w=W, saetze=None, start=100, ende=104):
        return rt.simuliere(
            UNIVERSUM, {IID: _k4()}, {IID: k1h}, {IID: _k1d()},
            saetze or _raster(0.0001), {IID: 5e6}, {"AAA": INSTR}, w,
            start_ms=start * VIER_H, end_ms=ende * VIER_H)

    def test_fallender_kurs_endet_im_stop_mit_verlust(self):
        # Einstieg bei Schritt 100 (Stunde 400), Kurs faellt danach auf 90.
        runden = self._lauf(_k1h(ab_stunde=402, kurs_danach=90.0))
        self.assertGreaterEqual(len(runden), 1)
        r = runden[0]
        self.assertEqual(r["grund"], "stop")
        self.assertLess(r["gv"], 0.0)
        self.assertEqual(r["seite"], "long")
        self.assertGreaterEqual(r["geschlossen_ts"], r["eroeffnet_ts"])

    def test_steigender_kurs_endet_im_ziel_mit_gewinn(self):
        runden = self._lauf(_k1h(ab_stunde=402, kurs_danach=115.0))
        self.assertGreaterEqual(len(runden), 1)
        self.assertEqual(runden[0]["grund"], "ziel")
        self.assertGreater(runden[0]["gv"], 0.0)

    def test_funding_geht_in_das_ergebnis_ein(self):
        # Hoher positiver Satz: Long zahlt - die gv der Runde ist kleiner als
        # ohne Funding, und funding_summe ist positiv.
        mit = self._lauf(_k1h(ab_stunde=420, kurs_danach=115.0),
                         saetze=_raster(0.01), ende=110)
        ohne = self._lauf(_k1h(ab_stunde=420, kurs_danach=115.0),
                          saetze=_raster(0.0), ende=110)
        self.assertGreater(mit[0]["funding_summe"], 0.0)
        self.assertLess(mit[0]["gv"], ohne[0]["gv"])

    def test_fehlende_funding_historie_bricht_laut_ab(self):
        with self.assertRaises(rt.FundingLuecke):
            self._lauf(_k1h(ab_stunde=450, kurs_danach=115.0),
                       saetze={IID: [[10**15, 0.0001]]})

    def test_keine_zwei_gleichzeitigen_positionen_derselben_basis(self):
        # Ein langer, ereignisloser Lauf: das Signal-Wechsel-Gatter und
        # 'bereits offen' lassen genau eine Position zu, nie mehrere.
        sichtungen = []
        original = rt.pruefe_einstieg

        def spion(kand, w, ib, k4, k1d, offene, zustand, t, dt, **kw):
            sichtungen.append(len(offene))
            return original(kand, w, ib, k4, k1d, offene, zustand, t, dt, **kw)

        with mock.patch.object(rt, "pruefe_einstieg", side_effect=spion):
            self._lauf(_k1h(ab_stunde=10_000, kurs_danach=100.0))
        self.assertTrue(all(n <= 1 for n in sichtungen))

    def test_ohne_kerzen_im_fenster_keine_runden(self):
        runden = rt.simuliere(UNIVERSUM, {IID: []}, {IID: []}, {IID: []},
                              {IID: [[0, 0.0001]]}, {IID: 5e6},
                              {"AAA": INSTR}, W, 0, 10 * VIER_H)
        self.assertEqual(runden, [])


    def test_entscheidung_nutzt_nur_abgeschlossene_4h_kerzen(self):
        staende = []
        with mock.patch.object(
                rt, "rangliste_schritt",
                side_effect=lambda u, k4, k1d, um, zeit_ms, **kw: staende.append(
                    zeit_ms) or []):
            self._lauf(_k1h(10_000, 100.0), start=100, ende=102)
        self.assertEqual(staende, [99 * VIER_H, 100 * VIER_H, 101 * VIER_H])

    def test_jede_1h_kerze_wird_hoechstens_einmal_je_position_geprueft(self):
        gesehen = []
        original = rt.pruefe_ausstieg_1h

        def spion(p, kerze, w):
            gesehen.append(kerze[0])
            return original(p, kerze, w)

        with mock.patch.object(rt, "pruefe_ausstieg_1h", side_effect=spion):
            self._lauf(_k1h(10_000, 100.0), start=100, ende=103)
        self.assertEqual(len(gesehen), len(set(gesehen)))
        self.assertTrue(gesehen)

    def test_gebuehr_einstieg_und_ausstieg_stehen_im_ergebnis(self):
        r = self._lauf(_k1h(ab_stunde=402, kurs_danach=115.0))[0]
        brutto = r["nominal"] * (r["ausstieg"] - r["einstieg"]) / r["einstieg"]
        self.assertAlmostEqual(
            r["gv"] + r["funding_summe"],
            brutto - 2 * r["nominal"] * W["gebuehr_taker"], places=6)


if __name__ == "__main__":
    unittest.main()
