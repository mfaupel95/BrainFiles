"""Tests fuer das Zeitfenster der Auswertung.

Geprueft wird das, was still schiefgehen kann: ein Journal mit Offset gegen
eines ohne Uhrzeit (orbk), und die Regel, dass ein leeres Fenster ALLES
durchlaesst statt NICHTS - sonst liest ein Aufruf ohne --tage ein leeres Buch.
"""

import datetime as dt
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import zeitfenster as zf                                       # noqa: E402


class TestParse(unittest.TestCase):

    def test_iso_mit_offset(self):
        d = zf.parse("2026-09-14T15:01:34+00:00")
        self.assertEqual(d, dt.datetime(2026, 9, 14, 15, 1, 34,
                                        tzinfo=dt.timezone.utc))

    def test_nur_datum_wird_tagesbeginn_utc(self):
        # orbk fuehrt nur ein Datum. Tagesbeginn ist die einzige Lesart, die
        # ein Tagesfenster nicht um einen Tag verschiebt.
        d = zf.parse("2026-09-13")
        self.assertEqual(d, dt.datetime(2026, 9, 13, 0, 0, 0,
                                        tzinfo=dt.timezone.utc))

    def test_muell_ist_none(self):
        self.assertIsNone(zf.parse(""))
        self.assertIsNone(zf.parse("gestern"))
        self.assertIsNone(zf.parse(None))

    def test_naiver_zeitstempel_gilt_als_utc(self):
        # Kein Journal schreibt heute naiv. Faellt eines doch so aus, ist
        # "als UTC lesen" die Lesart, die zum Rest des Baums passt - ein
        # TypeError beim Vergleich waere der schlechtere Ausgang.
        d = zf.parse("2026-09-14T15:01:34")
        self.assertEqual(d.tzinfo, dt.timezone.utc)


class TestFenster(unittest.TestCase):

    def test_ohne_angabe_offen(self):
        self.assertEqual(zf.fenster(), (None, None))

    def test_tage_zaehlt_rueckwaerts(self):
        von, bis = zf.fenster(tage=30)
        self.assertIsNotNone(von)
        self.assertIsNone(bis)
        self.assertAlmostEqual((zf.jetzt() - von).days, 30, delta=1)

    def test_seit_und_bis_als_datum(self):
        von, bis = zf.fenster(seit="2026-09-01", bis="2026-09-30")
        self.assertEqual(von, dt.datetime(2026, 9, 1,
                                          tzinfo=dt.timezone.utc))
        # Ein blosses Datum als `bis` meint den GANZEN Tag. Die Pruefung
        # auf .date() allein liess offen, ob die Uhrzeit dabei 00:00 ist -
        # dann faellt der ganze 30. September aus dem Fenster, und das
        # merkt niemand. Deshalb die Uhrzeit mit.
        self.assertEqual(bis, dt.datetime(2026, 9, 30, 23, 59, 59, 999999,
                                          tzinfo=dt.timezone.utc))

    def test_bis_mit_uhrzeit_bleibt_die_uhrzeit(self):
        # Tagesende NUR beim reinen Datum. Wer eine Uhrzeit angibt, meint
        # sie.
        von, bis = zf.fenster(bis="2026-09-30T08:00:00+00:00")
        self.assertIsNone(von)
        self.assertEqual(bis, dt.datetime(2026, 9, 30, 8,
                                          tzinfo=dt.timezone.utc))

    def test_tage_und_seit_zusammen_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            zf.fenster(tage=30, seit="2026-09-01")

    def test_tage_und_bis_zusammen_ist_ein_fehler(self):
        # `tage` zaehlt von JETZT rueckwaerts. Mit einem `bis` in der
        # Vergangenheit liegt der Anfang hinter dem Ende, und das Fenster
        # ist still leer - kein Fehler, keine Meldung, nur keine Zahlen.
        # Genauso unbestimmt wie tage+seit, also genauso ein Fehler.
        with self.assertRaises(ValueError):
            zf.fenster(tage=30, bis="2026-01-01")

    def test_tage_allein_bleibt_erlaubt(self):
        von, bis = zf.fenster(tage=30)
        self.assertIsNotNone(von)
        self.assertIsNone(bis)


class TestImFenster(unittest.TestCase):

    def setUp(self):
        self.von = dt.datetime(2026, 9, 10, tzinfo=dt.timezone.utc)
        self.bis = dt.datetime(2026, 9, 20, tzinfo=dt.timezone.utc)

    def test_offenes_fenster_laesst_alles_durch(self):
        self.assertTrue(zf.im_fenster({"zeit": "2020-01-01T00:00:00+00:00"},
                                      None, None))

    def test_drin_und_draussen(self):
        self.assertTrue(zf.im_fenster({"zeit": "2026-09-15T12:00:00+00:00"},
                                      self.von, self.bis))
        self.assertFalse(zf.im_fenster({"zeit": "2026-09-01T12:00:00+00:00"},
                                       self.von, self.bis))
        self.assertFalse(zf.im_fenster({"zeit": "2026-09-25T12:00:00+00:00"},
                                       self.von, self.bis))

    def test_unlesbare_zeit_faellt_raus(self):
        # Eine Zeile ohne lesbare Zeit ist im Fenster nicht belegbar. Sie
        # durchzulassen hiesse, sie jedem Fenster zuzuschlagen.
        self.assertFalse(zf.im_fenster({"zeit": ""}, self.von, self.bis))

    def test_unlesbare_zeit_bleibt_bei_offenem_fenster(self):
        self.assertTrue(zf.im_fenster({"zeit": ""}, None, None))


if __name__ == "__main__":
    unittest.main()
