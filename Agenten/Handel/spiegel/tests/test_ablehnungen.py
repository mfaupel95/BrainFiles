"""Tests fuer das Ablehnungsprotokoll (ablehnungen.csv).

Warum es das Protokoll gibt: das Journal haelt nur, was GEBUCHT wurde. Aus den
107 geschlossenen Runden vom September 2026 war noch abzuleiten, in welchem
Band das Buch getragen hat - aber nicht, wie viele Kandidaten an welchem Tor
haengen blieben. Ein volles Buch und ein zu strenges Tor sahen im Journal
gleich aus. Geprueft wird hier, was das Protokoll daraus macht:

  * jeder abgelehnte Kandidat steht mit Grund darin (nicht nur als Zahl),
  * dasselbe Signal steht nicht in jedem Zyklus erneut darin,
  * ein volles Buch zaehlt die Kandidaten, die es nicht mehr erreicht hat,
  * die gedruckte Zeile traegt kein Stichwort des Dauerlaufs (sonst Spam),
  * die Vorschau schreibt nichts, der Notausstieg spiegelt auch,
  * die Ablehnungs-Bilanz liest das Protokoll richtig.

Aufruf (aus dem Ordner spiegel/):
    <scanner-venv>/python.exe -m unittest discover -s tests -t tests
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

import spiegel as sp                                              # noqa: E402

WACHEN_VORLAGE = json.load(io.open(os.path.join(SPIEGEL, "wachen.json"),
                                  encoding="utf-8"))

SIGNAL = {"quelle": "tracker/smart_money", "kette": "solana", "wallet": "W1",
          "token": "T1", "symbol": "AAA", "preis": 1.0, "zeit_ms": 0,
          "alter_s": 5.0, "marktkap_usd": 500000.0, "quote": "SOLANA",
          "tx": "TX1"}

FILTERWOERTER = ("verkauf", "stop", "kill", "gesperrt", "ausstieg")


class Grundlage(unittest.TestCase):
    """Jeder Test arbeitet in einem eigenen Ordner - nichts am echten Buch."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (sp.ZUSTAND, sp.JOURNAL, sp.VERFOLGTE, sp.WACHEN,
                    sp.ABLEHNUNGEN)
        # SCHREIBEN ist modulweit: ohne diese Zeile schriebe diese Datei
        # nichts mehr, sobald eine Vorschau-Probe vorher gelaufen ist.
        self.alt_schreiben = sp.SCHREIBEN
        sp.SCHREIBEN = True
        sp.ZUSTAND = os.path.join(self.tmp.name, "zustand.json")
        sp.JOURNAL = os.path.join(self.tmp.name, "handelsjournal.csv")
        sp.VERFOLGTE = os.path.join(self.tmp.name, "verfolgte.json")
        sp.ABLEHNUNGEN = os.path.join(self.tmp.name, "ablehnungen.csv")
        self.alt_wachen = sp.WACHEN
        sp.WACHEN = os.path.join(self.tmp.name, "wachen.json")
        self.w = json.loads(json.dumps(WACHEN_VORLAGE))
        self.w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")
        self.schreibe_wachen()
        # Der Lauf baut eine zu alte Verfolgungsliste selbst aus dem Feed neu
        # (verfolgte_zu_alt): hier liegt gar keine, also griffe er zu. Im Test
        # waeren das echte Abrufe - deshalb stillgelegt.
        self.alt_waehlen = sp.waehlen
        sp.waehlen = lambda w: None

    def tearDown(self):
        sp.ZUSTAND, sp.JOURNAL, sp.VERFOLGTE, sp.WACHEN, sp.ABLEHNUNGEN = self.alt
        sp.SCHREIBEN = self.alt_schreiben
        sp.waehlen = self.alt_waehlen
        self.tmp.cleanup()

    def schreibe_wachen(self, **werte):
        self.w.update(werte)
        with io.open(sp.WACHEN, "w", encoding="utf-8") as f:
            json.dump(self.w, f, ensure_ascii=False, indent=2)

    def zeilen(self, pfad=None):
        pfad = pfad or sp.ABLEHNUNGEN
        if not os.path.exists(pfad):
            return []
        with open(pfad, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def je_grund(self, art):
        """{grund: summe(anzahl)} fuer eine Zeilenart."""
        aus = {}
        for z in self.zeilen():
            if z["art"] == art:
                aus[z["grund"]] = aus.get(z["grund"], 0) + int(z["anzahl"] or 0)
        return aus

    def papierlauf(self, signale, gefolgt=None, positionen=None, modus="papier"):
        z = {"positionen": positionen or [], "letzter_lauf": sp._jetzt()}
        gefolgt = gefolgt if gefolgt is not None else {("solana", "W1"): {}}
        puffer = io.StringIO()
        with patch.object(sp, "lade_zustand", return_value=z), \
                patch.object(sp, "signale_sammeln", return_value=signale), \
                patch.object(sp, "_gefolgt", return_value=gefolgt), \
                patch.object(sp.lesen, "preise", return_value={}):
            with contextlib.redirect_stdout(puffer):
                code = sp.lauf(modus)
        return code, puffer.getvalue(), z


class Protokoll(Grundlage):

    def test_jede_ablehnung_steht_mit_grund_im_protokoll(self):
        """Lage (Massenfaelle) und Entscheidung (bewertete Kandidaten) - beide
        mit Grund. Vorher stand nur die Zahl der Signale im Journal."""
        signale = [dict(SIGNAL, token="ALT", tx="T-alt", alter_s=999.0),
                   dict(SIGNAL, token="TEUER", tx="T-band",
                        marktkap_usd=5000000.0),
                   dict(SIGNAL, token="RISIKO", tx="T-risk")]
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "HIGH",
                                        "merkmale": ["isHoneypot"]}):
            code, aus, _ = self.papierlauf(signale)
        self.assertEqual(code, 0)

        lage = self.je_grund("zyklus")
        self.assertEqual(lage["Signale gesehen"], 3)
        self.assertEqual(lage["Lage: zu alt"], 1)
        self.assertEqual(lage["Lage: marktkap ausserhalb"], 1)
        self.assertEqual(lage["Lage: kaufbar"], 1)
        self.assertEqual(lage["Entscheidung: Risikostufe HIGH (isHoneypot)"], 1)

        einzeln = self.zeilen()
        kandidaten = [z for z in einzeln if z["art"] == "signal"]
        self.assertEqual(len(kandidaten), 1, einzeln)
        self.assertEqual(kandidaten[0]["token"], "RISIKO")
        self.assertEqual(kandidaten[0]["tx"], "T-risk")
        self.assertEqual(kandidaten[0]["symbol"], "AAA")
        self.assertEqual(kandidaten[0]["marktkap_usd"], "500000")

    def test_ein_kauf_steht_als_entscheidung_nicht_als_ablehnung(self):
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "safe", "merkmale": []}):
            code, aus, z = self.papierlauf([dict(SIGNAL)])
        self.assertEqual(code, 0)
        self.assertEqual(self.je_grund("zyklus")["Entscheidung: kopiert"], 1)
        self.assertEqual([z for z in self.zeilen() if z["art"] == "signal"], [])
        self.assertEqual(len(z["positionen"]), 1)

    def test_buch_voll_zaehlt_die_kandidaten_die_es_nicht_mehr_erreicht(self):
        """Ein volles Buch ist kein zu strenges Tor.

        Genau das war aus dem Journal nicht zu sehen: 20 offene Kopien, und
        jedes Signal des Zyklus fiel aus - ohne einen einzigen Grund in der
        Ablage.

        Gefuellt wird bis zu dem Wert, den der LAUF benutzt - nicht bis zu dem,
        der in der Datei steht: seit dem 14.09.2026 sammelt das Papierbuch mit
        mehr Plaetzen (spiegel._umfang). Ein Test, der die Rohzahl nimmt, misst
        an der falschen Grenze und wird gruen, ohne die Stelle zu treffen.
        """
        grenze = sp._umfang(self.w, "papier")["max_offen"]
        voll = [{"kette": "solana", "wallet": "W%d" % i, "token": "T%d" % i,
                 "symbol": "AAA", "einsatz_usd": 50.0, "menge": 1.0,
                 "preis_vorbild": 1.0, "preis_einstieg": 1.0,
                 "marktkap_usd": 100000.0, "risiko": "safe",
                 "stop_preis": 0.75, "ziel_preis": 1.6,
                 "frist": "2999-01-01T00:00:00+00:00", "eroeffnet": "2026-09-14",
                 "eroeffnet_zeit": "2026-09-14T00:00:00+00:00"}
                for i in range(grenze)]
        signale = [dict(SIGNAL, token="KAUFBAR", tx="T-1"),
                   dict(SIGNAL, token="ZUALT", tx="T-2", alter_s=9999.0)]
        code, aus, _ = self.papierlauf(signale, positionen=voll)
        self.assertEqual(code, 0)
        lage = self.je_grund("zyklus")
        self.assertEqual(lage["Entscheidung: Buch voll - Kandidat nicht "
                              "bewertet"], 1)
        self.assertEqual(lage["Lage: kaufbar"], 1)
        # Teilmenge, nicht zweite Zahl zum Addieren: "davon ..." steht im Namen.
        self.assertEqual(lage["Lage: davon kaufbar, aber nicht mehr erreicht"], 1)
        self.assertIn("Buch voll", aus)
        self.assertEqual([z for z in self.zeilen() if z["art"] == "signal"], [])

    def test_ein_nicht_verfolgtes_wallet_zaehlt_zur_lage_nicht_zur_entscheidung(self):
        """Jedes Signal landet in GENAU EINEM Lage-Zaehler.

        Sonst zaehlt es doppelt: am ersten echten Zyklus standen 11 Signale
        nicht verfolgter Wallets zugleich unter "kaufbar" und unter einer
        Entscheidung - und die Kontrollzeile ging nicht auf.
        """
        signale = [dict(SIGNAL, wallet="W9", token="T9", tx="T-9")]
        code, aus, _ = self.papierlauf(signale, gefolgt={("solana", "W1"): {}})
        self.assertEqual(code, 0)
        lage = self.je_grund("zyklus")
        self.assertEqual(lage["Lage: wallet nicht verfolgt"], 1)
        self.assertNotIn("Lage: kaufbar", lage)
        self.assertNotIn("Entscheidung: Wallet nicht verfolgt", lage)

    def test_die_zaehler_gehen_auf(self):
        """Die Kontrollzeile von --ablehnungen muss aus dem Zyklus heraus
        stimmen: kaufbar = bewertet + nicht mehr erreicht."""
        signale = [dict(SIGNAL, token="A", tx="T-a"),
                   dict(SIGNAL, token="B", wallet="W9", tx="T-b"),
                   dict(SIGNAL, token="C", tx="T-c", alter_s=999.0)]
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "safe", "merkmale": []}):
            self.papierlauf(signale)
        lage = self.je_grund("zyklus")
        kaufbar = lage["Lage: kaufbar"]
        bewertet = lage["Entscheidung: kopiert"]
        nicht = lage.get("Lage: davon kaufbar, aber nicht mehr erreicht", 0)
        self.assertEqual(kaufbar, bewertet + nicht, lage)

    def test_dasselbe_signal_wird_nicht_in_jedem_zyklus_erneut_protokolliert(self):
        """Der Feed reicht Stunden zurueck - ohne die Sperre stuende derselbe
        Kandidat alle 15 Minuten erneut im Protokoll, und die Zaehlung waere
        ein Vielfaches der Wahrheit."""
        signale = [dict(SIGNAL, token="RISIKO", tx="T-risk")]
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "HIGH",
                                        "merkmale": ["isHoneypot"]}):
            self.papierlauf(signale)
            self.papierlauf(signale)
        kandidaten = [z for z in self.zeilen() if z["art"] == "signal"]
        self.assertEqual(len(kandidaten), 1, kandidaten)
        # Die Zyklus-Zeilen entstehen trotzdem in jedem Zyklus: die Lage wird
        # je Zyklus neu gezaehlt.
        self.assertEqual(self.je_grund("zyklus")["Signale gesehen"], 2)

    def test_ein_zweiter_grund_ist_eine_eigene_zeile(self):
        """Die Sperre gilt je (Transaktion, Grund), nicht je Signal: kommt
        dasselbe Signal spaeter mit einem ANDEREN Grund, ist das eine neue
        Aussage - keine Wiederholung."""
        with patch.object(sp.lesen, "risiko",
                          side_effect=sp.lesen.Lesefehler("Feed weg")):
            self.papierlauf([dict(SIGNAL, token="T9", tx="T-9")])
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "HIGH",
                                        "merkmale": ["isHoneypot"]}):
            self.papierlauf([dict(SIGNAL, token="T9", tx="T-9")])
        gruende = [z["grund"] for z in self.zeilen() if z["art"] == "signal"]
        self.assertEqual(len(gruende), 2, gruende)
        self.assertTrue(any("nicht moeglich" in g for g in gruende), gruende)
        self.assertTrue(any("Risikostufe" in g for g in gruende), gruende)


