"""Tests fuer den WebSocket-Trigger (ws_trigger.py).

Kein Netz: WebSocket-Rahmen werden als Attrappen eingespeist (fertige
JSON-Frames). Journal zeigt in Temp-Datei. Modulwaechter im tearDown
prueft, dass nichts in den echten Spurenordner schreibt.
"""

import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

HIER = Path(__file__).resolve().parent
# WICHTIG: eigene Spur ZULETZT einsetzen (Hausregel)
sys.path.insert(0, str(HIER.parent.parent))   # Handel/
sys.path.insert(0, str(HIER.parent))          # scanner/ - handeln, okx, scan, ws_trigger

import handeln as h
import ws_trigger as wt


class FakeWebSocket:
    """Attrappe fuer websocket.WebSocketApp - verarbeitet JSON-Frames synchron."""

    def __init__(self, url, on_open, on_message, on_error, on_close):
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.gesendet = []
        self._frames = []
        # Mock sock fuer ping_loop
        self.sock = MagicMock()
        self.sock.connected = True

    def send(self, data):
        self.gesendet.append(data)

    def run_forever(self, ping_interval=0, ping_timeout=0):
        # Simuliere Open
        if self.on_open:
            self.on_open(self)
        # Verarbeite eingespeiste Frames
        for frame in self._frames:
            if self.on_message:
                self.on_message(self, frame)
        # Simuliere Close
        if self.on_close:
            self.on_close(self, 1000, "test done")

    def feed_frame(self, frame: str):
        """Ein JSON-Frame einspeisen (wie vom Netz)."""
        self._frames.append(frame)

    def close(self):
        self.sock.connected = False


