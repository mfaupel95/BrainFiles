"""Bereich Urteile: Vorschau rechnen, bestaetigen, genau diese Vorschau
eintragen lassen - und selbst nichts schreiben.

Kein Motor, keine echte wachen.json: FakeSteuerung nimmt die Befehle nur
entgegen, die Vorschau-Datei legt der Test selbst in den Temp-Ordner, der
Dialog ist eine Attrappe (ausser im Zeitablauf-Test).

Direkt ausfuehrbar:  python tests/test_leitstand_urteile.py
"""

import json
import sys
import tempfile
import tkinter as tk
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import backtest_urteile as bu                                  # noqa: E402
import leitstand_backtests as lbt                              # noqa: E402
import leitstand_bedienung as lb                               # noqa: E402
import leitstand_urteile as lu                                 # noqa: E402
import lesepruefung                                            # noqa: E402

JETZT = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
VORSCHAU = {
    "stand": "2026-09-29T12:00:00+00:00", "art": "urteile-vorschau",
    "spuren": {
        "gitter": {"stand": "2026-09-29T12:00:00+00:00", "bestanden": True,
                   "urteil": "Gitter schlaegt Halten", "kennzahlen": {}, "alt": False,
                   "sha256": "aa"},
        "nautilus": {"stand": "2026-09-29T12:00:00+00:00", "bestanden": False,
                     "urteil": "Gitter -3 USDT", "kennzahlen": {}, "alt": False,
                     "sha256": "bb"},
        "orbk": {"stand": "2026-09-29T12:00:00+00:00", "bestanden": None,
                 "urteil": "kein URTEIL", "kennzahlen": {}, "alt": False,
                 "sha256": "cc"},
    },
}


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


