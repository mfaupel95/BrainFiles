"""Tests fuer grid_historie.py - ohne Netz, ohne echte Dateien.

Die Rechenfunktionen sind reine Funktionen: sie bekommen die Zeile eines
geschlossenen Grids (mit den Feldern, die OKX wirklich liefert - gemessen
08.10.2026 an der echten Antwort) und rechnen. Ein Modulwaechter vergleicht
am Ende die Dateiliste des echten Ordners - ein Test, der nach draussen
schreibt, faellt auf.

Aufruf (aus DIESEM Ordner):  python -m unittest test_grid_historie
"""
import json
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HIER not in sys.path:
    sys.path.insert(0, HIER)
import grid_historie as gh  # noqa: E402

assert gh.__file__.startswith(HIER), gh.__file__

# Echte Zeilen aus der OKX-Historie (Antwort vom 08.10.2026, gekuerzt)
ZEC_3_95 = {
    "algoId": "3942883841725857792", "algoOrdType": "contract_grid",
    "direction": "long", "gridProfit": "35.28", "totalPnl": "46.76",
    "slTriggerPx": "", "cTime": "1790150356922", "uTime": "1790488423787",
    "investment": "153.17", "instId": "ZEC-USD_UM_XPERP-310530",
    "arbitrageNum": "92", "gridNum": "40",
}

PUMP_SHORT = {
    "algoId": "3948900000000000000", "algoOrdType": "contract_grid",
    "direction": "short", "gridProfit": "7.31", "totalPnl": "23.91",
    "slTriggerPx": "0.00345", "cTime": "1790200000000", "uTime": "1790316400000",
    "investment": "50.0", "instId": "PUMP-USD_UM_XPERP-310404",
}

OHNE_ZIEL = {
    "algoId": "3948000000000000000", "algoOrdType": "contract_grid",
    "direction": "long", "gridProfit": "", "totalPnl": "",
    "slTriggerPx": "0.1", "cTime": "", "uTime": "",
    "instId": "X-USD_UM_XPERP-310404",
}

# Tageskerzen [ts_ms, o, h, l, c, v] - aufsteigend, fuer marktbewegung
KERZEN = [
    [1790140000000, 100, 110, 99, 100, 1],
    [1790226000000, 101, 111, 100, 103, 1],
    [1790312000000, 103, 112, 102, 106, 1],
    [1790398000000, 106, 115, 105, 109, 1],
    [1790483000000, 109, 116, 108, 110, 1],
    [1790569000000, 110, 118, 109, 115, 1],
]


def _vorher():
    raus = {}
    for n in sorted(os.listdir(HIER)):
        p = os.path.join(HIER, n)
        if os.path.isfile(p):
            raus[n] = os.path.getsize(p)
    return raus


_STAND = _vorher()


def tearDownModule():
    nach = _vorher()
    neu = set(nach) - set(_STAND)
    geaendert = {k for k in set(nach) & set(_STAND) if nach[k] != _STAND[k]}
    # Laufzeitdateien schreibt der Waechter im Betrieb - im Test umgebogen
    for n in ("zustand.json", "bot_waechter_journal.jsonl"):
        neu.discard(n)
        geaendert.discard(n)
    assert not neu and not geaendert, (
        "Test hat in den echten Ordner geschrieben: neu=%s geaendert=%s"
        % (sorted(neu), sorted(geaendert)))


class LauefzeitTest(unittest.TestCase):
    def test_lauefzeit_aus_ctime_utime(self):
        g = dict(ZEC_3_95, cTime="1790150356922", uTime="1790488423787")
        d = gh.laufzeit_tage(g)
        # 337107 Sekunden / 86400 = 3.9017 Tage - das 3.95-Tage-Grid der Antwort
        self.assertIsNotNone(d)
        self.assertAlmostEqual(d, 3.90, places=1)

    def test_ohne_utime_ist_none(self):
        g = dict(ZEC_3_95, uTime="")
        self.assertIsNone(gh.laufzeit_tage(g))

    def test_ohne_beide_ist_none(self):
        self.assertIsNone(gh.laufzeit_tage(OHNE_ZIEL))


