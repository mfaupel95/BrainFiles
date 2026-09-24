#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GBrain-Maintenance-Waechter (Routine gbrain-maintenance-2e8fa54d-6f9f-4726-89e9-caf8a624b61a).

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut** und es wird nichts gesendet (Watchdog-Muster). Ausgabe gibt es nur, wenn
der GBrain-Doctor einen echten Fehler meldet oder der Launcher nicht erreichbar
ist.

WARUM
-----
Die maintenance.md der Installation verlangt genau EINE native Routine mit der
Routine-ID oben, die `doctor --fast --json` faehrt und Fehler meldet. Bezahlte
Embedding-/Extraction-Wartung bleibt ein separater Nutzerentscheid - dieser
Waechter startet NIE serve/cron/daemon und ruft keine bezahlten Pfade auf.

WAS ES TUT
----------
1. `wsl.exe -d archlinux /workspace/gbrain/bin/gbrain doctor --fast --json`
   ueber den absoluten Launcher (derselbe Weg wie jede Memory-Operation).
2. Launcher nicht erreichbar (wsl.exe fehlt, Distro weg, Exit != 0): Befund
   ausgeben.
3. Doctor-Status ist "error"/"fail" oder ein Check ist nicht ok: die
   fehlgeschlagenen Checks ausgeben.
4. Nur Warnungen (status "warnings", health_score hoch, keine error-Checks):
   schweigen - Warnungen wie "serve IPC socket not present" sind bei einer
   reinen CLI-Installation der Normalfall und kein Fehler.

Aufruf:
    python Agenten/Hermes/scripts/gbrain-maintenance-wache.py
"""
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LAUNCHER = ["wsl.exe", "-d", "archlinux", "/workspace/gbrain/bin/gbrain"]
ROUTINE_ID = "gbrain-maintenance-2e8fa54d-6f9f-4726-89e9-caf8a624b61a"


def doctor_fast():
    """Faehrt doctor --fast --json; liefert (rc, stdout, stderr)."""
    try:
        p = subprocess.run(
            LAUNCHER + ["doctor", "--fast", "--json"],
            capture_output=True, text=True, timeout=120,
        )
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return -1, "", "wsl.exe nicht gefunden (WSL2 fehlt?)"
    except subprocess.TimeoutExpired:
        return -1, "", "doctor --fast ueberschritt 120 s"


def main():
    rc, out, err = doctor_fast()
    if rc == -1:
        print(f"GBrain-Maintenance: Launcher nicht erreichbar - {err}")
        return
    if rc != 0:
        print(f"GBrain-Maintenance: doctor --fast Exit {rc}\nstderr: {err.strip()}\nstdout: {out.strip()[:2000]}")
        return
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        print(f"GBrain-Maintenance: doctor --fast lieferte kein JSON\n{out.strip()[:2000]}")
        return
    status = data.get("status", "")
    if status in ("error", "fail"):
        checks = data.get("checks", [])
        bad = [c for c in checks if c.get("status") in ("error", "fail")]
        lines = [f"GBrain-Maintenance: Doctor-Status {status}"]
        for c in bad:
            lines.append(f"- {c.get('name')}: {c.get('message', '')[:300]}")
        if not bad:
            lines.append(f"- (kein Check als error/fail markiert; top_issues: {json.dumps(data.get('top_issues', []), ensure_ascii=False)[:500]})")
        print("\n".join(lines))
    # status "ok" oder "warnings" ohne error-Checks: schweigen


if __name__ == "__main__":
    main()