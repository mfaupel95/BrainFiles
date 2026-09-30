"""Markt-Reiter: Bericht-Fixture wird angezeigt, fehlender oder kaputter
Bericht gibt einen Hinweis statt eines Absturzes, Alterswarnung ab 26 h,
Umschalter streng/weit.

Nur Temp-Dateien: kein echtes prognose_berichte/, kein Netz.

Direkt ausfuehrbar:  python tests/test_leitstand_markt.py
"""

import json
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitstand_bedienung as lb                               # noqa: E402
import leitstand_markt as lm                                   # noqa: E402

ERZEUGT = datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc)
TREFFER = {"inst": "ZEC-USDC", "richtung": "long", "preis": 1419.51, "score": 65.2,
           "chance": 81.5, "risiko": 28.6, "verhaeltnis": 2.85, "stop": 1249.1688,
           "ziel": 1696.69, "risiko_prozent": 12.0, "cr": 1.63,
           "kennzahlen": {"rsi14": 67.3}, "offene_tore": [], "guenstig": True,
           "umsatz_24h_usd": 12200137}
BERICHT = {
    "datum": "2026-09-29", "erzeugt": "2026-09-29T09:00:00+00:00",
    "tore": {"_mindest_score": "LONG: wie wachen.json", "mindest_score": 60,
             "hoechst_rsi": 55, "_hoechst_rsi": "nicht ueberhitzt"},
    "maerkte_geprueft": 65,
    "treffer": [TREFFER, dict(TREFFER, inst="FIL-USDT", score=61.0,
                              umsatz_24h_usd=11586398)],
    "werte": [],
}


class StubLeitstand:
    def __init__(self, root, zustand):
        self.root, self.zustand, self.meldungen = root, zustand, []
    def melde(self, text):
        self.meldungen.append(text)


