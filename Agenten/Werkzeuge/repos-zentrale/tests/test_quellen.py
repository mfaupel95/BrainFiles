"""Tests fuer quellen.py - die Wurzeln der Zentrale.

Die Regel, die hier festgenagelt wird: eine Wurzel bringt ihren Pfad SELBST mit
(kein absoluter Pfad im Code), Sperrlisten sind Namen und keine Muster, und
jeder Bereich hat eine Ueberschrift und eine Erklaerung.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import quellen  # noqa: E402


class WurzelnTest(unittest.TestCase):
    def test_reihenfolge_und_kennungen_sind_fest(self):
        self.assertEqual(
            quellen.REIHENFOLGE, ("repos", "werkstatt", "projekte", "handel")
        )

    def test_jede_kennung_der_reihenfolge_existiert(self):
        for kennung in quellen.REIHENFOLGE:
            self.assertIsNotNone(quellen.wurzel_von(kennung), kennung)

    def test_unbekannte_kennung_ist_none(self):
        self.assertIsNone(quellen.wurzel_von("gibtsnicht"))

    def test_pfade_sind_relativ_und_werden_angehaengt(self):
        with tempfile.TemporaryDirectory() as t:
            basis = Path(t)
            for w, pfad in quellen.alle(basis):
                self.assertTrue(str(pfad).startswith(str(basis)), pfad)
                self.assertFalse(Path(w.pfad_rel).is_absolute(), w.pfad_rel)

    def test_nur_repos_verlangt_git(self):
        self.assertTrue(quellen.wurzel_von("repos").nur_git)
        for kennung in ("werkstatt", "projekte", "handel"):
            self.assertFalse(quellen.wurzel_von(kennung).nur_git, kennung)

    def test_repos_und_werkstatt_teilen_wurzel_trennen_ueber_git(self):
        # Seit 14.10.2026 liegen die Klone direkt in Werkstatt: REPOS und
        # WERKSTATT lesen dieselbe Wurzel und trennen sich ueber die Git-Regel
        # (REPOS zeigt nur Klone, WERKSTATT laesst Klone aus).
        self.assertEqual(
            quellen.wurzel_von("repos").pfad_rel, quellen.wurzel_von("werkstatt").pfad_rel
        )
        self.assertTrue(quellen.wurzel_von("repos").nur_git)
        self.assertTrue(quellen.wurzel_von("werkstatt").ohne_git)
        self.assertEqual(
            quellen.wurzel_von("projekte").pfad_rel, "Werkstatt/Projekte"
        )

    def test_jeder_bereich_hat_erklaerung_und_titel(self):
        for kennung in quellen.REIHENFOLGE:
            bereich = quellen.bereich(kennung)
            self.assertTrue(bereich.isupper(), bereich)
            self.assertIn(bereich, quellen.BEREICH_ERKLAERUNG)

    def test_werkstatt_und_projekte_teilen_sich_einen_bereich(self):
        self.assertEqual(
            quellen.bereich("werkstatt"), quellen.bereich("projekte")
        )

    def test_sperrliste_ist_namensbasiert(self):
        """Keine Muster: ein Eintrag mit '*' oder '?' wuerde echte Projekte treffen."""
        for name in quellen.UEBERALL_OHNE:
            self.assertNotIn("*", name)
            self.assertNotIn("?", name)
            self.assertNotIn("/", name)

    def test_die_wichtigen_ordner_sind_gesperrt(self):
        for name in (".venv", "node_modules", "__pycache__", ".git", "cache"):
            self.assertIn(name, quellen.UEBERALL_OHNE)

    def test_werkstatt_ohne_git_repos_aus(self):
        # Seit 14.10.2026 liegen die Klone direkt unter Werkstatt - der Bereich
        # REPOS zeigt sie (nur_git), WERKSTATT muss sie auslassen (ohne_git),
        # sonst stuenden dort Doppelzeilen.
        repos = quellen.wurzel_von("repos")
        self.assertTrue(repos.nur_git)
        werkstatt = quellen.wurzel_von("werkstatt")
        self.assertTrue(werkstatt.ohne_git)
        self.assertNotIn("Repos", werkstatt.ohne)  # Repos-Ebene gibt es nicht mehr
        self.assertIn("Projekte", werkstatt.ohne)


if __name__ == "__main__":
    unittest.main()
