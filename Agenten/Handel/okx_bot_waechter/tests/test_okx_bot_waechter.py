"""Tests fuer den OKX-Bot-Waechter - ohne Netz, ohne echte Dateien.

Alle Boersenwege sind durch Attrappen ersetzt: kein Test ruft OKX, keiner legt
einen Bot an und keiner stoppt einen. Ein Modulwaechter vergleicht am Ende die
Dateiliste des echten Ordners - ein Test, der nach draussen schreibt, faellt auf.

Aufruf (aus DIESEM Ordner):  python -m unittest test_okx_bot_waechter
"""
import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HIER not in sys.path:
    sys.path.insert(0, HIER)
import bots      # noqa: E402
import waechter  # noqa: E402
import vorschlag  # noqa: E402

assert waechter.__file__.startswith(HIER), waechter.__file__
assert vorschlag.__file__.startswith(HIER), vorschlag.__file__

# Echter Bot UNI-USD_UM_XPERP-310718 am 23.09.2026 (Antwort der Boerse)
UNI_BOT = {"algoId": "3947610369740500992", "instId": "UNI-USD_UM_XPERP-310718",
           "direction": "long", "lever": "8", "investmentAmt": "67.59",
           "investmentCcy": "USDC", "initOrdAmt": "5.4072", "safetyOrdAmt": "3.35557926",
           "maxSafetyOrds": "11", "pxSteps": "0.0072", "pxStepsMult": "1",
           "volMult": "1.1", "pnlRatio": "-0.5508795588182615",
           "totalPnl": "-37.2339493000000128", "state": "running", "cTime": "1790150356922"}
UNI_DETAIL = {"avgPx": "9.9454583333333334", "initPx": "10.4407500000000001",
              "liqPx": "8.719328514679633", "fillSafetyOrds": "11", "slPx": "",
              "tpPx": "10.384", "sz": "48", "notionalUsd": "441.888", "upl": "-35.494"}
UNI_ORDERS = [{"side": "buy", "px": "10.44075", "ordType": "init_order"},
              {"side": "buy", "px": "9.613", "ordType": "safety_order"},
              {"side": "buy", "px": "9.689", "ordType": "safety_order"},
              {"side": "sell", "px": "10.384", "ordType": "tp_order"}]

_WACHEN = {"stop_erlaubt": False, "bauen_erlaubt": False, "stop_art": "1",
           "reserve_prozent": 0.0, "liq_warnung_prozent": 8.0,
           "liq_notfall_prozent": 4.0, "bots": {}}


def _vorher():
    raus = {}
    for n in sorted(os.listdir(HIER)):
        p = os.path.join(HIER, n)
        if os.path.isfile(p):
            raus[n] = os.path.getsize(p)
    return raus


_STAND = _vorher()


def tearDownModule():
    nach = _vorher()
    neu = set(nach) - set(_STAND)
    geaendert = {k for k in set(nach) & set(_STAND) if nach[k] != _STAND[k]}
    # zustand.json schreibt der Waechter im Betrieb - im Test muss er umgebogen sein
    neu.discard("zustand.json")
    geaendert.discard("zustand.json")
    neu.discard("bot_waechter_journal.jsonl")
    geaendert.discard("bot_waechter_journal.jsonl")
    if neu or geaendert:
        raise AssertionError("Tests haben den echten Ordner veraendert: neu=%s "
                             "geaendert=%s" % (neu, geaendert))


class StufenTest(unittest.TestCase):
    def test_plan_stufen_treffen_die_echte_order(self):
        """Gegenprobe am echten Bot: die letzte Planstufe war die tiefste Order."""
        stufen = bots.stufen_plan("10.4407500000000001", "0.0072", "1", "11")
        self.assertEqual(len(stufen), 11)
        self.assertAlmostEqual(stufen[-1], 9.6138, places=3)
        self.assertEqual(min(bots.kaufstufen(UNI_ORDERS)), 9.613)

    def test_kaufstufen_werfen_verkaufsauftraege_raus(self):
        self.assertEqual(bots.kaufstufen(UNI_ORDERS), [9.613, 9.689, 10.44075])

    def test_letzte_grenze_nimmt_die_tiefere_von_beiden(self):
        grenze, belegt, geplant = bots.letzte_kaufgrenze(
            UNI_ORDERS, [9.6138, 9.7, 10.0])
        self.assertEqual(grenze, 9.613)
        self.assertEqual(belegt, 9.613)
        self.assertEqual(geplant, 9.6138)

    def test_ohne_orders_gilt_der_plan(self):
        grenze, belegt, geplant = bots.letzte_kaufgrenze([], [9.6, 9.8])
        self.assertEqual(grenze, 9.6)
        self.assertIsNone(belegt)

    def test_munition_und_liq_abstand(self):
        self.assertEqual(bots.munition("11", "11"), 0)
        self.assertEqual(bots.munition("11", "9"), 2)
        self.assertAlmostEqual(bots.liq_abstand(100, 90), 10.0)
        self.assertIsNone(bots.liq_abstand(100, 0))


