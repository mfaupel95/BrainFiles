"""Tests fuer die Anzeigelogik des Fensters (ohne echtes Fenster, ohne Starts)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fenster  # noqa: E402
import manifest  # noqa: E402


def z(ordner, gruppe, *, notiz="", bot=None, start=None, gruende=None):
    return manifest.Zeile(
        ordner=ordner, gruppe=gruppe, notiz=notiz, bot=bot, start=start,
        gruende=list(gruende or []),
    )


class SichtbareZeilenTest(unittest.TestCase):
    def setUp(self):
        self.zeilen = [
            z("moon-dev-ai-agents", "startbar", notiz="47 Agenten", bot="moon-dev-agents"),
            z("ProjectAtlas", "einrichten", notiz="Rust, Repo-Karte"),
            z("santiment", "doku", notiz="nur Dokumentation"),
            z("frischer-klon", "neu", notiz="", gruende=["kein Eintrag im Manifest"]),
        ]

    def test_ohne_suchtext_bleiben_alle_zeilen(self):
        self.assertEqual(len(fenster.sichtbare_zeilen(self.zeilen, "")), 4)

    def test_suche_trifft_ordner_und_notiz_ohne_grossschreibung(self):
        gefunden = [x.ordner for x in fenster.sichtbare_zeilen(self.zeilen, "MOON")]
        self.assertEqual(gefunden, ["moon-dev-ai-agents"])
        gefunden = [x.ordner for x in fenster.sichtbare_zeilen(self.zeilen, "repo-karte")]
        self.assertEqual(gefunden, ["ProjectAtlas"])

    def test_suche_trifft_den_bot_namen(self):
        gefunden = [x.ordner for x in fenster.sichtbare_zeilen(self.zeilen, "moon-dev-agents")]
        self.assertEqual(gefunden, ["moon-dev-ai-agents"])

    def test_ohne_treffer_leere_liste(self):
        self.assertEqual(fenster.sichtbare_zeilen(self.zeilen, "gibtsnicht"), [])


class GruppenTest(unittest.TestCase):
    def test_gruppen_kommen_in_fester_reihenfolge(self):
        zeilen = [
            z("doc", "doku"), z("neu-klon", "neu"), z("weg", "fehlt"),
            z("laeuft", "startbar"), z("muss-install", "einrichten"),
        ]
        gruppen = fenster.nach_gruppen(zeilen)
        self.assertEqual(
            list(gruppen), ["startbar", "einrichten", "neu", "doku", "fehlt"]
        )

    def test_leere_gruppen_fallen_weg(self):
        gruppen = fenster.nach_gruppen([z("doc", "doku")])
        self.assertEqual(list(gruppen), ["doku"])

    def test_innerhalb_einer_gruppe_alphabetisch(self):
        gruppen = fenster.nach_gruppen([z("zeta", "startbar"), z("Alpha", "startbar")])
        self.assertEqual([x.ordner for x in gruppen["startbar"]], ["Alpha", "zeta"])


class TitelTest(unittest.TestCase):
    def test_jede_gruppe_hat_einen_titel_mit_zahl(self):
        for name in manifest.GRUPPEN_REIHENFOLGE:
            titel = fenster.gruppen_titel(name, 3)
            self.assertTrue(titel.strip().endswith("(3)"), titel)
            self.assertEqual(titel, fenster.gruppen_titel(name, 3))

    def test_hinweis_kommt_aus_den_gruenden(self):
        zeile = z("x", "einrichten", gruende=["venv fehlt", "kein Startbefehl belegt"])
        self.assertEqual(fenster.hinweis(zeile), "venv fehlt; kein Startbefehl belegt")

    def test_hinweis_ist_leer_wenn_alles_da_ist(self):
        self.assertEqual(fenster.hinweis(z("x", "startbar", notiz="47 Agenten")), "")

    def test_hinweis_faellt_auf_die_notiz_zurueck(self):
        self.assertEqual(fenster.hinweis(z("x", "doku", notiz="nur Dokumentation")),
                         "nur Dokumentation")


if __name__ == "__main__":
    unittest.main()
