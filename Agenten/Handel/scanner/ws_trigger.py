"""WebSocket-Trigger fuer die scanner-Spur.

Entfernt nur die Wartezeit bis zum naechsten 15-Minuten-Zyklus:
Signal bleibt identisch, Ausfuehrung folgt in Sekunden nach Kerzenschluss.

Regeln (nicht verhandelbar):
1. Signal-Logik UNVERAENDERT - handeln.py wird nur frueher gerufen
2. Sperrenkette UNANGETASTET - alle Wachen bleiben wirksam
3. PAPER ZUERST - Buchungen laufen ueber denselben Papierweg
4. Zyklus bleibt Rueckfallebene - Trigger ist Zusatz, kein Ersatz
5. Fuellpreis-Vergleich: herkunft=trigger vs herkunft=zyklus im Journal
6. Tests ohne Netz - WebSocket-Rahmen als Attrappen
"""

import argparse
import json
import os
import sys
import time
import signal
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import websocket
import okx
import handeln
import wachen_pruefung as wp
import scan


HIER = Path(__file__).resolve().parent
PID_DATEI = HIER / "ws_trigger.pid"
LOG_DATEI = HIER / "ws_trigger.log"

# OKX WebSocket: Der PUBLIC-Feed ist global (ws.okx.com) - gemessen 02.10.2026:
# ws.eea.okx.com loest im DNS NICHT auf, ws.okx.com schon; oeffentliche Kerzen
# sind nicht konto-gebunden. Nur ein privater Kanal waere regionen-abhaengig.
def _ws_host() -> str:
    return "ws.okx.com"


def _ws_url() -> str:
    # Die KERZENKANAELE (candle*) liegen auf dem BUSINESS-WebSocket, nicht auf
    # /public - gemessen 02.10.2026: /public wirft fuer candle15m immer
    # "doesn't exist" (auch BTC-USDT), /business bestaetigt die Subscription
    # und liefert Daten - auch fuer die EEA-Instrumente (BTC-USDC).
    return f"wss://{_ws_host()}:8443/ws/v5/business"
PING_INTERVAL = 30  # Sekunden
RECONNECT_BASE = 2  # Sekunden, exponentiell


def _jetzt_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log(zeile: str) -> None:
    """Schreibt mit Zeitstempel in Logdatei und stdout."""
    ts = _jetzt_iso()
    eintrag = f"[{ts}] {zeile}"
    print(eintrag)
    try:
        with LOG_DATEI.open("a", encoding="utf-8") as f:
            f.write(eintrag + "\n")
    except OSError:
        pass


def _schreibe_pid() -> bool:
    """Schreibt PID-Datei. Gibt False, wenn schon laeuft."""
    try:
        if PID_DATEI.exists():
            alt = PID_DATEI.read_text("utf-8").strip()
            if alt:
                try:
                    os.kill(int(alt), 0)
                    _log(f"Trigger laeuft schon (PID {alt}) - Abbruch")
                    return False
                except OSError:
                    pass  # Prozess tot, Datei verwaist
        PID_DATEI.write_text(str(os.getpid()), encoding="utf-8")
        return True
    except OSError as e:
        _log(f"PID-Datei nicht schreibbar: {e}")
        return False


def _entferne_pid() -> None:
    try:
        PID_DATEI.unlink(missing_ok=True)
    except OSError:
        pass