FERN = dict(UNI_DETAIL, liqPx="5.0")   # Liquidation weit weg -> nur die Kaufgrenze zaehlt


class BewertungDcaTest(unittest.TestCase):

    def test_bot_unter_der_letzten_kaufgrenze_ist_ausgelaufen(self):
        l = waechter.bewerte_dca(UNI_BOT, FERN, UNI_ORDERS, 9.199, _WACHEN)
        self.assertEqual(l["lage"], "AUSGELAUFEN")
        self.assertEqual(l["munition"], 0)
        self.assertTrue(any("unter der letzten Kaufgrenze" in g for g in l["gruende"]))
        self.assertTrue(any("kein boersenseitiger Stop" in g for g in l["gruende"]))

    def test_kurs_an_der_grenze_ist_knapp(self):
        l = waechter.bewerte_dca(UNI_BOT, FERN, UNI_ORDERS, 9.63, _WACHEN)
        self.assertEqual(l["lage"], "KNAPP")

    def test_ausgelaufen_und_nahe_liquidation_wird_notfall(self):
        """Zwei Gruende treffen zusammen: ausserhalb der Grenze UND nah an der Liq."""
        l = waechter.bewerte_dca(UNI_BOT, UNI_DETAIL, UNI_ORDERS, 9.199, _WACHEN)
        self.assertEqual(l["lage"], "NOTFALL")
        self.assertTrue(any("Liquidation" in g for g in l["gruende"]))

    def test_gesunder_bot_ist_ok(self):
        bot = dict(UNI_BOT, maxSafetyOrds="14", pnlRatio="0.7")
        detail = dict(UNI_DETAIL, fillSafetyOrds="1", liqPx="")
        l = waechter.bewerte_dca(bot, detail, UNI_ORDERS, 10.45, _WACHEN)
        self.assertEqual(l["lage"], "OK")
        self.assertEqual(l["munition"], 13)

    def test_nahe_liquidation_ist_notfall(self):
        """Ausgangslage gesund - nur die Naehe zur Liquidation entscheidet."""
        bot = dict(UNI_BOT, maxSafetyOrds="14")
        detail = dict(UNI_DETAIL, fillSafetyOrds="1")
        # Kurs ueber der Kaufgrenze (9.389 bei 14 Stufen), 7,7 % bis zur Liquidation
        l = waechter.bewerte_dca(bot, detail, UNI_ORDERS, 9.45, _WACHEN)
        self.assertEqual(l["lage"], "WARNUNG")
        # 3,2 % heran -> Notfallband (4 %)
        l2 = waechter.bewerte_dca(bot, dict(detail, liqPx="9.15"), UNI_ORDERS, 9.45, _WACHEN)
        self.assertEqual(l2["lage"], "NOTFALL")

    def test_reserve_verlangt_tieferen_kurs(self):
        w = dict(_WACHEN, reserve_prozent=5.0)
        l = waechter.bewerte_dca(UNI_BOT, FERN, UNI_ORDERS, 9.10, w)
        self.assertEqual(l["lage"], "AUSGELAUFEN")
        l2 = waechter.bewerte_dca(UNI_BOT, FERN, UNI_ORDERS, 9.63, w)
        self.assertEqual(l2["lage"], "KNAPP")


