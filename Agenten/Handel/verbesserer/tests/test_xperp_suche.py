import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_suche as xs  # noqa: E402

TAG = 86_400_000
GRENZEN = {
    "stop_atr_faktor": [1.0, 2.5], "ziel_atr_faktor": [2.0, 4.5],
    "einstieg_atr_abschlag": [0.0, 0.5], "trailing_trigger_r": [0.5, 2.0],
    "trailing_stop_prozent": [0.2, 1.0],
    "trailing_abstand_floor_pct": [0.15, 0.6],
    "trailing_min_hub_r": [0.1, 0.6], "trailing_max_halten_pct": [3.0, 8.0],
}
BASIS = {"stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0,
         "einstieg_atr_abschlag": 0.25, "trailing_trigger_r": 1.0,
         "trailing_stop_prozent": 0.4, "trailing_abstand_floor_pct": 0.25,
         "trailing_min_hub_r": 0.25, "trailing_max_halten_pct": 5.0}
KONF = {"such_budget": 60, "such_tage": 90, "test_tage": 15,
        "schritt_tage": 15, "holdout_tage": 20, "holdout_min_runden": 6,
        "overfit_min_fenster": 3, "overfit_min_runden": 20}


def _kz(je_runde, n=30, liq=0.0, ruecklauf=10.0):
    return {"n": n, "gv": je_runde * n, "je_runde": je_runde,
            "liquidationsanteil": liq, "ruecklauf": ruecklauf}


def _ev(fenster_je_runde, gesamt_je_runde=None, **kw):
    gesamt = (gesamt_je_runde if gesamt_je_runde is not None
              else sum(fenster_je_runde) / len(fenster_je_runde))
    return {"fenster": [_kz(x) for x in fenster_je_runde],
            "gesamt": _kz(gesamt, **kw)}


class TestBasisWerte(unittest.TestCase):
    def test_zieht_die_acht_schluessel(self):
        w = {**BASIS, "max_hebel": 5, "handel_erlaubt": True}
        self.assertEqual(xs.basis_werte(w), BASIS)

    def test_fehlender_schluessel_ist_laut(self):
        w = dict(BASIS)
        del w["trailing_min_hub_r"]
        with self.assertRaises(KeyError):
            xs.basis_werte(w)


class TestNachbarn(unittest.TestCase):
    def test_jeder_nachbar_aendert_genau_einen_schluessel_um_einen_schritt(self):
        for n in xs.nachbarn(BASIS, GRENZEN):
            diff = [k for k in BASIS if n[k] != BASIS[k]]
            self.assertEqual(len(diff), 1)
            k = diff[0]
            self.assertAlmostEqual(abs(n[k] - BASIS[k]), xs.SCHRITT[k])

    def test_alle_nachbarn_liegen_in_den_grenzen(self):
        for n in xs.nachbarn(BASIS, GRENZEN):
            for k, (lo, hi) in GRENZEN.items():
                self.assertGreaterEqual(n[k], lo)
                self.assertLessEqual(n[k], hi)

    def test_am_rand_gibt_es_nur_eine_richtung(self):
        rand = {**BASIS, "stop_atr_faktor": 1.0, "ziel_atr_faktor": 2.5}
        stops = [n["stop_atr_faktor"] for n in xs.nachbarn(rand, GRENZEN)
                 if n["stop_atr_faktor"] != 1.0]
        self.assertEqual(stops, [1.25])

    def test_zusatzbedingung_ziel_durch_stop_mindestens_1_5(self):
        eng = {**BASIS, "stop_atr_faktor": 2.0, "ziel_atr_faktor": 3.0}
        for n in xs.nachbarn(eng, GRENZEN):
            self.assertGreaterEqual(
                n["ziel_atr_faktor"] / n["stop_atr_faktor"], 1.5 - 1e-9)
        # stop 2.25 -> 3.0/2.25 = 1.33 -> darf nicht vorkommen
        self.assertNotIn(2.25, [n["stop_atr_faktor"]
                                for n in xs.nachbarn(eng, GRENZEN)])

    def test_keine_gleitkommadrift(self):
        werte = dict(BASIS)
        for _ in range(5):
            werte = [n for n in xs.nachbarn(werte, GRENZEN)
                     if n["einstieg_atr_abschlag"]
                     > werte["einstieg_atr_abschlag"]][0]
        self.assertEqual(werte["einstieg_atr_abschlag"], 0.5)


