"""Die Backtest-Zeile in der Auswertung.

Sie muss drei Faelle SAUBER trennen: gerechnet, nicht gerechnet und nicht
nachrechenbar. Ein leeres Feld waere von einem Messwert nicht zu unterscheiden.
"""

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import auswertung_alle                                            # noqa: E402

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "stop", "ziel", "stop_pct", "grund"]


def _journal(pfad, runden, ts_start=1700000000000):
    """Ein Journal mit EIN- und AUSSTIEGSZEILEN (nur so paart die Hausfunktion)."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN + ["_kerzen_ts"])
        w.writeheader()
        for i in range(runden):
            ts = ts_start + i * 3600000
            for akt, preis in (("kauf", 100.0), ("verkauf", 105.0)):
                w.writerow({"zeit": "2024-01-01T00:00:00+00:00", "modus": "papier",
                            "aktion": akt, "inst": "BTC-USDC", "seite": "long",
                            "preis": preis, "einsatz_usd": "100.00",
                            "stop": "95.0", "ziel": "110.0", "stop_pct": "5.0",
                            "grund": "backtest", "_kerzen_ts": ts})


def _markenzeile(pfad, preis, grund, stop="95.000000", ziel="110.000000"):
    """Eine Ausstiegszeile an einer echten Marke anhaengen (fuer T-177)."""
    with pfad.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN + ["_kerzen_ts"])
        w.writerow({"zeit": "2024-02-01T00:00:00+00:00", "modus": "papier",
                    "aktion": "verkauf", "inst": "BTC-USDC", "seite": "long",
                    "preis": preis, "einsatz_usd": "100.00", "stop": stop,
                    "ziel": ziel, "stop_pct": "5.0", "grund": grund,
                    "_kerzen_ts": 1700001000000})


class StandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = auswertung_alle.BACKTEST_WURZEL
        auswertung_alle.BACKTEST_WURZEL = Path(self.tmp.name)

    def tearDown(self):
        auswertung_alle.BACKTEST_WURZEL = self.alt
        self.tmp.cleanup()

    def test_nicht_nachrechenbare_spur_nennt_den_grund(self):
        text = auswertung_alle.backtest_stand("moondev_whale")
        self.assertIn("nicht nachrechenbar", text)
        self.assertIn("50030", text)

    def test_kern_spur_nennt_die_fehlende_naht(self):
        self.assertIn("keine Kerzen-Naht", auswertung_alle.backtest_stand("scanner"))

    def test_spur_ohne_lauf_wird_als_kein_lauf_gemeldet(self):
        text = auswertung_alle.backtest_stand("squeeze")
        self.assertIn("kein Lauf", text)
        self.assertIn("replay.py", text)

    def test_gerechneter_lauf_nennt_runden_treffer_und_zeitraum(self):
        _journal(Path(self.tmp.name) / "squeeze" / "ganz" / "handelsjournal.csv", 5)
        text = auswertung_alle.backtest_stand("squeeze")
        self.assertIn("5 Runden", text)
        self.assertIn("%", text)
        self.assertIn("2023-11", text)          # aus den Kerzenstempeln
        self.assertIn("Lauf 'ganz'", text)

    def test_der_lauf_mit_den_meisten_zeilen_gewinnt(self):
        """Nicht der neueste: die Parametersuche schreibt kurze Fensterlaeufe."""
        _journal(Path(self.tmp.name) / "squeeze" / "ganz" / "handelsjournal.csv", 9)
        _journal(Path(self.tmp.name) / "squeeze" / "squeeze_abcd1234"
                 / "handelsjournal.csv", 2)
        neu = Path(self.tmp.name) / "squeeze" / "squeeze_abcd1234" / "handelsjournal.csv"
        os.utime(neu, (2_000_000_000, 2_000_000_000))       # kuenstlich neu
        self.assertIn("Lauf 'ganz'", auswertung_alle.backtest_stand("squeeze"))

    def test_alter_lauf_ohne_kerzenuhr_sagt_das(self):
        pfad = Path(self.tmp.name) / "squeeze" / "alt" / "handelsjournal.csv"
        _journal(pfad, 3)
        with pfad.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SPALTEN)       # ohne _kerzen_ts
            w.writeheader()
            for akt, preis in (("kauf", 100.0), ("verkauf", 105.0)):
                w.writerow({"zeit": "2024-01-01T00:00:00+00:00", "modus": "papier",
                            "aktion": akt, "inst": "BTC-USDC", "seite": "long",
                            "preis": preis, "einsatz_usd": "100.00",
                            "stop": "95.0", "ziel": "110.0", "stop_pct": "5.0",
                            "grund": "backtest"})
        self.assertIn("vor der Kerzenuhr",
                      auswertung_alle.backtest_stand("squeeze"))

    def test_gleichstand_geht_an_den_lauf_mit_kerzenuhr(self):
        """Bei GLEICHER Zeilenzahl darf kein alter Lauf den datierten verdecken.

        Am 2026-09-26 lagen zwei Laeufe mit je 2180 Zeilen nebeneinander: der
        alte ohne Kerzenuhr (Name 'ganz') und der neu gefahrene datierte
        (Name 'ganz.…'). Entschieden hat der NAME - und der alte gewann. Die
        Zeile sagte 'Zeitraum unbekannt', obwohl ein datierter Lauf daneben lag.

        Der datierte Lauf heisst hier ABSICHTLICH alphabetisch kleiner: ohne
        die Regel gewaenne der Name, nicht die Kerzenuhr.
        """
        alt = Path(self.tmp.name) / "squeeze" / "z_alt" / "handelsjournal.csv"
        neu = Path(self.tmp.name) / "squeeze" / "a_dat" / "handelsjournal.csv"
        _journal(alt, 3)
        _journal(neu, 3)
        with alt.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SPALTEN)
            w.writeheader()
            for _ in range(3):
                for akt, preis in (("kauf", 100.0), ("verkauf", 105.0)):
                    w.writerow({"zeit": "2024-01-01T00:00:00+00:00", "modus": "papier",
                                "aktion": akt, "inst": "BTC-USDC", "seite": "long",
                                "preis": preis, "einsatz_usd": "100.00",
                                "stop": "95.0", "ziel": "110.0", "stop_pct": "5.0",
                                "grund": "backtest"})
        text = auswertung_alle.backtest_stand("squeeze")
        self.assertIn("Lauf 'a_dat'", text)
        self.assertIn("2023-11", text)
        self.assertNotIn("vor der Kerzenuhr", text)


    def test_markenzeilen_werden_gezaehlt(self):
        """Die Beruehrungsregel (T-177) ist an jeder Zeile ablesbar."""
        _journal(Path(self.tmp.name) / "squeeze" / "neu"
                 / "handelsjournal.csv", 4)
        pfad = Path(self.tmp.name) / "squeeze" / "neu" / "handelsjournal.csv"
        _markenzeile(pfad, "95.000000", "stop")
        text = auswertung_alle.backtest_stand("squeeze")
        # Gezaehlt werden die Stop-/Ziel-Ausstiege: der eine hier sitzt auf
        # seiner Marke. Die vier Zeilen mit grund 'backtest' sind keine
        # Markenausstiege und gehen nicht in den Nenner.
        self.assertIn("Ausstiege auf der Marke 1/1", text)

    def test_lauf_vor_der_regel_zeigt_die_null(self):
        """Ohne die Regel steht der Kerzenschluss im Journal: 0 auf der Marke."""
        _journal(Path(self.tmp.name) / "squeeze" / "alt2"
                 / "handelsjournal.csv", 3)
        pfad = Path(self.tmp.name) / "squeeze" / "alt2" / "handelsjournal.csv"
        _markenzeile(pfad, "104.000000", "ziel")      # Schluss, nicht Marke
        self.assertIn("Ausstiege auf der Marke 0/1",
                      auswertung_alle.backtest_stand("squeeze"))


    def test_gleichstand_geht_an_den_lauf_mit_der_regel(self):
        """Bei GLEICHER Zeilenzahl gewinnt der Lauf AUF DER MARKE.

        Zwei Laeufe, gleich viele Zeilen, gleiche Kerzenuhr: der eine schreibt
        den Kerzenschluss (alte Rechnung, Name 'vor177'), der andere die Marke
        (Beruehrungsregel, Name 'nach177'). 'vor177' steht alphabetisch HINTER
        'nach177' - ohne diese Regel zeigte die Auswertung also genau den Lauf
        ohne die Beruehrungsregel, waehrend daneben der berichtigte lag.
        """
        vor = Path(self.tmp.name) / "squeeze" / "vor177" / "handelsjournal.csv"
        nach = Path(self.tmp.name) / "squeeze" / "nach177" / "handelsjournal.csv"
        _journal(vor, 3)
        _journal(nach, 3)
        _markenzeile(vor, "104.000000", "ziel")         # Schluss, neben der Marke
        _markenzeile(nach, "110.000000", "ziel")        # genau auf der Marke
        text = auswertung_alle.backtest_stand("squeeze")
        self.assertIn("Lauf 'nach177'", text)
        self.assertIn("Ausstiege auf der Marke 1/1", text)


if __name__ == "__main__":
    unittest.main()
