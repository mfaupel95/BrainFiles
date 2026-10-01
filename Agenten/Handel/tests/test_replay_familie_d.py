"""Familie D: Mehrzeitrahmen (mosaic) und eigene Rechnung (gitter) - T-294/T-295.

Zwei Dinge werden hier geprueft, und das zweite ist das wichtigere:

  1. Der Adapter faehrt die Spur (Argumentordnung, Reihen, Journal).
  2. Er sieht NICHTS aus der Zukunft. Die groebere Kerze zaehlt erst, wenn sie
     abgeschlossen ist - waere die laufende 4H-Kerze dabei, saehe der Backtest
     den Rest der Stunde, den die Spur live noch nicht kennt. Das entwertet
     jede Kennzahl darauf, und man sieht es keiner Zahl an.

Der Test dafuer faehrt eine ATTRAPPE als Spur (eigener Ordner im Temp), die
jede empfangene Reihe mitschreibt. So wird die Regel geprueft und nicht die
Strategie von mosaic.

`replay.verzeichnis` zeigt in JEDEM Test in einen Temp-Ordner; die
synthetischen Tests biegen zusaetzlich `historie_binance.ORDNER` um. In keinen
Test wird ein echter Zielpfad geschrieben.
"""

import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import historie_binance                                            # noqa: E402
import replay                                                      # noqa: E402

MS = replay.MS_JE_TAKT

ATTRAPPE = '''"""Attrappe: schreibt mit, welche Reihen sie je Schritt bekommt."""
import json
import os

HIER = os.path.dirname(os.path.abspath(__file__))
SCHREIBEN = True
gesehen = []


def lade_wachen():
    with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
        return json.load(f)


def journal(**f):
    return None


def pruefe_ausstiege(z, k5, w, nur=None):
    raus = []
    for p in z.get("positionen", []):
        if p.get("inst") != nur:
            raus.append(p)
            continue
        if k5 and k5[-1][4] >= p["ziel"]:
            continue
        raus.append(p)
    z["positionen"] = raus


def pruefe_einstieg(inst, k4, k30, k5, z, w, faktor):
    gesehen.append({
        "inst": inst, "k4": k4[-1][0], "k30": k30[-1][0], "k5": k5[-1][0],
        "n4": len(k4), "n30": len(k30), "n5": len(k5), "faktor": faktor,
    })
    if any(p["inst"] == inst for p in z["positionen"]):
        return
    einstieg = k5[-1][4]
    z["positionen"].append({
        "inst": inst, "seite": "long", "einstieg": einstieg,
        "stop": einstieg * 0.9, "ziel": einstieg * 1.05,
        "stop_pct": 10.0, "nominal": 100.0, "pos_id": "p%d" % len(z["positionen"]),
    })
'''

WACHEN = {"instrumente": ["BTC-USDC"], "mindest_kerzen": 300,
          "journal_zweitziel": "Q:\\Handel_Journal\\nicht_anfassen"}

# Die Attrappe traegt dieselbe Fahrweise wie mosaic (drei Reihen).
SPEC = {"basis": "5M",
        "reihen": (("k4", "4H"), ("k30", "30M"), ("k5", "5M")),
        "einstieg": ("k4", "k30", "k5"),
        "ausstieg": "k5"}


def reihe_5m(anzahl, start=100.0, schritt=0.05, ts0=1_700_000_000_000):
    """Eine gleichmaessig steigende 5m-Reihe - [ts, o, h, t, c, v]."""
    aus, kurs = [], start
    for i in range(anzahl):
        ts = ts0 + i * MS["5M"]
        aus.append([ts, kurs, kurs + schritt, kurs - schritt, kurs + schritt,
                    10.0])
        kurs += schritt
    return aus


class FamilieDTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_verz = replay.verzeichnis
        self.alt_hier = replay.HIER
        self.alt_ordner = historie_binance.ORDNER
        replay.verzeichnis = lambda: os.path.join(self.tmp.name, "backtest")
        historie_binance.ORDNER = os.path.join(self.tmp.name, "historie")
        os.makedirs(historie_binance.ORDNER, exist_ok=True)

    def tearDown(self):
        replay.verzeichnis = self.alt_verz
        replay.HIER = self.alt_hier
        historie_binance.ORDNER = self.alt_ordner
        self.tmp.cleanup()

    def _attrappe_bauen(self, spur="attrappe"):
        ordner = os.path.join(self.tmp.name, spur)
        os.makedirs(ordner, exist_ok=True)
        with open(os.path.join(ordner, "handeln.py"), "w", encoding="utf-8") as f:
            f.write(ATTRAPPE)
        with open(os.path.join(ordner, "wachen.json"), "w", encoding="utf-8") as f:
            json.dump(WACHEN, f)
        replay.HIER = self.tmp.name
        return ordner

    def _historie_schreiben(self, anzahl=4000):
        with open(os.path.join(historie_binance.ORDNER, "BTCUSDT_5M.json"),
                  "w", encoding="utf-8") as f:
            json.dump(reihe_5m(anzahl), f)


