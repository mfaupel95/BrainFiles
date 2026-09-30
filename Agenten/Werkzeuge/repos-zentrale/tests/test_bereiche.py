"""Tests fuer die Bereichs-Anzeige: Baum, Filter, Summenzeile.

Reine Funktionen, kein Fenster - die Regeln stehen hier, nicht die Tageswerte.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fenster  # noqa: E402
import manifest  # noqa: E402


def z(ordner, gruppe, *, bereich="REPOS", wurzel="repos", notiz="", rolle="",
      bot=None, start=None, gruende=None, art="python"):
    return manifest.Zeile(
        ordner=ordner, gruppe=gruppe, notiz=notiz, rolle=rolle, bot=bot, start=start,
        gruende=list(gruende or []), bereich=bereich, wurzel=wurzel, art=art,
    )


class BereichsbaumTest(unittest.TestCase):
    def setUp(self):
        self.zeilen = [
            z("moon-dev-ai-agents", "startbar", rolle="Bot-Repo"),
            z("frischer-klon", "neu", gruende=["kein Eintrag im Manifest"]),
            z("omnitrade", "startbar", bereich="WERKSTATT", wurzel="werkstatt"),
            z("handelszentrale", "startbar", bereich="HANDEL", wurzel="handel",
              rolle="Werkzeug"),
            z("weg", "fehlt", bereich="HANDEL", wurzel="handel"),
        ]

    def test_bereiche_kommen_in_fester_reihenfolge(self):
        self.assertEqual(
            fenster.bereichsnamen(self.zeilen), ["REPOS", "WERKSTATT", "HANDEL"]
        )

    def test_bereich_enthaelt_gruppen_in_fester_reihenfolge(self):
        baum = fenster.nach_bereichen(self.zeilen)
        self.assertEqual(list(baum["REPOS"]), ["startbar", "neu"])
        self.assertEqual(list(baum["HANDEL"]), ["startbar", "fehlt"])

    def test_leerer_bereich_faellt_weg(self):
        baum = fenster.nach_bereichen([z("nur-repos", "startbar")])
        self.assertEqual(list(baum), ["REPOS"])

    def test_bereichsfilter_laesst_nur_seinen_bereich_uebrig(self):
        gefiltert = fenster.sichtbare_zeilen(self.zeilen, "", "HANDEL")
        self.assertEqual(sorted(x.ordner for x in gefiltert), ["handelszentrale", "weg"])

    def test_alle_bereiche_ist_kein_filter(self):
        for wahl in ("", fenster.ALLE_BEREICHE):
            self.assertEqual(len(fenster.sichtbare_zeilen(self.zeilen, "", wahl)), 5)

    def test_suche_trifft_rolle_und_pfad(self):
        self.assertEqual(
            [x.ordner for x in fenster.sichtbare_zeilen(self.zeilen, "werkzeug")],
            ["handelszentrale"],
        )

    def test_ueberschriften_tragen_die_zahl(self):
        self.assertEqual(fenster.bereich_titel("REPOS", 4), "REPOS - 4")
        self.assertEqual(fenster.gruppen_titel("startbar", 2), "STARTBAR (2)")


class SummenzeileTest(unittest.TestCase):
    def test_summe_nennt_bereiche_und_auffaelliges(self):
        zeilen = [
            z("a", "startbar"),
            z("b", "neu", gruende=["kein Eintrag im Manifest"]),
            z("c", "startbar", bereich="HANDEL", wurzel="handel"),
        ]
        text = fenster.zusammenfassung(zeilen)
        self.assertIn("3 Zeilen", text)
        self.assertIn("REPOS 2", text)
        self.assertIn("HANDEL 1", text)
        self.assertIn("1 auffaellig", text)

    def test_ohne_auffaelliges_bleibt_die_zeile_kurz(self):
        text = fenster.zusammenfassung([z("a", "startbar")])
        self.assertEqual(text, "1 Zeilen · REPOS 1")

    def test_leere_liste_ist_kein_fehler(self):
        self.assertEqual(fenster.zusammenfassung([]), "nichts gefunden")

    def test_auffaellige_sind_neu_und_fehlt(self):
        zeilen = [z("a", "startbar"), z("b", "neu"), z("c", "fehlt"), z("d", "doku")]
        self.assertEqual(
            sorted(x.ordner for x in fenster.auffaellige(zeilen)), ["b", "c"]
        )


class SpaltenbreitenTest(unittest.TestCase):
    """Die Spalten muessen auf jedem Monitor in das Fenster passen.

    Befund 30.09.2026: bei 125 % Anzeige brauchte ein 41-Zeichen-Hinweis 410 px,
    die Spalte war 366 px breit - der Text war abgeschnitten. Deshalb wird
    gerechnet, nicht geraten.
    """

    def test_bei_platz_bleiben_die_wunschbreiten(self):
        projekt, spalten = fenster.spaltenbreiten(4000, 1.0)
        self.assertEqual(projekt, fenster.BREITE_PROJEKT)
        self.assertEqual([b for _, _, b in spalten], [b for _, _, b in fenster.SPALTEN])

    def test_skalierung_streckt_alle_spalten(self):
        _, ohne = fenster.spaltenbreiten(4000, 1.0)
        _, mit = fenster.spaltenbreiten(4000, 1.25)
        for (_, _, a), (_, _, b) in zip(ohne, mit):
            self.assertGreater(b, a, "skalierte Spalte muss breiter sein")

    def test_kuerzung_trifft_zuerst_die_nebenspalten(self):
        """Die Hinweisspalte traegt den Grund - sie wird zuletzt gekuerzt."""
        voll = sum(b for _, _, b in fenster.SPALTEN) + fenster.BREITE_PROJEKT
        projekt, spalten = fenster.spaltenbreiten(voll - 200, 1.0)
        breiten = {k: b for k, _, b in spalten}
        self.assertEqual(
            breiten["hinweis"],
            dict((k, b) for k, _, b in fenster.SPALTEN)["hinweis"],
            "die Hinweisspalte darf erst zuletzt schrumpfen",
        )
        self.assertLess(breiten["art"], dict((k, b) for k, _, b in fenster.SPALTEN)["art"])

    def test_sehr_enge_breite_haelt_das_minimum(self):
        projekt, spalten = fenster.spaltenbreiten(700, 1.25)
        for _, _, b in spalten:
            self.assertGreaterEqual(b, fenster.SPALTEN_MINIMUM)
        self.assertGreaterEqual(projekt, fenster.SPALTEN_MINIMUM)

    def test_hinweis_bleibt_die_breiteste_spalte(self):
        _, spalten = fenster.spaltenbreiten(900, 1.0)
        breiten = sorted((b for _, _, b in spalten), reverse=True)
        self.assertEqual(
            breiten[0], dict((k, b) for k, _, b in spalten)["hinweis"]
        )

    def test_ohne_breite_bleibt_die_wunschbreite(self):
        projekt, spalten = fenster.spaltenbreiten(0, 1.0)
        self.assertEqual(
            sum(b for _, _, b in spalten),
            sum(b for _, _, b in fenster.SPALTEN),
        )

    def test_fenstergroesse_bleibt_im_bild(self):
        class Bildschirm:
            def winfo_screenwidth(self):
                return 1280

            def winfo_screenheight(self):
                return 800

        text = fenster.fenstergroesse(Bildschirm(), s=1.25)
        masse, _, lage = text.partition("+")
        b, _, h = masse.partition("x")
        self.assertLessEqual(int(b), 1280 - 80)
        self.assertLessEqual(int(h), 800 - 80)
        self.assertTrue(lage)

    def test_ohne_bildschirmdaten_gibt_es_eine_wunschgroesse(self):
        class Kaputt:
            def winfo_screenwidth(self):
                raise RuntimeError("kein Bildschirm")

            def winfo_screenheight(self):
                raise RuntimeError("kein Bildschirm")

        self.assertEqual(fenster.fenstergroesse(Kaputt(), s=1.0), "1400x900")


class HinweisUndFarbeTest(unittest.TestCase):
    def test_hinweis_nennt_grund_vor_notiz(self):
        zeile = z("x", "einrichten", notiz="egal", gruende=["venv fehlt"])
        self.assertEqual(fenster.hinweis(zeile), "venv fehlt")

    def test_farbe_traegt_den_zustand(self):
        f = fenster.Fenster.__new__(fenster.Fenster)      # nur die Methode brauchen
        self.assertEqual(f._farbe(z("a", "fehlt")), "fehlt")
        self.assertEqual(f._farbe(z("a", "neu")), "auffaellig")
        self.assertEqual(f._farbe(z("a", "startbar", gruende=["readme fehlt"])), "auffaellig")
        self.assertEqual(f._farbe(z("a", "startbar")), "startbar")


if __name__ == "__main__":
    unittest.main()
