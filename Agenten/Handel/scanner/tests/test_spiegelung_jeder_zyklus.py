"""Bedingung 4 im scanner: JEDER Ausgang des Zyklus spiegelt.

Auftrag Max 21.09.2026 ("Scanner-Spiegelung jeden Zyklus"). Der Fall davor:
Q:\\Handel_Journal\\ablehnungen.csv stand 21:23, lokal 21:40 - die Spiegelung
lag nur am ENDE des Zyklus, und der scanner lief seit 19:22 jeden Zyklus in
die Zeitgrenze (Ursache: der Live-Lauf hielt sich fuer eine Sitzung am
Bildschirm und wartete auf eine Freigabe, die niemand geben kann).

Der Test liest die QUELLE: in `lauf()` muss vor jedem `return` mindestens ein
`_spiegeln(` stehen. Ein neuer Ausgang ohne Spiegelung faellt damit auf, bevor
er in Produktion geht - ein Verhaltenstest waere hier zu teuer (der Zyklus
braucht Netz, Bericht und Zeit).
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

QUELLE = Path(__file__).resolve().parents[1] / "handeln.py"


def _lauf_rumpf():
    t = QUELLE.read_text(encoding="utf-8")
    baum = ast.parse(t)
    for knoten in baum.body:
        if isinstance(knoten, ast.FunctionDef) and knoten.name == "lauf":
            zeilen = t.splitlines()
            return zeilen[knoten.lineno - 1:knoten.end_lineno]
    raise AssertionError("lauf() nicht gefunden")


class JederAusgangSpiegelt(unittest.TestCase):
    def test_vor_jedem_return_steht_eine_spiegelung(self):
        zeilen = _lauf_rumpf()
        gesehen = 0
        ohne = []
        for i, z in enumerate(zeilen, start=1):
            if "_spiegeln(" in z:
                gesehen += 1
            if re.match(r"\s+return\b", z) and gesehen == 0:
                ohne.append((i, z.strip()))
        self.assertEqual(
            ohne, [],
            "Ausgang ohne Spiegelung - Bedingung 4 waere dort verletzt: %s" % ohne)

    def test_erste_spiegelung_steht_ganz_oben(self):
        zeilen = _lauf_rumpf()
        i_mirror = next(i for i, z in enumerate(zeilen) if "_spiegeln(" in z)
        i_return = next(i for i, z in enumerate(zeilen)
                        if re.match(r"\s+return\b", z))
        self.assertLess(i_mirror, i_return,
                        "die Spiegelung muss VOR dem ersten Ausgang stehen")

    def test_ziel_kommt_aus_der_wachen_datei(self):
        # Kein hartes Laufwerk im Code: Q: steht in wachen.json.
        t = QUELLE.read_text(encoding="utf-8")
        i = t.index("def lauf(")
        rumpf = t[i:]
        self.assertNotIn("Q:\\", rumpf[:4000])
        self.assertIn('journal_zweitziel', rumpf[:4000])


if __name__ == "__main__":
    unittest.main()
