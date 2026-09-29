"""Bausteine des Leitstands: Sortieren, Filtern, Kopieren, Zustandsdatei,
Fensterlage, Zeit-Dialog, Tabelle.

Gearbeitet wird in einem Temp-Ordner. Die Tk-Teile werden ohne Bildschirm
uebersprungen. Die Uhr ist eine Liste, die der Test weiterstellt.

Direkt ausfuehrbar:  python tests/test_leitstand_bedienung.py
"""

import csv
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitstand_bedienung as lb                               # noqa: E402


class Uhr:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class Sortieren(unittest.TestCase):
    def test_zahlen_numerisch_nicht_als_text(self):
        zeilen = [("a", "10"), ("b", "9"), ("c", "-2,5 %"), ("d", "100 USD")]
        self.assertEqual([z[0] for z in lb.sortiere(zeilen, 1, False)],
                         ["c", "b", "a", "d"])

    def test_umgekehrt(self):
        zeilen = [("a", 1), ("b", 3), ("c", 2)]
        self.assertEqual([z[0] for z in lb.sortiere(zeilen, 1, True)],
                         ["b", "c", "a"])

    def test_datum_und_dauer_sind_text(self):
        self.assertEqual(lb.sortier_schluessel("2026-09-29")[0], 1)
        self.assertEqual(lb.sortier_schluessel("1:30 h")[0], 1)
        self.assertEqual(lb.sortier_schluessel(True)[0], 1)
        self.assertEqual(lb.sortier_schluessel(None), (1, 0.0, ""))

    def test_zahlen_vor_text(self):
        zeilen = [("a", "Papier"), ("b", "3")]
        self.assertEqual([z[0] for z in lb.sortiere(zeilen, 1, False)], ["b", "a"])


class Filtern(unittest.TestCase):
    def test_alle_woerter_muessen_vorkommen(self):
        z = ("xperp", "scharf, noch 1:00 h", "leitstand")
        self.assertTrue(lb.passt(z, ""))
        self.assertTrue(lb.passt(z, "XPERP scharf"))
        self.assertFalse(lb.passt(z, "xperp papier"))


