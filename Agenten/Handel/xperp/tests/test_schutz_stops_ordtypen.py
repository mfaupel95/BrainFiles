"""Tests: schutz_stops liest ALLE ordTypes (T-278, 01.10.2026).

ANLASS, gemessen an der Boerse: das Uebernahme-Werkzeug meldete fuer ZEC, VVV
und ADA "Stop an der Boerse: fehlt - wuerde gestellt", waehrend langst OCOs
mit slTriggerPx (ZEC 38 K @ sl 1316.44, ADA 55 K @ sl 0.2286) und
move_order_stop (VVV, ADA) offen standen. Die Pruefung fragte nur
ordType=conditional. Folge: zwei Stops je Position, der engere feuert zuerst,
der Schutz zog sich unbemerkt von -8.6 % auf -2.7 % zusammen.

Die Tests tauschen nur okxf._mit_wiederholung (die Netznaht) - es geht NIE
eine echte Anfrage raus, und es wird NIE eine Order gestellt.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parent
sys.path.insert(0, str(HANDEL))
sys.path.insert(0, str(SPUR))

import okxf                                                      # noqa: E402

ZEC = "ZEC-USD_UM_XPERP-310510"

# So hat die Boerse am 01.10.2026 fuer ZEC geantwortet: conditional leer,
# die Sicherung sitzt im ordType oco.
ANTWORT = {
    "conditional": [],
    "oco": [{"algoId": "1", "slTriggerPx": "1316.44", "sz": "38"}],
    "move_order_stop": [],
    "trigger": [{"algoId": "2"}],            # nackter trigger, KEIN sl-Feld
}


def _faktnet(p, signiert=False, wirft=(), antwort=None):
    antwort = ANTWORT if antwort is None else antwort
    if wirft:
        raise RuntimeError("Netzstoerung")
    typ = p.split("ordType=")[1].split("&")[0]
    return [dict(s) for s in antwort.get(typ, [])]


class FrageAllerTypenTest(unittest.TestCase):
    def test_jeder_ordtype_wird_einzeln_gefragt(self):
        gefragte = []

        def zaehler(p, signiert=False):
            gefragte.append(p)
            return _faktnet(p, signiert=signiert)

        with patch.object(okxf, "_mit_wiederholung", side_effect=zaehler):
            fund = okxf.schutz_stops(ZEC)
        self.assertEqual(len(okxf.ALGO_ORDTYPES), len({g.split("ordType=")[1].split("&")[0] for g in gefragte}))
        for typ in okxf.ALGO_ORDTYPES:
            self.assertTrue(any(("ordType=" + typ) in g for g in gefragte), typ)
        self.assertTrue(all(ZEC in g for g in gefragte), "instId muss an jeder Frage haengen")
        self.assertEqual({"oco", "trigger"}, {s["ordType"] for s in fund},
                         "alle Funde kommen zusammen zurueck")


class StopImAnderenTypTest(unittest.TestCase):
    """Regression T-278: ein Stop, der nur als OCO existiert, MUSS zaehlen."""

    def setUp(self):
        import handeln as h
        self.h = h

    def test_oco_stop_ist_vorhanden(self):
        roh_pos = {"instId": ZEC, "slTriggerPx": ""}
        with patch.object(self.h.okxf, "_mit_wiederholung", side_effect=_faktnet):
            self.assertTrue(self.h._stop_vorhanden(ZEC, roh_pos))

    def test_gegenprobe_nur_conditional_sieht_den_oco_nicht(self):
        # Die alte Luecke, ausdruecklich belegt: wer nur conditional fragt,
        # findet den OCO-Stop nicht und stellt einen zweiten daneben.
        roh_pos = {"instId": ZEC, "slTriggerPx": ""}
        with patch.object(self.h.okxf, "_mit_wiederholung", side_effect=_faktnet):
            frueher = self.h.okxf.schutz_stops(ZEC, ordtypes=("conditional",))
        self.assertEqual([], [s for s in frueher if str(s.get("slTriggerPx") or "").strip()])


class FehlerbehandlungTest(unittest.TestCase):
    def test_alles_fehlt_ohne_beweis_wirft(self):
        def kaputt(p, signiert=False):
            raise RuntimeError("Netzstoerung")
        with patch.object(okxf, "_mit_wiederholung", side_effect=kaputt):
            with self.assertRaises(RuntimeError):
                okxf.schutz_stops(ZEC)          # _stop_vorhanden faengt das und
                                                # stellt im Zweifel KEINEN Stop.

    def test_ein_typ_fehlt_andere_liefern(self):
        def halb(p, signiert=False):
            if "conditional" in p:
                raise RuntimeError("Stoerung nur hier")
            return _faktnet(p, signiert=signiert)
        with patch.object(okxf, "_mit_wiederholung", side_effect=halb):
            fund = okxf.schutz_stops(ZEC)
        self.assertTrue(any(s.get("ordType") == "oco" for s in fund))


class RueckwaertskompatibelTest(unittest.TestCase):
    def test_aufruf_ohne_parameter_unveraendert(self):
        with patch.object(okxf, "_mit_wiederholung", side_effect=_faktnet):
            fund = okxf.schutz_stops()         # ohne inst: vier Fragen gesamt
        self.assertTrue(fund)


if __name__ == "__main__":
    unittest.main()
