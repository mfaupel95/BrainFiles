"""Tests fuer die IV-Wand-Spur - ohne Netz.

Geprueft wird die Rechnung, die diese Spur ausmacht: aus Open Interest und
Verfall die Wand bestimmen, daraus die Richtung ableiten und das Ziel als
MARKTPUNKT durch das Buch fuehren. Die Abrufe werden ersetzt
(`options_quelle`, `spot_quelle`), damit der Test nicht an OKX haengt.

Der Ordner-Waechter (setUpModule/tearDownModule) verhindert, dass ein Test in
den echten Spurenordner schreibt - das ist beim Bau der ersten Bot-Spur einmal
passiert.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
for p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln as h  # noqa: E402
import spur_buch as buch  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py: %s" % h.__file__

JETZT = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


def _offen(paare):
    return [{"instId": i, "oiUsd": v} for i, v in paare]


def _uebersicht(paare):
    return [{"instId": i, "markVol": v} for i, v in paare]


class WandTest(unittest.TestCase):
    def test_naechster_verfall_zaehlt_nicht_mit(self):
        # Ein Verfall in 2 Tagen faellt aus dem Fenster (7 bis 45 Tage).
        offen = _offen([("BTC-USD-260918-90000-C", "900000000"),
                        ("BTC-USD-261016-70000-C", "500000000")])
        wand = h.wand_bauen(offen, [], JETZT)
        self.assertEqual(wand["strike"], 70000.0)

    def test_call_und_put_desselben_strikes_zaehlen_zusammen(self):
        offen = _offen([("BTC-USD-261016-70000-C", "400000000"),
                        ("BTC-USD-261016-70000-P", "400000000"),
                        ("BTC-USD-261016-80000-C", "500000000")])
        wand = h.wand_bauen(offen, [], JETZT)
        self.assertEqual(wand["strike"], 70000.0)
        self.assertAlmostEqual(wand["oi_usd"], 800000000.0)

    def test_iv_wird_gemittelt(self):
        offen = _offen([("BTC-USD-261016-70000-C", "1"),
                        ("BTC-USD-261016-70000-P", "1")])
        uebersicht = _uebersicht([("BTC-USD-261016-70000-C", 0.40),
                                  ("BTC-USD-261016-70000-P", 0.60)])
        wand = h.wand_bauen(offen, uebersicht, JETZT)
        self.assertAlmostEqual(wand["iv_pct"], 50.0, places=6)

    def test_ohne_daten_keine_wand(self):
        self.assertIsNone(h.wand_bauen([], [], JETZT))

    def test_verfall_lesen(self):
        # OKX-Verfall ist 08:00 UTC. JETZT steht auf 12:00 UTC desselben Tages,
        # also bleiben 6 Tage und 20 Stunden - nicht glatte 7.
        self.assertAlmostEqual(h.tage_bis("260923", JETZT), 6.8333, places=3)
        self.assertIsNone(h.tage_bis("kaputt", JETZT))

    def test_strike_aus_instid(self):
        self.assertEqual(h.strike_aus("BTC-USD-260925-79000-C"),
                         (79000.0, "260925", "C"))
        self.assertIsNone(h.strike_aus("BTC-USDT"))


class RegelTest(unittest.TestCase):
    def _d(self, spot, wand):
        return {"spot": spot, "wand": {"strike": wand}}

    def test_unter_der_wand_ist_long(self):
        # Spot 70000, Wand 72000 -> 2,9 % darunter.
        self.assertEqual(h.signal(self._d(70000.0, 72000.0), {"max_abstand_pct": 5.0}),
                         "long")

    def test_ueber_der_wand_ist_short(self):
        self.assertEqual(h.signal(self._d(74000.0, 72000.0), {"max_abstand_pct": 5.0}),
                         "short")

    def test_zu_weit_weg_kein_signal(self):
        self.assertIsNone(h.signal(self._d(60000.0, 72000.0), {"max_abstand_pct": 5.0}))

    def test_genau_auf_der_wand_kein_signal(self):
        self.assertIsNone(h.signal(self._d(72000.0, 72000.0), {"max_abstand_pct": 5.0}))

    def test_ziel_ist_die_wand(self):
        self.assertEqual(h.ziel(self._d(70000.0, 72000.0), {}), 72000.0)

    def test_ziel_vor_wand_long_unter_der_wand(self):
        # Long kommt von unten: das Ziel muss UNTER der Wand liegen, sonst
        # waere es hinter dem Einstieg und spur_buch wuerde es ablehnen.
        z = h.ziel(self._d(70000.0, 72000.0), {"ziel_vor_wand_pct": 0.15})
        self.assertAlmostEqual(z, 72000.0 * 0.9985, places=6)
        self.assertLess(z, 72000.0)
        self.assertGreater(z, 70000.0)

    def test_ziel_vor_wand_short_ueber_der_wand(self):
        z = h.ziel(self._d(74000.0, 72000.0), {"ziel_vor_wand_pct": 0.15})
        self.assertAlmostEqual(z, 72000.0 * 1.0015, places=6)
        self.assertGreater(z, 72000.0)
        self.assertLess(z, 74000.0)

    def test_ziel_vor_wand_null_ist_die_wand(self):
        self.assertEqual(h.ziel(self._d(70000.0, 72000.0),
                                {"ziel_vor_wand_pct": 0.0}), 72000.0)


class BodenTest(unittest.TestCase):
    """Der Zielabstands-Boden: nicht gegen die Gebuehr handeln.

    GEMESSEN am Journal 02.10.2026 (OKX-Spot 0,10 % je Seite = 0,20 % je
    Runde): 5 von 9 Runden mit 0,015 bis 0,051 % Zielabstand waren netto
    -0,13 bis -0,16 %, die 4 mit >= 0,43 % netto +4,36 %. Der Boden 0,30 %
    ist damit die Gebuehr selbst, nicht eine willkuerliche Huerde.

    Die Gegenprobe steht am Ende: mit `min_ziel_abstand_pct: 0` MUESSEN diese
    Faelle wieder ein Signal liefern - sonst prueft der Test seinen eigenen
    Aufbau statt der Regel.
    """

    W = {"max_abstand_pct": 5.0, "min_ziel_abstand_pct": 0.3}

    def _d(self, spot, wand):
        return {"spot": spot, "wand": {"strike": wand}}

    def test_zu_knapp_an_der_wand_kein_signal(self):
        # Spot 85987, Wand 86000: 0,015 % Abstand - unter der Gebuehrenschwelle.
        self.assertIsNone(h.signal(self._d(85987.0, 86000.0), self.W))

    def test_knapp_ueber_dem_boden_long(self):
        # 70000 -> 72000 ist 2,86 % Abstand, klar ueber dem Boden.
        self.assertEqual(h.signal(self._d(70000.0, 72000.0), self.W), "long")

    def test_boden_gleich_ist_kein_signal(self):
        # Genau auf dem Boden: nicht handeln. Der Vergleich ist streng (`boden < abstand`),
        # 0,30 % Abstand faellt also durch.
        wand, abstand = 72000.0, 0.30
        spot = wand / (1.0 + abstand / 100.0)
        self.assertIsNone(h.signal(self._d(spot, wand), self.W))

    def test_boden_gilt_fuer_beide_seiten(self):
        wand, abstand = 72000.0, 0.30
        spot = wand / (1.0 + abstand / 100.0)
        w = self.W
        self.assertIsNone(h.signal(self._d(spot, wand), w))
        # Und mit einem Boden knapp darunter kommt die Seite zurueck.
        w2 = dict(w, min_ziel_abstand_pct=0.29)
        self.assertEqual(h.signal(self._d(spot, wand), w2), "long")

    def test_gegenprobe_ohne_boden_wieder_signal(self):
        """Ohne den Boden waere derselbe Fall ein Signal - der Test kann rot."""
        ohne = {"max_abstand_pct": 5.0}
        self.assertEqual(h.signal(self._d(85987.0, 86000.0), ohne), "long")
        self.assertIsNone(h.signal(self._d(85987.0, 86000.0), self.W))

    def test_oberer_rand_unveraendert(self):
        # Zu weit weg bleibt draussen, mit und ohne Boden.
        spot = wand = 60000.0
        self.assertIsNone(h.signal(self._d(spot, 72000.0), self.W))
        self.assertIsNone(h.signal(self._d(spot, 72000.0), {"max_abstand_pct": 5.0}))


class BuchTest(unittest.TestCase):
    """Der Buchweg mit einem Marktziel - gegen einen Temp-Ordner."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (buch.SCHREIBEN, h.options_quelle, h.spot_quelle)
        buch.SCHREIBEN = True
        w = json.load(open(os.path.join(SPUR, "wachen.json"), encoding="utf-8"))
        w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")
        with open(os.path.join(self.tmp.name, "wachen.json"), "w",
                  encoding="utf-8") as f:
            json.dump(w, f)
        h.spot_quelle = lambda w_: 70000.0
        h.options_quelle = lambda w_: {
            "offen": _offen([("BTC-USD-261016-72000-C", "900000000")]),
            "uebersicht": _uebersicht([("BTC-USD-261016-72000-C", 0.42)])}

    def tearDown(self):
        buch.SCHREIBEN, h.options_quelle, h.spot_quelle = self.alt
        self.tmp.cleanup()

    def test_ziel_ist_der_wandstrike_nicht_das_vielfache(self):
        """Ziel = Wand, verschoben um `ziel_vor_wand_pct` aus der WACHEN.

        Bis 02.10.2026 stand hier `72000.0` fest - ein Stand, keine Regel.
        Mit dem Schiebetor waere der Test bei jeder Aenderung an der Wachen rot
        geworden, ohne dass sich etwas an der Regel geaendert haette. Jetzt
        wird der Erwartungswert aus derselben Wachen gelesen, die der Lauf
        benutzt - damit prueft der Test die Regel und nicht den Stand.

        Gegenprobe: die Rechnung unten ist unabhaengig von `h.ziel()`
        nachgebaut (Wand x (1 - 0,15 %)), faellt also bei einem Fehler in der
        Funktion um.
        """
        with open(os.path.join(self.tmp.name, "wachen.json"), encoding="utf-8") as f:
            w = json.load(f)
        erwartet = 72000.0 * (1.0 - float(w.get("ziel_vor_wand_pct", 0.0)) / 100.0)
        buch.zyklus(self.tmp.name, h.daten_holen, h.signal, "papier",
                    "test", ziel=h.ziel)
        with open(os.path.join(self.tmp.name, "zustand.json"), encoding="utf-8") as f:
            z = json.load(f)
        (p,) = z["positionen"]
        self.assertEqual(p["seite"], "long")
        self.assertAlmostEqual(p["ziel"], erwartet, places=6)
        self.assertAlmostEqual(p["einstieg"], 70000.0, places=6)
        # Das Ziel muss zwischen Einstieg und Wand liegen - sonst waere es kein
        # Ziel, sondern hinter dem Einstieg.
        self.assertLess(p["ziel"], 72000.0)
        self.assertGreater(p["ziel"], p["einstieg"])

    def test_vorschau_schreibt_nichts(self):
        buch.zyklus(self.tmp.name, h.daten_holen, h.signal, "vorschau",
                    "test", ziel=h.ziel)
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name,
                                                    "handelsjournal.csv")))

    def test_ziel_hinter_dem_einstieg_wird_abgelehnt(self):
        # Ein long mit Ziel UNTER dem Einstieg ist kein Handel.
        self.assertIsNone(buch.einstieg({"positionen": []}, "BTC-USDT", "long",
                                        70000.0, {"risiko_je_position_usd": 5.0,
                                                  "max_pro_trade_usd": 100.0,
                                                  "stop_prozent": 4.0,
                                                  "pflicht_stop_prozent_min": 3.0,
                                                  "pflicht_stop_prozent_max": 8.0},
                                        1.0, "test", ziel_preis=69000.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
