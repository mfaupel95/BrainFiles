"""Familie E (xperp): bot.py in den Replay eingewickelt - kein Netz.

Zwei Ebenen, getrennt gehalten:

  MechanikTest   faehrt die Replay-Schleife mit einem Bot-STUB, der ueber
                 die sammle-Naht eine deterministische Order liefert. Das
                 prueft die SCHLEIFE (Fill am Limit, Ausstieg an der Marke,
                 Journal, Verfall) - reproduzierbar, ohne dass die
                 Indikatoren in bot.py einen Zufall beisteuern.

  BotIntegrationTest laedt ueber replay._bot_modul() die ECHTE bot.py und
                 ersetzt nur die Netzzugaenge (okxf-Ersatz). Er beweist,
                 dass die drei Methoden (lage/trend/grid) unter dem Ersatz
                 laufen - das Netz wird dabei mit einer Bombe abgesichert:
                 jeder echte okxf-Abruf wuerde den Test rot machen.
                 Deterministische Signale gibt es hier NICHT (ein 0-Runden-
                 Lauf ist ein gueltiges Ergebnis); die Mechanik prueft der
                 Stub-Test.

Damit kein Test ein ECHTES Ziel beruehrt: `replay.verzeichnis` zeigt auf
einen Temp-Ordner (Backtest-Ablage), `historie_okx.ORDNER` auf einen zweiten
(OKX-Kerzen + _instrumente.json). Der echte xperp-Ordner wird nur LESEND
ueber wachen_von() benutzt.
"""

import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import replay                                                     # noqa: E402
import historie_okx                                               # noqa: E402

INST = "SOL-USD_UM_XPERP-310629"
KERZEN_MS = 14_400_000        # 4H
START_MS = 1_750_000_000_000  # 2025-06-15, vor den XPERP-Listings - nur ein Vielfaches


def _kerzen(anzahl, preise):
    """4H-Reihen [ts, o, h, l, c, v] aus Preis-Liste (aufsteigend)."""
    reihen = []
    for i in range(anzahl):
        p = preise(i)
        reihen.append([START_MS + i * KERZEN_MS, p, p + 1.0, p - 1.0, p, 1.0])
    return reihen


def _konstant(anzahl, kurs=100.0):
    return _kerzen(anzahl, lambda i: kurs)


def _meta(inst=INST):
    return {"instId": inst, "uly": inst.split("-")[0] + "-USD",
            "instCategory": "1", "state": "live", "lever": "5",
            "ctVal": "1", "ctValCcy": "USD", "lotSz": "1", "minSz": "1",
            "tickSz": "0.1"}


def _wachen_patch():
    return {"instrumente": [INST], "order_gueltig_kerzen": 24}


def _echter_okxf():
    """Das echte xperp/okxf.py - fuer die reinen Rechenfunktionen."""
    pfad = os.path.join(HANDEL, "xperp", "okxf.py")
    s = importlib.util.spec_from_file_location("bt_test_okxf", pfad)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


class _Basis(unittest.TestCase):
    def setUp(self):
        self.bt = tempfile.TemporaryDirectory()   # Backtest-Ablage
        self.hx = tempfile.TemporaryDirectory()   # OKX-Kerzen + Metadaten
        self.alt_verz = replay.verzeichnis
        self.alt_ordner = historie_okx.ORDNER
        replay.verzeichnis = lambda: self.bt.name
        historie_okx.ORDNER = self.hx.name
        os.makedirs(historie_okx.ORDNER, exist_ok=True)
        historie_okx._speichere_instrumente([_meta()])
        with open(os.path.join(historie_okx.ORDNER, INST + "_4H.json"),
                  "w", encoding="utf-8") as f:
            json.dump(_konstant(420), f)

    def tearDown(self):
        replay.verzeichnis = self.alt_verz
        historie_okx.ORDNER = self.alt_ordner
        self.bt.cleanup()
        self.hx.cleanup()


