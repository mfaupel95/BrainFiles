"""Tests: Handpositionen (herkunft=boerse_handgriff) werden NICHT automatisch geschlossen.

ANLASS (06.10.2026, Vorfall NIGHT-XPERP): Max eroeffnet eine OKX-Position von
Hand; die Spur uebernimmt sie als Fremdposition (herkunft=boerse_handgriff).
Weil die von Hand eroeffnete Position an der OKX keine Boersen-Stop-Kennung
traegt, konnte die Spur weder Stop noch Trailing an der Boerse verankern
(Journal den ganzen Tag: "trailing nicht ausgefuehrt: keine Boersen-Stop-
Kennung in der Position"). Am 06.10. um 16:31:59 UTC schloss pruefe_ausstiege
die Position trotzdem mit grund=stop, als der Kurs fiel - Max wollte sie aber
halten ("ja war meine und das wollte ich", Auftrag 06.10.2026).

REGEL: Positionen mit herkunft=boerse_handgriff werden von pruefe_ausstiege
und flach_stellen (Kill/Kill-Switch/Notaus) NICHT geschlossen. Die Spur fuehrt
sie im Buch (Funding, Journal, Bilanz), aber der Ausstieg gehoert Max.

Die Tests schreiben nie in die echten Dateien: `journal` wird ersetzt und
`okxf` gestubbt (Muster aus test_handeln_geister.py).
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

import handeln as h                                                  # noqa: E402


def _handpos(inst="NIGHT-USD_UM_XPERP-310718"):
    """Eine von Max von Hand an der Boerse eroeffnete Position (der NIGHT-Fall)."""
    return {"inst": inst, "basis": "NIGHT", "seite": "long", "familie": "krypto",
            "einstieg": 0.050007, "nominal": 2244.29, "margin": 283.59,
            "hebel": 8.0, "kontrakte": 461.0, "stop": 0.048188,
            "ziel": 0.055, "liq": 0.0, "modus": "live",
            "herkunft": "boerse_handgriff",
            "pos_id": "20261006T073947-7d6ed4", "eroeffnet_zeit": "2026-10-06T07:39:48+00:00"}


def _normpos(inst="BTC-USD_UM_XPERP-310900"):
    """Eine normale Spur-Position (darf weiter automatisch geschlossen werden)."""
    return {"inst": inst, "basis": "BTC", "seite": "long", "familie": "krypto",
            "einstieg": 1.0, "nominal": 100.0, "margin": 20.0,
            "hebel": 5.0, "kontrakte": 10.0, "stop": 0.95,
            "ziel": 1.10, "liq": 0.0, "modus": "live",
            "pos_id": "20261006T090000-abc123", "eroeffnet_zeit": "2026-10-06T09:00:00+00:00"}


class HandpositionAusstieg(unittest.TestCase):
    def setUp(self):
        self.geschrieben = []
        self.j = patch.object(h, "journal",
                              side_effect=lambda **k: self.geschrieben.append(k))
        self.j.start()
        self.addCleanup(self.j.stop)

    def test_ausstieg_ueberspringt_handposition_bei_stop_beruehrt(self):
        """Der NIGHT-Fall: Kurs unter Stop -> pruefe_ausstiege darf NICHT schliessen."""
        p = _handpos()
        z = {"positionen": [p], "letzte_stops": {}}
        # Kurs = 0.048 (unter stop 0.048188) -> eine normale Position wuerde mit
        # grund=stop geschlossen. Handposition bleibt.
        with patch.object(h.okxf, "letzter_kurs_mit_fallback",
                          return_value=(p["inst"], 0.0480)):
            h.pruefe_ausstiege(z, live=True, w={})
        self.assertEqual(len(z["positionen"]), 1, "Handposition muss im Buch bleiben")
        self.assertEqual(z["positionen"][0]["inst"], "NIGHT-USD_UM_XPERP-310718")

    def test_ausstieg_ueberspringt_handposition_auch_bei_ziel(self):
        p = _handpos()
        z = {"positionen": [p], "letzte_stops": {}}
        with patch.object(h.okxf, "letzter_kurs_mit_fallback",
                          return_value=(p["inst"], 0.060)):
            h.pruefe_ausstiege(z, live=True, w={})
        self.assertEqual(len(z["positionen"]), 1)

    def test_kill_laesst_handposition_stehen(self):
        """flach_stellen (kill_switch/Notaus) darf Handpositionen nicht schliessen."""
        p = _handpos()
        z = {"positionen": [p]}
        with patch.object(h.okxf, "letzter_kurs_mit_fallback",
                          return_value=(p["inst"], 0.0480)):
            h.flach_stellen(z, live=True, grund="kill_switch")
        self.assertEqual(len(z["positionen"]), 1, "Kill darf Handposition nicht flachstellen")

    def test_normale_position_wird_weiter_geschlossen(self):
        """Gegenprobe: die Regel darf NUR Handpositionen schonen."""
        n = _normpos()
        z = {"positionen": [n], "letzte_stops": {}}
        with patch.object(h.okxf, "letzter_kurs_mit_fallback",
                          return_value=(n["inst"], 0.90)), \
             patch.object(h.okxf, "markt_schliessen") as schliessen:
            h.pruefe_ausstiege(z, live=True, w={})
        schliessen.assert_called_once()
        self.assertEqual(len(z["positionen"]), 0)
        grund = [g for g in self.geschrieben if g.get("aktion") == "schliessen"]
        self.assertEqual(grund[0]["grund"], "stop")

    def test_kill_flacht_normale_position_weiter(self):
        n = _normpos()
        z = {"positionen": [n]}
        with patch.object(h.okxf, "letzter_kurs_mit_fallback",
                          return_value=(n["inst"], 0.90)), \
             patch.object(h.okxf, "markt_schliessen") as schliessen:
            h.flach_stellen(z, live=True, grund="kill_switch")
        schliessen.assert_called_once()
        self.assertEqual(len(z["positionen"]), 0)


class HandpositionSchalter(unittest.TestCase):
    """Schalter handpositionen_automatisch_schliessen (T-374, 11.10.2026).

    true = Handpositionen werden wieder automatisch geschlossen (Stop/Ziel/
    Kill greifen wie bei jeder Position). false/fehlt = sie bleiben stehen.
    """

    def setUp(self):
        self.geschrieben = []
        self.j = patch.object(h, "journal",
                              side_effect=lambda **k: self.geschrieben.append(k))
        self.j.start()
        self.addCleanup(self.j.stop)

    def test_schalter_true_schliesst_handposition_bei_stop(self):
        """w={'handpositionen_automatisch_schliessen': True} -> Stop greift."""
        p = _handpos()
        z = {"positionen": [p], "letzte_stops": {}}
        with patch.object(h.okxf, "letzter_kurs_mit_fallback",
                          return_value=(p["inst"], 0.0480)), \
             patch.object(h.okxf, "markt_schliessen") as schliessen:
            h.pruefe_ausstiege(z, live=True,
                               w={"handpositionen_automatisch_schliessen": True})
        schliessen.assert_called_once()
        self.assertEqual(len(z["positionen"]), 0)

    def test_schalter_true_kill_flacht_handposition(self):
        """flach_stellen mit Schalter true schliesst die Handposition."""
        p = _handpos()
        z = {"positionen": [p]}
        with patch.object(h.okxf, "letzter_kurs_mit_fallback",
                          return_value=(p["inst"], 0.0480)), \
             patch.object(h.okxf, "markt_schliessen") as schliessen:
            h.flach_stellen(z, live=True, grund="kill_switch",
                            w={"handpositionen_automatisch_schliessen": True})
        schliessen.assert_called_once()
        self.assertEqual(len(z["positionen"]), 0)

    def test_schalter_false_laesst_handposition_stehen(self):
        """Gegenprobe: false (oder fehlend) behaelt das aktuelle Verhalten."""
        p = _handpos()
        z = {"positionen": [p], "letzte_stops": {}}
        with patch.object(h.okxf, "letzter_kurs_mit_fallback",
                          return_value=(p["inst"], 0.0480)):
            h.pruefe_ausstiege(z, live=True,
                               w={"handpositionen_automatisch_schliessen": False})
        self.assertEqual(len(z["positionen"]), 1)


if __name__ == "__main__":
    unittest.main()
