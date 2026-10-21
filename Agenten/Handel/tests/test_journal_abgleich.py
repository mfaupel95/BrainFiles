"""Tests fuer journal_abgleich.py. Alles in Wegwerf-Ordnern, nie die echte tracking.db."""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import journal_abgleich  # noqa: E402
import tracking  # noqa: E402

KOPF = "zeit,modus,aktion,inst,seite,preis,nominal_usd,grund,pos_id\n"


def _iso(tage_her, minuten=0):
    t = datetime.now(timezone.utc) - timedelta(days=tage_her) + timedelta(minutes=minuten)
    return t.isoformat()


class AbgleichTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        alt = tracking._DB_PFAD
        self.addCleanup(setattr, tracking, "_DB_PFAD", alt)
        self.db = os.path.join(self.tmp.name, "t.db")
        tracking.init_tracking(Path(self.db))
        self.spur = os.path.join(self.tmp.name, "demo")
        os.makedirs(self.spur)

    def _journal(self, zeilen):
        with open(os.path.join(self.spur, "handelsjournal.csv"), "w", encoding="utf-8", newline="") as f:
            f.write(KOPF + "".join(z + "\n" for z in zeilen))

    def _events(self):
        con = sqlite3.connect(self.db)
        try:
            return [json.loads(p) for (p,) in con.execute(
                "SELECT properties FROM events WHERE event='zyklus.abgeschlossen' ORDER BY id")]
        finally:
            con.close()

    def _lauf(self, **kw):
        return journal_abgleich.abgleich(self.db, self.tmp.name, **kw)

    def test_long_und_short_werden_abgeleitet(self):
        self._journal([
            f"{_iso(3)},papier,eroeffnen,BTC,long,100.0,200.0,,p1",
            f"{_iso(3, 120)},papier,schliessen,BTC,long,110.0,200.0,ziel 1.0,p1",
            f"{_iso(2)},live,eroeffnen,ETH,short,50.0,100.0,,p2",
            f"{_iso(2, 60)},live,schliessen,ETH,short,55.0,100.0,stop,p2",
        ])
        b = self._lauf(schreiben=True)
        self.assertEqual(b["demo"], {"fehlt": 2, "ohne_einstieg": 0, "geschrieben": 2})
        a, s = self._events()
        self.assertEqual((a["ergebnis_pct"], a["ergebnis_eur"], a["haltedauer_stunden"],
                          a["ausstiegsgrund"], a["is_paper"], a["quelle"]),
                         (10.0, 20.0, 2.0, "ziel", True, "journal_abgleich"))
        self.assertEqual((s["richtung"], s["ergebnis_pct"], s["ergebnis_eur"], s["is_paper"]),
                         ("short", -10.0, -10.0, False))

    def test_zweiter_lauf_ergaenzt_nichts(self):
        self._journal([f"{_iso(3)},papier,kauf,BTC,long,100.0,50.0,,",
                       f"{_iso(3, 5)},papier,verkauf,BTC,long,90.0,50.0,stop,"])
        self.assertEqual(self._lauf(schreiben=True)["demo"]["geschrieben"], 1)
        self.assertEqual(self._lauf(schreiben=True)["demo"], {"fehlt": 0, "ohne_einstieg": 0, "geschrieben": 0})
        self.assertEqual(len(self._events()), 1)

    def test_vorhandener_haken_ereignis_wird_nicht_doppelt(self):
        t = datetime.now(timezone.utc) - timedelta(days=3)
        self._journal([f"{_iso(3, -10)},papier,kauf,BTC,long,100.0,50.0,,",
                       f"{t.isoformat()},papier,verkauf,BTC,long,90.0,50.0,stop,"])
        with sqlite3.connect(self.db) as con:
            con.execute("INSERT INTO events (ts, event, properties) VALUES (?, ?, ?)",
                        ((t + timedelta(seconds=40)).isoformat(), "zyklus.abgeschlossen",
                         json.dumps({"spur_name": "demo", "instrument": "BTC"})))
        self.assertEqual(self._lauf(schreiben=True)["demo"]["fehlt"], 0)

    def test_trockenlauf_schreibt_nichts_und_sichert_nicht(self):
        self._journal([f"{_iso(3)},papier,kauf,BTC,long,100.0,50.0,,",
                       f"{_iso(3, 5)},papier,verkauf,BTC,long,90.0,50.0,stop,"])
        self.assertEqual(self._lauf()["demo"]["fehlt"], 1)
        self.assertEqual(self._events(), [])
        self.assertFalse(os.path.exists(self.db + ".vor-abgleich"))

    def test_ohne_einstieg_alte_und_fremde_zeilen(self):
        self._journal([
            f"{_iso(2)},papier,verkauf,AAA,long,10.0,50.0,stop,",                 # keine Eroeffnung
            f"{_iso(90)},papier,kauf,BBB,long,10.0,50.0,,",                        # zu alt
            f"{_iso(89)},papier,verkauf,BBB,long,11.0,50.0,ziel,",
            f"{_iso(2)},replay,kauf,CCC,long,10.0,50.0,,",                         # kein Papier/Live
            f"{_iso(1)},replay,verkauf,CCC,long,11.0,50.0,ziel,",
        ])
        b = self._lauf(schreiben=True)
        self.assertEqual(b["demo"], {"fehlt": 0, "ohne_einstieg": 1, "geschrieben": 0})

    def test_pos_id_ordnet_ueberlappende_positionen_zu(self):
        self._journal([
            f"{_iso(3)},papier,kauf,BTC,long,100.0,50.0,,a",
            f"{_iso(3, 10)},papier,kauf,BTC,long,200.0,50.0,,b",
            f"{_iso(3, 400)},papier,verkauf,BTC,long,220.0,50.0,ziel,b",
            f"{_iso(3, 800)},papier,verkauf,BTC,long,110.0,50.0,ziel,a",
        ])
        self._lauf(schreiben=True)
        pct = sorted(e["ergebnis_pct"] for e in self._events())
        self.assertEqual(pct, [10.0, 10.0])

    def test_erste_sicherung_nur_einmal(self):
        self._journal([f"{_iso(3)},papier,kauf,BTC,long,100.0,50.0,,",
                       f"{_iso(3, 5)},papier,verkauf,BTC,long,90.0,50.0,stop,"])
        self._lauf(schreiben=True)
        self.assertTrue(os.path.exists(self.db + ".vor-abgleich"))
        self.assertEqual(journal_abgleich._sicherung(self.db), None)


if __name__ == "__main__":
    unittest.main()
