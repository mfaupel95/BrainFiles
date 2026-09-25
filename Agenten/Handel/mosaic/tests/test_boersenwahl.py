"""Zwei Boersen fuer eine Spur: Wahl, Bindung und Ausstieg.

Auftrag Max 23.09.2026: "Mosaic live schalten, gerne auf okx und kraken."
Geprueft wird:
 (a) boersen_liste: Liste aus `boersen`, altes einzelnes `boerse` gilt weiter,
     unbekannter Name ist ein Fehler (kein stiller Ersatz);
 (b) venue_binden: erste EINSATZBEREITE Boerse gewinnt (Schluessel, Demo,
     Guthaben in der Waehrung der Boerse); keine bereit -> die erste;
 (c) venue_fuer_position: eine Position an einer anderen Boerse wird beim
     Ausstieg dort gebunden, ohne Feld bleibt es bei der gebundenen Boerse;
 (d) eine Live-Position traegt ihr `boerse`-Feld (Stempel beim Einstieg).

Kein Netz: alle Boersenfunktionen sind Attrappen, das Guthaben laeuft ueber die
Naht handeln._guthaben_roh. Zustand/Journal zeigen auf ein Temp-Verzeichnis,
ein Modulwaechter vergleicht danach den echten Spurenordner.
"""

import os
import sys
import tempfile
import types
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln  # noqa: E402


def _ordner_stand():
    out = {}
    for name in ("zustand.json", "zustand.mittel.json",
                 "handelsjournal.csv", "handelsjournal.mittel.csv"):
        p = os.path.join(HIER, name)
        out[name] = os.path.getsize(p) if os.path.exists(p) else None
    return out


def setUpModule():
    global _vorher
    _vorher = _ordner_stand()


def tearDownModule():
    nach = _ordner_stand()
    geaendert = [k for k in nach if nach[k] != _vorher.get(k)]
    assert not geaendert, ("Test hat in den ECHTEN Spurenordner geschrieben: %s"
                           % geaendert)


def _boerse_attrappe(name, frei=1000.0, schluessel=True, demo=False):
    """Ein Modul-Ersatz mit genau den Namen, die handeln.py benutzt."""
    return types.SimpleNamespace(
        __name__="attrappe_" + name,
        schluessel_vorhanden=lambda: schluessel,
        demo_modus=lambda: demo,
        guthaben_waehrung=lambda ccy, _f=frei: _f,
        markt_kauf=lambda inst, menge: "OID-" + name,
        markt_verkauf=lambda inst, menge: "TRX-" + name,
        algo_stop_setzen=lambda inst, menge, seite, preis: "ALG-" + name,
        algo_stornieren=lambda inst, algo: None,
        gefuellte_menge=lambda inst, oid: 0.0,
        letzter_kurs=lambda inst: 100.0,
        menge_fuer=lambda inst, betrag, kurs: (betrag / kurs, None),
    )


QW = {"boersen": ["kraken", "okx"], "mindest_guthaben": 60.0,
      "guthaben_waehrung_je_boerse": {"kraken": "EUR", "okx": "USDC"}}


class BoersenWahlTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self._saved = (handeln.ZUSTAND, handeln.JOURNAL, handeln.BOERSEN,
                       handeln.VENUE_NAME, handeln.VENUE,
                       handeln.GUTHABEN_WAEHRUNG, handeln.MINDEST_GUTHABEN)
        handeln.ZUSTAND = os.path.join(self.tmp, "zustand.json")
        handeln.JOURNAL = os.path.join(self.tmp, "handelsjournal.csv")
        handeln.BOERSEN = {"kraken": _boerse_attrappe("kraken"),
                           "okx": _boerse_attrappe("okx")}
        self._saved_guthaben = handeln._guthaben_roh

    def tearDown(self):
        (handeln.ZUSTAND, handeln.JOURNAL, handeln.BOERSEN,
         handeln.VENUE_NAME, handeln.VENUE,
         handeln.GUTHABEN_WAEHRUNG, handeln.MINDEST_GUTHABEN) = self._saved
        handeln._guthaben_roh = self._saved_guthaben
        # Die Seams (op_kauf & Co.) zeigen sonst auf die Attrappen und
        # verwirren die naechste Testdatei: echte Module neu binden.
        handeln.venue_binden({"boersen": ["kraken"]}, "kraken")
        self._tmp.cleanup()

    def _guthaben(self, werte):
        handeln._guthaben_roh = lambda name, ccy: werte.get(name, 0.0)

    # (a)
    def test_liste_aus_boersen(self):
        self.assertEqual(handeln.boersen_liste(QW), ["kraken", "okx"])

    def test_einzelne_boerse_gilt_weiter(self):
        self.assertEqual(handeln.boersen_liste({"boerse": "okx"}), ["okx"])
        self.assertEqual(handeln.boersen_liste({}), ["okx"])

    def test_unbekannte_boerse_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            handeln.boersen_liste({"boersen": ["kraken", "bitfinex"]})

    # (b)
    def test_erste_bereite_gewinnt(self):
        self._guthaben({"kraken": 10.0, "okx": 500.0})
        self.assertEqual(handeln.venue_binden(QW), "okx")
        self.assertEqual(handeln.GUTHABEN_WAEHRUNG, "USDC")

    def test_kraken_gewinnt_wenn_es_guthaben_hat(self):
        self._guthaben({"kraken": 100.0, "okx": 500.0})
        self.assertEqual(handeln.venue_binden(QW), "kraken")
        self.assertEqual(handeln.GUTHABEN_WAEHRUNG, "EUR")

    def test_keine_bereit_bleibt_bei_der_ersten(self):
        self._guthaben({"kraken": 1.0, "okx": 2.0})
        self.assertEqual(handeln.venue_binden(QW), "kraken")

    def test_demo_sperrt_die_boerse(self):
        handeln.BOERSEN["kraken"] = _boerse_attrappe("kraken", demo=True)
        self._guthaben({"kraken": 100.0, "okx": 500.0})
        self.assertEqual(handeln.venue_binden(QW), "okx")

    def test_fehlender_schluessel_sperrt_die_boerse(self):
        handeln.BOERSEN["kraken"] = _boerse_attrappe("kraken", schluessel=False)
        self._guthaben({"kraken": 100.0, "okx": 500.0})
        self.assertEqual(handeln.venue_binden(QW), "okx")

    def test_einzelne_boerse_bindet_ohne_guthabenabfrage(self):
        gerufen = []
        handeln._guthaben_roh = lambda name, ccy: gerufen.append(name) or 0.0
        self.assertEqual(handeln.venue_binden({"boersen": ["kraken"],
                                               "mindest_guthaben": 60.0}),
                         "kraken")
        self.assertEqual(gerufen, [], "Einzelboerse darf nicht extra abfragen")

    # (c)
    def test_position_an_anderer_boerse_wird_dort_gebunden(self):
        self._guthaben({"kraken": 100.0, "okx": 500.0})
        handeln.venue_binden(QW)
        self.assertEqual(handeln.VENUE_NAME, "kraken")
        p = {"inst": "BTC-USDC", "modus": "live", "boerse": "okx"}
        self.assertEqual(handeln.venue_fuer_position(p, QW), "okx")
        self.assertEqual(handeln.VENUE_NAME, "okx")

    def test_position_ohne_boerse_bleibt(self):
        self._guthaben({"kraken": 100.0, "okx": 500.0})
        handeln.venue_binden(QW)
        self.assertIsNone(handeln.venue_fuer_position(
            {"inst": "SOL-USDC", "modus": "live"}, QW))
        self.assertEqual(handeln.VENUE_NAME, "kraken")

    def test_unbekannte_boerse_in_der_position_ist_ein_fehler(self):
        handeln.venue_binden(QW)
        with self.assertRaises(ValueError):
            handeln.venue_fuer_position({"inst": "X", "boerse": "bitfinex"}, QW)


