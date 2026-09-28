"""Der zweite Einstiegsweg der IV-Waelle-Spur: Fade an der Tagesspannengrenze.

Warum diese Datei (29.09.2026): die Spur hatte seit dem 19.09.2026 kein
Geschaeft und deshalb kein Journal. Ursache war das Tor - `signal()` verlangt
eine Wand innerhalb von 0,5 % des Kurses UND im Band Grenze..3 Sigma, und an
den echten Deribit-Ketten liegt keine Wand je dort (Call 90.000 = 3,13 Sigma,
Put 60.000 = 13,9 Sigma bei Basis 84.470). Der Spannen-Fade ist das ueber 400
Tage gemessene Feld (siehe iv_waelle/NOTIZ.md).

Geprueft wird:
  * signal_an_der_spanne: short ueber der oberen, long unter der unteren
    Grenze, kein_signal innerhalb, und der Schutz gegen einen Kurs, der so
    weit gelaufen ist, dass der Stop vor dem Einstieg laege.
  * spanne_und_signal: der Wandweg hat Vorrang; ohne Wand greift der
    Spannenweg (abschaltbar).
  * tagesende: die Tagesspanne gehoert zu einem UTC-Tag.
  * ein VOLLER Papierzyklus in einen Temp-Ordner: das Journal entsteht mit
    Kopfzeile, bekommt eine kauf-Zeile und im naechsten Zyklus die verkauf-Zeile
    - also eine echte Runde, die die Auswertung zaehlen kann.

Der Ordner-Waechter (setUpModule/tearDownModule) haelt den echten Spurenordner
frei von Testdaten.
"""

import csv
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
for p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    if p not in sys.path:
        sys.path.insert(0, p)
# Die eigene Spur MUSS vorne stehen, sonst holt 'import handeln' ein
# gleichnamiges Modul aus scanner/ (Falle vom 16.09.2026).
if SPUR in sys.path:
    sys.path.remove(SPUR)
sys.path.insert(0, SPUR)

import handeln as h  # noqa: E402
import iv_waelle as k  # noqa: E402
import spur_buch as buch  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py: %s" % h.__file__

JETZT = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
TAG = JETZT.date().isoformat()
BASIS = 100000.0
IV = 40.0
SIGMA = k.tages_sigma(BASIS, IV)


def _bestand(ordner):
    aus = {}
    for name in sorted(os.listdir(ordner)):
        p = os.path.join(ordner, name)
        if os.path.isfile(p) and not name.endswith(".pyc"):
            aus[name] = os.path.getsize(p)
    return aus


_ECHT_VORHER = None


def setUpModule():
    global _ECHT_VORHER
    _ECHT_VORHER = _bestand(SPUR)


def tearDownModule():
    nachher = _bestand(SPUR)
    assert nachher == _ECHT_VORHER, (
        "Test hat in den echten Spurenordner geschrieben: vorher %s, nachher %s"
        % (_ECHT_VORHER, nachher))


def _wachen(ordner="/tmp"):
    return {
        "waehrung": "USD", "boerse": "deribit", "instrument": "BTC-PERPETUAL",
        "optionswaehrung": "BTC", "handel_erlaubt": False,
        "herzschlag_max_minuten": 180,
        "risiko_je_position_usd": 6.0, "max_offene_positionen": 4,
        "max_pro_trade_usd": 120.0, "max_gesamt_usd": 480.0,
        "kill_switch_gesamt_usd": 48.0, "drawdown_halbierung_usd": 24.0,
        "gebuehr_taker": 0.0005,
        "grenz_k": 1.0, "ziel_anteil": 0.5, "stop_sigma": 0.5,
        "naehe_prozent": 0.5, "stop_puffer_prozent": 0.25,
        "nur_handelbare_wand": True,
        "einstieg_an_der_spanne": True, "ausstieg_am_tagesende": True,
        "hist_vol_fenster": 20, "mischgewicht_iv": 0.5,
        "mindest_kerzen": 300, "kerzen_takt": "60",
        "instrumente": ["BTC-PERPETUAL"], "_grund": "iv_waelle",
        "journal_zweitziel": ordner,
    }


def _markt(spot, iv=IV, kette=None):
    """Marktdaten ohne Waende - genau der Fall, der die Spur blockierte."""
    return {"spot": spot, "basispreis": BASIS, "iv_prozent": iv,
            "hv_prozent": iv, "kette": kette if kette is not None else []}


def _spanne(k_vielfaches=1.0):
    return k.spanne(BASIS, IV, k=k_vielfaches)


