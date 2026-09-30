"""Tests fuer Agenten/Hermes/scripts/breite-wache.py - die MELDEREGELN.

OHNE NETZ: geprueft werden `stufe()` und `zeilen()` - die Entscheidung, ob und
was gesendet wird. `main()` wird NICHT gerufen: es wuerde messen (Netz), in die
echte Reihe schreiben und die echte Merkdatei setzen. Die Naht fuer die
Merkdatei ist das Modulattribut MERKDATEI; die Tests biegen sie auf einen
Temp-Ordner um.

Der Waechter folgt dem Watchdog-Muster: **leere Ausgabe heisst alles gut.**

Aufruf: python -m unittest test_breite_wache   (aus Agenten/Hermes/scripts)
"""
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHE = HIER.parent / "scripts" / "breite-wache.py"
if not WACHE.exists():                        # Test liegt schon in scripts/
    WACHE = HIER / "breite-wache.py"


def lade():
    spec = importlib.util.spec_from_file_location("breite_wache_test",
                                                  str(WACHE))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


w = lade()


def lage(breite=100.0, unter=(), ueber=None, n_gesamt=None, grundgesamtheit=30,
         offen=(), kerze="2026-09-25", ts="2026-09-25T17:00:00+00:00"):
    """Messung in der Form, die breite.py `messen()` liefert (ohne Netz)."""
    unter = [u if isinstance(u, dict) else {"inst": u, "abstand": -3.0}
             for u in unter]
    if ueber is None:
        n_erwartet = n_gesamt if n_gesamt is not None else (
            (grundgesamtheit or 0) - len(unter))
        ueber = max(0, n_erwartet - len(unter))
    gesamt = len(unter) + ueber
    m = {"breite": breite, "unter": unter, "n_ueber": ueber, "n_gesamt": gesamt,
         "offen": [o if isinstance(o, dict) else {"inst": o, "grund": "x"}
                   for o in offen],
         "kerze": kerze, "ts": ts}
    if grundgesamtheit is not None:
        m["grundgesamtheit"] = ["PAAR-%d" % i for i in range(grundgesamtheit)]
    return m


class StufeTest(unittest.TestCase):
    def test_grenzen(self):
        self.assertEqual(w.stufe(100.0), "ok")
        self.assertEqual(w.stufe(80.0), "ok")
        self.assertEqual(w.stufe(79.9), "achtung")
        self.assertEqual(w.stufe(60.0), "achtung")
        self.assertEqual(w.stufe(59.9), "warnung")
        self.assertEqual(w.stufe(0.0), "warnung")
        self.assertEqual(w.stufe(None), "unbekannt")


