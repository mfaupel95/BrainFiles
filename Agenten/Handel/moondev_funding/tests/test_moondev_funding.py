"""Tests fuer die Moon-Dev-Funding-Spur - ohne Netz, ohne den Bot.

Die Spur holt ihre Zahlen aus dem geklonten Fremd-Repo. Im Test wird diese
Quelle durch ein Lambda ersetzt (`funding_quelle`): sonst haengt jeder Test an
einer fremden Datei und an einer lebenden Boerse, und ein umbenanntes
Fremd-Repo waere ein roter Test statt einer Fehlermeldung im Betrieb.

Was hier belegt wird:
  * die Jahres-Rechnung des Bots (Rate * 24 * 365 * 100),
  * die Richtung (positiv -> short, negativ -> long, unter der Schwelle nichts),
  * Einstieg, Stop, Ziel und Nominal in Prozent,
  * Ausstieg an Stop und Ziel mit G/V auf den NOMINALWERT,
  * dass --vorschau nichts schreibt und die Dateien getrennt liegen.
"""

import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
# Reihenfolge: zuletzt eingefuegt = vorne. SPUR MUSS vorne stehen, sonst
# gewinnt scanner/handeln.py gegen das handeln.py dieser Spur.
for p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln as h  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py geladen: %s" % h.__file__


def _bestand(ordner):
    """Dateien (Name, Groesse) eines Ordners - ohne Zwischenspeicher."""
    aus = {}
    for name in sorted(os.listdir(ordner)):
        p = os.path.join(ordner, name)
        if os.path.isfile(p) and not name.endswith((".pyc", ".bak-20260915",
                                                    ".bak-20260916")):
            aus[name] = os.path.getsize(p)
    return aus


_ECHT_VORHER = None


def setUpModule():
    """Vor dem ersten Test: den echten Spurenordner merken.

    Ein Test, der in den ECHTEN Ordner schreibt, faellt sonst niemandem auf -
    er sieht aus wie ein normaler Lauf und legt Testbuchungen ins Journal, die
    spaeter als Handelsrunden gezaehlt werden (genau das passierte beim ersten
    Anlauf dieser Spur: 16 Zeilen mit Testkursen im echten Journal).
    """
    global _ECHT_VORHER
    _ECHT_VORHER = _bestand(SPUR)


def tearDownModule():
    nachher = _bestand(SPUR)
    assert nachher == _ECHT_VORHER, (
        "Ein Test hat in den echten Spurenordner geschrieben!\nvorher: %s\nnachher: %s"
        % (_ECHT_VORHER, nachher))

WACHEN = {
    "waehrung": "USD",
    "handel_erlaubt": False,
    "risiko_je_position_usd": 5.0,
    "max_offene_positionen": 3,
    "max_pro_trade_usd": 100.0,
    "max_gesamt_usd": 300.0,
    "kill_switch_gesamt_usd": 45.0,
    "stop_prozent": 6.0,
    "pflicht_stop_prozent_min": 5.0,
    "pflicht_stop_prozent_max": 12.0,
    "ziel_r_vielfaches": 1.5,
    "funding_schwelle_jahr_pct": 100.0,
    "instrumente": ["BTC", "ETH", "SOL"],
    " drawdown_halbierung_usd": 15.0,
    "drawdown_halbierung_usd": 15.0,
}


def kurse(btc=60_000.0, eth=3_000.0, sol=150.0):
    return {"BTC": {"funding_rate": 0.0, "mark_price": btc, "open_interest": 1.0},
            "ETH": {"funding_rate": 0.0, "mark_price": eth, "open_interest": 1.0},
            "SOL": {"funding_rate": 0.0, "mark_price": sol, "open_interest": 1.0}}


