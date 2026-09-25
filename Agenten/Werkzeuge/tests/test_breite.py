"""Tests fuer Agenten/Werkzeuge/breite.py - die REIHE, nicht die Tageszahl.

Ohne Netz: geprueft werden `merken` (eine Zeile je Kerzentag), `reihe` und
`verlauf` (Veraenderung in Punkten). `messen()` wird NICHT gerufen - ein Test,
der die echte Breite prueft, waere jeden Tag rot oder gruen, ohne dass sich
etwas geaendert haette.

Die Naht ist das Modulattribut `REIHE`: der Test biegt es auf einen
Temp-Ordner um. Zusaetzlich merkt sich der Test Groesse und Aenderungszeit der
ECHTEN Reihe und prueft am Ende, dass sie unberuehrt ist - ein Test darf nie in
den echten Laufzeitstand schreiben.

Aufruf: python -m unittest discover -s tests -t tests   (aus Agenten/Werkzeuge)
"""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
WERKZEUG = os.path.join(os.path.dirname(HIER), "breite.py")


def lade():
    spec = importlib.util.spec_from_file_location("breite_werkzeug_test",
                                                  WERKZEUG)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


b = lade()

_echte_reihe = (os.path.getsize(b.REIHE), os.path.getmtime(b.REIHE)) \
    if os.path.exists(b.REIHE) else None


def messung(breite, kerze="2026-09-25", unter=(), ueber=(("BTC-USDT", 84.0),),
            ts="2026-09-25T17:00:00+00:00"):
    """Messung in der Form, die messen() liefert (ohne Netz)."""
    ueber_s = [{"inst": i, "kurs": k, "ema": k / 1.2, "abstand": 20.0}
               for i, k in ueber]
    unter_s = [{"inst": i, "kurs": k, "ema": k * 1.05, "abstand": -5.0}
               for i, k in unter]
    return {
        "ts": ts, "kerze": kerze, "ueber": ueber_s, "unter": unter_s,
        "offen": [], "n_ueber": len(ueber_s),
        "n_gesamt": len(ueber_s) + len(unter_s), "breite": breite,
    }


class ReiheTest(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="breite-test-")
        self.echt = b.REIHE
        b.REIHE = os.path.join(self.ordner, "breite-reihe.jsonl")

    def tearDown(self):
        b.REIHE = self.echt
        shutil.rmtree(self.ordner, ignore_errors=True)

    def test_zweite_messung_derselben_kerze_ersetzt(self):
        b.merken(messung(100.0))
        b.merken(messung(96.5))
        zeilen = b.reihe(None)
        self.assertEqual(len(zeilen), 1,
                         "zwei Messungen EINES Kerzentags sind EINE Zeile")
        self.assertEqual(zeilen[0]["breite"], 96.5,
                         "die spaetere Messung gewinnt")

    def test_zwei_kerzen_geben_zwei_zeilen(self):
        b.merken(messung(100.0, kerze="2026-09-24"))
        b.merken(messung(93.0, kerze="2026-09-25"))
        zeilen = b.reihe(None)
        self.assertEqual([z["kerze"] for z in zeilen],
                         ["2026-09-24", "2026-09-25"])

    def test_alte_kerze_wird_an_ihrer_stelle_ersetzt(self):
        b.merken(messung(100.0, kerze="2026-09-24"))
        b.merken(messung(93.0, kerze="2026-09-25"))
        b.merken(messung(88.0, kerze="2026-09-24"))       # Nachlauf
        zeilen = b.reihe(None)
        self.assertEqual([z["kerze"] for z in zeilen],
                         ["2026-09-24", "2026-09-25"],
                         "die Reihe bleibt zeitlich sortiert")
        self.assertEqual(zeilen[0]["breite"], 88.0)

    def test_verlauf_rechnet_die_veraenderung(self):
        b.merken(messung(100.0, kerze="2026-09-24"))
        b.merken(messung(91.0, kerze="2026-09-25"))
        tage = b.verlauf()
        self.assertEqual(len(tage), 2)
        self.assertIsNone(tage[0]["delta"], "der erste Tag hat keinen Vorgaenger")
        self.assertEqual(tage[1]["delta"], -9.0)

    def test_verlauf_zaehlt_die_messungen_je_tag(self):
        for wert in (100.0, 99.0, 97.0):
            b.merken(messung(wert))
        tage = b.verlauf()
        self.assertEqual(len(tage), 1)
        self.assertEqual(tage[0]["messungen"], 1,
                         "ersetzt heisst: eine Zeile, nicht drei")

    def test_zeile_ohne_kerze_zaehlt_nicht_als_tag(self):
        with open(b.REIHE, "w", encoding="utf-8") as f:
            f.write(json.dumps(messung(50.0, kerze=None)) + "\n")
        self.assertEqual(b.verlauf(), [])

    def test_kaputte_zeile_killt_die_reihe_nicht(self):
        b.merken(messung(100.0))
        with open(b.REIHE, "a", encoding="utf-8") as f:
            f.write("{kein json\n")
        self.assertEqual(len(b.reihe(None)), 1)

    def test_reihe_ohne_datei_ist_leer(self):
        self.assertEqual(b.reihe(None), [])
        self.assertEqual(b.verlauf(), [])

    def test_verlauf_n_grenzt_auf_die_letzten_tage(self):
        for i, k in enumerate(("2026-09-21", "2026-09-22", "2026-09-23")):
            b.merken(messung(100.0 - i, kerze=k))
        self.assertEqual([z["kerze"] for z in b.verlauf(2)],
                         ["2026-09-22", "2026-09-23"])


class EchteReiheUnberuehrtTest(unittest.TestCase):
    def test_test_schreibt_nicht_in_den_echten_stand(self):
        if _echte_reihe is None:
            self.skipTest("keine echte Reihe vorhanden")
        self.assertEqual((os.path.getsize(b.REIHE), os.path.getmtime(b.REIHE)),
                         _echte_reihe,
                         "die echte breite-reihe.jsonl wurde angefasst")


if __name__ == "__main__":
    unittest.main()
