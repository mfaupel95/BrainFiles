"""Tests fuer kopier.py - das Papierbuch, ohne Netz, ohne Schreibzugriff.

Geprueft werden die Stellen, an denen ein Fehler Geld kosten wuerde: die
Kostenrechnung (Slippage und Gebuehr zweimal), die Tore vor dem Kauf (Kette,
Marktkapitalisierung, Doppelkopie, Alter des Signals, Risikostufe), die
Ausstiege (Vorbild ausgestiegen, Stop, Ziel, Frist, Kill-Switch, Herzschlag)
und die Registrierung des gesehenen Bestands (Einlauf, kein doppeltes
Signalfeuer). Dazu die zwei Sicherheitsnetze: der Schreibschutz in lesen.py
und der Verweigerungstext, den der Dauerlauf liest.

Aufruf:  python -m unittest discover -s tests   (im Ordner kopier/)
"""

import contextlib
import csv
import io
import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.abspath(__file__))
KOPIER = os.path.dirname(HIER)
if KOPIER not in sys.path:
    sys.path.insert(0, KOPIER)

import kopier as kp                                            # noqa: E402

WACHEN_ROH = json.load(io.open(os.path.join(KOPIER, "wachen.json"),
                               encoding="utf-8"))

MINT_FRISCH = str(int(time.time() * 1000))


def position(**over):
    p = {"kette": "solana", "wallet": "W1", "wallet_name": "AAA",
         "token": "T1", "symbol": "AAA", "quelle": "portfolio/AAA",
         "einsatz_usd": 50.0, "menge": 46.643688217324156,
         "preis_vorbild": 1.0, "preis_einstieg": 1.05,
         "marktkap_usd": 500000.0, "risiko": "ok",
         "stop_preis": 1.05 * 0.85,
         "trail_aktiv_ab_pct": 30.0, "trail_abstand_pct": 25.0,
         "hoechster_kurs": 1.05,
         "frist": "2999-01-01T00:00:00+00:00",
         "letzter_kurs": 1.0, "eroeffnet": "2026-09-14",
         "eroeffnet_zeit": "2026-09-14T20:00:00+00:00"}
    p.update(over)
    return p


def portfolio_pos(mint="T1", preis=1.0, mk=500000.0, kette="solana",
                  symbol="AAA"):
    return {"mint": mint, "kette": kette, "symbol": symbol, "name": symbol,
            "preis": preis, "marktkap_usd": mk, "wert_usd": 100.0,
            "updated_at": "2026-09-14T20:00:00Z", "is_exited": False,
            "dust": False, "vermutlich_verloren": False,
            "callout_zeit": None, "roh": {}}


def frischer_kauf(preis=1.0, sekunden=60):
    return {"tx": "TX_%s" % MINT_FRISCH, "typ": "buy",
            "zeit_ms": int((time.time() - sekunden) * 1000),
            "preis": preis, "betrag_usd": 10.0, "bonding_curve": False}