class SpannenSignalTest(unittest.TestCase):
    def test_ueber_der_oberen_grenze_ist_short(self):
        spanne = _spanne()
        kurs = spanne["oben"] * 1.001
        sig = k.signal_an_der_spanne(kurs, spanne)
        self.assertEqual(sig["richtung"], "short")
        self.assertEqual(sig["ausloeser"], "spanne")
        # Stop 0,5 Sigma HINTER die Grenze, Ziel der halbe Rueckweg zur Mitte.
        self.assertAlmostEqual(sig["stop"], spanne["oben"] + 0.5 * SIGMA, places=6)
        self.assertAlmostEqual(sig["ziel"], kurs - 0.5 * (kurs - BASIS), places=6)
        self.assertGreater(sig["stop"], sig["einstieg"])
        self.assertLess(sig["ziel"], sig["einstieg"])

    def test_unter_der_unteren_grenze_ist_long(self):
        spanne = _spanne()
        kurs = spanne["unten"] * 0.999
        sig = k.signal_an_der_spanne(kurs, spanne)
        self.assertEqual(sig["richtung"], "long")
        self.assertAlmostEqual(sig["stop"], spanne["unten"] - 0.5 * SIGMA, places=6)
        self.assertLess(sig["stop"], sig["einstieg"])
        self.assertGreater(sig["ziel"], sig["einstieg"])

    def test_innerhalb_der_spanne_ist_kein_signal(self):
        spanne = _spanne()
        sig = k.signal_an_der_spanne(BASIS, spanne)
        self.assertEqual(sig["richtung"], "kein_signal")
        self.assertIn("innerhalb", sig["grund"])

    def test_ohne_sigma_ist_kein_signal(self):
        spanne = _spanne()
        spanne["sigma"] = 0.0
        sig = k.signal_an_der_spanne(BASIS * 2, spanne)
        self.assertEqual(sig["richtung"], "kein_signal")
        self.assertIn("kein Sigma", sig["grund"])

    def test_zu_weit_gelaufen_ist_kein_geschaeft(self):
        # Kurs 4 Sigma ueber der Basis: der Stop (Grenze + 0,5 Sigma) laege
        # VOR dem Einstieg - daraus darf kein Geschaeft werden.
        spanne = _spanne()
        kurs = BASIS + 4.0 * SIGMA
        sig = k.signal_an_der_spanne(kurs, spanne)
        self.assertEqual(sig["richtung"], "kein_signal")
        self.assertIn("vor dem Einstieg", sig["grund"])

    def test_stop_sigma_und_ziel_anteil_sind_einstellbar(self):
        spanne = _spanne()
        kurs = spanne["oben"] * 1.001
        sig = k.signal_an_der_spanne(kurs, spanne, stop_sigma=1.0,
                                     ziel_anteil=1.0)
        self.assertAlmostEqual(sig["stop"], spanne["oben"] + 1.0 * SIGMA, places=6)
        self.assertAlmostEqual(sig["ziel"], BASIS, places=6)


class WegwahlTest(unittest.TestCase):
    """spanne_und_signal: Wandweg zuerst, Spannenweg als zweiter Weg."""

    def test_ohne_wand_greift_der_spannenweg(self):
        w = _wachen()
        d = _markt(_spanne()["oben"] * 1.001)          # keine Kette, keine Wand
        sig = h.spanne_und_signal(d, w)
        self.assertEqual(sig["richtung"], "short")
        self.assertEqual(sig["ausloeser"], "spanne")
        self.assertIn("ohne_wand", sig)

    def test_abgeschaltet_bleibt_es_beim_kein_signal(self):
        w = _wachen()
        w["einstieg_an_der_spanne"] = False
        d = _markt(_spanne()["oben"] * 1.001)
        sig = h.spanne_und_signal(d, w)
        self.assertEqual(sig["richtung"], "kein_signal")

    def test_wandweg_hat_vorrang(self):
        # Call-Wand 2 Sigma ueber der Basis, Kurs dicht darunter: die Wand ist
        # handelbar, also kommt der Wandweg - nicht der Spannenweg.
        strike = BASIS + 2.0 * SIGMA
        kurs = strike * 0.996
        kette = [{"instrument_name": "BTC-25DEC26-%d-C" % strike,
                  "open_interest": 9000.0, "mark_iv": 40.0}]
        sig = h.spanne_und_signal(_markt(kurs, kette=kette), _wachen())
        self.assertEqual(sig["richtung"], "short")
        self.assertNotEqual(sig.get("ausloeser"), "spanne")
        # Die Ersatz-Kette schreibt den Strike mit %d - also auf ganze Zahlen
        # gerundet. Genau deshalb wird hier mit Toleranz verglichen.
        self.assertAlmostEqual(sig["wand"], strike, delta=1.0)


