"""F7: ausrichten() richtet Kerzenreihen auf gemeinsame Kalendertage aus."""

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import ruecktest  # noqa: E402


def _reihe(tage):
    """Kerze je Kalendertag: [ts, o, h, l, c, vol]. ts = tag * 86400000."""
    return [[t * 86400000, 100.0, 103.0, 97.0, 100.0, 1000.0] for t in tage]


class TestAusrichten(unittest.TestCase):
    def test_gleiche_reihen_bleiben_gleich(self):
        reihen = {"AAA": _reihe(range(10)), "BBB": _reihe(range(10))}
        aus, hinweise = ruecktest.ausrichten(reihen)
        self.assertEqual(aus["AAA"], reihen["AAA"])
        self.assertEqual(aus["BBB"], reihen["BBB"])
        self.assertEqual(hinweise, [])

    def test_fehlender_tag_faellt_aus_der_schnittmenge(self):
        # BBB fehlt Tag 5 -> Schnittmenge ist 0..9 ohne 5; beide 9 lang.
        reihen = {"AAA": _reihe(range(10)),
                  "BBB": _reihe([t for t in range(10) if t != 5])}
        aus, hinweise = ruecktest.ausrichten(reihen)
        self.assertEqual(len(aus["AAA"]), 9)
        self.assertEqual(len(aus["BBB"]), 9)
        tage_aaa = [k[0] // 86400000 for k in aus["AAA"]]
        self.assertNotIn(5, tage_aaa)
        self.assertTrue(hinweise)

    def test_zu_kurzes_instrument_wird_verworfen_und_gemeldet(self):
        # CCC hat nur 5 von 10 Tagen (< 90 %) -> verworfen.
        reihen = {"AAA": _reihe(range(10)), "BBB": _reihe(range(10)),
                  "CCC": _reihe(range(5))}
        aus, hinweise = ruecktest.ausrichten(reihen)
        self.assertNotIn("CCC", aus)
        self.assertIn("AAA", aus)
        self.assertTrue(any("CCC" in h for h in hinweise))

    def test_doppelter_tag_eine_kerze_je_tag(self):
        # Zwei Kerzen am Tag 3 (verschiedene ts in derselben 24h) -> die
        # spaetere bleibt, die Reihe verschiebt sich nicht.
        reihen = {"AAA": _reihe(range(5)),
                  "BBB": _reihe(range(5)) + [[3 * 86400000 + 1, 1, 2, 3, 9.0, 1]]}
        aus, _ = ruecktest.ausrichten(reihen)
        self.assertEqual(len(aus["BBB"]), 5)
        tag3 = [k for k in aus["BBB"] if k[0] // 86400000 == 3]
        self.assertEqual(len(tag3), 1)
        self.assertEqual(tag3[0][4], 9.0)  # die spaetere Kerze

    def test_idempotent(self):
        reihen = {"AAA": _reihe(range(10)),
                  "BBB": _reihe([t for t in range(10) if t != 5])}
        einmal, _ = ruecktest.ausrichten(reihen)
        zweimal, hinweise2 = ruecktest.ausrichten(einmal)
        self.assertEqual(einmal, zweimal)
        self.assertEqual(hinweise2, [])

    def test_leere_eingabe(self):
        self.assertEqual(ruecktest.ausrichten({}), ({}, []))

    def test_alle_unter_min_anteil_wirft_nicht(self):
        # Nur ein Instrument -> max_tage = seine eigene Laenge, es bleibt immer.
        # Prueft, dass behalten nie leer an set.intersection(*[]) geht:
        # kuenstlich via min_anteil > 1.0 alle verwerfen.
        reihen = {"AAA": _reihe(range(10)), "BBB": _reihe(range(10))}
        aus, hinweise = ruecktest.ausrichten(reihen, min_anteil=1.1)
        self.assertEqual(aus, {})
        self.assertTrue(hinweise)


if __name__ == "__main__":
    unittest.main()
