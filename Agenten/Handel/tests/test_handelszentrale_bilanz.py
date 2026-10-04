"""Bilanzspalten in der Handelszentrale (Auftrag Max 05.10.2026).

Der Auftrag war "die PnL% etc als Auswahl in den Listen zum Filtern". In der
Zentrale fehlten sie voellig - dort standen nur Modus, Fenster, Pos und
Herzschlag. Geprueft wird:

1. Drei Zellen in fester Reihenfolge, mit "?" statt einer geratenen Zahl.
2. `spur_zeile` liefert genau so viele Zellen, wie die Tabelle Spalten hat -
   sonst schweigt die Anzeige still (Tabelle zeigt nur was hingesendet wird).
3. `bilanz_zellen` ist eine reine Funktion: kaputte Quelle -> "?", nicht raises.

Direkt ausfuehrbar:  python tests/test_handelszentrale_bilanz.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import handelszentrale as hz                                   # noqa: E402


KENNZAHLEN = {"n": 16, "treffer": 9, "treffer_pct": 56.25,
              "ergebnis": 35.72, "einheit": "USD"}
LEER = {"n": 0}


class Zellen(unittest.TestCase):
    def bilanz(self, daten, fenster=None):
        with patch.object(hz.auswertung_alle, "kennzahlen_fuer",
                          return_value=daten):
            return hz.bilanz_zellen("xperp", fenster)

    def test_vollstaendige_buch(self):
        self.assertEqual(self.bilanz(KENNZAHLEN), ("16", "56 %", "+35.72 USD"))

    def test_minus_bleibt_minus(self):
        d = dict(KENNZAHLEN, ergebnis=-5.02)
        self.assertEqual(self.bilanz(d)[2], "-5.02 USD")

    def test_ohne_runden_steht_fragezeichen(self):
        # Eine Spur mit leerem Journal darf KEINE 0 % und kein 0.00 zeigen -
        # das waere eine Zahl, die nach Messung aussieht.
        r, t, p = self.bilanz(LEER)
        self.assertEqual((r, t, p), ("?", "?", "?"))

    def test_fehlende_einheit_ist_kein_fehler(self):
        d = dict(KENNZAHLEN)
        d.pop("einheit")
        self.assertTrue(self.bilanz(d)[2].endswith("USD"))

    def test_kaputte_quelle_kein_absturz(self):
        with patch.object(hz.auswertung_alle, "kennzahlen_fuer",
                          side_effect=OSError("Journal nicht lesbar")):
            self.assertEqual(hz.bilanz_zellen("kaputt"), ("?", "?", "?"))

    def test_gerundet_aber_nicht_verschluckt(self):
        d = dict(KENNZAHLEN, treffer_pct=56.94)
        self.assertEqual(self.bilanz(d)[1], "57 %")


class Zeile(unittest.TestCase):
    STAND = {"spur": "xperp", "modus": "papier", "fenster": "",
             "stand": "Papier", "positionen": 7, "herzschlag": "ok",
             "handel_erlaubt": False}

    def test_zehn_zellen_fuer_zehn_spalten(self):
        with patch.object(hz, "bilanz_zellen", return_value=("1", "2", "3")):
            zeile = hz.spur_zeile(dict(self.STAND))
        self.assertEqual(len(zeile), 10)

    def test_die_zehn_spalten_der_tabelle(self):
        """Die Spalten der Tabelle und die Zellen muessen zusammenpassen.

        Sonst schweigt die Anzeige still: ttk.Treeview zeigt so viele Spalten
        wie Werte - ein Tuple zu kurz verliert die hinteren Spalten ohne
        Fehlermeldung.
        """
        quelle = Path(hz.__file__).read_text(encoding="utf-8")
        self.assertIn('"runden": "Runden"', quelle)
        self.assertIn('"treffer": "Treffer %"', quelle)
        self.assertIn('"pnl": "Ergebnis"', quelle)

    def test_reihenfolge_ist_steuer_modus_fenster_stand_pos(self):
        with patch.object(hz, "bilanz_zellen", return_value=("1", "2", "3")):
            zeile = hz.spur_zeile(dict(self.STAND))
        self.assertEqual(zeile[:5], ("xperp", "papier", "", "Papier", "7"))
        self.assertEqual(zeile[5:8], ("1", "2", "3"))
        self.assertEqual(zeile[8:], ("ok", "nein"))

    def test_unbekannter_schalter_bleibt_fragezeichen(self):
        stand = dict(self.STAND)
        stand["handel_erlaubt"] = None
        with patch.object(hz, "bilanz_zellen", return_value=("1", "2", "3")):
            self.assertEqual(hz.spur_zeile(stand)[-1], "?")


if __name__ == "__main__":
    unittest.main()
