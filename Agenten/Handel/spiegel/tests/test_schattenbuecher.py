"""Tests der Spiegel-Schattenbuecher 'knapp'/'weit' (V1 Ausstiegsgeometrie).

Der V1-Plan (docs/plans/2026-09-18-v1-ausstiegsgeometrie.md) verdrahtet zwei
Schattenbuecher, die dieselbe Signalquelle mit anderen Stop/Trailing-
Parametern fahren. Das Hauptbuch bleibt die Vergleichsgrundlage.

Geprueft werden laut Plan (Abschnitt "Tests vor der Verdrahtung"):
  - _buch_datei: Suffix bei HANDEL_BUCH=knapp/weit, leerer Suffix ohne
    Variable, Typ bleibt erhalten (str/Path), kein Schreiben.
  - Launcher: subprocess mit gesetzter Variable und --wachen (lesend) ->
    Ausgabe nennt die Arm-Wachen-Werte.
  - Auswertung: --pfad auf ein Arm-Journal (Temp-Kopie) liefert dieselben
    Spalten.
  - Gegenprobe Tor: die 6 Signalfaelle aus dem Filter-Beleg
    (30k/60k/100k/200k/300k/2M) fuer die Arm-Wachen - alle drei Buecher
    muessen identisch entscheiden (die Arme aendern NUR die Ausstiege,
    nicht das Tor).
  - Modulwaechter: kein Test schreibt in spiegel/.

Aufruf:  cd spiegel && python -m unittest discover -s tests -v
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
SPIEGEL = os.path.dirname(HIER)
for p in (HIER, SPIEGEL):
    if p not in sys.path:
        sys.path.insert(0, p)
PYTHON = sys.executable

import spiegel as sp  # noqa: E402

# Die drei Wachen: Hauptbuch + zwei Arme.
BASE = json.load(open(os.path.join(SPIEGEL, "wachen.json"), encoding="utf-8"))
KNAPP = json.load(open(os.path.join(SPIEGEL, "wachen.knapp.json"),
                       encoding="utf-8"))
WEIT = json.load(open(os.path.join(SPIEGEL, "wachen.weit.json"),
                      encoding="utf-8"))

# Signalfaelle des Filter-Belegs (30k/60k/100k/200k/300k/2M) gegen das Tor
# (marketcap_band_usd [250k, 1M]).
TOR_FAELLE = (30_000, 60_000, 100_000, 200_000, 300_000, 2_000_000)


def _modul_waechter():
    """Dateiliste+Groessen von spiegel/ (kein Schreiber weiss)."""
    raus = {}
    for name in os.listdir(SPIEGEL):
        pfad = os.path.join(SPIEGEL, name)
        if os.path.isfile(pfad):
            raus[name] = os.path.getsize(pfad)
    return raus


# Modulwaechter (Hausmuster): am Suite-Beginn die Dateiliste+Groessen des
# ECHTEN Spurenordners merken, am Ende vergleichen. Jeder Test, der in
# spiegel/ schriebe, faellt hier auf.
_SUITE_STAND = None


def setUpModule():
    global _SUITE_STAND
    _SUITE_STAND = _modul_waechter()


def tearDownModule():
    jetzt = _modul_waechter()
    verloren = [n for n in _SUITE_STAND if n not in jetzt]
    neu = [n for n in jetzt if n not in _SUITE_STAND]
    geaendert = [n for n in _SUITE_STAND if n in jetzt
                 and jetzt[n] != _SUITE_STAND[n]]
    if verloren or neu or geaendert:
        raise AssertionError(
            "Suite hat in den echten spiegel/-Ordner geschrieben: "
            "entfernt=%s neu=%s geaendert=%s"
            % (verloren, neu, geaendert))


class BuchDateiTest(unittest.TestCase):
    """_buch_datei: Suffix aus HANDEL_BUCH, sonst leer, Typ erhalten."""

    def tearDown(self):
        os.environ.pop("HANDEL_BUCH", None)

    def test_ohne_variable_leerer_suffix(self):
        os.environ.pop("HANDEL_BUCH", None)
        self.assertEqual(sp._buch_datei("wachen.json"), "wachen.json")

    def test_knapp_suffix(self):
        os.environ["HANDEL_BUCH"] = "knapp"
        self.assertEqual(sp._buch_datei("wachen.json"), "wachen.knapp.json")
        self.assertEqual(sp._buch_datei("handelsjournal.csv"),
                         "handelsjournal.knapp.csv")

    def test_weit_suffix(self):
        os.environ["HANDEL_BUCH"] = "weit"
        self.assertEqual(sp._buch_datei("zustand.json"), "zustand.weit.json")

    def test_typ_bleibt_path(self):
        os.environ["HANDEL_BUCH"] = "knapp"
        aus = sp._buch_datei(Path("wachen.json"))
        self.assertIsInstance(aus, Path)
        self.assertEqual(aus.name, "wachen.knapp.json")

    def test_unbekannter_arm_laesst_suffix_anhaengen(self):
        # Kein Freibrief, nur belegt: der Mechanismus haengt den Variablenwert
        # an. Die Verantwortung fuer gueltige Namen traegt der Launcher.
        os.environ["HANDEL_BUCH"] = "x"
        self.assertEqual(sp._buch_datei("a.csv"), "a.x.csv")


class LauncherTest(unittest.TestCase):
    """subprocess setzt HANDEL_BUCH und zeigt die Arm-Wachen (lesend)."""

    def _wachen_aus(self, launcher):
        r = subprocess.run([PYTHON, launcher, "--wachen"],
                           cwd=SPIEGEL, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_knapp_launcher_zeigt_arm_wachen(self):
        aus = self._wachen_aus("spiegel_knapp.py")
        self.assertIn("trail_aktiv_ab_pct             15.0", aus)
        self.assertIn("trail_abstand_pct              15.0", aus)
        self.assertIn("Q:\\Handel_Journal\\spiegel_knapp", aus)

    def test_weit_launcher_zeigt_arm_wachen(self):
        aus = self._wachen_aus("spiegel_weit.py")
        self.assertIn("trail_aktiv_ab_pct             40.0", aus)
        self.assertIn("trail_abstand_pct              30.0", aus)
        self.assertIn("Q:\\Handel_Journal\\spiegel_weit", aus)


class AuswertungPfadTest(unittest.TestCase):
    """--pfad auf ein Arm-Journal liest ein Arm-Buch (dieselben Spalten)."""

    def test_schattenbuch_lesen(self):
        import io
        import csv
        zeile = ["2026-09-18T00:00:00+00:00", "papier", "schliessen",
                 "solana", "W1", "T1", "AAA", "1.0", "48", "50.00",
                 "0.50", "3.0", "1.0", "stop"]
        with tempfile.TemporaryDirectory() as tmp:
            journal = os.path.join(tmp, "handelsjournal.knapp.csv")
            with open(journal, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=sp.SPALTEN)
                w.writeheader()
                w.writerow({k: v for k, v in zip(sp.SPALTEN, zeile)})
            import auswertung as aw
            aus = aw.lade_ausstiege(journal)
            self.assertTrue(aus)
            a = aus[0]
            for feld in ("kette", "token", "grund"):
                self.assertIn(feld, a)
            self.assertEqual(a["kette"], "solana")


class TorGegenprobeTest(unittest.TestCase):
    """Alle drei Buecher entscheiden am Tor identisch (nur die Ausstiege
    weichen ab - die Arme aendern wachen.knapp/.weit NICHT das Band)."""

    def _entscheid(self, w):
        z = {"positionen": []}
        sig = {"token": "T", "kette": "solana", "wallet": "W1",
               "alter_s": 5.0}
        out = {}
        for mk in TOR_FAELLE:
            s = dict(sig, marktkap_usd=mk)
            grund = sp._vorpruefung(s, w, z)
            out[mk] = "kaufbar" if grund[0] is None else grund[0]
        return out

    def test_tor_identisch_in_drei_buechern(self):
        self.assertEqual(self._entscheid(BASE),
                         self._entscheid(KNAPP))
        self.assertEqual(self._entscheid(BASE),
                         self._entscheid(WEIT))

    def test_tor_band_wirklich_das_hauptbuch(self):
        # Das Band ist [250k, 1M]: darunter und darueber ausserhalb, im Band
        # kaufbar. 300k ist im Band -> kaufbar; 30k/60k/100k/200k/2M nicht.
        e = self._entscheid(BASE)
        self.assertEqual(e[300_000], "kaufbar")
        for mk in (30_000, 60_000, 100_000, 200_000, 2_000_000):
            self.assertEqual(e[mk], "marktkap ausserhalb")


class ModulWaechterTest(unittest.TestCase):
    """Kein Test schreibt in den echten spiegel/-Ordner (setUpModule/tearDown)."""

    def test_suite_schreibt_nicht(self):
        self.assertTrue(_SUITE_STAND)
        self.assertTrue(True)  # die eigentliche Pruefung laeuft in tearDownModule


if __name__ == "__main__":
    unittest.main(verbosity=2)