"""Tests fuer breite-wache.py - pruefen die REGELN, nicht die Zahlen.

Ohne Netz: `zeilen()` bekommt erfundene Messungen. Ein Test, der die echte
Breite prueft, waere jeden Tag rot oder gruen, ohne dass sich etwas geaendert
haette - hier wird nur geprueft, WANN gemeldet wird und WANN geschwiegen.

Aufruf: python -m unittest test_breite_wache   (aus Agenten/Hermes/scripts)
"""
import importlib.util
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))


def lade():
    spec = importlib.util.spec_from_file_location(
        "breite_wache", os.path.join(HIER, "breite-wache.py"))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


w = lade()


def messung(breite, unter=(), ueber=(("BTC-USDT", 84.0), ("ETH-USDT", 26.0)),
            grundgesamtheit=None, offen=(), kerze="2026-09-25"):
    """Baut eine Messung in der Form, die messen() liefert.

    `grundgesamtheit` ist standardmaessig genau die Zahl der gelieferten Paare
    (also vollstaendige Deckung). Eine unvollstaendige Messung muss man
    ausdruecklich bestellen - sonst schlaegt die Deckungspruefung in JEDEM
    Testdatensatz zu und alle Regeltests werden rot.
    """
    ueber_s = [{"inst": i, "kurs": k, "ema": k / 1.2, "abstand": 20.0}
               for i, k in ueber]
    unter_s = [{"inst": i, "kurs": k, "ema": k * 1.05, "abstand": -5.0}
               for i, k in unter]
    n = len(ueber_s) + len(unter_s)
    return {
        "ts": "2026-09-25T06:00:00+00:00", "kerze": kerze,
        "ueber": ueber_s, "unter": unter_s, "offen": list(offen),
        "n_ueber": len(ueber_s), "n_gesamt": n,
        "breite": breite if breite is not None else None,
        "grundgesamtheit": ["x"] * (grundgesamtheit if grundgesamtheit
                                    is not None else n),
    }


class RegelnTest(unittest.TestCase):
    def test_erste_messung_wird_gemeldet(self):
        raus, neu = w.zeilen(messung(100.0), {})
        self.assertTrue(raus, "die erste Messung muss gemeldet werden")
        self.assertIn("erste Messung", raus[0])
        self.assertEqual(neu["stufe"], "ok")

    def test_keine_aenderung_schweigt(self):
        merker = {"breite": 100.0, "stufe": "ok", "unter": [], "ts": "x"}
        raus, _ = w.zeilen(messung(100.0), merker)
        self.assertEqual(raus, [], "ohne Aenderung darf nichts kommen")

    def test_stufe_faellt_wird_gemeldet(self):
        merker = {"breite": 95.0, "stufe": "ok", "unter": [], "ts": "x"}
        raus, neu = w.zeilen(messung(70.0), merker)
        self.assertTrue(raus)
        self.assertIn("gefallen", raus[0])
        self.assertEqual(neu["stufe"], "achtung")

    def test_stufe_erholt_wird_gemeldet(self):
        merker = {"breite": 55.0, "stufe": "warnung", "unter": [], "ts": "x"}
        raus, neu = w.zeilen(messung(90.0), merker)
        self.assertTrue(raus, "nach einer Warnung muss die Erholung kommen")
        self.assertIn("erholt", raus[0])
        self.assertEqual(neu["stufe"], "ok")

    def test_neues_paar_unter_der_ema_wird_gemeldet(self):
        merker = {"breite": 80.0, "stufe": "ok", "unter": [], "ts": "x"}
        raus, neu = w.zeilen(messung(80.0, unter=[("APT-USDT", 0.82)]), merker)
        self.assertTrue(raus)
        self.assertIn("Neu unter der EMA200", " ".join(raus))
        self.assertIn("APT-USDT", " ".join(raus))
        self.assertEqual(neu["unter"], ["APT-USDT"])

    def test_bekanntes_paar_unter_der_ema_wiederholt_sich_nicht(self):
        """Ein Paar, das unten bleibt, ist dieselbe Feststellung."""
        merker = {"breite": 80.0, "stufe": "ok", "unter": ["APT-USDT"], "ts": "x"}
        raus, _ = w.zeilen(messung(80.0, unter=[("APT-USDT", 0.82)]), merker)
        self.assertEqual(raus, [])

    def test_unvollstaendige_messung_wird_gemeldet(self):
        merker = {"breite": 100.0, "stufe": "ok", "unter": [], "ts": "x"}
        m = messung(100.0, grundgesamtheit=30, offen=[{"inst": "TON-USDT",
                                                       "grund": "51001"}])
        m["n_gesamt"] = 20
        raus, _ = w.zeilen(m, merker)
        self.assertTrue(raus, "eine kaputte Messung darf nicht schweigen")
        self.assertIn("unvollstaendig", " ".join(raus))

    def test_schwelle_erzwingt_meldung(self):
        merker = {"breite": 50.0, "stufe": "warnung", "unter": [], "ts": "x"}
        raus, neu = w.zeilen(messung(50.0), merker, schwelle=60.0)
        self.assertTrue(raus, "der Uebergang unter die Schwelle muss kommen")
        self.assertIn("Pruefschwelle", " ".join(raus))
        self.assertTrue(neu["schwelle_aktiv"])

    def test_schwelle_wiederholt_sich_nicht(self):
        """Dauerhaft unter der Schwelle ist EINE Meldung, kein Tagesalarm."""
        merker = {"breite": 50.0, "stufe": "warnung", "unter": [],
                  "schwelle_aktiv": True, "ts": "x"}
        raus, _ = w.zeilen(messung(50.0), merker, schwelle=60.0)
        self.assertEqual(raus, [])

    def test_stufen_einteilung(self):
        self.assertEqual(w.stufe(100.0), "ok")
        self.assertEqual(w.stufe(80.0), "ok")
        self.assertEqual(w.stufe(79.9), "achtung")
        self.assertEqual(w.stufe(60.0), "achtung")
        self.assertEqual(w.stufe(59.9), "warnung")
        self.assertEqual(w.stufe(None), "unbekannt")


if __name__ == "__main__":
    sys.exit(unittest.main())