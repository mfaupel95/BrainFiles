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

# Untergrenze fuer das Alter der Statusdatei. Der Lauf schreibt sie NUR, wenn er
# eine Kerze verarbeitet - bei `--interval 1h` also stuendlich (30.09.2026: eine
# stuendliche Sitzung stand 13 Minuten still und wurde faelschlich fuer tot
# erklaert). Deshalb wird die Grenze aus dem Intervall des laufenden Prozesses
# gerechnet, nicht geraten.
ALT_GRENZE_S = 300.0
INTERVALL_VORGABE_S = 60.0  # Vorgabe der CLI: --interval 1m
VIELFACHES = 2.5  # so oft das Intervall darf die Datei alt sein, bevor sie haengt


def _tasklist():
    sysroot = os.environ.get("SystemRoot") or r"C:\Windows"
    return os.path.join(sysroot, "System32", "tasklist.exe")


def _powershell():
    sysroot = os.environ.get("SystemRoot") or r"C:\Windows"
    return os.path.join(sysroot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")


def kommandozeile(pid):
    """Kommandozeile des Prozesses, "" wenn nicht ermittelbar. Nie werfen."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return ""
    if pid <= 0:
        return ""
    try:
        aus = subprocess.run(
            [_powershell(), "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter 'ProcessId=%d').CommandLine" % pid],
            capture_output=True, timeout=40,
        )
    except Exception:
        return ""
    return (aus.stdout or b"").decode("utf-8", "replace").strip()


def intervall_s(zeile):
    """Kerzenlaenge aus der Kommandozeile: '1m', '15m', '1h', '4h', '1d'.
    Ohne Angabe gilt die Vorgabe der CLI (1m). Unlesbares faellt auf die
    Vorgabe zurueck - geraten wird nicht."""
    if not zeile:
        return INTERVALL_VORGABE_S
    teile = zeile.replace('"', " ").split()
    for i, t in enumerate(teile):
        if t == "--interval" and i + 1 < len(teile):
            wert = teile[i + 1].strip().lower()
        elif t.startswith("--interval="):
            wert = t.split("=", 1)[1].strip().lower()
        else:
            continue
        ziffern = "".join(c for c in wert if c.isdigit())
        einheit = "".join(c for c in wert if c.isalpha())
        if not ziffern:
            return INTERVALL_VORGABE_S
        faktor = {"s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}.get(einheit, 60.0)
        return float(ziffern) * faktor
    return INTERVALL_VORGABE_S


def altersgrenze_s(pid, zeile=None, vielfaches=VIELFACHES):
    """Wie alt darf die Statusdatei werden, ohne dass es ein Haenger ist?
    Rueckfall, wenn die Statusdatei selbst keinen Kerzenabstand hergibt."""
    if zeile is None:
        zeile = kommandozeile(pid)
    return max(ALT_GRENZE_S, vielfaches * intervall_s(zeile))


def grenze_aus_datei(daten, pid=None):
    """Grenze aus der Statusdatei (Kerzenabstand) - das ist dieselbe Quelle, die
    auch die Handelszentrale liest. Nur wenn die Datei keinen Abstand hergibt,
    wird das Intervall aus der Kommandozeile des Prozesses geholt."""
    try:
        grenze = bruecke.altersgrenze_s(daten)
    except Exception:
        grenze = ALT_GRENZE_S
    if grenze > ALT_GRENZE_S:
        return grenze
    return altersgrenze_s(pid)


def pid_lebt(pid, name=None):
    """True, wenn genau diese PID in der Prozessliste steht. Nie werfen.

    `name` (optional) verlangt zusaetzlich, dass der Prozess dieses Programm
    ist. WARUM DAS NOETIG IST (30.09.2026 gemessen): Windows vergibt PIDs neu.
    Eine Statusdatei mit `state: running` und PID 2024 liess das Startwerkzeug
    "laeuft schon" melden - PID 2024 gehoerte inzwischen `csrss.exe`, der
    omnitrade-Lauf war seit 4,5 Stunden tot. Eine reine Existenzpruefung haelt
    einen Wiederverwendungsfall fuer einen lebenden Lauf.
    """
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
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
    except Exception:
        return False
    # tasklist schreibt in der Konsolencodepage (nicht UTF-8) - die PID ist
    # ASCII, deshalb genuegt ein fehlertolerantes Dekodieren.
    text = (aus.stdout or b"").decode("utf-8", "replace")
    if str(pid) not in text:
        return False
    if name and str(name).lower() not in text.lower():
        return False
    return True


def beurteile(lage=None, lebt=pid_lebt, alt_grenze_s=None, grenze_fuer=grenze_aus_datei):
    """Entscheidet, ob der Lauf laeuft. `lebt`/`lage`/`grenze_fuer` sind fuer Tests da.

    Reihenfolge der Zeugen: erst die Datei (Zustand), dann die PID (der harte
    Zeuge), zuletzt das Alter gegen die aus dem Intervall gerechnete Grenze.
    """
    lage = lage if lage is not None else bruecke.lage(veraltet_s=float("inf"))
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
    if alt_grenze_s is None:
        alt_grenze_s = grenze_fuer(lage, pid)
    alter = lage.get("alter_s")
    if alter is not None and alter > alt_grenze_s:
        ergebnis["grund"] = ("Statusdatei ist %.0f s alt (Grenze %.0f s aus dem Intervall), "
                             "PID %s lebt - der Lauf haengt" % (alter, alt_grenze_s, pid))
        return ergebnis
    ergebnis["laeuft"] = True
    ergebnis["alter_s"] = alter
    ergebnis["grund"] = ("laeuft, PID %s, Statusdatei %.0f s alt (Grenze %.0f s)"
                         % (pid, alter or 0.0, alt_grenze_s))
    return ergebnis


def main():
    u = beurteile()
    print(("LAEUFT: " if u["laeuft"] else "LAEUFT NICHT: ") + u["grund"])
    return 0 if u["laeuft"] else 1


if __name__ == "__main__":
    sys.exit(main())