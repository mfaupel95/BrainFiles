"""Tests fuer die Filter der Zentrale (reine Rechnung, ohne Fenster)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import auswahl  # noqa: E402
import manifest  # noqa: E402


def z(ordner, gruppe="startbar", *, bereich="REPOS", art="python", rolle="",
      notiz="", bot=None, bot_da=False, start=None, gruende=None, spur="", scharf=False):
    zeile = manifest.Zeile(
        ordner=ordner, gruppe=gruppe, notiz=notiz, rolle=rolle, bot=bot, start=start,
        gruende=list(gruende or []), bereich=bereich, art=art,
    )
    zeile.bot_da = bot_da
    zeile.spur = spur
    zeile.scharf = scharf
    return zeile


class KennzeichenTest(unittest.TestCase):
    def setUp(self):
        self.zeilen = [
            z("moon-dev-ai-agents", "startbar", bot="moon-dev-agents", bot_da=True,
              start=["x.exe"], notiz="47 Agenten"),
            z("frischer-klon", "neu", gruende=["kein Eintrag im Manifest"]),
            z("weg", "fehlt", bereich="HANDEL", gruende=["Ordner fehlt"]),
            z("scanner", "startbar", bereich="HANDEL", rolle="Spur", spur="scanner",
              scharf=True, start=["x.exe"], gruende=["fremd: fremdes Repo (x)"]),
            z("klassik_sma", "startbar", bereich="HANDEL", rolle="Spur", spur="klassik_sma",
              start=["y.exe"]),
            z("nur-text", "doku"),
        ]

    def namen(self, f):
        return [x.ordner for x in auswahl.filtern(self.zeilen, f)]

    def test_ohne_kennzeichen_bleibt_alles(self):
        self.assertEqual(len(self.namen(auswahl.Filter())), 6)

    def test_auffaellig_ist_neu_oder_fehlt(self):
        self.assertEqual(self.namen(auswahl.Filter(kennzeichen=("auffaellig",))),
                         ["frischer-klon", "weg"])

    def test_startbar_und_ohne_start_sind_gegensaetze(self):
        mit = set(self.namen(auswahl.Filter(kennzeichen=("startbar",))))
        ohne = set(self.namen(auswahl.Filter(kennzeichen=("ohne_start",))))
        self.assertTrue(mit)
        self.assertEqual(mit & ohne, set())

    def test_mit_start_fragt_den_befehl_nicht_die_gruppe(self):
        """Eine Zeile in EINRICHTEN kann einen Startbefehl haben (venv fehlt)."""
        zeilen = [z("halb", "einrichten", start=["x.exe"]), z("leer", "einrichten")]
        self.assertEqual([x.ordner for x in auswahl.filtern(zeilen, auswahl.Filter(
            kennzeichen=("mit_start",)))], ["halb"])

    def test_mit_bot_fragt_das_profil(self):
        self.assertEqual(self.namen(auswahl.Filter(kennzeichen=("mit_bot",))),
                         ["moon-dev-ai-agents"])

    def test_fremd_und_eigen_sind_gegensaetze(self):
        fremd = set(self.namen(auswahl.Filter(kennzeichen=("fremd",))))
        eigen = set(self.namen(auswahl.Filter(kennzeichen=("eigen",))))
        self.assertEqual(fremd, {"scanner"})
        self.assertEqual(fremd & eigen, set())

    def test_handel_filtert_den_bereich(self):
        self.assertEqual(self.namen(auswahl.Filter(kennzeichen=("handel",))),
                         ["weg", "scanner", "klassik_sma"])

    def test_spuren_und_scharf_kommen_von_aussen(self):
        self.assertEqual(self.namen(auswahl.Filter(kennzeichen=("spuren",))),
                         ["scanner", "klassik_sma"])
        self.assertEqual(self.namen(auswahl.Filter(kennzeichen=("scharf",))), ["scanner"])

    def test_kennzeichen_wirken_und_verknuepft(self):
        """Wer zwei Chips anmacht, will die Schnittmenge - nicht die Vereinigung."""
        self.assertEqual(self.namen(auswahl.Filter(kennzeichen=("handel", "spuren"))),
                         ["scanner", "klassik_sma"])
        self.assertEqual(self.namen(auswahl.Filter(kennzeichen=("handel", "auffaellig"))),
                         ["weg"])

    def test_unbekanntes_kennzeichen_schraenkt_nicht_ein(self):
        self.assertEqual(len(self.namen(auswahl.Filter(kennzeichen=("gibtsnicht",)))), 6)


class TextUndBereichTest(unittest.TestCase):
    def setUp(self):
        self.zeilen = [
            z("ProjectAtlas", notiz="Rust, Repo-Karte", rolle="Werkzeug"),
            z("omnitrade", bereich="WERKSTATT", rolle="Projekt"),
        ]

    def test_text_trifft_ordner_rolle_und_notiz(self):
        for wort in ("projectatlas", "PROJECTATLAS", "repo-karte", "werkzeug"):
            self.assertEqual(
                [x.ordner for x in auswahl.filtern(self.zeilen, auswahl.Filter(text=wort))],
                ["ProjectAtlas"], wort,
            )

    def test_bereich_mit_und_ohne_zahl(self):
        for wahl in ("WERKSTATT", "WERKSTATT (1)", "Alle Bereiche", ""):
            erwartet = ["omnitrade"] if wahl.startswith("WERKSTATT") else ["ProjectAtlas", "omnitrade"]
            self.assertEqual(
                [x.ordner for x in auswahl.filtern(self.zeilen, auswahl.Filter(bereich=wahl))],
                erwartet, wahl,
            )

    def test_gruppentitel_und_schluessel_meinen_dasselbe(self):
        """Die Auswahl zeigt 'NUR DOKU', gefiltert wird ueber 'doku'."""
        zeilen = [z("a", "startbar"), z("b", "doku")]
        for wahl in ("NUR DOKU", "doku", "Nur Doku (2)"):
            self.assertEqual(
                [x.ordner for x in auswahl.filtern(zeilen, auswahl.Filter(gruppe=wahl))],
                ["b"], wahl,
            )

    def test_gruppe_alle_laesst_alles_durch(self):
        self.assertEqual(auswahl.gruppe_schluessel(auswahl.ALLE_GRUPPEN), "")
        self.assertEqual(len(auswahl.filtern([z("a"), z("b")],
                                             auswahl.Filter(gruppe=auswahl.ALLE_GRUPPEN))), 2)

    def test_gruppe_filtert(self):
        zeilen = [z("a", "startbar"), z("b", "doku")]
        self.assertEqual(
            [x.ordner for x in auswahl.filtern(zeilen, auswahl.Filter(gruppe="NUR DOKU"))],
            ["b"],
        )

    def test_gruppe_und_text_wirken_zusammen(self):
        f = auswahl.Filter(text="project", bereich="WERKSTATT")
        self.assertEqual(auswahl.filtern(self.zeilen, f), [])


class BeschreibungTest(unittest.TestCase):
    def test_leerer_filter_ergibt_leeren_text(self):
        self.assertEqual(auswahl.beschreibung(auswahl.Filter()), "")

    def test_beschreibung_nennt_die_gesetzten_teile(self):
        f = auswahl.Filter(text="kraken", bereich="HANDEL (124)", gruppe="STARTBAR",
                           kennzeichen=("scharf",))
        text = auswahl.beschreibung(f)
        self.assertIn("HANDEL", text)
        self.assertIn("STARTBAR", text)
        self.assertIn("scharf", text)
        self.assertIn("kraken", text)


if __name__ == "__main__":
    unittest.main()