"""Tests fuer den LIVE-Orderweg von nautilus_kraken/handeln.py.

Kein Netz, keine echten Orders: kraken_rest, freigabefenster und sammle_quoten
sind Attrappen, Journal/Zustand/Wachen liegen im Temp-Ordner. Geprueft wird die
Sicherheitsregel, die ueber Buch und Boerse entscheidet:

  1. Eine PAPIER-Position im gemeinsamen Buch wird im Live-Lauf NICHT geordert.
     Sonst verkauft der erste echte Zyklus BTC, das nie gekauft wurde - genau
     dieser Fall ist bei scanner und xperp am 21./23.09.2026 eingetreten.
  2. Ein echter Kauf bekommt sofort seinen boersenseitigen Schutz-Stop.
  3. Ein gescheiterter Live-Auftrag hinterlaesst eine Journalzeile, nicht nur
     eine Konsolenzeile.
  4. Der Live-Lauf rechnet mit live_einsatz_eur, nicht mit dem Papier-Einsatz.
  5. Neue Positionen tragen ihren Buchmodus; Altbestand bleibt Papier.

Aufruf:  ../nautilus/.venv/Scripts/python.exe -m unittest test_live_orderweg
"""

import csv
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import handeln  # noqa: E402


class QuoteAttrappe:
    """Steht fuer einen Kraken-Quote-Tick (nur die Felder, die handeln liest)."""

    def __init__(self, bid=74000.0, ask=74001.0):
        self.bid_price = bid
        self.ask_price = ask
        self.ts_event = 0


class KrakenAttrappe:
    """Steht fuer kraken_rest: notiert jeden Aufruf, kann Fehler werfen."""

    def __init__(self, guthaben=100.0, fehler=None):
        self.aufrufe = []
        self._guthaben = guthaben
        self._fehler = fehler or {}

    def produkt(self):
        return "spot"

    def guthaben(self):
        return self._guthaben

    def markt_kauf(self, paar, menge, echt=False):
        self.aufrufe.append(("kauf", paar, menge, echt))
        if "kauf" in self._fehler:
            raise RuntimeError(self._fehler["kauf"])
        return "TX-KAUF"

    def markt_verkauf(self, paar, menge, echt=False):
        self.aufrufe.append(("verkauf", paar, menge, echt))
        if "verkauf" in self._fehler:
            raise RuntimeError(self._fehler["verkauf"])
        return "TX-VERKAUF"

    def stop_setzen(self, paar, menge, stop_preis, echt=False):
        self.aufrufe.append(("stop", paar, round(stop_preis, 4), echt))
        return "TX-STOP"


class LiveOrderwegTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hier = self.tmp.name
        self.wachen_pfad = os.path.join(self.hier, "wachen.json")
        self.zustand_pfad = os.path.join(self.hier, "zustand.json")
        self.journal_pfad = os.path.join(self.hier, "handelsjournal.csv")
        self.wachen = {
            "symbol": "BTC/EUR", "paar": "XXBTZEUR", "waehrung": "eur",
            "handel_erlaubt": True, "freigabe": {"erfuellt": True},
            "live_einsatz_eur": 1.0, "live_max_risiko_gesamt_eur": 20,
            "max_risiko_pro_trade": 50, "max_risiko_gesamt": 200,
            "max_offene_positionen": 4, "stop_pct": 19.8,
            "journal_zweitziel": "",
        }
        with open(self.wachen_pfad, "w", encoding="utf-8") as f:
            json.dump(self.wachen, f)
        self._schreibe_wachen = lambda: json.dump(
            self.wachen, open(self.wachen_pfad, "w", encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    # ------------------------------------------------------------ Hilfen
    def _zustand(self, positionen):
        with open(self.zustand_pfad, "w", encoding="utf-8") as f:
            json.dump({"positionen": positionen, "letzter_lauf": "2026-09-24T00:00:00Z"}, f)

    def _lauf(self, kraken, buchungen, positionen, quotes=None):
        """handeln.lauf('live') mit Attrappen; gibt (code, journalzeilen, zustand)."""
        with open(self.wachen_pfad, "w", encoding="utf-8") as f:
            json.dump(self.wachen, f)
        self._zustand(positionen)

        quotes = quotes if quotes is not None else (QuoteAttrappe(),)

        def quotes_attrappe(**kwargs):
            # Die echte Strategie gibt die Positionen mit zurueck - hier
            # entsteht eine neue Position je Eroeffnungs-Buchung.
            pos = list(kwargs.get("positionen") or [])
            for b in buchungen:
                if b["aktion"] != "schliessen":
                    pos.append({"token": b["token"], "symbol": b["symbol"],
                                "menge": b["menge"],
                                "einsatz_eur": b["einsatz_eur"],
                                "einstieg": b["kurs"]})
            return quotes, pos, buchungen

        with patch.object(handeln, "WACHEN", self.wachen_pfad), \
             patch.object(handeln, "ZUSTAND", self.zustand_pfad), \
             patch.object(handeln, "JOURNAL", self.journal_pfad), \
             patch.object(handeln, "kraken_rest", kraken), \
             patch.object(handeln, "sammle_quoten", quotes_attrappe), \
             patch.object(handeln, "lies_kopier_signale", lambda seit: []), \
             patch.object(handeln, "spiegle_journal",
                          lambda *a, **k: (True, "attrappe")), \
             patch("handeln.freigabefenster.lade") as lade:
            lade.return_value.offen.return_value = True
            code = handeln.lauf("live")
        zeilen = []
        if os.path.exists(self.journal_pfad):
            with open(self.journal_pfad, newline="", encoding="utf-8") as f:
                zeilen = list(csv.DictReader(f))
        zustand = {}
        if os.path.exists(self.zustand_pfad):
            with open(self.zustand_pfad, encoding="utf-8") as f:
                zustand = json.load(f)
        return code, zeilen, zustand

    # ------------------------------------------------------------ Faelle
    def test_papier_position_wird_nicht_echt_verkauft(self):
        kraken = KrakenAttrappe()
        buchungen = [{"aktion": "schliessen", "grund": "frist",
                      "symbol": "BTC/EUR", "token": "KOP:JUD",
                      "kurs": 70000.0, "menge": 0.0007,
                      "einsatz_eur": 1.0, "wert_eur": 1.2}]
        positionen = [{"token": "KOP:JUD", "symbol": "BTC/EUR",
                       "menge": 0.0007, "einsatz_eur": 1.0}]
        code, zeilen, zustand = self._lauf(kraken, buchungen, positionen)
        self.assertEqual(code, 0)
        self.assertEqual([a for a in kraken.aufrufe if a[0] == "verkauf"], [],
                         "eine Papier-Position darf NIE echt verkauft werden")
        self.assertTrue(any(z["aktion"] == "schliessen" and z["modus"] == "papier"
                            for z in zeilen), "der Papier-Ausstieg gehoert ins Journal")
        self.assertEqual(zustand["positionen"][0]["modus"], "papier")

    def test_echter_kauf_bekommt_seinen_stop(self):
        kraken = KrakenAttrappe()
        buchungen = [{"aktion": "eroeffnen", "grund": "signal",
                      "symbol": "BTC/EUR", "token": "KOP:NEU",
                      "kurs": 74000.0, "menge": 0.0000135,
                      "einsatz_eur": 1.0, "wert_eur": None}]
        code, zeilen, zustand = self._lauf(kraken, buchungen, [])
        self.assertEqual(code, 0)
        arten = [a[0] for a in kraken.aufrufe]
        self.assertEqual(arten, ["kauf", "stop"],
                         "auf den echten Kauf folgt der Schutz-Stop")
        stop = [a for a in kraken.aufrufe if a[0] == "stop"][0]
        self.assertAlmostEqual(stop[2], 74000.0 * (1 - 0.198), places=1)
        self.assertTrue(stop[3], "der Stop muss echt bestellt werden")
        self.assertTrue(any(z["aktion"] == "eroeffnen" and z["modus"] == "live"
                            for z in zeilen))
        self.assertEqual(zustand["positionen"][0]["modus"], "live")

    def test_gescheiterter_kauf_schreibt_eine_journalzeile(self):
        kraken = KrakenAttrappe(fehler={"kauf": "EOrder:Insufficient funds"})
        buchungen = [{"aktion": "eroeffnen", "grund": "signal",
                      "symbol": "BTC/EUR", "token": "KOP:NEU",
                      "kurs": 74000.0, "menge": 0.0000135,
                      "einsatz_eur": 1.0, "wert_eur": None}]
        code, zeilen, zustand = self._lauf(kraken, buchungen, [])
        self.assertEqual(code, 0)
        self.assertTrue(any(z["aktion"] == "fehler"
                            and z["grund"] == "order_gescheitert"
                            for z in zeilen),
                        "ein gescheiterter Live-Auftrag muss im Journal stehen")

    def test_live_rechnet_mit_dem_live_einsatz(self):
        # 1 EUR live, 50 EUR Papier: der Live-Lauf zieht max_risiko_pro_trade
        # auf live_einsatz_eur und den Gesamtdeckel auf den Live-Wert.
        lw = handeln.live_wachen(self.wachen)
        self.assertEqual(lw["max_risiko_pro_trade"], 1.0)
        self.assertEqual(lw["max_risiko_gesamt"], 20.0)
        self.assertEqual(self.wachen["max_risiko_pro_trade"], 50,
                         "die Papier-Wachen duerfen sich nicht aendern")

    def test_zu_kleines_guthaben_sperrt_vor_der_order(self):
        kraken = KrakenAttrappe(guthaben=0.5)
        buchungen = [{"aktion": "eroeffnen", "grund": "signal",
                      "symbol": "BTC/EUR", "token": "KOP:NEU",
                      "kurs": 74000.0, "menge": 0.0000135,
                      "einsatz_eur": 1.0, "wert_eur": None}]
        code, zeilen, zustand = self._lauf(kraken, buchungen, [])
        self.assertEqual(code, 0)
        self.assertEqual(kraken.aufrufe, [],
                         "ohne freies Guthaben darf keine Order rausgehen")
        self.assertEqual(zustand["modus"], "papier")


if __name__ == "__main__":
    unittest.main()