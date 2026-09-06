import csv
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCANNER = Path(__file__).resolve().parents[2] / "scanner"
sys.path.insert(0, str(SCANNER))
import handeln  # noqa: E402


class TestGebuehr(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        p = Path(self.tmp.name)
        handeln.JOURNAL = p / "handelsjournal.csv"
        handeln.ZUSTAND = p / "zustand.json"
        # Kurs bleibt konstant -> ohne Gebuehr waere die Runde +-0
        handeln.okx.letzter_kurs = lambda inst: 100.0

    def tearDown(self):
        self.tmp.cleanup()

    # Betraege so gewaehlt, dass beide Gebuehren volle Cent ergeben
    # (200 * 0,05 % = 0,10 ; 260 * 0,05 % = 0,13). Das Journal schreibt
    # "%.2f" - bei krummen Halb-Cent-Betraegen verwischt diese Rundung den
    # Nachweis, nicht die Gebuehr selbst.
    EINSATZ = 200.0
    EINSTIEG = 100.0
    ZIEL_KURS = 130.0

    def _runde_gv(self):
        z = {"positionen": [], "letzte_stops": {}, "letzter_lauf": None}
        v = {"inst": "BTC-USDT", "score": 70.0, "einstieg": self.EINSTIEG,
             "stop": 90.0, "stop_pct": 10.0, "ziel": self.ZIEL_KURS,
             "usd": self.EINSATZ}
        handeln.pruefe_einstiege(z, [v], handeln.scan.wachen(), live=False)
        # Ziel treffen
        handeln.okx.letzter_kurs = lambda inst: self.ZIEL_KURS
        handeln.pruefe_ausstiege(z, live=False)
        runden = []
        offen = {}
        with handeln.JOURNAL.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["aktion"] == "kauf":
                    offen[r["inst"]] = float(r["usd"])
                else:
                    runden.append(float(r["usd"]) - offen[r["inst"]])
        return runden[0]

    def test_runde_traegt_zwei_gebuehren(self):
        roh_erloes = self.EINSATZ * (self.ZIEL_KURS / self.EINSTIEG)
        gv_ohne_gebuehr = roh_erloes - self.EINSATZ  # = 60.0
        gv = self._runde_gv()
        # Kauf traegt eine Gebuehr auf den Einsatz, Verkauf eine auf den
        # Roh-Erloes - genau zwei, nicht eine, nicht null.
        erwartete_gebuehr = (self.EINSATZ * handeln.GEBUEHR_PCT
                             + roh_erloes * handeln.GEBUEHR_PCT)
        self.assertAlmostEqual(gv, gv_ohne_gebuehr - erwartete_gebuehr, 4)


if __name__ == "__main__":
    unittest.main()
