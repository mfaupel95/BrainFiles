"""Tests fuer nautilus_kraken/trailing_stop_strategie.py + handeln-Teile.

Kein Netz, keine Engine: Geprueft wird die reine Mathematik
(Stop/Trailing/Frist, Kosten, Waehrungsfelder) und die Verkabelung des
Zyklus (Kopier-Signale, Herzschlag-Fallback). Der echte Quotenpfad bleibt
test_quote_pfad.py; die Strategie-Klasse wird ueber on_quote_tick mit
einem Fake-Tick gefuettert, ohne Node.

Aufruf:  .venv\\Scripts\\python.exe -m unittest test_trailing_stop
"""

import csv
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import handeln

W = {
    "symbol": "BTC/EUR",
    "waehrung": "EUR",
    "max_risiko_pro_trade": 50.0,
    "max_offene_positionen": 4,
    "slippage_pct": 0.1,
    "gebuehr_pct": 0.0,
    "stop_pct": 19.8,
    "trail_aktiv_ab_pct": 30.0,
    "trail_abstand_pct": 25.0,
    "haltedauer_stunden": 168,
}


def position(**over):
    p = {"kette": "kraken", "token": "BTC/EUR", "symbol": "KOP:AAA",
         "quelle": "kopier", "quelle_token": "T1",
         "einsatz_eur": 50.0, "menge": 0.000645,
         "preis_einstieg": 70690.0, "letzter_kurs": 70690.0,
         "stop_preis": 70690.0 * 0.802, "trail_aktiv_ab_pct": 30.0,
         "trail_abstand_pct": 25.0, "hoechster_kurs": 70690.0,
         "frist": "2999-01-01T00:00:00+00:00", "eroeffnet": "2026-09-19"}
    p.update(over)
    return p


class Tick:
    def __init__(self, bid, ask):
        self.bid_price = bid
        self.ask_price = ask


class Waehrungsfelder(unittest.TestCase):
    def test_betrag_feld_eur_und_usd(self):
        from trailing_stop_strategie import betrag_feld
        self.assertEqual(betrag_feld({"waehrung": "EUR"}, "einsatz"),
                         "einsatz_eur")
        self.assertEqual(betrag_feld({"waehrung": "usd"}, "wert"),
                         "wert_usd")
        self.assertEqual(betrag_feld({}, "einsatz"), "einsatz_usd",
                         "Vorgabe USD, wenn waehrung fehlt")


class Mathematik(unittest.TestCase):
    def test_kauf_und_sofortiger_verkauf_verlieren_geld(self):
        mid = 100.0
        preis = handeln.trailing_stop_strategie.kaufpreis(mid, W)
        erloes = handeln.trailing_stop_strategie.verkaeuflich(
            1.0, preis, W)
        self.assertLess(erloes, mid, "Kosten wirken beim Kauf und Verkauf")
        # (1+slip)*(1-slip)*(1-geb) - rund 2*slip + geb.
        self.assertAlmostEqual(erloes, 100.0 * (1 + 0.001) * (1 - 0.001)
                               * (1 - 0.0), places=9)

    def test_stop_realisiert_max_20_prozent_verlust(self):
        """Am Stop-Preis raus: Einsatz 50, Erloes 40 (inkl. Kosten)."""
        preis = handeln.trailing_stop_strategie.kaufpreis(100.0, W)
        gebuehr = 50.0 * W["gebuehr_pct"] / 100.0
        menge = (50.0 - gebuehr) / preis
        p = position(preis_einstieg=preis, menge=menge,
                     stop_preis=handeln.trailing_stop_strategie
                     .stop_preis_fuer(preis, W))
        kurs = p["stop_preis"]
        erloes = handeln.trailing_stop_strategie.verkaeuflich(
            p["menge"], kurs, W)
        self.assertAlmostEqual(erloes / p["einsatz_eur"], 0.80, places=2)


class Ausstiege(unittest.TestCase):
    def test_stop_schliesst_sofort_unter_dem_preis(self):
        grund = handeln.trailing_stop_strategie.ausstiegsgrund(
            position(), 50000.0, datetime.now(timezone.utc), W)
        self.assertEqual(grund, "stop")

    def test_trailing_aktiv_und_nicht_aktiv(self):
        jetzt = datetime.now(timezone.utc)
        p = position(preis_einstieg=1.0, menge=1.0, hoechster_kurs=1.4,
                     letzter_kurs=1.0, stop_preis=0.7)
        grund = handeln.trailing_stop_strategie.ausstiegsgrund(
            p, 1.0, jetzt, W)
        self.assertEqual(grund, "trail")
        self.assertEqual(p["hoechster_kurs"], 1.4, "Peak bleibt")
        p = position(preis_einstieg=1.0, menge=1.0, hoechster_kurs=1.1,
                     letzter_kurs=1.0, stop_preis=0.7)
        grund = handeln.trailing_stop_strategie.ausstiegsgrund(
            p, 0.8, jetzt, W)
        self.assertIsNone(grund)

    def test_kein_fester_deckel(self):
        p = position(preis_einstieg=1.0, menge=1.0, hoechster_kurs=2.0,
                     letzter_kurs=2.0, stop_preis=0.7)
        grund = handeln.trailing_stop_strategie.ausstiegsgrund(
            p, 2.0, datetime.now(timezone.utc), W)
        self.assertIsNone(grund)

    def test_frist_ist_das_sicherheitsnetz(self):
        alt = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        p = position(frist=alt)
        grund = handeln.trailing_stop_strategie.ausstiegsgrund(
            p, p["preis_einstieg"], datetime.now(timezone.utc), W)
        self.assertEqual(grund, "frist")


