"""Tests fuer xperp/geister_nachziehen.py und die Hermes-Wache dazu.

Beide arbeiten auf TEMP-Journalen - nie auf einem echten Buch. Die Wache wird
per Pfad geladen (sie liegt unter Agenten/Hermes/scripts).

ANLASS (22.09.2026): Die Geisterpruefung schrieb `margin_usd = 0.00`; die
Wachen lesen die schliessen-Zeile als ERLoes, eine handgeschlossene Position
zaehlte also als Vollverlust ihres Einsatzes (HBAR: -16.84 USD in der
Drawdown-Kurve). Der Code ist repariert - alte Zeilen tragen die 0.00 aber
weiter, und genau die zieht das Werkzeug nach.
"""

from __future__ import annotations

import csv
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve()
SPUR = HIER.parents[1]                   # .../Agenten/Handel/xperp
AGENTEN = HIER.parents[3]                # .../Agenten
WERKZEUG = SPUR / "geister_nachziehen.py"
WACHE = AGENTEN / "Hermes" / "scripts" / "geister-zeilen-wache.py"

sys.path.insert(0, str(SPUR))

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "familie", "preis",
           "kontrakte", "nominal_usd", "margin_usd", "hebel", "stop", "ziel",
           "liq", "liq_abstand", "funding_pct", "gebuehr_pct", "quote_noetig",
           "quote_beob", "grund"]


def _lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, str(pfad))
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


def _zeile(aktion, inst, margin, grund="", kontrakte="10.0"):
    return ["2026-09-21T18:33:22+00:00", "live", aktion, inst, "long", "krypto",
            "90.0", kontrakte, "100.00", margin, "5.0"] + [""] * 8 + [grund]


def _journal(pfad, zeilen):
    with open(pfad, "w", newline="", encoding="utf-8") as f:
        s = csv.writer(f)
        s.writerow(SPALTEN)
        s.writerows(zeilen)


class Werkzeug(unittest.TestCase):
    """geister_nachziehen.py: kaputte Zeile -> echter Wert."""

    @classmethod
    def setUpClass(cls):
        cls.w = _lade(WERKZEUG, "geister_nachziehen_t")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pfad = os.path.join(self.tmp.name, "handelsjournal.csv")

    def _kaputt(self, pfad=None):
        kopf, zeilen, namen, kaputt, fehler = self.w._kaputte_zeilen(
            pfad or self.pfad)
        return kaputt, fehler

    def test_kaputte_zeile_wird_erkannt(self):
        _journal(self.pfad, [
            _zeile("eroeffnen", "X-1", "16.84"),
            _zeile("schliessen", "X-1", "0.00", "buchbereinigung_geist"),
        ])
        kaputt, fehler = self._kaputt()
        self.assertIsNone(fehler)
        self.assertEqual(len(kaputt), 1)
        self.assertEqual(kaputt[0][3], "16.84")

    def test_gesunde_zeile_bleibt_unberuehrt(self):
        _journal(self.pfad, [
            _zeile("eroeffnen", "X-1", "16.84"),
            _zeile("schliessen", "X-1", "18.34", "buchbereinigung_geist"),
        ])
        kaputt, _ = self._kaputt()
        self.assertEqual(kaputt, [], "0.00 erklaert den Schaden nicht")

    def test_fremder_grund_bleibt_unberuehrt(self):
        # Ein Stop, der wirklich 0 zurueckgab, ist kein Schreibfehler.
        _journal(self.pfad, [
            _zeile("eroeffnen", "X-1", "16.84"),
            _zeile("schliessen", "X-1", "0.00", "stop"),
        ])
        kaputt, _ = self._kaputt()
        self.assertEqual(kaputt, [])

    def test_einsatz_kommt_aus_der_fifo_paarung(self):
        # Zwei Anlaeufe desselben Instruments: die Zeile gehoert zum AELTESTEN.
        _journal(self.pfad, [
            _zeile("eroeffnen", "X-1", "11.11"),
            _zeile("eroeffnen", "X-1", "22.22"),
            _zeile("schliessen", "X-1", "0.00", "buchbereinigung_geist"),
        ])
        kaputt, _ = self._kaputt()
        self.assertEqual(kaputt[0][3], "11.11")

    def test_anwenden_schreibt_und_sichert(self):
        _journal(self.pfad, [
            _zeile("eroeffnen", "X-1", "16.84"),
            _zeile("schliessen", "X-1", "0.00", "buchbereinigung_geist"),
        ])
        vorher = os.path.getsize(self.pfad)
        self.w.nachziehen(spur=os.path.basename(self.tmp.name), anwenden=False)
        self.assertEqual(os.path.getsize(self.pfad), vorher,
                         "die Vorschau schreibt nicht")

    def test_korrektur_ist_wiederholbar(self):
        _journal(self.pfad, [
            _zeile("eroeffnen", "X-1", "16.84"),
            _zeile("schliessen", "X-1", "0.00", "buchbereinigung_geist"),
        ])
        # Das Werkzeug sucht seine Journale selbst -> hier direkt die Regel:
        kopf, zeilen, namen, kaputt, _ = self.w._kaputte_zeilen(self.pfad)
        for n, _inst, _alt, neu in kaputt:
            zeilen[n][namen.index("margin_usd")] = neu
        with open(self.pfad, "w", newline="", encoding="utf-8") as f:
            f.write(kopf)
            csv.writer(f).writerows(zeilen)
        kaputt2, _ = self._kaputt()
        self.assertEqual(kaputt2, [], "nach der Korrektur ist nichts mehr offen")

    def test_kein_eroeffnen_schema_wird_uebersprungen(self):
        with open(self.pfad, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["zeit", "modus", "aktion", "inst",
                                    "margin_usd", "grund"])
            csv.writer(f).writerow(["2026-09-22T00:00:00+00:00", "papier",
                                    "verkauf", "X-1", "0.00",
                                    "buchbereinigung_geist"])
        _k, _z, _n, kaputt, fehler = self.w._kaputte_zeilen(self.pfad)
        self.assertEqual(kaputt, [])
        self.assertIn("eroeffnen", fehler or "")


