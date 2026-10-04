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

import handelszentrale as hz                                 # noqa: E402
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


class Zahlen(unittest.TestCase):
    def test_ist_zahl(self):
        for w in ("3", "-1.25", "12,5 %", "+0.4", 7, 2.5):
            self.assertTrue(lb.ist_zahl(w), w)
        for w in ("orb", "1:30 h", "2026-09-29", "", None, True):
            self.assertFalse(lb.ist_zahl(w), w)

    def test_zahl_spalten_ignoriert_leere_zellen(self):
        zeilen = [("a", "1", "x"), ("b", "", "2"), ("c", "—", "3")]
        self.assertEqual(lb.zahl_spalten(zeilen, 3), {1})

    def test_feste_stellen_je_spalte(self):
        self.assertEqual(lb.feste_stellen(["25.0", "4", "0.125", "", "12,5 %"]),
                         ["25.000", "4.000", "0.125", "", "12,5 %"])
        self.assertEqual(lb.feste_stellen(["1", "10"]), ["1", "10"])
        self.assertEqual(lb.feste_stellen(["0.123456", "1"]), ["0.1235", "1.0000"])


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


class UmbrechenTest(MitTk):
    def test_wraplength_folgt_der_breite(self):
        self.root.deiconify()
        self.root.geometry("400x200")
        lbl = lb.umbrechen(tk.Label(self.root, text="lang " * 80))
        lbl.pack(fill="x")
        self.root.update()
        breite = int(str(lbl.cget("wraplength")))
        self.assertGreater(breite, 300)
        self.assertLessEqual(breite, 400)


class TabelleTest(MitTk):
    def _tabelle(self):
        t = lb.Tabelle(self.root, ("Spur", "Wert"), self.zustand, "probe")
        t.setze([("xperp", "10"), ("orb", "9"), ("gitter", "100")])
        return t

    def test_zahlen_rechtsbuendig_mit_fester_stellenzahl(self):
        t = lb.Tabelle(self.root, ("Tor", "Wert"), self.zustand, "probe")
        t.setze([("a", "25.0"), ("b", "4"), ("c", "0.5")])
        self.assertEqual(str(t.baum.column("Wert", "anchor")), "e")
        self.assertEqual(str(t.baum.column("Tor", "anchor")), "w")
        self.assertEqual([t.baum.item(i, "values")[1] for i in t.baum.get_children()],
                         ["25.0", "4.0", "0.5"])
        self.assertEqual(t.sichtbare()[1], ("b", "4"), "Kopieren/CSV bleiben roh")

    def test_breiten_nach_inhalt_und_pfadspalte_schmal(self):
        t = lb.Tabelle(self.root, ("Datei", "Nr", "Text"), self.zustand, "probe")
        t.setze([("x" * 80, "1", "y" * 80)])
        self.assertLessEqual(t.baum.column("Datei", "width"), lb.SCHMAL)
        self.assertLess(t.baum.column("Nr", "width"), t.baum.column("Text", "width"))
        t.baum.column("Text", width=50)            # vom Nutzer gezogen
        t.setze([("a", "2", "z" * 200)])
        self.assertEqual(t.baum.column("Text", "width"), 50)

    def test_nur_die_letzte_spalte_nimmt_den_restplatz(self):
        """Der Restplatz geht an die LETZTE Spalte - aber als gerechnete
        Breite, nicht ueber `stretch=True`.

        Der Test pruefte vorher `stretch == [False, False, True]`. Das ist
        seit dem 04.10.2026 die FALSCHE Erwartung: Tk verteilt bei
        `stretch=True` die Restbreite selbst und verfaelscht damit jede
        gerechnete Breite (gemessen 191 statt 125 px, Skill
        desktop-fenster). Die Regel ist jetzt zweigeteilt und wird auch so
        geprueft:

        1. keine Spalte dehnt sich (`stretch=False` ueberall), damit die
           Breiten berechenbar und fuer den Nutzer ziehbar bleiben;
        2. die letzte Spalte ist breiter als die reinen Textspalten, weil
           sie den Restplatz bekommen hat.
        """
        t = lb.Tabelle(self.root, ("Tor", "Wert", "Erklärung"), self.zustand, "probe")
        t.setze([("a", "1", "lang " * 30)])
        dehnt = [bool(int(str(t.baum.column(s, "stretch")))) for s in t.spalten]
        self.assertEqual(dehnt, [False, False, False],
                         "keine Spalte darf sich ueber stretch dehnen")
        breiten = [t.baum.column(s, "width") for s in t.spalten]
        self.assertGreater(breiten[-1], breiten[0],
                           "die letzte Spalte muss den Restplatz bekommen")
        # Die Deckelung prueft nur, wo es einen Restplatz gibt: ohne
        # Fenster (wie in diesem Test) ist der Baum 1 px breit, der
        # Restplatz also 0 und die letzte Spalte traegt nur ihren
        # Textbedarf - 1148 px fuer 150 Zeichen. Die Deckelung ist
        # eine Eigenschaft des Restplatzes, nicht der Breite.
        platz = t.baum.winfo_width() - hz.ROLLENDE
        if platz > 100:
            self.assertLessEqual(breiten[-1] - breiten[0], lb.REST_MAX + 1,
                                 "der Restplatz ist gedeckelt - sonst wird "
                                 "die Spalte zur Sackgasse aus Leerraum")

    def test_zebra_jede_zweite_zeile_andere_tags_bleiben(self):
        t = self._tabelle()
        t.setze([("a", "1"), ("b", "2"), ("c", "3")], tags=[(), ("wartet",), ()])
        tags = [tuple(t.baum.item(i, "tags")) for i in t.baum.get_children()]
        self.assertEqual(tags, [(), ("zebra", "wartet"), ()])

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

    def test_senkrechte_und_waagerechte_leiste_und_mausrad(self):
        """T-301: dieselbe Ausstattung wie die Tabellen der Handelszentrale."""
        t = self._tabelle()
        self.assertTrue(str(t.baum.cget("yscrollcommand")),
                        "keine vertikale Scrollbar")
        self.assertTrue(str(t.baum.cget("xscrollcommand")),
                        "keine waagerechte Scrollbar")
        self.assertTrue(str(t.baum.bind("<MouseWheel>")),
                        "keine Mausrad-Bindung")


