"""t_39925f0a (T-177): der Ausstieg geschieht am BERUEHRTEN Kurs.

Die Regel steht in `replay.beruehrte_marke()` / `replay.kurs_der_marke()`; sie
gilt fuer beide Rechenwege (`replay.lauf_a` und `backtest_prognose.lauf`) und
fuer die Journalzeilen der Familien A, B und C (`replay.Beruehrungsjournal`).

Geprueft wird das VERHALTEN, nicht die Form:
* Kerze mit Stop UND Ziel -> konservativ der STOP (auch wenn der Schluss im
  Ziel liegt - die guenstige Reihenfolge waere genau der Schoenheitsfehler)
* Kerze mit nur dem Ziel -> GENAU der Zielkurs in Journal und Runde
* Ausstieg ohne Marke (Frist, Rueckdreh) -> Zeile unveraendert
* GEGENPROBE: ohne die Regel steht wieder der Kerzenschluss da

Der Testaufruf steht im Testkopf: aus `Agenten/Handel/tests` heraus
`python -m unittest test_replay_ausstieg` bzw. die Suite mit
`-s . -t .`.
"""
import csv
import os
import sys
import tempfile
import types
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
for p in (SPUR, HIER):
    while p in sys.path:
        sys.path.remove(p)
sys.path.insert(0, HIER)      # die Testordner muessen auffindbar bleiben
sys.path.insert(0, SPUR)      # SPUR aber ZUERST (sonst gewinnt scanner/)

import replay                                                  # noqa: E402

STD = 3600000            # eine Stunde in ms
T0 = 1609459200000       # 2021-01-01 00:00 UTC


def kerzen(verlauf):
    """[ (o,h,l,c), ... ] -> Binance-Reihen [ts, o, h, l, c, v]."""
    return [[T0 + i * STD, o, h, l, c, 1.0]
            for i, (o, h, l, c) in enumerate(verlauf)]


# 23 flache Kerzen: `kerzen_fuer()` verlangt mindest_kerzen + 20 Kerzen, sonst
# faellt das Instrument aus dem Lauf (nicht weil die Regel nicht greift).
FLACH = [(100, 100, 100, 100)] * 23


class HistorieStub:
    """Ersatz fuer `historie_binance`: feste Kerzen, kein Dateizugriff."""

    ORDNER = os.getcwd()   # muss ein existierendes Verzeichnis sein

    def __init__(self, reihen):
        self.reihen = reihen

    def lade(self, inst, takt):
        return [list(k) for k in self.reihen.get(inst, [])]


class Attrappe:
    """Eine Spur-Attrappe: ein Einstieg, ein Ausstieg an einer Marke.

    Sie verhaelt sich wie die Kerzen-Spuren: Einstieg ueber `pruefe_einstieg`,
    Ausstieg ueber `pruefe_ausstiege` mit dem SCHLUSS als Kurs - genau der
    Fehler, den die Regel in `replay` behebt. `self.journal` wird von `replay`
    durch die Journal-Huelle ersetzt (bei echten Spuren ist das genauso: das
    Modul-Attribut IST der Modul-Global).
    """

    SCHREIBEN = True

    def __init__(self, stop_pct=5.0, ziel_pct=10.0, ausstieg_grund=None):
        self.stop_pct, self.ziel_pct = stop_pct, ziel_pct
        self.ausstieg_grund = ausstieg_grund
        self.WACHEN = None
        self.ZUSTAND = None
        self.JOURNAL = None

    def zeit_quelle(self):
        return "2021-01-01T00:00:00+00:00"

    def lade_wachen(self):
        return {"instrumente": ["TEST"], "kerzen_takt": "1H",
                "kerzen_anzahl": 6, "mindest_kerzen": 3}

    def pruefe_einstieg(self, inst, k, z, w, faktor):
        if z["positionen"] or not k or len(k) < 1:
            return
        kurs = k[-1][4]
        if kurs != 100.0:                    # nur auf der flachen Strecke
            return
        p = {"inst": inst, "seite": "long", "einstieg": kurs, "nominal": 100.0,
             "stop": kurs * (1 - self.stop_pct / 100.0),
             "ziel": kurs * (1 + self.ziel_pct / 100.0),
             "stop_pct": self.stop_pct}
        z["positionen"].append(p)
        self.journal(zeit=self.zeit_quelle(), modus="papier", aktion="kauf",
                     inst=inst, seite="long", preis="%.6f" % kurs,
                     einsatz_usd="100.00", stop="%.6f" % p["stop"],
                     ziel="%.6f" % p["ziel"],
                     stop_pct="%.2f" % self.stop_pct, grund="test")

    def pruefe_ausstiege(self, z, k, w, nur=None):
        behalten = []
        for p in z.get("positionen", []):
            kurs = k[-1][4]
            grund = self.ausstieg_grund
            if grund is None:
                if kurs <= p["stop"]:
                    grund = "stop"
                elif kurs >= p["ziel"]:
                    grund = "ziel"
            if grund is None:
                behalten.append(p)
                continue
            gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"]
            self.journal(zeit=self.zeit_quelle(), modus="papier",
                         aktion="verkauf", inst=p["inst"], seite=p["seite"],
                         preis="%.6f" % kurs,
                         einsatz_usd="%.2f" % (p["nominal"] + gv),
                         stop="%.6f" % p["stop"], ziel="%.6f" % p["ziel"],
                         stop_pct="%.2f" % p["stop_pct"], grund=grund)
        z["positionen"] = behalten


