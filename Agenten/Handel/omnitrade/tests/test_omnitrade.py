"""Tests fuer die omnitrade-Spur - ohne Netz, ohne laufenden Rust-Prozess.

Die Spur liest Statusdateien und spiegelt deren Position. Beides wird im Test
ersetzt:
  * `lesen.lebt_override` - die Prozessabfrage (tasklist) ist im Test ein
    Lambda, sonst haengt jeder Test an einer echten PID,
  * `handeln.lage_override` - die Statusdateien kommen aus einem Temp-Ordner,
  * der Buch-Zyklus laeuft in einem TEMP-Spurenordner (spur_buch leitet
    Wachen, Zustand und Journal aus dem uebergebenen Ordner ab).

Ein Modulwaechter (setUpModule/tearDownModule) vergleicht die Dateiliste des
ECHTEN Spurenordners vor und nach der Suite: ein Test, der dort hineinschreibt,
faellt auf, statt als Handelsrunde im echten Journal zu landen.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
# Reihenfolge: zuletzt eingefuegt = vorne. SPUR MUSS vorne stehen, sonst
# gewinnt scanner/handeln.py gegen das handeln.py dieser Spur.
for p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    while p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

import handeln as h      # noqa: E402
import lesen as l        # noqa: E402
import spur_buch as buch  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py geladen: %s" % h.__file__
assert l.__file__.startswith(SPUR), "falsches lesen.py geladen: %s" % l.__file__


def _bestand(ordner):
    aus = {}
    for name in sorted(os.listdir(ordner)):
        p = os.path.join(ordner, name)
        if os.path.isfile(p):
            aus[name] = os.path.getsize(p)
    return aus


_ECHT_VORHER = None


def setUpModule():
    global _ECHT_VORHER
    _ECHT_VORHER = _bestand(SPUR)


def tearDownModule():
    nachher = _bestand(SPUR)
    assert nachher == _ECHT_VORHER, (
        "Ein Test hat in den echten Spurenordner geschrieben!\nvorher: %s\nnachher: %s"
        % (_ECHT_VORHER, nachher))


def statusdatei(pfad, symbol="BTCUSDC", netto=0.01, state="running", pid=4711,
                kurs=80000.0, signal="buy", alter_ms=1000, schema=1):
    """Eine Statusdatei im Format von omnitrade-cli/src/status.rs schreiben."""
    jetzt = int(os.times()[4] * 0)  # kein Zeitbezug aus dem Test heraus
    import time
    daten = {
        "schema": schema, "state": state, "exchange": "okx", "symbol": symbol,
        "network": "testnet", "script": "strategien/adx_macd.omni",
        "initial_capital": 500.0, "pid": pid,
        "started_ms": int(time.time() * 1000) - 60000,
        "updated_ms": int(time.time() * 1000) - alter_ms,
        "candles_seen": 302, "last_close": kurs, "last_candle_ms": None,
        "last_signal": signal, "orders_placed": 1, "orders_rejected": 0,
        "net_quantity": netto, "last_error": "",
        "recent_orders": [{"time_ms": 1, "side": "buy", "quantity": netto,
                           "price": kurs, "outcome": "filled", "detail": ""}],
        "recent_candles": [{"time_ms": 1, "open": 1.0, "high": 1.0, "low": 1.0,
                            "close": kurs, "volume": 1.0},
                           {"time_ms": 3600001, "open": 1.0, "high": 1.0,
                            "low": 1.0, "close": kurs, "volume": 1.0}],
    }
    del jetzt
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(daten, f)
    return daten


class ZerlegungTest(unittest.TestCase):
    def test_symbol_wird_zerlegt(self):
        self.assertEqual(l.instrument("BTCUSDC"), "BTC-USDC")
        self.assertEqual(l.instrument("ETHUSDC"), "ETH-USDC")
        self.assertEqual(l.instrument("SOLUSDT"), "SOL-USDT")
        self.assertEqual(l.instrument("xrpusdc"), "XRP-USDC")

    def test_unbekanntes_symbol_ist_none(self):
        self.assertIsNone(l.instrument(""))
        self.assertIsNone(l.instrument(None))
        self.assertIsNone(l.instrument("BTC"))

    def test_quote_wird_hinten_gesucht(self):
        self.assertEqual(l.zerlege_symbol("AVAXEUR"), ("AVAX", "EUR"))
        # "USDC" endet nicht auf "C" - die Reihenfolge der Quoten entscheidet.
        self.assertEqual(l.zerlege_symbol("BTCUSDC"), ("BTC", "USDC"))


class LaufTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omnitrade_test_")
        self.alt_lebt = l.lebt_override
        l.lebt_override = lambda pid: True

    def tearDown(self):
        l.lebt_override = self.alt_lebt
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _datei(self, **kw):
        p = os.path.join(self.tmp, "live_test.json")
        statusdatei(p, **kw)
        return p

    def test_laufender_lauf_mit_position(self):
        e = l.lauf(self._datei())
        self.assertTrue(e["ok"])
        self.assertTrue(e["laeuft"])
        self.assertTrue(e["offen"])
        self.assertEqual(e["inst"], "BTC-USDC")
        self.assertAlmostEqual(e["kurs"], 80000.0)

    def test_leiche_mit_toter_pid_zaehlt_nicht(self):
        l.lebt_override = lambda pid: False
        e = l.lauf(self._datei())
        # Die Datei ist LESBAR (ok), aber der Lauf lebt nicht - genau dieser
        # Unterschied verhindert einen Einstieg auf eine stehengebliebene Menge.
        self.assertTrue(e["ok"])
        self.assertFalse(e["laeuft"])
        self.assertIn("lebt nicht", e["fehler"])

    def test_gestoppter_lauf_ist_kein_kandidat(self):
        e = l.lauf(self._datei(state="stopped", netto=0.0))
        self.assertTrue(e["ok"])
        self.assertFalse(e["laeuft"])
        self.assertIn("nicht running", e["fehler"])

    def test_verkaufspreis_kommt_aus_der_order(self):
        p = os.path.join(self.tmp, "live_verkauf.json")
        daten = statusdatei(p, netto=0.0, signal="sell")
        daten["recent_orders"] = [
            {"time_ms": 1000, "side": "buy", "quantity": 0.01, "price": 80000.0,
             "outcome": "filled", "detail": ""},
            {"time_ms": 2000, "side": "sell", "quantity": 0.01, "price": 81234.5,
             "outcome": "filled", "detail": ""},
            {"time_ms": 3000, "side": "sell", "quantity": 0.01, "price": 0.0,
             "outcome": "rejected", "detail": "abgelehnt"},
        ]
        with open(p, "w", encoding="utf-8") as f:
            json.dump(daten, f)
        e = l.lauf(p)
        self.assertAlmostEqual(e["verkauf"], 81234.5)

    def test_ohne_verkauf_kein_preis(self):
        self.assertIsNone(l.lauf(self._datei())["verkauf"])

    def test_alte_datei_ist_veraltet(self):
        # 10 Stunden alt bei stuendlichem Kerzenabstand (Grenze 2,5 * 3600 s).
        e = l.lauf(self._datei(alter_ms=10 * 3600 * 1000))
        self.assertFalse(e["ok"])
        self.assertIn("veraltet", e["fehler"])

    def test_haengende_datei_mit_lebender_pid_zaehlt_nicht(self):
        # PID lebt, aber die Datei ist zu alt - der Lauf haengt.
        # Genau dieser Fall wurde durch die Alterspruefung in beurteile() abgedeckt.
        e = l.lauf(self._datei(alter_ms=2 * 3600 * 1000))  # 2h alt bei 1h-Intervall
        self.assertTrue(e["ok"])
        self.assertFalse(e["laeuft"])
        self.assertIn("haengt", e["fehler"])

    def test_fehlende_datei_wirft_nicht(self):
        e = l.lauf(os.path.join(self.tmp, "gibtsnicht.json"))
        self.assertFalse(e["ok"])
        self.assertIn("keine Statusdatei", e["fehler"])

    def test_falsches_schema(self):
        e = l.lauf(self._datei(schema=99))
        self.assertFalse(e["ok"])

    def test_dateien_listet_nur_live_json(self):
        statusdatei(os.path.join(self.tmp, "live_a.json"))
        statusdatei(os.path.join(self.tmp, "live_b.json"))
        with open(os.path.join(self.tmp, "auswertung.md"), "w") as f:
            f.write("x")
        namen = [os.path.basename(p) for p in l.dateien(self.tmp)]
        self.assertEqual(namen, ["live_a.json", "live_b.json"])


class QuelleTest(unittest.TestCase):
    def setUp(self):
        self.alt = h.lage_override

    def tearDown(self):
        h.lage_override = self.alt

    def _lauf(self, **kw):
        e = {"ok": True, "laeuft": True, "inst": "BTC-USDC", "offen": True,
             "netto": 0.01, "kurs": 80000.0, "verkauf": None, "signal": "buy",
             "state": "running", "script": "strategien/adx_macd.omni",
             "datei": "live_a.json", "alter_s": 10.0, "fehler": ""}
        e.update(kw)
        return e

    def test_alle_lesbaren_laeufe_werden_instrumente(self):
        # Auch ein gestoppter Lauf kommt ins Dict - sein Zustand traegt den
        # Ausstieg. Der Einstieg entscheidet sich erst in signal().
        h.lage_override = lambda: ([self._lauf(),
                                    self._lauf(inst="ETH-USDC", laeuft=False,
                                               offen=False, kurs=2000.0,
                                               state="stopped",
                                               fehler="Zustand ist 'stopped'")], [])
        daten, kurse, fehler = h.quelle({})
        self.assertEqual(sorted(daten), ["BTC-USDC", "ETH-USDC"])
        self.assertAlmostEqual(kurse["BTC-USDC"], 80000.0)
        self.assertEqual(fehler, [])

    def test_verkaufspreis_schlaegt_last_close(self):
        h.lage_override = lambda: ([self._lauf(offen=False, netto=0.0,
                                               state="stopped", laeuft=False,
                                               kurs=80000.0, verkauf=81234.5)], [])
        daten, kurse, fehler = h.quelle({})
        self.assertAlmostEqual(kurse["BTC-USDC"], 81234.5)

    def test_offene_position_bewertet_mit_last_close(self):
        h.lage_override = lambda: ([self._lauf(kurs=80000.0, verkauf=70000.0)], [])
        daten, kurse, fehler = h.quelle({})
        self.assertAlmostEqual(kurse["BTC-USDC"], 80000.0)

    def test_ohne_kurs_kein_instrument(self):
        h.lage_override = lambda: ([self._lauf(kurs=None)], [])
        daten, kurse, fehler = h.quelle({})
        self.assertEqual(daten, {})
        self.assertTrue(fehler)

    def test_fehler_der_quelle_werden_durchgereicht(self):
        h.lage_override = lambda: ([], ["live_x.json: kaputt"])
        daten, kurse, fehler = h.quelle({})
        self.assertEqual(daten, {})
        self.assertEqual(fehler, ["live_x.json: kaputt"])


class SignalTest(unittest.TestCase):
    def test_laufender_lauf_mit_position_heisst_long(self):
        self.assertEqual(h.signal({"offen": True, "laeuft": True}, {}), "long")

    def test_keine_position_kein_signal(self):
        self.assertIsNone(h.signal({"offen": False, "laeuft": True}, {}))
        self.assertIsNone(h.signal({}, {}))

    def test_toter_lauf_mit_stehengebliebener_menge_kein_signal(self):
        # Genau der Fall vom 30.09.2026: Datei sagt running mit netto>0, die
        # PID ist tot. Ohne diese Bedingung entstuende eine Position, die
        # niemand mehr bewacht.
        self.assertIsNone(h.signal({"offen": True, "laeuft": False}, {}))


class AusstiegTest(unittest.TestCase):
    def setUp(self):
        self.alt = h.lage_override

    def tearDown(self):
        h.lage_override = self.alt

    def _mit(self, **kw):
        e = {"ok": True, "laeuft": True, "inst": "BTC-USDC", "offen": False,
             "netto": 0.0, "state": "running", "fehler": ""}
        e.update(kw)
        h.lage_override = lambda: ([e], [])
        return h.ausstieg_grund({"inst": "BTC-USDC"}, {})

    def test_lauf_ohne_position_schliesst(self):
        self.assertEqual(self._mit(state="running", offen=False),
                         "omnitrade flat")

    def test_gestoppter_lauf_hat_verkauft(self):
        # Die CLI verkauft beim Beenden - die Position ist bei ihr zu.
        self.assertEqual(self._mit(state="stopped", offen=False, laeuft=False),
                         "omnitrade flat")

    def test_gehaltene_position_bleibt_stehen(self):
        self.assertIsNone(self._mit(state="running", offen=True, netto=0.01))

    def test_startend_oder_fehler_ist_kein_signal(self):
        self.assertIsNone(self._mit(state="starting", offen=False))
        self.assertIsNone(self._mit(state="error", offen=False))

    def test_anderes_instrument_beruehrt_nicht(self):
        h.lage_override = lambda: ([{"ok": True, "laeuft": True, "inst": "ETH-USDC",
                                     "offen": False, "state": "running"}], [])
        self.assertIsNone(h.ausstieg_grund({"inst": "BTC-USDC"}, {}))

    def test_ohne_instrument_kein_ausstieg(self):
        self.assertIsNone(h.ausstieg_grund({}, {}))


class ZyklusTest(unittest.TestCase):
    """Der ganze Weg in einem Temp-Spurenordner - inklusive Buch und Journal."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="omnitrade_buch_")
        self.status = tempfile.mkdtemp(prefix="omnitrade_status_")
        self.ziel = tempfile.mkdtemp(prefix="omnitrade_q_")
        w = json.load(open(os.path.join(SPUR, "wachen.json"), encoding="utf-8"))
        # Ein Test darf nie in einen echten Zielpfad schreiben (Lehre 14.09.2026).
        w["journal_zweitziel"] = self.ziel
        w["handel_erlaubt"] = False
        with open(os.path.join(self.tmp, "wachen.json"), "w", encoding="utf-8") as f:
            json.dump(w, f)
        self.alt = h.lage_override

    def tearDown(self):
        h.lage_override = self.alt
        for d in (self.tmp, self.status, self.ziel):
            shutil.rmtree(d, ignore_errors=True)

    def _lauf(self, **kw):
        e = {"ok": True, "laeuft": True, "inst": "BTC-USDC", "offen": True,
             "netto": 0.01, "kurs": 80000.0, "verkauf": None, "signal": "buy",
             "state": "running", "fehler": "", "datei": "live_a.json",
             "alter_s": 5.0, "script": "strategien/adx_macd.omni"}
        e.update(kw)
        return e

    def _zyklus(self):
        return buch.zyklus(self.tmp, h.quelle, h.signal, "papier",
                           "handel/omnitrade", zusatz_ausstieg=h.ausstieg_grund)

    def _zustand(self):
        with open(os.path.join(self.tmp, "zustand.json"), encoding="utf-8") as f:
            return json.load(f)

    def _journal(self):
        p = os.path.join(self.tmp, "handelsjournal.csv")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return [z for z in f.read().splitlines() if z.strip()]

    def test_erster_zyklus_eroeffnet_position(self):
        h.lage_override = lambda: ([self._lauf()], [])
        self._zyklus()
        z = self._zustand()
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        self.assertEqual(p["inst"], "BTC-USDC")
        self.assertEqual(p["seite"], "long")
        # Stop 8 % unter dem Einstieg, Ziel 10R darueber.
        self.assertAlmostEqual(p["stop"], 80000.0 * 0.92, places=4)
        self.assertAlmostEqual(p["ziel"], 80000.0 + 10 * 80000.0 * 0.08, places=4)
        self.assertTrue(any("kauf" in z_ for z_ in self._journal()))

    def test_zweiter_zyklus_bucht_nicht_doppelt(self):
        h.lage_override = lambda: ([self._lauf()], [])
        self._zyklus()
        self._zyklus()
        self.assertEqual(len(self._zustand()["positionen"]), 1)
        kaeufe = [z for z in self._journal() if "kauf" in z]
        self.assertEqual(len(kaeufe), 1)

    def test_lauf_ohne_position_schliesst_mit_grund(self):
        h.lage_override = lambda: ([self._lauf()], [])
        self._zyklus()
        h.lage_override = lambda: ([self._lauf(offen=False, netto=0.0,
                                               state="stopped", laeuft=False)], [])
        self._zyklus()
        self.assertEqual(self._zustand()["positionen"], [])
        zeilen = self._journal()
        self.assertTrue(any("omnitrade flat" in z for z in zeilen), zeilen)

    def test_kein_laufender_lauf_kein_einstieg(self):
        # Ein toter Lauf mit stehengebliebener Menge liefert Daten (sein
        # Zustand wird fuer den Ausstieg gebraucht), aber kein Signal.
        h.lage_override = lambda: ([self._lauf(laeuft=False, offen=True,
                                               fehler="PID 4711 lebt nicht")], [])
        self._zyklus()
        self.assertEqual(self._zustand()["positionen"], [])
        self.assertEqual([z for z in self._journal() if "kauf" in z], [])

    def test_gar_keine_daten_bricht_sauber_ab(self):
        h.lage_override = lambda: ([], ["live_a.json: keine Statusdatei"])
        self._zyklus()
        self.assertEqual(self._zustand()["positionen"], [])


if __name__ == "__main__":
    unittest.main()