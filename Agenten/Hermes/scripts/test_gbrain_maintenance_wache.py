"""Tests fuer gbrain-maintenance-wache.py.

Kein echter wsl-Aufruf: die Naht `lauf` wird gesetzt. Die Merkdatei wird je
Test in einen Temp-Ordner gebogen.

Der Kern ist `test_faktbestand_gefallen_wird_gemeldet`: der Schaden vom
08.10.2026 war, dass `stats` 0 Seiten zeigte, waehrend 44 Fakten im Gehirn
lagen. Die Wache muss an der FAKTENZAHL haengen, nicht an der Seitenzahl.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location(
    "gbrain_wache", str(HIER / "gbrain-maintenance-wache.py"))
gw = importlib.util.module_from_spec(spec)
sys.modules["gbrain_wache"] = gw
spec.loader.exec_module(gw)

FAST_OK = json.dumps({"status": "warnings", "health_score": 90,
                      "checks": [{"name": "connection", "status": "warn"}],
                      "top_issues": []})


def recall_ausgabe(n: int) -> str:
    return "\n".join(
        f"\U0001f4cc id={i} [projects/x] Fakt {i} (fact, conf 1.00)"
        for i in range(1, n + 1))


def fake_lauf(antworten):
    """antworten: Liste von (rc, stdout, stderr) je Aufruf, in Reihenfolge."""
    aufrufe = []

    def lauf(argumente, frist=180):
        aufrufe.append(argumente)
        if not antworten:
            return (0, "", "")
        return antworten.pop(0)

    return lauf, aufrufe


class Basis(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="gbrain-wache-test-"))
        self.stand = self.tmp / "gbrain-wache-stand.json"
        gw.STAND = self.stand
        self._alt = gw.lauf
        self._argv = sys.argv

    def tearDown(self) -> None:
        gw.lauf = self._alt
        sys.argv = self._argv
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ausgabe(self) -> str:
        import io
        import contextlib
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            gw.main()
        return puffer.getvalue()

    def stand_lesen(self):
        return json.loads(self.stand.read_text(encoding="utf-8"))


class TestFaktbestand(Basis):
    def test_faktbestand_gefallen_wird_gemeldet(self):
        """44 -> 12 Fakten: melden. Der volle Doctor liefert die Ursache."""
        self.stand.write_text(json.dumps({"schema": 1, "fakten": 44, "hoechste": 44}),
                              encoding="utf-8")
        gw.lauf, aufrufe = fake_lauf([
            (0, FAST_OK, ""),                                  # doctor --fast
            (0, recall_ausgabe(12), ""),                       # recall
            (1, json.dumps({"top_issues": [
                {"name": "sync_freshness", "status": "fail",
                 "fix": "Source 'default' has never been synced."}]}), ""),  # doctor --json
        ])
        aus = self.ausgabe()
        self.assertIn("FAKTBESTAND GEFALLEN", aus)
        self.assertIn("Hoechststand 44, jetzt 12", aus)
        self.assertIn("sync_freshness", aus)
        self.assertEqual(self.stand_lesen()["fakten"], 12, "neuer Stand nicht gemerkt")

    def test_stabiler_bestand_schweigt(self):
        self.stand.write_text(json.dumps({"schema": 1, "fakten": 44, "hoechste": 44}),
                              encoding="utf-8")
        gw.lauf, _ = fake_lauf([(0, FAST_OK, ""), (0, recall_ausgabe(44), "")])
        self.assertEqual(self.ausgabe().strip(), "", "kein Befund, aber Ausgabe")

    def test_gewachsener_bestand_schweigt_und_merkt(self):
        self.stand.write_text(json.dumps({"schema": 1, "fakten": 44, "hoechste": 44}),
                              encoding="utf-8")
        gw.lauf, _ = fake_lauf([(0, FAST_OK, ""), (0, recall_ausgabe(46), "")])
        self.assertEqual(self.ausgabe().strip(), "")
        self.assertEqual(self.stand_lesen()["fakten"], 46)

    def test_erster_lauf_meldet_nicht(self):
        """Ohne Merkdatei: nur merken, kein Alarm beim Einrichten."""
        gw.lauf, _ = fake_lauf([(0, FAST_OK, ""), (0, recall_ausgabe(44), "")])
        self.assertEqual(self.ausgabe().strip(), "")
        self.assertEqual(self.stand_lesen()["fakten"], 44)

    def test_recall_unlesbar_wird_gemeldet(self):
        self.stand.write_text(json.dumps({"schema": 1, "fakten": 44, "hoechste": 44}),
                              encoding="utf-8")
        gw.lauf, _ = fake_lauf([(0, FAST_OK, ""), (1, "", "boom")])
        aus = self.ausgabe()
        self.assertIn("nicht lesbar", aus)
        self.assertEqual(self.stand_lesen()["fakten"], 44, "Stand darf nicht fallen")


class TestTripwire(Basis):
    def test_loeschender_befehl_wird_gewarnt(self):
        """Nennt der Doctor reinit-pglite, wird gewarnt - vor der Ausfuehrung."""
        fast = json.dumps({"status": "warnings", "health_score": 90, "checks": [],
                           "top_issues": [{"name": "embedding_width_consistency",
                                           "status": "warn",
                                           "fix": "Wipe-and-reinit is the only path"}]})
        gw.lauf, _ = fake_lauf([(0, fast, ""), (0, recall_ausgabe(44), "")])
        aus = self.ausgabe()
        self.assertIn("LOESCHENDEN Befehl", aus)
        self.assertIn("reinit", aus)
        self.assertIn("backup create", aus)

    def test_ohne_loeschwort_keine_warnung(self):
        gw.lauf, _ = fake_lauf([(0, FAST_OK, ""), (0, recall_ausgabe(44), "")])
        self.assertNotIn("LOESCHENDEN", self.ausgabe())


class TestDoctor(Basis):
    def test_launcher_weg_wird_gemeldet(self):
        gw.lauf, _ = fake_lauf([(-1, "", "wsl.exe nicht gefunden (WSL2 fehlt?)"),
                                (-1, "", "weg")])
        aus = self.ausgabe()
        self.assertIn("nicht erreichbar", aus)

    def test_fast_exit_fehler_wird_gemeldet(self):
        gw.lauf, _ = fake_lauf([(2, "", "kaputt"), (0, recall_ausgabe(44), "")])
        self.assertIn("doctor --fast Exit 2", self.ausgabe())

    def test_doctor_error_wird_gemeldet(self):
        fast = json.dumps({"status": "error", "health_score": 10,
                           "checks": [{"name": "connection", "status": "error",
                                       "message": "keine Verbindung"}],
                           "top_issues": []})
        gw.lauf, _ = fake_lauf([(0, fast, ""), (0, recall_ausgabe(44), "")])
        aus = self.ausgabe()
        self.assertIn("Doctor-Status error", aus)
        self.assertIn("keine Verbindung", aus)


class TestVerben(Basis):
    def test_stand_setzen_und_zeigen(self):
        gw.lauf, _ = fake_lauf([(0, recall_ausgabe(44), "")])
        sys.argv = ["wache", "--stand-setzen"]
        self.assertIn("44 Fakten", self.ausgabe())
        gw.lauf, _ = fake_lauf([(0, recall_ausgabe(44), "")])
        sys.argv = ["wache", "--stand-zeigen"]
        aus = self.ausgabe()
        self.assertIn("44", aus)
        self.assertIn("Merkdatei", aus)

    def test_stand_setzen_ohne_recall_setzt_nicht(self):
        gw.lauf, _ = fake_lauf([(1, "", "boom")])
        sys.argv = ["wache", "--stand-setzen"]
        self.assertIn("NICHT gesetzt", self.ausgabe())
        self.assertFalse(self.stand.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestSchwelle(Basis):
    """Der Bestand schwankt: Sitzungen schreiben UND nehmen zurueck.

    Gemessen 08.10.2026: 46 -> 41 in einer Stunde, alles gewollte `forget`s.
    Nur ein Rueckgang ueber die Schwelle ist ein Befund.
    """

    def test_kleiner_rueckgang_meldet_nicht(self):
        self.stand.write_text(json.dumps({"schema": 1, "fakten": 44, "hoechste": 44}),
                              encoding="utf-8")
        gw.lauf, _ = fake_lauf([(0, FAST_OK, ""), (0, recall_ausgabe(42), "")])
        self.assertEqual(self.ausgabe().strip(), "", "Fehlalarm bei gewolltem forget")
        stand = self.stand_lesen()
        self.assertEqual(stand["fakten"], 42, "Stand nicht nachgefuehrt")
        self.assertEqual(stand["hoechste"], 44, "Hoechststand darf nicht sinken")

    def test_rueckgang_ueber_der_schwelle_meldet(self):
        self.stand.write_text(json.dumps({"schema": 1, "fakten": 44, "hoechste": 44}),
                              encoding="utf-8")
        gw.lauf, _ = fake_lauf([
            (0, FAST_OK, ""),
            (0, recall_ausgabe(38), ""),
            (1, json.dumps({"top_issues": []}), ""),
        ])
        aus = self.ausgabe()
        self.assertIn("FAKTBESTAND GEFALLEN", aus)
        self.assertIn("Hoechststand 44", aus)
        self.assertIn("jetzt 38", aus)

    def test_schleichender_verlust_wird_erkannt(self):
        """Vier Laeufe mit je -2: einzeln harmlos, gegen den Hoechststand nicht."""
        self.stand.write_text(json.dumps({"schema": 1, "fakten": 44, "hoechste": 44}),
                              encoding="utf-8")
        gw.lauf, _ = fake_lauf([(0, FAST_OK, ""), (0, recall_ausgabe(42), "")])
        self.assertEqual(self.ausgabe().strip(), "")
        self.assertEqual(self.stand_lesen()["hoechste"], 44)

        gw.lauf, _ = fake_lauf([(0, FAST_OK, ""), (0, recall_ausgabe(40), "")])
        self.assertEqual(self.ausgabe().strip(), "")

        gw.lauf, _ = fake_lauf([
            (0, FAST_OK, ""), (0, recall_ausgabe(38), ""),
            (1, json.dumps({"top_issues": []}), "")])
        self.assertIn("FAKTBESTAND GEFALLEN", self.ausgabe())


if __name__ == "__main__":
    unittest.main(verbosity=2)
