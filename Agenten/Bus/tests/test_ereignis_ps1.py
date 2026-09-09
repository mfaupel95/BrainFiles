"""Test fuer Ereignis.ps1 - ruft PowerShell wirklich auf, mit totem Bus,
und prueft, was danach im Journal steht.
Direkt ausfuehrbar: python tests/test_ereignis_ps1.py
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal  # noqa: E402

BUS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PS1 = os.path.join(BUS, "Ereignis.ps1")


def _ps(skript, wurzel):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
         "$env:BUS_JOURNAL='%s'; $env:BUS_PORT='1'; . '%s'; %s"
         % (wurzel.replace("'", "''"), PS1.replace("'", "''"), skript)],
        capture_output=True, text=True, timeout=60)


def test_start_und_ende_landen_im_journal():
    with tempfile.TemporaryDirectory() as w:
        a = _ps("$m = Melde-Start -Wer 'routine/sicherung'; "
                "Melde-Ende -Marke $m -Code 0", w)
        assert a.returncode == 0, a.stderr
        z = journal.lesen(wurzel=w)
        assert [e["was"] for e in z] == ["start", "ende"], z
        assert z[1]["code"] == 0 and z[1]["wer"] == "routine/sicherung"


def test_fehlercode_kommt_durch():
    with tempfile.TemporaryDirectory() as w:
        _ps("$m = Melde-Start -Wer 'routine/zweitkopie'; "
            "Melde-Ende -Marke $m -Code 11 -Text 'robocopy 11'", w)
        z = journal.lesen(wurzel=w)
        assert z[1]["code"] == 11 and "robocopy" in z[1]["text"]


def test_toter_bus_bricht_das_skript_nicht_ab():
    # Genau der Fall aus der Spec: der Lauf muss weiterlaufen.
    with tempfile.TemporaryDirectory() as w:
        a = _ps("$ErrorActionPreference='Stop'; "
                "$m = Melde-Start -Wer 'a'; Write-Output 'weiter'", w)
        assert a.returncode == 0, a.stderr
        assert "weiter" in a.stdout
        # Das eigentliche Versprechen: trotz totem Bus (Port 1, niemand
        # hoert zu) landet die Zeile im Journal - Melde-Start faellt auf
        # den Journalfallback zurueck statt einfach nichts zu tun.
        z = journal.lesen(wurzel=w)
        assert [e["was"] for e in z] == ["start"], z
        assert z[0]["wer"] == "a"


def test_nicht_anlegbarer_journalordner_bleibt_still():
    # Befund 1: ein Cmdlet-Fehler (Laufwerk existiert nicht) darf nicht als
    # rohe PowerShell-Ausnahme auf stderr landen, auch wenn der Aufrufer
    # mit $ErrorActionPreference='Stop' arbeitet.
    with tempfile.TemporaryDirectory() as w:
        a = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
             "$env:BUS_JOURNAL='Z:\\nicht-vorhanden\\journal'; $env:BUS_PORT='1'; "
             ". '%s'; $ErrorActionPreference='Stop'; "
             "$m = Melde-Start -Wer 'a'; Write-Output 'weiter'" % PS1.replace("'", "''")],
            capture_output=True, text=True, timeout=60)
        assert a.returncode == 0, a.stderr
        assert "weiter" in a.stdout
        assert a.stderr == "", a.stderr


def test_log_ist_null_ohne_minus_log():
    # Befund 3: log soll null sein, nicht "", wenn -Log fehlt - sonst
    # muesste Teilprojekt 2 beide Faelle gesondert behandeln.
    with tempfile.TemporaryDirectory() as w:
        _ps("$m = Melde-Start -Wer 'routine/ohne-log'", w)
        z = journal.lesen(wurzel=w)
        assert z[0]["log"] is None, z[0]


def test_log_pfad_wird_uebernommen():
    with tempfile.TemporaryDirectory() as w:
        _ps("$m = Melde-Start -Wer 'routine/sicherung' "
            "-Log 'Agenten/Routinen/logs/sicherung-letzter-lauf.log'; "
            "Melde-Ende -Marke $m -Code 0", w)
        z = journal.lesen(wurzel=w)
        assert z[1]["log"].endswith("sicherung-letzter-lauf.log"), z[1]


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Ereignis.ps1-Tests bestanden")
