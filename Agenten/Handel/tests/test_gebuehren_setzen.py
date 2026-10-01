"""Tests fuer Agenten/Handel/gebuehren_setzen.py (netzfrei, ohne Schreibzugriff
auf echte Wachen).

Anlass (01.10.2026): Beim Setzen der Kraken-Gebuehr in `nautilus_kraken` stand
die `_gebuehr_quelle` schon in der Datei, der WERT (`gebuehr_taker`) fehlte
aber. `_feld_setzen` behandelte diesen Fall als "nur die Notiz auffrischen" -
der Wert fiel still unter den Tisch, und `anwenden()` stuerzte danach mit
einem irrefuehrenden `TypeError: float() argument must be ... not 'NoneType'`
ab, statt zu sagen, was los ist. Beide Seiten sind hier festgenagelt: der
Schreibweg setzt den Wert, und die Pruefung meldet es im Klartext.

Regel des Hauses: die Tests rechnen auf TEXT und auf einem Temp-Ordner. Ein
Waechter (setUpModule/tearDownModule) vergleicht alle echten `wachen*.json`
der Handelsspuren vorher und nachher - faellt ein Test, der nach draussen
schreibt.
"""

import importlib.util
import json
import os
import pathlib
import shutil
import tempfile
import unittest

HIER = pathlib.Path(__file__).resolve().parent
HANDEL = HIER.parent

spec = importlib.util.spec_from_file_location("gebuehren_setzen",
                                              HANDEL / "gebuehren_setzen.py")
gs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gs)


def _stand():
    """Groesse + mtime jeder echten Wachen-Datei der Handelsspuren."""
    aus = {}
    for p in sorted(HANDEL.glob("*/wachen*.json")):
        if ".bak-" in p.name:
            continue
        st = p.stat()
        aus[str(p.relative_to(HANDEL))] = (st.st_size, int(st.st_mtime))
    return aus


_VORHER = None


def setUpModule():
    global _VORHER
    _VORHER = _stand()


def tearDownModule():
    nachher = _stand()
    if nachher != _VORHER:
        neu = {k: v for k, v in nachher.items() if _VORHER.get(k) != v}
        raise AssertionError("Test hat in echte Wachen geschrieben: %s" % neu)


class FeldSetzenTest(unittest.TestCase):
    """Der Schreibweg auf TEXT - kein Dateizugriff."""

    def test_notiz_da_wert_fehlt_setzt_den_wert(self):
        """Der gefundene Fehler: Notiz ohne Wert."""
        roh = ('{\n  "gebuehr_pct": 0.6,\n'
               '  "_gebuehr_quelle": "alte Notiz",\n'
               '  "handel_erlaubt": false\n}\n')
        neu, alt = gs._feld_setzen(roh, "gebuehr_taker", 0.006, "neue Quelle")
        d = json.loads(neu)
        self.assertIsNone(alt)
        self.assertEqual(d["gebuehr_taker"], 0.006)
        self.assertEqual(d["_gebuehr_quelle"], "neue Quelle")
        self.assertEqual(d["gebuehr_pct"], 0.6, "Nachbarfeld darf nicht wandern")
        self.assertEqual(d["handel_erlaubt"], False)

    def test_notiz_ist_letzter_schluessel_ohne_komma(self):
        roh = '{\n  "a": 1,\n  "_gebuehr_quelle": "alt"\n}\n'
        neu, _ = gs._feld_setzen(roh, "gebuehr_taker", 0.001, "q")
        d = json.loads(neu)
        self.assertEqual(d["gebuehr_taker"], 0.001)
        self.assertEqual(d["_gebuehr_quelle"], "q")
        self.assertEqual(d["a"], 1)

    def test_wert_da_notiz_fehlt(self):
        roh = '{\n  "gebuehr_taker": 0.0005,\n  "a": 1\n}\n'
        neu, alt = gs._feld_setzen(roh, "gebuehr_taker", 0.001, "q")
        d = json.loads(neu)
        self.assertEqual(alt, "0.0005")
        self.assertEqual(d["gebuehr_taker"], 0.001)
        self.assertEqual(d["_gebuehr_quelle"], "q")

    def test_keiner_von_beiden_steht_drin(self):
        roh = '{\n  "a": 1,\n  "b": 2\n}\n'
        neu, alt = gs._feld_setzen(roh, "gebuehr_taker", 0.001, "q")
        d = json.loads(neu)
        self.assertIsNone(alt)
        self.assertEqual(d["gebuehr_taker"], 0.001)
        self.assertEqual(d["_gebuehr_quelle"], "q")
        self.assertEqual(d["b"], 2)

    def test_keine_doppelten_schluessel(self):
        """Ein zweiter _gebuehr_quelle-Schluessel waere wirkungslos (der letzte
        gewinnt) und wuerde die Datei widerspruechlich machen."""
        for roh in ('{\n  "_gebuehr_quelle": "alt",\n  "a": 1\n}\n',
                    '{\n  "gebuehr_taker": 0.001,\n  "a": 1\n}\n',
                    '{\n  "a": 1\n}\n'):
            neu, _ = gs._feld_setzen(roh, "gebuehr_taker", 0.002, "q")
            self.assertEqual(neu.count('"_gebuehr_quelle"'), 1, roh)
            self.assertEqual(neu.count('"gebuehr_taker"'), 1, roh)

    def test_zeilenende_bleibt(self):
        """Die Wachen sind LF-Dateien - der Ersatz darf keine CRLF einfuehren."""
        roh = '{\n  "a": 1\n}\n'
        neu, _ = gs._feld_setzen(roh, "gebuehr_taker", 0.001, "q")
        self.assertEqual(neu.count("\r\n"), 0)


