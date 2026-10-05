"""Der gehebelte Weg fuer mosaic (okx_perp) - die Rechnung, nicht der Draht.

Anlass (05.10.2026, Auftrag Max 'mosaic auf futures ... anbinden'): die Spur
hatte nur zwei SPOT-Wege. okx_spot.py ist `tdMode=cash` und damit strukturell
unfaehig, einen Hebel zu setzen. okx_perp.py stellt denselben Funktionssatz
wie die beiden anderen bereit, damit handeln.py unveraendert bleibt.

Diese Tests decken die vier Stellen ab, an denen ein gehebelt Weg von einem
Spot-Weg ABWEICHET - jede davon war entweder schon ein Fehler oder haette
einer werden koennen:

  1. `menge_fuer` rechnet NENNWERT (Margin x Hebel), nicht Margin. Verwechlt
     heisst: 100 USD Margin kaufen 100 USD Nennwert = 1x statt 6x.
  2. `stop_vor_liq` verweigert einen Stop, der die Liquidationsmarke nicht
     erreicht. Ein Long muss liq < stop < einstieg haben. Der erste Fassung
     dieser Pruefung hatte die Ungleichung VERKEHRT und lehnte jeden
     regulaeren Stop ab (gefunden am echten Lauf, nicht im Test).
  3. `guthaben_waehrung` liest `details[0]`, nicht die oberste Ebene - OKX
     liefert oben leere Strings. Mit den oberen Feldern kommt 0.00 heraus,
     das sieht wie ein leeres Konto aus und sperrt die Spur an einem Tor,
     das offen ist.
  4. Ein unbekannter Basiswert ist ein FEHLER, kein Rueckfall auf ein anderes
     Instrument.

Kein Test ruft das Netz: `_mit_wiederholung` wird ersetzt, sobald er gebraucht
wird (die Instrumentliste). Alles andere sind reine Funktionen.
"""

import importlib.util
import os
import pathlib
import sys
import unittest

HANDEL = pathlib.Path(__file__).resolve().parents[2]
SPUR = pathlib.Path(__file__).resolve().parents[1]

for pfad in (str(HANDEL), str(SPUR), str(SPUR / "xperp")):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

sys.modules.pop("okx_perp", None)
_spec = importlib.util.spec_from_file_location(
    "okx_perp_testmod", SPUR / "okx_perp.py")
op = importlib.util.module_from_spec(_spec)
sys.modules["okx_perp_testmod"] = op
_spec.loader.exec_module(op)


# --- Attrappen ---------------------------------------------------------------

_XPERP_BTC = {
    "instId": "BTC-USD_UM_XPERP-310404", "ruleType": "xperp",
    "state": "live", "ctVal": "0.0001", "ctValCcy": "BTC",
    "tickSz": "0.1", "lotSz": "1", "minSz": "1",
}
_XPERP_SOL = {
    "instId": "SOL-USD_UM_XPERP-310404", "ruleType": "xperp",
    "state": "live", "ctVal": "0.01", "ctValCcy": "SOL",
    "tickSz": "0.01", "lotSz": "1", "minSz": "1",
}


class AttrappenOkxf:
    """Ersetzt okxf NUR fuer die Instrumentliste. Alles andere bleibt der
    echte Weg - so schlaegt ein Fehler in der eigenen Datei durch."""

    def __init__(self, orig):
        self.__dict__["_orig"] = orig

    def __getattr__(self, name):
        return getattr(self._orig, name)

    def _mit_wiederholung(self, *a, **kw):
        if a and str(a[0]).startswith("/api/v5/public/instruments"):
            return [_XPERP_BTC, _XPERP_SOL]
        return self._orig._mit_wiederholung(*a, **kw)


def mit_attrappe(test):
    echt = op.okxf
    op.okxf = AttrappenOkxf(echt)
    try:
        test()
    finally:
        op.okxf = echt


