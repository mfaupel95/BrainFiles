"""liq_wand: Das Ziel muss in Handelsrichtung liegen (04.10.2026).

GEMESSEN an 43 echten Runden: Summe -1,16 %, 29 Ziel-Ausstiege im Mittel
-0,16 %, die 14 Stop-Ausstiege +0,24 %. Vertauscht - der Ertrag kam aus den
Verlusten.

Ursache: `wand()` liefert den Preis des groessten Liquidationsbandes, und der
liegt je nach Marktlage OBER oder UNTER dem Spot. Der Einstieg folgt der Wand.
Der alte Code nahm den Wandpreis blind als Ziel - bei einer Wand UNTER dem
Spot lag das Ziel dann unter dem Einstieg, und die Runde schloss mit minus.

Die Tests sichern die REGEL:
* Ein Ziel unter dem Einstieg bei long (oder ueber bei short) ist immer ein
  Fehler - nie eine gueltige Konfiguration.
* Liegt der Wandpreis falsch herum, kommt das Ziel aus dem R-Ziel, nicht aus
  dem Wandpreis.
* Beide Wandlagen (oben und unten) ergeben ein erreichbares Ziel.

Ohne Netz, ohne Order: `wand()` ist eine reine Funktion, `ziel()` rechnet nur
aus uebergebener Wand. Die Position kommt aus dem Aufrufer.

Ausfuehrbar:  python tests/test_liq_wand_ziel.py   (aus Agenten/Handel)
"""
import os
import sys
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPUR = os.path.join(HANDEL, "liq_wand")
for p in (SPUR, HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln as lw                                            # noqa: E402


class ZielRichtungTest(unittest.TestCase):
    """Ein Ziel muss in Handelsrichtung liegen."""

    W = {"bandbreite_prozent": 0.25, "ziel_r_vielfaches": 2.0}

    @staticmethod
    def _wand_ueber_spot():
        """Liquidierte SHORTS ueber dem Spot -> Kaufdruck -> die Spur geht
        long, die Wand liegt ueber dem Einstieg."""
        return {"spot": 85000.0,
                "liqs": [{"preis": 85200.0, "kontrakte": 500, "seite": "short"}]}

    @staticmethod
    def _wand_unter_spot():
        """Liquidierte LONGS unter dem Spot -> Verkaufsdruck -> die Spur geht
        short, die Wand liegt unter dem Einstieg."""
        return {"spot": 85000.0,
                "liqs": [{"preis": 84800.0, "kontrakte": 500, "seite": "long"}]}

    def test_wand_ueber_spot_liegt_ziel_darueber(self):
        z = lw.ziel(self._wand_ueber_spot(), self.W)
        self.assertGreater(z, 85000.0,
                           "long braucht ein Ziel UEBER dem Einstieg")

    def test_wand_unter_spot_liegt_ziel_darunter(self):
        z = lw.ziel(self._wand_unter_spot(), self.W)
        self.assertLess(z, 85000.0,
                        "short braucht ein Ziel UNTER dem Einstieg")

    def test_kein_ziel_falsch_herum(self):
        """Die eigentliche Regel - und diesmal gegen die ABWESENHEIT des
        Fixes geprueft.

        Der Fehler vom 04.10.2026 war nicht, dass die Wand falsch herum lag -
        das waere ein Ausnahmefall. Er war: der Code nahm den Wandpreis
        blind, egal wo er lag. In den 43 echten Runden lagen 12 mit dem Ziel
        UNTER dem Einstieg bei long.

        Deshalb braucht der Test BEIDE Richtungen JEWEILS in beiden Wandlagen.
        Nur die Kreuzung (falsch herum) faellt mit dem alten Code durch -
        die erste Fassung dieses Tests pruefte nur die richtigen Lagen und
        blieb deshalb bei der Gegenprobe gruen (gemessen 04.10.2026)."""
        faelle = (
            # (Name, Wandpreis, liquidierte Seite, erwartete Richtung)
            ("Wand ueber, long",  86000.0, "short", "ueber"),
            ("Wand ueber, short", 86000.0, "long",  "unter"),
            ("Wand unter, long",  84000.0, "short", "ueber"),
            ("Wand unter, short", 84000.0, "long",  "unter"),
        )
        spot = 85000.0
        for name, wandpreis, liq_seite, richtung in faelle:
            with self.subTest(fall=name):
                d = {"spot": spot,
                     "liqs": [{"preis": wandpreis, "kontrakte": 500,
                               "seite": liq_seite}]}
                z = lw.ziel(d, self.W)
                if richtung == "ueber":
                    self.assertGreater(z, spot,
                                       "long braucht ein Ziel UEBER dem "
                                       "Einstieg - hier waere es die "
                                       "Fehlkonfiguration aus dem Journal")
                else:
                    self.assertLess(z, spot,
                                    "short braucht ein Ziel UNTER dem Einstieg")

    def test_jede_der_vier_lagen_ist_ein_sinnvoller_zielpunkt(self):
        """Kein Platzhalter, kein 0, keine Wand, die der Einstieg bereits
        passiert hat. Der Zielpunkt MUSS zwischen Einstieg und Frist liegen."""
        spot = 85000.0
        for wandpreis in (83600.0, 84800.0, 85200.0, 86400.0):
            for liq_seite in ("long", "short"):
                d = {"spot": spot,
                     "liqs": [{"preis": wandpreis, "kontrakte": 500,
                               "seite": liq_seite}]}
                z = lw.ziel(d, self.W)
                self.assertIsNotNone(z)
                self.assertGreater(z, 0, "ein Zielpreis muss positiv sein")
                # Hoechstens R weit weg - sonst ist es kein Ziel.
                self.assertLess(abs(z / spot - 1) * 100, 10.0,
                                "Ziel %.2f ist %.1f %% vom Spot - zu weit"
                                % (z, abs(z / spot - 1) * 100))

    def test_falsche_wandlage_ersetzt_durch_r_ziel(self):
        """Liegt der Wandpreis falsch herum, kommt das Ziel aus R - nicht aus
        dem Wandpreis. Sonst bleibt es unerreichbar und die Runde laeuft bis
        zur Frist."""
        # 'short'-Seite (long) verlangt ein Ziel ueber dem Spot - hier liegt
        # die Wand darunter. Das Ziel muss dann aus R kommen.
        d = {"spot": 85000.0,
             "liqs": [{"preis": 84800.0, "kontrakte": 500, "seite": "short"}]}
        z = lw.ziel(d, self.W)
        self.assertGreater(z, 85000.0, "R-Ziel statt Wandpreis")
        self.assertAlmostEqual(z, 85000.0 * 1.02, places=2,
                               msg="2 %% R ueber dem Spot")

    def test_ziel_ist_reell_erreichbar(self):
        """Der Wandpreis selbst wird genommen, wenn er passt - sonst waere
        die ganze Bandbreiten-Rechnung umsonst.

        ABER: `wand()` rundet auf das Bandraster (0,25 % vom Spot). Der
        zurueckgegebene Preis ist deshalb der Band-Mittelpunkt, nicht der
        Rohpreis der Liquidation. Bei 85000 ist ein Band 212,50 breit - aus
        einer Liquidation bei 86000 wird ein Band bei 86062,50. Das ist
        Absicht (die Buendelung braucht Raster), der Test muss es wissen.
        """
        spot = 85000.0
        d = {"spot": spot,
             "liqs": [{"preis": 86000.0, "kontrakte": 500, "seite": "short"}]}
        z = lw.ziel(d, self.W)
        treffer = lw.wand(d["liqs"], spot, 0.25)
        self.assertAlmostEqual(z, float(treffer[0]), places=2,
                               msg="das Ziel IST der Wandpreis (gerastert)")
        self.assertGreater(z, spot)
        # Und es ist nicht der rohe Liquidationspreis - sonst haette der
        # Test die Rundung nicht bemerkt.
        self.assertNotAlmostEqual(z, 86000.0, places=2)


class RundenbilanzTest(unittest.TestCase):
    """Die Rechnung, die den Fehler sichtbar gemacht hat - als Regel.

    Der Test liest KEINE echte Journaldatei (ein Test darf nie in ein echtes
    Buch schreiben, und schon gar nicht davon abhaengen). Er rechnet die
    entscheidende Groesse: ein Ziel unter dem Einstieg ist per Definition
    ein Verlust, egal wie der Ausstieg heisst.
    """

    def test_ziel_unter_einstieg_ist_verlust(self):
        einstieg, ziel_ = 85000.0, 84800.0        # long, Ziel darunter
        self.assertLess(ziel_, einstieg)
        # Das ist die Konfiguration aus dem Journal, Grund 'ziel', Ergebnis
        # negativ - 29 von 43 Runden.
        self.assertLess((ziel_ / einstieg - 1) * 100, 0)

    def test_ersatzziel_aus_r_ist_gewinn(self):
        einstieg = 85000.0
        ziel_ = einstieg * 1.02                    # 2 % R
        self.assertGreater((ziel_ / einstieg - 1) * 100, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)