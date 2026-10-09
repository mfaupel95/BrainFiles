"""Tests fuer limits_backtest.portfolio - jede Bremse einzeln, kuenstliche Daten, ohne Netz."""

import importlib.util
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("lim_modul", os.path.join(HIER, "..", "limits_backtest.py"))
lim = importlib.util.module_from_spec(spec)
sys.modules["lim_modul"] = lim
spec.loader.exec_module(lim)

BAR = lim.BAR_MS
AUS = dict(plaetze=False, vf_usd=False, vf_pct=False, halbierung=False, kill=None)


def kerzen(n=400, preis=100.0):
    return [[i * BAR, preis, preis, preis, preis, 1.0] for i in range(n)]


def cfg(**kw):
    c = {"risiko": 5.0, "pct": 2.5, "max_pos": 3, "max_trade": 350.0, "fenster_ms": 12 * 3600 * 1000,
         "v_usd": 25.0, "g_usd": 25.0, "v_pct": 5.0, "g_pct": 5.0, "halb": 15.0, "kill": 45.0,
         "frist_ms": 168 * 3600 * 1000, "gebuehr": 0.0, "vorfilter_an": True}
    c.update(kw)
    return c


def daten(**inst):
    """inst: name -> {signal_bar: (dauer_bars, r)}"""
    out = {}
    for name, sigs in inst.items():
        out[name] = {"k": kerzen(), "sigs": set(sigs),
                     "ausgang": (lambda i, s=sigs: (i + s[i][0], s[i][1]))}
    return out


def regeln(**kw):
    r = dict(AUS)
    r.update(kw)
    return r


class GrundTest(unittest.TestCase):
    def test_summe_ohne_limits(self):
        e = lim.portfolio(cfg(), daten(A={1: (4, 2.0), 10: (4, -1.0)}), regeln())
        self.assertAlmostEqual(e["usd"], 5.0)               # 5 USD je R: (2 - 1) x 5
        self.assertEqual(e["einstiege"], 2)

    def test_eine_position_je_instrument(self):
        e = lim.portfolio(cfg(), daten(A={1: (8, 1.0), 3: (4, 1.0)}), regeln())
        self.assertEqual(e["einstiege"], 1)                 # Signal bei 3 trifft die offene Position

    def test_plaetze(self):
        d = daten(A={1: (20, 1.0)}, B={1: (20, 1.0)}, C={1: (20, 1.0)})
        self.assertEqual(lim.portfolio(cfg(max_pos=2), d, regeln(plaetze=True))["einstiege"], 2)
        self.assertEqual(lim.portfolio(cfg(max_pos=2), d, regeln(plaetze=False))["einstiege"], 3)

    def test_wieder_einstieg_im_selben_balken_nach_ausstieg(self):
        # Ausstieg und neues Signal im gleichen Balken: erst Ausstieg, dann Einstieg (Reihenfolge wie zyklus)
        e = lim.portfolio(cfg(), daten(A={1: (4, 1.0), 5: (4, 1.0)}), regeln())
        self.assertEqual(e["einstiege"], 2)


class VorfilterTest(unittest.TestCase):
    def test_verlust_usd_sperrt_neue_einstiege(self):
        d = daten(A={1: (1, -1.0)}, B={1: (1, -1.0)}, C={4: (4, 1.0)}, D={30: (4, 1.0)})
        e = lim.portfolio(cfg(v_usd=10.0), d, regeln(vf_usd=True))
        self.assertEqual(e["blockiert"].get("Vorfilter Verlust USD"), 1)       # C im 12h-Fenster
        self.assertEqual(e["einstiege"], 3)                                    # D nach dem Fenster wieder frei

    def test_gewinn_usd_sperrt(self):
        d = daten(A={1: (1, 6.0)}, B={4: (4, 1.0)})                            # +30 USD >= 25
        e = lim.portfolio(cfg(), d, regeln(vf_usd=True))
        self.assertEqual(e["blockiert"].get("Vorfilter Gewinn USD"), 1)

    def test_verlust_prozent_bei_stop_5_prozent(self):
        d = daten(A={1: (1, -1.0)}, B={4: (4, 1.0)})
        e5 = lim.portfolio(cfg(pct=5.0), d, regeln(vf_pct=True))               # -5 % des Einsatzes
        e25 = lim.portfolio(cfg(pct=2.5), d, regeln(vf_pct=True))              # nur -2,5 %
        self.assertEqual(e5["blockiert"].get("Vorfilter Verlust %"), 1)
        self.assertNotIn("Vorfilter Verlust %", e25["blockiert"])

    def test_gewinn_prozent_2r_bei_stop_2_5(self):
        d = daten(A={1: (1, 2.0)}, B={4: (4, 1.0)})                            # +5 %
        e = lim.portfolio(cfg(pct=2.5), d, regeln(vf_pct=True))
        self.assertEqual(e["blockiert"].get("Vorfilter Gewinn %"), 1)

    def test_vorfilter_aus_wenn_wache_ihn_nicht_setzt(self):
        d = daten(A={1: (1, -1.0)}, B={1: (1, -1.0)}, C={4: (4, 1.0)})
        e = lim.portfolio(cfg(v_usd=10.0, vorfilter_an=False), d, regeln(vf_usd=True))
        self.assertEqual(e["blockiert"], {})


