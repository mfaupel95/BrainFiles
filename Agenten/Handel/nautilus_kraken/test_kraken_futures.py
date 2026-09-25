"""Tests fuer den Kraken-FUTURES-Orderweg (kraken_futures.py).

Kein Netz, keine echten Orders: Der Transport (urllib) wird ersetzt und
mitgeschrieben, geprueft wird die FORM der Order - orderType, side, size,
reduceOnly, stopPrice - und die Weiche in kraken_rest.py.

Warum das zaehlt: Spot und Futures sind bei Kraken zwei Dienste. Eine
Futures-Order mit Spot-Vorzeichen (BTC-Menge statt Kontrakte, keine
reduceOnly-Kennzeichnung) wird von der Boerse entweder abgelehnt oder -
schlimmer - als neue Position eroeffnet.

Aufruf:  ..\\nautilus\\.venv\\Scripts\\python.exe test_kraken_futures.py
"""

import base64
import hashlib
import hmac
import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import kraken_futures as kf        # noqa: E402
import handeln                     # noqa: E402

KEY = "dGVzdC1rZXk="
SECRET = base64.b64encode(b"geheimer-schluessel-fuer-den-test").decode()


class FakeAntwort:
    def __init__(self, nutzlast):
        self._daten = json.dumps(nutzlast).encode()

    def read(self):
        return self._daten

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TransportTest(unittest.TestCase):
    """Kopf und Signatur - der Teil, an dem es 24.09.2026 wirklich lag."""

    def setUp(self):
        self.aufrufe = []

        def falscher_aufruf(req, timeout=None):
            self.aufrufe.append(req)
            if "/sendorder" in req.full_url:
                return FakeAntwort({"result": "success", "sendStatus": {
                    "status": "placed", "order_id": "OID-1"}})
            return FakeAntwort({"result": "success", "instruments": []})

        self.p = patch("kraken_futures.urllib.request.urlopen", falscher_aufruf)
        self.p.start()
        self.addCleanup(self.p.stop)
        self.env = patch.dict(os.environ, {"KRAKEN_FUTURE_API_KEY": KEY,
                                           "KRAKEN_FUTURE_API_SECRET": SECRET})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_kopf_traegt_die_drei_futures_felder(self):
        kf._roh("/accounts")
        kopf = self.aufrufe[0].headers
        for feld in ("Apikey", "Nonce", "Authent"):
            self.assertIn(feld, kopf, "Futures braucht %s im Kopf" % feld)
        self.assertEqual(kopf["Apikey"], KEY)

    def test_signaturpfad_ohne_derivatives(self):
        """Gemessen 24.09.2026: mit /derivatives im Pfad -> Authentication error."""
        self.assertEqual(kf.SIGNATUR_PRAEFIX, "/api/v3")
        self.assertNotIn("/derivatives", kf.SIGNATUR_PRAEFIX)
        self.assertTrue(kf.BASIS.endswith("/derivatives/api/v3"))
        self.assertEqual(kf._signatur("/accounts", "", "1234567890"),
                         kf._signatur("/accounts", "", "1234567890"))

    def test_signatur_nachrechenbar(self):
        """Unabhaengig nachgerechnet, nicht die eigene Funktion befragt."""
        nonce = "1234567890"
        nachricht = ("symbol=PF_XBTUSD" + nonce + "/api/v3" + "/sendorder").encode()
        mac = hmac.new(base64.b64decode(SECRET),
                       hashlib.sha256(nachricht).digest(), hashlib.sha512)
        erwartet = base64.b64encode(mac.digest()).decode()
        self.assertEqual(kf._signatur("/sendorder", "symbol=PF_XBTUSD", nonce),
                         erwartet)

    def test_lesende_aufrufe_sind_get(self):
        """Ein Koerper am GET-Aufruf machte ihn zum POST -> HTTP 404."""
        kf._roh("/accounts")
        self.assertIsNone(self.aufrufe[0].data)
        self.assertEqual(self.aufrufe[0].get_method(), "GET")

    def test_order_ist_post(self):
        kf._order_aufgeben({"orderType": "mkt", "symbol": "PF_XBTUSD",
                            "side": "buy", "size": 1})
        self.assertEqual(self.aufrufe[0].get_method(), "POST")
        self.assertEqual(self.aufrufe[0].data,
                         b"orderType=mkt&symbol=PF_XBTUSD&side=buy&size=1")

    def test_ohne_schluessel_klare_meldung(self):
        with patch.object(kf, "schluessel_vorhanden", return_value=False):
            with self.assertRaises(kf.KrakenFuturesFehler) as ctx:
                kf._roh("/accounts")
        self.assertIn("KRAKEN_FUTURE_API_KEY", str(ctx.exception))


