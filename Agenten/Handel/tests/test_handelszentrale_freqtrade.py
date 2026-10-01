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

# Zwei Bots, wie sie freqtrade/bots.json liefert (Name, Port, Strategie) -
# Attrappen, damit die Thread-Tests keine laufenden Container sehen.
BOT_A = {"name": "trading-agent", "port": 8081, "strategie": "MoonDevTradingAgent",
         "zeitrahmen": "1h", "container": "freqtrade-trading-agent",
         "max_open_trades": 3}
BOT_B = {"name": "topmovers", "port": 8082, "strategie": "MoonDevTopMovers",
         "zeitrahmen": "1h", "container": "freqtrade-topmovers",
         "max_open_trades": 3}
UEBERSICHT_A = {"name": "trading-agent", "port": 8081,
                "strategie": "MoonDevTradingAgent", "zeitrahmen": "1h",
                "max": 3, "erreichbar": True, "dry_run": True,
                "zustand": "running", "offen": 2, "trades": 12,
                "gewinn": -245.46, "fehler": ""}
UEBERSICHT_B = {"name": "topmovers", "port": 8082,
                "strategie": "MoonDevTopMovers", "zeitrahmen": "1h",
                "max": 3, "erreichbar": False, "dry_run": None,
                "zustand": "?", "offen": None, "trades": None,
                "gewinn": None, "fehler": "nicht erreichbar: refused"}


class BotAuswahlTest(unittest.TestCase):
    """`bot_waehlen` ist die einzige Stelle, die weiss, WELCHER Bot gemeint ist."""

    def test_namenach(self):
        self.assertEqual(hz.bot_waehlen([BOT_A, BOT_B], "topmovers"), BOT_B)

    def test_vorgabe_ist_der_erste(self):
        self.assertEqual(hz.bot_waehlen([BOT_A, BOT_B], None), BOT_A)

    def test_unbekannter_name_faellt_auf_den_ersten_zurueck(self):
        # Die Zentrale erfindet keinen Bot und startet nichts: sie lehnt sich
        # an den ersten an, statt eine leere Ansicht zu zeigen.
        self.assertEqual(hz.bot_waehlen([BOT_A, BOT_B], "gibt-es-nicht"), BOT_A)

    def test_leere_liste_ist_kein_Absturz(self):
        self.assertIsNone(hz.bot_waehlen([], "x"))
        self.assertIsNone(hz.bot_waehlen(None, "x"))


