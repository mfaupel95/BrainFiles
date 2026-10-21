"""
Wertet die gespeicherten Claude-Sitzungen aus, um wiederkehrende Aufgaben
zu finden - die Vorstufe zu einem neuen Skill.

Liest die JSONL-Transkripte unter ~/.claude/projects/ und beantwortet vier
Fragen, die man von Hand nicht beantworten kann:
  1. Was hat Max wiederholt verlangt?      -> Anweisungen, gekuerzt
  2. Welche Befehle liefen dabei wirklich? -> Themen-Cluster mit Anzahl
  3. Welche Werkzeuge wurden benutzt?      -> je MCP-Server, mit --werkzeuge
  4. Was ging dabei schief?                -> Fehlersignaturen, mit --umwege

Der dritte Punkt ist der Werkzeug-Abgleich: Ein Server, der eingetragen ist
und nie aufgerufen wird, kostet in jeder Sitzung Kontext und liefert nichts.

Der vierte Punkt ist der eigentliche Fund: die Befehlshaeufigkeit zeigt, WO
gearbeitet wurde, erst die Fehlersignaturen zeigen, WORAN es hing. Gezaehlt
wird je Signatur die Zahl VERSCHIEDENER Sitzungen und TAGE - dasselbe Problem
an mehreren Tagen ist ein Muster (und ein Skill-Kandidat), an einem Tag ein
Vorfall. Die Signaturen kommen aus den WERKZEUG-ERGEBNISSEN, nicht aus den
Befehlen; die Befehlsliste allein enthaelt keinen einzigen Fehler.

Bewusst sparsam: die Standardausgabe ist eine Zusammenfassung. Die
Volltexte landen in Dateien, nicht im Kontext - 954 eigenstaendige
Anweisungen ungekuerzt zu lesen kostet ein Vielfaches der Zusammenfassung.

Aufruf:
    python sitzungen_auswerten.py                 Zusammenfassung
    python sitzungen_auswerten.py --anweisungen   jede Anweisung, 170 Zeichen
    python sitzungen_auswerten.py --seit 2026-08-20
    python sitzungen_auswerten.py --ausgabe ORDNER   Volltexte dorthin
    python sitzungen_auswerten.py --werkzeuge     Aufrufe je Server und Skill
    python sitzungen_auswerten.py --umwege        Fehlersignaturen je Sitzung/Tag
"""

import argparse
import collections
import glob
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

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
    # --- Hermes-Betrieb (ab 21.09.2026) ---
    # Nachgezogen am 30.09.2026: fehlt ein Thema, untertreibt der Bericht genau
    # den Bereich mit der meisten Arbeit - "Hermes" war das Thema mit den
    # meisten Sitzungen und kam in der Liste bis dahin gar nicht vor.
    "Hermes/Profil/Gateway":   r"hermes|Hermes|profile|Profil|gateway|Gateway|config\.yaml"
                               r"|Delegation|Subagent|Kompression|Skill-Bibliothek|curator",
    "Handel/Spuren":           r"handeln\.py|dauerlauf|Spur|spur_|wachen\.json|freigabe|Journal"
                               r"|Position|OKX|Kraken|scanner",
    "Wachen/Cron/Routinen":    r"cron|Cron|Wache|Waechter|Routine|kanban|Kanban|no_agent",
    "Modelle/lokal":           r"ollama|Ollama|llama|Bonsai|VRAM|GGUF|gemma|qwen|Kronos|Modell",
    "Sandbox/Docker":          r"docker|Docker|Sandbox|Container|windows-mcp",
    "Fremd-Repos/Klone":       r"Werkstatt|Klon|clone|upstream|repos-updaten|Fundus|Bot",
    "Tests/Nachweis":          r"unittest|pytest|test_|Tests|Gegenprobe|Nachweis|assert",
    "Backtest/Historie":       r"Backtest|historie|replay|optimier|freqtrade|dry_run|Kosten",
    "Zugangsdaten":            r"Zugaenge|\.env|API_KEY|Schluessel|Token|Passphrase|Key",
    "Textdateien/Zeilenenden": r"CRLF|crlf|Zeilenende|newline=|\.gitignore|Whitelist",
    "Steuer/Belege":           r"Steuer|Beleg|Rechnung|Einspruch|Finanzamt|Frist",
}

