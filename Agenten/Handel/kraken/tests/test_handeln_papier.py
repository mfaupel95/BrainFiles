"""Test der Kraken-Spur: Ausstiegszeile, Alter der Rangliste, Einstandskurs.

Ohne Netz, ohne Order: `kraken.letzter_kurs` wird ersetzt, das Journal zeigt in
eine Temp-Datei, `live=False`.

Der Fall, um den es geht, ist die Zeile, die der Dauerlauf nach Telegram
weiterreicht: er schickt nur Zeilen, die ein Filterwort tragen (`verkauf`,
`stop`, `KILL`, `gesperrt`, `ausstieg`). Ein Ziel-Ausstieg trug bis zum
14.09.2026 keines davon - er stand im Journal und war im Chat unsichtbar.

Die Wachen sind hier eine KOPIE der Form, nicht der Werte: ein Test, der auf
den heutigen Inhalt von wachen.json baut, bricht, sobald Max einen Schalter
umlegt.

Direkt ausfuehrbar (aus dem kraken-Ordner):  python tests/test_handeln_papier.py
"""

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import handeln as h                                            # noqa: E402

# Nur die Form: welche Felder liest der Lauf.
W = {"max_pro_trade_eur": 50, "max_gesamt_eur": 200, "max_offene_positionen": 4,
     "gebuehr_taker": 0.004, "abklingzeit_tage": 3, "mindest_score": 65,
     "max_volatilitaet_pa": 1.20, "mindest_chance_risiko": 2.0,
     "pflicht_stop_prozent_min": 5.0, "pflicht_stop_prozent_max": 12.0,
     "bericht_max_alter_tage": 3}

FILTERWOERTER = ("verkauf", "stop", "kill", "gesperrt", "ausstieg")

POS = {"paar": "XETHZEUR", "einstieg": 3000.0, "eur": 50.0, "menge": 0.0166,
       "stop": 2790.0, "ziel": 3420.0, "eroeffnet": "2026-09-13",
       "kauf_txid": None, "stop_txid": None}


