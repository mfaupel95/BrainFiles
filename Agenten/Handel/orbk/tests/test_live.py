"""ORBK auf Kraken (Spur orbk): Live-Pfad - Sperrgruende, Orderplatzierung,
Fallsafe.

Der Live-Pfad platziert Einstieg + Boersen-Stop nur, wenn ALLE Sperren offen
sind (handel_erlaubt, freigabe.erfuellt, journal_zweitziel, API-Schluessel,
Freigabefenster). Bei geschlossenen Sperren faellt ein --live-Aufruf auf Papier
zurueck (wie kraken). Keine Testrunde beruehrt eine echte Order: alle
Boersenfunktionen werden ersetzt (Patch), und die Dry-Run-Funktion
platziere_einstieg(..., echt=False) darf die Boerse gar nicht erst ansprechen.

Der Live-Pfad legt seit dem Take-Profit-Ausbau zusaetzlich das ZIEL als
take-profit-market-Order an die Boerse (kraken.take_profit_setzen). Ein
Short-Signal wird live verweigert (Kraken-Spot kann kein Short halten). Der
Live-Ausstieg schliesst die echte Position nur nach Buch-vs-Boerse-Pruefung
(_exit_live/_abgleich_runde) - bei Ungewissheit keine Marktorder.
"""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import handeln

INST = {"kraken": "ETHUSD", "zone": "UTC", "eroeffnung": "00:00",
        "session_ende": "24:00", "spread_punkte": 0.1, "punkt_wert_usd": 1.0}
W = {"letzter_einstieg_min_vor_schluss": 60,
     "mindest_range_punkte": {"ETH_USD": 1.0},
     "max_range_punkte":     {"ETH_USD": 40.0},
     "ziel_modus": "r_vielfaches", "ziel_k": 1.5,
     "ziel_punkte": {"ETH_USD": 30},
     "instrument_aktiv": "ETH_USD",
     "instrumente": {"ETH_USD": INST}}


def _k(hh, mm, o, h, l, c):
    return {"zeit": datetime(2026, 9, 13, hh, mm, tzinfo=timezone.utc),
            "o": o, "h": h, "l": l, "c": c}


def _range_kerzen():
    return [_k(0, 0, 99, 100, 98, 99.5), _k(0, 15, 99.5, 100, 98, 99.8)]


def _breakout_kerzen():
    return _range_kerzen() + [_k(0, 30, 100.2, 100.5, 100.1, 100.4)]


def _w_offen():
    w = dict(W, handel_erlaubt=True,
             freigabe={"erfuellt": True, "backtest_bestanden": True},
             journal_zweitziel="Q:\\Handel_Journal\\orbk",
             risiko_pro_trade_usd=10.0)
    return w


class TestLiveSperren(unittest.TestCase):
    def test_gates_geschlossen_nennt_gruende(self):
        w = dict(W, handel_erlaubt=False, freigabe={"erfuellt": False},
                 journal_zweitziel=None)
        with patch.object(handeln, "zeitfenster_offen", lambda: False), \
                patch.object(handeln.kraken, "schluessel_vorhanden",
                             lambda: False):
            gruende = handeln.live_sperren(w)
        text = "; ".join(gruende)
        self.assertIn("handel_erlaubt=false", text)
        self.assertIn("freigabe.erfuellt=false", text)
        self.assertIn("journal_zweitziel", text)
        self.assertIn("KRAKEN_SPOT_API_KEY", text)
        self.assertIn("Freigabefenster", text)

    def test_nur_fenster_fehlt_genau_ein_grund(self):
        w = _w_offen()
        with patch.object(handeln, "zeitfenster_offen", lambda: False), \
                patch.object(handeln.kraken, "schluessel_vorhanden",
                             lambda: True):
            gruende = handeln.live_sperren(w)
        self.assertEqual(len(gruende), 1, gruende)
        self.assertIn("Freigabefenster", gruende[0])

    def test_alles_offen_leer(self):
        w = _w_offen()
        with patch.object(handeln, "zeitfenster_offen", lambda: True), \
                patch.object(handeln.kraken, "schluessel_vorhanden",
                             lambda: True):
            self.assertEqual(handeln.live_sperren(w), [])


