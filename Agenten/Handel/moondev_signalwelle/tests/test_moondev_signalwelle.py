"""Tests fuer die Bot-Spur moondev_signalwelle - ohne Netz.

Die Regel wird mit erfundenen Daten geprueft (die API liefert im Test nichts),
und der Buchlauf laeuft gegen einen Temp-Ordner: ein Test darf NIE in den
echten Spurenordner schreiben.
"""

import json
import os
import sys
import csv
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
for p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln as h  # noqa: E402
import spur_buch as buch  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py: %s" % h.__file__

WACHEN = {
    "waehrung": "USD", "handel_erlaubt": False,
    "risiko_je_position_usd": 5.0, "max_offene_positionen": 3,
    "max_pro_trade_usd": 100.0, "max_gesamt_usd": 300.0,
    "kill_switch_gesamt_usd": 45.0, "stop_prozent": 7.0,
    "pflicht_stop_prozent_min": 6.0, "pflicht_stop_prozent_max": 12.0,
    "ziel_r_vielfaches": 1.5, "drawdown_halbierung_usd": 15.0,
    "mindest_plus_1h_pct": 3.0, "hoechst_plus_1h_pct": 15.0,
    "mindest_volumen_usd": 20000000.0,
}


def _bestand(ordner):
    aus = {}
    for n in sorted(os.listdir(ordner)):
        p = os.path.join(ordner, n)
        if os.path.isfile(p) and not n.endswith((".pyc", ".bak-20260920")):
            aus[n] = os.path.getsize(p)
    return aus


_ECHT_VORHER = None


def setUpModule():
    global _ECHT_VORHER
    _ECHT_VORHER = _bestand(SPUR)


def tearDownModule():
    assert _bestand(SPUR) == _ECHT_VORHER, (
        "Ein Test hat in den echten Spurenordner geschrieben! "
        "vorher=%s nachher=%s" % (_ECHT_VORHER, _bestand(SPUR)))


class RegelTest(unittest.TestCase):
    def test_welle_im_fenster_ist_long(self):
        d = {"aenderung_1h": 5.0, "volumen_24h": 5e7}
        self.assertEqual(h.signal(d, dict(WACHEN)), "long")

    def test_spike_zu_stark_kein_signal(self):
        d = {"aenderung_1h": 20.0, "volumen_24h": 5e7}
        self.assertIsNone(h.signal(d, dict(WACHEN)))

    def test_zu_wenig_momentum_und_zu_wenig_volumen(self):
        self.assertIsNone(h.signal({"aenderung_1h": 1.0, "volumen_24h": 5e7},
                                   dict(WACHEN)))
        self.assertIsNone(h.signal({"aenderung_1h": 5.0, "volumen_24h": 1e6},
                                   dict(WACHEN)))
        self.assertIsNone(h.signal({"aenderung_1h": None, "volumen_24h": 5e7},
                                   dict(WACHEN)))

    def test_24h_aenderung_wirkt_nicht_auf_die_regel(self):
        # Diese Spur fragt bewusst die 1h-Welle, nicht die Tagesbewegung -
        # eine grosse 24h-Aenderung darf ohne 1h-Feld kein Signal ausloesen.
        d = {"aenderung_24h": 50.0, "volumen_24h": 5e7}
        self.assertIsNone(h.signal(d, dict(WACHEN)))


class BuchTest(unittest.TestCase):
    """Ein Papierlauf gegen einen Temp-Ordner - und die Vorschau ohne Datei."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_schreiben = buch.SCHREIBEN
        buch.SCHREIBEN = True
        w = dict(WACHEN)
        w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")
        w["grund"] = "test"
        with open(os.path.join(self.tmp.name, "wachen.json"), "w",
                  encoding="utf-8") as f:
            json.dump(w, f)
        self.alt_quelle = h.quelle_override
        self.alt_signal = h.signal
        h.signal = lambda d, w_: "long"
        h.quelle_override = lambda w_: ({"BTC": {}}, {"BTC": 100.0}, [])

    def tearDown(self):
        h.quelle_override = self.alt_quelle
        h.signal = self.alt_signal
        buch.SCHREIBEN = self.alt_schreiben
        self.tmp.cleanup()

    def test_vorschau_schreibt_nichts(self):
        buch.zyklus(self.tmp.name, h.daten_holen, h.signal, "vorschau", "test")
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name,
                                                    "handelsjournal.csv")))

    def test_papierlauf_bucht_und_spiegelt(self):
        buch.zyklus(self.tmp.name, h.daten_holen, h.signal, "papier", "test")
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name,
                                                   "handelsjournal.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name,
                                                   "zustand.json")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, "zweitziel",
                                                   "handelsjournal.csv")))

    def test_leere_quelle_bucht_nichts(self):
        """Keine Daten = KEINE BUCHUNG - nicht: keine Datei.

        Der Test pruefte vorher die Abwesenheit der Journaldatei. Seit dem
        02.10.2026 legt `lege_journal_an()` die Datei ab dem ersten Zyklus mit
        Kopfzeile an (Auftrag Max: "alle duerfen auch journal fuehren") -
        eine Spur, die noch nie ein Signal hatte, hatte sonst gar kein
        Journal und damit nichts ausser Haus (Bedingung 4). Der Test wurde
        dadurch rot, obwohl die EIGENSCHAFT ("leere Quelle bucht nichts")
        unveraendert gilt: der Unterschied zwischen "Journal existiert mit
        null Zeilen" und "Journal existiert nicht" ist die Antwort auf
        "noch nie ein Signal?" - genau der war vorher nicht beantwortbar.

        Die Eigenschaft wird jetzt so geprueft, wie sie gemeint ist: null
        Datenzeilen, nicht null Dateien.
        """
        h.quelle_override = lambda w_: ({}, {}, ["Boerse weg"])
        buch.zyklus(self.tmp.name, h.daten_holen, h.signal, "papier", "test")
        p = os.path.join(self.tmp.name, "handelsjournal.csv")
        if os.path.exists(p):
            with open(p, encoding="utf-8", newline="") as f:
                self.assertEqual(list(csv.DictReader(f)), [],
                                 "die leere Quelle hat keine Buchung gemacht")
        else:
            self.assertTrue(True, "kein Journal - auch das ist 'nichts gebucht'")

    def test_live_verweigert(self):
        # main() ist der --live-Weg; hier direkt die Meldung pruefen, ohne
        # main() ueber sys.argv aufzurufen. Der echte Spurenordner kann
        # bereits ein Journal aus echten Papierzyklen tragen - deshalb wird
        # hier NICHT auf Abwesenheit geprueft, sondern ueber den
        # Modulwaechter (setUpModule/tearDownModule), dass --live selbst
        # nichts NEUES schreibt.
        import io
        import contextlib
        alt_argv = sys.argv
        sys.argv = ["handeln.py", "--live"]
        puffer = io.StringIO()
        # Seit 11.10.2026 faellt --live auf den Papierzyklus zurueck (sonst
        # stand die Spur bei offenem Freigabefenster still). Der Zyklus wird
        # hier ersetzt, damit der Test nichts in den echten Ordner bucht.
        from unittest import mock
        try:
            with contextlib.redirect_stdout(puffer),                     mock.patch.object(h.buch, "zyklus", return_value=0) as z:
                code = h.main()
        finally:
            sys.argv = alt_argv
        self.assertEqual(code, 0)
        self.assertIn("Live waere gesperrt", puffer.getvalue())
        self.assertEqual(z.call_args[0][3], "papier")


if __name__ == "__main__":
    unittest.main(verbosity=2)
