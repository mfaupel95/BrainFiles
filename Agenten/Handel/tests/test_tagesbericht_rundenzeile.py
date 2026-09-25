"""Die Zeile '7 Tage: ...' im Tagesbericht.

WARUM: Der Bericht nennt fuer den scanner "83 Runden, +1801.08 USD, Treffer
100 %", obwohl im selben Fenster 101 Runden geschlossen wurden. Die fehlenden
18 sind Ausstiege ohne Handelsentscheidung (Zwangsschluss des Waechters oder
Buchhaltungs-Korrektur, `stoerungen.ist_stoerung`) - sie fallen aus der Quote,
standen aber nirgends daneben. "Treffer 100 %" las sich damit wie ein
fehlerfreier Automat. Geprueft wird die REGEL, nicht der Tageswert.
"""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)

import auswertung_alle as aa   # noqa: E402
import stoerungen              # noqa: E402
import tagesbericht as tb      # noqa: E402
import zeitfenster             # noqa: E402


def lage(n=83, treffer=83, ergebnis=1801.08, stoerung=0, stoerung_ergebnis=0.0,
         buchlage="belastbar", schluessel="scanner", waehrung="USD",
         buch_seit=None):
    return {
        "schluessel": schluessel, "waehrung": waehrung, "buchlage": buchlage,
        "buch_seit": buch_seit,
        "kennzahlen": {"n": n, "treffer": treffer, "ergebnis": ergebnis,
                       "n_stoerung": stoerung,
                       "stoerung_ergebnis": stoerung_ergebnis},
    }


class RundenzeileTest(unittest.TestCase):
    def test_ohne_stoerungen_bleibt_die_zeile_wie_bisher(self):
        z = tb.rundenzeile(lage())
        self.assertEqual(
            z, "  7 Tage: 83 Runden, +1801.08 USD, Treffer 100%")

    def test_ausstiege_ohne_handelsentscheidung_stehen_daneben(self):
        z = tb.rundenzeile(lage(stoerung=18, stoerung_ergebnis=210.14))
        self.assertIn("83 Runden", z)
        self.assertIn("Treffer 100%", z)
        self.assertIn("+18 Ausstiege ohne Handelsentscheidung", z)
        self.assertIn("+210.14 USD", z)
        self.assertIn("nicht in der Quote", z)

    def test_verlust_in_der_quote_senkt_die_trefferquote(self):
        z = tb.rundenzeile(lage(n=100, treffer=98, ergebnis=1500.0))
        self.assertIn("Treffer 98%", z)
        self.assertNotIn("ohne Handelsentscheidung", z)

    def test_zu_wenige_runden(self):
        z = tb.rundenzeile(lage(n=2, buchlage="zu_wenige_runden"))
        self.assertEqual(z, "  7 Tage: zu wenige Runden (2)")

    def test_kein_buch_mit_und_ohne_datum(self):
        self.assertEqual(
            tb.rundenzeile(lage(buchlage="kein_buch", buch_seit="12.09.2026")),
            "  kein Buch (seit 12.09.2026)")
        self.assertEqual(tb.rundenzeile(lage(buchlage="kein_buch")),
                         "  kein Buch")

    def test_ohne_schluessel_keine_zeile(self):
        self.assertIsNone(tb.rundenzeile(lage(schluessel=None,
                                             buchlage="kein_buch")))
        self.assertIsNone(tb.rundenzeile({}))


class RegelGegenDasEchteBuchTest(unittest.TestCase):
    """Die Regel gilt auch fuer die Zahlen, die wirklich im Journal stehen.

    Kein Tageswert wird festgeschrieben: geprueft wird nur, dass ein Buch mit
    Ausstiegen ohne Handelsentscheidung sie in der Zeile NENNT.
    """

    def test_scanner_nennt_seine_buchungen_wenn_es_welche_gibt(self):
        von, bis = zeitfenster.fenster(tage=7)
        k = aa.kennzahlen_fuer("scanner", von=von, bis=bis)
        if not k:
            self.skipTest("scanner hat kein Buch")
        z = tb.rundenzeile({"buchlage": "belastbar", "schluessel": "scanner",
                            "waehrung": "USD", "kennzahlen": k})
        if k.get("n_stoerung"):
            self.assertIn("ohne Handelsentscheidung", z)
            self.assertIn("%d Runden" % k["n"], z)
        else:
            self.assertNotIn("ohne Handelsentscheidung", z)

    def test_die_regel_der_ausnahmen(self):
        """Waechter-Reaktion und Buchbereinigung fallen aus der Quote.

        Nur diese beiden Klassen. Eine reine Mengen-/Bestandsanpassung
        (`anpassen`, `buch_nachgezogen_boerse`) zaehlt weiter als Runde - sie
        traegt Einsatz und Erloes und liegt deshalb nahe bei null; wer sie
        ebenfalls herausnehmen will, aendert `stoerungen.BUCHHALTUNG` fuer ALLE
        Spuren und muss die Buecher neu lesen.
        """
        for grund in ("herzschlag_alt", "zwangsschluss", "notaus",
                      "buchbereinigung", "buchbereinigung_geist"):
            with self.subTest(grund=grund):
                self.assertTrue(stoerungen.ist_stoerung(grund))
        for grund in ("ziel", "stop", "anpassen", "buch_nachgezogen_boerse",
                      "order_nicht_gefuellt", ""):
            with self.subTest(grund=grund):
                self.assertFalse(stoerungen.ist_stoerung(grund))


if __name__ == "__main__":
    unittest.main()