class Rein(unittest.TestCase):
    def test_lade_bericht(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "neuester.json"
            self.assertEqual(lm.lade_bericht(p), (None, "fehlt"))
            p.write_text(json.dumps(BERICHT), encoding="utf-8")
            self.assertEqual(lm.lade_bericht(p), (BERICHT, ""))
            p.write_text("{kaputt", encoding="utf-8")
            self.assertEqual(lm.lade_bericht(p), (None, "nicht lesbar"))
            p.write_bytes(b"\xff\xfe\x00")
            self.assertEqual(lm.lade_bericht(p), (None, "nicht lesbar"))
            p.write_text(json.dumps(dict(BERICHT, treffer="viele")), encoding="utf-8")
            self.assertEqual(lm.lade_bericht(p), (None, "nicht lesbar"))
            p.write_text("[]", encoding="utf-8")
            self.assertEqual(lm.lade_bericht(p), (None, "nicht lesbar"))
            p.write_text("[" * 200000, encoding="utf-8")
            self.assertEqual(lm.lade_bericht(p), (None, "nicht lesbar"))

    def test_alter_und_warnung(self):
        self.assertEqual(lm.alter_h(BERICHT, ERZEUGT + timedelta(hours=3)), 3.0)
        self.assertEqual(lm.warnung(BERICHT, ERZEUGT + timedelta(hours=25, minutes=59)),
                         "")
        self.assertEqual(lm.warnung(BERICHT, ERZEUGT + timedelta(hours=26)),
                         "Bericht ist 26 h alt — der Dauerlauf hat keinen "
                         "neueren geschrieben")
        kaputt = dict(BERICHT, erzeugt="gestern")
        self.assertIsNone(lm.alter_h(kaputt, ERZEUGT))
        self.assertEqual(lm.warnung(kaputt, ERZEUGT),
                         "Erzeugungszeit nicht lesbar")
        ohne_zone = dict(BERICHT, erzeugt="2026-09-29T09:00:00")
        self.assertIsNone(lm.alter_h(ohne_zone, ERZEUGT))

    def test_zukunft(self):
        frueh = ERZEUGT - timedelta(hours=21)
        self.assertEqual(lm.warnung(BERICHT, frueh),
                         "Erzeugungszeit liegt in der Zukunft")
        self.assertEqual(lm.warnung(BERICHT, ERZEUGT - timedelta(minutes=5)), "")
        self.assertNotIn("-21", lm.kopfzeile(BERICHT, frueh))
        self.assertIn("erzeugt vor — · ", lm.kopfzeile(BERICHT, frueh))

    def test_kopfzeile(self):
        self.assertEqual(lm.kopfzeile(BERICHT, ERZEUGT + timedelta(hours=3)),
                         "Bericht vom 2026-09-29 · erzeugt vor 3.0 h · "
                         "65 Märkte geprüft · 2 Treffer")

    def test_treffer_zeilen(self):
        zeilen = lm.treffer_zeilen(BERICHT)
        self.assertEqual(len(zeilen), 2)
        self.assertEqual(len(zeilen[0]), len(lm.TREFFER_FELDER))
        self.assertEqual(zeilen[0][:3], ("ZEC-USDC", "long", 1419.51))
        ohne = lm.treffer_zeilen(dict(BERICHT, treffer=[{"inst": "X"}, "kaputt"]))
        self.assertEqual(ohne, [("X",) + ("—",) * (len(lm.TREFFER_FELDER) - 1)])

    def test_tore_zeilen(self):
        self.assertEqual(lm.tore_zeilen(BERICHT), [
            ("hoechst_rsi", 55, "nicht ueberhitzt"),
            ("mindest_score", 60, "LONG: wie wachen.json")])
        self.assertEqual(lm.tore_zeilen(dict(BERICHT, tore="kaputt")), [])


def _alle(w):
    for k in w.winfo_children():
        yield k
        yield from _alle(k)


class Reiter(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ordner = Path(self.tmp.name) / "prognose_berichte"
        self.ordner.mkdir()
        self.ls = StubLeitstand(self.root, lb.Zustand(Path(self.tmp.name) / "z.json"))
        self.jetzt = ERZEUGT + timedelta(hours=3)

    def _bericht(self, name, daten):
        text = daten if isinstance(daten, str) else json.dumps(daten)
        (self.ordner / name).write_text(text, encoding="utf-8")

    def _reiter(self):
        r = lm.MarktReiter(self.root, self.ls, ordner=self.ordner,
                           uhr=lambda: self.jetzt)
        self.root.update_idletasks()
        return r

    def test_kopf_warnung_und_tabellen_getrennt(self):
        self._bericht("neuester.json", BERICHT)
        r = self._reiter()
        self.assertEqual(str(r.w_kopf.cget("style")), "Kopf.TLabel")
        texte = [str(k.cget("text")) for k in _alle(r) if isinstance(k, ttk.Label)]
        self.assertIn("Treffer", texte)
        self.assertIn("Tore", texte)

    def test_bericht_wird_angezeigt(self):
        self._bericht("neuester.json", BERICHT)
        r = self._reiter()
        self.assertIn("65 Märkte geprüft", r.w_kopf.cget("text"))
        self.assertEqual(r.w_warnung.cget("text"), "")
        self.assertEqual(len(r.treffer.sichtbare()), 2)
        self.assertEqual(len(r.tore.sichtbare()), 2)
        self.assertEqual(r.titel_zusatz(), "")
        self.assertEqual(r.status(), "")

    def test_status_meldet_zukunft_und_unlesbare_zeit(self):
        self._bericht("neuester.json", BERICHT)
        r = self._reiter()
        self.jetzt = ERZEUGT - timedelta(hours=21)
        r.refresh()
        self.assertEqual(r.status(), "Erzeugungszeit liegt in der Zukunft")
        self._bericht("neuester.json", dict(BERICHT, erzeugt="gestern"))
        r.refresh()
        self.assertEqual(r.status(), "Erzeugungszeit nicht lesbar")

    def test_fehlender_bericht_gibt_hinweis(self):
        r = self._reiter()
        self.assertEqual(r.w_kopf.cget("text"),
                         "Kein Marktbericht: neuester.json fehlt — ihn schreibt "
                         "der Dauerlauf (prognose.py)")
        self.assertEqual(r.treffer.sichtbare(), [])

    def test_unlesbarer_bericht_gibt_hinweis(self):
        self._bericht("neuester.json", "{kaputt")
        r = self._reiter()
        self.assertEqual(r.w_kopf.cget("text"), "Marktbericht nicht lesbar: neuester.json")
        self.assertEqual(r.treffer.sichtbare(), [])
        self.assertEqual(r.tore.sichtbare(), [])

    def test_alterswarnung_ab_26_h(self):
        self._bericht("neuester.json", BERICHT)
        r = self._reiter()
        self.jetzt = ERZEUGT + timedelta(hours=26)
        r.refresh()
        self.assertEqual(r.w_warnung.cget("text"),
                         "Bericht ist 26 h alt — der Dauerlauf hat keinen "
                         "neueren geschrieben")
        self.assertEqual(r.status(), "Marktbericht 26 h alt")

    def test_umschalter_streng_weit(self):
        self._bericht("neuester.json", dict(BERICHT, treffer=[]))
        self._bericht("neuester.weit.json", BERICHT)
        r = self._reiter()
        self.assertNotIn("disabled", r.r_weit.state())
        self.assertEqual(r.treffer.sichtbare(), [])
        r.fassung.set("weit")
        r.umschalten()
        self.assertEqual(len(r.treffer.sichtbare()), 2)
        self.assertEqual(self.ls.zustand.get("werte")["markt_fassung"], "weit")

    def test_ohne_weiten_bericht_ist_weit_gesperrt(self):
        self._bericht("neuester.json", BERICHT)
        r = self._reiter()
        self.assertIn("disabled", r.r_weit.state())
        self.assertEqual(r.tip_weit.text, "kein neuester.weit.json")

    def test_gemerkte_fassung_ohne_datei_faellt_auf_streng(self):
        self.ls.zustand.merke_in("werte", "markt_fassung", "weit")
        self._bericht("neuester.json", BERICHT)
        r = self._reiter()
        self.assertEqual(r.fassung.get(), "streng")
        self.assertEqual(len(r.treffer.sichtbare()), 2)


if __name__ == "__main__":
    unittest.main()
