#!/usr/bin/env python3
"""Test fuer Agenten/Hermes/scripts/omnitrade-wache.py.

Regeln, die getestet werden (nicht Tageswerte):
1. Leere Ausgabe wenn alle Laeufe laufen oder nie gelaufen sind.
2. Ein toter Lauf (Statusdatei existiert, Prozess weg) wird gemeldet und
   mit `starte()` neu gestartet.
3. Die Merkdatei verhindert die Wiederholung derselben Meldung (TAKTZEITRAUM).
4. `--trocken` startet nichts ECHTES.
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from unittest import mock

HIER = os.path.dirname(os.path.abspath(__file__))
QUEL = os.path.join(HIER, "omnitrade-wache.py")
spec = importlib.util.spec_from_file_location("omnitrade_wache_t", QUEL)
w = importlib.util.module_from_spec(spec)
sys.modules["omnitrade_wache_t"] = w

# omnitrade_start wird NIE echt importiert: der Test biegt das Modul in
# sys.modules, damit kein Popen auf dem Rechner laeuft.
start_mock = mock.MagicMock()
start_mock.LAEUFE = {
    "adx_macd_btc": ("adx_macd", "BTCUSDC"),
    "rsi30_stop5_btc": ("rsi30_stop5", "BTCUSDC"),
}
sys.modules["omnitrade_start"] = start_mock
spec.loader.exec_module(w)


class WacheBasis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omnitrade-wache-")
        w.MERK = os.path.join(self.tmp, "merk.json")
        start_mock.reset_mock()
        # Standard: kein Lauf tot
        start_mock.zustand.side_effect = lambda n: (True, "Prozess laeuft")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        if os.path.exists(w.MERK):
            os.remove(w.MERK)


class LeerWennAllesLaeuft(WacheBasis):
    def runTest(self):
        self.assertEqual(w.haupt(), "")


class LeerWennNieGestartet(WacheBasis):
    def runTest(self):
        # Statusdatei fehlt -> nie gelaufen -> nicht anfassen
        start_mock.zustand.side_effect = lambda n: (False, "keine Statusdatei")
        start_mock.statusdatei.return_value = os.path.join(
            self.tmp, "nie_gelaufen.json")
        self.assertEqual(w.haupt(), "")


class ToterLaufWirdNeuGestartet(WacheBasis):
    def runTest(self):
        start_mock.zustand.side_effect = lambda n: (
            False, "veraltet: seit 1000 min kein Lebenszeichen")
        pfad = os.path.join(self.tmp, "live_rsi30_stop5_BTCUSDC.json")
        with open(pfad, "w", encoding="utf-8") as f:
            f.write("{}")
        start_mock.statusdatei.return_value = pfad
        start_mock.starte.return_value = "rsi30_stop5_btc: gestartet, PID 999"
        text = w.haupt()
        self.assertIn("rsi30_stop5_btc", text)
        # beide Eintraege der Test-LAEUFE sind tot, beide werden gestartet;
        # geprueft wird der konkrete Name, nicht die Anzahl.
        namen = [c.args[0] for c in start_mock.starte.call_args_list]
        self.assertIn("rsi30_stop5_btc", namen)


class MerkdateiVerhindertWiederholung(WacheBasis):
    def runTest(self):
        start_mock.zustand.side_effect = lambda n: (
            False, "veraltet: seit 1000 min kein Lebenszeichen")
        pfad = os.path.join(self.tmp, "live_rsi30_stop5_BTCUSDC.json")
        with open(pfad, "w", encoding="utf-8") as f:
            f.write("{}")
        start_mock.statusdatei.return_value = pfad
        start_mock.starte.return_value = "gestartet"
        w.haupt()
        # zweiter Lauf sofort: gleiche Meldung, unterdrueckt
        start_mock.starte.reset_mock()
        self.assertEqual(w.haupt(), "")
        start_mock.starte.assert_not_called()


class TrockenStartetNichts(WacheBasis):
    def runTest(self):
        start_mock.zustand.side_effect = lambda n: (
            False, "veraltet: seit 1000 min kein Lebenszeichen")
        pfad = os.path.join(self.tmp, "live_rsi30_stop5_BTCUSDC.json")
        with open(pfad, "w", encoding="utf-8") as f:
            f.write("{}")
        start_mock.statusdatei.return_value = pfad
        text = w.haupt(trocken=True)
        self.assertIn("wuerde neu gestartet", text)
        start_mock.starte.assert_not_called()


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTests([
        LeerWennAllesLaeuft(), LeerWennNieGestartet(),
        ToterLaufWirdNeuGestartet(), MerkdateiVerhindertWiederholung(),
        TrockenStartetNichts(),
    ])
    ergebnis = unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(0 if ergebnis.wasSuccessful() else 1)