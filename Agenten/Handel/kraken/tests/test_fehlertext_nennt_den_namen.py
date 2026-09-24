"""Eine Zugangs-Fehlermeldung nennt die Variable, die der Code AUCH liest.

Befund 25.09.2026 (Einzahlungs-Sitzung): `kraken._roh_privat` liest
`KRAKEN_SPOT_API_KEY`/`KRAKEN_SPOT_API_SECRET`, warf aber

    RuntimeError: KRAKEN_API_KEY / KRAKEN_API_SECRET fehlen

Beide Paare existieren in HKCU\\Environment, aber nur das SPOT-Paar oeffnet den
Spot-Host (das generische Paar antwortet `EAPI:Invalid key`). Wer der Meldung
folgt und das genannte Paar setzt, aendert nichts; wer es prueft, findet es vor
und sucht den Fehler beim Schluessel statt beim Namen. Dieselbe Falle wie beim
Kraken-Futures-Namen (Einzahl `KRAKEN_FUTURE_API_KEY` hier, Mehrzahl
`KRAKEN_FUTURES_API_KEY` in der offiziellen kraken-cli).

Kein Netz: `_variable` wird ersetzt, es wird kein Aufruf gesendet.
Direkt ausfuehrbar:
    python tests/test_fehlertext_nennt_den_namen.py
"""

import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))           # kraken/

import kraken as k                             # noqa: E402


class FehlertextNenntDenNamenTest(unittest.TestCase):

    def setUp(self):
        self.orig_variable = k._variable
        self.orig_urlopen = k.urllib.request.urlopen
        k._variable = lambda name: None        # nichts gesetzt
        k.urllib.request.urlopen = self._kein_netz

    def tearDown(self):
        k._variable = self.orig_variable
        k.urllib.request.urlopen = self.orig_urlopen

    @staticmethod
    def _kein_netz(*a, **kw):
        raise AssertionError("Es darf kein Netzaufruf entstehen, wenn der Schluessel fehlt")

    def test_meldung_nennt_das_spot_paar(self):
        with self.assertRaises(RuntimeError) as ctx:
            k._roh_privat("Balance")
        text = str(ctx.exception)
        self.assertIn("KRAKEN_SPOT_API_KEY", text)
        self.assertIn("KRAKEN_SPOT_API_SECRET", text)

    def test_meldung_nennt_nicht_das_generische_paar(self):
        """Das generische Paar ist ein ANDERER Zugang - es darf nicht genannt werden."""
        with self.assertRaises(RuntimeError) as ctx:
            k._roh_privat("Balance")
        text = str(ctx.exception)
        self.assertNotIn("KRAKEN_API_KEY", text)
        self.assertNotIn("KRAKEN_API_SECRET", text)

    def test_quelle_liest_und_nennt_dasselbe(self):
        """Quelltext-Gegenprobe: gelesene und genannte Namen stimmen ueberein."""
        quelle = (HIER.parent / "kraken.py").read_text(encoding="utf-8")
        block = quelle.split("def _roh_privat")[1].split("\n\n")[0]
        for name in ("KRAKEN_SPOT_API_KEY", "KRAKEN_SPOT_API_SECRET"):
            self.assertIn('_variable("%s")' % name, block)
            self.assertIn(name, block.split("RuntimeError")[1])
        self.assertNotIn('_variable("KRAKEN_API_KEY")', block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
