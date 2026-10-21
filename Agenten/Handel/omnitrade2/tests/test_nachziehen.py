"""Tests fuer den Schutz-Stop-Nachzieher und die Boersenpruefungen der Wache.

Kein Netz, keine Boerse: das okxf-Modul wird durch eine Attrappe ersetzt, die
Position, Deckung und die gesetzten Stops in einer Liste fuehrt. Der Test
prueft die REGEL (Luecke statt Vollmenge, einmaliges Hochziehen, Orderweg-
Erkennung), nicht einen Tageswert.
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
SPUR = HIER.parent
WACHE = SPUR.parents[1] / "Hermes" / "scripts" / "omnitrade2-sol-wache.py"


def laden(pfad: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


class FakeOkxf:
    """Attrappe: eine Position, Stops in einer Liste, Aufrufe werden gezaehlt."""

    def __init__(self, menge=0.0, einstieg=100.0, stops=None):
        self.menge = menge
        self.einstieg = einstieg
        self.stops = list(stops or [])
        self.gesetzt = []
        self.positionen_aufrufe = 0

    def positionen(self, inst=None):
        self.positionen_aufrufe += 1
        if not self.menge:
            return []
        return [{"instId": inst, "pos": str(self.menge), "avgPx": str(self.einstieg), "upl": "0"}]

    def schutz_stops(self, inst=None, ordtypes=None):
        return list(self.stops)

    def ist_schutz_stop(self, auftrag):
        return bool(str((auftrag or {}).get("slTriggerPx") or "").strip())

    def schutz_stop_setzen(self, inst, seite, kontrakte, stop, ziel=None, tdmode="isolated"):
        self.gesetzt.append({"inst": inst, "seite": seite, "kontrakte": kontrakte, "stop": stop})
        self.stops.append({"instId": inst, "side": "sell" if seite == "long" else "buy",
                           "sz": str(kontrakte), "slTriggerPx": str(stop)})
        return {"algoId": "1", "sCode": "0"}


class NachziehenTest(unittest.TestCase):
    def setUp(self):
        self.n = laden(SPUR / "nachziehen.py", "nachziehen_test")
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name)
        # Alle Pfade in den Temp-Ordner biegen: kein Schreibzugriff nach draussen.
        self.alt = (self.n.LAUF_DATEI, self.n.ZUSTAND, self.n.STATUS)
        self.n.LAUF_DATEI = self.ordner / "lauf.json"
        self.n.ZUSTAND = self.ordner / "zustand.json"
        self.n.STATUS = self.ordner / "status.json"
        self.n.LAUF_DATEI.write_text(json.dumps({
            "inst": "SOL-TEST-1", "quantity": 0.19, "quantity_voll": 0.19, "phase": "voll",
        }), encoding="utf-8")

    def tearDown(self):
        self.n.LAUF_DATEI, self.n.ZUSTAND, self.n.STATUS = self.alt
        self.tmp.cleanup()

    def test_ohne_position_wird_nichts_gestellt(self):
        fake = FakeOkxf(menge=0.0)
        self.n.okxf_laden = lambda: fake
        erg = self.n.lauf(anwenden=True)
        self.assertEqual(fake.gesetzt, [])
        self.assertIn("keine Position", erg["handlung"][0])

    def test_volle_deckung_stellt_keinen_zweiten_stop(self):
        fake = FakeOkxf(menge=20.0, einstieg=100.0,
                        stops=[{"sz": "20", "slTriggerPx": "98"}])
        self.n.okxf_laden = lambda: fake
        self.n.lauf(anwenden=True)
        self.assertEqual(fake.gesetzt, [], "zwei Stops derselben Groesse waeren doppelt")

    def test_luecke_wird_nur_als_differenz_gestellt(self):
        # 20 Kontrakte, davon 1 gedeckt -> Stop fuer 19, nicht fuer 20.
        fake = FakeOkxf(menge=20.0, einstieg=100.0,
                        stops=[{"sz": "1", "slTriggerPx": "98"}])
        self.n.okxf_laden = lambda: fake
        erg = self.n.lauf(anwenden=True)
        self.assertEqual(len(fake.gesetzt), 1)
        self.assertAlmostEqual(fake.gesetzt[0]["kontrakte"], 19.0)
        self.assertAlmostEqual(fake.gesetzt[0]["stop"], 98.0)  # 2 % unter Einstieg
        self.assertEqual(fake.gesetzt[0]["seite"], "long")
        self.assertIn("NACHKONTROLLE", " ".join(erg["handlung"]))

    def test_short_bekommt_stop_ueber_dem_einstieg(self):
        fake = FakeOkxf(menge=-5.0, einstieg=100.0)
        self.n.okxf_laden = lambda: fake
        self.n.lauf(anwenden=True)
        self.assertEqual(fake.gesetzt[0]["seite"], "short")
        self.assertAlmostEqual(fake.gesetzt[0]["stop"], 102.0)

    def test_vorschau_stellt_nichts(self):
        fake = FakeOkxf(menge=5.0, einstieg=100.0)
        self.n.okxf_laden = lambda: fake
        self.n.lauf(anwenden=False)
        self.assertEqual(fake.gesetzt, [])

    def test_hochziehen_nur_einmal(self):
        self.n.LAUF_DATEI.write_text(json.dumps({
            "inst": "SOL-TEST-1", "quantity": 0.01, "quantity_voll": 0.19, "phase": "mikro",
        }), encoding="utf-8")
        fake = FakeOkxf(menge=1.0, einstieg=100.0)
        self.n.okxf_laden = lambda: fake
        starts = []
        self.n.loop_pid = lambda: None
        self.n.lauf_starten = lambda: starts.append(1) or "GESTARTET PID 1"
        self.n.lauf(anwenden=True)
        self.assertEqual(len(starts), 1, "Beleg steht -> genau ein Neustart")
        lauf = json.loads(self.n.LAUF_DATEI.read_text(encoding="utf-8"))
        self.assertEqual(lauf["phase"], "voll")
        self.assertAlmostEqual(lauf["quantity"], 0.19)
        # Zweiter Lauf darf nicht erneut hochziehen.
        self.n.lauf(anwenden=True)
        self.assertEqual(len(starts), 1)
        zustand = json.loads(self.n.ZUSTAND.read_text(encoding="utf-8"))
        self.assertIn("hochgezogen_am", zustand)


class WachenPruefungTest(unittest.TestCase):
    def setUp(self):
        self.w = laden(WACHE, "wache_test")
        self.merk = {}

    def test_orderweg_kaputt_wird_gemeldet(self):
        st = {"orders_placed": 0, "candles_seen": 342, "orders_rejected": 12}
        self.assertEqual(self.w.orderwegpruefung(self.merk, st), 1)

    def test_orderweg_gesund_bleibt_still(self):
        st = {"orders_placed": 1, "candles_seen": 342, "orders_rejected": 12}
        self.assertEqual(self.w.orderwegpruefung(self.merk, st), 0)

    def test_zu_frueh_bleibt_still(self):
        st = {"orders_placed": 0, "candles_seen": 10, "orders_rejected": 0}
        self.assertEqual(self.w.orderwegpruefung(self.merk, st), 0)

    def test_position_ohne_stop_wird_gemeldet(self):
        fake = FakeOkxf(menge=5.0, einstieg=100.0)
        self.w._nachzieher = lambda: (type("M", (), {
            "okxf_laden": staticmethod(lambda: fake),
            "position": staticmethod(lambda okxf, inst: {"menge": 5.0, "einstieg": 100.0,
                                                          "seite": "long"}),
            "deckung": staticmethod(lambda okxf, inst: (0.0, 0)),
            "MIN_LUECKE": 0.5,
        })(), None)
        st = {"symbol": "SOL-TEST-1"}
        self.assertEqual(self.w.boersenpruefung(self.merk, st, 5.0), 1)
        self.assertEqual(self.w.boersenpruefung(self.merk, st, 5.0), 0, "nicht doppelt melden")

    def test_arg_wert_liest_die_zahl(self):
        self.assertAlmostEqual(
            self.w._arg_wert("cli live --quantity 0.19 --allow-shorts", "--quantity"), 0.19)
        self.assertIsNone(self.w._arg_wert("cli live --allow-shorts", "--quantity"))

    def test_parameterdrift_wird_gemeldet_und_nicht_wiederholt(self):
        # Anlass 21.10.: Lauf von aussen mit 0.19 gestartet, lauf.json sagte 0.01.
        self.w.lauf_argumente = lambda inst: ("cli live --quantity 0.01", None)
        self.assertEqual(self.w.parameterpruefung(self.merk), 1)
        self.assertEqual(self.w.parameterpruefung(self.merk), 0, "nicht doppelt melden")

    def test_passende_parameter_bleiben_still(self):
        lauf = json.loads((SPUR / "lauf.json").read_text(encoding="utf-8"))
        self.w.lauf_argumente = lambda inst: (
            "cli live --quantity %s --allow-shorts" % lauf["quantity"], None)
        self.assertEqual(self.w.parameterpruefung(self.merk), 0)
        self.assertNotIn("parameter_gemeldet", self.merk)

    def test_prozessabfrage_fehler_wird_gemeldet(self):
        self.w.lauf_argumente = lambda inst: (None, "CIM weg")
        self.assertEqual(self.w.parameterpruefung(self.merk), 1)

    def test_boersenabfrage_fehler_wird_gemeldet(self):
        def platzt():
            raise RuntimeError("EAPI:Invalid nonce")
        self.w._nachzieher = lambda: (type("M", (), {"okxf_laden": staticmethod(platzt),
                                                     "position": staticmethod(lambda *a: None),
                                                     "deckung": staticmethod(lambda *a: (0, 0)),
                                                     "MIN_LUECKE": 0.5})(), None)
        self.assertEqual(self.w.boersenpruefung(self.merk, {"symbol": "X"}, 0.0), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
