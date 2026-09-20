"""Tests fuer den Wochenbericht."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import wochenbericht                                     # noqa: E402


class FensterTageTest(unittest.TestCase):
    def test_fenster_tage_kommt_aus_lage_keine_zweitdefinition(self):
        """Befund 2 der Schlusspruefung: eine Quelle fuer die Fensterbreite,
        damit eine kuenftige Aenderung nicht an einer Stelle stehen bleibt."""
        self.assertIs(wochenbericht.FENSTER_TAGE, wochenbericht.lage.FENSTER_TAGE)


class VerlaufTest(unittest.TestCase):
    def test_vier_fenster_vier_eintraege(self):
        gerufen = []

        def fake(spur, von=None, bis=None):
            gerufen.append((von, bis))
            return {"n": 10, "ergebnis": 1.0, "treffer": 6}

        v = wochenbericht.verlauf("scanner", kennzahlen_fn=fake)
        self.assertEqual(len(v), 4)
        self.assertEqual(len(gerufen), 4)

    def test_fenster_liegen_hintereinander_und_ueberlappen_nicht(self):
        gerufen = []

        def fake(spur, von=None, bis=None):
            gerufen.append((von, bis))
            return None

        wochenbericht.verlauf("scanner", kennzahlen_fn=fake)
        for juenger, aelter in zip(gerufen, gerufen[1:]):
            self.assertLessEqual(aelter[1], juenger[0])


class VerlaufszeileTest(unittest.TestCase):
    def test_belastbares_fenster_zeigt_das_ergebnis(self):
        werte = [{"n": 20, "ergebnis": 12.5, "treffer": 11}]
        zeile = wochenbericht.verlaufszeile("scanner", werte)
        self.assertIn("scanner", zeile)
        self.assertIn("+12.50", zeile)

    def test_zu_wenige_runden_zeigt_n_statt_ergebnis(self):
        # auswertung_alle.MIN_RUNDEN = 8 - drei Runden sind zu wenige fuer
        # eine Aussage, die Zeile darf trotzdem nicht die Ergebniszahl zeigen.
        werte = [{"n": 3, "ergebnis": 99.0, "treffer": 1}]
        zeile = wochenbericht.verlaufszeile("kraken", werte)
        self.assertIn("n=3", zeile)
        self.assertNotIn("99.00", zeile)

    def test_leeres_fenster_zeigt_einen_strich(self):
        zeile = wochenbericht.verlaufszeile("swap", [None])
        self.assertIn("-", zeile)


class BaueTest(unittest.TestCase):
    """Belegt den Mantel: baue() bindet lage.HIER an sein eigenes HIER waehrend
    des Aufrufs und stellt es danach zurueck - dasselbe Muster wie
    tagesbericht.baue()/tagesbericht._baue()."""

    def test_baue_erhebt_aus_dem_eigenen_hier_ordner(self):
        """Ein Fake-Holer liest eine Datei, die nur im Temp-Ordner liegt.
        Taucht der daraus gelesene Spurname im Volltext auf, kam die
        Erhebung aus DIESEM Ordner - nicht aus dem echten Handel-Baum, wo
        diese Datei nicht existiert und der Holer scheitern wuerde."""
        tmp = tempfile.mkdtemp(prefix="wochenbericht-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        with io.open(os.path.join(tmp, "merkmal.json"), "w",
                    encoding="utf-8") as f:
            json.dump({"spur": "kraken"}, f)

        def fake_holer():
            pfad = os.path.join(wochenbericht.lage.HIER, "merkmal.json")
            with io.open(pfad, encoding="utf-8") as f:
                spur = json.load(f)["spur"]
            return {"name": spur, "waehrung": "USD", "positionen": [],
                    "w": {}, "ordner": os.path.join(wochenbericht.lage.HIER,
                                                    spur)}

        vorher = wochenbericht.lage.HIER
        with patch.object(wochenbericht, "HIER", tmp), \
                patch.object(wochenbericht.lage, "HOLER", (fake_holer,)):
            text = wochenbericht.baue()
        self.assertIn("kraken", text)
        # Der Mantel stellt lage.HIER zurueck - kein Zustand bleibt haengen.
        self.assertEqual(wochenbericht.lage.HIER, vorher)

    def test_eine_kaputte_spur_reisst_den_bericht_nicht_mit(self):
        """Befund 1 der Schlusspruefung: verlauf() darf fuer eine Spur werfen,
        ohne _baue() mitzureissen - dieselbe Kapselung wie lage.erhebe() je
        Holer. Die kaputte Spur bekommt eine erkennbare Fehlzeile, die
        gesunde Spur bleibt normal im Bericht."""
        def fake_holer_gesund():
            return {"name": "kraken", "waehrung": "USD", "positionen": [],
                    "w": {}, "ordner": os.path.join(wochenbericht.lage.HIER,
                                                    "kraken")}

        def fake_holer_kaputt():
            return {"name": "swap", "waehrung": "USD", "positionen": [],
                    "w": {}, "ordner": os.path.join(wochenbericht.lage.HIER,
                                                    "swap")}

        echter_verlauf = wochenbericht.verlauf

        def verlauf_mit_ausfall(spur, *a, **kw):
            if spur == "swap":
                raise OSError("Journal kaputt")
            return echter_verlauf(
                spur, kennzahlen_fn=lambda *a2, **k2:
                    {"n": 10, "ergebnis": 1.0, "treffer": 6})

        with patch.object(wochenbericht.lage, "HOLER",
                          (fake_holer_gesund, fake_holer_kaputt)), \
                patch.object(wochenbericht, "verlauf",
                             side_effect=verlauf_mit_ausfall):
            text = wochenbericht.baue()
        self.assertIn("kraken", text)
        self.assertIn("swap", text)
        self.assertIn("ausgefallen", text)
        self.assertIn("Journal kaputt", text)

    def test_ohne_guthaben_abgleich_zeigt_eine_fehlzeile(self):
        """Erzwingt den ImportError unabhaengig davon, ob guthaben_abgleich.py
        (Aufgabe 7) inzwischen existiert: None in sys.modules laesst
        `import guthaben_abgleich` immer scheitern."""
        with patch.dict(sys.modules, {"guthaben_abgleich": None}):
            text = wochenbericht.baue()
        self.assertIn("Guthabenabgleich nicht verfuegbar", text)


class SummenTest(unittest.TestCase):
    def test_waehrungen_werden_nicht_stumm_addiert(self):
        posten = [
            {"spur": "scanner", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "USD", "live": True, "belastbar": True},
            {"spur": "kraken", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "EUR", "live": False, "belastbar": True},
        ]
        text = wochenbericht.bilanzteil(posten)
        self.assertIn("USD", text)
        self.assertIn("EUR", text)
        self.assertNotIn("+10.00", text)     # keine Summe ueber beide

    def test_papier_und_live_bleiben_getrennt(self):
        posten = [
            {"spur": "scanner", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "USD", "live": True, "belastbar": True},
            {"spur": "swap", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "USD", "live": False, "belastbar": True},
        ]
        text = wochenbericht.bilanzteil(posten)
        self.assertIn("Live", text)
        self.assertIn("Papier", text)


if __name__ == "__main__":
    unittest.main()
