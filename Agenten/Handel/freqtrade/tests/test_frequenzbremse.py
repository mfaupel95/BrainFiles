#!/usr/bin/env python3
"""Tests der Frequenzbremse (T-197). Netz- und Freqtrade-frei.

Die Regeln liegen in `user_data/strategies/frequenzbremse.py` als reine
Rechnung - genau deshalb sind sie hier ohne Boerse, ohne Container und ohne
Backtest pruefbar. Geprueft wird die REGEL, nicht ein Tageswert: jede Pruefung
haette auch rot werden koennen (Gegenprobe steht jeweils daneben).

Aufruf:  ./.venv/Scripts/python.exe -m unittest discover -s tests -t tests -v
"""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
STRATEGIEN = os.path.join(os.path.dirname(HIER), "user_data", "strategies")

_w = importlib.util.spec_from_file_location(
    "frequenzbremse", os.path.join(STRATEGIEN, "frequenzbremse.py"))
frequenzbremse = importlib.util.module_from_spec(_w)
sys.modules["frequenzbremse"] = frequenzbremse        # @dataclass-taugliche Reihenfolge
_w.loader.exec_module(frequenzbremse)


JETZT = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def runde(paar="BTC/USDT", vor_h=1.0, grund="exit_signal", ergebnis=-1.0,
          einsatz=100.0, dauer_h=1.0):
    return {"paar": paar, "auf_zeit": JETZT - timedelta(hours=vor_h + dauer_h),
            "zu_zeit": JETZT - timedelta(hours=vor_h), "grund": grund,
            "ergebnis_usd": ergebnis, "einsatz_usd": einsatz}


def g(**abweichend):
    """Grenzen fuer die Tests: Bremse AN, sonst waere jede Regel wirkungslos."""
    werte = dict(frequenzbremse.STANDARD)
    werte["bremse"] = True
    werte.update(abweichend)
    return frequenzbremse.grenzen(werte)


class SchalterTest(unittest.TestCase):
    def test_standard_ist_aus(self):
        # Eine stillschweigend drosselnde Neuerung waere schlimmer als keine:
        # ohne ausdrueckliche Angabe in der Bot-Konfiguration bremst nichts.
        self.assertFalse(frequenzbremse.STANDARD["bremse"])
        erlaubt, _, regel = frequenzbremse.urteil(
            [runde(grund="stop_loss", vor_h=0.5)], JETZT, "BTC/USDT",
            frequenzbremse.grenzen({}))
        self.assertTrue(erlaubt)
        self.assertEqual(regel, "bremse_aus")

    def test_aus_schaltet_jede_regel(self):
        # Alle Regeln scharf, aber der Hauptschalter aus.
        erlaubt, _, regel = frequenzbremse.urteil(
            [runde(grund="stop_loss", vor_h=0.5)], JETZT, "BTC/USDT",
            g(bremse=False, sperrfrist_stop_stunden=96))
        self.assertTrue(erlaubt)
        self.assertEqual(regel, "bremse_aus")

    def test_ohne_zeitpunkt_wird_nichts_gesperrt(self):
        erlaubt, _, regel = frequenzbremse.urteil([], None, "BTC/USDT", g())
        self.assertTrue(erlaubt)
        self.assertEqual(regel, "kein_zeitpunkt")

    def test_leere_geschichte_ist_frei(self):
        erlaubt, _, regel = frequenzbremse.urteil([], JETZT, "BTC/USDT", g())
        self.assertTrue(erlaubt)
        self.assertEqual(regel, "frei")


