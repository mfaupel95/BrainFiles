"""TASKS.md: die Kopfzeile von T-064 traegt wieder ein schliessendes '**'.

Befund 04.10.2026, Karte t_bb9fb140: T-064 stand als

    - [ ] **T-064 - Nautilus-Kraken-Orderweg: WebSocket-Token verweigert, REST traegt

Jeder Leser mit dem Hausform-Muster (`\\*\\*$` am Zeilenende) uebersieht eine
solche Zeile. Der Punkt fiel dadurch aus dem Routing-Plan und aus jedem
Werkzeug, das die Eintraege zaehlen will - und traegt ausgerechnet eine
erledigte Entscheidung (`ENTSCHEIDUNG Max 24.09.2026: REST bleibt`).

Gemessen an `MaxHirn/Archiv/TASKS.md`: 339 Statuszeichen-Kopfzeilen, davon
genau EINE mit ungerader Sternchen-Zahl. Der Test nennt diesen Fall
ausdruecklich, damit eine Regression an ihm auffaellt - nicht nur die
allgemeine Form.

Der Test liest nur. Er schreibt TASKS.md nicht an.

Ausfuehren (aus der Repo-Wurzel):
    python Agenten/Werkzeuge/tests/test_tasks_kopfzeilen.py
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
import unittest

_HIER = os.path.dirname(os.path.abspath(__file__))
_WURZEL = os.path.normpath(os.path.join(_HIER, "..", "..", ".."))
TASKS = os.path.join(_WURZEL, "MaxHirn", "Archiv", "TASKS.md")

# Die Kopfzeile, um die es geht - woertlich, wie sie vor der Reparatur war.
T064_KOPF = ("- [ ] **T-064 — Nautilus-Kraken-Orderweg: "
             "WebSocket-Token verweigert, REST traegt")
T064_TITEL = "Nautilus-Kraken-Orderweg: WebSocket-Token verweigert, REST traegt"

# Eine Zeile, die WIE ein Eintrag aussieht. Kein Muster darf sie uebersehen,
# ohne dass es das als Befund meldet.
VERDAECHTIG = re.compile(r"^-\s*\[.\]\s+\*\*T-\d{3,}")


def zeilen_lese(pfad=TASKS):
    with open(pfad, "rb") as f:
        raw = f.read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n").split("\n"), nl


def t064_kopfzeilen(zeilen):
    return [z for z in zeilen if z.startswith(T064_KOPF)]


def untermittelte_kopfzeilen(zeilen):
    return [z for z in zeilen if VERDAECHTIG.match(z) and z.count("**") % 2 != 0]


class T064KopfTest(unittest.TestCase):
    """Prueft die ECHTE TASKS.md. `TASKS_PFAD` ist der einzige Ansatzpunkt -
    die Gegenprobe haengt sich mit einer kaputten Kopie genau hier dran."""

    TASKS_PFAD = TASKS

    def setUp(self):
        self.zeilen, self.nl = zeilen_lese(self.TASKS_PFAD)

    def test_t064_kopfzeile_endet_mit_sternchenpaar(self):
        kopf = [z for z in self.zeilen if z.startswith(T064_KOPF)]
        self.assertEqual(len(kopf), 1,
                         "T-064-Kopfzeile nicht genau einmal gefunden: %r" % (kopf,))
        self.assertTrue(kopf[0].rstrip().endswith("**"),
                        "die reparierte Kopfzeile muss mit '**' enden: %r" % kopf[0])

    def test_t064_titel_ist_vollstaendig_lesbar(self):
        """Der Titel bricht nach 'REST traegt' ab - die Entscheidung dahinter
        ('REST bleibt') stand bisher in Folgezeilen ohne Feldmarke."""
        kopf = t064_kopfzeilen(self.zeilen)
        self.assertEqual(len(kopf), 1)
        titel = kopf[0].split("—", 1)[1].strip().strip("*").strip()
        self.assertEqual(titel, T064_TITEL)

    def test_der_haus_leser_findet_t064(self):
        """Der eigentliche Schaden: ein Leser mit dem Hausform-Muster
        (`**$` am Zeilenende) uebersieht die untermittelte Zeile GANZ - der
        Titel ist in beiden Kopien gleich lesbar, verschwunden ist er nur
        fuer diesen Leser. Genau der ging im Routing-Plan verloren."""
        mit_hausform = [z for z in self.zeilen
                        if re.match(r"^-\s*\[.\]\s+\*\*T-\d{3,}", z)
                        and z.rstrip().endswith("**")]
        self.assertEqual([z for z in mit_hausform if z.startswith(T064_KOPF)],
                         t064_kopfzeilen(self.zeilen),
                         "T-064 muss auch fuer den Haus-Leser eine Zeile sein")

    def test_keine_statuszeichen_kopfzeile_ist_untermittelt(self):
        """Die gemessene Zahl: 339 Kopfzeilen, keine mit ungerader
        Sternchen-Zahl. Ein Test, der nur die eine Zeile prueft, laesst die
        naechste untermittelte Kopfzeile unbemerkt - die Frage 'welche
        anderen sind betroffen' war in der Karte ausdruecklich offen."""
        self.assertEqual(untermittelte_kopfzeilen(self.zeilen), [],
                         "untermittelte Kopfzeile(n) gefunden")

    def test_t064_ist_im_abschnitt_offen_und_nicht_erledigt(self):
        a = next(i for i, z in enumerate(self.zeilen) if z.strip() == "## Offen")
        b = next((i for i, z in enumerate(self.zeilen)
                  if z.strip() == "## Erledigt"), len(self.zeilen))
        treffer = [i for i, z in enumerate(self.zeilen)
                   if z.startswith(T064_KOPF)]
        self.assertEqual(len(treffer), 1)
        self.assertTrue(a < treffer[0] < b,
                        "T-064 gehoert nicht in den Abschnitt Offen")


