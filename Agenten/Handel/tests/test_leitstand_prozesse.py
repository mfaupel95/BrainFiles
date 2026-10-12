"""Kraken quote Nodes und vollstaendige, rein lesende Spurensicht."""
import datetime as dt
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dauerlauf
import handelszentrale as hz
import leitstand_prozesse as lp


class KrakenQuoteNodes(unittest.TestCase):
    def test_spot_und_futures_sind_explizite_read_only_nodes(self):
        nodes = [p for p in lp.PROZESSE if getattr(p, "produkt", None)]
        self.assertEqual([p.produkt for p in nodes], ["spot", "futures"])
        self.assertTrue(all(p.read_only for p in nodes))

    def test_veraltete_pid_datei_findet_node_per_scan(self):
        node = next(p for p in lp.PROZESSE if getattr(p, "produkt", None) == "spot")

        def proc(pid, ppid, produkt):
            m = unittest.mock.MagicMock(pid=pid)
            m.ppid.return_value = ppid
            m.cmdline.return_value = ["python.exe", str(lp._KRAKEN_NODE)]
            m.environ.return_value = {"KRAKEN_PRODUKT": produkt} if produkt else {}
            return m

        launcher, kind, fremd = proc(19412, 1, None), proc(66816, 19412, None), proc(5, 1, "futures")
        with tempfile.TemporaryDirectory() as tmp:
            node._prozess = None
            node._pid_pfad = Path(tmp) / "node.pid"
            node._pid_pfad.write_text("101976\n", encoding="ascii")
            with patch.object(lp.hz, "prozess_lebt", return_value=False),                  patch.object(lp.psutil, "process_iter", return_value=[fremd, kind, launcher]):
                self.assertTrue(node.laeuft())
            self.assertEqual(node._pid_pfad.read_text(encoding="ascii").strip(), "19412")
            with patch.object(lp.hz, "prozess_lebt", return_value=False),                  patch.object(lp.psutil, "process_iter", return_value=[fremd]):
                self.assertFalse(node.laeuft())

    def test_zusatz_zeigt_papier_pnl_oder_nichts(self):
        node = next(p for p in lp.PROZESSE if getattr(p, "produkt", None) == "spot")
        with patch.object(lp, "lese_papierstand", return_value=None):
            self.assertEqual(node.zusatz(), "")
        stand = {"realisiert": 3.5, "unrealisiert": -1.25, "trades": 2}
        with patch.object(lp, "lese_papierstand", return_value=stand):
            self.assertEqual(node.zusatz(), "PnL +2.25 (2 Trades)")

    def test_spot_start_uebergibt_produkt_symbol_und_keinen_order_client(self):
        node = next(p for p in lp.PROZESSE if getattr(p, "produkt", None) == "spot")
        with patch.object(type(node), "laeuft", return_value=False), patch.object(lp.subprocess, "Popen") as popen:
            node.starten()
        args, kwargs = popen.call_args
        self.assertIn("run_kraken_paper_node.py", args[0][1])
        self.assertEqual(kwargs["env"]["KRAKEN_PRODUKT"], "spot")
        self.assertEqual(kwargs["env"]["KRAKEN_SYMBOL"], "BTC/EUR")
        self.assertEqual(kwargs["env"]["NAUTILUS_MIT_ORDER"], "")

    def test_node_erkennt_prozess_aus_vorheriger_leitstand_sitzung(self):
        node = next(p for p in lp.PROZESSE if getattr(p, "produkt", None) == "spot")
        with tempfile.TemporaryDirectory() as tmp:
            node._pid_pfad = Path(tmp) / "node.pid"
            node._pid_pfad.write_text("43210\n", encoding="ascii")
            with patch.object(lp.hz, "prozess_lebt", return_value=True) as lebt,                  patch.object(lp.psutil, "Process") as process:
                process.return_value.exe.return_value = str(lp._NAUTILUS_PY)
                process.return_value.cmdline.return_value = [str(lp._NAUTILUS_PY), str(lp._KRAKEN_NODE)]
                process.return_value.environ.return_value = {"KRAKEN_PRODUKT": "spot"}
                self.assertTrue(node.laeuft())
            lebt.assert_called_once_with(43210)

    def test_persistierte_pid_wird_nur_bei_identischem_node_akzeptiert(self):
        node = next(p for p in lp.PROZESSE if getattr(p, "produkt", None) == "spot")
        with tempfile.TemporaryDirectory() as tmp:
            node._pid_pfad = Path(tmp) / "node.pid"
            node._pid_pfad.write_text("43210\n", encoding="ascii")
            with patch.object(lp.hz, "prozess_lebt", return_value=True),                  patch.object(lp.psutil, "Process") as process:
                process.return_value.exe.return_value = str(lp._NAUTILUS_PY)
                process.return_value.cmdline.return_value = [str(lp._NAUTILUS_PY), str(lp._KRAKEN_NODE)]
                process.return_value.environ.return_value = {"KRAKEN_PRODUKT": "spot"}
                self.assertTrue(node.laeuft())
                process.return_value.cmdline.return_value = ["unrelated.exe"]
                self.assertFalse(node.laeuft())

    def test_quote_node_vererbt_keine_kraken_credentials(self):
        node = next(p for p in lp.PROZESSE if getattr(p, "produkt", None) == "spot")
        secrets = {"KRAKEN_SPOT_API_KEY": "secret", "KRAKEN_SPOT_API_SECRET": "secret",
                   "KRAKEN_FUTURES_DEMO_API_KEY": "secret",
                   "KRAKEN_FUTURES_DEMO_API_SECRET": "secret"}
        with patch.dict(lp.os.environ, secrets), patch.object(type(node), "laeuft", return_value=False), patch.object(lp.subprocess, "Popen") as popen:
            node.starten()
        child_env = popen.call_args.kwargs["env"]
        self.assertFalse(set(secrets) & set(child_env))

    def test_futures_start_uebergibt_pf_solusd_und_keinen_order_client(self):
        node = next(p for p in lp.PROZESSE if getattr(p, "produkt", None) == "futures")
        # laeuft() fest auf False: sonst entscheidet ein echter, evtl. noch
        # lebender Node aus einer frueheren Sitzung, ob Popen aufgerufen wird.
        with patch.object(type(node), "laeuft", return_value=False), \
             patch.object(lp.subprocess, "Popen") as popen:
            node.starten()
        _, kwargs = popen.call_args
        self.assertEqual(kwargs["env"]["KRAKEN_PRODUKT"], "futures")
        self.assertEqual(kwargs["env"]["KRAKEN_SYMBOL"], "PF_SOLUSD")
        self.assertEqual(kwargs["env"]["NAUTILUS_MIT_ORDER"], "")


