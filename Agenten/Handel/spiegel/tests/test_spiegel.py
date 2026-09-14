"""Tests fuer spiegel.py - das Papierbuch, ohne Netz, ohne Schreibzugriff.

Geprueft werden die drei Stellen, an denen ein Fehler Geld kosten wuerde:
die Kostenrechnung (Slippage und Gebuehr zweimal), die Tore vor dem Kauf
(Zu alt, Marktkapitalisierung, Risikostufe, Doppelkopie) und die Ausstiege
(Stop, Ziel, Frist, Kill-Switch). Dazu die zwei Sicherheitsnetze: keine
Schreibfunktion im Modul und der Verweigerungstext, den der Dauerlauf liest.

Aufruf:  python -m unittest discover -s tests   (im Ordner spiegel/)
"""

import contextlib
import csv
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.abspath(__file__))
SPIEGEL = os.path.dirname(HIER)
if SPIEGEL not in sys.path:
    sys.path.insert(0, SPIEGEL)

import spiegel as sp                                          # noqa: E402

WACHEN = json.load(io.open(os.path.join(SPIEGEL, "wachen.json"), encoding="utf-8"))

SIGNAL = {"quelle": "tracker/smart_money", "kette": "solana", "wallet": "W1",
          "token": "T1", "symbol": "AAA", "preis": 1.0, "zeit_ms": 0,
          "alter_s": 5.0, "marktkap_usd": 500000.0, "quote": "SOLANA",
          "tx": "TX1"}


def kopie(**over):
    p = {"kette": "solana", "wallet": "W1", "token": "T1", "symbol": "AAA",
         "einsatz_usd": 50.0, "menge": 48.54368932038835,
         "preis_vorbild": 1.0, "preis_einstieg": 1.03, "marktkap_usd": 500000.0,
         "risiko": "safe", "stop_preis": 0.7725, "ziel_preis": 1.648,
         "frist": "2999-01-01T00:00:00+00:00", "eroeffnet": "2026-09-12",
         "eroeffnet_zeit": "2026-09-12T20:00:00+00:00"}
    p.update(over)
    return p


