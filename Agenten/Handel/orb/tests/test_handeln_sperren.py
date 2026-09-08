"""Task 11: die neun Sperren vor der ersten echten Order (live_sperren),
das Freigabefenster vor dem Einstieg (hole_freigabe) und die Slippage-
Korrektur beim Live-Ausstieg (_schliesse nutzt den echten Fill-Preis,
SPEC.md Zeile 164).

Kein Netz. handeln.oanda.* und handeln.sitzung_da werden je Test per Lambda
gesetzt und in addCleanup zurueckgestellt - keine Umgebungsvariablen.
"""

import json
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import handeln

HIER = Path(__file__).resolve().parent


def _s(**over):
    base = {"freigabe_voll": True, "herzschlag_frisch": True, "ev_negativ": False,
            "rollierender_ev": 1.0, "ruecklauf_eur": 0.0}
    base.update(over)
    return base


class TestLiveSperren(unittest.TestCase):
    def setUp(self):
        self.w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
        self.w["handel_erlaubt"] = True
        self.w["journal_zweitziel"] = "X:/orb-kopie"
        self.w["mindest_marge_frei_eur"] = 200
        self.w["instrument_aktiv"] = "US30_USD"
        # gemeinsam genutzter Modulzustand - ohne Restore leckt das in andere Tests
        for attr in ("zugang_vorhanden", "konto_marge_frei"):
            self.addCleanup(setattr, handeln.oanda, attr,
                            getattr(handeln.oanda, attr))
        self.addCleanup(setattr, handeln, "sitzung_da", handeln.sitzung_da)
        handeln.oanda.zugang_vorhanden = lambda: True
        handeln.oanda.konto_marge_frei = lambda live=False: 5000.0
        handeln.sitzung_da = lambda: True          # Standard: Sitzung am Bildschirm

    def test_alle_offen_gibt_leere_liste(self):
        self.assertEqual(handeln.live_sperren(self.w, _s()), [])

    def test_handel_erlaubt_false_blockt(self):
        self.w["handel_erlaubt"] = False
        self.assertTrue(any("handel_erlaubt" in g
                            for g in handeln.live_sperren(self.w, _s())))

    def test_freigabe_nicht_voll_blockt(self):
        self.assertTrue(any("Freigabe" in g or "freigabe" in g
                            for g in handeln.live_sperren(self.w, _s(freigabe_voll=False))))

    def test_zu_wenig_marge_blockt(self):
        handeln.oanda.konto_marge_frei = lambda live=False: 100.0
        self.assertTrue(any("Marge" in g or "marge" in g
                            for g in handeln.live_sperren(self.w, _s())))

    def test_keine_sitzung_blockt(self):
        handeln.sitzung_da = lambda: False
        self.assertTrue(any("Sitzung" in g for g in handeln.live_sperren(self.w, _s())))

    # --- die restlichen Sperren, je einzeln ---------------------------------
    def test_kein_oanda_zugang_blockt(self):
        handeln.oanda.zugang_vorhanden = lambda: False
        g = handeln.live_sperren(self.w, _s())
        self.assertTrue(any("OANDA_TOKEN" in x for x in g))
        # Sperre 8 darf ohne Zugang nicht ins Netz greifen
        self.assertFalse(any("Marge" in x for x in g))

    def test_herzschlag_alt_blockt(self):
        self.assertTrue(any("Herzschlag" in g
                            for g in handeln.live_sperren(self.w, _s(herzschlag_frisch=False))))

    def test_ev_negativ_blockt(self):
        self.assertTrue(any("EV" in g for g in handeln.live_sperren(
            self.w, _s(ev_negativ=True, rollierender_ev=-0.5))))

    def test_kein_journal_zweitziel_blockt(self):
        self.w["journal_zweitziel"] = None
        self.assertTrue(any("journal_zweitziel" in g
                            for g in handeln.live_sperren(self.w, _s())))

    def test_jede_sperre_traegt_eine_nummer(self):
        self.w["handel_erlaubt"] = False
        handeln.oanda.zugang_vorhanden = lambda: True
        for g in handeln.live_sperren(self.w, _s(freigabe_voll=False,
                                                 herzschlag_frisch=False,
                                                 ev_negativ=True)):
            self.assertIn("Sperre", g)


