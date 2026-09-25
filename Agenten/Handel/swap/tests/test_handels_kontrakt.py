"""Der handelbare Kontrakt der SWAP-Spur: XPERP-Zwilling und freie Margin.

Anlass (25.09.2026): Die Spur handelte den gewoehnlichen Perpetual
(XAU-USDT-SWAP) und bekam von OKX "50124 does not have trading permission for
the market", waehrend derselbe Markt als XPERP-Kontrakt handelbar ist. Drei
Dinge werden hier festgehalten: die Zwillingstabelle, dass eine Reihe ohne
Zwilling aus dem Vorrat faellt, und dass der Live-Lauf ohne freie Margin den
Auftrag gar nicht erst versucht. Ohne Netz - jede Abfrage ist eine Attrappe.
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SWAP = os.path.dirname(HIER)
if SWAP not in sys.path:
    sys.path.insert(0, SWAP)

import freigabefenster                                        # noqa: E402
import handeln as h                                           # noqa: E402
import kandidaten as k                                        # noqa: E402
import okxf                                                   # noqa: E402

FUTURES = [
    {"instId": "XAU-USD_UM_XPERP-310502", "ruleType": "xperp",
     "state": "live", "instCategory": "4", "lever": "50"},
    {"instId": "CHIP-USD_UM_XPERP-310822", "ruleType": "xperp",
     "state": "live", "instCategory": "1", "lever": "20"},
    {"instId": "ALT-USD_UM_XPERP-310111", "ruleType": "xperp",
     "state": "suspendiert", "instCategory": "1", "lever": "20"},
    {"instId": "BTC-USD-260926", "ruleType": "1", "state": "live",
     "instCategory": "1", "lever": "100"},
]

WACHEN = {"max_offene_anlaeufe": 2, "max_margin_gesamt_usd": 100.0,
          "max_margin_je_anlauf_usd": 50.0, "risiko_je_anlauf_usd": 5.0,
          "max_hebel": 5, "wartungsmarge": 0.005,
          "gebuehr_maker": 0.0002, "gebuehr_taker": 0.0005,
          "stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0,
          "einstieg_atr_abschlag": 0.25, "abklingzeit_tage": 3,
          "handel_erlaubt": True, "journal_zweitziel": 1.0,
          "familien": {"krypto": {"aktiv": True, "max_anteil_gesamt": 1.0},
                       "rohstoff": {"aktiv": True, "max_anteil_gesamt": 0.5}}}


def kerzen(basis=1.0):
    """Kerzen in der Form von okxf.kerzen(): [ts, o, h, l, c, vol], aufsteigend.

    Mit echter Bewegung - sonst ist die Vola 0 und der Hebel-Deckel faellt auf
    seinen Hoechstwert.
    """
    reihe = []
    kurs = basis
    for i in range(300):
        schwung = 1 + (i % 7) * 0.004 - 0.012
        offen = kurs
        kurs = kurs * schwung
        reihe.append([i, offen, max(offen, kurs) * 1.003,
                      min(offen, kurs) * 0.997, kurs, 10.0])
    return reihe


class Zwillingstabelle(unittest.TestCase):

    def test_nimmt_nur_lebende_xperp_kontrakte(self):
        alt = okxf._mit_wiederholung
        okxf._mit_wiederholung = lambda *a, **kw: FUTURES
        try:
            m = k.handels_kontrakte()
        finally:
            okxf._mit_wiederholung = alt
        # Der suspendierte XPERP und der datierte Future fallen heraus.
        self.assertEqual(sorted(m), ["CHIP", "XAU"])
        self.assertEqual(m["XAU"]["instId"], "XAU-USD_UM_XPERP-310502")


class Vorrat(unittest.TestCase):

    def setUp(self):
        self.alt = (okxf.kerzen, okxf.tickers, k.instrumente,
                    k.handels_kontrakte)
        k4h = kerzen()
        okxf.kerzen = lambda inst, bar="1H", anzahl=300: k4h
        okxf.tickers = lambda inst_type="FUTURES": {
            "CHIP-USDT-SWAP": {"volCcy24h": "50000000", "last": "1.0"},
            "OHNE-USDT-SWAP": {"volCcy24h": "1000", "last": "1.0"}}
        k.instrumente = lambda: [
            {"instId": "CHIP-USDT-SWAP", "lever": "20", "instCategory": "1"},
            {"instId": "OHNE-USDT-SWAP", "lever": "5", "instCategory": "1"}]
        k.handels_kontrakte = lambda: {
            "CHIP": {"instId": "CHIP-USD_UM_XPERP-310822", "lever": "20"}}

    def tearDown(self):
        (okxf.kerzen, okxf.tickers, k.instrumente,
         k.handels_kontrakte) = self.alt

    def test_ohne_zwilling_faellt_die_reihe_aus_dem_vorrat(self):
        d = k.sammle(still=True, vorsortiert=None)
        self.assertEqual([z["instId"] for z in d], ["CHIP-USDT-SWAP"])
        self.assertEqual(d[0]["handels_instId"], "CHIP-USD_UM_XPERP-310822")
        self.assertEqual(d[0]["handels_instr"]["instId"],
                         "CHIP-USD_UM_XPERP-310822")
        self.assertEqual(d[0]["max_lever"], 20.0)


class Anlauf(unittest.TestCase):
    """Der Anlauf nimmt den Kontrakt aus dem Vorrat, nicht den Perpetual."""

    def setUp(self):
        self.alt = (okxf.kerzen, okxf.auf_tick, okxf.instrument,
                    h.indikatoren.lage, h.bot.groesse, h.bot.pruefpflicht)
        k4h = kerzen()
        okxf.kerzen = lambda inst, bar="1H", anzahl=300: k4h
        okxf.auf_tick = lambda instr, preis: round(preis, 2)

        def verboten(basis):
            raise AssertionError(
                "der Zwilling liegt vor - okxf.instrument darf nicht laufen")
        okxf.instrument = verboten
        h.indikatoren.lage = lambda kk, inst=None: {
            "signal": "long", "atr": 1.0, "kurs": 100.0, "grund": "Test"}
        h.bot.groesse = lambda w, instr, einstieg, stop, seite, deckel: {
            "kontrakte": 10, "nominal": 100.0, "hebel": 5.0, "margin": 20.0,
            "risiko": 3.0, "abstand": 0.03, "gedeckelt": False, "liq": 82.0}
        h.bot.pruefpflicht = lambda *a, **kw: {
            "traegt": True, "hebel_traegt": True, "hebel": 5.0,
            "hebel_deckel": 6.0, "liq_abstand": 0.18, "funding_pct": 0.0001,
            "gebuehren_pct": 0.001, "quote_noetig": 0.4,
            "quote_beobachtet": 0.5}

    def tearDown(self):
        (okxf.kerzen, okxf.auf_tick, okxf.instrument,
         h.indikatoren.lage, h.bot.groesse, h.bot.pruefpflicht) = self.alt

    def test_anlauf_handelt_den_zwilling(self):
        kandidat = {"basis": "XAU", "instId": "XAU-USDT-SWAP",
                    "handels_instId": "XAU-USD_UM_XPERP-310502",
                    "handels_instr": {"instId": "XAU-USD_UM_XPERP-310502",
                                      "ctVal": "0.001", "lotSz": "1",
                                      "tickSz": "0.1", "lever": "50"},
                    "seite": "long", "kategorie": "rohstoff",
                    "punkte": {"long": 60.0, "short": 10.0, "grid": 5.0},
                    "deckel": 6.0}
        a = h.anlauf(WACHEN, kandidat)
        self.assertIsNotNone(a)
        self.assertEqual(a["inst"], "XAU-USD_UM_XPERP-310502")
        self.assertEqual(a["instr"]["instId"], "XAU-USD_UM_XPERP-310502")


class Fenster:
    def __init__(self, offen):
        self._offen = offen

    def offen(self):
        return self._offen


def lage(freigabe=True, herzschlag=True, ev=1.0):
    return {"freigabe_erfuellt": freigabe, "herzschlag_frisch": herzschlag,
            "ev_negativ": ev is not None and ev < 0, "rollierender_ev": ev,
            "wochenende": False}


class Margin(unittest.TestCase):
    """Freie Margin ist ein Sperrgrund - eine gescheiterte Abfrage nicht."""

    def setUp(self):
        self.alt = (okxf.schluessel_vorhanden, okxf.guthaben_usdc,
                    freigabefenster.lade, h.risikostufe.live_erlaubt)
        okxf.schluessel_vorhanden = lambda: True
        h.risikostufe.live_erlaubt = lambda: True
        freigabefenster.lade = lambda spur: Fenster(False)

    def tearDown(self):
        (okxf.schluessel_vorhanden, okxf.guthaben_usdc,
         freigabefenster.lade, h.risikostufe.live_erlaubt) = self.alt

    def test_zu_wenig_margin_steht_vor_dem_fenster_in_der_liste(self):
        okxf.guthaben_usdc = lambda: 0.15
        g = h.sperren_live(WACHEN, lage())
        self.assertIn("nur 0.15 USDC frei, noetig 50.00 "
                      "(max_margin_je_anlauf_usd)", g)
        self.assertEqual(
            g[-1], "kein offenes Freigabefenster (Handelsregeln Punkt 3)")
        for grund in g[:-1]:
            self.assertNotIn("Freigabefenster", grund)

    def test_genug_margin_laesst_nur_das_fenster_offen(self):
        okxf.guthaben_usdc = lambda: 1000.0
        self.assertEqual(
            h.sperren_live(WACHEN, lage()),
            ["kein offenes Freigabefenster (Handelsregeln Punkt 3)"])

    def test_gescheiterte_abfrage_sperrt_nicht(self):
        def kaputt():
            raise RuntimeError("Netz weg")
        okxf.guthaben_usdc = kaputt
        self.assertIsNone(h.marge_frei_usd())
        self.assertEqual(
            h.sperren_live(WACHEN, lage()),
            ["kein offenes Freigabefenster (Handelsregeln Punkt 3)"])


if __name__ == "__main__":
    unittest.main()
