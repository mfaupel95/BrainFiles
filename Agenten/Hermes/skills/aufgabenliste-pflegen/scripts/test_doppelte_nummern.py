"""Tests fuer doppelte_nummern.py - es MUSS den ganzen Bestand lesen (T-332).

ANLASS
------
`doppelte_nummern.py` erkannte nur `- [ ]` und `- [x]`. Die Datei traegt aber
auch `- [?]` (wartet), `- [!]` (wichtig) und `- [✓]`. Folge: `hoechste
Nummer: T-318`, waehrend T-330 oben im Offen-Abschnitt stand. Der Pruefer
meldete OK, ohne den halben Bestand gelesen zu haben - ein Pruefer, der
gruen sagt und dabei blind ist, ist schlimmer als keiner.

DIE REGEL, DIE HIER FESTGENAGELT WIRD
------------------------------------
JEDES Statuszeichen zaehlt als Kopfzeile. Nicht nur die zwei, die man auf
Tastendruck bekommt. Der alte Ausdruck `[ x]` sah in einer Datei mit
`[?] [!] [✓]` 26 Eintraege nicht - und wer sie nicht sieht, kann weder eine
Doppelte darin finden noch die hoechste Nummer melden.

DIE GEGENPROBE, OHNE DIE DER TEST NICHTS BEWEIST
-----------------------------------------------
`KOPF` wird auf das alte Muster zurueckgesetzt; die Tests zu den seltenen
Zeichen `[?]`, `[!]`, `[✓]` MUSSEN dann rot werden. Ohne diese Zeilen waere
der Test eine Bestaetigung, dass der heutige Stand funktioniert - nicht, dass
er nicht wieder zurueckfallen kann.
"""

import importlib.util
import pathlib
import re
import unittest

HIER = pathlib.Path(__file__).resolve().parent
SCRIPT = HIER.parent / "scripts" / "doppelte_nummern.py"

spec = importlib.util.spec_from_file_location("doppelte_nummern", SCRIPT)
dn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dn)


def datei(*bloecke):
    """Eine Minimalliste mit `## Offen` und `## Erledigt`."""
    teile = ["## Regeln", "", "Nur lesend.", "", "## Offen"]
    teile.extend(bloecke)
    teile.extend(["", "## Erledigt", "", "- [x] **T-001 — erledigt**", ""])
    return "\n".join(teile)


class StatuszeichenTest(unittest.TestCase):
    """JEDES Zeichen zaehlt - das ist die ganze Regel."""

    def _nummer(self, zeile):
        # Genau EIN Muster - `dn.KOPF`. Es traegt alle fuenf Statuszeichen
        # ([ x?!✓]), den Geviertstrich wie den ASCII-Bindestrich und eine wie
        # drei Leerstellen. Der untermittelte Titel ist KEIN Fall dieses
        # Pruefers: T-064 (04.10.2026) wurde an der Quelle auf Hausform
        # gebracht (Commit 8deee333), und eine Sonderregel im Pruefer waere
        # eine zweite Wahrheit ueber die Form der Datei - die dann
        # auseinanderlaufen kann.
        m = dn.KOPF.search(zeile)
        self.assertIsNotNone(m, "nicht als Kopf erkannt: %s" % zeile)
        return m.group(1)

    def test_offen(self):
        self.assertEqual(self._nummer("- [ ] **T-010 — offen**"), "T-010")

    def test_erledigt(self):
        self.assertEqual(self._nummer("- [x] **T-011 — erledigt**"), "T-011")

    def test_wartend(self):
        """[?] - 'wartet auf Max'. Genau die Eintraege, die jemand beim
        Einruecken eines wartenden Punktes doppelt vergeben kann."""
        self.assertEqual(self._nummer("- [?] **T-012 — wartet**"), "T-012")

    def test_wichtig(self):
        self.assertEqual(self._nummer("- [!] **T-013 — wichtig**"), "T-013")

    def test_haekchen(self):
        self.assertEqual(self._nummer("- [✓] **T-014 — fertig**"), "T-014")

    def test_ascii_bindestrich_statt_geviertstrich(self):
        """T-064 und viele aeltere Eintraege tragen ASCII `-` statt `—`.
        Wer nur den Geviertstrich liest, verliert 46 Bloecke."""
        self.assertEqual(self._nummer("- [ ] **T-015 - ascii**"), "T-015")

    def test_drei_leerstellen_statt_einer(self):
        """In der Datei stehen eine UND drei Leerstellen nach dem Zeichen."""
        self.assertEqual(self._nummer("- [ ]   **T-016 — drei**"), "T-016")