# Zeilen, die keine echte Anweisung sind, sondern Mechanik der Oberflaeche.
RAUSCHEN = re.compile(
    r"^(Continue from where you left off|Erneut versuchen|Commit the working tree"
    r"|\[Request interrupted|Another Claude session sent|Base directory for this skill"
    r"|This session is being continued|Caveat:|# |## |\*\*|\{|\[your previous response"
    r"|\(re-invocation of /)",
    re.I,
)

# Laengengrenze fuer eine echte Anweisung. Alles darueber ist eingespielter
# Text (Skill-Inhalt, Werkzeug-Ausgabe, Zusammenfassung einer Vorgaengersitzung):
# gemessen war die laengste "Anweisung" 360.909 Zeichen lang und stammte aus
# einer JSON-Ausgabe. Ohne die Grenze zaehlt der Bericht Mechanik als Auftrag.
MAX_ANWEISUNG = 2000

# Fehlersignaturen fuer --umwege. Der Name ist der Befund, das Muster sucht in
# den Werkzeug-ERGEBNISSEN. Erweitern, sobald ein neuer Umweg auffaellt.
UMWEGE = {
    "Datei nicht gefunden":          r"(FileNotFoundError|No such file or directory|WinError 2\b)",
    "Modul nicht gefunden":          r"(ModuleNotFoundError|ImportError|No module named)",
    "Falscher Interpreter":          r"(sys\.executable|PYTHONHOME|init_import_site)",
    "Zugriff verweigert":            r"(PermissionError|Access is denied|Zugriff verweigert|WinError 5\b)",
    "Zeilenden/Whitelist":           r"(CRLF|\\r\\n|Zeilenende|check-ignore)",
    "Encoding/Umlaute":              r"(UnicodeDecodeError|UnicodeEncodeError|charmap|cp1252)",
    "JSON/Parse":                    r"(JSONDecodeError|Expecting value|Unterminated string"
                                     r"|SyntaxError|IndentationError)",
    "index.lock":                    r"index\.lock",
    "Zwei Sitzungen/Git":            r"(Unable to create .*index|Another git process"
                                     r"|Please commit your changes)",
    "Commit/Auslagerung knapp":      r"(WinError 1455|Auslagerungsdatei|COMMITMENT_LIMIT"
                                     r"|Cannot allocate memory)",
    "Sandbox/Bruecke tot":           r"(Docker daemon is not responding|Terminal environment"
                                     r" unavailable|could not stat)",
    "Zeitfenster/Timeout":           r"(Timeout|timed out|exceeded .* limit|Rueckgabe 143|exit code 143)",
    "Test rot":                      r"(FAILED|AssertionError|Ran \d+ tests? in)",
    "Schluessel/HTTP":               r"(HTTP 40[13]|50101|50119|Invalid key|authenticationError"
                                     r"|Invalid nonce)",
    "Aufgabe/Datei existiert schon": r"(already exists|AlreadyExists|0x80070005|0x80070002)",
}


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
                            if len(text) > MAX_ANWEISUNG:
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