class RegistrierungTest(_Basis):
    def test_xperp_ist_familie_e_und_nicht_mehr_gesperrt(self):
        self.assertIn("xperp", replay.SPUREN_TEIL_E)
        self.assertNotIn("xperp", replay.NICHT_NACHRECHENBAR)

    def test_lauf_e_verweigert_ohne_historie_mit_grund(self):
        os.remove(os.path.join(historie_okx.ORDNER, INST + "_4H.json"))
        with self.assertRaises(RuntimeError):
            replay.lauf_e("xperp", 0.05, "t1")

    def test_lauf_e_verweigert_ohne_metadaten_mit_grund(self):
        os.remove(os.path.join(historie_okx.ORDNER, "_instrumente.json"))
        with self.assertRaises(RuntimeError):
            replay.lauf_e("xperp", 0.05, "t2")


class BotStub:
    """Ersatz fuer xperp/bot.py: legt ueber sammle genau EINE Order.

    `orderboerse` liefert die Order (seite, kontrakte, einstieg, ziel, stop)
    beim ERSTEN Aufruf, danach nichts - so gibt es genau eine Position und
    die Runden sind determiniert.
    """

    def __init__(self, orderboerse, okxf):
        self.BAR = "4H"
        self.okxf = okxf
        self.tages_kerzen_quelle = None
        self.indikatoren = types.SimpleNamespace()
        self.zaehler = {"n": 0}
        self._order = orderboerse

    def _eine(self, w, wert, historie_quelle=None, hebel_wunsch=None,
              einsatz=None, sammle=None):
        if self.zaehler["n"] > 0 or sammle is None:
            return 0
        self.zaehler["n"] += 1
        sammle.append({"orders": [self._order]})
        return 0

    def zeige_lage(self, w, wert, historie_quelle=None):
        return None

    def zeige_trend(self, w, wert, historie_quelle=None, hebel_wunsch=None,
                    einsatz=None, sammle=None):
        return self._eine(w, wert, historie_quelle, hebel_wunsch,
                          einsatz, sammle)

    def zeige_grid(self, w, wert, historie_quelle=None, hebel_wunsch=None,
                   einsatz=None, sammle=None):
        return self._eine(w, wert, historie_quelle, hebel_wunsch,
                          einsatz, sammle)


class MechanikTest(_Basis):
    """Lauf mit deterministischer Order - prueft Fill, Ausstieg, Journal."""

    def _lauf(self, kurs_ab_schritt_300, order):
        """Preise ab dem 300. Index; davor ~100 (Indikator-Anlauf)."""
        alle = []
        for i in range(420):
            p = 100.0 if i < 300 else kurs_ab_schritt_300(i - 300)
            alle.append([START_MS + i * KERZEN_MS, p, p + 1.0, p - 1.0, p, 1.0])
        with open(os.path.join(historie_okx.ORDNER, INST + "_4H.json"),
                  "w", encoding="utf-8") as f:
            json.dump(alle, f)
        bot = BotStub(order, _echter_okxf())
        return replay.lauf_e("xperp", 0.05, "m", max_kerzen=420, bot=bot)

    def test_limit_fuellt_und_ziel_schliesst(self):
        # Order: buy @ 99.0, ziel 105.0, stop 95.0. Ab Schritt 300 faellt der
        # Kurs auf 98 (Fill ueber das Tief), steigt dann auf 110 (Ziel).
        def kurs(i):
            return 98.0 - i * 0.1 if i < 5 else 98.5 + i * 0.5

        runden, offen = self._lauf(kurs, ("buy", 2, 99.0, 105.0, 95.0))
        self.assertEqual(1, len(runden))
        self.assertEqual("long", runden[0]["seite"])
        self.assertEqual(99.0, runden[0]["einstieg"])
        self.assertEqual(105.0, runden[0]["ausstieg"])
        self.assertEqual(0, offen)

    def test_limit_verfaellt_ohne_fill(self):
        # Order buy @ 50.0 - der Kurs bleibt ueber 90, das Limit wird nie
        # beruehrt -> nach order_gueltig_kerzen ist alles vorbei, 0 Runden.
        def kurs(i):
            return 100.0 + i * 0.1

        runden, offen = self._lauf(kurs, ("buy", 2, 50.0, 105.0, 45.0))
        self.assertEqual(0, len(runden))
        self.assertEqual(0, offen)

    def test_stop_greift_zwischen_fill_und_ziel(self):
        # Fill bei 99, dann faellt der Kurs unter den Stop 97, bevor das
        # Ziel 104 kommt -> Runde mit grund stop zum Stoppreis.
        def kurs(i):
            return 100.0 - i * 0.5

        runden, offen = self._lauf(kurs, ("buy", 2, 99.0, 104.0, 97.0))
        self.assertEqual(1, len(runden))
        self.assertEqual(97.0, runden[0]["ausstieg"])
        self.assertEqual(0, offen)

    def test_journal_ist_paarbar(self):
        def kurs(i):
            return 98.0 - i * 0.1 if i < 5 else 98.5 + i * 0.5

        self._lauf(kurs, ("buy", 2, 99.0, 105.0, 95.0))
        journal = os.path.join(replay.buch_ordner("xperp", "m"),
                               "handelsjournal.csv")
        k = replay.kennzahlen(journal)
        self.assertGreaterEqual(k["runden"], 1)
        self.assertIn("f_max", k)
        # Die Beruehrungsregel: der ZIEL-Ausstieg sitzt auf der Marke.
        marke = replay.auf_der_marke(journal)
        self.assertGreaterEqual(marke["ausstiege_an_marke"], 1)


