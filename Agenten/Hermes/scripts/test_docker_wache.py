"""Tests fuer docker-wache.py (T-239).

Kein echter docker-/wsl-Aufruf: beide Nahte (runner, schlafen) sind gesetzt.
Die Merkdatei wird je Test in einen Temp-Ordner gebogen.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location("docker_wache", os.path.join(HIER, "docker-wache.py"))
dw = importlib.util.module_from_spec(spec)
sys.modules["docker_wache"] = dw
spec.loader.exec_module(dw)


def fake_runner(von_an_alive=False, heilbar=False, prot=None, desktop_laeuft=False):
    """Zustandsbehangter Fake: docker info antwortet ab `von_an_alive` bzw.
    NACH dem Heilgriff, wenn `heilbar`. `starten`-Zeuge laeuft ueber prot.

    `desktop_laeuft=True` bildet den T-306-Fall ab: die App laeuft, die Engine
    antwortet trotzdem nicht. tasklist liefert dann eine Prozesszeile - ohne
    sie wuerde der Test den zweiten Griff nie nehmen."""
    state = {"alive": bool(von_an_alive), "desktop": bool(desktop_laeuft)}
    nach_wsl = {"alive": None}       # None = App-start entscheidet

    def runner(cmd, frist):
        if prot is not None:
            prot.append(cmd[0])
        if cmd[0] == "docker":
            return (0, "27.x") if state["alive"] else (1, "Cannot connect to the Docker daemon")
        if cmd[0] == "wsl":
            nach_wsl["alive"] = bool(heilbar)
            if not state["desktop"]:
                # Kein zweiter Griff noetig: der Desktop-Start genuegt, und die
                # Engine ist danach da (das ist der alte, gemessene Weg).
                state["alive"] = bool(heilbar)
            return (0, "")
        if cmd[0] == "tasklist":
            if state["desktop"]:
                return (0, '"Docker Desktop.exe","1234","Konsolen","1","120.000 K"')
            return (0, "INFO: Keine Aufgaben laufen, die den angegebenen Kriterien entsprechen.")
        if cmd[0] == "taskkill":
            if state["desktop"]:
                # Der zweite Griff: erst das Beenden macht die Engine heilbar.
                state["alive"] = bool(heilbar)
                state["desktop"] = False
            return (0, "ERFOLGREICH: Der Prozess mit PID %s wurde beendet."
                    % cmd[-1])
        raise AssertionError("unerwartetes Programm: %s" % cmd[0])

    # Der Desktop-Start setzt die Engine nur, wenn der zweite Griff sie nicht
    # schon gesetzt hat.
    def starten():
        if nach_wsl["alive"] is not None:
            state["alive"] = nach_wsl["alive"]
    runner.starten = starten
    return runner


def starter(prot=None):
    def s():
        if prot is not None:
            prot.append("desktop")
    return s


class ZweiterGriffTest(unittest.TestCase):
    """T-306: laeuft die Desktop-App und bleibt die Engine trotzdem weg, hilft
    nur Beenden + Neustart.

    Geprueft wird die EIGENSCHAFT (der zweite Griff wird genommen und
    loest den Zustand), nicht ein Aufrufverzeichnis - ein Test gegen die
    Prozessliste wuerde nur den Aufbau des Fakes messen.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.merk = os.path.join(self.tmp.name, "docker-wache.json")
        self._alt = dw.MERKER
        dw.MERKER = self.merk
        self._alt_update = dw.update_laeuft
        dw.update_laeuft = lambda **kw: False
        self.schlafen = lambda s: None

    def tearDown(self):
        dw.MERKER = self._alt
        dw.update_laeuft = self._alt_update
        self.tmp.cleanup()

    def test_leerer_prozessabruf_ist_kein_befund(self):
        """`tasklist` ohne Treffer liefert eine Zeile, nicht leer - die
        Zeile darf nicht als 'App laeuft' gelesen werden."""
        leer = dw._desktop_prozesse(fake_runner(desktop_laeuft=False))
        self.assertEqual(leer, [])
        da = dw._desktop_prozesse(fake_runner(desktop_laeuft=True))
        self.assertEqual(len(da), 1)

    def test_laufende_app_wird_beendet_und_neu_gestartet(self):
        prot = []
        r = fake_runner(heilbar=True, prot=prot, desktop_laeuft=True)
        ok, text = dw.heilen(runner=r, schlafen=self.schlafen,
                             starten=lambda: (prot.append("desktop"), r.starten()))
        self.assertTrue(ok, text)
        self.assertIn("taskkill", prot, "der zweite Griff muss beenden")
        self.assertIn("desktop", prot, "danach neu starten")
        self.assertIn("stand noch", text)

    def test_ohne_app_kein_taskkill(self):
        """Ohne laufende App bleibt der alte Griff: beenden waere Blindflug."""
        prot = []
        r = fake_runner(heilbar=True, prot=prot, desktop_laeuft=False)
        ok, _ = dw.heilen(runner=r, schlafen=self.schlafen,
                          starten=lambda: (prot.append("desktop"), r.starten()))
        self.assertTrue(ok)
        self.assertNotIn("taskkill", prot)


class WachenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.merk = os.path.join(self.tmp.name, "docker-wache.json")
        self._alt = dw.MERKER
        dw.MERKER = self.merk
        self._alt_update = dw.update_laeuft
        dw.update_laeuft = lambda **kw: False      # Tests durften nicht von echten Update-Logs abhangen
        self.schlafen = lambda s: None

    def tearDown(self):
        dw.MERKER = self._alt
        dw.update_laeuft = self._alt_update
        self.tmp.cleanup()

    def test_lebende_engine_schweigt(self):
        prot = []
        self.assertEqual(dw.lauf(runner=fake_runner(von_an_alive=True, prot=prot),
                                 schlafen=self.schlafen), "")
        self.assertEqual(prot, ["docker"])               # nur die Frage, kein Heilgriff

    def test_erster_lauf_meldet_und_heilversuch_ohne_erfolg(self):
        prot = []
        text = dw.lauf(runner=fake_runner(heilbar=False, prot=prot),
                       schlafen=self.schlafen, starten=starter(prot))
        self.assertIn("Heilung MISSLUNGEN", text)
        self.assertIn("wsl", prot)                      # Der Heilgriff wurde versucht
        self.assertIn("desktop", prot)                  # ueber die Naht, nie echt

    def test_heilung_meldet_sich_und_wiederholt_nicht(self):
        text = dw.lauf(runner=fake_runner(heilbar=True), schlafen=self.schlafen,
                       starten=starter())
        self.assertIn("geheilt", text)
        # Naechster Lauf mit lebender Engine: Stille (Heilung war ja gemeldet).
        self.assertEqual(dw.lauf(runner=fake_runner(von_an_alive=True), schlafen=self.schlafen), "")

    def test_gleicher_ausfall_6_stunden_nur_einmal(self):
        leer = dw.lauf(runner=fake_runner(heilbar=False), schlafen=self.schlafen,
                       starten=starter())
        self.assertIn("MISSLUNGEN", leer)
        self.assertEqual(dw.lauf(runner=fake_runner(heilbar=False), schlafen=self.schlafen,
                                 starten=starter()), "")   # keine Wiederholung
        # Nach der Frist darf es wieder melden:
        d = json.load(open(self.merk, encoding="utf-8"))
        d["seit"] = time.time() - dw.WIEDERHOLUNG_S - 60
        json.dump(d, open(self.merk, "w", encoding="utf-8"))
        text = dw.lauf(runner=fake_runner(heilbar=False), schlafen=self.schlafen,
                       starten=starter())
        self.assertIn("MISSLUNGEN", text)

    def test_update_sperre_verweigert_heilung(self):
        prot = []
        dw.update_laeuft = lambda **kw: True
        try:
            text = dw.lauf(runner=fake_runner(prot=prot), schlafen=self.schlafen,
                           starten=starter(prot))
        finally:
            dw.update_laeuft = lambda **kw: False
        self.assertIn("hermes-update laeuft", text)
        self.assertNotIn("wsl", prot)                   # NICHT geheilt, nur gemeldet
        self.assertNotIn("desktop", prot)

    def test_erholung_wird_gemeldet(self):
        json.dump({"status": "weg", "seit": time.time() - 3600}, open(self.merk, "w"))
        text = dw.lauf(runner=fake_runner(von_an_alive=True), schlafen=self.schlafen)
        self.assertIn("Engine ist zurueck", text)
        self.assertEqual(dw.lauf(runner=fake_runner(von_an_alive=True), schlafen=self.schlafen), "")


class EchteNahtTest(unittest.TestCase):
    """Gegenprobe gegen die taubste Bauart: ein Runner, der ALLES beantwortet,
    darf die Wache nicht zum Heilgriff verleiten - und die Vorlage ohne
    docker-Aufruf darf nicht behaupten, die Engine lebe."""

    def test_engine_lebt_prueft_rueckgabe_code(self):
        self.assertTrue(dw.engine_lebt(runner=lambda cmd, frist: (0, "27")))
        self.assertFalse(dw.engine_lebt(runner=lambda cmd, frist: (1, "")))
        self.assertFalse(dw.engine_lebt(runner=lambda cmd, frist: (None, "Timeout")))

    def test_update_laeuft_nur_frische_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            logs = os.path.join(tmp, "logs")
            os.makedirs(logs)
            log = os.path.join(logs, "update-20261001.log")
            open(log, "w").write("x")
            self.assertTrue(dw.update_laeuft(hier=tmp))
            os.utime(log, (time.time() - 3600, time.time() - 3600))
            self.assertFalse(dw.update_laeuft(hier=tmp))


if __name__ == "__main__":
    unittest.main()