class Kopieren(unittest.TestCase):
    def test_tsv_ohne_tab_und_umbruch_in_zellen(self):
        t = lb.als_tsv(("A", "B"), [("x\ty", "z\nw"), (1, 2.5)])
        self.assertEqual(t, "A\tB\nx y\tz w\n1\t2.5")

    def test_csv_rundreise(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.csv")
            lb.csv_schreiben(p, ("Spur", "Wert"), [("xperp", "1,5"), ("orb", 3)])
            with open(p, encoding="utf-8-sig", newline="") as f:
                self.assertEqual(list(csv.reader(f, delimiter=";")),
                                 [["Spur", "Wert"], ["xperp", "1,5"], ["orb", "3"]])


class Fensterlage(unittest.TestCase):
    SCHIRM = (0, 0, 1920, 1080)

    def test_sichtbar(self):
        self.assertTrue(lb.lage_gueltig("1280x860+80+60", self.SCHIRM))

    def test_rechts_ausserhalb(self):
        self.assertFalse(lb.lage_gueltig("1280x860+1900+60", self.SCHIRM))

    def test_titelleiste_unter_dem_schirm(self):
        self.assertFalse(lb.lage_gueltig("1280x860+80+1070", self.SCHIRM))

    def test_linker_zweitmonitor(self):
        self.assertTrue(lb.lage_gueltig("1280x860+-1800+40", (-1920, 0, 3840, 1080)))

    def test_unsinn(self):
        self.assertFalse(lb.lage_gueltig("", self.SCHIRM))
        self.assertFalse(lb.lage_gueltig("gross", self.SCHIRM))


class ZustandDatei(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pfad = Path(self.tmp.name) / "leitstand_zustand.json"

    def test_rundreise(self):
        z = lb.Zustand(self.pfad, Uhr())
        z.merke("reiter", 2)
        z.merke_in("sortierung", "freigaben", ["Spur", True])
        self.assertTrue(z.speichern(sofort=True))
        neu = lb.Zustand(self.pfad, Uhr())
        self.assertEqual(neu.get("reiter"), 2)
        self.assertEqual(neu.get("sortierung"), {"freigaben": ["Spur", True]})

    def test_fehlend_gibt_vorgaben(self):
        self.assertEqual(lb.Zustand(self.pfad, Uhr()).daten, lb.Zustand.VORGABEN)

    def test_unlesbar_gibt_vorgaben(self):
        self.pfad.write_text("{kaputt", encoding="utf-8")
        self.assertEqual(lb.Zustand(self.pfad, Uhr()).daten, lb.Zustand.VORGABEN)

    def test_falscher_typ_wird_verworfen(self):
        self.pfad.write_text(json.dumps({"reiter": "zwei", "werte": [],
                                         "geometrie": "800x600+0+0"}),
                             encoding="utf-8")
        z = lb.Zustand(self.pfad, Uhr())
        self.assertEqual(z.get("reiter"), 0)
        self.assertEqual(z.get("werte"), {})
        self.assertEqual(z.get("geometrie"), "800x600+0+0")

    def test_liste_statt_objekt(self):
        self.pfad.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(lb.Zustand(self.pfad, Uhr()).daten, lb.Zustand.VORGABEN)

    def test_vorgaben_werden_nicht_geteilt(self):
        a = lb.Zustand(self.pfad, Uhr())
        a.daten["werte"]["x"] = 1
        self.assertEqual(lb.Zustand.VORGABEN["werte"], {})

    def test_hoechstens_alle_5_s(self):
        uhr = Uhr()
        z = lb.Zustand(self.pfad, uhr)
        z.merke("reiter", 1)                        # erster Wunsch: sofort
        self.assertEqual(json.loads(self.pfad.read_text("utf-8"))["reiter"], 1)
        uhr.t += 1
        z.merke("reiter", 2)                        # gebuendelt
        self.assertEqual(json.loads(self.pfad.read_text("utf-8"))["reiter"], 1)
        uhr.t += 2
        self.assertFalse(z.nachholen())
        uhr.t += 3
        self.assertTrue(z.nachholen())
        self.assertEqual(json.loads(self.pfad.read_text("utf-8"))["reiter"], 2)
        self.assertFalse(z.nachholen())             # nichts mehr offen

    def test_keine_tmp_bleibt_liegen(self):
        z = lb.Zustand(self.pfad, Uhr())
        z.merke("reiter", 3)
        self.assertEqual(os.listdir(self.tmp.name), ["leitstand_zustand.json"])


class MitTk(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.zustand = lb.Zustand(Path(self.tmp.name) / "z.json", Uhr())


class ZeitDialogTest(MitTk):
    def test_zeitablauf(self):
        uhr = Uhr()
        d = lb.ZeitDialog(self.root, "Test", 120, uhr=uhr)
        uhr.t += 121
        d._takt()
        self.assertEqual(d.ergebnis, "zeitablauf")

    def test_bedienung_setzt_die_uhr_zurueck(self):
        uhr = Uhr()
        d = lb.ZeitDialog(self.root, "Test", 120, uhr=uhr)
        uhr.t += 100
        d._bedient()
        uhr.t += 50
        d._takt()
        self.assertIsNone(d.ergebnis)
        self.assertAlmostEqual(d.rest_s(), 70)
        d.fertig("abgebrochen")

    def test_escape_und_schliessen_brechen_ab(self):
        d = lb.ZeitDialog(self.root, "Test", 120, uhr=Uhr())
        self.assertTrue(d.bind("<Escape>"))
        d.fertig("abgebrochen")
        d.fertig("ja")                              # zweiter Aufruf wirkungslos
        self.assertEqual(d.ergebnis, "abgebrochen")


class TabelleTest(MitTk):
    def _tabelle(self):
        t = lb.Tabelle(self.root, ("Spur", "Wert"), self.zustand, "probe")
        t.setze([("xperp", "10"), ("orb", "9"), ("gitter", "100")])
        return t

    def test_filter(self):
        t = self._tabelle()
        t.w_filter.set("or")
        self.assertEqual(t.sichtbare(), [("orb", "9")])

    def test_sortieren_und_umkehren(self):
        t = self._tabelle()
        t.sortiere_nach("Wert")
        self.assertEqual([z[0] for z in t.sichtbare()], ["orb", "xperp", "gitter"])
        t.sortiere_nach("Wert")
        self.assertEqual([z[0] for z in t.sichtbare()], ["gitter", "xperp", "orb"])
        self.assertEqual(self.zustand.get("sortierung")["probe"], ["Wert", True])
        self.assertTrue(t.baum.heading("Wert", "text").endswith("▼"))

    def test_sortierung_kommt_aus_dem_zustand(self):
        self.zustand.merke_in("sortierung", "probe", ["Spur", False])
        t = self._tabelle()
        self.assertEqual([z[0] for z in t.sichtbare()], ["gitter", "orb", "xperp"])

    def test_auswahl_bleibt_nach_neuem_setzen(self):
        t = self._tabelle()
        t.baum.selection_set(t.baum.get_children()[1])
        t.setze([("xperp", "11"), ("orb", "8"), ("gitter", "100")])
        self.assertEqual(t.auswahl(), [("orb", "8")])

    def test_kopieren_legt_sichtbares_ab(self):
        t = self._tabelle()
        t.w_filter.set("gitter")
        self.assertEqual(t.kopieren(), "Spur\tWert\ngitter\t100")
        self.assertEqual(self.root.clipboard_get(), "Spur\tWert\ngitter\t100")


if __name__ == "__main__":
    unittest.main()
