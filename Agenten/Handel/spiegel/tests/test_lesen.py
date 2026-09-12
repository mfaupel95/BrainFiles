"""Tests fuer lesen.py - ohne Netz, ohne CLI-Aufruf, ohne Schreibbefehl.

Der Schreibschutz ist der wichtigste Test dieser Datei: Die Spiegel-Spur ist
papierfest, und durchgesetzt wird das hier - nicht durch guten Willen im
Aufrufer. Ein Test, der eine echte Order erreichen koennte, waere der Fehler.

Aufruf:  python -m unittest discover -s tests   (im Ordner spiegel/)
"""

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.abspath(__file__))
SPIEGEL = os.path.dirname(HIER)
if SPIEGEL not in sys.path:
    sys.path.insert(0, SPIEGEL)

import lesen                                                  # noqa: E402


def antwort(daten, ok=True):
    """Eine CLI-Antwort, wie subprocess sie liefern wuerde."""
    import json
    return subprocess.CompletedProcess(
        [], 0, json.dumps({"ok": ok, "data": daten, "error": None if ok else daten}),
        "")


class Schreibschutz(unittest.TestCase):

    def test_jeder_schreibbefehl_wird_verweigert(self):
        for befehl in lesen.SCHREIBBEFEHLE:
            with self.assertRaises(lesen.Schreibversuch, msg=befehl):
                lesen.ruf([befehl, "irgendwas"])

    def test_der_schutz_greift_vor_dem_prozessstart(self):
        with patch("subprocess.run",
                   side_effect=AssertionError("Prozess darf nicht starten")):
            with self.assertRaises(lesen.Schreibversuch):
                lesen.ruf(["swap", "execute", "--chain", "solana"])

    def test_leerer_aufruf_ist_ein_lesefehler(self):
        with self.assertRaises(lesen.Lesefehler):
            lesen.ruf([])


class Fehlerbehandlung(unittest.TestCase):

    def test_cli_fehler_wird_zum_lesefehler(self):
        with patch("subprocess.run", return_value=antwort("kaputt", ok=False)):
            with self.assertRaises(lesen.Lesefehler):
                lesen.leaderboard("solana")

    def test_keine_json_antwort_wird_zum_lesefehler(self):
        with patch("subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, "<html>", "")):
            with self.assertRaises(lesen.Lesefehler):
                lesen.leaderboard("solana")

    def test_fehlendes_cli_wird_zum_lesefehler(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("weg")):
            with self.assertRaises(lesen.Lesefehler):
                lesen.leaderboard("solana")


class Normalisierung(unittest.TestCase):

    ROH = [
        {"chainIndex": "501", "walletAddress": "W1", "tokenContractAddress": "T1",
         "tokenSymbol": "AAA", "tokenPrice": "0.0000015", "marketCap": "250000",
         "tradeTime": "1789244400000", "quoteTokenSymbol": "SOLANA",
         "txHash": "TX1"},
        {"chainIndex": "501", "walletAddress": "W2", "tokenContractAddress": "T2",
         "tokenSymbol": "BBB", "tokenPrice": "0", "marketCap": "900",
         "tradeTime": "1789244400000", "txHash": "TX2"},
    ]

    def test_signale_haben_zahlen_und_adressen(self):
        with patch.object(lesen, "tracker", return_value=self.ROH):
            sig = lesen.signale("solana")
        self.assertEqual(len(sig), 1, "ein Preis von 0 ist kein Signal")
        s = sig[0]
        self.assertEqual(s["token"], "T1")
        self.assertEqual(s["wallet"], "W1")
        self.assertAlmostEqual(s["preis"], 0.0000015)
        self.assertAlmostEqual(s["marktkap_usd"], 250000.0)
        self.assertEqual(s["kette"], "solana")
        self.assertIsNotNone(s["alter_s"])

    def test_preise_baut_die_stapelabfrage_richtig(self):
        gesehen = {}

        def merke(args, timeout=None):
            gesehen["args"] = [str(a) for a in args]
            return [{"chainIndex": "501", "tokenContractAddress": "T1",
                     "price": "0.5"},
                    {"chainIndex": "8453", "tokenContractAddress": "0xAB",
                     "price": "2"}]

        with patch.object(lesen, "ruf", side_effect=merke):
            aus = lesen.preise([("solana", "T1"), ("base", "0xAB")])
        self.assertEqual(gesehen["args"][0], "market")
        self.assertEqual(gesehen["args"][1], "prices")
        self.assertEqual(gesehen["args"][3], "501:T1,8453:0xAB")
        self.assertAlmostEqual(aus[("solana", "T1")], 0.5)
        self.assertAlmostEqual(aus[("base", "0xAB")], 2.0)

    def test_index_kennt_name_index_und_vorgabe(self):
        self.assertEqual(lesen._index("solana"), "501")
        self.assertEqual(lesen._index("501"), "501")
        self.assertEqual(lesen._index(None, "base"), "8453")

    def test_risiko_gibt_stufe_und_merkmale(self):
        roh = {"combinedAction": "safe",
               "tokens": [{"action": "safe", "isHoneypot": False,
                           "isMintable": True}]}
        with patch.object(lesen, "ruf", return_value=roh):
            r = lesen.risiko("T1", "solana")
        self.assertEqual(r["stufe"], "safe")
        self.assertEqual(r["merkmale"], ["isMintable"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
