"""bots.py fuer HausSpur-Bots: Mount, Futures, Speichergrenze.

Direkt ausfuehrbar:  python freqtrade/tests/test_bots_hausspur.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bots                                                    # noqa: E402

HAUSBOT = {"name": "klassik-ema", "container": "freqtrade-klassik-ema",
           "strategie": "HausSpur", "hausspur": "klassik_ema", "port": 8085,
           "zeitrahmen": "4h", "max_open_trades": 3,
           "whitelist": ["BTC/USDT:USDT"]}
MOONBOT = {"name": "trading-agent", "container": "freqtrade-trading-agent",
           "strategie": "MoonDevTradingAgent", "port": 8081,
           "zeitrahmen": "1h", "whitelist": ["BTC/USDT"]}


class Config(unittest.TestCase):
    def test_hausspur_ist_futures_mit_name(self):
        c = bots.config_fuer(HAUSBOT)
        self.assertEqual(c["trading_mode"], "futures")
        self.assertEqual(c["margin_mode"], "isolated")
        self.assertEqual(c["hausspur"], {"name": "klassik_ema",
                                         "pfad": "/agenten/Handel"})
        self.assertTrue(c["dry_run"])

    def test_moondev_bleibt_spot(self):
        c = bots.config_fuer(MOONBOT)
        self.assertEqual(c["trading_mode"], "spot")
        self.assertNotIn("hausspur", c)


class Mounts(unittest.TestCase):
    def test_haus_nur_lesend_bei_hausspur(self):
        m = bots.mounts(HAUSBOT)
        handel = (bots.HAUS / "Handel").resolve().as_posix()
        self.assertIn(f"{handel}:/agenten/Handel:ro", m)
        self.assertIn(f"{(bots.HAUS / 'Bus').resolve().as_posix()}:/agenten/Bus:ro", m)
        self.assertNotIn("/agenten", " ".join(bots.mounts(MOONBOT)))

    def test_nicht_ganz_agenten(self):
        """Review I1: Hermes/.env & Co. duerfen nicht im Fremd-Image landen."""
        text = " ".join(bots.mounts(HAUSBOT))
        self.assertNotIn(f"{bots.HAUS.resolve().as_posix()}:/agenten:ro", text)

    def test_fremde_handelsordner_ueberdeckt(self):
        """Review I1: ai4trade/.env, OpenAlice/sealing.key liegen unter Handel/.

        Eigener Baum statt des echten: OpenAlice/ ist unversioniert und fehlt
        in einem frischen Klon - die Regel muss trotzdem greifen.
        """
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            for o in ("ai4trade", "OpenAlice", "freqtrade", "klassik_ema",
                      "scanner", "xperp", ".venv", "__pycache__"):
                (Path(d) / "Handel" / o).mkdir(parents=True)
            (Path(d) / "Bus").mkdir()
            with patch.object(bots, "HAUS", Path(d)), \
                    patch.object(bots, "bots", lambda: [HAUSBOT]):
                text = " ".join(bots.mounts(HAUSBOT)) + " "
        for geheim in ("ai4trade", "OpenAlice", "freqtrade"):
            self.assertIn(f"type=tmpfs,destination=/agenten/Handel/{geheim} ", text)
        for noetig in ("klassik_ema", "scanner", "xperp", ".venv", "__pycache__"):
            self.assertNotIn(f"destination=/agenten/Handel/{noetig} ", text)

    def test_download_ohne_haus(self):
        self.assertNotIn("/agenten", " ".join(bots._daten_fenster(["BTC/USDT:USDT"], "4h", True)))

    def test_start_mit_speichergrenze_und_mount(self):
        aufrufe = []

        def falsch_docker(args):
            aufrufe.append(args)

            class R:
                returncode, stdout, stderr = 0, "", ""
            return R()
        with patch.object(bots, "docker", falsch_docker), \
                patch.object(bots, "container_laeuft", lambda n: False), \
                patch.object(Path, "exists", lambda self: True), \
                patch.object(bots, "ausgewaehlt", lambda a: [HAUSBOT]):
            bots.cmd_start(["klassik-ema"])
        run = [a for a in aufrufe if a and a[0] == "run"][0]
        self.assertIn("--memory", run)
        self.assertEqual(run[run.index("--memory") + 1], "700m")
        self.assertIn(f"{(bots.HAUS / 'Handel').resolve().as_posix()}:/agenten/Handel:ro", run)
        self.assertIn("127.0.0.1:8085:8085", run)

    def test_speicher_je_bot(self):
        # Review M7: ein breiter Moon-Dev-Bot darf mehr bekommen als die Vorgabe.
        aufrufe = []

        def falsch_docker(args):
            aufrufe.append(args)

            class R:
                returncode, stdout, stderr = 0, "", ""
            return R()
        with patch.object(bots, "docker", falsch_docker),                 patch.object(bots, "container_laeuft", lambda n: False),                 patch.object(Path, "exists", lambda self: True),                 patch.object(bots, "ausgewaehlt", lambda a: [dict(HAUSBOT, speicher="1200m")]):
            bots.cmd_start(["klassik-ema"])
        run = [a for a in aufrufe if a and a[0] == "run"][0]
        self.assertEqual(run[run.index("--memory") + 1], "1200m")


class BacktestUrteil(unittest.TestCase):
    """Review I2: ein gescheiterter Lauf darf kein fremdes Urteil erben."""

    def _lauf(self, rc, zeiger_vorher, zeiger_nachher, timerange=None):
        gemerkt = []
        zeiger = iter([zeiger_vorher, zeiger_nachher])
        with patch.object(bots, "einweglauf", lambda f, b: rc), \
                patch.object(bots, "ausgewaehlt", lambda a: [HAUSBOT]), \
                patch.object(bots, "_letzter_zeiger", lambda: next(zeiger)), \
                patch.object(bots, "letztes_ergebnis", lambda: ERGEBNIS), \
                patch.object(bots, "urteil_merken", lambda n, u: gemerkt.append(n)):
            bots.cmd_backtest(["klassik-ema"], timerange)
        return gemerkt

    def test_erfolg_wird_gemerkt(self):
        self.assertEqual(self._lauf(0, "a.zip", "b.zip"), ["klassik-ema"])

    def test_gescheitert_nicht(self):
        self.assertEqual(self._lauf(1, "a.zip", "b.zip"), [])

    def test_kein_neues_ergebnis_nicht(self):
        self.assertEqual(self._lauf(0, "a.zip", "a.zip"), [])

    def test_schutzschicht_im_backtest(self):
        # Review M6: StoplossGuard/MaxDrawdown wirken live - im Backtest auch.
        fenster = []
        with patch.object(bots, "einweglauf", lambda f, b: fenster.append(f) or 1),                 patch.object(bots, "ausgewaehlt", lambda a: [HAUSBOT]),                 patch.object(bots, "_letzter_zeiger", lambda: None):
            bots.cmd_backtest(["klassik-ema"])
        self.assertIn("--enable-protections", fenster[0])

    def test_teilzeitraum_nicht(self):
        self.assertEqual(self._lauf(0, "a.zip", "b.zip", timerange="20260101-"), [])


class Daten(unittest.TestCase):
    def test_download_nennt_boerse_und_modus(self):
        f = bots._daten_fenster(["BTC/USDT:USDT"], "4h", True)
        self.assertEqual(f[f.index("--exchange") + 1], "binance")
        self.assertEqual(f[f.index("--trading-mode") + 1], "futures")


class Strategie(unittest.TestCase):
    QUELLE = (Path(bots.STRATEGIEN) / "HausSpur.py")

    def test_datei_da_und_ohne_regelkopie(self):
        text = self.QUELLE.read_text(encoding="utf-8")
        self.assertIn("class HausSpur(IStrategy)", text)
        self.assertIn("hausspur_regeln", text)
        for verboten in ("def einstieg_", "ta.EMA", "rolling("):
            self.assertNotIn(verboten, text)

    def test_unbekannte_spur_nennt_namen(self):
        text = self.QUELLE.read_text(encoding="utf-8")
        self.assertIn("OperationalException", text)


HANDEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HANDEL))
import hausspur_regeln as hr                                   # noqa: E402


class Manifest(unittest.TestCase):
    def setUp(self):
        self.alle = bots.bots()
        self.haus = [b for b in self.alle if b.get("hausspur")]

    def test_siebzehn_hausspuren(self):
        self.assertEqual(sorted(b["hausspur"] for b in self.haus), sorted(hr.ALLE))

    def test_ports_und_container_eindeutig(self):
        ports = [b["port"] for b in self.alle]
        self.assertEqual(len(ports), len(set(ports)))
        self.assertEqual(sorted(b["port"] for b in self.haus), list(range(8084, 8101)))
        self.assertEqual(len({b["container"] for b in self.alle}), len(self.alle))

    def test_zeitrahmen_und_paare_wie_wachen(self):
        for b in self.haus:
            self.assertEqual(b["zeitrahmen"], hr.zeitrahmen(b["hausspur"]), b["name"])
            haus = hr.paare(b["hausspur"])
            if b.get("_whitelist_vermerk"):
                # Auftrag Max 11.10.2026: Breite 3 -> 10 Paare, Hauspaare vorn,
                # gleichzeitig offen bleiben so viele wie im Haus.
                self.assertEqual(len(b["whitelist"]), 10, b["name"])
                self.assertEqual(b["whitelist"][:len(haus)], haus, b["name"])
                self.assertEqual(len(set(b["whitelist"])), 10, b["name"])
                self.assertEqual(b["max_open_trades"], len(haus), b["name"])
            else:
                self.assertEqual(b["whitelist"], haus, b["name"])
                self.assertEqual(b["max_open_trades"], len(b["whitelist"]))
            self.assertEqual(b["strategie"], "HausSpur")


ERGEBNIS = {"strategy": {"HausSpur": {
    "total_trades": 42, "profit_total": -0.0312, "max_drawdown_account": 0.081,
    "backtest_start": "2024-10-01 00:00:00", "backtest_end": "2026-10-01 00:00:00"}}}


class Urteile(unittest.TestCase):
    def test_aus_ergebnis(self):
        u = bots.urteil_aus_ergebnis(ERGEBNIS, "HausSpur")
        self.assertEqual(u, {"runden": 42, "netto_prozent": -3.12,
                             "max_ruecklauf_prozent": 8.1,
                             "zeitraum": "2024-10-01..2026-10-01"})

    def test_merken_ergaenzt(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "urteile.json"
            bots.urteil_merken("a", {"runden": 1}, p)
            bots.urteil_merken("b", {"runden": 2}, p)
            daten = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(set(daten), {"a", "b"})
            self.assertIn("stand", daten["a"])


if __name__ == "__main__":
    unittest.main()
