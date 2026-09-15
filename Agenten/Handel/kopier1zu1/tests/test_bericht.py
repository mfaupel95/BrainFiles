"""kopier1zu1 in den Berichten: die Zeilen sind Behauptungen ueber den Zustand.

Der teuerste Fehler dieser Art ist ein Feldname, den es nicht gibt - er sieht
nicht wie ein Fehler aus, sondern wie "0 Positionen" oder "kein Wert". Die
Tests hier pruefen deshalb zuerst, dass jeder gelesene Name auf der
Schreiberseite existiert, und danach die abgeleiteten Zahlen.

Kein Test faehrt einen Zyklus, keiner beruehrt das echte Buch oder Q:.
"""

import json
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
SPUR = HIER.parent
HANDEL = SPUR.parent
sys.path.insert(0, str(HANDEL))
sys.path.insert(0, str(HANDEL / "kopier"))

sys.dont_write_bytecode = True
import tagesbericht as t                                     # noqa: E402


def _lade_buch():
    import importlib.util                                    # noqa: PLC0415
    spec = importlib.util.spec_from_file_location(
        "kopier1zu1_handeln_test", str(SPUR / "handeln.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FeldnamenTest(unittest.TestCase):
    """Jeder Name, den der Bericht liest, muss der Schreiber auch schreiben."""

    def setUp(self):
        self.z = json.loads((SPUR / "zustand.json").read_text("utf-8"))
        self.pos = self.z.get("positionen", [])

    def test_gelesene_positionsfelder_existieren(self):
        if not self.pos:
            self.skipTest("kein offener Bestand - nichts zu pruefen")
        gelesen = {"kette", "token", "symbol", "menge", "einsatz_usd",
                   "preis_einstieg", "stop_usd", "eroeffnet"}
        for p in self.pos:
            fehlend = gelesen - set(p)
            self.assertFalse(fehlend, "Bericht liest %s, Position hat es nicht"
                             % sorted(fehlend))

    def test_stop_preis_ist_kein_usd_betrag(self):
        """stop_usd ist ein Verlustbetrag. Als Preis gelesen ergaebe er
        einen Stop-Abstand von -100 % und die Zeile 'Stop gerissen' fuer
        jede gesunde Position."""
        if not self.pos:
            self.skipTest("kein offener Bestand")
        for p in self.pos:
            self.assertGreater(p["stop_usd"], p["preis_einstieg"] * 1000,
                               "stop_usd sieht wie ein Preis aus - dann ist "
                               "diese Annahme hinfaellig")


class StopPreisTest(unittest.TestCase):
    """Der abgeleitete Stop-Preis muss die Bedingung des Schreibers treffen."""

    def setUp(self):
        self.w = json.loads((SPUR / "wachen.json").read_text("utf-8"))
        self.buch = _lade_buch()

    def test_rueckrechnung_trifft_den_stop_betrag(self):
        p = {"menge": 220000.0, "einsatz_usd": 30.0, "stop_usd": 10.0}
        preis = t._stop_preis_1zu1(p, self.w, self.buch)
        self.assertIsNotNone(preis)
        erloes = self.buch._verkaeuflich(p["menge"], preis, self.w)
        self.assertAlmostEqual(p["einsatz_usd"] - erloes, p["stop_usd"],
                               places=6)

    def test_ohne_buch_kein_geratener_wert(self):
        p = {"menge": 1.0, "einsatz_usd": 30.0, "stop_usd": 10.0}
        self.assertIsNone(t._stop_preis_1zu1(p, self.w, None))

    def test_ohne_stop_feld_kein_wert(self):
        p = {"menge": 1.0, "einsatz_usd": 30.0}
        self.assertIsNone(t._stop_preis_1zu1(p, self.w, self.buch))


class BerichtTest(unittest.TestCase):
    def test_liest_genau_so_viele_positionen_wie_der_zustand(self):
        """Die Zahl ist der Nachweis: ein falscher Feldname zeigt 0 an."""
        s = t.spur_kopier1zu1()
        echt = json.loads((SPUR / "zustand.json").read_text("utf-8"))
        self.assertEqual(len(s["positionen"]),
                         len(echt.get("positionen", [])))

    def test_spur_steht_im_baue_tupel(self):
        """Ohne Eintrag in baue() erscheint die Spur in keinem Bericht."""
        import inspect                                       # noqa: PLC0415
        quelle = inspect.getsource(t.baue)
        self.assertIn("spur_kopier1zu1", quelle)

    def test_papierfest_und_ohne_pruefmodul(self):
        s = t.spur_kopier1zu1()
        self.assertTrue(s["papierfest"])
        self.assertIsNone(s["pruefmodul"])

    def test_zeile_nutzt_den_abgeleiteten_stop_nicht_den_usd_betrag(self):
        """Am ECHTEN Aufruf, nicht an der Hilfsfunktion: wird stop_usd roh
        durchgereicht, rechnet zeile_position() daraus einen Abstand von
        rund -100 % und meldet 'Stop gerissen' fuer jede gesunde Position."""
        s = t.spur_kopier1zu1()
        if not s["positionen"]:
            self.skipTest("kein offener Bestand")
        echt = json.loads((SPUR / "zustand.json").read_text("utf-8"))
        for p, e in zip(s["positionen"], echt["positionen"]):
            self.assertIsNotNone(p["stop"])
            self.assertNotEqual(p["stop"], e["stop_usd"],
                                "stop_usd roh durchgereicht")
            self.assertLess(p["stop"], e["preis_einstieg"],
                            "Stop-Preis muss unter dem Einstieg liegen")
            zeile = t.zeile_position(p, "USD")
            self.assertNotIn("gerissen", zeile)

    def test_bilanz_faellt_nicht_aus(self):
        """Fehlt das Modul, stuende hier 'Auswertung nicht lesbar'."""
        s = t.spur_kopier1zu1()
        self.assertNotIn("nicht lesbar", s["bilanz"])


class BusTest(unittest.TestCase):
    def test_spur_im_bus_status(self):
        sys.path.insert(0, str(HANDEL.parent / "Bus"))
        import handel_befehle                                # noqa: PLC0415
        self.assertIn("kopier1zu1", handel_befehle.SPUREN)


class AuswertungTest(unittest.TestCase):
    """Mit 0 Ausstiegen ist 'nichts zu messen' der Normalfall, kein Fehler."""

    def _modul(self):
        import importlib.util                                # noqa: PLC0415
        spec = importlib.util.spec_from_file_location(
            "auswertung_kopier1zu1_test", str(SPUR / "auswertung.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_leeres_buch_meldet_sauber(self):
        a = self._modul()
        zeilen = a.bericht(a.lade_ausstiege(), a._kosten())
        self.assertTrue(any("nichts zu messen" in z for z in zeilen))

    def test_aktionsname_passt_zum_schreiber(self):
        """ACTIONEN muss den Namen treffen, den handeln.py wirklich schreibt."""
        a = self._modul()
        quelle = (SPUR / "handeln.py").read_text("utf-8")
        for name in a.ACTIONEN:
            self.assertIn('aktion="%s"' % name, quelle)


if __name__ == "__main__":
    unittest.main()
