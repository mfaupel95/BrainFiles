"""Test der kraken-Wache: die REGELN, nicht die heutigen Tageswerte.

Die Wache meldet nur Neues - wenn sie das falsch macht, ist sie entweder still
(und niemand merkt einen Ausfall) oder laut (und niemand liest sie mehr). Beide
Fehler sieht man nur an der Regel, nicht am heutigen Journal.

Geprueft wird die reine Funktion `meldungen_bauen` (ohne Netz, ohne Dateien) und
`lauf` mit einem Temp-Ordner als Naht. Ein zweiter Lauf mit demselben Stand darf
NICHTS wiederholen - das ist der eigentliche Wackeltest des Watchdog-Musters.

Direkt ausfuehrbar:  python test_kraken_wache.py
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

spec = importlib.util.spec_from_file_location("kraken_wache", HIER / "kraken-wache.py")
w = importlib.util.module_from_spec(spec)
sys.modules["kraken_wache"] = w
spec.loader.exec_module(w)

JETZT = dt.datetime(2026, 10, 1, 14, 0, tzinfo=dt.timezone.utc)


def zeile(modus, aktion, paar="SOLEUR", preis="104.26", zeit="2026-10-01T11:27:22+00:00",
          grund="", **rest):
    r = {"zeit": zeit, "modus": modus, "aktion": aktion, "paar": paar,
         "preis": preis, "eur": rest.pop("eur", "50.34"),
         "menge": rest.pop("menge", "0.47998464"),
         "stop": rest.pop("stop", "97.71146"), "ziel": rest.pop("ziel", "117.08708"),
         "grund": grund}
    r.update(rest)
    return r


class ErstlaufTest(unittest.TestCase):
    """Der erste Lauf setzt den Grundstand, statt 225 Zeilen nachzumelden."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (w.HANDEL, w.CACHE, w.SPUR)
        w.CACHE = Path(self.tmp.name)

    def tearDown(self):
        w.HANDEL, w.CACHE, w.SPUR = self.alt
        self.tmp.cleanup()

    def test_erster_lauf_setzt_stand_und_meldet_zusammenfassung(self):
        spur = Path(self.tmp.name) / "kraken"
        spur.mkdir()
        (spur / "handelsjournal.csv").write_text(
            "zeit,modus,aktion,paar,preis,eur,menge,stop,ziel,grund,pos_id\r\n"
            "2026-10-01T11:27:22+00:00,live,kauf,SOLEUR,104.26,50.34,0.48,97.7,117.1,,\r\n"
            "2026-10-01T09:00:00+00:00,papier,kauf,DOTEUR,1.06,50.00,47.0,0.98,1.22,,\r\n",
            encoding="utf-8")
        (spur / "zustand.json").write_text("{}", encoding="utf-8")
        w.HANDEL = Path(self.tmp.name)
        meldungen = w.lauf(schreiben=True, mit_netz=False)
        self.assertEqual(len(meldungen), 1)
        self.assertIn("eingerichtet", meldungen[0])
        self.assertIn("1 echte", meldungen[0], "nur der Live-Kauf zaehlt")
        stand = json.loads((Path(self.tmp.name) / "kraken-wache.json").read_text("utf-8"))
        self.assertEqual(stand["zeilen"], 2)

    def test_zweiter_lauf_ohne_neues_schweigt(self):
        spur = Path(self.tmp.name) / "kraken"
        spur.mkdir()
        (spur / "handelsjournal.csv").write_text(
            "zeit,modus,aktion,paar,preis,eur,menge,stop,ziel,grund,pos_id\r\n"
            "2026-10-01T11:27:22+00:00,live,kauf,SOLEUR,104.26,50.34,0.48,97.7,117.1,,\r\n",
            encoding="utf-8")
        (spur / "zustand.json").write_text("{}", encoding="utf-8")
        w.HANDEL = Path(self.tmp.name)
        w.lauf(schreiben=True, mit_netz=False)
        self.assertEqual(w.lauf(schreiben=True, mit_netz=False), [],
                         "ohne neue Zeile darf nichts kommen")


