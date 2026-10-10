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
    def test_angeboten_wird_alles_fahrbare(self):
        # Familie A UND D: mosaic und gitter sind seit 01.10.2026 fahrbar
        # (eigener Weg, am Spurnamen erkannt - T-294/T-295).
        self.assertEqual(lbt.replay_spuren(),
                         list(replay.SPUREN_TEIL_A)
                         + list(replay.MEHRZEITRAHMEN)
                         + list(replay.EIGENE_RECHNUNG)
                         + list(replay.SPUREN_TEIL_E))
        for spur in ("mosaic", "gitter"):
            self.assertIn(spur, lbt.replay_spuren())
        for spur, _grund in lbt.nicht_nachrechenbar():
            self.assertNotIn(spur, lbt.replay_spuren())

    def test_gegenprobe_nur_fuer_familie_a(self):
        """`--gegenprobe` vergleicht gegen `backtest_prognose` - fuer eine Spur
        mit eigener Rechnung gibt es das nicht."""
        self.assertTrue(lbt.gegenprobe_moeglich("squeeze"))
        self.assertFalse(lbt.gegenprobe_moeglich("mosaic"))
        self.assertFalse(lbt.gegenprobe_moeglich("gitter"))
        teile, fehler = lbt.pruefe_replay({"spur": "mosaic", "max_kerzen": "0",
                                           "gebuehr": "", "gegenprobe": True})
        self.assertIsNone(teile)
        self.assertIn("Gegenprobe", fehler)

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
        # squeeze steht in replay.SPUREN_TEIL_A. (gitter stand dort bis 01.10.2026
        # und faehrt seit dem einen eigenen Weg - angeboten wird es trotzdem.)
        teile, _f = lbt.pruefe_replay({"spur": "squeeze", "max_kerzen": "0",
                                       "gebuehr": "0.1", "gegenprobe": False})
        self.assertEqual(teile, ["--spur", "squeeze", "--gebuehr", "0.1"])

    def test_fenster_unter_der_spuranforderung_wird_abgewiesen(self):
        """Sonst startet der Reiter einen Lauf, der nur scheitern kann, und der
        Nutzer sieht statt eines Satzes einen Traceback (01.10.2026:
        supertrend, max_kerzen 200 gegen mindest_kerzen 300)."""
        teile, fehler = lbt.pruefe_replay({"spur": "supertrend",
                                           "max_kerzen": "200",
                                           "gebuehr": "0.1"})
        self.assertIsNone(teile)
        self.assertIn("320", fehler)
        self.assertIn("supertrend", fehler)

    def test_das_mindestmass_der_spur_ist_das_mass(self):
        """Geprueft wird gegen die ANFORDERUNG der Spur, nicht gegen eine Zahl
        im Reiter: macd_mtf braucht 600, also 620 Kerzen."""
        w = json.loads((Path(__file__).resolve().parent.parent
                        / "macd_mtf" / "wachen.json").read_text(encoding="utf-8"))
        teile, fehler = lbt.pruefe_replay({"spur": "macd_mtf",
                                           "max_kerzen": str(replay.bedarf(w) - 1),
                                           "gebuehr": "0.1"})
        self.assertIsNone(teile)
        self.assertIn(str(replay.bedarf(w)), fehler)
        teile, fehler = lbt.pruefe_replay({"spur": "macd_mtf",
                                           "max_kerzen": str(replay.bedarf(w)),
                                           "gebuehr": "0.1"})
        self.assertEqual(fehler, "")
        self.assertIn(str(replay.bedarf(w)), teile)

    def test_eine_spur_ohne_wachen_datei_sperrt_den_reiter_nicht(self):
        """Fail-open: fehlt die Datei, prueft der Replay beim Lauf - der Reiter
        darf deswegen keinen guten Aufruf verwerfen."""
        with patch.object(replay, "bedarf_fuer", return_value=None):
            teile, fehler = lbt.pruefe_replay({"spur": "squeeze",
                                               "max_kerzen": "50",
                                               "gebuehr": "0.1"})
        self.assertEqual(fehler, "")
        self.assertEqual(teile, ["--spur", "squeeze", "--gebuehr", "0.1",
                                 "--max-kerzen", "50"])

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

    def test_ueberschrift_je_block(self):
        r = self.reiter([])
        texte = _alle_texte(r)
        for t in ("Protokoll", "Läufe", "Kennzahlen"):
            self.assertIn(t, texte)

    def test_teiler_lage_wird_gemerkt_und_wiederhergestellt(self):
        self.root.deiconify()
        self.root.geometry("1000x800")
        r = self.reiter([])
        r.pack(fill="both", expand=True)
        self.root.update()
        r.teiler.sashpos(0, 150)
        r.teiler.sashpos(1, 420)
        r._teiler_merken()
        self.assertEqual(self.ls.zustand.get("teiler")["backtests"], [150, 420])
        r.destroy()
        r2 = self.reiter([])
        r2.pack(fill="both", expand=True)
        self.root.update()
        self.assertEqual([r2.teiler.sashpos(0), r2.teiler.sashpos(1)], [150, 420])

    def test_teiler_erststart_laesst_protokoll_und_tabellen_platz(self):
        self.root.deiconify()
        self.root.geometry("1000x900")
        r = self.reiter([])
        r.pack(fill="both", expand=True)
        self.root.update()
        h = r.teiler.winfo_height()
        self.assertLessEqual(r.teiler.sashpos(0), h * 0.4)
        self.assertLessEqual(r.teiler.sashpos(1), h * 0.65)

    def test_teiler_gewichte_lassen_protokoll_und_tabellen_mehr_platz(self):
        r = self.reiter([])
        gewichte = [int(r.teiler.pane(p, "weight")) for p in r.teiler.panes()]
        self.assertEqual(gewichte, [1, 2, 2])

    def test_urteile_eintragen_ist_nicht_abbrechbar(self):
        r = self.reiter([lbt.ReplayBereich])
        abgebrochen = []
        self.st.abbrechen = lambda: abgebrochen.append(1)
        self.assertTrue(r.abbrechbar())
        r.starte("urteile-eintragen", ["x"])
        self.assertFalse(r.abbrechbar())
        self.assertIn("disabled", r.k_abbrechen.state())
        r.abbrechen()
        self.assertEqual(abgebrochen, [])
        self.assertIn("nicht abbrechbar", self.ls.meldungen[-1])

    def test_gewoehnlicher_lauf_bleibt_abbrechbar(self):
        r = self.reiter([lbt.ReplayBereich])
        abgebrochen = []
        self.st.abbrechen = lambda: abgebrochen.append(1)
        r.starte("replay-squeeze", ["x"])
        self.assertTrue(r.abbrechbar())
        self.assertNotIn("disabled", r.k_abbrechen.state())
        r.abbrechen()
        self.assertEqual(abgebrochen, [1])

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


