"""Kill des Papierzweigs (mosaic): Zwangsschluss MIT Buchung, Frist, Reset, Live-Schutz.

Bis 15.10.2026 warf `nur_papier_verwerfen` die Papier-Positionen im Kill ohne
Buchung aus dem Buch, und die Spur blieb fuer immer gesperrt. Jetzt wie die
anderen Spuren ueber kill_gemeinsam. Ohne Netz: `_kurs_papier` wird ersetzt.
"""
import csv
import datetime
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
for p in (os.path.join(HANDEL, "scanner"), HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)


def lade():
    alt = list(sys.path)
    sys.path.insert(0, SPUR)
    try:
        spec = importlib.util.spec_from_file_location("mosaic_kill_papier",
                                                      os.path.join(SPUR, "handeln.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    finally:
        sys.path[:] = alt
    return m


def jetzt():
    return datetime.datetime.now(datetime.timezone.utc)


def pos(inst="BTC-USDT", modus="papier", **kw):
    p = {"inst": inst, "seite": "long", "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
         "stop_pct": 5.0, "nominal": 200.0, "modus": modus, "pos_id": "k-" + inst,
         "eroeffnet_zeit": jetzt().isoformat(timespec="seconds")}
    p.update(kw)
    return p


class KillPapier(unittest.TestCase):
    def setUp(self):
        self.m = lade()
        self.tmp = tempfile.mkdtemp(prefix="mosaickill-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        with open(os.path.join(SPUR, "wachen.json"), encoding="utf-8") as f:
            self.w = json.load(f)
        self.w.update(kill_switch_gesamt_usd=45.0)
        self.w.pop("kill_frist_stunden", None)
        self.w.pop("kill_wiederaufnahme", None)
        m = self.m
        m.WACHEN = os.path.join(self.tmp, "wachen.json")
        m.ZUSTAND = os.path.join(self.tmp, "zustand.json")
        m.JOURNAL = os.path.join(self.tmp, "handelsjournal.csv")
        m.SCHREIBEN = True
        m.spiegeln = lambda z, w: None
        self.kurs = {"BTC-USDT": 100.0, "ETH-USDT": 100.0}
        m._kurs_papier = lambda inst: self.kurs[inst]
        self.schreibe_wachen()
        self.verluste(5)                                  # 5 x -10 -> Ruecklauf 50 >= 45
        self.zustand()

    def schreibe_wachen(self):
        with open(self.m.WACHEN, "w", encoding="utf-8") as f:
            json.dump(self.w, f)

    def verluste(self, n):
        t0 = jetzt() - datetime.timedelta(days=20)
        for i in range(n):
            z = (t0 + datetime.timedelta(minutes=i)).isoformat(timespec="seconds")
            self.m.journal(zeit=z, modus="papier", aktion="kauf", inst="BTC-USDT",
                           seite="long", preis="100", einsatz_usd="200.00", grund="test")
            self.m.journal(zeit=z, modus="papier", aktion="verkauf", inst="BTC-USDT",
                           seite="long", preis="95", einsatz_usd="190.00", grund="stop")

    def zustand(self, **kw):
        z = {"positionen": [], "modus": "papier", "letzter_lauf": None}
        z.update(kw)
        with open(self.m.ZUSTAND, "w", encoding="utf-8") as f:
            json.dump(z, f)

    def seit(self, h):
        return (jetzt() - datetime.timedelta(hours=h)).isoformat(timespec="seconds")

    def lauf(self):
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            self.m.lauf("papier")
        self.ausgabe = puffer.getvalue()
        with open(self.m.ZUSTAND, encoding="utf-8") as f:
            return json.load(f)

    def verkaeufe(self):
        with open(self.m.JOURNAL, encoding="utf-8", newline="") as f:
            return [r for r in csv.DictReader(f) if r.get("aktion") == "verkauf"]

    def test_kill_bucht_papier_zum_marktkurs(self):
        self.kurs["BTC-USDT"] = 98.0
        self.zustand(positionen=[pos()])
        z = self.lauf()
        self.assertEqual(z["positionen"], [])
        zw = [r for r in self.verkaeufe() if r["grund"] == "kill_zwangsschluss"]
        self.assertEqual(len(zw), 1)
        self.assertAlmostEqual(float(zw[0]["einsatz_usd"]), 196.0, places=2)
        self.assertIn("kill_seit", z)

    def test_ohne_kurs_bleibt_die_position(self):
        self.m._kurs_papier = lambda inst: (_ for _ in ()).throw(RuntimeError("netz"))
        self.zustand(positionen=[pos()])
        z = self.lauf()
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(len(self.verkaeufe()), 5)

    def test_live_position_bleibt_papier_wird_gebucht(self):
        self.zustand(positionen=[pos("ETH-USDT", modus="live"), pos()])
        z = self.lauf()
        self.assertEqual([p["inst"] for p in z["positionen"]], ["ETH-USDT"])
        self.assertEqual(len(self.verkaeufe()), 6)

    def test_innerhalb_der_frist_bleibt_gesperrt(self):
        ori = self.seit(10)
        self.zustand(kill_seit=ori)
        z = self.lauf()
        self.assertEqual(z["kill_seit"], ori)
        self.assertIn("Frist noch", self.ausgabe)

    def test_nach_der_frist_beginnt_der_ruecklauf_bei_null(self):
        self.zustand(kill_seit=self.seit(200))
        z = self.lauf()
        self.assertIn("beginnt bei 0", self.ausgabe)
        self.assertNotIn("kill_seit", z)
        self.assertEqual(z["kill_ab_runde"], 5)
        self.assertNotIn("kill_seit", self.lauf())        # kein sofortiger Re-Kill

    def test_opt_out_haelt_die_sperre(self):
        self.w["kill_wiederaufnahme"] = False
        self.schreibe_wachen()
        ori = self.seit(200)
        self.zustand(kill_seit=ori)
        z = self.lauf()
        self.assertEqual(z["kill_seit"], ori)
        self.assertNotIn("kill_ab_runde", z)
        self.assertIn("bleibt gesperrt", self.ausgabe)

    def test_neuer_rueckgang_loest_den_kill_wieder_aus(self):
        self.zustand(kill_seit=self.seit(200))
        self.lauf()
        self.verluste(5)
        z = self.lauf()
        self.assertIn("Kill-Schwelle erreicht", self.ausgabe)
        self.assertIn("kill_seit", z)

    def test_live_position_haelt_die_sperre_ohne_ausdruecklichen_schalter(self):
        ori = self.seit(200)
        self.zustand(kill_seit=ori, positionen=[pos("ETH-USDT", modus="live")])
        z = self.lauf()
        self.assertEqual(z["kill_seit"], ori)
        self.assertIn("bleibt gesperrt", self.ausgabe)


if __name__ == "__main__":
    unittest.main()
