"""Tests fuer scripts/memory-verlust.py - Regel statt Zustand.

Gebaut wird eine eigene state.db und ein eigenes MEMORY.md im Temp-Ordner;
geprueft wird, dass belegte Verluste erkannt, umgeschriebene Fassungen NICHT
als Verlust gemeldet und absichtliche Entfernungen getrennt gezaehlt werden.
"""
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
MODULPFAD = os.path.join(HIER, "memory-verlust.py")


def laden():
    spec = importlib.util.spec_from_file_location("memory_verlust", MODULPFAD)
    m = importlib.util.module_from_spec(spec)
    sys.modules["memory_verlust"] = m
    spec.loader.exec_module(m)
    return m


mv = laden()


class VerlustTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "state.db")
        self.mem = os.path.join(self.tmp.name, "MEMORY.md")
        con = sqlite3.connect(self.db)
        con.execute("create table messages (timestamp real, session_id text, "
                    "tool_name text, content text)")
        self.con = con

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def schreibe_memory(self, text):
        open(self.mem, "w", encoding="utf-8").write(text)

    def schreibe_ergebnis(self, feld, eintraege, ts=1000.0):
        self.con.execute("insert into messages values (?,?,?,?)",
                         (ts, "sitzung1", "memory",
                          json.dumps({feld: {str(i + 1): t for i, t in enumerate(eintraege)}})))
        self.con.commit()

    def test_verlorener_eintrag_wird_gemeldet(self):
        self.schreibe_memory("BLEIBT: irgendwas.\n§\nANDERES: auch da.")
        self.schreibe_ergebnis("replaced_entries", ["VERLOREN: dieser Eintrag ist weg."])
        raus = mv.verluste(self.db, self.mem)
        self.assertEqual(1, len(raus))
        self.assertIn("VERLOREN", raus[0]["text"])

    def test_umgeschriebene_fassung_gilt_nicht_als_verlust(self):
        # Der Anfang (die ersten 70 Zeichen) steht weiter im Gedaechtnis
        # -> nur umformuliert, kein Verlust.
        kopf = "KRAKEN FUTURES (24./25.09.2026, gebaut, live bewiesen, gemessen): Eigener Dienst "
        self.assertGreater(len(kopf), 70)
        self.schreibe_memory(kopf + "in NEUER Fassung, laenger und anders formuliert.")
        self.schreibe_ergebnis("replaced_entries", [kopf + "in ALTER Fassung."])
        self.assertEqual([], mv.verluste(self.db, self.mem))

    def test_anderer_eintrag_mit_gleichem_wortlaut_rest_gilt_als_verlust(self):
        # Gegenprobe: gleicher Anfang, aber der Anfang steht NICHT mehr im Gedaechtnis.
        kopf = "KRAKEN FUTURES (24./25.09.2026, gebaut, live bewiesen, gemessen): Eigener Dienst "
        self.schreibe_memory("Ganz anderer Eintrag ohne diesen Anfang.")
        self.schreibe_ergebnis("replaced_entries", [kopf + "in ALTER Fassung."])
        self.assertEqual(1, len(mv.verluste(self.db, self.mem)))

    def test_wiederhergestellter_eintrag_gilt_als_vorhanden(self):
        # Mit Vermerk zurueckgeholt: der Kopf (erste 5 Woerter) steht wieder da.
        alt = "HERMES-CONFIG 30.09.2026 (Stand): config.yaml ist kommentarlos, 841 Zeilen."
        self.schreibe_memory("HERMES-CONFIG 30.09.2026 (Stand; WIEDERHERGESTELLT): "
                             "config.yaml ist kommentarlos.")
        self.schreibe_ergebnis("replaced_entries", [alt])
        self.assertEqual([], mv.verluste(self.db, self.mem))

    def test_absichtliche_entfernung_wird_getrennt_gezaehlt(self):
        self.schreibe_memory("BLEIBT: irgendwas.")
        self.schreibe_ergebnis("removed_entries", ["ABSICHTLICH: per remove geloescht."])
        raus = mv.verluste(self.db, self.mem)
        self.assertEqual(1, len(raus))
        self.assertEqual("removed_entries", raus[0]["art"])

    def test_volltext_bleibt_erhalten(self):
        lang = "HERMES-CONFIG: " + ("x" * 900)
        self.schreibe_memory("BLEIBT: irgendwas.")
        self.schreibe_ergebnis("replaced_entries", [lang])
        raus = mv.verluste(self.db, self.mem)
        self.assertEqual(lang, raus[0]["text"])

    def test_zeitstempel_wird_lesbar(self):
        self.assertEqual("1970-01-01 01:16:40", mv.zeit(1000.0))
        self.assertEqual("kaputt", mv.zeit("kaputt"))


if __name__ == "__main__":
    unittest.main()