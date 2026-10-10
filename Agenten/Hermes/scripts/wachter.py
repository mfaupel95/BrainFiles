#!/usr/bin/env python
"""
wachter.py — Telegram-Wachter für lotse-Sitzung.

Sobald SKILLSBOT_TOKEN/TELEGRAM_CHAT_ID/A2A_PEER_TOKENS gesetzt sind,
kann der SkillsBot (`Agenten/BUS/skillsbot.py`) über Telegram Freitext
an den Gateway (Port 9900) weiterleiten. Der Gateway bedient dann
das default-Profil lotse mit Modell deepseek/deepseek-v4-flash-0731
(über nous, inference-api.nousresearch.com/v1).

Das ist die aktuelle Session-Anbindung: Nachricht → SkillsBot →
A2A → lotse → deepseek/deepseek-v4-flash-0731.

Zusätzlich steht /bot lotse <text> für explizite Einzelaufträge
an das lotse-Profil bereit (hermes -p lotse chat -q).

WICHTIG: dieser Wachter ändert nichts — er prüft nur Zustand und
meldet. Eingriffe sind Max-Sache (Token setzen, Task starten).
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.abspath(os.path.join(HIER, os.pardir, os.pardir, os.pardir))


def _aus_registry(name):
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def _variable(name):
    return os.environ.get(name) or _aus_registry(name)


def bereit():
    fehlt = []
    if not _variable("SKILLSBOT_TOKEN"):
        fehlt.append("SKILLSBOT_TOKEN")
    if not _variable("TELEGRAM_CHAT_ID"):
        fehlt.append("TELEGRAM_CHAT_ID")
    if not _variable("A2A_PEER_TOKENS"):
        fehlt.append("A2A_PEER_TOKENS")
    return fehlt


def a2a_status():
    port_offen = False
    try:
        with socket.create_connection(("127.0.0.1", 9900), timeout=2):
            port_offen = True
    except OSError:
        pass
    if not port_offen:
        return "A2A-Gateway DOWN (Port 9900)"
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:9900/.well-known/agent-card.json", timeout=3
        ) as ant:
            karte = json.loads(ant.read().decode("utf-8"))
            name = karte.get("name", "?")
            skills = len(karte.get("skills", []))
            return f"A2A-Gateway OK: {name}, {skills} Skills"
    except Exception as e:
        return f"A2A-Gateway fragil: Port offen, Agent-Card nicht lesbar ({e})"


def lotse_modell():
    pfad = os.path.join(
        WURZEL, "Agenten", "Hermes", "profiles", "lotse", "config.yaml"
    )
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            zeilen = f.read().splitlines()
    except OSError as e:
        return f"lotse-Config nicht lesbar: {e}"
    provider = None
    default = None
    base_url = None
    in_model = False
    for zeile in zeilen:
        s = zeile.strip()
        if s == "model:":
            in_model = True
            continue
        if s and not s.startswith(" "):
            in_model = False
            continue
        if in_model and s.startswith("  provider:"):
            provider = s.split(":", 1)[1].strip().strip("'\"")
        if in_model and s.startswith("  default:"):
            default = s.split(":", 1)[1].strip().strip("'\"")
        if in_model and s.startswith("  base_url:"):
            base_url = s.split(":", 1)[1].strip().strip("'\"")
    if provider and default:
        return f"lotse-Modell: {default} über {provider}" + (
            f", Endpunkt {base_url}" if base_url else ""
        )
    return "lotse-Config unvollständig"


def skillbot_bot():
    tok = _variable("SKILLSBOT_TOKEN")
    if not tok:
        return "SkillsBot: kein SKILLSBOT_TOKEN → kein Dauerbetrieb"
    username = None
    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{tok}/getMe", timeout=10
        ) as ant:
            info = json.loads(ant.read().decode("utf-8"))
            username = info.get("result", {}).get("username")
    except Exception as e:
        return f"SkillsBot: Token gesetzt, Telegram-Antwort fehlgeschlagen ({e})"
    if username:
        return f"SkillsBot: @{username} (SKILLSBOT_TOKEN)"
    return "SkillsBot: Token gesetzt, aber getMe unerwartet"


def hermes_exe():
    pfad = os.path.join(WURZEL, "Agenten", "Hermes", "bin", "hermes.exe")
    return pfad if os.path.isfile(pfad) else None


def lotse_bot_test():
    exe = hermes_exe()
    if not exe:
        return "hermes.exe nicht gefunden"
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env["HERMES_HOME"] = os.path.join(WURZEL, "Agenten", "Hermes")
    try:
        proc = subprocess.run(
            [exe, "-p", "lotse", "chat", "-q", "Antworte nur mit: PONG"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=WURZEL,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return "lotse-Test: Zeitlimit (>180 s) — zu groß für Einzeltest"
    if proc.returncode != 0:
        return f"lotse-Test: Exit {proc.returncode}, letzter Fehler: " + (
            proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "—"
        )
    antwort = proc.stdout.strip()
    if "PONG" in antwort:
        return "lotse-Test: OK (PONG erhalten)"
    return f"lotse-Test: Exit 0, aber keine PONG — Antwort: {antwort[:120]}"


def prozesse():
    out = []
    for such in ("ollama", "python", "hermes", "gateway", "skillsbot"):
        try:
            proc = subprocess.run(
                            ["tasklist", "/FI", f"IMAGENAME eq {such}*", "/NH", "/FO", "CSV"],
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            timeout=20,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            zeilen = [z for z in proc.stdout.splitlines() if z.strip()]
            if len(zeilen) > 1:
                out.append(f"{such}: {len(zeilen)-1} Prozess(e)")
        except Exception:
            pass
    return ", ".join(out) if out else "keine Prozesse in tasklist"


def zustand():
    zeilen = []
    zeilen.append("=== lotse-Sitzung: Telegram-Anbindung ===")
    tok_fehlt = not _variable("SKILLSBOT_TOKEN")
    chat_fehlt = not _variable("TELEGRAM_CHAT_ID")
    a2a_fehlt = not _variable("A2A_PEER_TOKENS")
    zeilen.append(f"TELEGRAM_TOKEN gesetzt: {'NEIN' if tok_fehlt else 'JA'}")
    zeilen.append(f"TELEGRAM_CHAT_ID gesetzt: {'NEIN' if chat_fehlt else 'JA'}")
    zeilen.append(f"A2A_PEER_TOKENS gesetzt: {'NEIN' if a2a_fehlt else 'JA'}")
    zeilen.append("")
    zeilen.append(a2a_status())
    zeilen.append(lotse_modell())
    zeilen.append(skillbot_bot())
    zeilen.append("")
    zeilen.append("Prozesse (tasklist-Snapshot): " + prozesse())
    zeilen.append("")
    if _variable("SKILLSBOT_TOKEN"):
        zeilen.append(lotse_bot_test())
    else:
        zeilen.append(
            "lotse-Test: SKILLSBOT_TOKEN fehlt — Test nicht durchführbar."
        )
    zeilen.append("")
    zeilen.append(
        "Nächster Schritt: setx SKILLSBOT_TOKEN <token> (BotFather /newbot), "
        "setx TELEGRAM_CHAT_ID <id>, dann python skillsbot.py --probe"
    )
    return "\n".join(zeilen) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Lotse-Sitzung Wachter")
    ap.add_argument("--probe", action="store_true", help="Zustand anzeigen")
    args = ap.parse_args()
    if args.probe:
        print(zustand())
        sys.exit(0 if not bereit() else 2)
    else:
        print(zustand())
        sys.exit(0)