class UebersichtZeilenTest(unittest.TestCase):
    """Die Bots-Tabelle: eine Zeile je Bot, auch fuer den nicht erreichbaren."""

    def test_reichbarer_bot_probebetrieb(self):
        (werte, marke), = hz.freqtrade_uebersicht_zeilen([UEBERSICHT_A])
        self.assertEqual(werte[0], "trading-agent")
        self.assertEqual(werte[1], "8081")
        self.assertEqual(werte[4], "Probebetrieb")
        self.assertEqual(werte[6], "2 / 3")
        self.assertEqual(werte[8], "-245.46")
        self.assertEqual(marke, "gut")

    def test_toter_bot_bleibt_sichtbar(self):
        (werte, marke), = hz.freqtrade_uebersicht_zeilen([UEBERSICHT_B])
        self.assertEqual(marke, "schlecht")
        self.assertEqual(werte[4], "-")
        self.assertIn("refused", werte[9])

    def test_live_bot_ist_warnung(self):
        (werte, marke), = hz.freqtrade_uebersicht_zeilen(
            [dict(UEBERSICHT_A, dry_run=False)])
        self.assertEqual(werte[4], "LIVE")
        self.assertEqual(marke, "schlecht")

    def test_kaputte_Eingaenge_werden_uebersprungen(self):
        for zeilen in (None, [], [None], ["x"], [{}]):
            self.assertIsInstance(hz.freqtrade_uebersicht_zeilen(zeilen), list)

    def test_leere_uebersicht_ist_leere_tabelle(self):
        self.assertEqual(hz.freqtrade_uebersicht_zeilen([]), [])


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
    """Der Worker-Thread: Antwortform, Bot-Auswahl, Fehlerwege - ohne Netz.

    Jeder Aufruf patcht `bots`, `uebersicht` und die Lage: ein Test, der die
    echten Bot-Container sieht, waere abhaengig davon, ob gerade einer laeuft.
    """

    def test_offline_legt_nur_lage_ab(self):
        ziel = queue.Queue()
        with mock.patch.object(hz.freqtrade_bridge, "bots", return_value=[BOT_A]), \
                mock.patch.object(hz.freqtrade_bridge, "uebersicht",
                                  return_value=[UEBERSICHT_A]), \
                mock.patch.object(hz.freqtrade_bridge, "lage_fuer",
                                  return_value={"erreichbar": False, "fehler": "x"}), \
                mock.patch.object(hz.freqtrade_bridge, "offene_trades") as offen:
            hz._freqtrade_im_thread(ziel)
        offen.assert_not_called()
        uebersicht, lage, trades_offen, trades_zu, tage = ziel.get_nowait()
        self.assertEqual(uebersicht, [UEBERSICHT_A])
        self.assertEqual(lage, {"erreichbar": False, "fehler": "x"})
        self.assertEqual((trades_offen, trades_zu, tage), ([], {}, {}))

    def test_fehler_bei_trades_wirft_nicht(self):
        ziel = queue.Queue()
        with mock.patch.object(hz.freqtrade_bridge, "bots", return_value=[BOT_A]), \
                mock.patch.object(hz.freqtrade_bridge, "uebersicht",
                                  return_value=[UEBERSICHT_A]), \
                mock.patch.object(hz.freqtrade_bridge, "lage_fuer", return_value=LAGE), \
                mock.patch.object(hz.freqtrade_bridge, "offene_trades",
                                  side_effect=hz.freqtrade_bridge.FreqtradeFehler("weg")):
            hz._freqtrade_im_thread(ziel)
        paket = ziel.get_nowait()
        self.assertEqual(paket[1], LAGE)                 # Lage bleibt stehen
        self.assertEqual(paket[2:], ([], {}, {}))        # Tabellen bleiben leer

    def test_aenderung_des_gewaehlten_bots_erreicht_den_abruf(self):
        """Der Umschalter entscheidet, WELCHER Bot gefragt wird - nicht nur die Reihenfolge."""
        ziel = queue.Queue()
        with mock.patch.object(hz.freqtrade_bridge, "bots",
                               return_value=[BOT_A, BOT_B]), \
                mock.patch.object(hz.freqtrade_bridge, "uebersicht",
                                  return_value=[UEBERSICHT_A, UEBERSICHT_B]), \
                mock.patch.object(hz.freqtrade_bridge, "lage_fuer",
                                  return_value=LAGE) as lage:
            hz._freqtrade_im_thread(ziel, name=BOT_B["name"])
        ziel.get_nowait()
        self.assertEqual(lage.call_args[0][0]["name"], BOT_B["name"])

    def test_worker_antwortet_auch_bei_exception(self):
        """Ein werfender Worker darf die Sperre `_ft_laeuft` nicht zuhalten.

        Die Zentrale setzt sie erst, wenn ein Stueck im Korb liegt. Ohne
        Antwort holte das Fenster nie wieder FreqTrade-Daten - still, fuer den
        Nutzer nicht von einem abgeschalteten Bot zu unterscheiden.
        """
        ziel = queue.Queue()
        with mock.patch.object(hz.freqtrade_bridge, "bots",
                               side_effect=RuntimeError("ueberraschung")):
            hz._freqtrade_im_thread(ziel)
        uebersicht, lage, offen, zu, tage = ziel.get_nowait()
        self.assertFalse(lage["erreichbar"])
        self.assertIn("ueberraschung", lage["fehler"])
        self.assertEqual((uebersicht, offen, zu, tage), ([], [], {}, {}))

    def test_ohne_bots_json_ist_die_lage_der_basis_beantwortet(self):
        ziel = queue.Queue()
        with mock.patch.object(hz.freqtrade_bridge, "bots", return_value=[]), \
                mock.patch.object(hz.freqtrade_bridge, "uebersicht", return_value=[]), \
                mock.patch.object(hz.freqtrade_bridge, "lage",
                                  return_value={"erreichbar": False,
                                                "fehler": "basis aus"}) as basis:
            hz._freqtrade_im_thread(ziel)
        paket = ziel.get_nowait()
        basis.assert_called_once()
        self.assertEqual(paket[0], [])           # keine erfundenen Bot-Zeilen