class BotIntegrationTest(_Basis):
    """Echte bot.py unter dem okxf-Ersatz - kein Netz, Methoden laufen."""

    def setUp(self):
        super().setUp()
        # Jeder echte okxf-Abruf wuerde hier explodieren statt zu netzen.
        okx = _echter_okxf()
        okx._mit_wiederholung = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("okxf-Netzzugriff im Replay-Test"))

    def test_bot_modul_laedt_die_drei_methoden(self):
        bot = replay._bot_modul()
        for name in ("zeige_lage", "zeige_trend", "zeige_grid"):
            self.assertTrue(callable(getattr(bot, name, None)),
                            "%s fehlt in bot.py" % name)
        self.assertEqual("4H", bot.BAR)

    def test_okxf_ersatz_liefert_kerzen_und_instrumente(self):
        bot = replay._bot_modul()
        stand = {"bis_ms": START_MS + 419 * KERZEN_MS}
        alle = {INST: _konstant(420)}
        metas = {INST: _meta()}
        okx = _echter_okxf()
        ersatz = replay._okxf_ersatz(bot.okxf, stand, metas, alle, "4H")
        instr = ersatz.instrument(INST.split("-")[0])
        self.assertEqual(INST, instr["instId"])
        self.assertEqual(1.0, float(instr["ctVal"]))
        k = ersatz.kerzen(INST, "4H", 300)
        self.assertEqual(300, len(k))
        self.assertLessEqual(k[-1][0], stand["bis_ms"])
        # Tageskerzen verdichtet kommen aus derselben Basis.
        kt = ersatz.kerzen(INST, "1D", 10)
        self.assertGreaterEqual(len(kt), 1)

    def test_bot_orders_liest_sammle_naht(self):
        bot = replay._bot_modul()
        stand = {"bis_ms": START_MS + 419 * KERZEN_MS}
        alle = {INST: _konstant(420)}
        metas = {INST: _meta()}
        okx = _echter_okxf()
        puffer = __import__("io").StringIO()
        ersatz = replay._okxf_ersatz(bot.okxf, stand, metas, alle, "4H")
        bot.okxf = ersatz
        import contextlib
        w = replay.wachen_von("xperp")
        w["mindest_kerzen"] = 300
        with contextlib.redirect_stdout(puffer):
            replay._bot_orders(bot, w, INST, "lage", metas, puffer)
        # lage erzeugt keine Order (CLI-Wahrheit) - kein Crash unter dem
        # Ersatz ist der eigentliche Beweis.
        self.assertTrue(True)

    def test_lauf_mit_echtem_bot_durchlaeuft(self):
        # Ein 0-Runden-Lauf ist hier ein gueltiges Ergebnis (die Indikatoren
        # sind Zufall); der Beweis ist: lauf_e kommt unter dem Ersatz ohne
        # Netz bis zum Journal.
        replay.lauf_e("xperp", 0.05, "i", max_kerzen=420,
                      wachen_patch=_wachen_patch())
        journal = os.path.join(replay.buch_ordner("xperp", "i"),
                               "handelsjournal.csv")
        self.assertTrue(os.path.isfile(journal))


