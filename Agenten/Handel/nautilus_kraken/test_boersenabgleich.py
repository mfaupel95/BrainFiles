"""Tests fuer nautilus_kraken/boersenabgleich.py (T-227).

Kein Netz, keine Order: die Boerse ist eine Attrappe, `laden` ist die Naht.
Geprueft werden die REGELN:

  (a) gesunder Fall: Bestand da + Stop offen -> nichts tun;
  (b) stornierter Stop -> neu setzen, und zwar ueber den GEHALTENEN Bestand;
  (c) Position ohne Bestand + Stop gefeuert -> mit ECHTEM Erloes ausbuchen;
  (d) Position ohne Bestand, Stop nicht gefeuert -> NICHT buchen;
  (e) Waisenstop -> stornieren;
  (f) fremder Stop wird nie angefasst;
  (g) Papiermodus: keine Live-Position -> kein Boersenabruf;
  (h) Vorschau schreibt nichts, ordert nichts;
  (i) unlesbarer Bestand -> Buch unangetastet.

Aufruf:  .venv\\Scripts\\python.exe -m unittest test_boersenabgleich -v
"""

import os
import sys
import tempfile
import time
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HIER, HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)

import boersenabgleich  # noqa: E402


# --- Attrappen --------------------------------------------------------------

class FakeBoerse:
    """Ein Boersenzugang ohne Netz - dieselbe Oberflaeche wie KrakenBoerse."""

    def __init__(self, bestaende=None, stops=None, fremd=(), fehler=None):
        self.bestaende = dict(bestaende or {})     # {token: menge}
        self.stops = dict(stops or {})             # {txid: {...}}
        self.fremd = list(fremd)
        self.fehler = fehler
        self.gesetzt = []
        self.storniert = []
        self.gelesen = 0

    def basis(self, token):
        return token

    def bestand(self, token):
        self.gelesen += 1
        if self.fehler:
            raise RuntimeError(self.fehler)
        return float(self.bestaende.get(token, 0.0))

    def stop_wirksam(self, txid):
        if not txid:
            return False
        d = self.stops.get(txid)
        if d is None or d.get("unbekannt"):
            return None
        if float(d.get("vol_exec") or 0) > 0:
            return False
        return d.get("status") == "open"

    def stop_gefuellt(self, txid):
        return float((self.stops.get(txid) or {}).get("vol_exec") or 0) > 0

    def ausstieg(self, token, txid):
        d = self.stops.get(txid) or {}
        menge = float(d.get("vol_exec") or 0)
        cost = float(d.get("cost") or 0)
        if menge <= 0 or cost <= 0:
            return None
        return {"menge": menge, "preis": cost / menge,
                "erloes": cost - float(d.get("fee") or 0), "art": "stop-loss",
                "misc": "stopped"}

    def menge_gerundet(self, token, menge):
        m = float("%.8f" % float(menge))
        return m if m > 0 else None

    def stop_setzen(self, token, menge, preis):
        self.gesetzt.append((token, menge, preis))
        return "NEU-%d" % len(self.gesetzt)

    def stop_stornieren(self, token, txid):
        self.storniert.append((token, txid))

    def fremde_stops(self, bekannt):
        return list(self.fremd)


class Journal:
    def __init__(self):
        self.zeilen = []

    def __call__(self, **felder):
        self.zeilen.append(felder)


def live(token="BTC/EUR", **abweichend):
    p = {"token": token, "seite": "long", "preis_einstieg": 100.0,
         "stop_preis": 95.0, "einsatz_eur": 50.0, "menge": 0.5,
         "modus": "live", "stop_id": "S1", "boersen_stop_fehlt": False}
    p.update(abweichend)
    return p


def papier(token="BTC/EUR", **abweichend):
    p = {"token": token, "seite": "long", "preis_einstieg": 100.0,
         "stop_preis": 95.0, "einsatz_eur": 50.0, "menge": 0.5}
    p.update(abweichend)
    return p


def buch(*positionen):
    return {"positionen": list(positionen)}


def laufe(z, boerse, journal=None, anwenden=True, standard="kraken"):
    return boersenabgleich.pruefe(
        z, anwenden=anwenden, journal=journal, standard=standard,
        laden=lambda namen: {n: boerse for n in namen})


def offener_stop(preis=95.0, menge=0.5):
    return {"status": "open", "vol_exec": 0, "preis": preis, "menge": menge}


# --- Modulwaechter ----------------------------------------------------------

def _ordner_stand():
    out = {}
    for name in ("zustand.json", "handelsjournal.csv",
                 "zustand.futures.json", "handelsjournal.futures.csv"):
        p = os.path.join(HIER, name)
        out[name] = os.path.getsize(p) if os.path.exists(p) else None
    return out


def setUpModule():
    global _vorher
    _vorher = _ordner_stand()


def tearDownModule():
    nach = _ordner_stand()
    geaendert = [k for k in nach if nach[k] != _vorher.get(k)]
    assert not geaendert, ("Test hat in den ECHTEN Spurenordner geschrieben: %s"
                           % geaendert)


# --- Tests ------------------------------------------------------------------