class Ausgabe(Grundlage):

    def test_gedruckte_ablehnung_traegt_kein_stichwort_des_dauerlaufs(self):
        """Gerendert, nicht gelesen: die Zeile, die der Mensch sieht.

        Der Dauerlauf schickt jede Ausgabezeile mit einem Stichwort nach
        Telegram - eine Ablehnung ist keine Meldung wert.
        """
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "HIGH",
                                        "merkmale": ["isHoneypot"]}):
            _, aus, _ = self.papierlauf([dict(SIGNAL, token="RISIKO",
                                              tx="T-risk")])
        nein = [z for z in aus.splitlines() if z.strip().startswith("NEIN")]
        self.assertEqual(len(nein), 1, aus)
        self.assertIn("AAA", nein[0])
        self.assertIn("RISIKO", nein[0])
        self.assertIn("Risikostufe HIGH", nein[0])
        for wort in FILTERWOERTER:
            self.assertNotIn(wort, nein[0].lower(), nein[0])

    def test_dieselbe_zeile_steht_nicht_zweimal_in_der_ausgabe(self):
        signale = [dict(SIGNAL, token="RISIKO", tx="T-risk")]
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "HIGH",
                                        "merkmale": ["isHoneypot"]}):
            self.papierlauf(signale)
            _, aus, _ = self.papierlauf(signale)
        self.assertNotIn("NEIN", aus, aus)

    def test_die_vorschau_print_dieselbe_zeile_wie_der_papierlauf(self):
        """Zwei Wege, eine Formulierung - sonst liest sich derselbe Grund
        unterschiedlich, je nachdem wer ihn druckt."""
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "HIGH",
                                        "merkmale": ["isHoneypot"]}):
            _, papier, _ = self.papierlauf([dict(SIGNAL, token="R",
                                                 tx="T-r")])
            _, vorschau, _ = self.papierlauf([dict(SIGNAL, token="R",
                                                   tx="T-r")], modus="vorschau")
        zeile_p = [z for z in papier.splitlines() if "NEIN" in z][0]
        zeile_v = [z for z in vorschau.splitlines() if "NEIN" in z][0]
        self.assertEqual(zeile_p, zeile_v)


