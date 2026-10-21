"""FreqTrade-Reiter im Leitstand: Tabelle aller Bots, nur lesend, blockiert nie.

Direkt ausfuehrbar:  python tests/test_leitstand_freqtrade.py
"""

import sys
import tempfile
import threading
import time
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitstand as lst                                        # noqa: E402
import leitstand_freqtrade as lf                               # noqa: E402

BOTS = [{"name": "klassik-ema", "port": 8085, "hausspur": "klassik_ema"},
        {"name": "trading-agent", "port": 8081}]
UEB = [{"name": "klassik-ema", "port": 8085, "erreichbar": True, "dry_run": True,
        "zustand": "running", "offen": 1, "trades": 12, "gewinn": -3.5, "fehler": ""},
       {"name": "trading-agent", "port": 8081, "erreichbar": False, "dry_run": None,
        "zustand": "?", "offen": None, "trades": None, "gewinn": None,
        "fehler": "Verbindung abgelehnt"}]


class Reinfunktionen(unittest.TestCase):
    def test_zeilen(self):
        z = lf.zeilen(UEB, BOTS, {"klassik-ema": {"runden": 40, "netto_prozent": -2.5,
                                                  "stand": "2026-10-10T20:00:00+00:00"}})
        self.assertEqual(z[0], ("klassik-ema", "klassik_ema", "läuft", "1", "12",
                                "-3.50", "-2.50 % / 40 R (10.10.)"))
        self.assertEqual(z[1][1], "MoonDev")

    def test_taube_bots_mit_grund(self):
        z = lf.zeilen(UEB, BOTS, {})
        self.assertEqual(z[1][2], "taub: Verbindung abgelehnt")
        self.assertEqual(lf.status_text(UEB), "FreqTrade: 1 taub (trading-agent)")
        self.assertEqual(lf.titel(UEB), " (1/2)")
        self.assertEqual(lf.titel([]), "")

    def test_urteile_fehlen_oder_kaputt(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(lf.lade_urteile(Path(d) / "fehlt.json"), {})
            kaputt = Path(d) / "kaputt.json"
            kaputt.write_text("{nicht json", encoding="utf-8")
            self.assertEqual(lf.lade_urteile(kaputt), {})
        self.assertEqual(lf.zeilen(UEB, BOTS, {})[0][6], "—")

    def test_spur_kommt_durch_die_bruecke(self):
        """Die Spalte Spur liest bots() der Bruecke - die muss hausspur tragen."""
        import json
        import freqtrade_bridge as fb
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bots.json"
            p.write_text(json.dumps({"bots": [{"name": "klassik-ema", "port": 8085,
                                               "hausspur": "klassik_ema"}]}),
                         encoding="utf-8")
            self.assertEqual(lf.zeilen(UEB[:1], fb.bots(str(p)), {})[0][1], "klassik_ema")

    def test_kaputtes_urteil_wirft_nicht(self):
        # Review M10d: urteile.json ist Fremdtext, der Tk-Hauptthread darf nicht fallen.
        for u in ("kaputt", 5, ["x"], {"netto_prozent": "abc"}):
            self.assertEqual(lf._backtest_text(u), "?", u)

    def test_live_bot_faellt_auf(self):
        live = [dict(UEB[0], dry_run=False)]
        self.assertTrue(lf.zeilen(live, BOTS, {})[0][2].startswith("LIVE!"))


class Reiter(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_refresh_blockiert_nicht(self):
        freigabe = threading.Event()

        def langsam(**_kw):
            freigabe.wait(5)
            return UEB
        r = lf.FreqtradeReiter(self.root, None, quelle=langsam,
                               bot_quelle=lambda: BOTS,
                               urteile_pfad=Path("gibtsnicht.json"))
        t0 = time.monotonic()
        r.refresh()
        self.assertLess(time.monotonic() - t0, 0.5)
        freigabe.set()
        ende = time.monotonic() + 5
        while time.monotonic() < ende and not r.tabelle.get_children():
            self.root.update()
            time.sleep(0.02)
        self.assertEqual(len(r.tabelle.get_children()), 2)
        self.assertEqual(r.titel_zusatz(), " (1/2)")

    def _warte(self, bedingung, sek=5):
        ende = time.monotonic() + sek
        while time.monotonic() < ende and not bedingung():
            self.root.update()
            time.sleep(0.02)

    def _reiter(self, detail):
        r = lf.FreqtradeReiter(self.root, None, quelle=lambda **_kw: UEB,
                               bot_quelle=lambda: BOTS, detail_quelle=detail,
                               urteile_pfad=Path("gibtsnicht.json"))
        r.refresh()
        self._warte(lambda: r.tabelle.get_children())
        return r

    def test_auswahl_waehrend_abfrage_wird_nachgeholt(self):
        # Review M10a: unter Bot B duerfen nicht die Trades von Bot A stehen.
        freigabe = threading.Event()
        gefragt = []

        def detail(bot):
            gefragt.append(bot["name"])
            if bot["name"] == "klassik-ema":
                freigabe.wait(5)
            return [], [{"pair": bot["name"], "is_open": False}]
        r = self._reiter(detail)
        r.tabelle.selection_set("klassik-ema")
        self._warte(lambda: gefragt)
        r.tabelle.selection_set("trading-agent")
        self.root.update()
        freigabe.set()
        self._warte(lambda: gefragt[-1:] == ["trading-agent"] and not r._detail_laeuft)
        self.assertEqual(gefragt, ["klassik-ema", "trading-agent"])

    def test_gescheiterte_abfrage_sagt_es(self):
        # Review M10b: keine stumm geleerte Tabelle.
        def detail(_bot):
            raise OSError("Zeitgrenze")
        r = self._reiter(detail)
        r.tabelle.selection_set("klassik-ema")
        self._warte(lambda: r.offen.get_children())
        werte = r.offen.item(r.offen.get_children()[0], "values")
        self.assertIn("Zeitgrenze", " ".join(str(w) for w in werte))

    def test_detail_mit_kurzer_zeitgrenze(self):
        # Review M10c: 4 s wie die Uebersicht, nicht ZEITGRENZE der Bruecke.
        self.assertEqual(lf.DETAIL_ZEITGRENZE, 4)

    def test_nach_zerstoeren_kein_fehler(self):
        # Review M10e: ein spaetes Ergebnis trifft kein zerstoertes Widget.
        freigabe = threading.Event()

        def langsam(**_kw):
            freigabe.wait(5)
            return UEB
        r = lf.FreqtradeReiter(self.root, None, quelle=langsam,
                               bot_quelle=lambda: BOTS,
                               urteile_pfad=Path("gibtsnicht.json"))
        fehler = []
        self.root.report_callback_exception = lambda *a: fehler.append(a[1])
        r.refresh()
        r.destroy()
        freigabe.set()
        time.sleep(0.3)
        self.root.update()
        self.assertEqual(fehler, [])

    def test_im_leitstand_eingetragen(self):
        titel = [t for t, _k in lst.REITER]
        self.assertIn("FreqTrade", titel)
        self.assertIn("FreqTrade", lst.TAKT_SICHTBAR)
        self.assertIn("<Control-Key-8>", lst.KUERZEL)

    def test_schreibt_und_startet_nichts(self):
        quelle = Path(lf.__file__).read_text(encoding="utf-8")
        for verboten in ("forceenter", "forceexit", "subprocess", "bots.py start",
                         ".write_text(", "open(", "docker"):
            self.assertNotIn(verboten, quelle, verboten)


if __name__ == "__main__":
    unittest.main()