class JahresRechnungTest(unittest.TestCase):
    def test_stundenrate_auf_jahr(self):
        # 0,0001 % je Stunde -> 0,0001 * 24 * 365 = 0,876 % im Jahr.
        pct = h.jahres_funding_pct({"funding_rate": 0.000001})
        self.assertAlmostEqual(pct, 0.000001 * 24 * 365 * 100, places=6)

    def test_ohne_daten_keine_zahl(self):
        self.assertIsNone(h.jahres_funding_pct(None))
        self.assertIsNone(h.jahres_funding_pct({}))

    def test_richtung_nach_der_regel_des_bots(self):
        w = dict(WACHEN)
        # 200 %/Jahr: ueber der Schwelle -> short (Funding von den Longs).
        self.assertEqual(h.richtung(200.0, w), "short")
        self.assertEqual(h.richtung(-200.0, w), "long")
        self.assertIsNone(h.richtung(99.9, w))
        self.assertIsNone(h.richtung(-99.9, w))
        self.assertIsNone(h.richtung(None, w))


class EinstiegTest(unittest.TestCase):
    def setUp(self):
        self.z = {"positionen": []}
        # pruefe_einstieg() schreibt eine Journalzeile. Ohne diesen Schalter
        # landete sie in der ECHTEN Journaldatei der Spur (siehe setUpModule).
        self.alt_schreiben = h.SCHREIBEN
        h.SCHREIBEN = False

    def tearDown(self):
        h.SCHREIBEN = self.alt_schreiben

    def test_short_bei_hohem_funding(self):
        d = {"funding_rate": 200.0 / (24 * 365 * 100), "mark_price": 100.0}
        h.pruefe_einstieg("BTC", d, self.z, dict(WACHEN), 1.0)
        (p,) = self.z["positionen"]
        self.assertEqual(p["seite"], "short")
        self.assertEqual(p["inst"], "BTC")
        self.assertAlmostEqual(p["einstieg"], 100.0)
        # Stop 6 % ueber dem Einstieg, Ziel 1.5 * 6 % darunter.
        self.assertAlmostEqual(p["stop"], 106.0, places=6)
        self.assertAlmostEqual(p["ziel"], 100.0 - 1.5 * 6.0, places=6)
        self.assertAlmostEqual(p["nominal"], 5.0 / 0.06, places=4)

    def test_kein_einstieg_unter_der_schwelle(self):
        d = {"funding_rate": 50.0 / (24 * 365 * 100), "mark_price": 100.0}
        h.pruefe_einstieg("BTC", d, self.z, dict(WACHEN), 1.0)
        self.assertEqual(self.z["positionen"], [])

    def test_kein_zweiter_einstieg_im_selben_instrument(self):
        d = {"funding_rate": 300.0 / (24 * 365 * 100), "mark_price": 100.0}
        h.pruefe_einstieg("BTC", d, self.z, dict(WACHEN), 1.0)
        h.pruefe_einstieg("BTC", d, self.z, dict(WACHEN), 1.0)
        self.assertEqual(len(self.z["positionen"]), 1)

    def test_buch_voll(self):
        w = dict(WACHEN)
        w["max_offene_positionen"] = 1
        d = {"funding_rate": 300.0 / (24 * 365 * 100), "mark_price": 100.0}
        h.pruefe_einstieg("BTC", d, self.z, w, 1.0)
        h.pruefe_einstieg("ETH", d, self.z, w, 1.0)
        self.assertEqual(len(self.z["positionen"]), 1)

    def test_ratsche_halbiert_das_nominal(self):
        d = {"funding_rate": 300.0 / (24 * 365 * 100), "mark_price": 100.0}
        h.pruefe_einstieg("BTC", d, self.z, dict(WACHEN), 0.5)
        self.assertAlmostEqual(self.z["positionen"][0]["nominal"], 5.0 / 0.06 * 0.5,
                               places=4)


