#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests der mosaic-Stop-Wache - die REGELN, nicht die Tageswerte.

Geprueft werden die reinen Funktionen ``text_aus_bilanz`` und
``neu_zu_melden``: welche Lage wird gemeldet, welche nicht, und wird dieselbe
Feststellung wirklich nur einmal gemeldet. Kein Netz, kein Boersenzugang.

Aufruf:
    python test_mosaic_stop_wache.py
"""

import datetime as dt
import importlib.util
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent


def _lade():
    spec = importlib.util.spec_from_file_location(
        "mosaic_stop_wache_test", HIER / "mosaic-stop-wache.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


w = _lade()


def bilanz(*befunde, **zahlen):
    b = {"geprueft": zahlen.get("geprueft", len(befunde)), "ok": 0,
         "nachgesetzt": 0, "fehlt_weiter": 0, "weg": 0, "ausgebucht": 0,
         "waisen": 0, "unklar": 0, "befunde": list(befunde)}
    b.update({k: v for k, v in zahlen.items() if k in b})
    return b


def bf(inst, lage, text=""):
    return {"inst": inst, "boerse": "kraken", "lage": lage, "text": text}


class TextTest(unittest.TestCase):
    def test_alles_in_ordnung_ergibt_keine_meldung(self):
        b = bilanz(bf("BTC-USDC", "ok"), bf("ETH-USDC", "ok"), ok=2)
        self.assertEqual(w.text_aus_bilanz(b), [])

    def test_fehlender_stop_wird_genannt(self):
        b = bilanz(bf("BTC-USDC", "ok"), bf("ETH-USDC", "stop_fehlt", "0.04"),
                   ok=1, fehlt_weiter=1)
        zeilen = w.text_aus_bilanz(b)
        self.assertEqual(len(zeilen), 1)
        self.assertIn("ETH-USDC", zeilen[0])
        self.assertIn("OHNE wirksamen Stop", zeilen[0])

    def test_weggelaufene_position_wird_genannt(self):
        b = bilanz(bf("SOL-USDC", "weg", "Bestand 0"), weg=1)
        zeilen = w.text_aus_bilanz(b)
        self.assertEqual(len(zeilen), 1)
        self.assertIn("nicht mehr vorhanden", zeilen[0])

    def test_waisenstop_wird_genannt(self):
        b = bilanz(bf("ETH-USDC", "waisen", "Stop P1"), waisen=1)
        self.assertIn("Stop ohne Position", w.text_aus_bilanz(b)[0])

    def test_nachgesetzt_und_ausgebucht_gelten_nicht_als_stoerung(self):
        b = bilanz(bf("BTC-USDC", "nachgesetzt"), bf("SOL-USDC", "ausgebucht"),
                   nachgesetzt=1, ausgebucht=1)
        self.assertEqual(w.text_aus_bilanz(b), [])

    def test_abgleich_ohne_aussage_wird_gemeldet(self):
        """Unlesbare Boerse ist keine gute Nachricht - sonst bedeutet Stille
        faelschlich 'alles gut'."""
        b = bilanz(bf("BTC-USDC", "unklar_stop", "Netzfehler"),
                   bf("ETH-USDC", "unklar_stop", "Netzfehler"), unklar=2)
        zeilen = w.text_aus_bilanz(b)
        self.assertEqual(len(zeilen), 2)

    def test_leeres_buch_ergibt_keine_meldung(self):
        self.assertEqual(w.text_aus_bilanz(bilanz()), [])


class PauseTest(unittest.TestCase):
    def setUp(self):
        self.jetzt = dt.datetime(2026, 9, 30, 12, 0, 0)

    def test_erste_feststellung_wird_gemeldet(self):
        raus, merk = w.neu_zu_melden(["BTC-USDC (kraken): OHNE wirksamen Stop "
                                      "an der Boerse - 0.0006"],
                                     {}, self.jetzt)
        self.assertEqual(len(raus), 1)
        self.assertEqual(len(merk["gemeldet"]), 1)

    def test_dieselbe_feststellung_wird_nicht_wiederholt(self):
        zeile = "BTC-USDC (kraken): OHNE wirksamen Stop an der Boerse - 0.0006"
        _raus, merk = w.neu_zu_melden([zeile], {}, self.jetzt)
        raus2, _ = w.neu_zu_melden([zeile], merk,
                                   self.jetzt + dt.timedelta(minutes=30))
        self.assertEqual(raus2, [])

    def test_wandernde_zahl_ist_keine_neue_meldung(self):
        """Sonst gilt jeder neue Kurs als neue Feststellung."""
        _r, merk = w.neu_zu_melden(
            ["BTC-USDC (kraken): OHNE wirksamen Stop an der Boerse - 0.0006"],
            {}, self.jetzt)
        raus, _ = w.neu_zu_melden(
            ["BTC-USDC (kraken): OHNE wirksamen Stop an der Boerse - 0.0007"],
            merk, self.jetzt + dt.timedelta(hours=1))
        self.assertEqual(raus, [])

    def test_nach_der_pause_wird_wieder_gemeldet(self):
        zeile = "BTC-USDC (kraken): OHNE wirksamen Stop an der Boerse"
        _r, merk = w.neu_zu_melden([zeile], {}, self.jetzt)
        raus, _ = w.neu_zu_melden([zeile], merk,
                                  self.jetzt + dt.timedelta(hours=7))
        self.assertEqual(len(raus), 1)

    def test_andere_position_ist_eine_neue_meldung(self):
        _r, merk = w.neu_zu_melden(["BTC-USDC (kraken): weg"], {}, self.jetzt)
        raus, _ = w.neu_zu_melden(["ETH-USDC (kraken): weg"], merk, self.jetzt)
        self.assertEqual(len(raus), 1)

    def test_kaputte_merkdatei_sperrt_nichts_dauerhaft(self):
        raus, merk = w.neu_zu_melden(["BTC-USDC (kraken): weg"],
                                     {"gemeldet": {"BTC-USDC|weg": "kaputt"}},
                                     self.jetzt)
        self.assertEqual(len(raus), 1)


class AbgleichTest(unittest.TestCase):
    """Der Vorschau-Abgleich darf das echte Buch nicht anfassen."""

    def test_buch_bleibt_unveraendert(self):
        import json
        import shutil
        import tempfile
        zustand = Path(w.HANDEL) / "mosaic" / "zustand.json"
        if not zustand.exists():
            self.skipTest("kein Buch vorhanden")
        with tempfile.TemporaryDirectory() as d:
            kopie = Path(d) / "zustand.json"
            shutil.copy2(zustand, kopie)
            vorher = kopie.read_bytes()
            try:
                w.sammle(kopie, Path(w.HANDEL) / "mosaic" / "wachen.json")
            except Exception:                                  # noqa: BLE001
                self.skipTest("Boerse nicht erreichbar - hier nicht pruefbar")
            self.assertEqual(kopie.read_bytes(), vorher,
                             "die Wache hat das Buch veraendert")
            self.assertIsInstance(json.loads(kopie.read_text(encoding="utf-8")),
                                  dict)


if __name__ == "__main__":
    unittest.main()