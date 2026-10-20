"""Kill und Halbierung der Spur orbk (ORB, eine Position, echter Live-Ausstieg).

wachen_orb.lage() berechnete `kill` und `groessenfaktor`, aber lauf() las beides nie.
Jetzt: Kill schliesst Papier zum Marktkurs (Grund kill_zwangsschluss), eine echte Position
nur im Live-Lauf oder per Notausstieg ueber _exit_live (gegen die Boerse verifiziert,
reduceOnly), sperrt Einstiege, Frist/Reset ueber kill_gemeinsam, Halbierung wirkt auf das
Risiko der neuen Position. Ohne Netz: Kurse, Ausstiege und Boerse werden ersetzt.
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

HIER = Path(__file__).resolve().parent.parent
HEUTE = datetime.date.today().isoformat()


def jetzt():
    return datetime.datetime.now(datetime.timezone.utc)


def pos(modus=None, **kw):
    p = {"inst": "ETH_USDT", "richtung": "long", "einstieg": 100.0, "stop": 95.0,
         "ziel": 110.0, "tag": HEUTE, "letzter_kurs": 98.0, "punkt_wert_usdt": 1.0,
         "range_hoehe": 5.0, "risiko_usd": 10.0, "kontrakte": 2}
    if modus:
        p["modus"] = modus
    p.update(kw)
    return p


class FakeOkxf:
    def __init__(self):
        self.geschlossen = []
        self.offen = True
        self.schluessel = True

    def positionen(self):
        return [{"instId": "ETH-USDT-SWAP"}] if self.offen else []

    def markt_schliessen(self, paar, kontrakte, richtung):
        self.geschlossen.append((paar, kontrakte, richtung))

    def schluessel_vorhanden(self):
        return self.schluessel


class KillOrbk(unittest.TestCase):
    def setUp(self):
        for name in ("ZUSTAND", "JOURNAL", "_wachen", "_letzter_kurs", "pruefe_ausstiege",
                     "pruefe_einstieg", "okxf"):
            self.addCleanup(setattr, handeln, name, getattr(handeln, name))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        handeln.ZUSTAND = d / "zustand.json"
        handeln.JOURNAL = d / "handelsjournal.csv"
        self.w = json.loads((HIER / "wachen.json").read_text("utf-8"))
        self.w.update(kill_switch_gesamt_usd=45.0)
        for k in ("kill_frist_stunden", "kill_wiederaufnahme", "kill_verkauf_ohne_freigabekette"):
            self.w.pop(k, None)
        handeln._wachen = lambda: dict(self.w)
        self.kurs = 96.0
        handeln._letzter_kurs = lambda w, key: self.kurs
        handeln.pruefe_ausstiege = lambda z, w, jetzt=None, live=False: (False, None)
        self.okx = FakeOkxf()
        handeln.okxf = self.okx
        self.einstieg = None
        handeln.pruefe_einstieg = self.fake_einstieg
        self.verluste(5)
        self.zustand()

    def fake_einstieg(self, z, w, jetzt=None):
        if self.einstieg:
            z["position"] = dict(self.einstieg)
            return z["position"], "test"
        return None, "kein Signal"

    def verluste(self, n):
        t0 = jetzt() - datetime.timedelta(days=20)
        for i in range(n):
            tag = (t0 + datetime.timedelta(days=i)).date().isoformat()
            handeln.journal(tag, "ETH_USDT", "long", 100, 95, 110, "stop", 95, -5, -10.0,
                            "0.0", "0.0", 0)

    def zustand(self, **kw):
        z = {"position": None, "letzter_lauf": None, "modus": "papier"}
        z.update(kw)
        handeln.ZUSTAND.write_text(json.dumps(z), "utf-8")

    def lauf(self, modus="papier"):
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            self.meldungen = handeln.lauf(modus)
        self.ausgabe = puffer.getvalue()
        return json.loads(handeln.ZUSTAND.read_text("utf-8"))

    def seit(self, h):
        return (jetzt() - datetime.timedelta(hours=h)).isoformat(timespec="seconds")

    def zeilen(self):
        with open(handeln.JOURNAL, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def test_kill_bucht_papier_zum_marktkurs_und_sperrt_einstieg(self):
        self.zustand(position=pos())
        self.einstieg = pos()
        z = self.lauf()
        self.assertIsNone(z.get("position"))
        letzte = self.zeilen()[-1]
        self.assertEqual(letzte["ausgang"], "kill_zwangsschluss")
        self.assertEqual(float(letzte["ausstieg"]), 96.0)
        self.assertIn("kill_seit", z)

    def test_echte_position_bleibt_im_papierlauf_ohne_schalter(self):
        self.zustand(position=pos("live"))
        z = self.lauf()
        self.assertEqual(z["position"]["inst"], "ETH_USDT")
        self.assertEqual(self.okx.geschlossen, [])
        self.assertEqual(len(self.zeilen()), 5)

    def test_notausstieg_schliesst_echte_position_reduce_only(self):
        self.w["kill_verkauf_ohne_freigabekette"] = True
        self.zustand(position=pos("live"))
        z = self.lauf()
        self.assertIsNone(z.get("position"))
        self.assertEqual(self.okx.geschlossen, [("ETH-USDT-SWAP", 2, "long")])
        self.assertEqual(self.zeilen()[-1]["ausgang"], "kill_zwangsschluss")

    def test_boerse_hat_schon_geschlossen_keine_zweite_order(self):
        self.w["kill_verkauf_ohne_freigabekette"] = True
        self.okx.offen = False
        self.zustand(position=pos("live"))
        self.lauf()
        self.assertEqual(self.okx.geschlossen, [])           # kein Ueberverkauf

    def test_notausstieg_ohne_schluessel_laesst_stehen(self):
        self.w["kill_verkauf_ohne_freigabekette"] = True
        self.okx.schluessel = False
        self.zustand(position=pos("live"))
        self.assertIsNotNone(self.lauf()["position"])
        self.assertEqual(self.okx.geschlossen, [])

    def test_ohne_kurs_bleibt_die_position(self):
        handeln._letzter_kurs = lambda w, key: (_ for _ in ()).throw(RuntimeError("netz"))
        self.zustand(position=pos(letzter_kurs=None))
        self.assertIsNotNone(self.lauf()["position"])

    def test_nach_der_frist_beginnt_der_ruecklauf_bei_null(self):
        self.zustand(kill_seit=self.seit(200))
        z = self.lauf()
        self.assertIn("beginnt bei 0", self.ausgabe)
        self.assertNotIn("kill_seit", z)
        self.assertEqual(z["kill_ab_runde"], 5)
        self.assertNotIn("kill_seit", self.lauf())

    def test_live_position_haelt_die_sperre(self):
        ori = self.seit(200)
        self.zustand(kill_seit=ori, position=pos("live"))
        z = self.lauf()
        self.assertEqual(z["kill_seit"], ori)
        self.assertIn("bleibt gesperrt", self.ausgabe)

    def test_halbierung_wirkt_auf_das_risiko_der_neuen_position(self):
        self.w["kill_switch_gesamt_usd"] = 1000.0
        self.w["drawdown_halbierung_usd"] = 20.0
        self.einstieg = pos(risiko_usd=10.0)
        z = self.lauf()
        self.assertAlmostEqual(z["position"]["risiko_usd"], 5.0)


if __name__ == "__main__":
    unittest.main()