class VerdichtenTest(unittest.TestCase):
    def test_sechs_5m_kerzen_werden_eine_30m_kerze(self):
        basis = [[i * MS["5M"], 10.0 + i, 20.0 + i, 1.0 + i, 15.0 + i, 2.0]
                 for i in range(6)]
        d = replay.verdichten(basis, "30M")
        self.assertEqual(len(d), 1)
        k = d[0]
        self.assertEqual(k[0], 0)              # Start der ersten Halbstunde
        self.assertEqual(k[1], 10.0)           # open der ersten
        self.assertEqual(k[2], 25.0)           # hoechstes Hoch
        self.assertEqual(k[3], 1.0)            # tiefstes Tief
        self.assertEqual(k[4], 20.0)           # Schluss der letzten
        self.assertEqual(k[5], 12.0)           # Volumen summiert

    def test_achtundvierzig_5m_kerzen_werden_eine_4h_kerze(self):
        # 96 Kerzen = zwei volle 4H-Fenster (48 x 5m = 4 h).
        basis = [[i * MS["5M"], 1.0, 1.0, 1.0, 1.0, 1.0] for i in range(96)]
        self.assertEqual(len(replay.verdichten(basis[:48], "4H")), 1)
        self.assertEqual(len(replay.verdichten(basis, "4H")), 2)

    def test_bedarf_mehrzeitrahmen_rechnet_den_groessten_faktor(self):
        w = {"mindest_kerzen": 300}
        # 4H aus 5m = Faktor 48; 300 + Puffer, mal 48.
        self.assertEqual(replay.bedarf_mehrzeitrahmen(
            replay.MEHRZEITRAHMEN["mosaic"], w),
            (300 + replay.KERZEN_PUFFER) * 48)


class KeineZukunftTest(FamilieDTest):
    """Die groebere Kerze zaehlt erst, wenn sie ABGESCHLOSSEN ist."""

    def test_jede_gelieferte_reihe_endet_in_der_vergangenheit(self):
        self._attrappe_bauen()
        # 300 4H-Kerzen aus 5m = 14.400 Kerzen Vorlauf; 20.000 lassen rund
        # 5.600 Schritte uebrig.
        self._historie_schreiben(20000)
        spur = "attrappe"
        replay.MEHRZEITRAHMEN[spur] = SPEC
        # Die Spur wird EINMAL geladen: `spur_modul` baut bei jedem Aufruf ein
        # NEUES Modul, und `gesehen` der zweiten Instanz waere leer.
        modul = replay.spur_modul(spur)
        alt_fn = replay.spur_modul
        replay.spur_modul = lambda s: modul if s == spur else alt_fn(s)
        try:
            runden, _offen = replay.lauf_mehrzeitrahmen(spur, 0.1, "zukunft",
                                                        fenster=300)
        finally:
            replay.spur_modul = alt_fn
            del replay.MEHRZEITRAHMEN[spur]
        self.assertGreater(len(modul.gesehen), 0)
        for g in modul.gesehen:
            # k5 endet auf der Kerze des Schritts; die groeberen Reihen duerfen
            # nur Kerzen enthalten, die zu diesem Zeitpunkt FERTIG waren.
            self.assertEqual(g["n5"], 300)
            self.assertEqual(g["n30"], 300)
            self.assertEqual(g["n4"], 300)
            self.assertLessEqual(g["k30"] + MS["30M"], g["k5"])
            self.assertLessEqual(g["k4"] + MS["4H"], g["k5"])
        self.assertGreater(len(runden), 0)

    def test_ohne_historie_wird_der_grund_genannt(self):
        self._attrappe_bauen()
        replay.MEHRZEITRAHMEN["attrappe"] = SPEC
        try:
            with self.assertRaises(replay.HistorieFehlt) as e:
                replay.lauf_mehrzeitrahmen("attrappe", 0.1, "leer")
            self.assertIn("5M-Basis", str(e.exception))
        finally:
            del replay.MEHRZEITRAHMEN["attrappe"]


