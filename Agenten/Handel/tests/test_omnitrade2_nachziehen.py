r"""Nachzieher des omnitrade2-XPERP-Laufs: die Deckung ist RICHTUNGSGEBUNDEN.

Regel (Entscheidung Max 21.10.2026): als Schutz zaehlt nur ein Auftrag mit
``reduceOnly`` UND Seite GEGEN die Position (Short-Position -> Kauf-Stop,
Long-Position -> Verkaufs-Stop). Der Anlass ist konkret: ``okxf.ist_schutz_stop``
prueft nur, OB ein Triggerpreis vorhanden ist - nicht, wen er schuetzt. Ein Stop
der vorigen Richtung blieb nach einem Wechsel liegen und zaehlte als Deckung der
neuen Position; sie stuende nackt da, ohne dass die Wache etwas merkt.

Geprueft wird gegen eine Attrappe, die nur die vier Wege des Nachziehers kennt -
kein Netz, keine Boerse, keine echte Datei.

Aufruf aus `Agenten/Handel/tests`:
    ..\scanner\.venv\Scripts\python.exe -m unittest test_omnitrade2_nachziehen
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
PFAD = os.path.join(HANDEL, "omnitrade2", "nachziehen.py")

_spec = importlib.util.spec_from_file_location("nachziehen_test", PFAD)
nz = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = nz
_spec.loader.exec_module(nz)

INST = "SOL-USD_UM_XPERP-310404"


class FakeOkxf:
    """Nur die Wege, die der Nachzieher benutzt."""

    def __init__(self, pos=None, stops=()):
        self.pos = pos
        self.stops = list(stops)
        self.storniert = []
        self.gestellt = []

    def positionen(self, inst=None):
        return [self.pos] if self.pos else []

    def schutz_stops(self, inst=None):
        return list(self.stops)

    @staticmethod
    def ist_schutz_stop(auftrag):
        return any(
            str(auftrag.get(f) or "").strip()
            for f in ("slTriggerPx", "tpTriggerPx", "moveTriggerPx")
        )

    def algo_stornieren(self, inst, algo_id):
        self.storniert.append(algo_id)
        return []

    def schutz_stop_setzen(self, inst, seite, kontrakte, stop, ziel=None, **kw):
        self.gestellt.append((inst, seite, kontrakte, stop))
        return [{"algoId": "neu"}]


def boersenposition(menge, einstieg=100.0):
    return {"instId": INST, "pos": str(menge), "avgPx": str(einstieg)}


def stop(side, sz, algo="A1", reduce_only="true"):
    return {
        "algoId": algo,
        "instId": INST,
        "side": side,
        "sz": str(sz),
        "slTriggerPx": "102",
        "reduceOnly": reduce_only,
        "ordType": "conditional",
    }


class DecktPositionTest(unittest.TestCase):
    """Eine Regel, vier Faelle - jede Richtung und die reduceOnly-Bedingung."""

    def test_short_wird_von_kauf_stop_gedeckt(self):
        self.assertTrue(nz.deckt_position(stop("buy", 10), "short"))

    def test_short_wird_nicht_von_verkaufs_stop_gedeckt(self):
        self.assertFalse(nz.deckt_position(stop("sell", 10), "short"))

    def test_long_wird_von_verkaufs_stop_gedeckt(self):
        self.assertTrue(nz.deckt_position(stop("sell", 10), "long"))

    def test_ohne_reduce_only_zaehlt_nicht(self):
        self.assertFalse(nz.deckt_position(stop("buy", 10, reduce_only="false"), "short"))


class DeckungTest(unittest.TestCase):
    def test_fremder_stop_zaehlt_nicht_und_wird_zurueckgegeben(self):
        okxf = FakeOkxf(stops=[stop("buy", 10, "B1"), stop("sell", 10, "S1")])
        gedeckt, anzahl, fremde = nz.deckung(okxf, INST, "short")
        self.assertEqual(gedeckt, 10.0)
        self.assertEqual(anzahl, 1)
        self.assertEqual([f["algoId"] for f in fremde], ["S1"])

    def test_ohne_seite_zaehlt_alles(self):
        # Nur fuer Altaufrufer: ohne Richtung ist die Deckung blind.
        okxf = FakeOkxf(stops=[stop("buy", 10, "B1"), stop("sell", 6, "S1")])
        gedeckt, anzahl, fremde = nz.deckung(okxf, INST)
        self.assertEqual(gedeckt, 16.0)
        self.assertEqual(anzahl, 2)
        self.assertEqual(fremde, [])


class LaufTest(unittest.TestCase):
    """Der ganze Weg: Position lesen, Deckung richten, Luecke stellen."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_lauf = nz.LAUF_DATEI
        self.alt_zustand = nz.ZUSTAND
        self.alt_laden = nz.okxf_laden
        nz.LAUF_DATEI = Path(self.tmp.name) / "lauf.json"
        nz.ZUSTAND = Path(self.tmp.name) / "zustand.json"
        nz.LAUF_DATEI.write_text(
            json.dumps({"inst": INST, "quantity": 0.1, "phase": "voll"}), encoding="utf-8"
        )

    def tearDown(self):
        nz.LAUF_DATEI = self.alt_lauf
        nz.ZUSTAND = self.alt_zustand
        nz.okxf_laden = self.alt_laden
        self.tmp.cleanup()

    def _lauf(self, okxf, anwenden=False):
        nz.okxf_laden = lambda: okxf
        return nz.lauf(anwenden=anwenden)

    def test_stop_der_gegenrichtung_wird_storniert_und_luecke_gestellt(self):
        okxf = FakeOkxf(pos=boersenposition(-10), stops=[stop("sell", 10, "S1")])
        ergebnis = self._lauf(okxf, anwenden=True)
        self.assertEqual(okxf.storniert, ["S1"])
        self.assertEqual(okxf.gestellt, [(INST, "short", 10.0, 102.0)])
        self.assertIn("FREMDE Stops (1)", " ".join(ergebnis["handlung"]))
        self.assertEqual(ergebnis["luecke"], 10.0)

    def test_richtiger_stop_gilt_als_vollstaendige_deckung(self):
        okxf = FakeOkxf(pos=boersenposition(-10), stops=[stop("buy", 10)])
        ergebnis = self._lauf(okxf, anwenden=False)
        self.assertIn("Deckung vollstaendig (10.00 von 10.00 Kontrakten)",
                      " ".join(ergebnis["handlung"]))
        self.assertEqual(okxf.gestellt, [])

    def test_vorschau_schreibt_nichts_an_die_boerse(self):
        okxf = FakeOkxf(pos=boersenposition(-10), stops=[stop("sell", 10, "S1")])
        self._lauf(okxf, anwenden=False)
        self.assertEqual(okxf.storniert, [])
        self.assertEqual(okxf.gestellt, [])

    def test_zwei_stufen_werden_nur_als_luecke_gedeckt(self):
        # 20 Kontrakte offen, 10 geschuetzt -> genau 10 nachziehen, kein zweiter
        # Stop derselben Groesse (zwei gleich grosse Stops waeren ein doppelter
        # Ausstieg).
        okxf = FakeOkxf(pos=boersenposition(-20), stops=[stop("buy", 10)])
        ergebnis = self._lauf(okxf, anwenden=True)
        self.assertEqual(okxf.gestellt, [(INST, "short", 10.0, 102.0)])
        self.assertEqual(ergebnis["luecke"], 10.0)


if __name__ == "__main__":
    unittest.main()