class Ausstiegszeile(unittest.TestCase):
    """Die gedruckte Zeile - nicht das Journal. Genau das war die Luecke."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = h.JOURNAL
        h.JOURNAL = Path(self.tmp.name) / "handelsjournal.csv"

    def tearDown(self):
        h.JOURNAL = self.alt
        self.tmp.cleanup()

    def _lauf_mit_kurs(self, kurs):
        z = {"positionen": [dict(POS)], "letzte_stops": {}}
        with patch.object(h.kraken, "letzter_kurs", return_value=kurs):
            puffer = io.StringIO()
            with patch("sys.stdout", puffer):
                h.pruefe_ausstiege(z, W, False)
        return puffer.getvalue(), z

    def test_ziel_ausstieg_traegt_ein_filterwort(self):
        text, z = self._lauf_mit_kurs(POS["ziel"])
        self.assertIn("AUSSTIEG (ziel)", text)
        # Ohne Filterwort haette der Dauerlauf die Zeile nie weitergegeben.
        self.assertTrue(any(w in text.lower() for w in FILTERWOERTER),
                        "kein Filterwort in der Ausstiegszeile: %r" % text)
        self.assertIn(POS["paar"], text, "das Paar muss in der Zeile stehen")
        self.assertEqual(z["positionen"], [])

    def test_stop_ausstieg_nennt_grund_und_paar(self):
        text, _ = self._lauf_mit_kurs(POS["stop"] - 10)
        self.assertIn("AUSSTIEG (stop)", text)
        self.assertIn(POS["paar"], text)

    def test_ziel_ausstieg_ist_keine_abklingzeit(self):
        _, z = self._lauf_mit_kurs(POS["ziel"])
        self.assertEqual(z["letzte_stops"], {},
                         "ein Ziel ist kein Stop - kein Wiedereinstiegsverbot")

    def test_stop_ausstieg_setzt_abklingzeit(self):
        _, z = self._lauf_mit_kurs(POS["stop"] - 10)
        self.assertEqual(z["letzte_stops"].get(POS["paar"]), h._heute())


class RanglisteAlter(unittest.TestCase):

    def test_heutiger_bericht_ist_null_tage_alt(self):
        self.assertEqual(h._bericht_alter({"datum": h._heute()}), 0)

    def test_alter_wird_gerechnet(self):
        alt = (date.fromisoformat(h._heute()) - timedelta(days=9)).isoformat()
        self.assertEqual(h._bericht_alter({"datum": alt}), 9)

    def test_unlesbares_datum_gilt_als_zu_alt(self):
        # 999 ist die Sperre: ohne Datum wird nicht eingestiegen.
        self.assertEqual(h._bericht_alter({}), 999)
        self.assertEqual(h._bericht_alter({"datum": "keine datum"}), 999)
        self.assertEqual(h._bericht_alter({"datum": None}), 999)


class AlteRanglisteImLauf(unittest.TestCase):
    """Eine zu alte Rangliste sperrt die Einstiege - nicht die Ausstiege."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (h.JOURNAL, h.scan.wachen, h.scan.BERICHTE, h.ZUSTAND)
        h.JOURNAL = Path(self.tmp.name) / "handelsjournal.csv"
        h.ZUSTAND = Path(self.tmp.name) / "zustand.json"
        berichte = Path(self.tmp.name) / "berichte"
        berichte.mkdir()
        alt = (date.fromisoformat(h._heute()) - timedelta(days=10)).isoformat()
        (berichte / "neuester.json").write_text(json.dumps(
            {"datum": alt, "werte": [{"inst": "XETHZEUR", "score": 90.0,
                                      "verhaeltnis": 3.0, "preis": 3000.0,
                                      "kennzahlen": {"volatilitaet_pa": 0.5}}]}),
            encoding="utf-8")
        h.scan.BERICHTE = berichte
        h.scan.wachen = lambda: W

    def tearDown(self):
        (h.JOURNAL, h.scan.wachen, h.scan.BERICHTE, h.ZUSTAND) = self.alt
        self.tmp.cleanup()

    def test_keine_einstiege_aber_ausstiege_laufen(self):
        s = {"kill": False, "herzschlag_frisch": True, "rollierender_ev": None,
             "ev_negativ": False, "ruecklauf_eur": 0.0, "hoechststand_eur": 0.0,
             "groessenfaktor": 1.0, "freigabe_erfuellt": False}
        gerufen = {"ausstiege": 0, "einstiege": 0}
        z = {"positionen": [dict(POS)], "letzte_stops": {}, "letzter_lauf": None,
             "modus": None}

        def ausstiege(zustand, w, live):
            gerufen["ausstiege"] += 1

        def einstiege(zustand, vs, w, live, faktor=1.0):
            gerufen["einstiege"] += 1
            gerufen["vorschlaege"] = len(vs)

        def keine_kurse(inst):
            raise AssertionError("ohne Einstiege darf kein Kurs geholt werden")

        with patch.object(h, "lade_zustand", return_value=z), \
                patch.object(h, "schreibe_zustand", lambda zz: None), \
                patch.object(h, "_spiegeln", lambda w, zz=None: True), \
                patch.object(h.wp, "lage", return_value=s), \
                patch.object(h, "pruefe_ausstiege", side_effect=ausstiege), \
                patch.object(h, "pruefe_einstiege", side_effect=einstiege), \
                patch.object(h.kraken, "letzter_kurs", side_effect=keine_kurse):
            puffer = io.StringIO()
            with patch("sys.stdout", puffer):
                h.lauf("papier")
        text = puffer.getvalue()
        self.assertEqual(gerufen["ausstiege"], 1,
                         "Stop und Ziel muessen auch ohne frische Rangliste laufen")
        self.assertEqual(gerufen["vorschlaege"], 0)
        self.assertIn("keine Einstiege", text)

    def test_frische_rangliste_steigt_ein(self):
        """Gegenprobe: mit heutigem Datum kommen die Vorschlaege durch."""
        (h.scan.BERICHTE / "neuester.json").write_text(json.dumps(
            {"datum": h._heute(), "werte": [{"inst": "XETHZEUR", "score": 90.0,
                                             "verhaeltnis": 3.0, "preis": 3000.0,
                                             "kennzahlen": {"volatilitaet_pa": 0.5}}]}),
            encoding="utf-8")
        gerufen = {}

        with patch.object(h, "lade_zustand",
                          return_value={"positionen": [], "letzte_stops": {},
                                        "letzter_lauf": None, "modus": None}), \
                patch.object(h, "schreibe_zustand", lambda zz: None), \
                patch.object(h, "_spiegeln", lambda w, zz=None: True), \
                patch.object(h.wp, "lage", return_value={
                    "kill": False, "herzschlag_frisch": True,
                    "rollierender_ev": None, "ev_negativ": False,
                    "ruecklauf_eur": 0.0, "hoechststand_eur": 0.0,
                    "groessenfaktor": 1.0, "freigabe_erfuellt": False}), \
                patch.object(h, "pruefe_ausstiege", lambda *a: None), \
                patch.object(h, "pruefe_einstiege",
                             lambda zustand, vs, w, live, faktor=1.0:
                             gerufen.update(vorschlaege=len(vs))), \
                patch.object(h.kraken, "letzter_kurs", return_value=3001.0):
            with patch("sys.stdout", io.StringIO()):
                h.lauf("papier")
        self.assertEqual(gerufen.get("vorschlaege"), 1)


