"""Tests fuer carry.py - ohne Netz, mit URL-Attrappe.

carry.py ist ein rein lesender Scanner (kein Buch, kein Journal, kein
Orderweg). Diese Suite belegt:

  * die Basis-Rechnung (Perp-Mid gegen Spot-Mid derselben Boerse, in bp),
  * die Funding-Annualisierung: OKX 3 Zyklen/Tag (Doku + messbar), Kraken
    NUR als relative Rate je Zyklus - Kraken nennt kein Intervall, eine
    Jahreszahl waere geraten und darf im Code nicht auftauchen,
  * die OI-Rechnung: openInterest von Kraken-Futures ist in KONTRakten,
    duenn heisst USD < Schwelle (Kontrakte x Preis),
  * das Kosten-Urteil: positive Basis minus Rundenkosten (2 Einstiege +
    2 Ausstiege) > 0 - nur dann steht 'positiv' in der Zeile,
  * Extrem-Funding und duenne Maerkte werden als Markt-Falle markiert,
  * sammeln() faengt tote Abrufe ab statt den Lauf zu werfen.
"""

import json
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import carry  # noqa: E402


def _fake_get_json(zuordnung):
    """URL-Attrappe: {teilstring: antwort-dict} - der laengste Treffer gewinnt."""
    def get(url):
        treffer = [(len(t), a) for t, a in zuordnung.items() if t in url]
        if not treffer:
            raise RuntimeError("unbekannte URL: %s" % url)
        _, antwort = max(treffer)
        return antwort
    return get


OKX_TICKER = {"data": [{"last": "100.0", "bidPx": "99.9", "askPx": "100.1"}]}
OKX_FUNDING = {"data": [{"fundingRate": "0.0001"}]}  # 0,01 % je 8h

KRAKEN_FUTURES = {"tickers": [{
    "symbol": "PF_XBTUSD", "last": 100.0, "bid": 99.95, "ask": 100.05,
    "indexPrice": 99.9, "relativeFundingRate": 0.0001, "openInterest": 25000.0,
}]}
KRAKEN_SPOT = {"result": {"XBTUSDT": {"c": ["99.8"], "b": ["99.7"],
                                      "a": ["99.9"]}}}


class BasisUndFundingTest(unittest.TestCase):

    def test_basis_okx(self):
        daten = {"_fehler": [],
                 "BTC": {"okx_spot": {"last": 100.0, "bid": 99.9, "ask": 100.1},
                         "okx_perp": {"last": 101.0, "bid": 100.9,
                                      "ask": 101.1, "funding": 0.0}}}
        zeilen, _ = carry.auswerten(daten)
        z = zeilen[0]
        # Mid-Perp 101,0 gegen Mid-Spot 100,0 -> +100 bp
        self.assertAlmostEqual(z["okx_basis_bp"], 100.0, places=4)
        self.assertEqual(z["kraken_basis_bp"], None)

    def test_okx_funding_annualisiert(self):
        daten = {"_fehler": [],
                 "BTC": {"okx_spot": {"last": 100.0, "bid": 99.9, "ask": 100.1},
                         "okx_perp": {"last": 100.0, "bid": 99.9,
                                      "ask": 100.1, "funding": 0.0001}}}
        zeilen, _ = carry.auswerten(daten)
        # 0,0001 x 3 Zyklen x 365 Tage x 100 = 10,95 % p.a.
        self.assertAlmostEqual(zeilen[0]["okx_funding_pa"], 10.95, places=4)

    def test_kraken_funding_nur_je_zyklus(self):
        """Kraken nennt kein Funding-Intervall - im Ergebnis darf keine
        Jahreszahl stehen, nur die relative Rate je Zyklus in Prozent."""
        daten = {"_fehler": [],
                 "BTC": {"kraken_futures": {"funding_rel": 0.0001}}}
        zeilen, _ = carry.auswerten(daten)
        self.assertAlmostEqual(zeilen[0]["kraken_funding_rel"], 0.01, places=6)
        self.assertEqual(zeilen[0]["okx_funding_pa"], None)

    def test_kraken_oi_in_usd(self):
        """openInterest ist in Kontrakten - 25000 x 100 USD = 2,5 Mio USD."""
        daten = {"_fehler": [],
                 "BTC": {"kraken_futures": {"oi": 25000.0, "last": 100.0,
                                            "funding_rel": 0.0}}}
        zeilen, _ = carry.auswerten(daten)
        self.assertEqual(zeilen[0]["oi_usd"], 2500000.0)
        self.assertFalse(zeilen[0]["duenn"])

    def test_kraken_oi_duenn(self):
        daten = {"_fehler": [],
                 "BTC": {"kraken_futures": {"oi": 5000.0, "last": 100.0,
                                            "funding_rel": 0.0}}}
        zeilen, _ = carry.auswerten(daten)
        self.assertTrue(zeilen[0]["duenn"])
        self.assertIn("Markt-Falle", zeilen[0]["urteil"])

    def test_extrem_funding_ist_falle(self):
        daten = {"_fehler": [],
                 "BTC": {"okx_spot": {"last": 100.0, "bid": 99.9, "ask": 100.1},
                         "okx_perp": {"last": 101.0, "bid": 100.9,
                                      "ask": 101.1,
                                      "funding": 0.01}}}  # 1 % je 8h = extrem
        zeilen, _ = carry.auswerten(daten)
        self.assertTrue(zeilen[0]["extrem"])
        self.assertIn("Markt-Falle", zeilen[0]["urteil"])