class SperrfristZielTest(unittest.TestCase):
    def test_ziel_vor_einer_stunde_sperrt(self):
        erlaubt, grund, regel = frequenzbremse.urteil(
            [runde(grund="roi", vor_h=1.0)], JETZT, "BTC/USDT",
            g(sperrfrist_stop_stunden=0))
        self.assertFalse(erlaubt)
        self.assertEqual(regel, "sperrfrist_ziel")
        self.assertIn("Sperrfrist", grund)

    def test_gegenprobe_nach_der_frist_ist_wieder_frei(self):
        # Dieselbe Runde, nur drei Stunden alt: die Frist (2 h) ist vorbei.
        erlaubt, _, regel = frequenzbremse.urteil(
            [runde(grund="roi", vor_h=3.0)], JETZT, "BTC/USDT",
            g(sperrfrist_stop_stunden=0))
        self.assertTrue(erlaubt)
        self.assertEqual(regel, "frei")

    def test_ein_ziel_sperrt_nur_sein_eigenes_paar(self):
        erlaubt, _, regel = frequenzbremse.urteil(
            [runde(paar="BTC/USDT", grund="roi", vor_h=0.5)], JETZT, "ETH/USDT",
            g(sperrfrist_stop_stunden=0))
        self.assertTrue(erlaubt)
        self.assertEqual(regel, "frei")

    def test_der_stop_gilt_laenger_als_das_ziel(self):
        # Zwei Runden: das Ziel ist alt, der Stop frisch - der Stop zaehlt.
        erlaubt, _, regel = frequenzbremse.urteil(
            [runde(grund="roi", vor_h=30.0),
             runde(grund="stop_loss", vor_h=2.0)], JETZT, "BTC/USDT", g())
        self.assertFalse(erlaubt)
        self.assertEqual(regel, "sperrfrist_stop")


class AbstandTest(unittest.TestCase):
    def test_abstand_haelt_den_zweiten_einstieg_auf(self):
        erlaubt, _, regel = frequenzbremse.urteil(
            [runde(vor_h=3.0)], JETZT, "BTC/USDT",
            g(sperrfrist_ziel_stunden=0, sperrfrist_stop_stunden=0,
              mindestabstand_einstieg_stunden=6.0))
        self.assertFalse(erlaubt)
        self.assertEqual(regel, "mindestabstand")

    def test_ohne_abstand_greift_er_nicht(self):
        erlaubt, _, regel = frequenzbremse.urteil(
            [runde(vor_h=0.5)], JETZT, "BTC/USDT",
            g(sperrfrist_ziel_stunden=0, sperrfrist_stop_stunden=0,
              mindestabstand_einstieg_stunden=0))
        self.assertTrue(erlaubt)
        self.assertEqual(regel, "frei")

    def test_abstand_zaehlt_die_letzte_runde_des_paares(self):
        erlaubt, _, _ = frequenzbremse.urteil(
            [runde(paar="ETH/USDT", vor_h=0.2), runde(paar="BTC/USDT", vor_h=9.0)],
            JETZT, "BTC/USDT",
            g(sperrfrist_ziel_stunden=0, sperrfrist_stop_stunden=0,
              mindestabstand_einstieg_stunden=6.0))
        self.assertTrue(erlaubt)          # BTC ist 9 h her, ETH zaehlt nicht


