"""Test fuer die Ausstiegsgruende in handeln.py - ohne Netz, ohne Order.

Geprueft wird, was im Journal steht, wenn der Kurs eine Schwelle beruehrt.
Der Fall, um den es geht: Liegt der Kurs hinter der Liquidationsschwelle, ist
der Stop auf dem Weg dorthin schon durchlaufen - die Schwelle liegt immer
hinter ihm. Stuende der Stop zuerst im `if`, stuende bei einem Totalverlust
"stop" im Journal und die Liquidationszeile waere toter Code.

Der Kurs kommt aus einem Lambda, das Journal in eine Temp-Datei, `live=False`.
`okxf.markt_schliessen` wird durch einen Werfer ersetzt: Ein Test, der den
Order-Pfad erreichen koennte, waere der Fehler, nicht der Nachweis.

Direkt ausfuehrbar:  python test_ausstieg.py
"""

import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import handeln as h                                          # noqa: E402
import okxf                                                  # noqa: E402

LONG = {"inst": "XAU-USD_UM_XPERP-310620", "basis": "XAU", "seite": "long",
        "familie": "rohstoff", "einstieg": 100.0, "stop": 97.0, "ziel": 106.0,
        "liq": 82.0, "kontrakte": 10, "nominal": 100.0, "margin": 20.0,
        "hebel": 5.0, "gebuehr_taker": 0.0005, "eroeffnet": "2026-09-12"}
SHORT = dict(LONG, seite="short", stop=103.0, ziel=94.0, liq=118.0)


class Ausstieg(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kurs_original = h._kurs_aktuell    # die echte Funktion, fuer Rollover-Tests
        self.alt = (h.JOURNAL, h._kurs_aktuell, okxf.markt_schliessen)
        h.JOURNAL = os.path.join(self.tmp.name, "handelsjournal.csv")

        def kein_order(*a, **kw):
            raise AssertionError("Der Order-Pfad darf aus dem Test nie erreicht werden")
        okxf.markt_schliessen = kein_order

        def kein_kurs(p):
            raise AssertionError("kein Kurs gesetzt")
        h._kurs_aktuell = kein_kurs

    def tearDown(self):
        h.JOURNAL, h._kurs_aktuell, okxf.markt_schliessen = self.alt
        self.tmp.cleanup()

    def journal(self):
        if not os.path.exists(h.JOURNAL):
            return []                       # nichts geschrieben = keine Zeile
        with open(h.JOURNAL, encoding="utf-8") as f:
            return f.read().splitlines()

    def schliesse(self, position, kurs):
        """Ein Ausstiegslauf mit festem Kurs. Rueckgabe: (Grund, Zustand)."""
        h._kurs_aktuell = lambda p: kurs
        z = {"positionen": [dict(position)], "letzte_stops": {}}
        h.pruefe_ausstiege(z, False, {})
        zeilen = self.journal()
        grund = zeilen[1].split(",")[-1] if len(zeilen) > 1 else None
        return grund, z

    # --- Long ---

    def test_liquidation_wird_als_solche_erkannt(self):
        grund, z = self.schliesse(LONG, 80.0)          # hinter der Schwelle 82
        self.assertEqual(grund, "LIQUIDATION")
        self.assertEqual(z["positionen"], [])
        self.assertEqual(z["letzte_stops"]["XAU"], h._heute())

    def test_genau_auf_der_schwelle_zaehlt_als_liquidation(self):
        grund, _ = self.schliesse(LONG, 82.0)
        self.assertEqual(grund, "LIQUIDATION")

    def test_stop_zwischen_stop_und_schwelle_bleibt_stop(self):
        grund, _ = self.schliesse(LONG, 96.5)
        self.assertEqual(grund, "stop")

    def test_genau_auf_dem_stop_ist_kein_liquidationsfall(self):
        grund, _ = self.schliesse(LONG, 97.0)
        self.assertEqual(grund, "stop")

    def test_ziel_schliesst_ohne_abklingzeit(self):
        grund, z = self.schliesse(LONG, 107.0)
        self.assertEqual(grund, "ziel")
        self.assertEqual(z["letzte_stops"], {})

    def test_dazwischen_passiert_nichts(self):
        grund, z = self.schliesse(LONG, 100.0)
        self.assertIsNone(grund)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self.journal(), [])

    def test_ausstieg_zeile_traegt_filterwort_und_inst(self):
        """Der Dauerlauf schickt nur Zeilen mit Filterwort nach Telegram.

        Ein Ziel-Ausstieg trug bis zum 14.09.2026 keines davon (`ZU ... (ziel)`)
        - er stand im Journal und war im Chat unsichtbar. Geprueft wird die
        gedruckte Zeile, nicht das Journal.
        """
        h._kurs_aktuell = lambda p: 107.0
        z = {"positionen": [dict(LONG)], "letzte_stops": {}}
        puffer = io.StringIO()
        with patch("sys.stdout", puffer):
            h.pruefe_ausstiege(z, False, {})
        text = puffer.getvalue()
        self.assertIn("AUSSTIEG (ziel)", text)
        self.assertTrue(any(w in text.lower()
                            for w in ("verkauf", "stop", "kill", "gesperrt",
                                      "ausstieg")),
                        "kein Filterwort in der Zeile: %r" % text)
        self.assertIn(LONG["inst"], text,
                      "das Instrument muss in der Zeile stehen")

    # --- Short: die Schwelle liegt ueber dem Stop ---

    def test_short_liquidation_oberhalb_der_schwelle(self):
        grund, _ = self.schliesse(SHORT, 120.0)
        self.assertEqual(grund, "LIQUIDATION")

    def test_short_stop_unterhalb_der_schwelle(self):
        grund, _ = self.schliesse(SHORT, 104.0)
        self.assertEqual(grund, "stop")

    def test_short_ziel(self):
        grund, _ = self.schliesse(SHORT, 93.0)
        self.assertEqual(grund, "ziel")

    def test_rollover_stellt_inst_um_ohne_ausstieg(self):
        """Alter Kontrakt (51001): pruefe_ausstiege migriert die Position auf
        den lebenden Kontrakt des Basiswerts und bucht eine rollover-Zeile.

        Ohne die Umstellung bliebe die Position ewig ohne Kurs - Stop und
        Ziel wuerden nie geprueft (Befund 14.09.2026: XAU/BZ zeigten im
        Bericht 'kein Kurs')."""
        p = dict(LONG, inst="XAU-USD_UM_XPERP-310516")   # toter Kontrakt
        z = {"positionen": [p], "letzte_stops": {}}
        h._kurs_aktuell = self.kurs_original
        with patch.object(okxf, "letzter_kurs_mit_fallback",
                          return_value=("XAU-USD_UM_XPERP-310502",
                                        100.5)) as m:
            h.pruefe_ausstiege(z, False, {})
        m.assert_called_once_with("XAU-USD_UM_XPERP-310516", "XAU")
        self.assertEqual(z["positionen"][0]["inst"],
                         "XAU-USD_UM_XPERP-310502")
        zeilen = self.journal()
        rollover = [l for l in zeilen if "rollover" in l]
        self.assertEqual(len(rollover), 1)
        self.assertIn("XAU-USD_UM_XPERP-310516", rollover[0])

    def test_rollover_verhaelt_sich_wie_kurs_sonst(self):
        """Eine migrierte Position wird normal ausgestoppt: der Kurs des
        neuen Kontrakts entscheidet, der Grund bleibt 'stop'."""
        p = dict(LONG, inst="XAU-USD_UM_XPERP-310516",
                 stop=97.0)
        z = {"positionen": [p], "letzte_stops": {}}
        h._kurs_aktuell = self.kurs_original
        with patch.object(okxf, "letzter_kurs_mit_fallback",
                          return_value=("XAU-USD_UM_XPERP-310502", 96.5)):
            h.pruefe_ausstiege(z, False, {})
        self.assertEqual(z["positionen"], [])
        self.assertEqual(z["letzte_stops"]["XAU"], h._heute())
        zeilen = self.journal()
        self.assertTrue(any("rollover" in l for l in zeilen))
        letzte = zeilen[-1]
        self.assertTrue(letzte.endswith("stop") or ",stop" in letzte)