class RegelTest(unittest.TestCase):
    """Die Regel selbst - ohne Replay."""

    def test_beide_marken_ergeben_den_stop(self):
        k = [0, 100, 112.0, 95.0, 111.0, 1.0]
        self.assertEqual(replay.beruehrte_marke(k, "long", 95.0, 110.0), "stop")
        self.assertEqual(replay.kurs_der_marke(k, "long", 95.0, 110.0), 95.0)

    def test_nur_das_ziel_ergibt_den_zielkurs(self):
        k = [0, 100, 112.0, 99.0, 111.0, 1.0]
        self.assertEqual(replay.beruehrte_marke(k, "long", 95.0, 110.0), "ziel")
        self.assertEqual(replay.kurs_der_marke(k, "long", 95.0, 110.0), 110.0)

    def test_keine_marke_beruehrt(self):
        k = [0, 100, 105.0, 99.0, 104.0, 1.0]
        self.assertIsNone(replay.beruehrte_marke(k, "long", 95.0, 110.0))
        self.assertIsNone(replay.kurs_der_marke(k, "long", 95.0, 110.0))

    def test_short_gespiegelt(self):
        # Stop oben, Ziel unten - dieselbe Kerze, andere Seite.
        beide = [0, 100, 106.0, 90.0, 91.0, 1.0]
        self.assertEqual(replay.beruehrte_marke(beide, "short", 105.0, 92.0),
                         "stop")
        nur_ziel = [0, 100, 104.0, 90.0, 91.0, 1.0]
        self.assertEqual(replay.beruehrte_marke(nur_ziel, "short", 105.0, 92.0),
                         "ziel")

    def test_ohne_angaben_keine_marke(self):
        k = [0, 100, 112.0, 99.0, 111.0, 1.0]
        self.assertIsNone(replay.beruehrte_marke(k, None, 95.0, 110.0))
        self.assertIsNone(replay.beruehrte_marke(k, "long", None, 110.0))
        self.assertIsNone(replay.beruehrte_marke(None, "long", 95.0, 110.0))
        self.assertIsNone(replay.beruehrte_marke([0, 1], "long", 95.0, 110.0))

    def test_schreibweise_bleibt(self):
        # Die Zahl der Nachkommastellen kommt vom alten Wert - sonst wuerde aus
        # einem Preis ein anderer String.
        self.assertEqual(replay._preis_text(95.0, "110.123456"), "95.000000")
        self.assertEqual(replay._preis_text(0.00004259, "0.00004259"),
                         "0.00004259")
        # Die Marke darf ihre Stellen nicht verlieren: AUDIO stand mit Ziel
        # 0.68171040 im Journal, die alte Zelle trug 0.681710 - die erste
        # Fassung schnitt die Marke ab und der Ausstieg lag daneben.
        self.assertEqual(replay._preis_text(0.6817104, "0.681710"), "0.6817104")

    def test_unlesbare_zelle_ist_keine_null(self):
        self.assertEqual(replay._zahl("37439.51"), 37439.51)
        self.assertIsNone(replay._zahl(""))
        self.assertIsNone(replay._zahl(None))
        self.assertIsNone(replay._zahl("keine zahl"))