class FensterTest(unittest.TestCase):
    def test_verlustgrenze_im_fenster_sperrt_das_ganze_buch(self):
        # 6 % Verlust des Einsatzes in 12 h - ueber der Grenze von 5 %.
        erlaubt, grund, regel = frequenzbremse.urteil(
            [runde(paar="ETH/USDT", vor_h=2.0, ergebnis=-6.0, einsatz=100.0)],
            JETZT, "BTC/USDT",
            g(sperrfrist_ziel_stunden=0, sperrfrist_stop_stunden=0,
              mindestabstand_einstieg_stunden=0, verlust_max_pct=5.0))
        self.assertFalse(erlaubt)
        self.assertEqual(regel, "verlust_pct")

    def test_gegenprobe_unter_der_grenze_bleibt_frei(self):
        erlaubt, _, _ = frequenzbremse.urteil(
            [runde(paar="ETH/USDT", vor_h=2.0, ergebnis=-3.0, einsatz=100.0)],
            JETZT, "BTC/USDT",
            g(sperrfrist_ziel_stunden=0, sperrfrist_stop_stunden=0,
              mindestabstand_einstieg_stunden=0, verlust_max_pct=5.0))
        self.assertTrue(erlaubt)

    def test_alte_runden_zaehlen_nicht_mehr(self):
        # Derselbe Verlust, aber 20 h her - Fenster ist 12 h.
        erlaubt, _, _ = frequenzbremse.urteil(
            [runde(paar="ETH/USDT", vor_h=20.0, ergebnis=-6.0, einsatz=100.0)],
            JETZT, "BTC/USDT",
            g(sperrfrist_ziel_stunden=0, sperrfrist_stop_stunden=0,
              mindestabstand_einstieg_stunden=0, verlust_max_pct=5.0))
        self.assertTrue(erlaubt)

    def test_gewinnziel_im_fenster_stoppt_ebenfalls(self):
        erlaubt, _, regel = frequenzbremse.urteil(
            [runde(vor_h=1.0, ergebnis=6.0, einsatz=100.0)], JETZT, "BTC/USDT",
            g(sperrfrist_ziel_stunden=0, sperrfrist_stop_stunden=0,
              gewinn_ziel_pct=5.0))
        self.assertFalse(erlaubt)
        self.assertEqual(regel, "gewinn_pct")

    def test_usd_grenze_wirkt_wenn_gesetzt(self):
        erlaubt, _, regel = frequenzbremse.urteil(
            [runde(vor_h=1.0, ergebnis=-30.0, einsatz=1000.0)], JETZT, "BTC/USDT",
            g(sperrfrist_ziel_stunden=0, sperrfrist_stop_stunden=0,
              verlust_max_usd=25.0, verlust_max_pct=None))
        self.assertFalse(erlaubt)
        self.assertEqual(regel, "verlust_usd")

    def test_usd_grenze_ist_standardmaessig_aus(self):
        # Die Standardwerte sind null - sonst waere die Uebertragung auf ein
        # grosses Konto still falsch (siehe Modul-Docstring).
        self.assertIsNone(frequenzbremse.STANDARD["verlust_max_usd"])
        self.assertIsNone(frequenzbremse.STANDARD["gewinn_ziel_usd"])


class EinstiegsdeckelTest(unittest.TestCase):
    def test_deckel_zaehlt_nur_das_eigene_paar(self):
        runden = [runde(paar="BTC/USDT", vor_h=h) for h in (1.0, 3.0)]
        erlaubt, _, regel = frequenzbremse.urteil(
            runden, JETZT, "BTC/USDT",
            g(sperrfrist_ziel_stunden=0, sperrfrist_stop_stunden=0,
              fenster_stunden=12.0, max_einstiege_je_paar_im_fenster=2))
        self.assertFalse(erlaubt)
        self.assertEqual(regel, "max_einstiege")

    def test_deckel_ohne_fenster_ist_wirkungslos(self):
        runden = [runde(paar="BTC/USDT", vor_h=h) for h in (1.0, 3.0)]
        erlaubt, _, _ = frequenzbremse.urteil(
            runden, JETZT, "BTC/USDT",
            g(sperrfrist_ziel_stunden=0, sperrfrist_stop_stunden=0,
              fenster_stunden=0, max_einstiege_je_paar_im_fenster=1))
        self.assertTrue(erlaubt)


class GrenzenTest(unittest.TestCase):
    def test_fehlende_angabe_laesst_den_standard_stehen(self):
        # Eine Luecke darf keine Regel still umstellen.
        werte = frequenzbremse.grenzen({"mindestabstand_einstieg_stunden": 6.0})
        self.assertEqual(werte["sperrfrist_ziel_stunden"],
                         frequenzbremse.STANDARD["sperrfrist_ziel_stunden"])
        self.assertEqual(werte["mindestabstand_einstieg_stunden"], 6.0)

    def test_zeitpunkt_als_text_wird_verstanden(self):
        erlaubt, _, regel = frequenzbremse.urteil(
            [runde(grund="roi", vor_h=0.5)], "2026-10-01T12:00:00+00:00",
            "BTC/USDT", g(sperrfrist_stop_stunden=0))
        self.assertFalse(erlaubt)
        self.assertEqual(regel, "sperrfrist_ziel")

    def test_lage_nennt_regel_und_grund(self):
        aus = frequenzbremse.lage([runde(grund="roi", vor_h=0.5)], JETZT,
                                  "BTC/USDT", g(sperrfrist_stop_stunden=0))
        self.assertFalse(aus["erlaubt"])
        self.assertEqual(aus["regel"], "sperrfrist_ziel")
        self.assertEqual(aus["runden_paar"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)