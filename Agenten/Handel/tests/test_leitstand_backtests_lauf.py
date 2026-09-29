"""Laufsteuerung: Ausgabe kommt an, nur ein Lauf gleichzeitig, Abbruch wirkt
(auch auf Kindprozesse), Ablagedatei ist vollstaendig.

Gestartet werden Mini-Skripte aus einem Temp-Ordner mit sys.executable; die
Ablage liegt ebenfalls im Temp-Ordner. Kein Netz, kein echtes daten/backtest/.

Direkt ausfuehrbar:  python tests/test_leitstand_backtests_lauf.py
"""

import json
import os
import re
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitstand_laeufe as ll                                  # noqa: E402

ECHO = """
import json
print("zeile 1")
print("zeile 2")
print(json.dumps({"runden": 3}, indent=2))
"""

FEHLER = """
import sys
sys.stderr.write("kaputt\\n")
sys.exit(3)
"""

SCHLAEFER = """
import time
print("start", flush=True)
time.sleep(60)
"""

# Startet ein Kind, das alle 0,1 s die Uhr in eine Datei schreibt, und
# schlaeft dann selbst. Lebt das Kind nach dem Abbruch weiter, aendert sich
# die Datei weiter.
MIT_KIND = """
import subprocess, sys, time
herz = sys.argv[1]
kind = ("import time\\n"
        "while True:\\n"
        "    open(%r, 'w').write(str(time.monotonic()))\\n"
        "    time.sleep(0.1)\\n" % herz)
subprocess.Popen([sys.executable, "-c", kind], stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL)
print("kind gestartet", flush=True)
time.sleep(60)
"""


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ablage = self.tmp / "ablage"
        self.st = ll.Steuerung(self.ablage)
        self.addCleanup(self._aufraeumen)

    def _aufraeumen(self):
        if self.st.lauf:
            self.st.abbrechen()
            self.bis_fertig(frist=20)
        # Temp-Ordner bleibt bei Windows-Sperren notfalls liegen
        for p in sorted(self.tmp.rglob("*"), reverse=True):
            try:
                p.unlink() if p.is_file() else p.rmdir()
            except OSError:
                pass

    def skript(self, name, text):
        p = self.tmp / name
        p.write_text(textwrap.dedent(text), encoding="utf-8")
        return [sys.executable, str(p)]

    def bis_fertig(self, frist=30):
        zeilen, ende = [], None
        schluss = time.monotonic() + frist
        while ende is None:
            if time.monotonic() > schluss:
                self.fail("Lauf nicht fertig nach %d s" % frist)
            neu, ende = self.st.takt()
            zeilen += neu
            time.sleep(0.05)
        return zeilen, ende

    def bis_zeile(self, text, frist=20):
        schluss = time.monotonic() + frist
        gesehen = []
        while time.monotonic() < schluss:
            neu, ende = self.st.takt()
            gesehen += neu
            if any(text in z for z in gesehen):
                return
            self.assertIsNone(ende, "Lauf endete vor %r" % text)
            time.sleep(0.05)
        self.fail("Zeile %r kam nicht" % text)


class Ablauf(Basis):
    def test_ausgabe_kommt_an_und_ablage_vollstaendig(self):
        self.st.starte("mini", self.skript("echo.py", ECHO),
                       auswerten=ll.json_aus_ausgabe)
        zeilen, (pfad, daten) = self.bis_fertig()
        self.assertEqual(zeilen[:2], ["zeile 1\n", "zeile 2\n"])
        self.assertRegex(pfad.name, r"^\d{8}-\d{6}-mini\.json$")
        gelesen = json.loads(pfad.read_text(encoding="utf-8"))
        self.assertEqual(set(gelesen), {"name", "befehl", "start", "ende", "dauer_s",
                                        "exit_code", "abgebrochen", "ausgabe",
                                        "ergebnis"})
        self.assertEqual(gelesen["exit_code"], 0)
        self.assertFalse(gelesen["abgebrochen"])
        self.assertEqual(gelesen["ergebnis"], {"runden": 3})
        self.assertIn("zeile 2", gelesen["ausgabe"])
        self.assertEqual(daten, gelesen)
        self.assertFalse(list(self.ablage.glob("*.tmp")))

    def test_stderr_und_exit_code_landen_in_der_ablage(self):
        self.st.starte("fehler", self.skript("fehler.py", FEHLER))
        _z, (_p, daten) = self.bis_fertig()
        self.assertEqual(daten["exit_code"], 3)
        self.assertIn("kaputt", daten["ausgabe"])
        self.assertNotIn("ergebnis", daten)

    def test_nur_ein_lauf_gleichzeitig(self):
        self.st.starte("lang", self.skript("s.py", SCHLAEFER))
        self.bis_zeile("start")
        with self.assertRaisesRegex(RuntimeError, "es läuft schon: lang"):
            self.st.starte("zweiter", self.skript("e.py", ECHO))
        self.assertTrue(self.st.laeuft())
        self.assertIn("Backtest: lang läuft seit 0:", self.st.status())

    def test_abbruch_wirkt(self):
        self.st.starte("lang", self.skript("s.py", SCHLAEFER))
        self.bis_zeile("start")
        t0 = time.monotonic()
        self.st.abbrechen()
        _z, (_p, daten) = self.bis_fertig(frist=15)
        self.assertLess(time.monotonic() - t0, 15)
        self.assertTrue(daten["abgebrochen"])
        self.assertNotEqual(daten["exit_code"], 0)
        self.assertFalse(self.st.laeuft())
        self.assertEqual(self.st.status(), "")

    def test_abbruch_beendet_auch_kindprozesse(self):
        herz = self.tmp / "herz.txt"
        befehl = self.skript("k.py", MIT_KIND) + [str(herz)]
        self.st.starte("kind", befehl)
        self.bis_zeile("kind gestartet")
        schluss = time.monotonic() + 10
        while not herz.exists() and time.monotonic() < schluss:
            time.sleep(0.05)
        self.assertTrue(herz.exists(), "Kind hat nie geschrieben")
        self.st.abbrechen()
        self.bis_fertig(frist=15)
        time.sleep(1.0)
        vorher = herz.read_text()
        time.sleep(1.0)
        self.assertEqual(herz.read_text(), vorher,
                         "Kindprozess rechnet nach dem Abbruch weiter")


