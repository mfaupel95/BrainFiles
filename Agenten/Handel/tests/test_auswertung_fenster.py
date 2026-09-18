"""Tests fuer das Zeitfenster in der Spurenauswertung.

Zwei Dinge, die still schiefgehen: ein Aufruf OHNE Fenster muss dieselbe
Zahl liefern wie vor dem Umbau (sonst aendert der Umbau die Buecher), und
MIN_RUNDEN muss JE FENSTER greifen (sonst behauptet ein Monat mit drei
Runden eine Trefferquote).

Gearbeitet wird auf erfundenen Journalen in einem Temp-Ordner.
"""

import datetime as dt
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import auswertung_alle as aa                                   # noqa: E402

# Das Format, das runden_indikator ueber _paare wirklich liest: die Spalte
# `inst` gruppiert die Runden, und `einsatz_usd` traegt beim Kauf den Einsatz
# und beim Verkauf den Erloes - derselbe Feldname, zwei Bedeutungen
# (auswertung_alle.py:285 und :223). Ohne `inst` baut _paare keine Runde.
KOPF = "zeit,aktion,inst,einsatz_usd,grund\n"

# Eine Runde im August (+10), eine im September (-10).
JOURNAL = KOPF + (
    "2026-08-01T10:00:00+00:00,kauf,BTC,100,einstieg\n"
    "2026-08-02T10:00:00+00:00,verkauf,BTC,110,ziel\n"
    "2026-09-10T10:00:00+00:00,kauf,BTC,100,einstieg\n"
    "2026-09-11T10:00:00+00:00,verkauf,BTC,90,stop\n"
)


class TestFensterInZeilen(unittest.TestCase):
    """zeilen() liefert die Zeilen der Spur - ungeschnitten.

    Der Fensterschnitt sitzt nicht mehr hier. Ein Schnitt VOR der Paarung
    verwirft jede Runde, deren Einstieg vor dem Fenster liegt: _paare()
    sieht dann einen Ausstieg ohne Einstieg und wirft ihn weg. Geschnitten
    wird nach der Paarung, an der Ausstiegszeit der Runde.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        wurzel = Path(self.tmp.name)
        (wurzel / "squeeze").mkdir()
        (wurzel / "squeeze" / "handelsjournal.csv").write_text(
            JOURNAL, encoding="utf-8")
        self._alt = aa.HIER
        aa.HIER = wurzel

    def tearDown(self):
        aa.HIER = self._alt
        self.tmp.cleanup()

    def test_zeilen_liefert_alle_zeilen(self):
        self.assertEqual(len(aa.zeilen("squeeze")), 4)

    def test_zeilen_nimmt_kein_fenster_mehr_entgegen(self):
        # Ein Fensterschnitt VOR der Paarung ist die falsche Bedeutung; das
        # Schluesselwort darf nicht zurueckkommen, ohne dass es auffaellt.
        von = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
        with self.assertRaises(TypeError):
            aa.zeilen("squeeze", von=von)

    def test_fenster_schneidet_die_runden(self):
        von = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
        k = aa.kennzahlen_fuer("squeeze", von=von, bis=None)
        self.assertEqual(k["n"], 1)
        self.assertAlmostEqual(k["ergebnis"], -10.0)

    def test_kennzahlen_ohne_zeilen_sind_none(self):
        von = dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc)
        self.assertIsNone(aa.kennzahlen_fuer("squeeze", von=von, bis=None))


class TestMinRundenJeFenster(unittest.TestCase):

    def test_wenige_runden_gelten_als_nicht_belastbar(self):
        # Zwei Runden liegen unter MIN_RUNDEN. Die Kennzahlen duerfen
        # entstehen, aber die Belastbarkeit muss falsch sein.
        k = aa.kennzahlen([{"ergebnis": 10.0, "einsatz": 100.0, "grund": "ziel"},
                           {"ergebnis": -10.0, "einsatz": 100.0, "grund": "stop"}], "USD")
        self.assertFalse(aa.belastbar(k))

    def test_genug_runden_sind_belastbar(self):
        runden = [{"ergebnis": 1.0, "einsatz": 100.0, "grund": "ziel"}] * aa.MIN_RUNDEN
        self.assertTrue(aa.belastbar(aa.kennzahlen(runden, "USD")))

    def test_keine_kennzahlen_sind_nicht_belastbar(self):
        self.assertFalse(aa.belastbar(None))


class TestLage(unittest.TestCase):
    """Drei Kategorien statt zwei - und ein Strich heisst nicht mehr
    zweierlei."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.tmp.name)
        # Eine Spur mit Buch, eine ohne - beide mit Zustand, wie im Baum.
        for spur in ("squeeze", "supertrend"):
            (self.wurzel / spur).mkdir()
            (self.wurzel / spur / "zustand.json").write_text(
                "{}", encoding="utf-8")
        (self.wurzel / "squeeze" / "handelsjournal.csv").write_text(
            JOURNAL, encoding="utf-8")
        self._alt = aa.HIER
        aa.HIER = self.wurzel

    def tearDown(self):
        aa.HIER = self._alt
        self.tmp.cleanup()

    def test_ohne_journal_heisst_kein_buch(self):
        self.assertEqual(aa.lage_der_spur("supertrend", None), "kein Buch")

    def test_mit_journal_aber_wenig_runden(self):
        k = aa.kennzahlen_fuer("squeeze")
        self.assertEqual(aa.lage_der_spur("squeeze", k), "zu wenige Runden")

    def test_mit_genug_runden_belastbar(self):
        k = aa.kennzahlen([{"ergebnis": 1.0, "einsatz": 100.0, "grund": "ziel"}] * aa.MIN_RUNDEN,
                          "USD")
        self.assertEqual(aa.lage_der_spur("squeeze", k), "belastbar")

    def test_buch_seit_nennt_den_zustand(self):
        # Ohne Journal ist der Zustand die einzige Spur davon, dass die
        # Spur ueberhaupt laeuft.
        self.assertIsNotNone(aa.buch_seit("supertrend"))