class NeueZeilenTest(unittest.TestCase):

    def test_live_kauf_wird_gemeldet(self):
        rows = [zeile("live", "kauf")]
        m, _ = w.meldungen_bauen(rows, {"zeilen": 0}, jetzt=JETZT)
        self.assertEqual(len(m), 1)
        self.assertIn("LIVE-KAUF SOLEUR", m[0])
        self.assertIn("Stop 97.71146", m[0])

    def test_live_verkauf_wird_gemeldet(self):
        rows = [zeile("live", "verkauf", grund="stop")]
        m, _ = w.meldungen_bauen(rows, {"zeilen": 0}, jetzt=JETZT)
        self.assertIn("LIVE-VERKAUF", m[0])
        self.assertIn("Grund stop", m[0])

    def test_papierzeilen_werden_nicht_gemeldet(self):
        rows = [zeile("papier", "kauf"), zeile("papier", "verkauf")]
        m, _ = w.meldungen_bauen(rows, {"zeilen": 0}, jetzt=JETZT)
        self.assertEqual(m, [], "Papier ist nicht die Live-Seite")

    def test_fehlerzeile_wird_gemeldet(self):
        rows = [zeile("live", "fehler", grund="EOrder:Insufficient funds")]
        m, _ = w.meldungen_bauen(rows, {"zeilen": 0}, jetzt=JETZT)
        self.assertIn("FEHLER", m[0])
        self.assertIn("Insufficient funds", m[0])

    def test_alte_zeilen_werden_nicht_wiederholt(self):
        rows = [zeile("live", "kauf"), zeile("live", "kauf", paar="ADAEUR")]
        m1, stand = w.meldungen_bauen(rows, {"zeilen": 0}, jetzt=JETZT)
        self.assertEqual(len(m1), 2)
        m2, _ = w.meldungen_bauen(rows, stand, jetzt=JETZT)
        self.assertEqual(m2, [], "derselbe Stand darf nichts wiederholen")

    def test_nur_die_neue_zeile_kommt(self):
        alt = [zeile("live", "kauf")]
        neu = alt + [zeile("live", "kauf", paar="ADAEUR")]
        _, stand = w.meldungen_bauen(alt, {"zeilen": 0}, jetzt=JETZT)
        m, _ = w.meldungen_bauen(neu, stand, jetzt=JETZT)
        self.assertEqual(len(m), 1)
        self.assertIn("ADAEUR", m[0])


class BelegverfallTest(unittest.TestCase):

    def test_wenige_belege_schweigen(self):
        rows = [zeile("live", "kauf_beleg") for _ in range(2)]
        m, _ = w.meldungen_bauen(rows, {"zeilen": 0}, jetzt=JETZT)
        self.assertEqual(m, [])

    def test_viele_belege_ohne_ausfuehrung_melden(self):
        rows = [zeile("live", "kauf_beleg") for _ in range(6)]
        m, stand = w.meldungen_bauen(rows, {"zeilen": 0}, jetzt=JETZT)
        self.assertEqual(len(m), 1)
        self.assertIn("6 neue Belege", m[0])
        self.assertIn("T-283", m[0])
        m2, _ = w.meldungen_bauen(rows, stand, jetzt=JETZT)
        self.assertEqual(m2, [], "dieselbe Haeufung nicht zweimal")


class StopTest(unittest.TestCase):

    def test_position_ohne_stop_txid_wird_gemeldet(self):
        z = {"positionen": [{"paar": "SOLEUR", "kauf_txid": "O1", "stop_txid": None,
                             "menge": 0.48}]}
        m, _ = w.meldungen_bauen([], {"zeilen": 0}, z=z, jetzt=JETZT,
                                 geprueft_boerse=True)
        self.assertEqual(len(m), 1)
        self.assertIn("OHNE SCHUTZ", m[0])
        self.assertIn("SOLEUR", m[0])

    def test_boersen_stop_fehlt_flag_wird_gemeldet(self):
        z = {"positionen": [{"paar": "ADAEUR", "kauf_txid": "O2",
                             "stop_txid": "S2", "boersen_stop_fehlt": True,
                             "menge": 228.4}]}
        m, _ = w.meldungen_bauen([], {"zeilen": 0}, z=z, jetzt=JETZT,
                                 geprueft_boerse=True)
        self.assertIn("ADAEUR", m[0])

    def test_stop_an_der_boerse_verschwunden_wird_gemeldet(self):
        z = {"positionen": [{"paar": "SOLEUR", "kauf_txid": "O1",
                             "stop_txid": "S1", "menge": 0.48}]}
        m, _ = w.meldungen_bauen([], {"zeilen": 0}, z=z, jetzt=JETZT,
                                 offene_stops=[], geprueft_boerse=True)
        self.assertIn("nicht mehr an der Boerse", m[0])

    def test_stop_vorhanden_schweigt(self):
        z = {"positionen": [{"paar": "SOLEUR", "kauf_txid": "O1",
                             "stop_txid": "S1", "menge": 0.48}]}
        m, _ = w.meldungen_bauen([], {"zeilen": 0}, z=z, jetzt=JETZT,
                                 offene_stops=[{"menge": "0.48000000"}],
                                 geprueft_boerse=True)
        self.assertEqual(m, [])

    def test_ohne_boersenfrage_keine_stop_behauptung(self):
        """Ein Netzfehler darf nicht als Gefahr gemeldet werden."""
        z = {"positionen": [{"paar": "SOLEUR", "kauf_txid": "O1",
                             "stop_txid": "S1", "menge": 0.48}]}
        m, _ = w.meldungen_bauen([], {"zeilen": 0}, z=z, jetzt=JETZT,
                                 offene_stops=None, geprueft_boerse=False)
        self.assertEqual(m, [])

    def test_altbestand_ohne_boersenbezug_schweigt(self):
        z = {"positionen": [{"paar": "ATOMEUR", "menge": 32.8}]}
        m, _ = w.meldungen_bauen([], {"zeilen": 0}, z=z, jetzt=JETZT,
                                 geprueft_boerse=True)
        self.assertEqual(m, [])


