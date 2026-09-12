"""Tests fuer das Freigabefenster - Spur 3 (Kraken) darf nie live werden.

Anlass: Max' Anweisung "In Freigabe.py Spur 3 Kraken Papier schalten". Der
Kern ist nicht der heutige Zustand (handel_erlaubt und freigabe.erfuellt stehen
ohnehin auf false), sondern die Frage, was passiert, wenn jemand eines davon von
Hand umlegt: Eine stillgelegte Spur darf **nie** live freigegeben werden, und
das Fenster soll das aus der wachen.json der Spur lesen - nicht aus einer Liste
im Code, die beim Wiederanschalten vergessen wird.

Ohne Fenster: pruefe() rechnet, haelt_alles() entscheidet. Das ist genau der
Pfad, den auch der Knopf nimmt.
"""

import copy
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import freigabe                                                # noqa: E402

AUFTRAG = {"inst": "XXBTZEUR", "einstieg": 66748.2, "stop_pct": 7.0,
           "cr": 2.0, "eur": 50}
BESTAND = {"gebunden": 0.0, "offene_positionen": 0, "verlust_gesamt": 0.0}


def rechnung_und_pruefung(spur, auftrag=None, wachen=None):
    w = copy.deepcopy(wachen if wachen is not None else freigabe.lade_wachen(spur))
    a = dict(auftrag or AUFTRAG)
    r = freigabe.RECHNER[spur](a, w)
    return w, freigabe.pruefe(r, w, spur, BESTAND)


class KrakenIstPapier(unittest.TestCase):

    def test_stillgelegt_steht_als_eigene_zeile_in_den_wachen(self):
        self.assertTrue(freigabe.stillgelegt(freigabe.lade_wachen("kraken")))

    def test_kraken_wird_gesperrt_nicht_als_live_ausgewiesen(self):
        w, p = rechnung_und_pruefung("kraken")
        zeilen = {n: ok for n, _i, _s, ok in p}
        self.assertIn("Stillgelegt", zeilen)
        self.assertFalse(zeilen["Stillgelegt"])
        self.assertFalse(freigabe.haelt_alles(p), "Kraken darf nie live sein")
        # Der Knopf sperrt: "Stillgelegt" ist keine Zustandszeile mehr, es
        # zaehlt als harte Zeile - und genau die sperrt den Knopf in _neu().
        self.assertIn("Stillgelegt", freigabe.gerissene_grenzen(p))
        self.assertNotIn("Stillgelegt", freigabe.ZUSTANDSZEILEN,
                         "sonst waere es wieder Papier statt gesperrt")

    def test_auch_mit_umgelegten_schaltern_bleibt_kraken_gesperrt(self):
        """Der eigentliche Test: wer handel_erlaubt und die Freigabe umlegt,
        darf die stillgelegte Spur trotzdem nicht scharf schalten."""
        w = copy.deepcopy(freigabe.lade_wachen("kraken"))
        w["handel_erlaubt"] = True
        w["freigabe"] = dict(w.get("freigabe") or {}, erfuellt=True)
        w["journal_zweitziel"] = "Q:\\irgendwo"
        _w, p = rechnung_und_pruefung("kraken", wachen=w)
        self.assertFalse(freigabe.haelt_alles(p),
                         "stillgelegt schlaegt jeden Schalter")
        self.assertFalse({n: ok for n, _i, _s, ok in p}["Stillgelegt"])
        self.assertIn("Stillgelegt", freigabe.gerissene_grenzen(p))

    def test_ohne_stillgelegt_entscheidet_wie_bisher(self):
        """Gegenprobe: Die Sperre trifft nur stillgelegte Spuren. Eine Spur
        ohne das Feld bleibt live-faehig, wenn alles haelt."""
        w = copy.deepcopy(freigabe.lade_wachen("spot"))
        w["handel_erlaubt"] = True
        w["freigabe"] = dict(w.get("freigabe") or {}, erfuellt=True)
        w.pop("stillgelegt", None)
        auftrag = {"inst": "SOL-USDT", "einstieg": 168.42, "stop_pct": 6.0,
                   "cr": 2.0, "usd": 50}
        _w, p = rechnung_und_pruefung("spot", auftrag=auftrag, wachen=w)
        self.assertNotIn("Stillgelegt", {n for n, _i, _s, _o in p})
        self.assertTrue(freigabe.haelt_alles(p),
                        "ohne stillgelegt muss live moeglich bleiben")
        self.assertEqual(freigabe.gerissene_grenzen(p), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
