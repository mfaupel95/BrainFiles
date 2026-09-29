"""Bereich Optimieren: Trockenlauf zuerst, Rechnen erst danach, Anzeige und
Unterschied aus einer Fixture-optimierung.json, keine Schreibstelle.

Kein echtes daten/backtest und keine echte wachen.json: spur_opt.json,
optimierung.json und wachen.json liegen im temporaeren Ordner. Laeufe starten
nie wirklich; FakeSteuerung nimmt den Befehl nur entgegen.

Direkt ausfuehrbar:  python tests/test_leitstand_optimieren.py
"""

import json
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import leitstand_backtests as lbt                              # noqa: E402
import leitstand_bedienung as lb                               # noqa: E402
import leitstand_optimieren as lo                              # noqa: E402
import lesepruefung                                            # noqa: E402

SPUR_OPT = {"_hinweis": "x", "squeeze": {"schluessel": ["a", "b"], "raster": {}}}
WACHEN = {"a": 1, "b": 2.0, "c": "x"}
OPT = {
    "spur": "squeeze", "grundlinie_netto_je_runde": 0.12, "ohne_wirkung": ["c"],
    "kandidaten": [
        {"werte": {"a": 3, "b": 2.0}, "netto_je_runde": 0.4, "ueberlebt": True,
         "fenster_gewonnen": 2, "fenster_verloren": 0, "fenster_zu_wenig": 0,
         "grund": "gewinnt alle 2"},
        {"werte": {"a": 1, "b": 3.0}, "netto_je_runde": 0.05, "ueberlebt": False,
         "fenster_gewonnen": 1, "fenster_verloren": 1, "fenster_zu_wenig": 0,
         "grund": "kein Hebel"},
        {"werte": {"a": 5, "b": 1.0}, "fehler": "zu wenige Fenster"},
    ],
}
PLAN_AUSGABE = (
    "Zeitraum angehoben: 6 Monate im 4H-Takt sind 1092 Kerzen\n"
    "{\n  \"spur\": \"squeeze\",\n  \"kerzen\": 4380,\n  \"n_fenster\": 2,\n"
    "  \"kandidaten\": 9,\n  \"takt\": \"1H\",\n  \"geschaetzte_sekunden\": 432\n}\n"
    "Trockenlauf: nichts gerechnet, nichts geschrieben.\n")
GUELTIG = {"spur": "squeeze", "monate": "6", "fenster": "2", "kandidaten": "40",
           "gebuehr": ""}


class StubLeitstand:
    def __init__(self, root, zustand):
        self.root, self.zustand, self.meldungen = root, zustand, []
    def melde(self, text):
        self.meldungen.append(text)


class FakeSteuerung:
    def __init__(self, ablage):
        self.ablage, self.gestartet, self.lauf = ablage, [], None
        self.naechstes = ([], None)
    def starte(self, name, befehl, auswerten=None, stempel=None):
        if self.lauf:
            raise RuntimeError("es läuft schon: %s" % self.lauf)
        self.lauf = name
        self.gestartet.append((name, list(befehl), auswerten, stempel))
        return SimpleNamespace(name=name, befehl=list(befehl))
    def laeuft(self): return self.lauf is not None
    def abbrechen(self): pass
    def takt(self):
        erg, self.naechstes = self.naechstes, ([], None)
        if erg[1]:
            self.lauf = None
        return erg
    def status(self):
        return "Backtest: %s läuft seit 0:01" % self.lauf if self.lauf else ""


