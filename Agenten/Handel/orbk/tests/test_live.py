"""ORBK auf OKX-Perp (Spur orbk): Live-Pfad - Sperrgruende, Orderplatzierung,
Fallsafe.

Der Live-Pfad platziert Einstieg + Boersen-Stop/Ziel nur, wenn ALLE Sperren
offen sind (handel_erlaubt, freigabe.erfuellt, journal_zweitziel,
API-Schluessel, Freigabefenster). Bei geschlossenen Sperren faellt ein
--live-Aufruf auf Papier zurueck (wie xperp). Keine Testrunde beruehrt eine
echte Order: alle Boersenfunktionen werden ersetzt (Patch), und die
Dry-Run-Funktion platziere_einstieg(..., echt=False) darf die Boerse gar
nicht erst ansprechen.

Seit der OKX-Umstellung (15.10.2026) legt der Live-Pfad Einstieg
(okxf.order_limit) und Stop+Ziel zusammen als Schutz (okxf.schutz_stop_setzen)
an die Boerse; die Position traegt ord_id und kontrakte statt kraken-TXIDs.
Auf OKX-Perp sind Shorts moeglich: ein Short-Signal ordert sell und wird
NICHT verweigert. Der Live-Ausstieg schliesst die echte Position nur nach
Buch-vs-Boerse-Pruefung (_exit_live/_abgleich_runde) - bei Ungewissheit
keine Marktorder.
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

INST = {"okx": "ETH-USDT-SWAP", "zone": "UTC", "eroeffnung": "00:00",
        "session_ende": "24:00", "spread_punkte": 0.1, "punkt_wert_usdt": 1.0}
W = {"letzter_einstieg_min_vor_schluss": 60,
     "mindest_range_punkte": {"ETH_USDT": 1.0},
     "max_range_punkte":     {"ETH_USDT": 40.0},
     "ziel_modus": "r_vielfaches", "ziel_k": 1.5,
     "ziel_punkte": {"ETH_USDT": 30},
     "instrument_aktiv": "ETH_USDT",
     "instrumente": {"ETH_USDT": INST}}


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
                patch.object(handeln.okxf, "schluessel_vorhanden",
                             lambda: False):
            gruende = handeln.live_sperren(w)
        text = "; ".join(gruende)
        self.assertIn("handel_erlaubt=false", text)
        self.assertIn("freigabe.erfuellt=false", text)
        self.assertIn("journal_zweitziel", text)
        self.assertIn("OKX_API_KEY/SECRET/PASSPHRASE", text)
        self.assertIn("Freigabefenster", text)

    def test_nur_fenster_fehlt_genau_ein_grund(self):
        w = _w_offen()
        with patch.object(handeln, "zeitfenster_offen", lambda: False), \
                patch.object(handeln.okxf, "schluessel_vorhanden",
                             lambda: True):
            gruende = handeln.live_sperren(w)
        self.assertEqual(len(gruende), 1, gruende)
        self.assertIn("Freigabefenster", gruende[0])

    def test_alles_offen_leer(self):
        w = _w_offen()
        with patch.object(handeln, "zeitfenster_offen", lambda: True), \
                patch.object(handeln.okxf, "schluessel_vorhanden",
                             lambda: True):
            self.assertEqual(handeln.live_sperren(w), [])


class TestPlatzierung(unittest.TestCase):
    def setUp(self):
        self.z = {"position": {"inst": "ETH_USDT", "richtung": "long",
                               "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                               "tag": "2026-09-13", "range_hoehe": 2.0,
                               "punkt_wert_usdt": 1.0, "risiko_usd": 10.0}}

    def test_echt_false_ruft_keine_boerse(self):
        def _verboten(*a, **k):
            raise AssertionError("Dry-Run darf die Boerse nicht anrufen")
        with patch.object(handeln.okxf, "order_limit", _verboten), \
                patch.object(handeln.okxf, "schutz_stop_setzen", _verboten):
            p = handeln.platziere_einstieg(self.z, _w_offen(),
                                           self.z["position"], echt=False)
        self.assertIsNone(p)
        self.assertNotIn("ord_id", self.z["position"])

    def test_echt_true_ordert_einstieg_und_schutz_long(self):
        """Einstieg (order_limit, buy) + Schutz mit Stop UND Ziel an OKX."""
        aufrufe = []
        def _order_limit(inst, seite, kontrakte, preis, **k):
            aufrufe.append(("order_limit", inst, seite, kontrakte, preis))
            return "ORD-E"
        def _schutz(inst, seite, kontrakte, stop, ziel=None, **k):
            aufrufe.append(("schutz", inst, seite, kontrakte, stop, ziel))
            return {}
        with patch.object(handeln.okxf, "order_limit", _order_limit), \
                patch.object(handeln.okxf, "schutz_stop_setzen", _schutz):
            p = handeln.platziere_einstieg(self.z, _w_offen(),
                                           self.z["position"], echt=True)
        self.assertEqual(aufrufe[0],
                         ("order_limit", "ETH-USDT-SWAP", "buy", 5, 100.4))
        # Stop UND Ziel liegen jetzt in EINEM Schutz-Auftrag an OKX.
        self.assertEqual(aufrufe[1],
                         ("schutz", "ETH-USDT-SWAP", "long", 5, 98.0, 103.4))
        self.assertEqual(p["ord_id"], "ORD-E")
        self.assertEqual(p["kontrakte"], 5)
        self.assertEqual(p["modus"], "live")

    def test_echt_true_short_ordert_verkauf_an_okx(self):
        """Auf OKX-Perp sind Shorts moeglich: ein Short-Signal ordert sell
        und wird nicht mehr verweigert (Kraken-Spot existiert nicht mehr)."""
        aufrufe = []
        def _order_limit(inst, seite, kontrakte, preis, **k):
            aufrufe.append(("order_limit", seite))
            return "ORD-S"
        def _schutz(inst, seite, kontrakte, stop, ziel=None, **k):
            aufrufe.append(("schutz", seite))
            return {}
        z = {"position": {"inst": "ETH_USDT", "richtung": "short",
                          "einstieg": 97.6, "stop": 100.0, "ziel": 94.6,
                          "tag": "2026-09-13", "range_hoehe": 2.0,
                          "punkt_wert_usdt": 1.0, "risiko_usd": 10.0}}
        with patch.object(handeln.okxf, "order_limit", _order_limit), \
                patch.object(handeln.okxf, "schutz_stop_setzen", _schutz):
            p = handeln.platziere_einstieg(z, _w_offen(), z["position"],
                                           echt=True)
        self.assertEqual(aufrufe[0], ("order_limit", "sell"))
        self.assertEqual(aufrufe[1], ("schutz", "short"))
        self.assertEqual(p["modus"], "live")
        self.assertEqual(p["ord_id"], "ORD-S")


class TestVorschauUndFallsafe(unittest.TestCase):
    def test_vorschau_druckt_sperrgruende(self):
        puffer = io.StringIO()
        with patch.object(handeln, "_wachen",
                          lambda: dict(W, handel_erlaubt=False)), \
                patch.object(handeln, "lauf", lambda *a, **k: []), \
                patch.object(handeln, "zeitfenster_offen", lambda: False), \
                patch.object(handeln.okxf, "schluessel_vorhanden",
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
                patch.object(handeln.okxf, "schluessel_vorhanden",
                             lambda: True), \
                patch.object(handeln.okxf, "order_limit",
                             lambda *a, **k: (_ for _ in ()).throw(
                                 AssertionError("keine Order bei Sperren"))):
            code = handeln._main(["--live"])
        self.assertEqual(code, 0)
        self.assertEqual(gerufen, ["papier"])


class TestLaufLivePlatziert(unittest.TestCase):
    def test_offene_sperren_platzieren(self):
        aufrufe = []
        def _order_limit(inst, seite, kontrakte, preis, **k):
            aufrufe.append(("order_limit", seite, kontrakte))
            return "ORD-E"
        def _schutz(inst, seite, kontrakte, stop, ziel=None, **k):
            aufrufe.append(("schutz", seite, kontrakte))
            return {}
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
                        patch.object(handeln.okxf, "schluessel_vorhanden",
                                     lambda: True), \
                        patch.object(handeln.okxf, "order_limit",
                                     _order_limit), \
                        patch.object(handeln.okxf, "schutz_stop_setzen",
                                     _schutz), \
                        patch.object(handeln, "_jetzt", lambda: datetime(
                            2026, 9, 13, 0, 45, tzinfo=timezone.utc)), \
                        patch.object(handeln, "_letzter_kurs",
                                     lambda w_, k_: 100.4):
                    meldungen = handeln.lauf("live")
            finally:
                handeln.kerzen_quelle = None
            self.assertTrue(any("EINSTIEG (LIVE)" in m for m in meldungen),
                            meldungen)
            self.assertEqual(aufrufe[0][0], "order_limit")
            self.assertEqual(aufrufe[1][0], "schutz")
            nachher = json.loads(zpfad.read_text(encoding="utf-8"))
            self.assertEqual(nachher["position"]["modus"], "live")
            self.assertEqual(nachher["position"]["ord_id"], "ORD-E")


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
            self.assertNotIn("ord_id", nachher["position"])


if __name__ == "__main__":
    unittest.main()