class Rein(unittest.TestCase):
    def test_befehle(self):
        p = Path("ablage") / "x-urteile-vorschau.json"
        self.assertEqual(lu.urteile_befehl(["gitter", "orbk"], p),
                         [str(bu.PY_SCANNER), "backtest_urteile.py", "--spur", "gitter",
                          "--spur", "orbk", "--vorschau", "--vorschau-datei", str(p)])
        self.assertEqual(lu.eintragen_befehl(p),
                         [str(bu.PY_SCANNER), "backtest_urteile.py", "--aus-vorschau",
                          str(p)])

    def test_lade_vorschau(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "v.json"
            p.write_text(json.dumps(VORSCHAU), encoding="utf-8")
            self.assertEqual(lu.lade_vorschau(p), VORSCHAU)
            p.write_text("{kaputt", encoding="utf-8")
            self.assertIsNone(lu.lade_vorschau(p))
            p.write_text(json.dumps(dict(VORSCHAU, art="anderes")), encoding="utf-8")
            self.assertIsNone(lu.lade_vorschau(p))
            self.assertIsNone(lu.lade_vorschau(Path(tmp) / "fehlt.json"))
            for falsch in ([1], {"a": 1}, "ja", 1):
                spuren = {"gitter": dict(VORSCHAU["spuren"]["gitter"], bestanden=falsch)}
                p.write_text(json.dumps(dict(VORSCHAU, spuren=spuren)), encoding="utf-8")
                self.assertIsNone(lu.lade_vorschau(p), falsch)

    def test_anzeige_mit_fremdem_typ_gibt_fragezeichen(self):
        spuren = {"gitter": dict(VORSCHAU["spuren"]["gitter"], bestanden=[1])}
        self.assertEqual(lu.vorschau_zeilen(dict(VORSCHAU, spuren=spuren))[0][1], "?")

    def test_zeilen_und_aenderungen(self):
        self.assertEqual(lu.vorschau_zeilen(VORSCHAU), [
            ("gitter", "bestanden", "false → true", "Gitter schlaegt Halten"),
            ("nautilus", "nicht bestanden", "false → false", "Gitter -3 USDT"),
            ("orbk", "nicht ermittelbar", "false → bleibt", "kein URTEIL")])
        self.assertEqual(lu.aenderungen(VORSCHAU), [
            "gitter/wachen.json: backtest_bestanden false → true",
            "nautilus/wachen.json: backtest_bestanden false → false "
            "(Urteilstext und Datum neu)"])

    def test_darf_eintragen(self):
        p = Path("v.json")
        self.assertEqual(lu.darf_eintragen(None, None, JETZT),
                         (False, "erst Vorschau rechnen"))
        self.assertEqual(lu.darf_eintragen(p, None, JETZT),
                         (False, "Vorschau nicht lesbar"))
        self.assertEqual(lu.darf_eintragen(p, VORSCHAU, JETZT), (True, ""))
        self.assertEqual(lu.darf_eintragen(p, VORSCHAU, JETZT + timedelta(minutes=61)),
                         (False, "Vorschau älter als 60 min"))
        self.assertEqual(lu.darf_eintragen(p, VORSCHAU, JETZT - timedelta(minutes=10)),
                         (False, "Vorschau liegt in der Zukunft"))
        nur_orbk = dict(VORSCHAU, spuren={"orbk": VORSCHAU["spuren"]["orbk"]})
        self.assertEqual(lu.darf_eintragen(p, nur_orbk, JETZT),
                         (False, "keine Änderung"))
        self.assertEqual(lu.darf_eintragen(p, dict(VORSCHAU, stand="gestern"), JETZT),
                         (False, "Vorschau nicht lesbar"))

    def test_ergebnis_zeile(self):
        self.assertEqual(lu.ergebnis_zeile(0, "geschrieben: gitter/wachen.json\n"
                                              "unveraendert: nautilus/wachen.json\n"),
                         "geschrieben: gitter/wachen.json; "
                         "unveraendert: nautilus/wachen.json")
        self.assertEqual(lu.ergebnis_zeile(2, "nichts geschrieben - gitter/wachen.json "
                                              "hat sich seit der Vorschau geaendert\n"),
                         "nichts geschrieben - gitter/wachen.json hat sich seit der "
                         "Vorschau geaendert")
        self.assertEqual(lu.ergebnis_zeile(1, "nicht geschrieben: orbk - JSON\n"),
                         "Exit 1 — nicht geschrieben: orbk - JSON")
        self.assertEqual(lu.ergebnis_zeile(0, ""), "nichts zu schreiben")

    def test_ergebnis_zeile_nachbesserung_aufgabe_10(self):
        for text in ("nichts geschrieben - gitter: Probe gescheitert (kein Feld)",
                     "nichts geschrieben - Vorschau ohne Spuren",
                     "nichts geschrieben - Vorschau unlesbar"):
            self.assertEqual(lu.ergebnis_zeile(2, "Kopf\n%s\n" % text), text)
        self.assertEqual(lu.ergebnis_zeile(2, ""), "nichts geschrieben (Exit 2)")
        self.assertEqual(
            lu.ergebnis_zeile(1, "Urteile-Datei nicht geschrieben - Platte voll\n"),
            "Exit 1 — Urteile-Datei nicht geschrieben - Platte voll")
        self.assertEqual(
            lu.ergebnis_zeile(1, "geschrieben: gitter/wachen.json\n"
                                 "Urteile-Datei nicht geschrieben - Platte voll\n"),
            "Exit 1 — geschrieben: gitter/wachen.json; "
            "Urteile-Datei nicht geschrieben - Platte voll")


class Lesepruefung(unittest.TestCase):
    def test_urteile_bereich_schreibt_nichts(self):
        self.assertEqual(lesepruefung.schreibstellen(lu.__file__), [])
        self.assertFalse(lesepruefung.importiert(lu.__file__, "subprocess"))

    def test_lesepruefung_replace_mit_schluesselwort_ist_kein_fund(self):
        with tempfile.TemporaryDirectory() as tmp:
            q = Path(tmp) / "probe.py"
            q.write_text("x.replace(tzinfo=None)\nx.replace(1, tzinfo=None)\n",
                         encoding="utf-8")
            self.assertEqual(lesepruefung.schreibstellen(q), [])
            q.write_text("p.replace(q)\np.rename(q)\np.replace(target=q)\n"
                         "p.rename(target=q)\n", encoding="utf-8")
            self.assertEqual(len(lesepruefung.schreibstellen(q)), 4)

    def test_eingebunden(self):
        self.assertIn(lu.UrteileBereich, lbt.BEREICHE)


def attrappe(antwort, nebenbei=None):
    class Dialog:
        aufrufe = []

        def __init__(self, eltern, aenderungen, **kw):
            Dialog.aufrufe.append(list(aenderungen))

        def zeige_modal(self):
            if nebenbei:
                nebenbei()
            return antwort
    return Dialog


class Bereich(TkBasis):
    def setUp(self):
        super().setUp()
        self.jetzt = JETZT
        self.antwort, self.nebenbei = "ja", None

    def _bereich(self):
        fabrik = lambda e, r: lu.UrteileBereich(          # noqa: E731
            e, r, dialog=attrappe(self.antwort, self.nebenbei), uhr=lambda: self.jetzt)
        self.r = self.reiter([fabrik])
        return self.r.bereiche[0]

    def _ende(self, name, exit_code=0, ausgabe=""):
        self.st.naechstes = ([], (self.ablage / "x.json", {
            "name": name, "exit_code": exit_code, "abgebrochen": False,
            "ausgabe": ausgabe}))
        self.r._takt()
        self.root.update_idletasks()

    def _mit_vorschau(self):
        b = self._bereich()
        b.vorschau()
        name, befehl, _a, stempel = self.st.gestartet[-1]
        datei = Path(befehl[-1])
        datei.write_text(json.dumps(VORSCHAU), encoding="utf-8")
        self._ende(name)
        return b, datei

    def test_kein_autostart_und_eintragen_gesperrt(self):
        b = self._bereich()
        self.assertEqual(self.st.gestartet, [])
        self.assertIn("disabled", b.k_eintragen.state())
        self.assertEqual(b.tip_eintragen.text, "erst Vorschau rechnen")

    def test_vorschau_rechnen(self):
        b = self._bereich()
        b.vorschau()
        name, befehl, _a, stempel = self.st.gestartet[0]
        self.assertEqual(name, "urteile")
        self.assertEqual(befehl[-2:], ["--vorschau-datei",
                                       str(self.ablage / ("%s-urteile-vorschau.json"
                                                          % stempel))])
        self.assertEqual(befehl.count("--spur"), len(bu.MOTOREN))
        Path(befehl[-1]).write_text(json.dumps(VORSCHAU), encoding="utf-8")
        self._ende(name)
        self.assertEqual(len(b.tabelle.sichtbare()), 3)
        self.assertNotIn("disabled", b.k_eintragen.state())

    def test_keine_spur_gewaehlt(self):
        b = self._bereich()
        for v in b.vars.values():
            v.set(False)
        b._knoepfe()
        self.assertIn("disabled", b.k_vorschau.state())
        self.assertEqual(b.tip_vorschau.text, "keine Spur gewählt")

    def test_eintragen_nach_ja(self):
        b, datei = self._mit_vorschau()
        b.eintragen()
        name, befehl, _a, _s = self.st.gestartet[-1]
        self.assertEqual(name, "urteile-eintragen")
        self.assertEqual(befehl[-2:], ["--aus-vorschau", str(datei)])
        self.assertEqual(b.dialog.aufrufe, [lu.aenderungen(VORSCHAU)])
        self._ende(name, 0, "geschrieben: gitter/wachen.json\n")
        self.assertEqual(b.w_ergebnis.cget("text"), "geschrieben: gitter/wachen.json")
        self.assertIn("disabled", b.k_eintragen.state())    # Vorschau verbraucht
        self.assertEqual(b.tip_eintragen.text, "erst Vorschau rechnen")

    def test_abgebrochener_eintragelauf_meldet_pruefen(self):
        b, _datei = self._mit_vorschau()
        b.eintragen()
        name = self.st.gestartet[-1][0]
        self.st.naechstes = ([], (self.ablage / "x.json", {
            "name": name, "exit_code": -1, "abgebrochen": True, "ausgabe": ""}))
        self.r._takt()
        self.assertEqual(b.w_ergebnis.cget("text"),
                         "abgebrochen — Stand der wachen.json prüfen")

    def test_ausgetauschte_vorschau_datei_wird_nicht_eingetragen(self):
        halter = []
        def tausche():
            d = json.loads(halter[0].read_text(encoding="utf-8"))
            d["spuren"]["gitter"]["urteil"] = "untergeschoben"
            halter[0].write_text(json.dumps(d), encoding="utf-8")
        self.nebenbei = tausche
        b, datei = self._mit_vorschau()
        halter.append(datei)
        n = len(self.st.gestartet)
        b.eintragen()
        self.assertEqual(len(self.st.gestartet), n)
        self.assertEqual(b.w_ergebnis.cget("text"),
                         "Vorschau-Datei hat sich geändert — neu rechnen")

    def test_ja_nach_neuer_vorschau_startet_nichts(self):
        self.nebenbei = lambda: setattr(self.b, "datei", Path("andere-vorschau.json"))
        self.b, _datei = self._mit_vorschau()
        n = len(self.st.gestartet)
        self.b.eintragen()
        self.assertEqual(len(self.st.gestartet), n)
        self.assertEqual(self.b.w_ergebnis.cget("text"),
                         "Vorschau-Datei hat sich geändert — neu rechnen")

    def test_zukunftsstand_waehrend_des_dialogs(self):
        self.nebenbei = lambda: setattr(self, "jetzt", JETZT - timedelta(minutes=10))
        b, _datei = self._mit_vorschau()
        n = len(self.st.gestartet)
        b.eintragen()
        self.assertEqual(len(self.st.gestartet), n)
        self.assertEqual(b.w_ergebnis.cget("text"),
                         "Urteile nicht eingetragen — nichts geschrieben "
                         "(Vorschau liegt in der Zukunft)")

    def test_esc_im_echten_dialog_bricht_ab_ohne_start(self):
        class EscDialog(lu.EintragenDialog):
            def zeige_modal(self):
                self.after(30, lambda: self.event_generate("<Escape>", when="now"))
                self.after(300, lambda: self.fertig("abgebrochen"))   # Netz
                return super().zeige_modal()
        self.antwort = None
        b, _datei = self._mit_vorschau()
        b.dialog = EscDialog
        n = len(self.st.gestartet)
        b.eintragen()
        self.assertEqual(len(self.st.gestartet), n)
        self.assertEqual(b.w_ergebnis.cget("text"),
                         "Urteile nicht eingetragen — nichts geschrieben")

    def test_dialog_ja_ohne_fokus_abbrechen_hat_ihn(self):
        d = lu.EintragenDialog(self.root, ["gitter/wachen.json: x"])
        self.assertIn(str(d.k_ja.cget("takefocus")), ("0",))
        gefragt = []          # ohne Bildschirmfokus: wer bekommt focus_set?
        d.k_abbruch.focus_set = lambda: gefragt.append("abbruch")
        d.k_ja.focus_set = lambda: gefragt.append("ja")
        d.after(30, lambda: d.fertig("abgebrochen"))
        d.zeige_modal()
        self.assertEqual(gefragt, ["abbruch"])

    def test_abbrechen_schreibt_nichts(self):
        self.antwort = "abgebrochen"
        b, _datei = self._mit_vorschau()
        n = len(self.st.gestartet)
        b.eintragen()
        self.assertEqual(len(self.st.gestartet), n)
        self.assertEqual(b.w_ergebnis.cget("text"),
                         "Urteile nicht eingetragen — nichts geschrieben")
        self.assertNotIn("disabled", b.k_eintragen.state())

    def test_vorschau_veraltet_waehrend_des_dialogs(self):
        self.nebenbei = lambda: setattr(self, "jetzt", JETZT + timedelta(minutes=61))
        b, _datei = self._mit_vorschau()
        n = len(self.st.gestartet)
        b.eintragen()
        self.assertEqual(len(self.st.gestartet), n)
        self.assertEqual(b.w_ergebnis.cget("text"),
                         "Urteile nicht eingetragen — nichts geschrieben "
                         "(Vorschau älter als 60 min)")

    def test_alte_vorschau_sperrt_beim_refresh(self):
        b, _datei = self._mit_vorschau()
        self.jetzt = JETZT + timedelta(minutes=61)
        b.refresh()
        self.assertIn("disabled", b.k_eintragen.state())
        self.assertEqual(b.tip_eintragen.text, "Vorschau älter als 60 min")

    def test_vorschau_ohne_ergebnis(self):
        b = self._bereich()
        b.vorschau()
        self._ende("urteile", exit_code=1)
        self.assertEqual(b.w_ergebnis.cget("text"),
                         "Vorschau ohne Ergebnis (Exit 1) — Ausgabe oben")
        self.assertIn("disabled", b.k_eintragen.state())

    def test_gescheiterter_start_behaelt_die_vorschau(self):
        b, datei = self._mit_vorschau()
        self.st.lauf = "fremder-lauf"          # Steuerung lehnt den Start ab
        b.eintragen()
        self.assertEqual(b.datei, datei)
        self.st.lauf = None
        b._knoepfe()
        self.assertNotIn("disabled", b.k_eintragen.state())

    def test_echter_dialog_laeuft_ab_ohne_return_kuerzel(self):
        uhr = [0.0]
        d = lu.EintragenDialog(self.root, ["gitter/wachen.json: x"],
                               uhr=lambda: uhr[0])
        self.assertEqual(d.bind("<Return>"), "")
        uhr[0] = 121.0
        d._takt()
        self.assertEqual(d.ergebnis, "zeitablauf")


if __name__ == "__main__":
    unittest.main()
