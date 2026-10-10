"""auswahl_quant.py: Quant-Spalte, Rangfolge --rang quant, Short-Spiegelung. Ohne Netz."""

import contextlib
import io
import math
import sys
import unittest
from pathlib import Path
from unittest import mock

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))

import auswahl_quant as a                                     # noqa: E402


def kerzen(steigung, n, hf=0.0):
    out = []
    for i in range(n):
        c = 100.0 * math.exp(steigung * i) * (1 + hf * (1 if i % 2 else -1))
        out.append([i * 14400000, c, c * 1.01, c * 0.99, c, 1000.0])
    return out


INSTR = [{"instId": "UP-USDT-SWAP", "lever": "20"},
         {"instId": "DOWN-USDT-SWAP", "lever": "20"}]
STEIG = {"UP-USDT-SWAP": 0.002, "DOWN-USDT-SWAP": -0.002}


def sammeln():
    def holen(iid, bar, n):
        # 4H-Fenster kurz, Tagesfenster lang genug fuer das Urteil
        return kerzen(STEIG[iid], 300)
    with mock.patch.object(a.okxf, "instrumente", return_value=INSTR), \
            mock.patch.object(a.okxf, "tickers", return_value={}), \
            mock.patch.object(a.okxf, "kerzen", side_effect=holen), \
            mock.patch.object(a.time, "sleep"):
        return a.sammle(still=True, kategorien=["krypto"])


class AuswahlQuantTest(unittest.TestCase):
    def test_beide_richtungen_am_wert(self):
        d = {z["basis"]: z for z in sammeln()}
        self.assertGreater(d["UP"]["quant"]["long"]["quant_score"],
                           d["UP"]["quant"]["short"]["quant_score"])
        self.assertGreater(d["DOWN"]["quant"]["short"]["quant_score"],
                           d["DOWN"]["quant"]["long"]["quant_score"])

    def test_rang_quant_stellt_passenden_wert_nach_vorn(self):
        d = sammeln()
        for zweck, erwartet in (("long", "UP"), ("short", "DOWN")):
            aus = io.StringIO()
            with contextlib.redirect_stdout(aus):
                a.tabelle(d, zweck, 5, rang="quant")
            zeilen = [x for x in aus.getvalue().splitlines()
                      if x.startswith(("UP ", "DOWN "))]
            self.assertTrue(zeilen[0].startswith(erwartet), (zweck, zeilen))

    def test_grid_hat_keine_q_spalte(self):
        aus = io.StringIO()
        with contextlib.redirect_stdout(aus):
            a.tabelle(sammeln(), "grid", 5)
        self.assertNotIn("   Q", aus.getvalue().splitlines()[4])

    def test_unter_210_tagen_kein_urteil_und_kein_absturz(self):
        with mock.patch.object(a.okxf, "instrumente", return_value=INSTR[:1]), \
                mock.patch.object(a.okxf, "tickers", return_value={}), \
                mock.patch.object(a.okxf, "kerzen",
                                  side_effect=lambda i, b, n: kerzen(0.002, 100)
                                  if b == "1D" else kerzen(0.002, 300)), \
                mock.patch.object(a.time, "sleep"):
            d = a.sammle(still=True, kategorien=["krypto"])
        self.assertIsNone(d[0]["quant"]["long"])
        aus = io.StringIO()
        with contextlib.redirect_stdout(aus):
            a.tabelle(d, "long", 5, rang="quant")     # darf nicht abstuerzen
            a.detail(d[0])


if __name__ == "__main__":
    unittest.main()
