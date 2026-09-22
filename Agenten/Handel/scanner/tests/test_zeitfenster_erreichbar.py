"""Der Scanner muss das Freigabefenster sehen, das der Dauerlauf ihm oeffnet.

Am 22.09.2026 stand in jedem Zyklus "scanner: --live angefordert, aber
gesperrt: Freigabefenster nicht offen" - obwohl das Fenster offen war. Ursache:
handeln.py lud freigabefenster per blossem 'import', und der Handel-Ordner liegt
im Spurlauf NICHT auf sys.path. Die Sperre meldete ein offenes Fenster als
geschlossen und handelte Papier.

Der Test startet einen KINDprozess genau so, wie der Dauerlauf die Spur startet
(cwd = scanner/), und laesst ihn gegen eine eigene Zeitdatei pruefen - nie
gegen die echte freigabe_fenster.json.
"""

import os
import subprocess
import sys
import unittest

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # scanner/
PYTHON = sys.executable

KIND = r'''
import datetime as dt, json, os, sys, tempfile
import handeln

f = os.path.join(tempfile.gettempdir(), "fenster-kind-%d.json" % os.getpid())
with open(f, "w", encoding="utf-8") as fh:
    json.dump({"scanner": {"offen_bis":
              (dt.datetime.now() + dt.timedelta(hours=STUNDEN)).isoformat()}}, fh)
handeln.freigabefenster.DATEI = f
print("ERGEBNIS", handeln.zeitfenster_offen())
os.remove(f)
'''


class ZeitfensterErreichbarTest(unittest.TestCase):

    def kind(self, stunden):
        code = KIND.replace("STUNDEN", str(stunden))
        p = subprocess.run([PYTHON, "-c", code], cwd=SPUR,
                           capture_output=True, text=True, timeout=180,
                           env=dict(os.environ, MAXHIRN_ROUTINE="1"))
        self.assertIn("ERGEBNIS", p.stdout,
                      "Kindprozess ohne Ergebnis.\nstdout=%s\nstderr=%s"
                      % (p.stdout, p.stderr))
        return p.stdout.split("ERGEBNIS")[1].strip()

    def test_offenes_fenster_wird_gesehen(self):
        self.assertEqual(self.kind(2), "True")

    def test_geschlossenes_fenster_bleibt_zu(self):
        self.assertEqual(self.kind(-1), "False")

    def test_kein_blosser_import_im_kind(self):
        """Der Fehler war ein nacktes 'import freigabefenster' im Spurlauf."""
        with open(os.path.join(SPUR, "handeln.py"), encoding="utf-8") as fh:
            quelle = fh.read()
        for nr, zeile in enumerate(quelle.splitlines(), 1):
            self.assertNotEqual(
                zeile.strip(), "import freigabefenster",
                "handeln.py:%d laedt freigabefenster per blossem import - im "
                "Spurlauf nicht auffindbar" % nr)


if __name__ == "__main__":
    unittest.main()