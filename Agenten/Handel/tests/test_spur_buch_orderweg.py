"""Der gemeinsame Live-Orderweg in spur_buch - ohne eine einzige echte Order.

Geprueft wird die Kette, die am 21.09.2026 gebaut wurde: eine Buch-Spur
(moondev_*, iv_*) handelt live ueber `orderweg(w)` (Boerse aus der wachen) und
`sperren_live(w, s, spur)`. Der Test setzt einen Attrappen-Orderweg ein und
haelt fest:

  * Einstieg live: erst die Order, dann das Buch - mit Order-Kennung und Modus,
  * kein Stop an der Boerse -> Rueckverkauf, KEINE Position im Buch,
  * keine Order-Kennung -> keine Position,
  * Ausstieg live: Stop stornieren, dann verkaufen;
  * Verkauf scheitert -> Position bleibt im Buch,
  * Papier-Position wird im Live-Lauf NICHT angefasst,
  * die Sperrenkette nennt die Gruende (Schalter, Freigabe, Fenster).

Kein Netz, keine Boerse: der Orderweg ist eine Attrappe.
"""

import json
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
sys.path.insert(0, str(HANDEL))

import spur_buch as buch                                          # noqa: E402


class Attrappe:
    """Orderweg-Attrappe: merkt jeden Aufruf, kann Fehler erzwingen."""

    def __init__(self, kauf_ok=True, stop_ok=True, verkauf_ok=True, fehler_menge=None):
        self.aufrufe = []
        self.kauf_ok = kauf_ok
        self.stop_ok = stop_ok
        self.verkauf_ok = verkauf_ok
        self.fehler_menge = fehler_menge

    def schluessel_vorhanden(self):
        return True

    def demo_modus(self):
        return False

    def guthaben_waehrung(self, ccy="USDC"):
        return 500.0

    def letzter_kurs(self, inst):
        return 100.0

    def menge_fuer(self, inst, betrag, kurs):
        if self.fehler_menge:
            return 0.0, self.fehler_menge
        return round(betrag / kurs, 6), None

    def markt_kauf(self, inst, menge):
        self.aufrufe.append(("kauf", inst, menge))
        return "ORD-1" if self.kauf_ok else None

    def markt_verkauf(self, inst, menge):
        self.aufrufe.append(("verkauf", inst, menge))
        if not self.verkauf_ok:
            raise RuntimeError("Boerse nimmt den Verkauf nicht an")
        return "ORD-2"

    def algo_stop_setzen(self, inst, menge, seite, trigger):
        self.aufrufe.append(("stop", inst, round(trigger, 4)))
        if not self.stop_ok:
            raise RuntimeError("Stop abgelehnt")
        return "STOP-1"

    def algo_stornieren(self, inst, stop_id):
        self.aufrufe.append(("stop-storno", inst, stop_id))
        return True


W = {"risiko_je_position_usd": 5.0, "max_pro_trade_usd": 100.0,
     "live_max_pro_trade_usd": 20.0, "stop_prozent": 7.0,
     "pflicht_stop_prozent_min": 5.0, "pflicht_stop_prozent_max": 12.0,
     "ziel_r_vielfaches": 2.0, "max_offene_positionen": 3}


class EinstiegLiveTest(unittest.TestCase):

    def test_order_dann_buch(self):
        weg = Attrappe()
        z = {"positionen": []}
        p = buch.einstieg(z, "ABC-USDC", "long", 100.0, W, 1.0, "test",
                          live=True, weg=weg)
        self.assertIsNotNone(p)
        self.assertEqual(p["ord_id"], "ORD-1")
        self.assertEqual(p["modus"], "live")
        self.assertAlmostEqual(p["menge"], 0.2)       # 20 USD (live-Grenze) / 100
        self.assertEqual([a[0] for a in weg.aufrufe], ["kauf", "stop"])
        self.assertEqual(len(z["positionen"]), 1)

    def test_ohne_stop_wird_zurueckverkauft(self):
        weg = Attrappe(stop_ok=False)
        z = {"positionen": []}
        p = buch.einstieg(z, "ABC-USDC", "long", 100.0, W, 1.0, "test",
                          live=True, weg=weg)
        self.assertIsNone(p)
        self.assertEqual(z["positionen"], [], "keine Position ohne Boersen-Stop")
        self.assertEqual([a[0] for a in weg.aufrufe], ["kauf", "stop", "verkauf"])

    def test_ohne_ord_kennung_keine_position(self):
        weg = Attrappe(kauf_ok=False)
        z = {"positionen": []}
        self.assertIsNone(buch.einstieg(z, "ABC-USDC", "long", 100.0, W, 1.0, "t",
                                        live=True, weg=weg))
        self.assertEqual(z["positionen"], [])

    def test_menge_zu_klein_wird_gemeldet(self):
        weg = Attrappe(fehler_menge="unter der Mindestmenge")
        z = {"positionen": []}
        self.assertIsNone(buch.einstieg(z, "ABC-USDC", "long", 100.0, W, 1.0, "t",
                                        live=True, weg=weg))
        self.assertEqual(weg.aufrufe, [], "gar nicht erst ordern")

    def test_papier_einstieg_stellt_keine_order(self):
        weg = Attrappe()
        z = {"positionen": []}
        p = buch.einstieg(z, "ABC-USDC", "long", 100.0, W, 1.0, "test", weg=weg)
        self.assertEqual(p["modus"], "papier")
        self.assertEqual(weg.aufrufe, [])