class TestAnzeigeFuer(unittest.TestCase):
    """Vier Zustaende, eine Entscheidung - anzeige_fuer() ist die einzige
    Heimat des Anzeigetexts, den die Uebersicht heute noch im Druckblock
    selbst entschied."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.tmp.name)
        # kein Buch: kein Ordner noetig, hat_buch() prueft nur die Datei.
        # keine geschlossene Runde: ein Journal mit nur dem Kopf.
        (self.wurzel / "leer").mkdir()
        (self.wurzel / "leer" / "handelsjournal.csv").write_text(
            KOPF, encoding="utf-8")
        # zu wenige Runden / belastbar: dieselbe Spur, unterschiedliches k.
        (self.wurzel / "squeeze").mkdir()
        (self.wurzel / "squeeze" / "handelsjournal.csv").write_text(
            JOURNAL, encoding="utf-8")
        self._alt = aa.HIER
        aa.HIER = self.wurzel

    def tearDown(self):
        aa.HIER = self._alt
        self.tmp.cleanup()

    def test_kein_buch(self):
        self.assertEqual(aa.anzeige_fuer("supertrend", None), "kein Buch")

    def test_keine_geschlossene_runde(self):
        k = aa.kennzahlen_fuer("leer")
        self.assertIsNone(k)
        self.assertEqual(aa.anzeige_fuer("leer", k),
                          "keine geschlossene Runde")

    def test_zu_wenige_runden(self):
        k = aa.kennzahlen_fuer("squeeze")
        self.assertEqual(aa.anzeige_fuer("squeeze", k), "zu wenige Runden")

    def test_belastbar(self):
        k = aa.kennzahlen(
            [{"ergebnis": 1.0, "einsatz": 100.0, "grund": "ziel"}]
            * aa.MIN_RUNDEN, "USD")
        self.assertEqual(aa.anzeige_fuer("squeeze", k), "belastbar")


# Eine Runde ueber die Fensterkante: Einstieg im August, Ausstieg im
# September. Dazu das Gegenstueck: Einstieg im September, Ausstieg im
# Oktober. Genau die beiden Faelle, an denen sich die Bedeutung entscheidet.
JOURNAL_UEBER_DIE_KANTE = KOPF + (
    "2026-08-25T10:00:00+00:00,kauf,BTC,100,einstieg\n"
    "2026-09-05T10:00:00+00:00,verkauf,BTC,120,ziel\n"
    "2026-09-20T10:00:00+00:00,kauf,ETH,100,einstieg\n"
    "2026-10-05T10:00:00+00:00,verkauf,ETH,90,stop\n"
)


class TestRundeGehoertInsFensterIhresAusstiegs(unittest.TestCase):
    """Eine Runde faellt beim AUSSTIEG an - das ist ihr Fenster.

    Vorher schnitt zeilen() die Zeilen vor der Paarung. Eine Runde, die vor
    dem Fenster einstieg und darin ausstieg, verschwand damit spurlos: ihr
    Ausstieg stand ohne Einstieg da und wurde weggeworfen. Die Zahl war zu
    klein, ohne dass irgendwo etwas gemeldet wurde.
    """

    VON = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    BIS = dt.datetime(2026, 9, 30, 23, 59, 59, tzinfo=dt.timezone.utc)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        wurzel = Path(self.tmp.name)
        (wurzel / "squeeze").mkdir()
        (wurzel / "squeeze" / "handelsjournal.csv").write_text(
            JOURNAL_UEBER_DIE_KANTE, encoding="utf-8")
        self._alt = aa.HIER
        aa.HIER = wurzel

    def tearDown(self):
        aa.HIER = self._alt
        self.tmp.cleanup()

    def test_einstieg_vor_dem_fenster_zaehlt_trotzdem(self):
        k = aa.kennzahlen_fuer("squeeze", von=self.VON, bis=self.BIS)
        self.assertEqual(k["n"], 1)
        self.assertAlmostEqual(k["ergebnis"], 20.0)

    def test_ausstieg_nach_dem_fenster_zaehlt_nicht(self):
        k = aa.kennzahlen_fuer("squeeze", von=self.VON, bis=self.BIS)
        self.assertNotIn("stop", k["gruende"])

    def test_ohne_fenster_bleiben_es_beide_runden(self):
        k = aa.kennzahlen_fuer("squeeze")
        self.assertEqual(k["n"], 2)


# Das Gitter-Journal so, wie handeln.py es schreibt: KAUF und AUSSTIEG,
# der Zyklusgewinn als gw_usd in der Ausstiegszeile.
GITTER_KOPF = ("zeit,modus,aktion,inst,stufe,preis,menge,einsatz_usd,"
               "wert_usd,gw_usd,kasse_usd,buchwert_usd,bestand_menge,"
               "letzter_kurs,grund\n")
GITTER_JOURNAL = GITTER_KOPF + (
    "2026-08-25T10:00:00+00:00,papier,KAUF,BTC-USDT,6,100,1,100,,,,,,,Stufe 6\n"
    "2026-09-05T10:00:00+00:00,papier,AUSSTIEG,BTC-USDT,6,110,1,100,110,10,"
    ",,,,Stufe 6 -> 7\n"
    "2026-09-20T10:00:00+00:00,papier,KAUF,BTC-USDT,5,100,1,100,,,,,,,Stufe 5\n"
    "2026-10-05T10:00:00+00:00,papier,AUSSTIEG,BTC-USDT,5,90,1,100,90,-10,"
    ",,,,Stufe 5 -> 6\n"
)


def _lade_gitter():
    """gitter/auswertung.py ueber den Dateipfad - die Spur ist kein Paket."""
    name = "fenstertest_gitter_auswertung"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, HIER.parent / "gitter" / "auswertung.py")
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


class TestBeideWegeZaehlenGleich(unittest.TestCase):
    """Dieselben Daten, dasselbe Fenster, dieselbe Rundenzahl.

    gitter ist die einzige Spur, die beide Wege kennt: den Rundenweg aus
    auswertung_alle (kennzahlen_fuer) und die eigene Auswertung
    (kennzahlen_kurz ueber buchauswertung.lade_zeilen). gesamtbilanz.summe()
    addiert beide Wege in dieselbe Zelle - liefern sie verschiedene Zahlen,
    beantwortet eine Zelle zwei Fragen.

    lade_ausstiege() wird ueber das MODULATTRIBUT ersetzt: sein Vorgabewert
    `pfad=JOURNAL` wird beim Import gebunden, ein blosses Umbiegen von
    JOURNAL erreicht ihn nicht.
    """

    VON = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    BIS = dt.datetime(2026, 9, 30, 23, 59, 59, tzinfo=dt.timezone.utc)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        wurzel = Path(self.tmp.name)
        (wurzel / "gitter").mkdir()
        self.journal = wurzel / "gitter" / "handelsjournal.csv"
        self.journal.write_text(GITTER_JOURNAL, encoding="utf-8")
        self.wachen = wurzel / "gitter" / "wachen.json"
        self.wachen.write_text("{}", encoding="utf-8")
        self._alt = aa.HIER
        aa.HIER = wurzel
        self.m = _lade_gitter()
        self._alt_journal = self.m.JOURNAL
        self._alt_wachen = self.m.WACHEN
        self._alt_laden = self.m.lade_ausstiege
        echt = self._alt_laden
        pfad = str(self.journal)
        self.m.JOURNAL = pfad
        self.m.WACHEN = str(self.wachen)
        self.m.lade_ausstiege = (
            lambda p=pfad, von=None, bis=None: echt(p, von=von, bis=bis))

    def tearDown(self):
        self.m.JOURNAL = self._alt_journal
        self.m.WACHEN = self._alt_wachen
        self.m.lade_ausstiege = self._alt_laden
        aa.HIER = self._alt
        self.tmp.cleanup()

    def test_gleiche_rundenzahl_im_fenster(self):
        eins = aa.kennzahlen_fuer("gitter", von=self.VON, bis=self.BIS)
        zwei = self.m.kennzahlen_kurz(von=self.VON, bis=self.BIS)
        self.assertIsNotNone(eins)
        self.assertIsNotNone(zwei)
        self.assertEqual(eins["n"], zwei["n"])
        self.assertEqual(eins["n"], 1)

    def test_gleiche_rundenzahl_ohne_fenster(self):
        eins = aa.kennzahlen_fuer("gitter")
        zwei = self.m.kennzahlen_kurz()
        self.assertEqual(eins["n"], zwei["n"])
        self.assertEqual(eins["n"], 2)


if __name__ == "__main__":
    unittest.main()
