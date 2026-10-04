"""Die fuenf Spuren mit eigener Auswertung muessen summierbar werden.

Geprueft wird nicht die RECHNUNG - die bleibt, wie sie ist - sondern die
FORM: fuenf Module, eine Rueckgabe, damit die Gesamtbilanz sie addieren
kann, ohne fuenf Sonderfaelle zu kennen.
"""

import datetime as dt
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
sys.path.insert(0, str(WURZEL))

# Geladen wird ueber den Dateipfad, nicht ueber den Punktnamen. Die Spuren
# sind keine Pakete (kein __init__.py), und jede legt beim Import ihren
# eigenen Ordner in sys.path - ein "import spiegel.auswertung" haengt damit
# davon ab, was vorher lief. Der Dateipfad haengt von nichts ab.
SPUREN = ("spiegel", "omniquant", "kopier", "gitter")


def lade(spur):
    """Laedt <spur>/auswertung.py unter eigenem Modulnamen."""
    name = "spur_%s_auswertung" % spur
    if name in sys.modules:
        return sys.modules[name]
    pfad = WURZEL / spur / "auswertung.py"
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul

PFLICHTFELDER = ("n", "ergebnis", "treffer", "waehrung", "live")


class TestMindestform(unittest.TestCase):
    """Fuenf Module, eine Rueckgabe - hier nur, DASS es sie gibt."""

    def test_jedes_modul_hat_kennzahlen_kurz(self):
        for spur in SPUREN:
            with self.subTest(spur=spur):
                m = lade(spur)
                self.assertTrue(hasattr(m, "kennzahlen_kurz"),
                                "%s fehlt kennzahlen_kurz()" % spur)


class TestAufErfundenemJournal(unittest.TestCase):
    """Die Form UND das Fenster, gegen eine bekannte Zahl.

    Bis zum 18.09.2026 standen hier zwei Pruefungen, die leer durchliefen:
    eine uebersprang per `if k is None: continue`, die andere behauptete nur
    `assertIsNone`. Beide waren erfuellt, wenn ein Modul ueberhaupt nichts
    liest - genau der Ausfall, den sie fangen sollten. Ausserdem liefen sie
    gegen die echten Journale im Baum, ihr Ergebnis hing also am Datenstand.

    Jetzt liegt EINE erfundene Ausstiegsrunde im Temp-Ordner, und jede
    Behauptung hat ein positives Gegenstueck: ein Fenster um die Runde
    herum muss sie liefern (n == 1), eines danach nicht (None).

    lade_ausstiege() wird ueber das MODULATTRIBUT ersetzt: sein Vorgabewert
    `pfad=JOURNAL` wird beim Import gebunden, ein blosses Umbiegen von
    JOURNAL erreicht ihn nicht.
    """

    # Die Spalten aller fuenf Module zusammen. Jedes liest nur die seinen;
    # was es nicht kennt, stoert nicht. So braucht es nicht fuenf Journale.
    SPALTEN = ("zeit", "aktion", "einsatz_usd", "wert_usd", "grund", "inst",
               "symbol", "token", "kette", "wallet", "seite", "stufe",
               "gw_usd", "score", "cr", "mfe_pct", "mae_pct", "haltetage",
               "marktkap_usd")
    WERTE = {"zeit": "2026-09-10T12:00:00+00:00", "aktion": "",
             "einsatz_usd": "100", "wert_usd": "110", "grund": "ziel",
             "inst": "BTC-USDT", "symbol": "BTC", "token": "BTC",
             "kette": "sol", "wallet": "W1", "seite": "long", "stufe": "6",
             "gw_usd": "10", "score": "1", "cr": "1", "mfe_pct": "1",
             "mae_pct": "-1", "haltetage": "1", "marktkap_usd": "1000000"}

    VON = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    BIS = dt.datetime(2026, 9, 30, tzinfo=dt.timezone.utc)
    KUENFTIG = dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc)

    def setUp(self):
        self.ordner = tempfile.mkdtemp()
        self.alt = {}

    def tearDown(self):
        for spur, (journal, wachen, laden) in self.alt.items():
            m = lade(spur)
            m.JOURNAL = journal
            m.WACHEN = wachen
            m.lade_ausstiege = laden
        shutil.rmtree(self.ordner, ignore_errors=True)

    def _biege(self, spur):
        """Journal und Merker der Spur auf den Temp-Ordner legen.

        Nur lesend gegenueber dem Baum: das echte Journal wird nicht
        angefasst, das Zweitziel nirgends beruehrt.
        """
        m = lade(spur)
        if spur not in self.alt:
            self.alt[spur] = (m.JOURNAL, m.WACHEN, m.lade_ausstiege)
        werte = dict(self.WERTE, aktion=m.ACTIONEN[0])
        journal = os.path.join(self.ordner, "journal_%s.csv" % spur)
        with open(journal, "w", encoding="utf-8") as f:
            f.write(",".join(self.SPALTEN) + "\n")
            f.write(",".join(werte[s] for s in self.SPALTEN) + "\n")
        wachen = os.path.join(self.ordner, "wachen_%s.json" % spur)
        with open(wachen, "w", encoding="utf-8") as f:
            f.write('{"handel_erlaubt": false}')
        echt = self.alt[spur][2]
        m.JOURNAL = journal
        m.WACHEN = wachen
        m.lade_ausstiege = (
            lambda p=journal, von=None, bis=None: echt(p, von=von, bis=bis))
        return m

    def test_rueckgabe_ist_vollstaendig(self):
        for spur in SPUREN:
            with self.subTest(spur=spur):
                k = self._biege(spur).kennzahlen_kurz()
                self.assertIsNotNone(k, "%s liest sein Journal nicht" % spur)
                for feld in PFLICHTFELDER:
                    self.assertIn(feld, k, "%s: %s fehlt" % (spur, feld))
                self.assertEqual(k["n"], 1)
                self.assertIsInstance(k["waehrung"], str)
                self.assertIsInstance(k["live"], bool)
                self.assertFalse(k["live"])

    def test_fenster_um_die_runde_liefert_sie(self):
        # Das positive Gegenstueck. Ohne es ist "im Fenster nichts" auch
        # dann erfuellt, wenn das Modul ueberhaupt nichts liest.
        for spur in SPUREN:
            with self.subTest(spur=spur):
                k = self._biege(spur).kennzahlen_kurz(von=self.VON,
                                                      bis=self.BIS)
                self.assertIsNotNone(k)
                self.assertEqual(k["n"], 1)

    def test_fenster_nach_der_runde_ist_none(self):
        # Wuerde das Fenster nur entgegengenommen und nicht durchgereicht,
        # kaeme hier weiter die Zahl seit Anfang - die stille Falschzahl.
        for spur in SPUREN:
            with self.subTest(spur=spur):
                self.assertIsNone(
                    self._biege(spur).kennzahlen_kurz(von=self.KUENFTIG))


