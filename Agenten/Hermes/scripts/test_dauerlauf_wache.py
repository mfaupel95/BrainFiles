#!/usr/bin/env python3
"""Tests der Dauerlauf-Wache (T-193) - Regeln, keine Tageswerte.

Aufbau: Jeder Fall baut ein TEMP-Verzeichnis mit Sperrdatei, Protokoll und
Waechter-Protokoll, biegt die Pfade am geladenen Modul um und fragt die reine
Funktion. Geprueft wird die REGEL (welcher Befund bei welchem Zustand), nicht
der heutige Zustand des Rechners.

Besonders wichtig: die Wache darf NICHTS beenden. Das wird an der Quelle
geprueft (kein Stop-Process/taskkill/os.kill im Text) UND durch die Naht:
`prozess_mit_startzeit` ist im Test gefaelscht, ein echter Prozess wird nie
angefasst.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
import time
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SKRIPT = os.path.join(HIER, "dauerlauf-wache.py")


def laden():
    spec = importlib.util.spec_from_file_location("dauerlauf_wache", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class Basis(unittest.TestCase):
    """Gemeinsamer Aufbau: Temp-Ordner, Pfade umgebogen, Prozessantwort gefaelscht."""

    lebende = set()

    def setUp(self):
        self.w = laden()
        self.tmp = tempfile.mkdtemp(prefix="dauerlauf-wache-")
        self.handel = os.path.join(self.tmp, "Handel")
        self.wrapper = os.path.join(self.tmp, "logs")
        os.makedirs(self.handel)
        os.makedirs(self.wrapper)
        self.w.HANDEL = self.handel
        self.w.WRAPPER_LOGS = self.wrapper
        self.w.MERKDATEI = os.path.join(self.tmp, "merker.json")
        # Naht: kein echter Prozess wird befragt.
        self.w.prozess_mit_startzeit = lambda pid: (pid in Basis.lebende, "python.exe")
        self.w.startzeit_passt = lambda pid, zeit: True

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        Basis.lebende = set()

    # ---- Werkzeuge -----------------------------------------------------
    def sperre(self, suffix, pid, startzeit=1000.0):
        with open(os.path.join(self.handel, "dauerlauf%s.pid" % suffix),
                  "w", encoding="ascii") as f:
            f.write("%d %r\n" % (pid, startzeit))

    def protokoll(self, suffix, zeilen, alter_s=0):
        p = os.path.join(self.handel, "dauerlauf%s.log" % suffix)
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n")
        wenn = time.time() - alter_s
        os.utime(p, (wenn, wenn))

    def waechterlog(self, suffix, zeilen):
        p = os.path.join(self.wrapper, "handel-dauerlauf-letzter-lauf%s.log" % suffix)
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n")

    def jetzt_str(self, abzug_s=0):
        import datetime as dt
        return (dt.datetime.now() - dt.timedelta(seconds=abzug_s)).strftime(
            "%Y-%m-%d %H:%M:%S")


class RegelnTest(Basis):

    def test_gesund_meldet_nichts(self):
        """Lauf lebt, Protokoll frisch -> leere Ausgabe (die Wache ist still)."""
        Basis.lebende = {4242}
        self.sperre("", 4242)
        self.protokoll("", ["30.09. 13:22:20  iv_wand (papier) ok"], alter_s=60)
        schluessel, text = self.w.stufe_pruefen("niedrig", "")
        self.assertIsNone(schluessel, text)

    def test_143_wird_als_sigterm_gemeldet(self):
        """Der belegte Todesfall: Kind stirbt mit 143, der Lauf ist danach tot."""
        self.sperre("", 67500)
        self.protokoll("", [
            "30.09. 02:34:26  Dauerlauf startet, Takt 15 min",
            "30.09. 02:36:55  kraken (live) Rueckgabe 143",
        ], alter_s=600)
        schluessel, text = self.w.stufe_pruefen("niedrig", "")
        self.assertEqual(schluessel, "tot-143")
        self.assertIn("kraken", text)
        self.assertIn("143", text)

    def test_tod_ohne_spur_wird_unterschieden(self):
        """Kein Rueckgabecode in der letzten Zeile -> eigener Befund (Speicherdruck)."""
        self.sperre(".mittel", 61436)
        self.protokoll(".mittel", ["30.09. 01:58:00  spiegel (papier) ok"],
                       alter_s=3 * 3600)
        schluessel, text = self.w.stufe_pruefen("mittel", ".mittel")
        self.assertEqual(schluessel, "tot-spurlos")
        self.assertIn("61436", text)

    def test_haengt_wenn_prozess_lebt_und_protokoll_alt(self):
        Basis.lebende = {4280}
        self.sperre(".hoch", 4280)
        self.protokoll(".hoch", ["30.09. 09:00:00  orb (papier) ok"], alter_s=3 * 3600)
        schluessel, text = self.w.stufe_pruefen("hoch", ".hoch")
        self.assertEqual(schluessel, "haengt")
        self.assertIn("4280", text)

    def test_ohne_sperre_und_altes_protokoll(self):
        self.protokoll("", ["29.09. 23:22:59  xperp (papier) Rueckgabe 143"],
                       alter_s=5 * 3600)
        schluessel, _ = self.w.stufe_pruefen("niedrig", "")
        self.assertEqual(schluessel, "ohne-sperre")

    def test_wiederverwendete_pid_gilt_als_tot(self):
        """Numme lebt, aber mit ANDERER Startzeit -> nicht unser Lauf."""
        Basis.lebende = {999}
        self.sperre("", 999, startzeit=1000.0)
        self.protokoll("", ["30.09. 02:36:55  kraken (live) Rueckgabe 143"],
                       alter_s=600)
        self.w.startzeit_passt = lambda pid, zeit: False
        schluessel, _ = self.w.stufe_pruefen("niedrig", "")
        self.assertEqual(schluessel, "tot-143")

    def test_anderer_rueckgabecode_wird_benannt(self):
        self.sperre("", 4711)
        self.protokoll("", ["30.09. 10:12:36  nautilus_kraken (papier) Rueckgabe 3221226505"],
                       alter_s=600)
        schluessel, text = self.w.stufe_pruefen("niedrig", "")
        self.assertEqual(schluessel, "tot-code")
        self.assertIn("3221226505", text)

    def test_traceback_als_letzte_zeile(self):
        Basis.lebende = {4242}
        self.sperre("", 4242)
        self.protokoll("", ["30.09. 13:00:00  irgendwas (papier) ok",
                            "Traceback (most recent call last):"], alter_s=60)
        schluessel, _ = self.w.stufe_pruefen("niedrig", "")
        self.assertEqual(schluessel, "traceback")


class ChurnTest(Basis):

    def test_churn_erst_ab_der_grenze(self):
        """Zwei verwaiste Sperren sind Ruhe, drei sind der Befund vom 30.09."""
        self.waechterlog("", [
            "%s  verwaiste Sperre (PID 1 lebt nicht mehr) - wird ersetzt" % self.jetzt_str(600),
            "%s  verwaiste Sperre (PID 2 lebt nicht mehr) - wird ersetzt" % self.jetzt_str(400),
        ])
        schluessel, _ = self.w.churn_pruefen()
        self.assertIsNone(schluessel)

        self.waechterlog("", [
            "%s  verwaiste Sperre (PID 1 lebt nicht mehr) - wird ersetzt" % self.jetzt_str(600),
            "%s  verwaiste Sperre (PID 2 lebt nicht mehr) - wird ersetzt" % self.jetzt_str(400),
            "%s  verwaiste Sperre (PID 3 lebt nicht mehr) - wird ersetzt" % self.jetzt_str(200),
        ])
        schluessel, text = self.w.churn_pruefen()
        self.assertEqual(schluessel, "churn")
        self.assertIn("3 verwaiste Sperren", text)

    def test_alte_zeilen_zaehlen_nicht(self):
        """Der Churn vom 30.09. darf heute nicht mehr gemeldet werden."""
        self.waechterlog("", [
            "%s  verwaiste Sperre (PID %d lebt nicht mehr) - wird ersetzt"
            % (self.jetzt_str(3 * 3600), i) for i in range(5)
        ])
        schluessel, _ = self.w.churn_pruefen()
        self.assertIsNone(schluessel)


class MeldungTest(Basis):

    def test_befund_wiederholt_sich_nicht_vor_dem_fenster(self):
        befunde = [("tot-143", "text")]
        jetzt = time.time()
        neu = self.w.neu_zu_melden(befunde, {"tot-143": jetzt - 60}, jetzt)
        self.assertEqual(neu, [])

    def test_nach_dem_fenster_wieder_gemeldet(self):
        befunde = [("tot-143", "text")]
        jetzt = time.time()
        neu = self.w.neu_zu_melden(befunde, {"tot-143": jetzt - 7 * 3600}, jetzt)
        self.assertEqual(len(neu), 1)

    def test_unbekannter_befund_wird_gemeldet(self):
        neu = self.w.neu_zu_melden([("neu", "text")], {}, time.time())
        self.assertEqual(len(neu), 1)


class SicherheitTest(unittest.TestCase):

    def test_wache_beendet_nichts(self):
        """Die Wache darf keinen Prozess anfassen - geprueft am CODE, nicht am Text.

        Der Modulkopf NENNT die gemessenen Fingerabdruecke (taskkill, Stop-Process,
        os.kill) als Beleg - ein Textvergleich wuerde daran scheitern. Geprueft
        werden deshalb die tatsaechlich benutzten Namen und Attribute.
        """
        import ast
        with open(SKRIPT, encoding="utf-8") as f:
            baum = ast.parse(f.read())
        verboten = {"Stop-Process", "taskkill", "kill", "terminate",
                    "TerminateProcess", "Popen", "killall", "pkill"}
        benutzt = set()
        befehle = set()
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Name):
                benutzt.add(knoten.id)
            elif isinstance(knoten, ast.Attribute):
                benutzt.add(knoten.attr)
            elif isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
                befehle.add(knoten.value)
        treffer = verboten & benutzt
        self.assertEqual(treffer, set(), "die Wache beendet Prozesse: %s" % treffer)
        # Der einzige aufgerufene Fremdbefehl darf das lesende tasklist sein.
        fremd = {b for b in befehle if b in ("tasklist", "taskkill", "wmic",
                                             "powershell", "schtasks")}
        self.assertEqual(fremd, {"tasklist"}, "unerlaubter Fremdbefehl: %s" % fremd)

    def test_wache_schreibt_nur_ihre_merkdatei(self):
        """Geschrieben wird genau eine Datei: der Merker. Kein Zustand, kein Journal."""
        with open(SKRIPT, encoding="utf-8") as f:
            quelle = f.read()
        self.assertIn('open(MERKDATEI, "w"', quelle)
        for pfad in ("zustand", "handelsjournal", "freigabe"):
            self.assertNotIn('open(os.path.join(HANDEL, "%s' % pfad, quelle)

    def test_stufen_entsprechen_der_hausregel(self):
        """Die Dateinamen-Zusaatze muessen zu risikostufe.suffix_fuer() passen."""
        w = laden()
        handel = os.path.join(os.path.dirname(SKRIPT), "..", "..", "Handel")
        sys_path_ziel = os.path.abspath(handel)
        import sys
        sys.path.insert(0, sys_path_ziel)
        try:
            import risikostufe
        finally:
            sys.path.remove(sys_path_ziel)
        for name, suffix in w.STUFEN:
            self.assertEqual(risikostufe.suffix_fuer(name), suffix,
                             "Zusatz fuer %s weicht ab" % name)


if __name__ == "__main__":
    unittest.main(verbosity=2)