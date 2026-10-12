"""ORB auf OKX (Spur orb): Live-Pfad - Sperrgruende, Orderplatzierung, Fallsafe.

Der Live-Pfad platziert Einstieg + Boersen-Stop + Ziel nur, wenn ALLE Sperren
offen sind (handel_erlaubt, freigabe.erfuellt, journal_zweitziel, API-Schluessel,
Freigabefenster). Bei geschlossenen Sperren faellt ein --live-Aufruf auf Papier
zurueck (wie kraken). Keine Testrunde beruehrt eine echte Order: alle
Boersenfunktionen werden ersetzt (Patch), und die Dry-Run-Funktion
platziere_einstieg(..., echt=False) darf die Boerse gar nicht erst ansprechen.

Kein Netz: handeln.kerzen_quelle wird durch synthetische Kerzen ersetzt, das
Freigabefenster durch einen Patch auf handeln.zeitfenster_offen, und okxf-Order-
Funktionen sind gepatched (echter Schluessel ist auf dieser Maschine gesetzt,
darf aber nie angerufen werden).
"""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timezone
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
    """Wachen mit ALLEN Sperren offen bis auf das Fenster (das steuert der
    Test separat ueber handeln.zeitfenster_offen())."""
    w = dict(W, handel_erlaubt=True,
             freigabe={"erfuellt": True, "backtest_bestanden": True},
             journal_zweitziel="Q:\\Handel_Journal\\orb",
             risiko_pro_trade_usdt=10.0)
    return w


class TestLiveSperren(unittest.TestCase):
    def test_gates_geschlossen_nennt_gruende(self):
        w = dict(W, handel_erlaubt=False, freigabe={"erfuellt": False},
                 journal_zweitziel=None)
        with patch.object(handeln, "zeitfenster_offen", lambda: False), \
                patch.object(handeln.okxf, "schluessel_vorhanden", lambda: False):
            gruende = handeln.live_sperren(w)
        text = "; ".join(gruende)
        self.assertIn("handel_erlaubt=false", text)
        self.assertIn("freigabe.erfuellt=false", text)
        self.assertIn("journal_zweitziel", text)
        self.assertIn("OKX_API_KEY", text)
        self.assertIn("Freigabefenster", text)

    def test_nur_fenster_fehlt_genau_ein_grund(self):
        """ALLES offen bis aufs Fenster -> genau EIN Grund mit dem Wort."""
        w = _w_offen()
        with patch.object(handeln, "zeitfenster_offen", lambda: False), \
                patch.object(handeln.okxf, "schluessel_vorhanden", lambda: True):
            gruende = handeln.live_sperren(w)
        self.assertEqual(len(gruende), 1, gruende)
        self.assertIn("Freigabefenster", gruende[0])

    def test_alles_offen_leer(self):
        w = _w_offen()
        with patch.object(handeln, "zeitfenster_offen", lambda: True), \
                patch.object(handeln.okxf, "schluessel_vorhanden", lambda: True):
            self.assertEqual(handeln.live_sperren(w), [])


class TestPlatzierung(unittest.TestCase):
    """platziere_einstieg: echt=False ist die Validierung/Dry-Run (keine
    Boersenorder), echt=True ruft die Ordnung - nie eine echte Order, weil die
    Boersenfunktionen in Tests ersetzt sind."""

    def setUp(self):
        self.z = {"position": {"inst": "ETH_USDT", "richtung": "long",
                               "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                               "tag": "2026-09-13", "range_hoehe": 2.0,
                               "punkt_wert_usdt": 1.0, "risiko_usdt": 10.0}}

    def test_echt_false_ruft_keine_boerse(self):
        """Dry-Run: die geplante Order wird gezeigt, aber kein Exchange-Call."""
        def _verboten(*a, **k):
            raise AssertionError("Dry-Run darf die Boerse nicht anrufen")
        with patch.object(handeln.okxf, "order_limit", _verboten), \
                patch.object(handeln.okxf, "schutz_stop_setzen", _verboten):
            p = handeln.platziere_einstieg(self.z, _w_offen(),
                                           self.z["position"], echt=False)
        self.assertIsNone(p)
        self.assertNotIn("ord_id", self.z["position"])

    def test_echt_true_ordert_einstieg_stop_ziel(self):
        aufrufe = []
        def _order_limit(inst, seite, kontrakte, preis, **k):
            aufrufe.append(("order_limit", inst, seite, kontrakte, preis))
            return "ORD-1"
        def _schutz(inst, seite, kontrakte, stop, ziel=None, **k):
            aufrufe.append(("schutz", inst, seite, kontrakte, stop, ziel))
            return [{"algoId": "ALGO-1"}]
        with patch.object(handeln.okxf, "order_limit", _order_limit), \
                patch.object(handeln.okxf, "schutz_stop_setzen", _schutz):
            p = handeln.platziere_einstieg(self.z, _w_offen(),
                                           self.z["position"], echt=True)
        self.assertIsNotNone(p)
        self.assertEqual(aufrufe[0][:5], ("order_limit", "ETH-USDT-SWAP",
                                          "buy", 5, 100.4))
        self.assertEqual(aufrufe[1][:6], ("schutz", "ETH-USDT-SWAP",
                                          "long", 5, 98.0, 103.4))
        self.assertEqual(p["ord_id"], "ORD-1")
        self.assertEqual(p["kontrakte"], 5)
        self.assertEqual(p["modus"], "live")


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
        """--live mit geschlossenen Sperren: keine Order, lauf() als Papier."""
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
    """lauf('live') mit ALLEN Sperren offen platziert eine echte (gepatchte)
    Boersenorder - Einstieg + Stop + Ziel."""

    def test_offene_sperren_platzieren(self):
        aufrufe = []
        def _order_limit(inst, seite, kontrakte, preis, **k):
            aufrufe.append(("order_limit", inst, seite, kontrakte, preis))
            return "ORD-9"
        def _schutz(inst, seite, kontrakte, stop, ziel=None, **k):
            aufrufe.append(("schutz", inst, seite, kontrakte, stop, ziel))
            return [{"algoId": "ALGO-9"}]
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
            self.assertEqual(nachher["position"]["ord_id"], "ORD-9")


class TestKeinLiveEintragInPapier(unittest.TestCase):
    """Der Papierlauf bleibt unveraendert: kein Live-Merkmal in der Position."""

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
