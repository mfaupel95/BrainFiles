import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_ruecktest as rt  # noqa: E402

INSTR = {"instId": "AAA-USD_UM_XPERP-310620", "ctVal": "1", "lotSz": "1",
         "minSz": "1", "tickSz": "0.01", "lever": "20"}

W = {"stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0,
     "einstieg_atr_abschlag": 0.0, "wartungsmarge": 0.005,
     "max_margin_je_anlauf_usd": 80.0, "max_margin_gesamt_usd": 600.0,
     "max_hebel": 5, "risiko_je_anlauf_usd": 7.5, "max_offene_anlaeufe": 4,
     "gebuehr_taker": 0.0005, "trigger_modus": "signal",
     "abklingzeit_tage": 3, "freitag_stopp_utc": "19:00", "familien": {}}

KANDIDAT = {"basis": "AAA", "instId": INSTR["instId"], "seite": "long",
            "kategorie": "krypto", "punkte": 90.0, "deckel": 10.0}

MITTWOCH = datetime(2026, 6, 3, 12, tzinfo=timezone.utc)
SAMSTAG = datetime(2026, 6, 6, 12, tzinfo=timezone.utc)


def _trend_kerzen(n=150, start=100.0):
    aus = []
    for i in range(n):
        p = start + i * 0.5
        aus.append([i * 14_400_000, p, p * 1.002, p * 0.998, p, 1000.0])
    return aus


class TestPruefeEinstieg(unittest.TestCase):
    def setUp(self):
        self.k4 = _trend_kerzen()
        for ziel, rueck in (
                (rt.indikatoren, mock.patch.object(
                    rt.indikatoren, "lage",
                    return_value={"signal": "long", "grund": "Test",
                                  "atr": 1.0, "kurs": self.k4[-1][4]})),
                (rt.okxf, mock.patch.object(rt.okxf, "funding",
                                            return_value=0.0001))):
            rueck.start()
            self.addCleanup(rueck.stop)
        # Die Pflichtzahlen sind nicht Gegenstand dieser Tests - sie laufen
        # in Task 8 gegen echte Kerzen. Hier: Pflichtzahlen tragen.
        p = mock.patch.object(rt.bot, "pruefpflicht",
                              return_value={"traegt": True, "hebel_traegt": True})
        p.start()
        self.addCleanup(p.stop)

    def _einstieg(self, kand=KANDIDAT, offen=(), zustand=None, jetzt=MITTWOCH,
                  w=W):
        return rt.pruefe_einstieg(
            kand, w, {"AAA": INSTR}, {INSTR["instId"]: self.k4}, {},
            list(offen), {} if zustand is None else zustand,
            zeit_ms=self.k4[-1][0], jetzt_dt=jetzt)

    def test_erfolgreicher_einstieg_liefert_position_mit_stop_id(self):
        p = self._einstieg()
        self.assertIsNotNone(p)
        self.assertEqual(p["seite"], "long")
        self.assertTrue(p["stop_id"])
        self.assertLess(p["stop"], p["einstieg"])
        self.assertLess(p["liq"], p["stop"])

    def test_short_spiegelt_stop_ziel_liquidation(self):
        with mock.patch.object(
                rt.indikatoren, "lage",
                return_value={"signal": "short", "grund": "T", "atr": 1.0,
                              "kurs": self.k4[-1][4]}):
            p = self._einstieg(kand=dict(KANDIDAT, seite="short"))
        self.assertIsNotNone(p)
        self.assertGreater(p["stop"], p["einstieg"])
        self.assertGreater(p["liq"], p["stop"])
        self.assertLess(p["ziel"], p["einstieg"])

    def test_platzlimit_blockt_einstieg(self):
        voll = [{"basis": "X%d" % i, "margin": 1.0}
                for i in range(W["max_offene_anlaeufe"])]
        self.assertIsNone(self._einstieg(offen=voll))

    def test_signal_wechsel_gatter_blockt_gleiche_richtung(self):
        self.assertIsNone(self._einstieg(zustand={"vor_signal": {"AAA": "long"}}))

    def test_signal_wechsel_gatter_laesst_richtungswechsel_zu(self):
        self.assertIsNotNone(
            self._einstieg(zustand={"vor_signal": {"AAA": "short"}}))

    def test_bereits_offen_fuer_diese_basis(self):
        self.assertIsNone(self._einstieg(offen=[{"basis": "AAA", "margin": 1.0}]))

    def test_abklingzeit_nach_stop(self):
        zustand = {"letzte_stops": {"AAA": datetime(2026, 6, 2, tzinfo=timezone.utc)}}
        self.assertIsNone(self._einstieg(zustand=zustand))

    def test_abklingzeit_abgelaufen_laesst_zu(self):
        zustand = {"letzte_stops": {"AAA": datetime(2026, 5, 20, tzinfo=timezone.utc)}}
        self.assertIsNotNone(self._einstieg(zustand=zustand))

    def test_wochenende_sperrt_aktie_nicht_krypto(self):
        self.assertIsNone(self._einstieg(
            kand=dict(KANDIDAT, kategorie="aktie"), jetzt=SAMSTAG))
        self.assertIsNotNone(self._einstieg(jetzt=SAMSTAG))

    def test_gesamt_margin_deckel(self):
        belegt = [{"basis": "B", "margin": 599.0}]
        self.assertIsNone(self._einstieg(offen=belegt))

    def test_pflichtzahlen_tragen_nicht_blockt(self):
        with mock.patch.object(rt.bot, "pruefpflicht",
                               return_value={"traegt": False,
                                             "hebel_traegt": True}):
            self.assertIsNone(self._einstieg())

    def test_signal_widerspricht_kandidat(self):
        with mock.patch.object(
                rt.indikatoren, "lage",
                return_value={"signal": "short", "grund": "T", "atr": 1.0,
                              "kurs": self.k4[-1][4]}):
            self.assertIsNone(self._einstieg())

    def test_satz_bis_leitet_pruefpflicht_funding_auf_historischen_satz_um(self):
        gesehen = []

        def pflicht(*a, **k):
            gesehen.append(rt.okxf.funding(INSTR["instId"]))
            return {"traegt": True, "hebel_traegt": True}

        with mock.patch.object(rt.bot, "pruefpflicht", side_effect=pflicht):
            rt.pruefe_einstieg(
                KANDIDAT, W, {"AAA": INSTR}, {INSTR["instId"]: self.k4}, {},
                [], {}, zeit_ms=self.k4[-1][0], jetzt_dt=MITTWOCH,
                satz_bis=lambda inst, t: 0.0042)
        self.assertEqual(gesehen, [0.0042])
        # Nach dem Aufruf ist die echte Funktion wiederhergestellt.
        self.assertEqual(rt.okxf.funding(INSTR["instId"]), 0.0001)

    def test_tages_kerzen_seam_wird_nach_dem_aufruf_zurueckgesetzt(self):
        vorher = rt.bot.tages_kerzen_quelle
        self._einstieg()
        self.assertIs(rt.bot.tages_kerzen_quelle, vorher)