def umwege_lesen(basis, seit):
    """Fehlersignaturen aus den Werkzeug-Ergebnissen, je Sitzung und Tag."""
    sitzungen = {name: collections.Counter() for name in UMWEGE}
    tage = {name: set() for name in UMWEGE}
    dateien = glob.glob(os.path.join(basis, "**", "*.jsonl"), recursive=True)
    for pfad in dateien:
        try:
            with open(pfad, encoding="utf-8", errors="replace") as fh:
                for zeile in fh:
                    if not zeile.strip():
                        continue
                    try:
                        satz = json.loads(zeile)
                    except ValueError:
                        continue
                    tag = (satz.get("timestamp") or "")[:10]
                    if seit and tag and tag < seit:
                        continue
                    nachricht = satz.get("message") or {}
                    inhalt = nachricht.get("content")
                    if nachricht.get("role") != "user" or not isinstance(inhalt, list):
                        continue
                    for block in inhalt:
                        if not isinstance(block, dict) or block.get("type") != "tool_result":
                            continue
                        roh = block.get("content")
                        if isinstance(roh, list):
                            text = "\n".join(b.get("text", "") for b in roh
                                             if isinstance(b, dict))
                        else:
                            text = str(roh or "")
                        if not text:
                            continue
                        for name, muster in UMWEGE.items():
                            if re.search(muster, text):
                                sitzungen[name][os.path.basename(pfad)[:8]] += 1
                                tage[name].add(tag)
        except OSError:
            continue
    return dateien, sitzungen, tage


