"""Tests fuer scripts/memory-verlust-wache.py - Regel statt Zustand.

Geprueft wird das Verhalten der Wache: erster Lauf schweigt und setzt die
Merkdatei, ein NEUER Verlust wird genau einmal gemeldet, ein bekannter nicht
wieder, und ein Messfehler wird gemeldet statt verschwiegen.
"""
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
WACHE = os.path.join(HIER, "memory-verlust-wache.py")


def laden():
    spec = importlib.util.spec_from_file_location("memory_verlust_wache", WACHE)
    m = importlib.util.module_from_spec(spec)
    sys.modules["memory_verlust_wache"] = m
    spec.loader.exec_module(m)
    return m


w = laden()


class WachenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "state.db")
        self.mem = os.path.join(self.tmp.name, "MEMORY.md")
        self.merker = os.path.join(self.tmp.name, "merker.json")
        con = sqlite3.connect(self.db)
        con.execute("create table messages (timestamp real, session_id text, "
                    "tool_name text, content text)")
        self.con = con
        self.schreibe_memory("BLEIBT: ein Eintrag, der da ist.")

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def schreibe_memory(self, text):
        with open(self.mem, "w", encoding="utf-8") as f:
            f.write(text)

    def verlust(self, text, ts=1000.0, feld="replaced_entries"):
        self.con.execute("insert into messages values (?,?,?,?)",
                         (ts, "sitzung1", "memory", json.dumps({feld: {"1": text}})))
        self.con.commit()

    def lauf(self, **kw):
        return w.lauf(db=self.db, memory=self.mem, merkerpfad=self.merker, **kw)

    def test_erster_lauf_schweigt_und_setzt_merkdatei(self):
        self.verlust("ALTER EINTRAG: der ist schon weg.")
        self.assertEqual("", self.lauf())
        self.assertTrue(os.path.exists(self.merker))
        d = json.load(open(self.merker, encoding="utf-8"))
        self.assertEqual(1, len(d["bekannt"]))

    def test_neuer_verlust_wird_gemeldet_und_nur_einmal(self):
        self.verlust("ALTER EINTRAG: der ist schon weg.", ts=1000.0)
        self.lauf()                                    # Baseline
        self.verlust("NEUER EINTRAG: gerade verloren.", ts=2000.0)
        text = self.lauf()
        self.assertIn("NEUER EINTRAG", text)
        self.assertIn("1 neue", text)
        self.assertNotIn("ALTER EINTRAG", text)        # Altfall wird nicht wiederholt
        self.assertEqual("", self.lauf())              # dritter Lauf: nichts Neues

    def test_altfall_wird_nicht_erneut_gemeldet(self):
        self.verlust("ALTER EINTRAG: der ist schon weg.")
        self.lauf()
        self.assertEqual("", self.lauf())

    def test_absichtliche_entfernung_wird_mitgemeldet(self):
        # Eine Entfernung ist belegt (removed_entries) - die Wache soll sie zeigen.
        self.verlust("ENTFERNT: per remove geloescht.", feld="removed_entries")
        self.lauf()
        self.verlust("NEU ENTFERNT: zweiter Fall.", ts=2000.0, feld="removed_entries")
        text = self.lauf()
        self.assertIn("removed_entries", text)

    def test_messfehler_wird_gemeldet_statt_verschwiegen(self):
        text = w.lauf(db=os.path.join(self.tmp.name, "gibtsnicht.db"),
                      memory=self.mem, merkerpfad=self.merker)
        self.assertIn("FEHLER", text)

    def test_neu_baseline_setzt_merkdatei_zurueck(self):
        self.verlust("ALTER EINTRAG: der ist schon weg.")
        self.lauf()
        self.verlust("ZWEITER: auch weg.", ts=2000.0)
        self.assertIn("ZWEITER", self.lauf())
        text = self.lauf(neu_baseline=True)
        self.assertIn("neu gesetzt", text)
        self.assertEqual("", self.lauf())

    def test_meldung_kuerzt_lange_eintraege_und_zaehlt_den_rest(self):
        for i in range(7):
            self.verlust("LANG %d: %s" % (i, "x" * 300), ts=1000.0 + i)
        self.lauf()
        for i in range(7, 9):
            self.verlust("NEU %d: %s" % (i, "y" * 300), ts=2000.0 + i)
        text = self.lauf()
        self.assertIn("2 neue", text)
        self.assertIn("...", text)                     # gekuerzt


if __name__ == "__main__":
    unittest.main()