class EineFassungDerTore(Grundlage):

    def test_vorpruefung_und_kopie_nennen_denselben_grund(self):
        """Die Zaehlung darf keine zweite Fassung der Grenze sein."""
        faelle = ((dict(SIGNAL, alter_s=999.0), "zu alt"),
                  (dict(SIGNAL, marktkap_usd=None), "marktkap unbekannt"),
                  (dict(SIGNAL, marktkap_usd=1.0), "marktkap ausserhalb"),
                  (dict(SIGNAL), "token belegt"))
        for sig, erwartet in faelle:
            with self.subTest(erwartet=erwartet):
                z = {"positionen": []}
                if erwartet == "token belegt":
                    z = {"positionen": [{"kette": "solana", "wallet": "W2",
                                         "token": "T1"}] * self.w["max_kopien_je_token"]}
                schluessel, text = sp._vorpruefung(sig, self.w, z)
                self.assertEqual(schluessel, erwartet)
                p, grund = sp._kopie(sig, self.w, z)
                self.assertIsNone(p)
                self.assertEqual(grund, text)

    def test_ein_billiges_tor_kostet_keinen_abruf(self):
        """Wer erst nach dem Risiko-Scan ablehnt, zahlt fuer jedes Signal
        einen CLI-Aufruf - bei 700 Signalen je Zyklus ist das der Unterschied
        zwischen einem Zyklus von Sekunden und einem von Minuten."""
        def platzt(*a, **kw):
            raise AssertionError("Risiko-Scan fuer ein Signal, das schon am "
                                 "billigen Tor scheitert")

        with patch.object(sp.lesen, "risiko", platzt):
            for sig in (dict(SIGNAL, alter_s=999.0),
                        dict(SIGNAL, marktkap_usd=1.0),
                        dict(SIGNAL, marktkap_usd=None)):
                p, grund = sp._kopie(sig, self.w, {"positionen": []})
                self.assertIsNone(p, sig)
                self.assertTrue(grund)


