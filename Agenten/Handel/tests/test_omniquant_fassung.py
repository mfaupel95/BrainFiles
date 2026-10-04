"""Die waehlbare Prognose-FASSUNG der OmniQuant-Spur (24.09.2026, Auftrag Max).

Auftrag: "Omniquant auf Papier auf weit stellen". Geprueft wird die REGEL:

  * ohne Feld / "streng" -> der strenge Bericht (Voreinstellung unveraendert),
  * "weit" -> neuester.weit.json, die BUCHDATEIEN heissen weiter wie vorher
    (Fassung und Arm sind unabhaengig),
  * fehlt die gewaehlte Fassung auf der Platte, nennt die Fehlermeldung GENAU
    diese Datei - sonst sucht man den Fehler im falschen Bericht,
  * der Schattenarm (HANDEL_BUCH) haengt sein Suffix weiter an alle vier Namen.

Kein Netz, keine Order; die echte wachen.json wird nur gelesen.
"""

import importlib.util
import json
from datetime import datetime, timedelta, timezone
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
SPUR = os.path.join(HANDEL, "omniquant")

sys.path.insert(0, os.path.join(HANDEL, "scanner"))
sys.path.insert(0, HANDEL)
sys.path.insert(0, SPUR)

spec = importlib.util.spec_from_file_location(
    "omniquant_handeln_fassung", os.path.join(SPUR, "handeln.py"))
handeln = importlib.util.module_from_spec(spec)
sys.modules["omniquant_handeln_fassung"] = handeln
spec.loader.exec_module(handeln)
assert handeln.__file__.startswith(SPUR)


class BerichtPfadTest(unittest.TestCase):

    def test_ohne_feld_bleibt_es_streng(self):
        self.assertEqual(handeln.bericht_pfad({}), handeln.DEFAULT_BERICHT)

    def test_streng_ist_die_voreinstellung(self):
        self.assertEqual(handeln.bericht_pfad({"prognose_fassung": "streng"}),
                         handeln.DEFAULT_BERICHT)
        self.assertEqual(handeln.bericht_pfad({"prognose_fassung": ""}),
                         handeln.DEFAULT_BERICHT)

    def test_weit_zeigt_auf_den_weiten_bericht(self):
        pfad = handeln.bericht_pfad({"prognose_fassung": "weit"})
        self.assertEqual(os.path.basename(pfad), "neuester.weit.json")
        # Gleicher Ordner: die Fassung tauscht die DATEI, nicht den Ort.
        self.assertEqual(os.path.dirname(pfad), os.path.dirname(handeln.DEFAULT_BERICHT))

    def test_grossschreibung_ist_egal(self):
        self.assertEqual(handeln.bericht_pfad({"prognose_fassung": "WEIT"}),
                         handeln.bericht_pfad({"prognose_fassung": "weit"}))

    def test_buchdateien_bleiben_unberuehrt(self):
        # Der Kern der Trennung: die Fassung darf die Buchdateien NICHT umbenennen.
        self.assertEqual(os.path.basename(handeln.JOURNAL), "handelsjournal.csv")
        self.assertEqual(os.path.basename(handeln.ZUSTAND), "zustand.json")


