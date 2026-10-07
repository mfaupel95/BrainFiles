"""
Wertet die gespeicherten Claude-Sitzungen aus, um wiederkehrende Aufgaben
zu finden - die Vorstufe zu einem neuen Skill.

Liest die JSONL-Transkripte unter ~/.claude/projects/ und beantwortet zwei
Fragen, die man von Hand nicht beantworten kann:
  1. Was hat Max wiederholt verlangt?      -> Anweisungen, gekuerzt
  2. Welche Befehle liefen dabei wirklich? -> Themen-Cluster mit Anzahl
  3. Welche Werkzeuge wurden benutzt?      -> je MCP-Server, mit --werkzeuge

Der dritte Punkt ist der Werkzeug-Abgleich: Ein Server, der eingetragen ist
und nie aufgerufen wird, kostet in jeder Sitzung Kontext und liefert nichts.

Bewusst sparsam: die Standardausgabe ist eine Zusammenfassung. Die
Volltexte landen in Dateien, nicht im Kontext - 362 Anweisungen ungekuerzt
zu lesen kostet ein Vielfaches der Zusammenfassung.

Aufruf:
    python sitzungen_auswerten.py                 Zusammenfassung
    python sitzungen_auswerten.py --anweisungen   jede Anweisung, 170 Zeichen
    python sitzungen_auswerten.py --seit 2026-08-20
    python sitzungen_auswerten.py --ausgabe ORDNER   Volltexte dorthin
    python sitzungen_auswerten.py --werkzeuge     Aufrufe je Server und Skill
"""

import argparse
import collections
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Themen, an denen sich wiederkehrende Arbeit erkennen laesst. Erweitern,
# sobald ein neues Muster auffaellt - die Liste ist der eigentliche Wert.
THEMEN = {
    "Ereignisanzeige/Absturz": r"Get-WinEvent|LiveKernel|MEMORY\.DMP|BugCheck|Kernel-Power",
    "Dienste/Treiber":         r"Get-Service|Set-Service|pnputil|Get-PnpDevice|Restart-Service|driverquery",
    "Registry":                r"HKLM:|HKCU:|reg add|reg query|New-ItemProperty",
    "MCP/Claude-Konfig":       r"claude mcp|\.claude\.json|claude_desktop_config|mcpServers",
    "Git/Sichern":             r"git add|git commit|git status|git log|git revert",
    "Archiv-Index/Suche":      r"index\.py|search_cli\.py|sort_inbox\.py|archiv\.db|pruefe_signaturen",
    "Laufwerksvergleich":      r"Get-ChildItem -Recurse|robocopy|Compare-Object|Get-FileHash",
    "Aufgabenplanung":         r"schtasks|Register-ScheduledTask|Get-ScheduledTask",
    "Speicherplatz":           r"Get-PSDrive|Get-Volume|Remove-Item -Recurse|cleanmgr",
    "Umgebungsvariablen":      r"\$env:PATH|Environment.*Path|setx |GetEnvironmentVariable",
    "Prozesse":                r"Get-Process|Stop-Process|tasklist|taskkill",
    "Python/venv":             r"\.venv|pip install|python\.exe",
    "Netz/Pakete":             r"Invoke-WebRequest|Invoke-RestMethod|winget|npx ",
}

# Zeilen, die keine echte Anweisung sind, sondern Mechanik der Oberflaeche.
RAUSCHEN = re.compile(
    r"^(Continue from where you left off|Erneut versuchen|Commit the working tree"
    r"|\[Request interrupted|Another Claude session sent|Base directory for this skill)",
    re.I,
)


