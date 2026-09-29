r"""Tests fuer den FreqTrade-Reiter der Handelszentrale (reine Funktionen).

Aufruf aus `Agenten/Handel/tests`:
    ..\scanner\.venv\Scripts\python.exe -m unittest test_handelszentrale_freqtrade
"""

import os
import queue
import sys
import unittest
from unittest import mock

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import handelszentrale as hz  # noqa: E402

LAGE = {"erreichbar": True, "dry_run": True, "zustand": "running", "boerse": "binance",
        "strategie": "SampleStrategy", "zeitrahmen": "5m", "offene_trades": 1,
        "trades_gesamt": 3, "gewinn_geschlossen": 1.5, "gewinn_gesamt": -0.25,
        "waehrung": "USDT", "guthaben": 1000.0}


class KopfTest(unittest.TestCase):

    def test_noch_keine_lage(self):
        self.assertEqual(hz.freqtrade_kopf(None)[1], "matt")

    def test_offline(self):
        text, marke = hz.freqtrade_kopf({"erreichbar": False, "fehler": "weg"})
        self.assertIn("nicht erreichbar", text)
        self.assertIn("weg", text)
        self.assertEqual(marke, "schlecht")

    def test_probebetrieb(self):
        text, marke = hz.freqtrade_kopf(LAGE)
        self.assertIn("Probebetrieb", text)
        self.assertIn("1000.00 USDT", text)
        self.assertIn("-0.25", text)
        self.assertEqual(marke, "gut")

    def test_live_ist_warnung(self):
        text, marke = hz.freqtrade_kopf(dict(LAGE, dry_run=False))
        self.assertIn("LIVE", text)
        self.assertEqual(marke, "schlecht")


class ZeilenTest(unittest.TestCase):

    def test_zeit(self):
        self.assertEqual(hz._ft_zeit("2026-09-29 16:45:00"), "29.09. 16:45")
        self.assertEqual(hz._ft_zeit("2026-09-29T16:45:00+00:00"), "29.09. 16:45")

    def test_offene_zeile(self):
        zeile = hz.freqtrade_offen_zeile({
            "pair": "BTC/USDT", "is_short": False, "open_date": "2026-09-29 10:00:00",
            "open_rate": 60000, "current_rate": 60600, "stake_amount": 100,
            "profit_pct": 1.0})
        self.assertEqual(zeile[:3], ("BTC/USDT", "long", "29.09. 10:00"))
        self.assertEqual(zeile[-2:], ("100.00", "+1.00"))

    def test_geschlossene_neueste_zuerst_ohne_offene(self):
        antwort = {"trades": [
            {"pair": "A", "is_open": False, "close_date": "2026-09-28 10:00:00",
             "profit_pct": -1, "profit_abs": -2, "exit_reason": "stop_loss"},
            {"pair": "B", "is_open": True},
            {"pair": "C", "is_open": False, "close_date": "2026-09-29 10:00:00",
             "profit_pct": 2, "profit_abs": 3, "exit_reason": "roi"},
        ]}
        zeilen = hz.freqtrade_zu_zeilen(antwort)
        self.assertEqual([z[0] for z in zeilen], ["C", "A"])
        self.assertEqual(zeilen[1][3:], ("-1.00", "-2.00", "stop_loss"))

    def test_kaputte_antwort_ist_leer(self):
        for antwort in (None, {}, [], "x"):
            self.assertEqual(hz.freqtrade_zu_zeilen(antwort), [])

    def test_tagesbalken_aeltester_zuerst(self):
        antwort = {"data": [
            {"date": "2026-09-29", "abs_profit": 1.5, "trade_count": 2},
            {"date": "2026-09-28", "abs_profit": -0.5, "trade_count": 1},
            {"date": "kaputt"}]}
        self.assertEqual(hz.freqtrade_tagesbalken(antwort),
                         [("28.09.", -0.5, 1), ("29.09.", 1.5, 2)])
        for antwort in (None, {}, {"data": None}, "x"):
            self.assertEqual(hz.freqtrade_tagesbalken(antwort or {}), [])

    def test_gv_marke(self):
        self.assertEqual(hz._gv_marke("+1.00"), "gut")
        self.assertEqual(hz._gv_marke("-0.50"), "schlecht")
        self.assertEqual(hz._gv_marke("+0.00"), "")


class ThreadTest(unittest.TestCase):

    def test_offline_legt_nur_lage_ab(self):
        ziel = queue.Queue()
        with mock.patch.object(hz.freqtrade_bridge, "lage",
                               return_value={"erreichbar": False, "fehler": "x"}), \
                mock.patch.object(hz.freqtrade_bridge, "offene_trades") as offen:
            hz._freqtrade_im_thread(ziel)
        offen.assert_not_called()
        self.assertEqual(ziel.get_nowait(), ({"erreichbar": False, "fehler": "x"}, [], {}, {}))

    def test_fehler_bei_trades_wirft_nicht(self):
        ziel = queue.Queue()
        with mock.patch.object(hz.freqtrade_bridge, "lage", return_value=LAGE), \
                mock.patch.object(hz.freqtrade_bridge, "offene_trades",
                                  side_effect=hz.freqtrade_bridge.FreqtradeFehler("weg")):
            hz._freqtrade_im_thread(ziel)
        self.assertEqual(ziel.get_nowait()[0], LAGE)



class ReiterTest(unittest.TestCase):
    """Der Reiter wird wirklich gebaut und aus einer Lage gefuellt."""

    def test_reiter_zeigt_lage_und_trades(self):
        try:
            root = hz.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        root.withdraw()
        try:
            with mock.patch.object(hz.Handelszentrale, "_starte_freqtrade_worker"):
                app = hz.Handelszentrale(root)
            reiter = [app.reiter.tab(i, "text") for i in app.reiter.tabs()]
            self.assertEqual(reiter, ["Spuren", "FreqTrade"])
            offen = [{"pair": "BTC/USDT", "profit_pct": -0.5}]
            zu = {"trades": [{"pair": "ETH/USDT", "is_open": False,
                              "close_date": "2026-09-29 10:00:00", "profit_pct": 1}]}
            tage = {"data": [{"date": "2026-09-29", "abs_profit": -1}]}
            app._zeige_freqtrade(LAGE, offen, zu, tage)
            root.update()
            self.assertTrue(app.c_ft.find_all())
            self.assertEqual(app.ft_tage, [("29.09.", -1.0, 0)])
            self.assertEqual(len(app.t_ft_offen.get_children()), 1)
            self.assertEqual(len(app.t_ft_zu.get_children()), 1)
            self.assertIn("Probebetrieb", app.l_ft.cget("text"))
            app._zeige_freqtrade({"erreichbar": False, "fehler": "x"}, [], {})
            self.assertEqual(app.t_ft_offen.get_children(), ())
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