class GesunderFallTest(unittest.TestCase):
    def test_bestand_da_stop_offen_nichts_zu_tun(self):
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC/EUR": 0.5}, stops={"S1": offener_stop()})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["ok"], 1)
        self.assertEqual(bilanz["nachgesetzt"], 0)
        self.assertEqual(b.gesetzt, [])
        self.assertEqual(len(z["positionen"]), 1)
        self.assertFalse(z["positionen"][0]["boersen_stop_fehlt"])

    def test_alte_behauptung_wird_berichtigt(self):
        z = buch(live(boersen_stop_fehlt=True))
        b = FakeBoerse(bestaende={"BTC/EUR": 0.5}, stops={"S1": offener_stop()})
        laufe(z, b)
        self.assertFalse(z["positionen"][0]["boersen_stop_fehlt"])


class StornierterStopTest(unittest.TestCase):
    def test_stornierter_stop_wird_ueber_den_bestand_nachgesetzt(self):
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC/EUR": 0.4},
                       stops={"S1": {"status": "canceled", "vol_exec": 0}})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["nachgesetzt"], 1)
        self.assertEqual(b.gesetzt, [("BTC/EUR", 0.4, 95.0)])
        p = z["positionen"][0]
        self.assertEqual(p["stop_id"], "NEU-1")
        self.assertFalse(p["boersen_stop_fehlt"])

    def test_stop_wird_nie_ueber_mehr_als_den_bestand_gesetzt(self):
        z = buch(live(einsatz_eur=100.0, menge=1.0))
        b = FakeBoerse(bestaende={"BTC/EUR": 0.4},
                       stops={"S1": {"status": "canceled", "vol_exec": 0}})
        laufe(z, b)
        self.assertEqual(b.gesetzt[0][1], 0.4)

    def test_fehlende_kennung_setzt_ebenfalls(self):
        z = buch(live(stop_id=""))
        b = FakeBoerse(bestaende={"BTC/EUR": 0.5}, stops={})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["nachgesetzt"], 1)
        self.assertEqual(len(b.gesetzt), 1)

    def test_bestand_unter_ordermin_bleibt_ohne_stop_gemeldet(self):
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC/EUR": 0.5},
                       stops={"S1": {"status": "canceled", "vol_exec": 0}})
        b.menge_gerundet = lambda token, menge: None
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["fehlt_weiter"], 1)
        self.assertEqual(bilanz["nachgesetzt"], 0)
        self.assertEqual(b.gesetzt, [])
        self.assertTrue(z["positionen"][0]["boersen_stop_fehlt"])


class PositionWegTest(unittest.TestCase):
    def test_gefeuerter_stop_bucht_mit_echtem_erloes_aus(self):
        z = buch(live())
        b = FakeBoerse(bestaende={}, stops={"S1": {
            "status": "closed", "vol_exec": 0.5, "cost": 47.5, "fee": 0.285}})
        j = Journal()
        bilanz = laufe(z, b, journal=j)
        self.assertEqual(bilanz["ausgebucht"], 1)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(len(j.zeilen), 1)
        zeile = j.zeilen[0]
        self.assertEqual(zeile["modus"], "live")
        self.assertEqual(zeile["aktion"], "verkauf")
        self.assertEqual(zeile["grund"], "boersen_stop")
        self.assertAlmostEqual(float(zeile["einsatz_eur"]), 47.22, places=2)
        self.assertAlmostEqual(float(zeile["preis"]), 95.0, places=6)

    def test_ohne_beleg_kein_buch(self):
        z = buch(live())
        b = FakeBoerse(bestaende={},
                       stops={"S1": {"status": "canceled", "vol_exec": 0}})
        j = Journal()
        bilanz = laufe(z, b, journal=j)
        self.assertEqual(bilanz["ausgebucht"], 0)
        self.assertEqual(bilanz["unklar"], 1)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(j.zeilen, [])

    def test_nachgesetzter_stop_kommt_bei_einer_weg_position_nicht_mehr(self):
        z = buch(live())
        b = FakeBoerse(bestaende={}, stops={"S1": {
            "status": "closed", "vol_exec": 0.5, "cost": 47.5, "fee": 0.285}})
        laufe(z, b)
        self.assertEqual(b.gesetzt, [])


class WaisenstopTest(unittest.TestCase):
    def test_stop_ohne_position_wird_storniert(self):
        z = buch(live(token="BTC/EUR", stop_id="S9"),
                 papier(token="BTC/EUR", stop_id="P1"))
        b = FakeBoerse(bestaende={"BTC/EUR": 0.5},
                       stops={"S9": offener_stop(), "P1": offener_stop()})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["waisen"], 1)
        self.assertEqual(b.storniert, [("BTC/EUR", "P1")])

    def test_fremder_stop_wird_nie_angefasst(self):
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC/EUR": 0.5}, stops={"S1": offener_stop()},
                       fremd=[("FREMD-1", {"paar": "XXBTZEUR"})])
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["waisen"], 0)
        self.assertEqual(b.storniert, [])

    def test_erledigter_waisenstop_wird_vergessen(self):
        z = buch(live(token="BTC/EUR", stop_id="S9"),
                 papier(token="BTC/EUR", stop_id="P1"))
        b = FakeBoerse(bestaende={"BTC/EUR": 0.5},
                       stops={"S9": offener_stop(),
                              "P1": {"status": "closed", "vol_exec": 1.0}})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["waisen"], 0)
        self.assertEqual(b.storniert, [])


