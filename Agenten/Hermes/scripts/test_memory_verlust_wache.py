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
import time
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
        # Die Queue liegt IMMER im Temp-Ordner: sonst haengt die Suite am echten
        # pending/memory/ und ein echter Befund faerbt die Altfaelle-Tests rot.
        self.queue = os.path.join(self.tmp.name, "queue")
        os.makedirs(self.queue, exist_ok=True)
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
        kw.setdefault("queue_ordner", self.queue)
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
                      memory=self.mem, merkerpfad=self.merker, queue_ordner=self.queue)
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


class QueueTest(unittest.TestCase):
    """Zweite Messung der Wache: die Vorschlags-Queue `pending/memory/`.

    Geprueft wird die REGEL, nicht ein Tageszustand: eine frische, gepinnte Queue ist
    kein Befund; ungepinnt, verrottet oder unlesbar wird genau EINMAL gemeldet; eine
    wachsende Queue meldet nicht erneut; die Erholung wird einmal genannt.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "state.db")
        self.mem = os.path.join(self.tmp.name, "MEMORY.md")
        self.merker = os.path.join(self.tmp.name, "merker.json")
        self.queue = os.path.join(self.tmp.name, "queue")
        os.makedirs(self.queue)
        con = sqlite3.connect(self.db)
        con.execute("create table messages (timestamp real, session_id text, "
                    "tool_name text, content text)")
        self.con = con
        with open(self.mem, "w", encoding="utf-8") as f:
            f.write("BLEIBT: ein Eintrag, der da ist.")

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def vorschlag(self, vid, tage_alt=0.0, op="replace", gepinnt=False, unlesbar=False):
        pfad = os.path.join(self.queue, vid + ".json")
        with open(pfad, "w", encoding="utf-8") as f:
            if unlesbar:
                f.write("{ das ist kein JSON")
                return
            o = {"action": op, "content": "NEUER TEXT", "old_text": "ALTER TEXT"}
            if op in ("replace", "remove") and gepinnt:
                o["matched_entry"] = "ALTER TEXT vollstaendig"
            payload = ({"action": "batch", "target": "memory", "operations": [o]}
                       if op == "batch" else dict(o, target="memory"))
            json.dump({"id": vid, "subsystem": "memory", "action": op,
                       "created_at": 1000000.0 - tage_alt * 86400.0,
                       "payload": payload}, f)

    def lauf(self, **kw):
        kw.setdefault("queue_ordner", self.queue)
        return w.lauf(db=self.db, memory=self.mem, merkerpfad=self.merker, **kw)

    def test_leere_queue_ist_kein_befund(self):
        self.lauf()                                    # Baseline
        self.assertEqual("", self.lauf())

    def test_frischer_gepinnter_vorschlag_ist_kein_befund(self):
        self.lauf()
        self.vorschlag("frisch", tage_alt=0.5, gepinnt=True)
        self.assertEqual("", self.lauf())

    def test_ungepinnter_vorschlag_wird_genau_einmal_gemeldet(self):
        self.lauf()
        self.vorschlag("alt1", tage_alt=1.0, gepinnt=False)
        text = self.lauf()
        self.assertIn("ohne Pin", text)
        self.assertIn("alt1", text)
        self.assertEqual("", self.lauf())              # nicht wiederholt

    def test_verrottete_queue_wird_gemeldet(self):
        self.lauf()
        self.vorschlag("alt2", tage_alt=8.0, gepinnt=True)
        text = self.lauf()
        self.assertIn("verrottet", text)
        self.assertIn("8 Tage", text)

    def test_wachsende_queue_meldet_nicht_erneut(self):
        # Der Schluessel traegt keine Zahl: ein noch aelterer Stand ist DIESELBE Meldung.
        self.lauf()
        self.vorschlag("alt3", tage_alt=8.0, gepinnt=True)
        self.assertIn("verrottet", self.lauf())
        self.vorschlag("alt4", tage_alt=30.0, gepinnt=True)
        self.assertEqual("", self.lauf())

    def test_unlesbare_datei_ist_ein_befund(self):
        self.lauf()
        self.vorschlag("kaputt", unlesbar=True)
        text = self.lauf()
        self.assertIn("nicht lesbar", text)
        self.assertIn("kaputt", text)

    def test_erholung_wird_einmal_gemeldet(self):
        self.lauf()
        self.vorschlag("alt5", tage_alt=9.0, gepinnt=False)
        self.assertIn("ohne Pin", self.lauf())
        for name in os.listdir(self.queue):
            os.remove(os.path.join(self.queue, name))
        text = self.lauf()
        self.assertIn("keine Befunde mehr", text)
        self.assertIn("ungepinnt", text)
        self.assertEqual("", self.lauf())

    def test_erster_lauf_schweigt_auch_bei_kaputter_queue(self):
        # Baseline schluckt bewusst auch einen bestehenden Befund (wie bei den Verlusten).
        self.vorschlag("alt6", tage_alt=20.0, gepinnt=False)
        self.assertEqual("", self.lauf())
        d = json.load(open(self.merker, encoding="utf-8"))
        self.assertEqual(["ungepinnt", "verrottet"], sorted(d["queue"]))

    def test_queue_stand_zeigt_zahlen_ohne_merkdatei(self):
        self.vorschlag("alt7", tage_alt=10.0, gepinnt=False)
        text = w.queue_stand(self.queue)
        self.assertIn("Vorschlaege: 1", text)
        self.assertIn("ohne Pin: 1", text)
        self.assertIn("alt7", text)
        self.assertFalse(os.path.exists(self.merker))   # Handbetrieb schreibt nichts

    def test_batch_mit_gepinntem_replace_ist_kein_befund(self):
        self.lauf()
        self.vorschlag("batch1", tage_alt=1.0, op="batch", gepinnt=True)
        self.assertEqual("", self.lauf())


if __name__ == "__main__":
    unittest.main()