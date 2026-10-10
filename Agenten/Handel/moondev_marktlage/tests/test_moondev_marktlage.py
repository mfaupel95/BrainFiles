"""Tests fuer die Bot-Spur moondev_marktlage - ohne Netz.

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

# Reihenfolge ist entscheidend: eine bereits importierte NACHBARSPUR kann ihren
# Ordner auf sys.path gelegt haben (live_kraken.py laedt die Haus-Kraken-Spur
# ueber den Pfad und tut das). Dann gewinnt deren handeln.py und diese Suite
# prueft still das falsche Modul - genau dafuer steht die Zusicherung unten.
# Deshalb: fremde Spurordner raus, eigenes handeln aus dem Modulcache werfen,
# eigene Spur ZULETZT einfuegen (landet damit ganz vorne).
for fremd in [p for p in sys.path if os.path.basename(p) == "kraken"]:
    sys.path.remove(fremd)
sys.modules.pop("handeln", None)
for p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    # OHNE "if p not in sys.path": die Nachbarspur hat die Pfade schon
    # eingetragen (nur weiter hinten). Der eigene Ordner muss nach vorne,
    # sonst gewinnt wieder ein fremdes handeln.py.
    sys.path.insert(0, p)

import handeln as h  # noqa: E402
import spur_buch as buch  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py: %s" % h.__file__

WACHEN = {
    "waehrung": "USD", "handel_erlaubt": False,
    "risiko_je_position_usd": 5.0, "max_offene_positionen": 1,
    "max_pro_trade_usd": 100.0, "max_gesamt_usd": 300.0,
    "kill_switch_gesamt_usd": 45.0, "stop_prozent": 6.0,
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
    def test_breite_aufwaerts_ist_long(self):
        self.assertEqual(h.signal({"btc_aenderung_24h": 3.0, "breite": 0.7},
                                  dict(WACHEN)), "long")

    def test_breite_abwaerts_ist_short(self):
        self.assertEqual(h.signal({"btc_aenderung_24h": -3.0, "breite": 0.3},
                                  dict(WACHEN)), "short")

    def test_gegenlaeufig_kein_signal(self):
        # BTC steigt, aber der Markt faellt - genau der Fall, den der Agent
        # beschreibt: ein Coin allein sagt wenig.
        self.assertIsNone(h.signal({"btc_aenderung_24h": 3.0, "breite": 0.3},
                                   dict(WACHEN)))
        self.assertIsNone(h.signal({"btc_aenderung_24h": 0.5, "breite": 0.9},
                                   dict(WACHEN)))
        self.assertIsNone(h.signal({"btc_aenderung_24h": None, "breite": 0.9},
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
