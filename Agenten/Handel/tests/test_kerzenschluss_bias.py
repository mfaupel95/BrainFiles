"""Tests fuer kerzenschluss_bias - Regeln statt Tageswerte, ohne Netz.

Die Naht ist `kb.WURZEL` (der Backtest-Ordner). Ein Modulwaechter stellt sicher,
dass kein Test in einen echten Ordner schreibt.

Der Kern der Messung: jede Austrittszeile traegt ihre Marke SELBST, es wird also
je ZEILE gemessen und nicht ueber die Paarung (die ohne `pos_id` danebengreift).
Geprueft werden beide Seiten und beide Richtungen (long/short).
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import kerzenschluss_bias as kb                                   # noqa: E402

KOPF = ("zeit,modus,aktion,inst,seite,preis,einsatz_usd,stop,ziel,stop_pct,"
        "grund\n")


def zeile(inst, seite, preis, grund, stop=92.0, ziel=110.0):
    return ("2021-01-02T00:00:00+00:00,papier,verkauf,%s,%s,%.4f,62.50,%.4f,"
            "%.4f,8.00,%s\n" % (inst, seite, preis, stop, ziel, grund))


def schreibe(pfad, zeilen):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        f.write(KOPF)
        f.writelines(zeilen)


class MessungTest(unittest.TestCase):
    """Sechs Austritte mit bekanntem Ausgang, beide Richtungen."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="kerzenschluss_")
        cls.alt = kb.WURZEL
        kb.WURZEL = Path(cls.tmp)
        cls.pfad = Path(cls.tmp) / "spur" / "ganz" / "handelsjournal.csv"
        schreibe(str(cls.pfad), [
            zeile("BTC", "long", 85.0, "stop"),      # 7.61 unter dem Stop
            zeile("ETH", "long", 130.0, "ziel"),     # 18.18 ueber dem Ziel
            zeile("SOL", "short", 115.0, "stop", stop=108.0, ziel=90.0),
            zeile("ADA", "short", 80.0, "ziel", stop=108.0, ziel=90.0),
            zeile("DOT", "long", 110.0, "ziel"),     # genau auf dem Ziel
            zeile("LTC", "long", 99.0, "frist"),     # keine Marke -> zaehlt nicht
            "2021-01-02T00:00:00+00:00,papier,verkauf,XRP,,120.0000,62.50,"
            "92.0000,110.0000,8.00,stop\n",          # ohne Seite
        ])

    @classmethod
    def tearDownClass(cls):
        kb.WURZEL = cls.alt
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_beide_seiten_beider_richtungen(self):
        z = kb.messen(self.pfad)
        # long-Stop 7.6087 + short-Stop 6.4815
        self.assertAlmostEqual(14.0902, z["zuviel_verlust"], delta=0.01)
        # long-Ziel 18.1818 + short-Ziel 11.1111 (genau am Ziel zaehlt nicht)
        self.assertAlmostEqual(29.2929, z["zuviel_gewinn"], delta=0.01)
        self.assertAlmostEqual(15.2027, z["netto"], delta=0.01)
        self.assertEqual(2, z["stop_ausstiege"])
        self.assertEqual(3, z["ziel_ausstiege"])
        self.assertEqual(1, z["auf_der_marke"])
        self.assertEqual(1, z["ohne_seite"])
        self.assertEqual(6, z["ausstiege"])
        self.assertEqual(4, z["betroffen"])

    def test_ein_ausstieg_auf_der_marke_zaehlt_nicht_als_betroffen(self):
        pfad = Path(self.tmp) / "genau" / "ganz" / "handelsjournal.csv"
        schreibe(str(pfad), [zeile("DOT", "long", 110.0, "ziel")])
        z = kb.messen(pfad)
        self.assertEqual(1, z["auf_der_marke"])
        self.assertEqual(0, z["betroffen"])
        self.assertAlmostEqual(0.0, z["netto"], delta=1e-9)

    def test_frist_und_leere_zeilen_zaehlen_nicht(self):
        pfad = Path(self.tmp) / "nur_frist" / "ganz" / "handelsjournal.csv"
        schreibe(str(pfad), [zeile("LTC", "long", 99.0, "frist")])
        self.assertIsNone(kb.messen(pfad),
                          "ohne Marken-Austritt gibt es nichts zu messen")

    def test_leeres_journal_gibt_none(self):
        pfad = Path(self.tmp) / "leer" / "ganz" / "handelsjournal.csv"
        schreibe(str(pfad), [])
        self.assertIsNone(kb.messen(pfad))

    def test_journale_nimmt_das_groesste_je_ordner(self):
        ordner = os.path.join(self.tmp, "zwei", "ganz")
        schreibe(os.path.join(ordner, "handelsjournal.csv"),
                 [zeile("BTC", "long", 85.0, "stop")])
        andere = Path(self.tmp) / "zwei" / "ganz" / "fenster2.csv"
        schreibe(str(andere), [zeile("BTC", "long", 85.0, "stop"),
                               zeile("ETH", "long", 130.0, "ziel")])
        gefunden = [p for p in kb.journale() if "zwei" in str(p)]
        self.assertEqual(1, len(gefunden))
        self.assertEqual("fenster2.csv", gefunden[0].name)


class WaechterTest(unittest.TestCase):
    """Der Werkzeugordner darf sich waehrend der Tests nicht aendern."""

    def test_kein_schreiben_in_echte_ordner(self):
        ordner = [os.path.join(HANDEL, "daten", "backtest"), HANDEL]
        vorher = {o: sorted(os.listdir(o)) for o in ordner if os.path.isdir(o)}
        kb.messen(Path(HANDEL) / "daten" / "backtest" / "gibtsnicht" /
                  "handelsjournal.csv")
        for o, liste in vorher.items():
            self.assertEqual(liste, sorted(os.listdir(o)),
                             "Test hat in %s geschrieben" % o)


if __name__ == "__main__":
    unittest.main()