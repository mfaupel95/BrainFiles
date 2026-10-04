"""Bindung: alle Spuren schreiben und lesen ihren Bestand ueber atomar.py.

Zwei Ebenen, weil ein Test allein nicht reicht:
  1. Quelltext: kein direktes open(ZUSTAND, "w")/write_text und kein
     "OSError/ValueError -> leerer Bestand" mehr in den Spuren.
  2. Verhalten: ausgewaehlte Spuren wirklich laden und mit defekter Datei
     fahren - der Bestand darf nicht still leer werden.
"""

import importlib.util
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HANDEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HANDEL))

# Spuren, deren Bestand (zustand.json) produktiv geschrieben wird.
SPUREN = [
    "xperp/handeln.py", "moondev_funding/handeln.py", "gitter/handeln.py",
    "supertrend/handeln.py", "macd_mtf/handeln.py", "squeeze/handeln.py",
    "swap/handeln.py", "wavetrend/handeln.py", "mosaic/handeln.py",
    "moondev_marktlage/live_kraken.py", "omniquant/handeln.py",
    "nautilus_kraken/handeln.py", "kraken/handeln.py", "scanner/handeln.py",
    "orb/handeln.py", "orbk/handeln.py", "spiegel/spiegel.py",
    "kopier/kopier.py", "spur_buch.py",
]


def _text(rel):
    return (HANDEL / rel).read_text(encoding="utf-8")


class QuelltextTest(unittest.TestCase):
    def test_kein_direktes_schreiben_des_bestands(self):
        for rel in SPUREN:
            s = _text(rel)
            self.assertNotRegex(s, r'open\((?:pfad or )?ZUSTAND, "w"', rel)
            self.assertNotIn("ZUSTAND.write_text", s, rel)

    def test_schreibweg_geht_ueber_atomar(self):
        for rel in SPUREN:
            self.assertIn("atomar.schreibe_json", _text(rel), rel)

    def test_lader_fangen_defekt_nicht_als_leer(self):
        # "except (OSError, ValueError)" direkt in lade_zustand = leerer Bestand
        for rel in SPUREN:
            m = re.search(r"def lade_zustand\(.*?(?=\ndef )", _text(rel), re.S)
            if m:
                self.assertNotIn("except (OSError, ValueError)", m.group(0), rel)

    def test_lader_liest_ueber_atomar(self):
        for rel in SPUREN:
            m = re.search(r"def lade_zustand\(.*?(?=\ndef )", _text(rel), re.S)
            if m:
                self.assertIn("atomar.lade_json", m.group(0), rel)


def _lade_modul(rel, name):
    """Eine Spur wie der Dauerlauf laden: eigener Ordner vorn auf sys.path."""
    ordner = str((HANDEL / rel).parent)
    sys.path.insert(0, ordner)
    try:
        spec = importlib.util.spec_from_file_location(name, HANDEL / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(ordner)


class VerhaltenTest(unittest.TestCase):
    """Nur Spuren, die sich ohne Netz/Zusatzpakete importieren lassen."""

    def _spur(self, rel, name):
        try:
            return _lade_modul(rel, name)
        except Exception as e:                                 # noqa: BLE001
            self.skipTest("%s nicht ladbar in dieser Umgebung: %s" % (rel, e))

    def _pruefe(self, rel, name):
        mod = self._spur(rel, name)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        alt = mod.ZUSTAND
        mod.ZUSTAND = (Path(tmp.name) / "zustand.json"
                       if isinstance(alt, Path)
                       else os.path.join(tmp.name, "zustand.json"))
        self.addCleanup(setattr, mod, "ZUSTAND", alt)

        z = mod.lade_zustand()                         # Datei fehlt: Vorgabe
        self.assertIsInstance(z, dict)
        # Eigenes Feld statt "positionen": manche Spur leitet das beim
        # Schreiben selbst ab (gitter) und ueberschriebe die Testdaten.
        z["_stand"] = 1
        mod.schreibe_zustand(z)
        z["_stand"] = 2
        mod.schreibe_zustand(z)
        self.assertEqual(mod.lade_zustand()["_stand"], 2)

        with open(mod.ZUSTAND, "w", encoding="utf-8") as f:
            f.write('{"positionen": [')                # Absturz mitten im Schreiben
        z2 = mod.lade_zustand()                        # Sicherung, NICHT leer
        self.assertEqual(z2["_stand"], 1)

        os.remove(str(mod.ZUSTAND) + ".bak")
        # Keine Sicherung: laut. Jede Spur laedt ihre EIGENE atomar-Kopie
        # (per Pfad), die Klasse ist daher eine andere als hier - Name pruefen.
        with self.assertRaises(Exception) as ctx:
            mod.lade_zustand()
        self.assertEqual(type(ctx.exception).__name__, "ZustandDefekt")

    def test_xperp(self):
        self._pruefe("xperp/handeln.py", "t_xperp_handeln")

    def test_gitter(self):
        self._pruefe("gitter/handeln.py", "t_gitter_handeln")

    def test_supertrend(self):
        self._pruefe("supertrend/handeln.py", "t_supertrend_handeln")

    def test_scanner(self):
        self._pruefe("scanner/handeln.py", "t_scanner_handeln")

    def test_orb(self):
        self._pruefe("orb/handeln.py", "t_orb_handeln")


if __name__ == "__main__":
    unittest.main()
