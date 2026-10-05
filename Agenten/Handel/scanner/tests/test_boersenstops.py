"""Buch gegen Boerse: Notausstieg und Bestand jeder Live-Position.

Anlass (28.09.2026): Auf dem OKX-Konto standen vier Live-Positionen (BTC, ETH,
SOL, HYPE, rund 385 USD) ohne Stop - die vier Stops waren am 26.09. zwischen
14:25:59 und 14:26:06 an der Boerse storniert worden, waehrend ``zustand.json``
weiter ``boersen_stop_fehlt: false`` behauptete. Zusaetzlich war ZEC-USDC am
24.09. um 11:31 vom eigenen Stop verkauft worden und stand danach als Geist im
Buch. Die Lehre: die Fragen "ist der Bestand noch da?" und "ist der Notausstieg
noch wirksam?" kann nur die BOERSE beantworten.

Diese Tests laufen ohne Netz: ``okx`` wird durch eine Attrappe ersetzt, die
Antworten vorgegeben. Geschrieben wird nur in ein dict; die echte zustand.json
wird nie angefasst.
"""
import os
import sys
import unittest

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SPUR)
import boersenstops as bs  # noqa: E402

assert bs.__file__.startswith(SPUR), bs.__file__


class FakeOKX:
    """Attrappe der vier Boersen-Funktionen, die der Abgleich braucht."""

    def __init__(self, bestaende=None, stops=None, fuellungen=None,
                 setzen_fehler=None, algo=None, algo_fehler=None,
                 lot=None):
        self.bestaende = bestaende or {}      # inst -> (eq, frei)
        self.stops = stops or {}              # algoId -> dict
        self.fuellungen = fuellungen or {}    # inst -> dict
        self.setzen_fehler = setzen_fehler
        # T-362: die vierte Abgleichsstufe liest die offenen Algo-
        # Orders ueber `_roh` (die dritte las nur `stop_details`).
        self.algo = algo or {}                # ordType -> Liste
        self.algo_fehler = algo_fehler
        self.lot = lot or {}                   # inst -> {"lotSz": ...}
        self.gesetzt = []                     # (inst, menge, preis)
        self.storniert = []

    def bestand(self, inst):
        if inst not in self.bestaende:
            raise RuntimeError("kein Bestand messbar")
        return self.bestaende[inst]

    def stop_details(self, sid):
        if sid not in self.stops:
            raise RuntimeError("Stop unbekannt")
        return self.stops[sid]

    def stop_setzen(self, inst, menge, preis):
        if self.setzen_fehler:
            raise RuntimeError(self.setzen_fehler)
        self.gesetzt.append((inst, menge, preis))
        return "neu-%d" % len(self.gesetzt)

    def stop_stornieren(self, sid, inst=None):
        self.storniert.append(sid)

    def menge_gerundet(self, inst, menge):
        return round(menge, 6)

    def letzte_fuellung(self, inst, seite="sell"):
        return self.fuellungen.get(inst)

    def _roh(self, pfad, methode="GET", body=None, signiert=False):
        """Die offenen Algo-Auftraege je ordType (T-362)."""
        if self.algo_fehler:
            raise RuntimeError(self.algo_fehler)
        for typ in ("conditional", "oco", "move_order_stop"):
            if "ordType=%s" % typ in pfad:
                return list(self.algo.get(typ) or [])
        return []

    def instrument_regeln(self, inst):
        """lotSz/tickSz je Markt - die Toleranz der Deckung (T-362)."""
        return dict((self.lot or {}).get(inst) or {})


def position(inst="ETH-USDC", usd=100.0, einstieg=2500.0, stop=2400.0,
             stop_ord_id="alt-1", kauf="3943775234458243072"):
    p = {"inst": inst, "einstieg": einstieg, "usd": usd, "stop": stop,
         "ziel": 2800.0, "eroeffnet": "2026-09-22", "mfe_pct": 3.0,
         "mae_pct": -1.0}
    if kauf:
        p["kauf_ord_id"] = kauf
    if stop_ord_id:
        p["stop_ord_id"] = stop_ord_id
    return p


def zustand(*pos, offene_stops=None):
    return {"positionen": list(pos), "offene_stops": offene_stops or []}


