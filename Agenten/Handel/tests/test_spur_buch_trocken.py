"""Ein trockener Zulauf ist keine tote Spur (spur_buch.zyklus).

Befund 23.09.2026: robinhood_radar lief alle 15 Minuten ("(papier) ok" im
Dauerlauf-Log), aber sein Zustand stand 6,8 Stunden still - weil
spur_buch.zyklus im Zweig "keine Daten" ohne schreibe_zustand() zurueckkehrte.
Die stille-spuren-wache liest das Alter von `letzter_lauf` und meldete deshalb
"TOT" fuer eine gesunde Spur.

Der Test baut eine Spur im Tempordner (eigene Wachen, eigener Zustand, eigenes
Spiegelziel) und laesst den ECHTEN zyklus() laufen - ohne Netz, ohne echte
Spurdatei. Ein Waechter prueft, dass die echten Spuren unberuehrt bleiben.
"""
import json
import os
import sys
import tempfile
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)
import spur_buch  # noqa: E402

assert spur_buch.__file__.startswith(HANDEL), spur_buch.__file__

_ECHT = os.path.join(HANDEL, "robinhood_radar")


def _stand():
    raus = {}
    for datei in os.listdir(_ECHT):
        p = os.path.join(_ECHT, datei)
        if os.path.isfile(p):
            raus[datei] = os.path.getsize(p)
    return raus


_VORHER = None


def setUpModule():
    global _VORHER
    _VORHER = _stand()


def tearDownModule():
    nachher = _stand()
    if nachher != _VORHER:
        neu = set(nachher) - set(_VORHER)
        geaendert = {k for k in set(nachher) & set(_VORHER)
                     if nachher[k] != _VORHER[k]}
        raise AssertionError("Tests haben die echte Spur veraendert! "
                             "neu=%s geaendert=%s" % (neu, geaendert))


class TrockenerZyklusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="spurbuch_")
        self.spur = os.path.join(self.tmp, "probespur")
        os.makedirs(self.spur)
        self.ziel = os.path.join(self.tmp, "spiegel")
        w = {"journal_zweitziel": self.ziel, "grund": "probe",
             "herzschlag_max_minuten": 180, "risiko_je_position_usd": 5.0,
             "max_offene_positionen": 2, "stop_prozent": 10.0,
             "cr": 2.0}
        self._schreibe("wachen.json", w)
        self._schreibe("zustand.json", {"positionen": [],
                                        "letzter_lauf": None})

    def _schreibe(self, name, inhalt):
        with open(os.path.join(self.spur, name), "w", encoding="utf-8") as f:
            json.dump(inhalt, f)

    def _zustand(self):
        with open(os.path.join(self.spur, "zustand.json"),
                  encoding="utf-8") as f:
            return json.load(f)

    def _lauf(self, modus, daten, fehler=None):
        def quelle(w):
            return daten, {}, list(fehler or [])
        return spur_buch.zyklus(self.spur, quelle, lambda d, w: None, modus,
                                ereignis_name="handel/probespur",
                                datenlage=lambda: {"zu wenige": 3})

    def test_keine_daten_schreibt_den_herzschlag(self):
        self._lauf("papier", {})
        z = self._zustand()
        self.assertIsNotNone(z.get("letzter_lauf"),
                             "der Zyklus ist gelaufen - das muss sichtbar sein")
        self.assertTrue(z["datenlage"]["keine_daten"])
        self.assertEqual(z["datenlage"]["hinweis"], {"zu wenige": 3})

    def test_keine_daten_mit_grund_landet_im_zustand(self):
        self._lauf("papier", {}, fehler=["Radar-Datenbank nicht lesbar"])
        self.assertIn("nicht lesbar", self._zustand()["datenlage"]["grund"])

    def test_keine_daten_wird_gespiegelt(self):
        self._lauf("papier", {})
        self.assertTrue(os.path.isfile(os.path.join(self.ziel,
                                                    "zustand.json")),
                        "Bedingung 4 gilt auch fuer den trockenen Zyklus")

    def test_die_vorschau_schreibt_weiterhin_nichts(self):
        self._lauf("vorschau", {})
        self.assertIsNone(self._zustand().get("letzter_lauf"))

    def test_mit_daten_steht_die_kandidatenzahl_im_zustand(self):
        self._lauf("papier", {"0xabc": {"preis": 1.0}})
        z = self._zustand()
        self.assertFalse(z["datenlage"]["keine_daten"])
        self.assertEqual(z["datenlage"]["kandidaten"], 1)


if __name__ == "__main__":
    unittest.main()