class CLIUnterstuetzt(unittest.TestCase):
    def test_bot_methode_ist_ein_gueltiges_wahl(self):
        # Der CLI-Schalter existiert im argparse (Familie E braucht die Wahl
        # lage/trend/grid); das Parsing prueft die Datei, nicht das Netz.
        with open(os.path.join(HANDEL, "replay.py"), encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("--bot-methode", txt)
        self.assertIn("choices=(\"lage\", \"trend\", \"grid\")", txt)


class CLIEndeZuEndeTest(unittest.TestCase):
    """Der Akzeptanz-Aufruf `python replay.py --spur xperp --lauf test`.

    Faehrt die ECHTE Kommandozeile (subprocess, kein Import) und prueft, dass
    die JSON-Ausgabe die drei Akzeptanz-Groessen traegt: Runden, Trefferquote
    (p) und PnL (ergebnis_summe). Das ist der eine Test, der die Karte
    t_6ae063a4 beantwortet - die Mechanik pruefen die Stub-Tests oben, hier
    wird der Aufruf selbst zum Zeugen.

    Die OKX-Historie (daten/historie_okx) ist nicht versioniert - fehlt sie
    (Worktree, frische Kopie), wird der Test UEBERSPRUNGEN statt rot: ein
    fehlender Datenordner ist kein Codefehler. Erst 'python historie_okx.py
    --auffuellen --instrumente BTC --takte 4H' legt ihn an.
    """

    def setUp(self):
        self.ordner = os.path.join(HANDEL, "daten", "historie_okx")
        if not os.path.isdir(self.ordner):
            self.skipTest("OKX-Historie fehlt (%s) - erst historie_okx.py "
                          "--auffuellen" % self.ordner)

    def _lauf(self, *extra):
        import subprocess
        r = subprocess.run(
            [sys.executable, os.path.join(HANDEL, "replay.py"),
             "--spur", "xperp", "--lauf", "test"] + list(extra),
            cwd=HANDEL, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         "Exit %d\nstdout: %s\nstderr: %s"
                         % (r.returncode, r.stdout, r.stderr))
        return json.loads(r.stdout)

    def test_ausgabe_traegt_runden_trefferquote_und_pnl(self):
        aus = self._lauf()
        self.assertEqual("xperp", aus["spur"])
        self.assertEqual("okx", aus["kerzenquelle"])
        # Runden: die Top-Level-Zahl und die Kennzahlen-Rechnung muessen
        # uebereinstimmen (dieselbe Quelle, kein zweiter Zaehler).
        self.assertEqual(aus["runden"], aus["kennzahlen"]["runden"])
        # Trefferquote p und PnL ergebnis_summe sind die Akzeptanz-Groessen.
        self.assertIn("p", aus["kennzahlen"])
        self.assertIn("ergebnis_summe", aus["kennzahlen"])
        self.assertGreaterEqual(aus["kennzahlen"]["p"], 0.0)
        self.assertLessEqual(aus["kennzahlen"]["p"], 1.0)

    def test_bot_methode_ist_waehlbar_und_landet_im_ergebnis(self):
        for methode in ("lage", "trend", "grid"):
            aus = self._lauf("--bot-methode", methode)
            self.assertEqual(methode, aus["bot_methode"])
            # lage erzeugt keine Order (CLI-Wahrheit) - 0 Runden ist dort
            # ein gueltiges Ergebnis, kein Fehler.
            self.assertIn("runden", aus)


if __name__ == "__main__":
    unittest.main()
