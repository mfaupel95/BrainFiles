"""Tests fuer swap/handeln.py - Papier- und Live-Pfad, ohne Netz.

Der Live-Pfad wird nicht ausgefuehrt, sondern abgehoert: Die Order-Funktionen
werden im Test durch Aufzeichner ersetzt. Im Papierlauf muessen sie stumm
bleiben, im Live-Zweig duerfen sie nur mit den erwarteten Werten aufgerufen
werden - inklusive des boersenseitigen Stops (tp/sl an der Order).
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
SWAP = os.path.dirname(HIER)
if SWAP not in sys.path:
    sys.path.insert(0, SWAP)

import handeln as h                                            # noqa: E402
import freigabefenster                                         # noqa: E402
import okxf                                                    # noqa: E402

WACHEN = {
    "max_offene_anlaeufe": 2, "max_margin_gesamt_usd": 100.0,
    "max_margin_je_anlauf_usd": 25.0, "risiko_je_anlauf_usd": 5.0,
    "max_hebel": 5, "wartungsmarge": 0.005,
    "gebuehr_maker": 0.0002, "gebuehr_taker": 0.0005,
    "min_umsatz_24h_usd": 3000000,
    "stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0,
    "einstieg_atr_abschlag": 0.25,
    "herzschlag_max_minuten": 30, "abklingzeit_tage": 3,
    "familien": {"krypto": {"aktiv": True, "max_anteil_gesamt": 1.0},
                 "aktie": {"aktiv": True, "max_anteil_gesamt": 0.5},
                 "rohstoff": {"aktiv": True, "max_anteil_gesamt": 0.5}},
}

KAND = {"basis": "XAU", "instId": "XAU-USDT-SWAP", "seite": "long",
        "kategorie": "krypto", "punkte": {"long": 60.0, "short": 10.0,
                                             "grid": 5.0}, "deckel": 6.0}


def anlauf_stummel(w, kandidat):
    """Ein fertiger Anlauf ohne Netz - dieselbe Form wie handeln.anlauf()."""
    return {
        "instr": {"instId": kandidat["instId"], "ctVal": "1", "lotSz": "1",
                  "tickSz": "0.0001", "lever": "20"},
        "inst": kandidat["instId"], "basis": kandidat["basis"],
        "seite": kandidat["seite"], "kategorie": kandidat["kategorie"],
        "einstieg": 100.0, "stop": 97.0, "ziel": 106.0,
        "groesse": {"kontrakte": 10, "nominal": 100.0, "hebel": 5.0,
                    "margin": 20.0, "risiko": 3.0, "abstand": 0.03,
                    "gedeckelt": False, "liq": 82.0},
        "pflicht": {"traegt": True, "hebel_traegt": True, "hebel": 5.0,
                    "hebel_deckel": 6.0, "liq_abstand": 0.18,
                    "funding_pct": 0.0001, "gebuehren_pct": 0.001,
                    "quote_noetig": 0.4, "quote_beobachtet": 0.5},
        "punkte": kandidat["punkte"], "grund": "Test",
    }


def position(**over):
    p = {"inst": "XAU-USDT-SWAP", "basis": "XAU", "seite": "long",
         "familie": "krypto", "einstieg": 100.0, "stop": 97.0,
         "ziel": 106.0, "liq": 82.0, "kontrakte": 10, "nominal": 100.0,
         "margin": 20.0, "hebel": 5.0, "gebuehr_taker": 0.0005,
         "eroeffnet": "2026-09-11", "eroeffnet_zeit": "2026-09-11T10:00:00+00:00",
         "funding_zuletzt": "2026-09-11T10:00:00+00:00", "funding_summe": 0.0,
         # Seit 25.09.2026 ordnet jedes Buchstueck einem Zweig zu; Vorgabe ist
         # Papier (die Papierlauf-Tests), Live-Tests sagen modus="live" an.
         "modus": "papier"}
    p.update(over)
    return p


class Fenster:
    def __init__(self, offen):
        self._offen = offen

    def offen(self):
        return self._offen


def w_zu(handel_erlaubt=True, zweitziel=1.0):
    w = dict(WACHEN, handel_erlaubt=handel_erlaubt)
    if zweitziel is not None:
        w["journal_zweitziel"] = zweitziel
    return w


def lage_zu(freigabe=True, herzschlag=True, ev=1.0, wochenende=False):
    return {"freigabe_erfuellt": freigabe, "herzschlag_frisch": herzschlag,
            "ev_negativ": ev is not None and ev < 0, "rollierender_ev": ev,
            "wochenende": wochenende}


class Sperren(unittest.TestCase):
    """Die Sperrgruende von sperren_live() - Schnittstelle zum Dauerlauf.

    Sieben Bedingungen plus die freie Margin; sind alle Bedingungen offen und
    ist Geld da, bleibt genau der Fenster-Grund uebrig.
    """

    def setUp(self):
        self.alt = (okxf.schluessel_vorhanden, freigabefenster.lade,
                    okxf.guthaben_usdc)
        okxf.schluessel_vorhanden = lambda: True
        # Freie Margin reichlich: hier sollen die Bedingungen geprueft werden,
        # nicht das Guthaben - dafuer gibt es test_handels_kontrakt.py. Ohne
        # diese Attrappe liefe eine echte Kontoabfrage.
        okxf.guthaben_usdc = lambda: 1000.0

    def tearDown(self):
        (okxf.schluessel_vorhanden, freigabefenster.lade,
         okxf.guthaben_usdc) = self.alt

    def test_alles_zu_ergibt_sieben_gruende(self):
        okxf.schluessel_vorhanden = lambda: False
        freigabefenster.lade = lambda spur: Fenster(False)
        g = h.sperren_live(w_zu(False, None),
                           lage_zu(False, False, -1.0))
        self.assertEqual(len(g), 7)
        self.assertEqual(
            g[-1], "kein offenes Freigabefenster (Handelsregeln Punkt 3)")
        for grund in g[:-1]:
            self.assertNotIn("Freigabefenster", grund)

    def test_nur_das_fenster_fehlt_ergibt_genau_einen_grund(self):
        """Was dauerlauf.nur_fenster_fehlt als Bitte liest: ein Grund, das
        Wort Freigabefenster, kein Semikolon und kein Doppelpunkt darin."""
        freigabefenster.lade = lambda spur: Fenster(False)
        g = h.sperren_live(w_zu(True, 1.0), lage_zu(True, True, 1.0))
        self.assertEqual(
            g, ["kein offenes Freigabefenster (Handelsregeln Punkt 3)"])
        self.assertNotIn(";", g[0])
        self.assertNotIn(":", g[0])

    def test_fenster_offen_und_bedingungen_frei_ergibt_keine_sperre(self):
        freigabefenster.lade = lambda spur: Fenster(True)
        self.assertEqual(h.sperren_live(w_zu(True, 1.0),
                                        lage_zu(True, True, 1.0)), [])

    def test_vorschau_druckt_die_sperrliste_als_schnittstelle(self):
        with open(os.path.join(SWAP, "handeln.py"), encoding="utf-8") as f:
            quelle = f.read()
        self.assertIn("Live waere gesperrt durch: ", quelle)


class Papierlauf(unittest.TestCase):
    """Der Papierpfad: Positionen entstehen und schliessen, Orders nie."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (h.ZUSTAND, h.JOURNAL, h.anlauf, h._kurs,
                    okxf.hebel_setzen, okxf.order_limit,
                    okxf.markt_schliessen)
        h.ZUSTAND = os.path.join(self.tmp.name, "zustand.json")
        h.JOURNAL = os.path.join(self.tmp.name, "handelsjournal.csv")
        h.anlauf = anlauf_stummel

        def _verboten(*a, **kw):
            raise AssertionError("Papierlauf darf keine Order rufen")
        okxf.hebel_setzen = _verboten
        okxf.order_limit = _verboten
        okxf.markt_schliessen = _verboten

    def tearDown(self):
        (h.ZUSTAND, h.JOURNAL, h.anlauf, h._kurs,
         okxf.hebel_setzen, okxf.order_limit,
         okxf.markt_schliessen) = self.alt
        self.tmp.cleanup()

    def journal_zeilen(self):
        with open(h.JOURNAL, encoding="utf-8") as f:
            return f.read().splitlines()

    def test_papier_einstieg_legt_position_und_journalzeile_an(self):
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [KAND], WACHEN, False,
                           {"wochenende": False}, 1.0)
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        for feld in ("inst", "basis", "seite", "familie", "einstieg", "stop",
                     "ziel", "liq", "kontrakte", "nominal", "margin", "hebel",
                     "gebuehr_taker", "eroeffnet", "eroeffnet_zeit"):
            self.assertIn(feld, p)
        zeilen = self.journal_zeilen()
        self.assertEqual(len(zeilen), 2)          # Kopfzeile + Eroeffnung
        self.assertIn(",papier,eroeffnen,", zeilen[1])
        self.assertIn("XAU-USDT-SWAP", zeilen[1])

    def test_wochenende_sperrt_aktie_und_rohstoff_nicht_krypto(self):
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [dict(KAND, kategorie="rohstoff")], WACHEN,
                           False, {"wochenende": True}, 1.0)
        self.assertEqual(z["positionen"], [])
        h.pruefe_einstiege(z, [KAND], WACHEN, False,
                           {"wochenende": True}, 1.0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_kein_zweiter_anlauf_in_dieselbe_reihe(self):
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [KAND, KAND], WACHEN, False,
                           {"wochenende": False}, 1.0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_ohne_tragende_quote_kein_anlauf(self):
        z = {"positionen": [], "letzte_stops": {}}
        alt = anlauf_stummel(WACHEN, KAND)
        alt["pflicht"] = dict(alt["pflicht"], traegt=False)
        h.anlauf = lambda w, k: alt
        h.pruefe_einstiege(z, [KAND], WACHEN, False,
                           {"wochenende": False}, 1.0)
        self.assertEqual(z["positionen"], [])

    def test_rahmen_ist_bei_zwei_anlaeufen_zu(self):
        z = {"positionen": [position(), position(inst="BTC-USDT-SWAP", basis="BTC")],
             "letzte_stops": {}}
        h.pruefe_einstiege(z, [KAND], WACHEN, False,
                           {"wochenende": False}, 1.0)
        self.assertEqual(len(z["positionen"]), 2)

    def test_stop_schliesst_die_papierposition_und_setzt_die_abklingzeit(self):
        h._kurs = lambda inst: 96.0
        z = {"positionen": [position()], "letzte_stops": {}}
        h.pruefe_ausstiege(z, False, WACHEN)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(z["letzte_stops"]["XAU"],
                         datetime.now(timezone.utc).date().isoformat())
        self.assertIn("stop", self.journal_zeilen()[1])

    def test_ziel_schliesst_ohne_abklingzeit(self):
        h._kurs = lambda inst: 107.0
        z = {"positionen": [position()], "letzte_stops": {}}
        h.pruefe_ausstiege(z, False, WACHEN)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(z["letzte_stops"], {})
        self.assertIn("ziel", self.journal_zeilen()[1])

    def test_liquidation_ist_ein_eigener_grund(self):
        h._kurs = lambda inst: 80.0
        z = {"positionen": [position()], "letzte_stops": {}}
        h.pruefe_ausstiege(z, False, WACHEN)
        self.assertIn("LIQUIDATION", self.journal_zeilen()[1])

    def test_position_bleibt_wenn_kein_kurs_kommt(self):
        def platzt(inst):
            raise RuntimeError("kein Netz")
        h._kurs = platzt
        z = {"positionen": [position()], "letzte_stops": {}}
        h.pruefe_ausstiege(z, False, WACHEN)
        self.assertEqual(len(z["positionen"]), 1)

    def test_ergebnis_rechnet_gebuehr_beim_schliessen_ab(self):
        erloes = h._ergebnis(position(), 110.0)
        self.assertAlmostEqual(erloes, 20.0 + 10.0 - 0.05, places=6)

    def test_short_dreht_das_vorzeichen(self):
        p = position(seite="short")
        self.assertAlmostEqual(h._ergebnis(p, 90.0), 20.0 + 10.0 - 0.05, places=6)

    def test_notausstieg_raeumt_alles(self):
        h._kurs = lambda inst: 100.5
        z = {"positionen": [position(), position(inst="BTC-USDT-SWAP", basis="BTC")],
             "letzte_stops": {}}
        h.flach_stellen(z, False, "kill_switch")
        self.assertEqual(z["positionen"], [])
        self.assertEqual(len(self.journal_zeilen()), 3)   # Kopf + zwei Zeilen

    def test_abklingzeit_gilt_fuer_den_stoptag(self):
        heute = datetime.now(timezone.utc).date().isoformat()
        alt = (datetime.now(timezone.utc).date() - timedelta(days=5)).isoformat()
        z = {"letzte_stops": {"XAU": heute, "BTC": alt}}
        self.assertTrue(h.in_abklingzeit("XAU", z, WACHEN))
        self.assertFalse(h.in_abklingzeit("BTC", z, WACHEN))
        self.assertFalse(h.in_abklingzeit("ETH", z, WACHEN))


    def test_vorschau_schreibt_weder_journal_noch_zustand(self):
        """Der Dauerlauf fragt jede Spur zusaetzlich mit --vorschau ab.

        Eine Vorschau darf nichts buchen. Vorher liefen Ausstiege, Funding,
        Kill und Herzschlag VOR dem Vorschau-Zweig: jeder Probe-Lauf schrieb
        dann Phantom-Funding und Phantom-Ausstiege ins Journal - und darauf
        stehen Trefferquote, rollierender EV und Drawdown, also die Tore fuer
        den Live-Pfad.
        """
        z = {"positionen": [position()], "letzte_stops": {}}
        h.schreibe_zustand(z)
        alt_scan = h.rangliste
        h.rangliste = lambda z, still=True: ([], 0.0)
        try:
            h.lauf("vorschau")
        finally:
            h.rangliste = alt_scan
        self.assertFalse(os.path.exists(h.JOURNAL),
                         "Vorschau hat ins Journal geschrieben")
        nach = h.lade_zustand()
        self.assertEqual(len(nach["positionen"]), 1,
                         "Vorschau hat den Zustand veraendert")


class Livezweig(unittest.TestCase):
    """Der Live-Zweig: Orders nur hier, und nur mit dem boersenseitigen Stop."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.aufrufe = []
        self.alt = (h.ZUSTAND, h.JOURNAL, h.anlauf, h._kurs,
                    okxf.hebel_setzen, okxf.order_limit,
                    okxf.markt_schliessen)
        h.ZUSTAND = os.path.join(self.tmp.name, "zustand.json")
        h.JOURNAL = os.path.join(self.tmp.name, "handelsjournal.csv")
        h.anlauf = anlauf_stummel
        okxf.hebel_setzen = lambda inst, hebel, *a, **kw: self.aufrufe.append(
            ("hebel_setzen", inst, hebel))
        okxf.order_limit = lambda *a, **kw: self.aufrufe.append(
            ("order_limit", a, kw))
        okxf.markt_schliessen = lambda *a, **kw: self.aufrufe.append(
            ("markt_schliessen", a, kw))

    def tearDown(self):
        (h.ZUSTAND, h.JOURNAL, h.anlauf, h._kurs,
         okxf.hebel_setzen, okxf.order_limit,
         okxf.markt_schliessen) = self.alt
        self.tmp.cleanup()

    def journal_zeilen(self):
        with open(h.JOURNAL, encoding="utf-8") as f:
            return f.read().splitlines()

    def test_live_einstieg_setzt_hebel_und_order_mit_tp_und_sl(self):
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [KAND], WACHEN, True,
                           {"wochenende": False}, 1.0)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self.aufrufe[0][0], "hebel_setzen")
        self.assertEqual(self.aufrufe[0][1:], ("XAU-USDT-SWAP", 5.0))
        name, args, kw = self.aufrufe[1]
        self.assertEqual(name, "order_limit")
        self.assertEqual(args, ("XAU-USDT-SWAP", "buy", 10, 100.0))
        self.assertEqual(kw, {"tp": 106.0, "sl": 97.0})
        self.assertIn(",live,eroeffnen,", self.journal_zeilen()[1])

    def test_papier_einstieg_ruft_keine_order(self):
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [KAND], WACHEN, False,
                           {"wochenende": False}, 1.0)
        self.assertEqual(self.aufrufe, [])
        self.assertIn(",papier,eroeffnen,", self.journal_zeilen()[1])

    def test_live_einstieg_traegt_modus_live(self):
        """Sonst bucht der naechste Live-Zyklus die eigene Position als Altlast aus.

        Belegt im Journal 22.-24.09.2026 (dreimal): eroeffnen, 13 bis 28
        Minuten spaeter 'buchbereinigung' durch den Live-Zyklus, dann wieder
        eroeffnen - die Papierstrecke kam nie an Stop oder Ziel. Die andere
        Richtung waere teurer: eine ECHTE Position ohne dieses Feld bleibt nach
        dem Ausbuchen ohne Buch an der Boerse stehen.
        """
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [KAND], WACHEN, True,
                           {"wochenende": False}, 1.0)
        self.assertEqual(z["positionen"][0]["modus"], "live")
        # Die Probe: die Bereinigung des naechsten Live-Laufs laesst sie stehen.
        self.assertEqual(h.bueche_papier_altlasten_aus(z), 0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_papier_einstieg_traegt_modus_papier(self):
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [KAND], WACHEN, False,
                           {"wochenende": False}, 1.0)
        self.assertEqual(z["positionen"][0]["modus"], "papier")
        # Papier ist kein Altbestand: die Bereinigung laesst sie stehen.
        self.assertEqual(h.bueche_papier_altlasten_aus(z), 0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_live_fasst_papier_position_nicht_an(self):
        """Die teure Richtung: kein echtes markt_schliessen fuer Scheinware."""
        h._kurs = lambda inst: 96.0
        z = {"positionen": [position(modus="papier")], "letzte_stops": {}}
        h.pruefe_ausstiege(z, True, WACHEN)
        h.flach_stellen(z, True, "kill_switch")
        self.assertEqual(self.aufrufe, [])
        self.assertEqual(len(z["positionen"]), 1)

    def test_papier_fasst_live_position_nicht_an(self):
        """Spiegelbild: der Papierzweig verkauft keine echte Position."""
        h._kurs = lambda inst: 96.0
        z = {"positionen": [position(modus="live")], "letzte_stops": {}}
        h.pruefe_ausstiege(z, False, WACHEN)
        h.flach_stellen(z, False, "kill_switch")
        self.assertEqual(len(z["positionen"]), 1)

    def test_live_stop_ruft_markt_schliessen(self):
        h._kurs = lambda inst: 96.0
        z = {"positionen": [position(modus="live")], "letzte_stops": {}}
        h.pruefe_ausstiege(z, True, WACHEN)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self.aufrufe[0][0], "markt_schliessen")
        self.assertEqual(self.aufrufe[0][1], ("XAU-USDT-SWAP", 10, "long"))
        self.assertIn(",live,schliessen,", self.journal_zeilen()[1])

    def test_papier_stop_ruft_keine_order(self):
        h._kurs = lambda inst: 96.0
        z = {"positionen": [position(modus="papier")], "letzte_stops": {}}
        h.pruefe_ausstiege(z, False, WACHEN)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self.aufrufe, [])

    def test_live_notausstieg_ruft_markt_schliessen(self):
        h._kurs = lambda inst: 100.5
        z = {"positionen": [position(modus="live")], "letzte_stops": {}}
        h.flach_stellen(z, True, "kill_switch")
        self.assertEqual(len(self.aufrufe), 1)
        self.assertEqual(self.aufrufe[0][0], "markt_schliessen")

    def test_eroeffnen_fehler_hinterlaesst_keine_position(self):
        def kaputt(*a, **kw):
            raise RuntimeError("OKX nicht erreichbar")
        okxf.hebel_setzen = kaputt
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [KAND], WACHEN, True,
                           {"wochenende": False}, 1.0)
        self.assertEqual(z["positionen"], [])


if __name__ == "__main__":
    unittest.main()
