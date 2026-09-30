"""Tests fuer die runden Ecken: Geometrie, Knopfzustaende, Karten, Fensterrand.

Der Geometrieteil laeuft ohne Fenster; die Widget-Teile brauchen Tk und werden
sonst uebersprungen. Geprueft werden REGELN (Radius begrenzt, Punkte im Rahmen,
Zustand lesbar) - keine Pixelwerte eines bestimmten Monitors.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rund  # noqa: E402

try:
    import tkinter as tk

    _r = tk.Tk()
    _r.destroy()
    TK_DA = True
except Exception:  # pragma: no cover
    TK_DA = False


class EckenTest(unittest.TestCase):
    def test_punkte_liegen_im_rahmen(self):
        punkte = rund.ecken_punkte(0, 0, 100, 40, 8)
        self.assertTrue(punkte)
        for x, y in punkte:
            self.assertGreaterEqual(round(x, 6), 0)
            self.assertLessEqual(round(x, 6), 100)
            self.assertGreaterEqual(round(y, 6), 0)
            self.assertLessEqual(round(y, 6), 40)

    def test_radius_wird_auf_die_halbe_seite_begrenzt(self):
        """Ein Radius groesser als die Flaeche ergaebe eine Raute - das darf nicht."""
        punkte = rund.ecken_punkte(0, 0, 10, 10, 999)
        for x, y in punkte:
            self.assertLessEqual(round(x, 6), 10)
            self.assertLessEqual(round(y, 6), 10)
        # Bei r = halbe Seite liegt der erste Punkt genau in der Mitte der Kante.
        self.assertAlmostEqual(punkte[0][0], 5.0, places=6)

    def test_radius_null_gibt_ein_rechteck(self):
        self.assertEqual(
            rund.ecken_punkte(0, 0, 10, 20, 0), [(0, 0), (10, 0), (10, 20), (0, 20)]
        )

    def test_keine_doppelten_punkte(self):
        punkte = rund.ecken_punkte(0, 0, 100, 40, 8)
        for a, b in zip(punkte, punkte[1:]):
            self.assertGreater(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1e-9)

    def test_umriss_ist_eine_flache_liste(self):
        flach = rund.umriss(50, 20, 6)
        self.assertEqual(len(flach) % 2, 0)
        self.assertEqual(flach[0], 6.0)          # erster Punkt: x0 + r

    def test_viertelkreis_wird_gezeichnet(self):
        """Die Ecke oben rechts muss einen Bogen enthalten, keine Gerade."""
        punkte = rund.ecken_punkte(0, 0, 100, 40, 10)
        ecke = [(x, y) for x, y in punkte if x > 85 and y < 15]
        self.assertGreaterEqual(len(ecke), 4)
        for x, y in ecke:
            # Jeder Punkt der Ecke liegt auf dem Kreis um (90, 10)
            self.assertAlmostEqual(math.hypot(x - 90, y - 10), 10, places=6)


class VariantenTest(unittest.TestCase):
    def test_jede_variante_hat_alle_farbrollen(self):
        for name, v in rund.VARIANTEN.items():
            for rolle in ("flaeche", "schrift", "rand", "hover"):
                self.assertIn(rolle, v, f"{name} fehlt {rolle}")

    def test_radius_ist_gesetzt(self):
        self.assertGreater(rund.RADIUS, 0)
        self.assertLess(rund.RADIUS_KLEIN, rund.RADIUS)


@unittest.skipUnless(TK_DA, "kein Fenstersystem verfuegbar")
class KnopfTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.farben = {"bg": "#1e1e2e", "blatt": "#181825", "gitter": "#313244",
                       "auswahl": "#45475a", "text": "#cdd6f4", "matt": "#a6adc8",
                       "akzent": "#89b4fa", "gruen": "#a6e3a1", "rot": "#f38ba8",
                       "gelb": "#f9e2af", "zellgruen": "#1b4d3e", "zellrot": "#5c1f2b",
                       "blau": "#89b4fa"}

    def tearDown(self):
        self.root.destroy()

    def _knopf(self, **kwargs):
        geklickt = []
        k = rund.RunderKnopf(self.root, "Test", lambda: geklickt.append(1),
                             farben=self.farben, schrift_tupel=("Consolas", 11), **kwargs)
        k.pack()
        self.root.update()
        return k, geklickt

    def test_state_wird_wie_bei_ttk_gelesen_und_gesetzt(self):
        k, _ = self._knopf()
        self.assertEqual(str(k["state"]), "normal")
        k.configure(state="disabled")
        self.assertEqual(str(k["state"]), "disabled")
        k.configure(state="normal")
        self.assertEqual(str(k["state"]), "normal")

    def test_ein_ausgeschalteter_knopf_klickt_nicht(self):
        k, geklickt = self._knopf()
        k.setze_aktiv(False)
        k._loslassen()
        self.assertEqual(geklickt, [])
        k.setze_aktiv(True)
        k._druck()
        k._loslassen()
        self.assertEqual(geklickt, [1])

    def test_text_laesst_sich_aendern(self):
        k, _ = self._knopf()
        k.setze_text("Anders")
        self.assertEqual(k["text"], "Anders")

    def test_knopf_zeichnet_eine_flaeche_und_einen_text(self):
        k, _ = self._knopf()
        k.zeichnen()
        self.assertGreaterEqual(len(k.find_all()), 2)

    def test_variante_bestimmt_die_farbe(self):
        k, _ = self._knopf(variante="haupt")
        self.assertEqual(k._plan()["flaeche"], self.farben["akzent"])
        k.setze_variante("gefahr")
        self.assertEqual(k._plan()["flaeche"], self.farben["zellrot"])

    def test_hinweis_wird_beim_zeigen_gemeldet(self):
        gesehen = []
        k, _ = self._knopf(hinweis="Etwas erklaeren")
        k.bei_hinweis = gesehen.append
        k._hinein()
        self.assertEqual(gesehen, ["Etwas erklaeren"])

    def test_breite_folgt_dem_text(self):
        schmal, _ = self._knopf()
        breit, _ = self._knopf()
        breit.setze_text("Ein sehr langer Knopftext")
        self.assertGreater(
            rund.text_breite(self.root, ("Consolas", 11), "Ein sehr langer Knopftext"),
            rund.text_breite(self.root, ("Consolas", 11), "Test"),
        )
        self.assertTrue(schmal.winfo_reqwidth() > 0)


@unittest.skipUnless(TK_DA, "kein Fenstersystem verfuegbar")
class KarteTest(unittest.TestCase):
    def test_karte_hat_inhalt_und_zeichnet_den_rahmen(self):
        root = tk.Tk()
        root.withdraw()
        try:
            farben = {"bg": "#1e1e2e", "blatt": "#181825", "gitter": "#313244",
                      "akzent": "#89b4fa", "text": "#cdd6f4"}
            karte = rund.Karte(root, titel="Ueberschrift", farben=farben,
                               schrift_tupel=("Consolas", 11), hoehe=100)
            karte.pack(fill="both", expand=True)
            root.update()
            karte.zeichnen()
            self.assertTrue(karte.inhalt.winfo_exists())
            self.assertGreaterEqual(len(karte.find_all()), 2)   # Flaeche + Titel
            # Der Inhalt liegt IM Rahmen, nicht darueber hinaus.
            self.assertGreaterEqual(karte.coords(karte._id)[1], 0)
        finally:
            root.destroy()


@unittest.skipUnless(TK_DA, "kein Fenstersystem verfuegbar")
class FensterrandTest(unittest.TestCase):
    def test_fenster_ecken_meldet_erfolg_oder_scheitert_leise(self):
        """Auf Windows 11 muss der DWM-Aufruf gelingen; sonst bleibt es eckig."""
        root = tk.Tk()
        root.withdraw()
        try:
            ergebnis = rund.fenster_ecken(root)
            self.assertIsInstance(ergebnis, bool)
            if sys.platform == "win32":
                self.assertTrue(ergebnis, "DwmSetWindowAttribute hat abgelehnt")
        finally:
            root.destroy()

    def test_fenster_ecken_stuerzt_ohne_fenster_nicht_ab(self):
        class Ohne:
            def update_idletasks(self):
                raise RuntimeError("kein Fenster")

        self.assertFalse(rund.fenster_ecken(Ohne()))


if __name__ == "__main__":
    unittest.main()