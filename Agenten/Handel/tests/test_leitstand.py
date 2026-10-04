"""Leitstand-Rahmen: Reiter, Takt, Kuerzel, Statusleiste, Zustand, Herzschlag.

Die meisten Tests haengen Stub-Reiter ein. Ein Rauchtest baut die echten vier
Reiter mit Temp-Dateien (Freigaben, Ablage, Marktbericht) und ohne Netz:
Handelszentrale.refresh startet Kurs-Threads und wird ersetzt. Ohne
Bildschirm werden die Tk-Tests uebersprungen.

Direkt ausfuehrbar:  python tests/test_leitstand.py
"""

import datetime as dt
import json
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import font as tkfont, ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import freigabefenster as ff                                   # noqa: E402
import handelszentrale as hz                                   # noqa: E402
import leitstand as lst                                        # noqa: E402
import leitstand_bedienung as lb                               # noqa: E402
import leitstand_freigaben as lf                               # noqa: E402
import leitstand_laeufe as ll                                  # noqa: E402
import leitstand_markt as lm                                   # noqa: E402
import leitstand_stil as stil                                  # noqa: E402
import lesepruefung                                            # noqa: E402

TITEL = ("Überwachen", "Freigaben", "Backtests", "Markt")
VERBOTENE_TASTEN = ("Return", "KP_Enter", "Control-", "Alt-")


class StubReiter(ttk.Frame):
    def __init__(self, eltern, leitstand):
        super().__init__(eltern)
        self.ls, self.aufrufe, self.zusatz, self.text = leitstand, 0, "", ""
    def refresh(self):
        self.aufrufe += 1
    def titel_zusatz(self):
        return self.zusatz
    def status(self):
        return self.text


class FakeLauf:
    def __init__(self):
        self.abgebrochen = 0
    def laeuft(self):
        return True
    def abbrechen(self):
        self.abgebrochen += 1


STUBS = [(t, StubReiter) for t in TITEL]


