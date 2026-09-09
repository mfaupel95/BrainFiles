"""Test fuer bus.py - startet den Dienst auf einem freien Port im eigenen
Prozess und redet ueber localhost mit ihm. Kein Telegram, kein Melder.
Direkt ausfuehrbar: python tests/test_bus.py
"""
import json
import os
import queue
import sys
import tempfile
import threading
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bus       # noqa: E402
import journal   # noqa: E402


def _dienst(wurzel, q):
    srv = bus.starte(port=0, wurzel=wurzel, warteschlange=q)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def _post(port, nutzlast):
    req = urllib.request.Request(
        "http://127.0.0.1:%d/ereignis" % port,
        data=json.dumps(nutzlast).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as a:
        return a.status


def test_nimmt_an_und_schreibt_vor_dem_verteilen():
    with tempfile.TemporaryDirectory() as w:
        q = queue.Queue()
        srv, port = _dienst(w, q)
        try:
            e = journal.neu("handel/xperp", "ende", code=0, dauer_s=3)
            assert _post(port, e) == 200
            # Die Zeile muss auf Platte stehen, sobald die Antwort da ist -
            # das ist die Gegenmassnahme gegen einen Absturz danach.
            zeilen = journal.lesen(wurzel=w)
            assert len(zeilen) == 1 and zeilen[0]["id"] == e["id"]
            assert q.get(timeout=2)["id"] == e["id"]
        finally:
            srv.shutdown()


class PlatzendeSchlange:
    """Warteschlange, die beim Verteilen scheitert. Steht die Zeile danach
    trotzdem im Journal, war zuerst geschrieben worden - genau das ist die
    Zusicherung, an der der ganze Dienst haengt."""

    def put(self, _):
        raise RuntimeError("Verteilen gescheitert")


def test_journal_steht_auch_wenn_das_verteilen_scheitert():
    with tempfile.TemporaryDirectory() as w:
        srv, port = _dienst(w, PlatzendeSchlange())
        try:
            e = journal.neu("handel/xperp", "ende", code=0, dauer_s=3)
            try:
                _post(port, e)
            except (urllib.error.HTTPError, ConnectionError):
                # warteschlange.put() wirft hier unbehandelt - der
                # Handler-Thread bricht ab, die Verbindung faellt weg.
                # Ob der Client einen 500er oder nur den Verbindungsabbruch
                # sieht, ist fuer diesen Test gleichgueltig: entscheidend
                # ist allein, was schon vorher auf Platte stand.
                pass
            zeilen = journal.lesen(wurzel=w)
            assert len(zeilen) == 1 and zeilen[0]["id"] == e["id"]
        finally:
            srv.shutdown()


def test_kein_get_und_kein_fremder_pfad():
    with tempfile.TemporaryDirectory() as w:
        srv, port = _dienst(w, queue.Queue())
        try:
            for auf in ("/ereignis", "/beliebig"):
                try:
                    urllib.request.urlopen(
                        "http://127.0.0.1:%d%s" % (port, auf), timeout=3)
                    raise AssertionError("GET haette scheitern muessen")
                except urllib.error.HTTPError as f:
                    assert f.code in (404, 405), f.code
        finally:
            srv.shutdown()


def test_muell_wird_abgewiesen_ohne_absturz():
    with tempfile.TemporaryDirectory() as w:
        srv, port = _dienst(w, queue.Queue())
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:%d/ereignis" % port, data=b"kein json",
                headers={"Content-Type": "application/json"})
            try:
                urllib.request.urlopen(req, timeout=3)
                raise AssertionError("haette 400 geben muessen")
            except urllib.error.HTTPError as f:
                assert f.code == 400
            assert journal.lesen(wurzel=w) == []
            # Danach muss der Dienst weiterhin arbeiten.
            assert _post(port, journal.neu("a", "start")) == 200
        finally:
            srv.shutdown()


def test_bindet_nur_an_localhost():
    with tempfile.TemporaryDirectory() as w:
        srv, _ = _dienst(w, queue.Queue())
        try:
            assert srv.server_address[0] == "127.0.0.1"
        finally:
            srv.shutdown()


def test_port_kommt_aus_bus_json():
    assert bus.port_aus_datei() == 8787


def test_pid_sperre_laesst_keinen_zweiten_bus_zu():
    # Zwei Sprecher am selben Telegram-Token naehmen sich gegenseitig die
    # Nachrichten weg - davor warnt handel-dauerlauf.ps1 seit jeher.
    with tempfile.TemporaryDirectory() as w:
        echt, bus.PID_DATEI = bus.PID_DATEI, os.path.join(w, "bus.pid")
        try:
            assert bus.pid_sperren() is True        # wir selbst laufen
            assert bus.pid_sperren() is False       # derselbe Prozess: besetzt
            with open(bus.PID_DATEI, "w", encoding="utf-8") as f:
                f.write("999999")                   # tote PID
            assert bus.pid_sperren() is True        # Leiche blockiert nicht
        finally:
            bus.PID_DATEI = echt


def test_gestoertes_laeuft_verhindert_start():
    # Entscheidung "im Zweifel geschlossen": kann _laeuft nicht feststellen,
    # ob der Prozess lebt (tasklist fehlt, PermissionError, Timeout), darf
    # dieser Bus nicht starten. Sonst laufen zwei Busse gleichzeitig und
    # nehmen sich am selben Telegram-Token die Nachrichten weg.
    with tempfile.TemporaryDirectory() as w:
        echt_pid_datei, bus.PID_DATEI = bus.PID_DATEI, os.path.join(w, "bus.pid")
        echt_laeuft = bus._laeuft
        with open(bus.PID_DATEI, "w", encoding="utf-8") as f:
            f.write("999999")     # PID-Datei vorhanden, egal welcher Wert

        def _wirft(_pid):
            raise OSError("tasklist nicht im PATH")

        bus._laeuft = _wirft
        try:
            assert bus.pid_sperren() is False
        finally:
            bus._laeuft = echt_laeuft
            bus.PID_DATEI = echt_pid_datei


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Bus-Tests bestanden")
