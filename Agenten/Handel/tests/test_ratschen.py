"""Tests fuer ratschen.py - die eine Umsetzung, an der fuenf Spuren haengen.

Diese Suite prueft die geteilte Umsetzung DIREKT, nicht ueber eine Spur. Der
scanner hat die Ratsche heute zweimal falsch gehabt (erst an den Kapitaldeckel
gekoppelt, dann mit dem falschen Wort beschrieben); die uebrigen Spuren haben
sie uebernommen. Ein Fehler hier trifft alle.

Ausfuehren aus dem Ordner Handel/tests:
    ..\\scanner\\.venv\\Scripts\\python.exe -m unittest test_ratschen -v
"""

import os
import sys
import unittest
from importlib.util import module_from_spec, spec_from_file_location

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)

_s = spec_from_file_location("ratschen", os.path.join(HANDEL, "ratschen.py"))
R = module_from_spec(_s)
_s.loader.exec_module(R)


class BuchrisikoTest(unittest.TestCase):
    def test_paar_wird_multipliziert(self):
        w = {"risiko_je_position_usd": 6.0, "max_offene_positionen": 6}
        self.assertEqual(R.buch_risiko(w), 36.0)

    def test_zweites_namenspaar_gilt_ebenso(self):
        """Die Spuren nennen dieselbe Sache verschieden - die Bedeutung zaehlt."""
        w = {"risiko_je_anlauf_usd": 7.5, "max_offene_anlaeufe": 4}
        self.assertEqual(R.buch_risiko(w), 30.0)

    def test_ausdrueckliches_gesamtrisiko_gilt(self):
        self.assertEqual(R.buch_risiko({"max_risiko_gesamt_usd": 200.0}), 200.0)

    def test_nur_eine_der_beiden_zahlen_ist_nicht_herleitbar(self):
        """orbk nennt das Risiko, aber keine Positionszahl - raten waere
        schlimmer als zugeben, dass es nicht herleitbar ist."""
        self.assertIsNone(R.buch_risiko({"risiko_pro_trade_usd": 10.0}))
        self.assertIsNone(R.buch_risiko({"max_offene_positionen": 4}))

    def test_leere_wachen(self):
        self.assertIsNone(R.buch_risiko({}))


class SchwelleTest(unittest.TestCase):
    def test_ausdruecklicher_betrag_hat_vorrang(self):
        w = {"drawdown_halbierung_usd": 36.0,
             "risiko_je_position_usd": 6.0, "max_offene_positionen": 6}
        self.assertEqual(R.halbierungsschwelle(w), 36.0)

    def test_ohne_betrag_aus_dem_buchrisiko(self):
        w = {"risiko_je_position_usd": 6.0, "max_offene_positionen": 6}
        self.assertEqual(R.halbierungsschwelle(w), 36.0)

    def test_kapitaldeckel_verschiebt_nichts(self):
        """Der Fehler, der diese Datei ausgeloest hat. max_gesamt_usd darf die
        Schwelle NICHT bewegen - es ist der Deckel, nicht das Risiko."""
        eng = {"risiko_je_position_usd": 6.0, "max_offene_positionen": 6,
               "max_gesamt_usd": 400}
        weit = {"risiko_je_position_usd": 6.0, "max_offene_positionen": 6,
                "max_gesamt_usd": 10000}
        self.assertEqual(R.halbierungsschwelle(eng), R.halbierungsschwelle(weit))

    def test_prozentsatz_wird_nicht_gelesen(self):
        w = {"drawdown_halbierung_prozent": 15.0, "max_gesamt_usd": 400}
        self.assertIsNone(R.halbierungsschwelle(w))

    def test_null_ist_keine_schwelle(self):
        """0 als Betrag haette jede Position sofort halbiert."""
        self.assertIsNone(R.halbierungsschwelle({"drawdown_halbierung_usd": 0}))
        self.assertIsNone(R.halbierungsschwelle({"drawdown_halbierung_usd": -5}))

    def test_ohne_angabe_keine_erfundene_schwelle(self):
        self.assertIsNone(R.halbierungsschwelle({}))

    def test_faktor_skaliert_das_buchrisiko(self):
        w = {"risiko_je_position_usd": 6.0, "max_offene_positionen": 6,
             "drawdown_halbierung_im_buchrisiko": 2.0}
        self.assertEqual(R.halbierungsschwelle(w), 72.0)

    def test_unlesbarer_wert_gibt_keine_schwelle(self):
        self.assertIsNone(R.halbierungsschwelle({"drawdown_halbierung_usd": "viel"}))