class WSTrigger:
    def __init__(self, wachen: dict, modus: str = "papier"):
        self.wachen = wachen
        self.modus = modus  # "papier" oder "live"
        self.live = modus == "live"
        self.instrumente: List[str] = []
        self.ws = None
        self.running = False
        self.reconnect_wait = RECONNECT_BASE
        self.ping_thread: Optional[threading.Thread] = None
        self.letztes_ping = 0
        self._lock = threading.Lock()
        self._verarbeitete_kerzen: Set[str] = set()  # inst+timestamp gegen Doppelverarbeitung

    def _lade_instrumente(self) -> List[str]:
        """Instrumente aus wachen.json (Watchlist oder ganzes Universum)."""
        uni = self.wachen.get("universum") or {}
        if uni.get("modus") == "alle":
            quote = uni.get("quotes", ["USDT", "USDC"])
            min_vol = uni.get("min_volumen_24h_usd", 3000000)
            return [inst for inst, _ in okx.alle_paare(quote=quote, min_volumen_usd=min_vol)]
        return self.wachen.get("watchlist", [])

    def _abonnements_nachricht(self) -> dict:
        args = [{"channel": "candle15m", "instId": inst} for inst in self.instrumente]
        return {"op": "subscribe", "args": args}

    def _verbinde(self):
        """Erstellt die WebSocket-Verbindung (blockiert bis Schliessung)."""
        self.ws = websocket.WebSocketApp(
            _ws_url(),
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        # Bibliotheks-Ping aus (wir senden den OKX-Text-Ping alle 30 s selbst,
        # siehe _starte_ping); ping_timeout muss trotzdem > 0 sein, sonst
        # wirft run_forever WebSocketException 'Ensure ping_timeout > 0'.
        self.ws.run_forever(ping_interval=0, ping_timeout=10)

    def _verbinde_nur(self):
        """Erstellt WebSocket ohne zu blockieren (fuer Tests)."""
        self.ws = websocket.WebSocketApp(
            _ws_url(),
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

    def _on_open(self, ws):
        _log(f"WebSocket verbunden: {_ws_url()}")
        self.reconnect_wait = RECONNECT_BASE
        abo = self._abonnements_nachricht()
        ws.send(json.dumps(abo))
        _log(f"Abonniert: {len(self.instrumente)} Instrumente (candle15m)")
        self._starte_ping()

    def _starte_ping(self):
        def ping_loop():
            while self.running and self.ws and self.ws.sock and self.ws.sock.connected:
                time.sleep(1)
                jetzt = time.time()
                if jetzt - self.letztes_ping >= PING_INTERVAL:
                    try:
                        self.ws.send("ping")
                        self.letztes_ping = jetzt
                        _log("ping gesendet")
                    except Exception as e:
                        _log(f"Ping-Fehler: {e!r}")
                        break
        self.ping_thread = threading.Thread(target=ping_loop, daemon=True)
        self.ping_thread.start()

    def _on_message(self, ws, message: str):
        try:
            daten = json.loads(message)
        except json.JSONDecodeError:
            return

        # Ping/Pong
        if daten.get("event") == "pong" or message.strip() == "pong":
            return

        # Abonnement-Bestaetigung
        if daten.get("event") == "subscribe":
            _log(f"Abonnement bestaetigt: {daten.get('arg', {}).get('channel')}")
            return

        # Kerzendaten
        if "data" in daten and "arg" in daten:
            arg = daten["arg"]
            if arg.get("channel") == "candle15m":
                inst = arg.get("instId")
                for kerze in daten["data"]:
                    self._verarbeite_kerze(inst, kerze)

    def _verarbeite_kerze(self, inst: str, kerze: list):
        """Business-Kerze: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        - confirm ist das LETZTE Feld, 1 = abgeschlossene Kerze."""
        if len(kerze) < 9:
            return
        ts = int(kerze[0])
        confirm = kerze[-1]
        if confirm != "1" and confirm != 1:
            return  # nur abgeschlossene Kerzen

        schluessel = f"{inst}:{ts}"
        with self._lock:
            if schluessel in self._verarbeitete_kerzen:
                return
            self._verarbeitete_kerzen.add(schluessel)

        _log(f"Kerzenschluss {inst} @ {ts} -> Trigger-Ausfuehrung")
        self._fuehre_handeln_aus(inst, ts)

    def _fuehre_handeln_aus(self, inst_ausgeloest: str, kerzen_ts: int):
        """Fuehrt handeln.py-Logik aus: Ausstiege pruefen, Einstiege pruefen."""
        try:
            # 1. Wachen laden und Lage pruefen
            z = handeln.lade_zustand()
            s = wp.lage(self.wachen, handeln.JOURNAL, z)

            # 2. Live-Sperren pruefen (identisch zu handeln.py)
            live = False
            if self.live:
                gruende = handeln.sperren_live(self.wachen, s)
                if gruende:
                    _log(f"Trigger-Live gesperrt: {'; '.join(gruende)} -> Papier")
                else:
                    live = True

            # 3. Bericht laden (neuester.json)
            bpfad = scan.BERICHTE / "neuester.json"
            if not bpfad.exists():
                _log("Kein Bericht (neuester.json) - Trigger uebersprungen")
                return
            bericht = json.loads(bpfad.read_text("utf-8"))

            # 4. Vorschlaege bauen
            vs = handeln.vorschlaege(bericht, self.wachen)

            # 5. Ausstiege pruefen (ALLE Positionen, nicht nur inst_ausgeloest)
            # HERKUNFT auf "trigger" setzen fuer Journal-Eintraege
            handeln.HERKUNFT = "trigger"
            handeln.pruefe_ausstiege(z, live)

            # 6. Einstiege pruefen - nur wenn Buch nicht voll
            if len(z["positionen"]) < self.wachen["max_offene_positionen"]:
                faktor = wp.groessenfaktor(s["ruecklauf_usd"], self.wachen)
                handeln.pruefe_einstiege(z, vs, self.wachen, live, faktor=faktor)
            else:
                handeln.protokolliere("Buch voll (Trigger)")
            # HERKUNFT zuruecksetzen
            handeln.HERKUNFT = "zyklus"

            # 7. Zustand speichern + Spiegelung
            handeln.schreibe_zustand(z)
            if self.wachen.get("journal_zweitziel"):
                ok, info = wp.spiegele_journal([handeln.JOURNAL, handeln.ZUSTAND, handeln.ABLEHNUNGEN],
                                                self.wachen["journal_zweitziel"])
                _log(f"Spiegelung: {'ok' if ok else 'fehlgeschlagen'} ({info})")

            _log(f"Trigger-Zyklus abgeschlossen (live={live})")

        except Exception as e:
            _log(f"Trigger-Fehler: {e}")
            import traceback
            traceback.print_exc()

    def _on_error(self, ws, error):
        _log(f"WebSocket-Fehler: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        _log(f"WebSocket geschlossen ({close_status_code}: {close_msg})")
        self._stoppe_ping()
        if self.running:
            self._reconnect()

    def _stoppe_ping(self):
        self.running = False
        if self.ping_thread:
            self.ping_thread.join(timeout=2)
            self.ping_thread = None

    def _reconnect(self):
        wait = self.reconnect_wait
        _log(f"Reconnect in {wait}s...")
        time.sleep(wait)
        self.reconnect_wait = min(wait * 2, 300)  # max 5 Min
        if self.running:
            self._verbinde()

    def starten(self):
        if not _schreibe_pid():
            return
        self.instrumente = self._lade_instrumente()
        if not self.instrumente:
            _log("Keine Instrumente konfiguriert - Abbruch")
            _entferne_pid()
            return

        self.running = True
        _log(f"Starte Trigger (modus={self.modus}, {len(self.instrumente)} Instrumente)")

        def signal_handler(signum, frame):
            _log(f"Signal {signum} empfangen - stoppe")
            self.stoppen()
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            self._verbinde()
        finally:
            self.stoppen()

    def stoppen(self):
        self.running = False
        self._stoppe_ping()
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        _entferne_pid()
        _log("Trigger gestoppt")


def main():
    parser = argparse.ArgumentParser(description="WebSocket-Trigger fuer scanner-Spur")
    parser.add_argument("--modus", choices=["papier", "live"], default="papier",
                        help="papier (Standard) oder live")
    parser.add_argument("--test", action="store_true",
                        help="Testmodus: verarbeitet eine JSON-Zeile von stdin als Kerze")
    a = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = scan.wachen()

    if a.test:
        # Testmodus: eine Zeile JSON von stdin lesen, als Kerze verarbeiten
        # (sys ist oben schon importiert - ein import hier drinnen wuerde 'sys'
        # fuer die GANZE Funktion lokal machen, siehe UnboundLocalError 02.10.)
        zeile = sys.stdin.readline()
        if not zeile:
            return
        daten = json.loads(zeile)
        inst = daten.get("inst")
        kerze = daten.get("kerze")
        if inst and kerze:
            trigger = WSTrigger(w, a.modus)
            trigger.instrumente = [inst]
            trigger._verarbeite_kerze(inst, kerze)
        return

    trigger = WSTrigger(w, a.modus)
    trigger.starten()


if __name__ == "__main__":
    main()