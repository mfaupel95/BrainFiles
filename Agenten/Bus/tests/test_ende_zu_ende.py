"""Nimmt die vier 'Fertig, wenn'-Punkte der Spec ab. Startet einen echten
Bus mit einem Melder-Doppelgaenger auf einem freien Port.
Direkt ausfuehrbar: python tests/test_ende_zu_ende.py
"""
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auffaellig  # noqa: E402
import bus         # noqa: E402
import ereignis    # noqa: E402
import journal     # noqa: E402
import sprecher    # noqa: E402

BUS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Doppelgaenger:
    def __init__(self):
        self.gesendet = []

    def sende(self, text, stumm=False):
        self.gesendet.append(text)
        return True


def test_fehler_erreicht_das_handy_binnen_einer_minute():
    with tempfile.TemporaryDirectory() as w:
        q, d = queue.Queue(), Doppelgaenger()
        srv = bus.starte(port=0, wurzel=w, warteschlange=q)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        s = sprecher.Sprecher(d, auffaellig.regeln(), wurzel=w,
                              stand=os.path.join(w, "stand.json"))
        threading.Thread(target=s.lauf, args=(q,), daemon=True).start()
        try:
            ereignis.melden(journal.neu("routine/probe", "ende", code=9,
                                        dauer_s=1),
                            port=srv.server_address[1], wurzel=w)
            for _ in range(60):
                if d.gesendet:
                    break
                time.sleep(1)
            assert d.gesendet, "nichts gemeldet"
            assert "9" in d.gesendet[0]
        finally:
            srv.shutdown()


def test_toter_bus_laesst_die_routine_durchlaufen():
    with tempfile.TemporaryDirectory() as w:
        a = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command",
             "$env:BUS_JOURNAL='%s'; $env:BUS_PORT='1'; . '%s'; "
             "$m = Melde-Start -Wer 'routine/sicherung'; "
             "Start-Sleep -Milliseconds 100; "
             "Melde-Ende -Marke $m -Code 0; Write-Output 'fertig'"
             % (w.replace("'", "''"),
                os.path.join(BUS, "Ereignis.ps1").replace("'", "''"))],
            capture_output=True, text=True, timeout=60)
        assert a.returncode == 0 and "fertig" in a.stdout, a.stderr
        # Die Zeilen stehen trotzdem im Journal - das ist der ganze Punkt.
        assert len(journal.lesen(wurzel=w)) == 2


def test_alle_modultests_laufen():
    for name in ("test_journal", "test_bus", "test_ereignis",
                 "test_ereignis_ps1", "test_auffaellig", "test_sprecher",
                 "test_anbindung_handel", "test_anbindung_routinen",
                 "test_fremdarbeit_einziehen"):
        a = subprocess.run([sys.executable,
                            os.path.join(BUS, "tests", name + ".py")],
                           capture_output=True, text=True, cwd=BUS, timeout=300)
        assert a.returncode == 0, "%s:\n%s\n%s" % (name, a.stdout, a.stderr)


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("Ende-zu-Ende bestanden")
