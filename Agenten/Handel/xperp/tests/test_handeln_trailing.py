"""Die Verdrahtung des Trailing-Stops in xperp (05.10.2026).

`trailing.py` rechnet; dieser Test prueft, dass xperp/handeln.py den Weg
RUFT und die drei Bedingungen einhaelt, die ein Trailing im echten Betrieb
unmoeglich machen koennen:

  1. `trailing_aktiv` fehlt in der Wache -> es passiert NICHTS. Ohne diese
     Schranke wuerde jede Spur durch ein vergessenes Feld ploetzlich
     nachziehen.
  2. Eine Position mit MEHREREN Boersen-Stops -> kein Trailing. Der HYPE-
     Fall vom 05.10.2026: 33+22+12 Kontrakte auf einer Position von 67. Der
     engste Stop feuert beim naechsten Tick, die anderen bleiben als Waisen -
     drei einzelne Verlegungen wuerden die Position schliessen und zwei
     Schutzauftraege zuruecklassen.
  3. Ohne Stop-Kennung -> kein Trailing, sondern eine Journalzeile, die
     sagt, welches Werkzeug zustaendig ist.

Und der wichtigste Test: der Trailing darf eine Position NICHT schliessen.
Ein Fehler, der die Reihenfolge umdreht, wuerde hier stillschweigend
Positionen verkaufen.
"""

import importlib.util
import pathlib
import sys
import tempfile
import unittest

SPUR = pathlib.Path(__file__).resolve().parents[1]      # .../xperp
HANDEL = SPUR.parent                                          # .../Handel

for pfad in (str(HANDEL), str(SPUR)):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

sys.modules.pop("handeln", None)
_spec = importlib.util.spec_from_file_location("xperp_handeln_t",
                                               SPUR / "handeln.py")
h = importlib.util.module_from_spec(_spec)
sys.modules["xperp_handeln_t"] = h
_spec.loader.exec_module(h)


class AttrappeOkxf:
    """Nur die Aufrufe zaehlen. Kein Netz, keine Order."""

    def __init__(self):
        self.aufrufe = []
        self.kurs = 100.0

    def letzter_kurs(self, inst):
        return self.kurs

    def stop_nachziehen(self, algo_id, inst, preis):
        self.aufrufe.append((algo_id, inst, float(preis)))
        return str(algo_id)

    # T-365: die Mengen-Deckung ist die ERSTE Bedingung. Die Attrappe
    # simuliert eine VOLL gedeckte Position (10 Kontrakte, 10 geschuetzt),
    # damit der Trailing durchlaufen darf.
    def positionen(self):
        return [{"instId": "TEST-USD_UM_XPERP-310404", "pos": 10.0}]

    def schutz_stops(self, inst):
        return [{"reduceOnly": "true", "side": "sell",
                 "slTriggerPx": 95.0, "sz": "10"}]


def position(**kwargs):
    p = {"inst": "TEST-USD_UM_XPERP-310404", "basis": "TEST",
         "seite": "long", "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
         "liq": 0.0, "kontrakte": 10.0, "nominal": 100.0, "margin": 20.0,
         "hebel": 5.0, "modus": "live", "ord_id": "o-1",
         "eroeffnet": "2026-10-05", "eroeffnet_zeit": "2026-10-05T00:00:00+00:00",
         "funding_zuletzt": "", "funding_summe": 0.0, "pos_id": "P1"}
    p.update(kwargs)
    return p


