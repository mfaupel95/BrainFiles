"""Ein Papierzyklus darf KEINE echte Position schliessen (24.09.2026).

Das scanner-Buch ist EINES fuer Papier und Live. Gemessen am 24.09.2026 trug es
fuenf LIVE-Positionen (ETH/SOL/HYPE/BTC/ZEC, alle mit kauf_ord_id) und der Lauf
stand auf `live`, weil das Freigabefenster offen war. Sobald das Fenster
schliesst (Auto-Freigabe 12 h), laeuft dieselbe Spur als Papier - und haette
beim naechsten Stop-/Zielkurs die Buchzeile geloescht, waehrend die Position an
OKX offen bleibt: der boersenseitige Stop wuerde spaeter ohne Buchzeile
ausloesen (dieselbe Klasse wie xperp/HBAR und mosaic am 21./23.09.2026).

Diese Tests halten die Regel fest:
  * Papierlauf + echte Position (kauf_ord_id) -> bleibt stehen, keine Zeile
  * Papierlauf + Papierposition            -> wird wie immer geschlossen
  * Live-Lauf  + echte Position            -> wird geschlossen
  * flach_stellen (Notaus) ebenso
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parent
sys.path.insert(0, str(HANDEL))
sys.path.insert(0, str(SPUR))

import handeln as h                                                  # noqa: E402

assert Path(h.__file__).resolve().parent == SPUR, "falsches Modul: %s" % h.__file__

LIVE_POS = {"inst": "ETH-USDC", "usd": 100.0, "einstieg": 2600.0, "stop": 2500.0,
            "ziel": 3000.0, "kauf_ord_id": "3943775234458243072"}
PAPIER_POS = {"inst": "SOL-USDC", "usd": 50.0, "einstieg": 100.0, "stop": 90.0,
              "ziel": 130.0}


class KeinEingriffInEchtePositionen(unittest.TestCase):

    def setUp(self):
        self.zeilen = []
        self.p = [
            patch.object(h, "journal", side_effect=lambda *a, **k: self.zeilen.append(a)),
            patch.object(h, "_live_verkauf",
                         side_effect=AssertionError("Papierlauf hat live verkauft")),
            patch.object(h.okx, "letzter_kurs", side_effect=lambda inst: 2400.0)  # unter dem Stop
        ]
        for q in self.p:
            q.start()

    def tearDown(self):
        for q in self.p:
            q.stop()

    def test_papierlauf_laesst_echte_position_stehen(self):
        z = {"positionen": [dict(LIVE_POS)]}
        h.pruefe_ausstiege(z, live=False)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self.zeilen, [])

    def test_papierlauf_schliesst_papierposition_weiterhin(self):
        z = {"positionen": [dict(PAPIER_POS)]}
        h.pruefe_ausstiege(z, live=False)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(len(self.zeilen), 1)
        self.assertEqual(self.zeilen[0][1], "papier")

    def test_livelauf_schliesst_echte_position(self):
        z = {"positionen": [dict(LIVE_POS)], "letzte_stops": {}, "letzte_ziele": {}}
        with patch.object(h, "_live_verkauf", return_value="verkauft"):
            h.pruefe_ausstiege(z, live=True)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self.zeilen[0][1], "live")

    def test_notaus_im_papierlauf_laesst_echte_position_stehen(self):
        z = {"positionen": [dict(LIVE_POS), dict(PAPIER_POS)]}
        h.flach_stellen(z, live=False, grund="kill_switch")
        self.assertEqual([q["inst"] for q in z["positionen"]], ["ETH-USDC"])

    def test_kennung_ist_die_kauf_order(self):
        self.assertTrue(h.ist_live_position(LIVE_POS))
        self.assertFalse(h.ist_live_position(PAPIER_POS))
        self.assertFalse(h.ist_live_position({"inst": "X", "kauf_ord_id": ""}))


_VORHER = {p.name: p.stat().st_size for p in SPUR.iterdir() if p.is_file()}


def tearDownModule():
    nachher = {p.name: p.stat().st_size for p in SPUR.iterdir() if p.is_file()}
    neu = set(nachher) - set(_VORHER)
    weg = set(_VORHER) - set(nachher)
    geaendert = {n for n in set(_VORHER) & set(nachher) if _VORHER[n] != nachher[n]}
    assert not (neu or weg or geaendert), (
        "Tests haben in den echten Spurenordner geschrieben: neu=%s weg=%s geaendert=%s"
        % (sorted(neu), sorted(weg), sorted(geaendert)))


if __name__ == "__main__":
    unittest.main()