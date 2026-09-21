"""Die zwei Regeln, die am 21.09.2026 verletzt waren - und ihr Preis.

Vorgeschichte, damit die Tests nicht wie Formalismus aussehen: um 19:15 wurde
das Zeitlimit des Freigabefensters von 120 auf 600 s gestellt (Auftrag Max).
Der Abbruch des Dauerlaufs stand bei 300 s. Gleichzeitig galt die Annahme,
ein Live-Lauf aus dem Dauerlauf brauche MAXHIRN_ROUTINE nicht - er habe die
Freigabe ja schon. Beides zusammen: der Live-Lauf hielt sich fuer eine Sitzung
am Bildschirm (isatty auf geerbtem Terminal), zog das Freigabefenster auf,
wartete auf einen Klick, den niemand geben kann, und wurde nach 300 s
abgebrochen - bei scanner in JEDEM Zyklus ab 19:22. Lokal wuchs das
Ablehnungsprotokoll weiter, die Spiegelung nach Q: (Bedingung 4) lief nie
mehr, und die Live-Position stand ohne Ausstiegspruefung da.

Drei Zusicherungen halten das kuenftig:

  1. Der Dauerlauf setzt MAXHIRN_ROUTINE=1 in BEIDEN Modi - und jede Spur
     mit Freigabefenster respektiert es (in einem echten Kindprozess geprueft,
     nicht am Quelltext).
  2. Kein Freigabefenster darf laenger warten als der Aufrufer zulaesst.
  3. Ein Fensteraufruf traegt sein Zeitlimit als benannte Konstante, nicht
     als Zahl im Aufruf (eine Zahl im Aufruf faellt bei jeder Aenderung durch
     das Raster).
"""

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
sys.path.insert(0, str(HANDEL))

import dauerlauf                                                 # noqa: E402

PYTHON_VENV = HANDEL / "scanner" / ".venv" / "Scripts" / "python.exe"
# Spuren mit Freigabefenster: Ordner, Modul, Spur (so heisst sie im Dauerlauf).
MIT_FENSTER = (
    ("scanner", "handeln", "scanner"),
    ("kraken", "handeln", "kraken"),
    ("mosaic", "handeln", "mosaic"),
    ("moondev_marktlage", "live_kraken", "moondev_marktlage"),
)
# Reserve: der Zyklus muss nach dem Fenster noch rechnen und spiegeln.
RESERVE_S = 60


def _python():
    return str(PYTHON_VENV) if PYTHON_VENV.exists() else sys.executable


class UmgebungTest(unittest.TestCase):
    """Regel 1: die Ansage 'hier sitzt niemand' gilt in beiden Modi."""

    def test_beide_modi_setzen_maxhirn_routine(self):
        for modus in ("--papier", "--live"):
            with self.subTest(modus=modus):
                umg = dauerlauf.zyklus_umgebung(modus)
                self.assertEqual(umg.get("MAXHIRN_ROUTINE"), "1")
                # HANDEL_RISIKO gehoert weiter dazu (Risikostufen).
                self.assertIn("HANDEL_RISIKO", umg)

    def test_basis_umgebung_wird_nicht_veraendert(self):
        # Der Aufrufer gibt _env_sicher() hinein; ein Mutieren waere eine
        # Aenderung an einer Umgebung, die noch anderweitig benutzt wird.
        basis = {"PATH": "x"}
        umg = dauerlauf.zyklus_umgebung("--live", basis)
        self.assertEqual(umg["MAXHIRN_ROUTINE"], "1")
        self.assertNotIn("MAXHIRN_ROUTINE", basis)

    def test_jede_fensterspur_respektiert_die_variable(self):
        # Echter Kindprozess im Spurordner - genau wie der Dauerlauf startet.
        # Am Quelltext zu pruefen waere zu schwach: die Reihenfolge in
        # sitzung_da entscheidet.
        for ordner, modul, spur in MIT_FENSTER:
            with self.subTest(spur=spur):
                code = ("import {m} as h; print(h.sitzung_da())"
                        .format(m=modul))
                umg = dict(os.environ)
                umg.pop("MAXHIRN_ROUTINE", None)
                umg["MAXHIRN_ROUTINE"] = "1"
                p = subprocess.run([_python(), "-c", code],
                                   cwd=str(HANDEL / ordner), env=umg,
                                   capture_output=True, text=True, timeout=120)
                self.assertEqual(p.returncode, 0, p.stderr[-400:])
                self.assertEqual(p.stdout.strip(), "False",
                                 "%s oeffnet trotz MAXHIRN_ROUTINE ein Fenster"
                                 % spur)


class ZeitgrenzeTest(unittest.TestCase):
    """Regel 2: Fensterzeitlimit < Abbruchzeit des Aufrufers."""

    def test_alle_fenster_bleiben_unter_dem_abbruch(self):
        gesehen = {}
        for ordner, modul, spur in MIT_FENSTER:
            quelle = (HANDEL / ordner / (modul + ".py")).read_text("utf-8")
            treffer = re.search(r"^FREIGABE_ZEITLIMIT_S\s*=\s*(\d+)",
                                quelle, re.MULTILINE)
            self.assertIsNotNone(treffer, "kein FREIGABE_ZEITLIMIT_S in %s"
                                 % spur)
            gesehen[spur] = int(treffer.group(1))
        # Gegenprobe: der Scan darf nicht still leer laufen.
        self.assertEqual(len(gesehen), len(MIT_FENSTER))
        for spur, limit in gesehen.items():
            with self.subTest(spur=spur):
                self.assertLess(limit, dauerlauf.TIMEOUT_S - RESERVE_S,
                                "%s: Fenster %d s >= Abbruch %d s"
                                % (spur, limit, dauerlauf.TIMEOUT_S))

    def test_abbruchzeit_ist_groesser_als_das_fenster(self):
        # Die Regel in ihrer einfachsten Form; sie ist der Grund, warum
        # TIMEOUT_S am 21.09.2026 von 300 auf 700 ging.
        self.assertGreater(dauerlauf.TIMEOUT_S, 600)

    def test_kein_zeitlimit_als_nackte_zahl(self):
        # Ein zeitlimit=600 im Aufruf faellt bei der naechsten Aenderung
        # durch das Raster - es muss die Konstante sein.
        for ordner, modul, spur in MIT_FENSTER:
            quelle = (HANDEL / ordner / (modul + ".py")).read_text("utf-8")
            nackt = re.findall(r"zeitlimit\s*=\s*\d+", quelle)
            with self.subTest(spur=spur):
                self.assertEqual(nackt, [],
                                 "%s: Zeitlimit als Zahl im Aufruf" % spur)


if __name__ == "__main__":
    unittest.main()