class TrailingVerdrahtungTest(unittest.TestCase):
    def setUp(self):
        self.okxf_alt = h.okxf
        self.journal_alt = h.JOURNAL
        self.zustand_alt = h.ZUSTAND
        self.okxf = AttrappeOkxf()
        h.okxf = self.okxf
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="xperp-trailing-"))
        h.JOURNAL = str(self.tmp / "handelsjournal.csv")
        h.ZUSTAND = str(self.tmp / "zustand.json")
        h.SCHREIBEN = True

    def tearDown(self):
        h.okxf = self.okxf_alt
        h.JOURNAL, h.ZUSTAND = self.journal_alt, self.zustand_alt
        h.SCHREIBEN = False

    def _zeilen(self):
        if not pathlib.Path(h.JOURNAL).is_file():
            return []
        import csv
        with pathlib.Path(h.JOURNAL).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    # --- 1. Die Schranke -----------------------------------------------------

    def test_ohne_aktiv_wird_nichts_getan(self):
        """Eine Wache ohne `trailing_aktiv` zieht NICHT nach - auch dann
        nicht, wenn die Position 3R im Plus ist und eine Kennung traegt."""
        p = position(stop_id="algo-1")
        w = {"gebuehr_taker": 0.0005}
        h.okxf.kurs = 112.0
        h._trailing_versuch(p, 112.0, w)
        self.assertEqual(self.okxf.aufrufe, [],
                         "der Trailing lief ohne Freigabe in der Wache")
        self.assertEqual(float(p["stop"]), 95.0)

    def test_mit_aktiv_wird_gezogen(self):
        p = position(stop_id="algo-1")
        w = {"trailing_aktiv": True, "gebuehr_taker": 0.0005}
        h.okxf.kurs = 112.0
        h._trailing_versuch(p, 112.0, w)
        self.assertEqual(len(self.okxf.aufrufe), 1,
                         "der Trailing hat nicht gezogen")
        self.assertGreater(float(p["stop"]), 95.0)
        self.assertGreater(float(p["stop"]), 100.0,
                           "der neue Stop muss im Plus liegen")
        zeilen = self._zeilen()
        traila = [z for z in zeilen if z["aktion"] == "trailing"]
        self.assertEqual(len(traila), 1, "die Journalzeile fehlt: %s" % zeilen)

    # --- 2. Drei Stops auf einer Position ------------------------------------

    def test_drei_stops_werden_verweigert(self):
        """Der HYPE-Fall: 33+22+12 auf 67 Kontrakte. Ein Trailing je Stop
        wuerde den naechsten Tick die Position schliessen."""
        p = position(stop_ids=["a1", "a2", "a3"])
        w = {"trailing_aktiv": True, "gebuehr_taker": 0.0005}
        h.okxf.kurs = 112.0
        h._trailing_versuch(p, 112.0, w)
        self.assertEqual(self.okxf.aufrufe, [],
                         "bei drei Stops wurde nachgezogen")
        self.assertEqual(float(p["stop"]), 95.0, "der Stop hat sich bewegt")
        zeilen = self._zeilen()
        vermerkt = [z for z in zeilen if "stopdeckung" in (z["grund"] or "")]
        self.assertEqual(len(vermerkt), 1,
                         "der Vermerk nennt das Werkzeug nicht: %s" % zeilen)

    def test_ein_stop_darf_ziehen(self):
        """Genau EIN Stop ist der gesunde Fall - die Grenze darf nicht
        versehentlich auch ihn aussperren."""
        p = position(stop_ids=["a1"])
        w = {"trailing_aktiv": True, "gebuehr_taker": 0.0005}
        h.okxf.kurs = 112.0
        h._trailing_versuch(p, 112.0, w)
        self.assertEqual(len(self.okxf.aufrufe), 1)

    # --- 3. Ohne Kennung -----------------------------------------------------

    def test_ohne_kennung_kein_trailing_mit_vermerk(self):
        p = position()
        w = {"trailing_aktiv": True, "gebuehr_taker": 0.0005}
        h.okxf.kurs = 112.0
        h._trailing_versuch(p, 112.0, w)
        self.assertEqual(self.okxf.aufrufe, [])
        vermerkt = [z for z in self._zeilen()
                    if "stopdeckung" in (z["grund"] or "")]
        self.assertEqual(len(vermerkt), 1)

    def test_kennung_wird_an_der_boerse_nachgeschlagen(self):
        """11.10.2026: das Buch traegt beim Eroeffnen keine Kennung. Liegt an
        der Boerse genau EIN Schutz-Stop, wird dessen algoId genommen."""
        stops = [{"algoId": "boerse-1", "reduceOnly": "true", "side": "sell",
                  "slTriggerPx": "95", "sz": "10"}]
        self.okxf.schutz_stops = lambda inst: stops
        self.okxf.ist_schutz_stop = lambda s: bool(s.get("slTriggerPx"))
        p = position()
        w = {"trailing_aktiv": True, "gebuehr_taker": 0.0005}
        h.okxf.kurs = 112.0
        h._trailing_versuch(p, 112.0, w)
        self.assertEqual([a[0] for a in self.okxf.aufrufe], ["boerse-1"])
        self.assertNotIn("stop_ids", p, "Boersenliste darf nicht ins Buch")

    def test_zwei_boersen_stops_werden_verweigert(self):
        stops = [{"algoId": "b1", "slTriggerPx": "95", "sz": "6"},
                 {"algoId": "b2", "slTriggerPx": "94", "sz": "4"}]
        self.okxf.schutz_stops = lambda inst: stops
        self.okxf.ist_schutz_stop = lambda s: bool(s.get("slTriggerPx"))
        p = position()
        h._trailing_versuch(p, 112.0, {"trailing_aktiv": True,
                                        "gebuehr_taker": 0.0005})
        self.assertEqual(self.okxf.aufrufe, [])

    # --- 4. Der Aufruf geht an die BOERSE, nicht ins Buch --------------------

    def test_der_stop_des_buches_ist_der_der_boerse(self):
        """Buch und Boerse muessen denselben Stop fuehren - sonst verkauft
        ein spaeterer Zyklus zu einem Preis, den es dort nicht gibt."""
        p = position(stop_id="algo-1")
        w = {"trailing_aktiv": True, "gebuehr_taker": 0.0005}
        h.okxf.kurs = 112.0
        h._trailing_versuch(p, 112.0, w)
        buch = float(p["stop"])
        boerse = self.okxf.aufrufe[0][2]
        self.assertAlmostEqual(buch, boerse, places=6,
                               msg="Buch %.6f und Boerse %.6f laufen auseinander"
                                   % (buch, boerse))

    def test_hoechstkurs_wird_gepflegt(self):
        """Auch OHNE Trailing muss der Hochstand wachsen - sonst vergleicht
        der naechste Zyklus gegen einen zu neuen Wert und haelt den Stop
        zu weit hinten."""
        p = position(stop_id="algo-1")
        w = {"trailing_aktiv": False}
        h._trailing_versuch(p, 108.0, w)
        self.assertAlmostEqual(float(p["hoechstkurs"]), 108.0)
        h._trailing_versuch(p, 104.0, w)
        self.assertAlmostEqual(float(p["hoechstkurs"]), 108.0,
                               msg="der Hochstand ist gefallen")


