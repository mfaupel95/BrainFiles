"""Stop-Deckung: die Regel, nicht der Tageswert.

ANLASS 02.10.2026: ZEC stand mit 145 Kontrakten an der Boerse, geschuetzt
waren 126 - und `_stop_vorhanden` sagte "ja". Diese Tests halten die Regel fest,
die dort gerissen ist:

  * GESCHUETZT ist, was die MENGE deckt, nicht was ein Auftrag behauptet.
  * GEGENLAEUFIG muss die Order sein, und reduceOnly gehoert dazu.
  * Ein Stop auf der falschen Seite des Kurses ist kein Schutz.
  * Ein Stop unterhalb der Liquidation ist tot und wird gemeldet, nicht
    still uebergangen.

Kein Test greift auf die Boerse zu: `okxf` wird im Testmodul ersetzt.
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(HIER), "scanner"))
sys.path.insert(0, os.path.dirname(HIER))
sys.path.insert(0, HIER)

import stopdeckung as sd                                       # noqa: E402


class Auftrag(dict):
    """Ein Auftrag DICT wie OKX ihn liefert - `schutz_auftraege` liest
    per `.get()`, ein Objekt mit Attributen wuerde jeden Test auf eine
    Kapazitaetsfrage der Attrappe schicken statt auf die Regel."""

    def __init__(self, sz, stop, seite="sell", reduce=True, tp=None,
                 ordType="oco", sl=True):
        super().__init__({"instId": "X", "ordType": ordType, "side": seite,
                          "sz": str(sz), "reduceOnly": "true" if reduce else "false",
                          "state": "live"})
        if sl:
            self["slTriggerPx"] = str(stop)
        if tp is not None:
            self["tpTriggerPx"] = str(tp)


def fake(stops=None, positionen=None, kurs=1000.0, gesetzt=None):
    """okxf-Attrappe. `gesetzt` sammelt die echten Aufrufe."""
    class F:
        pass
    f = F()
    f.stops = stops or []
    f.gesetzt = gesetzt if gesetzt is not None else []
    f.positionen = lambda: positionen or []
    f.letzter_kurs = lambda inst: kurs
    f.schutz_stops = lambda inst=None, **kw: list(f.stops)
    f.schutz_stop_setzen = lambda inst, seite, menge, stop, ziel=None, **kw: (
        f.gesetzt.append({"inst": inst, "seite": seite, "menge": menge,
                          "stop": stop}) or {"algoId": "A1"})
    return f


class SchuetztFilterTest(unittest.TestCase):
    """Was als Schutz zaehlt - und was nicht."""

    def setUp(self):
        self.alt = sd.okxf

    def tearDown(self):
        sd.okxf = self.alt

    def test_gegenlaeufige_reduce_only_order_zaehlt(self):
        sd.okxf = fake([Auftrag(30, 900), Auftrag(20, 880)])
        a = sd.schutz_auftraege("X", "long")
        self.assertEqual([x["menge"] for x in a], [30.0, 20.0])

    def test_order_in_richtiger_richtung_zaehlt_nicht(self):
        """Ein Kauf-Stop auf einer Long-Position waere eine zweite Wette."""
        sd.okxf = fake([Auftrag(30, 900, seite="buy")])
        self.assertEqual(sd.schutz_auftraege("X", "long"), [])

    def test_ohne_reduce_only_zaehlt_nicht(self):
        sd.okxf = fake([Auftrag(30, 900, reduce=False)])
        self.assertEqual(sd.schutz_auftraege("X", "long"), [])

    def test_ohne_ausloesung_zaehlt_nicht(self):
        """Ein nackter Trigger ist eine Einstiegsorder, kein Schutz."""
        sd.okxf = fake([Auftrag(30, None, sl=False)])
        self.assertEqual(sd.schutz_auftraege("X", "long"), [])

    def test_reiner_take_profit_zaehlt_nicht(self):
        """11.10.2026 (ETH): ein Auftrag NUR mit tpTriggerPx loest nur im
        Gewinn aus - er schuetzt nichts. Vorher zaehlte er als Deckung."""
        sd.okxf = fake([Auftrag(30, None, sl=False, tp=1500)])
        self.assertEqual(sd.schutz_auftraege("X", "long"), [])

    def test_trailing_stop_zaehlt_ueber_move_trigger(self):
        """Ein Trailing (move_order_stop) traegt moveTriggerPx statt
        slTriggerPx (okxf.ist_schutz_stop) - er zaehlt."""
        t = Auftrag(30, None, sl=False, ordType="move_order_stop")
        t["moveTriggerPx"] = "900"
        sd.okxf = fake([t])
        a = sd.schutz_auftraege("X", "long")
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["menge"], 30.0)


class DeckungTest(unittest.TestCase):
    """Die eigentliche Regel: Menge, nicht Existenz."""

    def setUp(self):
        self.alt = sd.okxf

    def tearDown(self):
        sd.okxf = self.alt

    def pos(self, kon=145.0):
        return {"inst": "X", "seite": "long", "kontrakte": kon, "modus": "live"}

    def test_vollstaendig_geschuetzt_ergibt_keine_luecke(self):
        sd.okxf = fake([Auftrag(100, 900), Auftrag(45, 880)])
        d = sd.deckung(self.pos(), {"X": {"pos": "145"}})
        self.assertEqual(d["fehlt"], 0.0)
        self.assertEqual(d["gedeckt"], 145.0)

    def test_teilmenge_wird_als_luecke_gemeldet(self):
        """DER Fall vom 02.10.2026: 145 an der Boerse, 126 geschuetzt."""
        sd.okxf = fake([Auftrag(45, 900), Auftrag(11, 880), Auftrag(1, 885),
                        Auftrag(29, 887), Auftrag(12, 889), Auftrag(28, 893)])
        d = sd.deckung(self.pos(), {"X": {"pos": "145"}})
        self.assertEqual(d["gedeckt"], 126.0)
        self.assertEqual(d["fehlt"], 19.0)

    def test_gegen_die_boerse_und_nicht_gegen_das_buch(self):
        """Ein Handgriff hat das Buch verkleinert: die Boerse ist das Mass."""
        sd.okxf = fake([Auftrag(30, 900)])
        d = sd.deckung(self.pos(kon=30.0), {"X": {"pos": "145"}})
        self.assertEqual(d["soll"], 145.0)
        self.assertEqual(d["fehlt"], 115.0)


class PreispruefungTest(unittest.TestCase):
    """Ein Stop auf der falschen Seite ist kein Schutz."""

    def setUp(self):
        self.alt = sd.okxf

    def tearDown(self):
        sd.okxf = self.alt

    def test_stop_unter_kurs_bei_long_ist_erlaubt(self):
        sd.okxf = fake(kurs=1000.0)
        ok, grund = sd.preis_pruefbar("X", "long", 900.0, 800.0)
        self.assertTrue(ok, grund)

    def test_stop_ueber_kurs_bei_long_wird_verweigert(self):
        """Long-Stop ueber dem Kurs verkauft sofort - das ist kein Schutz."""
        sd.okxf = fake(kurs=1000.0)
        ok, grund = sd.preis_pruefbar("X", "long", 1000.0, 800.0)
        self.assertFalse(ok)
        self.assertIn("sofort", grund)

    def test_stop_unter_liquidation_wird_verweigert(self):
        sd.okxf = fake(kurs=1000.0)
        ok, grund = sd.preis_pruefbar("X", "long", 790.0, 800.0)
        self.assertFalse(ok)
        self.assertIn("Liquidation", grund)

    def test_stop_kurz_ueber_liquidation_ist_noch_schutz(self):
        sd.okxf = fake(kurs=1000.0)
        ok, grund = sd.preis_pruefbar("X", "long", 805.0, 800.0)
        self.assertTrue(ok, grund)

    def test_kurz_fehlender_kurs_blockiert(self):
        class F:
            def letzter_kurs(self, inst):
                raise OSError("Verbindung weg")
        sd.okxf = F()
        ok, grund = sd.preis_pruefbar("X", "long", 900.0, 800.0)
        self.assertFalse(ok)
        self.assertIn("nichts gestellt", grund)

    def test_short_ist_gespiegelt(self):
        sd.okxf = fake(kurs=1000.0)
        self.assertTrue(sd.preis_pruefbar("X", "short", 1100.0, 1200.0)[0])
        self.assertFalse(sd.preis_pruefbar("X", "short", 900.0, 800.0)[0])


class ToterStopTest(unittest.TestCase):
    def setUp(self):
        self.alt = sd.okxf

    def tearDown(self):
        sd.okxf = self.alt

    def test_stop_unter_liquidation_wird_als_tot_gemeldet(self):
        """Der gemessene ZEC-Fall: OCO-Stop 1232.32 bei liqPx 1239.12."""
        sd.okxf = fake([Auftrag(11, 1232.32), Auftrag(45, 1252.11)])
        tot = sd.tote_stops("X", "long", 1239.12)
        self.assertEqual([t["menge"] for t in tot], [11.0])

    def test_ohne_liquidation_kein_befund(self):
        sd.okxf = fake([Auftrag(11, 1232.32)])
        self.assertEqual(sd.tote_stops("X", "long", None), [])


class WerkzeugTest(unittest.TestCase):
    """`pruefe` sieht nur Live-Positionen und fasst die Boerse nicht an."""

    def setUp(self):
        self.alt = sd.okxf

    def tearDown(self):
        sd.okxf = self.alt

    def zustand(self, modus="live"):
        return {"positionen": [
            {"inst": "X", "seite": "long", "kontrakte": 145.0, "modus": modus},
            {"inst": "Y", "seite": "long", "kontrakte": 10.0, "modus": "papier"},
        ]}

    def test_papierposition_bleibt_aussen_vor(self):
        sd.okxf = fake([Auftrag(30, 900)],
                       positionen=[{"instId": "X", "pos": "145",
                                    "liqPx": "800"}])
        b = sd.pruefe(self.zustand(), still=True)
        self.assertEqual([x["position"]["inst"] for x in b], ["X"])

    def test_luecke_wird_als_befund_geliefert(self):
        sd.okxf = fake([Auftrag(30, 900)],
                       positionen=[{"instId": "X", "pos": "145",
                                    "liqPx": "800"}])
        b = sd.pruefe(self.zustand(), still=True)
        self.assertEqual(b[0]["deckung"]["fehlt"], 115.0)

    def test_vollstaendig_gedeckt_liefert_keinen_befund(self):
        sd.okxf = fake([Auftrag(145, 900)],
                       positionen=[{"instId": "X", "pos": "145",
                                    "liqPx": "800"}])
        self.assertEqual(sd.pruefe(self.zustand(), still=True), [])

    def test_boersenfrage_fehlschlag_bricht_ab_und_meldet(self):
        class F:
            def positionen(self):
                raise OSError("401")
        sd.okxf = F()
        self.assertIsNone(sd.pruefe(self.zustand(), still=True))


class KeinEigenerSchreibpfadTest(unittest.TestCase):
    """Merksatz: das Werkzeug schreibt keinen Journal-Ersatz.

    `stopdeckung` schreibt ZUSTAND (Vermerk), nicht das Journal - ein
    nachgesetzter Stop ist kein Handel und darf keine Runde erzeugen.
    """

    def test_quelle_hat_keine_journalzeile_fuer_nachgesetzten_stop(self):
        with open(os.path.join(HIER, "stopdeckung.py"), encoding="utf-8") as fh:
            quelle = fh.read()
        self.assertIn("stop_nachgesetzt", quelle)
        self.assertNotIn("h.journal(", quelle)
        self.assertNotIn("aktion=\"anpassen\"", quelle)


if __name__ == "__main__":
    unittest.main()