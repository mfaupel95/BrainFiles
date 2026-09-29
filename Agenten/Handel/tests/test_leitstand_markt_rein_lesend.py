"""Markt-Reiter bleibt rein lesend: keine Schreibstelle, kein Prozess, kein
Boersen-Client (auch nicht ueber prognose.py, das okx importiert).

Direkt ausfuehrbar:  python tests/test_leitstand_markt_rein_lesend.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import leitstand_markt as lm                                   # noqa: E402
import lesepruefung                                            # noqa: E402


class ReinLesend(unittest.TestCase):
    def test_keine_schreibstelle(self):
        self.assertEqual(lesepruefung.schreibstellen(lm.__file__), [])

    def test_kein_prozess_und_kein_boersen_client(self):
        for modul in ("subprocess", "prognose", "okx", "ccxt", "requests", "urllib",
                      "kraken", "freigabefenster", "backtest_urteile"):
            self.assertFalse(lesepruefung.importiert(lm.__file__, modul), modul)


if __name__ == "__main__":
    unittest.main()
