"""Die Grenze im Fenster: fremde Zeilen sind sichtbar und benannt.

Diese Datei prueft die Anbindung an `Agenten/FREMD-Liste.json` - nicht die Liste
selbst (das tut `Agenten/Werkzeuge/tests/test_fremd.py`), sondern was die Zentrale
daraus macht: Rolle, Hinweis, Zaehlung. Der Fall, der es ausgeloest hat:
`OpenAlice` stand als gewoehnliche Zeile zwischen unseren Spuren, obwohl es 81 %
der Zeilen in `Agenten/Handel` stellt.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
if str(HIER) not in sys.path:
    sys.path.insert(0, str(HIER))

import fenster  # noqa: E402
import manifest  # noqa: E402
import quellen  # noqa: E402
import scan  # noqa: E402

WURZEL = HIER.parents[2]     # repos-zentrale -> Werkzeuge -> Agenten -> BrainFiles
MANIFEST = HIER / "repos-zentrale.json"
PROFILE = WURZEL / "Agenten" / "Hermes" / "profiles"


def alle_zeilen() -> list[manifest.Zeile]:
    """Die echten Zeilen der Zentrale - aus Manifest und Platte."""
    plaetze = [(w, scan.ordner_scannen(p, wurzel=w.kennung, nur_git=w.nur_git,
                                      ohne=w.ohne, dateien=w.dateien))
               for w, p in quellen.alle(WURZEL)]
    return manifest.zeilen_bauen(plaetze, manifest.manifest_laden(MANIFEST), PROFILE)


class Pfadbau(unittest.TestCase):
    """Manifest-Pfad und Fremd-Pfad muessen denselben Baum meinen."""

    def test_handel_werkstatt_projekte(self):
        self.assertEqual(quellen.pfad_in_wurzel("handel", "OpenAlice"),
                         "Agenten/Handel/OpenAlice")
        self.assertEqual(quellen.pfad_in_wurzel("handel", "kraken/abgleich.py"),
                         "Agenten/Handel/kraken/abgleich.py")
        self.assertEqual(quellen.pfad_in_wurzel("werkstatt", "handel-stack"),
                         "Werkstatt/handel-stack")
        self.assertEqual(quellen.pfad_in_wurzel("projekte", "Checkpoints"),
                         "Werkstatt/Projekte/Checkpoints")
        self.assertEqual(quellen.pfad_in_wurzel("repos", "Kronos"),
                         "Werkstatt/Kronos")

    def test_unbekannte_kennung_faellt_auf_projekte_zurueck(self):
        self.assertEqual(quellen.pfad_in_wurzel("gibtsnicht", "x"),
                         "Werkstatt/Projekte/x")


class FremdModul(unittest.TestCase):
    """Das Modul wird ueber den Pfad geladen - und fehlt nie still."""

    def test_modul_wird_gefunden(self):
        modul = quellen.fremd_modul()
        self.assertIsNotNone(modul, "Agenten/Werkzeuge/fremd.py nicht gefunden")
        self.assertEqual(modul.wurzel(), WURZEL)

    def test_fremde_gibt_die_eintraege(self):
        self.assertGreaterEqual(len(quellen.fremde()), 5)


class ZeilenSindBenannt(unittest.TestCase):
    """Jede Zeile in fremdem Material traegt Rolle und Hinweis."""

    @classmethod
    def setUpClass(cls):
        cls.zeilen = alle_zeilen()

    def test_openalice_ist_benannt(self):
        treffer = [z for z in self.zeilen if z.ordner == "OpenAlice"]
        self.assertEqual(len(treffer), 1, "OpenAlice fehlt im Baum")
        z = treffer[0]
        self.assertEqual(z.rolle, "Fremdprojekt")
        self.assertTrue(any(g.startswith("fremd:") for g in z.gruende))
        self.assertTrue(any("nur lesen" in g for g in z.gruende))

    def test_jede_fremde_zeile_hat_rolle_und_hinweis(self):
        fremde = fenster.fremde_zeilen(self.zeilen)
        self.assertGreater(len(fremde), 0, "keine fremde Zeile erkannt")
        for z in fremde:
            with self.subTest(zeile=z.ordner):
                self.assertTrue(z.rolle, "fremde Zeile ohne Rolle")
                self.assertTrue(any(g.startswith("fremd:") for g in z.gruende))

    def test_unsere_spuren_sind_nicht_fremd(self):
        fremde = {z.ordner for z in fenster.fremde_zeilen(self.zeilen)}
        for name in ("klassik_ema", "klassik_sma", "klassik_rsi2", "scanner",
                     "handelszentrale.py", "spuren_stand.py"):
            with self.subTest(zeile=name):
                self.assertNotIn(name, fremde)

    def test_alle_repos_klone_sind_fremd(self):
        """Die Klonsammlung ist der zweite grosse Block - Werkstatt.
        Ausgemusterte (gruppe=ausgemustert) liegen in Werkstatt/Ausgemustert.
        Eigene Werks-Repos (Rolle Projekt/Spur/Spiegel/Werkzeug oder ohne
        Manifest-Eintrag = eigene Ordner) sind keine fremden Klone - alle
        anderen REPOS schon."""
        ausgemustert = {e.ordner for e in manifest.manifest_laden(MANIFEST)
                        if e.gruppe == "ausgemustert"}
        eigene = {e.ordner for e in manifest.manifest_laden(MANIFEST)
                  if e.rolle in ("Projekt", "Spur", "Spiegel (18.09.)", "Werkzeug")}
        repos = [z for z in self.zeilen if z.bereich == "REPOS"
                 and z.ordner not in ausgemustert and z.ordner not in eigene
                 and z.gruppe != "neu"]
        self.assertGreater(len(repos), 20)
        self.assertEqual(len(fenster.fremde_zeilen(repos)), len(repos))
    def test_die_liste_kennt_nur_vorhandene_pfade(self):
        """Ein Eintrag ohne Ordner waere toter Text - hier gegen die Platte."""
        modul = quellen.fremd_modul()
        for e in modul.laden():
            with self.subTest(pfad=e.pfad):
                self.assertTrue((WURZEL / e.pfad).exists(), f"{e.pfad} fehlt")


class Zaehlung(unittest.TestCase):
    """Die Kopfzeile nennt die Fremden - sonst sieht die Zahl groesser aus."""

    @classmethod
    def setUpClass(cls):
        cls.zeilen = alle_zeilen()

    def test_summenzeile_nennt_fremde(self):
        text = fenster.zusammenfassung(self.zeilen)
        fremde = len(fenster.fremde_zeilen(self.zeilen))
        self.assertIn(f"{len(self.zeilen)} Zeilen", text)
        self.assertIn(f"{fremde} fremd", text)

    def test_ohne_fremde_keine_zahl(self):
        ohne = [z for z in self.zeilen if z.ordner not in
                {f.ordner for f in fenster.fremde_zeilen(self.zeilen)}]
        self.assertNotIn("fremd", fenster.zusammenfassung(ohne))


if __name__ == "__main__":
    unittest.main(verbosity=2)