class PerpTest(unittest.TestCase):
    """Der Weg findet den Kontrakt und rechnet in Kontrakten."""

    def test_hauptfunktionen_vorhanden(self):
        """Dieselbe Funktionsnamen wie die beiden Spot-Wege - sonst bindet
        venue_binden() den Weg nicht und die Spur ordert ungehebelt."""
        for name in ("schluessel_vorhanden", "demo_modus", "markt_kauf",
                     "markt_verkauf", "algo_stop_setzen", "algo_stornieren",
                     "gefuellte_menge", "guthaben_waehrung", "letzter_kurs",
                     "menge_fuer"):
            self.assertTrue(hasattr(op, name), name)

    def test_spot_instanz_hat_keinen_hebel(self):
        """Die Behauptung, warum es diesen Weg gibt, muss WAHR sein: der
        Spot-Weg kann keinen Hebel. Faellt sie, waere der ganze Aufbau
        ueberfluessig."""
        echt = op.okxf
        op.okxf = echt
        spot = importlib.util.module_from_spec(
            importlib.util.spec_from_file_location(
                "okx_spot_testmod", SPUR / "okx_spot.py"))
        importlib.util.spec_from_file_location(
            "okx_spot_testmod", SPUR / "okx_spot.py").loader.exec_module(spot)
        self.assertFalse(hasattr(spot, "hebel_setzen"))
        self.assertFalse(hasattr(spot, "stop_vor_liq"))
        self.assertIn('"tdMode": "cash"', (SPUR / "okx_spot.py")
                      .read_text(encoding="utf-8"))

    def test_perp_fuer_findet_den_kontrakt(self):
        mit_attrappe(self._pruefe_finden)

    def _pruefe_finden(self):
        info = op.perp_fuer("BTC-USDC")
        self.assertEqual(info["instId"], "BTC-USD_UM_XPERP-310404")
        # Der Basiswert genuegt, das Suffix der Wache nicht
        self.assertEqual(op.perp_fuer("SOL-USDC")["instId"],
                         "SOL-USD_UM_XPERP-310404")

    def test_unbekannter_basiswert_ist_ein_fehler(self):
        mit_attrappe(self._pruefe_fehler)

    def _pruefe_fehler(self):
        # Kein Rueckfall auf ein anderes Instrument: still das falsche zu
        # handeln waere der teuerste Fehler dieser Datei.
        with self.assertRaises(op.OKXFehler):
            op.perp_fuer("XYZ-USDC")

    def test_menge_rechnet_nennwert_nicht_margin(self):
        mit_attrappe(self._pruefe_menge)

    def _pruefe_menge(self):
        info = op.perp_fuer("BTC-USDC")
        kurs = 86000.0
        n, fehler = op.menge_fuer("BTC-USDC", 600.0, kurs, info=info)
        self.assertIsNone(fehler)
        # 600 USD / 86000 / 0.0001 BTC = 69,77 -> auf lotSz 1 abgerundet 69
        self.assertEqual(n, 69.0)
        # ctVal ist die Falle: ohne sie kaeme der Faktor 10000 zu gross
        self.assertEqual(n * kurs * float(info["ctVal"]), 593.4)
        zu, _ = op.menge_fuer("BTC-USDC", 100.0, kurs, info=info)
        self.assertLess(zu, n, "100 USD Nennwert muessen weniger Kontrakte "
                               "geben als 600 - sonst rechnet die Funktion "
                               "Margin")

    def test_menge_unter_mindestmenge(self):
        mit_attrappe(self._pruefe_mindest)

    def _pruefe_mindest(self):
        n, fehler = op.menge_fuer("BTC-USDC", 0.5, 86000.0,
                                  info=op.perp_fuer("BTC-USDC"))
        self.assertEqual(n, 0.0)
        self.assertTrue(fehler)


