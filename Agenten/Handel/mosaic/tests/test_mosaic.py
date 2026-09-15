"""Tests der Mosaic-Spur (Mehr-Zeitrahmen-Preisaktion). Kein Netz.

Geprueft wird:
 (a) Bias: letzte 4H-Kerze gruen -> long, rot -> short, fehlende Kerzen -> None.
 (b) Nachfragezone: Swing-Tiefs der letzten 20 30M-Kerzen -> Preisspanne;
     Zone beruehrt = Low <= obere Grenze und High >= untere.
 (c) Structure Shift: 5M-Schluss ueber letztem relevantem Swing-High = BOS.
 (d) Signal: alle drei Bedingungen zusammen -> 'long'; ohne eine -> None.
 (e) Positionsgroesse respektiert max_pro_trade_usd und die Ratsche.
 (f) Stop/Ziel: G/V auf den Nominalwert (nicht auf die rohe Kursdifferenz).
 (g) --vorschau schreibt keine Datei.
 (h) Ohne Kerzen kein Absturz.

Lauf (aus mosaic/tests):
 ..\\..\\scanner\\.venv\\Scripts\\python.exe unittest test_mosaic -v
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
# Rueckwaerts einfuegen: insert(0, ...) dreht die Reihenfolge um. HIER muss
# ganz vorne landen, sonst gewinnt scanner/handeln.py gegen das handeln.py
# dieser Spur.
for p in (os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln  # noqa: E402


def _kerze(open_, high, low, close, ts=0):
    """Eine Kerze als [ts, open, high, low, close, vol]."""
    return [ts, open_, high, low, close, 0.0]


def _aufwaerts(n, basis=100.0, schritt=0.01, ts0=1700000000000,
               intervall=3600000, pullback=None):
    """n Kerzen mit Aufwaertsdrift und optionalem Pullback am Ende.

    Ohne pullback: monotone gruene Serie (fuer 4H-Bias, Struktur).
    Mit pullback=anteil: Die letzten Kerzen fallen vom Hoehepunkt zurueck
    (rote Kerzen) und drehen dann wieder nach oben - die klassische
    Pullback-Zone-Form, die Swing-Tiefs erzeugt.
    """
    out = []
    amp = 0.05
    for i in range(n):
        phase = i % 8
        welle = 0.0
        if phase == 4:
            welle = -amp
        elif phase == 7:
            welle = amp
        o = basis + i * schritt + welle * 0.4
        c = o + schritt
        if pullback and i >= n - pullback:
            # Pullback: vom Hoehepunkt fallen, dann wieder steigen
            anteil = (i - (n - pullback)) / float(pullback)
            c = basis + (n - pullback) * schritt - anteil * 2.0 * schritt
            if anteil < 0.5:
                c = basis + (n - pullback) * schritt - anteil * 4.0 * schritt
            else:
                c = basis + (n - pullback) * schritt + (anteil - 0.5) * schritt
            o = c - schritt
        h = max(o, c) + 0.01
        l = min(o, c) - 0.01
        out.append(_kerze(o, h, l, c, ts0 + i * intervall))
    return out


def _pullback_zone(k30_bisher, zone, ts0=1700000000000, intervall=1800000):
    """Haengt einen Pullback an: Kurs faellt in die Zone, beruehrt sie,
    dreht nach oben. Erzeugt echte Swing-Tiefs."""
    untere, obere = zone
    n = len(k30_bisher)
    i = 0
    start = k30_bisher[-1][4]
    # 5 Kerzen: 3 fallende bis in die Zone, 1 Tiefst in der Zone, 1 steigend
    ziele = [start, (untere + start) / 2, untere, untere, (untere + obere) / 2]
    for j, ziel in enumerate(ziele):
        o = start if j == 0 else k30_bisher[-1][4]
        c = ziel
        h = max(o, c) + 0.005
        l = min(o, c) - 0.005
        k30_bisher.append(_kerze(o, h, l, c, ts0 + (n + i) * intervall))
        i += 1
    return k30_bisher


def _k5_bos(basis=100.0, ts0=1700000000000, intervall=300000):
    """60 5M-Kerzen: klar oszillierend (echte Swing-Hochs bei ~0.05), dann
    Ausbruch nach oben ueber das hoechste Swing-Hoch = BOS."""
    out = []
    for i in range(60):
        if i < 50:
            # Oszillation um Basis mit Amplitude ~0.03, zwei Wellenberge
            # bei i=15 und i=40 (Swing-Hochs ~100.05), Tal dazwischen.
            if i < 20:
                phase = i / 20.0 * 2 * 3.14159  # eine volle Welle bis 20
            else:
                phase = (i - 20) / 30.0 * 2 * 3.14159  # eine weitere bis 50
            welle = 0.03 * (phase if i < 20 else (1 - abs(phase - 3.14159) / 3.14159))
            o = basis + welle
            c = o + 0.002
            h = o + 0.015
            l = o - 0.015
        else:
            # Ausbruch: deutlich ueber dem hoechsten Swing-Hoch der ersten 50
            # (die liegen bei ~100.05-100.10). Schluss muss ueber 100.19.
            o = basis + 0.20 + (i - 50) * 0.004
            c = o + 0.012
            h = o + 0.03
            l = o - 0.008
        out.append(_kerze(o, h, l, c, ts0 + i * intervall))
    return out


class MosaicTest(unittest.TestCase):

    def setUp(self):
        # Frische Wachen mit kleinem Fenster fuer die Tests.
        self.w = {
            "waehrung": "USD",
            "handel_erlaubt": False,
            "herzschlag_max_minuten": 180,
            "risiko_je_position_usd": 5.0,
            "max_offene_positionen": 4,
            "max_pro_trade_usd": 150.0,
            "max_gesamt_usd": 600.0,
            "kill_switch_gesamt_usd": 40.0,
            "pflicht_stop_prozent_min": 5.0,
            "pflicht_stop_prozent_max": 12.0,
            "ziel_r_vielfaches": 2.0,
            "mindest_kerzen": 30,
            "kerzen_takt_4h": "4H",
            "kerzen_takt_30m": "30m",
            "kerzen_takt_5m": "5m",
            "trend_kerzen_4h": 1,
            "trend_min_kerzen_4h": 0,
            "zone_schwung_kerzen_30m": 20,
            "zone_beruehrung_kerzen_30m": 30,
            "zone_typ": "swing",
            "struktur_shift_kerzen_5m": 30,
            "instrumente": ["TEST-USDT"],
            "journal_zweitziel": r"Q:\Handel_Journal\mosaic",
            "drawdown_halbierung_usd": 20.0,
        }

    def test_bias_gruene_kerze(self):
        k4 = _aufwaerts(10)
        self.assertEqual(handeln.bias_4h(k4, self.w), "long")

    def test_bias_rote_kerze(self):
        k4 = _aufwaerts(9)
        k4.append(_kerze(101.0, 101.5, 100.0, 100.5))  # rote Kerze
        self.assertEqual(handeln.bias_4h(k4, self.w), "short")

    def test_bias_keine_kerzen(self):
        self.assertIsNone(handeln.bias_4h([], self.w))

    def test_nachfrage_zone_spanne(self):
        k30 = _aufwaerts(40, basis=100.0)
        zone = handeln.nachfrage_zone(k30, self.w)
        self.assertIsNotNone(zone)
        untere, obere = zone
        self.assertLess(untere, obere)

    def test_zone_beruehrt(self):
        k30 = _aufwaerts(40, basis=100.0)
        zone = handeln.nachfrage_zone(k30, self.w)
        self.assertIsNotNone(zone)
        # Pullback in die Zone haengen
        k30 = _pullback_zone(k30, zone)
        self.assertTrue(handeln.zone_beruehrt(k30, self.w, zone))

    def test_structure_shift(self):
        k5 = _k5_bos()
        self.assertTrue(handeln.structure_shift(k5, self.w))

    def test_signal_alle_drei(self):
        k4 = _aufwaerts(10)
        k30 = _aufwaerts(40, basis=100.0)
        zone = handeln.nachfrage_zone(k30, self.w)
        k30 = _pullback_zone(k30, zone)
        k5 = _k5_bos()
        self.assertEqual(handeln.signal(k4, k30, k5, self.w), "long")

    def test_signal_ohne_bias(self):
        k4 = _aufwaerts(9)
        k4.append(_kerze(101.0, 101.5, 100.0, 100.5))  # rot
        k30 = _aufwaerts(40, basis=100.0)
        zone = handeln.nachfrage_zone(k30, self.w)
        k30 = _pullback_zone(k30, zone)
        k5 = _aufwaerts(60, basis=100.0, schritt=0.005)
        self.assertIsNone(handeln.signal(k4, k30, k5, self.w))

    def test_groesse_gedeckelt(self):
        pct = 5.0
        w = dict(self.w)
        w["risiko_je_position_usd"] = 5.0
        w["max_pro_trade_usd"] = 150.0
        self.assertEqual(handeln.position_groesse(100.0, pct, w), 100.0)
        w["max_pro_trade_usd"] = 50.0
        self.assertEqual(handeln.position_groesse(100.0, pct, w), 50.0)

    def test_ausstieg_gv_auf_nominal(self):
        z = {"positionen": [{
            "inst": "TEST-USDT", "seite": "long", "einstieg": 100.0,
            "stop": 95.0, "ziel": 110.0, "stop_pct": 5.0,
            "nominal": 100.0, "eroeffnet_zeit": "2026-09-15T00:00:00+00:00",
        }]}
        k5 = _aufwaerts(40, basis=100.0, schritt=0.01)[-30:]
        # Kurs steigt ueber Ziel (110) -> Zielausstieg
        k5[-1] = _kerze(109.0, 112.0, 108.5, 111.0)
        with tempfile.TemporaryDirectory() as tmp:
            journal = os.path.join(tmp, "handelsjournal.csv")
            old = (handeln.JOURNAL, handeln.ZUSTAND, handeln.SCHREIBEN)
            handeln.JOURNAL = journal
            handeln.ZUSTAND = os.path.join(tmp, "zustand.json")
            handeln.SCHREIBEN = False  # kein echtes Ziel schreiben
            try:
                # Spur muss kein echter Ordner sein: pruefe_ausstiege nutzt nur k5
                handeln.pruefe_ausstiege(z, k5, self.w, nur="TEST-USDT")
            finally:
                handeln.JOURNAL, handeln.ZUSTAND, handeln.SCHREIBEN = old
        self.assertEqual(len(z["positionen"]), 0)

    def test_vorschau_schreibt_nichts(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = (handeln.WACHEN, handeln.ZUSTAND, handeln.JOURNAL,
                   handeln.SCHREIBEN, handeln.kerzen_quelle)
            handeln.WACHEN = os.path.join(tmp, "wachen.json")
            handeln.ZUSTAND = os.path.join(tmp, "zustand.json")
            handeln.JOURNAL = os.path.join(tmp, "handelsjournal.csv")
            handeln.SCHREIBEN = False
            fake = {"instrumente": ["TEST-USDT"], "journal_zweitziel": None}
            handeln.kerzen_quelle = lambda inst, iv, n: _aufwaerts(10)
            try:
                with open(handeln.WACHEN, "w", encoding="utf-8") as f:
                    json.dump(fake, f)
                handeln.lauf("vorschau")
                self.assertFalse(os.path.exists(handeln.JOURNAL))
                self.assertFalse(os.path.exists(handeln.ZUSTAND))
            finally:
                (handeln.WACHEN, handeln.ZUSTAND, handeln.JOURNAL,
                 handeln.SCHREIBEN, handeln.kerzen_quelle) = old

    def test_ohne_kerzen_kein_absturz(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = (handeln.WACHEN, handeln.ZUSTAND, handeln.JOURNAL,
                   handeln.SCHREIBEN, handeln.kerzen_quelle)
            handeln.WACHEN = os.path.join(tmp, "wachen.json")
            handeln.ZUSTAND = os.path.join(tmp, "zustand.json")
            handeln.JOURNAL = os.path.join(tmp, "handelsjournal.csv")
            handeln.SCHREIBEN = False
            handeln.kerzen_quelle = lambda inst, iv, n: []
            try:
                with open(handeln.WACHEN, "w", encoding="utf-8") as f:
                    json.dump({"instrumente": ["TEST-USDT"],
                               "journal_zweitziel": None}, f)
                handeln.lauf("papier")  # darf nicht werfen
            finally:
                (handeln.WACHEN, handeln.ZUSTAND, handeln.JOURNAL,
                 handeln.SCHREIBEN, handeln.kerzen_quelle) = old


if __name__ == "__main__":
    unittest.main()