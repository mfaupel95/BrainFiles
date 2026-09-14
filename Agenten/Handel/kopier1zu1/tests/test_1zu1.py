"""Tests fuer die 1:1-Copy-Trade-Spur.

Kernpfade ohne Netz:
- _kopie_aus_trade rechnet Kaufpreis/Menge korrekt
- pruefe_verkaeufe schliesst Position bei Verkauf nach Einstieg
- Stop in USD greift bei realisiertem Verlust >= stop_usd
- Trailing-Stop nur nach Aktivierung
"""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
KOPIER = os.path.join(SPUR, os.pardir, "kopier")
sys.path.insert(0, SPUR)
sys.path.insert(0, KOPIER)

import handeln                                                    # noqa: E402


WACHEN = {
    "waehrung": "USD", "ketten": ["solana"],
    "max_einsatz_je_kauf_usd": 30,
    "max_offen": 30, "max_offen_papier": 100,
    "max_neu_je_zyklus": 15, "max_kaeufe_je_token": 3,
    "kill_switch_gesamt_usd": 100,
    "kill_switch_gesamt_usd_papier": 300,
    "slippage_pct": 5.0, "gebuehr_pct": 1.0,
    "stop_usd": 10.0,
    "trail_aktiv_ab_pct": 30.0, "trail_abstand_pct": 25.0,
    "haltedauer_stunden": 168,
    "max_alter_trade_sekunden": 900,
    "max_trader_je_zyklus": 10,
    "marketcap_band_usd": [50000, 1000000],
    "herzschlag_max_minuten": 180,
}


def _sig(wallet="W", token="T", preis=1.0, mk=300000):
    return {"kette": "solana", "wallet": wallet, "wallet_name": "trader",
            "token": token, "symbol": "SYM", "marktkap_usd": mk}


def _trade(preis=1.0, ms=None, tx="tx1", typ="buy"):
    return {"tx": tx, "typ": typ,
            "zeit_ms": ms if ms is not None
                       else int(datetime.now(timezone.utc).timestamp() * 1000),
            "preis": preis, "betrag_usd": 50, "bonding_curve": False}


class KopieAusTradeTest(unittest.TestCase):

    def test_kaufpreis_und_menge(self):
        w = dict(WACHEN)
        kop = handeln._kopie_aus_trade(_sig(), _trade(preis=1.0), w)
        # kaufpreis = 1.0 * (1 + 5%) = 1.05
        self.assertAlmostEqual(kop["preis_einstieg"], 1.05, places=4)
        # menge = (30 - 30*1%) / 1.05
        self.assertAlmostEqual(kop["menge"], (30 - 0.3) / 1.05, places=4)
        self.assertEqual(kop["stop_usd"], 10.0)
        self.assertEqual(kop["hoechster_kurs"], 1.05)


class VerkaufsAusstiegTest(unittest.TestCase):

    def test_verkauf_nach_einstieg_schliesst(self):
        w = dict(WACHEN)
        einstieg_ms = int((datetime.now(timezone.utc) - timedelta(
            minutes=5)).timestamp() * 1000)
        kop = handeln._kopie_aus_trade(_sig(), _trade(preis=1.0,
                                                     ms=einstieg_ms),
                                       w)
        kop["letzter_kurs"] = 1.2  # Portfolio-Snapshot
        z = {"positionen": [kop], "gesehene_tx": {}, "gesehen_bis_ms": {}}
        verkauf_ms = einstieg_ms + 60_000
        trades = {("W", "T"): {"wallet": "W", "wallet_name": "trader",
                                "token": "T", "symbol": "SYM",
                                "kette": "solana",
                                "marktkap_usd": 300000, "preis_jetzt": 1.2,
                                "trades": [_trade(preis=1.2, ms=verkauf_ms,
                                                  tx="verk", typ="sell")]}}
        handeln.SCHREIBEN = False
        handeln.pruefe_verkaeufe(z, trades, w)
        self.assertEqual(z["positionen"], [])

    def test_verkauf_vor_einstieg_ignoriert(self):
        w = dict(WACHEN)
        einstieg_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        kop = handeln._kopie_aus_trade(_sig(),
                                       _trade(preis=1.0, ms=einstieg_ms), w)
        kop["letzter_kurs"] = 1.2
        z = {"positionen": [kop], "gesehene_tx": {}, "gesehen_bis_ms": {}}
        verkauf_ms = einstieg_ms - 60_000                     # vor Einstieg
        trades = {("W", "T"): {"trades": [_trade(preis=1.2, ms=verkauf_ms,
                                                  typ="sell")],
                                "preis_jetzt": 1.2}}
        handeln.SCHREIBEN = False
        handeln.pruefe_verkaeufe(z, trades, w)
        self.assertEqual(len(z["positionen"]), 1)


