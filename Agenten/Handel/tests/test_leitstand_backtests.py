"""Backtest-Reiter: Replay-Befehl, feste Hinweiszeile, ein Lauf gleichzeitig,
Kennzahlen nach dem Ende, unlesbare Ablage.

Die Laufsteuerung ist eine Attrappe (kein Prozess); die echte ist in
test_leitstand_backtests_lauf.py geprueft. Ablage und Zustand liegen in einem
Temp-Ordner. Tk-Teile werden ohne Bildschirm uebersprungen.

Direkt ausfuehrbar:  python tests/test_leitstand_backtests.py
"""

import json
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitstand_backtests as lbt                              # noqa: E402
import leitstand_bedienung as lb                               # noqa: E402
import leitstand_laeufe as ll                                  # noqa: E402
import replay                                                  # noqa: E402


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

    def laeuft(self):
        return self.lauf is not None

    def abbrechen(self):
        pass

    def takt(self):
        erg, self.naechstes = self.naechstes, ([], None)
        if erg[1]:
            self.lauf = None
        return erg

    def status(self):
        return "Backtest: %s läuft seit 0:01" % self.lauf if self.lauf else ""


class Replay(unittest.TestCase):
    def test_angeboten_wird_nur_teil_a(self):
        self.assertEqual(lbt.replay_spuren(), list(replay.SPUREN_TEIL_A))
        for spur, _grund in lbt.nicht_nachrechenbar():
            self.assertNotIn(spur, lbt.replay_spuren())

    def test_befehl_mit_allen_feldern(self):
        teile, fehler = lbt.pruefe_replay({"spur": "squeeze", "max_kerzen": "2000",
                                           "gebuehr": "0,2", "gegenprobe": True})
        self.assertEqual(fehler, "")
        self.assertEqual(teile, ["--spur", "squeeze", "--gebuehr", "0.2",
                                 "--max-kerzen", "2000", "--gegenprobe"])
        b = lbt.replay_befehl(teile, "20260929-120000")
        self.assertEqual(b[0], sys.executable)
        self.assertEqual(b[1], "replay.py")
        self.assertEqual(b[-2:], ["--lauf", "leitstand-20260929-120000"])

    def test_null_kerzen_heisst_alle(self):
        teile, _f = lbt.pruefe_replay({"spur": "gitter", "max_kerzen": "0",
                                       "gebuehr": "0.1", "gegenprobe": False})
        self.assertEqual(teile, ["--spur", "gitter", "--gebuehr", "0.1"])

    def test_ungueltige_eingaben(self):
        for werte in ({"spur": "nautilus", "max_kerzen": "0", "gebuehr": "0.1"},
                      {"spur": "squeeze", "max_kerzen": "x", "gebuehr": "0.1"},
                      {"spur": "squeeze", "max_kerzen": "0", "gebuehr": "abc"},
                      {"spur": "squeeze", "max_kerzen": "0", "gebuehr": "9"},
                      {"spur": "squeeze", "max_kerzen": "-5", "gebuehr": "0.1"}):
            teile, fehler = lbt.pruefe_replay(werte)
            self.assertIsNone(teile, werte)
            self.assertTrue(fehler)


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
        self.ls = StubLeitstand(self.root,
                                lb.Zustand(Path(self.tmp.name) / "z.json"))
        self.st = FakeSteuerung(self.ablage)

    def reiter(self, bereiche=None):
        r = lbt.BacktestReiter(self.root, self.ls, steuerung=self.st,
                               bereiche=bereiche)
        self.root.update_idletasks()
        return r


def _alle_texte(widget):
    aus = []
    for k in widget.winfo_children():
        try:
            aus.append(str(k.cget("text")))
        except tk.TclError:
            pass
        aus += _alle_texte(k)
    return aus