class TabelleBaueinheitTest(unittest.TestCase):
    """`rad_selbst` kommt aus handelszentrale - die EINE Quelle beider
    Fenster (T-301). Bewusst NUR die Herkunft, nicht die Rechnung selbst
    (die prueft test_handelszentrale_struktur.RadRichtungTest)."""

    def test_rad_selbst_kommt_aus_der_zentrale(self):
        import re
        quelle = Path(lb.__file__).read_text(encoding="utf-8")
        # Der Leitstand definiert selbst kein rad_selbst - er nimmt das der
        # Zentrale. Eine zweite Fassung waere die zweite Quelle, die T-301
        # gerade verhindern will.
        self.assertNotIn("def rad_selbst", quelle)
        self.assertIn("hz.rad_selbst", quelle)


class Spaltenfilter(unittest.TestCase):
    """Freitext filtert in ALLEN Spalten; der Spaltenfilter in genau einer.

    Auftrag Max (05.10.2026): "die PnL% etc als Auswahl in den Listen zum
    Filtern". Ohne Vergleichszeichen ist es ein Teilstring, mit `>`/`<`/`=`
    eine Zahl - sonst waere "12,5 %" nicht gegen "3 %" zu halten.
    """

    SP = ("Spur", "Runden", "Treffer %", "Ergebnis")

    def t(self, bedingung, spalte="Treffer %"):
        return lb.passt_spalte(self.zeile, self.SP, spalte, bedingung)

    def setUp(self):
        self.zeile = ("moondev_signalwelle", "16", "56 %", "+35.72 USD")

    def test_ohne_bedingung_passt_alles(self):
        for zelle in ("", None):
            self.assertTrue(self.t(zelle))

    def test_teilstring_in_einer_spalte(self):
        self.assertTrue(self.t("signalwelle", "Spur"))
        self.assertFalse(self.t("signalwelle", "Ergebnis"))

    def test_groesser_als(self):
        self.assertTrue(self.t(">50"))
        self.assertFalse(self.t(">60"))

    def test_kleiner_als(self):
        self.assertTrue(self.t("<60"))
        self.assertFalse(self.t("<50"))

    def test_gleich_und_vergleich(self):
        self.assertTrue(self.t("=56"))
        self.assertTrue(self.t(">=56"))
        self.assertTrue(self.t("<=56"))
        self.assertFalse(self.t("<56"))

    def test_negative_ergebnis_filtern(self):
        zeile = ("kraken", "9", "40 %", "-12.30 USD")
        self.assertTrue(lb.passt_spalte(zeile, self.SP, "Ergebnis", "<0"))
        self.assertFalse(lb.passt_spalte(zeile, self.SP, "Ergebnis", ">0"))

    def test_zahl_aus_text_mit_einheit_und_prozent(self):
        self.assertEqual(lb.zahl_aus_text("12,5 %"), 12.5)
        self.assertEqual(lb.zahl_aus_text("35.72 USD"), 35.72)
        self.assertEqual(lb.zahl_aus_text("-3,10"), -3.1)
        self.assertEqual(lb.zahl_aus_text("+2 %"), 2.0)
        self.assertEqual(lb.zahl_aus_text("1.234,5"), 1234.5)
        self.assertEqual(lb.zahl_aus_text("1,234.5"), 1234.5)
        self.assertIsNone(lb.zahl_aus_text("Papier"))
        self.assertIsNone(lb.zahl_aus_text(""))

    def test_vergleich_ohne_zahl_treift_nichts(self):
        # ">Papier" ist keine Zahl - stilles Nichts-Finden waere eine
        # Falschaussage; die Zeile fliegt raus und man sieht es.
        self.assertFalse(self.t(">Papier"))

    def test_unbekannte_spalte_blendet_nicht_aus(self):
        self.assertTrue(self.t(">1000", "Gibt es nicht"))

    def test_fehlende_zelle_blendet_nicht_aus(self):
        kurz = ("kraken", "9")
        self.assertTrue(lb.passt_spalte(kurz, self.SP, "Treffer %", ">1"))