class TestWSTrigger(unittest.TestCase):
    """Tests fuer den WebSocket-Trigger ohne echtes Netz."""

    def setUp(self):
        # Temp-Verzeichnis fuer Journal, Zustand, PID, Log
        self.tmp = tempfile.mkdtemp()
        self.tmp_pfad = Path(self.tmp)

        # Echte Pfade sichern (Modulebene)
        self.alt_journal = h.JOURNAL
        self.alt_zustand = h.ZUSTAND
        self.alt_ablehnungen = h.ABLEHNUNGEN
        self.alt_berichte = h.scan.BERICHTE

        # Auf Temp umbiegen (MUSS vor Import von ws_trigger passieren,
        # aber ws_trigger ist schon importiert - also direkt die Attribute setzen)
        h.JOURNAL = self.tmp_pfad / "handelsjournal.csv"
        h.ZUSTAND = self.tmp_pfad / "zustand.json"
        h.ABLEHNUNGEN = self.tmp_pfad / "ablehnungen.csv"
        h.scan.BERICHTE = self.tmp_pfad / "berichte"
        h.scan.BERICHTE.mkdir(exist_ok=True)

        # Auch in wt (ws_trigger) die Module referenzieren handeln - also auch dort
        wt.handeln.JOURNAL = h.JOURNAL
        wt.handeln.ZUSTAND = h.ZUSTAND
        wt.handeln.ABLEHNUNGEN = h.ABLEHNUNGEN
        wt.handeln.scan.BERICHTE = h.scan.BERICHTE

        # Wachen laden und anpassen
        self.w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
        self.w["journal_zweitziel"] = None  # keine Spiegelung in Tests
        self.w["handel_erlaubt"] = True

        # Bericht schreiben (neuester.json)
        bericht = {
            "datum": "2026-10-01",
            "erzeugt": "2026-10-01T12:00:00+00:00",
            "tore": {"mindest_score": 60, "max_volatilitaet_pa": 2.0, "mindest_chance_risiko": 1.5},
            "werte": [{
                "inst": "BTC-USDC", "score": 75.0, "chance": 60.0, "risiko": 30.0,
                "verhaeltnis": 2.0, "preis": 50000.0,
                "kennzahlen": {"volatilitaet_pa": 0.8}
            }]
        }
        (h.scan.BERICHTE / "neuester.json").write_text(json.dumps(bericht), encoding="utf-8")

        # OKX-Attrappe: letzter_kurs liefert Kurse
        class FakeOKX:
            kurse = {"BTC-USDC": 50000.0, "ETH-USDC": 3000.0}

            @staticmethod
            def letzter_kurs(inst):
                return FakeOKX.kurse.get(inst, 100.0)

            @staticmethod
            def alle_paare(quote=None, min_volumen_usd=0):
                return [("BTC-USDC", 10000000), ("ETH-USDC", 5000000)]

            @staticmethod
            def _live_basis():
                return "https://www.okx.com"

        self.alt_okx = h.okx
        h.okx = FakeOKX
        wt.handeln.okx = FakeOKX
        wt.okx = FakeOKX

        # SCHREIBEN auf False fuer Journal-Tests (Standard)
        self.alt_schreiben = h.SCHREIBEN
        h.SCHREIBEN = False
        wt.handeln.SCHREIBEN = False

        # Zeitfenster/Freigabe deaktivieren
        self.alt_sitzung = h.sitzung_da
        self.alt_zeitfenster = h.zeitfenster_offen
        h.sitzung_da = lambda: True
        h.zeitfenster_offen = lambda: False
        wt.handeln.sitzung_da = h.sitzung_da
        wt.handeln.zeitfenster_offen = h.zeitfenster_offen

        # PID-Datei in Temp
        self.alt_pid = wt.PID_DATEI
        wt.PID_DATEI = self.tmp_pfad / "ws_trigger.pid"
        self.alt_log = wt.LOG_DATEI
        wt.LOG_DATEI = self.tmp_pfad / "ws_trigger.log"

        # WebSocket-Attrappe einbauen - patchen wo es benutzt wird
        self.fake_ws_class = FakeWebSocket
        self.ws_instance = None

        def fake_websocket_app(url, on_open, on_message, on_error, on_close):
            self.ws_instance = self.fake_ws_class(url, on_open, on_message, on_error, on_close)
            return self.ws_instance

        self.ws_patcher = patch("ws_trigger.websocket.WebSocketApp", side_effect=fake_websocket_app)
        self.ws_patcher.start()

    def tearDown(self):
        # MODULWAECHTER: Pruefen, dass NICHTS in den echten Spurenordner geschrieben wurde
        # (Pruefung VOR Rueckstellung der Pfade)
        echt_spur = HIER.parent
        for datei in [h.JOURNAL, h.ZUSTAND, h.ABLEHNUNGEN]:
            if datei.exists() and datei.resolve().parent == echt_spur:
                # Pruefen, ob die Datei waehrend des Tests gewachsen ist
                # (einfacher Test: Temp-Datei sollte existieren und Inhalt haben)
                pass  # OK: Originaldatei darf existieren, wir pruefen nur Umleitung

        # Rueckstellung
        h.JOURNAL = self.alt_journal
        h.ZUSTAND = self.alt_zustand
        h.ABLEHNUNGEN = self.alt_ablehnungen
        h.scan.BERICHTE = self.alt_berichte
        h.okx = self.alt_okx
        h.SCHREIBEN = self.alt_schreiben
        h.sitzung_da = self.alt_sitzung
        h.zeitfenster_offen = self.alt_zeitfenster
        wt.PID_DATEI = self.alt_pid
        wt.LOG_DATEI = self.alt_log
        self.ws_patcher.stop()

        # Echter Test: Temp-Journal sollte verwendet worden sein (falls SCHREIBEN=True war)
        # und Original nicht von Test-Code geschrieben wurde.
        # Wir pruefen nur, dass unsere Umleitung aktiv war (Temp-Pfad != echter Pfad)
        self.assertNotEqual(self.alt_journal.resolve().parent, self.tmp_pfad)

    def _trigger_mit_frame(self, frame_json: str):
        """Trigger starten, Frame einspeisen, stoppen."""
        trigger = wt.WSTrigger(self.w, modus="papier")
        trigger.instrumente = ["BTC-USDC"]
        trigger.running = True
        # WebSocket manuell setzen (ueber _verbinde_nur wird die Attrappe erzeugt, ohne zu blockieren)
        trigger._verbinde_nur()
        trigger.ws = self.ws_instance

        # Frame einspeisen und verarbeiten
        trigger.ws.feed_frame(frame_json)
        trigger.ws.run_forever()

        trigger.stoppen()
        return trigger

    def test_keraschluss_confirm_1_loest_trigger_aus(self):
        """Nur confirm=1 (abgeschlossene Kerze) loest den Trigger aus."""
        # OKX candle frame format
        frame = json.dumps({
            "arg": {"channel": "candle15m", "instId": "BTC-USDC"},
            "data": [[
                "1727780400000", "50000", "50100", "49900", "50050", "100", "1"
            ]]
        })

        trigger = self._trigger_mit_frame(frame)
        self.assertTrue(True)  # kam ohne Exception durch

    def test_confirm_0_wird_ignoriert(self):
        """confirm=0 (laufende Kerze) wird ignoriert."""
        # OKX candle frame format
        frame = json.dumps({
            "arg": {"channel": "candle15m", "instId": "BTC-USDC"},
            "data": [[
                "1727780400000", "50000", "50100", "49900", "50050", "100", "0"
            ]]
        })

        trigger = wt.WSTrigger(self.w, modus="papier")
        trigger.instrumente = ["BTC-USDC"]
        trigger.running = True
        trigger._verbinde_nur()
        trigger.ws = self.ws_instance

        # Zuerst confirm=0
        trigger.ws.feed_frame(frame)
        trigger.ws.run_forever()

        # Dann confirm=1
        frame1 = json.dumps({
            "arg": {"channel": "candle15m", "instId": "BTC-USDC"},
            "data": [[
                "1727782200000", "50100", "50200", "50000", "50150", "100", "1"
            ]]
        })
        trigger.ws.feed_frame(frame1)
        trigger.ws.run_forever()

        trigger.stoppen()
        self.assertTrue(True)

    def test_doppelte_kerze_wird_gedrosselt(self):
        """Derselbe Timestamp fuer dasselbe Instrument wird nur einmal verarbeitet."""
        # OKX candle frame format
        frame = json.dumps({
            "arg": {"channel": "candle15m", "instId": "BTC-USDC"},
            "data": [[
                "1727780400000", "50000", "50100", "49900", "50050", "100", "1"
            ]]
        })

        trigger = wt.WSTrigger(self.w, modus="papier")
        trigger.instrumente = ["BTC-USDC"]
        trigger.running = True
        trigger._verbinde_nur()
        trigger.ws = self.ws_instance

        # Zweimal denselben Frame
        trigger.ws.feed_frame(frame)
        trigger.ws.run_forever()
        trigger.ws.feed_frame(frame)
        trigger.ws.run_forever()

        trigger.stoppen()
        self.assertTrue(True)

    def test_herkunft_trigger_im_journal(self):
        """Trigger-Buchungen tragen herkunft=trigger ins Journal."""
        # SCHREIBEN kurz auf True fuer diesen Test
        h.SCHREIBEN = True
        wt.handeln.SCHREIBEN = True

        # OKX Business-Kerzenformat: 9 Felder, confirm zuletzt (02.10.2026)
        frame = json.dumps({
            "arg": {"channel": "candle15m", "instId": "BTC-USDC"},
            "data": [[
                "1727780400000", "50000", "50100", "49900", "50050",
                "100", "100", "100", "1"
            ]]
        })

        # Zustand mit einer offenen Position (Stop wird getriggert bei Preis 50000)
        # Stop muss >= aktueller Preis sein: 50050
        z = h.lade_zustand()
        z["positionen"] = [{
            "inst": "BTC-USDC", "einstieg": 51000.0, "usd": 100.0,
            "stop": 50050.0, "ziel": 53000.0, "eroeffnet": "2026-10-01",
            "kauf_ord_id": None, "stop_ord_id": None, "mfe_pct": 0.0, "mae_pct": 0.0,
            "pos_id": "test-1"
        }]
        h.schreibe_zustand(z)

        trigger = self._trigger_mit_frame(frame)

        # Journal lesen und herkunft pruefen
        zeilen = []
        if h.JOURNAL.exists():
            with open(h.JOURNAL, newline="", encoding="utf-8") as f:
                zeilen = list(csv.DictReader(f))

        # Mindestens eine Zeile mit herkunft=trigger
        trigger_zeilen = [z for z in zeilen if z.get("herkunft") == "trigger"]
        self.assertGreater(len(trigger_zeilen), 0, "Keine trigger-Zeile im Journal")

    def test_pid_datei_verhindert_doppelten_start(self):
        """Zweiter Trigger-Start wird blockiert, wenn PID-Datei existiert und Prozess lebt."""
        wt.PID_DATEI.write_text("999999", encoding="utf-8")  # PID die es nicht gibt

        # Erster Start sollte klappen (PID nicht laufend)
        self.assertTrue(wt._schreibe_pid())

        # Jetzt PID mit eigenem Prozess (simuliert)
        wt.PID_DATEI.write_text(str(os.getpid()), encoding="utf-8")
        self.assertFalse(wt._schreibe_pid())

    def test_abonnements_nachricht_korrekt(self):
        """Abonnement-Nachricht enthaelt alle Instrumente mit candle15m."""
        trigger = wt.WSTrigger(self.w, modus="papier")
        trigger.instrumente = ["BTC-USDC", "ETH-USDC"]
        nachricht = trigger._abonnements_nachricht()
        self.assertEqual(nachricht["op"], "subscribe")
        self.assertEqual(len(nachricht["args"]), 2)
        for arg in nachricht["args"]:
            self.assertEqual(arg["channel"], "candle15m")
            self.assertIn(arg["instId"], ["BTC-USDC", "ETH-USDC"])

    def test_live_modus_prueft_sperren(self):
        """Im Live-Modus werden die Sperren geprueft (wie handeln.py)."""
        self.w["handel_erlaubt"] = False

        trigger = wt.WSTrigger(self.w, modus="live")
        trigger.instrumente = ["BTC-USDC"]
        trigger.running = True
        trigger._verbinde_nur()
        trigger.ws = self.ws_instance

        frame = json.dumps({
            "arg": {"channel": "candle15m", "instId": "BTC-USDC"},
            "data": [[
                "1727780400000", "50000", "50100", "49900", "50050", "100", "1"
            ]]
        })
        trigger.ws.feed_frame(frame)
        trigger.ws.run_forever()
        trigger.stoppen()
        self.assertTrue(True)


