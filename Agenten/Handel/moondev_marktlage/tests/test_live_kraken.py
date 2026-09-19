"""Tests fuer den moonev_marktlage LIVE-Zweig (live_kraken.py).

Der erste echte Geldpfad - diese Tests muessen ohne Netz laufen und
DUERFEN NIE in echte Dateien schreiben (keine echte Instanz/Order).
Deshalb: live_kraken.ZUSTAND/JOURNAL auf einen Temp-Ordner umgebogen,
kraken-Orderfunktionen durch Stubs ersetzt.

Aufruf aus diesem Verzeichnis:  python -m unittest test_live_kraken
"""
import json
import os
import sys
import tempfile
import unittest

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
        lk.sitzung_da = lambda: False
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


if __name__ == "__main__":
    unittest.main()