"""Tests: Hebel und Stopweite je Familie (Auftrag Max 08.10.2026).

Rohstoffe (XAU, XAG, CL, BZ) laufen mit 10x und hoechstens 4 % Stop; alle
anderen Familien behalten das globale max_hebel (5). Geprueft wird die Kette
wachen.json -> wachen_xperp -> handeln.kandidaten()/anlauf() -> bot.groesse(),
ohne Netz (OKX-Zugriffe sind ersetzt).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parents[0]
for p in (HANDEL / "scanner", HANDEL, SPUR):
    if str(p) in sys.path:
        sys.path.remove(str(p))
    sys.path.insert(0, str(p))

import handeln as h                                                 # noqa: E402
import wachen_xperp as wx                                           # noqa: E402

assert str(Path(h.__file__).resolve()).startswith(str(SPUR)), h.__file__

WACHEN = json.loads((SPUR / "wachen.json").read_text(encoding="utf-8"))


class GrenzenTest(unittest.TestCase):
    def test_rohstoff_hat_eigene_grenze(self):
        self.assertEqual(wx.hebel_grenze(WACHEN, "rohstoff"), 10.0)
        self.assertEqual(wx.stop_max_pct(WACHEN, "rohstoff"), 4.0)

    def test_andere_familien_behalten_globalen_hebel(self):
        for fam in ("krypto", "aktie", "unbekannt"):
            self.assertEqual(wx.hebel_grenze(WACHEN, fam), float(WACHEN["max_hebel"]), fam)
            self.assertIsNone(wx.stop_max_pct(WACHEN, fam), fam)

    def test_globaler_hebel_unveraendert(self):
        self.assertEqual(WACHEN["max_hebel"], 5)

    def test_fuer_familie_veraendert_das_original_nicht(self):
        kopie = wx.fuer_familie(WACHEN, "rohstoff")
        self.assertEqual(kopie["max_hebel"], 10.0)
        self.assertEqual(WACHEN["max_hebel"], 5)
        self.assertIsNot(kopie, WACHEN)


def _wert(basis, kategorie, mae):
    return {"basis": basis, "instId": basis + "-USD_UM_XPERP", "kategorie": kategorie,
            "punkte": {"long": 10.0, "short": 0.0}, "vola": 0.2, "vola_tor": 5.0,
            "umsatz": 50_000_000, "mae_long": mae, "mae_short": mae}


class KandidatenTest(unittest.TestCase):
    def test_rohstoff_mit_deckel_zwischen_5_und_10_kommt_durch(self):
        # Auftrag Max 10.10.2026: "darf auch weniger, aber so hoch wie
        # moeglich" - 10x ist Obergrenze, zugelassen wird ab dem globalen
        # max_hebel (5); der Hebel selbst ist dann min(10, Deckel).
        mae = 0.13
        deckel = h.auswahl.hebel_deckel(mae)
        self.assertTrue(5 <= deckel < 10, deckel)
        werte = [_wert("XAU", "rohstoff", mae), _wert("BTC", "krypto", mae)]
        basen = [k["basis"] for k in h.kandidaten(werte, WACHEN)]
        self.assertIn("BTC", basen)
        self.assertIn("XAU", basen)

    def test_rohstoff_unter_globalem_hebel_faellt_weiter_raus(self):
        mae = 0.25
        self.assertLess(h.auswahl.hebel_deckel(mae), WACHEN["max_hebel"])
        basen = [k["basis"] for k in h.kandidaten([_wert("XAU", "rohstoff", mae)], WACHEN)]
        self.assertEqual(basen, [])

    def test_hebel_mindest_ist_globaler_hebel_fuer_alle_familien(self):
        for fam in ("rohstoff", "krypto", "aktie", "unbekannt"):
            self.assertEqual(wx.hebel_mindest(WACHEN, fam), float(WACHEN["max_hebel"]), fam)

    def test_rohstoff_mit_tragfaehigem_deckel_kommt_durch(self):
        mae = 0.05
        self.assertGreaterEqual(h.auswahl.hebel_deckel(mae), 10)
        basen = [k["basis"] for k in h.kandidaten([_wert("XAU", "rohstoff", mae)], WACHEN)]
        self.assertEqual(set(basen), {"XAU"})


class AnlaufTest(unittest.TestCase):
    """anlauf() mit ersetzten OKX-Zugriffen; atr steuert die Stopweite."""

    def _anlauf(self, kategorie, atr, deckel=20.0):
        w = dict(WACHEN, einstieg_atr_abschlag=0.0, stop_atr_faktor=1.0, ziel_atr_faktor=2.0)
        instr = {"instId": "XAU-USD_UM_XPERP-310502", "ctVal": 1.0}
        lage = {"signal": "long", "atr": atr, "kurs": 1000.0, "grund": "test"}
        gesehen = {}

        def pruef(wf, *a, **kw):
            gesehen["max_hebel"] = wf["max_hebel"]
            return {"traegt": True, "hebel_traegt": True}

        patches = [
            mock.patch.object(h.okxf, "instrument", lambda basis: instr),
            mock.patch.object(h.okxf, "kerzen", lambda *a, **k: [[0, 1, 1, 1, 1, 1]] * 80),
            mock.patch.object(h.okxf, "auf_tick", lambda i, p: p),
            mock.patch.object(h.okxf, "kontrakte_aus_nominal",
                              lambda i, nominal, einstieg: (nominal / einstieg, nominal)),
            mock.patch.object(h.indikatoren, "lage", lambda k, inst=None: lage),
            mock.patch.object(h.bot, "pruefpflicht", pruef),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        a = h.anlauf(w, {"basis": "XAU", "kategorie": kategorie, "seite": "long",
                         "deckel": deckel, "punkte": 10.0})
        return a, gesehen

    def test_rohstoff_stop_3_prozent_geht_mit_10x(self):
        a, gesehen = self._anlauf("rohstoff", atr=30.0)            # 3 % Stop
        self.assertIsNotNone(a)
        self.assertEqual(a["groesse"]["hebel"], 10.0)
        self.assertEqual(gesehen["max_hebel"], 10.0)

    def test_rohstoff_stop_ueber_4_prozent_entfaellt(self):
        a, _ = self._anlauf("rohstoff", atr=50.0)                  # 5 % Stop
        self.assertIsNone(a)

    def test_rohstoff_stop_genau_an_der_grenze_zaehlt_noch(self):
        a, _ = self._anlauf("rohstoff", atr=40.0)                  # 4 % Stop
        self.assertIsNotNone(a)

    def test_krypto_bleibt_bei_5x_und_ohne_stopgrenze(self):
        a, gesehen = self._anlauf("krypto", atr=50.0)              # 5 % Stop, keine Familiengrenze
        self.assertIsNotNone(a)
        self.assertEqual(a["groesse"]["hebel"], 5.0)
        self.assertEqual(gesehen["max_hebel"], 5)

    def test_hebel_nie_ueber_dem_volatilitaetsdeckel(self):
        a, _ = self._anlauf("rohstoff", atr=30.0, deckel=7.0)
        self.assertIsNotNone(a)
        self.assertEqual(a["groesse"]["hebel"], 7.0)

    def test_risiko_bleibt_konstant_hebel_aendert_nur_die_margin(self):
        a10, _ = self._anlauf("rohstoff", atr=30.0)
        a5, _ = self._anlauf("krypto", atr=30.0)
        self.assertAlmostEqual(a10["groesse"]["risiko"], a5["groesse"]["risiko"], places=6)
        self.assertAlmostEqual(a10["groesse"]["margin"] * 2, a5["groesse"]["margin"], places=6)


class AnfrageTextTest(unittest.TestCase):
    def test_freigabeanfrage_nennt_die_rohstoffgrenze(self):
        import freigabefenster as ff
        zeilen = dict(ff.grenzwerte(WACHEN))
        self.assertIn("Hebel bis", zeilen)
        self.assertIn("5", zeilen["Hebel bis"])
        self.assertIn("Hebel bis (rohstoff)", zeilen)
        self.assertIn("10", zeilen["Hebel bis (rohstoff)"])
        self.assertIn("4", zeilen["Hebel bis (rohstoff)"])


if __name__ == "__main__":
    unittest.main()
