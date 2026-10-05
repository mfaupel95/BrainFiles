"""Tests der Historie-Wache: Regeln, nicht Tageswerte.

Das Hausmuster (Faelle 25/26/27 aus trugschluesse): eine Attrappe entscheidet
die Regel, eine Gegenprobe zeigt, dass die Regel ueberhaupt rot werden kann.
Fest verdrahtete Tageswerte wuerden morgen zerbrechen.

GEMESSEN (05.10.2026): die Wache entstand, weil `daten/historie/` nur DREI
`1D`-Dateien vom 25.09.2026 trug, `Bestand().symbole()` 0 lieferte und beide
Gegenproben in `test_replay_feed` mit "nichts geprueft" abbrachen. Ohne
Nachfuell-Weg waechst so ein Befund still.

ZWEI EIGENE FEHLER BEIM BAU (05.10.2026), beide im Test, nicht in der Regel:
  1. Die Attrappe lag eine Ebene zu hoch (`tmp/historie` statt
     `tmp/daten/historie`) - der Test pruefte den Fehlerpfad.
  2. Attrappe und "jetzt" trugen zwei verschiedene Zeitanker, die gespannte
     Datei lag damit in der ZUKUNFT und jede Reihe war juenger als null Tage:
     7 Fehlschlaege aus einem Vorzeichenfehler. Deshalb EIN Anker fuer beides.
"""

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
# `scripts/` -> Hermes -> Agenten -> BrainFiles. `parents[3]` waere eine Ebene
# ZU WEIT und endet in `C:\\Users\\faupe\\Documents` (der eigene Erstlauf:
# der Test las dort ein replay.py, das es nicht gibt). Geprueft wird das
# einmal - ein falscher Anker darf nicht als Dateifehler durchlaufen.
WURZEL = HIER.parents[2]
if not (WURZEL / "Agenten" / "Handel" / "replay.py").is_file():
    WURZEL = HIER.parents[3]
SCRIPT = HIER / "historie-wache.py"


def _lade():
    spec = importlib.util.spec_from_file_location("historie_wache", SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class Attrappe(unittest.TestCase):
    """Ein Tempordner als `daten/historie` - die echte Platte bleibt unberuehrt."""

    TAG = 86_400_000
    # EIN Zeitpunkt fuer Attrappe UND "jetzt" - dieselbe Konstante. Mit zwei
    # verschiedenen Ankern liegt die gespannte Datei in der Zukunft, ihre
    # Reihen sind damit juenger als 0 Tage und NICHTS wird gemeldet.
    JETZT = 1_800_000_000_000

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="historie-wache-"))
        # Der Pfad, den die Wache liest, ist `HANDEL/daten/historie` - die
        # Attrappe muss genau diese Form haben, sonst prueft der Test den
        # Fehlerpfad ("Ordner fehlt") statt der Regel.
        self.ordner = self.tmp / "daten" / "historie" / "feed"
        self.ordner.mkdir(parents=True)
        w = _lade()
        # Die Wache liest den Pfad aus dem Modul - genau dieser Weg wird
        # umgebogen, sonst prueft der Test die echte Historie (Hausregel: ein
        # Test fasst keine echte Zieldatei an).
        self.alt, self.alt_feed = w.HANDEL, w.FEED_ORDNER
        w.HANDEL = self.tmp
        # `FEED_ORDNER` ist die Naht, die `_feed_ordner()` zurueckgibt - sie
        # muss mitgebogen werden, sonst liest der Test den echten Ordner.
        w.FEED_ORDNER = self.ordner
        self.w = w
        self.addCleanup(self.aufraeumen)

    def aufraeumen(self):
        self.w.HANDEL = self.alt
        self.w.FEED_ORDNER = self.alt_feed
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.assertFalse(self.tmp.exists())

    def lege(self, sym, takt="1D", n=40, tage_alt=0):
        ende = self.JETZT - int(tage_alt * self.TAG)
        reihe = [[ende - (n - 1 - i) * self.TAG, "1", "2", "0.5", "100.0",
                  "1"] for i in range(n)]
        with open(self.ordner / ("%s_%s.json" % (sym, takt)), "w",
                  encoding="utf-8") as f:
            json.dump(reihe, f)

    def lege_viele(self, anzahl, takt="1D", tage_alt=0, alt_ab=None):
        """`anzahl` Reihen - so viele, wie der Backtest fuer 1D verlangt.

        OHNE diese Menge meldet die Wache immer die Mindestzahl, und die
        Altersregel laesst sich gar nicht pruefen (der eigene Erstlauf:
        4 Fehlschlaege, weil drei Testklassen je 1-4 Reihen legten, der
        Backtest aber 30 will). Die beiden Regeln werden getrennt geprueft -
        jede mit ihrer eigenen Menge.
        """
        alt_ab = alt_ab if alt_ab is not None else anzahl
        for i in range(anzahl):
            sym = "S%03dUSDT" % i
            tage = tage_alt if i < alt_ab else 0.0
            self.lege(sym, takt=takt, tage_alt=tage)

    def jetzt(self):
        return self.JETZT

    def genug_1d(self):
        """Die Mindestzahl der 1D-Regel - als Konstante, nicht als Zahl."""
        return self.w.TAKTE_BEACHTET["1D"]


