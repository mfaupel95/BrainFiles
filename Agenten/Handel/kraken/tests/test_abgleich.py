"""Buch gegen Boerse: Geister und Waisen - reine Rechnung auf Attrappen, kein Netz.

Der Fall, der dieses Werkzeug ausgeloest hat (30.09.2026, T-208):
  * DOTEUR stand als Position im Buch, die Boerse hatte sie am 29.09. um 01:36
    per Stop verkauft (45,9896983 DOT, 45,89 EUR nach Gebuehr) - ein GEIST.
  * Vier SUIEUR-Auftraege sahen wie Waisen aus, weil das SPOT-Guthaben 0 SUI
    zeigte - dabei lagen 274,64 SUI in vier MARGIN-Positionen.

Deshalb sind hier BEIDE Faelle als Regressionstest festgenagelt.
"""
import csv
import importlib.util
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
sys.path.insert(0, HIER)


def _lade(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ab = _lade("abgleich", os.path.join(SPUR, "abgleich.py"))
_s = _lade("spot_stops_a", os.path.join(SPUR, "spot_stops.py"))
assert ab.__file__.startswith(SPUR), ab.__file__

PAARE = {
    "DOTEUR": {"base": "DOT", "quote": "ZEUR", "lot_decimals": 8, "ordermin": "0.2"},
    "SUIEUR": {"base": "SUI", "quote": "ZEUR", "lot_decimals": 5, "ordermin": "1"},
    "ATOMEUR": {"base": "ATOM", "quote": "ZEUR", "lot_decimals": 8, "ordermin": "1"},
}
DOT_MENGE = 45.9896983
SUI_GESAMT = 274.64483


class FalscherKraken:
    """Antworten in der ECHTEN Form: OpenPositions OHNE 'open'-Huelle."""

    def __init__(self, guthaben=None, positionen=None, orders=None,
                 closed=None, ledger=None):
        self._bal = guthaben or {}
        self._pos = positionen or {}
        self._ord = orders or {}
        self._closed = closed or {}
        self._ledger = ledger or {}

    def _roh_privat(self, name, **kw):
        if name == "BalanceEx":
            return self._bal
        if name == "OpenPositions":
            return dict(self._pos)
        if name == "OpenOrders":
            return {"open": self._ord}
        if name == "ClosedOrders":
            return {"closed": self._closed}
        if name == "Ledgers":
            return {"ledger": {k: v for k, v in self._ledger.items()
                               if v.get("asset") == kw.get("asset")}}
        return {}

    def _paare_laden(self):
        return PAARE


def buch_dot():
    return [{"paar": "DOTEUR", "einstieg": 1.0882, "eur": 50.05,
             "menge": DOT_MENGE, "stop": 1.0045728, "ziel": 1.2524544,
             "eroeffnet": "2026-09-27", "kauf_txid": "OQOZWH",
             "stop_txid": "O2YTEL-7R6ZT-ULOXRN"}]


def stop(txid, paar, vol, preis="1.0", art="stop-loss"):
    return {txid: {"vol": str(vol), "descr": {"pair": paar, "ordertype": art,
                                              "price": str(preis)}}}


class BestandTest(unittest.TestCase):
    def setUp(self):
        self._orig = _s._paare_laden
        _s._paare_laden = lambda: PAARE

    def tearDown(self):
        _s._paare_laden = self._orig

    def test_margin_zaehlt_zum_bestand(self):
        # 0 SUI im Guthaben, 274,64 SUI in Margin-Positionen.
        pos = {"p%d" % i: {"pair": "SUIEUR", "vol": v, "vol_closed": "0"}
               for i, v in enumerate(("136.77266", "101.30713", "27.85165",
                                      "8.71339"))}
        k = FalscherKraken(positionen=pos)
        b = ab.kontobestand(k, _s)
        self.assertAlmostEqual(b["SUI"]["margin"], SUI_GESAMT, places=4)
        self.assertAlmostEqual(b["SUI"]["gesamt"], SUI_GESAMT, places=4)

    def test_teilgeschlossene_position_zaehlt_den_rest(self):
        k = FalscherKraken(positionen={"p1": {"pair": "SUIEUR", "vol": "10",
                                              "vol_closed": "4"}})
        self.assertAlmostEqual(ab.kontobestand(k, _s)["SUI"]["gesamt"], 6.0)

    def test_spot_und_margin_werden_addiert(self):
        k = FalscherKraken(guthaben={"SUI": {"balance": "1.0", "hold_trade": "0"}},
                           positionen={"p1": {"pair": "SUIEUR", "vol": "2",
                                              "vol_closed": "0"}})
        self.assertAlmostEqual(ab.kontobestand(k, _s)["SUI"]["gesamt"], 3.0)

    def test_schutzauftraege_nur_stop_und_ziel(self):
        k = FalscherKraken(orders={**stop("O1", "SUIEUR", 1.0),
                                   "O2": {"vol": "1", "descr": {
                                       "pair": "SUIEUR", "ordertype": "limit",
                                       "price": "1"}},
                                   **stop("O3", "SUIEUR", 1.0, art="take-profit")})
        arten = sorted(a["art"] for a in ab.schutzauftraege(k, _s))
        self.assertEqual(arten, ["stop-loss", "take-profit"])


class BefundeTest(unittest.TestCase):
    def setUp(self):
        self._orig = _s._paare_laden
        _s._paare_laden = lambda: PAARE

    def tearDown(self):
        _s._paare_laden = self._orig

    def test_position_ohne_bestand_ist_geist(self):
        f = ab.befunde(buch_dot(), {}, [])
        self.assertEqual([x["art"] for x in f], ["geist"])
        self.assertEqual(f[0]["muenze"], "DOT")

    def test_position_mit_bestand_ist_kein_geist(self):
        bestand = {"DOT": {"spot": DOT_MENGE, "reserviert": 0.0, "margin": 0.0,
                           "gesamt": DOT_MENGE}}
        self.assertEqual(ab.befunde(buch_dot(), bestand, []), [])

    def test_papierposition_wird_nicht_geprueft(self):
        # Ohne Boersenseite (kein kauf_txid, kein beleg) gibt es nichts zu
        # vergleichen - ein Papierbuch ist nie an der Boerse.
        p = dict(buch_dot()[0])
        p.pop("kauf_txid")
        p.pop("stop_txid")
        self.assertEqual(ab.befunde([p], {}, []), [])

    def test_teilbestand_ist_eigene_art(self):
        bestand = {"DOT": {"spot": DOT_MENGE * 0.5, "reserviert": 0.0,
                           "margin": 0.0, "gesamt": DOT_MENGE * 0.5}}
        f = ab.befunde(buch_dot(), bestand, [])
        self.assertEqual([x["art"] for x in f], ["teils"])

    def test_auftrag_ohne_bestand_ist_waise(self):
        f = ab.befunde([], {}, ab.schutzauftraege(
            FalscherKraken(orders=stop("O1", "SUIEUR", 30.69)), _s))
        self.assertEqual([x["art"] for x in f], ["waise"])
        self.assertEqual(f[0]["txid"], "O1")

    def test_auftrag_ueber_marginposition_ist_keine_waise(self):
        # Der SUI-Fehlalarm: Spot 0, Margin 274,64 - der Auftrag ist gedeckt.
        pos = {"p1": {"pair": "SUIEUR", "vol": str(SUI_GESAMT), "vol_closed": "0"}}
        k = FalscherKraken(positionen=pos,
                           orders=stop("OJHKPN", "SUIEUR", 136.77266))
        bestand = ab.kontobestand(k, _s)
        self.assertEqual(ab.befunde([], bestand, ab.schutzauftraege(k, _s)), [])

    def test_leeres_buch_und_leere_boerse_keine_meldung(self):
        self.assertEqual(ab.befunde([], {}, []), [])


class EchterAusstiegTest(unittest.TestCase):
    def setUp(self):
        self._orig = _s._paare_laden
        _s._paare_laden = lambda: PAARE

    def tearDown(self):
        _s._paare_laden = self._orig

    def test_stop_aus_closed_orders_liefert_netto(self):
        # Die echten Zahlen des DOT-Stops vom 29.09.2026.
        k = FalscherKraken(closed={"O2YTEL-7R6ZT-ULOXRN": {
            "vol_exec": "45.98969830", "price": "1.0038", "cost": "46.16446",
            "fee": "0.27699", "closetm": 1790636215}})
        e = ab.echter_ausstieg(k, buch_dot()[0])
        self.assertAlmostEqual(e["netto"], 45.88747, places=5)
        self.assertAlmostEqual(e["menge"], DOT_MENGE, places=8)
        self.assertEqual(e["quelle"], "ClosedOrders O2YTEL-7R6ZT-ULOXRN")

    def test_ohne_zeugen_keine_zahl(self):
        self.assertIsNone(ab.echter_ausstieg(FalscherKraken(), buch_dot()[0]))

    def test_ledger_als_zweiter_zeuge(self):
        k = FalscherKraken(ledger={
            "L1": {"time": "1790636215.0", "type": "trade", "asset": "DOT",
                   "amount": "-45.98969830", "fee": "0", "refid": "OTX"},
            "L2": {"time": "1790636215.0", "type": "trade", "asset": "ZEUR",
                   "amount": "46.16446", "fee": "0.27699", "refid": "OTX"}})
        p = dict(buch_dot()[0])
        p.pop("stop_txid")
        e = ab.echter_ausstieg(k, p)
        self.assertAlmostEqual(e["brutto"], 46.16446, places=5)
        self.assertAlmostEqual(e["netto"], 45.88747, places=5)


class LaufTest(unittest.TestCase):
    """Der Schreibweg - auf Attrappen, ohne die echte Spur anzufassen."""

    def setUp(self):
        self._orig = _s._paare_laden
        _s._paare_laden = lambda: PAARE
        self.journal = []
        self.geschrieben = []
        self.tmp = tempfile.mkdtemp(prefix="t208_ab_")
        # NIE der echte Journalpfad: sonst liest der Test die echte Spur
        # (genau der Fehler, den die Haus-Regel "ein Test darf nie in einen
        # echten Zielpfad schreiben" verbietet).
        self.jpfad = os.path.join(self.tmp, "handelsjournal.csv")

    def tearDown(self):
        _s._paare_laden = self._orig

    def _lauf(self, k, buch, anwenden=True, jpfad=None):
        return ab.lauf(k, _s, buch=buch, anwenden=anwenden,
                       schreibe=lambda: self.geschrieben.append(1),
                       journal=lambda *f: self.journal.append(f),
                       journal_pfad=self.jpfad if jpfad is None else jpfad)

    def _kraken(self):
        return FalscherKraken(closed={"O2YTEL-7R6ZT-ULOXRN": {
            "vol_exec": "45.98969830", "price": "1.0038", "cost": "46.16446",
            "fee": "0.27699"}})

    def _journal_mit_zeile(self):
        """Ein Journal, in dem die Ausbuchung dieser Position schon steht."""
        with open(self.jpfad, "w", newline="", encoding="utf-8") as f:
            s = csv.writer(f)
            s.writerow(["zeit", "modus", "aktion", "paar", "preis", "eur",
                        "menge", "stop", "ziel", "grund"])
            s.writerow(["2026-09-30T11:00:00+00:00", "live", "verkauf", "DOTEUR",
                        "1.0038", "45.89", "%.8f" % DOT_MENGE, "", "",
                        "stop (boerse) buch_nachgezogen_boerse | ClosedOrders X"])
        return self.jpfad

    def test_vorschau_schreibt_nichts(self):
        buch = buch_dot()
        b = self._lauf(self._kraken(), buch, anwenden=False)
        self.assertEqual(b["ausgebucht"], 0)
        self.assertEqual(len(buch), 1)
        self.assertEqual(self.journal, [])
        self.assertEqual(self.geschrieben, [])

    def test_anwenden_bucht_mit_echtem_erloes(self):
        buch = buch_dot()
        b = self._lauf(self._kraken(), buch)
        self.assertEqual(b["ausgebucht"], 1)
        self.assertEqual(buch, [])
        self.assertEqual(self.geschrieben, [1])
        f = self.journal[0]
        self.assertEqual(f[1], "live")
        self.assertEqual(f[2], "verkauf")
        self.assertEqual(f[3], "DOTEUR")
        self.assertEqual(f[5], "45.89")                    # netto, nicht brutto
        self.assertIn("buch_nachgezogen_boerse", f[9])
        self.assertIn("stop (boerse)", f[9])

    def test_ohne_boersenerloes_bleibt_die_position_stehen(self):
        buch = buch_dot()
        b = self._lauf(FalscherKraken(), buch)
        self.assertEqual(b["ausgebucht"], 0)
        self.assertEqual(len(buch), 1)
        self.assertEqual(len(b["unklar"]), 1)
        self.assertEqual(self.journal, [])

    def test_zweiter_lauf_findet_nichts_mehr(self):
        buch = buch_dot()
        k = self._kraken()
        self._lauf(k, buch)
        b2 = self._lauf(k, buch)
        self.assertEqual(b2["ausgebucht"], 0)
        self.assertEqual(b2["befunde"], [])
        self.assertEqual(len(self.journal), 1)

    def test_vorgabe_journalpfad_ist_die_spur(self):
        # Der Vorgabepfad wurde von keinem Test beruehrt und war beim ersten
        # ECHTEN Lauf ein NameError (JOURNAL gab es im Modul nicht) - die
        # Attrappen hatten den Pfad immer mitgegeben. Deshalb hier ein Lauf
        # OHNE journal_pfad: er muss durchlaufen.
        b = ab.lauf(FalscherKraken(), _s, buch=[], anwenden=False)
        self.assertTrue(b["gelesen"])
        self.assertEqual(b["befunde"], [])
        self.assertTrue(ab.JOURNAL.endswith("handelsjournal.csv"))

    def test_schon_gebucht_erkennt_die_zeile(self):
        # Ein Abbruch zwischen Journalzeile und Zustandsschreiben darf die
        # Runde nicht doppelt buchen.
        p = buch_dot()[0]
        self.assertTrue(ab.schon_gebucht(self._journal_mit_zeile(), p))
        self.assertFalse(ab.schon_gebucht(self.jpfad, dict(p, menge=1.0)))
        self.assertFalse(ab.schon_gebucht(os.path.join(self.tmp, "gibtsnicht"), p))

    def test_mit_vorhandener_zeile_wird_nicht_doppelt_gebucht(self):
        self._journal_mit_zeile()
        buch = buch_dot()
        b = self._lauf(self._kraken(), buch)
        self.assertEqual(b["ausgebucht"], 1)          # aus dem Buch genommen
        self.assertEqual(buch, [])
        self.assertEqual(self.journal, [])            # aber KEINE zweite Zeile

    def test_nicht_lesbare_boerse_ist_keine_aussage(self):
        class Kaputt(FalscherKraken):
            def _roh_privat(self, name, **kw):
                raise RuntimeError("Netz weg")

        b = self._lauf(Kaputt(), buch_dot())
        self.assertFalse(b["gelesen"])
        self.assertIn("Netz weg", b["fehler"])
        self.assertEqual(self.geschrieben, [])
        self.assertEqual(self.journal, [])


class ZyklusAnbindungTest(unittest.TestCase):
    """Der Abgleich muss IM Zyklus laufen, und zwar vor den Ausstiegen.

    Ohne diese Bindung bleibt er ein Werkzeug, das niemand aufruft - genau der
    Fehler, den dieses Haus schon mehrfach hatte (ein Nachweis ist keine Wache).
    """

    def setUp(self):
        with open(os.path.join(SPUR, "handeln.py"), encoding="utf-8") as f:
            self.quelle = f.read()

    def test_abgleich_laeuft_vor_den_ausstiegen(self):
        # Die LETZTE Fundstelle ist der Aufruf im Zyklus - die erste waere die
        # Definition von pruefe_ausstiege (die steht weiter oben).
        self.assertIn("_abgleich_runde(z, w)", self.quelle)
        self.assertLess(self.quelle.index("    _abgleich_runde(z, w)\n"),
                        self.quelle.rindex("    pruefe_ausstiege(z, w, live)\n"))

    def test_bilanz_landet_im_zustand(self):
        self.assertIn('z["buch_abgleich"]', self.quelle)


if __name__ == "__main__":
    unittest.main()