class BewertungGridTest(unittest.TestCase):
    BOT = {"algoId": "1", "instId": "BTC-USD_UM_XPERP-310404", "direction": "long",
           "minPx": "75600", "maxPx": "90000", "gridNum": "40", "investment": "74.73",
           "pnlRatio": "0.01", "lever": "5", "cTime": "1790008447453"}

    def test_unter_der_unteren_kante_ist_ausgelaufen(self):
        l = waechter.bewerte_grid(self.BOT, {"liqPx": "50000", "slTriggerPx": ""},
                                  75000.0, _WACHEN)
        self.assertEqual(l["lage"], "AUSGELAUFEN")
        self.assertTrue(any("ausserhalb" in g for g in l["gruende"]))

    def test_im_netz_ist_ok(self):
        l = waechter.bewerte_grid(self.BOT, {"liqPx": "50000", "slTriggerPx": "75600"},
                                  80000.0, _WACHEN)
        self.assertEqual(l["lage"], "OK")

    def test_short_netz_kippt_nach_oben(self):
        bot = dict(self.BOT, direction="short")
        l = waechter.bewerte_grid(bot, {"liqPx": "50000", "slTriggerPx": "90000"},
                                  95000.0, _WACHEN)
        self.assertEqual(l["lage"], "AUSGELAUFEN")
        self.assertEqual(l["grenze"], 90000.0)


class TorTest(unittest.TestCase):
    def test_ohne_tor_ist_kein_bot_scharf(self):
        scharf, grund = waechter.bot_scharf("1", _WACHEN)
        self.assertFalse(scharf)
        self.assertIn("stop_erlaubt", grund)

    def test_einzelner_bot_kann_ausgenommen_werden(self):
        w = dict(_WACHEN, stop_erlaubt=True, bots={"1": {"scharf": False}})
        self.assertFalse(waechter.bot_scharf("1", w)[0])
        self.assertTrue(waechter.bot_scharf("2", w)[0])

    def test_anwenden_ohne_tor_stoppt_nichts(self):
        gerufen = []
        alt_stop, alt_sammle = bots.dca_stoppen, waechter.sammle
        bots.dca_stoppen = lambda *a, **k: gerufen.append(a) or {"ok": 1}
        try:
            l = waechter.bewerte_dca(UNI_BOT, UNI_DETAIL, UNI_ORDERS, 9.199, _WACHEN)
            with tempfile.TemporaryDirectory() as t:
                waechter.ZUSTAND = os.path.join(t, "z.json")
                waechter.JOURNAL = os.path.join(t, "j.jsonl")
                waechter.sammle = lambda w, **k: ([l], [])
                waechter.main(["--anwenden"])
        finally:
            bots.dca_stoppen, waechter.sammle = alt_stop, alt_sammle
        self.assertEqual(gerufen, [], "ohne Tor darf nichts gestoppt werden")

    def test_anwenden_mit_tor_stoppt_genau_einmal(self):
        gerufen = []
        alt_stop, alt_sammle, alt_wachen = bots.dca_stoppen, waechter.sammle, waechter.lade_wachen
        bots.dca_stoppen = lambda algo, art: gerufen.append((algo, art)) or {"ok": 1}
        try:
            w = dict(_WACHEN, stop_erlaubt=True)
            l = waechter.bewerte_dca(UNI_BOT, FERN, UNI_ORDERS, 9.199, w)
            with tempfile.TemporaryDirectory() as t:
                waechter.ZUSTAND = os.path.join(t, "z.json")
                waechter.JOURNAL = os.path.join(t, "j.jsonl")
                waechter.sammle = lambda w, **k: ([l], [])
                waechter.lade_wachen = lambda pfad=None: dict(_WACHEN, stop_erlaubt=True)
                waechter.main(["--anwenden"])
                # das Protokoll muss die Handlung tragen
                with open(waechter.JOURNAL, encoding="utf-8") as fh:
                    eintrag = json.loads(fh.readline())
        finally:
            bots.dca_stoppen, waechter.sammle = alt_stop, alt_sammle
            waechter.lade_wachen = alt_wachen
        self.assertEqual(gerufen, [("3947610369740500992", "1")])
        self.assertEqual(eintrag["lage"], "AUSGELAUFEN")
        self.assertIn("unter der letzten Kaufgrenze", eintrag["grund"])

    def test_bericht_ohne_anwenden_schreibt_kein_protokoll(self):
        alt_sammle, alt_wachen = waechter.sammle, waechter.lade_wachen
        try:
            w = dict(_WACHEN, stop_erlaubt=True)          # Tor offen, aber kein --anwenden
            l = waechter.bewerte_dca(UNI_BOT, FERN, UNI_ORDERS, 9.199, w)
            with tempfile.TemporaryDirectory() as t:
                waechter.ZUSTAND = os.path.join(t, "z.json")
                waechter.JOURNAL = os.path.join(t, "j.jsonl")
                waechter.sammle = lambda w, **k: ([l], [])
                waechter.lade_wachen = lambda pfad=None: dict(_WACHEN, stop_erlaubt=True)
                waechter.main([])
                self.assertFalse(os.path.exists(waechter.JOURNAL))
                self.assertTrue(os.path.exists(waechter.ZUSTAND))
        finally:
            waechter.sammle, waechter.lade_wachen = alt_sammle, alt_wachen


