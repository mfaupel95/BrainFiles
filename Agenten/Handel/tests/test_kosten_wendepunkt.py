"""Das Urteil des Kosten-Wendepunkts - Einheiten und Grenzen, ohne Netz.

Anlass: Bis zum 30.09.2026 druckte `kosten_wendepunkt.py` den Bruch
`gebuehr_taker` unveraendert mit Prozentzeichen (0.0005 -> "0.001 %" statt
"0.050 %") und verglich ihn direkt mit `f_max`, das in Prozent JE RUNDE steht.
Damit war jede Gebuehrenaussage um Faktor 100 zu klein und der Vergleich
bedeutungslos - sichtbar wurde das erst, als fuenf Spuren ueberhaupt erst ein
Gebuehrenfeld bekamen.
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import kosten_wendepunkt                                        # noqa: E402


class EinheitenTest(unittest.TestCase):
    """Der Bruch wird in Prozent umgerechnet - je Seite UND je Runde."""

    def test_kraken_gebuehr_wird_als_prozent_gedruckt(self):
        t = kosten_wendepunkt.urteil(0.006, 0.03)
        self.assertIn("0.600 % je Seite", t)
        self.assertIn("1.200 % je Runde", t)

    def test_der_alte_fehler_kommt_nicht_zurueck(self):
        # Gegenprobe: die rohe Zahl mit Prozentzeichen war die Fehlanzeige.
        t = kosten_wendepunkt.urteil(0.0005, 0.07)
        self.assertNotIn("0.001 %", t)
        self.assertIn("0.050 % je Seite", t)
        self.assertIn("0.100 % je Runde", t)

    def test_runde_zaehlt_beide_seiten(self):
        # Eine Runde ist Kauf UND Verkauf: die Grenze muss gegen den doppelten
        # Satz geprueft werden, nicht gegen eine Seite.
        self.assertIn("liegt darueber", kosten_wendepunkt.urteil(0.0005, 0.09))
        self.assertNotIn("liegt darueber", kosten_wendepunkt.urteil(0.0005, 0.11))


class GrenzenTest(unittest.TestCase):
    """Der Hinweis haengt an f_max, nicht an der Tagesform."""

    def test_ohne_gebuehrfeld_kein_gebuehrenhinweis(self):
        for geb in (None, 0, 0.0):
            t = kosten_wendepunkt.urteil(geb, 0.03)
            self.assertIn("haengt an der Gebuehrfreiheit", t)
            self.assertNotIn("gesetzte Gebuehr", t)

    def test_tote_spur_wird_deutlicher_benannt(self):
        t = kosten_wendepunkt.urteil(0.006, -0.09)
        self.assertIn("schon bei 0 % Gebuehr nicht tragfaehig", t)

    def test_gesunde_spur_bleibt_ohne_gebuehrenhinweis(self):
        # Der Scanner liegt bei +9,81 % je Runde - 0,1 % Gebuehr kippen ihn nicht.
        t = kosten_wendepunkt.urteil(0.0005, 9.81)
        self.assertEqual("", t)

    def test_schwelle_0_4_prozent_bleibt_erhalten(self):
        self.assertIn("unter 0,4 %", kosten_wendepunkt.urteil(0.0005, 0.39))
        self.assertNotIn("Gebuehrfreiheit", kosten_wendepunkt.urteil(0.0005, 0.41))


class FelderTest(unittest.TestCase):
    """Jede Spur, die live ordern kann, muss ihr Gebuehrenfeld tragen."""

    def test_kernspuren_haben_ein_gebuehrenfeld(self):
        import json
        from pathlib import Path
        for spur, soll in (("scanner", 0.0005), ("orb", 0.0005), ("orbk", 0.006),
                           ("moondev_signalwelle", 0.0005), ("iv_wand", 0.0005),
                           ("kraken", 0.006), ("xperp", 0.0005), ("swap", 0.0005),
                           ("mosaic", 0.006), ("liq_wand", 0.0005)):
            p = Path(HANDEL) / spur / "wachen.json"
            if not p.is_file():
                self.skipTest("Spur %s fehlt" % spur)
            w = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(soll, w.get("gebuehr_taker"),
                             "%s: Gebuehrenfeld fehlt oder hat den falschen Wert" % spur)

    def test_gebuehr_ist_ein_bruch_kein_prozentwert(self):
        # Ein Wert ueber 0,05 waere ein Prozentwert (5 %) und damit ein
        # Einheitenfehler - genau die Verwechslung, die hier passiert war.
        import json
        from pathlib import Path
        for p in sorted(Path(HANDEL).glob("*/wachen.json")):
            w = json.loads(p.read_text(encoding="utf-8"))
            if "gebuehr_taker" in w:
                self.assertLessEqual(w["gebuehr_taker"], 0.05,
                                     "%s: gebuehr_taker sieht wie Prozent aus" % p.parent.name)


if __name__ == "__main__":
    unittest.main()