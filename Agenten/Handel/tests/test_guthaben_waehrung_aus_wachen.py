"""Die Waehrung des Scanners kommt aus seiner Wachen, nicht aus dem Skript.

Anlass (T-311, 02.10.2026): das OKX-Konto (EEA) traegt 438 USDC und
0,00 USDT. Zwei Stellen lasen trotzdem USDT fest:

* `tagesbericht.guthaben_zeile()` iterierte ueber ('USDT', 'USDC') und
  nutzte bei leerer `details`-Liste `totalEq` als Rueckfall. `totalEq` ist
  die Summe ueber ALLE Waehrungen - der Bericht zeigte deshalb
  "USDT 838.81", eine Zahl fuer eine Waehrung, die es nicht gibt. Genau
  das liest sich als "USDT fehlt" bzw. als ein Buch, das nicht passt.
* `guthaben_abgleich._konto_fn('scanner')` rief `okx.guthaben_usdt()` und
  bekam 0.0; der Wochenbericht wies daraus eine Differenz aus.

Beide lesen jetzt `universum.quotes` aus `scanner/wachen.json` - dieselbe
Quelle wie das Guthaben-Tor in `handeln.py`. Ein Rueckfall auf `totalEq`
existiert nicht mehr: liefert die Boerse fuer eine Waehrung kein
`details`, ist das eine Waehrung OHNE Bestand (0.00), kein Gesamtstand.

Die Gegenprobe steckt in jedem Test: mit der alten festen Liste bzw. dem
alten `guthaben_usdt()` muss er rot werden.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(HANDEL, "scanner")
for _p in (SCAN, HANDEL):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _pfad(name):
    s = importlib.util.spec_from_file_location(
        "handel_" + name.replace(".py", ""), os.path.join(HANDEL, name))
    m = importlib.util.module_from_spec(s)
    sys.modules[s.name] = m
    s.loader.exec_module(m)
    return m


okx = _pfad(os.path.join("scanner", "okx.py"))


class WachenQuelleTest(unittest.TestCase):
    """Der Tagesbericht nennt die Waehrungen der Wachen."""

    def setUp(self):
        self.tb = _pfad("tagesbericht.py")

    def _mit_antwort(self, details):
        """Die Boersenantwort je Waehrung: USDT leer, USDC mit Bestand."""
        def fake(pfad, signiert=False):
            ccy = pfad.split("ccy=")[-1]
            if details.get(ccy) is None:
                return [{"details": [], "totalEq": "838.81"}]
            return [{"details": [{"availBal": str(details[ccy])},
                                 {"availBal": "1.50"}],
                     "totalEq": "838.81"}]
        return fake

    def _zeile(self, details):
        alt = okx._mit_wiederholung
        okx._mit_wiederholung = self._mit_antwort(details)
        sys.modules["okx"] = okx
        try:
            return self.tb.guthaben_zeile()
        finally:
            okx._mit_wiederholung = alt

    def test_nennt_die_quote_der_wachen_und_nicht_usdt(self):
        z = self._zeile({"USDC": 38.23})
        self.assertIn("USDC 39.73", z)      # 38.23 + 1.50, beide details
        self.assertNotIn("USDT", z)

    def test_kein_rueckfall_auf_totaleq(self):
        # GENAU der Fehler: USDT hat kein details, totalEq traf trotzdem ein.
        z = self._zeile({"USDC": 38.23})
        self.assertNotIn("838.81", z)

    def test_eine_waehrung_ohne_bestand_wird_als_solche_gemeldet(self):
        # Zwei Quotes in der Wachen: eine mit Bestand, eine ohne. Die ohne
        # liefert KEIN details zurueck - das ist der Fall, der vorher still
        # auf totalEq geriet und "USDT 838.81" erfand.
        tmp = tempfile.mkdtemp(prefix="wachen2q_")
        alt_hier = self.tb.HIER
        alt_q = self.tb.guthaben_zeile
        try:
            (Path(tmp) / "scanner").mkdir()
            with open(Path(tmp) / "scanner" / "wachen.json", "w",
                      encoding="utf-8") as f:
                json.dump({"budget_usd": 600,
                           "universum": {"quotes": ["USDC", "USDT"]}}, f)
            self.tb.HIER = tmp
            z = self._zeile({"USDC": 10.0})
        finally:
            self.tb.HIER = alt_hier
            del alt_q
        self.assertIn("USDT 0.00 (kein Bestand)", z)
        self.assertNotIn("838.81", z)

    def test_antwort_ausgefallen_nennt_den_grund(self):
        def kaputt(pfad, signiert=False):
            raise RuntimeError("Zeitueberschreitung")
        alt = okx._mit_wiederholung
        okx._mit_wiederholung = kaputt
        sys.modules["okx"] = okx
        try:
            z = self.tb.guthaben_zeile()
        finally:
            okx._mit_wiederholung = alt
        self.assertIn("n/A", z)
        self.assertIn("Zeitueberschreitung", z)


class AbgleichWaehrungTest(unittest.TestCase):
    """Der Wochenbericht fragt die Quote, in der der Scanner handelt."""

    def setUp(self):
        self.ga = _pfad("guthaben_abgleich.py")

    def test_quote_steht_in_der_wachen(self):
        with open(os.path.join(SCAN, "wachen.json"), encoding="utf-8") as f:
            wachen = json.load(f)
        erwartet = wachen["universum"]["quotes"][0]
        self.assertEqual(self.ga._scanner_quote(), erwartet)
        self.assertNotEqual(self.ga._scanner_quote(), "USDT")

    def test_der_abgleich_fragt_nicht_usdt(self):
        gerufen = []

        def fake(ccy="USDC"):
            gerufen.append(ccy)
            return 38.23
        alt = okx.guthaben
        okx.guthaben = fake
        sys.modules["okx"] = okx
        try:
            wert = self.ga._konto_fn("scanner")()
        finally:
            okx.guthaben = alt
        self.assertEqual(gerufen, ["USDC"])
        self.assertAlmostEqual(wert, 38.23)

    def test_rueckfall_ohne_wachenfeld_ist_usdc(self):
        tmp = tempfile.mkdtemp(prefix="wachenleer_")
        alt = self.ga.HIER
        try:
            (Path(tmp) / "scanner").mkdir()
            with open(Path(tmp) / "scanner" / "wachen.json", "w",
                      encoding="utf-8") as f:
                json.dump({"budget_usd": 600}, f)
            self.ga.HIER = tmp
            self.assertEqual(self.ga._scanner_quote(), "USDC")
        finally:
            self.ga.HIER = alt


if __name__ == "__main__":
    unittest.main()