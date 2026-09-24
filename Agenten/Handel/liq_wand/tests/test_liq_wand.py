"""Tests fuer die Liquidations-Wand-Spur (liq_wand).

Geprueft wird die REGEL mit erfundenen, aber realistisch geformten Daten -
ohne Netz. Die echte Messung vom 21.09.2026 (100 Eintraege, 78 Minuten,
71 Short- gegen 29 Long-Liquidationen, groesstes Band 0,75 % ueber dem Spot)
steht im Modulkopf der Spur und ist hier als Fixture nachgebaut.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parents[0]
for p in (HANDEL / "scanner", HANDEL, SPUR):
    if str(p) in sys.path:
        sys.path.remove(str(p))
    sys.path.insert(0, str(p))

import handeln as h                                                 # noqa: E402

assert str(Path(h.__file__).resolve()).startswith(str(SPUR)), h.__file__

W = json.loads((SPUR / "wachen.json").read_text(encoding="utf-8"))
SPOT = 86695.0


def _liq(preis, kontrakte, seite):
    return {"preis": preis, "kontrakte": kontrakte, "seite": seite,
            "ts": 1790027095733, "inst": "BTC-USDT-SWAP"}


def _cluster(preis, seite, masse=4800.0, stueck=30):
    """Ein dichter Cluster plus etwas Streuung ringsum."""
    raus = [_liq(preis, masse / stueck, seite) for _ in range(stueck)]
    raus += [_liq(SPOT * (1 + i * 0.001), 2.0, "long") for i in range(-5, 6)]
    return raus


class Wandfindung(unittest.TestCase):
    def test_groesstes_band_wird_gefunden(self):
        liqs = _cluster(SPOT * 1.0075, "short")
        preis, menge, seite = h.wand(liqs, SPOT, 0.25)
        self.assertAlmostEqual(preis, SPOT * 1.0075, delta=SPOT * 0.003)
        self.assertGreater(menge, 4000)
        self.assertEqual(seite, "short")

    def test_ohne_daten_keine_wand(self):
        self.assertIsNone(h.wand([], SPOT, 0.25))
        self.assertIsNone(h.wand([_liq(0, 0, "short")], SPOT, 0.25))

    def test_ohne_spot_keine_wand(self):
        self.assertIsNone(h.wand(_cluster(SPOT, "short"), 0, 0.25))

    def test_kaputte_werte_kippen_nicht(self):
        liqs = [{"preis": "x", "kontrakte": None, "seite": "short"}]
        liqs += _cluster(SPOT * 1.005, "short")
        self.assertIsNotNone(h.wand(liqs, SPOT, 0.25))


class Signal(unittest.TestCase):
    """Die Richtungsregel: der Cluster beschleunigt, er bremst nicht."""

    def test_shorts_liquidiert_ueber_dem_spot_ergibt_long(self):
        d = {"spot": SPOT, "liqs": _cluster(SPOT * 1.0075, "short")}
        self.assertEqual(h.signal(d, W), "long")

    def test_longs_liquidiert_unter_dem_spot_ergibt_short(self):
        d = {"spot": SPOT, "liqs": _cluster(SPOT * 0.9925, "long")}
        self.assertEqual(h.signal(d, W), "short")

    def test_shorts_liquidiert_unter_dem_spot_ergibt_nichts(self):
        # Kaufdruck ein Prozent unter dem Markt ist zu weit hinter dem Kurs -
        # die Toleranz (0,5 %) deckt das nicht ab.
        d = {"spot": SPOT, "liqs": _cluster(SPOT * 0.99, "short")}
        self.assertIsNone(h.signal(d, W))

    def test_longs_liquidiert_knapp_ueber_dem_spot_ergibt_short(self):
        # DER gemessene Fall (24.09.2026): das groesste Band lag 0,25 % ueber
        # dem Spot und bestand ganz aus liquidierten Longs - Verkaufsdruck, der
        # gerade durch das Band gelaufen ist. Die Wand sitzt knapp HINTER dem
        # Kurs; mit Toleranz ist das ein Short, ohne sie blieb die Spur stumm.
        d = {"spot": SPOT, "liqs": _cluster(SPOT * 1.0025, "long")}
        self.assertEqual(h.signal(d, W), "short")

    def test_shorts_liquidiert_knapp_unter_dem_spot_ergibt_long(self):
        # Die Spiegelform: Kaufdruck, der eben nach oben durchgelaufen ist.
        d = {"spot": SPOT, "liqs": _cluster(SPOT * 0.9975, "short")}
        self.assertEqual(h.signal(d, W), "long")

    def test_longs_liquidiert_weit_ueber_dem_spot_ergibt_nichts(self):
        # Zwei Prozent hinter dem Kurs ist keine Beschleunigung mehr.
        d = {"spot": SPOT, "liqs": _cluster(SPOT * 1.02, "long")}
        self.assertIsNone(h.signal(d, W))

    def test_toleranz_null_stellt_die_strenge_fassung_wieder_her(self):
        # Das Feld ist ein Schalter, kein fest verdrahteter Wert: mit 0 gilt
        # wieder "Wand muss vor dem Kurs liegen".
        streng = dict(W, hinter_dem_spot_prozent=0)
        d = {"spot": SPOT, "liqs": _cluster(SPOT * 1.0025, "long")}
        self.assertIsNone(h.signal(d, streng))
        self.assertEqual(h.signal(d, W), "short")

    def test_zu_weit_entfernte_wand_ergibt_nichts(self):
        d = {"spot": SPOT, "liqs": _cluster(SPOT * 1.05, "short")}
        self.assertIsNone(h.signal(d, W))

    def test_verstreute_liquidationen_ergeben_nichts(self):
        # Gleichverteilt ueber viele Baender: kein Band traegt 30 %.
        liqs = [_liq(SPOT * (1 + i * 0.002), 10.0, "short")
                for i in range(-25, 26)]
        self.assertIsNone(h.signal(d={"spot": SPOT, "liqs": liqs}, w=W))

    def test_zu_wenige_liquidationen_ergeben_nichts(self):
        d = {"spot": SPOT, "liqs": [_liq(SPOT * 1.005, 500.0, "short")] * 3}
        self.assertIsNone(h.signal(d, W))

    def test_leere_daten_ergeben_nichts(self):
        self.assertIsNone(h.signal({}, W))
        self.assertIsNone(h.signal({"spot": 0, "liqs": []}, W))


class Ziel(unittest.TestCase):
    def test_ziel_ist_die_wand(self):
        d = {"spot": SPOT, "liqs": _cluster(SPOT * 1.0075, "short")}
        linie = h.ziel(d, W)
        self.assertAlmostEqual(linie, SPOT * 1.0075, delta=SPOT * 0.003)

    def test_ohne_wand_kein_ziel(self):
        self.assertIsNone(h.ziel({"spot": SPOT, "liqs": []}, W))


class Wachen(unittest.TestCase):
    def test_live_wird_trotz_schalter_zu_papier(self):
        # Seit dem Auftrag Max vom 21./22.09.2026 stehen handel_erlaubt UND
        # freigabe.erfuellt in ALLEN Spuren auf true - ein Test auf den Schalter
        # meldete hier eine Aenderung, keinen Fehler. Was zaehlt: liq_wand hat
        # keinen Orderaufruf, deshalb muss '--live' IMMER zu Papier werden.
        modus, meldung = h.live_gate("live")
        self.assertEqual(modus, "papier")
        self.assertIn("keinen Orderaufruf", meldung)
        self.assertFalse(h.LIVE_ORDERWEG)

    def test_papier_und_vorschau_bleiben_unberuehrt(self):
        for m in ("papier", "vorschau", "wachen"):
            self.assertEqual(h.live_gate(m), (m, None))

    def test_ratschenbetrag_ist_das_buchrisiko(self):
        self.assertEqual(W["drawdown_halbierung_usd"],
                         W["risiko_je_position_usd"] * W["max_offene_positionen"])

    def test_stop_liegt_zwischen_den_pflichtgrenzen(self):
        self.assertLessEqual(W["pflicht_stop_prozent_min"], W["stop_prozent"])
        self.assertLessEqual(W["stop_prozent"], W["pflicht_stop_prozent_max"])

    def test_zweitziel_zeigt_auf_q(self):
        self.assertTrue(W["journal_zweitziel"].startswith("Q:"))

    def test_gebuehr_ist_gesetzt(self):
        # OKX-Swap ist nicht gebuehrfrei - eine 0 waere hier geschoent.
        self.assertGreater(W["gebuehr_taker"], 0)


class KeinSchreiben(unittest.TestCase):
    def test_reine_funktionen_beruehren_keine_dateien(self):
        vorher = {p.name for p in SPUR.iterdir()}
        d = {"spot": SPOT, "liqs": _cluster(SPOT * 1.0075, "short")}
        h.signal(d, W)
        h.ziel(d, W)
        self.assertEqual(vorher, {p.name for p in SPUR.iterdir()})


if __name__ == "__main__":
    unittest.main()
