# Hermes-Doctor: separate Claude-Code-Session zur Diagnose/Reparatur des Hermes-Checkouts
#
# Laeuft auf Zuruf (Skill hermes-doctor) oder als woechentlicher Diagnose-Cron.
# Grundidee (aus dem "Claude Code als Hermes Doctor"-Thread): ein separates
# Claude-Code-CLI-Prozess, das den Hermes-Checkout untersucht und Fehler findet,
# waehrend Hermes selbst der ausfuehrende und kommunizierende Agent bleibt.
#
# ZWEI MODI
# ---------
# --diagnose (STANDARD, sicher): rein lesend. Sammelt Befunde (hermes doctor,
#   git-Status, Log-Fehler), optional mit --claude zur Ursachen-Analyse durch
#   Claude Code (nur Read-Tools). Schreibt befund.json + Bericht. Fasst den
#   Live-Checkout NICHT an, startet/stoppt nichts, liest keine Secrets.
#
# --repair (explizit, opt-in): legt ein git-worktree vom Checkout an, kopiert
#   doctor-context.md als CLAUDE.md hinein und laesst Claude Code dort mit
#   Edit/Write/Bash(git*)/Bash(pytest*) arbeiten. Der Fix-Branch bleibt zur
#   Pruefung stehen; das Worktree wird entfernt. Der Live-Checkout bleibt
#   unberuehrt. --aufgabe ueberschreibt die Standard-Reparatur mit einer
#   eigenen Aufgabe (z.B. harmloser Test: nur zaehlen, kein Code aendern).
#
# --report: kompakte Telegram-taugliche Zusammenfassung auf stdout (fuer den
#   woechentlichen Diagnose-Cron; no_agent liefert stdout verbatim).
#
# Aufruf:
#   python Agenten/Hermes/scripts/hermes-doctor.py --diagnose
#   python Agenten/Hermes/scripts/hermes-doctor.py --diagnose --claude
#   python Agenten/Hermes/scripts/hermes-doctor.py --repair --max-turns 15
#   python Agenten/Hermes/scripts/hermes-doctor.py --repair --aufgabe "..."
#   python Agenten/Hermes/scripts/hermes-doctor.py --report
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                 # Agenten/Hermes/scripts -> BrainFiles
HERMES_HOME = WURZEL / "Agenten" / "Hermes"
CHECKOUT = HERMES_HOME / "hermes-agent"
VENV_PY = CHECKOUT / "venv" / "Scripts" / "python.exe"
WORKTREES = HERMES_HOME / ".doctor-worktrees"
LOGS = HERMES_HOME / "logs"
CONTEXT = HIER.parent / "doctor-context.md"
SCHEMA = HIER.parent / "befund-schema.json"


def claude_pfad():
    """claude-CLI aufloesen. subprocess braucht den ABSOLUTEN Pfad (blosser
    Name scheitert auf Windows mit WinError 2, obwohl 'claude' auf PATH ist)."""
    gefunden = shutil.which("claude") or shutil.which("claude.cmd")
    if gefunden:
        return gefunden
    # Rueckfall: npm-global-Verzeichnis
    for kandidat in (
        Path.home() / "AppData" / "Roaming" / "npm" / "claude.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "claude",
    ):
        if kandidat.exists():
            return str(kandidat)
    return "claude"


CLAUDE = claude_pfad()

# Dateien, die der Doctor NIE lesen oder anfassen darf.
GESPERRT = (".env", "auth.json", "state.db", "Zugaenge.md", "OKX_API.env")


def saubere_umgebung():
    """PYTHONHOME/PYTHONPATH entfernen (Falle: uv-venv vergiftet Kinder)."""
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    return env


