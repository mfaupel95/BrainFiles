"""Sperrfrist nach einem Ziel-Ausstieg (Auftrag Max 23.09.2026 "Sperrfrist 2h").

Befund: ZEC wurde live im Ziel verkauft (1618.36) und acht Sekunden spaeter zum
fast selben Kurs neu gekauft (1619.38) - 1,2 % Gebuehren fuer dieselbe Bewegung,
weil der Kandidat weiter auf der Rangliste stand. Ein Ziel-Ausstieg heisst, der
geplante Gewinn ist da; sofort wieder einzusteigen ist kein neues Signal.

Diese Tests laufen ohne Netz und schreiben in KEINE echte Datei: journal,
Protokoll, Ablehnungen und der Zustand werden umgebogen.
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SPUR)
import handeln as h  # noqa: E402

assert h.__file__.startswith(SPUR), h.__file__

WACHEN = {"max_offene_positionen": 5, "max_gesamt_usd": 600.0,
          "abklingzeit_tage": 4, "sperrfrist_nach_ziel_stunden": 2.0,
          "gebuehr_pct": 0.006, "pflicht_stop_prozent_min": 5.0,
          "risiko_je_position_usd": 6.0, "max_pro_trade_usd": 120.0}


def vor(stunden):
    return (datetime.now(timezone.utc)
            - timedelta(hours=stunden)).isoformat(timespec="seconds")


class Base(unittest.TestCase):
    """Patcht alles, was nach draussen schreiben koennte."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = {}
        for name in ("journal", "protokolliere", "protokolliere_kandidat",
                     "journal_ablehnung", "schreibe_zustand", "_spiegeln",
                     "okx", "ZUSTAND", "JOURNAL", "ABLEHNUNGEN"):
            if hasattr(h, name):
                self.alt[name] = getattr(h, name)
        self.geschrieben = []
        h.journal = lambda *a, **k: self.geschrieben.append(a)
        h.protokolliere = lambda *a, **k: None
        h.protokolliere_kandidat = lambda *a, **k: None
        h.journal_ablehnung = lambda **k: None
        h.schreibe_zustand = lambda z: None
        h._spiegeln = lambda w: None
        self.kaeufe = []
        h.okx = type("FakeOKX", (), {
            "letzter_kurs": staticmethod(lambda inst: self.kurs_je_inst.get(inst, 100.0)),
            "markt_kauf": staticmethod(lambda inst, usd: (self.kaeufe.append((inst, usd)) or "TX")),
            "order_details": staticmethod(lambda inst, oid: {"accFillSz": "1.0"}),
            "stop_setzen": staticmethod(lambda inst, menge, stop: "STOP"),
            "stop_stornieren": staticmethod(lambda oid: oid),
            "stop_details": staticmethod(lambda oid: {"accFillSz": "0"}),
            "guthaben_usdt": staticmethod(lambda: 1000.0),
            "quote": staticmethod(lambda inst: inst.split("-")[-1] if inst and "-" in inst else ""),
        })()
        self.kurs_je_inst = {}

    def tearDown(self):
        for name, wert in self.alt.items():
            setattr(h, name, wert)
        self.tmp.cleanup()


