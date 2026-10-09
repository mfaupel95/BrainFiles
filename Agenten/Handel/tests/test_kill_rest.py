"""Kill der Spuren mit eigenem Lauf (Auftrag Max 09.10.2026, Punkt 1 nach PR #21).

supertrend, squeeze, wavetrend, macd_mtf, moondev_funding und iv_waelle leerten im Kill die
Positionen OHNE Buchung und blieben danach fuer immer gesperrt (keine Frist). Jetzt wie
spur_buch: Zwangsschluss zum Marktkurs MIT Verkaufszeile (Grund `kill_zwangsschluss`), nach
`kill_frist_stunden` beginnt der Ruecklauf bei 0, Opt-out `kill_wiederaufnahme: false`.

Gegen die echten handeln.py in einem Temp-Verzeichnis, ohne Netz.
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
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)

KERZEN = [[i * 3600000, 100.0, 101.0, 99.0, 100.0, 1.0] for i in range(400)]
INST = "BTC-USDT-SWAP"


def jetzt():
    return datetime.datetime.now(datetime.timezone.utc)


def lade(spur):
    pfad = os.path.join(HANDEL, spur, "handeln.py")
    alt = list(sys.path)
    sys.path.insert(0, os.path.join(HANDEL, spur))
    try:
        spec = importlib.util.spec_from_file_location("kill_rest_" + spur, pfad)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    finally:
        sys.path[:] = alt
    return m


def position(**kw):
    p = {"inst": INST, "seite": "long", "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
         "stop_pct": 5.0, "nominal": 200.0, "modus": "papier", "pos_id": "k-1",
         "eroeffnet_zeit": jetzt().isoformat(timespec="seconds")}
    p.update(kw)
    return p


class Basis:
    """Gemeinsamer Teil; die Unterklassen binden die Spur an."""
    spur = None

    def setUp(self):
        self.m = lade(self.spur)
        self.tmp = tempfile.mkdtemp(prefix="killrest-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        with open(os.path.join(HANDEL, self.spur, "wachen.json"), encoding="utf-8") as f:
            self.w = json.load(f)
        self.w.update(kill_switch_gesamt_usd=45.0, handel_erlaubt=False)
        self.w.pop("kill_frist_stunden", None)
        self.w.pop("kill_wiederaufnahme", None)
        self.binde()
        self.schreibe_wachen()
        self.verluste(5)                                  # 5 x -10 USD -> Ruecklauf 50 >= 45
        self.zustand()

    # ---- Anbindung je Spur (Standard: Kerzenspuren) ----
    def binde(self):
        m = self.m
        m.WACHEN = os.path.join(self.tmp, "wachen.json")
        m.ZUSTAND = os.path.join(self.tmp, "zustand.json")
        m.JOURNAL = os.path.join(self.tmp, "handelsjournal.csv")
        m.SCHREIBEN = True
        m.lade_kerzen = lambda inst, intervall, anzahl: [list(k) for k in KERZEN]
        m.spiegeln = lambda z, w: None
        self.zp, self.jp = m.ZUSTAND, m.JOURNAL

    def schreibe_wachen(self):
        with open(os.path.join(self.tmp, "wachen.json"), "w", encoding="utf-8") as f:
            json.dump(self.w, f)

    def journal(self, **kw):
        self.m.journal(**kw)

    def lauf(self):
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            self.m.lauf("papier")
        self.ausgabe = puffer.getvalue()
        with open(self.zp, encoding="utf-8") as f:
            return json.load(f)

    # ---- gemeinsam ----
    def verluste(self, n):
        t0 = jetzt() - datetime.timedelta(days=20)
        for i in range(n):
            z = (t0 + datetime.timedelta(minutes=i)).isoformat(timespec="seconds")
            self.journal(zeit=z, modus="papier", aktion="kauf", inst=INST, seite="long",
                         preis="100", einsatz_usd="200.00", grund="test")
            self.journal(zeit=z, modus="papier", aktion="verkauf", inst=INST, seite="long",
                         preis="95", einsatz_usd="190.00", grund="stop")

    def zustand(self, **kw):
        z = {"positionen": [], "modus": "papier", "letzter_lauf": None, "verlust_usd": 0.0}
        z.update(kw)
        with open(self.zp, "w", encoding="utf-8") as f:
            json.dump(z, f)

    def seit(self, stunden):
        return (jetzt() - datetime.timedelta(hours=stunden)).isoformat(timespec="seconds")

    def verkaeufe(self):
        with open(self.jp, encoding="utf-8", newline="") as f:
            return [r for r in csv.DictReader(f) if r.get("aktion") == "verkauf"]

    # ---- Tests ----
    def test_kill_bucht_die_offene_position_zum_marktkurs(self):
        self.zustand(positionen=[position()])
        z = self.lauf()
        self.assertEqual(z["positionen"], [])
        zw = [r for r in self.verkaeufe() if "zwangsschluss" in r["grund"]]
        self.assertEqual(len(zw), 1)
        self.assertIn("kill_seit", z)
        self.assertEqual(len(self.verkaeufe()), 6)

    def test_innerhalb_der_frist_bleibt_gesperrt(self):
        ori = self.seit(10)
        self.zustand(kill_seit=ori)
        z = self.lauf()
        self.assertEqual(z["kill_seit"], ori)
        self.assertEqual(z["positionen"], [])
        self.assertIn("Frist noch", self.ausgabe)

    def test_nach_der_frist_beginnt_der_ruecklauf_bei_null(self):
        self.zustand(kill_seit=self.seit(200))
        z = self.lauf()
        self.assertIn("beginnt bei 0", self.ausgabe)
        self.assertNotIn("kill_seit", z)
        self.assertEqual(z["kill_ab_runde"], 5)
        z2 = self.lauf()                                  # kein sofortiger Re-Kill
        self.assertNotIn("kill_seit", z2)

    def test_neuer_rueckgang_loest_den_kill_wieder_aus(self):
        self.zustand(kill_seit=self.seit(200))
        self.lauf()
        self.verluste(5)
        z = self.lauf()
        self.assertIn("Kill-Schwelle erreicht", self.ausgabe)
        self.assertIn("kill_seit", z)

    def test_opt_out_haelt_die_sperre_auch_nach_der_frist(self):
        self.w["kill_wiederaufnahme"] = False
        self.schreibe_wachen()
        ori = self.seit(200)
        self.zustand(kill_seit=ori, positionen=[position()])
        z = self.lauf()
        self.assertEqual(z["kill_seit"], ori)
        self.assertNotIn("kill_ab_runde", z)
        self.assertEqual(z["positionen"], [])
        self.assertIn("bleibt gesperrt", self.ausgabe)

    def test_stop_hat_vorrang_vor_zwangsschluss(self):
        self.zustand(positionen=[position(stop=101.0)])   # Kurs 100 <= Stop 101
        self.lauf()
        letzte = self.verkaeufe()[-1]
        self.assertEqual(letzte["grund"], "stop")


class SupertrendKill(Basis, unittest.TestCase):
    spur = "supertrend"


class SqueezeKill(Basis, unittest.TestCase):
    spur = "squeeze"


class WavetrendKill(Basis, unittest.TestCase):
    spur = "wavetrend"


class MacdMtfKill(Basis, unittest.TestCase):
    spur = "macd_mtf"


class FundingKill(Basis, unittest.TestCase):
    spur = "moondev_funding"

    def binde(self):
        super().binde()
        m = self.m
        del m.lade_kerzen
        m.hole_kurse = lambda w, z: ({INST: {}}, {INST: 100.0}, [])
        m.pruefe_einstieg = lambda *a, **k: None
        w = self.w
        w["instrumente"] = [INST]


class IvWaelleKill(Basis, unittest.TestCase):
    spur = "iv_waelle"

    def binde(self):
        m = self.m
        m.wachen_pfad = os.path.join(self.tmp, "wachen.json")
        m.zustand_pfad = os.path.join(self.tmp, "zustand.json")
        m.journal_pfad = os.path.join(self.tmp, "handelsjournal.csv")
        m.markt_quelle = lambda w: ({INST: {"spot": 100.0, "basispreis": 100.0,
                                            "iv_prozent": 50.0, "hv_prozent": 50.0,
                                            "kette": []}}, {INST: 100.0}, [])
        self.zp, self.jp = m.zustand_pfad, m.journal_pfad
        m.buch.lege_journal_an(self.jp)

    def journal(self, **kw):
        self.m.buch.journal(self.jp, **kw)



if __name__ == "__main__":
    unittest.main()