class StopUsdTest(unittest.TestCase):

    def test_stop_bei_realisiertem_verlust(self):
        w = dict(WACHEN)
        kop = handeln._kopie_aus_trade(_sig(), _trade(preis=1.0), w)
        # Bei Einsatz 30, stop_usd 10: Kurs muss so tief fallen,
        # dass Verlust >= 10 USD. erloes = menge * kurs * 0.95 * 0.99
        # Grenzkurs: (30 - 10) / (menge * 0.95 * 0.99)
        grenz_kurs = 20 / (kop["menge"] * 0.95 * 0.99)
        # knapp darueber: kein Stop
        self.assertIsNone(handeln._ausstiegsgrund(
            kop, grenz_kurs + 0.01, datetime.now(timezone.utc), w))
        # knapp darunter: Stop
        self.assertEqual("stop", handeln._ausstiegsgrund(
            kop, grenz_kurs - 0.01, datetime.now(timezone.utc), w))


class TrailingTest(unittest.TestCase):

    def test_trailing_erst_nach_aktivierung(self):
        w = dict(WACHEN)
        kop = handeln._kopie_aus_trade(_sig(), _trade(preis=1.0), w)
        # +10%: unter Aktivierungsschwelle 30% -> kein Trail
        self.assertIsNone(handeln._ausstiegsgrund(
            kop, kop["preis_einstieg"] * 1.10,
            datetime.now(timezone.utc), w))
        # +40%: aktiviert; hoechster_kurs = 1.05 * 1.40 = 1.47
        self.assertIsNone(handeln._ausstiegsgrund(
            kop, kop["preis_einstieg"] * 1.40,
            datetime.now(timezone.utc), w))
        # Rueckfall auf -30% vom hoechsten -> Trail zieht (Abstand 25%)
        peak = kop["hoechster_kurs"]
        self.assertEqual("trail", handeln._ausstiegsgrund(
            kop, peak * 0.70, datetime.now(timezone.utc), w))


class VorpruefungTest(unittest.TestCase):

    def test_kette_falsch(self):
        z = {"positionen": []}
        sig = _sig(); sig["kette"] = "evm"
        self.assertEqual("kette nicht unterstuetzt",
                         handeln._vorpruefung(sig, WACHEN, z))

    def test_marktkap_ausserhalb(self):
        z = {"positionen": []}
        sig = _sig(); sig["marktkap_usd"] = 5_000_000
        self.assertEqual("marktkap ausserhalb",
                         handeln._vorpruefung(sig, WACHEN, z))

    def test_token_belegt(self):
        z = {"positionen": [{"token": "T"}, {"token": "T"}, {"token": "T"}]}
        self.assertEqual("token belegt",
                         handeln._vorpruefung(_sig(), WACHEN, z))


class UmfangTest(unittest.TestCase):

    def test_papier_umfang_greift(self):
        w2 = handeln._umfang(WACHEN, "papier")
        self.assertEqual(w2["max_offen"], WACHEN["max_offen_papier"])
        self.assertEqual(w2["kill_switch_gesamt_usd"],
                         WACHEN["kill_switch_gesamt_usd_papier"])

    def test_live_umfang_nimmt_muster(self):
        w2 = handeln._umfang(WACHEN, "live")
        self.assertEqual(w2["max_offen"], WACHEN["max_offen"])


if __name__ == "__main__":
    unittest.main()