class Grundlage(unittest.TestCase):
    """Jeder Test arbeitet in einem eigenen Ordner - nichts am echten Buch."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (kp.WACHEN, kp.ZUSTAND, kp.JOURNAL, kp.VERFOLGTE,
                    kp.ABLEHNUNGEN)
        self.alt_schreiben = kp.SCHREIBEN
        kp.SCHREIBEN = True
        kp.WACHEN = os.path.join(self.tmp.name, "wachen.json")
        kp.ZUSTAND = os.path.join(self.tmp.name, "zustand.json")
        kp.JOURNAL = os.path.join(self.tmp.name, "handelsjournal.csv")
        kp.VERFOLGTE = os.path.join(self.tmp.name, "verfolgte.json")
        kp.ABLEHNUNGEN = os.path.join(self.tmp.name, "ablehnungen.csv")
        w = json.loads(json.dumps(WACHEN_ROH))
        w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")
        with open(kp.WACHEN, "w", encoding="utf-8") as f:
            json.dump(w, f, ensure_ascii=False, indent=2)
        # Verfolgte Liste: frisch (stand = jetzt), keine Ausnahme-Mocks noetig.
        with io.open(kp.VERFOLGTE, "w", encoding="utf-8") as f:
            json.dump({"stand": kp._jetzt(), "regel": "Test",
                       "periode": "daily", "ketten": ["solana"],
                       "wallets": [{"wallet": "W1", "username": "AAA",
                                    "gemessen": True, "rank": 1,
                                    "pnl_usd": 100.0},
                                   {"wallet": "W2", "username": "BBB",
                                    "gemessen": True, "rank": 2,
                                    "pnl_usd": 50.0}]}, f)
        # Der Lauf baut eine zu alte Liste selbst neu - im Test nie.
        self.alt_waehlen = kp.waehlen
        kp.waehlen = lambda w: None

    def tearDown(self):
        kp.WACHEN, kp.ZUSTAND, kp.JOURNAL = self.alt[0], self.alt[1], self.alt[2]
        kp.VERFOLGTE, kp.ABLEHNUNGEN = self.alt[3], self.alt[4]
        kp.SCHREIBEN = self.alt_schreiben
        kp.waehlen = self.alt_waehlen
        self.tmp.cleanup()

    def schreibe_zustand(self, z):
        with open(kp.ZUSTAND, "w", encoding="utf-8") as f:
            json.dump(z, f, ensure_ascii=False, indent=2)

    def lese_zustand(self):
        with open(kp.ZUSTAND, encoding="utf-8") as f:
            return json.load(f)

    def protokoll_gruende(self):
        if not os.path.exists(kp.ABLEHNUNGEN):
            return []
        with open(kp.ABLEHNUNGEN, newline="", encoding="utf-8") as f:
            return [(r.get("art"), r.get("grund"),
                     int(float(r.get("anzahl") or 0)))
                    for r in csv.DictReader(f)]

    def wachen(self, **over):
        w = json.loads(json.dumps(WACHEN_ROH))
        w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")
        w.update(over)
        return w

    def zustand_leer(self):
        return {"positionen": [], "gesehen_portfolios": {},
                "letzter_lauf": kp._jetzt(), "modus": "papier"}

    def lese_journal(self):
        if not os.path.exists(kp.JOURNAL):
            return []
        with open(kp.JOURNAL, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))


class Sicherheit(Grundlage):
    def test_lesen_hat_schreibschutz(self):
        # kopier.py startet nicht, wenn lesen.SCHREIBBEFEHLE fehlt.
        self.assertTrue(getattr(kp.lesen, "SCHREIBBEFEHLE"))

    def test_live_verweigert_ohne_freigabenfenster(self):
        # lauf("live") druckt die Verweigerung und laeuft dann wie spiegel
        # als Papierzyklus WEITER - deshalb muss auch dieser Test auf den
        # Temp-Pfaden stehen, damit kein echter Lauf entsteht. Der Feed wird
        # gemockt; geprueft wird nur der Text.
        sicht = {"W1": {}}   # Portfolio-Mock zieht auch die Verfolgungsliste
        with patch.object(kp.lesen, "portfolio",
                          side_effect=portfolio_effekt(sicht)), \
             contextlib.redirect_stdout(io.StringIO()) as aus:
            code = kp.lauf("live")
        self.assertEqual(code, 0)
        self.assertNotIn("Freigabefenster", aus.getvalue())
        self.assertIn("kein Live-Pfad", aus.getvalue())

    def test_nein_zeile_ohne_filterwort(self):
        sig = {"symbol": "AAA", "token": "T1", "kette": "solana"}
        for grund in ("zu alt", "marktkap ausserhalb", "token belegt",
                      "Risikostufe blockiert (is_banned)"):
            zeile = kp._nein(sig, grund)
            for wort in ("verkauf", "stop", "KILL", "gesperrt", "ausstieg"):
                self.assertNotIn(wort.lower(), zeile.lower())


class Kosten(unittest.TestCase):
    def test_kopie_ohne_kursbewegung_ist_minus(self):
        w = {"slippage_pct": 5.0, "gebuehr_pct": 1.0}
        einsatz = 50.0
        kauf = kp._kaufpreis(1.0, w)                       # 1.05
        menge = (einsatz - einsatz * 0.01) / kauf
        erloes = kp._verkaeuflich(menge, 1.0, w)
        self.assertLess(erloes, einsatz)
        self.assertAlmostEqual(erloes, 44.338, places=2)


class Tore(unittest.TestCase):
    def _sig(self, **over):
        s = {"quelle": "portfolio/AAA", "wallet_name": "AAA",
             "kette": "solana", "wallet": "W1", "token": "T1",
             "symbol": "AAA", "preis": 1.0, "marktkap_usd": 500000.0,
             "alter_s": None, "tx": None, "vorbild_kurs": None}
        s.update(over)
        return s

    def _leer(self):
        return {"positionen": []}

    def test_kette_nicht_unterstuetzt(self):
        w = {"ketten": ["solana"]}
        schluessel, text = kp._vorpruefung(self._sig(kette=None), w,
                                           self._leer())
        self.assertEqual(schluessel, "kette nicht unterstuetzt")

    def test_marktkap_unbekannt(self):
        w = {"ketten": ["solana"], "marketcap_band_usd": [50000, 1000000]}
        schluessel, _ = kp._vorpruefung(self._sig(marktkap_usd=None), w,
                                        self._leer())
        self.assertEqual(schluessel, "marktkap unbekannt")

    def test_band_unten_und_oben(self):
        w = {"ketten": ["solana"], "marketcap_band_usd": [50000, 1000000],
             "max_kopien_je_token": 2}
        for mk, erwartet in ((40000.0, "marktkap ausserhalb"),
                             (2000000.0, "marktkap ausserhalb"),
                             (500000.0, None)):
            schluessel, _ = kp._vorpruefung(self._sig(marktkap_usd=mk), w,
                                            self._leer())
            self.assertEqual(schluessel, erwartet, msg=str(mk))

    def test_token_und_wallet_belegt(self):
        w = {"ketten": ["solana"], "marketcap_band_usd": [50000, 1000000],
             "max_kopien_je_token": 2}
        z = {"positionen": [
            position(wallet="W9", token="T1"),
            position(wallet="W8", token="T1")]}
        schluessel, _ = kp._vorpruefung(self._sig(token="T1"), w, z)
        self.assertEqual(schluessel, "token belegt")
        z = {"positionen": [position(wallet="W1", token="T1")]}
        schluessel, _ = kp._vorpruefung(self._sig(token="T1"), w, z)
        self.assertEqual(schluessel, "wallet belegt")

    def test_ein_billiges_tor_kostet_keinen_abruf(self):
        w = {"ketten": ["solana"], "marketcap_band_usd": [50000, 1000000],
             "max_kopien_je_token": 2}
        with patch.object(kp.lesen, "letzter_kauf") as abruf:
            kp._vorpruefung(self._sig(marktkap_usd=999999999.0), w,
                            {"positionen": []})
        abruf.assert_not_called()


class TeurePruefung(Grundlage):
    def _kandidat(self, **over):
        s = {"quelle": "portfolio/AAA", "wallet_name": "AAA",
             "kette": "solana", "wallet": "W1", "token": "T1",
             "symbol": "AAA", "preis": 1.0, "marktkap_usd": 500000.0,
             "alter_s": None, "tx": None, "vorbild_kurs": None}
        s.update(over)
        return s

    def test_signal_zu_alt(self):
        w = {"max_alter_signal_sekunden": 1800, "slippage_pct": 5.0,
             "gebuehr_pct": 1.0, "risiko_pflicht": False,
             "max_einsatz_je_kopie_usd": 50}
        with patch.object(kp.lesen, "letzter_kauf",
                          return_value={"W1": frischer_kauf(sekunden=4000)}):
            p, grund = kp._kopie(self._kandidat(), w,
                                 {"positionen": []})
        self.assertIsNone(p)
        self.assertEqual(grund, "zu alt")

    def test_kaufabruf_fehler(self):
        w = {"max_alter_signal_sekunden": 1800, "slippage_pct": 5.0,
             "gebuehr_pct": 1.0, "risiko_pflicht": False,
             "max_einsatz_je_kopie_usd": 50}
        with patch.object(kp.lesen, "letzter_kauf",
                          side_effect=kp.lesen.Lesefehler("weg")):
            p, grund = kp._kopie(self._kandidat(), w, {"positionen": []})
        self.assertIsNone(p)
        self.assertIn("Kaufabruf", grund)

    def test_frisches_signal_wird_position(self):
        w = {"max_alter_signal_sekunden": 1800, "slippage_pct": 5.0,
             "gebuehr_pct": 1.0, "risiko_pflicht": False,
             "max_einsatz_je_kopie_usd": 50,
             "stop_pct": 15.0, "trail_aktiv_ab_pct": 30.0,
             "trail_abstand_pct": 25.0, "haltedauer_stunden": 168}
        with patch.object(kp.lesen, "letzter_kauf",
                          return_value={"W1": frischer_kauf(preis=0.9)}):
            p, grund = kp._kopie(self._kandidat(), w, {"positionen": []})
        self.assertIsNone(grund)
        self.assertEqual(p["preis_einstieg"], 1.05)      # 5 % Slippage
        self.assertEqual(p["preis_vorbild"], 0.9)
        self.assertAlmostEqual(p["menge"], 47.142857, places=4)
        # stop_pct 15: am Stop realisiert das Buch inklusive Kosten -20 %.
        self.assertAlmostEqual(p["stop_preis"], 1.05 * 0.85, places=10)
        self.assertEqual(p["trail_aktiv_ab_pct"], 30.0)
        self.assertEqual(p["trail_abstand_pct"], 25.0)
        self.assertEqual(p["hoechster_kurs"], 1.05)
        self.assertNotIn("ziel_preis", p)
        self.assertEqual(p["letzter_kurs"], 1.0)

    def test_risiko_sperrt(self):
        w = {"max_alter_signal_sekunden": 1800, "slippage_pct": 5.0,
             "gebuehr_pct": 1.0, "risiko_pflicht": True,
             "max_risiko_stufen": ["ok"], "max_einsatz_je_kopie_usd": 50}
        with patch.object(kp.lesen, "letzter_kauf",
                          return_value={"W1": frischer_kauf()}), \
             patch.object(kp.lesen, "risiko",
                          return_value={"stufe": "blockiert",
                                        "merkmale": ["is_banned"]}):
            p, grund = kp._kopie(self._kandidat(), w, {"positionen": []})
        self.assertIsNone(p)
        self.assertEqual(grund, "Risikostufe blockiert (is_banned)")

    def test_oeffnen_schreibt_journal_und_signal_zeit(self):
        w = {"max_alter_signal_sekunden": 1800, "slippage_pct": 5.0,
             "gebuehr_pct": 1.0, "risiko_pflicht": False,
             "max_einsatz_je_kopie_usd": 50,
             "stop_pct": 15.0, "trail_aktiv_ab_pct": 30.0,
             "trail_abstand_pct": 25.0, "haltedauer_stunden": 168}
        z = {"positionen": []}
        with patch.object(kp.lesen, "letzter_kauf",
                          return_value={"W1": frischer_kauf()}):
            grund = kp.eroeffne(z, self._kandidat(), w)
        self.assertIsNone(grund)
        self.assertEqual(len(z["positionen"]), 1)
        zeilen = self.lese_journal()
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0]["aktion"], "eroeffnen")
        self.assertEqual(zeilen[0]["wallet"], "W1")
        self.assertEqual(zeilen[0]["slippage_pct"], "5.0")


class Ausstiege(Grundlage):
    def test_vorbild_ausstieg(self):
        z = {"positionen": [position(wallet="W1", token="T1",
                                     letzter_kurs=1.0)],
             "gesehen_portfolios": {}, "letzter_lauf": kp._jetzt(),
             "modus": "papier"}
        w = self.wachen(follow_ausstieg=True)
        sicht = {"W1": {"T2": portfolio_pos("T2")}}
        kp.pruefe_vorbild_ausstiege(z, sicht, w)
        self.assertEqual(len(z["positionen"]), 0)
        zeilen = self.lese_journal()
        self.assertEqual(zeilen[0]["aktion"], "schliessen")
        self.assertEqual(zeilen[0]["grund"], "vorbild_ausstieg")
        self.assertLess(float(zeilen[0]["wert_usd"]), 50.0)  # Kosten

    def test_vorbild_bleibt_wenn_position_gehalten(self):
        z = {"positionen": [position(wallet="W1", token="T1")]}
        w = self.wachen(follow_ausstieg=True)
        kp.pruefe_vorbild_ausstiege(z, {"W1": {"T1": portfolio_pos()}}, w)
        self.assertEqual(len(z["positionen"]), 1)

    def test_follow_ausstieg_abgeschaltet(self):
        z = {"positionen": [position(wallet="W1", token="T1")]}
        w = self.wachen(follow_ausstieg=False)
        kp.pruefe_vorbild_ausstiege(z, {"W1": {}}, w)
        self.assertEqual(len(z["positionen"]), 1)

    def test_stop_trailing_frist(self):
        w = self.wachen()
        frist_alt = "2000-01-01T00:00:00+00:00"
        # Kein fester Deckel: +100 % laeuft weiter (kein Ziel-Exit).
        # Zuerst geprueft, solange das Journal noch leer ist.
        z = {"positionen": [position(token="T1", hoechster_kurs=2.1,
                                     letzter_kurs=2.1)]}
        kp.pruefe_ausstiege(z, w)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self.lese_journal(), [])
        # Harter Stop: erster beobachteter Kurs unter stop_preis schliesst.
        z = {"positionen": [position(token="T1", letzter_kurs=0.5)]}
        with contextlib.redirect_stdout(io.StringIO()):
            kp.pruefe_ausstiege(z, w)
        self.assertEqual(len(z["positionen"]), 0)
        self.assertEqual(self.lese_journal()[-1]["grund"], "stop")
        # Trailing: war +30 % ueber dem Einstieg (Peak 1.4), faellt unter
        # Peak*(1-25 %) = 1.05 -> Ausstieg, auch bei +25 % ueber Einstieg.
        z = {"positionen": [position(token="T1", hoechster_kurs=1.4,
                                     letzter_kurs=1.0)]}
        with contextlib.redirect_stdout(io.StringIO()):
            kp.pruefe_ausstiege(z, w)
        self.assertEqual(len(z["positionen"]), 0)
        self.assertEqual(self.lese_journal()[-1]["grund"], "trail")
        # Trailing noch nicht aktiv: eher unter dem Einstieg -> kein Ausstieg.
        z = {"positionen": [position(token="T1", hoechster_kurs=1.1,
                                     letzter_kurs=1.0)]}
        kp.pruefe_ausstiege(z, w)
        self.assertEqual(len(z["positionen"]), 1)
        # Frist als Sicherheitsnetz gegen tote Positionen.
        z = {"positionen": [position(token="T1", letzter_kurs=1.0,
                                     frist=frist_alt)]}
        kp.pruefe_ausstiege(z, w)
        self.assertEqual(len(z["positionen"]), 0)
        self.assertEqual(self.lese_journal()[-1]["grund"], "frist")

    def test_kein_kurs_bleibt_offen(self):
        w = self.wachen()
        z = {"positionen": [position(token="T1", letzter_kurs=None)]}
        kp.pruefe_ausstiege(z, w)
        self.assertEqual(len(z["positionen"]), 1)

    def test_kein_kurs_nach_der_frist_schliesst_mit_erloes_null(self):
        w = self.wachen()
        frist_alt = "2000-01-01T00:00:00+00:00"
        z = {"positionen": [position(token="T1", letzter_kurs=None, frist=frist_alt),
                            position(token="T2", letzter_kurs=None)]}
        kp.pruefe_ausstiege(z, w)
        self.assertEqual([p["token"] for p in z["positionen"]], ["T2"])
        zeile = self.lese_journal()[-1]
        self.assertEqual(zeile["grund"], "frist_ohne_kurs")
        self.assertEqual(float(zeile["wert_usd"]), 0.0)

    def test_kill_switch_und_flach(self):
        w = self.wachen(kill_switch_gesamt_usd=10,
                        kill_switch_gesamt_usd_papier=10)
        # 8 Kopien a 50 USD, alle bei 0.5 (Stop laengst gerissen) ->
        # Ruecklauf gross, der Schwellenwert ist laengst unterschritten.
        z = {"positionen": [position(token="T%d" % i, letzter_kurs=0.5)
                            for i in range(8)]}
        self.assertTrue(kp.kill_switch(z, w))
        self.assertEqual(len(z["positionen"]), 8)   # prueft nur
        with contextlib.redirect_stdout(io.StringIO()):
            kp.flach_stellen(z, w, "kill_switch")
        self.assertEqual(len(z["positionen"]), 0)
        zeilen = self.lese_journal()
        self.assertTrue(zeilen)
        self.assertEqual(zeilen[0]["grund"], "kill_switch")

    def test_kill_switch_ruhig_bei_frischem_buch(self):
        w = self.wachen(kill_switch_gesamt_usd=10,
                        kill_switch_gesamt_usd_papier=10)
        z = {"positionen": [position(token="T1", letzter_kurs=1.0)]}
        self.assertFalse(kp.kill_switch(z, w))


def portfolio_effekt(sicht):
    """Mock fuer lesen.portfolio: W1 liefert die Sicht, andere Wallets nichts."""
    def effekt(wallet):
        return {"positions": sicht.get(wallet, {}), "summary": {}}
    return effekt


class Zyklus(Grundlage):
    def test_einlauf_uebernimmt_still_ohne_kauf(self):
        z = self.zustand_leer()
        self.schreibe_zustand(z)
        sicht = {"W1": {"T1": portfolio_pos("T1"),
                        "T2": portfolio_pos("T2", symbol="BBB")}}
        with patch.object(kp.lesen, "portfolio", side_effect=portfolio_effekt(sicht)), \
             patch.object(kp.lesen, "letzter_kauf") as kauf, \
             patch.object(kp.lesen, "risiko") as risiko:
            code = kp.lauf("papier")
        self.assertEqual(code, 0)
        kauf.assert_not_called()
        risiko.assert_not_called()
        self.assertEqual(self.lese_journal(), [])
        nachher = self.lese_zustand()
        self.assertEqual(set(nachher["gesehen_portfolios"]["W1"]),
                         {"T1", "T2"})

    def test_neue_position_wird_gekauft_und_registriert(self):
        z = self.zustand_leer()
        z["gesehen_portfolios"]["W1"] = {
            "T1": {"seit": kp._jetzt(), "letzter_kurs": 1.0}}
        self.schreibe_zustand(z)
        sicht = {"W1": {"T1": portfolio_pos("T1"),
                        "T2": portfolio_pos("T2", symbol="BBB", preis=0.5,
                                            mk=200000.0)}}
        with patch.object(kp.lesen, "portfolio", side_effect=portfolio_effekt(sicht)), \
             patch.object(kp.lesen, "letzter_kauf",
                          return_value={"W1": frischer_kauf(preis=0.45)}), \
             patch.object(kp.lesen, "risiko",
                          return_value={"stufe": "ok", "merkmale": []}):
            code = kp.lauf("papier")
        self.assertEqual(code, 0)
        zeilen = self.lese_journal()
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0]["aktion"], "eroeffnen")
        self.assertEqual(zeilen[0]["token"], "T2")
        nachher = self.lese_zustand()
        self.assertIn("T2", nachher["gesehen_portfolios"]["W1"])
        self.assertEqual(len(nachher["positionen"]), 1)

    def test_band_ablehnung_ohne_abruf_und_registriert(self):
        z = self.zustand_leer()
        z["gesehen_portfolios"]["W1"] = {
            "T1": {"seit": kp._jetzt(), "letzter_kurs": 1.0}}
        self.schreibe_zustand(z)
        sicht = {"W1": {"T1": portfolio_pos("T1"),
                        "T2": portfolio_pos("T2", mk=999999999.0)}}
        with patch.object(kp.lesen, "portfolio", side_effect=portfolio_effekt(sicht)), \
             patch.object(kp.lesen, "letzter_kauf") as kauf, \
             patch.object(kp.lesen, "risiko") as risiko:
            code = kp.lauf("papier")
        self.assertEqual(code, 0)
        kauf.assert_not_called()
        risiko.assert_not_called()
        self.assertEqual(self.lese_journal(), [])
        nachher = self.lese_zustand()
        self.assertIn("T2", nachher["gesehen_portfolios"]["W1"])
        # Und das Protokoll haelt die Lage fest.
        gruende = self.protokoll_gruende()
        self.assertIn(("zyklus", "Lage: marktkap ausserhalb", 1), gruende)
        self.assertIn(("zyklus", "Signale gesehen", 1), gruende)

    def test_zu_alt_und_kontrolle_geht_auf(self):
        z = self.zustand_leer()
        z["gesehen_portfolios"]["W1"] = {
            "T1": {"seit": kp._jetzt(), "letzter_kurs": 1.0}}
        self.schreibe_zustand(z)
        sicht = {"W1": {"T1": portfolio_pos("T1"),
                        "T2": portfolio_pos("T2")}}
        with patch.object(kp.lesen, "portfolio", side_effect=portfolio_effekt(sicht)), \
             patch.object(kp.lesen, "letzter_kauf",
                          return_value={"W1": frischer_kauf(sekunden=4000)}), \
             patch.object(kp.lesen, "risiko") as risiko:
            kp.lauf("papier")
        risiko.assert_not_called()
        self.assertEqual(self.lese_journal(), [])
        with contextlib.redirect_stdout(io.StringIO()) as aus:
            code = kp.ablehnungsbilanz()
        self.assertEqual(code, 0)
        self.assertIn("Kontrolle: kaufbar 1 = bewertet 1 + nicht mehr "
                      "erreicht 0", aus.getvalue().replace("\n", " "))

    def test_buch_voll_laesst_kandidaten_unregistriert(self):
        z = self.zustand_leer()
        z["gesehen_portfolios"]["W1"] = {
            "T1": {"seit": kp._jetzt(), "letzter_kurs": 1.0}}
        self.schreibe_zustand(z)
        sicht = {"W1": {"T1": portfolio_pos("T1"),
                        "T2": portfolio_pos("T2")}}
        # max_offen_papier 0: der erste Kandidat faellt am Platzmangel,
        # und nur die Kapazitaetsfalle darf ihn unregistriert lassen.
        w_direkt = self.wachen(max_offen_papier=0,
                               kill_switch_gesamt_usd_papier=9999)
        with open(kp.WACHEN, "w", encoding="utf-8") as f:
            json.dump(w_direkt, f, ensure_ascii=False, indent=2)
        with patch.object(kp.lesen, "portfolio", side_effect=portfolio_effekt(sicht)), \
             patch.object(kp.lesen, "letzter_kauf") as kauf:
            code = kp.lauf("papier")
        self.assertEqual(code, 0)
        kauf.assert_not_called()
        nachher = self.lese_zustand()
        # T2 ist NICHT registriert: im naechsten Zyklus darf er wieder
        # Kandidat sein.
        self.assertNotIn("T2", nachher["gesehen_portfolios"]["W1"])

    def test_vorbild_ausstieg_im_zyklus(self):
        z = self.zustand_leer()
        z["positionen"] = [position(wallet="W1", token="T1",
                                    letzter_kurs=1.0)]
        z["gesehen_portfolios"]["W1"] = {
            "T1": {"seit": kp._jetzt(), "letzter_kurs": 1.0}}
        self.schreibe_zustand(z)
        # W1 haelt nichts mehr - T1 ist weg: die Kopie schliesst. W2 ist neu
        # in der Sicht (Einlauf, kein Kauf).
        sicht = {"W1": {}, "W2": {"T9": portfolio_pos("T9")}}
        with patch.object(kp.lesen, "portfolio", side_effect=portfolio_effekt(sicht)), \
             patch.object(kp.lesen, "letzter_kauf") as kauf:
            code = kp.lauf("papier")
        self.assertEqual(code, 0)
        kauf.assert_not_called()
        zeilen = self.lese_journal()
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0]["aktion"], "schliessen")
        self.assertEqual(zeilen[0]["grund"], "vorbild_ausstieg")
        nachher = self.lese_zustand()
        self.assertEqual(len(nachher["positionen"]), 0)

    def test_herzschlag_alt_stellt_flach(self):
        z = self.zustand_leer()
        z["letzter_lauf"] = "2026-09-01T00:00:00+00:00"
        z["positionen"] = [position(wallet="W1", token="T1",
                                    letzter_kurs=1.0)]
        self.schreibe_zustand(z)
        with patch.object(kp.lesen, "portfolio") as pf:
            code = kp.lauf("papier")
        pf.assert_not_called()
        self.assertEqual(code, 0)
        zeilen = self.lese_journal()
        self.assertEqual(zeilen[0]["grund"], "herzschlag_alt")
        nachher = self.lese_zustand()
        self.assertEqual(len(nachher["positionen"]), 0)

    def test_vorschau_schreibt_nichts(self):
        z = self.zustand_leer()
        z["gesehen_portfolios"]["W1"] = {
            "T1": {"seit": kp._jetzt(), "letzter_kurs": 1.0}}
        self.schreibe_zustand(z)
        sicht = {"W1": {"T1": portfolio_pos("T1"),
                        "T2": portfolio_pos("T2", symbol="BBB")}}
        with patch.object(kp.lesen, "portfolio", side_effect=portfolio_effekt(sicht)), \
             patch.object(kp.lesen, "letzter_kauf",
                          return_value={"W1": frischer_kauf()}), \
             patch.object(kp.lesen, "risiko",
                          return_value={"stufe": "ok", "merkmale": []}):
            with contextlib.redirect_stdout(io.StringIO()) as aus:
                code = kp.lauf("vorschau")
        self.assertEqual(code, 0)
        self.assertIn("WAERE", aus.getvalue())
        self.assertEqual(self.lese_journal(), [])
        nachher = self.lese_zustand()
        self.assertEqual(len(nachher["positionen"]), 0)


class Bilanz(Grundlage):
    def test_bilanz_liest_journal(self):
        for zeile in (("eroeffnen", "W1", "AAA", "50.00", ""),
                      ("schliessen", "W1", "AAA", "50.00", "55.00"),
                      ("schliessen", "W2", "BBB", "50.00", "30.00")):
            kp.journal(zeit=kp._jetzt(), modus="papier", aktion=zeile[0],
                       kette="solana", wallet=zeile[1], token="T",
                       symbol=zeile[2], einsatz_usd=zeile[3],
                       wert_usd=zeile[4], grund="stop")
        with contextlib.redirect_stdout(io.StringIO()) as aus:
            kp.bilanz(self.wachen())
        text = aus.getvalue()
        self.assertIn("2 abgeschlossenen Kopien", text)
        self.assertIn("+5.00", text)
        self.assertIn("Rang 1", text)


class NachlaufMessungTest(unittest.TestCase):
    """T-268: die Messung selbst - Verteilung und Bestands-Stichprobe.

    Nur reine Funktionen: die echte Messung schreibt daten/messung.json und
    darf im Test nicht laufen (der Modulwaechter wuerde sie als Schreibzugriff
    melden - zu Recht).
    """

    def test_verteilung_ist_eine_verteilung_kein_mittelwert(self):
        v = kp._verteilung([1.0, 2.0, 3.0, 4.0])
        self.assertEqual(v["n"], 4)
        self.assertEqual(v["min"], 1.0)
        self.assertEqual(v["max"], 4.0)
        self.assertAlmostEqual(v["median"], 2.5, places=6)
        self.assertAlmostEqual(v["schnitt"], 2.5, places=6)

    def test_verteilung_ohne_werte_ist_kein_messwert(self):
        self.assertIsNone(kp._verteilung([]))

    def test_bestand_stichprobe_haelt_sich_an_das_marktkap_band(self):
        w = {"marketcap_band_usd": [50000, 1000000]}
        sicht = {"A": {
            "klein": {"preis": 1.0, "marktkap_usd": 100000, "symbol": "K",
                      "wert_usd": 10.0},
            "zu_gross": {"preis": 1.0, "marktkap_usd": 5000000, "symbol": "G",
                         "wert_usd": 10.0},
            "zu_klein": {"preis": 1.0, "marktkap_usd": 1000, "symbol": "Z",
                         "wert_usd": 10.0}}}
        aus = kp._bestand_als_stichprobe(w, sicht, {}, 10)
        self.assertEqual([s["token"] for s in aus], ["klein"])

    def test_bestand_stichprobe_nimmt_je_token_nur_eine_wallet(self):
        """Sonst steht dasselbe Token mehrfach in der Stichprobe und die
        Verteilung zaehlt eine Position doppelt."""
        w = {"marketcap_band_usd": [0, 10 ** 12]}
        sicht = {"A": {"T": {"preis": 1.0, "marktkap_usd": 100000,
                             "symbol": "X", "wert_usd": 5.0}},
                 "B": {"T": {"preis": 1.0, "marktkap_usd": 100000,
                             "symbol": "X", "wert_usd": 50.0}}}
        aus = kp._bestand_als_stichprobe(w, sicht, {}, 10)
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["wallet"], "B")      # die groessere Position

    def test_bestand_stichprobe_ohne_kurs_zaehlt_nicht(self):
        w = {"marketcap_band_usd": [0, 10 ** 12]}
        sicht = {"A": {"T": {"preis": None, "marktkap_usd": 100000,
                             "symbol": "X", "wert_usd": 5.0}}}
        self.assertEqual(kp._bestand_als_stichprobe(w, sicht, {}, 10), [])


if __name__ == "__main__":
    unittest.main()