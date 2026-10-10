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
        self.assertIn(f"{bots.HAUS.resolve().as_posix()}:/agenten:ro", m)
        self.assertNotIn("/agenten", " ".join(bots.mounts(MOONBOT)))

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
        self.assertIn(f"{bots.HAUS.resolve().as_posix()}:/agenten:ro", run)
        self.assertIn("127.0.0.1:8085:8085", run)


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


if __name__ == "__main__":
    unittest.main()
