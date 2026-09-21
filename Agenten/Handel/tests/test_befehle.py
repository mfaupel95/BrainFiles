"""Tests fuer befehle.py - die einheitlichen Handelsbefehle beider Bots.

Was hier gehaelt wird
---------------------
1. Die Spurliste wird NICHT abgeschrieben: `spuren()` muss genau die
   Schluessel von `dauerlauf.SPUREN` liefern. Das ist der Test gegen die
   stille Alterung - eine zweite Liste faellt hier auf, nicht erst beim
   naechsten neuen Spurordner.
2. Jede Spur hat eine Strategie-Familie UND eine Lesefunktion im Bericht.
   Fehlt eine, meldet das der Test (nicht die Ausgabe).
3. Das Modul ist rein lesend (AST-Pruefung) - es laeuft im SkillsBot neben
   dem Dauerlauf, ein zweiter Schreiber waere ein zweites Buch.
4. Die Rechenfunktionen fuer /markt rechnen richtig (synthetische Kerzen,
   kein Netz).
5. Die Zeithelfer lesen das echte Log-Format ("15.09. 20:02:47", lokal, ohne
   Jahr) - daran ist schon einmal eine Zeile gescheitert.
"""
import ast
import datetime as dt
import os
import sys
import tempfile
import unittest
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import befehle                                                # noqa: E402
import dauerlauf                                              # noqa: E402
import spuren_stand                                           # noqa: E402


class SpurenTest(unittest.TestCase):
    def test_spurliste_ist_dauerlauf_spuren(self):
        self.assertEqual(befehle.spuren(), list(dauerlauf.SPUREN))

    def test_jede_spur_hat_familie_und_leser(self):
        fehlende_familie = [s for s in befehle.spuren()
                            if befehle.familie(s) == "?"]
        fehlende_leser = [s for s in befehle.spuren()
                          if befehle._holer_fuer(s) is None]
        self.assertEqual(fehlende_familie, [])
        self.assertEqual(fehlende_leser, [])

    def test_indikatorspuren_sind_bekannt(self):
        for spur in befehle.INDIKATOREN:
            self.assertIn(spur, befehle.spuren())
            self.assertEqual(befehle.familie(spur), "Indikator")


class ReinLesendTest(unittest.TestCase):
    """Ein Leser, der schreibt, ist im zweiten Prozess ein zweiter Schreiber."""

    def test_quelle_oeffnet_nichts_zum_schreiben(self):
        with open(os.path.join(HANDEL, "befehle.py"), encoding="utf-8") as f:
            baum = ast.parse(f.read())
        verboten = []
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Call):
                name = getattr(knoten.func, "id", None) or getattr(
                    knoten.func, "attr", None)
                if name in ("dump", "write", "writer", "remove", "rename",
                            "replace", "system", "run", "Popen"):
                    verboten.append(name)
                if name == "open" and len(knoten.args) > 1:
                    modus = getattr(knoten.args[1], "value", "")
                    if isinstance(modus, str) and (
                            "w" in modus or "a" in modus or "+" in modus):
                        verboten.append("open(%s)" % modus)
            if isinstance(knoten, (ast.Import, ast.ImportFrom)):
                namen = [a.name for a in knoten.names]
                if "subprocess" in namen:
                    verboten.append("import subprocess")
        self.assertEqual(verboten, [])

    def test_lesen_aendert_keine_spurdatei(self):
        vorher = {}
        for spur in befehle.spuren():
            for datei in ("zustand.json", "handelsjournal.csv"):
                pfad = os.path.join(HANDEL, spur, datei)
                if os.path.exists(pfad):
                    vorher[pfad] = os.stat(pfad).st_mtime_ns
        self.assertTrue(vorher, "keine Spurdatei gefunden - Test blind")
        befehle.strategien()
        befehle.indikatoren()
        for pfad, mtime in vorher.items():
            self.assertEqual(os.stat(pfad).st_mtime_ns, mtime,
                             "%s wurde von einem Befehl angefasst" % pfad)


class TextTest(unittest.TestCase):
    def test_klartext_entfernt_nur_fett(self):
        self.assertEqual(befehle.klartext("<b>Handel</b> 20:00"),
                         "Handel 20:00")

    def test_hilfe_ist_gruppiert_und_html(self):
        text = befehle.hilfe()
        for wort in ("/lage", "/bericht", "/spur NAME", "/strategien",
                     "/indikatoren", "/markt", "/freigabe_xperp"):
            self.assertIn(wort, text)

    def test_unbekannte_spur_nennt_die_bekannten(self):
        text = befehle.spur("quatsch")
        self.assertIn("Unbekannte Spur", text)
        self.assertIn("xperp", text)

    def test_leerer_spurname_ist_kein_traceback(self):
        self.assertIn("Unbekannte Spur", befehle.spur(""))

    def test_strategien_nennt_jede_spur(self):
        text = befehle.strategien()
        fehlend = [s for s in befehle.spuren() if s not in text]
        self.assertEqual(fehlend, [])
        self.assertIn("Befund, keine Messung", text)


