"""orbk auf OKX-Perp (15.10.2026): Live-Ausstieg, Buch-vs-Boerse-Abgleich,
Schutz-Stop/Ziel. Kein Test platziert eine echte Order: alle Boersenfunktionen
werden ersetzt (Patch), und die erwarteten Marktcloses laufen nur mit echt=True
in der erwarteten Stelle.

Seit der OKX-Umstellung ist der Take-Profit keine eigene kraken-Order mehr:
Einstieg heisst okxf.order_limit, Stop UND Ziel heissen zusammen
okxf.schutz_stop_setzen. Der Live-Ausstieg prueft zuerst okxf.positionen()
und schliesst nur eine noch offene Position per okxf.markt_schliessen.
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


def _w_offen():
    return dict(W, handel_erlaubt=True,
                freigabe={"erfuellt": True, "backtest_bestanden": True},
                journal_zweitziel="Q:\\Handel_Journal\\orbk",
                risiko_pro_trade_usd=10.0)


def _pos_live(letzter_kurs=97.0, modus="live"):
    """Eine LONG-Live-Position, deren Stop (98) verletzt ist."""
    return {"inst": "ETH_USDT", "richtung": "long", "einstieg": 100.0,
            "stop": 98.0, "ziel": 103.0, "tag": "2026-09-13",
            "letzter_kurs": letzter_kurs, "kontrakte": 5, "modus": modus}


class OkxFake:
    """handeln.okxf ohne Netz: jeder Aufruf wird mitgeschrieben."""

    def __init__(self, offen=True, lesefehler=False, close_fehler=False):
        self.offen = offen
        self.lesefehler = lesefehler
        self.close_fehler = close_fehler
        self.rufe = []

    def positionen(self, inst=None):
        self.rufe.append(("positionen",))
        if self.lesefehler:
            raise RuntimeError("Netz weg")
        return [{"instId": "ETH-USDT-SWAP"}] if self.offen else []

    def markt_schliessen(self, inst, kontrakte, seite, **k):
        self.rufe.append(("markt_schliessen", inst, kontrakte, seite))
        if self.close_fehler:
            raise RuntimeError("EOrder:Insufficient funds")
        return "ORD-CLOSE"


class LiveExitTest(unittest.TestCase):
    """Live-Ausstieg: Markt-Close NUR fuer eine live-markierte Position."""

    # Ein Zeitpunkt INNERHALB der Session (tag 2026-09-13, session_ende 24:00),
    # damit nicht der reale Jetzt-Zeitpunkt den Zwangsschluss ausloest.
    JETZT = datetime(2026, 9, 13, 1, 0, tzinfo=timezone.utc)

    def test_live_position_im_live_lauf_ordert_markt_close(self):
        fake = OkxFake()                        # Position an der Boerse offen
        z = {"position": _pos_live()}
        journal_rec = []
        with patch.object(handeln, "okxf", fake), \
                patch.object(handeln, "journal",
                             lambda *f: journal_rec.append(f)), \
                patch("sys.stdout", new_callable=io.StringIO):
            veraendert, grund = handeln.pruefe_ausstiege(
                z, _w_offen(), jetzt=self.JETZT, live=True)
        self.assertTrue(veraendert)
        self.assertEqual(grund, "stop")
        self.assertIn(("markt_schliessen", "ETH-USDT-SWAP", 5, "long"),
                      fake.rufe,
                      "echter Markt-Close nur fuer eine live Position")
        # Lokal gebucht.
        self.assertEqual(z["position"]["ausgang"], "stop")
        self.assertTrue(journal_rec)

    def test_boerse_hat_schon_geschlossen_keine_zweite_order(self):
        fake = OkxFake(offen=False)             # Boerse hat schon geschlossen
        z = {"position": _pos_live()}
        with patch.object(handeln, "okxf", fake), \
                patch.object(handeln, "journal", lambda *f: None), \
                patch("sys.stdout", new_callable=io.StringIO):
            veraendert, grund = handeln.pruefe_ausstiege(
                z, _w_offen(), jetzt=self.JETZT, live=True)
        self.assertTrue(veraendert)
        self.assertEqual(grund, "stop (boerse)")
        # KEINE Marktorder: die wuerde ueberverkaufen und einen Short eroeffnen.
        self.assertNotIn(("markt_schliessen", "ETH-USDT-SWAP", 5, "long"),
                         fake.rufe)

    def test_boerse_nicht_lesbar_keine_order_ungeklaert(self):
        fake = OkxFake(lesefehler=True)
        z = {"position": _pos_live()}
        with patch.object(handeln, "okxf", fake), \
                patch.object(handeln, "journal", lambda *f: None), \
                patch("sys.stdout", new_callable=io.StringIO):
            veraendert, grund = handeln.pruefe_ausstiege(
                z, _w_offen(), jetzt=self.JETZT, live=True)
        self.assertFalse(veraendert, "bei Ungewissheit wird nicht gebucht")
        self.assertTrue(z["position"]["exit_ungeklaert"])
        self.assertEqual([r for r in fake.rufe if r[0] == "markt_schliessen"],
                         [], "keine Marktorder bei Ungewissheit")

    def test_live_position_im_papier_lauf_keine_order_kein_schluss(self):
        """Ein PAPIERLauf schliesst eine echte Position nicht (Boerse schuetzt)."""
        fake = OkxFake()
        z = {"position": _pos_live()}
        with patch.object(handeln, "okxf", fake), \
                patch("sys.stdout", new_callable=io.StringIO):
            veraendert, grund = handeln.pruefe_ausstiege(
                z, _w_offen(), jetzt=self.JETZT, live=False)
        self.assertFalse(veraendert)
        self.assertEqual(fake.rufe, [], "Papierlauf darf keine Boerse anrufen")
        self.assertIsNotNone(z["position"])

    def test_papier_position_im_papier_lauf_bleibt_reine_buchung(self):
        fake = OkxFake()
        z = {"position": _pos_live(modus=None)}     # nicht live markiert
        z["position"].pop("kontrakte")
        journal_rec = []
        with patch.object(handeln, "okxf", fake), \
                patch.object(handeln, "journal",
                             lambda *f: journal_rec.append(f)), \
                patch("sys.stdout", new_callable=io.StringIO):
            veraendert, grund = handeln.pruefe_ausstiege(
                z, _w_offen(), jetzt=self.JETZT, live=False)
        self.assertTrue(veraendert)
        self.assertEqual([r for r in fake.rufe if r[0] == "markt_schliessen"],
                         [], "Papierpfad ist reine Buchoperation")
        self.assertTrue(journal_rec)


class AbgleichRundeTest(unittest.TestCase):
    """Buch gegen Boerse fuer Live-Positionen, vor den Ausstiegen."""

    def test_stop_ausgeloest_an_boerse_wird_nachgezogen(self):
        fake = OkxFake(offen=False)             # Boerse hat schon geschlossen
        z = {"position": _pos_live()}
        journal_rec = []
        with patch.object(handeln, "okxf", fake), \
                patch.object(handeln, "journal",
                             lambda *f: journal_rec.append(f)), \
                patch("sys.stdout", new_callable=io.StringIO):
            bilanz = handeln._abgleich_runde(z, _w_offen())
        self.assertTrue(bilanz["ausgebucht"])
        self.assertIsNone(z.get("position"),
                          "an der Boerse weg - nicht im Buch behalten")
        self.assertEqual([r for r in fake.rufe if r[0] == "markt_schliessen"],
                         [],
                         "keine Marketorder - ein gefuellter Stop hat verkauft")
        self.assertTrue(any("ziel (boerse)" in str(f) for f in journal_rec))

    def test_stop_offen_position_bleibt(self):
        fake = OkxFake()                        # Position noch offen
        z = {"position": _pos_live()}
        with patch.object(handeln, "okxf", fake), \
                patch("sys.stdout", new_callable=io.StringIO):
            bilanz = handeln._abgleich_runde(z, _w_offen())
        self.assertFalse(bilanz["ausgebucht"])
        self.assertIsNotNone(z["position"])
        self.assertNotIn("markt_schliessen", [r[0] for r in fake.rufe])

    def test_papier_position_wird_nicht_geprueft(self):
        fake = OkxFake()
        z = {"position": _pos_live(modus=None)}
        with patch.object(handeln, "okxf", fake), \
                patch("sys.stdout", new_callable=io.StringIO):
            bilanz = handeln._abgleich_runde(z, _w_offen())
        self.assertIsNone(bilanz)
        self.assertEqual(fake.rufe, [])

    def test_boerse_nicht_lesbar_keine_aussage(self):
        fake = OkxFake(lesefehler=True)
        z = {"position": _pos_live()}
        with patch.object(handeln, "okxf", fake), \
                patch("sys.stdout", new_callable=io.StringIO):
            bilanz = handeln._abgleich_runde(z, _w_offen())
        self.assertIsNone(bilanz)
        self.assertIsNotNone(z["position"], "keine Aussage statt geratener Zahl")


class ShortLaufPlatziertTest(unittest.TestCase):
    """Auf OKX-Perp sind Shorts moeglich: ein live Short-Signal ordert sell
    (die alte Short-Verweigerung von Kraken-Spot existiert nicht mehr)."""

    def _k(self, hh, mm, o, h, l, c):
        return {"zeit": datetime(2026, 9, 13, hh, mm, tzinfo=timezone.utc),
                "o": o, "h": h, "l": l, "c": c}

    def _short_kerzen(self):
        return [self._k(0, 0, 99, 100, 98, 99.5),
                self._k(0, 15, 99.5, 100, 98, 99.8),
                self._k(0, 30, 98.0, 98.1, 97.0, 97.4)]  # Schluss < Tief -> short

    def test_live_short_signal_platziert_sell(self):
        aufrufe = []
        def _order_limit(inst, seite, kontrakte, preis, **k):
            aufrufe.append(("order_limit", seite))
            return "ORD-S"
        def _schutz(inst, seite, kontrakte, stop, ziel=None, **k):
            aufrufe.append(("schutz", seite))
            return {}
        with tempfile.TemporaryDirectory() as w:
            zpfad = Path(w) / "zustand.json"
            jpfad = Path(w) / "handelsjournal.csv"
            zpfad.write_text(json.dumps({"position": None, "letzter_lauf": None}),
                             encoding="utf-8")
            handeln.kerzen_quelle = lambda w_, key: self._short_kerzen()
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
                                     lambda w_, k_: 97.4):
                    with redirect_stdout(io.StringIO()):
                        meldungen = handeln.lauf("live")
            finally:
                handeln.kerzen_quelle = None
            self.assertTrue(any("EINSTIEG (LIVE)" in m for m in meldungen),
                            meldungen)
            # Short legt Einstieg (sell) + Schutz in Shortrichtung an OKX.
            self.assertEqual(aufrufe[0], ("order_limit", "sell"))
            self.assertEqual(aufrufe[1], ("schutz", "short"))
            nachher = json.loads(zpfad.read_text(encoding="utf-8"))
            self.assertIsNotNone(nachher.get("position"),
                                 "verweigerter Short macht keine Position")
            self.assertEqual(nachher["position"]["richtung"], "short")
            self.assertEqual(nachher["position"]["modus"], "live")


if __name__ == "__main__":
    unittest.main()
