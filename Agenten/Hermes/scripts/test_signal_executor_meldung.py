"""Nur melden, was sich aendert: die Wiederholungssperre des Signal-Ausfuehrers.

ANLASS (03.10.2026, 22:38-22:48 gemessen)
-----------------------------------------
Der Cron laeuft JEDE MINUTE und schickte in jedem Lauf dieselben Zeilen:
`moondev_topmovers: freigabe nicht erteilt, Auftrag bleibt` - dreifach,
weil drei Risikostufen (Basis, mittel, hoch) je eine signal_queue*.json
haben. Nachrichten an Max alle zwei Minuten, ohne dass sich etwas geaendert
haette.

DIE REGELN
----------
1. Eine Meldung geht raus, wenn ihr TEXT sich gegen den letzten Lauf
   aendert - nicht wenn sie nur wiederholt wird.
2. Eine ausgefuehrte Order und ein Ordnerfehler gehen IMMER raus, auch
   unveraendert: beides ist ein Ereignis, kein Zustand.
3. Nach WIEDERHOLUNG_S kommt derselbe Zustand noch einmal - "wartet auf
   Freigabe" ist nuetzlich, aber taeglich, nicht minuetlich.
4. Der Weg aus der Warteliste loescht die Merkung: sonst waere die naechste
   Meldung derselben Spur nie wieder "neu".

Die Merkdatei wird auf einen TEMP-Pfad gebogen - der Test fasst die echte
nicht an (T-100: eine Datei, die der Test haette schreiben koennen, waere
zugleich die, die ein schreibender Test zerstoeren kann).
"""
import importlib.util
import os
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "signal-executor.py")


def lade(tempdir):
    spec = importlib.util.spec_from_file_location("sigexec_test", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["sigexec_test"] = m
    spec.loader.exec_module(m)
    # Das ECHTE MERK merken, BEVOR es auf den Temp-Pfad gebogen wird - sonst
    # prueft der Pfad-Test genau die Sache, die er abstellen sollte.
    m.MERK_ECHT = m.MERK
    m.MERK = os.path.join(tempdir, "merk.json")
    return m


class NurAenderungenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.m = lade(self.tmp)

    def tearDown(self):
        if os.path.isfile(self.m.MERK):
            os.remove(self.m.MERK)
        os.rmdir(self.tmp)

    # 1. Grundregel: dasselbe zweimal -> nur einmal
    def test_unveraendert_geht_nur_einmal_raus(self):
        z = {"topmovers": "freigabe nicht erteilt"}
        r1 = self.m.melde_neu(dict(z), 1000.0)
        r2 = self.m.melde_neu(dict(z), 1001.0)
        r3 = self.m.melde_neu(dict(z), 1002.0)
        self.assertEqual(len(r1), 1, "die erste Meldung muss raus")
        self.assertEqual(r2, [], "unveraendert darf nicht erneut raus")
        self.assertEqual(r3, [], "unveraendert darf nicht erneut raus")

    # Gegenprobe: ohne Merkdatei kommt die Zeile wieder. Ohne diese Regel
    # waere der Test auch gruen, wenn melde_neu() naemlich immer [] gaebe.
    def test_gegenprobe_ohne_merk_wird_wieder_gemeldet(self):
        z = {"topmovers": "freigabe nicht erteilt"}
        self.m.melde_neu(dict(z), 1000.0)
        os.remove(self.m.MERK)                     # Merkung weg
        r = self.m.melde_neu(dict(z), 1001.0)
        self.assertEqual(len(r), 1, "ohne Merkung ist die Meldung neu")

    # 2. Aenderung geht raus
    def test_textwechsel_geht_raus(self):
        self.m.melde_neu({"spur": "freigabe nicht erteilt"}, 1000.0)
        r = self.m.melde_neu({"spur": "kein offenes Freigabefenster"}, 1001.0)
        self.assertEqual(len(r), 1)
        self.assertIn("Freigabefenster", r[0])

    # 3. Wiederholung nach der Frist
    def test_nach_der_frist_wiederholt_es_sich(self):
        z = {"spur": "freigabe nicht erteilt"}
        self.m.melde_neu(dict(z), 1000.0)
        r = self.m.melde_neu(dict(z), 1000.0 + self.m.WIEDERHOLUNG_S + 1)
        self.assertEqual(len(r), 1, "nach der Frist wird wiederholt")
        self.assertEqual(
            self.m.melde_neu(dict(z), 1000.0 + self.m.WIEDERHOLUNG_S + 2), [])

    # 4. Order und Fehler gehen IMMER raus
    def test_order_und_fehler_gehen_immer_raus(self):
        self.m.melde_neu({"spur": "LONG AR @ 4.51 (Order gesetzt)"}, 1000.0)
        r = self.m.melde_neu({"spur": "LONG AR @ 4.51 (Order gesetzt)"}, 1001.0)
        self.assertEqual(len(r), 1, "eine Order ist ein Ereignis, kein Zustand")
        self.m.melde_neu({"spur": "Signal nicht ausgefuehrt: Order scheitert"}, 2000.0)
        r2 = self.m.melde_neu({"spur": "Signal nicht ausgefuehrt: Order scheitert"}, 2001.0)
        self.assertEqual(len(r2), 1, "ein Fehler ist ein Ereignis, kein Zustand")

    # 5. Weg aus der Warteliste loescht die Merkung
    def test_weg_und_zurueck_wieder_melden(self):
        z = {"spur": "freigabe nicht erteilt"}
        self.m.melde_neu(dict(z), 1000.0)
        self.assertEqual(self.m.melde_neu(dict(z), 1001.0), [])
        self.m.melde_neu({}, 1002.0)              # Queue leer -> Spur weg
        self.assertEqual(len(self.m.melde_neu(dict(z), 1003.0)), 1,
                         "nach dem Weg muss dieselbe Meldung wieder neu sein")

    # 6. Die Merkdatei liegt im Cache und wird im Test umgebogen
    def test_merkdatei_ist_im_cache(self):
        self.assertTrue(self.m.CACHE.endswith(os.path.join("Hermes", "cache")),
                        "die Merkdatei gehoert nach Agenten/Hermes/cache")
        self.assertTrue(self.m.MERK_ECHT.startswith(self.m.CACHE),
                        "das echte MERK muss im Cache liegen, nicht daneben")
        self.assertNotEqual(self.m.MERK_ECHT, self.m.MERK,
                            "der Test biegt das MERK um - steht hier das echte, "
                            "schreibt der Test in die Betriebsdatei")


class ZusammenfassungProSpurTest(unittest.TestCase):
    """Drei Risikostufen sind EINE Spur: eine Zeile, mit Stufenzahl."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.m = lade(self.tmp)

    def tearDown(self):
        if os.path.isfile(self.m.MERK):
            os.remove(self.m.MERK)
        os.rmdir(self.tmp)

    def test_dreimal_dieselbe_meldung_wird_eine_zeile(self):
        m = self.m.zeilen_je_spur({"topmovers": {
            "stufen": 3, "meldung": "freigabe nicht erteilt", "ok": False}})
        self.assertEqual(len(m), 1)
        self.assertIn("3 Risikostufen", m["topmovers"])

    def test_order_wird_nicht_als_stufenzahl_ausgegeben(self):
        m = self.m.zeilen_je_spur({"xperp": {
            "stufen": 2, "meldung": "LONG AR @ 4.51", "ok": True}})
        self.assertNotIn("Risikostufen", m["xperp"])


if __name__ == "__main__":
    unittest.main()