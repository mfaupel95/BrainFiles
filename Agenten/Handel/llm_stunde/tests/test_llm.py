import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # llm_stunde
import llm  # noqa: E402

W = {"llm": {"modell": "x", "bruecke": "http://127.0.0.1:1/v1", "temperatur": 0,
             "konfidenz_min": 70, "timeout_s": 1}}


def kerzen_aus(schluesse):
    return [[i * 3600000, c, c * 1.005, c * 0.995, c, 100.0 + i]
            for i, c in enumerate(schluesse)]


class Antwort(unittest.TestCase):
    def test_buy_mit_konfidenz(self):
        self.assertEqual(llm.lies_antwort("BUY\nTechnik ok.\nConfidence: 75%"), ("BUY", 75))

    def test_nothing_ohne_zahl(self):
        self.assertEqual(llm.lies_antwort("NOTHING\nkeine Lage"), ("NOTHING", None))

    def test_leere_antwort_ist_fehler(self):
        self.assertEqual(llm.lies_antwort("")[0], "FEHLER")

    def test_text_ohne_kopfzeile_ist_fehler(self):
        self.assertEqual(llm.lies_antwort("Ich denke, es geht hoch.")[0], "FEHLER")

    def test_kleinschreibung_wird_akzeptiert(self):
        self.assertEqual(llm.lies_antwort("buy\nConfidence: 80%")[0], "BUY")


class Aufruf(unittest.TestCase):
    def test_netzfehler_ist_fehler_nicht_exception(self):
        def kaputt(*a, **k):
            raise TimeoutError("Bruecke tot")
        r = llm.frage({"kandidat": "long"}, W, aufrufer=kaputt)
        self.assertEqual(r["urteil"], "FEHLER")
        self.assertFalse(llm.darf_einsteigen(r, W))

    def test_antwort_wird_gelesen_und_gehasht(self):
        r = llm.frage({"kandidat": "long"}, W,
                      aufrufer=lambda p, w: "BUY\nok\nConfidence: 80%")
        self.assertEqual((r["urteil"], r["konfidenz"]), ("BUY", 80))
        self.assertEqual(len(r["prompt_hash"]), 16)

    def test_gleicher_snapshot_gleicher_hash(self):
        a = llm.frage({"x": 1}, W, aufrufer=lambda p, w: "NOTHING")["prompt_hash"]
        b = llm.frage({"x": 1}, W, aufrufer=lambda p, w: "NOTHING")["prompt_hash"]
        self.assertEqual(a, b)


class Momentaufnahme(unittest.TestCase):
    def test_enthaelt_moondev_kennzahlen(self):
        s = llm.momentaufnahme(kerzen_aus([100.0] * 60), "ema1h", "long", 2.3)
        for feld in ("schluss", "ma20", "ma40", "stop_prozent", "rendite_24h_pct", "volumen_rel_20"):
            self.assertIn(feld, s)
        self.assertEqual(s["ma20"], 100.0)

    def test_ohne_volumenspalte_bricht_nicht(self):
        fuenf = [[i * 3600000, c, c, c, c] for i, c in enumerate([100.0] * 60)]
        s = llm.momentaufnahme(fuenf, "ema1h", "long", 2.5)
        self.assertIsNone(s["volumen_rel_20"])
        self.assertEqual(s["ma20"], 100.0)


if __name__ == "__main__":
    unittest.main()
