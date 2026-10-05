"""signalwelle-Weg: ein Paar ist kein Kurzzeichen (Befund 05.10.2026).

Der signal-executor ruft `spur_buch.venue_inst()` und danach den Orderweg.
`venue_inst("ADA")` liefert "ADA-USDC". `boersenpaar()` haengte die Quote noch
 einmal an, suchte "ADA-USDC-USDC", fand nichts und meldete:

    ADA-USDC hat an der OKX keinen Spotmarkt (Marktliste vollstaendig gelesen)

Das war eine ERFUNDENE Tatsache. Gemessen am 05.10.2026 fuehrt die OKX 1143
Spotpaare, darunter ADA-USDC. Die Meldung stand ueber 36 Stunden im
Merkfilei des Executors und war der Grund, warum die Spur nicht handelte.

Geprueft wird die EIGENTLICHT: dasselbe Instrument darf in beiden Formen zum
selben Paar fuehren, und eine erfundene Tatsache ("kein Markt") darf nicht
mehr entstehen. Die Marktauswahl laeuft gegen eine Attrappe, damit der Test
ohne Netz und ohne OKX laeuft.

Direkt ausfuehrbar:  python moondev_signalwelle/tests/test_weg_paar.py
"""

import importlib.util
import os
import sys
import unittest
from pathlib import Path

SPUR = Path(__file__).resolve().parent.parent      # moondev_signalwelle/
HANDEL = SPUR.parent                                # Handel/
sys.path.insert(0, str(HANDEL))
sys.path.insert(0, str(HANDEL / "mosaic"))          # okx_spot


def weg_laden():
    pfad = HANDEL / "moondev_signalwelle" / "weg.py"
    spec = importlib.util.spec_from_file_location("sw_weg", pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Was die OKX am 05.10.2026 wirklich fuehrte (Auszug, 1143 Paare gesamt)
OKX_MARKT = {"ADA-USDC", "NIGHT-USDC", "AR-USDC", "MON-USDC", "SAND-USDC",
             "STRK-USDC", "BTC-USDT", "ETH-USDC", "SOL-USDC"}


class PaarOhneDoppelte(unittest.TestCase):
    def setUp(self):
        self.m = weg_laden()
        self.alt = self.m._MAERKTE[0]
        self.m._MAERKTE[0] = set(OKX_MARKT)
        self.addCleanup(self.setzen_auf_alt)

    def setzen_auf_alt(self):
        self.m._MAERKTE[0] = self.alt

    def test_kurzzeichen_ergibt_das_paar(self):
        self.assertEqual(self.m.boersenpaar("ADA"), "ADA-USDC")

    def test_vollstaendiges_paar_bleibt_es(self):
        """Das ist der behobene Fehler: ADA-USDC darf nicht zu ADA-USDC-USDC."""
        self.assertEqual(self.m.boersenpaar("ADA-USDC"), "ADA-USDC")

    def test_beide_formen_fuehren_zum_selben_paar(self):
        kurz = self.m.boersenpaar("ADA")
        paar = self.m.boersenpaar("ADA")
        self.assertEqual(kurz, paar)
        # und beide Wege, die der Executor nimmt
        import spur_buch
        import json
        w = json.loads((HANDEL / "moondev_signalwelle" / "wachen.json")
                       .read_text(encoding="utf-8"))
        for inst in ("ADA", "NIGHT", "AR"):
            vi = spur_buch.venue_inst(inst, w)
            self.assertEqual(self.m.boersenpaar(vi),
                             self.m.boersenpaar(inst),
                             "%s: der Executor-Weg weicht ab" % inst)

    def test_ein_wirklich_fehlendes_paar_bleibt_none(self):
        # GENIUS, BTW und QNT fuehrt die OKX nicht - da ist None RICHTIG.
        for inst in ("GENIUS", "BTW", "QNT"):
            self.assertIsNone(self.m.boersenpaar(inst), inst)

    def test_quote_bleibt_vor_eur(self):
        m2 = self.m
        ma = {"BTC-USDT", "BTC-EUR"}
        m2._MAERKTE[0] = ma
        self.assertEqual(m2.boersenpaar("BTC"), "BTC-USDT")

    def test_leere_marktliste_ist_ein_ausfall_nicht_kein_markt(self):
        """Der Ausfall darf nicht wie eine Messung aussehen."""
        self.m._MAERKTE[0] = set()
        with self.assertRaises(Exception) as ctx:
            self.m.boersenpaar("ADA")
        self.assertIn("nicht lesbar", str(ctx.exception).lower()
                      if "nicht lesbar" in str(ctx.exception).lower()
                      else str(ctx.exception))
        self.assertNotIn("keinen Spotmarkt", str(ctx.exception))


class Meldend(PaarOhneDoppelte):
    """Die Meldung, die 36 Stunden falsch in der Merkdatei stand.

    Erbt setUp() von der Klasse darueber: gleiche Attrappe, gleiches
    Zuruecksetzen. Eine eigene Kopie von setUp waere eine zweite Wahrheit -
    und genau die hat hier schon einmal gestimmt und nicht gepasst.
    """

    def test_ada_wird_nicht_mit_kein_markt_abgelehnt(self):
        """ADA hat einen Markt - der Weg darf nicht mit Meldend enden.

        `markt_kauf` wird hier ABGEFANGEN: ohne das wuerde der Test eine echte
        Order an die OKX schicken (gemessen am 05.10.2026 - der erste
        Entwurf tat genau das und bekam "OKX 1: All operations failed").
        """
        aufrufe = []
        self.m.okx.markt_kauf = lambda paar, menge: aufrufe.append((paar, menge)) or "ORDER"
        try:
            erg = self.m.markt_kauf("ADA", 3.0)
        except self.m.Meldend as e:
            self.fail("ADA hat einen Markt, wurde aber abgelehnt: %s" % e)
        self.assertEqual(erg, "ORDER")
        self.assertEqual(aufrufe, [("ADA-USDC", 3.0)],
                         "die Order ging an das falsche Paar")

    def test_ein_wirklich_fehlendes_paar_wird_abgelehnt_ohne_order(self):
        """GENIUS hat keinen Markt: Meldend, und KEIN Aufruf an die Boerse."""
        aufrufe = []
        self.m.okx.markt_kauf = lambda paar, menge: aufrufe.append(paar)
        with self.assertRaises(self.m.Meldend) as ctx:
            self.m.markt_kauf("GENIUS", 1.0)
        self.assertIn("keinen Spotmarkt", str(ctx.exception))
        self.assertEqual(aufrufe, [], "es ging trotzdem eine Order raus")


if __name__ == "__main__":
    unittest.main()