class AnwendenMeldetKlarTest(unittest.TestCase):
    """`anwenden()` darf bei einem misslungenen Schreibvorgang nicht mit
    einem TypeError aus dem Vergleich fallen, sondern muss den Grund nennen."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="gebuehren_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "spur").mkdir()
        (self.tmp / "spur" / "wachen.json").write_text(
            '{\n  "gebuehr_taker": 0.001\n}\n', encoding="utf-8")
        self.alt_hier, self.alt_tab = gs.HIER, gs.AENDERUNGEN
        gs.HIER = str(self.tmp)
        gs.AENDERUNGEN = [("spur/wachen.json", "gebuehr_taker", 0.002, "q")]
        self.addCleanup(self._zurueck)

    def _zurueck(self):
        gs.HIER, gs.AENDERUNGEN = self.alt_hier, self.alt_tab

    def test_erfolgsfall_schreibt_und_meldet(self):
        self.assertEqual(gs.anwenden(), 1)
        d = json.loads((self.tmp / "spur" / "wachen.json").read_text("utf-8"))
        self.assertEqual(d["gebuehr_taker"], 0.002)
        self.assertTrue((self.tmp / "spur" / "wachen.json.bak-20261001").exists()
                        or list(self.tmp.glob("spur/*.bak-*")),
                        "Sicherung muss daneben liegen")

    def test_misslungener_ersatz_nennt_den_grund(self):
        """Der Ersatz wird auf 'nichts geaendert' gestellt - der Fehler muss
        das Feld und den erwarteten Wert nennen, nicht 'NoneType'.

        WICHTIG: `mock.patch.object` statt einer Zuweisung - eine Zuweisung
        ohne Ruecknahme hat in diesem Modul schon einmal alle folgenden Tests
        still auf eine Attrappe umgestellt (der Ersatz blieb stehen).
        """
        from unittest import mock
        with mock.patch.object(gs, "_feld_setzen",
                               lambda roh, feld, wert, quelle: (roh, None)):
            with self.assertRaises(RuntimeError) as ctx:
                gs.anwenden()
        text = str(ctx.exception)
        self.assertIn("gebuehr_taker", text)
        self.assertIn("liess sich nicht setzen", text)
        self.assertNotIn("NoneType", text)


class TabelleTest(unittest.TestCase):
    """Die Tabelle selbst - sie ist die Wahrheit ueber die gesetzten Saetze."""

    def test_jede_zeile_hat_datei_wert_und_quelle(self):
        for datei, feld, wert, quelle in gs.AENDERUNGEN:
            self.assertTrue((HANDEL / datei).exists(), datei)
            self.assertIn(feld, ("gebuehr_taker", "gebuehr_pct"), datei)
            self.assertIsInstance(wert, float, datei)
            self.assertGreater(wert, 0, datei)
            self.assertTrue(str(quelle).strip(), datei)

    def test_gebuehr_taker_ist_ein_bruch_nicht_prozent(self):
        """Die Verwechslung, die am 01.10.2026 fast entstanden waere: 0.6
        (Prozent) statt 0.006 (Bruch) - das waere die 100-fache Gebuehr."""
        for datei, feld, wert, _q in gs.AENDERUNGEN:
            if feld != "gebuehr_taker":
                continue
            self.assertLess(wert, 0.1, "%s: %r sieht nach Prozent aus" % (datei, wert))

    def test_dieselbe_spur_nicht_zweimal_mit_verschiedenen_werten(self):
        gesehen = {}
        for datei, feld, wert, _q in gs.AENDERUNGEN:
            key = (datei, feld)
            if key in gesehen:
                self.assertEqual(gesehen[key], wert,
                                 "%s %s doppelt mit zwei Werten" % key)
            gesehen[key] = wert

    def test_jede_gesetzte_wachen_traegt_ihre_quelle(self):
        """Wert ohne Quelle ist nicht nachpruefbar - das Haus fuehrt beides."""
        for datei, feld, wert, _q in gs.AENDERUNGEN:
            w = json.loads((HANDEL / datei).read_text("utf-8"))
            self.assertEqual(float(w.get(feld)), float(wert), datei)
            self.assertTrue(str(w.get("_gebuehr_quelle") or "").strip(),
                            "%s: %s ohne _gebuehr_quelle" % (datei, feld))


if __name__ == "__main__":
    unittest.main()