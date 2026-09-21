"""Tests fuer die Sendestelle (melder.py) - Telegram-HTML entschaerfen.

ANLASS (21.09.2026, gemessen): Der Wochenbericht enthaelt den Satz
"n=<Zahl> heisst: zu wenige Runden". Telegram liest mit parse_mode=HTML ein
"<Zahl>" als Marke und weist die GANZE Nachricht ab:

    400 Bad Request: can't parse entities: Unsupported start tag "zahl"

Der Bericht kam deshalb nie an. Dieselbe Falle lauerte in jedem Traceback im
Bericht (<module>, <lambda>) und in jeder Fehlermeldung eines fremden
Programms. Darum wird an der Sendestelle entschaerft, nicht in jedem Bericht.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

HANDEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HANDEL))

import melder                                                       # noqa: E402


class Entschaerfen(unittest.TestCase):
    def test_unbekannte_marke_wird_entschaerft(self):
        self.assertEqual(melder._entschaerfe("n=<Zahl> heisst: zu wenige Runden"),
                         "n=&lt;Zahl&gt; heisst: zu wenige Runden")

    def test_erlaubte_marken_bleiben(self):
        roh = "<b>Fett</b> <i>kursiv</i> <code>x</code> <pre>y</pre>"
        self.assertEqual(melder._entschaerfe(roh), roh)

    def test_traceback_wird_entschaerft(self):
        roh = '<pre>File "<stdin>", line 1, in <module></pre>'
        self.assertEqual(melder._entschaerfe(roh),
                         '<pre>File "&lt;stdin&gt;", line 1, in &lt;module&gt;</pre>')

    def test_nacktes_und_wird_entschaerft(self):
        self.assertEqual(melder._entschaerfe("Stop 5% & Ziel 8%"), "Stop 5% &amp; Ziel 8%")

    def test_gueltige_entitaet_bleibt(self):
        # Ein bereits entschaerfter Text darf NICHT doppelt entschaerft werden,
        # sonst stuende "&amp;amp;" in der Nachricht.
        for roh in ("&amp;", "&lt;", "&#39;", "&#x27;"):
            self.assertEqual(melder._entschaerfe(roh), roh)

    def test_anker_mit_ziel_bleibt(self):
        roh = '<a href="https://example.org/a?b=1&amp;c=2">Text</a>'
        self.assertEqual(melder._entschaerfe(roh), roh)

    def test_idempotent(self):
        roh = "n=<Zahl> a & b"
        einmal = melder._entschaerfe(roh)
        self.assertEqual(melder._entschaerfe(einmal), einmal)

    def test_stuecke_bleiben_unter_der_grenze(self):
        lang = "\n".join("Zeile %d mit etwas Text" % i for i in range(500))
        for s in melder._stuecke(lang):
            self.assertLessEqual(len(s), melder.MAX_ZEICHEN)

    def test_kurzer_text_bleibt_ein_stueck(self):
        self.assertEqual(melder._stuecke("kurz"), ["kurz"])

    def test_keine_zeile_geht_verloren(self):
        lang = "\n".join("Zeile %d" % i for i in range(900))
        zurueck = "\n".join(melder._stuecke(lang))
        for i in (0, 450, 899):
            self.assertIn("Zeile %d" % i, zurueck)


class UeberlangeZeile(unittest.TestCase):
    """Eine EINZELNE Zeile ueber der Grenze.

    GEMESSEN 21.09.2026: sie rutschte ungeteilt durch (4500 Zeichen bei
    MAX_ZEICHEN 4000) - Telegram schnitt den Rest ab. Der Fall entsteht durch
    einen Traceback ohne Umbruch oder eine lange Fehlerzeile eines fremden
    Programms, also genau dann, wenn die Meldung wichtig ist.
    """

    def test_einzelne_ueberlange_zeile_wird_geteilt(self):
        lang = "x" * (melder.MAX_ZEICHEN + 500)
        stuecke = melder._stuecke(lang)
        self.assertGreater(len(stuecke), 1)
        for s in stuecke:
            self.assertLessEqual(len(s), melder.MAX_ZEICHEN)

    def test_ueberlange_zeile_verliert_nichts(self):
        lang = "".join(str(i % 10) for i in range(melder.MAX_ZEICHEN + 500))
        self.assertEqual("".join(melder._stuecke(lang)), lang)

    def test_ueberlange_zeile_zwischen_normalen(self):
        text = "Kopf\n" + "y" * (melder.MAX_ZEICHEN + 100) + "\nFuss"
        stuecke = melder._stuecke(text)
        for s in stuecke:
            self.assertLessEqual(len(s), melder.MAX_ZEICHEN)
        zurueck = "".join(stuecke)
        self.assertIn("Kopf", zurueck)
        self.assertIn("Fuss", zurueck)


class MarkeUeberDerGrenze(unittest.TestCase):
    """Eine Marke, die ueber die Stueckgrenze reicht.

    GEMESSEN 21.09.2026: ein <b> ueber viele Zeilen hinterliess im ersten
    Stueck ein offenes und im zweiten ein verwaistes </b>; Telegram weist
    BEIDE Nachrichten ab. Jedes Stueck muss fuer sich gueltig sein.
    """

    @staticmethod
    def _bilanz(s, marke="b"):
        auf = len(re.findall(r"<%s(?:\s[^<>]*)?>" % marke, s))
        return auf, s.count("</%s>" % marke)

    def test_jedes_stueck_ist_fuer_sich_geschlossen(self):
        text = ("<b>Kopf\n" + "\n".join("Zeile %d" % i for i in range(700))
                + "\nFuss</b>")
        stuecke = melder._stuecke(text)
        self.assertGreater(len(stuecke), 1)
        for s in stuecke:
            auf, zu = self._bilanz(s)
            self.assertEqual(auf, zu, "offene Marke in einem Stueck: %r" % s[:60])

    def test_text_bleibt_erhalten(self):
        text = ("<b>Kopf\n" + "\n".join("Zeile %d" % i for i in range(700))
                + "\nFuss</b>")
        ohne = re.sub(r"</?b>", "", "".join(melder._stuecke(text)))
        for stelle in ("Kopf", "Zeile 350", "Fuss"):
            self.assertIn(stelle, ohne)

    def test_zwei_verschachtelte_marken(self):
        text = ("<b><i>Kopf\n" + "\n".join("Z %d" % i for i in range(900))
                + "\nFuss</i></b>")
        for s in melder._stuecke(text):
            for marke in ("b", "i"):
                auf, zu = self._bilanz(s, marke)
                self.assertEqual(auf, zu, "Marke %s unausgeglichen" % marke)

    def test_marke_mit_ziel_ueberlebt_die_trennung(self):
        text = ('<a href="https://example.invalid">Anfang\n'
                + "\n".join("Z %d" % i for i in range(800)) + "\nEnde</a>")
        for s in melder._stuecke(text):
            auf = len(re.findall(r"<a(?:\s[^<>]*)?>", s))
            self.assertEqual(auf, s.count("</a>"))


class EchterTagesbericht(unittest.TestCase):
    """Der laengste Text, den der Betrieb wirklich sendet.

    Der Tagesbericht laeuft ueber die Grenze (gemessen 9.125 Zeichen, drei
    Stuecke) - er ist damit der einzige Text, bei dem Trennung UND
    Entschaerfung zusammen wirken muessen.
    """

    @classmethod
    def setUpClass(cls):
        import tagesbericht
        cls.text = melder._entschaerfe(tagesbericht.baue())

    def test_jedes_stueck_ist_gueltiges_telegram_html(self):
        stuecke = melder._stuecke(self.text)
        for s in stuecke:
            self.assertLessEqual(len(s), melder.MAX_ZEICHEN)
            rest = re.sub(r"</?(?:b|i|u|s|code|pre|a)(?:\s[^<>]*)?>", "", s)
            self.assertNotIn("<", rest)
            self.assertNotIn(">", rest)
            auf = len(re.findall(r"<b(?:\s[^<>]*)?>", s))
            self.assertEqual(auf, s.count("</b>"))


class EchterWochenbericht(unittest.TestCase):
    """Der Bericht, an dem es aufgefallen ist - gegen die echte Vorlage."""

    def test_wochenbericht_ist_nach_dem_entschaerfen_gueltig(self):
        import wochenbericht

        roh = wochenbericht.baue()
        entschaerft = melder._entschaerfe(roh)
        rest = re.sub(r"</?(?:b|i|u|s|code|pre|a)(?:\s[^<>]*)?>", "", entschaerft)
        self.assertNotIn("<", rest, "rohe Marken bleiben - Telegram weist die Nachricht ab")
        self.assertNotIn(">", rest)
        self.assertEqual(entschaerft.count("<"), entschaerft.count(">"))


if __name__ == "__main__":
    unittest.main()