class TagesendeTest(unittest.TestCase):
    """Der Tagesende-Ausstieg haengt an der Uhr - die wird hier festgesetzt.

    Ohne feste Uhr misst der Test die Wanduhr des Rechners: am 29.09.2026 um
    00:40 Ortszeit ist es 22:40 UTC des 28.09., ein Zeitstempel vom 29.09. liegt
    damit in der Zukunft und galt als "anderer Tag".
    """

    def setUp(self):
        self.alt = h.zeit_quelle
        h.zeit_quelle = lambda: JETZT.isoformat(timespec="seconds")

    def tearDown(self):
        h.zeit_quelle = self.alt

    def test_gleicher_tag_laeuft_weiter(self):
        w = _wachen()
        p = {"eroeffnet_zeit": JETZT.replace(hour=1).isoformat()}
        self.assertIsNone(h.tagesende(p, w))

    def test_vortag_wird_geschlossen(self):
        w = _wachen()
        p = {"eroeffnet_zeit": "2026-09-28T23:55:00+00:00"}
        self.assertEqual(h.tagesende(p, w), "tagesende")

    def test_abschaltbar(self):
        w = _wachen()
        w["ausstieg_am_tagesende"] = False
        p = {"eroeffnet_zeit": "2026-09-28T23:55:00+00:00"}
        self.assertIsNone(h.tagesende(p, w))

    def test_unlesbarer_zeitpunkt_gilt_als_tagesende(self):
        w = _wachen()
        self.assertEqual(h.tagesende({"eroeffnet_zeit": "kaputt"}, w),
                         "tagesende")


class ZyklusTest(unittest.TestCase):
    """Ein VOLLER Papierzyklus: das Journal entsteht und traegt eine Runde."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (buch.SCHREIBEN, h.zeit_quelle, h.markt_quelle,
                    h.wachen_pfad, h.zustand_pfad, h.journal_pfad)
        buch.SCHREIBEN = True
        h.zeit_quelle = lambda: JETZT.isoformat(timespec="seconds")
        h.wachen_pfad = os.path.join(self.tmp.name, "wachen.json")
        h.zustand_pfad = os.path.join(self.tmp.name, "zustand.json")
        h.journal_pfad = os.path.join(self.tmp.name, "handelsjournal.csv")
        with open(h.wachen_pfad, "w", encoding="utf-8") as f:
            json.dump(_wachen(os.path.join(self.tmp.name, "zweitziel")), f)

    def tearDown(self):
        (buch.SCHREIBEN, h.zeit_quelle, h.markt_quelle,
         h.wachen_pfad, h.zustand_pfad, h.journal_pfad) = self.alt
        self.tmp.cleanup()

    def _zyklus(self, kurs):
        h.markt_quelle = lambda w_: (
            {"BTC-PERPETUAL": _markt(kurs)}, {"BTC-PERPETUAL": kurs}, [])
        h.lauf("papier")

    def _zeilen(self):
        with open(h.journal_pfad, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_journal_entsteht_und_traegt_eine_runde(self):
        spanne = _spanne()
        self._zyklus(spanne["oben"] * 1.001)           # ueber der Grenze -> short
        zeilen = self._zeilen()
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0]["aktion"], "kauf")
        self.assertEqual(zeilen[0]["seite"], "short")
        self.assertEqual(zeilen[0]["grund"], "iv_waelle:spanne")

        # Der naechste Zyklus steht am Ziel: der Ausstieg wird gebucht.
        self._zyklus(float(zeilen[0]["ziel"]) * 0.999)
        zeilen = self._zeilen()
        self.assertEqual(len(zeilen), 2)
        self.assertEqual(zeilen[1]["aktion"], "verkauf")
        self.assertEqual(zeilen[1]["grund"], "ziel")
        # Der Erloes steht beim Verkauf im SELBEN Feld wie der Einsatz beim
        # Kauf (einsatz_usd) - so liest es auch auswertung_alle.runden_indikator.
        self.assertGreater(float(zeilen[1]["einsatz_usd"]),
                           float(zeilen[0]["einsatz_usd"]))
        with open(h.zustand_pfad, encoding="utf-8") as f:
            z = json.load(f)
        self.assertEqual(z["positionen"], [])

    def test_zweiter_zyklus_am_gleichen_tag_handelt_nicht_doppelt(self):
        spanne = _spanne()
        self._zyklus(spanne["oben"] * 1.001)
        self._zyklus(spanne["oben"] * 1.002)            # gleiches Instrument
        self.assertEqual(len(self._zeilen()), 1)

    def test_position_vom_vortag_wird_am_tagesende_geschlossen(self):
        spanne = _spanne()
        self._zyklus(spanne["oben"] * 1.001)
        # Der naechste Tag: derselbe Kurs, aber der Einstieg ist von gestern.
        h.zeit_quelle = lambda: (JETZT.replace(day=JETZT.day + 1)
                                 .isoformat(timespec="seconds"))
        self._zyklus(spanne["oben"] * 1.001)
        zeilen = self._zeilen()
        # Drei Zeilen: der Ausstieg am Tagesende, und danach ein NEUES
        # Geschaeft - der Kurs steht weiter ueber der Grenze, und in einem
        # echten Lauf kommt die Spanne dieses Tages aus dessen Eroeffnungskurs.
        self.assertEqual([z["aktion"] for z in zeilen],
                         ["kauf", "verkauf", "kauf"])
        self.assertEqual(zeilen[1]["grund"], "tagesende")


if __name__ == "__main__":
    unittest.main(verbosity=2)