class AblehnungsBilanz(Grundlage):

    def schreibe_protokoll(self, zeilen):
        with open(sp.ABLEHNUNGEN, "w", newline="", encoding="utf-8") as f:
            s = csv.DictWriter(f, fieldnames=sp.SPALTEN_ABLEHNUNG)
            s.writeheader()
            for z in zeilen:
                s.writerow({k: z.get(k, "") for k in sp.SPALTEN_ABLEHNUNG})

    def test_die_bilanz_zaehlt_lage_und_entscheidung_getrennt(self):
        jetzt = sp._jetzt()
        self.schreibe_protokoll([
            {"zeit": jetzt, "art": "zyklus", "grund": "Signale gesehen",
             "anzahl": 700},
            {"zeit": jetzt, "art": "zyklus", "grund": "Lage: zu alt",
             "anzahl": 600},
            {"zeit": jetzt, "art": "zyklus", "grund": "Lage: kaufbar",
             "anzahl": 40},
            {"zeit": jetzt, "art": "zyklus",
             "grund": "Entscheidung: Buch voll - Kandidat nicht bewertet",
             "anzahl": 1},
            {"zeit": jetzt, "art": "zyklus",
             "grund": "Lage: davon kaufbar, aber nicht mehr erreicht",
             "anzahl": 39},
            {"zeit": jetzt, "art": "zyklus", "grund": "Entscheidung: kopiert",
             "anzahl": 1},
            {"zeit": jetzt, "art": "signal", "grund": "Risikostufe HIGH (x)",
             "anzahl": 1, "token": "T1"},
        ])
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = sp.ablehnungsbilanz(24)
        text = puffer.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("600", text)
        self.assertIn("zu alt", text)
        self.assertIn("1 von 1 Zyklen", text)
        self.assertIn("Kontrolle: kaufbar 40 = bewertet 1 + nicht mehr "
                      "erreicht 39", text)
        self.assertIn("Risikostufe HIGH (x)", text)
        self.assertNotIn("Achtung", text)

    def test_die_bilanz_meldet_eine_luecke_statt_sie_zu_verschweigen(self):
        """Wenn die beiden Seiten nicht aufgehen, ist ein Zweig im Zyklus
        nicht gezaehlt - das gehoert gesagt, nicht gerundet."""
        jetzt = sp._jetzt()
        self.schreibe_protokoll([
            {"zeit": jetzt, "art": "zyklus", "grund": "Signale gesehen",
             "anzahl": 10},
            {"zeit": jetzt, "art": "zyklus", "grund": "Lage: kaufbar",
             "anzahl": 5},
        ])
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            sp.ablehnungsbilanz(24)
        self.assertIn("Achtung", puffer.getvalue())

    def test_ohne_protokoll_ist_die_bilanz_kein_absturz(self):
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = sp.ablehnungsbilanz(24)
        self.assertEqual(code, 1)
        self.assertIn("Noch kein Ablehnungsprotokoll", puffer.getvalue())

    def test_der_zeitraum_grenzt_die_zeilen(self):
        alt = "2020-01-01T00:00:00+00:00"
        neu = sp._jetzt()
        self.schreibe_protokoll([
            {"zeit": alt, "art": "zyklus", "grund": "Signale gesehen",
             "anzahl": 1},
            {"zeit": neu, "art": "zyklus", "grund": "Signale gesehen",
             "anzahl": 2},
        ])
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            sp.ablehnungsbilanz(24)
        self.assertIn("1 Zyklen", puffer.getvalue())


