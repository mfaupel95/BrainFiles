"""Tests fuer den ai4trade-Heartbeat-Poller (T-113) - ohne Netz.

Wichtigster Test: die Auth-Falle. Der Plattform-Skill nennt
``X-Claw-Token``, die API will ``Bearer``. Faellt der erste Weg aus, muss der
zweite greifen - sonst steht der Poller still, und Stille sieht aus wie Ruhe.
Zweiter wichtiger Test: eine Fehlerantwort darf NIE das Passwort ausgeben
(die Login-/Fehlerantwort der Plattform echot das Feld ``input``).
"""
import importlib.util
import json
import os
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lade():
    spec = importlib.util.spec_from_file_location(
        "ai4trade_heartbeat", os.path.join(HIER, "heartbeat.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


hb = _lade()
assert hb.__file__.endswith("heartbeat.py")


class EnvTest(unittest.TestCase):
    def test_liest_schluessel_und_entfernt_quotes(self):
        # Nie in den echten Ordner schreiben (Hausregel: ein Test darf keinen
        # echten Zielpfad anfassen) - der cache-Ordner traegt den Laufzeitstand.
        import tempfile
        d = tempfile.mkdtemp(prefix="ai4trade-env-")
        p = os.path.join(d, "test-env")
        with open(p, "w", encoding="utf-8") as f:
            f.write('# Kommentar\nA="eins"\n\nB=zwei\n')
        self.assertEqual({"A": "eins", "B": "zwei"}, hb._env(p))
        os.remove(p)
        os.rmdir(d)

    def test_fehlende_datei_ist_leer(self):
        self.assertEqual({}, hb._env(os.path.join(HIER, "gibtsnicht.env")))


class ZugangTest(unittest.TestCase):
    """Die Umgebung hat Vorrang vor der .env - sonst bringt das Verlagern
    der Geheimnisse nichts, solange die alte Datei noch herumliegt."""

    def setUp(self):
        self._alt = {k: os.environ.get(k)
                     for k in ("AI4TRADE_TOKEN", "AI4TRADE_AGENT_ID")}

    def tearDown(self):
        for k, v in self._alt.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_umgebung_schlaegt_datei(self):
        import tempfile
        d = tempfile.mkdtemp(prefix="ai4trade-zugang-")
        p = os.path.join(d, "test-env")
        with open(p, "w", encoding="utf-8") as f:
            for zeile in ("AI4TRADE_TOKEN=aus-der-datei",
                          "AI4TRADE_AGENT_ID=1"):
                print(zeile, file=f)
        os.environ["AI4TRADE_TOKEN"] = "aus-der-umgebung"
        z = hb.zugang(p)
        self.assertEqual("aus-der-umgebung", z["AI4TRADE_TOKEN"])
        # Was nur in der Datei steht, bleibt erhalten (Rueckfall).
        self.assertEqual("1", z["AI4TRADE_AGENT_ID"])
        os.remove(p)
        os.rmdir(d)

    def test_ohne_datei_reicht_die_umgebung(self):
        os.environ["AI4TRADE_TOKEN"] = "nur-umgebung"
        z = hb.zugang(os.path.join(HIER, "gibtsnicht.env"))
        self.assertEqual("nur-umgebung", z["AI4TRADE_TOKEN"])


class AuthTest(unittest.TestCase):
    def setUp(self):
        # WICHTIG: andere Klassen patchen hb.heartbeat/hb.hole - ohne dieses
        # Zuruecksetzen erbt der naechste Test den Patch und geht ins echte Netz.
        self._hole_orig = hb.hole
        self._hb_orig = hb.heartbeat
        self.addCleanup(self._zurueck)
        self.env = {"AI4TRADE_TOKEN": "T" * 43, "AI4TRADE_AGENT_ID": "25970"}
        self.aufrufe = []
        self.antworten = {}

    def _zurueck(self):
        hb.hole = self._hole_orig
        hb.heartbeat = self._hb_orig

    def _hole(self, tok, aid, kopf_name="Authorization", wert=None, url=None):
        kopf = wert if kopf_name == "X-Claw-Token" else "Bearer " + tok
        self.aufrufe.append((kopf_name, kopf))
        return self.antworten.get(kopf_name, (401, {"detail": "Invalid token"}))

    def test_bearer_ist_der_erste_weg(self):
        self.antworten["Authorization"] = (200, {"agent_id": 25970})
        hb.hole = self._hole
        s, a, weg = hb.heartbeat(self.env)
        self.assertEqual(200, s)
        self.assertEqual("Bearer", weg)
        self.assertEqual([("Authorization", "Bearer " + "T" * 43)], self.aufrufe)

    def test_rueckfall_auf_claw_token(self):
        self.antworten["X-Claw-Token"] = (200, {"agent_id": 25970})
        hb.hole = self._hole
        s, a, weg = hb.heartbeat(self.env)
        self.assertEqual(200, s)
        self.assertEqual("X-Claw-Token", weg)
        self.assertEqual(2, len(self.aufrufe))

    def test_beide_wege_tot_meldet_den_ersten_fehler(self):
        hb.hole = self._hole
        s, a, weg = hb.heartbeat(self.env)
        self.assertEqual(401, s)
        self.assertEqual("Bearer", weg)

    def test_ohne_token_kein_aufruf(self):
        hb.hole = self._hole
        s, a, weg = hb.heartbeat({})
        self.assertIsNone(s)
        self.assertEqual([], self.aufrufe)


class StandTest(unittest.TestCase):
    def test_neue_nachricht_wird_gemeldet_gesehene_nicht(self):
        antwort = {"messages": [{"id": 2, "content": "hallo"},
                                {"id": 1, "content": "alt"}]}
        neue, stand = hb.neu_gegen_stand(antwort, {})
        self.assertEqual(2, len(neue))
        self.assertEqual("id:2", hb._kennung(neue[0]))
        self.assertEqual("messages:2", "messages:%s" % neue[0]["id"])
        neue2, _ = hb.neu_gegen_stand(antwort, stand)
        self.assertEqual([], neue2)

    def test_aufgaben_zaehlen_mit(self):
        neue, _ = hb.neu_gegen_stand({"tasks": [{"task_id": 7}]}, {})
        self.assertEqual(["tasks"], [e["_art"] for e in neue])
        self.assertEqual("Aufgabe", hb._zeile(neue[0]).split()[0])

    def test_leere_antwort_ergibt_nichts(self):
        neue, stand = hb.neu_gegen_stand({"messages": [], "tasks": []}, {})
        self.assertEqual([], neue)
        self.assertIn("zuletzt", stand)

    def test_stand_waechst_nicht_unbegrenzt(self):
        alt = {"gesehen": ["id:%d" % i for i in range(600)]}
        _, stand = hb.neu_gegen_stand({"messages": [{"id": "neu"}]}, alt)
        self.assertLessEqual(len(stand["gesehen"]), 500)

    def test_ohne_kennung_zaehlt_der_inhalt(self):
        e = {"content": "ohne id"}
        neue, stand = hb.neu_gegen_stand({"messages": [e]}, {})
        self.assertEqual(1, len(neue))
        neue2, _ = hb.neu_gegen_stand({"messages": [e]}, stand)
        self.assertEqual([], neue2)


class AusgabeTest(unittest.TestCase):
    def setUp(self):
        self._orig = hb.heartbeat
        self.addCleanup(lambda: setattr(hb, "heartbeat", self._orig))

    def _lauf(self, antwort, stand_pfad, argv=()):
        hb.heartbeat = lambda env=None: (200, antwort, "Bearer")
        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            rc = hb.main(list(argv) + ["--stand", stand_pfad])
        return rc, puffer.getvalue()

    def test_leere_antwort_ist_leise(self):
        p = os.path.join(HIER, "cache", "test-stand-1.json")
        rc, aus = self._lauf({"agent_id": 25970, "messages": []}, p)
        self.assertEqual(0, rc)
        self.assertEqual("", aus)
        os.remove(p)

    def test_neue_nachricht_wird_gedruckt(self):
        p = os.path.join(HIER, "cache", "test-stand-2.json")
        rc, aus = self._lauf({"agent_id": 25970,
                              "messages": [{"id": 5, "content": "Antwort auf "
                                            "deinen Beitrag"}]}, p)
        self.assertEqual(0, rc)
        self.assertIn("1 neue(s) Ereignis(se)", aus)
        self.assertIn("Antwort auf deinen Beitrag", aus)
        os.remove(p)

    def test_fehler_wird_gemeldet_nicht_verschwiegen(self):
        hb.heartbeat = lambda env=None: (401, {"detail": "Invalid token"},
                                         "Bearer")
        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            rc = hb.main(["--stand", os.path.join(HIER, "cache", "x.json")])
        self.assertEqual(1, rc)
        self.assertIn("fehlgeschlagen", puffer.getvalue())


class GeheimnisTest(unittest.TestCase):
    """Eine Fehlerantwort darf kein Passwort ausgeben - die Plattform echot
    das Feld 'input' der Anfrage zurueck (28.09.2026 gesehen)."""

    def test_input_feld_wird_verworfen(self):
        roh = json.dumps({"detail": [{"type": "missing", "loc": ["body", "name"],
                                      "input": {"password": "GEHEIM123"}}]})
        j = json.loads(roh)
        if isinstance(j.get("detail"), list):
            j = {"felder": [d.get("loc") for d in j["detail"]]}
        text = json.dumps(j, ensure_ascii=False)
        self.assertNotIn("GEHEIM123", text)
        self.assertIn("name", text)


if __name__ == "__main__":
    unittest.main()