"""Stop-Deckung im Live-Zweig: der Stop wird nicht nur gesetzt, sondern
VERIFIZIERT - und die MENGE wird verglichen (T-323, 05.10.2026).

Hintergrund
-----------
Am 05.10.2026 stand die Behauptung "der Schutz-Stop ist nicht lesbar" im
Raum. Sie war falsch geraten: `/editorder` ist der SPOT-Endpunkt, der
Futures-Dienst nennt den Weg `/openorders`. Wer den falschen benutzt,
bekommt `requiredArgumentMissing`, meldet "nicht lesbar" und haelt eine
geschuetzte Position fuer ungeschuetzt.

Zwei Regeln werden hier festgenagelt:

  1. Ohne erkannten Schutz wird der Stop NACHGESETZT - nicht gemeldet und
     nicht weitergehandelt. Ein Stop, der nur im Buch steht, ist kein Schutz.
  2. "Ein Treffer" gilt nicht als Deckung. T-323 belegte 145 Kontrakte mit
     einem Stop ueber 126: 19 Kontrakte liefen ungeschuetzt, ohne dass ein
     Abruf das anzeigt. Deshalb wird die Menge durchgereicht.

Kein Netz, keine Order, keine echte Datei: alle Boersen-Funktionen sind
Attrappen, und der Modulwaechter vergleicht am Ende Dateiliste und Groessen
des echten Spurenordners.

Lauf (aus dem omniquant-Ordner):
    ../scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
"""

import os
import sys
import unittest
from unittest import mock

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
while HIER in sys.path:
    sys.path.remove(HIER)
sys.path.insert(0, HIER)          # eigene Spur ZULETZT vorne - nicht scanner/

import kraken_perp as kp                           # noqa: E402
import live_perp as lp                              # noqa: E402

assert kp.__file__.startswith(HIER), "falsches kraken_perp: %s" % kp.__file__

_SPURORDNER = HIER


def _stand():
    aus = {}
    for name in sorted(os.listdir(_SPURORDNER)):
        p = os.path.join(_SPURORDNER, name)
        if os.path.isfile(p):
            aus[name] = os.path.getsize(p)
    return aus


_STAND_VOR = None


def setUpModule():
    global _STAND_VOR
    _STAND_VOR = _stand()


def tearDownModule():
    nach = _stand()
    neu = {k: v for k, v in nach.items() if _STAND_VOR.get(k) != v}
    assert not neu, "Tests haben in den echten Spurenordner geschrieben: %s" % neu


class _HandelnAttrappe:
    """Nur was `stopdeckung_pruefen` schreibt - kein echtes Journal."""

    def __init__(self):
        self.zeilen = []

    def _jetzt(self):
        return "2026-10-05T06:00:00+00:00"

    def _heute(self):
        return "2026-10-05"

    def journal(self, **felder):
        self.zeilen.append(felder)


def _p(**felder):
    pos = {"inst": "NEAR-USDC", "seite": "long", "kontrakte": 61,
           "stop": 4.2856, "ziel": 5.592, "modus": "live",
           "boerse": "kraken_futures"}
    pos.update(felder)
    return pos


class _Setter:
    """Zaehlt die Stop-Aufträge und merkt sich die letzte OrderId."""

    def __init__(self, antwort=None):
        self.rufe = []
        self.antwort = antwort or {"sendStatus": {"order_id": "neu-4711"}}

    def __call__(self, inst, kontrakte, stop, **kw):
        self.rufe.append((inst, kontrakte, stop))
        return self.antwort