class AusstiegLiveTest(unittest.TestCase):

    def setUp(self):
        self.tmp = HIER / "tmp_journal_orderweg.csv"
        self.zustand_tmp = HIER / "tmp_zustand_orderweg.json"
        self.weg = Attrappe()
        self.live = {"inst": "ABC-USDC", "seite": "long", "einstieg": 100.0,
                     "stop": 93.0, "ziel": 114.0, "stop_pct": 7.0, "nominal": 20.0,
                     "modus": "live", "menge": 0.2, "ord_id": "ORD-1",
                     "stop_id": "STOP-1"}
        self.papier = dict(self.live, modus="papier")

    def tearDown(self):
        for p in (self.tmp, self.zustand_tmp,
                  Path(str(self.zustand_tmp) + ".bak")):
            if p.exists():
                p.unlink()

    def _zustand_offen(self):
        """Insts, die der geschriebene Zustand noch als offen fuehrt."""
        with open(self.zustand_tmp, encoding="utf-8") as f:
            return [p["inst"] for p in json.load(f)["positionen"]]

    def test_live_ausstieg_storniert_erst_den_stop(self):
        z = {"positionen": [dict(self.live)]}
        buch.pruefe_ausstiege(z, {"ABC-USDC": 92.0}, W, self.tmp,
                              live=True, weg=self.weg,
                              zustand_pfad=self.zustand_tmp)
        self.assertEqual([a[0] for a in self.weg.aufrufe], ["stop-storno", "verkauf"])
        self.assertEqual(z["positionen"], [])
        # T-356: die Buchung ist EINE - Journal UND Zustand zusammen.
        self.assertEqual(self._zustand_offen(), [],
                         "der Zustand fuehrt die verkaufte Position nicht mehr")

    def test_papier_position_geht_nie_an_die_boerse(self):
        """Eine Papier-Position darf im Live-Lauf geschlossen werden - aber NUR
        im Buch: kein Storno, kein Verkauf, keine Order."""
        z = {"positionen": [dict(self.papier)]}
        buch.pruefe_ausstiege(z, {"ABC-USDC": 92.0}, W, self.tmp,
                              live=True, weg=self.weg,
                              zustand_pfad=self.zustand_tmp)
        self.assertEqual(self.weg.aufrufe, [], "Papier wird nie an die Boerse geschickt")
        self.assertEqual(z["positionen"], [], "im Buch wird sie sauber geschlossen")
        zeile = self.tmp.read_text(encoding="utf-8").strip().splitlines()[1]
        self.assertIn("papier", zeile, "und die Journalzeile nennt Papier")
        self.assertEqual(self._zustand_offen(), [],
                         "der Zustand fuehrt die Position nicht mehr offen")

    def test_verkauf_scheitert_position_bleibt(self):
        self.weg.verkauf_ok = False
        z = {"positionen": [dict(self.live)]}
        buch.pruefe_ausstiege(z, {"ABC-USDC": 92.0}, W, self.tmp,
                              live=True, weg=self.weg,
                              zustand_pfad=self.zustand_tmp)
        self.assertEqual(len(z["positionen"]), 1,
                         "was nicht verkauft ist, bleibt im Buch")
        self.assertFalse(self.zustand_tmp.exists(),
                         "keine Buchung ohne Verkauf - kein Zustands-Schreiben")


