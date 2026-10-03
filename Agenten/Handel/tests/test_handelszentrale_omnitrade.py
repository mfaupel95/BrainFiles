"""Tests fuer den omnitrade-Reiter der Handelszentrale (30.09.2026).

Der Reiter trug bis dahin NUR den Rust-Lauf. Seit dem 30.09.2026 gibt es die
Haus-Spur `omnitrade`, die dessen Position spiegelt - und sie heisst genauso.
Diese Datei belegt, dass beide getrennt und beschriftet im selben Reiter
stehen: "Laeufe" (Rust, Statusdatei) und "Haus-Buch der Spur"
(zustand.json/handelsjournal.csv).

Geprueft wird auf den REINEN Funktionen (ohne Fenster) plus ein echter
Fensteraufbau, weil ein tk-Mock genau die zwei Startfehler verdeckt, die erst
beim Bauen auftreten (fehlendes `ttk`, ein `root` in einer Builder-Methode).
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

_spec = importlib.util.spec_from_file_location(
    "handelszentrale", os.path.join(HANDEL, "handelszentrale.py"))
gui = importlib.util.module_from_spec(_spec)
sys.modules["handelszentrale"] = gui
_spec.loader.exec_module(gui)

WACHEN = {
    "handel_erlaubt": False,
    "boerse": "kraken",
    "kraken_quote": "USDC",
    "max_offene_positionen": 3,
    "herzschlag_max_minuten": 180,
    "freigabe": {"erfuellt": False},
}

# Die Spur schreibt ihre Zeitstempel als UTC-aware ISO-Strings
# ("2026-09-30T19:56:46+00:00") - `alter_minuten()` rechnet mit aware-Werten,
# ein naives `datetime.now()` lief in einen TypeError.
JETZT = datetime(2026, 9, 30, 22, 0, 0, tzinfo=timezone.utc)


def zustand(positionen=(), alter_minuten=2, modus="papier"):
    return {
        "positionen": list(positionen),
        "modus": modus,
        "letzter_lauf": (JETZT - timedelta(minutes=alter_minuten)).isoformat(),
    }


POSITION = {
    "inst": "BTC-USDC", "seite": "long", "einstieg": 80000.0, "stop": 73600.0,
    "ziel": 144000.0, "nominal": 62.5, "modus": "papier",
}


class KopfTest(unittest.TestCase):
    def test_kopf_nennt_modus_plaetze_und_boerse(self):
        text, marke = gui.omnitrade_spur_kopf(zustand([POSITION]), WACHEN, JETZT)
        self.assertIn("Haus-Buch", text)
        self.assertIn("papier", text)
        self.assertIn("1 von 3", text)
        self.assertIn("vor 2 min", text)
        self.assertIn("kraken/USDC", text)
        self.assertEqual(marke, "matt")

    def test_leerer_stand_ist_kein_fehler(self):
        text, marke = gui.omnitrade_spur_kopf(None, None, JETZT)
        self.assertIn("Haus-Buch", text)
        self.assertIn("noch kein Zyklus", text)
        self.assertEqual(marke, "matt")

    def test_alter_herzschlag_wird_gewarnt(self):
        # 200 min > herzschlag_max_minuten 180: die Spur lief nicht.
        text, marke = gui.omnitrade_spur_kopf(zustand(alter_minuten=200), WACHEN, JETZT)
        self.assertTrue(text.startswith("⚠"), text)
        self.assertEqual(marke, "schlecht")

    def test_scharf_ist_gruen(self):
        w = dict(WACHEN, handel_erlaubt=True, freigabe={"erfuellt": True})
        text, marke = gui.omnitrade_spur_kopf(zustand([POSITION]), w, JETZT)
        self.assertIn("LIVE scharf", text)
        self.assertEqual(marke, "gut")

    def test_papier_wird_benannt_nicht_verschwiegen(self):
        # Ein Reiter, der "0 Plaetze" zeigt und den Schalter verschweigt, liest
        # sich wie ein handelnder Automat.
        text, _ = gui.omnitrade_spur_kopf(zustand(), WACHEN, JETZT)
        self.assertIn("handel_erlaubt=False", text)
        self.assertIn("freigabe=False", text)


class PositionenTest(unittest.TestCase):
    def test_position_wird_aufbereitet(self):
        zeilen = gui.omnitrade_spur_positionen("omnitrade", zustand([POSITION]), WACHEN)
        self.assertEqual(len(zeilen), 1)
        inst, seite, einstieg, stop, ziel, nominal = zeilen[0]
        # Das Instrument kommt aus dem NORMALISIERTEN Dict (`instrument`) -
        # `inst` gibt es nur im rohen, und wer das verwechselt, zeigt "?".
        self.assertEqual(inst, "BTC-USDC")
        self.assertEqual(seite, "LONG")
        self.assertTrue(einstieg)
        self.assertTrue(stop)
        self.assertTrue(ziel)
        self.assertTrue(nominal)

    def test_leerer_zustand_keine_zeilen(self):
        self.assertEqual(gui.omnitrade_spur_positionen("omnitrade", {}, WACHEN), [])


class JournalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omnitrade_gui_")
        self.pfad = os.path.join(self.tmp, "handelsjournal.csv")
        with open(self.pfad, "w", encoding="utf-8", newline="") as f:
            f.write("zeit,modus,aktion,inst,seite,preis,grund\n")
            f.write("2026-09-30T19:00:00+00:00,papier,kauf,BTC-USDC,long,80000,"
                    "omnitrade_spiegel\n")
            f.write("2026-09-30T21:00:00+00:00,papier,verkauf,BTC-USDC,long,81000,"
                    "omnitrade flat\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_neueste_zuerst_mit_modus(self):
        zeilen = gui.omnitrade_spur_journal(self.pfad)
        self.assertEqual(len(zeilen), 2)
        self.assertEqual(zeilen[0][2], "VERKAUF")
        self.assertEqual(zeilen[0][1], "papier")
        self.assertEqual(zeilen[0][5], "omnitrade flat")
        self.assertEqual(zeilen[1][2], "KAUF")

    def test_fehlende_datei_ist_leer(self):
        self.assertEqual(gui.omnitrade_spur_journal(os.path.join(self.tmp, "weg.csv")), [])


class FensterTest(unittest.TestCase):
    """Der echte Fensteraufbau - deckt fehlendes ttk und falsches root auf."""

    def test_reiter_traegt_beide_tabellen(self):
        try:
            root = gui.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        root.withdraw()
        try:
            app = gui.Handelszentrale(root)
            root.update()
            # Haus-Buch der Spur: eigene Widgets, eigener Beschriftungstext.
            self.assertIn("Haus-Buch", app.l_omni_spur.cget("text"))
            self.assertTrue(hasattr(app, "t_omni_pos"))
            self.assertTrue(hasattr(app, "t_omni_journal"))
            # Und die Rust-Seite ist unveraendert daneben.
            self.assertTrue(hasattr(app, "t_laeufe"))
            self.assertTrue(hasattr(app, "t_omni"))
            reiter = [app.reiter.tab(i, "text") for i in app.reiter.tabs()]
            self.assertIn("omnitrade", reiter)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()