class RechnenTest(unittest.TestCase):
    """BTC-Menge -> Kontrakte, tickSize-Rundung."""

    def test_kontrakt_ist_eine_basis_einheit(self):
        """GEMESSEN 25.09.2026: 1 Kontrakt = 1 Einheit der BASIS, nicht 1 USD.

        Belegte Gegenprobe am echten Konto: 1 Kontrakt PF_NEARUSD bei 4,5517 USD
        belegte 0,4548 USD Marge (10 % Einschuss) - waere 1 Kontrakt = 1 USD,
        haetten es 0,10 USD sein muessen. Und PF_XBTUSD wurde mit 141,59 USD
        frei abgelehnt: 1 Kontrakt = 1 BTC = rund 8.450 USD Einschuss.
        Die frueher hier behauptete Formel (menge x kurs) war falsch - sie
        haette aus einem Kopiersignal von 0,0001 BTC eine 0,001-BTC-Order
        gemacht, die an der Boerse nie durchgeht.
        """
        self.assertEqual(kf.kontrakte("PF_NEARUSD", 3), 3)
        self.assertEqual(kf.kontrakte("PF_XBTUSD", 0.5), 1)      # gerundet, mind. 1

    def test_kontrakte_nie_null(self):
        self.assertEqual(kf.kontrakte("PF_XBTUSD", 0.0000001), 1)
        self.assertEqual(kf.kontrakte("PF_NEARUSD", 0), 1)

    def test_einschuss_rechnet_den_gemessenen_fall_nach(self):
        """10 % Einschuss (Europa, retail) - die Zahl, die am Konto stand."""
        with patch.object(kf, "instrument", return_value={
                "marginSchedules": {"europa": {"retail": [
                    {"numNonContractUnits": 0.0, "initialMargin": 0.1,
                     "maintenanceMargin": 0.05}]}}}):
            self.assertAlmostEqual(kf.einschuss("PF_NEARUSD", 1, kurs=4.5517), 0.45517,
                                   places=5)
            self.assertAlmostEqual(kf.einschuss("PF_XBTUSD", 1, kurs=84485.0), 8448.5,
                                   places=1)

    def test_einschuss_ohne_plan_nimmt_den_hoechsten_satz(self):
        """Kein Margenplan im Record (aeltere Form): konservativ rechnen."""
        with patch.object(kf, "instrument", return_value={
                "retailMarginLevels": [{"numNonContractUnits": 0.0,
                                        "initialMargin": 0.01},
                                       {"numNonContractUnits": 1000.0,
                                        "initialMargin": 0.5}]}):
            self.assertAlmostEqual(kf.einschuss("PF_XBTUSD", 1, kurs=100.0), 1.0,
                                   places=6)

    def test_handelbar_nennt_den_grund(self):
        """Der Kurs wird gepatcht: sonst haengt der Text am LIVE-Kurs und der Test
        kippt bei jeder Bewegung - ein Test gegen einen Zustand statt eine Regel."""
        with patch.object(kf, "instrument", return_value={
                "marginSchedules": {"europa": {"retail": [
                    {"numNonContractUnits": 0.0, "initialMargin": 0.1}]}}}),              patch.object(kf, "letzter_kurs", return_value=84485.0):
            grund = kf.handelbar("PF_XBTUSD", 1, frei=141.58)
            self.assertEqual(grund, "1 Kontrakt PF_XBTUSD braucht 8448.50 USD "
                                    "Einschuss, frei sind 141.58 USD")
            self.assertIsNone(kf.handelbar("PF_XBTUSD", 1, frei=9000.0))

    def test_preis_gerundet_auf_tick(self):
        with patch.object(kf, "instrument", return_value={"tickSize": 1}):
            # 'auf' rundet von der Null weg (Long-Stop nie tiefer als gerechnet)
            self.assertEqual(kf.preis_gerundet("PF_XBTUSD", 78000.4), "78001")
            self.assertEqual(kf.preis_gerundet("PF_XBTUSD", 78000.4, "ab"), "78000")
            self.assertEqual(kf.preis_gerundet("PF_XBTUSD", 78000.6), "78001")
            self.assertEqual(kf.preis_gerundet("PF_XBTUSD", 78000.6, "ab"), "78000")

    def test_preis_gerundet_ohne_wissenschaftliche_schreibweise(self):
        with patch.object(kf, "instrument", return_value={"tickSize": 0.5}):
            self.assertEqual(kf.preis_gerundet("PF_NEARUSD", 4.6), "5.0")


