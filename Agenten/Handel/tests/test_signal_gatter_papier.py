"""Das Signal-Gatter gilt nur im LIVE-Betrieb (T-347).

BEFUND (gemessen 04.10.2026): `trigger_modus: signal` legte seinen Auftrag in
die signal_queue und kehrte zurueck - in JEDEM Modus. Eine Spur mit
`handel_erlaubt=false` wartete damit auf einen signal-executor, der sie nie
abholt (er scheitert selbst an handel_erlaubt/freigabe). Ergebnis: fuenf
Spuren mit vorhandenem Signal und NULL Buchzeilen (nautilus_emacross,
omnitrade, omnitrade_futures, trendwende_btc, iv_waelle).

TEIL 1 - die beiden Regeln als reine Funktionen, ohne Zyklus und ohne
Broker:
  * `signal_gatter_gilt(w, live)` - wann das Gatter ueberhaupt greift.
  * `signal_gewechselt(z, inst, seite, w)` - ob sich die Richtung bewegt hat.
Beide sind extrahiert, weil ein Test des Live-Zweigs sonst eine offene
Freigabekette braeuchte - und eine, die zu oeffnen waere genau das, was der
Test nicht tun darf.

TEIL 2 - der Papier-Zyklus mit echten Dateien in einem Tempordner:
Papier bucht das Signal in das Buch, die Queue bleibt leer, und ein zweiter
Takt legt keinen zweiten Einstieg an (Hausregel "ein Instrument, eine
Position" in `einstieg`).

GEGENPROBE: `signal_gatter_gilt(w, live)` mit umgekehrtem `live` wirft die
beiden Live-Aussagen um; `signal_gewechselt` mit `alt != seite` konstant
immer True macht beide Wechsel-Tests rot.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HANDEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      os.pardir))
for p in (HANDEL, os.path.join(HANDEL, "scanner")):
    if p not in sys.path:
        sys.path.insert(0, p)

import spur_buch


class GatterGiltTest(unittest.TestCase):
    W = {"trigger_modus": "signal"}

    def test_papier_gatter_aus(self):
        self.assertFalse(spur_buch.signal_gatter_gilt(self.W, False),
                         "im Papier wird gebucht - das Gatter waere dort "
                         "nur ein Verbot zu messen (T-347)")

    def test_live_gatter_an(self):
        self.assertTrue(spur_buch.signal_gatter_gilt(self.W, True))

    def test_ohne_flag_immer_aus(self):
        self.assertFalse(spur_buch.signal_gatter_gilt({}, True))

    def test_falscher_wert_ist_kein_signal(self):
        self.assertFalse(spur_buch.signal_gatter_gilt({"trigger_modus": "takt"},
                                                       True))

    def test_leerer_live_wert_ist_kein_live(self):
        self.assertFalse(spur_buch.signal_gatter_gilt(self.W, None))


class WechselTest(unittest.TestCase):
    W = {"trigger_modus": "signal"}

    def test_erster_auftrag_durch(self):
        self.assertTrue(spur_buch.signal_gewechselt({}, "BTC", "long", self.W))

    def test_gleiche_richtung_gesperrt(self):
        z = {}
        spur_buch.signal_gewechselt(z, "BTC", "long", self.W)
        for _ in range(95):          # ein Tag im 15-Minuten-Takt
            self.assertFalse(spur_buch.signal_gewechselt(z, "BTC", "long",
                                                         self.W))

    def test_richtungswechsel_durch(self):
        z = {}
        spur_buch.signal_gewechselt(z, "BTC", "long", self.W)
        self.assertTrue(spur_buch.signal_gewechselt(z, "BTC", "short", self.W))

    def test_instrumente_unabhaengig(self):
        z = {}
        spur_buch.signal_gewechselt(z, "BTC", "long", self.W)
        self.assertTrue(spur_buch.signal_gewechselt(z, "ETH", "long", self.W))

    def test_verweigert_und_merkt_trotzdem(self):
        z = {}
        spur_buch.signal_gewechselt(z, "BTC", "long", self.W)
        spur_buch.signal_gewechselt(z, "BTC", "long", self.W)      # gesperrt
        self.assertEqual(z["vor_signal"]["BTC"], "long")
        self.assertFalse(spur_buch.signal_gewechselt(z, "BTC", "long",
                                                      self.W),
                         "ein verweigerter Auftrag darf beim naechsten Takt "
                         "nicht wieder 'neu' sein")


class PapierZyklusTest(unittest.TestCase):
    """Ein Lauf, eine Quelle, ein Buch - ohne Netz und ohne Broker."""

    WACHEN = {"instrument": "BTC", "trigger_modus": "signal",
              "waehrung": "USD", "max_pro_trade_usd": 100.0,
              "max_gesamt_usd": 500.0, "max_offene_positionen": 5,
              "stop_prozent": 2.0, "ziel_r_vielfaches": 2.0,
              "risiko_je_position_usd": 1.0}

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="spurbuch-gatter-")
        # Die Wachen-Datei IST der Testgegenstand - sie entsteht hier, nicht
        # im echten Spurordner. `spur_buch.lade_wachen` liest genau diese.
        with open(os.path.join(self.ordner, "wachen.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(self.WACHEN, fh)
        # signal_queue.json anlegen: der Code schreibt in die Datei, die
        # `trigger_modus` benennt, und legt sie nicht selbst an.
        with open(os.path.join(self.ordner, "signal_queue.json"), "w",
                  encoding="utf-8") as fh:
            json.dump([], fh)

    def tearDown(self):
        # EIN Waechter: der Test darf keine echte Datei anfasst. Erst
        # loeschen, dann ist der Ordner weg - NICHT zuruecksetzen, das
        # loescht die echte Datei (Lehre 03.10.2026, scanner/ablehnungen.csv).
        shutil.rmtree(self.ordner, ignore_errors=True)
        self.assertFalse(os.path.isdir(self.ordner))

    def quelle(self, w):
        return ({"BTC": {"kerzen": [{"c": 100.0}]}}, {"BTC": 100.0}, [])

    def signal(self, daten, w):
        return "long"

    def _zyklus(self):
        spur_buch.zyklus(self.ordner, self.quelle, self.signal, "papier", None)
        with open(os.path.join(self.ordner, "zustand.json"),
                  encoding="utf-8") as fh:
            z = json.load(fh)
        with open(os.path.join(self.ordner, "signal_queue.json"),
                  encoding="utf-8") as fh:
            q = json.load(fh)
        return z, q

    def test_papier_bucht_das_signal_in_das_buch(self):
        z, q = self._zyklus()
        self.assertTrue(z["positionen"],
                        "Papier muss das Signal buchen - das ist der Zweck "
                        "des Papierbetriebs (T-347)")
        self.assertEqual(q, [], "im Papier gehoert nichts in die Queue")

    def test_papier_bleibt_bei_einem_einstieg_pro_instrument(self):
        self._zyklus()
        z, _q = self._zyklus()
        self.assertEqual(len(z["positionen"]), 1,
                         "die Hausregel verbietet ein zweites Mal dasselbe "
                         "Instrument - unabhaengig vom Gatter")


if __name__ == "__main__":
    unittest.main()