"""Mehrere Spuren auf einmal freigeben (Auftrag Max 05.10.2026).

Drei Eigenschaften sind je eine Fehlerquelle:

1. Eine Spur OHNE wartende Anfrage darf nicht mitgenommen werden - der
   Dialog wuerde eine Frage stellen, die niemand beantworten kann.
2. Die Dauer ist die KUERZESTE der Anfragen. Sonst bekaeme eine Spur mit
   30-Minuten-Anfrage eine Stunde, die niemand bestellt hat.
3. Jede Spur einzeln oeffnen, nicht im Buendel: `freigabefenster.oeffnen()`
   nimmt die Sperre je Spur, und ein Buendel wuerde den Rest verpassen.

Direkt ausfuehrbar:  python tests/test_leitstand_freigaben_mehrfach.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import leitstand_freigaben as lf                                # noqa: E402


class Fenster:
    """Attrappe eines freigabefenster.Fenster."""

    def __init__(self, d):
        self.d = d

    def anfrage_offen(self):
        return "anfrage_bis" in self.d

    def offen(self):
        return "offen_bis" in self.d


class Wartend:
    def __init__(self, offen):
        self._offen = set(offen)

    def lade(self, spur):
        if spur in self._offen:
            return Fenster({"anfrage_bis": "jetzt"})
        return Fenster({})

    def oeffnen(self, spur, stunden, wer=""):
        if spur not in self._offen:
            return None
        self._offen.discard(spur)
        return stunden * 60


class Mehrfach(unittest.TestCase):
    def setUp(self):
        self.aufrufe = []

    def freigab(self, offen, spuren, stunden=2):
        """freigeben_mehrfach gegen eine Attrappe fahren."""
        w = Wartend(offen)
        with patch.object(lf.ff, "lade", side_effect=w.lade), \
             patch.object(lf, "freigeben",
                          side_effect=lambda s, st: self._echt(s, st, w)):
            return lf.freigeben_mehrfach(spuren, stunden), w

    def _echt(self, spur, stunden, w):
        minuten = w.oeffnen(spur, stunden, wer="leitstand")
        self.aufrufe.append((spur, minuten))
        if minuten is None:
            return "Anfrage war verfallen — nichts geändert"
        return "%s scharf für %d:%02d h" % (spur, minuten // 60, minuten % 60)

    def test_zwei_spuren_werden_beide_geoeffnet(self):
        ergebnis, _w = self.freigab({"a", "b"}, ["a", "b"])
        self.assertEqual([s for s, _t in ergebnis], ["a", "b"])
        self.assertTrue(all("scharf für" in t for _s, t in ergebnis))

    def test_ohne_anfrage_wird_nichts_geoeffnet(self):
        ergebnis, _w = self.freigab(set(), ["a", "b"])
        for _s, t in ergebnis:
            self.assertIn("verfallen", t)
        # `oeffnen` wird wohl aufgerufen (das ist der Weg), gibt aber None
        # zurueck - es wurde also nichts geschrieben. Zaehlt werden die
        # Minuten, nicht die Aufrufe.
        self.assertEqual([m for _s, m in self.aufrufe], [None, None])

    def test_gemischt_nur_die_mit_anfrage(self):
        ergebnis, _w = self.freigab({"a"}, ["a", "b"])
        nach = dict(ergebnis)
        self.assertIn("scharf für", nach["a"])
        self.assertNotIn("scharf für", nach["b"])

    def test_meldung_nennt_erfolge_und_misserfolg(self):
        m = lf.mehrfach_meldung([("a", "a scharf für 1:00 h"),
                                 ("b", "Sperre belegt — bitte erneut")])
        self.assertIn("1 freigegeben", m)
        self.assertIn("Sperre belegt", m)

    def test_meldung_bei_vollstaendigem_erfolg(self):
        m = lf.mehrfach_meldung([("a", "a scharf für 1:00 h"),
                                 ("b", "b scharf für 1:00 h")])
        self.assertIn("2 freigegeben", m)
        self.assertNotIn("|", m)

    def test_meldung_ohne_ergebnis(self):
        self.assertEqual(lf.mehrfach_meldung([]), "")

    def test_leere_liste(self):
        ergebnis, _w = self.freigab({"a"}, [])
        self.assertEqual(ergebnis, [])


class KuerzesteDauer(unittest.TestCase):
    """Wer drei freigibt, will nicht die laengste Dauer als Mindestmass."""

    class F:
        def __init__(self, minuten):
            self.d = {"anfrage_dauer_minuten": minuten}

    def test_minimum_wird_genommen(self):
        werte = {"a": 90, "b": 30, "c": 60}
        with patch.object(lf.ff, "lade",
                          side_effect=lambda s: self.F(werte[s])):
            stunden = min(lf.vorbelegte_stunden(lf.ff.lade(s))
                          for s in ("a", "b", "c"))
        self.assertEqual(stunden, 1)          # 30 min -> 1 h (gerundet)

    def test_alle_gleich(self):
        with patch.object(lf.ff, "lade", side_effect=lambda s: self.F(120)):
            stunden = min(lf.vorbelegte_stunden(lf.ff.lade(s))
                          for s in ("a", "b"))
        self.assertEqual(stunden, 2)


class KnopfPfad(unittest.TestCase):
    """Der Reiter darf eine Auswahl OHNE Anfrage nicht zum Dialog schicken."""

    class Reiter:
        pass

    def test_gewaehlt_viele_liest_die_auswahl(self):
        r = self.Reiter()
        r.tabelle = type("T", (), {"auswahl": lambda self: [("a", 1),
                                                             ("b", 2)]})()
        self.assertEqual(lf.FreigabenReiter.gewaehlt_viele(r), ["a", "b"])

    def test_wartende_filtert_aus(self):
        r = self.Reiter()
        with patch.object(lf.ff, "lade",
                          side_effect=lambda s: Fenster({"anfrage_bis": "j"}
                                                         if s == "a" else {})):
            wartend = lf.FreigabenReiter._wartende(r, ["a", "b", "c"])
        self.assertEqual(wartend, ["a"])

    def test_wartende_verschluckt_einen_fehler(self):
        # Eine kaputte Spur darf den ganzen Vorgang nicht abbrechen - die
        # anderen werden trotzdem freigegeben.
        r = self.Reiter()

        def lade(s):
            if s == "kaputt":
                raise ValueError("wachen.json nicht lesbar")
            return Fenster({"anfrage_bis": "j"} if s == "a" else {})

        with patch.object(lf.ff, "lade", side_effect=lade):
            wartend = lf.FreigabenReiter._wartende(r, ["a", "kaputt"])
        self.assertEqual(wartend, ["a"])


if __name__ == "__main__":
    unittest.main()
