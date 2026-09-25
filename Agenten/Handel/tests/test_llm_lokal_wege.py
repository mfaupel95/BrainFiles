"""Zwei Wege zum lokalen Urteil: Ollama (/api/chat) und der OpenAI-Weg (Bonsai).

Anlass (T-084, 25.09.2026): `moondev_whale`, `-liquidation`, `-sentiment` holen
ihr Urteil ueber `Handel/llm_lokal.py`. Das war fest auf Ollamas eigene
Schnittstelle verdrahtet; Bonsai 2 27B (PrismML-Fork von llama.cpp) bietet sie
nicht - dort gibt es nur `/v1/chat/completions` (gemessen: `/api/chat` -> 404).
Der Weg wird deshalb je Spur in der wachen.json gewaehlt (`llm_weg`), sonst aus
dem Modellnamen abgeleitet.

Geprueft wird:
  1. die Wahl des Wegs (ausdruecklich, wachen-Feld, Modellname, Vorgabe)
  2. dass jeder Weg seinen EIGENEN Aufruf benutzt (kein Test darf ins Netz)
  3. der Koerper des OpenAI-Aufrufs: kein Denk-Budget-Fehler (reasoning_effort
     und max_tokens 512 - mit 250 kamen am 25.09.2026 LEERE Antworten zurueck)
  4. dass der Ollama-Weg unveraendert bleibt (`think: false`)
  5. die Kette bis zum Urteil inklusive Confidence-Tor und Nachfassen
  6. der Zwischenspeicher (ein Aufruf je Marktbild, nicht zwei)
"""

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import llm_lokal as ll                      # noqa: E402

assert ll.__file__.startswith(HANDEL), ll.__file__

GUTES_URTEIL = "SELL\nHohes Volumen beim Abverkauf\nConfidence: 72%"


class FakeAntwort:
    def __init__(self, nutzlast):
        self._daten = json.dumps(nutzlast).encode()

    def read(self):
        return self._daten

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class WegsWahlTest(unittest.TestCase):
    def setUp(self):
        ll.leere_cache()

    def test_ausdruecklicher_weg_gewinnt(self):
        self.assertEqual(ll.weg_aus("qwen35-8k:latest", "bonsai"), "bonsai")
        self.assertEqual(ll.weg_aus("bonsai", "ollama"), "ollama")

    def test_wachenfeld_waehlt(self):
        self.assertEqual(ll.weg_aus(None, None, {"llm_weg": "bonsai"}), "bonsai")
        self.assertEqual(ll.weg_aus(None, None, {"llm_weg": "OLLAMA"}), "ollama")

    def test_modellname_deutet_den_weg(self):
        self.assertEqual(ll.weg_aus("bonsai", None, {}), "bonsai")
        self.assertEqual(ll.weg_aus(
            r"C:\...\Modelle\GGUF\Ternary-Bonsai-2-27B-PTQ1_0.gguf", None, {}),
            "bonsai")
        self.assertEqual(ll.weg_aus("qwen35-8k:latest", None, {}), "ollama")

    def test_ohne_alles_bleibt_es_ollama(self):
        self.assertEqual(ll.weg_aus(None, None, {}), "ollama")


class AufrufTest(unittest.TestCase):
    """Der Aufruf je Weg - mit gefaelschtem Transport, nie echt."""

    def setUp(self):
        ll.leere_cache()
        self.aufrufe = []

        def falsch(req, timeout=None):
            self.aufrufe.append((req.full_url, json.loads(req.data.decode())))
            return FakeAntwort({"choices": [
                {"message": {"content": GUTES_URTEIL}}],
                "message": {"content": GUTES_URTEIL}, "done": True})

        self.p = patch("llm_lokal.urllib.request.urlopen", falsch)
        self.p.start()
        self.addCleanup(self.p.stop)

    def test_bonsai_geht_auf_v1_chat_completions(self):
        text = ll.frage("Marktbild", "bonsai", 30, weg="bonsai")
        self.assertIn("SELL", text)
        url, koerper = self.aufrufe[0]
        self.assertTrue(url.endswith("/v1/chat/completions"), url)
        self.assertEqual(koerper["model"], "bonsai")
        self.assertEqual(koerper["messages"][0]["content"], "Marktbild")

    def test_bonsai_koerper_verhindert_das_denkbudget(self):
        """Mit max_tokens 250 kam eine LEERE Antwort zurueck (Wiki Bonsai)."""
        ll.frage("Marktbild", "bonsai", 30, weg="bonsai")
        koerper = self.aufrufe[0][1]
        self.assertEqual(koerper["reasoning_effort"], "none")
        self.assertGreaterEqual(koerper["max_tokens"], 512)
        self.assertEqual(koerper["stream"], False)
        self.assertEqual(koerper["temperature"], 0)
        self.assertEqual(koerper["seed"], 42)

    def test_ollama_bleibt_bei_api_chat_und_think_false(self):
        ll.frage("Marktbild", "qwen35-8k:latest", 30)
        url, koerper = self.aufrufe[0]
        self.assertTrue(url.endswith("/api/chat"), url)
        self.assertIs(koerper["think"], False)
        self.assertEqual(koerper["options"]["num_predict"], ll.NUM_PREDICT)

    def test_ein_aufruf_je_marktbild(self):
        for _ in range(2):
            ll.frage("dasselbe Bild", "bonsai", 30, weg="bonsai")
        self.assertEqual(len(self.aufrufe), 1,
                         "der Zwischenspeicher muss den zweiten Aufruf sparen")


