"""Gemeinsamer, persistenter Kraken-nonce-Pool.

Kraken verlangt je Schluessel streng monotone Nonces innerhalb der
Zukunftsgrenze (relativ zur eigenen Serverzeit). Die einzig BEWIESENE
funktionierende Erhebung ist eine monotone Wallclock-Datei:

    nonce = max(int(time.time() * 1_000_000), letzter + 1)

Gemessen 2026-09-19: genau diese Logik (ohne irgendeine Serverzeit-Korrektur)
lief 5/5 durch. Ein nachtraeglich aufgesetzter "Drift-Abzug"
(nonce = Serverzeit statt Wallclock) senkte den nonce UNTER den von
parallelen Prozessen gesetzten Kraken-Peak und erzeugte damit die
"EAPI:Invalid nonce"-Flut, die er loesen sollte. Deshalb KEINE Drift-Korrektur
mehr - nur den Wallclock-Zaehler, der von allen Programmen geteilt wird.

ZWEI unabhaengige Befunde:

1. PARALLELE PROZESSE, derselbe Schluessel. Zwei Programme teilen den
   KRAKEN_API_KEY:
     - Agenten/Handel/kraken/kraken.py        (die Handels-Spur)
     - Agenten/MCP-Server/kraken/kraken_mcp.py (der MCP-Server)
   Jedes erhob die nonce unabhaengig mit `time.time()*1e6`. Laeuft beides
   parallel, ueberholt der spaetere den frueheren und Kraken antwortet
   "EAPI:Invalid nonce". Deshalb: EINE hier zentralisierte Erhoehung ueber
   eine exklusiv erzeugte Sperrdatei (Lesen-Erhoehen-Schreiben atomar).

2. ZUKUNFTSGRENZE. Eine lokale Uhr, die der Kraken-Serverzeit voreilt, erzeugt
   Wallclock-nonces, die Kraken als "zu weit in der Zukunft" ablehnen kann.
   Der gemeinsame Zaehler haelt die Werte streng steigend; ob die lokale Uhr
   vor- oder nachlaeuft, gleicht sich ueber die Monotonie aus.

Nur Standardbibliothek, damit auch der MCP-Server (anderes venv) es laden
kann. Die nonce-Datei (.kraken_nonce) ist ueber die .gitignore-Wildcard
(Zeile 20) ausgeschlossen und liegt nie im Repo.
"""

import os
import time

_DATEI = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".kraken_nonce")
_SPERRE = _DATEI + ".lock"


def monotone_nonce() -> int:
    """Naechster nonce: streng steigende monotone Wallclock (bewaehrte Logik).

    EINHEIT: NANOSEKUNDEN (seit 22.09.2026; vorher Mikrosekunden).
    Anlass: die kraken-cli (offizielles Kraken-Werkzeug) signiert mit
    Nanosekunden. Kraken merkt sich je Schluessel den HOECHSTEN gesehenen
    Wert; danach war jeder Mikrosekunden-nonce rund tausendfach kleiner und
    JEDE Hausabfrage endete mit "EAPI:Invalid nonce" - der Ausfall traf sofort
    die Live-Sperre von mosaic und die kraken-Spur. Die Einheit muss also
    mindestens die groesste sein, die ein Werkzeug auf denselben Schluessel
    sendet. Nanosekunden sind belegt: die CLI arbeitet im Betrieb damit.
    """
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
        # max() haelt die Datei monoton ueber NTP-Rueckspruenge hinweg.
        nonce = max(int(time.time() * 1_000_000_000), letzter + 1)
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

def vorwaerts(sekunden: float = 1.0) -> int:
    """Den gemeinsamen Zaehler um <sekunden> vor die JETZIGE Zeit schieben.

    ANLASS (gemessen 24.09.2026): Kraken merkt sich je Schluessel den HOECHSTEN
    gesehenen nonce. Setzt ein Werkzeug, das diesen Pool NICHT benutzt, einen
    hoeheren Wert (die offizielle kraken-cli signiert in Nanosekunden aus ihrer
    eigenen Uhr), ist jeder Pool-Wert darunter und Kraken antwortet
    "EAPI:Invalid nonce" - auch bei streng monotonen eigenen Werten. Ein
    einfacher Wiederholversuch mit demselben Wert hilft dann nicht.

    Der neue Wert wird IN DIE DATEI geschrieben, damit die Monotonie erhalten
    bleibt: sonst waere der naechste normale Aufruf wieder zu niedrig.
    """
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
        jetzt = int(time.time() * 1_000_000_000)
        nonce = max(jetzt, letzter) + int(sekunden * 1_000_000_000)
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
