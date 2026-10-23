"""Tests fuer die IV-Waelle-Spur (handeln.py) - ohne Netz.

Geprueft wird, wie die Spur die Signal-Regel AUS iv_waelle.py in eine
Papierposition uebersetzt: spanne_und_signal ruft k.signal() unveraendert,
einstieg setzt Stop hinter die Wand und Ziel als halben Rueckweg, und der
Lauf schreibt Zustand/Journal/Kopie nur in den vom Test gesetzten
Temp-Ordner.

Der Ordner-Waechter (setUpModule/tearDownModule) verhindert, dass ein Test in
den echten Spurenordner schreibt - im Baum zaehlten einmal Testdaten als
echte Handelsrunden.
"""

import importlib.util
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
# SPUR MUSS vorne stehen - auch wenn ein anderes Testmodul (test_iv_waelle)
# den Ordner schon in sys.path gelegt hat, sonst gewinnt scanner/handeln.py.
if SPUR in sys.path:
    sys.path.remove(SPUR)
sys.path.insert(0, SPUR)

_spec = importlib.util.spec_from_file_location(
    "iv_waelle_handeln_test", os.path.join(SPUR, "handeln.py"))
h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h)
import spur_buch as buch  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py: %s" % h.__file__

JETZT = datetime(2026, 9, 18, 8, 30, tzinfo=timezone.utc).isoformat(timespec="seconds")


def _bestand(ordner):
    aus = {}
    for name in sorted(os.listdir(ordner)):
        p = os.path.join(ordner, name)
        if os.path.isfile(p) and not name.endswith((".pyc", ".bak-20260918")):
            aus[name] = os.path.getsize(p)
    return aus


_ECHT_VORHER = None


def setUpModule():
    global _ECHT_VORHER
    _ECHT_VORHER = _bestand(SPUR)


def tearDownModule():
    nachher = _bestand(SPUR)
    assert nachher == _ECHT_VORHER, (
        "Ein Test hat in den echten Spurenordner geschrieben!\nvorher: %s\nnachher: %s"
        % (_ECHT_VORHER, nachher))


def _kette(strikes_und_oi):
    """Ersatz-Optionskette: [(strike, seite, oi), ...]."""
    return [{"instrument_name": "BTC-25DEC26-%d-%s" % (strike, seite),
             "open_interest": oi, "mark_iv": 40.0}
            for strike, seite, oi in strikes_und_oi]


def _markt(spot, iv=40.0, hv=40.0, kette=None, basis=None):
    return {"spot": spot, "basispreis": basis if basis is not None else spot,
            "iv_prozent": iv, "hv_prozent": hv,
            "kette": kette if kette is not None else _kette([])}


def _sigma(basis=100000.0, iv=40.0):
    return basis * iv / 100.0 / (365.0 ** 0.5)


def _call_kette(spot, basis=100000.0, sigma_faktor=2.0, oi=9000.0):
    """Kette mit EINER Call-Wand bei `faktor`*Sigma ueber der Basis, und der
    laufende Kurs dicht UNTER dieser Wand.

    Zwei Bedingungen muessen gleichzeitig gelten: der Kurs muss innerhalb von
    naehe_prozent (0.5 %) unter der Wand liegen (Ausloesung), aber die Wand
    mindestens abstand_min_prozent (0.3 %) ueber dem Kurs (sonst wuerde
    waende() sie nicht als Wand werten). 0.4 % darunter erfuellt beides.
    """
    strike = basis + sigma_faktor * _sigma(basis)
    kurs = strike * (1.0 - 0.004)
    return _kette([(strike, "C", oi)]), strike, kurs


def _wachen(ordner):
    """Wachen fuer den Testlauf: alles aus der echten wachen.json, aber mit
    dem Zweitziel im Temp-Ordner. Werte sind in dieser Testdatei bewusst klein
    und eindeutig, damit ein Rechenfehler sofort auffaellt."""
    return {
        "waehrung": "USD",
        "boerse": "deribit",
        "instrument": "BTC-PERPETUAL",
        "optionswaehrung": "BTC",
        "handel_erlaubt": False,
        "herzschlag_max_minuten": 180,
        "risiko_je_position_usd": 6.0,
        "max_offene_positionen": 4,
        "max_pro_trade_usd": 120.0,
        "max_gesamt_usd": 480.0,
        "kill_switch_gesamt_usd": 48.0,
        "drawdown_halbierung_usd": 24.0,
        "gebuehr_taker": 0.0005,
        "grenz_k": 1.0,
        "ziel_anteil": 0.5,
        "stop_sigma": 0.5,
        "naehe_prozent": 0.5,
        "stop_puffer_prozent": 0.25,
        "nur_handelbare_wand": True,
        "hist_vol_fenster": 20,
        "mischgewicht_iv": 0.5,
        "mindest_kerzen": 300,
        "kerzen_takt": "60",
        "instrumente": ["BTC-PERPETUAL"],
        "_grund": "iv_waelle",
        "journal_zweitziel": ordner,
    }


