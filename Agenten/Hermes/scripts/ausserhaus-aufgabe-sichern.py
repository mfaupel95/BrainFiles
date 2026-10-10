#!/usr/bin/env python3
"""Sorgt dafuer, dass die Windows-Aufgabe 'MaxHirn-Ausserhaus-Kopie' existiert.

WARUM ES DIESES SKRIPT GIBT (30.09.2026):
Die Aufgabe taeglich 21:30 (Agenten/Routinen/ausserhaus-kopie-aufgabe.ps1)
erneuert die Ausser-Haus-Kopie auf Q:, wenn die Platte angesteckt ist. Wird sie
aus einer Sandbox heraus angelegt (Hermes-Terminal im Container), ist sie im
Aufgaben-Speicher dieser Sandbox sichtbar, aber NICHT auf dem Rechner: sie
verschwindet, sobald die Sandbox wechselt. Ein HERMES-CRON laeuft dagegen im
Gateway, also auf dem RECHTEN Rechner - deshalb legt dieses Skript die Aufgabe
von dort aus an und prueft sie taeglich nach.

Verhalten: existiert die Aufgabe, gibt es KEINE Ausgabe (dann sendet der Cron
nichts). Fehlt sie oder ist sie abgeschaltet, wird sie angelegt und eine Zeile
gemeldet. Laeuft als no_agent-Cron: die Ausgabe ist die Nachricht.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import os

NAME = "MaxHirn-Ausserhaus-Kopie"
HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                      # .../BrainFiles (Agenten/Hermes/scripts/<datei>)
REGISTRAR = WURZEL / "Agenten" / "Routinen" / "ausserhaus-kopie-aufgabe.ps1"


def _ohne_python_leck(env: dict) -> dict:
    """Ein geerbtes PYTHONHOME/PYTHONPATH vergiftet jeden Kind-Python."""
    env = dict(env)
    for name in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(name, None)
    return env


def _powershell(argumente: list[str], frist: int = 60) -> subprocess.CompletedProcess:
    import os

    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", *argumente],
        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=frist,
        env=_ohne_python_leck(os.environ),
    )


def zustand() -> str:
    """'da' / 'abgeschaltet' / 'fehlt' - ueber schtasks, nicht ueber Cmdlets.

    Get-ScheduledTask -TaskName findet in dieser Umgebung auch vorhandene
    Aufgaben nicht; schtasks /query ist die verlaessliche Sicht.
    """
    p = _powershell(["schtasks", "/query", "/tn", NAME, "/fo", "list"])
    if p.returncode != 0:
        return "fehlt"
    text = (p.stdout or "") + (p.stderr or "")
    if "Aufgabenname" not in text:
        return "fehlt"
    # Zeilenform: "Status:  Deaktiviert" bzw. "Status:  Bereit"
    for zeile in text.splitlines():
        z = zeile.strip()
        if z.startswith("Status:") and "Deaktiviert" in z:
            return "abgeschaltet"
    return "da"


def main() -> int:
    if not REGISTRAR.is_file():
        print(f"Ausserhaus-Kopie: Registrar fehlt - {REGISTRAR}")
        return 1

    vorher = zustand()
    if vorher == "da":
        return 0                                # leise: nichts senden
    if vorher == "abgeschaltet":
        p = _powershell(["schtasks", "/change", "/tn", NAME, "/enable"])
        ok = p.returncode == 0
        print(
            f"Ausserhaus-Kopie war abgeschaltet und wurde "
            f"{'wieder eingeschaltet' if ok else 'NICHT eingeschaltet'}."
        )
        return 0 if ok else 1

    p = _powershell(["-File", str(REGISTRAR)], frist=120)
    text = ((p.stdout or "") + (p.stderr or "")).strip()
    nachher = zustand()
    if nachher == "da":
        print(f"Ausserhaus-Kopie (taeglich 21:30) war nicht vorhanden und ist angelegt.")
        return 0
    print("Ausserhaus-Kopie liess sich NICHT anlegen. Registrar sagte:")
    print(text[-800:])
    return 1


if __name__ == "__main__":
    sys.exit(main())