def hermes_lesen(db_pfad, seit):
    """DIE ZWEITE QUELLE: `Agenten/Hermes/state.db` (T-229).

    Warum ueberhaupt: seit dem 21.09.2026 ist Hermes der Hauptagent, die
    Rueckschau las aber nur `~/.claude/projects/**/*.jsonl`. Sie war damit
    blind fuer die Gegenwart - ein Muster, das heute entsteht, kam dort
    gar nicht vor. Zwei Quellen, zwei Agenten, dieselben Auswertungen.

    Das Schema (Stand 04.10.2026, 514 Sitzungen / 136.213 Nachrichten):
      sessions(id, source, cwd, git_branch, profile_name, started_at,
               message_count, tool_call_count, ...)
      messages(id, session_id, role, content, tool_name, tool_calls,
               timestamp, ...)

    RUECKGABE dieselben vier Bestaende wie `sitzungen_lesen` plus
    `umwege_tage`: (sitzungen, anweisungen, befehle, werkzeuge, server,
    skills, umwege) - damit kann der Aufruher beide Quellen mischen,
    ohne die Form zu aendern.

    NUR LESEND: die Datei wird mit `file:...?mode=ro` geoeffnet und kann
    waehrend des Lesens geschrieben werden (die laufende Sitzung schreibt
    hinein). Beim ersten Fehler wird gemeldet und weitergegangen - eine
    Sperre darf die Auswertung nicht umwerfen.
    """
    anweisungen, befehle, werkzeuge = [], [], collections.Counter()
    server, skills = collections.Counter(), collections.Counter()
    umwege = collections.Counter()
    umwege_tage = collections.defaultdict(set)
    if not os.path.isfile(db_pfad):
        raise FileNotFoundError(db_pfad)
    # read-only: mode=ro verhindert, dass diese Auswertung den Zustand des
    # laufenden Agenten anfasst.
    db = sqlite3.connect("file:%s?mode=ro" % db_pfad.replace(os.sep, "/"),
                         uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        sitzungen = {}
        for s in db.execute(
                "SELECT id, source, cwd, git_branch, profile_name, started_at"
                " FROM sessions"):
            sitzungen[s["id"]] = s
        for m in db.execute(
                "SELECT session_id, role, content, tool_name, tool_calls,"
                " timestamp FROM messages ORDER BY id"):
            s = sitzungen.get(m["session_id"])
            if s is None:
                continue
            ts = m["timestamp"] or 0
            tag = _tag_von_ts(ts)
            if seit and tag and tag < seit:
                continue
            kennung = (s["id"] or "")[:8]
            rolle = m["role"]
            inhalt = m["content"] or ""
            if rolle == "user":
                text = (inhalt or "").strip()
                if 12 <= len(text) <= MAX_ANWEISUNG and not text.startswith("<"):
                    anweisungen.append((tag, kennung, text))
            elif rolle == "assistant":
                befehle_aus, namen = _werkzeuge_aus_tool_calls(m["tool_calls"])
                for name in namen:
                    werkzeuge[name] += 1
                    if name.startswith("mcp__"):
                        teile = name.split("__")
                        if len(teile) > 1:
                            server[teile[1]] += 1
                befehle.extend(befehle_aus)
            if rolle in ("tool", "user"):
                for name, muster in UMWEGE.items():
                    if re.search(muster, inhalt or ""):
                        umwege[name] += 1
                        umwege_tage[name].add(kennung)
    finally:
        db.close()
    return (len(sitzungen), anweisungen, befehle, werkzeuge, server, skills,
            umwege, umwege_tage)


def _tag_von_ts(ts):
    """Unix-Zeit -> JJJJ-MM-TT (UTC), '' bei 0/None."""
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(float(ts), timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""


def _werkzeuge_aus_tool_calls(roh):
    """(befehle, werkzeugnamen) aus dem JSON-Feld `tool_calls`.

    Die Form ist eine LISTE mit `function.name` und `function.arguments`,
    wobei `arguments` selbst ein JSON-STRING ist (04.10.2026 gemessen:
    60.197 Zeilen, jede mit bis zu zwei Aufrufen). Der Aufrufer liest hier
    bewusst NICHT `messages.tool_name`: das ist nur bei den ERGEBNISZEILEN
    (role='tool') gesetzt, bei den Aufrufzeilen immer leer - eine Abfrage
    darauf zaehlt 0 Werkzeuge und sieht damit aus wie eine stille Sitzung.

    Kaputt ist das Feld dann kein Grund, die Zeile zu verlieren: der
    Klammerzähl-Block liefert auch aus teilweise zerstoertem JSON, was an
    uneinheitlichen Stellen noch lesbar ist.
    """
    namen, befehle = [], []
    roh = (roh or "").strip()
    if not roh:
        return befehle, namen
    try:
        liste = json.loads(roh)
    except ValueError:
        liste = None
    if isinstance(liste, list):
        for eintrag in liste:
            if not isinstance(eintrag, dict):
                continue
            funktion = eintrag.get("function") or {}
            name = funktion.get("name") or eintrag.get("name")
            if not name:
                continue
            namen.append(name)
            roh_arg = funktion.get("arguments", eintrag.get("arguments"))
            if isinstance(roh_arg, str):
                try:
                    roh_arg = json.loads(roh_arg)
                except ValueError:
                    pass
            if isinstance(roh_arg, dict) and isinstance(roh_arg.get("command"), str):
                befehle.append(roh_arg["command"])
        return befehle, namen
    # Fallback: Block fuer Block (kaputtes oder unerwartetes JSON).
    for name in re.findall(r'"name"\s*:\s*"([^"]{1,80})"', roh):
        namen.append(name)
    befehle.extend(_befehle_aus_tool_calls(roh))
    return befehle, namen


def _befehle_aus_tool_calls(roh):
    """`command`-Felder aus einem JSON-Feld `tool_calls` herausloesen.

    Das Feld traegt je Hermes-Version eine andere Form (Liste mit
    name/arguments, JSON-Text, Doppel-JSON). Statt drei Formen zu raten wird
    mit einer laufenden Klammerzählung jeder JSON-Objekt-Block geprueft -
    ein Muster, das bei keiner Form falsch trifft.
    """
    aus = []
    roh = (roh or "").strip()
    if not roh:
        return aus
    tiefe = 0
    start = None
    for i, z in enumerate(roh):
        if z == "{":
            if tiefe == 0:
                start = i
            tiefe += 1
        elif z == "}" and tiefe:
            tiefe -= 1
            if tiefe == 0 and start is not None:
                block = roh[start:i + 1]
                start = None
                m = re.search(r'"command"\s*:\s*("(?:[^"\\]|\\.)*")', block)
                if m:
                    try:
                        wert = json.loads(m.group(1))
                    except ValueError:
                        wert = m.group(1).strip('"')
                    if isinstance(wert, str):
                        aus.append(wert)
    return aus


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--basis", default=os.path.join(os.path.expanduser("~"), ".claude", "projects"))
    p.add_argument("--hermes-db", default=None,
                   help="zweite Quelle: state.db (Standard: Agenten/Hermes/state.db, "
                        "'nein' schaltet sie ab)")
    p.add_argument("--seit", default=None, help="nur ab diesem Tag, JJJJ-MM-TT")
    p.add_argument("--anweisungen", action="store_true", help="jede Anweisung gekuerzt zeigen")
    p.add_argument("--werkzeuge", action="store_true", help="Aufrufe je MCP-Server und Skill")
    p.add_argument("--umwege", action="store_true", help="Fehlersignaturen je Sitzung und Tag")
    p.add_argument("--ausgabe", default=None, help="Ordner fuer die Volltexte")
    args = p.parse_args()

    # Die zweite Quelle ist Standard, weil Hermes der Hauptagent ist
    # (T-229). Ohne sie ist die Rueckschau fuer die Gegenwart blind.
    db = args.hermes_db
    if db is None:
        db = os.path.join(os.path.expanduser("~"), "Documents", "BrainFiles",
                          "Agenten", "Hermes", "state.db")
    elif db.lower() in ("nein", "keine", "off", ""):
        db = None

    if args.umwege:
        dateien, sitzungen, tage = umwege_lesen(args.basis, args.seit)
        print(f"gelesen: {len(dateien)} Dateien"
              + (f", seit {args.seit}" if args.seit else ""))
        if db:
            try:
                (n_h, _a, _b, _w, _s, _sk, u2, t2) = hermes_lesen(db, args.seit)
                for name in tage:
                    tage[name] |= t2.get(name, set())
                for name, zaehler in sitzungen.items():
                    sitzungen[name] += u2.get(name, 0)
                print(f"Hermes: {n_h} Sitzungen aus {os.path.basename(db)}")
            except (OSError, sqlite3.Error) as e:
                print(f"Hermes-Quelle nicht lesbar ({type(e).__name__}: {e})")
        print("\nUmwege (Sitzungen = Muster, Tage = Dauer):")
        print(f"  {'Signatur':32s} Sitzungen  Tage  Treffer")
        for name in sorted(sitzungen, key=lambda n: -len(sitzungen[n])):
            if not sitzungen[name]:
                continue
            print(f"  {name:32s} {len(sitzungen[name]):6d}  {len(tage[name]):4d}"
                  f"  {sum(sitzungen[name].values()):6d}")
        print("\nEin Umweg in vielen Sitzungen ueber viele Tage ist ein Muster,"
              "\nkein Vorfall - und der Kandidat fuer einen Skill.")
        return 0

    anzahl, anweisungen, befehle, werkzeuge, server, skills = sitzungen_lesen(args.basis, args.seit)
    quelle = f"Claude-Transkripte: {anzahl}"
    if db:
        try:
            (n_h, a2, b2, w2, s2, sk2, _u, _t) = hermes_lesen(db, args.seit)
            anweisungen += a2
            befehle += b2
            werkzeuge.update(w2)
            server.update(s2)
            skills.update(sk2)
            quelle += f"  +  Hermes state.db: {n_h}"
        except (OSError, sqlite3.Error) as e:
            print(f"Hermes-Quelle nicht lesbar ({type(e).__name__}: {e})",
                  file=sys.stderr)
    echte = [a for a in anweisungen if not RAUSCHEN.match(a[2])]

    print(f"Sitzungen: {quelle}")
    print(f"Anweisungen: {len(anweisungen)} (davon eigenstaendig: {len(echte)})"
          f"   Befehle: {len(befehle)}")
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