class LadeBerichtTest(unittest.TestCase):
    """Ohne Netz: ein Temp-Bericht, der nur in der weiten Fassung existiert."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self._lade_wachen_alt = handeln.lade_wachen
        self._bericht_alt = handeln.DEFAULT_BERICHT
        self._quelle_alt = handeln.bericht_quelle
        handeln.bericht_quelle = None
        handeln.DEFAULT_BERICHT = os.path.join(self.tmp, "neuester.json")

    def tearDown(self):
        handeln.lade_wachen = self._lade_wachen_alt
        handeln.DEFAULT_BERICHT = self._bericht_alt
        handeln.bericht_quelle = self._quelle_alt
        self._tmp.cleanup()

    @staticmethod
    def _erzeugt(stunden_alt=1.0):
        """Zeitstempel RELATIV zu jetzt.

        Vorher stand hier ein festes Datum (2026-09-24) - der Test war damit eine
        Uhrzeitbombe: nach 26 Stunden kippte er in 'Bericht 123.0 h alt, Grenze
        26 h' um, ohne dass sich am Code etwas geaendert haette. Geprueft wird
        die REGEL (frischer Bericht wird gelesen, alter abgelehnt), nicht ein
        Kalendertag.
        """
        jetzt = datetime.now(timezone.utc) - timedelta(hours=stunden_alt)
        return jetzt.isoformat()

    def _schreibe_weit(self, stunden_alt=1.0):
        with open(os.path.join(self.tmp, "neuester.weit.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"erzeugt": self._erzeugt(stunden_alt),
                       "treffer": [{"inst": "TEST-USDT", "richtung": "long"}]}, f)

    def test_weit_liest_die_weite_datei(self):
        self._schreibe_weit()
        handeln.lade_wachen = lambda: {"prognose_fassung": "weit",
                                       "max_bericht_alter_stunden": 26}
        b, fehler = handeln.lade_bericht()
        self.assertIsNone(fehler)
        self.assertEqual(b["treffer"][0]["inst"], "TEST-USDT")

    def test_fehlt_die_fassung_nennt_die_meldung_diese_datei(self):
        handeln.lade_wachen = lambda: {"prognose_fassung": "weit",
                                       "max_bericht_alter_stunden": 26}
        b, fehler = handeln.lade_bericht()
        self.assertIsNone(b)
        self.assertIn("neuester.weit.json", fehler)

    def test_zu_alter_bericht_wird_abgelehnt(self):
        """Die Gegenprobe zur Grenze: 27 h bei Grenze 26 h muss auffallen."""
        self._schreibe_weit(stunden_alt=27.0)
        handeln.lade_wachen = lambda: {"prognose_fassung": "weit",
                                       "max_bericht_alter_stunden": 26}
        b, fehler = handeln.lade_bericht()
        self.assertIsNone(b)
        self.assertIn("alt", fehler.lower())

    def test_streng_liest_die_strenge_datei(self):
        # Der strenge Bericht existiert, der weite nicht - mit fassung=streng
        # muss er trotzdem gefunden werden.
        with open(os.path.join(self.tmp, "neuester.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"erzeugt": self._erzeugt(), "treffer": []}, f)
        handeln.lade_wachen = lambda: {"max_bericht_alter_stunden": 26}
        b, fehler = handeln.lade_bericht()
        self.assertIsNone(fehler)
        self.assertEqual(b["treffer"], [])


class AuftragTest(unittest.TestCase):
    """Der Stand, den Max bestellt hat - in den echten wachen-Dateien."""

    def test_schattenarm_weit_bleibt_papier(self):
        """Der Schattenarm (wachen.weit.json) muss Papier bleiben,
        auch wenn die Hauptspur live geschaltet ist.

        04.10.2026 (T-309): der Test verlangte zusaetzlich
        `prognose_fassung == "weit"` in der ARM-Wachen und meldete
        `None != 'weit'`. Das Feld steht aber im HAUPTbuch (dort wurde der
        Schalter am 01.10.2026 gesetzt, Commit aecd6178 / Auftrag Max
        "auto freigabe erlaubt"); die Arm-Wache fuehrt es nie und kann es
        auch nicht brauchen - siehe der Test darueber, WIE der Arm seine
        weite Fassung findet.

        Geprueft wird die EIGENSCHAFT, die Max entschieden hat: im Arm wird
        nicht gehandelt. Das HAUPTbuch traegt die weite Fassung, weil es
        seit dem 24.09.2026 (Auftrag Max "Omniquant auf Papier auf weit
        stellen") der einzige laufende Arm ist.
        """
        with open(os.path.join(SPUR, "wachen.weit.json"), encoding="utf-8") as f:
            w = json.load(f)
        self.assertFalse(w.get("handel_erlaubt"),
                         "Omniquant-Weit-Arm wurde auf PAPIER bestellt")
        with open(os.path.join(SPUR, "wachen.json"), encoding="utf-8") as f:
            haupt = json.load(f)
        self.assertEqual(haupt.get("prognose_fassung"), "weit",
                         "das Hauptbuch verliert die weite Fassung - dann "
                         "laeuft die laufende Spur auf dem strengen Bericht")

    def test_der_arm_findet_seine_fassung_ueber_den_arm_nicht_ueber_das_feld(self):
        """Die Fassung des ARMS haengt am Suffix, nicht am Wachen-Feld.

        Dernaechstliegende Fehler waere, `prognose_fassung: "weit"` in die
        Arm-Wache zu schreiben, damit die alte Behauptung des Tests wieder
        gilt. Dann haette der Arm ZWEI Wege zur weite Fassung (Suffix UND
        Feld) und der naechste Schalter wieder eine zweite Wahrheit.

        Gemessen am 04.10.2026: mit `HANDEL_BUCH=weit` und ohne jedes Feld in
        `wachen.weit.json` liefert `bericht_pfad()` die weite Datei - der
        Rueckfall auf "streng" von `bericht_pfad` gibt es nur fuer den
        HAUPTarm, dessen `DEFAULT_BERICHT` ohne Suffix `neuester.json`
        heisst. Die Pfade entstehen beim IMPORT, darum misst ein Kindprozess.
        """
        import subprocess
        code = (
            "import json,os,sys;"
            "os.environ['HANDEL_BUCH']='weit';"
            "sys.path.insert(0,%r);sys.path.insert(0,%r);"
            "import handeln as h;"
            "print(json.dumps({'arm':h.ARM,"
            "'bericht':os.path.basename(h.DEFAULT_BERICHT),"
            "'mit_wache':os.path.basename(h.bericht_pfad(h.lade_wachen())),"
            "'ohne_wache':os.path.basename(h.bericht_pfad({}))}))"
            % (SPUR, HANDEL))
        p = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, encoding="utf-8", cwd=SPUR,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(p.returncode, 0, p.stderr[-600:])
        d = json.loads(p.stdout.strip().splitlines()[-1])
        # Der Arm liest die weite Fassung - so, wie er es ohne jedes Feld tut.
        self.assertEqual(d["mit_wache"], "neuester.weit.json")
        self.assertEqual(d["ohne_wache"], "neuester.weit.json",
                         "der Rueckfall auf 'streng' gilt fuer den HAUPTarm - "
                         "im Arm heisst er neuester.weit.json")
        # Und die Arm-Wache fuehrt das Feld nicht (es waere der zweite Weg).
        with open(os.path.join(SPUR, "wachen.weit.json"), encoding="utf-8") as f:
            self.assertNotIn("prognose_fassung", json.load(f),
                             "die Arm-Wache fuehrt das Feld - zwei Wege zur "
                             "weiten Fassung, einer davon stirbt zuerst")

    def test_hauptspur_ist_live_wie_bestellt(self):
        """Die Hauptspur ist seit aecd6178 live geschaltet (Max' Auftrag)."""
        with open(os.path.join(SPUR, "wachen.json"), encoding="utf-8") as f:
            w = json.load(f)
        self.assertTrue(w.get("handel_erlaubt"),
                        "Omniquant-Hauptspur wurde live bestellt")

    def test_weiter_bericht_ist_frischer_als_die_grenze(self):
        # Ohne frischen Bericht faellt die Spur still auf Abstention - der
        # haeufigste stumme Ausfall bei Bericht-Spuren.
        with open(os.path.join(SPUR, "wachen.json"), encoding="utf-8") as f:
            grenze = json.load(f).get("max_bericht_alter_stunden", 26)
        pfad = os.path.join(HANDEL, "prognose_berichte", "neuester.weit.json")
        self.assertTrue(os.path.isfile(pfad), "weiter Bericht fehlt: %s" % pfad)
        with open(pfad, encoding="utf-8") as f:
            b = json.load(f)
        self.assertIn("erzeugt", b)
        self.assertLessEqual(grenze, 26)


if __name__ == "__main__":
    unittest.main()
