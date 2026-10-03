"""Freitext im SkillsBot - Frist und Meldung.

ANLASS (01.10.2026): Max schickte "Netto in den Bericht" und spaeter
"Omniquant Handel Freigabe auf kraken live" als FREITEXT. Beide Male kam nach
300,4 s die 16-Zeichen-Antwort `(Aufgabe FAILED)` (skillsbot.log). Die
Gateway-Logs derselben Stunde zeigen, dass der Hauptagent NICHT scheitert,
sondern arbeitet: 401,4 s fuer dieselbe Omniquant-Frage (07:56:34) und 1504,6 s
fuer die Rueckfrage danach (08:23:16).

Die Frist war also zu kurz, nicht der Agent kaputt - und die Meldung behauptete
das Gegenteil. Geprueft wird deshalb:
  - die Frist traegt echte Arbeit (>= 900 s) und ist dieselbe wie fuer /bot,
  - die Warteschleife benutzt SIE (nicht mehr das HTTP-Zeitlimit),
  - die Meldung sagt "laeuft noch" und "NICHT gescheitert" und nennt Minuten,
  - Freitext sagt VOR dem Warten Bescheid (Muster von /run).
"""

from __future__ import annotations

import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

BUS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUS))
import skillsbot as s                                             # noqa: E402


class FristTest(unittest.TestCase):

    def test_frist_traegt_echte_arbeit(self):
        # Gemessen: 401 s und 1504 s fuer echte Auftraege. 300 s war zu kurz.
        self.assertGreaterEqual(s.A2A_FRIST_S, 900)

    def test_gleiche_arbeit_gleiche_frist(self):
        """Freitext und /bot sind dieselbe Art Arbeit - also dieselbe Grenze."""
        self.assertGreaterEqual(s.BOT_FRIST_S, 900)

    def test_warteschleife_benutzt_die_frist_nicht_das_http_limit(self):
        quelle = Path(s.__file__).read_text(encoding="utf-8")
        rumpf = quelle.split("def _aufgabe_abholen(")[1].split("\ndef ")[0]
        self.assertIn("A2A_FRIST_S", rumpf)
        self.assertNotIn("A2A_TIMEOUT_S", rumpf)


class MeldungTest(unittest.TestCase):

    def test_meldung_sagt_dass_es_weiterlaeuft(self):
        text = s.frist_meldung()
        self.assertIn("NICHT gescheitert", text)
        self.assertIn("Minuten", text)

    def test_meldung_nennt_einen_weg_weiter(self):
        text = s.frist_meldung()
        self.assertTrue("/bot" in text or "Desktop" in text, text)

    def test_meldung_behauptet_nicht_das_gegenteil(self):
        """'(Aufgabe FAILED)' war die falsche Auskunft (16 Zeichen)."""
        text = s.frist_meldung()
        self.assertNotIn("FAILED", text)
        self.assertGreater(len(text), 100)


class VorwarnungTest(unittest.TestCase):

    def test_freitext_sagt_vor_dem_warten_bescheid(self):
        """T-288: Freitext antwortet SOFORT und laeuft im Hintergrund-Thread.

        Der Bot ist damit nicht mehr bis zu 30 Minuten blockiert: `bearbeite`
        gibt sofort "Angenommen." zurueck, schickt eine Vorwarnung und der
        Thread sendet das Ergebnis als eigene Nachricht.
        """
        gesendet = []
        gestartet = []
        original_start = threading.Thread.start

        def merke(chat, text):
            gesendet.append(text)

        def starte(self):
            gestartet.append(self)
            original_start(self)

        with patch.object(s, "sende", merke), \
                patch.object(s, "frage", lambda t, k: ("Antwort", None)), \
                patch.object(s, "_lade_json", lambda p, v: {}), \
                patch.object(threading.Thread, "start", starte):
            antwort, _ = s.bearbeite("mach irgendwas", 42)
        self.assertEqual(antwort, "Angenommen.")
        self.assertTrue(gesendet, "keine Vorwarnung gesendet")
        self.assertIn("Minuten", gesendet[0])
        # Der Thread laeuft und sendet das Ergebnis als eigene Nachricht.
        self.assertEqual(len(gestartet), 1, "kein Hintergrund-Thread gestartet")
        gestartet[0].join(timeout=5)
        self.assertIn("Antwort", gesendet)

    def test_slash_befehl_schickt_keine_vorwarnung(self):
        """Ein Befehl antwortet in Sekunden - eine Vorwarnung waere Laerm."""
        gesendet = []
        with patch.object(s, "sende", lambda c, t: gesendet.append(t)), \
                patch.object(s, "_handelsantwort", lambda w: "Antwort"), \
                patch.object(s, "_lade_json", lambda p, v: {}):
            s.bearbeite("/spuren", 42)
        self.assertEqual(gesendet, [])


if __name__ == "__main__":
    unittest.main()