class TestFix3Und7(unittest.TestCase):
    def setUp(self):
        self.k4 = _trend_kerzen(600)
        for rueck in (
                mock.patch.object(rt.okxf, "funding", return_value=0.0001),
                mock.patch.object(rt.bot, "pruefpflicht",
                                  return_value={"traegt": True,
                                                "hebel_traegt": True})):
            rueck.start()
            self.addCleanup(rueck.stop)

    def _lauf(self, kand=KANDIDAT):
        gesehen = []

        def lage(k, **kw):
            gesehen.append(len(k))
            return {"signal": kand["seite"], "grund": "T", "atr": 1.0,
                    "kurs": self.k4[-1][4]}

        with mock.patch.object(rt.indikatoren, "lage", side_effect=lage):
            p = rt.pruefe_einstieg(
                kand, W, {"AAA": INSTR}, {INSTR["instId"]: self.k4}, {}, [],
                {}, zeit_ms=self.k4[-1][0], jetzt_dt=MITTWOCH)
        return p, gesehen

    def test_signal_sieht_hoechstens_300_kerzen_wie_live(self):
        p, gesehen = self._lauf()
        self.assertIsNotNone(p)
        self.assertEqual(gesehen, [300])

    def test_position_traegt_familie_fuer_den_familiendeckel(self):
        p, _ = self._lauf(dict(KANDIDAT, kategorie="aktie"))
        self.assertEqual(p["familie"], "aktie")
        w = dict(W, familien={"aktie": {"max_anteil_gesamt": 0.5}})
        belegung = rt.wx.familien_belegung([p], w)
        self.assertAlmostEqual(belegung["aktie"]["margin"], p["margin"])


if __name__ == "__main__":
    unittest.main()
