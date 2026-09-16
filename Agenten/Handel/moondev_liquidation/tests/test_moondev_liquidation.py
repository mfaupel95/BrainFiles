"""Tests fuer die Bot-Spur moondev_liquidation - ohne Netz und ohne Modell.

Die Summen werden aus erfundenen Saetzen gerechnet, das Urteil kommt aus
`urteil_override`, das Buch laeuft gegen einen Temp-Ordner. Ein Test darf NIE
in den echten Spurenordner schreiben.
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
    "kill_switch_gesamt_usd": 15.0, "stop_prozent": 7.0,
    "pflicht_stop_prozent_min": 5.0, "pflicht_stop_prozent_max": 12.0,
    "ziel_r_vielfaches": 1.5, "drawdown_halbierung_usd": 5.0,
    "inst": "BTC-USDT-SWAP", "uly": "BTC-USDT", "bar": "15m",
    "grund": "moondev_liquidation",
    "mindest_abdeckung_minuten": 10, "hoechst_abdeckung_minuten": 240,
    "mindest_rate_usd_pro_stunde": 100000.0,
    "kaskade_rate_usd_pro_stunde": 750000.0,
    "schief_anteil_oben": 0.75, "schief_anteil_unten": 0.25,
    "llm_modell": "test-modell", "llm_mindest_confidence": 60.0,
}

JETZT = 1_789_500_000_000


def _saetze(seiten_usd, spanne_minuten=60):
    """Saetze wie OKX sie liefert: gleichmaessig ueber die GESAMTE Spanne."""
    aus = []
    n = len(seiten_usd)
    schritt = (spanne_minuten * 60000.0 / (n - 1)) if n > 1 else 0.0
    for i, (seite, usd) in enumerate(seiten_usd):
        ts = JETZT - int((n - i - 1) * schritt)
        aus.append({"seite": seite, "preis": 75000.0, "kontrakte": usd / 750.0,
                    "ts": ts, "inst": "BTC-USDT-SWAP", "usd": usd})
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


class SummenTest(unittest.TestCase):
    def test_summen_und_rate(self):
        liq = _saetze([("short", 500000.0), ("long", 500000.0)], 60)
        s = h.summen(liq, dict(WACHEN))
        self.assertAlmostEqual(s["gesamt_usd"], 1000000.0)
        self.assertAlmostEqual(s["anteil_long"], 0.5, places=3)
        # 60 Minuten Abdeckung -> Rate = Summe je Stunde.
        self.assertAlmostEqual(s["rate_usd_pro_stunde"], 1000000.0, delta=50000)

    def test_leere_saetze_ergeben_nichts(self):
        self.assertIsNone(h.summen([], dict(WACHEN)))
        self.assertIsNone(h.summen([{"seite": "long", "ts": JETZT}],
                                   dict(WACHEN)))


class GateTest(unittest.TestCase):
    """signal(): ohne Gate wird das Modell nicht einmal gefragt."""

    def setUp(self):
        self.alt = h.urteil_override
        self.fragen = []

    def tearDown(self):
        h.urteil_override = self.alt

    def _urteilen(self, d, w):
        self.fragen.append(d)
        return "short", {"aktion": "SELL", "confidence": 80.0, "grund": "x"}

    def test_ohne_gate_kein_aufruf(self):
        h.urteil_override = self._urteilen
        self.assertIsNone(h.signal({"signal_gate": False}, dict(WACHEN)))
        self.assertEqual(self.fragen, [])

    def test_mit_gate_urteilt_das_modell(self):
        h.urteil_override = self._urteilen
        w = dict(WACHEN)
        d = {"signal_gate": True, "rate_usd_pro_stunde": 900000.0,
             "anteil_long": 0.02}
        self.assertEqual(h.signal(d, w), "short")
        self.assertIn("SELL", w["_grund"])

    def test_prompt_traegt_die_zahlen(self):
        d = {"gesamt_usd": 1234567.0, "abdeckung_minuten": 111.8, "anzahl": 100,
             "lang_usd": 5305.0, "kurz_usd": 739748.0, "anteil_long": 0.0071,
             "rate_usd_pro_stunde": 768000.0, "kerzen_text": "  eine Kerze"}
        text = h.marktbild(d, dict(WACHEN))
        self.assertIn("1,234,567", text)
        self.assertIn("739,748", text)
        self.assertIn("Confidence: X%", text)


class QuelleTest(unittest.TestCase):
    """Gate aus gestellten OKX-Saetzen, Kurs aus gestellten Kerzen."""

    def setUp(self):
        self.alt_liq = h.daten.okx_liquidationen
        self.alt_kerzen = h.daten.okx_kerzen

    def tearDown(self):
        h.daten.okx_liquidationen = self.alt_liq
        h.daten.okx_kerzen = self.alt_kerzen

    def test_kaskade_oeffnet_das_gate(self):
        h.daten.okx_liquidationen = lambda uly="BTC-USDT", grenze=100: _saetze(
            [("short", 700000.0), ("short", 600000.0), ("long", 20000.0)], 60)
        h.daten.okx_kerzen = lambda *a, **k: [[1, 1, 1, 1, 75000.0, 1.0],
                                              [2, 1, 1, 1, 74250.0, 1.0]]
        aus, kurse, fehler = h.quelle(dict(WACHEN))
        d = aus["BTC-USDT-SWAP"]
        self.assertTrue(d["signal_gate"], d)
        self.assertTrue(d["schief"])           # Long-Anteil 0.03 -> schief
        self.assertTrue(d["kaskade"])

    def test_ruhiger_markt_ohne_ungleichgewicht_kein_signal(self):
        h.daten.okx_liquidationen = lambda uly="BTC-USDT", grenze=100: _saetze(
            [("short", 50000.0), ("long", 50000.0)], 60)
        h.daten.okx_kerzen = lambda *a, **k: [[1, 1, 1, 1, 75000.0, 1.0]]
        aus, kurse, fehler = h.quelle(dict(WACHEN))
        d = aus["BTC-USDT-SWAP"]
        self.assertFalse(d["signal_gate"])
        self.assertTrue(d["laut"])             # Rate 100k/h = genau die Schwelle

    def test_zu_kurzer_ausschnitt_urteilt_nicht(self):
        h.daten.okx_liquidationen = lambda uly="BTC-USDT", grenze=100: _saetze(
            [("short", 900000.0), ("short", 900000.0)], 2)
        h.daten.okx_kerzen = lambda *a, **k: [[1, 1, 1, 1, 75000.0, 1.0]]
        aus, kurse, fehler = h.quelle(dict(WACHEN))
        self.assertFalse(aus["BTC-USDT-SWAP"]["frisch"])
        self.assertTrue(any("nicht frisch" in f for f in fehler))

    def test_zu_alte_spanne_urteilt_nicht(self):
        h.daten.okx_liquidationen = lambda uly="BTC-USDT", grenze=100: _saetze(
            [("short", 5000000.0), ("long", 100000.0)], 600)
        h.daten.okx_kerzen = lambda *a, **k: [[1, 1, 1, 1, 75000.0, 1.0]]
        aus, kurse, fehler = h.quelle(dict(WACHEN))
        self.assertFalse(aus["BTC-USDT-SWAP"]["frisch"])


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
