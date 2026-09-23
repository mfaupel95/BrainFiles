"""Tests fuer den moonev_marktlage LIVE-Zweig (live_kraken.py).

Der erste echte Geldpfad - diese Tests muessen ohne Netz laufen und
DUERFEN NIE in echte Dateien schreiben (keine echte Instanz/Order).
Deshalb: live_kraken.ZUSTAND/JOURNAL auf einen Temp-Ordner umgebogen,
kraken-Orderfunktionen durch Stubs ersetzt.

Aufruf aus diesem Verzeichnis:  python -m unittest test_live_kraken
"""
import builtins
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SPUR)

import live_kraken as lk  # noqa: E402

# --- Test-Helper ------------------------------------------------------------


def stub_kraken(module):
    """Ersetzt Order-Kontakte durch lokale Stubs (kein Netz, keine Order)."""
    module.kraken.schluessel_vorhanden = lambda: True
    module.kraken.markt_kauf = lambda pair, menge, echt=False: "TX-TEST"
    module.kraken.markt_verkauf = lambda pair, menge, echt=False: "TX-TEST2"
    module.kraken.stop_setzen = lambda pair, menge, stop, echt=False: "TX-STOP"
    module.kraken.gefuellte_menge = lambda txid: 0.0001
    module.kraken.letzter_kurs = lambda pair: 81741.4
    module.kraken.paar_info = lambda pair: {
        "mengen_stellen": 8, "mindestmenge": 0.00005, "mindestwert": 0.5}
    module.kraken.guthaben = lambda waehrung="ZEUR": 500.0


class LiveBase(unittest.TestCase):
    def setUp(self):
        # Eigener Temp-Bereich: NIE in die echten Spurdateien schreiben.
        self.tmp = tempfile.TemporaryDirectory()
        zustand = os.path.join(self.tmp.name, "zustand.live.json")
        journal = os.path.join(self.tmp.name, "handelsjournal.live.csv")
        self._alt = (lk.ZUSTAND, lk.JOURNAL)
        lk.ZUSTAND, lk.JOURNAL = zustand, journal
        self._sun_alt = lk.sitzung_da
        self._frei_alt = lk.hole_freigabe
        self._lw_alt = lk._lade_wachen if hasattr(lk, "_lade_wachen") else lk.lade_wachen
        stub_kraken(lk)

    def tearDown(self):
        lk.ZUSTAND, lk.JOURNAL = self._alt
        lk.sitzung_da = self._sun_alt
        lk.hole_freigabe = self._frei_alt
        lk.lade_wachen = self._lw_alt
        self.tmp.cleanup()


# --- Tests -------------------------------------------------------------------


class SignalTest(LiveBase):
    def test_long_wenn_breit_und_weiss(self):
        lk.daten_holen = lambda w: ({"BTC": {"btc_aenderung_24h": 3.0, "breite": 0.8}},
                                    {"BTC": 1.0}, [])
        long, staerke = lk.signal({"btc_schwelle_pct": 2.0})
        self.assertTrue(long)
        self.assertIsNotNone(staerke)

    def test_kein_signal_unter_schwelle(self):
        lk.daten_holen = lambda w: ({"BTC": {"btc_aenderung_24h": 1.0, "breite": 0.5}},
                                    {"BTC": 1.0}, [])
        self.assertIsNone(lk.signal({"btc_schwelle_pct": 2.0})[0])


class SignalStaerkeTest(LiveBase):
    def test_min_bei_schwelle(self):
        self.assertEqual(lk.signalstaerke({"pct": 2.0, "breite": 0.60}), 10.0)

    def test_max_bei_vollem_signal(self):
        self.assertEqual(lk.signalstaerke({"pct": 6.0, "breite": 1.00}), 30.0)

    def test_dazwischen_linear(self):
        v1 = lk.signalstaerke({"pct": 4.0, "breite": 0.80})
        self.assertGreater(v1, 10.0)
        self.assertLess(v1, 30.0)

    def test_unter_schwelle_kein_kauf_min(self):
        self.assertEqual(lk.signalstaerke({"pct": 1.5, "breite": 0.5}), 10.0)