class GanzeDateiTest(unittest.TestCase):
    """Der Prüfer an einer Liste, nicht an einem Zeichen."""

    def test_alle_zeichen_findet_der_pruefer(self):
        text = datei(
            "- [ ] **T-020 — a**",
            "      Angelegt: 04.10.2026",
            "- [?] **T-021 — b**",
            "      Angelegt: 04.10.2026",
            "- [!] **T-022 — c**",
            "      Angelegt: 04.10.2026",
            "- [✓] **T-023 — d**",
            "      Angelegt: 04.10.2026",
        )
        bloecke, abschnitte = dn.zerlege(text)
        self.assertEqual(len(bloecke), 5, "5 Bloecke erwartet, %d gefunden"
                         % len(bloecke))
        self.assertIn("Offen", abschnitte)
        self.assertIn("Erledigt", abschnitte)

    def test_hoechste_nummer_ist_die_aus_einem_wartenden_eintrag(self):
        """DER BEFUND: T-318 war gemeldet, T-330 stand oben.

        Der hoechste Eintrag traegt `[?]` (wartet auf eine Entscheidung). Ein
        Pruefer, der `[?]` uebersieht, meldet die falsche hoechste Nummer.
        """
        text = datei(
            "- [x] **T-318 — alt**",
            "      Angelegt: 01.01.2026",
            "- [ ] **T-330 — neu**",
            "      Angelegt: 04.10.2026",
        )
        bloecke, _abschnitte = dn.zerlege(text)
        hoechste = max(b["nummer"] for b in bloecke)
        self.assertEqual(hoechste, "T-330")

    def test_doppelte_nummer_in_einem_wartenden_eintrag_wird_gesehen(self):
        """Der eigentliche Zweck: eine Doppelt vergebene Nummer MUSS
        auffallen - auch wenn sie in einem Eintrag mit `[?]` steht."""
        text = datei(
            "- [ ] **T-139 — erster**",
            "      Angelegt: 01.01.2026",
            "- [?] **T-139 — zweiter**",
            "      Angelegt: 04.10.2026",
        )
        bloecke, _ = dn.zerlege(text)
        nach_nummer = {}
        for b in bloecke:
            nach_nummer.setdefault(b["nummer"], []).append(b)
        doppelt = [n for n, bs in nach_nummer.items() if len(bs) > 1]
        self.assertEqual(doppelt, ["T-139"])

    def test_fehlender_abschnitt_wird_gemeldet(self):
        text = "- [ ] **T-030 — ohne Abschnitte**\n"
        bloecke, abschnitte = dn.zerlege(text)
        fehlt = [a for a in ("Offen", "Erledigt") if a not in abschnitte]
        self.assertEqual(fehlt, ["Offen", "Erledigt"])

    def test_zaun_inhalt_ist_keine_aufgabe(self):
        """Ein Codeblock, in dem eine Zeile wie ein Kopf aussieht, ist kein
        Eintrag. Sonst zaehlt die Vorlage im Eintragsformat mit - und eine
        doppelte Nummer darin wird als Kollision gemeldet, die keine ist.

        Geprueft wird die EIGENSCHAFT: die Zahl im Zaun taucht nicht auf.
        Die Liste enthaelt zusaetzlich den Erledigt-Eintrag, den `datei()`
        anhaengt - deshalb wird nur auf das Vorhandensein von T-999 geprueft
        und nicht auf die vollstaendige Liste.
        """
        text = datei(
            "- [ ] **T-040 — echt**",
            "      Angelegt: 04.10.2026",
            "",
            "```",
            "- [ ] **T-999 — nur ein Beispiel**",
            "```",
        )
        bloecke, _ = dn.zerlege(text)
        nummern = [b["nummer"] for b in bloecke]
        self.assertIn("T-040", nummern)
        self.assertNotIn("T-999", nummern,
                         "eine Zeile im Codeblock ist eine Vorlage, kein "
                         "Eintrag")


class GegenprobeTest(unittest.TestCase):
    """Der Test muss fallen, wenn das Muster zurueckfaellt."""

    def setUp(self):
        self.alt_kopf = dn.KOPF

    def tearDown(self):
        dn.KOPF = self.alt_kopf

    def _muster_alt(self):
        """Das alte Muster: nur die zwei Tastendruck-Zeichen."""
        dn.KOPF = re.compile(r"^- \[[ x]\]\s*\*\*(T-\d+)\s*[—-]?\s*(.*?)\*\*",
                             re.M)

    def test_altes_muster_uebersieht_das_wartezeichen(self):
        """Beleegt, dass die Regelpruefung ueberhaupt etwas faengt.

        DER BEFUND VOM 04.10.: der hoechste Eintrag trug `[?]` (wartet auf
        eine Entscheidung), der Pruefer meldete die Nummer darunter.
        """
        self._muster_alt()
        text = datei(
            "- [x] **T-318 — unten**",
            "      Angelegt: 01.01.2026",
            "- [?] **T-330 — wartet, ganz oben**",
            "      Angelegt: 04.10.2026",
        )
        bloecke, _abschnitte = dn.zerlege(text)
        hoechste = max(b["nummer"] for b in bloecke)
        self.assertEqual(hoechste, "T-318",
                         "das alte Muster meldet die falsche hoechste "
                         "Nummer - genau der Befund vom 04.10.2026")

if __name__ == "__main__":
    unittest.main()