class SignalTest(unittest.TestCase):
    """spanne_und_signal uebernimmt die Regel aus iv_waelle.py unveraendert."""

    def test_keine_wand_ist_kein_signal(self):
        d = _markt(100000.0, basis=100000.0)
        sig = h.spanne_und_signal(d, _wachen("/tmp"))
        self.assertEqual(sig["richtung"], "kein_signal")

    def test_waende_zu_weit_sind_kein_signal(self):
        # Call-Wand 5 Sigma ueber der Basis: ausserhalb 3 Sigma -> kein_signal.
        w = _wachen("/tmp")
        kette, strike, kurs = _call_kette(100000.0, basis=100000.0, sigma_faktor=5.0)
        # laufender Kurs dicht unter der 5-Sigma-Wand
        d = _markt(kurs, basis=100000.0, kette=kette)
        sig = h.spanne_und_signal(d, w)
        self.assertEqual(sig["richtung"], "kein_signal")

    def test_signal_an_der_call_wand_ist_short(self):
        # Spanne verankert am Tagesbeginn (100000), Kurs hat sich an die
        # 2-Sigma-Wand heranbewegt: handelbar (1-3 Sigma), also short.
        w = _wachen("/tmp")
        kette, strike, kurs = _call_kette(100000.0, basis=100000.0, sigma_faktor=2.0)
        d = _markt(kurs, basis=100000.0, kette=kette)
        sig = h.spanne_und_signal(d, w)
        self.assertEqual(sig["richtung"], "short")
        self.assertGreater(sig["stop"], strike)       # Stop hinter der Wand


class EinstiegTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (buch.SCHREIBEN, h.zeit_quelle, h.markt_quelle)
        buch.SCHREIBEN = True
        h.zeit_quelle = lambda: JETZT
        h.markt_quelle = None
        # Spur auf Temp umbiegen.
        h.wachen_pfad = os.path.join(self.tmp.name, "wachen.json")
        h.zustand_pfad = os.path.join(self.tmp.name, "zustand.json")
        h.journal_pfad = os.path.join(self.tmp.name, "handelsjournal.csv")
        w = _wachen(os.path.join(self.tmp.name, "zweitziel"))
        with open(h.wachen_pfad, "w", encoding="utf-8") as f:
            json.dump(w, f)

    def tearDown(self):
        (buch.SCHREIBEN, h.zeit_quelle, h.markt_quelle) = self.alt
        self.tmp.cleanup()

    def _signal(self):
        w = _wachen("/tmp")
        kette, strike, kurs = _call_kette(100000.0, basis=100000.0, sigma_faktor=2.0)
        d = _markt(kurs, basis=100000.0, kette=kette)
        return d, h.spanne_und_signal(d, w)

    def test_einstieg_setzt_stop_hinter_wand_und_ziel_halben_rueckweg(self):
        z = {"positionen": []}
        d, sig = self._signal()
        p = h.einstieg(z, "BTC-PERPETUAL", d, sig, _wachen("/tmp"), 1.0,
                       h.journal_pfad, h.zustand_pfad)
        self.assertIsNotNone(p)
        (pos,) = z["positionen"]
        self.assertEqual(pos["seite"], "short")
        self.assertGreater(pos["stop"], sig["wand"])
        # Ziel = halber Rueckweg zur Mitte: ziel < einstieg.
        self.assertLess(pos["ziel"], pos["einstieg"])
        self.assertAlmostEqual(pos["ziel_anteil"] if "ziel_anteil" in pos
                               else 0.5, 0.5, places=6)

    def test_kein_einstieg_bei_kein_signal(self):
        z = {"positionen": []}
        sig = {"richtung": "kein_signal"}
        self.assertIsNone(h.einstieg(z, "BTC-PERPETUAL", {}, sig,
                                     _wachen("/tmp"), 1.0, h.journal_pfad,
                                     h.zustand_pfad))
        self.assertEqual(z["positionen"], [])

    def test_buch_voll_laesst_keinen_einstieg(self):
        w = _wachen("/tmp")
        w["max_offene_positionen"] = 1
        z = {"positionen": [{"inst": "ANDERE"}]}
        d, sig = self._signal()
        self.assertIsNone(h.einstieg(z, "BTC-PERPETUAL", d, sig, w, 1.0,
                                     h.journal_pfad, h.zustand_pfad))

    def test_ratsche_halbiert_das_nominal(self):
        z = {"positionen": []}
        d, sig = self._signal()
        w = _wachen("/tmp")
        p_voll = h.einstieg(z, "BTC-PERPETUAL", d, sig, w, 1.0,
                            h.journal_pfad, h.zustand_pfad)
        z2 = {"positionen": []}
        p_half = h.einstieg(z2, "BTC-PERPETUAL", d, sig, w, 0.5,
                            h.journal_pfad, h.zustand_pfad)
        self.assertAlmostEqual(p_half["nominal"], p_voll["nominal"] * 0.5,
                               places=4)