class BeobachteteTakteTest(unittest.TestCase):
    def test_nur_takte_aus_der_liste(self):
        self.assertEqual({"1D", "1H"}, set(_lade().TAKTE_BEACHTET))

    def test_mindestzahl_der_1d_ist_die_des_backtests(self):
        """Die Wache darf nicht strenger sein als der Lauf, den sie warnt.

        `replay.lauf_feed(..., mindest_symbole=30)` ist die Vorgabe. Eine
        Wache, die 40 verlangt, wuerde einen Lauf melden, der laeuft.
        """
        quelle = (WURZEL / "Agenten" / "Handel" / "replay.py").read_text(
            encoding="utf-8")
        self.assertIn("mindest_symbole=30", quelle,
                      "die Vorgabe im Backtest hat sich geaendert - die "
                      "Mindestzahl in TAKTE_BEACHTET muss mitziehen")


class FrischTest(Attrappe):
    """Die ALTERS-Regel, mit genug Reihen - sonst meldet immer die Zahl."""

    def test_alle_reihen_frisch_ist_leise(self):
        self.lege_viele(self.genug_1d())
        zeilen, merker = self.w.befunde(self.jetzt())
        self.assertEqual([], zeilen, "eine frische Historie schweigt")
        self.assertEqual(self.genug_1d(), merker["takte"]["1D"]["n"])
        self.assertEqual([], merker["takte"]["1D"]["zu_alt"])

    def test_fuenf_tage_sind_noch_frisch(self):
        self.lege_viele(self.genug_1d(), tage_alt=5.0)
        zeilen, _ = self.w.befunde(self.jetzt())
        self.assertEqual([], zeilen)

    def test_grenze_strikt_gleich(self):
        self.lege_viele(self.genug_1d(), tage_alt=5.001)
        zeilen, _ = self.w.befunde(self.jetzt())
        self.assertTrue(any("aelter als 5" in z for z in zeilen), zeilen)


class ZuAltTest(Attrappe):
    def test_eine_alte_reihe_wird_genannt(self):
        self.lege_viele(self.genug_1d(), tage_alt=10.0, alt_ab=1)
        zeilen, merker = self.w.befunde(self.jetzt())
        zu_alt = merker["takte"]["1D"]["zu_alt"]
        self.assertEqual(1, len(zu_alt), zu_alt)
        self.assertTrue(any("1 von %d Reihen aelter" % self.genug_1d() in z
                            for z in zeilen), zeilen)

    def test_junge_reihe_wird_nicht_mit_genannt(self):
        """Genau die ZU ALTEN - eine Liste aller Reihen waere unbrauchbar."""
        self.lege_viele(self.genug_1d(), tage_alt=10.0, alt_ab=1)
        _, merker = self.w.befunde(self.jetzt())
        zu_alt = merker["takte"]["1D"]["zu_alt"]
        self.assertEqual(1, len(zu_alt),
                         "nur die eine alte Reihe, nicht alle %d"
                         % self.genug_1d())

    def test_zu_wenige_reihen_wird_gemeldet(self):
        """Die MINDESTZAHL - eigene Regel, eigene Menge."""
        n = self.genug_1d() - 1
        self.lege_viele(n)
        zeilen, _ = self.w.befunde(self.jetzt())
        self.assertTrue(any("nur %d von %d" % (n, self.genug_1d()) in z
                            for z in zeilen), zeilen)