class TestFenster(unittest.TestCase):
    def test_vier_fenster_und_holdout(self):
        ende = 1000 * TAG
        fenster, holdout = xs.fenster_grenzen(ende, KONF)
        self.assertEqual(len(fenster), 4)
        S = xs.rt.SCHRITT_MS
        self.assertEqual(fenster[0], (910 * TAG, 925 * TAG - S))
        self.assertEqual(fenster[-1], (955 * TAG, 970 * TAG - S))
        self.assertEqual(holdout, (980 * TAG, 1000 * TAG))

    def test_fenster_beruehren_den_holdout_nicht(self):
        # simuliere() rechnet bis einschliesslich end_ms (und schaut 4H
        # weiter): der letzte Schritt muss VOR dem Holdout liegen.
        fenster, holdout = xs.fenster_grenzen(1000 * TAG, KONF)
        self.assertLessEqual(fenster[-1][1] + xs.rt.SCHRITT_MS, holdout[0])

    def test_fenster_ueberlappen_nicht(self):
        fenster, _ = xs.fenster_grenzen(1000 * TAG, KONF)
        for (_, bis), (von, _) in zip(fenster, fenster[1:]):
            self.assertLess(bis, von)
            self.assertLessEqual(bis + xs.rt.SCHRITT_MS, von)

    def test_zu_wenig_rueckblick_gibt_keine_fenster(self):
        fenster, _ = xs.fenster_grenzen(
            1000 * TAG, {**KONF, "such_tage": 30})
        self.assertEqual(fenster, [])


class TestKennzahlen(unittest.TestCase):
    def _runde(self, ts, gv, grund="ziel"):
        return {"geschlossen_ts": ts, "gv": gv, "grund": grund,
                "kategorie": "krypto", "funding_summe": 0.0}

    def test_leer(self):
        self.assertEqual(xs.kennzahlen([]), _kz(0.0, n=0, ruecklauf=0.0))

    def test_werte(self):
        k = xs.kennzahlen([self._runde(1, 10.0),
                           self._runde(2, -4.0, "LIQUIDATION")])
        self.assertEqual(k["n"], 2)
        self.assertAlmostEqual(k["je_runde"], 3.0)
        self.assertAlmostEqual(k["liquidationsanteil"], 0.5)
        self.assertAlmostEqual(k["ruecklauf"], 4.0)

    def test_bewerte_fenster_ruft_je_fenster_und_fasst_zusammen(self):
        aufrufe = []

        def sim(w, von, bis):
            aufrufe.append((von, bis))
            return [self._runde(bis, 2.0)]

        ev = xs.bewerte_fenster(sim, {"x": 1}, [(0, 10), (10, 20)])
        self.assertEqual(aufrufe, [(0, 10), (10, 20)])
        self.assertEqual(len(ev["fenster"]), 2)
        self.assertEqual(ev["gesamt"]["n"], 2)
        self.assertAlmostEqual(ev["gesamt"]["je_runde"], 2.0)


class TestSieb(unittest.TestCase):
    def _regeln(self, basis, kand):
        return {r["regel"]: r for r in xs.sieb_regeln(basis, kand, KONF)}

    def setUp(self):
        self.basis = _ev([1.0, 1.0, 1.0, 1.0], liq=0.1, ruecklauf=100.0)

    def test_alles_bestanden(self):
        kand = _ev([2.0, 2.0, 2.0, 0.5], liq=0.1, ruecklauf=105.0)
        self.assertEqual(xs.sieb(self.basis, kand, KONF), [])

    def test_a_aggregat_nicht_besser(self):
        kand = _ev([2.0, 2.0, 2.0, 0.0], gesamt_je_runde=1.0, liq=0.1,
                   ruecklauf=100.0)
        self.assertFalse(self._regeln(self.basis, kand)["a"]["ok"])

    def test_b_nur_die_haelfte_der_fenster_reicht_nicht(self):
        kand = _ev([2.0, 2.0, 0.5, 0.5], gesamt_je_runde=1.5, liq=0.1,
                   ruecklauf=100.0)
        self.assertFalse(self._regeln(self.basis, kand)["b"]["ok"])

    def test_b_mindestens_overfit_min_fenster(self):
        basis = _ev([1.0, 1.0], liq=0.1, ruecklauf=100.0)
        kand = _ev([2.0, 2.0], liq=0.1, ruecklauf=100.0)   # 2 > 1, aber < 3
        self.assertFalse(self._regeln(basis, kand)["b"]["ok"])

    def test_c_zu_wenige_runden(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=100.0)
        kand["gesamt"]["n"] = 19
        self.assertFalse(self._regeln(self.basis, kand)["c"]["ok"])

    def test_d_mehr_liquidationen_als_die_basis(self):
        kand = _ev([2.0] * 4, liq=0.2, ruecklauf=100.0)
        self.assertFalse(self._regeln(self.basis, kand)["d"]["ok"])

    def test_e_ruecklauf_mehr_als_zehn_prozent_ueber_basis(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=110.5)
        self.assertFalse(self._regeln(self.basis, kand)["e"]["ok"])

    def test_e_basis_ohne_ruecklauf_und_kandidat_mit(self):
        basis = _ev([1.0] * 4, liq=0.1, ruecklauf=0.0)
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=1.0)
        self.assertFalse(self._regeln(basis, kand)["e"]["ok"])

    def test_jede_regel_traegt_ist_und_soll_fuer_den_bericht(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=100.0)
        regeln = xs.sieb_regeln(self.basis, kand, KONF)
        self.assertEqual([r["regel"] for r in regeln],
                         ["a", "b", "c", "d", "e"])
        for r in regeln:
            self.assertTrue(r["ist"] and r["soll"] and r["text"])


