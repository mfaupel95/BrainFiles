"""Der Schattenarm 'weit' der OmniQuant-Spur (24.09.2026, Auftrag Max).

Geprueft wird die REGEL, nicht ein eingefrorener Stand:
  * die Arm-Namen haengen zusammen (HANDEL_BUCH=weit -> wachen.weit.json,
    zustand.weit.json, handelsjournal.weit.csv, neuester.weit.json),
  * der Hauptarm bleibt ohne die Variable unveraendert,
  * die weiche Prognose-Fassung ist in JEDEM der drei Tore weiter als die
    strenge - sonst waere der Arm kein Schattenarm,
  * beide Fassungen schreiben in VERSCHIEDENE Dateien (kein Ueberschreiben).

Die Pfade werden in einem Kindprozess erfragt: die Konstanten entstehen beim
Import, ein Test im eigenen Prozess wuerde eine schon geladene Fassung messen.
Kein Netz, keine Order, keine echten Buchdateien (nur ihre NAMEN).
"""

import json
import os
import subprocess
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
SPUR = os.path.join(HANDEL, "omniquant")
PYTHON = sys.executable

FRAGE = r"""
import json, os, sys
sys.path.insert(0, r"{spur}")
sys.path.insert(0, r"{handel}")
if sys.argv[1]:
    os.environ["HANDEL_BUCH"] = sys.argv[1]
import handeln as h
print(json.dumps({{
    "wachen": os.path.basename(h.WACHEN),
    "zustand": os.path.basename(h.ZUSTAND),
    "journal": os.path.basename(h.JOURNAL),
    "bericht": os.path.basename(h.DEFAULT_BERICHT),
}}))
"""