class OrderformTest(unittest.TestCase):
    """Die FORM der Order - hier entscheidet sich, ob es ein Ausstieg ist."""

    def setUp(self):
        self.gesendet = []
        p = patch.object(kf, "_order_aufgeben",
                         side_effect=lambda werte: self.gesendet.append(werte) or "ID-1")
        p.start()
        self.addCleanup(p.stop)
        p2 = patch.object(kf, "kontrakte", return_value=8)
        p2.start()
        self.addCleanup(p2.stop)

    def test_marktkauf_ist_eine_marktorder(self):
        kf.markt_kauf("PF_XBTUSD", 0.0001, echt=True)
        self.assertEqual(self.gesendet[0], {"orderType": "mkt",
                                            "symbol": "PF_XBTUSD",
                                            "side": "buy", "size": 8})

    def test_verkauf_gegen_long_ist_reduce_only(self):
        with patch.object(kf, "offene_positionen",
                          return_value=[{"symbol": "PF_XBTUSD", "side": "long"}]):
            kf.markt_verkauf("PF_XBTUSD", 0.0001, echt=True)
        self.assertEqual(self.gesendet[0]["side"], "sell")
        self.assertEqual(self.gesendet[0]["reduceOnly"], "true")

    def test_verkauf_ohne_bestand_ist_nicht_reduce_only(self):
        with patch.object(kf, "offene_positionen", return_value=[]):
            kf.markt_verkauf("PF_XBTUSD", 0.0001, echt=True)
        self.assertNotIn("reduceOnly", self.gesendet[0])

    def test_stop_ist_eigene_reduce_only_order(self):
        with patch.object(kf, "offene_positionen",
                          return_value=[{"symbol": "PF_XBTUSD", "side": "long"}]), \
             patch.object(kf, "preis_gerundet", return_value="78000"):
            kf.stop_setzen("PF_XBTUSD", 0.0001, 78000.4, echt=True)
        self.assertEqual(self.gesendet[0]["orderType"], "stp")
        self.assertEqual(self.gesendet[0]["side"], "sell")
        self.assertEqual(self.gesendet[0]["reduceOnly"], "true")
        self.assertEqual(self.gesendet[0]["stopPrice"], "78000")

    def test_stop_fuer_short_kauft_zurueck(self):
        with patch.object(kf, "offene_positionen",
                          return_value=[{"symbol": "PF_XBTUSD", "side": "short"}]), \
             patch.object(kf, "preis_gerundet", return_value="86000"):
            kf.stop_setzen("PF_XBTUSD", 0.0001, 85999.5, echt=True)
        self.assertEqual(self.gesendet[0]["side"], "buy")

    def test_ohne_echt_wird_nichts_gesendet(self):
        kf.markt_kauf("PF_XBTUSD", 0.0001)
        kf.markt_verkauf("PF_XBTUSD", 0.0001)
        kf.stop_setzen("PF_XBTUSD", 0.0001, 78000)
        self.assertEqual(self.gesendet, [])


