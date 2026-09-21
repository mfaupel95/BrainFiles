"""Stille Spuren im Bericht: gezaehlt, benannt und mit Alter.

Auftrag Max 21.09.2026: die stillen Spuren (Omniquant, iv_waelle, iv_wand,
nautilus, nautilus_kraken, orbk, supertrend ...) gehoeren in den Bericht. Vorher
stand dort nur EINE Zeile mit acht Namen - sie sagt nicht, welche Spur seit
einer Stunde und welche seit drei Wochen nichts tut.

Zwei Fallen, die dieser Test festhaelt:
  1. Nicht jede Journalzeile ist ein Handel. Die Nautilus-Arme schreiben im
     Takt `zyklus`-Zeilen mit Bid/Ask; wer nur die letzte Zeile liest, haelt
     die Spur fuer beschaftigt, obwohl sie nicht handelt.
  2. Die beiden Kraken-Arme teilen sich den `schluessel` "nautilus_kraken" -
     in der Namenszeile standen sie deshalb zweimal identisch da.

Direkt ausfuehrbar:  python tests/test_stille_spuren.py
"""

import csv
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import tagesbericht as tb                                        # noqa: E402


def _journal(zeilen):
    tmp = Path(tempfile.mkdtemp()) / "handelsjournal.csv"
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["zeit", "modus", "aktion", "inst", "grund"])
        for z in zeilen:
            w.writerow(z)
    return tmp


def _zeit(tage_zurueck):
    return (dt.datetime.now(dt.timezone.utc)
            - dt.timedelta(days=tage_zurueck)).isoformat(timespec="seconds")


class LetzteBuchungTest(unittest.TestCase):

    def test_zyklus_zeilen_sind_keine_buchungen(self):
        # Der Fehler, den die Quote-Sammler ausgeloest haetten: heute eine
        # "zyklus"-Zeile, aber seit Wochen kein Handel.
        j = _journal([[_zeit(30), "papier", "kauf", "BTC/EUR", "x"],
                      [_zeit(0), "papier", "zyklus", "BTC/EUR", "quotes"]])
        tage_b, n_b, tage_z, n_z = tb.letzte_buchung(j)
        self.assertEqual(n_b, 1)
        self.assertEqual(n_z, 2)
        self.assertGreaterEqual(tage_b, 29)
        self.assertEqual(tage_z, 0)

    def test_nur_kurse_heisst_kein_handel(self):
        j = _journal([[_zeit(0), "papier", "zyklus", "PF_XBTUSD", "quotes"],
                      [_zeit(0), "papier", "quotes", "PF_XBTUSD", "quotes"]])
        tage_b, n_b, _, n_z = tb.letzte_buchung(j)
        self.assertIsNone(tage_b)
        self.assertEqual(n_b, 0)
        self.assertEqual(n_z, 2)

    def test_fehlende_datei_ist_kein_fehler(self):
        self.assertEqual(tb.letzte_buchung("/gibt/es/nicht.csv"),
                         (None, 0, None, 0))
        self.assertEqual(tb.letzte_buchung(None), (None, 0, None, 0))


class JournalOhneAktionsspalteTest(unittest.TestCase):
    """orbk und orb schreiben `einstieg`/`ausgang` OHNE `aktion`-Spalte.

    Genau daran ist der erste Entwurf gescheitert: jede Zeile galt als "keine
    Buchung", und orbk stand mit 8 echten Zeilen als "noch kein Handel" im
    Bericht. Ein Schema-Wechsel darf das Alter einer Spur nicht erfinden.
    """

    def test_orbk_schema_zaehlt_als_buchung(self):
        tmp = Path(tempfile.mkdtemp()) / "handelsjournal.csv"
        with tmp.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["zeit", "inst", "richtung", "einstieg", "stop", "ziel",
                        "ausgang", "ausstieg", "gv_punkte", "gv_usd"])
            w.writerow([_zeit(1), "ETH_USD", "long", "100", "98", "105",
                        "ziel", "105", "5", "5"])
        tage, n, _, _ = tb.letzte_buchung(tmp)
        self.assertEqual(n, 1)
        self.assertEqual(tage, 1)

    def test_quotespalte_schlaegt_nicht_zu(self):
        tmp = Path(tempfile.mkdtemp()) / "handelsjournal.csv"
        with tmp.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["zeit", "inst", "bid", "ask", "quotes", "grund", "preis"])
            w.writerow([_zeit(0), "BTC/USD", "1", "2", "5", "quotes", ""])
        tage, n, tage_z, _ = tb.letzte_buchung(tmp)
        self.assertIsNone(tage)
        self.assertEqual(n, 0)
        self.assertEqual(tage_z, 0)


class StillblockTest(unittest.TestCase):

    def _eintrag(self, name, journal=None, erlaubt=False, schluessel=None):
        return {"name": name, "schluessel": schluessel, "wachen": {},
                "roh": {"journal": str(journal) if journal else None,
                        "wachen": {"handel_erlaubt": erlaubt}}}
        # Achtung: `wachen` kommt aus lage.zu_lage und nicht aus roh - hier
        # wird beides gesetzt, damit der Test beide Wege abdeckt.

    def test_alter_und_handelserlaubnis_stehen_drin(self):
        j = _journal([[_zeit(4), "papier", "kauf", "HYPE-USDC", "kopie"]])
        e = self._eintrag("Omniquant (papier)", j, erlaubt=False)
        e["wachen"] = {"handel_erlaubt": False}
        zeile = tb.stillblock([e])
        self.assertIn("letzte Buchung vor 4 Tag(en)", zeile)
        self.assertIn("handel_erlaubt=false", zeile)

    def test_ohne_journal_steht_kein_journal(self):
        e = self._eintrag("SuperTrend (Indikator)", None)
        self.assertIn("kein Journal", tb.stillblock([e]))

    def test_nur_kurse_ergibt_eigenen_text(self):
        j = _journal([[_zeit(0), "papier", "zyklus", "PF_XBTUSD", "quotes"]])
        e = self._eintrag("ORB-Kraken (Papier)", j)
        self.assertIn("noch kein Handel", tb.stillblock([e]))

    def test_leere_liste_ergibt_leeren_text(self):
        self.assertEqual(tb.stillblock([]), "")


class SammelzeileTest(unittest.TestCase):

    def test_doppelter_schluessel_wird_ausgeschrieben(self):
        stille = [
            {"name": "Kraken-Spot (EUR) (papier)", "schluessel": "nautilus_kraken"},
            {"name": "Kraken-Futures (USD) (papier)", "schluessel": "nautilus_kraken"},
        ]
        zeile = tb.sammelzeile(stille)
        self.assertIn("Kraken-Spot (EUR) (papier)", zeile)
        self.assertIn("Kraken-Futures (USD) (papier)", zeile)
        self.assertNotIn("nautilus_kraken", zeile)
        self.assertTrue(zeile.startswith("2 Spuren still:"))

    def test_eindeutiger_schluessel_bleibt_kurz(self):
        zeile = tb.sammelzeile([{"name": "IV-Wand (Optionszone)",
                                 "schluessel": "iv_wand"}])
        self.assertIn("iv_wand", zeile)
        self.assertNotIn("Optionszone", zeile)


if __name__ == "__main__":
    unittest.main(verbosity=2)