class TkBasis(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ablage = Path(self.tmp.name) / "ablage"
        self.ablage.mkdir()
        self.ls = StubLeitstand(self.root, lb.Zustand(Path(self.tmp.name) / "z.json"))
        self.st = FakeSteuerung(self.ablage)
    def reiter(self, bereiche=None):
        r = lbt.BacktestReiter(self.root, self.ls, steuerung=self.st, bereiche=bereiche)
        self.root.update_idletasks()
        return r


def _schreib(pfad, daten):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(daten if isinstance(daten, str) else json.dumps(daten),
                    encoding="utf-8")
    return pfad


class Rein(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.t = Path(self.tmp.name)
        self.spur_opt = _schreib(self.t / "spur_opt.json", SPUR_OPT)

    def test_spuren_nur_mit_eintrag(self):
        self.assertEqual(lo.spuren(self.spur_opt), ["squeeze"])
        self.assertEqual(lo.spuren(_schreib(self.t / "kaputt.json", "{x")), [])
        self.assertEqual(lo.spuren(self.t / "fehlt.json"), [])

    def test_pruefe_werte(self):
        p = lambda **aend: lo.pruefe_werte(dict(GUELTIG, **aend), self.spur_opt)
        self.assertEqual(p(), "")
        self.assertEqual(p(gebuehr="0,2"), "")
        self.assertEqual(p(spur="gitter"),
                         "Spur 'gitter' hat keinen Eintrag in spur_opt.json")
        self.assertEqual(p(monate="sechs"), "monate: ganze Zahl erwartet")
        self.assertEqual(p(fenster="1"), "fenster: erlaubt 2 bis 12")
        self.assertEqual(p(kandidaten="501"), "kandidaten: erlaubt 1 bis 500")
        self.assertEqual(p(gebuehr="viel"), "gebuehr: Zahl erwartet")
        self.assertEqual(p(gebuehr="9"), "gebuehr: erlaubt 0 bis 5")

    def test_befehl(self):
        b = lo.optimieren_befehl(dict(GUELTIG, gebuehr="0,2"), trocken=True)
        self.assertEqual(b[1:], ["optimieren.py", "--spur", "squeeze", "--monate", "6",
                                 "--fenster", "2", "--max-kandidaten", "40",
                                 "--gebuehr", "0.2", "--trocken"])
        b = lo.optimieren_befehl(GUELTIG, trocken=False)
        self.assertNotIn("--trocken", b)
        self.assertNotIn("--gebuehr", b)

    def test_plan_text_mit_hinweis(self):
        import leitstand_laeufe as ll
        plan = ll.json_aus_ausgabe(PLAN_AUSGABE)
        text = lo.plan_text(plan, lo.angehoben(PLAN_AUSGABE))
        self.assertTrue(text.startswith(
            "9 Kandidaten · 2 Fenster · Takt 1H · 4380 Kerzen"
            " · etwa 7:12 min"))
        self.assertIn("\nZeitraum angehoben: 6 Monate", text)
        self.assertEqual(lo.angehoben("nur Text\n"), "")

    def test_kandidaten_zeilen(self):
        zeilen, tags = lo.kandidaten_zeilen(OPT)
        self.assertEqual(zeilen[0], ("heute", "heutige Einstellung", "0.12", "", "",
                                     "Grundlinie"))
        self.assertEqual(zeilen[1], (1, "a=3, b=2", "0.4", "2/0/0", "ja",
                                     "gewinnt alle 2"))
        self.assertEqual(zeilen[3][0], 3)
        self.assertEqual(zeilen[3][5], "Fehler: zu wenige Fenster")
        self.assertEqual(tags, [("grundlinie",), ("ueberlebt",), (), ()])
        self.assertEqual(lo.ohne_wirkung_text(OPT), "Feld c ändert nichts")

    def test_lade_optimierung(self):
        opt, fehler = lo.lade_optimierung("squeeze", self.t / "bt")
        self.assertIsNone(opt)
        self.assertEqual(fehler, "noch keine Optimierung für squeeze")
        _schreib(self.t / "bt" / "squeeze" / "optimierung.json", "{kaputt")
        self.assertEqual(lo.lade_optimierung("squeeze", self.t / "bt"),
                         (None, "optimierung.json nicht lesbar"))
        _schreib(self.t / "bt" / "squeeze" / "optimierung.json", OPT)
        self.assertEqual(lo.lade_optimierung("squeeze", self.t / "bt"), (OPT, ""))

    def test_alte_werte_und_diff(self):
        _schreib(self.t / "squeeze" / "wachen.json", WACHEN)
        alt = lo.alte_werte("squeeze", ["a", "b", "neu"], self.t)
        self.assertEqual(alt, {"a": 1, "b": 2.0})
        self.assertEqual(lo.diff_text("squeeze", alt, {"a": 3, "b": 2.0, "neu": 1}),
                         "squeeze/wachen.json\n  a: 1 → 3\n  neu: fehlt → 1")
        self.assertEqual(lo.diff_text("squeeze", alt, {"a": 1, "b": 2}),
                         "squeeze/wachen.json: keine Änderung gegenüber heute")
        self.assertIsNone(lo.alte_werte("gitter", ["a"], self.t))
        self.assertEqual(lo.diff_text("gitter", None, {"a": 1}),
                         "gitter/wachen.json nicht lesbar")

    def test_trocken_pruefung(self):
        p = lo.TrockenPruefung()
        self.assertEqual(p.darf_rechnen(GUELTIG), (False, "erst Trockenlauf"))
        p.merke(GUELTIG)
        self.assertEqual(p.darf_rechnen(GUELTIG), (True, ""))
        self.assertEqual(p.darf_rechnen(dict(GUELTIG, monate="12")),
                         (False, "Werte geändert — Trockenlauf läuft neu"))
        p.vergiss()
        self.assertEqual(p.darf_rechnen(GUELTIG), (False, "erst Trockenlauf"))


class Lesepruefung(unittest.TestCase):
    def test_optimieren_schreibt_nichts(self):
        self.assertEqual(lesepruefung.schreibstellen(lo.__file__), [])
        self.assertFalse(lesepruefung.importiert(lo.__file__, "subprocess"))

    FORMEN = [
        "open('x', 'w')", "open('x', 'a')", "open('x', 'r+')", "open('x', mode='wb')",
        "open('x', 'xb')", "open('x', modus)", "io.open('x', 'w')",
        "codecs.open('x', 'w')", "io.open('x', mode='a')", "jd(1, f)",
        "json.dump(1, f)", "os.remove('x')", "os.unlink('x')", "os.rename('a', 'b')",
        "os.replace('a', 'b')", "os.makedirs('x')", "os.mkdir('x')", "os.rmdir('x')",
        "os.open('x', os.O_WRONLY)", "shutil.move('a', 'b')", "shutil.copy('a', 'b')",
        "shutil.copy2('a', 'b')", "shutil.copyfile('a', 'b')",
        "shutil.copytree('a', 'b')", "shutil.rmtree('a')", "sh_move('a', 'b')",
        "Path('x').write_text('')", "Path('x').write_bytes(b'')",
        "Path('x').rename('y')", "Path('x').replace('y')", "Path('x').mkdir()",
        "Path('x').unlink()", "Path('x').touch()", "Path('x').rmdir()",
        "Path('x').open('a')", "csv.writer(f)", "csv.DictWriter(f, [])",
        "tempfile.NamedTemporaryFile()", "tempfile.mkstemp()", "tempfile.mkdtemp()",
        "f.write('x')", "obj.writelines([])", "osr('a', 'b')", "cw(f)",
    ]

    def test_die_pruefung_findet_jede_schreibform(self):
        kopf = ["import io, codecs, csv, os, shutil, tempfile", "import json",
                "from json import dump as jd", "from shutil import move as sh_move",
                "from os import replace as osr", "from csv import writer as cw",
                "from pathlib import Path"]
        with tempfile.TemporaryDirectory() as tmp:
            quelle = Path(tmp) / "probe.py"
            quelle.write_text("\n".join(kopf + self.FORMEN) + "\n", encoding="utf-8")
            funde = lesepruefung.schreibstellen(quelle)
            erste = len(kopf) + 1
            zeilen = sorted(int(f.split(":")[0][3:]) for f in funde)
            self.assertEqual(zeilen, list(range(erste, erste + len(self.FORMEN))),
                             "\n".join(funde))

    def test_die_pruefung_laesst_lesen_durch(self):
        with tempfile.TemporaryDirectory() as tmp:
            quelle = Path(tmp) / "probe.py"
            quelle.write_text(
                "\n".join(["import json", "from pathlib import Path", "p = 'x'",
                           "json.dumps({})", "open(p)", "open(p, 'r')",
                           "open(p, 'rb')", "open('wax.txt')",
                           "'a'.replace('a', 'b')", "Path(p).read_text()",
                           "import subprocess"]) + "\n", encoding="utf-8")
            self.assertEqual(lesepruefung.schreibstellen(quelle), [])
            self.assertTrue(lesepruefung.importiert(quelle, "subprocess"))
            self.assertFalse(lesepruefung.importiert(quelle, "shutil"))


class Bereich(TkBasis):
    def setUp(self):
        super().setUp()
        t = Path(self.tmp.name)
        self.spur_opt = _schreib(t / "spur_opt.json", SPUR_OPT)
        self.wurzel = t / "bt"
        self.opt_datei = _schreib(self.wurzel / "squeeze" / "optimierung.json", OPT)
        self.hier = t / "hier"
        _schreib(self.hier / "squeeze" / "wachen.json", WACHEN)
        self.fabrik = lambda e, r: lo.OptimierenBereich(
            e, r, spur_datei=self.spur_opt, wurzel=self.wurzel, hier=self.hier)

    def _trocken_fertig(self, r, exit_code=0, ausgabe=PLAN_AUSGABE):
        self.st.naechstes = ([], (self.ablage / "x.json", {
            "name": self.st.lauf, "exit_code": exit_code, "abgebrochen": False,
            "ausgabe": ausgabe}))
        r._takt()
        self.root.update_idletasks()

    def _waehle(self, b, nr):
        for iid in b.tabelle.baum.get_children():
            if b.tabelle.baum.item(iid, "values")[0] == str(nr):
                b.tabelle.baum.selection_set(iid)
        b._auswahl()

    def test_trockenlauf_startet_sobald_sichtbar(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self.assertEqual(len(self.st.gestartet), 1)
        name, befehl, _a, _s = self.st.gestartet[0]
        self.assertEqual(name, "optimieren-trocken-squeeze")
        self.assertEqual(befehl[-1], "--trocken")
        self.assertIn("disabled", b.k_rechnen.state())
        self.assertEqual(b.tip.text, "erst Trockenlauf")

    def test_rechnen_erst_nach_trockenlauf(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self._trocken_fertig(r)
        self.assertNotIn("disabled", b.k_rechnen.state())
        self.assertIn("9 Kandidaten", b.w_plan.cget("text"))
        self.assertIn("Zeitraum angehoben", b.w_plan.cget("text"))
        self.assertEqual(len(self.st.gestartet), 1)        # kein zweiter Trockenlauf
        b.rechnen()
        name, befehl, _a, _s = self.st.gestartet[-1]
        self.assertEqual(name, "optimieren-squeeze")
        self.assertNotIn("--trocken", befehl)
        self.assertEqual(self.ls.zustand.get("werte")["optimieren"]["spur"], "squeeze")

    def test_wertaenderung_sperrt_und_rechnet_den_plan_neu(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self._trocken_fertig(r)
        b.vars["monate"].set("12")
        self.assertIn("disabled", b.k_rechnen.state())
        self.assertEqual(b.tip.text,
                         "Werte geändert — Trockenlauf läuft neu")
        b._wenn_sichtbar()                                  # statt der Entprellung
        self.assertEqual(len(self.st.gestartet), 2)
        self.assertIn("12", self.st.gestartet[-1][1])

    def test_ungueltiger_wert_sperrt_ohne_lauf(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self._trocken_fertig(r)
        b.vars["fenster"].set("99")
        b._wenn_sichtbar()
        self.assertEqual(len(self.st.gestartet), 1)
        self.assertEqual(b.tip.text, "fenster: erlaubt 2 bis 12")

    def test_trockenlauf_ohne_plan(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self._trocken_fertig(r, exit_code=1, ausgabe="Traceback ...\nKeyError\n")
        self.assertEqual(b.w_plan.cget("text"), "Trockenlauf ohne Plan (Exit 1)")
        self.assertEqual(b.tip.text, "erst Trockenlauf")
        b._wenn_sichtbar()                   # derselbe Versuch nicht in Schleife
        self.assertEqual(len(self.st.gestartet), 1)

    def test_tabelle_und_unterschied(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self.assertEqual(len(b.tabelle.sichtbare()), 4)
        self.assertEqual(b.tabelle.sichtbare()[0][0], "heute")
        self.assertEqual(b.w_hinweis.cget("text"), "Feld c ändert nichts")
        self._waehle(b, 1)
        self.assertEqual(b.w_diff.get("1.0", "end-1c"),
                         "squeeze/wachen.json\n  a: 1 → 3")
        self.assertEqual(b.kopieren(), "squeeze/wachen.json\n  a: 1 → 3")
        self.assertEqual(self.root.clipboard_get(), "squeeze/wachen.json\n  a: 1 → 3")
        self.assertEqual(self.ls.meldungen[-1], "Unterschied kopiert")
        self._waehle(b, 2)
        self.assertEqual(b.w_diff.get("1.0", "end-1c"),
                         "nur überlebende Kandidaten werden verglichen")
        self.assertEqual(json.loads((self.hier / "squeeze" / "wachen.json")
                                    .read_text(encoding="utf-8")), WACHEN)

    def test_unlesbare_optimierung(self):
        self.opt_datei.write_text("{kaputt", encoding="utf-8")
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self.assertEqual(b.w_hinweis.cget("text"), "optimierung.json nicht lesbar")
        self.assertEqual(b.tabelle.sichtbare(), [])

    def test_falsch_typisierter_zustand_wirft_nicht(self):
        for falsch in ("text", [1], {"optimieren": "x"}, {"optimieren": [1]}):
            self.ls.zustand.daten["werte"] = falsch
            b = self.reiter([self.fabrik]).bereiche[0]
            self.assertEqual(b.vars["monate"].get(), "6")

    def test_direkter_aufruf_bricht_den_timer_ab(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        b.vars["monate"].set("12")
        timer = b._entprell
        self.assertIsNotNone(timer)
        abgebrochen, orig = [], b.after_cancel
        b.after_cancel = lambda i: (abgebrochen.append(i), orig(i))
        b._wenn_sichtbar()
        self.assertEqual(abgebrochen, [timer])
        self.assertIsNone(b._entprell)
        r.destroy()
        self.root.update()

    def test_start_nicht_moeglich(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self._trocken_fertig(r)
        r.starte = lambda *a, **k: False
        b.vars["monate"].set("12")
        b._wenn_sichtbar()
        self.assertEqual(b.w_plan.cget("text"), "Start nicht möglich")
        self.assertIsNone(b._versucht)
        self.assertEqual(b.tip.text, "erst Trockenlauf")

    def test_unsichtbar_startet_nichts(self):
        r = self.reiter([lbt.ReplayBereich, self.fabrik])
        self.root.update()
        self.assertEqual(self.st.gestartet, [])
        r.arten.select(1)
        self.root.update()
        self.assertEqual([g[0] for g in self.st.gestartet],
                         ["optimieren-trocken-squeeze"])


if __name__ == "__main__":
    unittest.main()
