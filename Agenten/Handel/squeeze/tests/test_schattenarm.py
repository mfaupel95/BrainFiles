"""Der Schattenarm squeeze_eth an seinem Vertrag.

Geprueft wird, was gelten soll:
  1. Der Hauptarm laeuft unveraendert weiter (BTC/ETH/SOL) - ein Schattenarm,
     der den Hauptarm mitnimmt, ist kein Schattenarm, sondern eine
     Aenderung ohne Vergleichsgrundlage.
  2. Der Arm hat eigene Buchdateien und einen EIGENEN Spiegel. Ohne
     eigenen Spiegel schreiben Haupt- und Schattenarm dieselbe Datei und
     Bedingung 4 ist erfuellt, weil sie ueberschreiben statt zu spiegeln.
  3. HANDEL_BUCH wird VOR dem Kern-Import gesetzt. `handeln` liest das
     Suffix beim Laden; ein Starter, der es danach setzt, laeuft mit
     falschen Dateinamen und schreibt in das Hauptbuch.
  4. Beide Arme bleiben Papier - ein Schattenarm hat keinen Orderweg.
"""
import json
import os
import subprocess
import sys
import unittest

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(SPUR)
VENV = os.path.join(HANDEL, "scanner", ".venv", "Scripts", "python.exe")


class ArmTest(unittest.TestCase):
    # 1 -------------------------------------------------------------
    def test_hauptarm_bleibt_unveraendert(self):
        w = json.load(open(os.path.join(SPUR, "wachen.json"), encoding="utf-8"))
        self.assertGreater(len(w["instrumente"]), 1,
                           "der Hauptarm muss mehrere Instrumente behalten - "
                           "sonst gibt es nichts zu vergleichen")
        self.assertIn("BTC-USDC", w["instrumente"])

    def test_arm_ist_auf_eine_basis_geklemmt(self):
        w = json.load(open(os.path.join(SPUR, "wachen.eth.json"),
                           encoding="utf-8"))
        self.assertEqual(w["instrumente"], ["ETH-USDC"])

    # 2 -------------------------------------------------------------
    def test_arm_hat_eigenen_spiegel(self):
        w = json.load(open(os.path.join(SPUR, "wachen.eth.json"),
                           encoding="utf-8"))
        haupt = json.load(open(os.path.join(SPUR, "wachen.json"),
                               encoding="utf-8"))
        self.assertNotEqual(w["journal_zweitziel"], haupt["journal_zweitziel"],
                            "gleicher Spiegel heisst: beide Arme beschreiben "
                            "dieselbe Datei")

    # 3 -------------------------------------------------------------
    def test_umgebung_vor_dem_import(self):
        src = open(os.path.join(SPUR, "squeeze_eth.py"), encoding="utf-8").read()
        i_env = src.index('os.environ["HANDEL_BUCH"]')
        i_imp = src.index("import handeln")
        self.assertLess(i_env, i_imp,
                        "HANDEL_BUCH muss VOR dem Import gesetzt werden - "
                        "handeln liest das Suffix beim Laden")

    # 4 -------------------------------------------------------------
    def test_beide_arme_sind_papier(self):
        for name in ("wachen.json", "wachen.eth.json"):
            w = json.load(open(os.path.join(SPUR, name), encoding="utf-8"))
            self.assertFalse(w.get("handel_erlaubt", False),
                             "%s: ein Schattenarm hat keinen Orderweg" % name)

    # 5 - der echte Lauf: der Arm darf das Hauptbuch nicht anfassen
    def test_lauf_legt_eigene_dateien_an(self):
        env = dict(os.environ, MAXHIRN_ROUTINE="1",
                   PYTHONHOME="", PYTHONPATH="")
        vorher = (os.path.getmtime(os.path.join(SPUR, "zustand.json"))
                  if os.path.exists(os.path.join(SPUR, "zustand.json")) else None)
        subprocess.run([VENV, "squeeze_eth.py", "--papier"], cwd=SPUR, env=env,
                       timeout=180, capture_output=True)
        self.assertTrue(os.path.exists(os.path.join(SPUR, "zustand.eth.json")),
                        "der Arm muss sein eigenes Zustandsfile schreiben")
        if vorher is not None:
            nachher = os.path.getmtime(os.path.join(SPUR, "zustand.json"))
            self.assertEqual(vorher, nachher,
                             "der Hauptarm wurde angefasst - der Arm laeuft "
                             "mit den falschen Dateinamen")


if __name__ == "__main__":
    unittest.main()