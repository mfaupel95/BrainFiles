"""Tests fuer die Bot-Spur moondev_sentiment - ohne Netz und ohne Modell.

Feeds und Kerzen werden gestellt, das Urteil kommt aus `urteil_override`, das
Buch laeuft gegen einen Temp-Ordner. Ein Test darf NIE in den echten
Spurenordner schreiben.
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
    "risiko_je_position_usd": 5.0, "max_offene_positionen": 1,
    "max_pro_trade_usd": 100.0, "max_gesamt_usd": 100.0,
    "kill_switch_gesamt_usd": 15.0, "stop_prozent": 6.0,
    "pflicht_stop_prozent_min": 5.0, "pflicht_stop_prozent_max": 12.0,
    "ziel_r_vielfaches": 1.5, "drawdown_halbierung_usd": 5.0,
    "inst": "BTC-USDT-SWAP", "bar": "1H", "kerzen": 25,
    "je_quelle": 8, "hoechst_schlagzeilen": 12,
    "zeichen_je_schlagzeile": 140, "mindest_schlagzeilen": 6,
    "grund": "moondev_sentiment",
    "llm_modell": "test-modell", "llm_mindest_confidence": 60.0,
}

TITEL = ["Spot Bitcoin ETFs See Third Straight Day of Outflows",
         "Exchange Reserves Fall to Lowest Level Since 2021",
         "Analysts Warn of Leverage Build-Up in Perpetual Futures",
         "Bitcoin Holds Above Support as Funding Rates Cool Off",
         "Miners Sell Into Strength, On-Chain Data Shows",
         "Regulator Signals Clearer Rules for Crypto Custody",
         "Whale Wallets Accumulate After the Pullback",
         "ETF Inflows Return for the First Time in a Week"]


def _kerzen(anzahl=25, start=74000.0, ende=75000.0):
    """Kerzen in OKX-Form, aufsteigend."""
    aus = []
    for i in range(anzahl):
        kurs = start + (ende - start) * i / float(max(1, anzahl - 1))
        aus.append([1789500000000 + i * 3600000, kurs, kurs, kurs, kurs, 10.0])
    return aus


def _bestand(ordner):
    aus = {}
    for n in sorted(os.listdir(ordner)):
        p = os.path.join(ordner, n)
        if os.path.isfile(p) and not n.endswith(".pyc"):
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


class QuelleTest(unittest.TestCase):
    def setUp(self):
        self.alt_titel = h.daten.schlagzeilen
        self.alt_kerzen = h.daten.okx_kerzen

    def tearDown(self):
        h.daten.schlagzeilen = self.alt_titel
        h.daten.okx_kerzen = self.alt_kerzen

    def test_gate_offen_bei_genug_schlagzeilen(self):
        h.daten.schlagzeilen = lambda *a, **k: (list(TITEL), [])
        h.daten.okx_kerzen = lambda *a, **k: _kerzen()
        aus, kurse, fehler = h.quelle(dict(WACHEN))
        d = aus["BTC-USDT-SWAP"]
        self.assertTrue(d["nachrichten_gate"])
        self.assertEqual(d["anzahl_schlagzeilen"], 8)
        self.assertAlmostEqual(d["kurs_aenderung_24h"], 1.351, places=2)
        self.assertEqual(kurse["BTC-USDT-SWAP"], 75000.0)

    def test_zu_wenig_text_kein_urteil(self):
        h.daten.schlagzeilen = lambda *a, **k: (TITEL[:3], [])
        h.daten.okx_kerzen = lambda *a, **k: _kerzen()
        aus, kurse, fehler = h.quelle(dict(WACHEN))
        self.assertFalse(aus["BTC-USDT-SWAP"]["nachrichten_gate"])
        self.assertTrue(any("Schlagzeilen" in f for f in fehler))

    def test_feed_ausfall_ist_kein_signal(self):
        h.daten.schlagzeilen = lambda *a, **k: ([], ["coindesk: 403"])
        h.daten.okx_kerzen = lambda *a, **k: _kerzen()
        aus, kurse, fehler = h.quelle(dict(WACHEN))
        self.assertEqual(aus["BTC-USDT-SWAP"]["anzahl_schlagzeilen"], 0)
        self.assertIn("coindesk: 403", fehler)

    def test_ohne_kurs_kein_buch(self):
        h.daten.schlagzeilen = lambda *a, **k: (list(TITEL), [])
        h.daten.okx_kerzen = lambda *a, **k: []
        aus, kurse, fehler = h.quelle(dict(WACHEN))
        self.assertEqual(kurse, {})
        self.assertTrue(any("kein Kurs" in f for f in fehler))


class SignalTest(unittest.TestCase):
    def setUp(self):
        self.alt = h.urteil_override
        self.fragen = []

    def tearDown(self):
        h.urteil_override = self.alt

    def test_ohne_gate_kein_aufruf(self):
        h.urteil_override = lambda d, w: (self.fragen.append(d), "long")[1]
        self.assertIsNone(h.signal({"nachrichten_gate": False}, dict(WACHEN)))
        self.assertEqual(self.fragen, [])

    def test_mit_gate_urteilt_das_modell(self):
        h.urteil_override = lambda d, w: ("short", {"aktion": "SELL",
                                                    "confidence": 70.0,
                                                    "grund": "Ausflüsse"})
        w = dict(WACHEN)
        d = {"nachrichten_gate": True, "anzahl_schlagzeilen": 8}
        self.assertEqual(h.signal(d, w), "short")
        self.assertIn("SELL", w["_grund"])

    def test_prompt_traegt_die_schlagzeilen(self):
        d = {"schlagzeilen": TITEL[:3], "kurs_aenderung_24h": -2.4,
             "kurs_aenderung_1h": -0.5}
        text = h.marktbild(d, dict(WACHEN))
        self.assertIn("Outflows", text)
        self.assertIn("-2.40%", text)
        self.assertIn("Confidence: X%", text)


class BuchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_schreiben = buch.SCHREIBEN
        buch.SCHREIBEN = True
        w = dict(WACHEN)
        w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")
        with open(os.path.join(self.tmp.name, "wachen.json"), "w",
                  encoding="utf-8") as f:
            json.dump(w, f)
        self.alt_quelle = h.quelle_override
        self.alt_signal = h.signal
        h.signal = lambda d, w_: "long"
        h.quelle_override = lambda w_: ({"BTC-USDT-SWAP": {}},
                                        {"BTC-USDT-SWAP": 75000.0}, [])

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
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, "zweitziel",
                                                   "handelsjournal.csv")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
