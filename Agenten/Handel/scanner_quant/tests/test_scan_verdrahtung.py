"""scan.py (Quant-Kopie): Modi bericht/tor/aus, ohne Netz, ohne Schreiben.

Okx wird durch eine Attrappe ersetzt. Geprueft wird die VERDRAHTUNG - ob das
Urteil im Bericht ankommt und ob 'tor' sperrt -, nicht die Rechnung (die
steht in test_quant.py).
"""

import contextlib
import io
import math
import sys
import unittest
from pathlib import Path
from unittest import mock

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))

import scan                                                   # noqa: E402


def kerzen(steigung, n=300):
    out = []
    for i in range(n):
        c = 100.0 * math.exp(steigung * i)
        out.append([i * 86400000, c, c * 1.01, c * 0.99, c, 1000.0 * (1 + i % 3)])
    return out


WACHEN = {"universum": {"modus": "watchlist"}, "watchlist": ["AAA-USDC"],
          "mindest_score": 0, "max_volatilitaet_pa": 99.0,
          "mindest_chance_risiko": 0.0}


def lauf_mit(q):
    stumm = io.StringIO()
    with mock.patch.object(scan, "wachen", return_value=WACHEN), \
            mock.patch.object(scan, "quant_einstellung", return_value=q), \
            mock.patch.object(scan.okx, "kerzen",
                              side_effect=lambda inst, *a: kerzen(0.002)), \
            mock.patch.object(scan.time, "sleep"), \
            contextlib.redirect_stdout(stumm):
        bericht = scan.lauf(kurz=True)
    return bericht, stumm.getvalue()


class ModiTest(unittest.TestCase):
    def test_aus_ist_wie_das_original(self):
        b, text = lauf_mit({"aktiv": False})
        self.assertNotIn("quant", b["werte"][0])
        self.assertNotIn("QScore", text)
        self.assertIsNone(b["quant"])

    def test_bericht_haengt_urteil_an_und_aendert_das_tor_nicht(self):
        b, text = lauf_mit({"aktiv": True, "modus": "bericht",
                            "mindest_quant_score": 101})
        self.assertIn("quant_score", b["werte"][0]["quant"])
        self.assertIn("QScore", text)
        self.assertIn("| JA", text)          # Tor offen trotz unerreichbarer Schwelle

    def test_tor_sperrt_bei_zu_niedrigem_quant_score(self):
        _, text = lauf_mit({"aktiv": True, "modus": "tor",
                            "mindest_quant_score": 101})
        self.assertNotIn("| JA", text)

    def test_tor_laesst_gesunden_trend_durch(self):
        _, text = lauf_mit({"aktiv": True, "modus": "tor",
                            "mindest_quant_score": 50})
        self.assertIn("| JA", text)


if __name__ == "__main__":
    unittest.main()
