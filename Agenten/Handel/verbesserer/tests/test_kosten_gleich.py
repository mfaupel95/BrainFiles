import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
SCANNER = WURZEL.parent / "scanner"
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(SCANNER))


class TestKostenGleich(unittest.TestCase):
    def test_konstante_identisch(self):
        import kosten
        import handeln
        self.assertEqual(kosten.GEBUEHR_PCT, handeln.GEBUEHR_PCT)


if __name__ == "__main__":
    unittest.main()
