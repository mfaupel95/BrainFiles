"""Der Boersen-Stop im Live-Pfad: gesetzt, gemerkt, abgeraeumt, nachgesehen.

Drei Loecher, die dieser Test festhaelt (Befund 14.09.2026):

1. Der Notausstieg wurde beim Einstieg gesetzt, aber seine algoId weggeworfen
   (`okx.stop_setzen(...)` ohne Zuweisung). Damit konnte ihn niemand mehr
   abbestellen - er blieb beim Handelsplatz im Buch und haette eine spaetere
   Position desselben Instruments zum alten Stoppreis verkaufen koennen.
2. Kein Ausstieg stornierte den Stop vor dem Verkauf, auch der Notausstieg
   (kill_switch, Herzschlag) nicht.
3. Loeste der Stop zwischen zwei Zyklen aus, scheiterte der eigene Verkauf -
   die Position blieb als Karteileiche im Buch stehen, obwohl sie am Markt
   laengst verkauft war.

Kein Netz: handeln.okx wird durch eine Attrappe ersetzt, JOURNAL zeigt in eine
Temp-Datei. Direkt ausfuehrbar:  python tests/test_handeln_boersenstop.py
"""

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))          # scanner/ - handeln, okx

import handeln as h                                            # noqa: E402

# Nur die Form: welche Felder liest der Lauf.
W = {"max_offene_positionen": 4, "max_gesamt_usd": 200, "abklingzeit_tage": 3}

V = {"inst": "LINK-USDC", "einstieg": 11.8, "stop": 11.0, "ziel": 13.3,
     "stop_pct": 6.4, "usd": 50.0, "score": 70.0}

P = {"inst": "LINK-USDC", "einstieg": 11.8, "usd": 50.0, "stop": 11.0,
     "ziel": 13.3, "eroeffnet": "2026-09-14", "kauf_ord_id": "kauf-1",
     "stop_ord_id": "algo-1", "boersen_stop_fehlt": False}


class AttrappeOKX:
    """Das okx-Modul ohne Netz. Jeder Aufruf wird mitgeschrieben."""

    def __init__(self, kurs=11.9, fuellung=4.2, stop_fehler=False,
                 verkauf_fehler=False, storno_fehler=False,
                 stop_gefuellt=False, storno_erledigt=False):
        self.kurs = kurs
        self.fuellung = fuellung
        self.stop_fehler = stop_fehler
        self.verkauf_fehler = verkauf_fehler
        self.storno_fehler = storno_fehler
        self.stop_gefuellt = stop_gefuellt
        self.storno_erledigt = storno_erledigt
        self.rufe = []

    def letzter_kurs(self, inst):
        self.rufe.append(("kurs", inst))
        return self.kurs

    def markt_kauf(self, inst, usd):
        self.rufe.append(("kauf", inst, usd))
        return "kauf-1"

    def order_details(self, inst, ord_id):
        self.rufe.append(("details", inst, ord_id))
        return {"accFillSz": "%.8f" % self.fuellung}

    def markt_verkauf(self, inst, menge):
        self.rufe.append(("verkauf", inst, menge))
        if self.verkauf_fehler:
            raise RuntimeError("OKX 51008: zu wenig Guthaben")
        return "verkauf-1"

    def stop_setzen(self, inst, menge, preis):
        self.rufe.append(("stop", inst, menge, preis))
        if self.stop_fehler:
            raise RuntimeError("OKX 51000: Parameter falsch")
        return "algo-1"

    def stop_stornieren(self, algo_id, inst=None):
        self.rufe.append(("storno", algo_id, inst))
        if self.storno_erledigt:
            return None                 # wie okx.py bei OKX 51400: nichts mehr da
        if self.storno_fehler:
            # Nicht 51400 - "erledigt" wird von okx.stop_stornieren geschluckt.
            # Hier muss ein echter Fehler stehen, sonst prueft der Test nichts.
            raise RuntimeError("OKX 50014: Parameter instId can not be empty")
        return algo_id

    def stop_details(self, algo_id):
        self.rufe.append(("stopdetails", algo_id))
        return {"state": "filled" if self.stop_gefuellt else "live",
                "instId": "LINK-USDC",
                "accFillSz": "%.8f" % (self.fuellung if self.stop_gefuellt
                                       else 0)}

    def stop_inst(self, algo_id):
        self.rufe.append(("stopinst", algo_id))
        return "LINK-USDC"

    def quote(self, inst):
        self.rufe.append(("quote", inst))
        if not inst or "-" not in inst:
            return ""
        return inst.split("-")[-1]

    def namen(self):
        return [r[0] for r in self.rufe]


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.alt = h.JOURNAL
        h.JOURNAL = Path(self.tmp.name) / "handelsjournal.csv"
        # dito: pruefe_einstiege protokolliert Ablehnungen daneben
        self.alt_abl = h.ABLEHNUNGEN
        h.ABLEHNUNGEN = Path(self.tmp.name) / "ablehnungen.csv"
        self.addCleanup(lambda: setattr(h, "ABLEHNUNGEN", self.alt_abl))
        self.addCleanup(setattr, h, "JOURNAL", self.alt)

    def _lauf(self, fake, fn):
        """fn() mit Attrappe statt okx und abgefangener Ausgabe."""
        puffer = io.StringIO()
        with patch.object(h, "okx", fake):
            with patch("sys.stdout", puffer), patch("sys.stderr", puffer):
                fn()
        return puffer.getvalue()


