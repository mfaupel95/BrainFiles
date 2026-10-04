"""Tests der Eingangsfilter-Studie - auf kuenstlichen Journalen.

Kein Test schreibt in einen echten Spurenordner: die Journale liegen im
Tempverzeichnis, und ein Waechter vergleicht am Ende Dateiliste und Groessen
der drei Spurenordner (Hausmuster).
"""

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
SPUREN = ("spiegel", "kopier")
if str(HANDEL) not in sys.path:
    sys.path.insert(0, str(HANDEL))

import filter_studie as fs   # noqa: E402

STAND = {}


def _stand(spur):
    d = HANDEL / spur
    if not d.exists():
        return []
    return sorted((p.name, p.stat().st_size) for p in d.glob("*"))


def setUpModule():
    for spur in SPUREN:
        STAND[spur] = _stand(spur)


def tearDownModule():
    for spur in SPUREN:
        if _stand(spur) != STAND[spur]:
            raise AssertionError("Test hat in %s/ geschrieben!" % spur)


KOPF = ["zeit", "modus", "aktion", "kette", "wallet", "token", "symbol",
        "preis", "menge", "einsatz_usd", "wert_usd", "marktkap_usd",
        "slippage_pct", "gebuehr_pct", "grund"]


def journal_schreiben(pfad, posten, kette="solana"):
    """Journal aus (zeit, marktkap, einsatz, wert)-Posten schreiben."""
    with open(pfad, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(KOPF)
        for i, (zeit, mk, einsatz, wert) in enumerate(posten):
            token = "T%03d" % i
            w.writerow([zeit, "papier", "eroeffnen", kette, "W1", token, "SYM",
                        "0.001", "1000", "%.2f" % einsatz, "", "%d" % mk,
                        "3.0", "1.0", "kopie"])
            w.writerow([zeit, "papier", "schliessen", kette, "W1", token, "SYM",
                        "0.001", "1000", "%.2f" % einsatz, "%.2f" % wert, "",
                        "3.0", "1.0", "trail"])


def posten_aus(mk_gewinn, mk_verlust, je_haelfte=20, kette="solana"):
    """Posten mit klarem Ausgang: ein Band gewinnt, das andere verliert.

    Die Haelfte der Posten liegt zeitlich frueh, die andere spaet - so sind
    beide Zeithaelfte besetzt (die Studie sortiert nach `zeit`).
    """
    posten = []
    for i in range(je_haelfte):
        zeit_alt = "2026-09-1%dT00:00:00+00:00" % (i % 4 + 1)
        zeit_jung = "2026-09-1%dT00:00:00+00:00" % (i % 4 + 5)
        posten.append((zeit_alt, mk_gewinn, 50.0, 60.0))
        posten.append((zeit_jung, mk_gewinn, 50.0, 60.0))
        posten.append((zeit_alt, mk_verlust, 50.0, 40.0))
        posten.append((zeit_jung, mk_verlust, 50.0, 40.0))
    return posten


def aus_bauen(posten):
    """Dieselben Posten als Ausstiegs-Dicts (wie lade_ausstiege sie liefert)."""
    aus = []
    for i, (zeit, mk, einsatz, wert) in enumerate(posten):
        aus.append({"zeit": zeit, "name": "T%03d" % i, "grund": "trail",
                    "einsatz": einsatz, "wert": wert,
                    "netto_pct": (wert / einsatz - 1.0) * 100.0,
                    "marktkap_usd": float(mk), "kette": "solana",
                    "kosten": (1.0, 1.0)})
    return aus


class HalbierungTest(unittest.TestCase):
    def test_halbierung_60_40_nach_zeit(self):
        aus = [{"zeit": "2026-09-1%dT00:00:00+00:00" % i} for i in range(1, 6)]
        alt, jung = fs.zeit_halbieren(aus)
        self.assertEqual(len(alt), 3)
        self.assertEqual(len(jung), 2)
        self.assertEqual(alt[0]["zeit"], "2026-09-11T00:00:00+00:00")
        self.assertEqual(jung[-1]["zeit"], "2026-09-15T00:00:00+00:00")

    def test_masse_liefert_beide_kostenblicke(self):
        aus = aus_bauen([("2026-09-11T00:00:00+00:00", 500000, 50.0, 100.0),
                         ("2026-09-12T00:00:00+00:00", 500000, 50.0, 25.0)])
        m = fs.masse(aus, 1.0)
        self.assertEqual(m["n"], 2)
        self.assertAlmostEqual(m["netto"], 25.0, places=6)
        self.assertAlmostEqual(m["quote"], 50.0, places=6)


class LadenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="studie_")
        self.journal = os.path.join(self.tmp, "handelsjournal.csv")
        journal_schreiben(self.journal, posten_aus(500_000, 100_000))

    def test_lade_spur_liest_das_journal_der_spur(self):
        aus, kosten = fs.lade_spur("spiegel", journal=self.journal)
        self.assertEqual(len(aus), 80)
        self.assertEqual(aus[0]["kette"], "solana")
        self.assertIsNotNone(kosten)

    def test_unbekannte_spur_wirft(self):
        with self.assertRaises(ValueError):
            fs.lade_spur("gibtsnicht")


