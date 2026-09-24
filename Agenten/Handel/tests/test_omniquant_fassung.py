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

    def _schreibe_weit(self):
        with open(os.path.join(self.tmp, "neuester.weit.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"erzeugt": "2026-09-24T09:01:00+00:00",
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

    def test_streng_liest_die_strenge_datei(self):
        # Der strenge Bericht existiert, der weite nicht - mit fassung=streng
        # muss er trotzdem gefunden werden.
        with open(os.path.join(self.tmp, "neuester.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"erzeugt": "2026-09-24T09:01:00+00:00", "treffer": []}, f)
        handeln.lade_wachen = lambda: {"max_bericht_alter_stunden": 26}
        b, fehler = handeln.lade_bericht()
        self.assertIsNone(fehler)
        self.assertEqual(b["treffer"], [])


class AuftragTest(unittest.TestCase):
    """Der Stand, den Max bestellt hat - in der echten wachen.json."""

    def test_spur_faehrt_weit_und_bleibt_papier(self):
        with open(os.path.join(SPUR, "wachen.json"), encoding="utf-8") as f:
            w = json.load(f)
        self.assertEqual(w.get("prognose_fassung"), "weit")
        self.assertFalse(w.get("handel_erlaubt"),
                         "Omniquant wurde auf PAPIER bestellt")

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