class TestAbstieg(unittest.TestCase):
    @staticmethod
    def _bewerter(zaehler):
        def bewerte(werte):
            zaehler.append(dict(werte))
            je = -abs(werte["stop_atr_faktor"] - 1.0)
            return _ev([je] * 4)
        return bewerte

    def test_steigt_zum_besseren_stop_ab(self):
        z = []
        erg = xs.abstieg(BASIS, self._bewerter(z), GRENZEN, 60)
        self.assertEqual(erg["bestes"]["stop_atr_faktor"], 1.0)
        self.assertGreater(erg["bestes_ev"]["gesamt"]["je_runde"],
                           erg["basis_ev"]["gesamt"]["je_runde"])

    def test_budget_deckelt_die_auswertungen(self):
        z = []
        erg = xs.abstieg(BASIS, self._bewerter(z), GRENZEN, 5)
        self.assertLessEqual(erg["auswertungen"], 5)
        self.assertEqual(len(z), erg["auswertungen"])

    def test_kein_satz_wird_zweimal_bewertet(self):
        z = []
        xs.abstieg(BASIS, self._bewerter(z), GRENZEN, 200)
        gesehen = [tuple(sorted(w.items())) for w in z]
        self.assertEqual(len(gesehen), len(set(gesehen)))

    def test_basis_bleibt_wenn_nichts_besser_ist(self):
        def bewerte(werte):
            return _ev([1.0 if werte == BASIS else 0.0] * 4)
        erg = xs.abstieg(BASIS, bewerte, GRENZEN, 60)
        self.assertEqual(erg["bestes"], BASIS)


class TestEntscheide(unittest.TestCase):
    def _lauf(self, kand_ev, holdout_basis, holdout_kand):
        besser = {**BASIS, "stop_atr_faktor": 1.25}

        def bewerte(werte):
            return kand_ev if werte == besser else _ev(
                [1.0] * 4, liq=0.1, ruecklauf=100.0)

        def holdout(werte):
            return holdout_kand if werte == besser else holdout_basis

        # Nachbarn von BASIS: nur 'besser' liefert mehr als die Basis.
        return xs.entscheide(BASIS, bewerte, holdout, GRENZEN, KONF), besser

    def test_kein_besserer_kandidat(self):
        def bewerte(werte):
            return _ev([1.0] * 4)
        erg = xs.entscheide(BASIS, bewerte, lambda w: _kz(1.0), GRENZEN, KONF)
        self.assertIsNone(erg["kandidat"])
        self.assertIsNone(erg["fast_kandidat"])
        self.assertEqual(erg["grund"], "kein besserer Kandidat gefunden")
        self.assertIsNone(erg["holdout_basis"])

    def test_sieb_nicht_bestanden_fasst_den_holdout_nicht_an(self):
        # Aggregat besser, aber nur 2 von 4 Fenstern.
        kand = _ev([3.0, 3.0, 0.5, 0.5], gesamt_je_runde=1.75, liq=0.1,
                   ruecklauf=100.0)
        erg, _ = self._lauf(kand, _kz(1.0), _kz(2.0))
        self.assertIsNone(erg["kandidat"])
        self.assertTrue(erg["grund"].startswith("Sieb nicht bestanden"))
        self.assertIn("b", erg["grund"])
        self.assertIsNone(erg["holdout_basis"])
        self.assertTrue(any(not r["ok"] for r in erg["regeln"]))

    def test_holdout_nicht_bestanden_gibt_fast_kandidat(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=100.0)
        erg, besser = self._lauf(kand, _kz(1.0, n=10), _kz(0.5, n=10))
        self.assertIsNone(erg["kandidat"])
        self.assertEqual(erg["fast_kandidat"], besser)
        self.assertEqual(erg["grund"], "Holdout nicht bestanden")
        self.assertIsNotNone(erg["holdout_basis"])

    def test_holdout_mit_zu_wenigen_runden_scheitert(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=100.0)
        erg, _ = self._lauf(kand, _kz(1.0, n=10), _kz(5.0, n=5))   # < 6
        self.assertIsNone(erg["kandidat"])
        self.assertEqual(erg["grund"], "Holdout nicht bestanden")

    def test_alles_bestanden_gibt_den_vorschlag(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=100.0)
        erg, besser = self._lauf(kand, _kz(1.0, n=10), _kz(2.0, n=10))
        self.assertEqual(erg["kandidat"], besser)
        self.assertIsNone(erg["fast_kandidat"])
        self.assertTrue(erg["grund"].startswith("Vorschlag"))
        self.assertEqual(erg["basis_werte"], BASIS)


if __name__ == "__main__":
    unittest.main()
