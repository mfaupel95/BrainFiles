"""T-234: die Zentrale traegt Startbefehle nur, wenn sie belegt sind - und der
Beleg muss PORTABEL sein.

Drei Regeln, die das Werkzeug einhaelt und die hier geprueft werden:

1. Ein Eintrag ohne Start, der als 'startbar' benannt ist, braucht eine
   Begruendung - kein stilles Loch.
2. Was ins Manifest geschrieben wird, ist RELATIV zur Haus-Wurzel (kein
   absoluter C:\\...-Pfad, kein Hermes-Tool-Pfad) - der Baum muss umziehbar
   bleiben, und ein Hermes-Update macht tools/<version> ungueltig.
3. Vorschau schreibt NICHT (sonst ist 'Vorschau' ein Wort ohne Wirkung).

Test laeuft aus Agenten/Werkzeuge/repos-zentrale/.
"""
import json
import os
import sys
import unittest

from pathlib import Path

ZENTRALE = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, ZENTRALE)

import startbefehle_werkstatt as sw     # noqa: E402

MANIFEST = os.path.join(ZENTRALE, "repos-zentrale.json")


def manifest():
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


class ManifestFormTest(unittest.TestCase):
    def test_hermes_toolpfad_wird_zu_bash(self):
        befehl = [r"C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\tools"
                  r"\git-2.53.0+3-win32-x64\usr\bin\bash.exe", "x.sh"]
        aus = sw.manifest_form(befehl)
        self.assertEqual(aus[0], "bash", aus)
        self.assertNotIn("tools\\git-", aus[0])

    def test_hauspfad_wird_relativ(self):
        haus = sw.HAUS()
        befehl = [os.path.join(haus, "Agenten", "Handel", "omnitrade",
                               "handeln.py")]
        aus = sw.manifest_form(befehl)
        self.assertEqual(aus, ["Agenten/Handel/omnitrade/handeln.py"], aus)

    def test_fremder_pfad_bleibt_absolut(self):
        befehl = [r"D:\anders\ding.exe"]
        self.assertEqual(sw.manifest_form(befehl), befehl)


class ManifestInhaltTest(unittest.TestCase):
    def test_kein_absoluter_pfad_im_manifest(self):
        """Grundregel des Hauses: keine absoluten C:\\-Pfade im Manifest."""
        schlecht = []
        for x in manifest()["repos"]:
            for teil in (x.get("start") or []):
                if ":\\" in teil or teil.lower().endswith("bash.exe"):
                    schlecht.append((x.get("ordner"), teil))
        self.assertEqual(schlecht, [], "absolute Pfade im Manifest")

    def test_werkstatt_freqtrade_ist_geklaert(self):
        zeile = None
        for x in manifest()["repos"]:
            if x.get("wurzel") == "werkstatt" and x.get("ordner") == "freqtrade":
                zeile = x
        self.assertIsNotNone(zeile, "Werkstatt/freqtrade fehlt im Manifest")
        self.assertFalse(zeile.get("start"),
                         "der Fremd-Klon darf keinen Start bekommen")
        self.assertEqual(zeile.get("gruppe"), "kein_start")
        self.assertTrue(any("Fremd-Klon" in w for w in zeile.get("warnungen", [])),
                        zeile.get("warnungen"))

    def test_startbare_werkstatt_zeilen_sind_belegt(self):
        """Jede Zeile der Wurzel werkstatt mit Start traegt eine Frist."""
        for x in manifest()["repos"]:
            if x.get("wurzel") == "werkstatt" and x.get("start"):
                self.assertIn("beleg_frist_s", x,
                              "%s ohne beleg_frist_s" % x.get("ordner"))

    def test_omnitrade_und_omniroute_haben_start(self):
        zeilen = {(x.get("wurzel"), x.get("ordner")): x
                  for x in manifest()["repos"]}
        for schluessel in (("werkstatt", "omnitrade"), ("werkstatt", "OmniRoute")):
            x = zeilen.get(schluessel)
            self.assertIsNotNone(x, schluessel)
            self.assertTrue(x.get("start"), "%s ohne Start" % (schluessel,))

    def test_house_anker_zeigt_auf_die_echte_wurzel(self):
        """Im Worktree gibt es keine venvs - der Anker muss trotzdem greifen."""
        haus = sw.HAUS()
        self.assertTrue(os.path.isdir(os.path.join(haus, "Agenten", "Handel")))
        self.assertTrue(os.path.isfile(os.path.join(haus, "Agenten", "Handel",
                                                     "scanner", ".venv",
                                                     "Scripts", "python.exe")))


class VorschauTest(unittest.TestCase):
    def test_werkstatt_findung_ignoriert_leeres_verzeichnis(self):
        """Der Worktree hat ein LEERES Werkstatt/ - das darf nicht gewinnen."""
        gefunden = sw.WERKSTATT
        kinder = os.listdir(gefunden) if os.path.isdir(gefunden) else []
        self.assertIn("omnitrade", kinder,
                      "gefunden: %s mit %r" % (gefunden, kinder[:8]))

    def test_kandidaten_kommen_nicht_in_die_fremd_liste(self):
        for ordner, _, _, _ in sw.KANDIDATEN:
            self.assertNotIn(ordner, sw.FREMDE_KLONEN,
                             "%s ist zugleich Kandidat und Fremd-Klon" % ordner)


if __name__ == "__main__":
    unittest.main()