class MelderegelTest(unittest.TestCase):
    def test_erste_messung_meldet(self):
        raus, neu = w.zeilen(lage(100.0), {})
        self.assertTrue(raus, "die erste Messung ist eine Nachricht wert")
        self.assertIn("erste Messung", raus[0])
        self.assertEqual(neu["stufe"], "ok")
        self.assertEqual(neu["breite"], 100.0)

    def test_keine_aenderung_ist_still(self):
        merker = {"breite": 100.0, "stufe": "ok", "unter": [],
                  "gemeldet_breite": 100.0, "schwelle_aktiv": False}
        raus, neu = w.zeilen(lage(100.0), merker)
        self.assertEqual(raus, [], "leere Ausgabe heisst alles gut")
        self.assertEqual(neu["breite"], 100.0)

    def test_stufenwechsel_nach_unten_meldet(self):
        merker = {"breite": 100.0, "stufe": "ok", "unter": [],
                  "gemeldet_breite": 100.0}
        raus, neu = w.zeilen(lage(72.0), merker)
        self.assertIn("gefallen", raus[0])
        self.assertIn("72.0", raus[0])
        self.assertEqual(neu["stufe"], "achtung")

    def test_stufenwechsel_nach_oben_meldet(self):
        merker = {"breite": 40.0, "stufe": "warnung", "unter": [],
                  "gemeldet_breite": 40.0}
        raus, neu = w.zeilen(lage(85.0), merker)
        self.assertIn("erholt", raus[0])
        self.assertEqual(neu["stufe"], "ok")

    def test_neues_paar_unter_der_ema(self):
        merker = {"breite": 90.0, "stufe": "ok", "unter": ["APT-USDT"],
                  "gemeldet_breite": 90.0}
        raus, neu = w.zeilen(lage(85.0, unter=[{"inst": "APT-USDT",
                                                "abstand": -1.2},
                                               {"inst": "OP-USDT",
                                                "abstand": -4.5}]),
                             merker)
        text = "\n".join(raus)
        self.assertIn("Neu unter der EMA200", text)
        self.assertIn("OP-USDT", text)
        self.assertIn("-4.50 %", text)
        self.assertNotIn("  APT-USDT  ", text,
                         "was schon unter der EMA stand, ist keine Neuigkeit")
        self.assertEqual(neu["unter"], ["APT-USDT", "OP-USDT"])

    def test_weiter_unter_der_ema_wird_genannt(self):
        merker = {"breite": 90.0, "stufe": "ok", "unter": ["APT-USDT"],
                  "gemeldet_breite": 90.0}
        raus, _neu = w.zeilen(lage(60.0, unter=["APT-USDT"]), merker)
        self.assertIn("Weiter unter der EMA200: APT-USDT", "\n".join(raus))

    def test_deckung_zu_gering_meldet_die_offenen(self):
        raus, _neu = w.zeilen(lage(50.0, n_gesamt=20, grundgesamtheit=30,
                                   offen=["TON-USDT"]), {})
        text = "\n".join(raus)
        self.assertIn("unvollstaendig", text)
        self.assertIn("20 von 30", text)
        self.assertIn("TON-USDT", text)

    def test_ohne_grundgesamtheit_gilt_als_unvollstaendig(self):
        """main() MUSS die Grundgesamtheit setzen - sonst schlaegt die Wache an."""
        raus, _neu = w.zeilen(lage(50.0, grundgesamtheit=None), {})
        self.assertIn("unvollstaendig", "\n".join(raus))

    def test_rueckgang_gegen_die_letzte_meldung(self):
        """Innerhalb der Stufe 'ok' war die Wache blind - 100 auf 81 ist stumm."""
        merker = {"breite": 100.0, "stufe": "ok", "unter": [],
                  "gemeldet_breite": 100.0}
        raus, neu = w.zeilen(lage(88.0), merker)
        self.assertIn("Rueckgang um 12.0 Punkte", "\n".join(raus))
        self.assertEqual(neu["gemeldet_breite"], 88.0,
                         "nach der Meldung setzt der Bezug neu auf")

    def test_kleiner_rueckgang_ist_still(self):
        merker = {"breite": 100.0, "stufe": "ok", "unter": [],
                  "gemeldet_breite": 100.0}
        raus, neu = w.zeilen(lage(95.0), merker)
        self.assertEqual(raus, [],
                         "2-3 Punkte am Tag sind Rauschen, nicht Nachricht")
        self.assertEqual(neu["gemeldet_breite"], 100.0,
                         "der Bezug bleibt stehen, sonst summieren sich "
                         "Haeppchen nie zu einer Meldung")

    def test_schwelle_wird_einmal_gemeldet(self):
        merker = {"breite": 70.0, "stufe": "achtung", "unter": [],
                  "gemeldet_breite": 70.0, "schwelle_aktiv": False}
        raus, neu = w.zeilen(lage(45.0), merker, schwelle=50.0)
        self.assertIn("unter der Pruefschwelle von 50 %", "\n".join(raus))
        self.assertTrue(neu["schwelle_aktiv"])
        raus2, _neu2 = w.zeilen(lage(45.0), neu, schwelle=50.0)
        self.assertEqual(raus2, [], "kein taeglicher Weckruf")

    def test_zeile_nennt_deckung_und_kerze(self):
        raus, _neu = w.zeilen(lage(100.0, ueber=29), {})
        self.assertIn("29 von 29 Paaren ueber der EMA200", "\n".join(raus))
        self.assertIn("2026-09-25", "\n".join(raus))