class Basis(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self._zu)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pfad = Path(self.tmp.name) / "z.json"
        p = patch.object(hz, "SCHRIFT_GROESSE", 11)
        p.start()
        self.addCleanup(p.stop)

    def _zu(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass                      # schliessen() hat es schon getan

    def leitstand(self, daten=None, reiter=STUBS):
        if daten is not None:
            self.pfad.write_text(json.dumps(daten), encoding="utf-8")
        self.z = lb.Zustand(self.pfad)
        ls = lst.Leitstand(self.root, zustand=self.z, reiter=reiter,
                           uhr=lambda: dt.datetime(2026, 9, 29, 12, 0, 5),
                           herz=lambda: "Dauerlauf läuft nicht")
        self.root.update()
        return ls


class Rahmen(Basis):
    def test_titel_bekommen_den_zusatz(self):
        ls = self.leitstand()
        ls.reiter[1].zusatz = " (2)"
        ls._takt()
        self.assertEqual(ls.buch.tab(1, "text"), "Freigaben (2)")
        self.assertEqual(ls.buch.tab(0, "text"), TITEL[0])

    def test_gemerkter_reiter_gilt_beim_start(self):
        ls = self.leitstand({"reiter": 2})
        self.assertEqual(ls.sichtbarer_index(), 2)

    def test_unsinniger_reiter_faellt_auf_den_ersten(self):
        ls = self.leitstand({"reiter": 9})
        self.assertEqual(ls.sichtbarer_index(), 0)

    def test_kuerzel_wechselt_reiter_merkt_ihn_und_frischt_auf(self):
        ls = self.leitstand()
        vorher = ls.reiter[2].aufrufe
        ls.kuerzel("<Control-Key-3>")
        self.root.update()
        self.assertEqual(ls.sichtbarer_index(), 2)
        self.assertEqual(self.z.get("reiter"), 2)
        self.assertEqual(ls.reiter[2].aufrufe, vorher + 1)

    def test_f5_frischt_nur_den_sichtbaren_auf(self):
        ls = self.leitstand()
        vorher = [r.aufrufe for r in ls.reiter]
        ls.kuerzel("<F5>")
        nachher = [r.aufrufe for r in ls.reiter]
        self.assertEqual(nachher, [vorher[0] + 1] + vorher[1:])

    def test_schrift_bleibt_in_den_grenzen_und_wird_gemerkt(self):
        ls = self.leitstand()
        ls.setze_schrift(16)
        ls.kuerzel("<Control-plus>")
        self.assertEqual(ls.schrift, 16)
        ls.setze_schrift(8)
        ls.kuerzel("<Control-KP_Subtract>")
        self.assertEqual(ls.schrift, 8)
        self.assertEqual(self.z.get("schrift"), 8)
        ls.kuerzel("<Control-KP_Add>")
        self.assertEqual(ls.schrift, 9)

    def test_schriftwechsel_wirkt_ueber_den_stil_in_allen_reitern(self):
        ls = self.leitstand()
        schrift = lambda n: tkfont.nametofont(n, self.root).cget("size")
        self.assertEqual(schrift(stil.TEXT), 11)
        hoehe = int(ttk.Style(self.root).lookup("Treeview", "rowheight"))
        ls.setze_schrift(15)
        self.assertEqual((schrift(stil.TEXT), schrift(stil.TITEL)), (15, 17))
        self.assertGreater(int(ttk.Style(self.root).lookup("Treeview", "rowheight")), hoehe)

    def test_stil_liegt_ueber_dem_der_reiter(self):
        # Die Zentrale setzt in _baue ihr eigenes Theme; der Leitstand kommt danach.
        class Eigensinn(StubReiter):
            def __init__(self, eltern, leitstand):
                super().__init__(eltern, leitstand)
                ttk.Style(self).configure("Treeview", background="#ffffff")
        self.leitstand(reiter=[(TITEL[0], Eigensinn)] + STUBS[1:])
        self.assertEqual(ttk.Style(self.root).lookup("Treeview", "background"),
                         stil.FARBEN["blatt"])

    def test_gemerkte_schrift_gilt_nur_in_den_grenzen(self):
        self.assertEqual(self.leitstand({"schrift": 14}).schrift, 14)

    def test_unsinnige_schrift_bleibt_bei_der_vorgabe(self):
        self.assertEqual(self.leitstand({"schrift": 40}).schrift, 11)

    def test_takt_freigaben_immer_markt_nur_sichtbar(self):
        ls = self.leitstand()
        vorher = [r.aufrufe for r in ls.reiter]
        ls._takt()
        nachher = [r.aufrufe for r in ls.reiter]
        self.assertEqual(nachher, [vorher[0], vorher[1] + 1, vorher[2], vorher[3]])
        ls.kuerzel("<Control-Key-4>")
        self.root.update()
        vorher = [r.aufrufe for r in ls.reiter]
        ls._takt()
        nachher = [r.aufrufe for r in ls.reiter]
        self.assertEqual(nachher, [vorher[0], vorher[1] + 1, vorher[2], vorher[3] + 1])

    def test_statusleiste_zeigt_herz_zeit_status_und_meldung(self):
        ls = self.leitstand()
        ls.reiter[2].text = "Backtest: replay läuft seit 0:07"
        ls.melde("xperp scharf für 6:00 h")
        ls._takt()
        text = ls.w_status.cget("text")
        for teil in ("Dauerlauf läuft nicht", "aktualisiert 12:00:05",
                     "Backtest: replay läuft seit 0:07",
                     "xperp scharf für 6:00 h"):
            self.assertIn(teil, text)

    def test_fehler_eines_reiters_haelt_den_takt_nicht_an(self):
        ls = self.leitstand()
        def kaputt():
            raise ValueError("nicht lesbar")
        ls.reiter[1].refresh = kaputt
        ls._takt()
        self.assertIn("Freigaben: Fehler beim Auffrischen", ls.w_status.cget("text"))
        self.assertIn("aktualisiert 12:00:05", ls.w_status.cget("text"))

    def test_kuerzel_sind_gebunden_und_nur_diese(self):
        self.leitstand()
        for seq in lst.KUERZEL:
            self.assertTrue(self.root.bind(seq), seq)
        self.assertEqual(len(self.root.bind()), len(lst.KUERZEL))
        self.assertEqual({was for was, _arg in lst.KUERZEL.values()},
                         {"reiter", "auffrischen", "schrift"})

    def test_gueltige_lage_wird_uebernommen(self):
        x, y, _b, _h = lb.virtueller_schirm(self.root)
        geo = "900x700+%d+%d" % (x + 10, y + 10)
        with patch.object(self.root, "geometry") as g:
            self.leitstand({"geometrie": geo})
        g.assert_any_call(geo)

    def test_lage_ausserhalb_aller_schirme_wird_verworfen(self):
        geo = "900x700+-30000+-30000"
        with patch.object(self.root, "geometry") as g:
            self.leitstand({"geometrie": geo})
        self.assertNotIn(geo, [c.args[0] for c in g.call_args_list if c.args])
        g.assert_any_call(lst.start_lage(self.root.winfo_screenwidth(),
                                         self.root.winfo_screenheight()))

    def test_startlage_85_prozent_zentriert_nie_unter_minsize(self):
        self.assertEqual(lst.start_lage(2000, 1000), "1700x850+150+75")
        self.assertEqual(lst.start_lage(1024, 700), "1000x640+12+30")

    def test_schliessen_speichert_sofort_und_zerstoert(self):
        ls = self.leitstand()
        ls.kuerzel("<Control-Key-2>")
        self.root.update()
        self.assertTrue(ls.schliessen(frage=lambda *a, **k: self.fail("gefragt")))
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        self.assertEqual(daten["reiter"], 1)
        self.assertTrue(daten["geometrie"])
        with self.assertRaises(tk.TclError):
            self.root.winfo_exists()

    def test_schliessen_waehrend_urteile_eintragen_verweigert(self):
        ls = self.leitstand()
        ls.reiter[2].steuerung = lauf = FakeLauf()
        ls.reiter[2].abbrechbar = lambda: False
        self.assertFalse(ls.schliessen(frage=lambda *a, **k: self.fail("gefragt")))
        self.assertEqual(lauf.abgebrochen, 0)
        self.assertTrue(self.root.winfo_exists())
        self.assertIn("bitte warten", ls._meldung)

    def test_schliessen_bei_laufendem_backtest_fragt_erst(self):
        ls = self.leitstand()
        ls.reiter[2].steuerung = lauf = FakeLauf()
        self.assertFalse(ls.schliessen(frage=lambda *a, **k: False))
        self.assertEqual(lauf.abgebrochen, 0)
        self.assertTrue(self.root.winfo_exists())
        self.assertTrue(ls.schliessen(frage=lambda *a, **k: True))
        self.assertEqual(lauf.abgebrochen, 1)


class Echt(Basis):
    """Die vier echten Reiter, alles auf Temp-Dateien, kein Netz."""

    def setUp(self):
        super().setUp()
        t = Path(self.tmp.name)
        self.hz_refresh = self._ersetze(hz.Handelszentrale, "refresh")
        self._ersetze(hz.Handelszentrale, "_buero_im_bild")
        for ziel, name, wert in ((ff, "DATEI", t / "freigabe_fenster.json"),
                                 (ll, "ABLAGE", t / "ablage"),
                                 (lm, "BERICHTE", t / "berichte"),
                                 (lf, "blinken", lambda _root: False)):
            p = patch.object(ziel, name, wert)
            p.start()
            self.addCleanup(p.stop)

    def _ersetze(self, klasse, name):
        p = patch.object(klasse, name, autospec=True)
        m = p.start()
        self.addCleanup(p.stop)
        return m

    def test_vier_reiter_mit_ihren_titeln(self):
        ls = self.leitstand(reiter=None)
        self.assertEqual([ls.buch.tab(i, "text") for i in range(4)], list(TITEL))
        ls._takt()
        self.assertNotIn("Fehler", ls.w_status.cget("text"))

    def test_f5_im_ueberwachen_reiter_ruft_die_zentrale(self):
        ls = self.leitstand(reiter=None)
        vorher = self.hz_refresh.call_count
        ls.kuerzel("<F5>")
        self.assertEqual(self.hz_refresh.call_count, vorher + 1)

    def test_schrift_wirkt_auf_die_zentrale(self):
        ls = self.leitstand(reiter=None)
        ls.setze_schrift(14)
        self.assertEqual(hz.SCHRIFT_GROESSE, 14)
        self.assertEqual(ls.reiter[0].hz.w_schrift.get(), "14")

    def test_kein_widget_bindet_eine_ausloesende_taste(self):
        ls = self.leitstand(reiter=None)
        offen = list(self.root.winfo_children())
        while offen:
            w = offen.pop()
            offen.extend(w.winfo_children())
            for seq in w.bind():
                for taste in VERBOTENE_TASTEN:
                    self.assertNotIn(taste, seq, "%s bindet %s" % (w, seq))
        self.assertEqual(len(self.root.bind()), len(lst.KUERZEL))
        self.assertEqual(ls.sichtbarer_index(), 0)


class Herzschlag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.pid, self.log = t / "dauerlauf.pid", t / "dauerlauf.log"
        p = patch.object(hz, "dauerlauf_dateien",
                         lambda: (str(self.pid), str(self.log)))
        p.start()
        self.addCleanup(p.stop)

    def herz(self, lebt, minuten):
        with patch.object(hz, "prozess_lebt", return_value=lebt) as pl, \
                patch.object(hz, "dauerlauf_stand", return_value=("x", minuten)):
            text = lst.herzschlag(dt.datetime(2026, 9, 29, 12, 0, tzinfo=dt.timezone.utc))
        return text, pl

    def test_lebt_und_frisch(self):
        self.pid.write_text("1234", encoding="ascii")
        text, pl = self.herz(True, 5.0)
        self.assertEqual(text, "Dauerlauf läuft (letzter Zyklus vor 5 min)")
        pl.assert_called_once_with(1234)

    def test_lebt_aber_zu_lange_still(self):
        self.pid.write_text("1234", encoding="ascii")
        self.assertEqual(self.herz(True, 45.0)[0], "Dauerlauf läuft nicht")

    def test_prozess_nicht_abfragbar(self):
        self.pid.write_text("1234", encoding="ascii")
        self.assertEqual(self.herz(None, 5.0)[0], "Dauerlauf läuft nicht")

    def test_ohne_pid_datei(self):
        text, pl = self.herz(None, None)
        self.assertEqual(text, "Dauerlauf läuft nicht")
        pl.assert_called_once_with(None)

    def test_unlesbare_pid_datei(self):
        self.pid.write_text("kaputt", encoding="ascii")
        text, pl = self.herz(None, 5.0)
        self.assertEqual(text, "Dauerlauf läuft nicht")
        pl.assert_called_once_with(None)


class Lesepruefung(unittest.TestCase):
    def test_der_rahmen_schreibt_selbst_nichts(self):
        self.assertEqual(lesepruefung.schreibstellen(lst.__file__), [])

    def test_der_rahmen_startet_nichts_und_handelt_nicht(self):
        for modul in ("subprocess", "okx", "ccxt", "requests", "kraken",
                      "backtest_urteile"):
            self.assertFalse(lesepruefung.importiert(lst.__file__, modul), modul)


class PidDatei(unittest.TestCase):
    """Die Sperrdatei traegt ZWEI Felder - der Leser nahm die ganze Zeile.

    `sperre.py` schreibt `PID Zeitstempel`, damit ein Waechter eine verwaiste
    Sperre erkennt. `int()` auf die ganze Zeile scheitert still, `pid` wird
    None, und der Herzschlag meldet "laeuft nicht" fuer einen Lauf, der
    laeuft. Die Tests hier schrieben vorher selbst "1234" und konnten das
    echte Format deshalb nie sehen.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pfad = Path(self.tmp.name) / "dauerlauf.pid"

    def test_echtes_format_liefert_die_pid(self):
        self.pfad.write_text("27264 1791133901.9455156\n", encoding="ascii")
        self.assertEqual(lst.pid_aus_datei(self.pfad), 27264)

    def test_nur_pid_geht_auch(self):
        self.pfad.write_text("1234", encoding="ascii")
        self.assertEqual(lst.pid_aus_datei(self.pfad), 1234)

    def test_leere_und_fehlende_datei(self):
        self.assertIsNone(lst.pid_aus_datei(self.pfad))
        self.pfad.write_text("   \n", encoding="ascii")
        self.assertIsNone(lst.pid_aus_datei(self.pfad))

    def test_kaputter_inhalt_ist_none_statt_ausnahme(self):
        self.pfad.write_text("keine PID hier", encoding="ascii")
        self.assertIsNone(lst.pid_aus_datei(self.pfad))

    def test_herzschlag_sieht_den_lauf_mit_echtem_format(self):
        """Gegenprobe: mit der echten Datei meldet der Herzschlag 'laeuft'.

        Vor der Reparatur schrieb der Test '1234' und war gruen - genau
        deshalb blieb der Fehler drei Tage unentdeckt.
        """
        self.pfad.write_text("27264 1791133901.9455156\n", encoding="ascii")
        with patch.object(lst.hz, "dauerlauf_dateien",
                          return_value=(str(self.pfad), "woegal.log")), \
             patch.object(lst.hz, "prozess_lebt", return_value=True) as pl, \
             patch.object(lst.hz, "dauerlauf_stand",
                          return_value=("05.10. 00:20:57", 5.0)):
            text = lst.herzschlag(dt.datetime(2026, 10, 5, 0, 26,
                                              tzinfo=dt.timezone.utc))
        self.assertIn("läuft", text)
        self.assertIn("5 min", text)
        pl.assert_called_once_with(27264)


if __name__ == "__main__":
    unittest.main()