def pfade(arm=""):
    p = subprocess.run([PYTHON, "-c", FRAGE.format(spur=SPUR, handel=HANDEL), arm],
                       capture_output=True, text=True, encoding="utf-8",
                       cwd=SPUR, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert p.returncode == 0, p.stderr[-600:]
    return json.loads(p.stdout.strip().splitlines()[-1])


class ArmPfadeTest(unittest.TestCase):

    def test_weit_haengt_an_jeder_buchdatei(self):
        d = pfade("weit")
        self.assertEqual(d["wachen"], "wachen.weit.json")
        self.assertEqual(d["zustand"], "zustand.weit.json")
        self.assertEqual(d["journal"], "handelsjournal.weit.csv")
        self.assertEqual(d["bericht"], "neuester.weit.json")

    def test_hauptarm_bleibt_unveraendert(self):
        d = pfade("")
        self.assertEqual(d["wachen"], "wachen.json")
        self.assertEqual(d["zustand"], "zustand.json")
        self.assertEqual(d["journal"], "handelsjournal.csv")
        self.assertEqual(d["bericht"], "neuester.json")

    def test_arme_teilen_keine_datei(self):
        a, b = pfade(""), pfade("weit")
        self.assertEqual(len(set(a.values()) & set(b.values())), 0)


class BerichtNamenTest(unittest.TestCase):
    """Die Fassung des Berichts folgt der FORM der Buchdateien (Punkt)."""

    def _name(self, fassung, name):
        code = ("import os,sys;sys.path.insert(0,%r);"
                "os.environ['PROGNOSE_FASSUNG']=%r;import prognose;p=prognose._fassung(%r);"
                "print(p)" % (HANDEL, fassung, name))
        p = subprocess.run([PYTHON, "-c", code], capture_output=True, text=True,
                           encoding="utf-8", cwd=HANDEL,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        assert p.returncode == 0, p.stderr[-400:]
        return p.stdout.strip().splitlines()[-1]

    def test_ohne_fassung_unveraendert(self):
        self.assertEqual(self._name("", "neuester.json"), "neuester.json")

    def test_weit_nennt_dieselbe_form_wie_die_buecher(self):
        self.assertEqual(self._name("weit", "neuester.json"), "neuester.weit.json")
        self.assertTrue(self._name("weit", "2026-09-24.json").startswith("2026-09-24."))


class ToreTest(unittest.TestCase):
    """Der Arm ist nur dann ein Schattenarm, wenn jedes Tor WEITER ist."""

    def _konf(self, name):
        with open(os.path.join(HANDEL, name), encoding="utf-8") as fh:
            return json.load(fh)["tore"]

    def test_weiche_fassung_ist_weiter(self):
        streng, weit = self._konf("prognose.json"), self._konf("prognose.weit.json")
        self.assertGreaterEqual(weit["hoechst_rsi"], streng["hoechst_rsi"])
        self.assertLessEqual(weit["mindest_cr"], streng["mindest_cr"])
        self.assertGreaterEqual(weit["ruecksetzer_bis_pct"], streng["ruecksetzer_bis_pct"])
        # Mindestens eines muss wirklich weiter sein, sonst waere es derselbe Lauf.
        self.assertNotEqual(
            (weit["hoechst_rsi"], weit["mindest_cr"], weit["ruecksetzer_bis_pct"]),
            (streng["hoechst_rsi"], streng["mindest_cr"], streng["ruecksetzer_bis_pct"]))

    def test_score_schwelle_weit_ist_nicht_strenger(self):
        """Die weite Fassung darf einen eigenen (weicheren) Score haben.

        Bis 11.10.2026 galt: der Score bleibt die gemeinsame Messlatte beider
        Arme (assertEqual). Am 11.10. wurde der weite Score bewusst auf 55
        gesenkt (prognose.weit.json: 'WEIT 11.10.2026: 60 -> 55. Gemessen ueber
        49 Maerkte: Score war bei 16 Long-Kandidaten das EINZIGE geschlossene
        Tor; 55 hebt die Treffer von 5 auf 7') - die weite Fassung ist der
        Schattenarm, der MEHR faengt, nicht dieselbe Messlatte. Die Regel ist
        damit: weit ist hoechstens so streng wie streng.
        """
        streng, weit = self._konf("prognose.json"), self._konf("prognose.weit.json")
        self.assertLessEqual(weit["mindest_score"], streng["mindest_score"])

    def test_wachen_weit_zeigt_auf_den_weichen_bericht(self):
        with open(os.path.join(SPUR, "wachen.weit.json"), encoding="utf-8") as fh:
            w = json.load(fh)
        with open(os.path.join(SPUR, "wachen.json"), encoding="utf-8") as fh:
            haupt = json.load(fh)
        self.assertTrue(w["signal_quelle"].endswith("neuester.weit.json"))
        self.assertTrue(haupt["signal_quelle"].endswith("neuester.json"))
        self.assertNotEqual(w["signal_quelle"], haupt["signal_quelle"])
        # Gleiche Groessen und gleiches Risiko: der Vergleich misst die TORE.
        for schluessel in ("max_einsatz_je_position_usd", "max_offen", "max_neu_je_zyklus",
                           "max_gesamt_risiko_usd", "max_halte_dauer_tage", "gebuehr_pct",
                           "slippage_pct"):
            self.assertEqual(w.get(schluessel), haupt.get(schluessel),
                             "%s unterscheidet sich - dann misst der Vergleich mehr als die Tore"
                             % schluessel)


class AnbindungTest(unittest.TestCase):
    """Der Arm existiert als Dateisatz - und der Dauerlauf faehrt ihn NICHT mehr.

    Am 24.09.2026 (Auftrag Max "Omniquant auf Papier auf weit stellen") liest
    der HAUPTARM die weite Fassung selbst. Der Arm bleibt als Aufzeichnung
    liegen; liefe er weiter, buchten zwei Buecher dieselben Signale.
    """

    def test_arm_laeuft_nicht_mehr_und_hauptarm_liest_weit(self):
        sys.path.insert(0, HANDEL)
        import dauerlauf
        import lage
        self.assertNotIn("omniquant_weit", dauerlauf.SPUREN)
        # Die Anzeige kennt den Arm weiterhin (sein Buch bleibt lesbar) ...
        namen = [f.__name__ for f in lage.HOLER]
        self.assertIn("spur_omniquant_weit", namen)
        s = lage.spur_omniquant_weit()
        self.assertIn("weit", s["name"])
        self.assertTrue(s["journal"].endswith("handelsjournal.weit.csv"))
        self.assertNotEqual(s["journal"], lage.spur_omniquant()["journal"])
        # ... und die weite Fassung hat trotzdem einen Abnehmer: den Hauptarm.
        with open(os.path.join(SPUR, "wachen.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f).get("prognose_fassung"), "weit")

    def test_arm_dateien_liegen_bereit(self):
        # Wieder einschalten soll moeglich sein, ohne etwas zu rekonstruieren.
        for name in ("omniquant_weit.py", "wachen.weit.json",
                     "handelsjournal.weit.csv"):
            self.assertTrue(os.path.isfile(os.path.join(SPUR, name)), name)


if __name__ == "__main__":
    unittest.main()