class HeilTest(unittest.TestCase):
    """`_luecken_schliessen` heilt still und meldet nur, was neu ist.

    Die Naht ist der Parameter `w` - ein gefaelschtes Werkzeugmodul genuegt,
    damit kein Netz und kein Schreibzugriff noetig ist.
    """

    def _werkzeug(self, gefuellt=0, abgleich=()):
        class Fake:
            @staticmethod
            def fuellen(tage=None, verlauf_je_inst=None):
                return {"gefuellt": gefuellt, "abgleich": list(abgleich),
                        "ohne": [], "kerzen_je_paar": {}, "tage": 1}
        return Fake

    def test_ohne_verlauf_passiert_nichts(self):
        self.assertEqual(w._luecken_schliessen(self._werkzeug(), {}), [])

    def test_stille_heilung_ohne_meldung(self):
        raus = w._luecken_schliessen(self._werkzeug(),
                                     {"_verlauf": {"A-USDT": [(1, 2.0)]}})
        self.assertEqual(raus, [], "leere Ausgabe heisst: nichts zu sagen")

    def test_nachgefuellte_tage_werden_gemeldet(self):
        raus = w._luecken_schliessen(self._werkzeug(gefuellt=2),
                                     {"_verlauf": {"A-USDT": [(1, 2.0)]}})
        self.assertIn("nachgefuellt: 2", raus[0])

    def test_abgleich_drift_wird_gemeldet(self):
        raus = w._luecken_schliessen(
            self._werkzeug(abgleich=[{"kerze": "2026-09-25", "live": 100.0,
                                      "nachgerechnet": 96.5, "diff": -3.5}]),
            {"_verlauf": {"A-USDT": [(1, 2.0)]}})
        self.assertIn("Abgleich 2026-09-25", raus[0])
        self.assertIn("-3.5 pp", raus[0])

    def test_kleine_abweichung_ist_still(self):
        raus = w._luecken_schliessen(
            self._werkzeug(abgleich=[{"kerze": "2026-09-25", "live": 100.0,
                                      "nachgerechnet": 99.8, "diff": -0.2}]),
            {"_verlauf": {"A-USDT": [(1, 2.0)]}})
        self.assertEqual(raus, [], "Rundung ist kein Regelbruch")

    def test_fehler_wird_gemeldet_statt_verschluckt(self):
        class Kaputt:
            @staticmethod
            def fuellen(tage=None, verlauf_je_inst=None):
                raise OSError("Platte voll")
        raus = w._luecken_schliessen(Kaputt, {"_verlauf": {"A": [(1, 2.0)]}})
        self.assertIn("nicht nachgerechnet", raus[0])
        self.assertIn("Platte voll", raus[0])


class MerkdateiTest(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="breite-wache-")
        self.echt = w.MERKDATEI
        w.MERKDATEI = Path(self.ordner) / "breite-wache.json"

    def tearDown(self):
        w.MERKDATEI = self.echt
        shutil.rmtree(self.ordner, ignore_errors=True)

    def test_merken_und_lesen(self):
        w._merke({"breite": 96.55, "stufe": "ok"})
        self.assertEqual(w._merker()["breite"], 96.55)

    def test_kaputte_merkdatei_ist_leer(self):
        with open(w.MERKDATEI, "w", encoding="utf-8") as f:
            f.write("{kein json")
        self.assertEqual(w._merker(), {})

    def test_fehlende_merkdatei_ist_leer(self):
        os.remove(w.MERKDATEI) if os.path.exists(w.MERKDATEI) else None
        self.assertEqual(w._merker(), {})


if __name__ == "__main__":
    unittest.main()