class ZielMerkenTest(Base):
    """Ein Ausstieg im Ziel muss die Sperrfrist starten."""

    def test_zielausstieg_setzt_die_sperre(self):
        z = {"positionen": [{"inst": "ZEC-USDC", "einstieg": 100.0,
                             "usd": 65.96, "stop": 90.0, "ziel": 105.0,
                             "eroeffnet": h._heute()}],
             "letzte_stops": {}, "letzte_ziele": {}}
        self.kurs_je_inst["ZEC-USDC"] = 110.0        # ueber dem Ziel
        h.pruefe_ausstiege(z, live=False)
        self.assertEqual(z["positionen"], [])
        self.assertIn("ZEC-USDC", z["letzte_ziele"])
        self.assertEqual(len(self.geschrieben), 1)
        self.assertEqual(self.geschrieben[0][8], "ziel")

    def test_stopausstieg_setzt_die_abklingzeit_nicht_die_zielsperre(self):
        z = {"positionen": [{"inst": "ZEC-USDC", "einstieg": 100.0,
                             "usd": 65.96, "stop": 90.0, "ziel": 105.0,
                             "eroeffnet": h._heute()}],
             "letzte_stops": {}, "letzte_ziele": {}}
        self.kurs_je_inst["ZEC-USDC"] = 85.0         # unter dem Stop
        h.pruefe_ausstiege(z, live=False)
        self.assertIn("ZEC-USDC", z["letzte_stops"])
        self.assertEqual(z["letzte_ziele"], {})

    def test_ohne_zustandsfeld_kein_absturz(self):
        # Alte zustand.json kennt letzte_ziele nicht.
        z = {"positionen": [{"inst": "ZEC-USDC", "einstieg": 100.0,
                             "usd": 65.96, "stop": 90.0, "ziel": 105.0,
                             "eroeffnet": h._heute()}],
             "letzte_stops": {}}
        self.kurs_je_inst["ZEC-USDC"] = 110.0
        h.pruefe_ausstiege(z, live=False)
        self.assertIn("ZEC-USDC", z["letzte_ziele"])


class SperrfristTest(Base):
    def test_ohne_angabe_ist_die_sperre_aus(self):
        w = dict(WACHEN, sperrfrist_nach_ziel_stunden=0)
        self.assertFalse(h.in_zielsperre("ZEC-USDC",
                                         {"letzte_ziele": {"ZEC-USDC": vor(0.1)}}, w))

    def test_frische_sperre_greift(self):
        z = {"letzte_ziele": {"ZEC-USDC": vor(0.1)}}
        self.assertTrue(h.in_zielsperre("ZEC-USDC", z, WACHEN))

    def test_nach_zwei_stunden_ist_sie_vorbei(self):
        z = {"letzte_ziele": {"ZEC-USDC": vor(2.5)}}
        self.assertFalse(h.in_zielsperre("ZEC-USDC", z, WACHEN))

    def test_anderes_instrument_ist_nicht_gesperrt(self):
        z = {"letzte_ziele": {"ZEC-USDC": vor(0.1)}}
        self.assertFalse(h.in_zielsperre("SOL-USDC", z, WACHEN))

    def test_kaputter_zeitstempel_sperrt_nicht_dauerhaft(self):
        z = {"letzte_ziele": {"ZEC-USDC": "kein datum"}}
        self.assertFalse(h.in_zielsperre("ZEC-USDC", z, WACHEN))

    def test_fehlendes_feld_ist_kein_fehler(self):
        self.assertFalse(h.in_zielsperre("ZEC-USDC", {}, WACHEN))


class EinstiegTest(Base):
    def kandidat(self, inst="ZEC-USDC"):
        return {"inst": inst, "usd": 120.0, "einstieg": 100.0,
                "stop": 95.0, "ziel": 110.0, "score": 67.8,
                "stop_pct": 5.0}

    def test_gesperrter_kandidat_wird_nicht_gekauft(self):
        z = {"positionen": [], "letzte_stops": {},
             "letzte_ziele": {"ZEC-USDC": vor(0.5)}}
        h.pruefe_einstiege(z, [self.kandidat()], WACHEN, live=True)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self.kaeufe, [], "kein Kauf in der Sperrfrist")

    def test_nach_der_sperrfrist_wird_gekauft(self):
        z = {"positionen": [], "letzte_stops": {},
             "letzte_ziele": {"ZEC-USDC": vor(3.0)}}
        h.pruefe_einstiege(z, [self.kandidat()], WACHEN, live=True)
        self.assertEqual([p["inst"] for p in z["positionen"]], ["ZEC-USDC"])
        self.assertEqual(len(self.kaeufe), 1)


if __name__ == "__main__":
    unittest.main()