class VerdiktTest(unittest.TestCase):
    def test_traegt_wenn_beide_haelften_positiv_und_besetzt(self):
        aus = aus_bauen(posten_aus(500_000, 100_000, je_haelfte=60))
        r = {x["regel"]: x for x in fs.studie_aus(aus, 1.0)}
        self.assertEqual(r["untergrenze 250k"]["verdikt"], "traegt")
        self.assertGreaterEqual(r["untergrenze 250k"]["alt"]["n"], 30)
        self.assertGreaterEqual(r["untergrenze 250k"]["jung"]["n"], 30)

    def test_gegenrichtung_kippt_das_verdikt(self):
        """Gegenprobe: dasselbe Band, umgekehrter Ausgang -> verworfen."""
        aus = aus_bauen(posten_aus(100_000, 500_000, je_haelfte=60))
        r = {x["regel"]: x for x in fs.studie_aus(aus, 1.0)}
        self.assertEqual(r["untergrenze 250k"]["verdikt"], "verworfen")

    def test_nicht_entschieden_bei_zu_kleiner_gruppe(self):
        aus = aus_bauen(posten_aus(500_000, 100_000, je_haelfte=3))
        r = fs.studie_aus(aus, 1.0)
        self.assertTrue(all(x["verdikt"] == "nicht entschieden" for x in r))


class BerichtTest(unittest.TestCase):
    def test_bericht_nennt_jede_regel_und_ihr_verdikt(self):
        e = {"spiegel": {"spur": "spiegel", "n": 4, "ganz": {"netto": 1.0,
                                                            "brutto": 2.0},
                         "regeln": [{"regel": "untergrenze 250k",
                                     "verdikt": "traegt", "grund": "x",
                                     "ganz": {"n": 4, "netto": 1.0},
                                     "alt": {"n": 2, "netto": 1.0},
                                     "jung": {"n": 2, "netto": 1.0}}]}}
        zeilen = "\n".join(fs.bericht(e))
        self.assertIn("untergrenze 250k", zeilen)
        self.assertIn("traegt", zeilen)

    def test_fehler_wird_gemeldet_statt_verschluckt(self):
        zeilen = "\n".join(fs.bericht({"spiegel": {"spur": "spiegel", "n": 0,
                                                   "regeln": [],
                                                   "fehler": "ValueError: x"}}))
        self.assertIn("FEHLER", zeilen)


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="studie_")
        self.journal = os.path.join(self.tmp, "handelsjournal.csv")
        journal_schreiben(self.journal, posten_aus(500_000, 100_000))
        self.ziel = HANDEL / "filter_studie_ergebnis.json"

    def test_main_ohne_json_schreibt_nichts(self):
        vorher = self.ziel.exists()
        rc = fs.main(["--spur", "spiegel", "--journal", self.journal])
        self.assertEqual(rc, 0)
        self.assertEqual(self.ziel.exists(), vorher)

    def test_main_ohne_journal_liest_die_echte_spur(self):
        """Die echten Journale sind lesbar - Anzahl kommt aus der Spur."""
        rc = fs.main(["--spur", "spiegel"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
