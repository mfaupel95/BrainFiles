"""Gegenprobe fuer spur-wache.py mit NACHGEBAUTEN Spuren.

Die echten Spurenordner bleiben unberuehrt: Journal, Zustand und Wachen
werden auf einen Temp-Ordner umgebogen, die Signal-Pruefung durch eine
Attrappe ersetzt. Geprueft wird die Melde-REGEL:

  - ein Einstieg wird genau EINMAL gemeldet, ein zweiter Lauf schweigt,
  - eine geschlossene Runde nennt G/V und Grund,
  - ein zurueckgehaltenes Signal kommt einmal je Ereignis,
  - Stillstand ab 45 min, danach genau eine Erholungsmeldung,
  - leere Ausgabe, wenn nichts los ist.
"""

from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("spur_wache",
                                              HIER / "spur-wache.py")
sw = importlib.util.module_from_spec(spec)
sys.modules["spur_wache"] = sw
spec.loader.exec_module(sw)

SPALTEN = ["zeit", "aktion", "inst", "richtung", "preis", "einsatz_usd",
           "stop", "ziel", "gv_usd", "grund"]


def _jetzt(minuten_zurueck=0):
    t = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minuten_zurueck)
    return t.isoformat()


class WacheTest(unittest.TestCase):
    spur = "liq_wand"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="spurwache_"))
        self.ordner = self.tmp / self.spur
        self.ordner.mkdir(parents=True)
        (self.ordner / "wachen.json").write_text(
            json.dumps({"instrument": "BTC-USDT-SWAP"}), encoding="utf-8")
        self._journal([])
        self._zustand(0)

        self._handel, self._cache = sw.HANDEL, sw.CACHE
        sw.HANDEL, sw.CACHE = self.tmp, self.tmp / "cache"
        # Attrappe statt echtem Netz-/Modulzugriff.
        self._echt = sw.SPUREN[self.spur]
        self.rueck = (None, None)
        sw.SPUREN[self.spur] = lambda w: self.rueck

    def tearDown(self):
        sw.HANDEL, sw.CACHE = self._handel, self._cache
        sw.SPUREN[self.spur] = self._echt
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- Helfer ---
    def _journal(self, zeilen):
        with (self.ordner / "handelsjournal.csv").open(
                "w", encoding="utf-8", newline="") as fh:
            s = csv.DictWriter(fh, fieldnames=SPALTEN)
            s.writeheader()
            for z in zeilen:
                s.writerow({k: z.get(k, "") for k in SPALTEN})

    def _zustand(self, alter_min):
        (self.ordner / "zustand.json").write_text(
            json.dumps({"letzter_lauf": _jetzt(alter_min)}), encoding="utf-8")

    def _lauf(self):
        return sw.pruefe(self.spur, schreiben=True)

    # --- Tests ---
    def test_stille_wenn_nichts_los_ist(self):
        self.assertEqual(self._lauf(), [])

    def test_einstieg_wird_genau_einmal_gemeldet(self):
        self._journal([{"zeit": _jetzt(5), "aktion": "kauf",
                        "inst": "BTC-USDT-SWAP", "richtung": "long",
                        "preis": "86594.5", "einsatz_usd": "120.00",
                        "stop": "85295.58", "ziel": "87460.44"}])
        erste = self._lauf()
        self.assertEqual(len(erste), 1)
        self.assertIn("ERSTER EINSTIEG", erste[0])
        self.assertIn("86594.5000", erste[0])
        self.assertEqual(self._lauf(), [])          # zweiter Lauf schweigt

    def test_runde_nennt_gv_und_grund(self):
        self._journal([{"zeit": _jetzt(9), "aktion": "kauf",
                        "inst": "BTC-USDT-SWAP", "preis": "86594.5"}])
        self._lauf()
        self._journal([
            {"zeit": _jetzt(9), "aktion": "kauf", "inst": "BTC-USDT-SWAP",
             "preis": "86594.5"},
            {"zeit": _jetzt(1), "aktion": "verkauf", "inst": "BTC-USDT-SWAP",
             "preis": "87460.4", "gv_usd": "5.80", "grund": "ziel"}])
        m = self._lauf()
        self.assertEqual(len(m), 1)
        self.assertIn("RUNDE ZU", m[0])
        self.assertIn("+5.80 USD", m[0])
        self.assertIn("ziel", m[0])

    def test_zurueckgehaltenes_signal_nur_einmal_je_ereignis(self):
        self.rueck = ("2026-09-22 00|86000", "liq_wand: Wand bei 86000 ...")
        self.assertEqual(len(self._lauf()), 1)
        self.assertEqual(self._lauf(), [])          # gleiches Ereignis
        self.rueck = ("2026-09-22 01|85000", "liq_wand: Wand bei 85000 ...")
        self.assertEqual(len(self._lauf()), 1)      # neues Ereignis

    def test_fehler_der_pruefung_wird_gemeldet(self):
        # kennung None + Text = echter Fehler, nicht "kein Signal"
        self.rueck = (None, "Liquidationen nicht abrufbar: timeout")
        m = self._lauf()
        self.assertEqual(len(m), 1)
        self.assertIn("nicht abrufbar", m[0])

    def test_stillstand_und_erholung(self):
        self._zustand(70)
        m = self._lauf()
        self.assertEqual(len(m), 1)
        self.assertIn("STILLSTAND", m[0])
        self.assertEqual(self._lauf(), [])          # nicht wiederholen
        self._zustand(3)
        m = self._lauf()
        self.assertEqual(len(m), 1)
        self.assertIn("laeuft wieder", m[0])

    def test_wache_ueberlebt_kaputte_spur(self):
        def kaputt(w):
            raise RuntimeError("Modul weg")
        sw.SPUREN[self.spur] = kaputt
        # pruefe() reicht durch, main() faengt - hier die Fehlerform pruefen.
        with self.assertRaises(RuntimeError):
            self._lauf()


class TrendwendeTest(WacheTest):
    """Dieselbe Regel, zweite Spur - der Name darf nicht fest verdrahtet sein."""
    spur = "trendwende_btc"


if __name__ == "__main__":
    unittest.main()