class SperrgrundNenntDieBoerse(unittest.TestCase):
    """Der Guthaben-Sperrgrund nennt die Boerse - und die uebrigen mit.

    Anlass (25.09.2026): Die Meldung "nur 0.71 EUR frei, noetig 60.00" liest
    sich wie OKX, denn dort liegen USDC; gefragt war aber Kraken (EUR). Beide
    Boersen hatten kein Geld. Wer den Grund liest, soll das sehen.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._saved = (handeln.BOERSEN, handeln.VENUE_NAME, handeln.VENUE,
                       handeln.GUTHABEN_WAEHRUNG, handeln.MINDEST_GUTHABEN,
                       handeln._guthaben_roh, handeln.risikostufe.live_erlaubt,
                       handeln.sitzung_da, handeln.zeitfenster_offen)
        handeln.BOERSEN = {"kraken": _boerse_attrappe("kraken"),
                           "okx": _boerse_attrappe("okx")}
        handeln.risikostufe.live_erlaubt = lambda: True
        handeln.sitzung_da = lambda: False
        # Zeitfenster offen: sonst stuende der Fenster-Grund daneben und der
        # Test prueft die Liste statt der Meldung.
        handeln.zeitfenster_offen = lambda: True

    def tearDown(self):
        (handeln.BOERSEN, handeln.VENUE_NAME, handeln.VENUE,
         handeln.GUTHABEN_WAEHRUNG, handeln.MINDEST_GUTHABEN,
         handeln._guthaben_roh, handeln.risikostufe.live_erlaubt,
         handeln.sitzung_da, handeln.zeitfenster_offen) = self._saved
        handeln.venue_binden({"boersen": ["kraken"]}, "kraken")
        self._tmp.cleanup()

    def _guthaben(self, werte):
        handeln._guthaben_roh = lambda name, ccy: werte.get(name, 0.0)

    def _boersen(self, kraken, okx):
        """Beide Boersen mit einem freien Betrag belegen.

        Zwei Stellen sind zu fuellen: die gebundene Boerse fragt ueber die Naht
        op_guthaben (Modulattrappe), die Nachbarbseite ueber _guthaben_roh.
        """
        handeln.BOERSEN = {"kraken": _boerse_attrappe("kraken", frei=kraken),
                           "okx": _boerse_attrappe("okx", frei=okx)}
        self._guthaben({"kraken": kraken, "okx": okx})

    def _w(self):
        return dict(QW, handel_erlaubt=True, journal_zweitziel="Q:\\Test")

    def _lage(self):
        return {"freigabe_erfuellt": True, "herzschlag_frisch": True,
                "ev_negativ": False, "rollierender_ev": 1.0}

    def test_grund_nennt_boerse_waehrung_und_die_zweite(self):
        self._boersen(0.71, 0.03)
        handeln.venue_binden(QW)
        g = handeln.live_sperren(self._w(), self._lage())
        self.assertEqual(len(g), 1)
        self.assertIn("kraken: nur 0.71 EUR frei, noetig 60.00", g[0])
        self.assertIn("okx: nur 0.03 USDC frei, noetig 60.00", g[0])

    def test_genug_guthaben_ergibt_keinen_grund(self):
        self._boersen(100.0, 100.0)
        handeln.venue_binden(QW)
        self.assertEqual(handeln.live_sperren(self._w(), self._lage()), [])


if __name__ == "__main__":
    unittest.main()