class DcaPlanTest(unittest.TestCase):
    def test_letzte_stufe_landet_auf_dem_planboden(self):
        p = vorschlag.dca_plan(100.0, 50.0, 120.0, n_max=12, px_schritt=0.0075,
                              fallraum_prozent=15.0)
        self.assertAlmostEqual(p["letzte_stufe"], p["planboden"], places=6)
        self.assertAlmostEqual(p["planboden"], 85.0, places=6)
        self.assertEqual(p["maxSafetyOrds"], 12)
        self.assertAlmostEqual(p["pxSteps"] * 12, 0.15, places=5)

    def test_marktboden_bleibt_harte_untergrenze(self):
        p = vorschlag.dca_plan(100.0, 90.0, 120.0, fallraum_prozent=30.0)
        self.assertAlmostEqual(p["planboden"], 90.0, places=6)
        self.assertAlmostEqual(p["fallraum_prozent"], 10.0, places=4)

    def test_stop_liegt_auf_der_letzten_kaufgrenze(self):
        p = vorschlag.dca_plan(100.0, 80.0, 120.0, fallraum_prozent=15.0)
        soll = (p["avg_px_wenn_voll"] - p["planboden"]) / p["avg_px_wenn_voll"]
        self.assertAlmostEqual(p["slPct"], round(soll, 4), places=4)

    def test_liquidation_liegt_unter_dem_planboden(self):
        p = vorschlag.dca_plan(100.0, 80.0, 120.0, fallraum_prozent=15.0,
                              hebel_max=10, sicherheitsabstand=0.05)
        self.assertLess(p["liq_bei_hebel"], p["planboden"] * 0.96)
        self.assertLessEqual(p["hebel"], 10)

    def test_boden_ueber_dem_kurs_ist_ein_fehler(self):
        self.assertIn("fehler", vorschlag.dca_plan(100.0, 110.0, 120.0))

    def test_koerper_traegt_den_gebauten_stop(self):
        p = vorschlag.dca_plan(100.0, 80.0, 120.0, fallraum_prozent=15.0)
        k = vorschlag.koerper_dca(p, "UV-USD_UM_XPERP-310718")
        self.assertEqual(k["slMode"], "market")
        self.assertEqual(k["slPct"], str(p["slPct"]))
        self.assertEqual(k["maxSafetyOrds"], str(p["maxSafetyOrds"]))
        self.assertEqual(k["instId"], "UV-USD_UM_XPERP-310718")


class GridPlanTest(unittest.TestCase):
    AI = {"direction": "long", "minPx": "68914.8", "maxPx": "103372.2",
          "gridNum": "200", "lever": "5", "minInvestment": "534.4162",
          "annualizedRate": "0.5439", "duration": "14D"}

    def test_bereich_wird_auf_die_beobachtete_spanne_gezogen(self):
        p = vorschlag.grid_plan(self.AI, 83995.0, 74900.0, 87389.7, 600.0)
        self.assertEqual(p["minPx"], 68914.8)      # OKX-Kante war schon tiefer
        self.assertEqual(p["maxPx"], 103372.2)
        self.assertEqual(p["gridNum"], 120)        # gedeckelt
        self.assertEqual(p["slTriggerPx"], p["minPx"])

    def test_zu_kleiner_einsatz_wird_gewarnt(self):
        p = vorschlag.grid_plan(self.AI, 83995.0, 74900.0, 87389.7, 150.0)
        self.assertTrue(any("Mindestinvestment" in w for w in p["warnungen"]))

    def test_kurs_ausserhalb_des_netzes_wird_gemeldet(self):
        p = vorschlag.grid_plan(self.AI, 40000.0, 50000.0, 65000.0, 600.0)
        self.assertTrue(any("UNTER der unteren Kante" in w for w in p["warnungen"]))


