"""Tests fuer kraken_abweisungs_sonde.py - ohne Netz, ohne echte Kraken-Konten.

Der Aufbau: ein winziger HTTP-Server im Testprozess spielt Kraken. Die
Hausmodule (kraken.py, kraken_futures.py) werden ueber den Pfad geladen und
ihre BASIS-Adresse auf die Attrappe umgebogen; die Sonde bekommt sie ueber
die Naht `lauf(module=...)`. So wird genau die Frage geprueft, die T-073 offen
liess: unterscheidet die Sonde "Schluessel/Konto" von "Netz/IP" richtig, und
haelt sie im Fehlerfall den Zeugen fest?

WARUM DIE NAHT NOETIG IST (teuer gelernt, 25.09.2026): die erste Fassung der
Sonde trug EIGENE Basis-Konstanten. Beim Testlauf bogen die Tests nur diese
um - `kraken.guthaben()` ging aber weiter an api.kraken.com, und sechs Aufrufe
mit Attrappen-Schluessel landeten beim ECHTEN Kraken. Jeder davon zaehlt dort
als Fehlversuch und kann das Konto zeitweise sperren (genau der Zustand, den
T-073 beschreibt). Regel daraus: eine Sonde darf keine eigene Adresse
mitbringen, und ein Test muss beweisen, dass NICHTS an den echten Host geht.

Geprueft wird die REGEL, nicht ein eingefrorener Wert:
  * nur signierte Wege rot  -> Lage "schluessel"
  * auch oeffentliche rot   -> Lage "netz"
  * alles gruen             -> Lage "ok", keine Kuehlzeit
  * nach einer Abweisung    -> Kuehlzeit, der naechste Lauf klopft NICHT
  * Erholung                -> "erholt_nach_min" erscheint
  * Zeuge                   -> Status, Header und Rohkoerper im Protokoll
  * Adressregel             -> die Sonde kennt keine eigene Kraken-Adresse
  * Modulwaechter           -> im ECHTEN cache-Ordner kommt nichts hinzu
"""

import base64
import http.server
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse

TESTS = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(TESTS)
sys.path.insert(0, HANDEL)

import kraken_abweisungs_sonde as sonde  # noqa: E402

ECHTER_CACHE = os.path.join(HANDEL, "cache")
STARTBESTAND = None


def setUpModule():
    global STARTBESTAND
    STARTBESTAND = sorted(os.listdir(ECHTER_CACHE)) if os.path.isdir(ECHTER_CACHE) else []


def tearDownModule():
    jetzt = sorted(os.listdir(ECHTER_CACHE)) if os.path.isdir(ECHTER_CACHE) else []
    neu = [n for n in jetzt if n not in STARTBESTAND]
    if neu:
        raise AssertionError("Sonde hat in den ECHTEN cache-Ordner geschrieben: %s" % neu)


class Attrappe:
    """Ein HTTP-Server, der Kraken spielt."""

    def __init__(self):
        self.antworten = {}
        self.anfragen = []
        aussen = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):      # kein Testrauschen
                pass

            def _sende(self):
                aussen.anfragen.append(self.path)
                koerper, kopf = aussen._antwort(self.path)
                roh = koerper.encode()
                self.send_response(kopf.pop("status", 200))
                for k, v in kopf.items():
                    self.send_header(k, v)
                self.send_header("Content-Type", "application/json")
                self.send_header("cf-ray", "attrappe-1234")
                self.send_header("Content-Length", str(len(roh)))
                self.end_headers()
                self.wfile.write(roh)

            def do_GET(self):
                self._sende()

            def do_POST(self):
                laenge = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(laenge)
                self._sende()

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.basis = "http://127.0.0.1:%d" % self.server.server_address[1]

    def _antwort(self, pfad):
        for muster, antwort in self.antworten.items():
            if pfad.startswith(muster):
                return antwort
        return json.dumps({"error": [], "result": {}}), {}

    def stoppe(self):
        self.server.shutdown()
        self.server.server_close()


GESUND = {
    "/0/public/Time": (json.dumps({"error": [], "result": {"unixtime": 1}}), {}),
    "/0/private/Balance": (json.dumps({"error": [], "result": {"ZEUR": "1.0"}}), {}),
    "/tickers": (json.dumps({"result": "success", "tickers": []}), {}),
    "/accounts": (json.dumps({"result": "success",
                              "accounts": {"flex": {"availableMargin": 1.0}}}), {}),
}
SPOT_ABGEWIESEN = {
    "/0/public/Time": GESUND["/0/public/Time"],
    "/tickers": GESUND["/tickers"],
    "/0/private/Balance": (json.dumps({"error": ["EGeneral:Permission denied"],
                                       "result": {}}), {}),
    "/accounts": (json.dumps({"result": "error", "errors": "authenticationError"}), {}),
}


class SondenTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        sonde.PROTOKOLL = os.path.join(self.tmp.name, "kraken-abweisungen.jsonl")
        sonde.STAND_DATEI = os.path.join(self.tmp.name, "stand.json")
        self.alt_env = {}
        for name, wert in (("KRAKEN_SPOT_API_KEY", "attrappe-key"),
                           ("KRAKEN_SPOT_API_SECRET",
                            base64.b64encode(b"geheim" * 8).decode()),
                           ("KRAKEN_FUTURE_API_KEY", "attrappe-future-key"),
                           ("KRAKEN_FUTURE_API_SECRET",
                            base64.b64encode(b"geheim" * 8).decode())):
            self.alt_env[name] = os.environ.get(name)
            os.environ[name] = wert
        self.attrappe = Attrappe()

    def tearDown(self):
        self.attrappe.stoppe()
        self.tmp.cleanup()
        for name, wert in self.alt_env.items():
            if wert is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = wert

    # --- Hilfen -------------------------------------------------------------
    def _module(self):
        """Die Hausmodule mit umgebogener Adresse und eigenem nonce-Zaehler."""
        kraken = sonde._lade(sonde.KRAKEN_QUELLE, "test_kraken_quelle")
        futures = sonde._lade(sonde.FUTURES_QUELLE, "test_kraken_futures")
        pool = sonde._lade(sonde.NONCE_POOL, "test_nonce_pool")
        for m in (kraken, futures):
            m.BASIS = self.attrappe.basis
        pool._DATEI = os.path.join(self.tmp.name, ".kraken_nonce")
        pool._SPERRE = pool._DATEI + ".lock"
        return (kraken, futures, pool)

    def _lauf(self, antworten=GESUND):
        self.attrappe.antworten = dict(antworten)
        return sonde.lauf(melden=False, module=self._module())

    def _protokoll(self):
        with open(sonde.PROTOKOLL, "r", encoding="utf-8") as f:
            return [json.loads(z) for z in f if z.strip()]

    # --- die Adressregel ----------------------------------------------------
    def test_sonde_kennt_keine_eigene_kraken_adresse(self):
        self.assertFalse(hasattr(sonde, "SPOT_BASIS"),
                         "die Sonde darf keine eigene Spot-Adresse mitbringen")
        self.assertFalse(hasattr(sonde, "FUTURES_BASIS"),
                         "die Sonde darf keine eigene Futures-Adresse mitbringen")

    def test_alle_wege_gehen_an_die_uebergebene_adresse(self):
        self._lauf()
        gerufen = " ".join(self.attrappe.anfragen)
        for pfad in ("/0/public/Time", "/0/private/Balance", "/tickers", "/accounts"):
            self.assertIn(pfad, gerufen)

    # --- gesund -------------------------------------------------------------
    def test_alles_offen_ergibt_ok_ohne_kuehlzeit(self):
        zeile = self._lauf()
        self.assertEqual(zeile["lage"], "ok")
        self.assertIsNone(sonde._lies_stand().get("kuehlzeit_bis"))
        self.assertEqual(len(self._protokoll()), 1)
        self.assertNotIn("zeuge", zeile)

    # --- nur signiert rot ---------------------------------------------------
    def test_nur_signierte_wege_rot_ergibt_schluessel(self):
        zeile = self._lauf(SPOT_ABGEWIESEN)
        self.assertEqual(zeile["lage"], "schluessel")
        zeuge = zeile.get("zeuge") or {}
        self.assertIn("roh_spot", zeuge)
        self.assertEqual(zeuge["roh_spot"]["status"], 200)
        self.assertIn("cf-ray", zeuge["roh_spot"]["kopf"])
        self.assertIn("Permission denied", zeuge["roh_spot"]["anfang"])
        self.assertIn("authenticationError", zeuge["roh_futures"]["anfang"])
        stand = sonde._lies_stand()
        self.assertTrue(stand.get("kuehlzeit_bis"))
        self.assertTrue(stand.get("stoerung_seit"))

    # --- alles rot ----------------------------------------------------------
    def test_auch_oeffentliche_wege_rot_ergibt_netz(self):
        zeile = self._lauf({
            "/0/public/Time": ("cloudflare blockt", {"status": 520}),
            "/tickers": ("cloudflare blockt", {"status": 1020}),
        })
        self.assertEqual(zeile["lage"], "netz")
        self.assertFalse(zeile["wege"]["offen_spot"])
        self.assertFalse(zeile["wege"]["offen_futures"])

    # --- Kuehlzeit ----------------------------------------------------------
    def test_kuehlzeit_verhindert_den_naechsten_klopfer(self):
        self._lauf(SPOT_ABGEWIESEN)
        vorher = len(self.attrappe.anfragen)
        zweiter = sonde.lauf(melden=False, module=self._module())
        self.assertTrue(zweiter.get("letzter_lauf_uebersprungen"))
        self.assertEqual(len(self.attrappe.anfragen), vorher,
                         "die Sonde hat trotz Kuehlzeit wieder angeklopft")

    def test_nach_erholung_erscheint_die_dauer(self):
        self._lauf(SPOT_ABGEWIESEN)
        stand = sonde._lies_stand()
        stand["kuehlzeit_bis"] = None
        sonde._schreib_stand(stand)
        zeile = self._lauf(GESUND)
        self.assertEqual(zeile["lage"], "ok")
        self.assertIsNotNone(zeile.get("erholt_nach_min"))
        self.assertNotIn("stoerung_seit", sonde._lies_stand())

    # ---Einordnung als reine Regel ------------------------------------------
    def test_einordnung_ist_eine_regel(self):
        gruen, rot = {"ok": True}, {"ok": False, "fehler": "x"}
        self.assertEqual(sonde.einordnung({"offen_spot": gruen, "privat_spot": gruen})[0], "ok")
        self.assertEqual(sonde.einordnung({"offen_spot": gruen, "privat_spot": rot})[0],
                         "schluessel")
        self.assertEqual(sonde.einordnung({"offen_spot": rot, "privat_spot": rot})[0], "netz")
        # Ein fallender OEFFENTLICHER Weg bleibt ein Netz-Befund, auch wenn die
        # signierten Wege gerade gehen - ohne Schluessel gibt es nichts zu
        # authentifizieren, also kann es kein Schluesselproblem sein.
        self.assertEqual(sonde.einordnung({"offen_spot": rot, "privat_spot": gruen})[0],
                         "netz")

    # --- die Wache ----------------------------------------------------------
    def _wache(self, antworten):
        self.attrappe.antworten = dict(antworten)
        puffer, alt = io.StringIO(), sys.stdout
        sys.stdout = puffer
        try:
            code = sonde.wache(module=self._module())
        finally:
            sys.stdout = alt
        return code, puffer.getvalue()

    def test_wache_schweigt_wenn_gesund(self):
        code, text = self._wache(GESUND)
        self.assertEqual(code, 0)
        self.assertEqual(text.strip(), "")

    def test_wache_meldet_die_abweisung_mit_frage(self):
        code, text = self._wache(SPOT_ABGEWIESEN)
        self.assertEqual(code, 1)
        self.assertIn("Kraken weist ab", text)
        self.assertIn("Kraken-Portal", text)

    # --- Nonce-Einheit: Nanosekunden (Haus-Standard) ------------------------
    def test_roh_futures_nutzt_gemeinsamen_pool_nanosekunden(self):
        """_roh_futures muss den gemeinsamen Pool (Nanosekunden) nutzen,
        nicht futures._nonce() (Millisekunden). Die Einheit muss mindestens
        so gross sein, die groesste, die ein Werkzeug auf denselben Schluessel
        sendet - sonst ist jeder Wert darunter ungueltig (EAPI:Invalid nonce).
        """
        kraken, futures, pool = self._module()

        class MockPool:
            def monotone_nonce(self):
                return 1_700_000_000_000_000_000  # ~2023-11-14 in Nanosekunden

        aufgerufen = {}
        original = sonde._roh_aufruf

        def mock_roh_aufruf(url, kopf, daten):
            aufgerufen["kopf"] = kopf
            return {"status": 200, "kopf": {}, "anfang": "{}"}

        sonde._roh_aufruf = mock_roh_aufruf
        try:
            sonde._roh_futures(futures, MockPool())
        finally:
            sonde._roh_aufruf = original

        nonce = aufgerufen["kopf"]["Nonce"]
        # Nanosekunden seit 1970: > 1e18 (Millisekunden wären ~1e12)
        self.assertGreater(int(nonce), 10**18,
                           "Nonce muss im Nanosekundenbereich liegen")