class Einstandskurs(unittest.TestCase):
    """Einstand, Stop und Ziel kommen vom lebenden Kurs, nicht aus dem Bericht."""

    def test_lebender_kurs_schlaegt_den_berichtspreis(self):
        with patch.object(h.kraken, "letzter_kurs", return_value=3100.0):
            self.assertEqual(h._kurs_jetzt("XETHZEUR", 3000.0), 3100.0)

    def test_ausfall_faellt_auf_den_berichtspreis_zurueck(self):
        with patch.object(h.kraken, "letzter_kurs",
                          side_effect=RuntimeError("kein Netz")):
            self.assertEqual(h._kurs_jetzt("XETHZEUR", 3000.0), 3000.0)

    def test_nullkurs_gilt_als_ausfall(self):
        with patch.object(h.kraken, "letzter_kurs", return_value=0.0):
            self.assertEqual(h._kurs_jetzt("XETHZEUR", 3000.0), 3000.0)

    def test_stop_und_ziel_haengen_am_lebenden_kurs(self):
        bericht = {"datum": h._heute(), "werte": [
            {"inst": "XETHZEUR", "score": 90.0, "verhaeltnis": 3.0,
             "preis": 3000.0, "kennzahlen": {"volatilitaet_pa": 0.5}}]}
        with patch.object(h.kraken, "letzter_kurs", return_value=2000.0):
            vs = h.vorschlaege(bericht, W)
        self.assertEqual(len(vs), 1)
        v = vs[0]
        self.assertEqual(v["einstieg"], 2000.0)
        self.assertLess(v["stop"], 2000.0)
        self.assertGreater(v["ziel"], 2000.0)
        # Chance/Risiko 2:1 auf dem lebenden Kurs, nicht auf dem Berichtspreis.
        self.assertAlmostEqual(v["ziel"] - v["einstieg"],
                               2.0 * (v["einstieg"] - v["stop"]), places=6)


class Gebuehr(unittest.TestCase):
    """Was der Freibetrag des Abos an der Kaufzeile aendert.

    Der Test behauptet die RECHNUNG, nicht den Wert in wachen.json:
    `gebuehr_taker` ist seit dem 14.09.2026 null, darf aber jederzeit wieder
    steigen (faellt das Abo weg). Deshalb wird beides geprueft - mit 0 und mit
    0,40 %.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = h.JOURNAL
        h.JOURNAL = Path(self.tmp.name) / "handelsjournal.csv"

    def tearDown(self):
        h.JOURNAL = self.alt
        self.tmp.cleanup()

    def _kaufzeile(self, satz):
        w = dict(W)
        w["gebuehr_taker"] = satz
        v = {"inst": "XETHZEUR", "eur": 50.0, "einstieg": 3000.0,
             "stop": 2790.0, "ziel": 3420.0, "stop_pct": 7.0, "score": 80.0}
        z = {"positionen": [], "letzte_stops": {}}
        with patch.object(h, "menge_fuer", return_value=(0.0166, None)), \
             patch("sys.stdout", io.StringIO()):
            h.pruefe_einstiege(z, [v], w, False)
        zeilen = [x for x in h.JOURNAL.read_text("utf-8").splitlines()
                  if ",kauf," in x]
        self.assertEqual(len(zeilen), 1, "genau eine Kaufzeile erwartet")
        return zeilen[0].split(",")[5], z["positionen"][0]

    def test_ohne_gebuehr_steht_der_nominale_einsatz_in_der_kaufzeile(self):
        betrag, pos = self._kaufzeile(0.0)
        self.assertEqual(betrag, "50.00")
        self.assertEqual(pos["eur"], 50.0)

    def test_mit_gebuehr_steht_sie_in_der_kaufzeile(self):
        betrag, _ = self._kaufzeile(0.004)
        self.assertEqual(betrag, "50.20")


if __name__ == "__main__":
    unittest.main(verbosity=2)