class ZeitTest(unittest.TestCase):
    def test_takt_aus_der_startzeile(self):
        with tempfile.TemporaryDirectory() as t:
            pfad = os.path.join(t, "dauerlauf.log")
            with open(pfad, "w", encoding="utf-8") as f:
                f.write("15.09. 19:59:54  Dauerlauf startet, Takt 15 min\n")
                f.write("15.09. 20:00:21  xperp (papier) ok\n")
            alt = befehle.DAUERLAUF_LOG
            befehle.DAUERLAUF_LOG = pfad
            try:
                self.assertEqual(befehle._takt_minuten(), 15)
            finally:
                befehle.DAUERLAUF_LOG = alt

    def test_logalter_liest_die_letzte_zeile(self):
        with tempfile.TemporaryDirectory() as t:
            pfad = os.path.join(t, "dauerlauf.log")
            jetzt = dt.datetime.now()
            with open(pfad, "w", encoding="utf-8") as f:
                f.write("15.09. 08:00:00  Dauerlauf startet, Takt 15 min\n")
                f.write("%s  kraken (papier) ok\n"
                        % jetzt.strftime("%d.%m. %H:%M:%S"))
            alt = befehle.DAUERLAUF_LOG
            befehle.DAUERLAUF_LOG = pfad
            try:
                alter = befehle._log_alter()
            finally:
                befehle.DAUERLAUF_LOG = alt
        self.assertIsNotNone(alter)
        self.assertLess(alter, 2.0)

    def test_fehlendes_log_ist_kein_fehler(self):
        alt = befehle.DAUERLAUF_LOG
        befehle.DAUERLAUF_LOG = os.path.join(HANDEL, "gibt-es-nicht.log")
        try:
            self.assertIsNone(befehle._log_alter())
            self.assertIsNone(befehl_minuten := befehle._takt_minuten())
        finally:
            befehle.DAUERLAUF_LOG = alt


class MarktTest(unittest.TestCase):
    """Nur die Rechnung - die Abrufe stehen in markt()."""

    def _kerzen(self, schluesse):
        return [[i, c, c + 1, c - 1, c, 1.0] for i, c in enumerate(schluesse)]

    def test_atr_ist_mittlere_spanne(self):
        # 15 Kerzen mit Range 2 (= hoch-tief) und gleichem Schluss -> ATR 2.
        kerzen = [[i, 10, 11, 9, 10, 1] for i in range(15)]
        self.assertAlmostEqual(befehle._atr(kerzen, 14), 2.0)

    def test_atr_ohne_genug_kerzen_ist_none(self):
        self.assertIsNone(befehle._atr(self._kerzen([1, 2, 3]), 14))

    def test_sma_nimmt_die_letzten(self):
        self.assertAlmostEqual(befehle._sma([1, 2, 3, 4], 2), 3.5)
        self.assertIsNone(befehle._sma([1, 2], 5))

    def test_kursformat(self):
        self.assertEqual(befehle._kurs_text(77081.8), "77082")
        self.assertEqual(befehle._kurs_text(99.58), "99.58")
        self.assertEqual(befehle._kurs_text(None), "?")


class LageTest(unittest.TestCase):
    def test_lage_zeigt_kopf_spuren_und_summe(self):
        text = befehle.klartext(befehle.lage())
        self.assertIn("Handel Lage", text)
        self.assertIn("offene Position(en) insgesamt", text)
        fehlend = [s for s in befehle.spuren() if s not in text]
        self.assertEqual(fehlend, [])


class LiveTest(unittest.TestCase):
    """Der /live-Befehl: nur Spuren, die echtes Geld bewegen KOENNEN.

    Der Fehler, gegen den diese Tests stehen: `handel_erlaubt=true` steht seit
    dem 21.09.2026 in JEDER wachen.json - auch in den 22 Spuren ohne Orderaufruf.
    Eine Anzeige, die den Schalter allein liest, behauptet 29 handelnde Spuren.
    """

    def test_live_trennt_orderweg_von_schalter(self):
        text = befehle.klartext(befehle.live())
        self.assertIn("Live-Stand", text)
        self.assertIn("Eigener Orderweg", text)
        self.assertIn("OHNE Orderweg", text)
        # Die Spuren mit Haus-Orderweg muessen namentlich drinstehen.
        for spur in ("xperp", "scanner", "kraken", "mosaic"):
            self.assertIn(spur, text)

    def test_testdateien_zaehlen_nicht_als_orderweg(self):
        """demo_order_test.py ruft submit_order - das ist eine Anbindungsprobe."""
        import spuren_stand
        ordner = os.path.join(HANDEL, "nautilus_kraken")
        dateien, _ = spuren_stand.orderweg(Path(ordner))
        self.assertEqual([d for d in dateien if "test" in d], [])

    def test_orderweg_art_haus_gegen_fremd(self):
        import spuren_stand
        dateien, art = spuren_stand.orderweg(Path(os.path.join(HANDEL, "scanner")))
        self.assertIn("okx.py", dateien)
        self.assertEqual(art, "haus")

    def test_modus_zaehlung_liest_keine_bak_dateien(self):
        buch = befehle._positionen_je_modus("scanner")
        self.assertTrue(all(v >= 1 for v in buch.values()))


if __name__ == "__main__":
    unittest.main()
