"""Tests fuer die Bot-Spur moondev_listingarb - ohne Netz.

Die Regel wird mit erfundenen Daten geprueft (die API liefert im Test nichts),
und der Buchlauf laeuft gegen einen Temp-Ordner: ein Test darf NIE in den
echten Spurenordner schreiben (das ist beim Bau der Funding-Spur einmal
passiert - 16 Testbuchungen landeten im echten Journal).
"""

import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
for p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln as h  # noqa: E402
import spur_buch as buch  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py: %s" % h.__file__

WACHEN = {
    "waehrung": "USD", "handel_erlaubt": False,
    "risiko_je_position_usd": 5.0, "max_offene_positionen": 3,
    "max_pro_trade_usd": 100.0, "max_gesamt_usd": 300.0,
    "kill_switch_gesamt_usd": 45.0, "stop_prozent": 7.0,
    "pflicht_stop_prozent_min": 5.0, "pflicht_stop_prozent_max": 12.0,
    "ziel_r_vielfaches": 2.0, "drawdown_halbierung_usd": 15.0,
    # Fuer die REGEL-Tests ausdruecklich Kraken (EUR): auf OKX (USDC) prueft
    # signal() zusaetzlich, ob das Paar <SYM>-USDC existiert - das ist ein
    # eigener Fall und steht in OkxPaarTest.
    "boerse": "kraken",
}


def _bestand(ordner):
    aus = {}
    for n in sorted(os.listdir(ordner)):
        p = os.path.join(ordner, n)
        if os.path.isfile(p) and not n.endswith((".pyc", ".bak-20260916")):
            aus[n] = os.path.getsize(p)
    return aus


_ECHT_VORHER = None


def setUpModule():
    global _ECHT_VORHER
    _ECHT_VORHER = _bestand(SPUR)


def tearDownModule():
    assert _bestand(SPUR) == _ECHT_VORHER, (
        "Ein Test hat in den echten Spurenordner geschrieben! "
        "vorher=%s nachher=%s" % (_ECHT_VORHER, _bestand(SPUR)))


class RegelTest(unittest.TestCase):
    def test_grosser_coin_ohne_binance_ist_long(self):
        d = {"marktkap": 2e9, "volumen_24h": 5e7, "auf_binance": False}
        self.assertEqual(h.signal(d, dict(WACHEN)), "long")

    def test_auf_binance_kein_signal(self):
        d = {"marktkap": 2e9, "volumen_24h": 5e7, "auf_binance": True}
        self.assertIsNone(h.signal(d, dict(WACHEN)))

    def test_zu_klein_kein_signal(self):
        d = {"marktkap": 5e8, "volumen_24h": 5e7, "auf_binance": False}
        self.assertIsNone(h.signal(d, dict(WACHEN)))
        d = {"marktkap": 2e9, "volumen_24h": 1e6, "auf_binance": False}
        self.assertIsNone(h.signal(d, dict(WACHEN)))


class BuchTest(unittest.TestCase):
    """Ein Papierlauf gegen einen Temp-Ordner - und die Vorschau ohne Datei."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_schreiben = buch.SCHREIBEN
        buch.SCHREIBEN = True
        w = dict(WACHEN)
        w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")
        w["grund"] = "test"
        with open(os.path.join(self.tmp.name, "wachen.json"), "w",
                  encoding="utf-8") as f:
            json.dump(w, f)
        self.alt_quelle = h.quelle_override
        self.alt_signal = h.signal
        h.signal = lambda d, w_: "long"
        h.quelle_override = lambda w_: ({"BTC": {}}, {"BTC": 100.0}, [])

    def tearDown(self):
        h.quelle_override = self.alt_quelle
        h.signal = self.alt_signal
        buch.SCHREIBEN = self.alt_schreiben
        self.tmp.cleanup()

    def test_vorschau_schreibt_nichts(self):
        buch.zyklus(self.tmp.name, h.daten_holen, h.signal, "vorschau", "test")
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name,
                                                    "handelsjournal.csv")))

    def test_papierlauf_bucht_und_spiegelt(self):
        buch.zyklus(self.tmp.name, h.daten_holen, h.signal, "papier", "test")
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name,
                                                   "handelsjournal.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name,
                                                   "zustand.json")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, "zweitziel",
                                                   "handelsjournal.csv")))

    def test_leere_quelle_bucht_nichts(self):
        h.quelle_override = lambda w_: ({}, {}, ["Boerse weg"])
        buch.zyklus(self.tmp.name, h.daten_holen, h.signal, "papier", "test")
        # Seit 02.10.2026 ("alle duerfen auch journal fuehren") legt der Kern
        # das Journal schon im ersten Zyklus an - mit Kopfzeile, null Buchungen.
        import csv
        pfad = os.path.join(self.tmp.name, "handelsjournal.csv")
        self.assertTrue(os.path.exists(pfad))
        with open(pfad, newline="", encoding="utf-8") as f:
            self.assertEqual([r for r in csv.reader(f) if r], [buch.SPALTEN])


class OkxPaarTest(unittest.TestCase):
    """Auf OKX wird nur gehandelt, was dort als <SYM>-USDC existiert.

    Gemessen 25.09.2026: von den drei Signalen des Tages (VVV, WBT, XMR) hatte
    nur VVV ueberhaupt ein OKX-Paar - und das nur als -USDT. Ohne diese Pruefung
    schickte der Orderweg ein Paar, das die Boerse nicht kennt.
    """

    def setUp(self):
        self.alt = h.instrumente_override
        h.instrumente_override = lambda: {"HYPE-USDC", "JUP-USDC"}

    def tearDown(self):
        h.instrumente_override = self.alt

    @staticmethod
    def _coin(**abweichend):
        d = {"marktkap": 2e9, "volumen_24h": 5e7, "auf_binance": False}
        d.update(abweichend)
        return d

    def test_ohne_okx_paar_kein_einstieg(self):
        w = dict(WACHEN, boerse="okx")
        self.assertIsNone(h.signal(self._coin(okx_usdc=False), w))

    def test_mit_okx_paar_einstieg(self):
        w = dict(WACHEN, boerse="okx")
        self.assertEqual(h.signal(self._coin(okx_usdc=True), w), "long")

    def test_kraken_boerse_ignoriert_das_okx_paar(self):
        self.assertEqual(h.signal(self._coin(okx_usdc=False), dict(WACHEN)), "long")

    def test_quelle_markiert_das_paar(self):
        maerkte = [{"symbol": "hype", "name": "Hyperliquid", "market_cap": 2e9,
                    "total_volume": 1e8, "market_cap_rank": 10, "current_price": 5.0},
                   {"symbol": "wbt", "name": "WhiteBIT", "market_cap": 3e9,
                    "total_volume": 2e8, "market_cap_rank": 11, "current_price": 1.0}]
        from unittest.mock import patch
        with patch.object(h.daten, "maerkte", lambda anzahl=100: maerkte), \
                patch.object(h.daten, "binance_paare", lambda: set()):
            aus, kurse, fehler = h.quelle(dict(WACHEN, boerse="okx"))
        self.assertEqual(fehler, [])
        self.assertTrue(aus["HYPE"]["okx_usdc"])
        self.assertFalse(aus["WBT"]["okx_usdc"])
        self.assertEqual(kurse["HYPE"], 5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
