"""Bedingung 5 (rollierender EV) fuer die Kraken-Spur: Schalter und Sperre.

Auftrag Max am 01.10.2026 ("bedingung 5 entfaellt"): die EV-Sperre gilt fuer
kraken nicht mehr. Sie ist NICHT geloescht, sondern ueber `bedingung_5_aktiv`
in der wachen.json abschaltbar - fehlt das Feld, gilt sie wie bisher. Ohne
diesen Test waere die Lockerung eine unsichtbare Codeverzweigung: niemand
faende sie wieder, wenn die Spur einmal wieder Papier laufen soll.

Geprueft wird die REGEL, nicht der heutige Wert:
  * die Vorgabe ist "gilt" (jedes fehlende Feld sperrt weiter),
  * `false` nimmt den Sperrgrund UND die Sperr-Schliessung heraus,
  * wer sie aussetzt, dokumentiert es in derselben Datei.

Ohne Netz, ohne Order, ohne Schreibzugriff - die echte wachen.json wird nur
gelesen.

Direkt ausfuehrbar (aus dem kraken-Ordner):  python tests/test_bedingung_5.py
"""

import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import handeln as h                                            # noqa: E402

# Nur die Form: die Felder, die live_sperren() liest.
W = {"max_pro_trade_eur": 50, "max_gesamt_eur": 200, "max_offene_positionen": 4,
     "handel_erlaubt": True, "journal_zweitziel": "Q:\\Handel_Journal\\kraken",
     "herzschlag_max_minuten": 180, "mindest_guthaben_je_quote": {"EUR": 60}}

# Lage mit negativem Erwartungswert - der einzige Grund, um den es hier geht.
# Die Rundenfelder traegt zeige_wachen() in der Kopfzeile mit.
S = {"kill": False, "herzschlag_frisch": True, "rollierender_ev": -0.028,
     "ev_negativ": True, "ruecklauf_eur": 5.62, "hoechststand_eur": 34.32,
     "groessenfaktor": 1.0, "freigabe_erfuellt": True,
     "runden_echt": 1, "runden_papier_echt": 5, "runden_stoerung": 47,
     "erste_runde": "2026-09-12", "herzschlag_alter_min": 13.0}

EV_WORT = "Bedingung 5"


class SchalterTest(unittest.TestCase):
    """Die Vorgabe muss 'gilt' sein - ein fehlendes Feld darf nicht oeffnen."""

    def test_fehlendes_feld_heisst_gilt(self):
        self.assertTrue(h.bedingung_5_gilt({}))

    def test_true_heisst_gilt(self):
        self.assertTrue(h.bedingung_5_gilt({"bedingung_5_aktiv": True}))

    def test_false_heisst_gilt_nicht(self):
        self.assertFalse(h.bedingung_5_gilt({"bedingung_5_aktiv": False}))

    def test_null_oeffnet_nicht(self):
        """None ist kein 'aus' - nur das ausdrueckliche false zaehlt."""
        self.assertTrue(h.bedingung_5_gilt({"bedingung_5_aktiv": None}))

    def test_leere_wachen_oeffnen_nicht(self):
        self.assertTrue(h.bedingung_5_gilt(None))


class SperrgrundTest(unittest.TestCase):
    """Der EV-Grund steht genau dann in der Sperrliste, wenn der Schalter gilt."""

    def _gruende(self, w):
        with patch.object(h.kraken, "schluessel_vorhanden", return_value=True), \
                patch.object(h, "sitzung_da", return_value=True), \
                patch.object(h, "guthaben_lage",
                             return_value={"EUR": (189.42, 60.0)}):
            return h.live_sperren(w, S)

    def test_ohne_schalter_steht_der_grund_drin(self):
        gruende = self._gruende(dict(W))
        self.assertTrue(any(EV_WORT in g for g in gruende), gruende)

    def test_mit_false_faellt_der_grund(self):
        w = dict(W, bedingung_5_aktiv=False)
        gruende = self._gruende(w)
        self.assertFalse(any(EV_WORT in g for g in gruende), gruende)

    def test_andere_gruende_bleiben(self):
        """Der Schalter nimmt NUR Bedingung 5 heraus, nichts sonst."""
        w = dict(W, bedingung_5_aktiv=False, handel_erlaubt=False)
        gruende = self._gruende(w)
        self.assertTrue(any("handel_erlaubt" in g for g in gruende), gruende)

    def test_positiver_ev_ist_ohne_schalter_kein_grund(self):
        s = dict(S, ev_negativ=False, rollierender_ev=1.5)
        with patch.object(h.kraken, "schluessel_vorhanden", return_value=True), \
                patch.object(h, "sitzung_da", return_value=True), \
                patch.object(h, "guthaben_lage",
                             return_value={"EUR": (189.42, 60.0)}):
            gruende = h.live_sperren(dict(W), s)
        self.assertFalse(any(EV_WORT in g for g in gruende), gruende)


class SperrSchliessungTest(unittest.TestCase):
    """zeige_wachen() legt handel_erlaubt nur um, wenn der Schalter gilt.

    Das ist der eigentliche Schaden des alten Zustands: sperre_zu() schreibt in
    die wachen.json - ein ausgesetzter Schalter, der trotzdem sperrt, waere von
    aussen nicht zu sehen.
    """

    def _zeige(self, w):
        gerufen = []
        with patch.object(h, "lade_zustand", return_value={"positionen": []}), \
                patch.object(h.wp, "lage", return_value=S), \
                patch.object(h.wp, "sperre_zu",
                             side_effect=lambda g: gerufen.append(g) or True), \
                patch.object(h, "_spiegeln", lambda w, z=None: True), \
                patch.object(h, "_guthaben_text", lambda w: "EUR 189.42/60.00"):
            with patch("sys.stdout", io.StringIO()):
                h.zeige_wachen(w)
        return gerufen

    def test_ohne_schalter_wird_gesperrt(self):
        self.assertTrue(any(EV_WORT in g for g in self._zeige(dict(W))))

    def test_mit_false_wird_nicht_gesperrt(self):
        gerufen = self._zeige(dict(W, bedingung_5_aktiv=False))
        self.assertFalse(any(EV_WORT in g for g in gerufen), gerufen)


class EchteWachenTest(unittest.TestCase):
    """Die ausgelieferte Datei muss den Schalter UND den Grund nennen.

    Ein ausgesetztes Kriterium ohne Datum und Begruendung waere nicht mehr zu
    beurteilen - deshalb steht beides in der wachen.json, nicht nur im Code.
    """

    @classmethod
    def setUpClass(cls):
        cls.w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))

    def test_schalter_steht_auf_false(self):
        self.assertIs(self.w.get("bedingung_5_aktiv"), False)

    def test_begruendung_ist_datiert_und_unterschrieben(self):
        text = self.w.get("_bedingung_5_entfaellt") or ""
        self.assertIn("01.10.2026", text)
        self.assertIn("Max", text)

    def test_der_weg_zurueck_steht_in_der_datei(self):
        """Wer den Schalter sucht, findet hier, wie er ihn umlegt."""
        self.assertIn("true", (self.w.get("_bedingung_5_entfaellt") or "").lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)