class SperrenTest(unittest.TestCase):

    def test_kette_nennt_die_gruende(self):
        w = {"handel_erlaubt": False, "boerse": "okx", "journal_zweitziel": "Q:/x"}
        gruende = buch.sperren_live(w, {"freigabe_erfuellt": False,
                                        "herzschlag_frisch": True}, "moondev_test")
        text = " | ".join(gruende)
        self.assertIn("handel_erlaubt=false", text)
        self.assertIn("freigabe.erfuellt=false", text)
        self.assertIn("Freigabefenster", text)

    def test_orderweg_waehlt_die_boerse(self):
        self.assertEqual(buch.orderweg({"boerse": "kraken"}).__name__,
                         "mosaic/kraken_spot")
        self.assertEqual(buch.orderweg({}).__name__, "mosaic/okx_spot")
        self.assertIsNone(buch.orderweg({"boerse": "gibtsnicht"}))

    def test_live_grenze_hat_vorrang(self):
        self.assertEqual(buch.live_grenze({"max_pro_trade_usd": 100,
                                           "live_max_pro_trade_usd": 20},
                                          "max_pro_trade_usd", 5), 20.0)
        self.assertEqual(buch.live_grenze({"max_pro_trade_usd": 100},
                                          "max_pro_trade_usd", 5), 100.0)


if __name__ == "__main__":
    unittest.main()

class SchreibweiseTest(unittest.TestCase):
    """Kurzzeichen der Spur -> Paar der Boerse."""

    def test_kurzzeichen_wird_zum_paar(self):
        self.assertEqual(buch.venue_inst("XMR", {"boerse": "okx"}), "XMR-USDC")
        self.assertEqual(buch.venue_inst("ZRO", {}), "ZRO-USDC")
        self.assertEqual(buch.venue_inst("BTC", {"boerse": "kraken"}), "BTC-EUR")
        self.assertEqual(buch.venue_inst("BTC-USDC", {"boerse": "okx"}), "BTC-USDC")

    def test_live_einstieg_schickt_das_paar_an_die_boerse(self):
        weg = Attrappe()
        z = {"positionen": []}
        p = buch.einstieg(z, "XMR", "long", 100.0, W, 1.0, "test", live=True, weg=weg)
        self.assertEqual(p["venue_inst"], "XMR-USDC")
        self.assertEqual(weg.aufrufe[0], ("kauf", "XMR-USDC", 0.2))
        self.assertEqual(p["inst"], "XMR", "das Buch behaelt das Kurzzeichen")

    def test_boersen_kurs_ersetzt_quelle_kurs_im_live_lauf(self):
        """Im Live-Lauf holt spur_buch den Kurs von der Boerse, nicht aus quelle().

        Beleg 22.09.2026: CoinGecko liefert USD (z. B. 170 fuer XMR),
        Kraken erwartet EUR (z. B. 497). Ein Stop bei 158 USD wuerde an Kraken
        als 158 EUR gesetzt - viel zu tief und sofort gerissen.
        Die Attrappe gibt 200.0 zurueck (Boersen-EUR-Kurs), spur_buch muss
        diesen Kurs fuer Stop, Ziel und Menge verwenden, nicht den uebergebenen 100.
        """
        class BoesenKursAttrappe(Attrappe):
            def letzter_kurs(self, inst):
                return 200.0   # "EUR"-Kurs, deutlich anders als 100 USD

        weg = BoesenKursAttrappe()
        z = {"positionen": []}
        p = buch.einstieg(z, "XMR", "long", 100.0, W, 1.0, "test", live=True, weg=weg)
        self.assertIsNotNone(p)
        # Einstieg muss auf Boersen-Kurs liegen
        self.assertAlmostEqual(p["einstieg"], 200.0)
        # Stop und Ziel muessen auf Basis 200 gerechnet sein
        self.assertAlmostEqual(p["stop"], 200.0 * 0.93, places=2)
        self.assertAlmostEqual(p["ziel"], 200.0 * 1.14, places=2)

    def test_kein_boersen_kurs_ueberspring_den_einstieg(self):
        """Wenn der Boersen-Kurs nicht abrufbar ist, wird der Einstieg uebersprungen."""
        class KeinKursAttrappe(Attrappe):
            def letzter_kurs(self, inst):
                raise RuntimeError("Netz weg")

        z = {"positionen": []}
        p = buch.einstieg(z, "XMR", "long", 100.0, W, 1.0, "test",
                          live=True, weg=KeinKursAttrappe())
        self.assertIsNone(p)
        self.assertEqual(z["positionen"], [])

    def test_menge_fehler_reisst_den_zyklus_nicht(self):
        class Krach(Attrappe):
            def menge_fuer(self, inst, betrag, kurs):
                raise RuntimeError("OKX 51001 Instrument unbekannt")

        z = {"positionen": []}
        self.assertIsNone(buch.einstieg(z, "GIBTSNICHT", "long", 100.0, W, 1.0,
                                        "test", live=True, weg=Krach()))
        self.assertEqual(z["positionen"], [])
