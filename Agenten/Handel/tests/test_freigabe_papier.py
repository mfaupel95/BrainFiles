"""Tests fuer das Freigabefenster: eine stillgelegte Spur darf nie live werden.

Anlass: Max' Anweisung "In Freigabe.py Spur 3 Kraken Papier schalten" und der
Nachtrag, sie lieber zu **sperren** als Papier freizugeben.

Der Test prueft die **Mechanik**, nicht den heutigen Zustand der Dateien.
Das ist Absicht: `stillgelegt` in `kraken/wachen.json` ist ein Schalter, den
Max von Hand umlegt (am 12.09.2026 genau das getan). Ein Test, der den
aktuellen Wert der echten Datei behauptet, bricht bei jeder solchen Entscheidung
- und dann wird er abgeschwaecht statt ernst genommen. Die Vorlage kommt aus
der echten Datei, die Behauptung aus der Ueberschreibung.

Ohne Fenster: pruefe() rechnet, haelt_alles() und gerissene_grenzen() sind
genau das, was der Knopf auswertet.
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

BESTAND = {"gebunden": 0.0, "offene_positionen": 0, "verlust_gesamt": 0.0}


def vorlage():
    """Die Kraken-Wachen als Vorlage - nur als Form, nicht als Behauptung."""
    return copy.deepcopy(freigabe.lade_wachen("kraken"))


def wachen(**ueber):
    w = vorlage()
    for schluessel, wert in ueber.items():
        if wert is None:
            w.pop(schluessel, None)
        else:
            w[schluessel] = wert
    return w


def pruefung(w, auftrag=None):
    a = dict(auftrag or freigabe.BEISPIEL["kraken"][0])
    r = freigabe.RECHNER["kraken"](a, w)
    return freigabe.pruefe(r, w, "kraken", BESTAND)


def zeilenstand(p):
    return {n: ok for n, _i, _s, ok in p}


class StillgelegtSperrt(unittest.TestCase):

    def test_stillgelegt_erzeugt_eine_harte_zeile(self):
        p = pruefung(wachen(stillgelegt=True, handel_erlaubt=True,
                            freigabe={"erfuellt": True}))
        self.assertIn("Stillgelegt", zeilenstand(p))
        self.assertFalse(zeilenstand(p)["Stillgelegt"])
        # Harte Zeile = Knopf gesperrt. Nicht Zustandszeile, sonst waere es
        # wieder Papier statt gesperrt.
        self.assertIn("Stillgelegt", freigabe.gerissene_grenzen(p))
        self.assertNotIn("Stillgelegt", freigabe.ZUSTANDSZEILEN)

    def test_auch_mit_umgelegten_schaltern_bleibt_es_gesperrt(self):
        """Wer handel_erlaubt und die Freigabe umlegt, darf eine stillgelegte
        Spur trotzdem nicht scharf schalten."""
        p = pruefung(wachen(stillgelegt=True, handel_erlaubt=True,
                            freigabe={"erfuellt": True},
                            journal_zweitziel="Q:\\irgendwo"))
        self.assertFalse(freigabe.haelt_alles(p), "stillgelegt schlaegt jeden Schalter")
        self.assertIn("Stillgelegt", freigabe.gerissene_grenzen(p))

    def test_ohne_feld_bleibt_die_spur_live_faehig(self):
        """Gegenprobe: die Sperre trifft nur, wo das Feld gesetzt ist."""
        p = pruefung(wachen(stillgelegt=None, handel_erlaubt=True,
                            freigabe={"erfuellt": True},
                            journal_zweitziel="Q:\\irgendwo"))
        self.assertNotIn("Stillgelegt", zeilenstand(p))
        self.assertTrue(freigabe.haelt_alles(p))

    def test_false_ist_kein_stillgelegt(self):
        p = pruefung(wachen(stillgelegt=False, handel_erlaubt=True,
                            freigabe={"erfuellt": True}))
        self.assertNotIn("Stillgelegt", zeilenstand(p))
        self.assertNotIn("Stillgelegt", freigabe.gerissene_grenzen(p))

    def test_nur_die_stillgelegte_spur_ist_gesperrt(self):
        """Die Mechanik kennt keine Spur und keine Liste - sie liest das Feld."""
        self.assertTrue(freigabe.stillgelegt({"stillgelegt": True}))
        self.assertFalse(freigabe.stillgelegt({"stillgelegt": False}))
        self.assertFalse(freigabe.stillgelegt({}))

    def test_echte_kraken_wachen_sind_lesbar(self):
        """Nur die Form: die Datei muss existieren und das Feld ein Schalter
        sein. Welchen Wert er hat, entscheidet Max - nicht dieser Test."""
        w = freigabe.lade_wachen("kraken")
        self.assertIn("stillgelegt", w)
        self.assertIsInstance(w["stillgelegt"], bool)
        self.assertIn("waehrung", w)


if __name__ == "__main__":
    unittest.main(verbosity=2)
