"""T-312: futures_probe darf keine Position ohne Schutz-Stop offen lassen.

Zwei Regeln, beide mit Gegenprobe:
1. fuelungen() faengt eine /fills-Exception und gibt leere Liste zurueck
   (vorher propagierte sie aus lauf() und der Notausstieg wurde nie erreicht).
2. Bei nicht lesbarer Kauf-Fuellung wird der Verkauf (reduceOnly) trotzdem
   versucht - der Verkauf haengt nicht am Fill-Polling. Erst wenn auch der
   Verkauf scheitert, greift der Schutz-Stop.

Direkt ausfuehrbar: python test_futures_probe_t312.py
"""
import os
import sys
import unittest
from unittest import mock

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))   # nautilus_kraken/ (futures_probe.py)
import futures_probe as fp  # noqa: E402


def _alle(mocks):
    """Kontextmanager, der mehrere Mocks gleichzeitig aktiviert."""
    import contextlib
    return contextlib.ExitStack() if False else _Stack(mocks)


class _Stack:
    def __init__(self, mocks):
        self.mocks = mocks
        self._stack = None
        self._aktiv = []

    def __enter__(self):
        import contextlib
        self._stack = contextlib.ExitStack()
        for m in self.mocks:
            self._aktiv.append(self._stack.enter_context(m))
        return self._aktiv

    def __exit__(self, *exc):
        return self._stack.__exit__(*exc)


class FuelungenTest(unittest.TestCase):
    """Regel 1: eine /fills-Exception ist 'keine Fuellung', kein Absturz."""

    def test_exception_wird_als_leere_liste_behandelt(self):
        with mock.patch.object(fp.kf, "_roh",
                               side_effect=RuntimeError("authenticationError")):
            ergebnis = fp.fuelungen("ord-1", fp.datetime.now(fp.timezone.utc),
                                    frist_s=1)
        self.assertEqual(ergebnis, [])

    def test_erfolg_liefert_die_eigene_fuellung(self):
        def roh(pfad):
            return {"fills": [{"order_id": "ord-1", "price": "1.0",
                               "size": "1"}]}
        with mock.patch.object(fp.kf, "_roh", side_effect=roh):
            ergebnis = fp.fuelungen("ord-1", fp.datetime.now(fp.timezone.utc),
                                    frist_s=1)
        self.assertEqual(len(ergebnis), 1)


class VerkaufUnabhaengigTest(unittest.TestCase):
    """Regel 2: bei unlesbarer Kauf-Fuellung wird der Verkauf versucht."""

    def _lage(self):
        return {"kurs": 100.0, "frei": 1000.0, "positionen": [],
                "orders": [], "nominal": 8.0, "einschuss": 1.0}

    def _lage_mocks(self):
        """Lage-Abhaengigkeiten: Kurs/Guthaben/Positionen/Orders/Einschuss."""
        return [
            mock.patch.object(fp.kf, "letzter_kurs", return_value=100.0),
            mock.patch.object(fp.kf, "guthaben", return_value=1000.0),
            mock.patch.object(fp.kf, "offene_positionen", return_value=[]),
            mock.patch.object(fp.kf, "offene_orders", return_value=[]),
            mock.patch.object(fp.kf, "einschuss", return_value=1.0),
            mock.patch.object(fp.kf, "instrument",
                              return_value={"contractSize": "1",
                                            "tickSize": "0.01"}),
        ]

    def test_verkauf_wird_bei_unlesbarer_kauffuellung_versucht(self):
        aufrufe = []
        fills_zaehler = {"n": 0}

        def roh(pfad):
            # Erster /fills-Aufruf (Kauf): leer - simuliert authenticationError
            # bzw. leere Antwort. Der Verkauf muss trotzdem laufen. Zweiter
            # /fills-Aufruf (Verkauf): liefert eine Fuellung.
            if "/fills" in pfad:
                fills_zaehler["n"] += 1
                if fills_zaehler["n"] == 1:
                    return {"fills": []}
                return {"fills": [{"order_id": "verkauf-id",
                                   "price": "100.0", "size": "8"}]}
            return {"fills": []}

        def order(body):
            aufrufe.append(body)
            return "verkauf-id"

        mocks = self._lage_mocks() + [
            mock.patch.object(fp.kf, "_roh", side_effect=roh),
            mock.patch.object(fp.kf, "_order_aufgeben", side_effect=order),
        ]
        with _alle(mocks):
            rc = fp.lauf(8, anwenden=True)
        # Der Verkauf (reduceOnly) wurde gesendet, obwohl die Kauf-Fuellung
        # nie lesbar war.
        self.assertTrue(any(b.get("side") == "sell" and b.get("reduceOnly")
                            for b in aufrufe),
                        "Verkauf muss unabhaengig vom Kauf-Fill-Polling laufen")
        self.assertEqual(rc, 0)

    def test_schutz_stop_wenn_auch_verkauf_scheitert(self):
        def roh(pfad):
            return {"fills": []}

        def order(body):
            # Kauf geht durch, nur der Verkauf scheitert.
            if body.get("side") == "buy":
                return "kauf-id"
            raise RuntimeError("Verkauf abgelehnt")

        mocks = self._lage_mocks() + [
            mock.patch.object(fp.kf, "_roh", side_effect=roh),
            mock.patch.object(fp.kf, "_order_aufgeben", side_effect=order),
            mock.patch.object(fp.kf, "stop_setzen",
                              return_value="stop-kennung"),
        ]
        with _alle(mocks) as alle:
            rc = fp.lauf(8, anwenden=True)
            stop = alle[-1]
        stop.assert_called_once()
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