def sitzungen_lesen(basis, seit):
    anweisungen, befehle, werkzeuge = [], [], collections.Counter()
    server, skills = collections.Counter(), collections.Counter()
    dateien = glob.glob(os.path.join(basis, "**", "*.jsonl"), recursive=True)
    for pfad in dateien:
        try:
            with open(pfad, encoding="utf-8", errors="replace") as fh:
                for zeile in fh:
                    zeile = zeile.strip()
                    if not zeile:
                        continue
                    try:
                        satz = json.loads(zeile)
                    except ValueError:
                        continue
                    tag = (satz.get("timestamp") or "")[:10]
                    if seit and tag and tag < seit:
                        continue
                    nachricht = satz.get("message") or {}
                    rolle = nachricht.get("role") or satz.get("type")
                    inhalt = nachricht.get("content")

                    if rolle == "user":
                        stuecke = [inhalt] if isinstance(inhalt, str) else [
                            b.get("text", "") for b in (inhalt or [])
                            if isinstance(b, dict) and b.get("type") == "text"
                        ]
                        for text in stuecke:
                            text = (text or "").strip()
                            if len(text) < 12 or text.startswith("<"):
                                continue
                            anweisungen.append((tag, os.path.basename(pfad)[:8], text))
                    elif rolle == "assistant" and isinstance(inhalt, list):
                        for block in inhalt:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                name = block.get("name", "")
                                eingabe = block.get("input") or {}
                                werkzeuge[name] += 1
                                if name.startswith("mcp__"):
                                    server[name.split("__")[1]] += 1
                                elif name == "Skill":
                                    skills[eingabe.get("skill", "?")] += 1
                                befehl = eingabe.get("command")
                                if isinstance(befehl, str):
                                    befehle.append(befehl)
        except OSError as fehler:
            print(f"uebersprungen: {pfad} ({fehler})")
    return len(dateien), anweisungen, befehle, werkzeuge, server, skills


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--basis", default=os.path.join(os.path.expanduser("~"), ".claude", "projects"))
    p.add_argument("--seit", default=None, help="nur ab diesem Tag, JJJJ-MM-TT")
    p.add_argument("--anweisungen", action="store_true", help="jede Anweisung gekuerzt zeigen")
    p.add_argument("--werkzeuge", action="store_true", help="Aufrufe je MCP-Server und Skill")
    p.add_argument("--ausgabe", default=None, help="Ordner fuer die Volltexte")
    args = p.parse_args()

    if not os.path.isdir(args.basis):
        print(f"Kein Sitzungsordner unter {args.basis}")
        return 1

    anzahl, anweisungen, befehle, werkzeuge, server, skills = sitzungen_lesen(args.basis, args.seit)
    echte = [a for a in anweisungen if not RAUSCHEN.match(a[2])]

    print(f"Sitzungen: {anzahl}   Anweisungen: {len(anweisungen)} "
          f"(davon eigenstaendig: {len(echte)})   Befehle: {len(befehle)}")
    print("\nWiederkehrende Arbeit (Anzahl Befehle je Thema):")
    zaehler = collections.Counter()
    for befehl in befehle:
        for name, muster in THEMEN.items():
            if re.search(muster, befehl, re.I | re.M):
                zaehler[name] += 1
    for name, wert in zaehler.most_common():
        print(f"  {wert:5d}  {name}")

    print("\nWerkzeuge:", ", ".join(f"{k}={v}" for k, v in werkzeuge.most_common(10)))

    if args.werkzeuge:
        gesamt = sum(server.values())
        print(f"\nMCP-Aufrufe: {gesamt} in {len(server)} Servern")
        for name, wert in server.most_common():
            anteil = 100.0 * wert / gesamt if gesamt else 0
            print(f"  {wert:5d}  ({anteil:4.1f} %)  {name}")
        print(f"\nSkill-Aufrufe: {sum(skills.values())}")
        for name, wert in skills.most_common():
            print(f"  {wert:5d}  {name}")
        print("\nAbgleichen mit `claude mcp list` und claude_desktop_config.json:")
        print("Ein eingetragener Server ohne Aufrufe ist Ballast, kein Werkzeug.")

    if args.anweisungen:
        print(f"\n--- {len(echte)} Anweisungen ---")
        for tag, sitzung, text in sorted(echte):
            print(f"[{tag} {sitzung}] {' '.join(text.split())[:170]}")

    if args.ausgabe:
        os.makedirs(args.ausgabe, exist_ok=True)
        ziel_a = os.path.join(args.ausgabe, "anweisungen.txt")
        ziel_b = os.path.join(args.ausgabe, "befehle.txt")
        with open(ziel_a, "w", encoding="utf-8") as fh:
            for tag, sitzung, text in sorted(echte):
                fh.write(f"\n=== {tag} [{sitzung}] ===\n{text}\n")
        with open(ziel_b, "w", encoding="utf-8") as fh:
            fh.write("\n---\n".join(befehle))
        print(f"\nVolltexte: {ziel_a} / {ziel_b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