class EinstiegLive(Basis):
    def _einstieg(self, fake):
        z = {"positionen": [], "letzte_stops": {}}
        text = self._lauf(fake, lambda: h.pruefe_einstiege(z, [dict(V)], W, True))
        return text, z

    def test_stop_wird_gesetzt_und_die_nummer_gemerkt(self):
        fake = AttrappeOKX()
        _, z = self._einstieg(fake)
        self.assertIn(("stop", "LINK-USDC", 4.2, 11.0), fake.rufe)
        self.assertEqual(z["positionen"][0]["stop_ord_id"], "algo-1")
        self.assertFalse(z["positionen"][0]["boersen_stop_fehlt"])

    def test_stop_nicht_setzbar_wird_zurueckverkauft(self):
        fake = AttrappeOKX(stop_fehler=True)
        text, z = self._einstieg(fake)
        self.assertEqual(z["positionen"], [], "ohne Stop nicht halten")
        self.assertIn(("verkauf", "LINK-USDC", 4.2), fake.rufe)
        self.assertIn("zurueckverkauft", text)

    def test_rueckverkauf_fehlt_position_wird_markiert(self):
        fake = AttrappeOKX(stop_fehler=True, verkauf_fehler=True)
        _, z = self._einstieg(fake)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertTrue(z["positionen"][0]["boersen_stop_fehlt"])
        self.assertIsNone(z["positionen"][0]["stop_ord_id"])

    def test_kauf_ohne_fuellung_wird_nicht_gebucht(self):
        fake = AttrappeOKX(fuellung=0)
        text, z = self._einstieg(fake)
        self.assertEqual(z["positionen"], [])
        self.assertIn("ohne Fuellung", text)


