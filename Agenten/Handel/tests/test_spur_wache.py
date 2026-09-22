"""Tests fuer die Spur-Wache: die zwei neuen Spuren supertrend und iv_waelle.

ANLASS (Auftrag Max, 22.09.2026: "Ja aufnehmen"). Beide Spuren sind still, und
bei beiden ist Stille der Normalfall:

  * `supertrend` stand nach einem stillen `ImportError` FUENF TAGE ohne Signal,
    ohne dass es auffiel.
  * `iv_waelle` hat seit dem 19.09. keine einzige Journalzeile geschrieben.

Ohne Wache ist "wartet korrekt" nicht von "kaputt" zu unterscheiden. Geprueft
wird hier die ENTSCHEIDUNG der beiden Funktionen — ohne Netz, mit
nachgebauten Spuren (`_spur_laden` wird ersetzt) und einem Temp-Ordner fuer
den Zustand. Die echten Buecher werden nur gelesen, nie geschrieben.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
WACHE = HIER.parents[1] / "Hermes" / "scripts" / "spur-wache.py"


def _lade(pfad, name="spur_wache_t"):
    spec = importlib.util.spec_from_file_location(name, str(pfad))
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


KERZEN = [[str(1700000000 + i * 3600), "1", "1", "1", "100", "1"]
          for i in range(400)]


def _supertrend_stub(signal_wert):
    return types.SimpleNamespace(
        lade_kerzen=lambda inst, takt, anzahl: KERZEN,
        signal=lambda k, idx: signal_wert,
        atr_abs=lambda k, idx, n=14: 1.0,
    )


def _ivwaelle_stub(daten, sig):
    return types.SimpleNamespace(
        _hole_markt=lambda w: (daten, {}, []),
        spanne_und_signal=lambda d, w: sig,
    )


class SupertrendZurueckgehalten(unittest.TestCase):
    def setUp(self):
        self.m = _lade(WACHE)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.alt = self.m.HANDEL
        self.m.HANDEL = Path(self.tmp.name)
        self.addCleanup(lambda: setattr(self.m, "HANDEL", self.alt))
        self.w = {"instrument": "BTC-USDT-SWAP", "mindest_kerzen": 300,
                  "max_offene_positionen": 4}

    def _zustand(self, n):
        p = self.m.HANDEL / "supertrend"
        p.mkdir(parents=True, exist_ok=True)
        (p / "zustand.json").write_text(
            json.dumps({"positionen": [{"inst": "X%d" % i} for i in range(n)]}),
            encoding="utf-8")

    def test_wende_mit_vollem_buch_wird_gemeldet(self):
        self._zustand(4)
        self.m._spur_laden = lambda spur: _supertrend_stub(("short", 100.0))
        kennung, text = self.m._zurueck_supertrend(self.w)
        self.assertTrue(kennung)
        self.assertIn("Buch voll", text)

    def test_ohne_wende_bleibt_es_still(self):
        self._zustand(0)
        self.m._spur_laden = lambda spur: _supertrend_stub(None)
        self.assertEqual(self.m._zurueck_supertrend(self.w), (None, None))

    def test_fehler_wird_gemeldet_nicht_verschluckt(self):
        def platzt(spur):
            raise ImportError("indikatoren fehlen")
        self.m._spur_laden = platzt
        kennung, text = self.m._zurueck_supertrend(self.w)
        self.assertIsNone(kennung, "kein Signal, sondern ein Fehler")
        self.assertIn("nicht ladbar", text)

    def test_zu_wenige_kerzen_sind_kein_befund(self):
        self._zustand(0)
        self.m._spur_laden = lambda spur: types.SimpleNamespace(
            lade_kerzen=lambda inst, takt, anzahl: KERZEN[:10],
            signal=lambda k, idx: ("short", 1.0),
            atr_abs=lambda k, idx, n=14: 1.0)
        self.assertEqual(self.m._zurueck_supertrend(self.w), (None, None))


class IvWaelleZurueckgehalten(unittest.TestCase):
    def setUp(self):
        self.m = _lade(WACHE)
        self.w = {"instrument": "BTC-PERPETUAL", "naehe_prozent": 0.5}

    def _sig(self, lage, strike, sigma=1.5, richtung="kein_signal", spot=100000.0):
        return ({"richtung": richtung, "spot": spot,
                 "lagen": {"call_wand": {"lage": lage, "strike": strike,
                                         "abstand_sigma": sigma}}},
                {"BTC-PERPETUAL": {"spot": spot}})

    def test_handelbare_wand_in_der_ferne_wird_gemeldet(self):
        sig, daten = self._sig("handelbar", 105000.0)
        self.m._spur_laden = lambda spur: _ivwaelle_stub(daten, sig)
        kennung, text = self.m._zurueck_ivwaelle(self.w)
        self.assertTrue(kennung, "einmal je Tag und Wand")
        self.assertIn("handelbare Wand", text)
        self.assertIn("5.00 %", text)

    def test_kurs_an_der_wand_ist_kein_befund(self):
        sig, daten = self._sig("handelbar", 100200.0)
        self.m._spur_laden = lambda spur: _ivwaelle_stub(daten, sig)
        self.assertEqual(self.m._zurueck_ivwaelle(self.w), (None, None))

    def test_signal_da_heisst_die_spur_handelt(self):
        sig, daten = self._sig("handelbar", 100200.0, richtung="short")
        self.m._spur_laden = lambda spur: _ivwaelle_stub(daten, sig)
        self.assertEqual(self.m._zurueck_ivwaelle(self.w), (None, None))

    def test_nicht_handelbare_wand_ist_melde_rauschen(self):
        # "zu weit" (mehr als 3 Sigma) ist eine Lage, kein Signal - taeglich
        # gemeldet waere es Rauschen.
        sig, daten = self._sig("zu_weit", 200000.0, sigma=9.0)
        self.m._spur_laden = lambda spur: _ivwaelle_stub(daten, sig)
        self.assertEqual(self.m._zurueck_ivwaelle(self.w), (None, None))

    def test_datenfehler_wird_nicht_als_signal_gemeldet(self):
        self.m._spur_laden = lambda spur: types.SimpleNamespace(
            _hole_markt=lambda w: ({}, {}, ["DVOL nicht erreichbar"]),
            spanne_und_signal=lambda d, w: {})
        self.assertEqual(self.m._zurueck_ivwaelle(self.w), (None, None))


class BeideSpurenSindAngemeldet(unittest.TestCase):
    def test_wache_kennt_vier_spuren(self):
        m = _lade(WACHE)
        self.assertEqual(sorted(m.SPUREN),
                         ["iv_waelle", "liq_wand", "supertrend",
                          "trendwende_btc"])


if __name__ == "__main__":
    unittest.main()
