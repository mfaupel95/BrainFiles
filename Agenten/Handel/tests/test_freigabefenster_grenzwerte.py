"""anfrage_text() liefert nach dem Herausziehen von grenzwerte() denselben Text.

Die goldenen Texte stammen aus dem Code vor der Aenderung (Stand 3d70c36,
29.09.2026). anfrage_text liest keine Datei - kein Temp-Ordner noetig.

Direkt ausfuehrbar:  python tests/test_freigabefenster_grenzwerte.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import freigabefenster as ff                                   # noqa: E402

W_XPERP = {"max_pro_trade_usd": 50, "max_gesamt_usd": 200,
           "max_offene_positionen": 3, "max_hebel": 5,
           "kill_switch_gesamt_usd": 100}

GOLD_XPERP = (
    "<b>Freigabe xperp?</b>\n"
    "Dauer: 1:30 h\n"
    "\n"
    "Es gelten die Grenzen aus wachen.json:\n"
    "  je Anlauf          50 USD\n"
    "  gesamt             200 USD\n"
    "  Positionen         3 \n"
    "  Hebel bis          5 x\n"
    "  Kill-Switch        100 USD\n"
    "\n"
    "/ja        freigeben fuer 1:30 h\n"
    "/ja 6      stattdessen 6 Stunden\n"
    "/nein      ablehnen\n"
    "\n"
    "Ohne Antwort verfaellt die Anfrage in 30 Minuten.")

GOLD_KRAKEN = (
    "<b>Freigabe kraken?</b>\n"
    "Dauer: 1:00 h\n"
    "\n"
    "Es gelten die Grenzen aus wachen.json:\n"
    "  je Anlauf          25 EUR\n"
    "\n"
    "/ja        freigeben fuer 1:00 h\n"
    "/ja 6      stattdessen 6 Stunden\n"
    "/nein      ablehnen\n"
    "\n"
    "Ohne Antwort verfaellt die Anfrage in 30 Minuten.")


class AnfrageText(unittest.TestCase):
    def test_xperp_text_unveraendert(self):
        self.assertEqual(ff.anfrage_text("xperp", W_XPERP, 90, "USD"), GOLD_XPERP)

    def test_kraken_text_unveraendert(self):
        self.assertEqual(ff.anfrage_text("kraken", {"max_pro_trade_eur": 25},
                                         60, "EUR"), GOLD_KRAKEN)


class Grenzwerte(unittest.TestCase):
    def test_paare_in_fester_reihenfolge(self):
        self.assertEqual(ff.grenzwerte(W_XPERP, "USD"), [
            ("je Anlauf", "50 USD"), ("gesamt", "200 USD"),
            ("Positionen", "3 "), ("Hebel bis", "5 x"),
            ("Kill-Switch", "100 USD")])

    def test_fehlende_werte_fallen_weg(self):
        self.assertEqual(ff.grenzwerte({}, "USD"), [])

    def test_erster_vorhandener_name_gewinnt(self):
        w = {"max_margin_je_anlauf_usd": 7, "max_pro_trade_usd": 9}
        self.assertEqual(ff.grenzwerte(w, "USD")[0], ("je Anlauf", "9 USD"))


if __name__ == "__main__":
    unittest.main()
