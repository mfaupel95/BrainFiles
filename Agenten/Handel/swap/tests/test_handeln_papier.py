"""Tests fuer swap/handeln.py - Papierpfad, ohne Netz, ohne Order.

Der Order-Pfad wird nicht benutzt, sondern geprueft: Die vier Funktionen, die
Geld bewegen, sind im Modul stillgelegt, und die Papierspur kennt keinen
Live-Zweig. Ein Test, der eine Order erreichen koennte, waere der Fehler.
"""

import ast
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
SWAP = os.path.dirname(HIER)
if SWAP not in sys.path:
    sys.path.insert(0, SWAP)

import handeln as h                                          # noqa: E402
import okxf                                                  # noqa: E402

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
         "funding_zuletzt": "2026-09-11T10:00:00+00:00", "funding_summe": 0.0}
    p.update(over)
    return p


def gedruckte_zeilen(pfad):
    """Alle Zeichenketten, die das Modul druckt - aus dem Quelltext geholt.

    Nicht die Datei als Ganzes durchsuchen: Der Modulkopf erklaert die Regel
    und nennt dabei genau die Woerter, um die es geht. Ein Test ueber den
    ganzen Quelltext schlaegt deshalb fehl, ohne dass etwas kaputt ist - und
    ein Test, der dann abgeschwaecht wird, prueft nichts mehr. Gedruckt wird
    nur, was in einem print()-Aufruf steht; das ist genau das, was der
    Dauerlauf liest.
    """
    with open(pfad, encoding="utf-8") as f:
        baum = ast.parse(f.read())
    aus = []
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Call) and getattr(knoten.func, "id", "") == "print":
            for arg in knoten.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    aus.append(arg.value)
    return aus


class Sicherheitsnetz(unittest.TestCase):

    def test_die_vier_order_funktionen_sind_stillgelegt(self):
        for name in ("order_limit", "markt_schliessen", "hebel_setzen",
                     "order_stornieren"):
            with self.assertRaises(h.Papierfehler, msg=name):
                getattr(okxf, name)("XAU-USDT-SWAP", 1, "long")

    def test_papierspur_kennt_keinen_live_zweig(self):
        with open(os.path.join(SWAP, "handeln.py"), encoding="utf-8") as f:
            quelle = f.read()
        for verbot in ("live = True", "live=True", "if live:"):
            self.assertNotIn(verbot, quelle)

    def test_live_verweigert_mit_einem_grund_ohne_das_wort_freigabefenster(self):
        """Sonst fragt der Dauerlauf eine Freigabe an, die nichts oeffnen kann.

        Geprueft wird die Ausgabe, nicht die Datei: dauerlauf.nur_fenster_fehlt
        liest stdout und stellt nur dann eine Anfrage, wenn dort genau EIN
        Grund steht und dieser das Wort Freigabefenster traegt. Beide gedruckten
        Zeilen, die der Dauerlauf zu sehen bekommt, muessen das einhalten - die
        aus --vorschau (die er liest) und die aus --live (die er ausloest).
        """
        zeilen = gedruckte_zeilen(os.path.join(SWAP, "handeln.py"))
        vorschau = [z for z in zeilen if "gesperrt durch" in z]
        self.assertEqual(len(vorschau), 1, vorschau)
        gruende = [g.strip() for g in vorschau[0].split(":", 1)[-1].split(";")]
        self.assertEqual(len(gruende), 1, gruende)
        self.assertIn("kein Live-Pfad in dieser Spur (Papier)", gruende[0])
        for z in zeilen:
            if "kein Live-Pfad" in z:
                self.assertNotIn("Freigabefenster", z)


