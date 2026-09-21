"""Tests fuer den Rueckdreh-Ausstieg (trendwende_btc).

AUFTRAG Max 21.09.2026: "Rueckdreh einbauen". Die Spur steigt beim Wechsel des
SuperTrend von +1 auf -1 short ein; der ehrliche Gegenpart ist der Ausstieg,
sobald der Trend wieder auf +1 steht. Sonst endet ein Short erst an Stop, Ziel
oder Frist - also moeglicherweise lange nachdem seine Begruendung entfallen ist.

Geprueft wird die REGEL, nicht ein Datenlauf: trend_richtung() wird ersetzt,
damit kein Netz noetig ist und der Fall eindeutig bleibt.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parents[0]
for p in (HANDEL / "scanner", HANDEL / "xperp", SPUR):
    if str(p) in sys.path:
        sys.path.remove(str(p))
    sys.path.insert(0, str(p))

import handeln as h                                                 # noqa: E402

assert str(Path(h.__file__).resolve()).startswith(str(SPUR)), h.__file__

W = json.loads((SPUR / "wachen.json").read_text(encoding="utf-8"))


class Rueckdreh(unittest.TestCase):
    def setUp(self):
        self._echt = h.trend_richtung

    def tearDown(self):
        h.trend_richtung = self._echt

    def _mit(self, richtung):
        h.trend_richtung = lambda w: richtung

    def test_trend_wieder_aufwaerts_beendet_den_short(self):
        self._mit(1)
        self.assertEqual(h.rueckdreh({"seite": "short"}, W), "rueckdreh")

    def test_trend_weiter_abwaerts_laesst_laufen(self):
        self._mit(-1)
        self.assertIsNone(h.rueckdreh({"seite": "short"}, W))

    def test_unbekannte_richtung_beendet_nichts(self):
        # Kein Kurs, kein Indikator - dann wird NICHT verkauft. Ein Ausstieg
        # aus Unwissen waere schlechter als keiner.
        self._mit(None)
        self.assertIsNone(h.rueckdreh({"seite": "short"}, W))

    def test_long_position_wird_nicht_angefasst(self):
        # Die Spur eroeffnet keine Longs; eine Long-Position waere ein
        # Fremdkoerper und darf nicht von dieser Regel geschlossen werden.
        self._mit(1)
        self.assertIsNone(h.rueckdreh({"seite": "long"}, W))

    def test_abschaltbar_ueber_die_wachen(self):
        self._mit(1)
        aus = dict(W, ausstieg_bei_rueckdreh=False)
        self.assertIsNone(h.rueckdreh({"seite": "short"}, aus))

    def test_vorgabe_ist_an(self):
        self.assertTrue(W.get("ausstieg_bei_rueckdreh"))


class StopHatVorrang(unittest.TestCase):
    """spur_buch fragt den Zusatz erst NACH Stop und Ziel.

    Das ist keine Kosmetik: ist der Stop gerissen, muss 'stop' im Journal
    stehen - sonst rechnet jede spaetere Auswertung die Runde falsch zu.
    """

    def test_reihenfolge_in_spur_buch(self):
        import inspect
        import spur_buch
        quelle = inspect.getsource(spur_buch.pruefe_ausstiege)
        self.assertLess(quelle.index('grund = "stop"'),
                        quelle.index("zusatz(p, w)"))

    def test_zusatz_ist_optional(self):
        import inspect
        import spur_buch
        sig = inspect.signature(spur_buch.pruefe_ausstiege)
        self.assertIn("zusatz", sig.parameters)
        self.assertIsNone(sig.parameters["zusatz"].default)


class Verdrahtung(unittest.TestCase):
    def test_zyklus_bekommt_den_rueckdreh(self):
        quelle = (SPUR / "handeln.py").read_text(encoding="utf-8")
        self.assertIn("zusatz_ausstieg=rueckdreh", quelle)

    def test_signal_und_rueckdreh_teilen_die_rechnung(self):
        # Beide benutzen trend_richtung bzw. dieselben Wachen-Werte - zwei
        # Kopien derselben Formel waeren die Stelle, an der Einstieg und
        # Ausstieg auseinanderlaufen.
        quelle = (SPUR / "handeln.py").read_text(encoding="utf-8")
        self.assertIn("def trend_richtung(w)", quelle)
        self.assertIn("trend_richtung(w) == 1", quelle)


if __name__ == "__main__":
    unittest.main()