class HalbierungTest(unittest.TestCase):
    def test_halbe_groesse_nach_ruecklauf(self):
        # zwei Verluste (-10 USD) mit Schwelle 10 -> naechste Position halb: +1R = +2,5 statt +5 USD
        d = daten(A={1: (1, -1.0)}, B={1: (1, -1.0)}, C={30: (4, 1.0)})
        halb = lim.portfolio(cfg(halb=10.0), d, regeln(halbierung=True))
        voll = lim.portfolio(cfg(halb=10.0), d, regeln(halbierung=False))
        self.assertAlmostEqual(voll["usd"], -10.0 + 5.0)
        self.assertAlmostEqual(halb["usd"], -10.0 + 2.5)


class KillTest(unittest.TestCase):
    BASIS = {1: (1, -1.0), 3: (1, -1.0)}                                       # zwei Verluste -> Ruecklauf 10

    def test_implementiert_ist_dauerhaft(self):
        # Verluste schliessen bei Balken 2 und 4 (Ruecklauf 10 = Schwelle). Der Kill greift am Anfang
        # von Balken 5; die Frist (42 Balken) endet bei Balken 47 - genau dort laeuft EIN Zyklus frei.
        sigs = dict(self.BASIS)
        sigs[47] = (3, 2.0)                                  # im freien Zyklus: wird eroeffnet ...
        for b in (60, 70, 120, 200, 300):
            sigs[b] = (3, 2.0)                               # ... danach nie wieder gebucht
        e = lim.portfolio(cfg(kill=10.0), daten(A=sigs), regeln(kill="implementiert"))
        self.assertAlmostEqual(e["usd"], -10.0)              # NICHTS wird je wieder gebucht
        self.assertEqual(e["einstiege"], 3)                  # 2 Verlust-Runden + Balken 47 (freier Zyklus); der naechste liegt bei 90
        self.assertGreaterEqual(e["kills"], 2)               # Kill wird immer wieder neu ausgeloest
        self.assertGreaterEqual(e["ungebucht"], 1)           # die Position des freien Zyklus wird verworfen

    def test_gemeint_handelt_nach_der_frist_weiter(self):
        sigs = dict(self.BASIS)
        for b in (60, 70, 80):
            sigs[b] = (3, 2.0)
        e = lim.portfolio(cfg(kill=10.0), daten(A=sigs), regeln(kill="gemeint"))
        self.assertGreater(e["usd"], -10.0)                 # Gewinne werden wieder gebucht
        self.assertEqual(e["kills"], 1)

    def test_kill_loescht_offene_position_ohne_buchung(self):
        # A oeffnet bei Balken 2 (langer Trade); die beiden Verluste von B und C schliessen bei 2 und 4.
        # Beim Kill (Anfang Balken 5) ist A offen und wird OHNE Buchung geloescht.
        sigs = {2: (30, 4.0)}
        d = daten(A=sigs, B={1: (1, -1.0)}, C={3: (1, -1.0)})
        e = lim.portfolio(cfg(kill=10.0), d, regeln(kill="implementiert"))
        self.assertAlmostEqual(e["usd"], -10.0)
        self.assertEqual(e["ungebucht"], 1)

    def test_gemeint_bucht_die_offene_position_zum_marktkurs(self):
        sigs = {2: (30, 4.0)}
        d = daten(A=sigs, B={1: (1, -1.0)}, C={3: (1, -1.0)})
        e = lim.portfolio(cfg(kill=10.0), d, regeln(kill="gemeint"))
        self.assertEqual(e["ungebucht"], 0)
        self.assertEqual(e["runden"], 3)                      # B, C und A (zum Kurs 100 = Einstand, nur Gebuehr 0)

    def test_ohne_kill_stufe_kein_kill(self):
        e = lim.portfolio(cfg(kill=10.0), daten(A=dict(self.BASIS)), regeln(kill=None))
        self.assertEqual(e["kills"], 0)


class KonfigTest(unittest.TestCase):
    def test_konfig_aus_echten_wachen(self):
        import json
        w = json.load(open(os.path.join(HIER, "..", "klassik_ema", "wachen.json"), encoding="utf-8"))
        c = lim.konfig(w)
        self.assertEqual((c["risiko"], c["max_pos"], c["halb"], c["kill"]),
                         (5.0, 3, 15.0, float(w["kill_switch_gesamt_usd"])))
        self.assertAlmostEqual(c["pct"], 2.5)
        self.assertTrue(c["vorfilter_an"])


if __name__ == "__main__":
    unittest.main()


class RollingStartTest(unittest.TestCase):
    def test_start_ms_ueberspringt_frueheres(self):
        sigs = {1: (1, -1.0), 3: (1, -1.0), 60: (3, 2.0)}
        d = daten(A=sigs)
        ab_start = lim.portfolio(cfg(), d, regeln(), start_ms=50 * BAR)
        self.assertEqual(ab_start["einstiege"], 1)                       # nur das Signal bei 60
        self.assertAlmostEqual(ab_start["usd"], 10.0)

    def test_frisches_buch_ruecklauf_beginnt_bei_null(self):
        # die Verluste VOR dem Start zaehlen nicht in den Ruecklauf des frischen Buchs
        sigs = {1: (1, -1.0), 3: (1, -1.0), 60: (3, 2.0), 70: (3, 2.0)}
        e = lim.portfolio(cfg(kill=10.0), daten(A=sigs), regeln(kill="implementiert"), start_ms=50 * BAR)
        self.assertEqual(e["kills"], 0)
        self.assertEqual(e["einstiege"], 2)