class Spiegelung(Grundlage):

    def test_das_protokoll_geht_mit_ausser_haus(self):
        """Bedingung 4 gilt fuer die neue Datei genauso: ein Protokoll, das
        nur hier liegt, ist beim Ausfall weg - und dann fehlt genau die
        Begruendung, die man spaeter braucht."""
        with patch.object(sp.lesen, "risiko",
                          return_value={"stufe": "safe", "merkmale": []}):
            self.papierlauf([dict(SIGNAL)])
        ziel = os.path.join(self.tmp.name, "zweitziel")
        self.assertTrue(os.path.exists(os.path.join(ziel, "ablehnungen.csv")),
                        os.listdir(ziel) if os.path.isdir(ziel) else ziel)
        self.assertTrue(os.path.exists(os.path.join(ziel,
                                                    "handelsjournal.csv")))

    def test_der_notausstieg_spiegelt_auch(self):
        """Herzschlag alt stellt das Buch flach - der Zustand aendert sich,
        also muss die Kopie ausser Haus mit. Bis zum 14.09.2026 spiegelte
        nur der normale Weg."""
        position = {"kette": "solana", "wallet": "W1", "token": "T1",
                    "symbol": "AAA", "einsatz_usd": 50.0, "menge": 1.0,
                    "preis_vorbild": 1.0, "preis_einstieg": 1.0,
                    "marktkap_usd": 100000.0, "risiko": "safe",
                    "stop_preis": 0.75, "ziel_preis": 1.6,
                    "frist": "2999-01-01T00:00:00+00:00",
                    "eroeffnet": "2026-09-01",
                    "eroeffnet_zeit": "2026-09-01T00:00:00+00:00"}
        z = {"positionen": [position], "letzter_lauf": "2020-01-01T00:00:00+00:00"}
        puffer = io.StringIO()
        with patch.object(sp, "lade_zustand", return_value=z), \
                patch.object(sp.lesen, "preise", return_value={}), \
                patch.object(sp, "signale_sammeln", return_value=[]), \
                patch.object(sp, "_gefolgt", return_value={("solana", "W1"): {}}):
            with contextlib.redirect_stdout(puffer):
                code = sp.lauf("papier")
        self.assertEqual(code, 0)
        self.assertIn("Herzschlag alt", puffer.getvalue())
        ziel = os.path.join(self.tmp.name, "zweitziel")
        self.assertTrue(os.path.exists(os.path.join(ziel, "zustand.json")),
                        os.listdir(ziel) if os.path.isdir(ziel) else ziel)

    def test_die_vorschau_kopiert_nichts(self):
        z = {"positionen": [{"kette": "solana", "wallet": "W1", "token": "T1",
                             "symbol": "AAA", "einsatz_usd": 50.0,
                             "menge": 1.0, "preis_vorbild": 1.0,
                             "preis_einstieg": 1.0, "marktkap_usd": 100000.0,
                             "risiko": "safe", "stop_preis": 0.75,
                             "ziel_preis": 1.6, "frist": "2020-01-01T00:00:00+00:00",
                             "eroeffnet": "2026-09-01",
                             "eroeffnet_zeit": "2026-09-01T00:00:00+00:00"}],
             "letzter_lauf": "2020-01-01T00:00:00+00:00"}
        puffer = io.StringIO()
        with patch.object(sp, "lade_zustand", return_value=z), \
                patch.object(sp.lesen, "preise", return_value={}), \
                patch.object(sp, "signale_sammeln", return_value=[]), \
                patch.object(sp, "_gefolgt", return_value={("solana", "W1"): {}}):
            with contextlib.redirect_stdout(puffer):
                sp.lauf("vorschau")
        ziel = os.path.join(self.tmp.name, "zweitziel")
        self.assertFalse(os.path.isdir(ziel) and os.listdir(ziel),
                         "Vorschau hat kopiert")


if __name__ == "__main__":
    unittest.main(verbosity=2)