class StrategieOhneNode(unittest.TestCase):
    """on_quote_tick direkt gefuettert - kein Node, kein Netz."""

    def _strategie(self, wachen=None, positionen=None, signale=None):
        from nautilus_trader.trading.config import StrategyConfig
        from trailing_stop_strategie import TrailingStopStrategie
        return TrailingStopStrategie(
            StrategyConfig(strategy_id="test-strategie"),
            wachen or W, positionen or [], signale or [], [])

    def test_frisches_signal_wird_papier_position(self):
        s = self._strategie(signale=[{"zeit": "x", "token": "T1",
                                      "symbol": "AAA"}])
        s.on_quote_tick(Tick(70690.0, 70710.0))
        self.assertEqual(len(s.positionen), 1)
        p = s.positionen[0]
        self.assertEqual(p["quelle"], "kopier")
        self.assertEqual(p["quelle_token"], "T1")
        self.assertEqual(p["symbol"], "KOP:AAA")
        self.assertEqual(p["token"], "BTC/EUR")
        self.assertAlmostEqual(p["preis_einstieg"], 70700.0 * 1.001,
                               places=3)
        self.assertAlmostEqual(p["einsatz_eur"], 50.0)
        self.assertEqual(len(s.buchungen), 1)
        self.assertEqual(s.buchungen[0]["aktion"], "eroeffnen")

    def test_max_offene_positionen_begrenzt_einstiege(self):
        voll = [position(token="BTC/EUR", symbol="KOP:B") for _ in range(4)]
        s = self._strategie(positionen=voll, signale=[
            {"zeit": "x", "token": "T5", "symbol": "E"}])
        s.on_quote_tick(Tick(70690.0, 70710.0))
        self.assertEqual(len(s.positionen), 4, "kein Einstieg bei vollem Buch")
        self.assertEqual(len(s.signale), 1,
                         "Kapazitaetsfall bleibt unregistriert")

    def test_ausstieg_bucht_ins_journal(self):
        menge = (50.0 - 50.0 * W["gebuehr_pct"] / 100.0) / 1.0
        p = position(preis_einstieg=1.0, menge=menge, hoechster_kurs=1.4,
                     letzter_kurs=1.0, stop_preis=0.7, einsatz_eur=50.0)
        s = self._strategie(positionen=[p])
        s.on_quote_tick(Tick(0.95, 0.95))
        self.assertEqual(s.positionen, [])
        self.assertEqual(len(s.buchungen), 1)
        b = s.buchungen[0]
        self.assertEqual(b["aktion"], "schliessen")
        self.assertEqual(b["grund"], "trail")
        self.assertAlmostEqual(
            b["wert_eur"] / 50.0,
            (menge / 50.0) * 0.95 * (1 - 0.001) * (1 - 0.0), places=6)

    def test_hoechster_kurs_wird_fortgeschrieben(self):
        p = position(preis_einstieg=1.0, menge=1.0, hoechster_kurs=1.0,
                     letzter_kurs=1.0, stop_preis=0.7)
        s = self._strategie(positionen=[p])
        s.on_quote_tick(Tick(1.2, 1.2))
        self.assertEqual(p["hoechster_kurs"], 1.2)
        self.assertEqual(len(s.positionen), 1)


class SignaleUndFallback(unittest.TestCase):
    def test_lies_kopier_signale_nur_neuere(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = os.path.join(tmp, "handelsjournal.csv")
            with open(j, "w", newline="", encoding="utf-8") as f:
                s = csv.DictWriter(f, fieldnames=["zeit", "aktion", "token",
                                                  "symbol"])
                s.writeheader()
                s.writerow({"zeit": "2026-09-19T10:00:00+00:00",
                            "aktion": "eroeffnen", "token": "A", "symbol": "A1"})
                s.writerow({"zeit": "2026-09-19T11:00:00+00:00",
                            "aktion": "schliessen", "token": "B", "symbol": "B1"})
                s.writerow({"zeit": "2026-09-19T12:00:00+00:00",
                            "aktion": "eroeffnen", "token": "C", "symbol": "C1"})
            handeln.KOPIER_JOURNAL = j
            signale = handeln.lies_kopier_signale("2026-09-19T11:30:00+00:00")
            self.assertEqual([s["token"] for s in signale], ["C"])
            signale = handeln.lies_kopier_signale("")
            self.assertEqual(signale, [])
            signale = handeln.lies_kopier_signale("2026-09-19T13:00:00+00:00")
            self.assertEqual(signale, [])

    def test_lies_kopier_signale_ohne_datei(self):
        handeln.KOPIER_JOURNAL = "Z:/gibt-es-nicht/kopier/handelsjournal.csv"
        self.assertEqual(handeln.lies_kopier_signale("2026-09-19"), [])

    def test_kopier_frisch_ja_und_nein(self):
        with tempfile.TemporaryDirectory() as tmp:
            z = os.path.join(tmp, "zustand.json")
            handeln.KOPIER_ZUSTAND = z
            self.assertFalse(handeln.kopier_frisch())
            with open(z, "w", encoding="utf-8") as f:
                json.dump({"letzter_lauf":
                           datetime.now(timezone.utc).isoformat()}, f)
            self.assertTrue(handeln.kopier_frisch())
            alt = (datetime.now(timezone.utc) - timedelta(minutes=40))
            with open(z, "w", encoding="utf-8") as f:
                json.dump({"letzter_lauf": alt.isoformat()}, f)
            self.assertFalse(handeln.kopier_frisch())


if __name__ == "__main__":
    unittest.main()