class LiquidationsTest(unittest.TestCase):
    """Die eine Pruefung, die es bei Spot nicht gibt.

    Ein Long verliert, wenn der Kurs faellt: er trifft zuerst den naeher am
    Einstieg liegenden Stop, erst danach die tiefer liegende
    Liquidationsmarke. Also muss `liq < stop < einstieg` gelten. Die erste
    Fassung dieser Funktion drehte die Ungleichung um und lehnte jeden
    regulaeren Stop ab - gefunden am echten Lauf, nicht im Test.
    """

    def test_long_stop_zwischen_liq_und_einstieg(self):
        for stop in (99.0, 95.0, 90.0, 83.9):
            ok, grund = op.stop_vor_liq(stop, 100.0, 6, "long")
            self.assertTrue(ok, "Stop %s muss bei 6x kommen: %s"
                            % (stop, grund))

    def test_long_stop_unter_liq_kaeme_nie(self):
        for stop in (83.8, 83.0, 72.0):
            ok, grund = op.stop_vor_liq(stop, 100.0, 6, "long")
            self.assertFalse(ok, "Stop %s liegt auf/unter liq" % stop)
            self.assertIn("kaeme nie", grund)

    def test_long_stop_auf_dem_kurs_verkauft_sofort(self):
        ok, grund = op.stop_vor_liq(100.0, 100.0, 6, "long")
        self.assertFalse(ok)
        self.assertIn("verkauft sofort", grund)

    def test_short_ist_der_spiegel(self):
        self.assertTrue(op.stop_vor_liq(105.0, 100.0, 6, "short")[0])
        self.assertTrue(op.stop_vor_liq(110.0, 100.0, 6, "short")[0])
        self.assertFalse(op.stop_vor_liq(116.2, 100.0, 6, "short")[0])
        ok, grund = op.stop_vor_liq(116.2, 100.0, 6, "short")
        self.assertIn("kaeme nie", grund)
        self.assertFalse(op.stop_vor_liq(99.0, 100.0, 6, "short")[0])

    def test_grenze_liegt_erwartbar(self):
        """Die Hebelgrenze ist eine Rechnung, kein Wunsch: bei 6x ist die
        Liquidation 16,17 % entfernt und jeder Stop der Spur (5-12 %) kommt
        vorher. Erst weit ueber 10x wird ein 5-%-Stop unerreichbar."""
        self.assertTrue(op.stop_vor_liq(95.0, 100.0, 6, "long")[0])
        self.assertTrue(op.stop_vor_liq(95.0, 100.0, 15, "long")[0])
        self.assertFalse(op.stop_vor_liq(95.0, 100.0, 20, "long")[0])

    def test_liquidationspreis_ist_gespiegelt(self):
        self.assertAlmostEqual(op.liquidationspreis(100.0, 6, "long"), 83.8333,
                               places=3)
        self.assertAlmostEqual(op.liquidationspreis(100.0, 6, "short"),
                               116.1667, places=3)


class GuthabenTest(unittest.TestCase):
    """Die Waehrung steht in `details`, nicht oben.

    Mit den oberen Feldern las die erste Fassung 0.00 - das sieht wie ein
    leeres Konto aus und sperrt die Spur an einem Guthaben-Tor, das offen
    ist. Der Test haelt genau diese Antwortform fest.
    """

    def test_liest_details(self):
        echt = op.okxf

        class K:
            @staticmethod
            def _mit_wiederholung(*a, **kw):
                return [{"availEq": "", "availBal": None, "eq": None,
                         "details": [{"ccy": "USDC",
                                      "availEq": "302.38611026017145",
                                      "eq": "845.88"}]}]

        op.okxf = K
        try:
            self.assertAlmostEqual(op.guthaben_waehrung(), 302.38611, places=4)
        finally:
            op.okxf = echt

    def test_leeres_konto_ist_null_nicht_fehler(self):
        echt = op.okxf

        class K:
            @staticmethod
            def _mit_wiederholung(*a, **kw):
                return [{"details": [{"ccy": "USDC", "availEq": "0"}]}]

        op.okxf = K
        try:
            self.assertEqual(op.guthaben_waehrung(), 0.0)
        finally:
            op.okxf = echt


class VerdrahtungTest(unittest.TestCase):
    """handeln.py muss den Weg kennen - und ihn vom Nominal unterscheiden."""

    def setUp(self):
        self.text = (SPUR / "handeln.py").read_text(encoding="utf-8")

    def test_weg_in_der_boersentabelle(self):
        self.assertIn('"okx_perp": okx_perp', self.text)
        self.assertIn('NOMINAL_STATT_MARGINAL = {"okx_perp"}', self.text)

    def test_hebel_geht_an_den_kauf(self):
        """Der Hebel wird uebergeben, nicht in der Wache gesucht: ein Kauf
        ohne Hebel waere eine ungehebelte Order auf einem gehebelten Weg."""
        self.assertIn("hebel_aus(w)", self.text)
        self.assertIn("op_kauf(inst, menge, hebel_aus(w))", self.text)

    def test_kein_hebel_ueber_die_deckelgrenze(self):
        self.assertIn("HEBEL_MAX = 6", self.text)

    def test_der_betrag_geht_nominal_an_menge_fuer(self):
        """Sonst kauft der gehebelte Weg Margin statt Nennwert."""
        self.assertIn("live_menge_fuer(inst, nominal, kurs)", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)