class TorTest(unittest.TestCase):

    def test_leere_lage_ist_kein_geschlossenes_tor(self):
        self.assertFalse(w.tor_zu({}), "nicht abrufbar ist kein Zustand")

    def test_eine_waehrung_ueber_dem_tor_oeffnet(self):
        self.assertFalse(w.tor_zu({"EUR": (189.42, 60.0), "USDC": (25.0, 60.0)}))

    def test_alle_unter_dem_tor_ist_zu(self):
        self.assertTrue(w.tor_zu({"EUR": (53.81, 60.0), "USDC": (25.0, 60.0)}))

    def test_tor_zu_wird_einmal_gemeldet(self):
        g = {"EUR": (53.81, 60.0)}
        m, stand = w.meldungen_bauen([], {"zeilen": 0}, guthaben=g, jetzt=JETZT)
        self.assertIn("Guthaben-Tor ZU", m[0])
        m2, _ = w.meldungen_bauen([], stand, guthaben=g, jetzt=JETZT)
        self.assertEqual(m2, [], "derselbe Zustand nicht zweimal")

    def test_tor_wieder_offen_ist_keine_meldung(self):
        m, stand = w.meldungen_bauen([], {"zeilen": 0}, guthaben={"EUR": (10.0, 60.0)},
                                     jetzt=JETZT)
        self.assertTrue(m)
        m2, _ = w.meldungen_bauen([], stand, guthaben={"EUR": (189.42, 60.0)},
                                  jetzt=JETZT)
        self.assertEqual(m2, [], "die Rueckkehr zur Ruhe muss nicht gemeldet werden")


class StillstandTest(unittest.TestCase):

    def test_frischer_zyklus_schweigt(self):
        z = {"letzter_lauf": "2026-10-01T13:55:00+00:00"}
        m, _ = w.meldungen_bauen([], {"zeilen": 0}, z=z, jetzt=JETZT)
        self.assertEqual(m, [])

    def test_alter_zyklus_wird_gemeldet_und_nicht_wiederholt(self):
        z = {"letzter_lauf": "2026-10-01T12:00:00+00:00"}
        m, stand = w.meldungen_bauen([], {"zeilen": 0}, z=z, jetzt=JETZT)
        self.assertIn("STILLSTAND", m[0])
        m2, stand2 = w.meldungen_bauen([], stand, z=z, jetzt=JETZT)
        self.assertEqual(m2, [], "ein anhaltender Stillstand ist EINE Meldung")

    def test_erholung_wird_gemeldet(self):
        z = {"letzter_lauf": "2026-10-01T12:00:00+00:00"}
        _, stand = w.meldungen_bauen([], {"zeilen": 0}, z=z, jetzt=JETZT)
        z2 = {"letzter_lauf": "2026-10-01T13:59:00+00:00"}
        m, _ = w.meldungen_bauen([], stand, z=z2, jetzt=JETZT)
        self.assertIn("laeuft wieder", m[0])

    def test_fehlender_letzter_lauf_ist_kein_stillstand(self):
        m, _ = w.meldungen_bauen([], {"zeilen": 0}, z={}, jetzt=JETZT)
        self.assertEqual(m, [], "ohne Zeitstempel nichts behaupten")


class EchteDateiTest(unittest.TestCase):
    """Die ausgelieferte Wache muss auf die ECHTE Spur zeigen."""

    def test_spurname_ist_kraken(self):
        self.assertEqual(w.SPUR, "kraken")

    def test_pfade_zeigen_auf_die_handelsspur(self):
        self.assertTrue((w.HANDEL / "kraken" / "handeln.py").exists())
        self.assertTrue((w.HANDEL / "kraken" / "handelsjournal.csv").exists())

    def test_stillstandsgrenze_ist_groesser_als_ein_takt(self):
        self.assertGreaterEqual(w.STILL_MIN, 45,
                                "der Zyklus dauert ~6,5 min - darunter waere jede "
                                "langsame Runde ein Fehlalarm")


if __name__ == "__main__":
    unittest.main(verbosity=2)