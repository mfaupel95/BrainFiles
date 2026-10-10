"""Der Dienst. Nimmt Ereignisse entgegen, schreibt sie fort, gibt sie weiter.

Er fuehrt nichts aus. Ein Ereignis annehmen ist Schreiben, kein Ausloesen -
deshalb braucht er auch keinen Schluessel: das Schlimmste, was ein fremder
lokaler Prozess anrichten kann, ist eine erfundene Journalzeile.

Die Reihenfolge in do_POST ist bindend und der Grund, warum dieser Dienst
ueberhaupt vertretbar ist: erst anhaengen und flushen, dann verteilen. Faellt
er dazwischen aus, steht die Zeile trotzdem auf Platte.
"""

import json
import os
import queue
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import journal

HIER = os.path.dirname(os.path.abspath(__file__))
PID_DATEI = os.path.join(HIER, "bus.pid")
GRENZE = 64 * 1024      # eine Ereigniszeile ist nie groesser


def port_aus_datei():
    with open(os.path.join(HIER, "bus.json"), encoding="utf-8") as f:
        return int(json.load(f)["port"])


def _laeuft(pid):
    try:
        a = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid],
                                   capture_output=True, timeout=10,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except Exception as exc:                                  # noqa: BLE001
        # Im Zweifel geschlossen: koennen wir nicht feststellen, ob der
        # Prozess noch lebt (tasklist fehlt im PATH, PermissionError,
        # Timeout), nehmen wir an, dass er es tut, und lassen diesen Bus
        # nicht starten. Ein nicht gestarteter Bus kostet nichts - die
        # Erzeuger schreiben ihre Zeilen ohnehin selbst ins Journal -,
        # waehrend zwei laufende Busse sich am selben Telegram-Token
        # gegenseitig die Nachrichten wegnehmen. Genau die verkehrte
        # Auslegung war die Ursache des urspruenglichen Fehlers.
        print("bus: _laeuft konnte PID %d nicht pruefen (%s) - "
              "kein Start zur Sicherheit" % (pid, exc), file=sys.stderr)
        return True
    # In Bytes vergleichen: tasklist gibt Umlaute aus, die mit der
    # Konsolen-Codepage nicht immer dekodierbar sind. text=True wuerde
    # einen UnicodeDecodeError werfen.
    return str(pid).encode("ascii") in a.stdout


def pid_sperren():
    """True, wenn wir der einzige Bus sind. Zwei Sprecher am selben Telegram-
    Token naehmen sich gegenseitig die Nachrichten weg."""
    if os.path.exists(PID_DATEI):
        try:
            with open(PID_DATEI, encoding="utf-8") as f:
                alt = int(f.read().strip())
        except (OSError, ValueError):
            alt = None
        if alt:
            try:
                laeuft = _laeuft(alt)
            except Exception as exc:                          # noqa: BLE001
                # Im Zweifel geschlossen, auch wenn _laeuft selbst (etwa
                # weil ausgetauscht oder veraendert) unerwartet durchreicht
                # statt intern abzufangen: kein Start ist die verkraftbare
                # Seite, zwei laufende Busse sind es nicht.
                print("bus: _laeuft warf unerwartet (%s) - kein Start "
                      "zur Sicherheit" % exc, file=sys.stderr)
                return False
            if laeuft:
                return False
    with open(PID_DATEI, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    return True


def _bauen(wurzel, warteschlange):
    class Griff(BaseHTTPRequestHandler):
        def do_POST(self):                                  # noqa: N802
            if self.path != "/ereignis":
                return self._kurz(404)
            try:
                n = int(self.headers.get("Content-Length", 0))
                if n <= 0 or n > GRENZE:
                    return self._kurz(400)
                e = json.loads(self.rfile.read(n).decode("utf-8"))
                if not isinstance(e, dict) or "id" not in e or "wer" not in e:
                    return self._kurz(400)
            except (ValueError, UnicodeDecodeError):
                return self._kurz(400)
            try:
                journal.anhaengen(e, wurzel=wurzel)          # 1. auf Platte
            except OSError:
                return self._kurz(500)
            warteschlange.put(e)                             # 2. erst dann
            self._kurz(200)

        def do_GET(self):                                   # noqa: N802
            self._kurz(405)

        def _kurz(self, code):
            self.send_response(code)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *_):
            pass    # kein Zugriffsprotokoll - das Journal ist das Protokoll

    return Griff


def starte(port=None, wurzel=None, warteschlange=None):
    """Bindet an 127.0.0.1. Serviert erst, wenn der Aufrufer serve_forever()
    ruft - so kann der Test den Port abfragen, bevor etwas laeuft."""
    q = warteschlange if warteschlange is not None else queue.Queue()
    p = port if port is not None else port_aus_datei()
    return ThreadingHTTPServer(("127.0.0.1", p), _bauen(wurzel, q))


def main():
    if not pid_sperren():
        print("Ein Bus laeuft bereits - dieser beendet sich.")
        return 1
    try:
        q = queue.Queue()
        srv = starte(warteschlange=q)
        _sprecher_starten(q)
        print("Bus lauscht auf 127.0.0.1:%d" % srv.server_address[1])
        srv.serve_forever()
    finally:
        try:
            os.remove(PID_DATEI)
        except OSError:
            pass
    return 0


def _sprecher_starten(q):
    """Der Sprecher laeuft als Faden im selben Prozess wie der Bus. Ein
    eigener Prozess braechte einen zweiten Telegram-Sprecher in Reichweite -
    und zwei am selben Token nehmen sich gegenseitig die Nachrichten weg."""
    import auffaellig
    import sprecher
    sys.path.insert(0, os.path.join(HIER, os.pardir, "Handel"))
    import melder                                           # noqa: E402
    s = sprecher.Sprecher(melder, auffaellig.regeln())
    threading.Thread(target=s.lauf, args=(q,), daemon=True).start()


if __name__ == "__main__":
    sys.exit(main())
