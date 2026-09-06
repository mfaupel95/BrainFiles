import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import bewertung  # noqa: E402
import ruecktest  # noqa: E402


def _kerzen(n):
    k, p = [], 100.0
    for i in range(n):
        p *= 1.0 + (0.005 if i % 4 else -0.006)
        k.append([i * 86400000, p, p * 1.02, p * 0.98, p, 1000.0 + i % 7])
    return k


class TestMatrix(unittest.TestCase):
    def test_matrix_entspricht_direktem_aufruf(self):
        kerzen = {"BTC-USDT": _kerzen(150)}
        m = ruecktest.merkmals_matrix(kerzen)
        tag = 140
        direkt = bewertung.roh_komponenten(kerzen["BTC-USDT"][:tag + 1])
        self.assertEqual(m["BTC-USDT"][tag], direkt)

    def test_keine_eintraege_vor_mindest_kerzen(self):
        m = ruecktest.merkmals_matrix({"BTC-USDT": _kerzen(150)})
        self.assertTrue(min(m["BTC-USDT"]) >= ruecktest.MINDEST_KERZEN)

    def test_deterministisch(self):
        kerzen = {"X": _kerzen(140)}
        self.assertEqual(ruecktest.merkmals_matrix(kerzen),
                         ruecktest.merkmals_matrix(kerzen))