class DeckungVorhandenTest(unittest.TestCase):
    """Der erkannte Zustand wird durchgereicht - ohne eigene Order."""

    def setUp(self):
        self.h = _HandelnAttrappe()
        self.setter = _Setter()

    def _mit(self, gedeckt):
        return (lambda inst, kontrakte=None, fuer_ausstieg=True: gedeckt)

    def test_gedeckte_position_bekommt_keine_zweite_order(self):
        p = _p()
        with mock.patch.object(kp, "schutzstop_vorhanden",
                                        self._mit(True)), \
                mock.patch.object(kp, "stop_setzen", self.setter):
            self.assertTrue(lp.stopdeckung_pruefen(self.h, p))
        self.assertEqual(self.setter.rufe, [], "eine gedeckte Position wird "
                                                "noch einmal geschuetzt")
        self.assertEqual(self.h.zeilen, [], "kein Fehler, kein Geraeusch")

    def test_die_menge_wird_durchgereicht(self):
        """Ohne den Mengenvergleich waere ein zu kleiner Stop ein Treffer."""
        p = _p()
        gesehen = []
        def spion(inst, kontrakte=None, fuer_ausstieg=True):
            gesehen.append((inst, kontrakte))
            return False
        with mock.patch.object(kp, "schutzstop_vorhanden", spion), \
                mock.patch.object(kp, "stop_setzen", self.setter):
            lp.stopdeckung_pruefen(self.h, p)
        self.assertEqual(gesehen[0], ("NEAR-USDC", 61),
                         "die Kontraktzahl muss in die Pruefung")

    def test_fehlender_stop_wird_mit_der_vollen_menge_nachgesetzt(self):
        p = _p()
        with mock.patch.object(kp, "schutzstop_vorhanden",
                                        self._mit(False)), \
                mock.patch.object(kp, "stop_setzen", self.setter):
            lp.stopdeckung_pruefen(self.h, p)
        self.assertEqual(self.setter.rufe, [("NEAR-USDC", 61, 4.2856)])
        self.assertEqual(p["stop_algo_id"], "neu-4711")

    def test_nachsatz_wird_nachkontrolliert(self):
        """Erst setzen ist nicht Beweis - die Menge muss danach gemessen sein."""
        p = _p()
        antworten = iter([False, True])
        with mock.patch.object(
                kp, "schutzstop_vorhanden",
                lambda inst, kontrakte=None, fuer_ausstieg=True:
                    next(antworten)), \
                mock.patch.object(kp, "stop_setzen", self.setter):
            self.assertTrue(lp.stopdeckung_pruefen(self.h, p))
        self.assertEqual(len(self.setter.rufe), 1)

    def test_zu_kleiner_stop_wird_als_luecke_gemeldet(self):
        """Der T-323-Fall: Stop liegt an, deckt aber nicht die ganze Menge."""
        p = _p()
        antworten = iter([False, False])
        with mock.patch.object(
                kp, "schutzstop_vorhanden",
                lambda inst, kontrakte=None, fuer_ausstieg=True:
                    next(antworten)), \
                mock.patch.object(kp, "stop_setzen", self.setter):
            self.assertFalse(lp.stopdeckung_pruefen(self.h, p))
        self.assertTrue(any("deckt aber die ganze Position nicht"
                            in (z.get("grund") or "") for z in self.h.zeilen),
                        "eine zu kleine Deckung ist eine Luecke, kein Erfolg")


class LueckeTest(unittest.TestCase):
    """Kein Stop, kein Setzen, keine Order - aber eine benannte Luecke."""

    def setUp(self):
        self.h = _HandelnAttrappe()
        self.setter = _Setter()

    def test_position_ohne_stop_wird_nicht_erfunden(self):
        p = _p(stop=None)
        with mock.patch.object(
                kp, "schutzstop_vorhanden",
                lambda inst, kontrakte=None, fuer_ausstieg=True: False), \
                mock.patch.object(kp, "stop_setzen", self.setter):
            self.assertFalse(lp.stopdeckung_pruefen(self.h, p))
        self.assertEqual(self.setter.rufe, [],
                         "ohne Stoppreis gibt es nichts zu setzen")
        self.assertTrue(any("KEIN Stop im Buch" in (z.get("grund") or "")
                            for z in self.h.zeilen))

    def test_nicht_pruefbare_deckung_wird_laut_und_brieft_nicht(self):
        def kaputt(inst, kontrakte=None, fuer_ausstieg=True):
            raise OSError("no route to host")
        p = _p()
        with mock.patch.object(kp, "schutzstop_vorhanden", kaputt), \
                mock.patch.object(kp, "stop_setzen", self.setter):
            self.assertFalse(lp.stopdeckung_pruefen(self.h, p))
        self.assertEqual(self.setter.rufe, [],
                         "ein Netzfehler darf keinen Stop doppelt setzen")
        self.assertTrue(any("nicht pruefbar" in (z.get("grund") or "")
                            for z in self.h.zeilen),
                        "Stille waere hier die teure Variante")

    def test_fehlgeschlagener_nachsatz_benennt_die_luecke(self):
        def kaputt(inst, kontrakte, stop, **kw):
            raise RuntimeError("margin required")
        p = _p()
        with mock.patch.object(
                kp, "schutzstop_vorhanden",
                lambda inst, kontrakte=None, fuer_ausstieg=True: False), \
                mock.patch.object(kp, "stop_setzen", kaputt):
            self.assertFalse(lp.stopdeckung_pruefen(self.h, p))
        self.assertTrue(any("SICHERHEITSLÜCKE" in (z.get("grund") or "")
                            for z in self.h.zeilen))