class Reiter(TkBasis):
    def test_feste_hinweiszeile(self):
        r = self.reiter()
        self.assertIn(lbt.HINWEIS_FREIGABE, _alle_texte(r))

    def test_start_uebergibt_befehl_und_merkt_werte(self):
        r = self.reiter([lbt.ReplayBereich])
        b = r.bereiche[0]
        b.w_spur.set("squeeze")
        b.w_kerzen.set("1500")
        b.w_gebuehr.set("0.1")
        b.w_gegen.set(True)
        b.starten()
        name, befehl, auswerten, stempel = self.st.gestartet[0]
        self.assertEqual(name, "replay-squeeze")
        self.assertIn("--gegenprobe", befehl)
        self.assertEqual(befehl[-1], "leitstand-" + stempel)
        self.assertIs(auswerten, ll.json_aus_ausgabe)
        self.assertEqual(self.ls.zustand.get("werte")["replay"]["max_kerzen"], "1500")
        self.assertIn("disabled", b.k_start.state())

    def test_ungueltige_gebuehr_startet_nicht(self):
        r = self.reiter([lbt.ReplayBereich])
        r.bereiche[0].w_gebuehr.set("viel")
        r.bereiche[0].starten()
        self.assertEqual(self.st.gestartet, [])
        self.assertIn("Gebühr", self.ls.meldungen[-1])

    def test_zweiter_start_meldet_statt_zu_starten(self):
        r = self.reiter([lbt.ReplayBereich])
        self.assertTrue(r.starte("a", ["x"]))
        self.assertFalse(r.starte("b", ["y"]))
        self.assertEqual(self.ls.meldungen[-1], "es läuft schon: a")
        self.assertEqual(len(self.st.gestartet), 1)

    def test_lauf_ende_zeigt_kennzahlen_und_gibt_start_frei(self):
        r = self.reiter([lbt.ReplayBereich])
        rueck = []
        r.starte("replay-squeeze", ["x"], fertig=lambda p, d: rueck.append(d))
        daten = {"name": "replay-squeeze", "exit_code": 0, "abgebrochen": False,
                 "ergebnis": {"spur": "squeeze", "runden": 10}}
        self.st.naechstes = (["fertig\n"], (self.ablage / "x.json", daten))
        r._takt()
        self.assertIn(("runden", "10", "", ""), r.ergebnis.sichtbare())
        self.assertEqual(self.ls.meldungen[-1], "replay-squeeze fertig")
        self.assertEqual(rueck, [daten])
        self.assertNotIn("disabled", r.bereiche[0].k_start.state())
        self.assertIn("fertig", r.w_ausgabe.get("1.0", "end"))

    def test_ablagefehler_wird_als_letzte_meldung_gezeigt(self):
        r = self.reiter([lbt.ReplayBereich])
        r.starte("replay-squeeze", ["x"])
        daten = {"name": "replay-squeeze", "exit_code": 0, "abgebrochen": False,
                 "ablage_fehler": "Zugriff verweigert"}
        self.st.naechstes = ([], (self.ablage / "x.json", daten))
        r._takt()
        self.assertTrue(self.ls.meldungen[-1].startswith(
            "replay-squeeze: Ergebnis NICHT abgelegt"))

    def test_abgebrochen_und_exit_code_werden_gemeldet(self):
        r = self.reiter([])
        r.starte("a", ["x"])
        self.st.naechstes = ([], (self.ablage / "a.json",
                                  {"name": "a", "exit_code": 1, "abgebrochen": True}))
        r._takt()
        self.assertEqual(self.ls.meldungen[-1], "a abgebrochen")
        r.starte("b", ["x"])
        self.st.naechstes = ([], (self.ablage / "b.json",
                                  {"name": "b", "exit_code": 4, "abgebrochen": False}))
        r._takt()
        self.assertEqual(self.ls.meldungen[-1], "b endete mit Exit 4")

    def test_unlesbare_ablage_steht_als_nicht_lesbar_in_der_liste(self):
        (self.ablage / "20260929-120000-x.json").write_text("{kaputt",
                                                            encoding="utf-8")
        r = self.reiter([])
        r.refresh()
        self.assertEqual(r.liste.sichtbare()[0][1], "nicht lesbar")

    def test_vergleichen_zweier_laeufe(self):
        for datei, runden in (("20260929-120000-a.json", 10),
                              ("20260929-130000-b.json", 12)):
            (self.ablage / datei).write_text(json.dumps(
                {"name": datei, "befehl": ["x"], "exit_code": 0,
                 "ergebnis": {"runden": runden}}), encoding="utf-8")
        r = self.reiter([])
        r.refresh()
        for iid in r.liste.baum.get_children():
            r.liste.baum.selection_add(iid)
        r.vergleichen()
        self.assertIn(("runden", "10", "12", "2"), r.ergebnis.sichtbare())

    def test_titel_und_status_waehrend_eines_laufs(self):
        r = self.reiter([])
        self.assertEqual(r.titel_zusatz(), "")
        r.starte("a", ["x"])
        self.assertEqual(r.titel_zusatz(), " ●")
        self.assertEqual(r.status(), "Backtest: a läuft seit 0:01")


if __name__ == "__main__":
    unittest.main()