class Wache(unittest.TestCase):
    """Die Hermes-Wache: korrigiert, schweigt, wenn nichts zu tun ist."""

    @classmethod
    def setUpClass(cls):
        cls.w = _lade(WERKZEUG, "geister_nachziehen_w")
        cls.wache = _lade(WACHE, "geister_zeilen_wache_t")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pfad = os.path.join(self.tmp.name, "handelsjournal.csv")

    def test_schweigt_wenn_nichts_kaputt_ist(self):
        _journal(self.pfad, [_zeile("eroeffnen", "X-1", "16.84")])
        meldungen, fehler = self.wache.wachen(werkzeug=self.w,
                                              journale=[self.pfad])
        self.assertIsNone(fehler)
        self.assertEqual(meldungen, [], "leere Ausgabe = nichts senden")

    def test_meldet_und_korrigiert(self):
        _journal(self.pfad, [
            _zeile("eroeffnen", "X-1", "16.84"),
            _zeile("schliessen", "X-1", "0.00", "buchbereinigung_geist"),
        ])
        meldungen, fehler = self.wache.wachen(werkzeug=self.w, journale=[self.pfad],
                                              min_ruhe_min=-1)
        self.assertIsNone(fehler)
        self.assertTrue(meldungen)
        _k, _z, _n, kaputt, _ = self.w._kaputte_zeilen(self.pfad)
        self.assertEqual(kaputt, [], "die Wache korrigiert wirklich")

    def test_frisch_geschriebenes_journal_bleibt_liegen(self):
        """Ein laufender Zyklus darf nicht mitten im Schreiben erwischt werden."""
        _journal(self.pfad, [
            _zeile("eroeffnen", "X-1", "16.84"),
            _zeile("schliessen", "X-1", "0.00", "buchbereinigung_geist"),
        ])
        meldungen, fehler = self.wache.wachen(werkzeug=self.w, journale=[self.pfad],
                                              min_ruhe_min=60)
        self.assertIsNone(fehler)
        self.assertEqual(meldungen, [])
        _k, _z, _n, kaputt, _ = self.w._kaputte_zeilen(self.pfad)
        self.assertEqual(len(kaputt), 1, "unberuehrt gelassen")

    def test_vorschau_schreibt_nicht(self):
        _journal(self.pfad, [
            _zeile("eroeffnen", "X-1", "16.84"),
            _zeile("schliessen", "X-1", "0.00", "buchbereinigung_geist"),
        ])
        meldungen, _ = self.wache.wachen(werkzeug=self.w, journale=[self.pfad],
                                         min_ruhe_min=-1, anwenden=False)
        self.assertTrue(meldungen)
        _k, _z, _n, kaputt, _ = self.w._kaputte_zeilen(self.pfad)
        self.assertEqual(len(kaputt), 1, "Vorschau laesst die Zeile stehen")


if __name__ == "__main__":
    unittest.main()
