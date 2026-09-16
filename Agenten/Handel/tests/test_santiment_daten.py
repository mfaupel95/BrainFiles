"""Tests fuer santiment_daten.py - reine Rechnung, KEIN Netz.

Der Endpunkt wird nie wirklich gerufen: `graphql` bzw. `urlopen` werden durch
Doubles ersetzt. Der Fenster-Parser wird gegen die ECHTE Fehlermeldung der API
geprueft (Wortlaut am 16.09.2026 abgeschrieben) - dort steckt die Grenze, und
genau die muss richtig herauskommen.

Aufruf aus `Agenten/Handel/tests`:
    ..\\scanner\\.venv\\Scripts\\python.exe -m unittest test_santiment_daten
"""
import contextlib
import io
import json
import os
import sys
import unittest
from unittest import mock

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import santiment_daten as sd  # noqa: E402

# Wortlaut der API, live abgeschrieben am 16.09.2026:
FENSTER_FEHLER = (
    "Both `from` and `to` parameters are outside the allowed interval you can "
    "query social_volume_total with your current subscription SANAPI FREE. "
    "Upgrade to a higher tier in order to access more data.\n\n"
    "Allowed time restrictions:\n"
    "  - `from` - 2025-09-16 15:05:01.934532Z\n"
    "  - `to` - 2026-08-17 15:05:01.934532Z\n"
)


class FensterTest(unittest.TestCase):

    def test_liest_die_grenzen_aus_der_meldung(self):
        with mock.patch.object(sd, "metrik",
                               side_effect=sd.SantimentFehler(FENSTER_FEHLER)):
            fenster, fehler = sd.erlaubtes_fenster("social_volume_total")
        self.assertIsNone(fehler)
        self.assertEqual(fenster, ("2025-09-16 15:05:01.934532Z",
                                   "2026-08-17 15:05:01.934532Z"))

    def test_fremde_meldung_wird_nicht_als_fenster_gedeutet(self):
        with mock.patch.object(sd, "metrik",
                               side_effect=sd.SantimentFehler("irgendwas anderes")):
            fenster, fehler = sd.erlaubtes_fenster("mvrv_usd")
        self.assertIsNone(fenster)
        self.assertIn("irgendwas anderes", fehler)

    def test_offenes_fenster_gilt_als_frei(self):
        """Kein Fehler = die Stufe darf beliebig weit zurueck (Schluessel aktiv)."""
        with mock.patch.object(sd, "metrik", return_value=[("2026-09-01T00:00:00Z", 1.0)]):
            fenster, meldung = sd.erlaubtes_fenster("daily_active_addresses")
        self.assertEqual(fenster, (None, None))
        self.assertIn("offen", meldung)


class MetrikTest(unittest.TestCase):

    def test_leere_reihe_ist_kein_fehler(self):
        """Ausserhalb des Fensters liefert die API eine leere Reihe - kein Absturz."""
        antwort = {"getMetric": {"timeseriesData": None}}
        with mock.patch.object(sd, "graphql", return_value=antwort):
            self.assertEqual(sd.metrik("social_volume_total", "bitcoin", "a", "b"), [])

    def test_reihe_wird_zu_tupeln(self):
        antwort = {"getMetric": {"timeseriesData": [
            {"datetime": "2026-09-01T00:00:00Z", "value": 676374.0},
            {"datetime": "2026-09-02T00:00:00Z", "value": 650981.0}]}}
        with mock.patch.object(sd, "graphql", return_value=antwort):
            reihe = sd.metrik("daily_active_addresses", "bitcoin", "a", "b")
        self.assertEqual(reihe[0], ("2026-09-01T00:00:00Z", 676374.0))
        self.assertEqual(len(reihe), 2)


class GraphqlTest(unittest.TestCase):

    class _Antwort(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _urlopen_mit(self, rumpf):
        rohdaten = json.dumps(rumpf).encode("utf-8")
        return mock.Mock(return_value=self._Antwort(rohdaten))

    def test_errors_werden_zur_ausnahme(self):
        rumpf = {"errors": [{"message": "Both `from` and `to` parameters are outside …"}],
                 "data": {"getMetric": {"timeseriesData": None}}}
        with mock.patch.object(sd.urllib.request, "urlopen", self._urlopen_mit(rumpf)):
            with self.assertRaises(sd.SantimentFehler) as ctx:
                sd.graphql("{ __typename }")
        self.assertIn("outside", str(ctx.exception))

    def test_data_kommt_zurueck(self):
        rumpf = {"data": {"__schema": {"queryType": {"name": "RootQueryType"}}}}
        with mock.patch.object(sd.urllib.request, "urlopen", self._urlopen_mit(rumpf)):
            d = sd.graphql("{ __schema { queryType { name } } }")
        self.assertEqual(d["__schema"]["queryType"]["name"], "RootQueryType")

    def test_ohne_schluessel_kein_authorization_kopf(self):
        rumpf = {"data": {"ok": True}}
        with mock.patch.object(sd, "schluessel", return_value=""):
            with mock.patch.object(sd.urllib.request, "urlopen",
                                   self._urlopen_mit(rumpf)) as u:
                sd.graphql("{ __typename }")
        anfrage = u.call_args[0][0]
        self.assertNotIn("Authorization", anfrage.headers)

    def test_mit_schluessel_wird_apikey_gesendet(self):
        rumpf = {"data": {"ok": True}}
        with mock.patch.object(sd, "schluessel", return_value="GEHEIM123"):
            with mock.patch.object(sd.urllib.request, "urlopen",
                                   self._urlopen_mit(rumpf)) as u:
                sd.graphql("{ __typename }")
        anfrage = u.call_args[0][0]
        self.assertEqual(anfrage.headers.get("Authorization"), "Apikey GEHEIM123")


class ProbeTest(unittest.TestCase):

    def test_probe_zaehlt_die_beantworteten_abfragen(self):
        def fake_metrik(metric, slug, von, bis, interval="1d"):
            if metric == "social_volume_total":
                raise sd.SantimentFehler(FENSTER_FEHLER)
            return [("2026-09-08T00:00:00Z", 597207.0)]

        with mock.patch.object(sd, "schluessel", return_value=""), \
             mock.patch.object(sd, "graphql",
                               return_value={"__schema": {"queryType": {"name": "RootQueryType"}}}), \
             mock.patch.object(sd, "projekte", return_value=[("bitcoin", "Bitcoin", "BTC", 1e12)]), \
             mock.patch.object(sd, "metrik", side_effect=fake_metrik), \
             mock.patch.object(sd, "trendende_woerter", return_value=[("ukraine", 12.0)]):
            puffer = io.StringIO()
            with contextlib.redirect_stdout(puffer):
                code = sd.probe()
        bericht = puffer.getvalue()
        self.assertEqual(code, 0, "Probe muss gruen sein, wenn die Abfragen laufen")
        self.assertIn("5 von 5", bericht)
        self.assertIn("anonym", bericht)


if __name__ == "__main__":
    unittest.main(verbosity=2)
