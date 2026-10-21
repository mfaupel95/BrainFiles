"""Tests fuer die kerzenabhaengige Todesgrenze der omnitrade-order-wache.

Befund 11.10.2026: live.json (der Hauptlauf) laeuft auf 1d-Kerzen und schreibt
die Statusdatei nur beim Kerzenabschluss. Die feste TOT_MINUTEN=45 erklaerte
einen gesunden Lauf (692 min alt) fuer tot, waehrend die autoritative Pruefung
(omnitrade_bridge.lage) die Grenze kerzenabhaengig auf 60 h setzt und gesund
meldet. Darum waechst die Grenze jetzt mit dem Kerzenabstand aus der Datei.
Geprueft wird die REGEL, nicht ein Tageswert.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "omnitrade_order_wache", HIER / "omnitrade-order-wache.py")
ow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ow)


def _daten(abstand_min, anz_kerzen=20):
    """Statusdatei-Inhalt mit `anz_kerzen` Kerzen im Abstand `abstand_min`."""
    aus = []
    basis = 1767225600000  # willkuerlicher Start
    for i in range(anz_kerzen):
        aus.append({"time_ms": basis + i * abstand_min * 60_000,
                    "close": 100.0})
    return {"state": "running", "pid": 46064, "recent_candles": aus}


class AltersgrenzeTest(unittest.TestCase):

    def test_taegliche_kerzen_geben_60h(self):
        """1d-Kerzen -> Grenze 60 h (2,5 * 24 h), ein 10 h alter Lauf ist gesund."""
        d = _daten(24 * 60)
        g = ow.altersgrenze_min(d)
        self.assertGreaterEqual(g, 3600, "1d-Kerzen muessen > 45 min erlauben")
        alter_min = 10 * 60
        self.assertGreater(g, alter_min,
                           "10 h Alter darf einen 1d-Lauf nicht fuer tot erklaeren")

    def test_15min_kerzen_fallen_auf_grenze(self):
        """15-min-Kerzen -> Grenze bleibt beim 45-min-Floor."""
        d = _daten(15)
        g = ow.altersgrenze_min(d)
        self.assertEqual(g, ow.TOT_MINUTEN)
        self.assertLess(g, 2 * 60)

    def test_ohne_kerzen_fallback_45(self):
        """Zu wenige/noch keine Kerzen -> Sicherheits-Fallback 45 min."""
        self.assertEqual(ow.altersgrenze_min({}), ow.TOT_MINUTEN)
        self.assertEqual(ow.altersgrenze_min({"recent_candles": []}),
                         ow.TOT_MINUTEN)
        self.assertEqual(ow.altersgrenze_min({"recent_candles": [{"time_ms": 1}]}),
                         ow.TOT_MINUTEN)


class VergleicheTest(unittest.TestCase):

    def test_taeglicher_lauf_wird_nicht_fuer_tot_erklaert(self):
        """Kernfall 11.10.2026: 1d-Lauf, ~10 h alt -> NICHT als tot melden."""
        alt = {"pid": 999, "state": "running", "orders_placed": 0,
               "net_quantity": 0.0, "last_signal": "buy", "letzte_order": {},
               "aktualisiert": ow.zeit()}
        neu = dict(alt)
        neu["aktualisiert"] = alt["aktualisiert"] - 10 * 3600  # 10 h alt
        g = ow.altersgrenze_min(_daten(24 * 60))
        zeilen = ow.vergleiche(alt, neu, Path("live.json"), g)
        self.assertEqual(zeilen, [],
                         "ein gesunder taeglicher Lauf darf nicht als tot gelten")

    def test_15min_lauf_der_steht_wird_gemeldet(self):
        """Kurzer Takt, Lauf steht 2 h -> echter Befund wird weiterhin gemeldet."""
        alt = {"pid": 1, "state": "running", "orders_placed": 0,
               "net_quantity": 0.0, "last_signal": "keep", "letzte_order": {},
               "aktualisiert": ow.zeit()}
        neu = dict(alt)
        neu["aktualisiert"] = alt["aktualisiert"] - 2 * 3600  # 2 h alt
        g = ow.altersgrenze_min(_daten(15))  # 45-min-Floor
        zeilen = ow.vergleiche(alt, neu, Path("live_x.json"), g)
        self.assertTrue(any("kein Lebenszeichen" in z for z in zeilen),
                        "ein 2 h stehender 15-min-Lauf muss gemeldet werden")


if __name__ == "__main__":
    unittest.main(verbosity=2)