class TestPlatzierung(unittest.TestCase):
    def setUp(self):
        self.z = {"position": {"inst": "ETH_USD", "richtung": "long",
                               "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                               "tag": "2026-09-13", "range_hoehe": 2.0,
                               "punkt_wert_usd": 1.0, "risiko_usd": 10.0}}
        # paar_info ist eine oeffentliche (Netz-)Abfrage; fuer echte Runden
        # wird sie hier ersetzt, damit der Test nicht ans Netz geht.
        self.paar_info = patch.object(handeln.kraken, "paar_info",
                                      lambda paar: {"mengen_stellen": 8,
                                                    "preis_stellen": 4})

    def test_echt_false_ruft_keine_boerse(self):
        def _verboten(*a, **k):
            raise AssertionError("Dry-Run darf die Boerse nicht anrufen")
        with patch.object(handeln.kraken, "markt_kauf", _verboten), \
                patch.object(handeln.kraken, "stop_setzen", _verboten):
            p = handeln.platziere_einstieg(self.z, _w_offen(),
                                           self.z["position"], echt=False)
        self.assertIsNone(p)
        self.assertNotIn("kauf_txid", self.z["position"])

    def test_echt_true_ordert_kauf_stop_und_take_profit_long(self):
        aufrufe = []
        def _markt_kauf(paar, menge, echt=False):
            aufrufe.append(("kauf", paar, menge, echt))
            return "TX-KAUF"
        def _stop(paar, menge, stop, echt=False, **k):
            aufrufe.append(("stop", paar, menge, stop, echt))
            return "TX-STOP"
        def _tp(paar, menge, preis, echt=False, **k):
            aufrufe.append(("tp", paar, menge, preis, echt))
            return "TX-TP"
        with self.paar_info, \
                patch.object(handeln.kraken, "markt_kauf", _markt_kauf), \
                patch.object(handeln.kraken, "stop_setzen", _stop), \
                patch.object(handeln.kraken, "take_profit_setzen", _tp):
            p = handeln.platziere_einstieg(self.z, _w_offen(),
                                           self.z["position"], echt=True)
        self.assertEqual(aufrufe[0][:4], ("kauf", "ETHUSD", 5.0, True))
        self.assertEqual(aufrufe[1][:5], ("stop", "ETHUSD", 5.0, 98.0, True))
        # Das ZIEL liegt jetzt als eigenstaendige Boersenorder.
        self.assertEqual(aufrufe[2][:5], ("tp", "ETHUSD", 5.0, 103.4, True))
        self.assertEqual(p["kauf_txid"], "TX-KAUF")
        self.assertEqual(p["stop_txid"], "TX-STOP")
        self.assertEqual(p["tp_txid"], "TX-TP")
        self.assertFalse(p["tp_fehlt"])
        self.assertEqual(p["menge"], 5.0)
        self.assertEqual(p["modus"], "live")

    def test_echt_true_short_wird_verweigert(self):
        """Kraken-Spot kann kein Short halten: ein Short-Signal darf im
        Live-Pfad KEINE Order legen und nennt einen klaren Sperrgrund."""
        def _verboten(*a, **k):
            raise AssertionError("Short darf keine Order an die Boerse legen")
        z = {"position": {"inst": "ETH_USD", "richtung": "short",
                          "einstieg": 97.6, "stop": 100.0, "ziel": 94.6,
                          "tag": "2026-09-13", "range_hoehe": 2.0,
                          "punkt_wert_usd": 1.0, "risiko_usd": 10.0}}
        with self.paar_info, \
                patch.object(handeln.kraken, "markt_verkauf", _verboten), \
                patch.object(handeln.kraken, "markt_kauf", _verboten), \
                patch.object(handeln.kraken, "stop_setzen", _verboten), \
                patch.object(handeln.kraken, "take_profit_setzen", _verboten), \
                patch("builtins.print") as pr:
            p = handeln.platziere_einstieg(z, _w_offen(), z["position"],
                                           echt=True)
        self.assertIsNone(p)
        gedruckt = " ".join(str(a[0]) for a in pr.call_args_list)
        self.assertIn("Short", gedruckt)
        self.assertIn("nicht moeglich", gedruckt)



class TestVorschauUndFallsafe(unittest.TestCase):
    def test_vorschau_druckt_sperrgruende(self):
        puffer = io.StringIO()
        with patch.object(handeln, "_wachen",
                          lambda: dict(W, handel_erlaubt=False)), \
                patch.object(handeln, "lauf", lambda *a, **k: []), \
                patch.object(handeln, "zeitfenster_offen", lambda: False), \
                patch.object(handeln.kraken, "schluessel_vorhanden",
                             lambda: True):
            with redirect_stdout(puffer):
                code = handeln._main(["--vorschau"])
        aus = puffer.getvalue()
        self.assertEqual(code, 0)
        zeilen = [z for z in aus.splitlines() if "gesperrt durch" in z]
        self.assertEqual(len(zeilen), 1, aus)
        self.assertIn("handel_erlaubt=false", zeilen[0])

    def test_live_gesperrt_faellt_auf_papier(self):
        gerufen = []
        def _lauf(modus="papier"):
            gerufen.append(modus)
            return []
        with patch.object(handeln, "_wachen",
                          lambda: dict(W, handel_erlaubt=False)), \
                patch.object(handeln, "lauf", _lauf), \
                patch.object(handeln, "zeitfenster_offen", lambda: False), \
                patch.object(handeln.kraken, "schluessel_vorhanden",
                             lambda: True), \
                patch.object(handeln.kraken, "markt_kauf",
                             lambda *a, **k: (_ for _ in ()).throw(
                                 AssertionError("keine Order bei Sperren"))):
            code = handeln._main(["--live"])
        self.assertEqual(code, 0)
        self.assertEqual(gerufen, ["papier"])


