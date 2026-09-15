"""Tests fuer die Risikostufen (Agenten/Handel/risikostufe.py).

WARUM DIESE TESTS
-----------------
Die Stufen skalieren Geldbetraege in einer laufenden Handelssimulation. Zwei
Fehler waeren hier teuer:
1. Ein Feld skalieren, das gar kein Einsatz ist (Marktkapazitaet, Messwert,
   Kontoschwelle) - dann handelt die Spur aus einem falschen Grund.
2. Die Ratsche (drawdown_halbierung_usd) oder den Kill-Schalter stehen lassen -
   dann sperrt die doppelte Position sich selbst und die Stufe liefert keine
   Daten mehr.

Der wichtigste Test ist deshalb der GEGEN DIE ECHTEN WACHEN: er laeuft ueber
jede vorhandene wachen.json und prueft beide Richtungen.
"""

import glob
import json
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import risikostufe  # noqa: E402


class StufenTest(unittest.TestCase):

    def setUp(self):
        self.alt = os.environ.get("HANDEL_RISIKO")
        os.environ.pop("HANDEL_RISIKO", None)

    def tearDown(self):
        if self.alt is None:
            os.environ.pop("HANDEL_RISIKO", None)
        else:
            os.environ["HANDEL_RISIKO"] = self.alt

    def test_ohne_variable_ist_basis(self):
        self.assertEqual(risikostufe.stufe(), "niedrig")
        self.assertEqual(risikostufe.faktor(), 1.0)
        self.assertTrue(risikostufe.ist_basis())
        self.assertEqual(risikostufe.suffix(), "")

    def test_tippfehler_bleibt_basis(self):
        # "mitel" darf nicht als 4x durchgehen.
        os.environ["HANDEL_RISIKO"] = "mitel"
        self.assertEqual(risikostufe.stufe(), "niedrig")
        self.assertEqual(risikostufe.faktor(), 1.0)

    def test_faktoren(self):
        for stufe, faktor in (("niedrig", 1.0), ("mittel", 2.0), ("hoch", 4.0)):
            os.environ["HANDEL_RISIKO"] = stufe
            self.assertEqual(risikostufe.faktor(), faktor)

    def test_basis_aendert_nichts(self):
        w = {"risiko_je_position_usd": 6.0, "marketcap_band_usd": [50000, 1000000]}
        self.assertEqual(risikostufe.skaliere(w), w)

    def test_mittel_verdoppelt_das_risiko(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        w = {"risiko_je_position_usd": 6.0, "max_pro_trade_usd": 120,
             "drawdown_halbierung_usd": 36.0, "kill_switch_gesamt_usd": 200}
        aus = risikostufe.skaliere(w)
        self.assertEqual(aus["risiko_je_position_usd"], 12.0)
        self.assertEqual(aus["max_pro_trade_usd"], 240)
        # Die Ratsche MUSS mit: sonst sperrt die doppelte Position sich selbst.
        self.assertEqual(aus["drawdown_halbierung_usd"], 72.0)
        self.assertEqual(aus["kill_switch_gesamt_usd"], 400)
        # Vorlage unveraendert - sonst waere die Basis nach einem Aufruf kaputt.
        self.assertEqual(w["risiko_je_position_usd"], 6.0)

    def test_marktdaten_bleiben(self):
        os.environ["HANDEL_RISIKO"] = "hoch"
        w = {"marketcap_band_usd": [50000, 1000000],
             "groesster_ruecklauf_papierlauf_usd": 3.21,
             "mindest_guthaben_eur": 10.0,
             "umsatz_bezug_usd": 10000,
             "punkt_wert_usd": 0.01,
             "risiko_je_position_usd": 6.0}
        aus = risikostufe.skaliere(w)
        self.assertEqual(aus["marketcap_band_usd"], [50000, 1000000])
        self.assertEqual(aus["groesster_ruecklauf_papierlauf_usd"], 3.21)
        self.assertEqual(aus["mindest_guthaben_eur"], 10.0)
        self.assertEqual(aus["umsatz_bezug_usd"], 10000)
        self.assertEqual(aus["punkt_wert_usd"], 0.01)
        self.assertEqual(aus["risiko_je_position_usd"], 24.0)

    def test_dokumentierte_vorwerte_bleiben(self):
        # Felder mit fuehrendem Unterstrich sind der dokumentierte Vorwert.
        os.environ["HANDEL_RISIKO"] = "hoch"
        w = {"_risiko_je_position_usd": 6.0, "_max_pro_trade_usd": 120}
        self.assertEqual(risikostufe.skaliere(w), w)

    def test_texte_und_listen_bleiben(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        w = {"handel_erlaubt": False, "modus": "papier", "paare": ["BTC/USD"],
             "risiko_je_position_usd": 6.0}
        aus = risikostufe.skaliere(w)
        self.assertIs(aus["handel_erlaubt"], False)
        self.assertEqual(aus["modus"], "papier")
        self.assertEqual(aus["paare"], ["BTC/USD"])

    def test_dateiname_bekommt_suffix(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        self.assertTrue(risikostufe.datei("C:/x/zustand.json").endswith("zustand.mittel.json"))
        self.assertTrue(risikostufe.datei("C:/x/handelsjournal.csv").endswith("handelsjournal.mittel.csv"))
        os.environ["HANDEL_RISIKO"] = "niedrig"
        self.assertTrue(risikostufe.datei("C:/x/zustand.json").endswith("zustand.json"))
        self.assertNotIn(".niedrig", risikostufe.datei("C:/x/zustand.json"))

    def test_never_liste_gewinnt(self):
        # Beide Listen zusammen: NIE gewinnt. Doppelte Eintraege sind also
        # harmlos, statt still zu skalieren.
        for feld in risikostufe.NIE_SKALIEREN:
            self.assertNotIn(feld, risikostufe.SKALIEREN, feld)


class EchteWachenTest(unittest.TestCase):
    """Der eigentliche Nachweis: gegen jede vorhandene wachen.json."""

    def setUp(self):
        self.alt = os.environ.get("HANDEL_RISIKO")

    def tearDown(self):
        if self.alt is None:
            os.environ.pop("HANDEL_RISIKO", None)
        else:
            os.environ["HANDEL_RISIKO"] = self.alt

    def _wachen(self):
        for pfad in sorted(glob.glob(os.path.join(HANDEL, "*", "wachen.json"))):
            try:
                with open(pfad, "r", encoding="utf-8") as f:
                    yield pfad, json.load(f)
            except (OSError, ValueError) as fehler:
                raise AssertionError("wachen.json nicht lesbar: %s (%s)" % (pfad, fehler))

    def test_mindestens_zehn_wachen_vorhanden(self):
        self.assertGreaterEqual(len(list(self._wachen())), 10)

    def test_verdoppelt_genau_das_risiko(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        getroffen = 0
        for pfad, w in self._wachen():
            aus = risikostufe.skaliere(w)
            for feld in ("risiko_je_position_usd", "risiko_je_position_eur",
                         "risiko_pro_trade_usd", "risiko_je_anlauf_usd"):
                if isinstance(w.get(feld), (int, float)):
                    getroffen += 1
                    self.assertAlmostEqual(aus[feld], w[feld] * 2, places=4,
                                           msg="%s: %s" % (pfad, feld))
        self.assertGreater(getroffen, 0, "kein Risikofeld in den Wachen gefunden?")

    def test_marktkapazitaet_bleibt_ueberall(self):
        os.environ["HANDEL_RISIKO"] = "hoch"
        for pfad, w in self._wachen():
            aus = risikostufe.skaliere(w)
            if "marketcap_band_usd" in w:
                self.assertEqual(aus["marketcap_band_usd"], w["marketcap_band_usd"], pfad)

    def test_ratsche_und_kill_wachsen_mit(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        geprueft = 0
        for pfad, w in self._wachen():
            aus = risikostufe.skaliere(w)
            for feld in ("drawdown_halbierung_usd", "kill_switch_gesamt_usd"):
                if isinstance(w.get(feld), (int, float)):
                    geprueft += 1
                    self.assertAlmostEqual(aus[feld], w[feld] * 2, places=4, msg=pfad)
        self.assertGreater(geprueft, 0)

    def test_struktur_bleibt_gleich(self):
        # Kein Feld darf verschwinden oder dazukommen - sonst liest eine Spur
        # ploetzlich ins Leere.
        os.environ["HANDEL_RISIKO"] = "hoch"
        for pfad, w in self._wachen():
            self.assertEqual(set(risikostufe.skaliere(w).keys()), set(w.keys()), pfad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
