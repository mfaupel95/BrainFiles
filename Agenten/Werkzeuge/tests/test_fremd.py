"""Tests fuer fremd.py - die Grenze zwischen Hauscode und Fremd-Material.

Die wichtigen Faelle sind die Gegenproben: dass `ist_fremd` NICHT anschlaegt
(OpenAlice2, unsere eigenen Spuren) und dass `pruefen()` wirklich rot werden kann.
Ein Pruefer, der nur bei gesunder Liste gruen ist, prueft nichts.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
WERKZEUGE = HIER.parent
WURZEL = WERKZEUGE.parents[1]
if str(WERKZEUGE) not in sys.path:
    sys.path.insert(0, str(WERKZEUGE))

import fremd  # noqa: E402


def attrappe(eintraege, ordner=("a/b",)) -> Path:
    """Eine Temp-Wurzel mit Liste und Ordnern - fuer die Fehlerfaelle."""
    tmp = Path(tempfile.mkdtemp(prefix="fremd-test-"))
    (tmp / "Agenten").mkdir(parents=True, exist_ok=True)
    for o in ordner:
        (tmp / o).mkdir(parents=True, exist_ok=True)
    (tmp / "Agenten" / fremd.DATEINAME).write_text(
        json.dumps({"fassung": 1, "eintraege": eintraege}, ensure_ascii=False),
        encoding="utf-8",
    )
    return tmp


def eintrag(pfad, **rest):
    e = {"pfad": pfad, "art": "Fremd-Klon", "herkunft": "Klon",
         "regel": "nur lesen", "warum": "Test"}
    e.update(rest)
    return e


class EchteListe(unittest.TestCase):
    """Die Liste im Baum muss gesund sein - das ist die Dauerpruefung."""

    def test_wurzel_zeigt_auf_brainfiles(self):
        self.assertEqual(fremd.wurzel(), WURZEL)
        self.assertTrue((WURZEL / "Agenten" / "Handel").is_dir())

    def test_liste_ist_vorhanden_und_gefuellt(self):
        eintraege = fremd.laden()
        self.assertGreaterEqual(len(eintraege), 5, "die Liste ist leer oder fehlt")
        for e in eintraege:
            with self.subTest(pfad=e.pfad):
                for feld in fremd.FELDER:
                    self.assertTrue(getattr(e, feld).strip(), feld)

    def test_pruefen_ist_gesund(self):
        self.assertEqual(fremd.pruefen(), [])

    def test_openalice_steht_drin(self):
        """Der Fall, der die ganze Liste ausgeloest hat: 81 % der Zeilen."""
        self.assertIsNotNone(fremd.ist_fremd("Agenten/Handel/OpenAlice"))
        self.assertIsNotNone(fremd.ist_fremd("Agenten/Handel/OpenAlice/autoquant/cli.py"))

    def test_kein_eintrag_ist_eine_wurzel_unseres_codes(self):
        """Die Wurzeln, die eigenen Code tragen, duerfen nicht als Ganzes fremd sein.

        `Werkstatt/Repos` ist bewusst NICHT dabei: das ist die Klonsammlung, deren
        Inhalt zu 100 % fremd ist - eine eigene Wurzel der Zentrale, aber kein
        eigener Code. Genau diesen Unterschied prueft der Fall.
        """
        sys.path.insert(0, str(WURZEL / "Agenten" / "Werkzeuge" / "repos-zentrale"))
        try:
            import quellen
            unsere = [w.pfad_rel for w in quellen.WURZELN if w.kennung != "repos"]
            unsere.append(quellen.PROJEKTE.pfad_rel)
        finally:
            sys.path.pop(0)
        self.assertEqual(fremd.pruefen(eigene_wurzeln=tuple(unsere)), [])
        # Gegenprobe: dieselbe Pruefung kann rot werden - eine Wurzel unseres
        # Codes als Ganzes in der Liste.
        w = attrappe([eintrag("Agenten/Handel")], ordner=("Agenten/Handel",))
        self.assertTrue(any("EIGENE Wurzel" in b for b in
                            fremd.pruefen(w, eigene_wurzeln=("Agenten/Handel",))))
        # ... aber der echte Baum hat das nicht:
        self.assertIsNone(fremd.ist_fremd("Agenten/Handel/scanner/handeln.py"))


class IstFremd(unittest.TestCase):
    """Pfadgrenzen, laengster Treffer, Gross-/Kleinschreibung."""

    def setUp(self):
        self.e = [fremd.Fremd("A/B", "x", "y", "z", "w"),
                  fremd.Fremd("A/B/C", "tiefer", "y", "z", "w")]

    def test_pfadgrenze_statt_textanfang(self):
        self.assertIsNotNone(fremd.ist_fremd("A/B/x.py", self.e))
        self.assertIsNone(fremd.ist_fremd("A/B2/x.py", self.e), "B2 ist nicht B")

    def test_der_genaueste_eintrag_gewinnt(self):
        treffer = fremd.ist_fremd("A/B/C/d.py", self.e)
        self.assertEqual(treffer.pfad, "A/B/C")

    def test_gleichheit_zaehlt_mit(self):
        self.assertIsNotNone(fremd.ist_fremd("A/B", self.e))

    def test_schreibweise_egal_und_backslash_erlaubt(self):
        self.assertIsNotNone(fremd.ist_fremd("a\\b\\x.py", self.e))
        self.assertIsNotNone(fremd.ist_fremd("A/B/", self.e))

    def test_unser_code_ist_nicht_fremd(self):
        for pfad in ("Agenten/Handel/klassik_ema/handeln.py",
                     "Agenten/Handel/scanner/handeln.py",
                     "Agenten/Handel/klassik_regeln.py",
                     "Agenten/Bus/bus.py",
                     "MaxHirn/Wissen/Schutzregeln.md"):
            with self.subTest(pfad=pfad):
                self.assertIsNone(fremd.ist_fremd(pfad))

    def test_ohne_fremd_filtert(self):
        pfade = ["A/B/x.py", "A/C/y.py", "A/B2/z.py"]
        self.assertEqual(fremd.ohne_fremd(pfade, self.e), ["A/C/y.py", "A/B2/z.py"])


class PruefenKannRotWerden(unittest.TestCase):
    """Jede Regel in pruefen() bekommt einen Fall, der sie ausloest."""

    def test_gesunde_attrappe_ist_gruen(self):
        w = attrappe([eintrag("a/b")])
        self.assertEqual(fremd.pruefen(w), [])

    def test_fehlender_ordner(self):
        w = attrappe([eintrag("a/b")], ordner=())
        self.assertTrue(any("liegt nicht auf der Platte" in b for b in fremd.pruefen(w)))

    def test_leeres_feld(self):
        w = attrappe([eintrag("a/b", warum="")])
        self.assertTrue(any("'warum'" in b for b in fremd.pruefen(w)))

    def test_absoluter_pfad_und_backslash(self):
        w = attrappe([eintrag("C:/x/a")], ordner=())
        b = fremd.pruefen(w)
        self.assertTrue(any("absoluter Pfad" in x for x in b))
        w2 = attrappe([eintrag("a\\b")], ordner=())
        self.assertTrue(any("Backslash" in x for x in fremd.pruefen(w2)))

    def test_aufstieg_im_pfad(self):
        w = attrappe([eintrag("../a")], ordner=())
        self.assertTrue(any("'..' im Pfad" in x for x in fremd.pruefen(w)))

    def test_doppelter_eintrag(self):
        w = attrappe([eintrag("a/b"), eintrag("a/b")])
        self.assertTrue(any("doppelt" in x for x in fremd.pruefen(w)))

    def test_baum_im_baum(self):
        w = attrappe([eintrag("a/b"), eintrag("a/b/c")], ordner=("a/b", "a/b/c"))
        self.assertTrue(any("ein Eintrag genuegt" in x for x in fremd.pruefen(w)))

    def test_eigene_wurzel_als_fremd(self):
        w = attrappe([eintrag("a/b")])
        b = fremd.pruefen(w, eigene_wurzeln=("a/b",))
        self.assertTrue(any("EIGENE Wurzel" in x for x in b))

    def test_fehlende_liste_ist_ein_befund_kein_absturz(self):
        tmp = Path(tempfile.mkdtemp(prefix="fremd-leer-"))
        (tmp / "Agenten").mkdir(parents=True, exist_ok=True)
        self.assertEqual(fremd.laden(tmp), [])
        self.assertTrue(any("Liste fehlt" in b for b in fremd.pruefen(tmp)))

    def test_kaputtes_json_ist_ein_befund(self):
        tmp = Path(tempfile.mkdtemp(prefix="fremd-kaputt-"))
        (tmp / "Agenten").mkdir(parents=True, exist_ok=True)
        (tmp / "Agenten" / fremd.DATEINAME).write_text("{kein json", encoding="utf-8")
        self.assertEqual(fremd.laden(tmp), [])
        self.assertTrue(any("kein gueltiges JSON" in b for b in fremd.pruefen(tmp)))


class AnzeigeStimmtMitDerListe(unittest.TestCase):
    """FREMD.md ist die lesbare Fassung - und darf keine zweite Wahrheit sein."""

    def test_md_nennt_dieselben_pfade(self):
        md = WURZEL / "Agenten" / "FREMD.md"
        self.assertTrue(md.is_file(), "Agenten/FREMD.md fehlt")
        text = md.read_text(encoding="utf-8")
        aus_md = set(re.findall(r"^\|\s*`([^`]+)`", text, flags=re.M))
        aus_liste = {e.pfad for e in fremd.laden()}
        self.assertEqual(aus_md, aus_liste)

    def test_tabelle_ist_die_anzeige(self):
        tabelle = fremd.als_text()
        for e in fremd.laden():
            self.assertIn(f"`{e.pfad}`", tabelle)


if __name__ == "__main__":
    unittest.main(verbosity=2)