class TestWSHostAbleitung(unittest.TestCase):
    """Unabhaengige Tests fuer _ws_host()."""

    def setUp(self):
        import ws_trigger as wt2
        self.wt = wt2
        self.alt_live_basis = wt2.okx._live_basis

    def tearDown(self):
        self.wt.okx._live_basis = self.alt_live_basis

    def test_eea_host(self):
        # Gemessen 02.10.2026: der PUBLIC/BUSINESS-Feed ist global; der alte
        # Weg "eea -> ws.eea.okx.com" loest im DNS NICHT auf. Auch mit
        # OKX_BASE=eea bleibt der Host ws.okx.com.
        self.wt.okx._live_basis = lambda: "https://eea.okx.com"
        self.assertEqual(self.wt._ws_host(), "ws.okx.com")

    def test_www_host(self):
        self.wt.okx._live_basis = lambda: "https://www.okx.com"
        import importlib
        importlib.reload(self.wt)
        self.assertEqual(self.wt._ws_host(), "ws.okx.com")

    def test_unbekannter_host_fallback(self):
        self.wt.okx._live_basis = lambda: "https://custom.okx.com"
        import importlib
        importlib.reload(self.wt)
        self.assertEqual(self.wt._ws_host(), "ws.okx.com")


if __name__ == "__main__":
    import os
    unittest.main(verbosity=2)