class GegenprobeTest(unittest.TestCase):
    """Gegenprobe: dieselben Pruefmethoden auf der KAPUTTEN Fassung.

    Nicht die Regexe nachgebaut, sondern die Testklasse mit einer
    Wegwerf-Kopie von TASKS.md laufen lassen: die kaputte Fassung MUSS
    rot werden. Ein Test, der auf seiner kaputten Fassung gruen bleibt,
    prueft nichts - genau so entstand dieser Befund (der Plan-Pruefer
    teilte die Enge des Plan-Bauers und meldete die Luecke GRUEN).
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="t064_gegenprobe_")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.pfad = os.path.join(self.dir, "TASKS.md")
        zeilen, nl = zeilen_lese(TASKS)
        kaputt = [z[:-2] if z.rstrip().endswith("**") and z.startswith(T064_KOPF)
                  else z for z in zeilen]
        self.assertNotEqual(zeilen, kaputt, "die Gegenprobe aendert nichts")
        with open(self.pfad, "w", encoding="utf-8", newline=nl) as f:
            f.write(nl.join(kaputt))
        # Die Kopie traegt den Defekt - sonst prueft die Gegenprobe nichts.
        kopf = t064_kopfzeilen(kaputt)
        self.assertEqual(len(kopf), 1)
        self.assertFalse(kopf[0].rstrip().endswith("**"))
        self.assertEqual([x for x in untermittelte_kopfzeilen(kaputt)
                          if x.startswith(T064_KOPF)], kopf)

    def _lauf(self, methode):
        klasse = type("KaputteFassung", (T064KopfTest,), {"TASKS_PFAD": self.pfad})
        return klasse(methode).run()

    def test_gegenprobe_bricht_die_kopfzeile_um(self):
        erg = self._lauf("test_t064_kopfzeile_endet_mit_sternchenpaar")
        self.assertFalse(erg.wasSuccessful(),
                         "mit der kaputten Fassung muss der Test fallen")

    def test_gegenprobe_meldet_die_untermittelte_zeile(self):
        erg = self._lauf("test_keine_statuszeichen_kopfzeile_ist_untermittelt")
        self.assertFalse(erg.wasSuccessful(),
                         "mit der kaputten Fassung muss der Test fallen")

    def test_gegenprobe_bricht_den_haus_leser(self):
        erg = self._lauf("test_der_haus_leser_findet_t064")
        self.assertFalse(erg.wasSuccessful(),
                         "mit der kaputten Fassung muss der Test fallen")

    def test_die_echte_datei_bleibt_unberuehrt(self):
        """Die Gegenprobe schreibt in einen Tempordner; TASKS.md wird nur
        gelesen. Nach dem Lauf steht die echte Kopfzeile mit '**'."""
        zeilen, _ = zeilen_lese(TASKS)
        kopf = t064_kopfzeilen(zeilen)
        self.assertEqual(len(kopf), 1)
        self.assertTrue(kopf[0].rstrip().endswith("**"))


if __name__ == "__main__":
    unittest.main(verbosity=2)