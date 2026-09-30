"""quoten_vergleich: die Regel, nicht die Tageswerte.

Die Spreads selbst haengen am Markt und gehoeren nicht in einen Test. Was
festgenagelt wird, ist die REGEL, mit der das Werkzeug antwortet:

  - Deckt die eigene Waehrung die Instrumente ab, und gibt es eines, das NUR
    in der anderen Quote erreichbar ist? Ist die Antwort nein, erschliesst ein
    Umtausch kein Instrument - dann ist die Spread-Frage zweitrangig.
  - Die Paartabelle wird ueber `wsname` normalisiert (XBT/USDC -> Basis XBT,
    Quote USDC), nicht ueber Namen geraten.

Ohne Netz: die AssetPairs-Antwort wird als Attrappe hereingereicht (`abruf`).

Aufruf (aus Agenten/Handel/kraken):  python -m unittest tests.test_quoten_vergleich
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
KRAKEN = os.path.dirname(HIER)
if KRAKEN not in sys.path:
    sys.path.insert(0, KRAKEN)

import quoten_vergleich as qv                               # noqa: E402

assert qv.__file__.startswith(KRAKEN), qv.__file__

# Attrappe: XBT und SOL in EUR und USDC, NURUSDC nur in USDC.
# Die Quote-Schluessel sind ueber wsname normalisiert (ZEUR -> EUR).
ATT = {
    "XXBTZEUR": {"wsname": "XBT/EUR", "base": "XXBT", "quote": "ZEUR"},
    "XBTUSDC": {"wsname": "XBT/USDC", "base": "XBT", "quote": "USDC"},
    "SOLEUR": {"wsname": "SOL/EUR", "base": "SOL", "quote": "ZEUR"},
    "SOLUSDC": {"wsname": "SOL/USDC", "base": "SOL", "quote": "USDC"},
    "NURUSDC": {"wsname": "NURUSDC/USDC", "base": "NURUSDC", "quote": "USDC"},
    "OHNUSDCEUR": {"wsname": "OHNUSDC/EUR", "base": "OHNUSDC", "quote": "ZEUR"},
}


class Paartabelle(unittest.TestCase):

    def test_wsname_wird_normalisiert(self):
        pro = qv.paare_nach_wsname(ATT)
        self.assertEqual(pro["XBT"]["USDC"], "XBTUSDC")
        self.assertEqual(pro["XBT"]["EUR"], "XXBTZEUR")
        self.assertEqual(pro["SOL"]["USDC"], "SOLUSDC")

    def test_paare_ohne_wsname_fallen_raus(self):
        pro = qv.paare_nach_wsname({"KAPUTT": {"base": "X", "quote": "ZEUR"}})
        self.assertEqual(pro, {})


class Deckung(unittest.TestCase):

    def test_kein_instrument_nur_in_der_anderen_quote(self):
        # Der Regelfall: alles hat ein EUR-Paar -> Umtausch erschliesst nichts.
        wl = ["XXBTZEUR", "SOLEUR", "OHNUSDCEUR"]
        d = qv.deckung(wl, "USDC", ATT)
        self.assertEqual(d["nur_ziel"], [])
        self.assertEqual(d["ohne_eigene"], [])

    def test_instrument_nur_in_der_anderen_quote_wird_gemeldet(self):
        # Gegenprobe: ohne EUR-Paar muss es auftauchen - sonst wuerde das
        # Werkzeug "Umtausch lohnt nicht" sagen, obwohl es etwas erschliesst.
        wl = ["XXBTZEUR", "NURUSDC"]
        d = qv.deckung(wl, "USDC", ATT)
        self.assertEqual(d["nur_ziel"], ["NURUSDC"])
        self.assertEqual(d["ohne_eigene"], ["NURUSDC"])

    def test_fehlende_zielquote_wird_gemeldet(self):
        wl = ["XXBTZEUR", "OHNUSDCEUR"]
        d = qv.deckung(wl, "USDC", ATT)
        self.assertEqual(d["ohne_ziel"], ["OHNUSDC"])

    def test_verteilung_zaehlt_die_quotes(self):
        d = qv.deckung(["XXBTZEUR"], "USDC", ATT)
        self.assertEqual(d["paare_je_quote"]["EUR"], 3)
        self.assertEqual(d["paare_je_quote"]["USDC"], 3)
        self.assertEqual(d["instrumente"], 1)

    def test_leere_watchlist_ist_kein_fehler(self):
        d = qv.deckung([], "USDC", ATT)
        self.assertEqual(d["instrumente"], 0)
        self.assertEqual(d["nur_ziel"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)