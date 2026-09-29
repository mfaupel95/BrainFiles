"""Tests fuer die Gateway-Identitaets-Wache (Agenten/Hermes/scripts/gateway-identitaet-wache.py).

Kein Netz, kein echter Gateway: geprueft werden die Regeln der Wache - lebende
PID erkennen, fehlende gateway.pid aus dem Lock rekonstruieren, dieselbe
Feststellung nicht wiederholen, und im Zweifel NICHT eingreifen.

Aufruf (aus Agenten/Handel/tests):
    ../../..//Handel/.venv/Scripts/python.exe -m unittest test_gateway_identitaet_wache
oder ueber die Handel-Suite:  python -m unittest discover -s tests -t tests
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

HIER = Path(__file__).resolve()
BRAIN = HIER.parents[3]                     # Agenten/Handel/tests/x.py -> BrainFiles
SKRIPT = BRAIN / "Agenten" / "Hermes" / "scripts" / "gateway-identitaet-wache.py"


def _laden():
    spec = importlib.util.spec_from_file_location("gateway_identitaet_wache", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class LeerePIDTest(unittest.TestCase):
    """_lebt: der eigene Prozess lebt, eine erfundene PID nicht."""

    def test_eigene_pid_lebt(self):
        w = _laden()
        self.assertTrue(w._lebt(os.getpid()))

    def test_erfundene_pid_lebt_nicht(self):
        w = _laden()
        self.assertFalse(w._lebt(4321000))

    def test_null_und_negativ_lebt_nicht(self):
        w = _laden()
        self.assertFalse(w._lebt(0))
        self.assertFalse(w._lebt(-1))


class ReparaturTest(unittest.TestCase):
    """gateway.pid wird aus dem Lock rekonstruiert - Inhalt der Instanz, nicht geraten."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name)
        self.w = _laden()

    def tearDown(self):
        self.tmp.cleanup()

    def test_pid_datei_hat_denselben_record_wie_der_lock(self):
        record = {"pid": os.getpid(), "kind": "hermes-gateway",
                  "start_time": 12345, "hermes_home": str(self.ordner)}
        lock = self.ordner / "gateway.lock"
        lock.write_text(json.dumps(record), encoding="utf-8")
        pid_datei = self.ordner / "gateway.pid"

        text = self.w.reparieren(pid_datei, record)

        self.assertTrue(pid_datei.exists())
        self.assertEqual(json.loads(pid_datei.read_text(encoding="utf-8")), record)
        self.assertIn("gateway.pid aus dem Lock geschrieben", text)

    def test_fehlender_ordner_wird_nicht_erfunden(self):
        # Ein Schreibfehler darf nicht als Erfolg durchgehen.
        record = {"pid": os.getpid()}
        ziel = self.ordner / "gibtesnicht" / "gateway.pid"
        text = self.w.reparieren(ziel, record)
        self.assertIn("Reparatur fehlgeschlagen", text)


class ProbeTest(unittest.TestCase):
    """Ohne Checkout-venv gibt es eine ehrliche Antwort, keine Ausnahme."""

    def test_ohne_venv_kein_absturz(self):
        w = _laden()
        alt = w.CHECKOUT
        try:
            w.CHECKOUT = Path(tempfile.gettempdir()) / "gibtesnicht" / "hermes-agent"
            ok, profile, fehler = w.proben()
        finally:
            w.CHECKOUT = alt
        self.assertIsNone(ok)
        self.assertEqual(profile, [])
        self.assertIn("Checkout-venv fehlt", fehler)


class MeldungTest(unittest.TestCase):
    """Dieselbe Feststellung wird nicht bei jedem Lauf wiederholt."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.stand_pfad = Path(self.tmp.name) / "stand.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_zweite_gleiche_meldung_ist_still(self):
        w = _laden()
        zeilen = ["erste Zeile", "zweite Zeile"]
        jetzt = datetime.now()
        stand = {"_pfad": str(self.stand_pfad)}

        aus1 = self._abfangen(w.melden, zeilen, stand, jetzt)
        aus2 = self._abfangen(w.melden, zeilen, stand, jetzt + timedelta(minutes=5))

        self.assertIn("erste Zeile", aus1)
        self.assertEqual(aus2, "")
        self.assertTrue(self.stand_pfad.exists())

    def test_nach_der_sperrfrist_wieder_gemeldet(self):
        w = _laden()
        zeilen = ["Kernzeile"]
        jetzt = datetime.now()
        stand = {"_pfad": str(self.stand_pfad)}
        self._abfangen(w.melden, zeilen, stand, jetzt)
        aus = self._abfangen(w.melden, zeilen, stand, jetzt + timedelta(hours=w.WIEDERHOLUNG_H + 1))
        self.assertIn("Kernzeile", aus)

    def test_neuer_befund_wird_sofort_gemeldet(self):
        w = _laden()
        jetzt = datetime.now()
        stand = {"_pfad": str(self.stand_pfad)}
        self._abfangen(w.melden, ["alt"], stand, jetzt)
        aus = self._abfangen(w.melden, ["neu"], stand, jetzt + timedelta(minutes=1))
        self.assertIn("neu", aus)

    def test_neustart_merker_ueberlebt_die_sperre(self):
        # Ein Neustart am selben Tag darf sich nicht wiederholen, auch wenn die
        # Meldung selbst unterdrueckt wurde.
        w = _laden()
        jetzt = datetime.now()
        stand = {"_pfad": str(self.stand_pfad), "letzter_neustart_tag": jetzt.strftime("%Y-%m-%d")}
        self._abfangen(w.melden, ["x"], stand, jetzt)
        gespeichert = json.loads(self.stand_pfad.read_text(encoding="utf-8"))
        self.assertEqual(gespeichert["letzter_neustart_tag"], jetzt.strftime("%Y-%m-%d"))

    @staticmethod
    def _abfangen(funktion, *args):
        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            funktion(*args)
        return puffer.getvalue()


class KeinEingriffBeiUpdateTest(unittest.TestCase):
    """Waehrend eines Update-Laufs wird nichts angefasst."""

    def test_update_laeuft_liefert_bool(self):
        w = _laden()
        self.assertIsInstance(w.update_laeuft(), bool)

    def test_update_abfrage_findet_sich_nicht_selbst(self):
        # Ohne zusammengesetztes Muster findet die Prozessabfrage ihren eigenen
        # Suchtext und meldet dauerhaft "es laeuft ein Update".
        w = _laden()
        self.assertFalse(w.update_laeuft())


if __name__ == "__main__":
    unittest.main()