class KostenUrteilTest(unittest.TestCase):

    def _zeile_mit_basis(self, okx_basis_pct=0.05):
        """okx_basis_pct = Perp-Ueberhang gegen Spot in Prozent."""
        spot_last = 100.0
        perp_last = spot_last * (1 + okx_basis_pct / 100)
        daten = {"_fehler": [],
                 "BTC": {"okx_spot": {"last": spot_last, "bid": spot_last,
                                      "ask": spot_last},
                         "okx_perp": {"last": perp_last, "bid": perp_last,
                                      "ask": perp_last, "funding": 0.0}}}
        zeilen, _ = carry.auswerten(daten)
        return zeilen[0]

    def test_kleine_basis_deckt_nicht(self):
        z = self._zeile_mit_basis(0.05)  # 5 bp
        # Rundenkosten OKX: (0,10 % + 0,05 %) x 2 x 10000 = 30 bp
        self.assertAlmostEqual(z["netto_bp"], 5.0 - 30.0, places=4)
        self.assertIn("deckt", z["urteil"])

    def test_grosse_basis_positiv(self):
        z = self._zeile_mit_basis(1.0)  # 100 bp
        self.assertGreater(z["netto_bp"], 0)
        self.assertIn("positiv", z["urteil"])

    def test_kraken_kosten_hoeher(self):
        """Kraken-Runde kostet (0,60 + 0,05) x 2 x 10000 = 130 bp."""
        daten = {"_fehler": [],
                 "BTC": {"kraken_spot": {"last": 100.0, "bid": 100.0,
                                         "ask": 100.0},
                         "kraken_futures": {"last": 100.6, "bid": 100.6,
                                            "ask": 100.6, "oi": 1e9,
                                            "funding_rel": 0.0}}}
        zeilen, _ = carry.auswerten(daten)
        z = zeilen[0]
        self.assertAlmostEqual(z["kraken_basis_bp"], 60.0, places=4)
        self.assertAlmostEqual(z["netto_bp"], 60.0 - 130.0, places=4)

    def test_ein_fehlender_markt_ist_kein_fehler(self):
        daten = {"_fehler": [],
                 "BTC": {"okx_spot": {"last": 100.0, "bid": 99.9, "ask": 100.1}}}
        zeilen, fehler = carry.auswerten(daten)
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0]["urteil"], "-")


class SammelnTest(unittest.TestCase):

    def _attrappe(self):
        zu = {}
        for inst in ("BTC-USDT", "BTC-USDT-SWAP", "ETH-USDT",
                     "ETH-USDT-SWAP", "SOL-USDT", "SOL-USDT-SWAP"):
            zu["/api/v5/market/ticker?instId=" + inst] = OKX_TICKER
        for inst in ("BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"):
            zu["/api/v5/public/funding-rate?instId=" + inst] = OKX_FUNDING
        zu["/derivatives/api/v3/tickers"] = KRAKEN_FUTURES
        zu["/0/public/Ticker?pair=XBTUSDT,ETHUSDT,SOLUSDT"] = KRAKEN_SPOT
        return _fake_get_json(zu)

    def test_sammeln_baue_struktur(self):
        d = carry.sammeln(get_json=self._attrappe())
        self.assertIn("BTC", d)
        btc = d["BTC"]
        self.assertIn("okx_spot", btc)
        self.assertIn("okx_perp", btc)
        self.assertEqual(btc["okx_perp"]["funding"], 0.0001)
        self.assertIn("kraken_futures", btc)
        self.assertIn("kraken_spot", btc)
        self.assertEqual(d["_fehler"], [])

    def test_toter_abruf_wird_abgefangen(self):
        def kaputt(url):
            raise RuntimeError("netz weg")
        d = carry.sammeln(get_json=kaputt)
        self.assertIn("_fehler", d)
        self.assertTrue(any("netz weg" in f for f in d["_fehler"]))
        # und der Lauf liefert trotzdem das Grundgeruest
        self.assertIn("BTC", d)

    def test_einzelner_markt_fehlt(self):
        ticker_ohne_btc = {"data": []} if False else None
        # ATTENTION: BTC-Ticker-Abruf bricht ab -> Fehler, kein Crash
        def teilweise(url):
            if "funding-rate" in url:
                return OKX_FUNDING
            raise RuntimeError("unbekannt: " + url)
        d = carry.sammeln(get_json=teilweise)
        self.assertGreaterEqual(len(d["_fehler"]), 1)


class AusgabeTest(unittest.TestCase):

    def test_zeilen_text_laueft_ohne_daten(self):
        t = carry.zeilen_text([], [])
        self.assertIn("Gebuehren", t)

    def test_zeilen_text_mit_fehler(self):
        t = carry.zeilen_text([], ["okx_spot_BTC-USDT: kaputt"])
        self.assertIn("kaputt", t)

    def test_json_ausgabe(self):
        daten = {"_fehler": [],
                 "BTC": {"okx_spot": {"last": 100.0, "bid": 99.9, "ask": 100.1}}}
        zeilen, _ = carry.auswerten(daten)
        aus = json.dumps({"zeilen": zeilen}, default=str)
        self.assertIn("BTC", aus)


if __name__ == "__main__":
    unittest.main()