class GuthabenTest(unittest.TestCase):
    def test_guthaben_liest_cash_konto(self):
        antwort = {"result": "success",
                   "accounts": {"cash": {"type": "cashAccount",
                                         "balances": {"usd": 12.5,
                                                      "eur": 0.0}}}}
        with patch.object(kf, "_roh", return_value=antwort):
            self.assertEqual(kf.guthaben(), 12.5)
            self.assertEqual(kf.guthaben("eur"), 0.0)

    def test_leeres_konto_ist_null_nicht_fehler(self):
        antwort = {"result": "success",
                   "accounts": {"cash": {"type": "cashAccount", "balances": {}}}}
        with patch.object(kf, "_roh", return_value=antwort):
            self.assertEqual(kf.guthaben(), 0.0)

    def test_guthaben_liest_das_flex_konto(self):
        """Gemessen 25.09.2026 am echten Konto: multiCollateral legt das Geld in
        'flex', 'cash.balances' bleibt 0,0 - die alte Lesart meldete 0 USD,
        obwohl 141,59 USD verfuegbar waren."""
        antwort = {"result": "success", "accounts": {
            "cash": {"type": "cashAccount", "balances": {"usd": 0, "eur": 0}},
            "flex": {"type": "multiCollateralMarginAccount",
                     "availableMargin": 141.5931, "balanceValue": 141.9984,
                     "collateralValue": 141.5931,
                     "currencies": {"USD": {"quantity": 8.8926, "available": 8.8926},
                                    "EUR": {"quantity": 45.7427, "available": 45.7427},
                                    "USDC": {"quantity": 81.0838, "available": 81.0838}}}}}
        with patch.object(kf, "_roh", return_value=antwort):
            self.assertAlmostEqual(kf.guthaben(), 141.5931, places=4)
            self.assertAlmostEqual(kf.guthaben("EUR"), 45.7427, places=4)
            self.assertAlmostEqual(kf.guthaben("usdc"), 81.0838, places=4)
            self.assertEqual(kf.guthaben("gbp"), 0.0)

    def test_flex_ohne_availablemargin_faellt_auf_usd_zurueck(self):
        antwort = {"result": "success", "accounts": {
            "flex": {"currencies": {"USD": {"available": 3.25}}}}}
        with patch.object(kf, "_roh", return_value=antwort):
            self.assertAlmostEqual(kf.guthaben(), 3.25, places=4)

    def test_leeres_flex_ist_null_nicht_fehler(self):
        antwort = {"result": "success", "accounts": {"flex": {"currencies": {}}}}
        with patch.object(kf, "_roh", return_value=antwort):
            self.assertEqual(kf.guthaben(), 0.0)


class SperrenketteTest(unittest.TestCase):
    """Futures besichert aus dem Verrechnungskonto: ohne freies Guthaben keine Order."""

    def test_ohne_usd_gesperrt(self):
        w = {"handel_erlaubt": True, "freigabe": {"erfuellt": True}}
        with patch("handeln.freigabefenster.lade") as lade, \
             patch("handeln.kraken_rest.produkt", return_value="futures"), \
             patch("handeln.kraken_rest.guthaben", return_value=0.0):
            lade.return_value.offen.return_value = True
            sperren = handeln.sperren_zeile(w)
        self.assertIn("kein freies USD im Futures-Konto", sperren)

    def test_mit_usd_offen(self):
        w = {"handel_erlaubt": True, "freigabe": {"erfuellt": True}}
        with patch("handeln.freigabefenster.lade") as lade, \
             patch("handeln.kraken_rest.produkt", return_value="futures"), \
             patch("handeln.kraken_rest.guthaben", return_value=100.0):
            lade.return_value.offen.return_value = True
            self.assertIsNone(handeln.sperren_zeile(w))

    def test_spot_fragt_kein_guthaben(self):
        """Der Spot-Zweig bleibt unveraendert - dort gilt die alte Kette."""
        w = {"handel_erlaubt": True, "freigabe": {"erfuellt": True}}
        with patch("handeln.freigabefenster.lade") as lade, \
             patch("handeln.kraken_rest.guthaben") as g:
            lade.return_value.offen.return_value = True
            self.assertIsNone(handeln.sperren_zeile(w))
        g.assert_not_called()


class WeicheTest(unittest.TestCase):
    """KRAKEN_PRODUKT entscheidet, welche Schnittstelle geladen wird."""

    def _lade(self, produkt):
        pfad = os.path.join(HIER, "kraken_rest.py")
        spec = importlib.util.spec_from_file_location("kr_%s" % produkt, pfad)
        modul = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {"KRAKEN_PRODUKT": produkt}):
            spec.loader.exec_module(modul)
        return modul

    def test_spot_laedt_spot(self):
        self.assertEqual(self._lade("spot").produkt(), "spot")

    def test_futures_laedt_futures(self):
        modul = self._lade("futures")
        self.assertEqual(modul.produkt(), "futures")
        self.assertTrue(modul._kraken.__file__.endswith("kraken_futures.py"))
        self.assertEqual(modul.GUTHABEN_WAEHRUNG, "usd")

    def test_spot_laedt_kraken_py(self):
        modul = self._lade("spot")
        self.assertTrue(modul._kraken.__file__.endswith("kraken.py"))
        self.assertEqual(modul.GUTHABEN_WAEHRUNG, "ZEUR")


if __name__ == "__main__":
    unittest.main()