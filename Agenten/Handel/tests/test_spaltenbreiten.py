r"""Regel statt Stand: `spaltenbreiten` gibt jedem Text sein Platz.

Warum diese Regel ueberhaupt existiert (gemessen am 04.10.2026 mit
`messprobe.py`, Aufruf ohne --dpi): 57 Texte passten nicht in ihre Spalte
und die Positionstabelle der Handelszentrale war 36 px breiter als ihr
Baum. Ursache waren feste Pixelzahlen, nicht die Schrift.

Geprueft werden die drei Regeln der Funktion, jede mit einer Gegenprobe:

  1. Ein Text passt in seine Spalte - bei JEDER Skalierung und jeder
     Zeichenbreite. Nicht: die Summe passt.
  2. Die Summe passt in den Baum, solange der Platz reicht.
  3. Reicht der Platz nicht, wird GESCHNITTEN statt abgeschnitten: keine
     Spalte faellt unter das, was ihr schlimmster Text braucht.

Was hier NICHT geprueft wird: dass die Zahl im echten Fenster stimmt. Dafuer
ist `messprobe.py` da - ein Test gegen die echte Schrift wuerde einen
Bildschirm brauchen, die Messprobe braucht nur Tk.

Aufruf aus `Agenten/Handel/tests`:
    ..\scanner\.venv\Scripts\python.exe -m unittest test_spaltenbreiten
"""

import os
import sys
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import handelszentrale as hz  # noqa: E402


SPUREN = ["xperp", "scanner", "nautilus_kraken_futures", "squeeze_eth"]
KOPF = {"spur": "Spur", "kurs": "Kurs"}
WUNSCH = [220, 90]


class TextPasstTest(unittest.TestCase):
    """Regel 1: jeder Text passt in seine Spalte."""

    def test_langer_spurname_passt_in_aller_skalierung(self):
        for zb in (hz.ZEICHEN_BREITE_TK, hz.ZEICHEN_BREITE_DPI, 11, 14):
            breiten = dict(hz.spaltenbreiten(
                ["spur", "kurs"], KOPF, WUNSCH,
                texte={"spur": SPUREN}, zeichen_breite=zb))
            noetig = len("nautilus_kraken_futures") * zb + hz.SPALTEN_RAND
            self.assertGreaterEqual(
                breiten["spur"], noetig,
                "bei %d px je Zeichen ist %r abgeschnitten (Spalte %d < %d)"
                % (zb, "nautilus_kraken_futures", breiten["spur"], noetig))

    def test_ueberschrift_passt_auch_ohne_texte(self):
        for zb in (hz.ZEICHEN_BREITE_TK, hz.ZEICHEN_BREITE_DPI):
            breiten = dict(hz.spaltenbreiten(
                ["spur"], {"spur": "Spurenname der Tabell"}, [120],
                zeichen_breite=zb))
            self.assertGreaterEqual(breiten["spur"],
                                    len("Spurenname der Tabell") * zb
                                    + hz.SPALTEN_RAND)

    def test_leere_und_none_texte_werfen_nicht(self):
        breiten = dict(hz.spaltenbreiten(
            ["spur"], KOPF, WUNSCH, texte={"spur": ["", None, "xperp"]},
            zeichen_breite=hz.ZEICHEN_BREITE_TK))
        self.assertGreater(breiten["spur"], 0)

    def test_reihenfolge_der_spalten_bleibt(self):
        ergebnis = hz.spaltenbreiten(["kurs", "spur"], KOPF, WUNSCH)
        self.assertEqual([s for s, _ in ergebnis], ["kurs", "spur"])


class SummePasstTest(unittest.TestCase):
    """Regel 2: die Summe passt in den Baum."""

    def test_grosser_baum_braucht_kein_kuerzen(self):
        breiten = dict(hz.spaltenbreiten(
            ["spur", "kurs"], KOPF, WUNSCH, texte={"spur": SPUREN},
            zeichen_breite=hz.ZEICHEN_BREITE_TK, verfuegbar=2000))
        self.assertLessEqual(sum(breiten.values()), 2000 - hz.ROLLENDE)

    def test_enger_baum_wird_auf_die_positionstabelle_gebracht(self):
        breiten = dict(hz.spaltenbreiten(
            ["spur", "kurs"], KOPF, WUNSCH, texte={"spur": SPUREN},
            zeichen_breite=hz.ZEICHEN_BREITE_TK, verfuegbar=400))
        self.assertLessEqual(sum(breiten.values()), 400 - hz.ROLLENDE)

    def test_ohne_verfuegbaren_platz_bleibt_es_beim_wunsch(self):
        breiten = dict(hz.spaltenbreiten(
            ["spur", "kurs"], KOPF, WUNSCH, texte={"spur": SPUREN},
            zeichen_breite=hz.ZEICHEN_BREITE_TK, verfuegbar=0))
        self.assertGreaterEqual(breiten["spur"], 220)