class TestLiveMerker(unittest.TestCase):
    """_live() darf nie werfen - der Merker entscheidet mit, ob eine Zahl
    als echtes Geld gilt. Ein Wurf hier nimmt die ganze Spur aus der
    Gesamtbilanz, wegen einer Datei, die nur informativ ist."""

    def setUp(self):
        self.ordner = tempfile.mkdtemp()
        self.datei = os.path.join(self.ordner, "wachen.json")
        self.alt = {}

    def tearDown(self):
        for spur, wert in self.alt.items():
            lade(spur).WACHEN = wert
        shutil.rmtree(self.ordner, ignore_errors=True)

    def _merker(self, spur, inhalt):
        """Setzt WACHEN der Spur auf eine eigene Datei und liest _live()."""
        m = lade(spur)
        if spur not in self.alt:
            self.alt[spur] = m.WACHEN
        if inhalt is None:
            if os.path.exists(self.datei):
                os.remove(self.datei)
        else:
            with open(self.datei, "w", encoding="utf-8") as f:
                f.write(inhalt)
        m.WACHEN = self.datei
        return m._live()

    def test_papier_bei_jedem_fehlschlag(self):
        # None heisst: Datei fehlt ganz.
        for inhalt in (None, "kein JSON {", "[]", "42", "null", '"x"', "{}",
                       '{"handel_erlaubt": false}'):
            for spur in SPUREN:
                with self.subTest(spur=spur, inhalt=inhalt):
                    self.assertFalse(self._merker(spur, inhalt))

    def test_true_wird_erkannt(self):
        for spur in SPUREN:
            with self.subTest(spur=spur):
                self.assertTrue(
                    self._merker(spur, '{"handel_erlaubt": true}'))


if __name__ == "__main__":
    unittest.main()
