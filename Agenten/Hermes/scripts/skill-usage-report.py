"""Skill-Nutzungsbericht: wie oft wurden die geladenen Skills wirklich benutzt?

Laeuft als Hermes-Cron OHNE Modell (`no_agent`) woechentlich und meldet die
Zahlen von `hermes curator usage` nach Telegram - gekuerzt auf den
handelbaren Kern: die meistgenutzten Skills und die ungenutzten (use=0).

WARUM
-----
Jede geladene SKILL.md kostet bei JEDER Anfrage Kontext-Tokens. Am 11.09.2026
hat das Ausmisten die Bibliothek von 127 auf 48 Skills getrimmt und die Last
von ~4.400 auf ~1.200 Tokens je Anfrage gesenkt - der woechentliche Bericht
haelt diesen Stand: ungenutzte Skills fallen auf, bevor sie teuer werden.

WAS ES TUT (nur lesend)
-----------------------
1. `hermes.exe curator usage` aufrufen (PYTHONHOME/PYTHONPATH entfernt, wie
   bei jedem hermes.exe-Aufruf aus einer Agentensitzung noetig).
2. Ausgabe kuerzen: Top 10 nach 'act' + alle Zeilen mit use=0.
3. Leere/fehlerhafte Ausgabe wird gemeldet, bricht aber nicht ab.

Aufruf:
    python Agenten/Hermes/scripts/skill-usage-report.py
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
HERMES = HIER.parents[1] / "bin" / "hermes.exe"   # Agenten/Hermes/bin/hermes.exe


def curator_usage():
    """(returncode, zeilen) - Zeilen ohne Kopf/Leerzeilen."""
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    try:
        r = subprocess.run([str(HERMES), "curator", "usage"],
                           capture_output=True, text=True, timeout=120,
                           errors="replace", env=env)
    except (OSError, subprocess.SubprocessError) as e:
        return -1, ["Aufruf fehlgeschlagen: %s" % e]
    text = (r.stdout or "") + ("\n" + r.stderr if r.stderr else "")
    zeilen = [z.strip() for z in text.splitlines() if z.strip()]
    return r.returncode, zeilen


def parse(zeilen):
    """(kopf, daten) - daten: (name, origin, use, act, rest)."""
    kopf = [z for z in zeilen if z.lower().startswith("skills:") or
            z.lower().startswith("  skill")]
    daten = []
    for z in zeilen:
        teile = z.split()
        if len(teile) < 5:
            continue
        name, origin = teile[0], teile[1]
        if name in ("skill", "skills:") or name.startswith("---"):
            continue
        try:
            use = int(teile[2])
            act = int(teile[5])
        except (ValueError, IndexError):
            continue
        daten.append((name, origin, use, act, " ".join(teile[6:])))
    return kopf, daten


def main():
    ap = argparse.ArgumentParser(description="Skill-Nutzungsbericht")
    ap.add_argument("--nur", default="",
                    help="nur Skills mit diesem Namens-Praefix zeigen "
                         "(Komma-getrennt, z.B. 'okx,handel')")
    args = ap.parse_args()
    praefixe = [p.strip() for p in args.nur.split(",") if p.strip()]

    code, zeilen = curator_usage()
    kopf, daten = parse(zeilen)
    if code != 0 or not daten:
        print("Skill-Nutzung: Ausgabe unlesbar (Exit %d):" % code)
        print("\n".join(zeilen[:10]))
        return 0

    if praefixe:
        daten = [d for d in daten
                 if any(d[0].startswith(p) for p in praefixe)]
        if not daten:
            print("Skill-Nutzung: kein Skill mit Praefix %s gefunden."
                  % ", ".join(praefixe))
            return 0

    top = sorted(daten, key=lambda d: -d[3])[:10]
    ungenutzt = [d for d in daten if d[2] == 0]

    titel = "Skill-Nutzung (woechentlich): %d Skills geladen" % len(daten)
    if praefixe:
        titel += "  [nur %s]" % ", ".join(praefixe)
    print(titel)
    if kopf:
        print(kopf[0])
    print("\nMeistgenutzt (act):")
    for name, origin, use, act, rest in top:
        print("  %-28s %5d Aufrufe  (%s)" % (name, act, origin))
    if ungenutzt:
        print("\nNIE benutzt (use=0) - Kandidaten fuer das Archiv (curator restore holt zurueck):")
        for name, origin, use, act, rest in ungenutzt:
            print("  %s (%s)" % (name, origin))
    else:
        print("\nKein Skill mit use=0 - alle geladenen Skills wurden benutzt.")
    print("\nTrimmen:  hermes curator restore <name>  |  Liste: hermes curator list-archived")
    return 0


if __name__ == "__main__":
    sys.exit(main())