class SpurStatus(unittest.TestCase):
    def test_statusliste_nutzt_alle_spuren_und_zeigt_heartbeat(self):
        now = dt.datetime(2026, 10, 10, 20, 0, tzinfo=dt.timezone.utc)
        spuren = {"demo": {"ordner": "spur-demo", "waehrung": "USD"}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "spur-demo").mkdir()
            (root / "spur-demo" / "zustand.json").write_text(
                json.dumps({"letzter_lauf": "2026-10-10T19:50:00+00:00", "positionen": [{}]}),
                encoding="utf-8")
            (root / "spur-demo" / "wachen.json").write_text(
                json.dumps({"herzschlag_max_minuten": 30}), encoding="utf-8")
            with patch.object(hz, "SPUREN", list(spuren)), \
                 patch.object(dauerlauf, "SPUREN", spuren), \
                 patch.object(lp, "HIER", root):
                rows = lp.spuren_status(jetzt=now)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["spur"], "demo")
        self.assertEqual(rows[0]["herzschlag"], "ok")
        self.assertEqual(rows[0]["positionen"], 1)


    def test_spuren_status_format_zeigt_unbekannt_und_positionszahl(self):
        zeilen = [
            {"spur": "nautilus_kraken", "modus": "papier", "herzschlag": "ok",
             "alter_minuten": 5, "positionen": 2, "handel_erlaubt": False},
            {"spur": "scanner", "modus": "-", "herzschlag": "unbekannt",
             "alter_minuten": None, "positionen": 0, "handel_erlaubt": True},
        ]
        text = lp.formatiere_spuren_status(zeilen)
        self.assertIn("nautilus_kraken", text)
        self.assertIn("ok (5 min)", text)
        self.assertIn("unbekannt", text)
        self.assertIn("scanner", text)
        self.assertIn("HANDEL_ERLAUBT", text)
        self.assertNotIn(" LIVE", text)

    def test_statusliste_enthaelt_alle_navi_spuren_aus_der_einen_spurliste(self):
        erwartet = {"nautilus", "nautilus_kraken", "nautilus_kraken_futures",
                    "nautilus_emacross"}
        self.assertTrue(erwartet.issubset(set(dauerlauf.SPUREN)))
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(lp, "HIER", Path(tmp)):
                rows = lp.spuren_status()
        self.assertEqual({r["spur"] for r in rows}, set(dauerlauf.SPUREN))

    def test_filter_spuren_zeigt_nur_nautilus_familie_oder_alle(self):
        zeilen = [{"spur": n, "modus": "-", "herzschlag": "unbekannt",
                   "alter_minuten": None, "positionen": 0, "handel_erlaubt": False}
                  for n in ("nautilus", "nautilus_kraken", "scanner")]
        naut = lp.filter_spuren(zeilen, "Nautilus")
        self.assertEqual([r["spur"] for r in naut], ["nautilus", "nautilus_kraken"])
        self.assertEqual(len(lp.filter_spuren(zeilen, "Alle")), 3)

    def test_futures_spur_liest_eigene_zustand_und_wachen_datei(self):
        now = dt.datetime(2026, 10, 10, 20, 0, tzinfo=dt.timezone.utc)
        spuren = {
            "nautilus_kraken": {"ordner": "shared"},
            "nautilus_kraken_futures": {"ordner": "shared", "skript": "handeln_futures.py"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "shared"
            folder.mkdir()
            (folder / "zustand.json").write_text(json.dumps({
                "modus": "spot", "letzter_lauf": "2026-10-10T19:59:00+00:00", "positionen": []}), encoding="utf-8")
            (folder / "wachen.json").write_text(json.dumps({"herzschlag_max_minuten": 30}), encoding="utf-8")
            (folder / "zustand.futures.json").write_text(json.dumps({
                "modus": "futures", "letzter_lauf": "2026-10-10T19:50:00+00:00", "positionen": [{}]}), encoding="utf-8")
            (folder / "wachen.futures.json").write_text(json.dumps({"herzschlag_max_minuten": 30}), encoding="utf-8")
            with patch.object(hz, "SPUREN", list(spuren)),                  patch.object(dauerlauf, "SPUREN", spuren),                  patch.object(lp, "HIER", root):
                rows = lp.spuren_status(jetzt=now)
        futures = next(r for r in rows if r["spur"] == "nautilus_kraken_futures")
        self.assertEqual(futures["modus"], "futures")
        self.assertEqual(futures["positionen"], 1)
        self.assertEqual(futures["alter_minuten"], 10)

    def test_fehlende_dateien_werden_als_unbekannt_gezeigt_nicht_ausgelassen(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(hz, "SPUREN", ["missing"]), \
                 patch.object(dauerlauf, "SPUREN", {"missing": {"ordner": "nope"}}), \
                 patch.object(lp, "HIER", Path(tmp)):
                rows = lp.spuren_status()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["herzschlag"], "unbekannt")

    def test_modus_faellt_auf_positionen_zurueck_wenn_oben_fehlt(self):
        self.assertEqual(lp._modus_der_spur({"positionen": [{"modus": "live"}]}), "live")
        self.assertEqual(lp._modus_der_spur({"modus": "papier", "positionen": [{"modus": "live"}]}), "papier")
        self.assertEqual(lp._modus_der_spur({}), "-")


class ProzessReiterUI(unittest.TestCase):
    def test_statusfilter_zeigt_nautilus_oder_alle_spuren(self):
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        root.withdraw()
        self.addCleanup(root.destroy)

        class StubProzess:
            name = "stub"
            def laeuft(self): return False
            def starten(self): pass
            def stoppen(self): pass

        rows = [
            {"spur": "nautilus_kraken", "modus": "papier", "herzschlag": "ok",
             "alter_minuten": 5, "positionen": 0, "handel_erlaubt": False},
            {"spur": "scanner", "modus": "live", "herzschlag": "ok",
             "alter_minuten": 2, "positionen": 1, "handel_erlaubt": True},
        ]
        with patch.object(lp, "PROZESSE", [StubProzess()]),              patch.object(lp, "spuren_status", return_value=rows):
            view = lp.ProzessReiter(root, object())
            text = view._spur_text.get("1.0", "end")
            # Standard ist "Alle" - sonst fehlen 40 von 45 Spuren.
            self.assertIn("nautilus_kraken", text)
            self.assertIn("scanner", text)
            view._spur_filter.set("Nautilus")
            view._zeige_spuren()
            text = view._spur_text.get("1.0", "end")
            self.assertIn("nautilus_kraken", text)
            self.assertNotIn("scanner", text)



if __name__ == "__main__":
    unittest.main()