class RichtungsgewinnTest(unittest.TestCase):
    def test_grundformel(self):
        self.assertAlmostEqual(gh.richtungsgewinn(ZEC_3_95), 46.76 - 35.28)

    def test_short_grid(self):
        self.assertAlmostEqual(gh.richtungsgewinn(PUMP_SHORT), 23.91 - 7.31)

    def test_fehlende_zahlen_sind_none_nicht_null(self):
        self.assertIsNone(gh.richtungsgewinn(OHNE_ZIEL))

    def test_leere_strings_sind_none(self):
        g = dict(ZEC_3_95, gridProfit="", totalPnl="")
        self.assertIsNone(gh.richtungsgewinn(g))


class StopTest(unittest.TestCase):
    def test_leerer_stop_ist_kein_stop(self):
        self.assertFalse(gh.stop_vorhanden(ZEC_3_95))

    def test_gesetzter_stop_ist_stop(self):
        self.assertTrue(gh.stop_vorhanden(PUMP_SHORT))


class MarktbewegungTest(unittest.TestCase):
    def test_erste_gegen_letzte_kerze_im_fenster(self):
        # cTime 1790150356 = 01.09., uTime 1790488423 = 05.09. -> Kerzen 2-5
        g = dict(ZEC_3_95, cTime="1790150356922", uTime="1790488423787")
        w = gh.marktbewegung(g, KERZEN)
        self.assertIsNotNone(w)
        self.assertAlmostEqual(w, (110.0 / 103.0 - 1.0) * 100.0)

    def test_fenster_vor_der_ersten_kerze_ist_none(self):
        g = dict(ZEC_3_95, cTime="1700000000000", uTime="1700100000000")
        self.assertIsNone(gh.marktbewegung(g, KERZEN))

    def test_ohne_kerzen_ist_none(self):
        self.assertIsNone(gh.marktbewegung(ZEC_3_95, []))

    def test_ohne_zeiten_ist_none(self):
        self.assertIsNone(gh.marktbewegung(OHNE_ZIEL, KERZEN))


class AuswerteTest(unittest.TestCase):
    def test_zeile_hat_alle_felder(self):
        x = gh.auswerte(ZEC_3_95, KERZEN)
        self.assertEqual(x["seite"], "LONG")
        self.assertEqual(x["inst"], ZEC_3_95["instId"])
        self.assertEqual(x["netzgewinn"], 35.28)
        self.assertEqual(x["gesamt"], 46.76)
        self.assertAlmostEqual(x["richtungsgewinn"], 46.76 - 35.28)
        self.assertFalse(x["stop"])
        self.assertEqual(x["hebel"], "-")

    def test_short_seite(self):
        x = gh.auswerte(PUMP_SHORT, [])
        self.assertEqual(x["seite"], "SHORT")
        self.assertTrue(x["stop"])

    def test_unbekannte_richtung_bleibt_roh(self):
        g = dict(ZEC_3_95, direction="neutral")
        self.assertEqual(gh.auswerte(g, [])["seite"], "neutral")


class SummenTest(unittest.TestCase):
    def test_summen_nur_belegte_werte(self):
        z = [gh.auswerte(ZEC_3_95, []), gh.auswerte(PUMP_SHORT, []),
             gh.auswerte(OHNE_ZIEL, [])]
        s = gh.summen(z)
        self.assertEqual(s["n"], 3)
        self.assertAlmostEqual(s["netz"], 35.28 + 7.31)
        self.assertAlmostEqual(s["richtung"], (46.76 - 35.28) + (23.91 - 7.31))
        self.assertEqual(s["ohne_stop"], 1)  # nur ZEC hat keinen Stop
        self.assertAlmostEqual(s["invest"], 153.17 + 50.0)

    def test_ohne_stop_zaehlt_nur_belegtes(self):
        z = [gh.auswerte(OHNE_ZIEL, []), gh.auswerte(PUMP_SHORT, [])]
        s = gh.summen(z)
        self.assertEqual(s["netz"], 7.31)  # leerer gridProfit zaehlt nicht mit
        self.assertEqual(s["ohne_stop"], 0)  # OH,NE_ZIEL hat Stop gesetzt


if __name__ == "__main__":
    unittest.main()
