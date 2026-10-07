"""KrakenModell: Gebuehr live aus wachen.json, USDC/EURC nach EUR am
Tagesschlusskurs - kein 1:1, keine stille Luecken-Fuellung."""

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import kraken_modell  # noqa: E402


def _fx(tag_kurs):
    """{tag: schlusskurs} -> Kerzenliste, Form [ts, o, h, l, c, vol]."""
    return [[tag * 86400000, k, k, k, k, 1.0] for tag, k in tag_kurs.items()]


WACHEN = {"gebuehr_taker": 0.006}


class TestGebuehrLive(unittest.TestCase):
    def test_gebuehr_pct_liest_wachen_live(self):
        m = kraken_modell.erzeuge(WACHEN, [], [])
        self.assertEqual(m["gebuehr_pct"]("XXBTZEUR", 100), 0.006)

    def test_gebuehr_pct_folgt_wachen_aenderung(self):
        # Keine Kopie zur Erzeugungszeit - dieselbe Referenz wird gelesen.
        w = dict(WACHEN)
        m = kraken_modell.erzeuge(w, [], [])
        w["gebuehr_taker"] = 0.001
        self.assertEqual(m["gebuehr_pct"]("XXBTZEUR", 100), 0.001)


class TestWaehrungsumrechnung(unittest.TestCase):
    def test_eur_paar_bleibt_identitaet(self):
        m = kraken_modell.erzeuge(WACHEN, _fx({100: 1.08}), _fx({100: 1.0}))
        self.assertEqual(m["in_basiswaehrung"](50.0, "XXBTZEUR", 100), 50.0)

    def test_usdc_paar_wird_nach_eur_umgerechnet(self):
        # 1 EUR = 1.08 USD; 54 USDC -> 50 EUR.
        m = kraken_modell.erzeuge(WACHEN, _fx({100: 1.08}), _fx({100: 1.0}))
        self.assertAlmostEqual(
            m["in_basiswaehrung"](54.0, "XBTUSDC", 100), 50.0, places=4)

    def test_eurc_paar_wird_mit_gemessenem_kurs_umgerechnet(self):
        # Kraken-Paarname EURCEUR: Basis EURC, Quote EUR - der Schlusskurs
        # ist "EUR je 1 EURC", also wird MULTIPLIZIERT (umgekehrte Richtung
        # zu EURUSDC, wo die Basis EUR ist). 50 EURC bei Kurs 1,1 -> 55 EUR.
        m = kraken_modell.erzeuge(WACHEN, _fx({100: 1.08}), _fx({100: 1.1}))
        self.assertAlmostEqual(
            m["in_basiswaehrung"](50.0, "XBTEURC", 100), 55.0, places=4)

    def test_fehlender_fx_tag_wirft_statt_eins_zu_eins_anzunehmen(self):
        m = kraken_modell.erzeuge(WACHEN, _fx({100: 1.08}), _fx({100: 1.0}))
        with self.assertRaises(kraken_modell.FXLuecke):
            m["in_basiswaehrung"](54.0, "XBTUSDC", 999)

    def test_laufende_kosten_null_wie_spot(self):
        m = kraken_modell.erzeuge(WACHEN, [], [])
        self.assertEqual(m["laufende_kosten"]({"einstieg_tag": 1}, 5), 0.0)

    def test_pruefe_ausstieg_unveraendert_wie_spot(self):
        import ruecktest
        m = kraken_modell.erzeuge(WACHEN, [], [])
        position = {"stop": 90.0, "ziel": 110.0}
        kerze = [0, 100.0, 95.0, 85.0, 92.0, 1.0]  # tief 85 <= stop 90
        self.assertEqual(m["pruefe_ausstieg"](position, kerze),
                         ruecktest.SPOT_MODELL["pruefe_ausstieg"](position, kerze))


if __name__ == "__main__":
    unittest.main()