class BauenTorTest(unittest.TestCase):
    def _vorschlag(self, ordner, art="dca"):
        v = {"art": art, "instId": "UV-USD_UM_XPERP-310718", "budget": 100.0,
             "kurs": 100.0, "boden": 80.0,
             "plan": {"_rechnung": "Probe", "warnungen": []},
             "koerper": {"instId": "UV-USD_UM_XPERP-310718"}}
        p = os.path.join(ordner, "probe.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(v, f)
        return p

    def test_ohne_tor_wird_nichts_angelegt(self):
        import bauen
        gerufen = []
        alt = bots.dca_anlegen
        bots.dca_anlegen = lambda k: gerufen.append(k) or {"ok": 1}
        try:
            with tempfile.TemporaryDirectory() as t:
                p = self._vorschlag(t)
                bauen.JOURNAL = os.path.join(t, "b.jsonl")
                bauen.WACHEN = os.path.join(t, "w.json")
                with open(bauen.WACHEN, "w", encoding="utf-8") as f:
                    json.dump({"bauen_erlaubt": False}, f)
                bauen.main([p, "--anwenden"])
                with open(bauen.JOURNAL, encoding="utf-8") as f:
                    eintrag = json.loads(f.readline())
        finally:
            bots.dca_anlegen = alt
        self.assertEqual(gerufen, [])
        self.assertFalse(eintrag["angelegt"])
        self.assertIn("bauen_erlaubt", eintrag["grund"])

    def test_mit_tor_und_anwenden_wird_angelegt(self):
        import bauen
        gerufen = []
        alt = bots.dca_anlegen
        bots.dca_anlegen = lambda k: gerufen.append(k) or {"ok": 1}
        try:
            with tempfile.TemporaryDirectory() as t:
                p = self._vorschlag(t)
                bauen.JOURNAL = os.path.join(t, "b.jsonl")
                bauen.WACHEN = os.path.join(t, "w.json")
                with open(bauen.WACHEN, "w", encoding="utf-8") as f:
                    json.dump({"bauen_erlaubt": True, "_vorschlag": {"startgeld_max_usd": 300}},
                              f)
                bauen.main([p, "--anwenden"])
        finally:
            bots.dca_anlegen = alt
        self.assertEqual(len(gerufen), 1)

    def test_deckel_sperrt_grosse_einsaetze(self):
        import bauen
        gerufen = []
        alt = bots.dca_anlegen
        bots.dca_anlegen = lambda k: gerufen.append(k) or {"ok": 1}
        try:
            with tempfile.TemporaryDirectory() as t:
                p = self._vorschlag(t)
                bauen.JOURNAL = os.path.join(t, "b.jsonl")
                bauen.WACHEN = os.path.join(t, "w.json")
                with open(bauen.WACHEN, "w", encoding="utf-8") as f:
                    json.dump({"bauen_erlaubt": True, "_vorschlag": {"startgeld_max_usd": 50}}, f)
                bauen.main([p, "--anwenden"])
                bauen.main([p, "--anwenden", "--deckel-aus"])
        finally:
            bots.dca_anlegen = alt
        self.assertEqual(len(gerufen), 1, "nur der Lauf mit aufgehobenem Deckel darf bauen")

    def test_fehlendes_mindestinvestment_sperrt(self):
        import bauen
        gerufen = []
        alt = bots.dca_anlegen
        bots.dca_anlegen = lambda k: gerufen.append(k) or {"ok": 1}
        try:
            with tempfile.TemporaryDirectory() as t:
                p = self._vorschlag(t)
                v = json.load(open(p, encoding="utf-8"))
                v["plan"]["warnungen"] = ["Einsatz 100 liegt unter dem Mindestinvestment von OKX (534)"]
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(v, f)
                bauen.JOURNAL = os.path.join(t, "b.jsonl")
                bauen.WACHEN = os.path.join(t, "w.json")
                with open(bauen.WACHEN, "w", encoding="utf-8") as f:
                    json.dump({"bauen_erlaubt": True}, f)
                bauen.main([p, "--anwenden"])
        finally:
            bots.dca_anlegen = alt
        self.assertEqual(gerufen, [])


class WachenDateiTest(unittest.TestCase):
    def test_tore_stehen_auf_false(self):
        """Die Vorgabe in wachen.json darf niemand versehentlich scharf stellen."""
        w = waechter.lade_wachen()
        self.assertFalse(w["stop_erlaubt"])
        self.assertFalse(w["bauen_erlaubt"])

    def test_zeile_je_bot_ist_eine_zeile(self):
        l = waechter.bewerte_dca(UNI_BOT, FERN, UNI_ORDERS, 9.199, _WACHEN)
        z = waechter.zeile(l)
        self.assertEqual(len(z.splitlines()), 1, "eine Meldung je Bot, nicht zwei")
        self.assertIn(l["lage"], z)
        self.assertIn("Grenze 9.6130", z)


if __name__ == "__main__":
    unittest.main()