def lauf(cmd, cwd=None, timeout=120, env=None):
    """subprocess.run mit sauberer Umgebung; gibt (rc, stdout, stderr) zurueck."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, env=env or saubere_umgebung())
        return r.returncode, (r.stdout or ""), (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "", "Timeout nach %ds" % timeout
    except OSError as e:
        return 127, "", str(e)


def hermes_doctor():
    """`hermes doctor` (Integritaets-Check) ueber das venv-python, rein lesend."""
    if not VENV_PY.exists():
        return "venv fehlt: %s" % VENV_PY
    rc, out, err = lauf([str(VENV_PY), "-m", "hermes_cli.main", "doctor"],
                        cwd=str(CHECKOUT), timeout=180)
    return (out or err or "").strip() or "hermes doctor: Exit %d (leer)" % rc


def git_status():
    """Zweig, uncommittete Aenderungen, Commits hinter origin. Rein lesend."""
    zeilen = []
    rc, out, _ = lauf(["git", "-C", str(CHECKOUT), "status", "--porcelain"])
    n = len([l for l in out.splitlines() if l.strip()]) if out.strip() else 0
    zeilen.append("uncommittet: %d Datei(en)" % n)
    if out.strip():
        zeilen.append("  " + out.strip().replace("\n", "\n  "))
    rc, out, _ = lauf(["git", "-C", str(CHECKOUT), "rev-parse", "--abbrev-ref", "HEAD"])
    zeilen.append("Zweig: %s" % out.strip())
    rc, out, _ = lauf(["git", "-C", str(CHECKOUT), "rev-list", "--count",
                       "HEAD..origin/main"])
    if rc == 0 and out.strip().isdigit():
        zeilen.append("Commits hinter origin/main: %s" % out.strip())
    return "\n".join(zeilen)


def log_fehler(zeilen=60):
    """Letzte Zeilen des Gateway-Logs auf CRITICAL/ERROR/Traceback pruefen."""
    log = LOGS / "gateway.log"
    if not log.exists():
        return "kein gateway.log unter %s" % LOGS
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return "gateway.log nicht lesbar: %s" % e
    letzte = text.splitlines()[-zeilen:]
    treffer = [l for l in letzte if re.search(r"CRITICAL|ERROR|Traceback|Exception", l)]
    if not treffer:
        return "letzte %d Zeilen gateway.log: keine CRITICAL/ERROR/Traceback" % zeilen
    return "letzte %d Zeilen gateway.log - %d Fehlerzeile(n):\n  %s" % (
        zeilen, len(treffer), "\n  ".join(treffer[:10]))


def befund_roh_sammeln():
    """Mechanische, deterministische Befunde ohne Claude."""
    return {
        "zeitpunkt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "checkout": str(CHECKOUT),
        "hermes_doctor": hermes_doctor(),
        "git_status": git_status(),
        "log_fehler": log_fehler(),
    }


def claude_prompt(befund_roh, modus, aufgabe=None):
    """Prompt fuer Claude Code. modus='diagnose' -> nur Read; 'repair' -> Edit/Write.
    aufgabe (nur repair): ueberschreibt die Standard-Reparatur-Anweisung mit
    einer eigenen Aufgabe (z.B. harmloser Test: nur zaehlen, kein Code aendern)."""
    kontext = CONTEXT.read_text(encoding="utf-8") if CONTEXT.exists() else ""
    if modus == "diagnose":
        return (
            "Du bist der Hermes-Doctor. Analysiere die folgenden Befunde des "
            "Hermes-Checkouts und finde Ursachen. Du darfst NUR lesen "
            "(Read-Tools), nichts aendern, nichts starten/stoppen, keine "
            "Secrets (.env, auth.json, state.db) lesen.\n\n"
            "BEFUNDE:\n%s\n\n"
            "ARBEITSREGELN:\n%s\n\n"
            "Antworte als JSON mit den Feldern: befunde (Liste von "
            "{schwere, bereich, beschreibung, ursache, empfohlener_fix}), "
            "aenderungen (leer), tests (leer), verbote_verletzt (leer)."
            % (json.dumps(befund_roh, ensure_ascii=False, indent=2), kontext)
        )
    if aufgabe:
        return (
            "Du bist der Hermes-Doctor im Reparaturmodus. Du arbeitest in einem "
            "git-worktree des Hermes-Checkouts.\n\n"
            "AUFGABE:\n%s\n\n"
            "ARBEITSREGELN:\n%s\n\n"
            "Schreibe am Ende befund.json in das Worktree-Wurzelverzeichnis mit "
            "den Feldern: befunde, aenderungen (Liste geaenderter Dateien), "
            "tests (Liste ausgefuehrter Tests), verbote_verletzt."
            % (aufgabe, kontext)
        )
    return (
        "Du bist der Hermes-Doctor im Reparaturmodus. Du arbeitest in einem "
        "git-worktree des Hermes-Checkouts. Behebe die folgenden Befunde, "
        "fuehre Tests aus und committe die Aenderungen im Worktree. "
        "Du darfst NUR das Worktree veraendern, niemals pushen, niemals "
        "hermes update ausfuehren, niemals Secrets lesen.\n\n"
        "BEFUNDE:\n%s\n\n"
        "ARBEITSREGELN:\n%s\n\n"
        "Schreibe am Ende befund.json in das Worktree-Wurzelverzeichnis mit "
        "den Feldern: befunde, aenderungen (Liste geaenderter Dateien), "
        "tests (Liste ausgefuehrter Tests), verbote_verletzt."
        % (json.dumps(befund_roh, ensure_ascii=False, indent=2), kontext)
    )


def claude_ausfuehren(prompt, modus, max_turns, cwd=None):
    """claude -p aufrufen; gibt (rc, text) zurueck. Der Prompt wird per stdin
    gepipt (Windows-Befehlszeilenlimit ~32k Zeichen), nicht als Argument.
    cwd: Arbeitsverzeichnis fuer claude - im repair-Modus das WORKTREE
    (doc_dir), NICHT der Live-Checkout - sonst waere die Isolation aufgehoben."""
    allowed = "Read" if modus == "diagnose" else "Read,Edit,Write,Bash(git*),Bash(pytest*)"
    cmd = [CLAUDE, "-p", "Analysiere den stdin-Inhalt und antworte wie gefordert.",
           "--allowedTools", allowed, "--max-turns", str(max_turns),
           "--output-format", "json"]
    try:
        r = subprocess.run(cmd, cwd=cwd or str(CHECKOUT), input=prompt,
                           capture_output=True, text=True, timeout=600,
                           env=saubere_umgebung())
        return r.returncode, (r.stdout or r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "Timeout nach 600s"
    except OSError as e:
        return 127, str(e)


def claude_gesperrt(text):
    """Erkennt, ob Claude Code wegen Kontingent/Limit nicht antwortet
    (weekly limit / out_of_credits / rate_limit) - dann ist es KEIN
    Skriptfehler, sondern ein Konto-Zustand."""
    t = text.lower()
    if any(k in t for k in ("weekly limit", "out_of_credits", "rate_limit",
                            "credit balance", "overage")):
        return True
    return False


def parse_claude_json(text):
    """claude -p --output-format json -> result-Feld extrahieren."""
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "result" in data:
            return data["result"]
        return text
    except json.JSONDecodeError:
        return text


def schreibe_befund(befund, modus):
    """befund.json nach LOGS schreiben. Gibt den Pfad zurueck."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    LOGS.mkdir(parents=True, exist_ok=True)
    ziel = LOGS / ("hermes-doctor-%s-%s.json" % (modus, stamp))
    ziel.write_text(json.dumps(befund, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return ziel


def repair_worktree(befund_roh, max_turns, aufgabe=None):
    """Reparatur in einem git-worktree. Gibt (befund, fix_branch) zurueck.
    aufgabe: eigene (z.B. harmlose) Aufgabe statt der Standard-Reparatur."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    doc_dir = WORKTREES / stamp
    branch = "doctor-fix-%s" % stamp
    WORKTREES.mkdir(parents=True, exist_ok=True)
    rc, out, err = lauf(["git", "-C", str(CHECKOUT), "worktree", "add",
                         str(doc_dir), "-b", branch], timeout=300)
    if rc != 0:
        return {"fehler": "worktree anlegen: %s" % (err or out)}, None
    try:
        if CONTEXT.exists():
            (doc_dir / "CLAUDE.md").write_text(CONTEXT.read_text(encoding="utf-8"),
                                               encoding="utf-8")
        prompt = claude_prompt(befund_roh, "repair", aufgabe=aufgabe)
        rc, text = claude_ausfuehren(prompt, "repair", max_turns, cwd=str(doc_dir))
        befund = {"claude_rc": rc, "claude_ausgabe": parse_claude_json(text)}
        bf = doc_dir / "befund.json"
        if bf.exists():
            try:
                befund.update(json.loads(bf.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                befund["befund_json_unlesbar"] = True
        return befund, branch
    finally:
        lauf(["git", "-C", str(CHECKOUT), "worktree", "remove", "--force",
              str(doc_dir)], timeout=120)


def bericht(befund_roh, ziel):
    """Kompakte, Telegram-taugliche Zusammenfassung des Diagnose-Befunds."""
    hd = befund_roh.get("hermes_doctor", "")
    ok = "All checks passed" in hd
    warn = hd.count("⚠")
    git = befund_roh.get("git_status", "")
    log = befund_roh.get("log_fehler", "")
    zeilen = [
        "Hermes-Doctor (%s):" % befund_roh.get("zeitpunkt", "?"),
        "- hermes doctor: %s" % ("OK" if ok else "Befund vorhanden"),
    ]
    if warn:
        zeilen.append("- Warnungen: %d" % warn)
    for g in git.splitlines():
        zeilen.append("- git: %s" % g)
    if "keine CRITICAL" in log:
        zeilen.append("- gateway.log: keine Fehler")
    else:
        zeilen.append("- gateway.log: %s" % log.splitlines()[0])
    zeilen.append("- Befund: %s" % ziel)
    return "\n".join(zeilen)


def main():
    ap = argparse.ArgumentParser(description="Hermes-Doctor (Diagnose/Reparatur)")
    ap.add_argument("--diagnose", action="store_true", default=True,
                    help="rein lesende Diagnose (Standard)")
    ap.add_argument("--claude", action="store_true",
                    help="Befunde zusaetzlich durch Claude Code analysieren lassen")
    ap.add_argument("--repair", action="store_true",
                    help="Reparatur in einem git-worktree (opt-in, explizit)")
    ap.add_argument("--max-turns", type=int, default=10,
                    help="claude -p --max-turns (Kosten-/Laufzeit-Deckel)")
    ap.add_argument("--report", action="store_true",
                    help="kompakte Zusammenfassung auf stdout (fuer Cron-Lieferung)")
    ap.add_argument("--aufgabe", default=None,
                    help="eigene Aufgabe fuer --repair statt der Standard-Reparatur "
                         "(z.B. harmloser Test: nur zaehlen, kein Code aendern)")
    args = ap.parse_args()

    if args.repair:
        args.diagnose = False

    befund_roh = befund_roh_sammeln()

    if args.repair:
        befund, branch = repair_worktree(befund_roh, args.max_turns,
                                         aufgabe=args.aufgabe)
        befund["modus"] = "repair"
        befund["fix_branch"] = branch
        befund["roh"] = befund_roh
        ziel = schreibe_befund(befund, "repair")
        print("HERMES-DOCTOR repair fertig. Fix-Branch: %s" % branch)
        print("Befund: %s" % ziel)
        print("Der Fix-Branch liegt zur Pruefung bereit - NICHT automatisch gemergt.")
        return 0

    # Diagnose
    befund = {"modus": "diagnose", "roh": befund_roh}
    if args.claude:
        prompt = claude_prompt(befund_roh, "diagnose")
        rc, text = claude_ausfuehren(prompt, "diagnose", args.max_turns)
        befund["claude_rc"] = rc
        if claude_gesperrt(text):
            befund["claude_gesperrt"] = (
                "Claude Code antwortet nicht: Konto-Kontingent/Limit "
                "(weekly limit / out_of_credits). Mechanische Diagnose "
                "unten ist vollstaendig; die Claude-Analyse laeuft, sobald "
                "das Limit zurueckgesetzt ist.")
        else:
            befund["analyse"] = parse_claude_json(text)
    ziel = schreibe_befund(befund, "diagnose")
    if args.report:
        print(bericht(befund_roh, ziel))
    else:
        print("HERMES-DOCTOR diagnose fertig.")
        print("Befund: %s" % ziel)
        print("hermes doctor: %s" % ("OK" if "All checks passed" in befund_roh["hermes_doctor"] else "Befund vorhanden"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