class Papierlauf(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (h.ZUSTAND, h.JOURNAL, h.anlauf, h._kurs)
        h.ZUSTAND = os.path.join(self.tmp.name, "zustand.json")
        h.JOURNAL = os.path.join(self.tmp.name, "handelsjournal.csv")
        h.anlauf = anlauf_stummel

    def tearDown(self):
        h.ZUSTAND, h.JOURNAL, h.anlauf, h._kurs = self.alt
        self.tmp.cleanup()

    def journal_zeilen(self):
        with open(h.JOURNAL, encoding="utf-8") as f:
            return f.read().splitlines()

    # --- Einstieg ---

    def test_papier_einstieg_legt_position_und_journalzeile_an(self):
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [KAND], WACHEN, {"wochenende": False}, 1.0)
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        for feld in ("inst", "basis", "seite", "familie", "einstieg", "stop",
                     "ziel", "liq", "kontrakte", "nominal", "margin", "hebel",
                     "gebuehr_taker", "eroeffnet", "eroeffnet_zeit"):
            self.assertIn(feld, p)
        zeilen = self.journal_zeilen()
        self.assertEqual(len(zeilen), 2)          # Kopfzeile + Eroeffnung
        self.assertIn("eroeffnen", zeilen[1])
        self.assertIn("XAU-USDT-SWAP", zeilen[1])

    def test_wochenende_sperrt_aktie_und_rohstoff_nicht_krypto(self):
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [dict(KAND, kategorie="rohstoff")], WACHEN,
                           {"wochenende": True}, 1.0)
        self.assertEqual(z["positionen"], [])
        h.pruefe_einstiege(z, [KAND], WACHEN, {"wochenende": True}, 1.0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_kein_zweiter_anlauf_in_dieselbe_reihe(self):
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [KAND, KAND], WACHEN, {"wochenende": False}, 1.0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_ohne_tragende_quote_kein_anlauf(self):
        z = {"positionen": [], "letzte_stops": {}}
        alt = anlauf_stummel(WACHEN, KAND)
        alt["pflicht"] = dict(alt["pflicht"], traegt=False)
        h.anlauf = lambda w, k: alt
        h.pruefe_einstiege(z, [KAND], WACHEN, {"wochenende": False}, 1.0)
        self.assertEqual(z["positionen"], [])

    def test_rahmen_ist_bei_zwei_anlaeufen_zu(self):
        z = {"positionen": [position(), position(inst="BTC-USDT-SWAP", basis="BTC")],
             "letzte_stops": {}}
        h.pruefe_einstiege(z, [KAND], WACHEN, {"wochenende": False}, 1.0)
        self.assertEqual(len(z["positionen"]), 2)

    # --- Ausstieg ---

    def test_stop_schliesst_die_papierposition_und_setzt_die_abklingzeit(self):
        h._kurs = lambda inst: 96.0
        z = {"positionen": [position()], "letzte_stops": {}}
        h.pruefe_ausstiege(z, WACHEN)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(z["letzte_stops"]["XAU"],
                         datetime.now(timezone.utc).date().isoformat())
        self.assertIn("stop", self.journal_zeilen()[1])

    def test_ziel_schliesst_ohne_abklingzeit(self):
        h._kurs = lambda inst: 107.0
        z = {"positionen": [position()], "letzte_stops": {}}
        h.pruefe_ausstiege(z, WACHEN)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(z["letzte_stops"], {})
        self.assertIn("ziel", self.journal_zeilen()[1])

    def test_liquidation_ist_ein_eigener_grund(self):
        h._kurs = lambda inst: 80.0
        z = {"positionen": [position()], "letzte_stops": {}}
        h.pruefe_ausstiege(z, WACHEN)
        self.assertIn("LIQUIDATION", self.journal_zeilen()[1])

    def test_position_bleibt_wenn_kein_kurs_kommt(self):
        def platzt(inst):
            raise RuntimeError("kein Netz")
        h._kurs = platzt
        z = {"positionen": [position()], "letzte_stops": {}}
        h.pruefe_ausstiege(z, WACHEN)
        self.assertEqual(len(z["positionen"]), 1)

    def test_ergebnis_rechnet_gebuehr_beim_schliessen_ab(self):
        # 10 % im Plus auf 100 USD Nominal = 10 USD, minus 0,05 USD Taker
        erloes = h._ergebnis(position(), 110.0)
        self.assertAlmostEqual(erloes, 20.0 + 10.0 - 0.05, places=6)

    def test_short_dreht_das_vorzeichen(self):
        p = position(seite="short")
        self.assertAlmostEqual(h._ergebnis(p, 90.0), 20.0 + 10.0 - 0.05, places=6)

    def test_notausstieg_raeumt_alles(self):
        h._kurs = lambda inst: 100.5
        z = {"positionen": [position(), position(inst="BTC-USDT-SWAP", basis="BTC")],
             "letzte_stops": {}}
        h.flach_stellen(z, "kill_switch")
        self.assertEqual(z["positionen"], [])
        self.assertEqual(len(self.journal_zeilen()), 3)   # Kopf + zwei Zeilen

    # --- Sperren ---

    def test_abklingzeit_gilt_fuer_den_stoptag(self):
        heute = datetime.now(timezone.utc).date().isoformat()
        alt = (datetime.now(timezone.utc).date() - timedelta(days=5)).isoformat()
        z = {"letzte_stops": {"XAU": heute, "BTC": alt}}
        self.assertTrue(h.in_abklingzeit("XAU", z, WACHEN))
        self.assertFalse(h.in_abklingzeit("BTC", z, WACHEN))
        self.assertFalse(h.in_abklingzeit("ETH", z, WACHEN))


if __name__ == "__main__":
    unittest.main()
