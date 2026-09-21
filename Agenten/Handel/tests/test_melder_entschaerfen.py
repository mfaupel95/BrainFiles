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


class EchterWochenbericht(unittest.TestCase):
    """Der Bericht, an dem es aufgefallen ist - gegen die echte Vorlage."""

    def test_wochenbericht_ist_nach_dem_entschaerfen_gueltig(self):
        import re
        import wochenbericht

        roh = wochenbericht.baue()
        entschaerft = melder._entschaerfe(roh)
        rest = re.sub(r"</?(?:b|i|u|s|code|pre|a)(?:\s[^<>]*)?>", "", entschaerft)
        self.assertNotIn("<", rest, "rohe < bleiben - Telegram weist die Nachricht ab")
        self.assertNotIn(">", rest)
        self.assertEqual(entschaerft.count("<"), entschaerft.count(">"))


if __name__ == "__main__":
    unittest.main()