class KeinFehlerTest(unittest.TestCase):
    """Ein Trailing, der nicht ausloest, schreibt KEINE Journalzeile.

    Sonst waende sich die Auswertung mit jedem Zyklus: die Spur stuende in
    jedem Lauf mit 47 offenen Positionen auf 'trailing', ohne dass sich
    etwas bewegt haette.
    """

    def setUp(self):
        self.okxf_alt = h.okxf
        self.journal_alt = h.JOURNAL
        self.okxf = AttrappeOkxf()
        h.okxf = self.okxf
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="xperp-trail-nf-"))
        h.JOURNAL = str(self.tmp / "handelsjournal.csv")
        h.SCHREIBEN = True

    def tearDown(self):
        h.okxf = self.okxf_alt
        h.JOURNAL = self.journal_alt
        h.SCHREIBEN = False

    def test_vor_dem_trigger_stille(self):
        p = position(stop_id="algo-1")
        w = {"trailing_aktiv": True, "gebuehr_taker": 0.0005}
        h._trailing_versuch(p, 101.0, w)
        self.assertEqual(self.okxf.aufrufe, [])
        self.assertFalse(pathlib.Path(h.JOURNAL).is_file(),
                         "es wurde eine Journalzeile ohne Ereignis geschrieben")


if __name__ == "__main__":
    unittest.main(verbosity=2)