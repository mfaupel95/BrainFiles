"""Tests: eingelegt.json laden - defekt/fehlend bricht lauf nicht ab.

Bauplan-Abschnitt 6, Test 1: Ein defektes oder fehlendes eingelegt.json darf
den lauf nicht abbrechen; leer = alter Weg (Rangliste).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parent
for p in (HANDEL / "scanner", HANDEL, SPUR):
    if str(p) in sys.path:
        sys.path.remove(str(p))
    sys.path.insert(0, str(p))

import handeln as h                                                 # noqa: E402

assert str(Path(h.__file__).resolve()).startswith(str(SPUR)), h.__file__


class Laden(unittest.TestCase):
    def test_fehlende_datei_ist_leer(self):
        with patch.object(h, "EINGELEGT", str(SPUR / "gibt_es_nicht.json")):
            self.assertEqual(h.lade_eingelegt(), [])

    def test_defekte_datei_ist_leer_und_meldet(self):
        d = SPUR / "_defekt_eingelegt.json"
        d.write_text("{ kaputt", encoding="utf-8")
        try:
            with patch.object(h, "EINGELEGT", str(d)):
                with patch("builtins.print") as pr:
                    self.assertEqual(h.lade_eingelegt(), [])
                self.assertTrue(any("nicht lesbar" in str(a) for a in pr.call_args_list))
        finally:
            d.unlink(missing_ok=True)

    def test_leere_liste_ist_der_alte_weg(self):
        # leer -> kandidaten_aus_auftraegen liefert nichts, lauf faellt auf
        # die Rangliste zurueck (kein eingelegter Kandidat).
        z = {"eingelegt": []}
        self.assertEqual(h.kandidaten_aus_auftraegen(z, {}), [])

    def test_kein_array_ist_leer(self):
        d = SPUR / "_kein_array.json"
        d.write_text('{"a": 1}', encoding="utf-8")
        try:
            with patch.object(h, "EINGELEGT", str(d)):
                self.assertEqual(h.lade_eingelegt(), [])
        finally:
            d.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
