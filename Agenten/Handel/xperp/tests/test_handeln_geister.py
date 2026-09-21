"""Tests: Geisterpruefung und Fuellungspruefung in xperp/handeln.py.

ANLASS (21.09.2026, gemeldet von Max): "Spur xperp zeigt 2 Positionen. Live ist
aber nur BZ da." Nachgemessen an der Boerse:

    Book:   HBAR-USD_UM_XPERP-310815, BZ-..., CRCL-...
    Boerse: CRCL (1.1), BZ (208), SUI (1066 - nicht vom Bot)

HBAR war ein GEIST: die Limit-Order lag offen und war nie gefuellt
(accFillSz = 0, state = live), /account/positions kennt das Instrument nicht.
xperp hatte die Position beim ANNEHMEN der Order gebucht, nicht beim Fuellen.

Die Tests schreiben nie in die echten Dateien: `journal` wird ersetzt und
`okxf` gestubbt.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parent
sys.path.insert(0, str(SPUR))
sys.path.insert(0, str(HANDEL))

import handeln as h                                                  # noqa: E402


def _pos(inst, modus="live"):
    return {"inst": inst, "seite": "long", "familie": "krypto", "einstieg": 1.0,
            "nominal": 100.0, "margin": 20.0, "hebel": 5.0, "kontrakte": 10.0,
            "modus": modus}


class Geister(unittest.TestCase):
    def setUp(self):
        self.geschrieben = []
        self.j = patch.object(h, "journal",
                              side_effect=lambda **k: self.geschrieben.append(k))
        self.j.start()
        self.addCleanup(self.j.stop)

    def test_position_ohne_bestand_wird_ausgebucht(self):
        z = {"positionen": [_pos("HBAR-100"), _pos("BZ-200")]}
        boerse = [{"instId": "BZ-200", "pos": "208"}]
        with patch.object(h.okxf, "positionen", return_value=boerse),                 patch.object(h.okxf, "order_stornieren") as storno:
            n = h.bueche_geister_aus(z, {})
        storno.assert_not_called()
        self.assertEqual(n, 1)
        self.assertEqual([p["inst"] for p in z["positionen"]], ["BZ-200"])
        self.assertEqual(self.geschrieben[0]["grund"], "buchbereinigung_geist")

    def test_gefuellte_order_bleibt_trotz_fehlender_position(self):
        """Die Wettlaufsituation vom 21.09.2026 (HBAR).

        Beim Pruefen war accFillSz 0, Sekunden spaeter war die Order
        gefuellt. Haette die Pruefung die Position ausgebucht, liefe sie
        ohne Buch weiter - genau das ist an dem Abend passiert.
        """
        p = _pos("HBAR-100"); p["ord_id"] = "3942552192558157824"
        z = {"positionen": [p]}
        with patch.object(h.okxf, "positionen", return_value=[]),                 patch.object(h.okxf, "gefuellte_kontrakte", return_value=9.4),                 patch.object(h.okxf, "order_stornieren") as storno:
            n = h.bueche_geister_aus(z, {})
        self.assertEqual(n, 0, "eine gefuellte Order ist keine Leiche")
        self.assertEqual(len(z["positionen"]), 1)
        storno.assert_not_called()

    def test_offene_order_des_geists_wird_storniert(self):
        # Bleibt die Order liegen, kann sie spaeter fuellen und eine Position
        # ohne Buch erzeugen (genau der HBAR-Fall: state=live, accFillSz=0).
        p = _pos("HBAR-100"); p["ord_id"] = "3942552192558157824"
        z = {"positionen": [p]}
        with patch.object(h.okxf, "positionen", return_value=[]),                 patch.object(h.okxf, "order_stornieren") as storno:
            h.bueche_geister_aus(z, {})
        storno.assert_called_once_with("HBAR-100", "3942552192558157824")

    def test_position_mit_groesse_null_ist_ein_geist(self):
        # OKX behaelt geschlossene Positionen als Zeile mit pos=0 (am 21.09.2026
        # bei ZEC/LINK gesehen) - das ist kein Bestand.
        z = {"positionen": [_pos("ZEC-300")]}
        with patch.object(h.okxf, "positionen",
                          return_value=[{"instId": "ZEC-300", "pos": "0"}]):
            self.assertEqual(h.bueche_geister_aus(z, {}), 1)
        self.assertEqual(z["positionen"], [])

    def test_papierpositionen_werden_nicht_angefasst(self):
        z = {"positionen": [_pos("ALT-1", modus="papier")]}
        with patch.object(h.okxf, "positionen", return_value=[]):
            self.assertEqual(h.bueche_geister_aus(z, {}), 0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_netzfehler_laesst_das_buch_in_ruhe(self):
        z = {"positionen": [_pos("HBAR-100"), _pos("BZ-200")]}
        with patch.object(h.okxf, "positionen", side_effect=RuntimeError("kein Netz")):
            self.assertEqual(h.bueche_geister_aus(z, {}), 0)
        self.assertEqual(len(z["positionen"]), 2, "ein Netzfehler darf nichts loeschen")

    def test_echte_position_bleibt(self):
        z = {"positionen": [_pos("CRCL-1")]}
        with patch.object(h.okxf, "positionen",
                          return_value=[{"instId": "CRCL-1", "pos": "1.1"}]):
            self.assertEqual(h.bueche_geister_aus(z, {}), 0)
        self.assertEqual(len(z["positionen"]), 1)


class Fuellung(unittest.TestCase):
    def test_nicht_gefuellte_order_ergibt_null(self):
        with patch.object(h.okxf, "gefuellte_kontrakte", return_value=0.0):
            self.assertEqual(h._warten_auf_fuellung("X", "1", 10, versuche=1), 0.0)

    def test_gefuellte_order_gibt_menge(self):
        with patch.object(h.okxf, "gefuellte_kontrakte", return_value=9.4):
            self.assertEqual(h._warten_auf_fuellung("X", "1", 10, versuche=1), 9.4)

    def test_unbekannt_zaehlt_als_nicht_gefuellt(self):
        # None = Abfrage unmoeglich. Dann wird NICHT gebucht: lieber eine
        # Order zu viel stornieren als eine Position erfinden.
        with patch.object(h.okxf, "gefuellte_kontrakte", return_value=None):
            self.assertEqual(h._warten_auf_fuellung("X", "1", 10, versuche=1), 0.0)

    def test_langsame_fuellung_wird_erwartet(self):
        folge = [0.0, 0.0, 5.0]
        with patch.object(h.okxf, "gefuellte_kontrakte", side_effect=lambda i, o: folge.pop(0)):
            self.assertEqual(
                h._warten_auf_fuellung("X", "1", 10, versuche=3, warte=0), 5.0)


class PapierlaufLaesstEchtePositionenInRuhe(unittest.TestCase):
    """Ein Papierlauf darf keine echte Position ausbuchen.

    ANLASS (gemessen 21.09.2026, 20:52): xperp lief mit handel_erlaubt=false
    im PAPER, der Kill-Switch loeste aus und schrieb
    "papier,schliessen,HBAR-...,grund kill_switch" ins Journal - waehrend
    /account/positions die 9.4 Kontrakte unveraendert hielt. Die echte Position
    war damit aus dem Buch, aber nicht an der Boerse geschlossen.
    """

    def setUp(self):
        self.geschrieben = []
        self.j = patch.object(h, "journal",
                              side_effect=lambda **k: self.geschrieben.append(k))
        self.j.start()
        self.addCleanup(self.j.stop)
        self.storno = patch.object(h.okxf, "markt_schliessen")
        self.storno.start()
        self.addCleanup(self.storno.stop)

    def test_flach_stellen_papier_laesst_live_stehen(self):
        z = {"positionen": [_pos("HBAR-100"), _pos("ALT-1", modus="papier")]}
        self.j.stop()   # der echte journal()-Aufruf wuerde schreiben
        h.journal = lambda **k: None
        with patch.object(h, "_kurs_aktuell", return_value=1.0):
            h.flach_stellen(z, live=False, grund="kill_switch")
        self.assertEqual([p["inst"] for p in z["positionen"]], ["HBAR-100"])
        h.okxf.markt_schliessen.assert_not_called()

    def test_pruefe_ausstiege_papier_laesst_live_stehen(self):
        z = {"positionen": [_pos("HBAR-100")]}
        z["positionen"][0]["stop"] = 99.0     # Kurs 1.0 -> Stop laengst gerissen
        z["positionen"][0]["ziel"] = 99.0
        h.journal = lambda **k: None
        with patch.object(h, "_kurs_aktuell", return_value=1.0):
            h.pruefe_ausstiege(z, live=False, w={})
        self.assertEqual(len(z["positionen"]), 1,
                         "Papierlauf darf eine echte Position nicht schliessen")


if __name__ == "__main__":
    unittest.main()