class TestHoleFreigabe(unittest.TestCase):
    """freigabe.py hat die Spur 'orb' erst ab Task 12. Bis dahin - und bei
    jedem Fehler im Fenster - liefert hole_freigabe False: kein Einstieg."""

    def _z(self):
        return {"positionen": [{"risiko_eur": 20.0}], "letzte_stops": {}}

    def test_ohne_orb_spur_kein_einstieg(self):
        # freigabe.bestaetige(..., "orb", ...) wirft ValueError (unbekannte Spur)
        self.assertFalse(handeln.hole_freigabe({"inst": "US30_USD"}, self._z(),
                                               _s()))

    def test_importfehler_kein_einstieg(self):
        import sys
        echt = sys.modules.pop("freigabe", None)
        sys.modules["freigabe"] = None          # import freigabe -> ImportError
        try:
            self.assertFalse(handeln.hole_freigabe({"inst": "US30_USD"},
                                                   self._z(), _s()))
        finally:
            if echt is not None:
                sys.modules["freigabe"] = echt
            else:
                sys.modules.pop("freigabe", None)


class TestSchliesseFuellpreis(unittest.TestCase):
    """SPEC.md Zeile 164: im Live-Ausstieg zaehlt der echte
    orderFillTransaction.price, nicht der gerechnete Mid. Papier bleibt Mid."""

    def setUp(self):
        self.addCleanup(setattr, handeln.oanda, "markt_order",
                        handeln.oanda.markt_order)
        self.addCleanup(setattr, handeln, "journal", handeln.journal)
        self.w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
        self.w["instrument_aktiv"] = "US30_USD"
        self.w["instrumente"]["US30_USD"] = {
            "oanda": "US30_USD", "eroeffnung": "15:30", "zone": "Europe/Berlin",
            "cash_close": "22:00", "spread_punkte": 2.0, "punkt_wert_eur": 1.0}
        self.rows = []
        handeln.journal = lambda *f: self.rows.append(f)

    def _pos(self):
        return {"inst": "US30_USD", "richtung": "long", "einstieg": 40000.0,
                "stop": 39900.0, "ziel": 40200.0, "units": 2.0, "risiko_eur": 20.0,
                "eroeffnet": date.today().isoformat(), "order_id": None}

    def test_live_nimmt_echten_fuellpreis(self):
        handeln.oanda.markt_order = lambda *a, **k: ("tx1", 40080.0)
        z = {"positionen": [], "letzte_stops": {}}
        handeln._schliesse(self._pos(), 40100.0, self.w, True, "ziel", z)
        row = next(r for r in self.rows if r[2] == "ausstieg")
        self.assertAlmostEqual(float(row[5]), 40080.0, places=3)      # Preis-Spalte
        # G/V zum Fill: (40080-40000)*1*2 - halber Spread (0.5*2*1*2=2) = 158
        self.assertAlmostEqual(float(row[6]), 20.0 + 158.0, places=3)

    def test_live_ohne_fuellpreis_faellt_auf_mid_zurueck(self):
        handeln.oanda.markt_order = lambda *a, **k: ("tx1", None)
        z = {"positionen": [], "letzte_stops": {}}
        handeln._schliesse(self._pos(), 40100.0, self.w, True, "ziel", z)
        row = next(r for r in self.rows if r[2] == "ausstieg")
        self.assertAlmostEqual(float(row[5]), 40100.0, places=3)
        self.assertAlmostEqual(float(row[6]), 20.0 + 198.0, places=3)

    def test_papier_bleibt_mid(self):
        handeln.oanda.markt_order = lambda *a, **k: ("tx1", 40080.0)  # darf nie gerufen werden
        z = {"positionen": [], "letzte_stops": {}}
        handeln._schliesse(self._pos(), 40100.0, self.w, False, "ziel", z)
        row = next(r for r in self.rows if r[2] == "ausstieg")
        self.assertAlmostEqual(float(row[5]), 40100.0, places=3)
        self.assertAlmostEqual(float(row[6]), 20.0 + 198.0, places=3)


if __name__ == "__main__":
    unittest.main()