class SperrenTest(LiveBase):
    def test_sperre_ohne_freigabe(self):
        lk.sitzung_da = lambda: True
        w = {"handel_erlaubt": False, "journal_zweitziel": self.tmp.name}
        z = {"positionen": []}
        gruende = lk.live_sperren(w, z)
        kombi = " ".join(gruende).lower()
        self.assertTrue(any("handel_erlaubt" in g.lower() for g in gruende))
        self.assertTrue(any("freigabe" in g.lower() for g in gruende))

    def test_sperre_ohne_freigabefenster(self):
        # Der ECHTE Zustand darf hier nicht mitreden: laeuft die Spur live, ist
        # ihr Freigabefenster offen - dann fehlt der Grund zu Recht, und der
        # Test meldete einen gesunden Betrieb als Fehler. Geprueft wird die
        # Regel: keine Sitzung UND kein Zeitfenster = gesperrt.
        self.addCleanup(setattr, lk, "sitzung_da", lk.sitzung_da)
        self.addCleanup(setattr, lk, "zeitfenster_offen", lk.zeitfenster_offen)
        lk.sitzung_da = lambda: False
        lk.zeitfenster_offen = lambda: False
        w = {"handel_erlaubt": True, "journal_zweitziel": self.tmp.name}
        z = {"positionen": []}
        gruende = lk.live_sperren(w, z)
        self.assertTrue(any("sitzung" in g.lower() for g in gruende))


class MengeTest(LiveBase):
    def test_menge_fuer_10eur(self):
        menge, fehler = lk.menge_fuer(10.0, 81741.4)
        self.assertIsNone(fehler)
        self.assertGreater(menge, 0)
        self.assertLess(menge, 0.001)

    def test_unter_mindestwert_gibt_fehler(self):
        # Kurs extrem hoch -> Wert unter 0.5 EUR
        menge, fehler = lk.menge_fuer(0.1, 81741.4)
        self.assertIsNotNone(fehler)