class ReiterTest(unittest.TestCase):
    """Der Reiter wird wirklich gebaut und aus Uebersicht + Lage gefuellt."""

    def _app(self, root):
        with mock.patch.object(hz.Handelszentrale, "_starte_freqtrade_worker"):
            return hz.Handelszentrale(root)

    def test_reiter_zeigt_lage_und_trades(self):
        try:
            root = hz.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        root.withdraw()
        try:
            app = self._app(root)
            reiter = [app.reiter.tab(i, "text") for i in app.reiter.tabs()]
            self.assertEqual(reiter, ["Spuren", "FreqTrade", "omnitrade"])
            offen = [{"pair": "BTC/USDT", "profit_pct": -0.5}]
            zu = {"trades": [{"pair": "ETH/USDT", "is_open": False,
                              "close_date": "2026-09-29 10:00:00", "profit_pct": 1}]}
            tage = {"data": [{"date": "2026-09-29", "abs_profit": -1}]}
            app._zeige_freqtrade([UEBERSICHT_A, UEBERSICHT_B], LAGE, offen, zu, tage)
            root.update()
            self.assertTrue(app.c_ft.find_all())
            self.assertEqual(app.ft_tage, [("29.09.", -1.0, 0)])
            self.assertEqual(len(app.t_ft_offen.get_children()), 1)
            self.assertEqual(len(app.t_ft_zu.get_children()), 1)
            self.assertIn("Probebetrieb", app.l_ft.cget("text"))
            app._zeige_freqtrade([], {"erreichbar": False, "fehler": "x"}, [], {})
            self.assertEqual(app.t_ft_offen.get_children(), ())
        finally:
            root.destroy()

    def test_reiter_zeigt_alle_bots_auch_den_toten(self):
        """Die Bot-Liste ist die Antwort des Reiters - nicht nur eine Kopfzeile.

        Vorher zeigte der Reiter EINEN Bot an einer festen Adresse; als drei
        Container liefen und die feste Adresse nicht antwortete, war die
        Antwort "nicht erreichbar" - fuer jeden Bot einzeln unsichtbar.
        """
        try:
            root = hz.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        root.withdraw()
        try:
            app = self._app(root)
            app._zeige_freqtrade([UEBERSICHT_A, UEBERSICHT_B], LAGE, [], {})
            root.update()
            zeilen = list(app.t_ft_bots.get_children())
            self.assertEqual(len(zeilen), 2)
            werte_a = app.t_ft_bots.item(zeilen[0], "values")
            werte_b = app.t_ft_bots.item(zeilen[1], "values")
            self.assertEqual(werte_a[0], "trading-agent")
            self.assertEqual(werte_b[0], "topmovers")
            self.assertIn("refused", werte_b[9])       # Grund bleibt lesbar
            self.assertIn("schlecht", app.t_ft_bots.item(zeilen[1], "tags"))
            # Der Umschalter fuehrt genau die Bot-Namen aus der Liste.
            self.assertEqual(list(app.w_ft_bot.cget("values")),
                             ["trading-agent", "topmovers"])
            self.assertEqual(app.ft_bot, "trading-agent")
        finally:
            root.destroy()

    def test_kopfzeile_nennt_den_gewaehlten_bot(self):
        try:
            root = hz.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        root.withdraw()
        try:
            app = self._app(root)
            app.ft_bot = "topmovers"
            app._zeige_freqtrade([UEBERSICHT_B], dict(LAGE), [], {})
            self.assertIn("topmovers", app.l_ft.cget("text"))
        finally:
            root.destroy()

    def test_auswahl_eines_bots_startt_den_abruf_mit_diesem_namen(self):
        try:
            root = hz.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        root.withdraw()
        try:
            app = self._app(root)
            app._zeige_freqtrade([UEBERSICHT_A, UEBERSICHT_B], LAGE, [], {})
            root.update()
            zweiter = list(app.t_ft_bots.get_children())[1]
            app.t_ft_bots.selection_set(zweiter)
            with mock.patch.object(hz.Handelszentrale,
                                   "_starte_freqtrade_worker") as start:
                app._ft_bot_auswahl()
            start.assert_called_once()
            self.assertEqual(app.ft_bot, "topmovers")
            self.assertEqual(app.w_ft_bot.get(), "topmovers")
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
