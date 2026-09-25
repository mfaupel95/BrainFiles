"""Die Grenzen der Futures-Spur muessen zum INSTRUMENT passen.

Befund 25.09.2026 (Auftrag Max, Symbolwechsel auf SOL): 1 Kontrakt ist EINE
Einheit der Basiswaehrung, Einschuss 10 % fuer ein EEA-Konto. PF_XBTUSD kostet
damit rund 8.450 USD Einschuss je Kontrakt - mit 141,59 USD frei war die Spur
gebaut, aber nie fahrbar (die Boerse lehnte selbst size 1 ab). PF_SOLUSD kostet
rund 11,75 USD.

Diese Datei prueft die zwei Dinge, die damals gefehlt haben:
  * Das Symbol in den Wachen passt zum Einschuss, den der Einsatz deckt.
  * Der Live-Einsatz wird auch unter dem USD-Namen gelesen (vorher nur _eur).

Kein Netz: der Margenplan kommt als Attrappe, das gemessene Zahlenverhaeltnis
steht als Kommentar.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import handeln                                     # noqa: E402
import kraken_futures as kf                        # noqa: E402

WACHEN_FUTURES = json.loads((HIER / "wachen.futures.json").read_text(encoding="utf-8"))

# Margenplan wie im echten Record (Europa/retail, 10 %) - gemessen am Konto:
# 1 Kontrakt PF_NEARUSD bei 4,5517 USD belegte 0,4548 USD Marge.
PLAN = {"marginSchedules": {"europa": {"retail": [
    {"numNonContractUnits": 0.0, "initialMargin": 0.1, "maintenanceMargin": 0.05}]}}}
KURSE = {"PF_XBTUSD": 84485.0, "PF_SOLUSD": 117.52, "PF_NEARUSD": 4.5517}


class GrenzenTest(unittest.TestCase):

    def test_wachen_handelt_sol(self):
        self.assertEqual(WACHEN_FUTURES["symbol"], "PF_SOLUSD")
        self.assertEqual(WACHEN_FUTURES["paar"], "PF_SOLUSD")
        self.assertEqual(WACHEN_FUTURES["produkt"], "futures")

    def test_live_wachen_liest_den_usd_namen(self):
        """Vorher las live_wachen nur live_einsatz_eur - der USD-Einsatz der
        Futures-Spur waere wirkungslos geblieben und der Papier-Einsatz 50 haette
        gegolten (menge 0,42 SOL -> aufgerundet 1 Kontrakt = 118 USD)."""
        w = {"waehrung": "usd", "max_risiko_pro_trade": 50, "max_risiko_gesamt": 200,
             "live_einsatz_usd": 118.0, "live_max_risiko_gesamt_usd": 25.0}
        lw = handeln.live_wachen(w)
        self.assertEqual(lw["max_risiko_pro_trade"], 118.0)
        self.assertEqual(lw["max_risiko_gesamt"], 25.0)
        self.assertEqual(w["max_risiko_pro_trade"], 50)      # Kopie, nicht in-place

    def test_live_wachen_liest_weiter_den_eur_namen(self):
        w = {"waehrung": "eur", "max_risiko_pro_trade": 50, "max_risiko_gesamt": 200,
             "live_einsatz_eur": 1.0, "live_max_risiko_gesamt_eur": 20}
        lw = handeln.live_wachen(w)
        self.assertEqual(lw["max_risiko_pro_trade"], 1.0)
        self.assertEqual(lw["max_risiko_gesamt"], 20)

    def test_einsatz_deckt_den_mindestkontrakt(self):
        """Die Regel, die den XBT-Fall gefunden haette."""
        symbol = WACHEN_FUTURES["paar"]
        einsatz = float(WACHEN_FUTURES["live_einsatz_usd"])
        with patch.object(kf, "instrument", return_value=PLAN), \
             patch.object(kf, "letzter_kurs", side_effect=lambda s: KURSE[s]):
            noetig = kf.einschuss(symbol, 1)
            self.assertLess(einsatz, 200.0)                  # kein Kontoblindflug
            self.assertGreaterEqual(einsatz, noetig,
                                    "Einsatz deckt 1 Kontrakt %s nicht" % symbol)
            # Gegenprobe: mit dem ALTEN Symbol (1 BTC je Kontrakt) faellt genau
            # diese Regel um - sie ist also nicht leer.
            alt = kf.einschuss("PF_XBTUSD", 1)
            self.assertGreater(alt, float(WACHEN_FUTURES["live_einsatz_usd"]))

    def test_kleinster_satz_wird_gesperrt_wenn_er_zu_gross_ist(self):
        """handelbar() nennt den Grund in Zahlen - die Sperre bleibt lesbar."""
        with patch.object(kf, "instrument", return_value=PLAN), \
             patch.object(kf, "letzter_kurs", side_effect=lambda s: KURSE[s]):
            grund = kf.handelbar("PF_XBTUSD", 1, frei=141.58)
            self.assertIn("8448.50", grund)
            self.assertIsNone(kf.handelbar("PF_SOLUSD", 1, frei=141.58))


if __name__ == "__main__":
    unittest.main(verbosity=2)