"""Tests fuer xperp/boersen_bruecke.py.

Die Testfaelle sind die ECHTEN Zahlen aus der Nacht 04./05.10.2026, nicht
erfundene: sie sind der Grund, warum die Datei ueberhaupt existiert.

Gegenprobe als Regel, nicht als Zusatz: der Papierlauf (`live=False`) darf
NICHTS buchen. Ein Abgleich, der die Boerse liest und im Papierlauf ins
Live-Buch schreibt, waere schlimmer als die Luecke, die er schliesst - er
wuerde echte Positionen als verkauft ausweisen, nur auf dem Papier.

Ausfuehren (aus dem Handel-Ordner):
    ../scanner/.venv/Scripts/python.exe xperp/tests/test_boersen_bruecke.py
"""
from __future__ import annotations

import importlib.util
import os
import unittest

_HIER = os.path.dirname(os.path.abspath(__file__))
_BR = os.path.normpath(os.path.join(_HIER, "..", "boersen_bruecke.py"))

_spec = importlib.util.spec_from_file_location("bruecke_testmodul", _BR)
assert _spec and _spec.loader
bb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bb)


def pos(pos_id, inst, menge, preis, eroeffnet="2026-10-04T09:20:03+00:00",
        margin=469.0, modus="live"):
    """Eine Live-Position im Buch, wie `handeln` sie schreibt."""
    return {"pos_id": pos_id, "inst": inst, "kontrakte": menge,
            "preis": preis, "margin_usd": margin, "modus": modus,
            "eroeffnet_zeit": eroeffnet, "seite": "long"}


def fill(inst, menge, kurs, ts_ms, seite="sell"):
    return {"instId": inst, "side": seite, "fillSz": str(menge),
            "fillPx": str(kurs), "ts": str(ts_ms)}


