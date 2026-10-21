r"""Wache des omnitrade2-XPERP-Laufs: Deckel-Ablehnung ist NORMAL, Abbruch zaehlt.

Zwei Regeln aus dem Grill vom 21.10.2026, beide vorher nicht geprueft:

  * Eine Ablehnung durch den POSITIONSDECKEL ist erwartetes Verhalten - der Plan
    haelt nur begrenzte Stufen, die Strategie wiederholt ihr Signal minuetlich.
    Vorher stand der Notional-Wert IM Meldungstext, also galt jede Ablehnung als
    neuer Fehler (6 Meldungen an einem Vormittag). Jetzt: zaehlen, hoechstens
    eine Zeile am Tag.
  * Der Versuch hat ein Abbruchkriterium (kumuliert -2,50 USD oder drei
    Verlustrunden in Folge). Gemessen wird an der BOERSE
    (positions-history/realizedPnl), nicht am Loop-Status - der fuehrt kein
    Ergebnis.

Aufruf aus `Agenten/Handel/tests`:
    ..\scanner\.venv\Scripts\python.exe -m unittest test_omnitrade2_wache
"""

import contextlib
import importlib.util
import io
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))          # Agenten/Handel/tests
AGENTEN = os.path.dirname(os.path.dirname(HIER))          # Agenten
PFAD = os.path.join(AGENTEN, "Hermes", "scripts", "omnitrade2-sol-wache.py")

_spec = importlib.util.spec_from_file_location("omnitrade2_wache_test", PFAD)
if _spec is None or not os.path.exists(PFAD):  # pragma: no cover - Pfadfehler laut
    raise SystemExit("Wache nicht gefunden: %s" % PFAD)
wache = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = wache
_spec.loader.exec_module(wache)

DECKEL_TEXT = ("Risk guard rejection: Positionsdeckel überschritten: 40.3674 > "
               "25.00 (Laufposition -0.3800)")


class IstDeckelTest(unittest.TestCase):
    def test_deckelmeldung_wird_erkannt(self):
        self.assertTrue(wache.ist_deckel(DECKEL_TEXT))

    def test_echter_fehler_ist_kein_deckel(self):
        self.assertFalse(wache.ist_deckel("Order rejected: 51008 balance insufficient"))
        self.assertFalse(wache.ist_deckel(""))


class AblehnungenTest(unittest.TestCase):
    def setUp(self):
        self.merk = {"tag": "2026-10-21", "meldungen": 0, "deckel_zaehler": 0}

    def _ruf(self, rejected, text):
        with contextlib.redirect_stdout(io.StringIO()) as aus:
            zahl = wache.ablehnungen(self.merk, {"orders_rejected": rejected, "last_error": text})
        return zahl, aus.getvalue()

    def test_deckel_wird_einmal_am_tag_genannt(self):
        zahl, text = self._ruf(3, DECKEL_TEXT)
        self.assertEqual(zahl, 1)
        self.assertIn("Deckel-Ablehnung", text)
        # zweite Ablehnung derselben Art am selben Tag: still
        zahl2, text2 = self._ruf(4, DECKEL_TEXT)
        self.assertEqual(zahl2, 0)
        self.assertEqual(text2, "")

    def test_deckel_zaehlt_weiter_ohne_zu_melden(self):
        self._ruf(3, DECKEL_TEXT)
        self._ruf(7, DECKEL_TEXT)
        self.assertEqual(self.merk["deckel_zaehler"], 7)
        self.assertEqual(self.merk["rejected_seen"], 7)

    def test_am_naechsten_tag_wieder_eine_zeile(self):
        self._ruf(3, DECKEL_TEXT)
        self.merk["tag"] = "2026-10-22"
        zahl, _text = self._ruf(5, DECKEL_TEXT)
        self.assertEqual(zahl, 1)

    def test_echte_ablehnung_wird_immer_gemeldet(self):
        zahl, text = self._ruf(1, "Order rejected: 51008 balance insufficient")
        self.assertEqual(zahl, 1)
        self.assertIn("ABGELEHNT", text)
        zahl2, text2 = self._ruf(2, "Order rejected: 51008 balance insufficient")
        self.assertEqual(zahl2, 1)
        self.assertIn("ABGELEHNT", text2)


class FakeOkxf:
    def __init__(self, eintraege):
        self.eintraege = eintraege

    def geschlossene_positionen(self, inst=None, limit=20):
        return list(self.eintraege)


class FakeNachzieher:
    def __init__(self, eintraege):
        self.okxf = FakeOkxf(eintraege)

    def okxf_laden(self):
        return self.okxf


class AbbruchTest(unittest.TestCase):
    SEIT = 1_000_000

    def setUp(self):
        self.merk = {"tag": "2026-10-21", "meldungen": 0}
        self.st = {"symbol": "SOL-USD_UM_XPERP-310404", "started_ms": self.SEIT}
        self.alt = wache._nachzieher

    def tearDown(self):
        wache._nachzieher = self.alt

    def _pruef(self, eintraege):
        wache._nachzieher = lambda: (FakeNachzieher(eintraege), None)
        with contextlib.redirect_stdout(io.StringIO()) as aus:
            zahl = wache.abbruchpruefung(self.merk, self.st)
        return zahl, aus.getvalue()

    @staticmethod
    def _eintrag(u_time, pnl):
        return {"uTime": str(u_time), "realizedPnl": str(pnl)}

    def test_kumulierter_verlust_erreicht_die_grenze(self):
        zahl, text = self._pruef([self._eintrag(1_000_100, -1.4),
                                  self._eintrag(1_000_200, -1.2)])
        self.assertEqual(zahl, 1)
        self.assertIn("ABBRUCHKRITERIUM", text)
        self.assertIn("-2.60", text)

    def test_kleiner_verlust_meldet_nichts(self):
        zahl, text = self._pruef([self._eintrag(1_000_100, -0.4)])
        self.assertEqual(zahl, 0)
        self.assertEqual(text, "")

    def test_drei_verlustrunden_in_folge(self):
        zahl, text = self._pruef([self._eintrag(1_000_300, -0.2),
                                  self._eintrag(1_000_200, -0.3),
                                  self._eintrag(1_000_100, -0.1)])
        self.assertEqual(zahl, 1)
        self.assertIn("3 Verlustrunden in Folge", text)

    def test_gewinn_unterbricht_die_folge(self):
        zahl, _text = self._pruef([self._eintrag(1_000_400, -0.2),
                                   self._eintrag(1_000_300, -0.2),
                                   self._eintrag(1_000_200, 0.5),
                                   self._eintrag(1_000_100, -0.2)])
        self.assertEqual(zahl, 0)

    def test_schliessungen_vor_dem_start_zaehlen_nicht(self):
        zahl, _text = self._pruef([self._eintrag(999_000, -5.0),
                                   self._eintrag(999_500, -5.0)])
        self.assertEqual(zahl, 0)

    def test_dieselbe_feststellung_wird_nicht_wiederholt(self):
        self._pruef([self._eintrag(1_000_100, -3.0)])
        zahl, text = self._pruef([self._eintrag(1_000_100, -3.0)])
        self.assertEqual(zahl, 0)
        self.assertEqual(text, "")


if __name__ == "__main__":
    unittest.main()
