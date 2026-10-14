"""Handergebnisse und die Kapitalkurve der Strategie (Auftrag Max 14.10.2026, Variante C).

BEFUND: Der Kill vom 06.10.2026 (Ruecklauf 835 USD) kam von einer uebernommenen
Handposition (STRK), und die Halbierung (30 USD) lag mit rund -400 USD
Handergebnis dauerhaft darunter. `handergebnis_in_kapitalkurve: false` nimmt
Runden, die mit `fremdposition_uebernommen` eroeffnet wurden, aus Halbierung und
Kill heraus; der Konto-Ruecklauf (alle Runden) bleibt als reine Meldung.
"""

from __future__ import annotations

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

SPUR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPUR))

import wachen_xperp as wx                                              # noqa: E402

KOPF = ["zeit", "modus", "aktion", "inst", "seite", "margin_usd", "grund"]
STRAT = "AAA-USD_UM_XPERP-310101"
HAND = "STRK-USD_UM_XPERP-310919"


def schreibe(pfad, zeilen):
    with open(pfad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KOPF)
        w.writeheader()
        for i, z in enumerate(zeilen):
            z = dict(z)
            z.setdefault("zeit", "2026-10-%02dT10:00:00+00:00" % (i + 1))
            z.setdefault("modus", "live")
            z.setdefault("seite", "long")
            w.writerow(z)


def runde(inst, einsatz, zurueck, auf_grund="punkte 80", zu_grund="stop"):
    return [dict(aktion="eroeffnen", inst=inst, margin_usd=einsatz, grund=auf_grund),
            dict(aktion="schliessen", inst=inst, margin_usd=zurueck, grund=zu_grund)]


import json                                                            # noqa: E402

# Echte Wache als Grundlage (alle Felder, die lage() liest), nur die Schwellen
# fuer den Test fest.
W = json.loads((SPUR / "wachen.json").read_text(encoding="utf-8"))
W.update(drawdown_halbierung_usd=30.0, kill_switch_gesamt_usd=100.0,
         handergebnis_in_kapitalkurve=True)
W.pop("konto_warnschwelle_usd", None)


class HandKurveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pfad = os.path.join(self.tmp.name, "handelsjournal.csv")
        # Strategie: +20 USD. Hand: -150 USD (uebernommen, dann als Geist ausgebucht)
        schreibe(self.pfad,
                 runde(STRAT, 50, 70) +
                 runde(HAND, 200, 50, auf_grund="fremdposition_uebernommen",
                       zu_grund="buchbereinigung_geist"))

    def lage(self, **w):
        return wx.lage(dict(W, **w), self.pfad, {})

    def test_runden_tragen_ihre_herkunft(self):
        r = {x["inst"]: x["herkunft"] for x in wx.runden_aus_journal(self.pfad)}
        self.assertEqual(r, {STRAT: "strategie", HAND: "handgriff"})

    def test_standard_zaehlt_alle_runden_wie_bisher(self):
        s = self.lage()
        self.assertAlmostEqual(s["ruecklauf_usd"], 150.0)
        self.assertTrue(s["kill"])                       # 150 >= 100
        self.assertEqual(s["groessenfaktor"], 0.5)

    def test_ohne_handergebnis_in_der_kurve_keine_halbierung_und_kein_kill(self):
        s = self.lage(handergebnis_in_kapitalkurve=False)
        self.assertAlmostEqual(s["ruecklauf_usd"], 0.0)
        self.assertFalse(s["kill"])
        self.assertEqual(s["groessenfaktor"], 1.0)
        self.assertEqual(s["runden_hand"], 1)

    def test_konto_ruecklauf_bleibt_auf_allen_runden(self):
        s = self.lage(handergebnis_in_kapitalkurve=False)
        self.assertAlmostEqual(s["konto_ruecklauf_usd"], 150.0)

    def test_kontowarnung_nur_mit_schwelle(self):
        self.assertFalse(self.lage(handergebnis_in_kapitalkurve=False)["konto_warnung"])
        s = self.lage(handergebnis_in_kapitalkurve=False, konto_warnschwelle_usd=120.0)
        self.assertTrue(s["konto_warnung"])
        self.assertFalse(s["kill"])                      # nur Meldung, kein Kill
        s2 = self.lage(handergebnis_in_kapitalkurve=False, konto_warnschwelle_usd=200.0)
        self.assertFalse(s2["konto_warnung"])

    def test_eigene_strategieverluste_zaehlen_weiter(self):
        schreibe(self.pfad, runde(STRAT, 100, 20, zu_grund="stop") +
                 runde(HAND, 200, 50, auf_grund="fremdposition_uebernommen",
                       zu_grund="buchbereinigung_geist"))
        s = self.lage(handergebnis_in_kapitalkurve=False)
        self.assertAlmostEqual(s["ruecklauf_usd"], 80.0)  # nur die eigene Runde
        self.assertEqual(s["groessenfaktor"], 0.5)

    def test_echte_wachen_schalten_die_trennung_ein(self):
        w = json.loads((SPUR / "wachen.json").read_text(encoding="utf-8"))
        self.assertIs(w.get("handergebnis_in_kapitalkurve"), False)
        self.assertGreater(float(w.get("konto_warnschwelle_usd") or 0), 0)


if __name__ == "__main__":
    unittest.main()