class Hilfen(unittest.TestCase):
    def test_kuerzen_behaelt_das_ende(self):
        t = ll.kuerze("a" * 10 + "b" * 10, 10)
        self.assertTrue(t.startswith("[… 10 Zeichen am Anfang gekürzt]"))
        self.assertTrue(t.endswith("b" * 10))
        self.assertEqual(ll.kuerze("kurz", 10), "kurz")

    def test_json_aus_ausgabe_mit_hinweiszeilen(self):
        text = ("Zeitraum angehoben: 6 Monate im 4H-Takt ...\n"
                "{\n  \"a\": {\n    \"b\": 1\n  }\n}\n"
                "Trockenlauf: nichts gerechnet, nichts geschrieben.\n")
        self.assertEqual(ll.json_aus_ausgabe(text), {"a": {"b": 1}})
        self.assertIsNone(ll.json_aus_ausgabe("nur Text\n"))
        self.assertIsNone(ll.json_aus_ausgabe("{kaputt\n"))

    def test_json_aus_ausgabe_nimmt_das_letzte(self):
        self.assertEqual(ll.json_aus_ausgabe('{"x": 1}\n{"x": 2}\n'), {"x": 2})

    def test_sicherer_name(self):
        self.assertEqual(ll.sicherer_name("einzel-ORB (xperp)"), "einzel-ORB_xperp")
        self.assertEqual(ll.sicherer_name("///"), "lauf")

    def test_zeitstempel_format(self):
        self.assertRegex(ll.zeitstempel(), r"^\d{8}-\d{6}$")


class Liste(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.o = Path(self.tmp.name)

    def _lauf(self, datei, **felder):
        d = {"name": "a", "befehl": ["py", "x.py"], "start": "s", "ende": "e",
             "dauer_s": 75.0, "exit_code": 0, "abgebrochen": False, "ausgabe": ""}
        d.update(felder)
        (self.o / datei).write_text(json.dumps(d), encoding="utf-8")

    def test_neueste_zuerst_unlesbar_benannt_vorschau_ausgelassen(self):
        self._lauf("20260101-000000-a.json")
        (self.o / "20260102-000000-b.json").write_text("{kaputt", encoding="utf-8")
        (self.o / "20260103-000000-urteile-vorschau.json").write_text("{}",
                                                                    encoding="utf-8")
        liste = ll.laufliste(self.o)
        self.assertEqual([d["datei"] for d in liste],
                         ["20260102-000000-b.json", "20260101-000000-a.json"])
        self.assertEqual(liste[0]["name"], "nicht lesbar")
        zeilen = ll.listen_zeilen(liste)
        self.assertEqual(zeilen[0][1], "nicht lesbar")
        self.assertEqual(zeilen[1], ("20260101-000000-a.json", "a", "s", "1:15", "ok"))

    def test_ergebnisspalte(self):
        self._lauf("1.json", abgebrochen=True, exit_code=1)
        self._lauf("2.json", exit_code=2)
        erg = {z[0]: z[4] for z in ll.listen_zeilen(ll.laufliste(self.o))}
        self.assertEqual(erg, {"1.json": "abgebrochen", "2.json": "Exit 2"})

    def test_fehlender_ordner_ist_leere_liste(self):
        self.assertEqual(ll.laufliste(self.o / "gibtsnicht"), [])


class Vergleich(unittest.TestCase):
    A = {"ergebnis": {"spur": "squeeze", "runden": 10, "kennzahlen": {"ev": 0.5}}}
    B = {"ergebnis": {"spur": "squeeze", "runden": 12,
                      "kennzahlen": {"ev": 0.25, "neu": 1}}}

    def test_nebeneinander_mit_differenz(self):
        z = {r[0]: r[1:] for r in ll.vergleich(self.A, self.B)}
        self.assertEqual(z["runden"], ("10", "12", "2"))
        self.assertEqual(z["ev"], ("0.5", "0.25", "-0.25"))
        self.assertEqual(z["neu"], ("", "1", ""))
        self.assertEqual(z["spur"], ("squeeze", "squeeze", ""))

    def test_ohne_ergebnis_wirft(self):
        with self.assertRaises(ValueError):
            ll.vergleich(self.A, {"ausgabe": "x"})

    def test_einzelergebnis_und_gegenprobe(self):
        z = ll.ergebnis_zeilen({"ergebnis": {"gleich": True, "abweichungen": [],
                                             "runden": 4, "runden_alt": 4}})
        self.assertIn(("gleich", "True", "", ""), z)
        self.assertEqual(ll.ergebnis_zeilen({}),
                         [("Ergebnis", "kein Replay-Ergebnis", "", "")])


if __name__ == "__main__":
    unittest.main()
