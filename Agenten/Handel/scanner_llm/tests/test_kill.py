"""Kill der Spur scanner_llm: Zwangsschluss mit Buchung, Live-Schutz, Frist, Notausstieg.

Bis 20.10.2026 buchte flach_stellen im Papierlauf auch eine echte Live-Position
(kauf_ord_id) mit einer Papier-Zeile aus - an der Boerse blieb sie offen - und
sperrte die Spur ohne Frist dauerhaft. Ohne Netz, ohne LLM: marktkurs und okx
werden ersetzt.
"""
import csv
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
SPUR_DIR = HIER.parent
sys.path.insert(0, str(SPUR_DIR))

import handeln  # noqa: E402


def jetzt():
    return datetime.datetime.now(datetime.timezone.utc)


def pos(inst, kauf_ord_id=None, usd=60.0):
    return {"inst": inst, "einstieg": 10.0, "stop": 9.0, "ziel": 12.0, "usd": usd,
            "stop_pct": 10.0, "kauf_ord_id": kauf_ord_id, "pos_id": "k-" + inst,
            "eroeffnet": jetzt().strftime("%Y-%m-%d")}


class FakeOkx:
    def __init__(self):
        self.verkauft = []
        self.schluessel = True

    def markt_verkauf(self, inst, menge):
        self.verkauft.append((inst, menge))

    def schluessel_vorhanden(self):
        return self.schluessel


class KillSpur(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        for name in ("ZUSTAND", "JOURNAL", "okx", "marktkurs", "wachen", "vorschlaege",
                     "llm_sieben", "sperre_zu", "_spiegeln"):
            self.addCleanup(setattr, handeln, name, getattr(handeln, name))
        self.addCleanup(setattr, handeln.scan, "BERICHTE", handeln.scan.BERICHTE)
        handeln.ZUSTAND = d / "zustand.json"
        handeln.JOURNAL = d / "handelsjournal.csv"
        (d / "neuester.json").write_text(json.dumps({"datum": "2026-10-20"}), "utf-8")
        handeln.scan.BERICHTE = d
        self.okx = FakeOkx()
        handeln.okx = self.okx
        handeln.marktkurs = lambda inst: 10.0
        handeln.vorschlaege = lambda b, w: []
        handeln.llm_sieben = lambda vs, w: []
        handeln.sperre_zu = lambda grund: False
        handeln._spiegeln = lambda w: None
        self.w = json.loads((SPUR_DIR / "wachen.json").read_text("utf-8"))
        self.w.update(kill_switch_gesamt_usd=45.0, handel_erlaubt=False, journal_zweitziel="")
        self.w.pop("kill_frist_stunden", None)
        self.w.pop("kill_wiederaufnahme", None)
        self.w.pop("kill_verkauf_ohne_freigabekette", None)
        handeln.wachen = lambda: dict(self.w)
        self.verluste(5)                                   # 5 x -10 -> Ruecklauf 50 >= 45
        self.zustand()

    def verluste(self, n):
        t0 = jetzt() - datetime.timedelta(days=20)
        for i in range(n):
            z = (t0 + datetime.timedelta(minutes=i)).isoformat(timespec="seconds")
            handeln.journal(z, "papier", "kauf", "BTC-USDC", "10", "60.00", "9", "12",
                            "test", "0", "0", "0", "v%d" % i)
            handeln.journal((t0 + datetime.timedelta(minutes=i, seconds=30)).isoformat(
                timespec="seconds"), "papier", "verkauf", "BTC-USDC", "8.5", "50.00",
                            "9", "12", "stop", "0", "0", "0", "v%d" % i)

    def zustand(self, **kw):
        z = {"positionen": [], "letzte_stops": {}, "letzte_ziele": {},
             "letzter_lauf": None, "modus": None}
        z.update(kw)
        handeln.ZUSTAND.write_text(json.dumps(z), "utf-8")

    def lauf(self, modus="papier"):
        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            handeln.lauf(modus)
        self.ausgabe = puffer.getvalue()
        return json.loads(handeln.ZUSTAND.read_text("utf-8"))

    def seit(self, h):
        return (jetzt() - datetime.timedelta(hours=h)).isoformat(timespec="seconds")

    def verkaeufe(self):
        with open(handeln.JOURNAL, encoding="utf-8", newline="") as f:
            return [r for r in csv.DictReader(f) if r["aktion"] == "verkauf"]

    def test_papier_wird_zum_marktkurs_gebucht(self):
        self.zustand(positionen=[pos("ETH-USDC")])
        z = self.lauf()
        self.assertEqual(z["positionen"], [])
        zw = [r for r in self.verkaeufe() if r["grund"] == "kill_zwangsschluss"]
        self.assertEqual(len(zw), 1)
        self.assertEqual(zw[0]["modus"], "papier")
        self.assertIn("kill_seit", z)
        self.assertEqual(self.okx.verkauft, [])

    def test_live_position_bleibt_im_papierlauf_ohne_schalter(self):
        self.zustand(positionen=[pos("ETH-USDC", "ord-1"), pos("SOL-USDC")])
        z = self.lauf()
        self.assertEqual([p["inst"] for p in z["positionen"]], ["ETH-USDC"])
        self.assertEqual(self.okx.verkauft, [])
        self.assertEqual(len(self.verkaeufe()), 6)         # 5 alte + SOL

    def test_notausstieg_verkauft_live_mit_schalter(self):
        self.w["kill_verkauf_ohne_freigabekette"] = True
        self.zustand(positionen=[pos("ETH-USDC", "ord-1")])
        z = self.lauf()
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self.okx.verkauft, [("ETH-USDC", 6.0)])
        letzte = self.verkaeufe()[-1]
        self.assertEqual((letzte["modus"], letzte["grund"]), ("live", "kill_zwangsschluss"))

    def test_notausstieg_ohne_schluessel_verkauft_nicht(self):
        self.w["kill_verkauf_ohne_freigabekette"] = True
        self.okx.schluessel = False
        self.zustand(positionen=[pos("ETH-USDC", "ord-1")])
        z = self.lauf()
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self.okx.verkauft, [])

    def test_ohne_kurs_bleibt_die_position(self):
        handeln.marktkurs = lambda inst: None
        self.zustand(positionen=[pos("ETH-USDC")])
        self.assertEqual(len(self.lauf()["positionen"]), 1)

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
        self.assertNotIn("kill_seit", self.lauf())         # kein sofortiger Re-Kill

    def test_opt_out_haelt_die_sperre(self):
        self.w["kill_wiederaufnahme"] = False
        ori = self.seit(200)
        self.zustand(kill_seit=ori)
        z = self.lauf()
        self.assertEqual(z["kill_seit"], ori)
        self.assertNotIn("kill_ab_runde", z)

    def test_herzschlag_alt_laesst_live_im_papierlauf_stehen(self):
        z = {"positionen": [pos("ETH-USDC", "ord-1"), pos("SOL-USDC")]}
        rest = handeln.flach_stellen(z, False, "herzschlag_alt")
        self.assertEqual(rest, 1)
        self.assertEqual([p["inst"] for p in z["positionen"]], ["ETH-USDC"])

    def test_wachen_json_schaltet_ein(self):
        w = json.loads((SPUR_DIR / "wachen.json").read_text("utf-8"))
        self.assertIs(w.get("kill_wiederaufnahme"), False)
        self.assertIs(w.get("kill_verkauf_ohne_freigabekette"), True)


if __name__ == "__main__":
    unittest.main()