class UrteilWegTest(unittest.TestCase):
    """Die Kette bis zum Urteil - ueber beide Wege, ohne Netz."""

    def setUp(self):
        ll.leere_cache()

    def test_bonsai_urteil_haelt_den_vertrag(self):
        gesehen = []

        def antwort(prompt, modell, zeitgrenze):
            gesehen.append((prompt, modell, zeitgrenze))
            return GUTES_URTEIL

        with patch.object(ll, "BONSAI_ANFRAGE", antwort):
            seite, info = ll.entscheide("Marktbild", {
                "llm_weg": "bonsai", "llm_modell": "bonsai",
                "llm_mindest_confidence": 60.0})
        self.assertEqual(seite, "short")
        self.assertEqual(info["weg"], "bonsai")
        self.assertEqual(info["modell"], "bonsai")
        self.assertAlmostEqual(info["confidence"], 72.0)
        self.assertEqual(gesehen[0][1], "bonsai")

    def test_bonsai_ohne_modellnamen_nimmt_die_vorgabe(self):
        with patch.object(ll, "BONSAI_ANFRAGE", lambda p, m, z: GUTES_URTEIL):
            _, info = ll.entscheide("Marktbild", {"llm_weg": "bonsai"})
        self.assertEqual(info["modell"], ll.BONSAI_MODELL)

    def test_confidence_tor_gilt_auch_auf_dem_zweiten_weg(self):
        with patch.object(ll, "BONSAI_ANFRAGE",
                          lambda p, m, z: "BUY\nschwach\nConfidence: 40%"):
            seite, info = ll.entscheide("Marktbild", {
                "llm_weg": "bonsai", "llm_mindest_confidence": 60.0})
        self.assertIsNone(seite)
        self.assertIn("zu unsicher", info["fehler"])

    def test_leere_antwort_ist_kein_urteil(self):
        with patch.object(ll, "BONSAI_ANFRAGE", lambda p, m, z: ""):
            seite, info = ll.entscheide("Marktbild", {"llm_weg": "bonsai"})
        self.assertIsNone(seite)
        self.assertIn("bonsai ueber bonsai", info["fehler"])

    def test_unlesbare_antwort_wird_einmal_nachgefasst(self):
        laeufe = []

        def antwort(prompt, modell, zeitgrenze):
            laeufe.append(prompt)
            return "LONGLY ohne Vertrag" if len(laeufe) == 1 else GUTES_URTEIL

        with patch.object(ll, "BONSAI_ANFRAGE", antwort):
            seite, info = ll.entscheide("Marktbild", {"llm_weg": "bonsai"})
        self.assertEqual(seite, "short")
        self.assertTrue(info.get("nachgefasst"))
        self.assertEqual(len(laeufe), 2)
        self.assertIn("Answer again", laeufe[1])

    def test_ollama_weg_bleibt_der_standard(self):
        gesehen = []

        def antwort(prompt, modell, zeitgrenze):
            gesehen.append(modell)
            return GUTES_URTEIL

        with patch.object(ll, "ANFRAGE", antwort):
            seite, info = ll.entscheide("Marktbild", {})
        self.assertEqual(seite, "short")
        self.assertEqual(info["weg"], "ollama")
        self.assertEqual(info["modell"], ll.MODELL_STANDARD)
        self.assertEqual(gesehen, [ll.MODELL_STANDARD])


class DienstTest(unittest.TestCase):
    def test_bonsai_da_liest_die_modellliste(self):
        with patch("llm_lokal.urllib.request.urlopen",
                   lambda u, timeout=None: FakeAntwort({"models": [{"name": "x"}]})):
            self.assertTrue(ll.bonsai_da())

    def test_bonsai_da_ist_false_wenn_der_dienst_schweigt(self):
        def kaputt(u, timeout=None):
            raise OSError("kein Dienst")

        with patch("llm_lokal.urllib.request.urlopen", kaputt):
            self.assertFalse(ll.bonsai_da())


if __name__ == "__main__":
    unittest.main()