class UnbeachteterTaktTest(Attrappe):
    def test_5m_wird_nicht_gemeldet(self):
        """5M/4H liest kein Lauf - sie zu melden waere taegliches Rauschen."""
        for takt in ("5M", "4H"):
            self.lege("AAAUSDT", takt=takt, tage_alt=900.0)
        zeilen, merker = self.w.befunde(self.jetzt())
        self.assertEqual([], zeilen)
        self.assertEqual({}, merker["takte"],
                         "ein unbeachteter Takt darf nicht mal im Merker "
                         "landen")

    def test_1h_wird_dabei_wohl_gemeldet(self):
        self.lege("AAAUSDT", takt="1H", tage_alt=900.0)
        zeilen, _ = self.w.befunde(self.jetzt())
        self.assertTrue(any(z.startswith("1H:") for z in zeilen), zeilen)


class KaputterOrdnerTest(Attrappe):
    def test_fehlender_ordner_wird_gemeldet(self):
        shutil.rmtree(self.ordner.parent)
        zeilen, _ = self.w.befunde(self.jetzt())
        self.assertEqual(1, len(zeilen), zeilen)
        self.assertIn("Historie fehlt", zeilen[0])

    def test_defekte_datei_wird_uebersprungen_nicht_gezaehlt(self):
        self.lege("AAAUSDT")
        with open(self.ordner / "BBBUSDT_1D.json", "w",
                  encoding="utf-8") as f:
            f.write("{kaputt")
        for sym in ("CCCUSDT", "DDDUSDT"):
            self.lege(sym)
        _, merker = self.w.befunde(self.jetzt())
        self.assertEqual(3, merker["takte"]["1D"]["n"],
                         "eine unlesbare Datei zaehlt nicht als Reihe - "
                         "sonst waere die Breite eine Zufallsgroesse")


class GegenprobeTest(Attrappe):
    """Die Regel muss ueberhaupt ROT werden koennen."""

    def test_ohne_altergrenze_wird_nichts_gemeldet(self):
        """MAX_ALTER_TAGE auf unendlich -> die Wache schweigt beim Alter."""
        alt = self.w.MAX_ALTER_TAGE
        self.w.MAX_ALTER_TAGE = 10 ** 9
        try:
            self.lege_viele(self.genug_1d(), tage_alt=10_000.0)
            zeilen, merker = self.w.befunde(self.jetzt())
        finally:
            self.w.MAX_ALTER_TAGE = alt
        self.assertEqual([], zeilen)
        self.assertEqual([], merker["takte"]["1D"]["zu_alt"])

    def test_ohne_mindestzahl_wird_die_luecke_verschwiegen(self):
        alt = dict(self.w.TAKTE_BEACHTET)
        self.w.TAKTE_BEACHTET = {"1D": 1}
        try:
            self.lege("AAAUSDT")
            zeilen, _ = self.w.befunde(self.jetzt())
        finally:
            self.w.TAKTE_BEACHTET = alt
        self.assertEqual([], zeilen, "mit der Mindestzahl 1 ist die Historie "
                                    "ausreichend - es darf nichts gemeldet "
                                    "werden")

    def test_kommt_die_geregelte_meldung_von_allein(self):
        """Gegenprobe zurueck: beide Meldungen erscheinen wieder."""
        n = self.genug_1d()
        # n-1 Reihen, davon EINE zu alt: so greifen beide Regeln zugleich.
        # (Ein zusaetzliches `lege` waere die n-te Reihe - dann waere die
        # Mindestzahl erfuellt und nur die Altersregel spruenge.)
        self.lege_viele(n - 1, tage_alt=10.0, alt_ab=1)
        zeilen, _ = self.w.befunde(self.jetzt())
        self.assertTrue(any("nur %d von %d" % (n - 1, n) in z for z in zeilen),
                        zeilen)
        self.assertTrue(any("aelter als 5" in z for z in zeilen), zeilen)


if __name__ == "__main__":
    unittest.main()