class SpaltenfilterAmBaum(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self._zu)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.zustand = lb.Zustand(Path(self.tmp.name) / "z.json")

    def _zu(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def tab(self):
        t = lb.Tabelle(self.root, ("Spur", "Treffer %", "Ergebnis"),
                       self.zustand, "probe")
        t.setze([("signalwelle", "56 %", "+35.72 USD"),
                 ("marktlage", "0 %", "-5.02 USD"),
                 ("kraken", "67 %", "+12.00 USD")])
        return t

    def test_die_spalten_liste_ist_die_der_tabelle(self):
        t = self.tab()
        self.assertEqual(list(t.cmb_spalte.cget("values"))[1:],
                         list(t.spalten))

    def test_filteren_nach_spalte_und_wert(self):
        t = self.tab()
        t.w_spalte.set("Treffer %")
        t.w_wert.set(">50")
        # Die Reihenfolge bleibt die der Quelle - der Filter sortiert nicht.
        # Sortieren macht der Spaltenkopf, das ist eine eigene Sache.
        self.assertEqual([z[0] for z in t.sichtbare()],
                         ["signalwelle", "kraken"])

    def test_beide_filter_gleichzeitig(self):
        t = self.tab()
        t.w_filter.set("kraken")
        t.w_spalte.set("Ergebnis")
        t.w_wert.set("<0")
        self.assertEqual(t.sichtbare(), [])      # kraken hat +12
        t.w_wert.set(">0")
        self.assertEqual([z[0] for z in t.sichtbare()], ["kraken"])

    def test_filter_weg_leert_alles(self):
        t = self.tab()
        t.w_filter.set("a")
        t.w_spalte.set("Ergebnis")
        t.w_wert.set("<0")
        t._filter_weg()
        self.assertEqual(len(t.sichtbare()), 3)
        self.assertEqual(t.w_filter.get(), "")
        self.assertEqual(t.w_spalte.get(), "")
        self.assertEqual(t.w_wert.get(), "")


if __name__ == "__main__":
    unittest.main()