class FamilieATest(unittest.TestCase):
    """Ende zu Ende durch `lauf_a` - die Zeile im Backtest-Journal zaehlt."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bt_ausstieg_")
        self.alt = (replay.spur_modul, replay.historie_binance,
                    replay.buch_ordner)
        replay.buch_ordner = lambda spur, lauf, setzen=None: self.tmp
        self.journal = os.path.join(self.tmp, "handelsjournal.csv")

    def tearDown(self):
        (replay.spur_modul, replay.historie_binance,
         replay.buch_ordner) = self.alt

    def fahre(self, letzte_kerze, attrappe=None):
        attrappe = attrappe or Attrappe()
        replay.spur_modul = lambda spur: attrappe
        replay.historie_binance = HistorieStub(
            {"TEST": kerzen(FLACH + [letzte_kerze])})
        runden, offen = replay.lauf_a("TEST", 0.1, "test")
        return runden, attrappe

    def zeilen(self):
        with open(self.journal, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_stop_und_ziel_in_einer_kerze_ergibt_den_stop(self):
        runden, _ = self.fahre((100, 112.0, 95.0, 111.0))
        aus = [z for z in self.zeilen() if z["aktion"] == "verkauf"]
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["grund"], "stop")
        self.assertEqual(aus[0]["preis"], "95.000000")
        self.assertAlmostEqual(runden[0]["ausstieg"], 95.0)
        self.assertAlmostEqual(runden[0]["brutto_pct"], -5.0)

    def test_nur_das_ziel_ergibt_genau_den_zielkurs(self):
        runden, _ = self.fahre((100, 112.0, 99.0, 111.0))
        aus = [z for z in self.zeilen() if z["aktion"] == "verkauf"]
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["grund"], "ziel")
        # NICHT der Schluss 111, sondern die Marke.
        self.assertEqual(aus[0]["preis"], "110.000000")
        self.assertAlmostEqual(runden[0]["ausstieg"], 110.0)
        self.assertAlmostEqual(runden[0]["brutto_pct"], 10.0)

    def test_gegenprobe_ohne_die_regel_steht_der_schluss_da(self):
        # Die Gegenprobe liegt IM Test: ohne `beruehrte_marke` faellt beides
        # auf den Kerzenschluss zurueck - genau die alte Rechnung. Ein Test,
        # der nur mit dem Fix gruen ist, beweist nichts ueber den Fix.
        alt = replay.beruehrte_marke
        replay.beruehrte_marke = lambda *a, **k: None
        try:
            runden, _ = self.fahre((100, 112.0, 99.0, 111.0))
        finally:
            replay.beruehrte_marke = alt
        aus = [z for z in self.zeilen() if z["aktion"] == "verkauf"]
        self.assertEqual(aus[0]["preis"], "111.000000")
        self.assertAlmostEqual(runden[0]["ausstieg"], 111.0)

    def test_ausstieg_ohne_marke_bleibt_unveraendert(self):
        # Frist/Rueckdreh haben keinen Markenpreis - sie gehen durch wie bisher.
        # Die Frist feuert auf der ersten flachen Kerze nach dem Einstieg, also
        # steht dort der Schluss dieser Kerze (100) - NICHT eine Marke.
        runden, _ = self.fahre((100, 112.0, 99.0, 111.0),
                               Attrappe(ausstieg_grund="frist"))
        aus = [z for z in self.zeilen() if z["aktion"] == "verkauf"]
        self.assertEqual(aus[0]["grund"], "frist")
        self.assertEqual(aus[0]["preis"], "100.000000")
        self.assertAlmostEqual(runden[0]["ausstieg"], 100.0)
        self.assertEqual(replay.auf_der_marke(self.journal)["ausstiege"], 0)

    def test_die_gegenprobe_zaehlt_die_zeilen(self):
        self.fahre((100, 112.0, 99.0, 111.0))
        self.assertEqual(replay.auf_der_marke(self.journal),
                         {"ausstiege_an_marke": 1, "ausstiege": 1})


class HuelleTest(unittest.TestCase):
    """Die Journal-Huelle gegen das ECHTE Journal von `spur_buch`."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bt_huelle_")
        self.pfad = os.path.join(self.tmp, "handelsjournal.csv")
        import spur_buch
        self.spur_buch = spur_buch

    def schreibe(self, huelle, **f):
        huelle(self.pfad, **f)

    def test_markenzeile_bekommt_marke_und_erloes(self):
        kerzen_jetzt = {"TEST": [0, 100, 112.0, 95.0, 111.0, 1.0]}
        h = replay.Beruehrungsjournal(kerzen_jetzt, self.spur_buch.journal)
        self.schreibe(h, zeit="2021-01-01T00:00:00+00:00", modus="papier",
                      aktion="kauf", inst="TEST", seite="long",
                      preis="100.000000", einsatz_usd="100.00",
                      stop="95.000000", ziel="110.000000", grund="test")
        self.schreibe(h, zeit="2021-01-02T00:00:00+00:00", modus="papier",
                      aktion="verkauf", inst="TEST", seite="long",
                      preis="111.000000", einsatz_usd="111.00",
                      stop="95.000000", ziel="110.000000", grund="ziel")
        with open(self.pfad, newline="", encoding="utf-8") as f:
            zeilen = list(csv.DictReader(f))
        self.assertEqual(len(zeilen), 2)
        # Der Einstieg bleibt, wie die Spur ihn geschrieben hat.
        self.assertEqual(zeilen[0]["preis"], "100.000000")
        self.assertEqual(zeilen[0]["grund"], "test")
        # Der Ausstieg sitzt auf der Marke, der Erloes folgt der Marke.
        self.assertEqual(zeilen[1]["preis"], "95.000000")
        self.assertEqual(zeilen[1]["grund"], "stop")
        self.assertEqual(zeilen[1]["einsatz_usd"], "95.00")
        self.assertEqual(h.berichtigt, 1)
        self.assertEqual(h.ohne_marke, 0)

    def test_zwei_markenzeilen_je_instrument_bleiben_getrennt(self):
        """Zwei Ausstiege desselben Instruments in EINEM Schritt.

        `letzte_ausstiege` (ein Einzelwert) gab beiden Runden den Kurs der
        zweiten Zeile - die Gegenprobe fand genau das (10,0000000000 gegen
        9,9955891139). Die Warteschlange gibt sie in der Reihenfolge der
        Zeilen heraus, `schritt_anfang()` leert sie.
        """
        kerzen_jetzt = {"TEST": [0, 100, 112.0, 99.0, 111.0, 1.0]}
        h = replay.Beruehrungsjournal(kerzen_jetzt, self.spur_buch.journal)
        # Erste Zeile: nur das Ziel ist beruehrt (Tief 99 ueber dem Stop 95).
        self.schreibe(h, zeit="2021-01-02T00:00:00+00:00", modus="papier",
                      aktion="verkauf", inst="TEST", seite="long",
                      preis="111.000000", einsatz_usd="100.00",
                      stop="95.000000", ziel="110.000000", grund="ziel")
        # Zweite Zeile im SELBEN Schritt: nur der Stop ist beruehrt.
        kerzen_jetzt["TEST"] = [0, 100, 101.0, 90.0, 91.0, 1.0]
        self.schreibe(h, zeit="2021-01-02T00:00:00+00:00", modus="papier",
                      aktion="verkauf", inst="TEST", seite="long",
                      preis="91.000000", einsatz_usd="100.00",
                      stop="95.000000", ziel="110.000000", grund="stop")
        self.assertEqual(h.nimm_marke("TEST"), 110.0)   # in der Reihenfolge
        self.assertEqual(h.nimm_marke("TEST"), 95.0)    # der Zeilen
        self.assertIsNone(h.nimm_marke("TEST"))         # nichts mehr
        self.assertIsNone(h.nimm_marke("ANDERES"))
        h.schritt_anfang()
        self.assertIsNone(h.nimm_marke("TEST"))

    def test_zeile_ohne_kerze_wird_gezaehlt_nicht_still_gelassen(self):
        h = replay.Beruehrungsjournal({}, self.spur_buch.journal)
        self.schreibe(h, zeit="2021-01-01T00:00:00+00:00", modus="papier",
                      aktion="verkauf", inst="FEHLT", seite="long",
                      preis="111.000000", einsatz_usd="111.00",
                      stop="95.000000", ziel="110.000000", grund="ziel")
        with open(self.pfad, newline="", encoding="utf-8") as f:
            zeilen = list(csv.DictReader(f))
        self.assertEqual(zeilen[0]["preis"], "111.000000")
        self.assertEqual(zeilen[0]["grund"], "ziel")
        self.assertEqual(h.berichtigt, 0)
        self.assertEqual(h.ohne_marke, 1)

    def test_kerze_auf_abruf(self):
        # Familie C holt die Kerze erst, wenn eine Markenzeile auftaucht.
        geholt = []

        def kerze_fuer(inst):
            geholt.append(inst)
            return [0, 100, 112.0, 95.0, 111.0, 1.0]

        h = replay.Beruehrungsjournal({}, self.spur_buch.journal,
                                      kerze_fuer=kerze_fuer)
        self.schreibe(h, zeit="2021-01-01T00:00:00+00:00", modus="papier",
                      aktion="kauf", inst="TEST", seite="long",
                      preis="100.000000", einsatz_usd="100.00",
                      stop="95.000000", ziel="110.000000", grund="test")
        self.assertEqual(geholt, [])           # Einstieg fragt nichts ab
        self.schreibe(h, zeit="2021-01-02T00:00:00+00:00", modus="papier",
                      aktion="verkauf", inst="TEST", seite="long",
                      preis="111.000000", einsatz_usd="111.00",
                      stop="95.000000", ziel="110.000000", grund="ziel")
        self.assertEqual(geholt, ["TEST"])
        with open(self.pfad, newline="", encoding="utf-8") as f:
            zeilen = list(csv.DictReader(f))
        self.assertEqual(zeilen[1]["preis"], "95.000000")
        self.assertEqual(zeilen[1]["einsatz_usd"], "95.00")

    def test_short_erloes_laeuft_andersherum(self):
        # Short: Stop liegt OBEN. Der Erloes MUSS fallen, wenn der Stop greift.
        kerzen_jetzt = {"TEST": [0, 100, 106.0, 90.0, 91.0, 1.0]}
        h = replay.Beruehrungsjournal(kerzen_jetzt, self.spur_buch.journal)
        self.schreibe(h, zeit="2021-01-01T00:00:00+00:00", modus="papier",
                      aktion="kauf", inst="TEST", seite="short",
                      preis="100.000000", einsatz_usd="100.00",
                      stop="105.000000", ziel="90.000000", grund="test")
        self.schreibe(h, zeit="2021-01-02T00:00:00+00:00", modus="papier",
                      aktion="verkauf", inst="TEST", seite="short",
                      preis="90.500000", einsatz_usd="109.50",
                      stop="105.000000", ziel="90.000000", grund="ziel")
        with open(self.pfad, newline="", encoding="utf-8") as f:
            zeilen = list(csv.DictReader(f))
        self.assertEqual(zeilen[1]["preis"], "105.000000")
        self.assertEqual(zeilen[1]["grund"], "stop")
        self.assertEqual(zeilen[1]["einsatz_usd"], "95.00")


