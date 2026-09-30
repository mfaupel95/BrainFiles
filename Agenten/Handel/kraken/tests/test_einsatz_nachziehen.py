"""Einsatz nachziehen: Stueckpreis im Einsatz erkennen und ersetzen - kein Netz.

Der Fehler (30.09.2026, T-208): `beleg_hand.py` schrieb den Stueckpreis als
Einsatz. Vier ueber die Hand ausgefuehrte Belege stehen deshalb mit 0,21 /
0,95 / 1,15 / 1,61 EUR im Journal statt mit ~50 EUR.

Die Pruefung rechnet aus der Zeile selbst nach - eine Attrappe mit den echten
Zahlen steht unten, und die Gegenprobe (zweiter Lauf findet nichts) ist Teil
der Tests.
"""
import csv
import importlib.util
import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
sys.path.insert(0, HIER)


def _lade(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


n = _lade("einsatz_nachziehen", os.path.join(SPUR, "einsatz_nachziehen.py"))
assert n.__file__.startswith(SPUR), n.__file__

KOPF = ["zeit", "modus", "aktion", "paar", "preis", "eur", "menge", "stop",
        "ziel", "grund"]
# Die vier echten Zeilen mit dem Stueckpreis als Einsatz.
KAPUTT = [
    ["2026-09-27T17:01:46+00:00", "live", "kauf", "DOTEUR", "1.0882", "1.15",
     "45.98969830", "1.0045728", "1.2524544", "beleg 07617cb76f16661b ueber die Hand"],
    ["2026-09-28T13:15:03+00:00", "live", "kauf", "ATOMEUR", "1.5206", "1.61",
     "32.88175720", "1.4171992", "1.7274016", "beleg 6d615f0f0699df09 ueber die Hand"],
    ["2026-09-28T14:44:58+00:00", "live", "kauf", "FILEUR", "0.902", "0.95",
     "55.43237250", "0.827134", "1.051732", "beleg 5f7a6296c5115f2e ueber die Hand"],
    ["2026-09-29T02:08:48+00:00", "live", "kauf", "XXLMZEUR", "0.200049", "0.21",
     "249.93876500", "0.18644567", "0.22725566", "beleg 22876b5873fbcda8 ueber die Hand"],
]
GEBUEHR = 0.006


class JournalFehlerTest(unittest.TestCase):
    def test_die_vier_echten_zeilen_werden_gefunden(self):
        treffer = n.journal_fehler(KAPUTT, GEBUEHR)
        self.assertEqual(len(treffer), 4)
        neu = {KAPUTT[t[0]][3]: round(t[2], 2) for t in treffer}
        self.assertEqual(neu["DOTEUR"], 50.35)
        self.assertEqual(neu["ATOMEUR"], 50.30)
        self.assertEqual(neu["FILEUR"], 50.30)
        self.assertEqual(neu["XXLMZEUR"], 50.30)

    def test_richtiger_einsatz_bleibt_unberuehrt(self):
        zeile = ["2026-09-27T17:01:46+00:00", "live", "kauf", "DOTEUR", "1.0882",
                 "50.35", "45.98969830", "1.0", "1.2", ""]
        self.assertEqual(n.journal_fehler([zeile], GEBUEHR), [])

    def test_nur_kauf_zeilen_werden_geprueft(self):
        # Eine Verkaufszeile traegt den ERLoES in der eur-Spalte - dort ist
        # ein kleiner Wert richtig (Teilverkauf) und darf nicht angefasst werden.
        zeile = ["2026-09-29T01:36:00+00:00", "live", "verkauf", "DOTEUR",
                 "1.0038", "45.89", "45.98969830", "", "", "stop (boerse)"]
        self.assertEqual(n.journal_fehler([zeile], GEBUEHR), [])

    def test_kaputte_zeile_ohne_preis_bleibt_liegen(self):
        zeile = ["2026-09-29T01:36:00+00:00", "live", "kauf", "DOTEUR", "", "0",
                 "45.98969830", "", "", ""]
        self.assertEqual(n.journal_fehler([zeile], GEBUEHR), [])

    def test_idempotent(self):
        treffer = n.journal_fehler(KAPUTT, GEBUEHR)
        nach = [list(z) for z in KAPUTT]
        for i, _, neu, _ in treffer:
            nach[i][5] = "%.2f" % neu
        self.assertEqual(n.journal_fehler(nach, GEBUEHR), [])


class BuchFehlerTest(unittest.TestCase):
    def test_position_mit_stueckpreis_wird_gefunden(self):
        pos = [{"paar": "DOTEUR", "einstieg": 1.0882, "eur": 1.14,
                "menge": 45.9896983}]
        t = n.buch_fehler(pos)
        self.assertEqual(len(t), 1)
        self.assertAlmostEqual(t[0][2], 50.05, places=2)

    def test_position_mit_betrag_bleibt_unberuehrt(self):
        pos = [{"paar": "ATOMEUR", "einstieg": 1.5206, "eur": 50.0,
                "menge": 32.8817572}]
        self.assertEqual(n.buch_fehler(pos), [])


class LaufTest(unittest.TestCase):
    """Der Schreibweg auf Dateien im Temp-Ordner - nie auf die echte Spur."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="t208_")
        self.j = os.path.join(self.tmp, "handelsjournal.csv")
        self.z = os.path.join(self.tmp, "zustand.json")
        with open(self.j, "w", newline="", encoding="utf-8") as f:
            s = csv.writer(f)
            s.writerow(KOPF)
            s.writerows(KAPUTT)
        with open(self.z, "w", encoding="utf-8") as f:
            json.dump({"positionen": [{"paar": "DOTEUR", "einstieg": 1.0882,
                                       "eur": 1.14, "menge": 45.9896983},
                                      {"paar": "ATOMEUR", "einstieg": 1.5206,
                                       "eur": 50.0, "menge": 32.8817572}]}, f)
        self._j, self._z = n.JOURNAL, n.ZUSTAND
        n.JOURNAL, n.ZUSTAND = self.j, self.z

    def tearDown(self):
        n.JOURNAL, n.ZUSTAND = self._j, self._z

    def _lies(self):
        with open(self.j, newline="", encoding="utf-8") as f:
            return [x for x in csv.reader(f)][1:]

    def test_vorschau_schreibt_nichts(self):
        n.lauf(anwenden=False)
        self.assertEqual(self._lies()[0][5], "1.15")

    def test_anwenden_schreibt_und_sichert(self):
        self.assertEqual(n.lauf(anwenden=True), 0)
        zeilen = self._lies()
        self.assertEqual(zeilen[0][5], "50.35")
        self.assertEqual(zeilen[3][5], "50.30")
        with open(self.z, encoding="utf-8") as f:
            z = json.load(f)
        self.assertEqual(z["positionen"][0]["eur"], 50.05)
        self.assertEqual(z["positionen"][1]["eur"], 50.0)
        self.assertEqual(len(z["buch_korrekturen"]), 1)
        dateien = os.listdir(self.tmp)
        self.assertTrue(any(x.startswith("handelsjournal.bak-") for x in dateien))
        self.assertTrue(any(x.startswith("handelsjournal.verworfen-") for x in dateien))
        self.assertTrue(any(x.startswith("zustand.bak-") for x in dateien))

    def test_zweiter_lauf_findet_nichts(self):
        n.lauf(anwenden=True)
        self.assertEqual(n.lauf(anwenden=False), 0)
        self.assertEqual(n.journal_fehler(self._lies(), GEBUEHR), [])


if __name__ == "__main__":
    unittest.main()