class Fallback(unittest.TestCase):
    """okxf.letzter_kurs_mit_fallback gegen OKX-Antworten - ohne Netz."""

    def test_fallback_wechselt_auf_lebenden_kontrakt(self):
        fehler = okxf.OKXFehler(
            "OKX 51001: Instrument ID, Instrument ID code, or Spread ID "
            "doesn't exist.")
        with patch.object(okxf, "_mit_wiederholung",
                          side_effect=[fehler, [{"last": "4335.5"}]]) as m, \
             patch.object(okxf, "instrument",
                          return_value={"instId": "XAU-USD_UM_XPERP-310502"}):
            inst, kurs = okxf.letzter_kurs_mit_fallback(
                "XAU-USD_UM_XPERP-310516", "XAU")
        self.assertEqual(inst, "XAU-USD_UM_XPERP-310502")
        self.assertEqual(kurs, 4335.5)

    def test_ohne_basis_kein_fallback(self):
        fehler = okxf.OKXFehler(
            "OKX 51001: Instrument ID, Instrument ID code, or Spread ID "
            "doesn't exist.")
        with patch.object(okxf, "_mit_wiederholung",
                          side_effect=fehler) as m:
            self.assertRaises(okxf.OKXFehler, okxf.letzter_kurs_mit_fallback,
                              "XAU-USD_UM_XPERP-310516")
        m.assert_called_once()

    def test_transportfehler_kein_fallback(self):
        # 429/Timeout ist kein Rollover: darf nicht still auf einen anderen
        # Kontrakt wechseln.
        with patch.object(okxf, "_mit_wiederholung",
                          side_effect=RuntimeError("kaputt")):
            self.assertRaises(RuntimeError, okxf.letzter_kurs_mit_fallback,
                              "XAU-USD_UM_XPERP-310516", "XAU")


if __name__ == "__main__":
    unittest.main(verbosity=2)