class AusstiegTest(unittest.TestCase):
    def setUp(self):
        self.alt_schreiben = h.SCHREIBEN
        h.SCHREIBEN = False

    def tearDown(self):
        h.SCHREIBEN = self.alt_schreiben

    def _position(self, seite="long", einstieg=100.0, stop=94.0, ziel=109.0):
        return {"positionen": [{"inst": "BTC", "seite": seite,
                                "einstieg": einstieg, "stop": stop, "ziel": ziel,
                                "stop_pct": 6.0, "nominal": 100.0,
                                "eroeffnet_zeit": "2026-01-01T00:00:00+00:00"}]}

    def test_long_stop_und_gv_auf_dem_nominal(self):
        z = self._position()
        h.pruefe_ausstiege(z, {"BTC": 94.0}, dict(WACHEN))
        self.assertEqual(z["positionen"], [])
        # 6 % Verlust auf 100 USD Nominal = -6.00 USD, nicht -6 Kurspunkte.
        # Das Journal ist hier abgeschaltet (SCHREIBEN False in setUp).

    def test_long_ziel(self):
        z = self._position()
        h.pruefe_ausstiege(z, {"BTC": 109.0}, dict(WACHEN))
        self.assertEqual(z["positionen"], [])

    def test_short_ziel_und_stop_gespiegelt(self):
        z = self._position(seite="short", stop=106.0, ziel=91.0)
        h.pruefe_ausstiege(z, {"BTC": 91.0}, dict(WACHEN))
        self.assertEqual(z["positionen"], [])
        z = self._position(seite="short", stop=106.0, ziel=91.0)
        h.pruefe_ausstiege(z, {"BTC": 106.5}, dict(WACHEN))
        self.assertEqual(z["positionen"], [])

    def test_kein_kurs_haelt_die_position(self):
        z = self._position()
        h.pruefe_ausstiege(z, {}, dict(WACHEN))
        self.assertEqual(len(z["positionen"]), 1)

    def test_zwischen_stop_und_ziel_passiert_nichts(self):
        z = self._position()
        h.pruefe_ausstiege(z, {"BTC": 101.0}, dict(WACHEN))
        self.assertEqual(len(z["positionen"]), 1)


class DateienTest(unittest.TestCase):
    """Die Spur schreibt in ihre eigenen Dateien - und nur dort."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (h.SCHREIBEN, h.ZUSTAND, h.JOURNAL, h.WACHEN, h.funding_quelle)
        h.SCHREIBEN = True
        h.ZUSTAND = os.path.join(self.tmp.name, "zustand.json")
        h.JOURNAL = os.path.join(self.tmp.name, "handelsjournal.csv")
        h.WACHEN = os.path.join(self.tmp.name, "wachen.json")
        w = dict(WACHEN)
        w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")
        with open(h.WACHEN, "w", encoding="utf-8") as f:
            json.dump(w, f)

    def tearDown(self):
        (h.SCHREIBEN, h.ZUSTAND, h.JOURNAL, h.WACHEN, h.funding_quelle) = self.alt
        self.tmp.cleanup()

    def test_vorschau_schreibt_nichts(self):
        h.funding_quelle = lambda s: {"funding_rate": 300.0 / (24 * 365 * 100),
                                      "mark_price": 100.0}
        h.lauf("vorschau")
        self.assertFalse(os.path.exists(h.JOURNAL))
        self.assertFalse(os.path.exists(h.ZUSTAND))

    def test_papierlauf_bucht_und_spiegelt(self):
        h.funding_quelle = lambda s: {"funding_rate": 300.0 / (24 * 365 * 100),
                                      "mark_price": 100.0}
        h.lauf("papier")
        self.assertTrue(os.path.exists(h.JOURNAL))
        self.assertTrue(os.path.exists(h.ZUSTAND))
        with open(h.ZUSTAND, encoding="utf-8") as f:
            z = json.load(f)
        self.assertEqual(len(z["positionen"]), 3)          # BTC, ETH, SOL
        self.assertTrue(all(p["seite"] == "short" for p in z["positionen"]))
        # Bedingung 4: die Kopie liegt im Zweitziel.
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, "zweitziel",
                                                    "handelsjournal.csv")))

    def test_quelle_fehler_bricht_nicht_ab(self):
        def kaputt(_s):
            raise RuntimeError("Boerse weg")
        h.funding_quelle = kaputt
        h.lauf("papier")                                    # darf nicht werfen
        self.assertFalse(os.path.exists(h.JOURNAL))


if __name__ == "__main__":
    unittest.main(verbosity=2)