class EchteHistorieTest(unittest.TestCase):
    """Die ECHTE Historie bleibt stehen - nur der Ausgang zeigt nach innen.

    `FamilieDTest` biegt auch `historie_binance.ORDNER` um (synthetische
    Reihen). Wer die echten Reihen braucht, erbt von HIER.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_verz = replay.verzeichnis
        replay.verzeichnis = lambda: self.tmp.name

    def tearDown(self):
        replay.verzeichnis = self.alt_verz
        self.tmp.cleanup()


class DeterminismusTest(EchteHistorieTest):
    """Zwei Laeufe ueber dieselben Kerzen ergeben dasselbe Journal."""

    def _vergleiche(self, spur, lauf_a, lauf_b):
        p = os.path.join(replay.buch_ordner(spur, lauf_a), "handelsjournal.csv")
        q = os.path.join(replay.buch_ordner(spur, lauf_b), "handelsjournal.csv")
        with open(p, "rb") as f:
            a = f.read()
        with open(q, "rb") as f:
            b = f.read()
        self.assertTrue(a, "leeres Journal - der Lauf hat nichts gebucht")
        self.assertEqual(a, b, "das Journal traegt noch einen Zufallsanteil")

    def test_mosaic_ist_zweimal_gleich(self):
        if not historie_binance.lade("BTC-USDC", "5M"):
            self.skipTest("keine 5M-Historie fuer BTC-USDC")
        replay.lauf_mehrzeitrahmen("mosaic", 0.6, "det_a")
        replay.lauf_mehrzeitrahmen("mosaic", 0.6, "det_b")
        self._vergleiche("mosaic", "det_a", "det_b")

    def test_gitter_ist_zweimal_gleich(self):
        if not historie_binance.lade("BTC-USDT", "1H"):
            self.skipTest("keine 1H-Historie fuer BTC-USDT")
        replay.lauf_eigene_rechnung("gitter", 0.1, "det_a", max_kerzen=4000)
        replay.lauf_eigene_rechnung("gitter", 0.1, "det_b", max_kerzen=4000)
        self._vergleiche("gitter", "det_a", "det_b")


class GitterTest(EchteHistorieTest):
    def test_lauf_liefert_die_zahlen_des_gitters(self):
        if not historie_binance.lade("BTC-USDT", "1H"):
            self.skipTest("keine 1H-Historie fuer BTC-USDT")
        k = replay.lauf_eigene_rechnung("gitter", 0.1, "lauf",
                                        max_kerzen=4000)
        self.assertGreater(k["kerzen"], 0)
        self.assertEqual(k["zyklen"], k["runden"])
        self.assertEqual(k["kaeufe"], k["verkaeufe"] + k["offen"])
        # Buchwert = Einsatz + Ergebnis, per Definition.
        self.assertAlmostEqual(k["buchwert"], k["ergebnis"] + 1000.0, places=6)
        self.assertIn("halten_pct", k)
        self.assertEqual(k["gebuehr_pct"], 0.1)

    def test_zu_kleines_fenster_wird_benannt(self):
        with self.assertRaises(replay.HistorieFehlt):
            replay.lauf_eigene_rechnung("gitter", 0.1, "leer", max_kerzen=10)


class AusstiegAmKursDerMarkeTest(unittest.TestCase):
    def test_ziel_gewinnt_gegen_den_kerzenschluss(self):
        offen = {1: {"seite": "long", "einstieg": 100.0, "nominal": 100.0,
                     "stop_pct": 5.0, "stop": 95.0, "ziel": 110.0, "ts": 0}}
        kerze = [3_600_000, 100.0, 112.0, 99.0, 105.0]
        runden = []
        replay._ausstiege_buchen(offen, runden, {1: None},
                                 {"positionen": []}, kerze, 0.1, "X")
        self.assertEqual(len(runden), 1)
        self.assertEqual(runden[0]["ausstieg"], 110.0)
        self.assertEqual(offen, {})

    def test_offene_position_wird_nicht_gebucht(self):
        # Dieselbe Position steht noch im Buch - `nachher` traegt ihre id.
        pos = {"inst": "X"}
        offen = {id(pos): {"seite": "long", "einstieg": 100.0,
                           "nominal": 100.0, "stop_pct": 5.0, "stop": 95.0,
                           "ziel": 110.0, "ts": 0}}
        runden = []
        replay._ausstiege_buchen(offen, runden, {id(pos): pos},
                                 {"positionen": [pos]}, [0, 1, 2, 3, 4],
                                 0.1, "X")
        self.assertEqual(runden, [])
        self.assertEqual(len(offen), 1)


class KennungTest(unittest.TestCase):
    def test_kennung_fest_macht_kennungen_reproduzierbar(self):
        import pos_kennung
        zurueck = replay.kennung_fest()
        try:
            a = pos_kennung.neu("2026-09-30T15:30:12+00:00")
            b = pos_kennung.neu("2026-09-30T15:30:12+00:00")
        finally:
            zurueck()
        self.assertEqual(a, "20260930T153012-000001")
        self.assertEqual(b, "20260930T153012-000002")
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()