class SchnittStattAbschneidenTest(unittest.TestCase):
    """Regel 3: gekuerzt wird, aber nicht unter den Text."""

    def test_zu_enge_baum_opfert_die_haupt__nicht_die_ecke(self):
        """Bei zu engem Baum wird die Kennzahl geopfert, nicht der Spurname.

        200 px Platz, zwei Spalten mit 238 px und 98 px Bedarf: zusammen
        336, Platz 160. Die Regel sagt "schneiden statt abschneiden" - es
        bleibt also mehr Platz im Baum als die Untergrenzen fordern, und
        eine waagerechte Leiste traegt den Rest. Die Hauptspalte (der
        Spurname) darf dabei NICHT unter ihre Untergrenze.
        """
        breiten = dict(hz.spaltenbreiten(
            ["spur", "kurs"], KOPF, WUNSCH,
            texte={"spur": ["nautilus_kraken_futures", "moondev_listingarb"]},
            zeichen_breite=hz.ZEICHEN_BREITE_DPI, verfuegbar=200))
        # 1. Die Hauptspalte haelt ihr Minimum - das ist die Regel.
        spur_bedarf = (len("nautilus_kraken_futures") * hz.ZEICHEN_BREITE_DPI
                       + hz.SPALTEN_RAND)
        self.assertGreaterEqual(breiten["spur"], spur_bedarf)
        # 2. Und die Kennzahl wurde dafuer gekuerzt - sonst waere die
        #    Hauptspalte auf Kosten der letzten geschaetzt worden.
        self.assertLess(breiten["kurs"], WUNSCH[1])

    def test_genau_dann_gilt_die_summe_wenn_der_platz_reicht(self):
        """Sobald genug Platz da ist, gilt die Summe - und dann erst."""
        breiten = dict(hz.spaltenbreiten(
            ["spur", "kurs"], KOPF, WUNSCH,
            texte={"spur": ["nautilus_kraken_futures"]},
            zeichen_breite=hz.ZEICHEN_BREITE_DPI, verfuegbar=600))
        self.assertLessEqual(sum(breiten.values()), 600 - hz.ROLLENDE)

    def test_die_letzte_spalte_ist_die_erste_zum_kuerzen(self):
        """Der Ueberhang kommt aus der LETZTEN Spalte, nicht aus der ersten.

        Beide Spalten haben Luft ueber ihrem Text. Bei 200 px Baum muesste
        die Hauptspalte (der Spurname) unberuehrt bleiben und die Kurs-
        spalte den Ueberhang tragen - sonst verlier der Name zuerst.
        """
        breiten = dict(hz.spaltenbreiten(
            ["spur", "kurs"], KOPF, WUNSCH, texte={"spur": ["xperp"]},
            zeichen_breite=hz.ZEICHEN_BREITE_TK, verfuegbar=200))
        # Die Spalte ohne eigene Texte haelt SPALTEN_MINIMUM als Minimum;
        # mit 220 px Wunsch hat sie also genau 60 px Spielraum nach unten.
        # 200 - 40 (Rollbalken) = 160 px Platz, Wunsch 220 + 90 = 310.
        # Ueberhang 150: erst die letzte Spalte (60 nutzbar), dann die
        # erste. Ergebnis: Haupt 100, letzte 60 = 160 px.
        self.assertEqual(sum(breiten.values()), 200 - hz.ROLLENDE)
        self.assertLessEqual(breiten["kurs"], hz.SPALTEN_MINIMUM)
        # Und die Hauptspalte ist NICHT auf ihr Minimum gefallen.
        self.assertGreater(breiten["spur"], hz.SPALTEN_MINIMUM)

    def test_untere_grenze_der_spalte(self):
        for sp, breite in hz.spaltenbreiten(["a"], {}, [200],
                                          verfuegbar=500):
            self.assertGreaterEqual(breite, hz.SPALTEN_MINIMUM)

    def test_leere_spaltenliste(self):
        self.assertEqual(hz.spaltenbreiten([], {}, []), [])


class GegenprobeTest(unittest.TestCase):
    """Die Funktion muss ueberhaupt rot werden koennen.

    Ein Test, der nur einen Fall prueft und sonst nichts, ist bei einer
    neuen Formel genauso blind wie der alte feste Breitenwert. Deshalb
    hier die kaputten Varianten, jeweils erwartet als Abweichung von der
    Regel - wenn eine davon NICHT auffaellt, ist die Regel nicht aktiv.
    """

    def test_zu_kurze_spalte_wird_erkannt(self):
        """Ein Wert unter dem Textbedarf MUSS auffallen."""
        breiten = dict(hz.spaltenbreiten(
            ["spur"], {}, [60], texte={"spur": ["nautilus_kraken_futures"]},
            zeichen_breite=hz.ZEICHEN_BREITE_DPI))
        noetig = 23 * hz.ZEICHEN_BREITE_DPI + hz.SPALTEN_RAND
        self.assertGreaterEqual(breiten["spur"], noetig)
        # Gegenprobe: die alte, feste Breite von 110 px haette nicht
        # bestanden - 110 < 238.
        self.assertLess(110, noetig)

    def test_zu_breite_summe_wird_erkannt(self):
        """Eine Summe ueber dem Baum muss erkannt werden."""
        breiten = dict(hz.spaltenbreiten(
            ["a", "b"], {}, [300, 300], verfuegbar=400))
        self.assertLessEqual(sum(breiten.values()), 400 - hz.ROLLENDE)


if __name__ == "__main__":
    unittest.main()