class JournalTest(LiveBase):
    def test_journal_schreibt(self):
        lk.journal(zeit="Z", modus="live", aktion="kauf", pair="XBTUSD",
                   seite="long", preis="81741.4", eur="10.00", menge="0.000122",
                   stop="76835.0", ziel="94165.0", grund="g")
        self.assertTrue(os.path.exists(lk.JOURNAL))
        with open(lk.JOURNAL, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("kauf", text)
        self.assertIn("10.00", text)


class FreigabeDurchlaufTest(LiveBase):
    """Der bestaetigte Auftrag traegt gebunden/stop/ziel (vom Fenster
    berechnet). pruefe_einstiege MUSS diese uebernehmen - beim ersten
    Geldpfad darf nichts anderes als das Bestaetigte ausgefuehrt werden."""

    def setUp(self):
        super().setUp()
        self._signal_alt = lk.signal
        lk.signal = lambda w: (True, {"pct": 4.0, "breite": 0.8})
        lk.hole_freigabe = lambda v, z, s: [
            {"inst": "XBTUSD", "einstieg": 81741.4, "stop_pct": 6.0,
             "cr": 2.0, "gebunden": 20.0, "stop": 76835.0, "ziel": 96653.0}]

    def tearDown(self):
        lk.signal = self._signal_alt
        super().tearDown()

    def test_uebernimmt_bestaetigte_werte(self):
        z = {"positionen": []}
        w = {"max_offene_positionen": 1, "stop_prozent": 6.0, "cr": 2.0}
        lk.pruefe_einstiege(z, w, live=False)
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        # Nicht meine 10-EUR-Vorgabe, sondern die bestaetigten 20 EUR:
        self.assertAlmostEqual(p["eur"], 20.0)
        self.assertAlmostEqual(p["stop"], 76835.0)
        self.assertAlmostEqual(p["ziel"], 96653.0)

    def test_abgelehnt_kein_eintrag(self):
        lk.hole_freigabe = lambda v, z, s: []
        z = {"positionen": []}
        w = {"max_offene_positionen": 1}
        lk.pruefe_einstiege(z, w, live=False)
        self.assertEqual(len(z["positionen"]), 0)


class Verdrahtung(unittest.TestCase):
    """Der Live-Zweig muss im DAUERLAUF funktionieren (22.09.2026, Auftrag Max
    "Ja kraken verdrahten"). Drei Dinge fehlten dafuer:

      1. `sitzung_da()` ist unter MAXHIRN_ROUTINE=1 immer False -> ohne das
         Zeitfenster (freigabefenster.py) konnte die Spur NIE live gehen.
      2. Das Fenster stand auf "kraken" - ein Fenster der Haus-Spur haette
         diese mit scharf geschaltet.
      3. Der alte Herzschlag schrieb den Zustand NICHT -> die Sperre blieb fuer
         immer zu (Deadlock: der Herzschlag kommt aus zustand.letzter_lauf).
    """

    def setUp(self):
        self.gedruckt = []
        self.p = patch.object(builtins, "print",
                              side_effect=lambda *a, **k: self.gedruckt.append(
                                  " ".join(str(x) for x in a)))
        self.p.start()
        self.addCleanup(self.p.stop)

    def _text(self):
        return "\n".join(self.gedruckt)

    def test_sperrenzeile_nennt_einen_lesbaren_grund(self):
        self.addCleanup(setattr, lk, "live_sperren", lk.live_sperren)
        lk.live_sperren = lambda w, z: ["Freigabefenster nicht offen - keine "
                                        "Sitzung am Bildschirm und kein Zeitfenster"]
        gruende = lk.sperren_zeile()
        self.assertEqual(len(gruende), 1)
        self.assertIn("Live waere gesperrt durch: Freigabefenster", self._text())

    def test_zeitfenster_folgt_dem_fenster(self):
        self.addCleanup(setattr, lk, "freigabefenster", lk.freigabefenster)

        class Fenster:
            offen_wert = False

            def lade(self, spur):
                assert spur == "moondev_marktlage", "eigener Spurname erwartet"
                return self

            def offen(self):
                return Fenster.offen_wert

        lk.freigabefenster = Fenster()
        self.assertFalse(lk.zeitfenster_offen())
        Fenster.offen_wert = True
        self.assertTrue(lk.zeitfenster_offen())

    def test_lesefehler_gilt_als_zu(self):
        self.addCleanup(setattr, lk, "freigabefenster", lk.freigabefenster)

        class Kaputt:
            def lade(self, spur):
                raise RuntimeError("Datei kaputt")

        lk.freigabefenster = Kaputt()
        self.assertFalse(lk.zeitfenster_offen())

    def _umgebung(self, frisch=False, kill=False):
        """Alles, was `lauf()` anfasst, lokal ersetzen - kein Netz, keine Datei."""
        stub_kraken(lk)
        self.addCleanup(setattr, lk, "schreibe_zustand", lk.schreibe_zustand)
        self.addCleanup(setattr, lk, "lade_wachen", lk.lade_wachen)
        self.addCleanup(setattr, lk, "lade_zustand", lk.lade_zustand)
        self.addCleanup(setattr, lk.wp, "lage", lk.wp.lage)
        lk.lade_wachen = lambda: {"herzschlag_max_minuten": 180,
                                  "journal_zweitziel": None,
                                  "max_offene_positionen": 1,
                                  "mindest_guthaben_eur": 0}
        lk.lade_zustand = lambda: {"positionen": []}
        lk.wp.lage = lambda w, j, z: {
            "herzschlag_frisch": frisch, "kill": kill, "ruecklauf_eur": 0.0,
            "freigabe_erfuellt": True, "ev_negativ": False,
            "rollierender_ev": 0.0}

    def test_alter_herzschlag_schreibt_trotzdem(self):
        """Der Deadlock: ohne diesen Schreibvorgang heilt die Sperre nie."""
        geschrieben = []
        self._umgebung(frisch=False)
        lk.schreibe_zustand = lambda z: geschrieben.append(z)
        lk.lauf("live")
        self.assertEqual(len(geschrieben), 1,
                         "Herzschlag muss geschrieben werden, sonst Deadlock")

    def test_vorschau_schreibt_und_handelt_nicht(self):
        geschrieben, ausstiege = [], []
        self._umgebung(frisch=False)
        self.addCleanup(setattr, lk, "pruefe_ausstiege", lk.pruefe_ausstiege)
        self.addCleanup(setattr, lk, "pruefe_einstiege", lk.pruefe_einstiege)
        lk.schreibe_zustand = lambda z: geschrieben.append(z)
        lk.pruefe_ausstiege = lambda z, w, live: ausstiege.append(1)
        lk.pruefe_einstiege = lambda z, w, live: ausstiege.append(2)
        lk.lauf("vorschau")
        self.assertEqual(geschrieben, [], "die Vorschau schreibt keinen Zustand")
        self.assertEqual(ausstiege, [], "die Vorschau handelt nicht")
        self.assertIn("Live waere gesperrt durch:", self._text())


class EinsatzDeckelungTest(unittest.TestCase):
    """Der Einsatz darf nie groesser sein als das freie Guthaben.

    Anlass 23.09.2026 (Auftrag Max "Marktlage 70"): 88.56 EUR frei, mindestens
    noetig 100 -> der Live-Zweig war dauerhaft gesperrt. Die Schwelle ist jetzt
    70, und der Einsatz wird zusaetzlich auf das freie Guthaben gedeckelt -
    ein Signal von 150 EUR bei 88 EUR frei waere sonst eine abgelehnte Order,
    kein Handel.
    """

    def setUp(self):
        self.alt = lk.kraken.guthaben

    def tearDown(self):
        lk.kraken.guthaben = self.alt

    def wachen(self, **a):
        w = {"live_einsatz_min_eur": 60.0, "live_einsatz_max_eur": 150.0,
             "gebuehr_taker": 0.006}
        w.update(a)
        return w

    def test_deckelt_auf_das_freie_guthaben(self):
        lk.kraken.guthaben = lambda ccy="ZEUR": 88.56
        eur, hinweis = lk.einsatz_gedeckelt(150.0, self.wachen())
        self.assertLessEqual(eur, 88.56)
        self.assertGreater(eur, 87.0)
        self.assertIn("gedeckelt", hinweis)

    def test_kleiner_einsatz_bleibt_unveraendert(self):
        lk.kraken.guthaben = lambda ccy="ZEUR": 500.0
        eur, hinweis = lk.einsatz_gedeckelt(60.0, self.wachen())
        self.assertEqual(eur, 60.0)
        self.assertIsNone(hinweis)

    def test_unlesbares_guthaben_aendert_nichts(self):
        def kaputt(ccy="ZEUR"):
            raise RuntimeError("Netz weg")
        lk.kraken.guthaben = kaputt
        eur, hinweis = lk.einsatz_gedeckelt(120.0, self.wachen())
        self.assertEqual(eur, 120.0)
        self.assertIn("nicht abrufbar", hinweis)

    def test_kein_guthaben_meldet_statt_zu_raten(self):
        lk.kraken.guthaben = lambda ccy="ZEUR": 0.0
        eur, hinweis = lk.einsatz_gedeckelt(120.0, self.wachen())
        self.assertEqual(eur, 120.0)
        self.assertIn("kein freies", hinweis)

    def test_gebuehr_und_luft_sind_eingerechnet(self):
        lk.kraken.guthaben = lambda ccy="ZEUR": 100.0
        eur, _ = lk.einsatz_gedeckelt(150.0, self.wachen(gebuehr_taker=0.01))
        self.assertAlmostEqual(eur, 100.0 * (1 - 0.01 - 0.002), places=6)


class HerzschlagQuelleTest(unittest.TestCase):
    """Der Herzschlag kommt aus dem FRISCHESTEN Zustand (Papier oder Live).

    Befund 23.09.2026: die Spur lief alle 15 Minuten live, ihr Papierzustand
    stand aber seit dem 22.09. 21:12 still - nach herzschlag_max_minuten sperrte
    sie sich damit selbst ("Live waere gesperrt durch: Herzschlag alt").
    Umgekehrt darf eine Spur, die NOCH NIE live lief, nicht gesperrt sein -
    deshalb zaehlen beide Staende.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = lk.HIER
        lk.HIER = self.tmp.name
        self.addCleanup(setattr, lk, "HIER", self.alt)

    def _schreibe(self, name, letzter):
        with open(os.path.join(self.tmp.name, name), "w",
                  encoding="utf-8") as f:
            json.dump({"letzter_lauf": letzter, "positionen": []}, f)

    def test_frischer_live_zustand_schlaegt_alten_papierzustand(self):
        self._schreibe("zustand.json", "2026-09-22T19:12:16+00:00")
        self._schreibe("zustand.live.json", "2026-09-23T05:42:11+00:00")
        self.assertEqual(lk._papier_zustand()["letzter_lauf"],
                         "2026-09-23T05:42:11+00:00")

    def test_frischer_papierzustand_zaehlt_weiter(self):
        # Eine Spur, die noch nie live lief, muss sich scharf machen koennen.
        self._schreibe("zustand.json", "2026-09-23T05:50:00+00:00")
        self._schreibe("zustand.live.json", "2026-09-20T05:42:11+00:00")
        self.assertEqual(lk._papier_zustand()["letzter_lauf"],
                         "2026-09-23T05:50:00+00:00")

    def test_ohne_dateien_kein_herzschlag(self):
        self.assertIsNone(lk._papier_zustand().get("letzter_lauf"))

    def test_kaputte_datei_wird_uebersprungen(self):
        self._schreibe("zustand.json", "2026-09-23T05:50:00+00:00")
        with open(os.path.join(self.tmp.name, "zustand.live.json"), "w") as f:
            f.write("{ kein json")
        self.assertEqual(lk._papier_zustand()["letzter_lauf"],
                         "2026-09-23T05:50:00+00:00")


if __name__ == "__main__":
    unittest.main()