AKTIV = {"state": "live", "accFillSz": "0"}
ERLEDIGT = {"state": "canceled", "accFillSz": "0"}


class StopFehltTest(unittest.TestCase):
    def test_fehlender_stop_wird_gesetzt(self):
        p = position()
        o = FakeOKX(bestaende={"ETH-USDC": (0.04, 0.04)},
                    stops={"alt-1": ERLEDIGT})
        z = zustand(p)
        bil = bs.pruefe(z, o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(1, bil["nachgesetzt"])
        self.assertEqual([("ETH-USDC", 0.04, 2400.0)], o.gesetzt)
        self.assertEqual("neu-1", p["stop_ord_id"])
        self.assertFalse(p["boersen_stop_fehlt"])

    def test_wirksamer_stop_bleibt_unangetastet(self):
        p = position()
        o = FakeOKX(bestaende={"ETH-USDC": (0.04, 0.04)},
                    stops={"alt-1": AKTIV})
        bil = bs.pruefe(zustand(p), o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(1, bil["ok"])
        self.assertEqual([], o.gesetzt)
        self.assertEqual("alt-1", p["stop_ord_id"])

    def test_vorschau_setzt_nichts(self):
        p = position()
        o = FakeOKX(bestaende={"ETH-USDC": (0.04, 0.04)},
                    stops={"alt-1": ERLEDIGT})
        bil = bs.pruefe(zustand(p), o, anwenden=False, journal=lambda *a: None)
        self.assertEqual(1, bil["fehlt_weiter"])
        self.assertEqual([], o.gesetzt)
        self.assertEqual("alt-1", p["stop_ord_id"])

    def test_scheitern_beim_setzen_wird_gemeldet_nicht_verschwiegen(self):
        p = position()
        o = FakeOKX(bestaende={"ETH-USDC": (0.04, 0.04)},
                    stops={"alt-1": ERLEDIGT}, setzen_fehler="OKX 51008")
        bil = bs.pruefe(zustand(p), o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(1, bil["fehlt_weiter"])
        self.assertTrue(p["boersen_stop_fehlt"])

    def test_teilbestand_bekommt_stop_ueber_den_echten_bestand(self):
        # Von Hand die Haelfte verkauft: der Stop darf nur den Rest decken,
        # sonst lehnt die Boerse ihn beim Ausloesen ab.
        p = position(usd=100.0, einstieg=2500.0)      # Buchmenge 0,04
        o = FakeOKX(bestaende={"ETH-USDC": (0.02, 0.02)},
                    stops={"alt-1": ERLEDIGT})
        bs.pruefe(zustand(p), o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(0.02, o.gesetzt[0][1])

    def test_stopzustand_unlesbar_laesst_alles_stehen(self):
        p = position()
        o = FakeOKX(bestaende={"ETH-USDC": (0.04, 0.04)},
                    stops={})                        # stop_details wirft
        bil = bs.pruefe(zustand(p), o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(1, bil["unklar"])
        self.assertEqual([], o.gesetzt)

    def test_papier_position_wird_nicht_angefasst(self):
        p = position(kauf=None)
        o = FakeOKX(bestaende={}, stops={})
        bil = bs.pruefe(zustand(p), o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(0, bil["geprueft"])
        self.assertEqual([], o.gesetzt)


class BestandWegTest(unittest.TestCase):
    def test_gefeuerter_stop_bucht_mit_echtem_kurs_aus(self):
        p = position(usd=65.96, einstieg=1619.38)
        o = FakeOKX(bestaende={"ETH-USDC": (0.0, 0.0)},
                    stops={"alt-1": {"state": "effective", "accFillSz": "0.04076"}},
                    fuellungen={"ETH-USDC": {"avgPx": "1470.89",
                                             "accFillSz": "0.040760"}})
        zeilen = []
        z = zustand(p)
        bil = bs.pruefe(z, o, anwenden=True, journal=lambda *a: zeilen.append(a))
        self.assertEqual(1, bil["ausgebucht"])
        self.assertEqual([], z["positionen"])
        self.assertEqual(1, len(zeilen))
        self.assertEqual("verkauf", zeilen[0][2])
        self.assertIn("boersen_stop", zeilen[0][8])
        self.assertEqual("alt-1" in o.storniert, False)   # Zustand nicht wirksam

    def test_ohne_belegten_ausstiegspreis_wird_nicht_gebucht(self):
        # Kein geratener Kurs: lieber eine gemeldete Unklarheit als ein
        # erfundenes Ergebnis im Journal.
        p = position()
        o = FakeOKX(bestaende={"ETH-USDC": (0.0, 0.0)},
                    stops={"alt-1": AKTIV}, fuellungen={})
        z = zustand(p)
        bil = bs.pruefe(z, o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(1, bil["unklar"])
        self.assertEqual(1, len(z["positionen"]))

    def test_bestand_unlesbar_laesst_position_stehen(self):
        p = position()
        o = FakeOKX(bestaende={}, stops={"alt-1": AKTIV})
        z = zustand(p)
        bil = bs.pruefe(z, o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(1, bil["unklar"])
        self.assertEqual(1, len(z["positionen"]))

    def test_geringer_restbestand_gilt_als_weg(self):
        # 1 % der Buchmenge und weniger ist Boersenstaub, keine Position.
        p = position(usd=100.0, einstieg=2500.0)          # Buchmenge 0,04
        o = FakeOKX(bestaende={"ETH-USDC": (0.0002, 0.0002)},
                    stops={"alt-1": AKTIV},
                    fuellungen={"ETH-USDC": {"avgPx": "2500", "accFillSz": "0.04"}})
        z = zustand(p)
        bil = bs.pruefe(z, o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(1, bil["ausgebucht"])
        self.assertEqual([], z["positionen"])


class WaisenstopTest(unittest.TestCase):
    def test_waisenstop_wird_storniert(self):
        o = FakeOKX(bestaende={}, stops={"w-1": AKTIV})
        z = zustand(offene_stops=[{"stop_ord_id": "w-1", "inst": "ZEC-USDC"}])
        bil = bs.pruefe(z, o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(1, bil["waisen"])
        self.assertEqual(["w-1"], o.storniert)
        self.assertEqual([], z["offene_stops"])

    def test_erledigter_waisenstop_faellt_ohne_storno(self):
        o = FakeOKX(bestaende={}, stops={"w-1": ERLEDIGT})
        z = zustand(offene_stops=[{"stop_ord_id": "w-1", "inst": "ZEC-USDC"}])
        bil = bs.pruefe(z, o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(0, bil["waisen"])
        self.assertEqual([], o.storniert)
        self.assertEqual([], z["offene_stops"])

    def test_stop_einer_offenen_position_gilt_nicht_als_waise(self):
        p = position(stop_ord_id="alt-1")
        o = FakeOKX(bestaende={"ETH-USDC": (0.04, 0.04)},
                    stops={"alt-1": AKTIV})
        z = zustand(p, offene_stops=[{"stop_ord_id": "alt-1",
                                      "inst": "ETH-USDC"}])
        bil = bs.pruefe(z, o, anwenden=True, journal=lambda *a: None)
        self.assertEqual(0, bil["waisen"])
        self.assertEqual([], o.storniert)
        self.assertEqual(1, len(z["offene_stops"]))


class EinbauTest(unittest.TestCase):
    """Der Zyklus muss den Abgleich WIRKLICH aufrufen - ein Werkzeug, das
    niemand startet, findet nichts (Lehre vom 21.09.2026: ein Nachweis ist
    keine Wache)."""

    def test_live_zweig_ruft_den_abgleich_vor_der_handelsentscheidung(self):
        quelle = (open(os.path.join(SPUR, "handeln.py"), encoding="utf-8")
                  .read())
        self.assertIn("boersenstops.pruefe", quelle)
        self.assertLess(quelle.index("boersenstops.pruefe"),
                        quelle.index("if modus == \"vorschau\""))
        # Nur im Live-Zweig - im Papierlauf gibt es keine Boersenposition.
        self.assertIn("if live and SCHREIBEN:", quelle)

    def test_werkzeug_ist_aus_dem_handel_ordner_dokumentiert(self):
        self.assertTrue(os.path.exists(os.path.join(SPUR, "boersenstops.py")))


if __name__ == "__main__":
    unittest.main()