class AusstiegLive(Basis):
    def _ausstieg(self, fake, pos=None, offene_stops=None):
        z = {"positionen": [dict(P if pos is None else pos)],
             "letzte_stops": {}}
        if offene_stops is not None:
            z["offene_stops"] = offene_stops
        text = self._lauf(fake, lambda: h.pruefe_ausstiege(z, True))
        return text, z

    def test_ausstieg_storniert_den_stop_vor_dem_verkauf(self):
        fake = AttrappeOKX(kurs=P["ziel"] + 1)
        _, z = self._ausstieg(fake)
        self.assertIn("storno", fake.namen())
        self.assertLess(fake.namen().index("storno"),
                        fake.namen().index("verkauf"),
                        "erst den Stop abbestellen, dann verkaufen")
        self.assertEqual(z["positionen"], [])

    def test_nicht_stornierbarer_stop_haelt_den_verkauf_nicht_auf(self):
        fake = AttrappeOKX(kurs=P["ziel"] + 1, storno_fehler=True)
        _, z = self._ausstieg(fake)
        self.assertIn("verkauf", fake.namen())
        self.assertEqual(z["positionen"], [])
        self.assertEqual(len(z["offene_stops"]), 1,
                         "der offene Stop wird gemerkt")
        self.assertEqual(z["offene_stops"][0]["stop_ord_id"], "algo-1")

    def test_ausgeloester_boersenstop_raeumt_die_position_weg(self):
        fake = AttrappeOKX(kurs=P["ziel"] + 1, storno_fehler=True,
                           stop_gefuellt=True)
        text, z = self._ausstieg(fake)
        self.assertNotIn("verkauf", fake.namen(),
                         "der Stop hat schon verkauft - kein zweiter Verkauf")
        self.assertEqual(z["positionen"], [], "keine Karteileiche im Buch")
        self.assertIn("stop (boerse)", text)
        self.assertEqual(z["letzte_stops"][P["inst"]], h._heute())

    def test_verkauf_fehlt_ohne_boersenstop_position_bleibt(self):
        fake = AttrappeOKX(kurs=P["ziel"] + 1, verkauf_fehler=True)
        _, z = self._ausstieg(fake)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertIsNone(z.get("offene_stops"))

    def test_ohne_okx_order_wird_nicht_verkauft(self):
        # Papier-Altlast im Live-Buch (21.09.2026): kein kauf_ord_id, also gibt
        # es am Handelsplatz nichts zu verkaufen. Ein Market-Verkauf wuerde den
        # GESAMTEN Bestand des Werts auf dem Konto treffen - auch Coins, die
        # diese Spur nie gekauft hat. Vorher lief das in OKX 51000
        # ("Parameter ordId error"), weil mit ordId=None abgefragt wurde.
        fake = AttrappeOKX(kurs=P["ziel"] + 1)
        pos = dict(P, kauf_ord_id=None)
        text, z = self._ausstieg(fake, pos=pos)
        self.assertNotIn("verkauf", fake.namen(), "keine Order an die Boerse")
        self.assertNotIn("details", fake.namen(), "gar nicht erst abfragen")
        self.assertEqual(len(z["positionen"]), 1, "Position bleibt bis zur Bereinigung")
        self.assertIn("ohne OKX-Order", text)

    def test_notausstieg_storniert_den_stop(self):
        fake = AttrappeOKX()
        z = {"positionen": [dict(P)], "letzte_stops": {}}
        self._lauf(fake, lambda: h.flach_stellen(z, True, "herzschlag_alt"))
        self.assertEqual(z["positionen"], [])
        self.assertIn("storno", fake.namen())

    def test_offene_stops_werden_beim_naechsten_lauf_storniert(self):
        fake = AttrappeOKX()
        z = {"positionen": [], "letzte_stops": {},
             "offene_stops": [{"inst": "LINK-USDC", "stop_ord_id": "algo-9",
                               "seit": "2026-09-14"}]}
        text = self._lauf(fake, lambda: h.pruefe_ausstiege(z, True))
        self.assertIn(("storno", "algo-9", "LINK-USDC"), fake.rufe)
        self.assertEqual(z["offene_stops"], [])
        self.assertIn("storniert", text)

    def test_offener_stop_bleibt_wenn_er_nicht_weggeht(self):
        fake = AttrappeOKX(storno_fehler=True)
        z = {"positionen": [], "letzte_stops": {},
             "offene_stops": [{"inst": "LINK-USDC", "stop_ord_id": "algo-9",
                               "seit": "2026-09-14"}]}
        self._lauf(fake, lambda: h.pruefe_ausstiege(z, True))
        self.assertEqual(len(z["offene_stops"]), 1,
                         "was nicht weggeht, bleibt gemerkt")

    def test_fehlendes_inst_wird_lesend_nachgeholt(self):
        # Alteintrag ohne inst: ohne instId antwortet OKX mit 50014 und der
        # Stop liesse sich nie stornieren (Befund 23.09.2026).
        fake = AttrappeOKX()
        z = {"positionen": [], "letzte_stops": {},
             "offene_stops": [{"stop_ord_id": "algo-9", "seit": "2026-09-14"}]}
        self._lauf(fake, lambda: h.pruefe_ausstiege(z, True))
        self.assertIn(("storno", "algo-9", "LINK-USDC"), fake.rufe)
        self.assertEqual(z["offene_stops"], [])

    def test_doppelte_offene_stops_werden_zusammengefasst(self):
        # Genau der Befund: 23 Kopien desselben Stops in zustand.json.
        fake = AttrappeOKX()
        z = {"positionen": [], "letzte_stops": {},
             "offene_stops": [{"inst": "LINK-USDC", "stop_ord_id": "algo-9",
                               "seit": "2026-09-14"}] * 23}
        self._lauf(fake, lambda: h.pruefe_ausstiege(z, True))
        self.assertEqual([r for r in fake.rufe if r[0] == "storno"],
                         [("storno", "algo-9", "LINK-USDC")],
                         "derselbe Stop wird EINMAL storniert")
        self.assertEqual(z["offene_stops"], [])

    def test_an_der_boerse_erledigter_stop_faellt_aus_der_liste(self):
        # OKX 51400 (gefuellt/storniert/nicht existent) heisst: erledigt. Sonst
        # meldet der Live-Lauf jede Runde "bleibt liegen" (der eigentliche
        # Befund vom 23.09.2026).
        fake = AttrappeOKX(storno_erledigt=True)
        z = {"positionen": [], "letzte_stops": {},
             "offene_stops": [{"inst": "LINK-USDC", "stop_ord_id": "algo-9",
                               "seit": "2026-09-14"}]}
        text = self._lauf(fake, lambda: h.pruefe_ausstiege(z, True))
        self.assertEqual(z["offene_stops"], [], "erledigt ist kein Fehler")
        self.assertIn("war schon weg", text)

    def test_derselbe_stop_wird_nicht_zweimal_gemerkt(self):
        fake = AttrappeOKX(storno_fehler=True, kurs=11.9)
        z = {"positionen": [], "letzte_stops": {}, "offene_stops": []}
        self._lauf(fake, lambda: h.pruefe_einstiege(z, [dict(V)], W, True))
        fake.rufe.clear()
        for _ in range(2):
            self._lauf(fake, lambda: h.pruefe_ausstiege(z, True))
        self.assertLessEqual(len(z.get("offene_stops") or []), 1,
                             "kein Wachstum bei wiederholten Versuchen")


if __name__ == "__main__":
    unittest.main()
