"""Tests: NVDA-Phi - LLM-Filter nur im Papierlauf und nur fuer NVDA.

ANLASS (2026-10-13, Auftrag Max): Max will Phi (das LLM) fuer NVDA in der
xperp-Papierspur. Das LLM darf NUR im Papierlauf laufen und NUR fuer NVDA-
Kandidaten. Ein Regressionstest beweist, dass der Live-Lauf Phi nie aufruft.

Die Bedingung steht in `_phi_prueken()` (handeln.py) - drei Komponenten:
  1. nicht live (Papierlauf)
  2. basis == "NVDA"
  3. llm_aktiv in den Wachen

Der Override (llm_modell/llm_weg) steht in `pruefe_einstiege()` - nur fuer
den NVDA-Aufruf, die gemeinsame wachen.json bleibt unveraendert.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parent
sys.path.insert(0, str(SPUR))
sys.path.insert(0, str(HANDEL))

import handeln as h  # noqa: E402


class PhiBedingung(unittest.TestCase):
    """_phi_pruefen: die Bedingung fuer den LLM-Aufruf."""

    def test_papier_nvda_llm_aktiv(self):
        """Papier + NVDA + llm_aktiv -> True."""
        self.assertTrue(
            h._phi_pruefen({"basis": "NVDA"}, False, {"llm_aktiv": True}))

    def test_live_nvda_llm_aktiv(self):
        """Live + NVDA + llm_aktiv -> False (live ruft Phi nie auf)."""
        self.assertFalse(
            h._phi_pruefen({"basis": "NVDA"}, True, {"llm_aktiv": True}))

    def test_live_btc_llm_aktiv(self):
        """Live + BTC + llm_aktiv -> False."""
        self.assertFalse(
            h._phi_pruefen({"basis": "BTC"}, True, {"llm_aktiv": True}))

    def test_papier_btc_llm_aktiv(self):
        """Papier + BTC + llm_aktiv -> False (nur NVDA)."""
        self.assertFalse(
            h._phi_pruefen({"basis": "BTC"}, False, {"llm_aktiv": True}))

    def test_papier_nvda_llm_inaktiv(self):
        """Papier + NVDA + llm_aktiv=False -> False."""
        self.assertFalse(
            h._phi_pruefen({"basis": "NVDA"}, False, {"llm_aktiv": False}))


class LiveRuftPhiNichtAuf(unittest.TestCase):
    """Regressionstest: Live-Lauf ruft llm_filter nie auf."""

    def setUp(self):
        self.kand = [{
            "basis": "NVDA", "seite": "long", "kategorie": "aktie",
            "instId": "NVDA-USD_UM_XPERP-310900",
            "punkte": {"long": 5.0, "short": 0.0}, "deckel": 5.0,
        }]
        self.w = {
            "llm_aktiv": True, "llm_modell": "bonsai", "llm_weg": "bonsai",
            "max_margin_gesamt_usd": 600.0,
            "risiko_je_anlauf_usd": 7.5, "max_hebel": 5,
            "max_offene_anlaeufe": 4, "stop_atr_faktor": 1.25,
            "ziel_atr_faktor": 3.0, "einstieg_atr_abschlag": 0.25,
            "wartungsmarge": 0.005, "gebuehr_taker": 0.0005,
        }

    def test_live_nvda_kein_llm(self):
        """pruefe_einstiege(live=True) ruft urteile_kandidat nie auf."""
        with patch.object(h.llm_filter, "urteile_kandidat") as urteile,              patch.object(h, "anlauf", return_value=None),              patch.object(h, "zugelassen", return_value=h.ERLAEUT):
            h.pruefe_einstiege({"positionen": []}, self.kand, self.w,
                               live=True, s={"wochenende": False})
        urteile.assert_not_called()

    def test_live_btc_kein_llm(self):
        """pruefe_einstiege(live=True) mit BTC ruft urteile_kandidat nie auf."""
        kand_btc = [{"basis": "BTC", "seite": "long", "kategorie": "krypto",
                     "instId": "BTC-USD_UM_XPERP-310900",
                     "punkte": {"long": 5.0, "short": 0.0}, "deckel": 5.0}]
        with patch.object(h.llm_filter, "urteile_kandidat") as urteile,              patch.object(h, "anlauf", return_value=None),              patch.object(h, "zugelassen", return_value=h.ERLAEUT):
            h.pruefe_einstiege({"positionen": []}, kand_btc, self.w,
                               live=True, s={"wochenende": False})
        urteile.assert_not_called()


class PapierRuftPhiFuerNvdaAuf(unittest.TestCase):
    """Integrationstest: Papier-Lauf ruft llm_filter fuer NVDA auf."""

    def setUp(self):
        self.kand = [{
            "basis": "NVDA", "seite": "long", "kategorie": "aktie",
            "instId": "NVDA-USD_UM_XPERP-310900",
            "punkte": {"long": 5.0, "short": 0.0}, "deckel": 5.0,
        }]
        self.w = {
            "llm_aktiv": True, "llm_modell": "bonsai", "llm_weg": "bonsai",
            "max_margin_gesamt_usd": 600.0,
            "risiko_je_anlauf_usd": 7.5, "max_hebel": 5,
            "max_offene_anlaeufe": 4, "stop_atr_faktor": 1.25,
            "ziel_atr_faktor": 3.0, "einstieg_atr_abschlag": 0.25,
            "wartungsmarge": 0.005, "gebuehr_taker": 0.0005,
        }

    def test_papier_nvda_llm_wird_aufgerufen(self):
        """pruefe_einstiege(live=False) mit NVDA ruft urteile_kandidat auf."""
        with patch.object(h.llm_filter, "urteile_kandidat",
                         return_value=(None, {"fehler": "test"})) as urteile,              patch.object(h, "anlauf", return_value=None),              patch.object(h, "zugelassen", return_value=h.ERLAEUT),              patch.object(h.okxf, "kerzen", return_value=[]):
            h.pruefe_einstiege({"positionen": []}, self.kand, self.w,
                               live=False, s={"wochenende": False})
        urteile.assert_called()

    def test_papier_nvda_phi_konfiguration(self):
        """NVDA paper bekommt Phi: llm_modell=phi4-mini, llm_weg=ollama."""
        with patch.object(h.llm_filter, "urteile_kandidat",
                         return_value=(None, {"fehler": "test"})) as urteile,              patch.object(h, "anlauf", return_value=None),              patch.object(h, "zugelassen", return_value=h.ERLAEUT),              patch.object(h.okxf, "kerzen", return_value=[]):
            h.pruefe_einstiege({"positionen": []}, self.kand, self.w,
                               live=False, s={"wochenende": False})
        w_gerufen = urteile.call_args[0][3]
        self.assertEqual(w_gerufen.get("llm_modell"), "phi4-mini")
        self.assertEqual(w_gerufen.get("llm_weg"), "ollama")

    def test_papier_nvda_original_w_unveraendert(self):
        """Das originale w (bonsai) wird nicht veraendert."""
        w_kopie = dict(self.w)
        with patch.object(h.llm_filter, "urteile_kandidat",
                         return_value=(None, {"fehler": "test"})),              patch.object(h, "anlauf", return_value=None),              patch.object(h, "zugelassen", return_value=h.ERLAEUT),              patch.object(h.okxf, "kerzen", return_value=[]):
            h.pruefe_einstiege({"positionen": []}, self.kand, w_kopie,
                               live=False, s={"wochenende": False})
        self.assertEqual(w_kopie.get("llm_modell"), "bonsai")
        self.assertEqual(w_kopie.get("llm_weg"), "bonsai")

    def test_papier_btc_kein_llm(self):
        """pruefe_einstiege(live=False) mit BTC ruft urteile_kandidat nicht auf."""
        kand_btc = [{"basis": "BTC", "seite": "long", "kategorie": "krypto",
                     "instId": "BTC-USD_UM_XPERP-310900",
                     "punkte": {"long": 5.0, "short": 0.0}, "deckel": 5.0}]
        with patch.object(h.llm_filter, "urteile_kandidat") as urteile,              patch.object(h, "anlauf", return_value=None),              patch.object(h, "zugelassen", return_value=h.ERLAEUT):
            h.pruefe_einstiege({"positionen": []}, kand_btc, self.w,
                               live=False, s={"wochenende": False})
        urteile.assert_not_called()


if __name__ == "__main__":
    unittest.main()