class AusstiegPrueftZuerstDieDeckungTest(unittest.TestCase):
    """Die Reihenfolge ist die Regel: erst Schutz, dann Ausstieg."""

    def test_ausstieg_prueft_die_deckung_vor_der_kursabfrage(self):
        z = {"positionen": [_p()]}
        reihenfolge = []

        def deckung(handeln, p):
            reihenfolge.append("deckung")
            return True

        def kurs(inst, fuer_ausstieg=True):
            reihenfolge.append("kurs")
            return 4.95

        with mock.patch.object(lp, "stopdeckung_pruefen", deckung), \
                mock.patch.object(lp, "markte_laden", lambda: 0), \
                mock.patch.object(kp, "offene_positionen", return_value=[{"side": "long", "size": 61}]), \
                mock.patch.object(kp, "letzter_kurs", kurs), \
                mock.patch.object(
                    kp, "schutzstop_vorhanden",
                    lambda *a, **k: True):
            lp.pruefe_ausstiege(_HandelnAttrappe(), {}, z)
        self.assertEqual(reihenfolge[0], "deckung",
                         "ohne Deckung ist die Kursabfrage verfrueht")

    def test_geisterposition_wird_gemeldet_ohne_neuen_stop_oder_ausstieg(self):
        p = _p()
        z = {"positionen": [p]}
        h = _HandelnAttrappe()
        with mock.patch.object(kp, "offene_positionen", return_value=[]), \
                mock.patch.object(lp, "stopdeckung_pruefen") as deckung, \
                mock.patch.object(kp, "letzter_kurs", return_value=5.0) as kurs, \
                mock.patch.object(kp, "markt_verkauf") as verkauf:
            lp.pruefe_ausstiege(h, {}, z)
        deckung.assert_not_called()
        kurs.assert_not_called()
        verkauf.assert_not_called()
        self.assertEqual(z["positionen"], [p])
        self.assertTrue(any("GEISTERPOSITION" in (r.get("grund") or "")
                            for r in h.zeilen))

    def test_mengenabweichung_wird_gemeldet_und_nicht_gehandelt(self):
        p = _p()
        h = _HandelnAttrappe()
        z = {"positionen": [p]}
        with mock.patch.object(kp, "offene_positionen",
                               return_value=[{"side": "long", "size": 60}]), \
                mock.patch.object(lp, "stopdeckung_pruefen") as deckung, \
                mock.patch.object(kp, "letzter_kurs") as kurs, \
                mock.patch.object(kp, "markt_verkauf") as verkauf:
            lp.pruefe_ausstiege(h, {}, z)
        deckung.assert_not_called()
        kurs.assert_not_called()
        verkauf.assert_not_called()
        self.assertTrue(any("Boerse long 60" in (r.get("grund") or "")
                            for r in h.zeilen))

    def test_papierpositionen_werden_nicht_geprueft(self):
        """Nur `modus: live` - eine Papierposition hat keinen Boersen-Stop."""
        z = {"positionen": [_p(modus="papier")]}
        with mock.patch.object(lp, "stopdeckung_pruefen") as deckung:
            lp.pruefe_ausstiege(_HandelnAttrappe(), {}, z)
        deckung.assert_not_called()


if __name__ == "__main__":
    unittest.main()