class LaufTest(unittest.TestCase):
    """Der volle Lauf gegen einen Temp-Ordner - kein Netz, kein Orderpfad."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (buch.SCHREIBEN, h.zeit_quelle, h.markt_quelle,
                    h.wachen_pfad, h.zustand_pfad, h.journal_pfad)
        buch.SCHREIBEN = True
        h.zeit_quelle = lambda: JETZT
        h.wachen_pfad = os.path.join(self.tmp.name, "wachen.json")
        h.zustand_pfad = os.path.join(self.tmp.name, "zustand.json")
        h.journal_pfad = os.path.join(self.tmp.name, "handelsjournal.csv")
        w = _wachen(os.path.join(self.tmp.name, "zweitziel"))
        with open(h.wachen_pfad, "w", encoding="utf-8") as f:
            json.dump(w, f)

    def tearDown(self):
        (buch.SCHREIBEN, h.zeit_quelle, h.markt_quelle,
         h.wachen_pfad, h.zustand_pfad, h.journal_pfad) = self.alt
        self.tmp.cleanup()

    def test_vorschau_schreibt_nichts(self):
        kette, strike, kurs = _call_kette(100000.0, basis=100000.0, sigma_faktor=2.0)
        h.markt_quelle = lambda w_: (
            {"BTC-PERPETUAL": _markt(kurs, basis=100000.0, kette=kette)},
            {"BTC-PERPETUAL": kurs}, [])
        h.lauf("vorschau")
        self.assertFalse(os.path.exists(h.journal_pfad))
        self.assertFalse(os.path.exists(h.zustand_pfad))
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "zweitziel")))

    def test_vorschau_bucht_auch_keinen_ausstieg(self):
        # Position am Stop: pruefe_ausstiege WUERDE schliessen und ins
        # Journal buchen. In der Vorschau passiert das nie - ein Exit ist
        # eine Buchung, keine Ansage.
        position = {"inst": "BTC-PERPETUAL", "seite": "long",
                    "einstieg": 100000.0, "stop": 100500.0, "ziel": 110000.0,
                    "nominal": 100.0, "stop_pct": 0.5}
        with open(h.zustand_pfad, "w", encoding="utf-8") as f:
            json.dump({"positionen": [position]}, f)
        h.markt_quelle = lambda w_: (
            {"BTC-PERPETUAL": _markt(100400.0, basis=100000.0)},
            {"BTC-PERPETUAL": 100400.0}, [])   # unter dem Stop
        h.lauf("vorschau")
        self.assertFalse(os.path.exists(h.journal_pfad),
                         "Vorschau hat einen Ausstieg gebucht")
        with open(h.zustand_pfad, encoding="utf-8") as f:
            z = json.load(f)
        self.assertEqual(len(z["positionen"]), 1,
                         "Vorschau hat die Position veraendert")

    def test_papierlauf_bucht_und_spiegelt(self):
        kette, strike, kurs = _call_kette(100000.0, basis=100000.0, sigma_faktor=2.0)
        h.markt_quelle = lambda w_: (
            {"BTC-PERPETUAL": _markt(kurs, basis=100000.0, kette=kette)},
            {"BTC-PERPETUAL": kurs}, [])
        h.lauf("papier")
        self.assertTrue(os.path.exists(h.journal_pfad))
        self.assertTrue(os.path.exists(h.zustand_pfad))
        with open(h.zustand_pfad, encoding="utf-8") as f:
            z = json.load(f)
        self.assertEqual(len(z["positionen"]), 1)
        pos = z["positionen"][0]
        self.assertEqual(pos["seite"], "short")
        self.assertGreater(pos["stop"], pos["einstieg"])
        # Bedingung 4: die Kopie liegt im Zweitziel.
        self.assertTrue(os.path.exists(os.path.join(
            self.tmp.name, "zweitziel", "handelsjournal.csv")))

    def test_quelle_fehler_bricht_nicht_ab(self):
        def kaputt(_w_):
            return {}, {}, ["Indexpreis: weg"]
        h.markt_quelle = kaputt
        h.lauf("papier")                              # darf nicht werfen
        self.assertFalse(os.path.exists(h.journal_pfad))


if __name__ == "__main__":
    unittest.main(verbosity=2)