EINTRAG = {"name": "Mini", "skript": "gitter/backtest_gitter.py", "schreibt": [],
           "felder": [
               {"flag": "--wochen", "typ": "float", "vorgabe": 8.0, "min": 1, "max": 104},
               {"flag": "--stufen", "typ": "int", "vorgabe": None, "min": 2, "max": 200},
               {"flag": "--modell", "typ": "wahl", "vorgabe": "beide",
                "werte": ["schluss", "beide"]},
               {"flag": "--instrument", "typ": "text", "vorgabe": "alle"},
               {"flag": "--raster", "typ": "schalter", "vorgabe": False}]}


class Einzel(unittest.TestCase):
    def test_befehl_aus_vorgaben(self):
        werte = {f["flag"]: f["vorgabe"] for f in EINTRAG["felder"]}
        befehl, fehler = lbt.einzel_befehl(EINTRAG, werte)
        self.assertEqual(fehler, "")
        self.assertEqual(befehl, [sys.executable, "gitter/backtest_gitter.py",
                                  "--wochen", "8.0", "--modell", "beide",
                                  "--instrument", "alle"])

    def test_schalter_und_leere_felder(self):
        befehl, _f = lbt.einzel_befehl(EINTRAG, {"--wochen": "", "--stufen": "12",
                                                 "--modell": "", "--instrument": "",
                                                 "--raster": True})
        self.assertEqual(befehl[2:], ["--stufen", "12", "--raster"])

    def test_ungueltige_werte(self):
        for flag, wert in (("--wochen", "200"), ("--wochen", "acht"),
                           ("--stufen", "1.5"), ("--modell", "alles"),
                           ("--instrument", "BTC; del *")):
            befehl, fehler = lbt.einzel_befehl(EINTRAG, {flag: wert})
            self.assertIsNone(befehl, (flag, wert))
            self.assertIn(flag, fehler)

    def test_liste_verwirft_gefaehrliche_eintraege(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "liste.json"
            p.write_text(json.dumps({"eintraege": [
                EINTRAG,
                dict(EINTRAG, name="Json", felder=[{"flag": "--json", "typ": "text"}]),
                dict(EINTRAG, name="Opt", skript="optimieren.py"),
                dict(EINTRAG, name="Weg", skript="../x.py"),
                dict(EINTRAG, name="Fehlt", skript="gibtsnicht.py")]}),
                encoding="utf-8")
            gut, fehler = lbt.lade_liste(p)
        self.assertEqual([e["name"] for e in gut], ["Mini"])
        for name in ("Json", "Opt", "Weg", "Fehlt"):
            self.assertIn(name, fehler)

    def test_text_beginnt_mit_buchstabe_oder_ziffer(self):
        for wert in ("-x", "--json", ".x", "..", "a..b", "/x", "_x"):
            befehl, _f = lbt.einzel_befehl(EINTRAG, {"--instrument": wert})
            self.assertIsNone(befehl, wert)
        for wert in ("BTC", "XBT/USD", "a-b_c.d", "1"):
            befehl, _f = lbt.einzel_befehl(EINTRAG, {"--instrument": wert})
            self.assertIsNotNone(befehl, wert)

    def test_liste_verwirft_laufwerkspfad_und_falsche_grenzen(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "liste.json"
            falsch = [dict(f) for f in EINTRAG["felder"]]
            falsch[0]["min"] = "1"
            bool_grenze = [dict(f) for f in EINTRAG["felder"]]
            bool_grenze[0]["max"] = True
            p.write_text(json.dumps({"eintraege": [
                EINTRAG,
                dict(EINTRAG, name="Laufwerk", skript="C:x.py"),
                dict(EINTRAG, name="Grenze", felder=falsch),
                dict(EINTRAG, name="Bool", felder=bool_grenze)]}),
                encoding="utf-8")
            gut, fehler = lbt.lade_liste(p)
        self.assertEqual([e["name"] for e in gut], ["Mini"])
        for name in ("Laufwerk", "Grenze", "Bool"):
            self.assertIn(name, fehler)

    def test_unlesbare_liste(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "liste.json"
            p.write_text("{kaputt", encoding="utf-8")
            self.assertEqual(lbt.lade_liste(p),
                             ([], "leitstand_backtests.json nicht lesbar"))


class EinzelReiter(TkBasis):
    def _liste(self, eintraege):
        p = Path(self.tmp.name) / "liste.json"
        p.write_text(json.dumps({"eintraege": eintraege}), encoding="utf-8")
        return p

    def _reiter(self, p):
        return lbt.BacktestReiter(self.root, self.ls, steuerung=self.st,
                                  bereiche=[lambda e, rt: lbt.EinzelBereich(e, rt, p)])

    def test_start_mit_feldern_aus_der_liste(self):
        r = self._reiter(self._liste([EINTRAG]))
        b = r.bereiche[0]
        b.vars["--wochen"].set("4")
        b.starten()
        name, befehl, _a, _s = self.st.gestartet[0]
        self.assertEqual(name, "einzel-Mini")
        self.assertEqual(befehl[1:4], ["gitter/backtest_gitter.py", "--wochen", "4.0"])
        self.assertEqual(self.ls.zustand.get("werte")["einzel"]["Mini"]["--wochen"], "4")

    def test_leere_liste_sperrt_start(self):
        r = self._reiter(self._liste([]))
        self.assertIn("disabled", r.bereiche[0].k_start.state())

    def test_falsch_typisierter_zustand_faellt_auf_vorgaben_zurueck(self):
        p = self._liste([EINTRAG])
        for werte in ({"einzel": "kaputt"}, {"einzel": {"Mini": "kaputt"}},
                      {"einzel": ["x"]}, "kaputt"):
            self.ls.zustand.daten["werte"] = werte
            r = self._reiter(p)
            self.assertEqual(r.bereiche[0].vars["--wochen"].get(), "8.0", werte)
            r.bereiche[0].starten()
            self.assertEqual(self.ls.zustand.get("werte")["einzel"]["Mini"]["--wochen"],
                             "8.0")
            self.st.lauf = None

    def test_replay_und_einzel_bauen_mit_kaputten_werten(self):
        p = self._liste([EINTRAG])
        for werte in ("kaputt", {"replay": "kaputt"}, {"replay": ["x"]}):
            self.ls.zustand.daten["werte"] = werte
            r = lbt.BacktestReiter(
                self.root, self.ls, steuerung=self.st,
                bereiche=[lbt.ReplayBereich,
                          lambda e, rt: lbt.EinzelBereich(e, rt, p)])
            self.assertEqual(r.bereiche[0].w_spur.get(),
                             lbt.REPLAY_VORGABEN["spur"], werte)
            self.assertEqual(r.bereiche[1].vars["--wochen"].get(), "8.0", werte)


if __name__ == "__main__":
    unittest.main()

class ReplayGebuehrFeldTest(unittest.TestCase):
    """Das Feld darf LEER bleiben - dann gilt der Satz der Spur."""

    def _werte(self, spur="squeeze", gebuehr=""):
        return {"spur": spur, "max_kerzen": "0", "gebuehr": gebuehr,
                "gegenprobe": False}

    def test_leeres_feld_gibt_kein_gebuehr_argument(self):
        teile, fehler = lbt.pruefe_replay(self._werte())
        self.assertEqual("", fehler)
        self.assertNotIn("--gebuehr", teile)

    def test_eigene_gebuehr_steht_im_befehl(self):
        teile, fehler = lbt.pruefe_replay(self._werte(gebuehr="0.6"))
        self.assertEqual("", fehler)
        self.assertIn("--gebuehr", teile)
        self.assertIn("0.6", teile)

    def test_kaputte_gebuehr_ist_ein_eingabefehler(self):
        teile, fehler = lbt.pruefe_replay(self._werte(gebuehr="abc"))
        self.assertIsNone(teile)
        self.assertIn("Gebühr", fehler)

    def test_gebuehr_ueber_der_grenze_wird_abgewiesen(self):
        teile, fehler = lbt.pruefe_replay(self._werte(gebuehr="9"))
        self.assertIsNone(teile)
        self.assertIn("0 bis 5", fehler)

    def test_vorgabe_ist_leer_und_nicht_null_eins(self):
        self.assertEqual("", lbt.REPLAY_VORGABEN["gebuehr"])