class GroessenfaktorTest(unittest.TestCase):
    W = {"drawdown_halbierung_usd": 36.0}

    def test_darunter_volle_groesse(self):
        self.assertEqual(R.groessenfaktor(35.99, self.W), 1.0)

    def test_genau_auf_der_schwelle_halbiert(self):
        self.assertEqual(R.groessenfaktor(36.0, self.W), 0.5)

    def test_ohne_schwelle_volle_groesse(self):
        """Fehlende Konfiguration darf den Handel nicht drosseln."""
        self.assertEqual(R.groessenfaktor(9999.0, {}), 1.0)

    def test_uebergebenes_none_drosselt_nicht(self):
        self.assertEqual(R.groessenfaktor(9999.0, {}, None), 1.0)

    def test_uebergebene_schwelle_hat_vorrang(self):
        """Der scanner reicht seine eigene Schwelle durch, damit nicht zweimal
        gerechnet wird."""
        self.assertEqual(R.groessenfaktor(10.0, self.W, 5.0), 0.5)


class GewinnschutzTest(unittest.TestCase):
    """'Erreichbar' waere das falsche Wort: drawdown() rechnet hoch minus kum,
    und die kumulierte Kurve darf ins Minus laufen. Die Frage ist, ob die
    Halbierung noch greift, SOLANGE die Spur im Gewinn ist."""

    W = {"drawdown_halbierung_usd": 36.0}

    def test_schwelle_unter_dem_hoechststand_greift_im_gewinn(self):
        self.assertTrue(R.im_gewinn(140.24, self.W))

    def test_schwelle_ueber_dem_hoechststand_greift_erst_im_minus(self):
        self.assertFalse(R.im_gewinn(0.16, self.W))

    def test_ohne_hoechststand_kein_falscher_alarm(self):
        """kraken hat noch keine Runden und liefert None - das ist kein
        Fehlerfall und darf keinen Absturz geben."""
        self.assertTrue(R.im_gewinn(None, self.W))
        self.assertTrue(R.im_gewinn(0, self.W))

    def test_ohne_schwelle_kein_alarm(self):
        self.assertTrue(R.im_gewinn(1.0, {}))


class ZusammenarbeitTest(unittest.TestCase):
    """Die Werte, die nach der Migration tatsaechlich in den wachen.json
    stehen, muessen reproduzierbar sein. Wenn diese Tests fallen, ist eine
    Spur umgestellt worden - dann gehoert pruefe_ratschen.py mitgelesen."""

    ERWARTET = {
        # scanner: 20.09.2026 auf 5 Plaetze umgestellt (Max: "600 gesamt,
        # 120 pro Trade, 5") - Buchrisiko 6.0 x 5 = 30.0 statt 36.0.
        "scanner": 30.0,
        "xperp": 30.0,
        "swap": 30.0,
        "orbk": 10.0,
        "kraken": 24.0,
        # signalwelle: 20.09.2026 neu, 5.0 x 3 Plaetze = 15.0.
        "moondev_signalwelle": 15.0,
    }

    def test_jede_spur_ergibt_ihren_betriebswert(self):
        import json
        for spur, erwartet in self.ERWARTET.items():
            p = os.path.join(HANDEL, spur, "wachen.json")
            if not os.path.exists(p):
                self.skipTest("%s fehlt" % spur)
            with open(p, "r", encoding="utf-8") as f:
                w = json.load(f)
            self.assertEqual(R.halbierungsschwelle(w), erwartet,
                             "%s: Schwelle hat sich verschoben" % spur)

    def test_jede_spur_ist_herleitbar(self):
        """Keine Spur steht mehr ohne Buchrisiko da: orbk hat eine
        Positionszahl, kraken ein Risiko je Position bekommen. Waere das
        wieder weg, muesste die Schwelle ausdruecklich hingeschrieben werden
        und die Ratsche haenge an einer fremden Groesse."""
        import json
        for spur in self.ERWARTET:
            with open(os.path.join(HANDEL, spur, "wachen.json"),
                      "r", encoding="utf-8") as f:
                w = json.load(f)
            self.assertIsNotNone(R.buch_risiko(w),
                                 "%s: Buchrisiko nicht herleitbar" % spur)

    def test_keine_spur_liest_noch_den_prozentsatz(self):
        """Der Schluessel ist ueberall entfallen - ausser bei orb, das ruht."""
        import json
        for spur in self.ERWARTET:
            with open(os.path.join(HANDEL, spur, "wachen.json"),
                      "r", encoding="utf-8") as f:
                w = json.load(f)
            self.assertNotIn("drawdown_halbierung_prozent", w,
                             "%s fuehrt noch den toten Prozentsatz" % spur)


if __name__ == "__main__":
    unittest.main()
