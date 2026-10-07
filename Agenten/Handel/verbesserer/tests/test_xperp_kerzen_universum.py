import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_kerzen  # noqa: E402


def _instr(basis, suffix="-USD_UM_XPERP-310620"):
    return {"instId": basis + suffix}


class TestUniversum(unittest.TestCase):
    def test_hole_universum_fasst_drei_familien_zusammen_und_cacht(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(
                    xperp_kerzen.okxf, "instrumente",
                    side_effect=lambda kategorie: {
                        xperp_kerzen.okxf.KRYPTO: [_instr("BTC")],
                        xperp_kerzen.okxf.AKTIE: [_instr("NVDA")],
                        xperp_kerzen.okxf.ROHSTOFF: [_instr("XAU")],
                    }[kategorie]):
                u = xperp_kerzen.hole_universum(cache_dir=d)
            self.assertEqual(sorted(x["basis"] for x in u),
                             ["BTC", "NVDA", "XAU"])
            kat = {x["basis"]: x["kategorie"] for x in u}
            self.assertEqual(kat["NVDA"], "aktie")

            geladen = xperp_kerzen.laden_universum(cache_dir=d)
            self.assertEqual(len(geladen), 3)

    def test_laden_universum_ohne_cache_gibt_leere_liste(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(xperp_kerzen.laden_universum(cache_dir=d), [])


if __name__ == "__main__":
    unittest.main()
