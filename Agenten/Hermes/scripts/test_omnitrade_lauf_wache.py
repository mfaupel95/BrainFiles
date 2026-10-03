"""Tests fuer die erweiterte omnitrade-lauf-wache: alle status/*.json.

Geprueft wird die REGEL, nicht ein Tageswert:

- mehrere Dateien, eine laeuft -> nur die stehende wird gemeldet
- alle laufen -> leere Ausgabe
- kaputte Datei -> kein Absturz
- mehrere stehen -> Ueberschrift + je eine Zeile
- --alle zeigt gesamt + jede Datei
- --status PFAD (Einzeldatei) funktioniert noch
- Entdopplung: dieselbe Feststellung wird unterdrueckt
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHE_PFAD = HIER / "omnitrade-lauf-wache.py"

_spec = importlib.util.spec_from_file_location("omnitrade_lauf_wache", WACHE_PFAD)
wache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wache)


def _status_dict(state="running", pid=4242, alter_s=5.0, schema=1,
                 intervall_s=60.0, kerzen=4, **kw):
    """Dict einer Statusdatei."""
    jetzt_ms = time.time() * 1000.0
    updated_ms = jetzt_ms - alter_s * 1000.0
    kerzenliste = [{"time_ms": jetzt_ms - (kerzen - i) * intervall_s * 1000.0,
                    "close": 100.0 + i} for i in range(kerzen)]
    daten = {"schema": schema, "state": state, "exchange": "okx",
             "symbol": "BTCUSDC", "network": "testnet",
             "script": "strategien/rsi30_stop5.omni", "pid": pid,
             "updated_ms": updated_ms, "recent_candles": kerzenliste}
    daten.update(kw)
    return daten


def schreibe(pfad, state="running", pid=4242, alter_s=5.0, schema=1,
             symbol="BTCUSDC", **kw):
    """Eine Statusdatei auf die Platte schreiben."""
    daten = _status_dict(state=state, pid=pid, alter_s=alter_s, schema=schema, **kw)
    daten["symbol"] = symbol
    pfad.write_text(json.dumps(daten), encoding="utf-8")
    return pfad


class Basis(unittest.TestCase):
    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp(prefix="omnitrade-wache-"))
        self.merk = self.ordner / "merker.json"
        self._merk = wache.MERKDATEI
        self._lebt = wache.LEBT
        self._env_ordner = os.environ.get("OMNITRADE_STATUS_ORDNER")
        wache.MERKDATEI = self.merk
        os.environ["OMNITRADE_STATUS_ORDNER"] = str(self.ordner)
        wache.LEBT = lambda pid: True  # alle PIDs leben im Test
        # Umgebungsvariable loeschen, die auf einzelne Datei zeigt
        os.environ.pop("OMNITRADE_STATUS", None)

    def tearDown(self):
        wache.MERKDATEI = self._merk
        wache.LEBT = self._lebt
        os.environ.pop("OMNITRADE_STATUS_ORDNER", None)
        if self._env_ordner is not None:
            os.environ["OMNITRADE_STATUS_ORDNER"] = self._env_ordner
        shutil.rmtree(self.ordner, ignore_errors=True)

    def lauf(self, *argumente):
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = wache.main(list(argumente))
        return code, puffer.getvalue()


class MehrdateienTest(Basis):

    def test_eine_laeuft_eine_steht(self):
        """Datei A lebt, Datei B tot -> nur B wird gemeldet."""
        schreibe(self.ordner / "live_BTC.json", pid=100, alter_s=10.0,
                 symbol="BTCUSDC")
        schreibe(self.ordner / "live_ETH.json", pid=200, alter_s=5.0,
                 symbol="ETHUSDC")
        # ETH lebt nicht
        wache.LEBT = lambda pid: pid == 100
        code, ausgabe = self.lauf()
        self.assertEqual(code, 0)
        self.assertIn("1/2 laufen", ausgabe)
        self.assertIn("ETH", ausgabe)
        self.assertIn("BEENDET", ausgabe)
        self.assertNotIn("BTC", ausgabe)

    def test_alle_laufen_leer(self):
        schreibe(self.ordner / "live_A.json", pid=100, alter_s=5.0)
        schreibe(self.ordner / "live_B.json", pid=200, alter_s=5.0)
        code, ausgabe = self.lauf()
        self.assertEqual(ausgabe.strip(), "")

    def test_kaputte_datei_kaputt(self):
        schreibe(self.ordner / "live_A.json", pid=100, alter_s=5.0)
        (self.ordner / "live_kaputt.json").write_text("{", encoding="utf-8")
        code, ausgabe = self.lauf()
        self.assertIn("1/2 laufen", ausgabe)
        self.assertIn("KAPUTT", ausgabe)

    def test_leerer_ordner(self):
        code, ausgabe = self.lauf()
        self.assertEqual(code, 0)
        self.assertEqual(ausgabe.strip(), "")

    def test_leerer_ordner_alle(self):
        code, ausgabe = self.lauf("--alle")
        self.assertIn("leer", ausgabe)

    def test_alle_zeigt_jede_datei(self):
        schreibe(self.ordner / "live_A.json", pid=100, alter_s=5.0,
                 symbol="BTCUSDC")
        schreibe(self.ordner / "live_B.json", pid=200, alter_s=600.0,
                 symbol="ETHUSDC")
        wache.LEBT = lambda pid: pid == 100
        code, ausgabe = self.lauf("--alle")
        self.assertEqual(code, 0)
        self.assertIn("1 laufen", ausgabe)
        self.assertIn("1 stehen", ausgabe)
        self.assertIn("BTC", ausgabe)
        self.assertIn("ETH", ausgabe)

    def test_status_einzeldatei(self):
        """--status PFAD: alte Form fuer eine Datei."""
        pfad = self.ordner / "live.json"
        schreibe(pfad, pid=100, alter_s=5.0)
        wache.LEBT = lambda pid: True
        code, ausgabe = self.lauf("--status", str(pfad))
        self.assertEqual(code, 0)
        self.assertEqual(ausgabe.strip(), "")

    def test_status_einzeldatei_tot(self):
        pfad = self.ordner / "live.json"
        schreibe(pfad, pid=100, alter_s=5.0)
        wache.LEBT = lambda pid: False
        code, ausgabe = self.lauf("--status", str(pfad))
        self.assertNotEqual(ausgabe.strip(), "")
        self.assertIn("steh", ausgabe.lower())

    def test_entdopplung(self):
        schreibe(self.ordner / "live_ETH.json", pid=200, alter_s=5.0)
        wache.LEBT = lambda pid: False
        code, erster = self.lauf()
        self.assertNotEqual(erster.strip(), "")
        code, zweiter = self.lauf()
        self.assertEqual(zweiter.strip(), "", "dieselbe Meldung darf nicht wiederholt werden")

    def test_anderer_befund_entdoppelt_nicht(self):
        schreibe(self.ordner / "live_ETH.json", pid=200, alter_s=5.0)
        wache.LEBT = lambda pid: False
        self.assertNotEqual(self.lauf()[1].strip(), "")
        wache.LEBT = lambda pid: True
        schreibe(self.ordner / "live_BTC.json", pid=100, alter_s=600.0)
        wache.LEBT = lambda pid: pid == 100
        code, ausgabe = self.lauf()
        self.assertNotEqual(ausgabe.strip(), "")

    def test_drei_stehen_eine_laeuft(self):
        for i, state in enumerate(["running", "running", "stopped", "running"]):
            f = self.ordner / ("live_%d.json" % i)
            schreibe(f, pid=1000+i, state=state)
        wache.LEBT = lambda pid: pid == 1000
        code, ausgabe = self.lauf()
        self.assertEqual(code, 0)
        # 1 laeuft, 3 stehen
        self.assertIn("1/4 laufen", ausgabe)

    def test_wache_startet_nichts(self):
        quelle = WACHE_PFAD.read_text(encoding="utf-8")
        self.assertIn("omnitrade.cmd start", quelle)
        for verboten in ("subprocess", "Popen", "os.system", "Start-Process",
                         "taskkill", "Stop-Process"):
            self.assertNotIn(verboten, quelle,
                             "Wache darf nichts starten/beenden")


if __name__ == "__main__":
    unittest.main(verbosity=2)
