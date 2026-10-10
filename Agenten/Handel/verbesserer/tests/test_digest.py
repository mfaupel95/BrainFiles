import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
import digest  # noqa: E402

BEFUND = {"befunde": [{"merkmal": "grund", "auspraegung": "stop",
                       "n": 12, "mittel_gv": -1.2}]}
BASIS = {"gesamt": {"netto_gv_je_runde": -0.1, "n": 30}}
KAND = {"gesamt": {"netto_gv_je_runde": 0.05, "n": 30}}


class TestDigest(unittest.TestCase):
    def test_modus_aus_wird_uebersprungen(self):
        r = digest.erzeuge(BEFUND, BASIS, KAND, {}, {"modus": "aus"})
        self.assertIsNotNone(r["uebersprungen"])
        self.assertEqual(r["empfehlungen"], "")

    def test_ruf_fehler_wird_uebersprungen(self):
        def kaputt(*a, **k):
            raise OSError("keine Verbindung")
        r = digest.erzeuge(BEFUND, BASIS, KAND, {}, {"modus": "ollama"},
                           ruf=kaputt)
        self.assertIn("keine Verbindung", r["uebersprungen"])

    def test_ruf_liefert_nichtstring_wird_uebersprungen(self):
        r = digest.erzeuge(BEFUND, BASIS, KAND, {}, {"modus": "ollama"},
                           ruf=lambda p, k: {"response": "x"})
        self.assertIsNotNone(r["uebersprungen"])
        self.assertEqual(r["empfehlungen"], "")
        self.assertEqual(r["lehren"], "")

    def test_llm_konf_none_wird_uebersprungen(self):
        r = digest.erzeuge(BEFUND, BASIS, KAND, {}, None)
        self.assertIsNotNone(r["uebersprungen"])
        self.assertEqual(r["empfehlungen"], "")

    def test_erfolg_liefert_texte(self):
        def ruf(prompt, konf):
            return "1. Stops zu eng\n2. DOGE raus\n\nLEHREN: Enge Stops kosten."
        r = digest.erzeuge(BEFUND, BASIS, KAND, {}, {"modus": "ollama"}, ruf=ruf)
        self.assertIn("Stops", r["empfehlungen"])
        self.assertIsNone(r["uebersprungen"])

    def test_annotiere_bericht_setzt_abschnitt_vorn(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "bericht.md"
            p.write_text("# Vorschlag spur1\n\nInhalt\n", "utf-8")
            digest.annotiere_bericht(p, {"empfehlungen": "Mach X", "uebersprungen": None})
            t = p.read_text("utf-8")
            self.assertLess(t.index("Priorisierte Empfehlungen"), t.index("Inhalt"))

    def test_lehren_anhaengen_legt_datei_an(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "handelslehren-eingang.md"
            digest.haenge_lehren_an(p, "Enge Stops kosten.", "2026-09-13")
            self.assertIn("2026-09-13", p.read_text("utf-8"))

    def test_digest_aendert_wachen_neu_nicht(self):
        with TemporaryDirectory() as d:
            w = Path(d) / "wachen.neu.json"
            w.write_text('{"mindest_score": 65}', "utf-8")
            vorher = w.read_bytes()
            digest.erzeuge(BEFUND, BASIS, KAND, {}, {"modus": "aus"})
            self.assertEqual(w.read_bytes(), vorher)

    def test_fast_kandidat_im_prompt(self):
        gesehen = {}

        def ruf(prompt, konf):
            gesehen["prompt"] = prompt
            return "1. ok\n\nLEHREN: ok."
        digest.erzeuge(BEFUND, BASIS, None, {}, {"modus": "ollama"},
                       ruf=ruf, fast_kandidat={"gates": {}})
        self.assertIn("Holdout", gesehen["prompt"])

    def test_ohne_fast_kandidat_kein_holdout_hinweis(self):
        gesehen = {}

        def ruf(prompt, konf):
            gesehen["prompt"] = prompt
            return "1. ok\n\nLEHREN: ok."
        digest.erzeuge(BEFUND, BASIS, KAND, {}, {"modus": "ollama"}, ruf=ruf)
        self.assertNotIn("Holdout", gesehen["prompt"])
