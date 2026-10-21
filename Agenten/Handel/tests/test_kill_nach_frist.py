"""Der Kill von spur_buch.zyklus (Befund 09.10.2026, behoben am selben Tag, Weg c).

URSPRUNG: Ist der gebuchte Ruecklauf >= Schwelle, stellte zyklus() alle Positionen flach, OHNE
sie zu buchen. Nach der Frist (168 h) lief ein Zyklus frei, im naechsten griff der Kill sofort
wieder (der Ruecklauf war ja nie gesunken) und loeschte die frisch eroeffnete Position wieder
ungebucht: der Kill war faktisch dauerhaft (Backtest PR #20: vier von fuenf Klassikspuren
stehen so binnen eines Jahres still).

JETZT: (1) der Kill schliesst offene Positionen zum Marktkurs und BUCHT sie (Grund
`kill_zwangsschluss`), (2) nach der Frist beginnt der Ruecklauf bei 0 (`kill_ab_runde`).

Alles gegen den echten spur_buch.zyklus in einem Temp-Verzeichnis, ohne Netz.
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
from unittest.mock import patch
from contextlib import redirect_stdout

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)

spec = importlib.util.spec_from_file_location("spur_buch_kill", os.path.join(HANDEL, "spur_buch.py"))
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)

KERZEN = [[0, 100, 101, 99, 100, 1.0]] * 100
INST = "BTC-USDT-SWAP"


def jetzt():
    return datetime.datetime.now(datetime.timezone.utc)


def position(modus="papier", **kw):
    p = {"inst": INST, "seite": "long", "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
         "stop_pct": 5.0, "nominal": 200.0, "modus": modus, "pos_id": "k-1"}
    p.update(kw)
    return p


class Basis(unittest.TestCase):
    kurs = 100.0
    signal_seite = "long"

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="kill-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        with open(os.path.join(HANDEL, "klassik_ema", "wachen.json"), encoding="utf-8") as f:
            self.w = json.load(f)
        # Schwelle fest 45 USD: die Tests haengen nicht an der echten Konfiguration der Spur
        self.w.update(journal_zweitziel=None, risikovorfilter=False, handel_erlaubt=False,
                      kill_switch_gesamt_usd=45.0)
        self.schreibe_wachen()
        self.jp = os.path.join(self.tmp, "handelsjournal.csv")
        self.zp = os.path.join(self.tmp, "zustand.json")
        sb.lege_journal_an(self.jp)
        self.verluste(5)                                     # 5 x -10 USD -> Ruecklauf 50 >= 45
        self.zustand()

    def schreibe_wachen(self):
        with open(os.path.join(self.tmp, "wachen.json"), "w", encoding="utf-8") as f:
            json.dump(self.w, f)

    def verluste(self, n, inst=INST):
        t0 = jetzt() - datetime.timedelta(days=20)
        for i in range(n):
            z = (t0 + datetime.timedelta(minutes=i)).isoformat(timespec="seconds")
            sb.journal(self.jp, zeit=z, modus="papier", aktion="kauf", inst=inst, seite="long",
                       preis="100", einsatz_usd="200.00", grund="test")
            sb.journal(self.jp, zeit=z, modus="papier", aktion="verkauf", inst=inst, seite="long",
                       preis="95", einsatz_usd="190.00", grund="stop")

    def zustand(self, **kw):
        z = {"positionen": [], "modus": "papier", "letzter_lauf": None, "verlust_usd": 0.0}
        z.update(kw)
        with open(self.zp, "w", encoding="utf-8") as f:
            json.dump(z, f)

    def seit(self, stunden):
        return (jetzt() - datetime.timedelta(hours=stunden)).isoformat(timespec="seconds")

    def zyklus(self, modus="papier", kurse=None, signal=None, preis_fuer=None):
        kurse = {INST: self.kurs} if kurse is None else kurse

        def quelle(w):
            return {INST: {"kerzen": KERZEN}}, dict(kurse), []

        sig = (lambda d, w: self.signal_seite) if signal is None else signal
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            sb.zyklus(self.tmp, quelle, sig, modus, "kill-test", preis_fuer=preis_fuer)
        self.ausgabe = puffer.getvalue()
        with open(self.zp, encoding="utf-8") as f:
            return json.load(f)

    def zeilen(self):
        with open(self.jp, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def verkaeufe(self):
        return [r for r in self.zeilen() if r.get("aktion") == "verkauf"]


class FristTest(Basis):
    def test_nach_der_frist_beginnt_der_ruecklauf_bei_null(self):
        self.zustand(kill_seit=self.seit(200))
        z1 = self.zyklus()
        self.assertIn("beginnt bei 0", self.ausgabe)
        self.assertEqual(z1["kill_ab_runde"], 5)
        self.assertNotIn("kill_seit", z1)
        self.assertEqual(len(z1["positionen"]), 1)            # freier Zyklus: Position eroeffnet
        z2 = self.zyklus()
        self.assertEqual(len(z2["positionen"]), 1)            # ... und sie BLEIBT (frueher: ungebucht geloescht)
        self.assertNotIn("kill_seit", z2)
        self.assertEqual(sb.wp.lage(self.w, self.jp, z2)["ruecklauf_usd"], 0.0)

    def test_gewuenscht_position_des_freien_zyklus_wird_nicht_ungebucht_geloescht(self):
        self.zustand(kill_seit=self.seit(200))
        self.zyklus()
        z2 = self.zyklus()
        self.assertTrue(len(z2["positionen"]) == 1 or len(self.verkaeufe()) > 5)

    def test_erst_ein_neuer_rueckgang_loest_den_kill_wieder_aus(self):
        self.zustand(kill_seit=self.seit(200))
        self.zyklus()                                         # Reset
        self.verluste(5)                                      # NEUER Rueckgang um 50 USD
        z = self.zyklus()
        self.assertIn("Kill-Schwelle erreicht", self.ausgabe)
        self.assertIn("kill_seit", z)
        self.assertEqual(z["positionen"], [])

    def test_kleiner_neuer_rueckgang_loest_nichts_aus(self):
        self.zustand(kill_seit=self.seit(200))
        self.zyklus()
        self.verluste(2)                                      # nur -20 USD seit dem Reset
        z = self.zyklus()
        self.assertNotIn("kill_seit", z)
        self.assertEqual(len(z["positionen"]), 1)

    def test_innerhalb_der_frist_bleibt_gesperrt(self):
        self.zustand(kill_seit=self.seit(10))
        z = self.zyklus()
        self.assertEqual(z["positionen"], [])
        self.assertIn("Frist noch", self.ausgabe)
        self.assertEqual(z["kill_seit"][:10], self.seit(10)[:10])    # die laufende Frist wird nicht neu gestartet

    def test_unlesbarer_zeitstempel_gilt_als_neuer_kill(self):
        self.zustand(kill_seit="kaputt", positionen=[position()])
        z = self.zyklus()
        self.assertEqual(z["positionen"], [])
        self.assertNotEqual(z["kill_seit"], "kaputt")
        self.assertEqual(len(self.verkaeufe()), 6)            # die offene Position wurde gebucht


class OptOutTest(Basis):
    def test_ohne_wiederaufnahme_bleibt_die_spur_nach_der_frist_gesperrt(self):
        self.w["kill_wiederaufnahme"] = False
        self.schreibe_wachen()
        ori = self.seit(200)
        self.zustand(kill_seit=ori)
        z = self.zyklus()
        self.assertIn("bleibt gesperrt", self.ausgabe)
        self.assertEqual(z["kill_seit"], ori)                 # Frist wird nicht neu gestartet
        self.assertNotIn("kill_ab_runde", z)
        self.assertEqual(z["positionen"], [])
        z = self.zyklus()                                     # auch beim zweiten Mal
        self.assertEqual(z["positionen"], [])

    def test_ohne_wiederaufnahme_schliesst_der_kill_weiter_offene_positionen(self):
        self.w["kill_wiederaufnahme"] = False
        self.schreibe_wachen()
        self.zustand(kill_seit=self.seit(200), positionen=[position()])
        z = self.zyklus()
        self.assertEqual(z["positionen"], [])
        self.assertEqual(len(self.verkaeufe()), 6)

    def test_standard_ist_wiederaufnahme(self):
        self.zustand(kill_seit=self.seit(200))
        z = self.zyklus()
        self.assertIn("beginnt bei 0", self.ausgabe)
        self.assertNotIn("kill_seit", z)

    def test_wachen_der_live_faehigen_spuren_haben_den_opt_out(self):
        for sp in ("moondev_listingarb", "moondev_marktlage", "moondev_signalwelle",
                   "moondev_topmovers", "omnitrade_futures", "moondev_liquidation",
                   "moondev_sentiment", "moondev_whale"):
            with open(os.path.join(HANDEL, sp, "wachen.json"), encoding="utf-8") as f:
                self.assertIs(json.load(f).get("kill_wiederaufnahme"), False, sp)


class SchliessenTest(Basis):
    def test_kill_bucht_die_offene_position_zum_marktkurs(self):
        self.kurs = 98.0
        self.zustand(positionen=[position()])
        z = self.zyklus()
        self.assertEqual(z["positionen"], [])
        self.assertIn("kill_seit", z)
        v = self.verkaeufe()
        self.assertEqual(len(v), 6)
        letzte = v[-1]
        self.assertEqual(letzte["grund"], "kill_zwangsschluss")
        self.assertAlmostEqual(float(letzte["einsatz_usd"]), 200.0 * (98.0 / 100.0), places=2)   # 196

    def test_kill_zwangsschluss_zaehlt_in_der_kapitalkurve_nicht_in_den_kennzahlen(self):
        self.kurs = 98.0
        # eine echte Position hat im Journal ihre Kaufzeile (daraus bildet wp die Runde)
        sb.journal(self.jp, zeit=(jetzt() - datetime.timedelta(hours=1)).isoformat(timespec="seconds"),
                   modus="papier", aktion="kauf", inst=INST, seite="long", preis="100",
                   einsatz_usd="200.00", grund="test")
        self.zustand(positionen=[position()])
        self.zyklus()
        runden = sb.wp.runden_aus_journal(self.jp)
        self.assertEqual(len(runden), 6)
        echt, stoer = sb.wp.teile_runden(runden)
        self.assertEqual(len(echt), 5)                        # die Kill-Runde ist keine Handelsrunde
        self.assertEqual(len(stoer), 1)
        _hoch, rueck = sb.wp.drawdown(runden)
        self.assertAlmostEqual(rueck, 54.0)                   # 50 + 4: sie zaehlt im Rücklauf

    def test_kill_ohne_kurs_laesst_die_position_im_buch(self):
        self.zustand(positionen=[position()])
        z = self.zyklus(kurse={})
        self.assertEqual(len(z["positionen"]), 1)             # nicht stillschweigend geloescht
        self.assertIn("kill_seit", z)
        self.assertIn("noch offen", self.ausgabe)
        self.assertEqual(len(self.verkaeufe()), 5)

    def test_kurs_ueber_preis_fuer_wird_genutzt(self):
        self.zustand(positionen=[position()])
        z = self.zyklus(kurse={}, preis_fuer=lambda inst: 97.0)
        self.assertEqual(z["positionen"], [])
        self.assertAlmostEqual(float(self.verkaeufe()[-1]["einsatz_usd"]), 194.0, places=2)

    def test_stop_hat_vorrang_vor_zwangsschluss(self):
        self.kurs = 94.0
        self.zustand(positionen=[position()])
        self.zyklus()
        self.assertEqual(self.verkaeufe()[-1]["grund"], "stop")      # ehrlicher Grund, kein "kill"

    def test_vorschau_aendert_nichts(self):
        self.zustand(positionen=[position()])
        vorher_z = open(self.zp, encoding="utf-8").read()
        vorher_j = open(self.jp, encoding="utf-8").read()
        self.zyklus(modus="vorschau")
        self.assertEqual(open(self.zp, encoding="utf-8").read(), vorher_z)
        self.assertEqual(open(self.jp, encoding="utf-8").read(), vorher_j)

    def test_ohne_kill_bleibt_alles_wie_vorher(self):
        # Ruecklauf unter der Schwelle: kein Kill, die offene Position bleibt, nichts wird gebucht
        shutil.rmtree(self.tmp)
        os.makedirs(self.tmp)
        self.w["kill_switch_gesamt_usd"] = 1000.0
        self.schreibe_wachen()
        sb.lege_journal_an(self.jp)
        self.verluste(5)
        self.zustand(positionen=[position()])
        z = self.zyklus()
        self.assertNotIn("kill_seit", z)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(len(self.verkaeufe()), 5)


class FakeWeg:
    """Boersenseite: nur das, was pruefe_ausstiege im Live-Betrieb ruft."""

    def __init__(self):
        self.verkauft, self.storniert = [], []

    def letzter_kurs(self, inst):
        return 97.0

    def algo_stornieren(self, inst, stop_id):
        self.storniert.append((inst, stop_id))

    def markt_verkauf(self, inst, menge):
        self.verkauft.append((inst, menge))


class LiveTest(Basis):
    def test_live_kill_storniert_den_stop_und_verkauft_an_der_boerse(self):
        weg = FakeWeg()
        z = {"positionen": [position(modus="live", stop_id="S1", menge=0.5)]}

        def quelle(w):
            return {}, {INST: 97.0}, []

        offen = sb.kill_schliessen(z, self.w, quelle, None, self.jp, self.zp, live=True, weg=weg)
        self.assertEqual(offen, 0)
        self.assertEqual(weg.storniert, [(INST, "S1")])
        self.assertEqual(weg.verkauft, [(INST, 0.5)])
        self.assertEqual(self.verkaeufe()[-1]["modus"], "live")
        self.assertEqual(self.verkaeufe()[-1]["grund"], "kill_zwangsschluss")

    def test_live_verkauf_scheitert_position_bleibt(self):
        class Kaputt(FakeWeg):
            def markt_verkauf(self, inst, menge):
                raise RuntimeError("Boerse antwortet nicht")

        z = {"positionen": [position(modus="live", stop_id="S1", menge=0.5)]}
        offen = sb.kill_schliessen(z, self.w, lambda w: ({}, {INST: 97.0}, []), None,
                                   self.jp, self.zp, live=True, weg=Kaputt())
        self.assertEqual(offen, 1)
        self.assertEqual(len(self.verkaeufe()), 5)            # nichts gebucht, was nicht verkauft ist


class LivePositionTest(Basis):
    def test_papierzyklus_laesst_live_positionen_im_buch_und_unverkauft(self):
        self.zustand(positionen=[position(modus="live", stop_id="S1", menge=0.5)])
        z = self.zyklus()                                    # modus papier -> live=False
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(z["positionen"][0]["modus"], "live")
        self.assertEqual(len(self.verkaeufe()), 5)           # keine Verkaufszeile dazu
        self.assertIn("kill_seit", z)                        # die Spur ist trotzdem gesperrt

    def test_gemischtes_buch_schliesst_nur_die_papierposition(self):
        self.zustand(positionen=[position(modus="live", stop_id="S1", menge=0.5, pos_id="L"),
                                 position(pos_id="P", inst="ETH-USDT-SWAP")])
        z = self.zyklus(kurse={INST: 100.0, "ETH-USDT-SWAP": 100.0})
        self.assertEqual([p["pos_id"] for p in z["positionen"]], ["L"])
        self.assertEqual(len(self.verkaeufe()), 6)

    def test_live_zyklus_verkauft_die_live_position(self):
        weg = FakeWeg()
        z = {"positionen": [position(modus="live", stop_id="S1", menge=0.5)]}
        offen = sb.kill_schliessen(z, self.w, lambda w: ({}, {INST: 97.0}, []), None,
                                   self.jp, self.zp, live=True, weg=weg)
        self.assertEqual(offen, 0)
        self.assertEqual(weg.verkauft, [(INST, 0.5)])


class NotausstiegTest(Basis):
    """Kill ohne Freigabekette (Auftrag Max 14.10.2026, Entscheidung 2)."""

    def mit_weg(self, weg, ist_basis=True, schluessel=True):
        weg.schluessel_vorhanden = lambda: schluessel
        return (patch.object(sb, "orderweg", lambda w: weg),
                patch.object(sb.risikostufe, "live_erlaubt", lambda: ist_basis))

    def lauf(self, w_extra, weg, **kw):
        self.w.update(w_extra)
        self.schreibe_wachen()
        self.zustand(positionen=[position(modus="live", stop_id="S1", menge=0.5)])
        a, b = self.mit_weg(weg, **kw)
        with a, b:
            return self.zyklus()               # modus papier -> live=False

    def test_schalter_an_verkauft_die_live_position(self):
        weg = FakeWeg()
        z = self.lauf({"kill_verkauf_ohne_freigabekette": True}, weg)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(weg.verkauft, [(INST, 0.5)])
        self.assertEqual(weg.storniert, [(INST, "S1")])

    def test_schalter_aus_laesst_die_position_stehen(self):
        weg = FakeWeg()
        z = self.lauf({}, weg)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(weg.verkauft, [])

    def test_stufe_verkauft_nie(self):
        weg = FakeWeg()
        z = self.lauf({"kill_verkauf_ohne_freigabekette": True}, weg, ist_basis=False)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(weg.verkauft, [])

    def test_ohne_schluessel_verkauft_nichts(self):
        weg = FakeWeg()
        z = self.lauf({"kill_verkauf_ohne_freigabekette": True}, weg, schluessel=False)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(weg.verkauft, [])

    def test_papierposition_geht_nie_an_die_boerse(self):
        weg = FakeWeg()
        self.w.update(kill_verkauf_ohne_freigabekette=True)
        self.schreibe_wachen()
        self.zustand(positionen=[position(), position(modus="live", stop_id="S1", menge=0.5,
                                                      pos_id="L", inst="ETH-USDT-SWAP")])
        a, b = self.mit_weg(weg)
        with a, b:
            z = self.zyklus(kurse={INST: 97.0, "ETH-USDT-SWAP": 97.0})
        self.assertEqual(z["positionen"], [])
        self.assertEqual(weg.verkauft, [("ETH-USDT-SWAP", 0.5)])      # nur die Live-Position

    def test_wachen_der_live_spuren_schalten_ein(self):
        for sp in ("moondev_listingarb", "moondev_marktlage", "moondev_signalwelle",
                   "moondev_topmovers", "omnitrade_futures", "moondev_liquidation",
                   "moondev_sentiment", "moondev_whale"):
            with open(os.path.join(HANDEL, sp, "wachen.json"), encoding="utf-8") as f:
                self.assertIs(json.load(f).get("kill_verkauf_ohne_freigabekette"), True, sp)


class LageTest(Basis):
    def test_ruecklauf_ohne_marke_ist_unveraendert(self):
        self.assertAlmostEqual(sb.wp.lage(self.w, self.jp, {})["ruecklauf_usd"], 50.0)

    def test_ruecklauf_ab_marke(self):
        s = sb.wp.lage(self.w, self.jp, {"kill_ab_runde": 3})
        self.assertAlmostEqual(s["ruecklauf_usd"], 20.0)      # nur die letzten 2 Runden
        self.assertEqual(s["kill_ab_runde"], 3)
        self.assertEqual(s["runden_gesamt"], 5)

    def test_marke_ueber_der_rundenzahl_gibt_null(self):
        self.assertEqual(sb.wp.lage(self.w, self.jp, {"kill_ab_runde": 99})["ruecklauf_usd"], 0.0)

    def test_kaputte_marke_wird_ignoriert(self):
        self.assertAlmostEqual(sb.wp.lage(self.w, self.jp, {"kill_ab_runde": "x"})["ruecklauf_usd"], 50.0)


if __name__ == "__main__":
    unittest.main()