class NonceWiederholungTest(unittest.TestCase):
    """Der Haus-Ausweg aus T-075: bei "EAPI:Invalid nonce" schiebt die Sonde
    den geteilten Zaehler mit vorwaerts() vor und wiederholt - identisch zu
    kraken.py._roh_privat. Ohne das Schieben waere der Zeuge ein
    Nonce-Artefakt statt der echten Abweisung.

    Alle Aufrufe gehen an eine TOTE Adresse (Port 9 = discard) - selbst ein
    Fehlgriff der echten urllib-Schicht kaeme nie bei Kraken an. Die Sonde
    kennt weiterhin keine eigene Kraken-Adresse.
    """

    class Pool:
        def __init__(self):
            self.wert = 1_700_000_000_000_000_000   # ~2023-11, Nanosekunden
            self.vorwaerts_aufrufe = []

        def monotone_nonce(self):
            return self.wert

        def vorwaerts(self, sekunden):
            self.wert += int(sekunden * 1_000_000_000)
            self.vorwaerts_aufrufe.append(sekunden)
            return self.wert

    NONCE_ANTWORT = {"status": 200, "kopf": {},
                     "anfang": '{"error":["EAPI:Invalid nonce"],"result":{}}'}
    ABWEISUNG = {"status": 200, "kopf": {},
                 "anfang": '{"error":["EGeneral:Permission denied"],"result":{}}'}

    def setUp(self):
        self.alt_env = {}
        for name, wert in (("KRAKEN_SPOT_API_KEY", "attrappe-key"),
                           ("KRAKEN_SPOT_API_SECRET",
                            base64.b64encode(b"geheim" * 8).decode()),
                           ("KRAKEN_FUTURE_API_KEY", "attrappe-future-key"),
                           ("KRAKEN_FUTURE_API_SECRET",
                            base64.b64encode(b"geheim" * 8).decode())):
            self.alt_env[name] = os.environ.get(name)
            os.environ[name] = wert
        self.rufe = []

    def tearDown(self):
        for name, wert in self.alt_env.items():
            if wert is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = wert

    def _module(self, basis="http://127.0.0.1:9"):
        """Hausmodule mit toter Adresse: nie echtes Kraken."""
        kraken = sonde._lade(sonde.KRAKEN_QUELLE, "test_nc_kraken")
        futures = sonde._lade(sonde.FUTURES_QUELLE, "test_nc_futures")
        for m in (kraken, futures):
            m.BASIS = basis
        return kraken, futures

    def _fange_ab(self, antworten):
        self._antworten = list(antworten)

        def fake_roh_aufruf(url, kopf, daten):
            self.rufe.append({"url": url, "kopf": kopf, "daten": daten})
            return self._antworten.pop(0)

        self._original_roh = sonde._roh_aufruf
        sonde._roh_aufruf = fake_roh_aufruf

    def _gib_frei(self):
        sonde._roh_aufruf = self._original_roh

    def test_spot_wiederholt_invalid_nonce_mit_vorwaerts(self):
        kraken, _ = self._module()
        pool = self.Pool()
        self._fange_ab([self.NONCE_ANTWORT, self.ABWEISUNG])
        try:
            ergebnis = sonde._roh_spot(kraken, pool)
        finally:
            self._gib_frei()
        self.assertEqual(pool.vorwaerts_aufrufe, [1])
        self.assertEqual(ergebnis["versuche"], 2)
        self.assertIn("Permission denied", ergebnis["anfang"])
        self.assertEqual(len(self.rufe), 2)
        for r in self.rufe:
            self.assertTrue(r["url"].startswith("http://127.0.0.1:9"),
                            "der Zeuge geht an die tote Testadresse, nie an Kraken")
        nonces = [int(urllib.parse.parse_qs(r["daten"].decode())["nonce"][0])
                  for r in self.rufe]
        self.assertGreater(nonces[1], nonces[0],
                           "der zweite Versuch muss einen hoeheren nonce tragen")

    def test_spot_gibt_nach_drei_versuchen_den_letzten_befund(self):
        kraken, _ = self._module()
        pool = self.Pool()
        self._fange_ab([self.NONCE_ANTWORT] * 3)
        try:
            ergebnis = sonde._roh_spot(kraken, pool)
        finally:
            self._gib_frei()
        self.assertEqual(pool.vorwaerts_aufrufe, [1, 2])
        self.assertEqual(ergebnis["versuche"], 3)
        self.assertEqual(len(self.rufe), 3)

    def test_spot_wiederholt_nur_nonce_befunde(self):
        kraken, _ = self._module()
        pool = self.Pool()
        self._fange_ab([self.ABWEISUNG])
        try:
            ergebnis = sonde._roh_spot(kraken, pool)
        finally:
            self._gib_frei()
        self.assertEqual(pool.vorwaerts_aufrufe, [],
                         "eine echte Abweisung schiebt den Pool nicht vor")
        self.assertEqual(ergebnis["versuche"], 1)
        self.assertEqual(len(self.rufe), 1)

    def test_futures_wiederholt_mit_hoeherem_nonce(self):
        _, futures = self._module()
        pool = self.Pool()
        self._fange_ab([self.NONCE_ANTWORT, self.ABWEISUNG])
        try:
            ergebnis = sonde._roh_futures(futures, pool)
        finally:
            self._gib_frei()
        self.assertEqual(pool.vorwaerts_aufrufe, [1])
        self.assertEqual(ergebnis["versuche"], 2)
        nonces = [int(r["kopf"]["Nonce"]) for r in self.rufe]
        self.assertGreater(nonces[1], nonces[0],
                           "der zweite Versuch muss einen hoeheren nonce tragen")


if __name__ == "__main__":
    unittest.main()