class Grundlage(unittest.TestCase):
    """Jeder Test arbeitet in einem eigenen Ordner - nichts am echten Buch."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (sp.ZUSTAND, sp.JOURNAL, sp.VERFOLGTE)
        sp.ZUSTAND = os.path.join(self.tmp.name, "zustand.json")
        sp.JOURNAL = os.path.join(self.tmp.name, "handelsjournal.csv")
        sp.VERFOLGTE = os.path.join(self.tmp.name, "verfolgte.json")
        with io.open(sp.VERFOLGTE, "w", encoding="utf-8") as f:
            json.dump({"stand": "2026-09-12", "regel": "Test",
                       "ketten": ["solana"],
                       "wallets": [{"kette": "solana", "wallet": "W1",
                                    "gemessen": False}]}, f)

    def tearDown(self):
        sp.ZUSTAND, sp.JOURNAL, sp.VERFOLGTE = self.alt
        self.tmp.cleanup()

    def journal(self):
        if not os.path.exists(sp.JOURNAL):
            return []
        with open(sp.JOURNAL, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))


class Kosten(Grundlage):

    def test_kaufpreis_ist_teurer_als_das_vorbild(self):
        self.assertAlmostEqual(sp._kaufpreis(1.0, WACHEN), 1.03)

    def test_verkaeuflich_zieht_slippage_und_gebuehr_ab(self):
        # 100 Stueck zu 1,00 USD, 3 % Slippage, 1 % Gebuehr
        self.assertAlmostEqual(sp._verkaeuflich(100.0, 1.0, WACHEN),
                               100 * 0.97 * 0.99)

    def test_eine_kopie_ohne_kursbewegung_verliert_geld(self):
        # Der wichtigste Test der Spur: Wer kauft und sofort verkauft, zahlt.
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "safe", "merkmale": []}):
            p, _ = sp._kopie(dict(SIGNAL, marktkap_usd=500000.0), WACHEN,
                             {"positionen": []})
        erloes = sp._verkaeuflich(p["menge"], p["preis_vorbild"], WACHEN)
        self.assertLess(erloes, p["einsatz_usd"])


class Tore(Grundlage):

    def test_zu_alte_signale_werden_verworfen(self):
        p, grund = sp._kopie(dict(SIGNAL, alter_s=600.0), WACHEN,
                             {"positionen": []})
        self.assertIsNone(p)
        self.assertIn("zu alt", grund)

    def test_marktkapitalisierung_ausserhalb_des_bandes(self):
        for mk, wort in ((10000.0, "ausserhalb"), (999000000.0, "ausserhalb")):
            p, grund = sp._kopie(dict(SIGNAL, marktkap_usd=mk), WACHEN,
                                 {"positionen": []})
            self.assertIsNone(p, mk)
            self.assertIn(wort, grund)

    def test_unbekannte_marktkapitalisierung_ist_ein_grund_kein_raten(self):
        p, grund = sp._kopie(dict(SIGNAL, marktkap_usd=None), WACHEN,
                             {"positionen": []})
        self.assertIsNone(p)
        self.assertIn("unbekannt", grund)

    def test_risikostufe_ueber_der_grenze_verhindert_die_kopie(self):
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "HIGH", "merkmale": ["isHoneypot"]}):
            p, grund = sp._kopie(SIGNAL, WACHEN, {"positionen": []})
        self.assertIsNone(p)
        self.assertIn("Risikostufe HIGH", grund)

    def test_doppelte_kopie_derselben_wallet_auf_demselben_token(self):
        z = {"positionen": [kopie()]}
        p, grund = sp._kopie(SIGNAL, WACHEN, z)
        self.assertIsNone(p)
        self.assertIn("schon", grund)

    def test_zwei_kopien_je_token_sind_die_grenze(self):
        z = {"positionen": [kopie(wallet="W2"), kopie(wallet="W3")]}
        p, grund = sp._kopie(dict(SIGNAL, wallet="W9"), WACHEN, z)
        self.assertIsNone(p)
        self.assertIn("schon 2 Kopien", grund)

    def test_eine_kopie_setzt_stop_ziel_frist_und_menge(self):
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "safe", "merkmale": []}):
            p, grund = sp._kopie(SIGNAL, WACHEN, {"positionen": []})
        self.assertIsNone(grund)
        self.assertAlmostEqual(p["preis_einstieg"], 1.03)
        self.assertAlmostEqual(p["stop_preis"], 1.03 * 0.75)
        self.assertAlmostEqual(p["ziel_preis"], 1.03 * 1.60)
        self.assertAlmostEqual(p["menge"], (50.0 - 0.5) / 1.03)
        self.assertEqual(p["risiko"], "safe")
        self.assertTrue(p["frist"].startswith("2"))


class Buch(Grundlage):

    def test_eroeffnen_schreibt_journalzeile(self):
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "safe", "merkmale": []}):
            z = {"positionen": [], "letzter_lauf": None}
            sp.eroeffne(z, SIGNAL, WACHEN)
        self.assertEqual(len(z["positionen"]), 1)
        zeilen = self.journal()
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0]["aktion"], "eroeffnen")
        self.assertEqual(zeilen[0]["wallet"], "W1")
        self.assertEqual(zeilen[0]["slippage_pct"], "3.0")

    def test_die_eroeffnungszeile_nennt_die_frist_mit_datum_und_zone(self):
        """Die Zeile mit "Stop" geht nach Telegram - und sie trug die Frist
        als UTC-Stunde ohne Datum ("Frist 13:22"), obwohl die Frist 24 h in
        der Zukunft lag. Fuer Max in UTC+2 sah das wie eine abgelaufene
        Frist aus (Befund 13.09.2026, Kopie PFCHAN)."""
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "safe", "merkmale": []}):
            z = {"positionen": [], "letzter_lauf": None}
            aus = io.StringIO()
            with contextlib.redirect_stdout(aus):
                sp.eroeffne(z, SIGNAL, WACHEN)
        zeilen = [x for x in aus.getvalue().splitlines() if "Stop" in x]
        self.assertEqual(len(zeilen), 1)
        frist = zeilen[0].split("Frist", 1)[1].strip()
        # Datum, lokale Uhrzeit und die Kennzeichnung "lokal" - nicht die
        # nackte UTC-Stunde.
        self.assertRegex(frist, r"^\d{2}\.\d{2}\. \d{2}:\d{2} lokal$")

    def test_lokal_rechnet_utc_in_die_eigene_zone_um(self):
        import datetime as dt
        utc = "2026-09-14T13:22:22+00:00"
        erwartet = (dt.datetime.fromisoformat(utc).astimezone()
                    .strftime("%d.%m. %H:%M"))
        self.assertEqual(sp._lokal(utc), erwartet)
        self.assertNotIn("T13:22", sp._lokal(utc))

    def test_lokal_kippt_bei_unlesbarer_zeit_nicht(self):
        self.assertEqual(sp._lokal(""), "")
        self.assertEqual(sp._lokal("keine-zeit"), "keine-zeit")

    def test_stop_ziel_und_frist_schliessen_die_kopie(self):
        faelle = ((0.70, "stop"), (2.0, "ziel"))
        for kurs, grund in faelle:
            with self.subTest(kurs=kurs):
                z = {"positionen": [kopie()]}
                with patch.object(sp.lesen, "preise",
                                  return_value={("solana", "T1"): kurs}):
                    sp.pruefe_ausstiege(z, WACHEN)
                self.assertEqual(z["positionen"], [])
                self.assertEqual(self.journal()[-1]["grund"], grund)
        z = {"positionen": [kopie(frist="2000-01-01T00:00:00+00:00")]}
        with patch.object(sp.lesen, "preise",
                          return_value={("solana", "T1"): 1.05}):
            sp.pruefe_ausstiege(z, WACHEN)
        self.assertEqual(self.journal()[-1]["grund"], "frist")

    def test_kurs_dazwischen_laesst_die_kopie_stehen(self):
        z = {"positionen": [kopie()]}
        with patch.object(sp.lesen, "preise",
                          return_value={("solana", "T1"): 1.04}):
            sp.pruefe_ausstiege(z, WACHEN)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self.journal(), [])

    def test_fehlender_kurs_kippt_die_kopie_nicht(self):
        z = {"positionen": [kopie()]}
        with patch.object(sp.lesen, "preise", return_value={}):
            sp.pruefe_ausstiege(z, WACHEN)
        self.assertEqual(len(z["positionen"]), 1)

    def test_kill_switch_greift_erst_an_der_grenze(self):
        # Grenze 100 USD. Ein Buch mit 4 x 50 USD Einsatz, das auf 4 x ~18,6
        # USD gefallen ist, liegt bei etwa -125 USD - darunter greift sie.
        vier = {"positionen": [kopie(token="T%d" % i) for i in range(1, 5)]}
        kurse4 = {("solana", "T%d" % i): 0.4 for i in range(1, 5)}
        with patch.object(sp.lesen, "preise", return_value=kurse4):
            self.assertTrue(sp.kill_switch(vier, WACHEN))
        # Ein einzelner Verlust von rund 31 USD ist noch kein Ruecklauf.
        with patch.object(sp.lesen, "preise",
                          return_value={("solana", "T1"): 0.4}):
            self.assertFalse(sp.kill_switch({"positionen": [kopie()]}, WACHEN))

    def test_flach_stellen_schreibt_jede_kopie_zu(self):
        z = {"positionen": [kopie(), kopie(token="T2")]}
        with patch.object(sp.lesen, "preise",
                          return_value={("solana", "T1"): 1.0,
                                        ("solana", "T2"): 1.0}):
            sp.flach_stellen(z, WACHEN, "herzschlag_alt")
        self.assertEqual(z["positionen"], [])
        self.assertEqual([g["grund"] for g in self.journal()],
                         ["herzschlag_alt", "herzschlag_alt"])


class Messung(Grundlage):

    def test_messen_rechnet_tiefe_und_nachlauf(self):
        """Die zwei Kostenposten getrennt: Pool-Tiefe und Nachlauf.

        Tiefe bei 50 USD Einsatz und 10.000 USD Liquiditaet: 2*50/10000 = 1 %.
        Nachlauf: Kurs jetzt 1,10 gegen Signal 1,00 = +10 %.
        """
        sig = [dict(SIGNAL, preis=1.0, alter_s=10.0)]
        with patch.object(sp, "signale_sammeln", return_value=sig), \
                patch.object(sp, "HIER", self.tmp.name), \
                patch.object(sp.lesen, "preise",
                             return_value={("solana", "T1"): 1.10}), \
                patch.object(sp.lesen, "preise_info",
                             return_value={"liquidity": "10000",
                                           "marketCap": "50000",
                                           "holders": "12"}):
            puffer = io.StringIO()
            with patch("sys.stdout", puffer):
                rc = sp.messen(WACHEN, {"positionen": []})
        self.assertEqual(rc, 0)
        ausgabe = puffer.getvalue()
        self.assertIn("1.000%", ausgabe)
        self.assertIn("+10.00%", ausgabe)
        with io.open(os.path.join(self.tmp.name, "daten", "messung.json"),
                     encoding="utf-8") as f:
            daten = json.load(f)
        self.assertEqual(daten["annahme_slippage_pct"], WACHEN["slippage_pct"])
        self.assertAlmostEqual(daten["werte"][0]["tiefe_pct"], 1.0)
        self.assertAlmostEqual(daten["werte"][0]["nachlauf_pct"], 10.0)

    def test_messen_ohne_frische_signale_ist_kein_lauf(self):
        with patch.object(sp, "signale_sammeln", return_value=[]):
            with patch("sys.stdout", io.StringIO()):
                self.assertEqual(sp.messen(WACHEN, {"positionen": []}), 1)


class Sicherheitsnetze(Grundlage):

    def test_modul_ruft_das_cli_nicht_selbst(self):
        # spiegel.py darf nur ueber lesen.py mit der Aussenwelt sprechen -
        # dort sitzt der Schreibschutz.
        with open(os.path.join(SPIEGEL, "spiegel.py"), encoding="utf-8") as f:
            quelle = f.read()
        self.assertNotIn("subprocess", quelle)
        self.assertNotIn("onchainos", quelle)

    def test_lesen_hat_den_schreibschutz(self):
        self.assertTrue(sp.lesen.SCHREIBBEFEHLE)

    def test_verweigerungstext_ist_fuer_den_dauerlauf_lesbar(self):
        """Genau ein Grund, ohne das Wort Freigabefenster - sonst fragt der
        Dauerlauf eine Freigabe an, die nichts oeffnen kann."""
        z = {"positionen": [], "letzter_lauf": None}
        with patch.object(sp, "lade_zustand", return_value=z), \
                patch.object(sp, "signale_sammeln", return_value=[]), \
                patch.object(sp, "_gefolgt", return_value={("solana", "W1"): {}}):
            puffer = io.StringIO()
            with patch("sys.stdout", puffer):
                sp.lauf("vorschau")
        zeilen = [z for z in puffer.getvalue().splitlines()
                  if "gesperrt durch" in z]
        self.assertEqual(len(zeilen), 1, zeilen)
        gruende = [g.strip() for g in zeilen[0].split(":", 1)[-1].split(";")]
        self.assertEqual(len(gruende), 1, gruende)
        self.assertNotIn("Freigabefenster", zeilen[0])

    def test_papierlauf_druckt_den_verweigerungstext_nicht(self):
        """Im Papierlauf darf die Sperrzeile nicht stehen.

        Der Dauerlauf schickt jede Ausgabezeile mit dem Wort "gesperrt" nach
        Telegram (dauerlauf.zyklus) - bei einem Lauf alle 15 Minuten war das
        Spam (aufgefallen 13.09.2026). Gelesen wird die Zeile nur mit
        --vorschau.
        """
        z = {"positionen": [], "letzter_lauf": sp._jetzt()}
        with patch.object(sp, "lade_zustand", return_value=z), \
                patch.object(sp, "signale_sammeln", return_value=[]), \
                patch.object(sp, "_gefolgt", return_value={("solana", "W1"): {}}):
            puffer = io.StringIO()
            with patch("sys.stdout", puffer):
                sp.lauf("papier")
        self.assertNotIn("gesperrt", puffer.getvalue(), puffer.getvalue())

    def test_vorschau_schreibt_nichts(self):
        """Die Vorschau darf das Buch nicht anfassen.

        Ohne das schloss sie Kopien im Journal, die im Zustand offen blieben -
        zwei Wahrheiten, und die Vorschau waere keine Vorschau mehr.
        """
        # Frischer Herzschlag, sonst greift zuerst der Notausstieg und der Test
        # prueft die falsche Stelle.
        z = {"positionen": [kopie(frist="2000-01-01T00:00:00+00:00")],
             "letzter_lauf": sp._jetzt()}
        with patch.object(sp, "lade_zustand", return_value=z), \
                patch.object(sp, "signale_sammeln", return_value=[SIGNAL]), \
                patch.object(sp.lesen, "preise",
                             return_value={("solana", "T1"): 1.05}), \
                patch.object(sp.lesen, "risiko",
                             return_value={"stufe": "safe", "merkmale": []}), \
                patch.object(sp, "_gefolgt",
                             return_value={("solana", "W1"): {}}):
            puffer = io.StringIO()
            with patch("sys.stdout", puffer):
                sp.lauf("vorschau")
        self.assertEqual(self.journal(), [], "kein Journal in der Vorschau")
        self.assertFalse(os.path.exists(sp.ZUSTAND),
                         "kein Zustand in der Vorschau")
        text = puffer.getvalue()
        # Die Vorschau muss ihren Ausstieg als Ausstieg zeigen UND als Vorschau
        # erkennbar bleiben (vorher: "WAERE ZU"). Nur die Marke hat sich
        # geaendert - der Dauerlauf braucht das neutrale Wort "AUSSTIEG".
        self.assertIn("AUSSTIEG (", text)
        self.assertIn("[nur Vorschau]", text)

    def test_leere_verfolgungsliste_verhindert_den_lauf(self):
        with io.open(sp.VERFOLGTE, "w", encoding="utf-8") as f:
            json.dump({"wallets": []}, f)
        z = {"positionen": [], "letzter_lauf": None}
        with patch.object(sp, "lade_zustand", return_value=z):
            self.assertEqual(sp.lauf("papier"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