class BrueckeTest(unittest.TestCase):
    """Jeder Test setzt beide Seiten: was das Buch sagt und was die Boerse."""

    def setUp(self):
        self.boerse = {}
        self.fills = []
        self.abgerufen = {"pos": 0, "fills": 0}
        bb.boersen_mengen = self._mengen
        bb.verkaeufe_seit = self._fills

    def _mengen(self):
        self.abgerufen["pos"] += 1
        return dict(self.boerse)

    def _fills(self, seit, bis=None):
        self.abgerufen["fills"] += 1
        agg = {}
        for f in self.fills:
            if (f.get("side") or "").lower() != "sell":
                continue
            a = agg.setdefault(f["instId"], {"menge": 0.0, "volumen": 0.0,
                                             "anzahl": 0, "erste": 0, "letzte": 0})
            ts = int(f["ts"])
            a["menge"] += float(f["fillSz"])
            a["volumen"] += float(f["fillSz"]) * float(f["fillPx"])
            a["anzahl"] += 1
            a["erste"] = ts if not a["erste"] else min(a["erste"], ts)
            a["letzte"] = max(a["letzte"], ts)
        for a in agg.values():
            a["kurs"] = a["volumen"] / a["menge"] if a["menge"] else 0.0
            a["erloes"] = a["volumen"]
        return agg

    # --- die drei Faelle aus der Nacht ------------------------------

    def test_ganz_verkaufte_position_wird_verkauf_nicht_geist(self):
        """STRK 8.033 -> 0. Ohne Fuellung bleibt es 'geister'; MIT Fuellung
        muss es 'verkauf' sein - das ist genau der Unterschied, an dem das
        Ergebnis von +70,76 USD verloren ging."""
        self.boerse = {"STRK-USD_UM_XPERP-310919": 0.0}
        self.fills = [fill("STRK-USD_UM_XPERP-310919", 8033, 0.0537, 1759600000000)]
        p = bb.plan({"positionen": [pos("p1", "STRK-USD_UM_XPERP-310919", 8033, 0.05433)]})
        e = p[0]
        self.assertEqual(e["aktion"], "verkauf")
        self.assertAlmostEqual(e["differenz"], 8033.0)
        self.assertAlmostEqual(e["verkauf"]["kurs"], 0.0537, places=6)
        self.assertEqual(e["verkauf"]["anzahl"], 1)

    def test_teilverkauf_behaelt_den_rest_offen(self):
        """Buch 8.033, Boerse 5.000: 3.033 verkauft, 5.000 bleiben stehen.
        Der alte Abgleich zog das Buch stur auf die Boersengroesse und
        nannte es 'Handanpassung' - damit verschwand der Verkauf aus der
        Kapitalkurve."""
        self.boerse = {"STRK-USD_UM_XPERP-310919": 5000.0}
        self.fills = [fill("STRK-USD_UM_XPERP-310919", 3033, 0.0537, 1759600000000)]
        p = bb.plan({"positionen": [pos("p1", "STRK-USD_UM_XPERP-310919", 8033, 0.05433)]})
        e = p[0]
        self.assertEqual(e["aktion"], "verkauf")
        self.assertAlmostEqual(e["differenz"], 3033.0)
        self.assertAlmostEqual(e["boerse"], 5000.0)

    def test_ohne_fuellung_bleibt_es_geister_und_wird_benannt(self):
        """Kein Zeuge heisst neutral, nicht 'aufgeraeumt'. Die Buchung wird
        dann mit `quelle: neutral` geschrieben - eine Behauptung waere
        schlimmer als eine Luecke."""
        self.boerse = {"SOL-USD_UM_XPERP-310404": 0.0}
        p = bb.plan({"positionen": [pos("p2", "SOL-USD_UM_XPERP-310404", 334, 121.21)]})
        e = p[0]
        self.assertEqual(e["aktion"], "geister")
        # `verkauf` ist der Schluessel selbst, nicht sein Inhalt - die
        # erste Fassung pruefte `assertNotIn("verkauf", e)` und schlug fehl,
        # WEIL der Schluessel mit None dasteht. Der Zeuge ist die ganze
        # Aussage, nicht die Existenz des Feldes.
        self.assertIsNone(e["verkauf"])
        self.assertIn("KEINE Fuellung", bb.bericht(p))

    # --- die drei Zusicherungen ---------------------------------------

    def test_unveraenderte_position_wird_nicht_angefasst(self):
        self.boerse = {"HYPE-USD_UM_XPERP-310523": 67.0}
        p = bb.plan({"positionen": [pos("p3", "HYPE-USD_UM_XPERP-310523", 67, 90.597)]})
        self.assertEqual(p[0]["aktion"], "unveraendert")
        self.assertEqual(p[0]["differenz"], 0.0)
        self.assertEqual(self.abgerufen["fills"], 0,
                         "ohne Differenz wird NICHT nach Fuellungen gefragt")

    def test_papier_positionen_werden_ignoriert(self):
        """Nur modus=live gehoert zur Bruecke. Eine Papierposition, die
        zufaellig denselben Kandidaten traegt, darf keinen Verkauf erzeugen."""
        self.boerse = {"SOL-USD_UM_XPERP-310404": 0.0}
        p = bb.plan({"positionen": [pos("p4", "SOL-USD_UM_XPERP-310404", 334, 121.21,
                                        modus="papier")]})
        self.assertEqual(p, [])

    def test_netzfehler_fasst_das_buch_nicht_an(self):
        def kaputt():
            raise RuntimeError("Boerse nicht erreichbar")
        bb.boersen_mengen = kaputt
        p = bb.plan({"positionen": [pos("p5", "SOL-USD_UM_XPERP-310404", 334, 121.21)]})
        self.assertIsNone(p, "ohne Boerse wird nichts geplant")
        self.assertIn("unberuehrt", bb.bericht(None))

    # --- die Rechnung, an der es haengt --------------------------------

    def test_verkauf_benoennt_kurs_und_menge_fuer_die_buchung(self):
        """Was der Aufrufer zum Buchen braucht: Stueckzahl, Kurs, Erloes und
        den Zeitstempel. Fehlt eines, kann die Buchung nicht entstehen."""
        self.boerse = {"QUANT-USD_UM_XPERP-311003": 0.0}
        self.fills = [fill("QUANT-USD_UM_XPERP-311003", 641, 254.9, 1759658000000)]
        e = bb.plan({"positionen": [pos("p6", "QUANT-USD_UM_XPERP-311003", 641, 261.80)]})[0]
        v = e["verkauf"]
        self.assertEqual(v["menge"], 641)
        self.assertAlmostEqual(v["kurs"], 254.9, places=4)
        self.assertAlmostEqual(v["erloes"], 641 * 254.9, places=2)
        self.assertGreater(v["erste"], 0)
        # Der Verlust ist (Verkaufskurs - Einstand) x Menge = -4.422,90 USD.
        # Genau das stand in keiner Journalzeile dieser Nacht; dort stand
        # ein Geister mit 0,00. Die erste Fassung dieses Tests rechnete
        # (0 - Einstand) x Menge - das ist nicht der Verlust, sondern der
        # Einsatz bei einem Verkauf zum Nullpreis (167.813 USD), also eine
        # Formel, die nie eine richtige Zahl ergaeben kann.
        verlust = (v["kurs"] - 261.80) * 641
        self.assertAlmostEqual(verlust, -4422.90, places=2)
        self.assertAlmostEqual(verlust, v["erloes"] - 261.80 * 641, places=2)

    def test_mehrere_fuellungen_ergeben_einen_mittelkurs(self):
        """STRK wurde in Wellen verkauft, nicht in einem Zug. Der Kurs muss
        der mengengewichtete sein - der letzte Fill allein waere geraten."""
        self.boerse = {"MON-USD_UM_XPERP-310711": 0.0}
        self.fills = [fill("MON-USD_UM_XPERP-310711", 1389, 0.03243, 1759632279000),
                      fill("MON-USD_UM_XPERP-310711", 256, 0.03243, 1759632279000),
                      fill("MON-USD_UM_XPERP-310711", 607, 0.03246, 1759632280000)]
        e = bb.plan({"positionen": [pos("p7", "MON-USD_UM_XPERP-310711", 2252, 0.0330)]})[0]
        v = e["verkauf"]
        self.assertEqual(v["anzahl"], 3)
        erwartet = (1389 * 0.03243 + 256 * 0.03243 + 607 * 0.03246) / (1389 + 256 + 607)
        self.assertAlmostEqual(v["kurs"], erwartet, places=8)


class BerichtTest(unittest.TestCase):
    def test_bericht_nennt_alle_drei_ausgaenge(self):
        eintraege = [
            {"inst": "A", "buch": 10, "boerse": 10, "aktion": "unveraendert",
             "differenz": 0.0},
            {"inst": "B", "buch": 8, "boerse": 5, "aktion": "verkauf",
             "differenz": 3.0, "verkauf": {"menge": 3.0, "kurs": 1.5,
                                            "anzahl": 2, "erloes": 4.5,
                                            "erste": 1, "letzte": 2}},
            {"inst": "C", "buch": 4, "boerse": 0, "aktion": "geister",
             "differenz": 4.0},
        ]
        text = bb.bericht(eintraege)
        self.assertIn("1 Teilverkauf", text)
        self.assertIn("1 ganz weg", text)
        self.assertIn("bezeugt", text)
        self.assertIn("VERKAUF zum echten Kurs", text)
        self.assertIn("KEINE Fuellung", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)