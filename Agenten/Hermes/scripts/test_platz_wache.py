#!/usr/bin/env python3
"""Tests der Platz-Wache-Reserve - Regeln, keine Tageswerte.

Geprueft wird die REGEL: wann wird aufgeraeumt und wann NICHT, welche Posten
duerfen geloescht werden, und dass eine Messung ueber der Reserve nichts
anfasst. Alle Loeschpfade werden auf ein TEMP-Verzeichnis umgebogen
(`LOCALAPPDATA`) und die Prozessabfrage gefaelscht - echte Caches, echte
Laufwerke und echte Prozesse werden nie angefasst.

Der Anlass steht im Modul selbst: am 30.09.2026 lief C: waehrend eines
Desktop-Baus auf 0,1 GB, der Build brach ab und der Desktop kam in eine
Bootschleife. Deshalb wird hier besonders geprueft, dass ein laufender Bau
JEDES Aufraeumen verhindert.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
import time
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SKRIPT = os.path.join(HIER, "platz-wache.py")


def laden():
    spec = importlib.util.spec_from_file_location("platz_wache", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class Basis(unittest.TestCase):
    """Gemeinsamer Aufbau: Loeschpfade im Temp-Ordner, Prozessabfrage still."""

    def setUp(self):
        self.w = laden()
        self.tmp = tempfile.mkdtemp(prefix="platz-wache-")
        self.alt_local = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.tmp
        self.w._prozess_kommandos = lambda: []      # keine echte Prozessabfrage
        self.w.bau_marker = lambda: []              # keine echten Update-Marker

    def tearDown(self):
        if self.alt_local is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self.alt_local
        shutil.rmtree(self.tmp, ignore_errors=True)

    def temp_datei(self, name: str, alter_h: float, groesse: int = 1024) -> str:
        ordner = os.path.join(self.tmp, "Temp")
        os.makedirs(ordner, exist_ok=True)
        pfad = os.path.join(ordner, name)
        with open(pfad, "wb") as fh:
            fh.write(b"x" * groesse)
        zeit = time.time() - alter_h * 3600
        os.utime(pfad, (zeit, zeit))
        return pfad


class TestBauLaeuft(Basis):
    """Ein laufender Bau ist das Wichtigste: dann wird NICHT geloescht."""

    def test_marker_datei_haelt_auf(self):
        marker = os.path.join(self.tmp, ".hermes-update-in-progress")
        open(marker, "w").close()
        self.assertTrue(self.w.bau_laeuft([__import__("pathlib").Path(marker)], []))

    def test_bau_befehl_haelt_auf(self):
        self.assertTrue(self.w.bau_laeuft([], ["node electron-builder --win"]))
        self.assertTrue(self.w.bau_laeuft([], ["python -m hermes_cli.main update --yes"]))
        self.assertTrue(self.w.bau_laeuft([], ["python source_completion.py --finish-update"]))

    def test_ohne_zeugen_ist_frei(self):
        self.assertFalse(self.w.bau_laeuft([], ["python -m hermes_cli.main gateway run"]))
        self.assertFalse(self.w.bau_laeuft([], []))

    def test_gateway_lauf_ist_kein_bau(self):
        """Der Gateway laeuft immer - er darf das Aufraeumen nicht blockieren."""
        self.assertFalse(self.w.bau_laeuft([], [
            "python.exe -m hermes_cli.main gateway run",
            "node MCP-Server/index.js",
        ]))


class TestSchritte(Basis):
    """Welche Posten duerfen geloescht werden - und welche nie."""

    def test_genau_die_vier_erlaubten(self):
        namen = {name for name, _ in self.w.aufraeum_schritte()}
        self.assertEqual(namen, {"temp", "crashdumps", "uv", "npm"})

    def test_verbotene_ziele_kommen_nicht_vor(self):
        text = " ".join(f"{n} {b}" for n, b in self.w.aufraeum_schritte()).lower()
        for verboten in ("node_modules", ".venv", "pnpm", "modelle", "_backups", "pagefile"):
            self.assertNotIn(verboten, text)

    def test_reserve_deckt_den_build(self):
        """Der Desktop-Build braucht rund 20 GB - die Reserve muss darueber liegen."""
        self.assertGreaterEqual(self.w.SCHWELLEN["frei_c_gb"], 20.0)


class TestReserve(Basis):
    """Wann passiert etwas - und wann nichts."""

    def test_ueber_der_reserve_passiert_nichts(self):
        self.assertEqual(self.w.reserve_aufraeumen({"frei_c_gb": 99.0}), [])

    def test_unbekannter_wert_passiert_nichts(self):
        self.assertEqual(self.w.reserve_aufraeumen({}), [])
        self.assertEqual(self.w.reserve_aufraeumen({"frei_c_gb": None}), [])

    def test_laufender_bau_loescht_nichts(self):
        datei = self.temp_datei("alt.tmp", alter_h=30)
        self.w.bau_laeuft = lambda marker, kommandos: True
        zeilen = self.w.reserve_aufraeumen({"frei_c_gb": 5.0})
        self.assertTrue(any("NICHT geloescht" in z for z in zeilen), zeilen)
        self.assertTrue(os.path.exists(datei), "eine alte Temp-Datei wurde trotz laufendem Bau geloescht")

    def test_trockenlauf_loescht_nichts(self):
        datei = self.temp_datei("alt.tmp", alter_h=30)
        zeilen = self.w.reserve_aufraeumen({"frei_c_gb": 5.0}, trocken=True)
        self.assertTrue(any("wuerde:" in z for z in zeilen), zeilen)
        self.assertTrue(os.path.exists(datei), "der Trockenlauf hat geloescht")

    def test_meldung_nennt_die_reserve(self):
        self.w.bau_laeuft = lambda marker, kommandos: True
        zeilen = self.w.reserve_aufraeumen({"frei_c_gb": 7.0})
        self.assertTrue(zeilen and "Reserve verletzt" in zeilen[0], zeilen)
        self.assertIn(str(self.w.SCHWELLEN["frei_c_gb"]), zeilen[0])


class TestDateienLoeschen(Basis):
    """Das Loeschen selbst: Alter entscheidet, Grenzen werden eingehalten."""

    def test_alte_datei_weg_junge_bleibt(self):
        alt = self.temp_datei("alt.tmp", alter_h=30, groesse=2048)
        jung = self.temp_datei("jung.tmp", alter_h=1, groesse=2048)
        frei = self.w._dateien_loeschen(__import__("pathlib").Path(self.tmp) / "Temp", 24.0)
        self.assertFalse(os.path.exists(alt))
        self.assertTrue(os.path.exists(jung))
        self.assertEqual(frei, 2048)

    def test_fehlender_ordner_ist_null(self):
        self.assertEqual(self.w._dateien_loeschen(__import__("pathlib").Path(self.tmp) / "gibtsnicht", 24.0), 0)

    def test_unterordner_werden_mitgenommen(self):
        unter = os.path.join(self.tmp, "Temp", "tief", "tiefer")
        os.makedirs(unter, exist_ok=True)
        pfad = os.path.join(unter, "alt.tmp")
        with open(pfad, "wb") as fh:
            fh.write(b"y" * 512)
        zeit = time.time() - 48 * 3600
        os.utime(pfad, (zeit, zeit))
        self.w._dateien_loeschen(__import__("pathlib").Path(self.tmp) / "Temp", 24.0)
        self.assertFalse(os.path.exists(pfad))


if __name__ == "__main__":
    unittest.main(verbosity=2)