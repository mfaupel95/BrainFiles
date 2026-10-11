"""PreToolUse-Hook fuer `Bash` des handels-disponent - Erlaubnisliste statt Selbstverpflichtung.

Liest das Hook-JSON von stdin (`tool_input.command`). Exitcode 0 = erlaubt,
Exitcode 2 = gesperrt (Grund auf stderr, geht an den Agenten zurueck).

Erlaubt (jeweils genau EIN Befehl, keine Verkettung):
  python [-I] <pfad>/xperp/bot.py [Argumente ohne Schalter fuer Ausfuehrung]   frischer Kurs
  python [-I] <pfad>/xperp/handeln.py --vorschau [weitere Argumente]           Trockenlauf
Alles andere wird gesperrt - auch `--live`, `--papier`, `--wachen`, Pipes,
`;`, `&&`, `||`, Umleitungen, `$(...)` und Backticks.

Aktiv ist der Hook erst, wenn er verdrahtet ist (siehe HOOK-EINRICHTEN.md).
"""
import json
import re
import shlex
import sys

VERBOTEN_ZEICHEN = re.compile(r"[;&|<>`]|\$\(|\n")
VERBOTENE_SCHALTER = {"--live", "--papier", "--wachen", "--ausfuehren", "--order"}
PYTHON = re.compile(r"(^|[\/])python(\d(\.\d+)?)?(\.exe)?$", re.I)


def bewerte(befehl):
    """(erlaubt, grund)"""
    if VERBOTEN_ZEICHEN.search(befehl):
        return False, "Verkettung, Pipe, Umleitung oder Unterbefehl ist nicht erlaubt"
    try:
        t = shlex.split(befehl, posix=True)
    except ValueError as e:
        return False, "Befehl nicht lesbar: %s" % e
    if not t or not PYTHON.search(t[0].replace("\\", "/")):
        return False, "nur `python <skript>` ist erlaubt"
    args = [a for a in t[1:] if a != "-I"]
    if not args:
        return False, "kein Skript angegeben"
    skript = args[0].replace("\\", "/")
    rest = args[1:]
    schalter = {a for a in rest if a.startswith("--")}
    if schalter & VERBOTENE_SCHALTER:
        return False, "Schalter nicht erlaubt: " + ", ".join(sorted(schalter & VERBOTENE_SCHALTER))
    if skript.endswith("xperp/bot.py") or skript == "bot.py":
        return True, "frischer Kurs"
    if skript.endswith("xperp/handeln.py"):
        if "--vorschau" in rest:
            return True, "Trockenlauf"
        return False, "handeln.py nur mit --vorschau"
    return False, "Skript nicht auf der Erlaubnisliste: " + skript


def main():
    try:
        daten = json.load(sys.stdin)
        befehl = (daten.get("tool_input") or {}).get("command") or ""
    except Exception as e:
        print("Hook-Eingabe nicht lesbar: %s" % e, file=sys.stderr)
        return 2
    ok, grund = bewerte(befehl)
    if ok:
        return 0
    print("Disponent-Bash gesperrt: %s" % grund, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