class AufDerMarkeTest(unittest.TestCase):
    """Die Gegenprobe aus dem Journal - auch fuer fremde Zeilenformen."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bt_marke_")
        self.pfad = os.path.join(self.tmp, "handelsjournal.csv")

    def schreibe(self, zeilen):
        with open(self.pfad, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["aktion", "preis", "stop", "ziel",
                                              "grund"])
            w.writeheader()
            for z in zeilen:
                w.writerow(z)

    def test_zaehlt_nur_markenzeilen(self):
        self.schreibe([
            {"aktion": "kauf", "preis": "100", "stop": "95", "ziel": "110",
             "grund": "test"},
            {"aktion": "verkauf", "preis": "95.000000", "stop": "95.000000",
             "ziel": "110.000000", "grund": "stop"},
            {"aktion": "verkauf", "preis": "111.000000", "stop": "95.000000",
             "ziel": "110.000000", "grund": "ziel"},
            {"aktion": "verkauf", "preis": "104.000000", "stop": "95.000000",
             "ziel": "110.000000", "grund": "frist"},
        ])
        self.assertEqual(replay.auf_der_marke(self.pfad),
                         {"ausstiege_an_marke": 1, "ausstiege": 2})

    def test_fehlende_datei_ist_keine_null_runde(self):
        self.assertEqual(replay.auf_der_marke(os.path.join(self.tmp, "nix.csv")),
                         {"ausstiege_an_marke": 0, "ausstiege": 0})


class DochtZaehlerTest(unittest.TestCase):
    """T-202: die Messung der Docht-Beruehrung ohne Schluss jenseits der Marke.

    Ein Ausstieg allein wegen eines Dochts ist NICHT abgebildet (der Ausloeser
    bleibt der Kerzenschluss, wie live). Diese Tests pruefen nur den ZAEHLER,
    der die Messung fuers Bericht liefert - keine Aenderung des Ausstiegs.
    """

    def test_docht_streift_stop_und_schliesst_darueber(self):
        # Long: Stop 95, Tief 94.9 (streift), Schluss 96 (darueber) -> True.
        k = [0, 100, 100.0, 94.9, 96.0, 1.0]
        self.assertTrue(
            replay.docht_beruehrung_ohne_schluss(k, "long", 95.0, 110.0))

    def test_docht_streift_ziel_und_schliesst_darunter(self):
        # Long: Ziel 110, Hoch 110.1 (streift), Schluss 109 (darunter) -> True.
        k = [0, 100, 110.1, 99.0, 109.0, 1.0]
        self.assertTrue(
            replay.docht_beruehrung_ohne_schluss(k, "long", 95.0, 110.0))

    def test_schluss_jenseits_der_marke_ist_kein_docht_fall(self):
        # Long: Schluss 111 liegt JENSEITS des Ziels 110 -> kein Docht-Fall.
        k = [0, 100, 112.0, 99.0, 111.0, 1.0]
        self.assertFalse(
            replay.docht_beruehrung_ohne_schluss(k, "long", 95.0, 110.0))

    def test_keine_beruehrung_ist_false(self):
        k = [0, 100, 105.0, 99.0, 104.0, 1.0]
        self.assertFalse(
            replay.docht_beruehrung_ohne_schluss(k, "long", 95.0, 110.0))

    def test_short_gespiegelt(self):
        # Short: Stop 105, Hoch 105.1 (streift), Schluss 104 (darunter) -> True.
        k = [0, 100, 105.1, 99.0, 104.0, 1.0]
        self.assertTrue(
            replay.docht_beruehrung_ohne_schluss(k, "short", 105.0, 92.0))
        # Short: Schluss 106 liegt jenseits des Stops -> kein Docht-Fall.
        k2 = [0, 100, 106.0, 99.0, 106.0, 1.0]
        self.assertFalse(
            replay.docht_beruehrung_ohne_schluss(k2, "short", 105.0, 92.0))

    def test_ohne_angaben_kein_docht_fall(self):
        k = [0, 100, 112.0, 94.9, 96.0, 1.0]
        self.assertFalse(replay.docht_beruehrung_ohne_schluss(k, None, 95.0, 110.0))
        self.assertFalse(replay.docht_beruehrung_ohne_schluss(k, "long", None, 110.0))
        self.assertFalse(replay.docht_beruehrung_ohne_schluss(None, "long", 95.0, 110.0))
        self.assertFalse(replay.docht_beruehrung_ohne_schluss([0, 1], "long", 95.0, 110.0))


class DochtAusstiegTest(unittest.TestCase):
    """T-202: der Ausstieg wird auch ausgeloest, wenn die Marke NUR am Docht
    beruehrt wurde (Hoch/Tief kreuzt die Marke, der Schluss liegt zurueck).

    Die Spur prueft nur den Schluss (`pruefe_ausstiege`); der Replay schliesst
    die Position NACH `pruefe_ausstiege` selbst, wenn die Kerze eine Marke nur
    am Docht beruehrt hat. Der Ausstieg geschieht am KURS DER MARKE.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bt_docht_")
        self.alt = (replay.spur_modul, replay.historie_binance,
                    replay.buch_ordner)
        replay.buch_ordner = lambda spur, lauf, setzen=None: self.tmp
        self.journal = os.path.join(self.tmp, "handelsjournal.csv")

    def tearDown(self):
        (replay.spur_modul, replay.historie_binance,
         replay.buch_ordner) = self.alt

    def fahre(self, letzte_kerze, attrappe=None):
        attrappe = attrappe or Attrappe()
        replay.spur_modul = lambda spur: attrappe
        replay.historie_binance = HistorieStub(
            {"TEST": kerzen(FLACH + [letzte_kerze])})
        runden, offen = replay.lauf_a("TEST", 0.1, "test")
        return runden, attrappe

    def zeilen(self):
        with open(self.journal, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_docht_streift_stop_und_schliesst_darueber(self):
        # Long: Stop 95, Tief 94.9 (streift), Schluss 96 (darueber). Die Spur
        # schliesst NICHT (Schluss 96 > Stop 95), der Docht-Ausstieg schon.
        runden, _ = self.fahre((100, 100.0, 94.9, 96.0))
        aus = [z for z in self.zeilen() if z["aktion"] == "verkauf"]
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["grund"], "stop")
        self.assertEqual(aus[0]["preis"], "95.000000")
        self.assertAlmostEqual(runden[0]["ausstieg"], 95.0)
        self.assertAlmostEqual(runden[0]["brutto_pct"], -5.0)

    def test_docht_streift_ziel_und_schliesst_darunter(self):
        # Long: Ziel 110, Hoch 110.1 (streift), Schluss 109 (darunter).
        runden, _ = self.fahre((100, 110.1, 99.0, 109.0))
        aus = [z for z in self.zeilen() if z["aktion"] == "verkauf"]
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["grund"], "ziel")
        self.assertEqual(aus[0]["preis"], "110.000000")
        self.assertAlmostEqual(runden[0]["ausstieg"], 110.0)
        self.assertAlmostEqual(runden[0]["brutto_pct"], 10.0)

    def test_schluss_jenseits_der_marke_kein_doppelter_ausstieg(self):
        # Schluss 111 liegt JENSEITS des Ziels 110: pruefe_ausstiege schliesst
        # schon, der Docht-Ausstieg darf NICHT noch einmal schliessen.
        runden, _ = self.fahre((100, 112.0, 99.0, 111.0))
        aus = [z for z in self.zeilen() if z["aktion"] == "verkauf"]
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["grund"], "ziel")
        self.assertEqual(aus[0]["preis"], "110.000000")

    def test_keine_beruehrung_kein_ausstieg(self):
        runden, _ = self.fahre((100, 105.0, 99.0, 104.0))
        aus = [z for z in self.zeilen() if z["aktion"] == "verkauf"]
        self.assertEqual(len(aus), 0)
        self.assertEqual(runden, [])

    def test_gegenprobe_ohne_docht_regel_bleibt_offen(self):
        # Gegenprobe: ohne `docht_ausstiege_anwenden` bleibt die Position
        # offen - der Docht-Ausstieg ist die Ursache des Ausstiegs.
        alt = replay.docht_ausstiege_anwenden
        replay.docht_ausstiege_anwenden = lambda *a, **k: 0
        try:
            runden, _ = self.fahre((100, 100.0, 94.9, 96.0))
        finally:
            replay.docht_ausstiege_anwenden = alt
        aus = [z for z in self.zeilen() if z["aktion"] == "verkauf"]
        self.assertEqual(len(aus), 0)
        self.assertEqual(runden, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