class PapiermodusTest(unittest.TestCase):
    def test_ohne_live_position_kein_boersenabruf(self):
        z = buch(papier(), papier(token="ETH/EUR"))
        gerufen = []

        def laden(namen):
            gerufen.append(namen)
            return {}

        bilanz = boersenabgleich.pruefe(z, anwenden=True, laden=laden)
        self.assertEqual(gerufen, [])
        self.assertEqual(bilanz["geprueft"], 0)
        self.assertEqual(len(z["positionen"]), 2)

    def test_papierposition_wird_nicht_ausgebucht(self):
        z = buch(live(), papier(token="ETH/EUR"))
        b = FakeBoerse(bestaende={"BTC/EUR": 0.5, "ETH/EUR": 0.0},
                       stops={"S1": offener_stop()})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["geprueft"], 1)
        self.assertEqual(len(z["positionen"]), 2)


class VorschauTest(unittest.TestCase):
    def test_vorschau_setzt_keinen_stop_und_bucht_nicht(self):
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC/EUR": 0.5},
                       stops={"S1": {"status": "canceled", "vol_exec": 0}})
        j = Journal()
        bilanz = laufe(z, b, journal=j, anwenden=False)
        self.assertEqual(bilanz["fehlt_weiter"], 1)
        self.assertEqual(b.gesetzt, [])
        self.assertEqual(j.zeilen, [])
        self.assertEqual(z["positionen"][0]["stop_id"], "S1")

    def test_vorschau_bucht_weg_position_nicht_aus(self):
        z = buch(live())
        b = FakeBoerse(bestaende={}, stops={"S1": {
            "status": "closed", "vol_exec": 0.5, "cost": 47.5, "fee": 0.285}})
        j = Journal()
        bilanz = laufe(z, b, journal=j, anwenden=False)
        self.assertEqual(bilanz["weg"], 1)
        self.assertEqual(bilanz["ausgebucht"], 0)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(j.zeilen, [])


class UnklarerFallTest(unittest.TestCase):
    def test_unlesbarer_bestand_laesst_das_buch_in_ruhe(self):
        z = buch(live())
        b = FakeBoerse(fehler="Netzfehler")
        j = Journal()
        bilanz = laufe(z, b, journal=j)
        self.assertEqual(bilanz["unklar"], 1)
        self.assertEqual(bilanz["ok"], 0)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(b.gesetzt, [])
        self.assertEqual(j.zeilen, [])

    def test_unbekannte_boerse_wird_gemeldet_statt_geraten(self):
        z = buch(live(boerse="unbekannt"))
        b = FakeBoerse(bestaende={"BTC/EUR": 0.5}, stops={"S1": offener_stop()})
        bilanz = boersenabgleich.pruefe(
            z, anwenden=True,
            laden=lambda namen: {n: (b if n == "kraken" else None)
                                 for n in namen})
        self.assertEqual(bilanz["unklar"], 1)
        self.assertEqual(bilanz["ok"], 0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_nicht_lesbarer_stop_gilt_nicht_als_fehlt(self):
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC/EUR": 0.5},
                       stops={"S1": {"unbekannt": True}})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["unklar"], 1)
        self.assertEqual(b.gesetzt, [])


class ZeitwacheTest(unittest.TestCase):
    def test_frische_zustandsdatei_verhindert_das_schreiben(self):
        with tempfile.TemporaryDirectory() as d:
            pfad = os.path.join(d, "zustand.json")
            with open(pfad, "w", encoding="utf-8") as f:
                f.write('{"positionen": []}\n')
            os.utime(pfad, (time.time(), time.time()))
            rc = boersenabgleich.main(["--anwenden", "--pfad", pfad])
            self.assertEqual(rc, 2)
            with open(pfad, encoding="utf-8") as f:
                self.assertEqual(f.read(), '{"positionen": []}\n')

    def test_leeres_buch_ohne_boersenabruf(self):
        with tempfile.TemporaryDirectory() as d:
            pfad = os.path.join(d, "zustand.json")
            with open(pfad, "w", encoding="utf-8") as f:
                f.write('{"positionen": []}\n')
            self.assertEqual(boersenabgleich.main(["--pfad", pfad]), 0)


class EinbauTest(unittest.TestCase):
    """Der Abgleich muss in handeln.py eingebaut sein."""

    def _quelle(self):
        with open(os.path.join(HIER, "handeln.py"), encoding="utf-8") as f:
            return f.read()

    def test_abgleich_wird_gerufen(self):
        q = self._quelle()
        self.assertIn("boersenabgleich.pruefe(", q)

    def test_abgleich_steht_im_live_zweig(self):
        q = self._quelle()
        i = q.index("boersenabgleich.pruefe(")
        block = q[max(0, i - 500):i]
        self.assertIn("live_vorab", block)


if __name__ == "__main__":
    unittest.main()