class TestLaufLivePlatziert(unittest.TestCase):
    def test_offene_sperren_platzieren(self):
        aufrufe = []
        def _markt_kauf(paar, menge, echt=False):
            aufrufe.append(("kauf", paar, menge, echt))
            return "TX-KAUF"
        def _stop(paar, menge, stop, echt=False, **k):
            aufrufe.append(("stop", paar, menge, stop, echt))
            return "TX-STOP"
        def _tp(paar, menge, preis, echt=False, **k):
            aufrufe.append(("tp", paar, menge, preis, echt))
            return "TX-TP"
        with tempfile.TemporaryDirectory() as w:
            zpfad = Path(w) / "zustand.json"
            jpfad = Path(w) / "handelsjournal.csv"
            zpfad.write_text(json.dumps({"position": None, "letzter_lauf": None}),
                             encoding="utf-8")
            handeln.kerzen_quelle = lambda w_, key: _breakout_kerzen()
            try:
                with patch.object(handeln, "_wachen", _w_offen), \
                        patch.object(handeln, "ZUSTAND", zpfad), \
                        patch.object(handeln, "JOURNAL", jpfad), \
                        patch.object(handeln, "zeitfenster_offen",
                                     lambda: True), \
                        patch.object(handeln.kraken, "schluessel_vorhanden",
                                     lambda: True), \
                        patch.object(handeln.kraken, "paar_info",
                                     lambda paar: {"mengen_stellen": 8,
                                                   "preis_stellen": 4}), \
                        patch.object(handeln.kraken, "markt_kauf", _markt_kauf), \
                        patch.object(handeln.kraken, "stop_setzen", _stop), \
                        patch.object(handeln.kraken, "take_profit_setzen", _tp), \
                        patch.object(handeln, "_jetzt", lambda: datetime(
                            2026, 9, 13, 0, 45, tzinfo=timezone.utc)), \
                        patch.object(handeln, "_letzter_kurs",
                                     lambda w_, k_: 100.4):
                    meldungen = handeln.lauf("live")
            finally:
                handeln.kerzen_quelle = None
            self.assertTrue(any("EINSTIEG (LIVE)" in m for m in meldungen),
                            meldungen)
            self.assertEqual(aufrufe[0][0], "kauf")
            self.assertEqual(aufrufe[1][0], "stop")
            nachher = json.loads(zpfad.read_text(encoding="utf-8"))
            self.assertEqual(nachher["position"]["modus"], "live")
            self.assertEqual(nachher["position"]["kauf_txid"], "TX-KAUF")
            self.assertEqual(nachher["position"]["tp_txid"], "TX-TP")


class TestKeinLiveEintragInPapier(unittest.TestCase):
    def test_papier_position_ohne_live_felder(self):
        with tempfile.TemporaryDirectory() as w:
            zpfad = Path(w) / "zustand.json"
            jpfad = Path(w) / "handelsjournal.csv"
            zpfad.write_text(json.dumps({"position": None, "letzter_lauf": None}),
                             encoding="utf-8")
            handeln.kerzen_quelle = lambda w_, key: _breakout_kerzen()
            try:
                with patch.object(handeln, "_wachen", lambda: W), \
                        patch.object(handeln, "ZUSTAND", zpfad), \
                        patch.object(handeln, "JOURNAL", jpfad), \
                        patch.object(handeln, "zeitfenster_offen",
                                     lambda: True), \
                        patch.object(handeln, "_jetzt", lambda: datetime(
                            2026, 9, 13, 0, 45, tzinfo=timezone.utc)), \
                        patch.object(handeln, "_letzter_kurs",
                                     lambda w_, k_: 100.4):
                    meldungen = handeln.lauf("papier")
            finally:
                handeln.kerzen_quelle = None
            nachher = json.loads(zpfad.read_text(encoding="utf-8"))
            self.assertTrue(any("EINSTIEG (Papier)" in m for m in meldungen),
                            meldungen)
            self.assertNotIn("modus", nachher["position"])
            self.assertNotIn("kauf_txid", nachher["position"])


if __name__ == "__main__":
    unittest.main()
