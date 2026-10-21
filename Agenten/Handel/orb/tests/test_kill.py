"""Kill und Halbierung der Spur orb (ORB auf OKX-Perpetuals).

wachen_orb.lage() berechnete `kill` und `groessenfaktor`, aber lauf() las beides nie;
ausserdem las kill_ausgeloest den Schluessel kill_switch_gesamt_usd, die Wache nennt
ihn kill_switch_gesamt_usdt - der Kill konnte nie ausloesen. Jetzt: Kill schliesst Papier
zum Marktkurs (Grund kill_zwangsschluss), laesst echte Positionen stehen, sperrt Einstiege,
Frist/Reset ueber kill_gemeinsam, Halbierung wirkt auf das Risiko neuer Positionen.
Ohne Netz: Kurse, Ausstiege und Einstiege werden ersetzt.
"""
import csv
import datetime
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import handeln
import wachen_orb as wp

HIER = Path(__file__).resolve().parent.parent
HEUTE = datetime.date.today().isoformat()


def jetzt():
    return datetime.datetime.now(datetime.timezone.utc)


def pos(inst="BTC_USDT", modus=None, **kw):
    p = {"inst": inst, "richtung": "long", "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
         "tag": HEUTE, "letzter_kurs": 98.0, "punkt_wert_usdt": 1.0, "range_hoehe": 5.0,
         "risiko_usdt": 10.0}
    if modus:
        p["modus"] = modus
    p.update(kw)
    return p


class KillOrb(unittest.TestCase):
    def setUp(self):
        for name in ("ZUSTAND", "JOURNAL", "_wachen", "_letzter_kurs", "pruefe_ausstiege",
                     "pruefe_einstieg"):
            self.addCleanup(setattr, handeln, name, getattr(handeln, name))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        handeln.ZUSTAND = d / "zustand.json"
        handeln.JOURNAL = d / "handelsjournal.csv"
        self.w = json.loads((HIER / "wachen.json").read_text("utf-8"))
        self.w.pop("kill_switch_gesamt_usd", None)
        self.w["kill_switch_gesamt_usdt"] = 45.0           # wie die echte Wache (USDT)
        self.w.pop("kill_frist_stunden", None)
        self.w.pop("kill_wiederaufnahme", None)
        handeln._wachen = lambda: dict(self.w)
        self.kurs = {"BTC_USDT": 96.0, "ETH_USDT": 96.0}
        handeln._letzter_kurs = lambda w, key: self.kurs[key]
        handeln.pruefe_ausstiege = lambda z, w, jetzt=None: []
        self.einstiege = []
        handeln.pruefe_einstieg = lambda z, w, jetzt=None: self.einstiege_liefern(z)
        self.verluste(5)
        self.zustand()

    def einstiege_liefern(self, z):
        neu = list(self.einstiege)
        z.setdefault("positionen", []).extend(neu)
        self.einstiege = []
        return neu

    def verluste(self, n):
        t0 = jetzt() - datetime.timedelta(days=20)
        for i in range(n):
            tag = (t0 + datetime.timedelta(days=i)).date().isoformat()
            handeln.journal(tag, "BTC_USDT", "long", 100, 95, 110, "stop", 95, -5, -10.0,
                            "0.0", "0.0", 0)

    def zustand(self, **kw):
        z = {"positionen": [], "letzter_lauf": None, "modus": "papier"}
        z.update(kw)
        handeln.ZUSTAND.write_text(json.dumps(z), "utf-8")

    def lauf(self):
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            self.meldungen = handeln.lauf("papier")
        self.ausgabe = puffer.getvalue()
        return json.loads(handeln.ZUSTAND.read_text("utf-8"))

    def seit(self, h):
        return (jetzt() - datetime.timedelta(hours=h)).isoformat(timespec="seconds")

    def zeilen(self):
        with open(handeln.JOURNAL, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def test_kill_ausloesung_mit_usdt_schluessel(self):
        self.assertTrue(wp.lage(self.w, handeln.JOURNAL, {})["kill"])

    def test_kill_bucht_papier_zum_marktkurs_und_sperrt_einstieg(self):
        self.zustand(positionen=[pos()])
        self.einstiege = [pos("ETH_USDT")]
        z = self.lauf()
        self.assertEqual(z["positionen"], [])
        letzte = self.zeilen()[-1]
        self.assertEqual(letzte["ausgang"], "kill_zwangsschluss")
        self.assertEqual(float(letzte["ausstieg"]), 96.0)
        self.assertEqual(len(self.einstiege), 1)            # pruefe_einstieg lief nie
        self.assertIn("kill_seit", z)

    def test_echte_position_bleibt(self):
        self.zustand(positionen=[pos(modus="live"), pos("ETH_USDT")])
        z = self.lauf()
        self.assertEqual([p["inst"] for p in z["positionen"]], ["BTC_USDT"])
        self.assertEqual(len(self.zeilen()), 6)

    def test_ohne_kurs_bleibt_die_position(self):
        self.kurs = {}
        self.zustand(positionen=[pos(letzter_kurs=None)])
        self.assertEqual(len(self.lauf()["positionen"]), 1)

    def test_nach_der_frist_beginnt_der_ruecklauf_bei_null(self):
        self.zustand(kill_seit=self.seit(200))
        z = self.lauf()
        self.assertIn("beginnt bei 0", self.ausgabe)
        self.assertNotIn("kill_seit", z)
        self.assertEqual(z["kill_ab_runde"], 5)
        self.assertNotIn("kill_seit", self.lauf())

    def test_live_position_haelt_die_sperre(self):
        ori = self.seit(200)
        self.zustand(kill_seit=ori, positionen=[pos(modus="live")])
        z = self.lauf()
        self.assertEqual(z["kill_seit"], ori)
        self.assertIn("bleibt gesperrt", self.ausgabe)

    def test_opt_out_haelt_die_sperre(self):
        self.w["kill_wiederaufnahme"] = False
        ori = self.seit(200)
        self.zustand(kill_seit=ori)
        self.assertEqual(self.lauf()["kill_seit"], ori)

    def test_halbierung_wirkt_auf_das_risiko_neuer_positionen(self):
        self.w["kill_switch_gesamt_usdt"] = 1000.0         # kein Kill, nur Halbierung
        self.w["drawdown_halbierung_usd"] = 20.0
        self.einstiege = [pos("ETH_USDT", risiko_usdt=10.0)]
        z = self.lauf()
        self.assertAlmostEqual(z["positionen"][0]["risiko_usdt"], 5.0)

    def test_ohne_ruecklauf_volles_risiko(self):
        self.w["kill_switch_gesamt_usdt"] = 1000.0
        self.w["drawdown_halbierung_usd"] = 1000.0
        self.einstiege = [pos("ETH_USDT", risiko_usdt=10.0)]
        self.assertAlmostEqual(self.lauf()["positionen"][0]["risiko_usdt"], 10.0)


if __name__ == "__main__":
    unittest.main()
