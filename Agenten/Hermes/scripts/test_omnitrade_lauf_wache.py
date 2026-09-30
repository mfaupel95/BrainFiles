"""Tests fuer die Wache des omnitrade-Demo-Laufs
(Agenten/Hermes/scripts/omnitrade-lauf-wache.py).

Geprueft wird die REGEL, nicht ein Tageswert:

- gesunder Lauf              -> LEERE Ausgabe (Watchdog: nichts senden),
- tote PID bei frischer Datei -> Befund "lebt nicht" (die Anzeige-Luege),
- tote PID bei ALTER Datei    -> Befund "lebt nicht", NICHT "haengt" (der
  haertere Zeuge gewinnt; sonst behauptet die Meldung "PID lebt noch"),
- lebende PID + alte Datei    -> Befund "HAENGT",
- Zustand nicht mehr running  -> Befund mit dem Zustand,
- Statusdatei fehlt / kaputt / fremdes Schema -> je ein Befund, kein Absturz,
- Stunde-Kerzen: 50 min alte Datei ist KEIN Haenger (Grenze aus dem Intervall),
- PID-Wechsel                 -> kein Fehler und keine zweite Meldung,
- dieselbe Feststellung       -> innerhalb der Wiederholungsfrist still,
- --grenze-s 0                -> meldet auch den gesunden Lauf (Alarmrichtung),
- die Wache nennt den Startbefehl, fuehrt ihn aber nicht aus.

Gemessen wird in TEMP-Verzeichnissen: die echte Statusdatei, die echte Merkdatei
und die echte Prozessliste bleiben unberuehrt (LEBT wird gestellt, kein tasklist).

Start:  python -m unittest test_omnitrade_lauf_wache  (aus diesem Ordner)
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


def status(pfad, state="running", pid=4242, alter_s=5.0, schema=1,
           intervall_s=60.0, kerzen=4, updated_ms=None, rohtext=None):
    """Eine Statusdatei nach Schema 1 schreiben, wie omnitrade sie schreibt."""
    if rohtext is not None:
        pfad.write_text(rohtext, encoding="utf-8")
        return pfad
    jetzt_ms = time.time() * 1000.0
    if updated_ms is None:
        updated_ms = jetzt_ms - alter_s * 1000.0
    kerzenliste = [{"time_ms": jetzt_ms - (kerzen - i) * intervall_s * 1000.0,
                    "close": 100.0 + i} for i in range(kerzen)]
    daten = {"schema": schema, "state": state, "exchange": "okx",
             "symbol": "BTCUSDC", "network": "testnet",
             "script": "strategien/rsi30_stop5.omni", "pid": pid,
             "updated_ms": updated_ms, "recent_candles": kerzenliste}
    pfad.write_text(json.dumps(daten), encoding="utf-8")
    return pfad


class Basis(unittest.TestCase):
    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp(prefix="omnitrade-wache-"))
        self.status = self.ordner / "live.json"
        self.merk = self.ordner / "merker.json"
        self._merk = wache.MERKDATEI
        self._lebt = wache.LEBT
        self._env = os.environ.get("OMNITRADE_STATUS")
        wache.MERKDATEI = self.merk
        os.environ["OMNITRADE_STATUS"] = str(self.status)
        self.lebendig(True)

    def tearDown(self):
        wache.MERKDATEI = self._merk
        wache.LEBT = self._lebt
        if self._env is None:
            os.environ.pop("OMNITRADE_STATUS", None)
        else:
            os.environ["OMNITRADE_STATUS"] = self._env
        shutil.rmtree(self.ordner, ignore_errors=True)

    def lebendig(self, lebt=True):
        """Die Prozessliste stellen - kein tasklist im Test."""
        wache.LEBT = lambda pid: bool(lebt)

    def lauf(self, *argumente):
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = wache.main(list(argumente))
        return code, puffer.getvalue()


class RegelTest(Basis):

    def test_gesunder_lauf_ist_still(self):
        status(self.status, pid=4242, alter_s=5.0)
        code, ausgabe = self.lauf()
        self.assertEqual(code, 0)
        self.assertEqual(ausgabe.strip(), "", "ein laufender Lauf darf nichts melden")

    def test_alle_zeigt_den_gesunden_stand(self):
        status(self.status, pid=4242, alter_s=5.0)
        _, ausgabe = self.lauf("--alle")
        self.assertIn("4242", ausgabe)
        self.assertIn("laeuft", ausgabe)

    def test_tote_pid_wird_gemeldet(self):
        """Genau die Luege aus T-211: Datei sagt running, Prozess ist weg."""
        status(self.status, state="running", pid=76116, alter_s=5.0)
        self.lebendig(False)
        _, ausgabe = self.lauf()
        self.assertIn("76116", ausgabe)
        self.assertIn("lebt nicht", ausgabe)
        self.assertIn(wache.STARTBEFEHL, ausgabe)

    def test_tote_pid_bei_alter_datei_ist_kein_haenger(self):
        """Alter UND tote PID: gemeldet wird der Tod, nicht 'PID lebt noch'."""
        status(self.status, state="running", pid=69800, alter_s=400.0)
        self.lebendig(False)
        _, ausgabe = self.lauf()
        self.assertIn("lebt nicht", ausgabe)
        self.assertNotIn("HAENGT", ausgabe)
        self.assertNotIn("lebt noch", ausgabe)

    def test_haengende_datei_wird_gemeldet(self):
        status(self.status, state="running", pid=4242, alter_s=400.0)
        self.lebendig(True)
        _, ausgabe = self.lauf()
        self.assertIn("HAENGT", ausgabe)
        self.assertIn("4242", ausgabe)

    def test_stundenlauf_ist_kein_haenger(self):
        """--interval 1h: 50 min alte Datei ist normal (Grenze 9000 s)."""
        status(self.status, state="running", pid=29296, alter_s=3000.0,
               intervall_s=3600.0)
        self.lebendig(True)
        _, ausgabe = self.lauf()
        self.assertEqual(ausgabe.strip(), "",
                         "ein stuendlicher Lauf darf nach 50 min nicht gemeldet werden")

    def test_sauberes_ende_wird_gemeldet(self):
        status(self.status, state="stopped", pid=4242, alter_s=5.0)
        self.lebendig(False)
        _, ausgabe = self.lauf()
        self.assertIn("stopped", ausgabe)
        self.assertIn("Zustand", ausgabe)

    def test_fehlende_datei_wird_gemeldet(self):
        self.assertFalse(self.status.exists())
        _, ausgabe = self.lauf()
        self.assertIn("keine Statusdatei", ausgabe)
        self.assertNotEqual(ausgabe.strip(), "")

    def test_kaputte_datei_wird_gemeldet(self):
        status(self.status, rohtext="{das ist kein json")
        _, ausgabe = self.lauf()
        self.assertIn("KAPUTT", ausgabe)

    def test_fremdes_schema_wird_gemeldet(self):
        status(self.status, schema=2, pid=4242, alter_s=5.0)
        self.lebendig(True)
        _, ausgabe = self.lauf()
        self.assertIn("KAPUTT", ausgabe)
        self.assertIn("Schema", ausgabe)

    def test_alarmrichtung_grenze_null(self):
        """Gegenprobe: mit --grenze-s 0 muss derselbe gesunde Lauf auffallen."""
        status(self.status, state="running", pid=4242, alter_s=5.0)
        self.lebendig(True)
        _, ausgabe = self.lauf("--grenze-s", "0")
        self.assertIn("HAENGT", ausgabe)

    def test_pid_wechsel_ist_kein_fehler(self):
        """Der Lauf wird von Hand neu gestartet - die Wache fuehrt keine Historie."""
        status(self.status, state="running", pid=111, alter_s=5.0)
        self.assertEqual(self.lauf()[1].strip(), "")
        status(self.status, state="running", pid=222, alter_s=5.0)
        self.assertEqual(self.lauf()[1].strip(), "",
                         "ein anderer PID ist derselbe gesunde Zustand")

    def test_wache_startet_nichts(self):
        """Sie NENNT den Startbefehl, fuehrt ihn aber nicht aus."""
        quelle = WACHE_PFAD.read_text(encoding="utf-8")
        self.assertIn("omnitrade.cmd start", quelle)
        for verboten in ("subprocess", "Popen", "os.system", "Start-Process",
                         "taskkill", "Stop-Process"):
            self.assertNotIn(verboten, quelle,
                             "die Wache darf nichts starten oder beenden")


class WiederholungTest(Basis):

    def test_dieselbe_feststellung_bleibt_still(self):
        status(self.status, state="running", pid=4242, alter_s=5.0)
        self.lebendig(False)
        _, erster = self.lauf()
        self.assertNotEqual(erster.strip(), "")
        _, zweiter = self.lauf()
        self.assertEqual(zweiter.strip(), "",
                         "dieselbe Feststellung darf nicht wiederholt werden")
        self.assertTrue(self.merk.exists(), "Merkdatei wurde nicht geschrieben")

    def test_pid_wechsel_wiederholt_die_meldung_nicht(self):
        """Der Schluessel ist die Meldung OHNE Zahlen: tote PID bleibt tote PID."""
        status(self.status, state="running", pid=111, alter_s=5.0)
        self.lebendig(False)
        self.assertNotEqual(self.lauf()[1].strip(), "")
        status(self.status, state="running", pid=222, alter_s=7.0)
        self.assertEqual(self.lauf()[1].strip(), "",
                         "eine andere PID ist dieselbe Feststellung")

    def test_nach_ablauf_der_wiederholung_wieder_gemeldet(self):
        status(self.status, state="running", pid=4242, alter_s=5.0)
        self.lebendig(False)
        self.lauf()
        stand = json.loads(self.merk.read_text(encoding="utf-8"))
        alt = time.time() - (wache.WIEDERHOLUNG_STUNDEN + 1) * 3600
        for k in stand:
            stand[k] = datetime.fromtimestamp(alt, timezone.utc).isoformat(
                timespec="seconds")
        self.merk.write_text(json.dumps(stand), encoding="utf-8")
        self.assertNotEqual(self.lauf()[1].strip(), "")

    def test_anderer_befund_wird_nicht_verschluckt(self):
        """Aus 'tote PID' wird 'Datei weg' - das ist eine neue Feststellung."""
        status(self.status, state="running", pid=4242, alter_s=5.0)
        self.lebendig(False)
        self.assertNotEqual(self.lauf()[1].strip(), "")
        self.status.unlink()
        _, ausgabe = self.lauf()
        self.assertIn("keine Statusdatei", ausgabe)


if __name__ == "__main__":
    unittest.main(verbosity=2)