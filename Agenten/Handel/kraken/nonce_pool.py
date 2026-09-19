"""Gemeinsamer, persistenter Kraken-nonce-Pool.

Kraken verlangt je Schluessel streng monotone Nonces, die NICHT weiter als
~1-2 Sekunden in der Zukunft liegen (relativ zur Kraken-Serverzeit).

ZWEI unabhaengige Fallen, beide gemessen 2026-09-19:

1. PARALLELE PROZESSE, derselbe Schluessel. Zwei Programme teilen den
   KRAKEN_API_KEY:
     - Agenten/Handel/kraken/kraken.py        (die Handels-Spur)
     - Agenten/MCP-Server/kraken/kraken_mcp.py (der MCP-Server)
   Jedes erhob die nonce unabhaengig mit `time.time()*1e6`. Laeuft beides
   parallel, ueberholt der spaetere den frueheren und Kraken antwortet
   "EAPI:Invalid nonce". Deshalb: EINE hier zentralisierte Erhoehung ueber
   eine exklusiv erzeugte Sperrdatei (Lesen-Erhoehen-Schreiben atomar).

2. SYSTEMUHR EILT VORAUS. Die lokale Uhr kann der Kraken-Serverzeit um
   Sekunden voraus sein (hier 2,76 s). Ein nonce aus `time.time()` liegt
   dann in der Zukunft und wird abgelehnt - sogar mit monotonen
   +1-Tag-Werten. Deshalb wird beim ersten Aufruf die Kraken-Serverzeit
   geholt (`/0/public/Time`) und aus der Abweichung ein Korrektur-Offset
   berechnet: nonce = max(lokal - drift, letzter + 1).

Nur Standardbibliothek, damit auch der MCP-Server (anderes venv) es laden
kann. Die nonce-Datei (.kraken_nonce) ist ueber die .gitignore-Wildcard
(Zeile 20) ausgeschlossen und liegt nie im Repo.
"""

import json
import os
import time
import urllib.parse
import urllib.request

_DATEI = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".kraken_nonce")
_SPERRE = _DATEI + ".lock"
_BASIS = "https://api.kraken.com"
_HEADERS = {"User-Agent": "MaxHirn-Handel/1.0"}

_DRIFT = None  # System - KrakenServer, in Sekunden; einmal gemessen.


def _server_zeit():
    """Kraken-Serverzeit in Sekunden via /0/public/Time (oeffentlich)."""
    url = _BASIS + "/0/public/Time"
    req = urllib.request.Request(url, headers=_HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=20) as antwort:
        return json.loads(antwort.read().decode())["result"]["unixtime"]


def _drift_berechnen():
    global _DRIFT
    try:
        _DRIFT = time.time() - _server_zeit()
    except Exception:                              # pragma: no cover - Netz aus
        _DRIFT = 0.0  # ohne Serverkontakt: keine Korrektur, Datei schuetzt
    return _DRIFT


def _nonce_roh():
    """Steigender nonce-Wert nahe der Kraken-Serverzeit (nicht Zukunft)."""
    if _DRIFT is None:
        _drift_berechnen()
    return int((time.time() - _DRIFT) * 1_000_000)


def monotone_nonce() -> int:
    """Naechster nonce: streng steigend, nie in der Zukunft (Serverzeit)."""
    # Exklusiv erzeugen; warten, falls ein anderer Prozess gerade schreibt.
    while True:
        try:
            fd = os.open(_SPERRE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            time.sleep(0.01)
    try:
        letzter = 0
        try:
            with open(_DATEI) as f:
                roh = f.read().strip()
                letzter = int(roh) if roh else 0
        except (OSError, ValueError):
            letzter = 0
        # max() haelt die Datei monoton ueber NTP-Rueckspruenge hinweg; der
        # Drift-Abzug haelt sie unter der Serverzeit (keine Zukunft).
        nonce = max(_nonce_roh(), letzter + 1)
        with open(_DATEI, "w") as f:
            f.write(str(nonce))
            f.flush()
    finally:
        os.close(fd)
        try:
            os.remove(_SPERRE)
        except OSError:
            pass
    return nonce