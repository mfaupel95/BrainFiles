"""orbk Live-Ausbau (12.10.2026): Boersen-Take-Profit, Live-Ausstieg,
Buch-vs-Boerse-Abgleich, Short-Verweigerung. Kein Test platziert eine echte
Order: alle Boersenfunktionen werden ersetzt (Patch), und die erwarteten
Marktcloses laufen nur mit echt=True in der erwarteten Stelle.
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


def _w_offen():
    return dict(W, handel_erlaubt=True,
                freigabe={"erfuellt": True, "backtest_bestanden": True},
                journal_zweitziel="Q:\\Handel_Journal\\orbk",
                risiko_pro_trade_usd=10.0)


def _pos_live(letzter_kurs=97.0, modus="live"):
    """Eine LONG-Live-Position, deren Stop (98) verletzt ist."""
    return {"inst": "ETH_USD", "richtung": "long", "einstieg": 100.0,
            "stop": 98.0, "ziel": 103.0, "tag": "2026-09-13",
            "letzter_kurs": letzter_kurs, "menge": 5.0,
            "kauf_txid": "TX-KAUF", "stop_txid": "TX-STOP",
            "tp_txid": "TX-TP", "modus": modus}


class KrakenAttrappe:
    """handeln.kraken ohne Netz: jeder Aufruf wird mitgeschrieben."""

    def __init__(self, stop_gefuellt=False, tp_gefuellt=False,
                 verkauf_fehler=False, lesefehler=False):
        self.stop_gefuellt_flag = stop_gefuellt
        self.tp_gefuellt_flag = tp_gefuellt
        self.verkauf_fehler = verkauf_fehler
        self.lesefehler = lesefehler
        self.rufe = []

    def stop_gefuellt(self, txid):
        self.rufe.append(("stop_gefuellt", txid))
        if self.lesefehler:
            raise RuntimeError("Netz weg")
        return self.stop_gefuellt_flag

    def order_stornieren(self, txid):
        self.rufe.append(("storno", txid))
        return {"count": 1}

    def markt_verkauf(self, paar, menge, echt=False):
        self.rufe.append(("verkauf", paar, menge, echt))
        if self.verkauf_fehler:
            raise RuntimeError("EOrder:Insufficient funds")
        return "TX-CLOSE"

    def _verboten(self, *a, **k):
        raise AssertionError("unerwartete Orderfunktion: %s" % a)

    markt_kauf = stop_setzen = take_profit_setzen = _verboten


class TakeProfitSetzenTest(unittest.TestCase):
    """kraken.take_profit_setzen (seit 12.10.2026) - Runde an _add_order."""

    def _rufe(self, echt):
        aufrufe = []

        def _add_order(paar, seite, menge, ordertyp="market", preis=None,
                       echt=False, **z):
            aufrufe.append((paar, seite, menge, ordertyp, preis, echt))
            return "TX"
        with patch.object(handeln.kraken, "_add_order", _add_order), \
                patch.object(handeln.kraken, "paar_info",
                             lambda p: {"preis_stellen": 4, "mengen_stellen": 8}):
            tx = handeln.kraken.take_profit_setzen("ETHUSD", 5.0, 103.42,
                                                   echt=echt)
        return aufrufe, tx

    def test_echt_false_validiert_mit_richtigem_ordertyp(self):
        aufrufe, tx = self._rufe(echt=False)
        self.assertEqual(len(aufrufe), 1)
        paar, seite, menge, art, preis, echt = aufrufe[0]
        self.assertEqual((paar, seite, menge, art),
                         ("ETHUSD", "sell", 5.0, "take-profit-market"))
        # 103.42 mit preis_stellen=4 -> gerundet "103.4200" (aufgerundet, damit
        # der Trigger nie VOR dem Ziel feuert).
        self.assertEqual(preis, "103.4200")
        self.assertIs(echt, False)          # validate-Pfad, keine echte Order

    def test_echt_true_leitet_echt_durch(self):
        aufrufe, tx = self._rufe(echt=True)
        self.assertEqual(aufrufe[0][5], True)
        self.assertEqual(tx, "TX")


class LiveExitTest(unittest.TestCase):
    """(b) Live-Ausstieg: Markt-Close NUR fuer eine live-markierte Position."""

    # Ein Zeitpunkt INNERHALB der Session (tag 2026-09-13, session_ende 24:00),
    # damit nicht der reale Jetzt-Zeitpunkt den Zwangsschluss ausloest.
    JETZT = datetime(2026, 9, 13, 1, 0, tzinfo=timezone.utc)

    def test_live_position_im_live_lauf_ordert_markt_verkauf(self):
        fake = KrakenAttrappe()                     # Stop/Ziel noch offen
        z = {"position": _pos_live()}
        journal_rec = []
        with patch.object(handeln, "kraken", fake), \
                patch.object(handeln, "journal",
                             lambda *f: journal_rec.append(f)), \
                patch("sys.stdout", new_callable=io.StringIO):
            veraendert, grund = handeln.pruefe_ausstiege(
                z, _w_offen(), jetzt=self.JETZT, live=True)
        self.assertTrue(veraendert)
        self.assertEqual(grund, "stop")
        self.assertIn(("verkauf", "ETHUSD", 5.0, True), fake.rufe,
                      "echter Markt-Close nur fuer eine live Position")
        # Schutzauftraege erst abraeumen, dann verkaufen.
        self.assertLess(fake.rufe.index(("storno", "TX-STOP")),
                        fake.rufe.index(("verkauf", "ETHUSD", 5.0, True)))
        # Lokal gebucht.
        self.assertEqual(z["position"]["ausgang"], "stop")
        self.assertTrue(journal_rec)

    def test_boerse_hat_schon_geschlossen_keine_zweite_order(self):
        fake = KrakenAttrappe(stop_gefuellt=True)   # Boersen-Stop hat verkauft
        z = {"position": _pos_live()}
        with patch.object(handeln, "kraken", fake), \
                patch.object(handeln, "journal", lambda *f: None), \
                patch("sys.stdout", new_callable=io.StringIO):
            veraendert, grund = handeln.pruefe_ausstiege(
                z, _w_offen(), jetzt=self.JETZT, live=True)
        self.assertTrue(veraendert)
        self.assertEqual(grund, "stop (boerse)")
        # KEINE Marktorder: die wuerde ueberverkaufen und einen Short eroeffnen.
        self.assertNotIn(("verkauf", "ETHUSD", 5.0, True), fake.rufe)

    def test_boerse_nicht_lesbar_keine_order_ungeklaert(self):
        fake = KrakenAttrappe(lesefehler=True)
        z = {"position": _pos_live()}
        with patch.object(handeln, "kraken", fake), \
                patch.object(handeln, "journal", lambda *f: None), \
                patch("sys.stdout", new_callable=io.StringIO):
            veraendert, grund = handeln.pruefe_ausstiege(
                z, _w_offen(), jetzt=self.JETZT, live=True)
        self.assertFalse(veraendert, "bei Ungewissheit wird nicht gebucht")
        self.assertTrue(z["position"]["exit_ungeklaert"])
        self.assertEqual([r for r in fake.rufe if r[0] == "verkauf"], [],
                         "keine Marktorder bei Ungewissheit")

    def test_live_position_im_papier_lauf_keine_order_kein_schluss(self):
        """Ein PAPIERLauf schliesst eine echte Position nicht (Boerse schuetzt)."""
        fake = KrakenAttrappe()
        z = {"position": _pos_live()}
        with patch.object(handeln, "kraken", fake), \
                patch("sys.stdout", new_callable=io.StringIO):
            veraendert, grund = handeln.pruefe_ausstiege(
                z, _w_offen(), jetzt=self.JETZT, live=False)
        self.assertFalse(veraendert)
        self.assertEqual(fake.rufe, [], "Papierlauf darf keine Boerse anrufen")
        self.assertIsNotNone(z["position"])

    def test_papier_position_im_papier_lauf_bleibt_reine_buchung(self):
        fake = KrakenAttrappe()
        z = {"position": _pos_live(modus=None)}     # nicht live markiert
        z["position"].pop("kauf_txid")
        z["position"].pop("stop_txid")
        z["position"].pop("tp_txid")
        journal_rec = []
        with patch.object(handeln, "kraken", fake), \
                patch.object(handeln, "journal",
                             lambda *f: journal_rec.append(f)), \
                patch("sys.stdout", new_callable=io.StringIO):
            veraendert, grund = handeln.pruefe_ausstiege(
                z, _w_offen(), jetzt=self.JETZT, live=False)
        self.assertTrue(veraendert)
        self.assertEqual([r for r in fake.rufe if r[0] == "verkauf"], [],
                         "Papierpfad ist reine Buchoperation")
        self.assertTrue(journal_rec)


class AbgleichRundeTest(unittest.TestCase):
    """(3) Buch gegen Boerse fuer Live-Positionen, vor den Ausstiegen."""

    def test_stop_ausgeloest_an_boerse_wird_nachgezogen(self):
        fake = KrakenAttrappe(stop_gefuellt=True)
        z = {"position": _pos_live()}
        journal_rec = []
        with patch.object(handeln, "kraken", fake), \
                patch.object(handeln, "journal",
                             lambda *f: journal_rec.append(f)), \
                patch("sys.stdout", new_callable=io.StringIO):
            bilanz = handeln._abgleich_runde(z, _w_offen())
        self.assertTrue(bilanz["ausgebucht"])
        self.assertIsNone(z.get("position"),
                          "an der Boerse weg - nicht im Buch behalten")
        self.assertEqual([r for r in fake.rufe if r[0] == "verkauf"], [],
                         "keine Marketorder - ein gefuellter Stop hat verkauft")
        self.assertTrue(any("stop (boerse)" in str(f) for f in journal_rec))

    def test_stop_offen_position_bleibt(self):
        fake = KrakenAttrappe()                     # nichts gefuellt
        z = {"position": _pos_live()}
        with patch.object(handeln, "kraken", fake), \
                patch("sys.stdout", new_callable=io.StringIO):
            bilanz = handeln._abgleich_runde(z, _w_offen())
        self.assertFalse(bilanz["ausgebucht"])
        self.assertIsNotNone(z["position"])
        self.assertNotIn("verkauf", [r[0] for r in fake.rufe])

    def test_papier_position_wird_nicht_geprueft(self):
        fake = KrakenAttrappe()
        z = {"position": _pos_live(modus=None)}
        with patch.object(handeln, "kraken", fake), \
                patch("sys.stdout", new_callable=io.StringIO):
            bilanz = handeln._abgleich_runde(z, _w_offen())
        self.assertIsNone(bilanz)
        self.assertEqual(fake.rufe, [])

    def test_boerse_nicht_lesbar_keine_aussage(self):
        fake = KrakenAttrappe(lesefehler=True)
        z = {"position": _pos_live()}
        with patch.object(handeln, "kraken", fake), \
                patch("sys.stdout", new_callable=io.StringIO):
            bilanz = handeln._abgleich_runde(z, _w_offen())
        self.assertIsNone(bilanz)
        self.assertIsNotNone(z["position"], "keine Aussage statt geratener Zahl")


class ShortVerweigerungLaufTest(unittest.TestCase):
    """(d) Ein Short-Signal wird im Live-Pfad verweigert - nie eine Order."""

    def _k(self, hh, mm, o, h, l, c):
        return {"zeit": datetime(2026, 9, 13, hh, mm, tzinfo=timezone.utc),
                "o": o, "h": h, "l": l, "c": c}

    def _short_kerzen(self):
        return [self._k(0, 0, 99, 100, 98, 99.5),
                self._k(0, 15, 99.5, 100, 98, 99.8),
                self._k(0, 30, 98.0, 98.1, 97.0, 97.4)]  # Schluss < Tief -> short

    def test_live_short_signal_kein_einstieg_keine_order(self):
        def _verboten(*a, **k):
            raise AssertionError("Short darf keine Order an die Boerse legen")
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
                        patch.object(handeln.kraken, "schluessel_vorhanden",
                                     lambda: True), \
                        patch.object(handeln.kraken, "paar_info",
                                     lambda p: {"mengen_stellen": 8,
                                                "preis_stellen": 4}), \
                        patch.object(handeln.kraken, "markt_kauf", _verboten), \
                        patch.object(handeln.kraken, "markt_verkauf", _verboten), \
                        patch.object(handeln.kraken, "stop_setzen", _verboten), \
                        patch.object(handeln.kraken, "take_profit_setzen",
                                     _verboten), \
                        patch.object(handeln, "_jetzt", lambda: datetime(
                            2026, 9, 13, 0, 45, tzinfo=timezone.utc)), \
                        patch.object(handeln, "_letzter_kurs",
                                     lambda w_, k_: 97.4):
                    with redirect_stdout(io.StringIO()):
                        meldungen = handeln.lauf("live")
            finally:
                handeln.kerzen_quelle = None
            self.assertTrue(any("kein Einstieg" in m for m in meldungen),
                            meldungen)
            self.assertFalse(any("EINSTIEG (LIVE)" in m for m in meldungen))
            nachher = json.loads(zpfad.read_text(encoding="utf-8"))
            self.assertIsNone(nachher.get("position"),
                              "verweigerter Short darf keine Position machen")


if __name__ == "__main__":
    unittest.main()
