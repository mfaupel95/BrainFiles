"""Tests fuer die Bot-Spur moondev_whale - ohne Netz und ohne Modell.

Das Urteil kommt aus `urteil_override` (Seam), die Daten aus `quelle_override`.
Der Buchlauf laeuft gegen einen Temp-Ordner: ein Test darf NIE in den echten
Spurenordner schreiben (das ist beim Bau der Funding-Spur einmal passiert - 16
Testbuchungen landeten im echten Journal).
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
import llm_lokal as llm  # noqa: E402
import spur_buch as buch  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py: %s" % h.__file__

WACHEN = {
    "waehrung": "USD", "handel_erlaubt": False,
    "risiko_je_position_usd": 5.0, "max_offene_positionen": 1,
    "max_pro_trade_usd": 100.0, "max_gesamt_usd": 100.0,
    "kill_switch_gesamt_usd": 15.0, "stop_prozent": 6.0,
    "pflicht_stop_prozent_min": 5.0, "pflicht_stop_prozent_max": 12.0,
    "ziel_r_vielfaches": 1.5, "drawdown_halbierung_usd": 5.0,
    "inst": "BTC-USDT-SWAP", "grund": "moondev_whale",
    "schwelle_mal_mittel": 1.31, "mindest_aenderung_pct": 0.5,
    "fenster_minuten": 15, "periode_minuten": 5,
    "llm_modell": "test-modell", "llm_mindest_confidence": 60.0,
}


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


def _historie(werte, periode_ms=300000):
    """OI-Historie wie OKX sie liefert: neuester Punkt zuerst."""
    jetzt = 1_789_500_000_000
    return [[jetzt - i * periode_ms, wert, 5_000_000.0]
            for i, wert in enumerate(werte)]


class VertragTest(unittest.TestCase):
    """Der Vertrag des Bots wird streng gelesen - daran haengt der Handel."""

    def test_drei_zeilen_werden_gelesen(self):
        u = llm.urteil("BUY\nMomentum steigt\nConfidence: 72%")
        self.assertEqual(u["seite"], "long")
        self.assertEqual(u["confidence"], 72.0)

    def test_unbekannte_erste_zeile_ist_kein_signal(self):
        self.assertIsNone(llm.urteil("Vielleicht kaufen\nConfidence: 90%"))

    def test_fehlende_confidence_ist_kein_signal(self):
        u = llm.urteil("BUY\nGrund ohne Prozent")
        self.assertIsNotNone(u)
        self.assertIsNone(u["confidence"])
        alt = llm.ANFRAGE
        llm.ANFRAGE = lambda p, m, z: "BUY\nGrund ohne Prozent"
        llm.leere_cache()
        try:
            seite, info = llm.entscheide("bild", {})
        finally:
            llm.ANFRAGE = alt
            llm.leere_cache()
        self.assertIsNone(seite)
        self.assertIn("Confidence", info["fehler"])

    def test_leere_antwort_ist_kein_signal(self):
        self.assertIsNone(llm.urteil(""))
        self.assertIsNone(llm.urteil(None))

    def test_nothing_ist_keine_richtung(self):
        u = llm.urteil("NOTHING\nkein Setup\nConfidence: 80%")
        self.assertIsNone(u["seite"])


class EntscheideTest(unittest.TestCase):
    """entscheide() mit gestellter Antwort - die Confidence ist ein Gate."""

    def setUp(self):
        self.alt = llm.ANFRAGE
        llm.leere_cache()

    def tearDown(self):
        llm.ANFRAGE = self.alt
        llm.leere_cache()

    def test_confidence_ueber_schwelle_traegt(self):
        llm.ANFRAGE = lambda p, m, z: "SELL\nUeberhitzung\nConfidence: 75%"
        seite, info = llm.entscheide("bild", {"llm_mindest_confidence": 60.0})
        self.assertEqual(seite, "short")
        self.assertEqual(info["confidence"], 75.0)

    def test_confidence_unter_schwelle_faellt_aus(self):
        llm.ANFRAGE = lambda p, m, z: "BUY\nunsicher\nConfidence: 40%"
        seite, info = llm.entscheide("bild", {"llm_mindest_confidence": 60.0})
        self.assertIsNone(seite)
        self.assertIn("zu unsicher", info["fehler"])

    def test_modell_ohne_antwort_ist_kein_signal(self):
        llm.ANFRAGE = lambda p, m, z: None
        seite, info = llm.entscheide("bild", {})
        self.assertIsNone(seite)
        self.assertIn("kein Urteil", info["fehler"])

    def test_zweiter_aufruf_kommt_aus_dem_speicher(self):
        rufe = []

        def zaehlen(p, m, z):
            rufe.append(p)
            return "BUY\nGrund\nConfidence: 80%"
        llm.ANFRAGE = zaehlen
        llm.entscheide("dasselbe bild", {})
        llm.entscheide("dasselbe bild", {})
        self.assertEqual(len(rufe), 1)


class QuelleTest(unittest.TestCase):
    """Das Gate rechnet auf der OI-Historie - ohne Netz, mit gestellten Daten."""

    def test_anomalie_wird_erkannt(self):
        ruhig = [1000.0] * 40
        ruhig[0] = 1045.0          # +4.5 % im Fenster gegen ruhige Umgebung
        alt = h.daten.okx_oi_historie
        alt_kerzen = h.daten.okx_kerzen
        h.daten.okx_oi_historie = lambda ccy="BTC", periode="5m": _historie(ruhig)
        h.daten.okx_kerzen = lambda *a, **k: [[1, 1, 1, 1, 100.0, 1.0],
                                              [2, 1, 1, 1, 100.0, 1.0],
                                              [3, 1, 1, 1, 101.0, 1.0]]
        try:
            aus, kurse, fehler = h.quelle(dict(WACHEN))
        finally:
            h.daten.okx_oi_historie = alt
            h.daten.okx_kerzen = alt_kerzen
        self.assertEqual(fehler, [])
        d = aus["BTC-USDT-SWAP"]
        self.assertTrue(d["anomalie"], d)
        self.assertAlmostEqual(d["oi_aenderung_pct"], 4.5, places=2)
        self.assertEqual(kurse["BTC-USDT-SWAP"], 101.0)

    def test_ruhiger_markt_ist_keine_anomalie(self):
        ruhig = [1000.0 + (i % 3) * 0.5 for i in range(40)]
        alt = h.daten.okx_oi_historie
        alt_kerzen = h.daten.okx_kerzen
        h.daten.okx_oi_historie = lambda ccy="BTC", periode="5m": _historie(ruhig)
        h.daten.okx_kerzen = lambda *a, **k: [[1, 1, 1, 1, 100.0, 1.0],
                                              [3, 1, 1, 1, 100.0, 1.0]]
        try:
            aus, kurse, fehler = h.quelle(dict(WACHEN))
        finally:
            h.daten.okx_oi_historie = alt
            h.daten.okx_kerzen = alt_kerzen
        self.assertFalse(aus["BTC-USDT-SWAP"]["anomalie"])

    def test_zu_kurze_historie_bucht_nichts(self):
        alt = h.daten.okx_oi_historie
        h.daten.okx_oi_historie = lambda ccy="BTC", periode="5m": _historie([1.0, 1.0])
        try:
            aus, kurse, fehler = h.quelle(dict(WACHEN))
        finally:
            h.daten.okx_oi_historie = alt
        self.assertEqual(aus, {})
        self.assertTrue(fehler)


class GateTest(unittest.TestCase):
    """signal(): ohne Anomalie wird das Modell nicht einmal gefragt."""

    def setUp(self):
        self.alt_urteil = h.urteil_override
        self.fragen = []

    def tearDown(self):
        h.urteil_override = self.alt_urteil

    def test_ohne_anomalie_kein_aufruf(self):
        def zaehlen(d, w):
            self.fragen.append(d)
            return "long", {"aktion": "BUY", "confidence": 90.0, "grund": "x"}
        h.urteil_override = zaehlen
        self.assertIsNone(h.signal({"anomalie": False}, dict(WACHEN)))
        self.assertEqual(self.fragen, [])

    def test_mit_anomalie_urteilt_das_modell(self):
        h.urteil_override = lambda d, w: ("long", {"aktion": "BUY",
                                                   "confidence": 71.0,
                                                   "grund": "Momentum"})
        w = dict(WACHEN)
        d = {"anomalie": True, "oi_aenderung_pct": 4.1, "fenster_minuten": 15}
        self.assertEqual(h.signal(d, w), "long")
        self.assertIn("BUY", w["_grund"])
        self.assertIn("71", w["_grund"])


class BuchTest(unittest.TestCase):
    """Ein Papierlauf gegen einen Temp-Ordner - und die Vorschau ohne Datei."""

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
        h.signal = lambda d, w_: "short"
        h.quelle_override = lambda w_: ({"BTC-USDT-SWAP": {}},
                                        {"BTC-USDT-SWAP": 100.0}, [])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
