"""Tests fuer die Bot-Spur moondev_topmovers - ohne Netz.

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
    "kill_switch_gesamt_usd": 45.0, "stop_prozent": 8.0,
    "pflicht_stop_prozent_min": 5.0, "pflicht_stop_prozent_max": 12.0,
    "ziel_r_vielfaches": 1.5, "drawdown_halbierung_usd": 15.0,
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
    def test_momentum_im_fenster_ist_long(self):
        d = {"aenderung_24h": 12.0, "volumen_24h": 5e7}
        self.assertEqual(h.signal(d, dict(WACHEN)), "long")

    def test_ueberhitzung_kein_signal(self):
        d = {"aenderung_24h": 80.0, "volumen_24h": 5e7}
        self.assertIsNone(h.signal(d, dict(WACHEN)))

    def test_zu_wenig_momentum_und_zu_wenig_volumen(self):
        self.assertIsNone(h.signal({"aenderung_24h": 3.0, "volumen_24h": 5e7},
                                   dict(WACHEN)))
        self.assertIsNone(h.signal({"aenderung_24h": 12.0, "volumen_24h": 1e6},
                                   dict(WACHEN)))
        self.assertIsNone(h.signal({"aenderung_24h": None, "volumen_24h": 5e7},
                                   dict(WACHEN)))


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
