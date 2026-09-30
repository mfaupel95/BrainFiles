"""Laeuft der omnitrade-Lauf wirklich noch? - rein lesend, eine Antwort.

WARUM DIESE DATEI EXISTIERT
---------------------------
Die Statusdatei `status/live.json` bleibt nach einem harten Ende auf
`"state": "running"` mit einer TOTEN PID stehen (30.09.2026 mehrfach erlebt).
Wer nur die Datei liest, glaubt an einen laufenden Handel. Umgekehrt ist die
Prozessliste allein kein Beweis: dasselbe Programm `omnitrade-cli.exe` faehrt
auch `backtest --script ...` - ein Backtest sieht dann aus wie "es laeuft
schon" und sperrt den echten Start (30.09.2026 erlebt).

Deshalb entscheidet diese Datei die Frage an ZWEI Zeugen:
  1. Statusdatei: Zustand, Alter, PID  (aus `omnitrade_bridge.lage()`)
  2. Prozessliste: lebt genau diese PID?

Aufruf:  python omnitrade_lauf.py        -> eine Zeile, Exit 0 = laeuft, 1 = nein
Rahmen:  nur lesen, wirft nie, kein Netz.
"""

import os
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import omnitrade_bridge as bruecke  # noqa: E402  (gleicher Ordner, Pfad oben gesetzt)

# Eine Statusdatei, die aelter ist als das, was omnitrade selbst als verdaechtig
# ansieht, plus Reserve: 1m-Kerzen schreiben jede Minute.
ALT_GRENZE_S = 300.0


def _tasklist():
    sysroot = os.environ.get("SystemRoot") or r"C:\Windows"
    return os.path.join(sysroot, "System32", "tasklist.exe")


def pid_lebt(pid):
    """True, wenn genau diese PID in der Prozessliste steht. Nie werfen."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        aus = subprocess.run(
            [_tasklist(), "/FI", "PID eq %d" % pid, "/NH"],
            capture_output=True, timeout=30,
        )
    except Exception:
        return False
    # tasklist schreibt in der Konsolencodepage (nicht UTF-8) - die PID ist
    # ASCII, deshalb genuegt ein fehlertolerantes Dekodieren.
    text = (aus.stdout or b"").decode("utf-8", "replace")
    return str(pid) in text


def beurteile(lage=None, lebt=pid_lebt, alt_grenze_s=ALT_GRENZE_S):
    """Entscheidet, ob der Lauf laeuft. `lebt`/`lage` sind fuer Tests da."""
    lage = lage if lage is not None else bruecke.lage()
    pid = lage.get("pid")
    ergebnis = {"laeuft": False, "grund": "", "pid": pid, "alter_s": lage.get("alter_s")}
    if not lage.get("ok"):
        ergebnis["grund"] = "keine Statusdatei (%s)" % (lage.get("fehler") or "fehlt")
        return ergebnis
    if lage.get("state") != "running":
        ergebnis["grund"] = "Zustand ist %r, nicht running" % lage.get("state")
        return ergebnis
    if not lebt(pid):
        ergebnis["grund"] = "PID %s aus der Statusdatei lebt nicht (Stand bleibt stehen)" % pid
        return ergebnis
    alter = lage.get("alter_s")
    if alter is not None and alter > alt_grenze_s:
        ergebnis["grund"] = "Statusdatei ist %.0f s alt (Grenze %.0f s), PID lebt" % (alter, alt_grenze_s)
        return ergebnis
    ergebnis["laeuft"] = True
    ergebnis["grund"] = "laeuft, PID %s, Statusdatei %.0f s alt" % (pid, alter or 0.0)
    return ergebnis


def main():
    u = beurteile()
    print(("LAEUFT: " if u["laeuft"] else "LAEUFT NICHT: ") + u["grund"])
    return 0 if u["laeuft"] else 1


if __name__ == "__main__":
    sys.exit(main())