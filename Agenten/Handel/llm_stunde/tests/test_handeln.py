import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # llm_stunde
import handeln  # noqa: E402

W = {"llm": {"konfidenz_min": 70}}


class Entscheid(unittest.TestCase):
    def test_regelarm_einstieg_ohne_llm(self):
        e = handeln.entscheide("R", kandidat="long", llm_erg=None, w=W)
        self.assertEqual(e["entscheid"], "einstieg")

    def test_regelarm_kein_kandidat_kein_einstieg(self):
        e = handeln.entscheide("R", kandidat=None, llm_erg=None, w=W)
        self.assertEqual(e["entscheid"], "kein_einstieg")

    def test_llmarm_kein_einstieg_bei_fehler(self):
        e = handeln.entscheide("L", kandidat="long",
                               llm_erg={"urteil": "FEHLER", "konfidenz": None}, w=W)
        self.assertEqual(e["entscheid"], "kein_einstieg")

    def test_llmarm_einstieg_nur_bei_buy_ueber_schwelle(self):
        e = handeln.entscheide("L", kandidat="long",
                               llm_erg={"urteil": "BUY", "konfidenz": 72}, w=W)
        self.assertEqual(e["entscheid"], "einstieg")

    def test_llmarm_unter_schwelle_bleibt_aus(self):
        e = handeln.entscheide("L", kandidat="long",
                               llm_erg={"urteil": "BUY", "konfidenz": 69}, w=W)
        self.assertEqual(e["entscheid"], "kein_einstieg")

    def test_llmarm_ohne_antwort_bleibt_aus(self):
        e = handeln.entscheide("L", kandidat="long", llm_erg=None, w=W)
        self.assertEqual(e["entscheid"], "kein_einstieg")


class Aufruf(unittest.TestCase):
    def test_live_wird_verweigert(self):
        self.assertEqual(handeln.main(["--live"]), 2)

    def test_ausstieg_nur_fuer_long(self):
        zusatz = handeln._ausstieg_fabrik("ema1h")
        self.assertIsNone(zusatz({"inst": "BTC-USDT-SWAP", "seite": "short"}, {}))


if __name__ == "__main__":
    unittest.main()
