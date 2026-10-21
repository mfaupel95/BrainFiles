#!/usr/bin/env python3
"""Geplanter Gateway-Neustart (11.10.2026, auf Max' Anweisung: "Restarte in 10 min").

Hintergrund — warum ein Neustart ueberhaupt noetig ist:
  Der Haupt-Gateway (PID 37640) traegt in gateway_state.json noch
  telegram.state = "fatal" (telegram-bot-token_lock) und sechs
  duplicate_credential-Eintraege. Hermes versucht einen Token-Konflikt beim
  START ausdruecklich nicht erneut (gateway/restart.py::is_global_startup_conflict,
  run_startup.py:1344) — das Gate ist zu, solange kein Fremdprozess laeuft.
  Also: nur ein Neustart bringt Telegram zurueck.

Ablauf:
  1. Zustand VORHER festhalten (PID, Plattform-States, active_agents).
  2. `hermes gateway restart` — der von Hermes dokumentierte Weg.
  3. Bis zu 90 s auf telegram.state == "connected" warten und pollen.
  4. Zustand NACHHER festhalten und beide Staende vergleichen.

Aufruf:  python gateway-neustart-geplant.py [--nach-sekunden N]
  --nach-sekunden N  wartet N Sekunden, bevor der Neustart laeuft (fuer
                     "restarte in 10 Minuten"). Ohne Angabe: sofort.

Hinweis: Der Cron-Weg ist fuer diesen Befehl gesperrt (cronjob_manage lehnt
Gateway-Lifecycle-Kommandos ab, #30719 — SIGTERM-Respawn-Schleifen unter
Dienst-Aufsicht). Der Aufruf muss aus einer Shell AUSSERHALB des Gateways
kommen; als Hintergrundprozess des Agenten ist das gegeben.

Rueckgabe: ein kurzer Bericht auf stdout (wird per Cron an Telegram geliefert).
Kein Geheimnis wird gelesen, ausgegeben oder protokolliert.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERMES_HOME = Path(r"C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes")
STATE = HERMES_HOME / "gateway_state.json"
LOG = HERMES_HOME / "profiles" / "hermes-wartung" / "logs" / "gateway-restart-geplant.log"

WARTEN_SEK = 90
POLL_SEK = 5


def zustand() -> dict:
    """Plattform-Zustaende aus gateway_state.json, robust gegen Schreibrennen."""
    for _ in range(5):
        try:
            d = json.loads(STATE.read_text(encoding="utf-8"))
            plattformen = d.get("platforms") or {}
            return {
                "pid": d.get("pid"),
                "gateway_state": d.get("gateway_state"),
                "active_agents": d.get("active_agents"),
                "telegram": (plattformen.get("telegram") or {}).get("state"),
                "fatal": sorted(
                    k for k, v in plattformen.items()
                    if (v or {}).get("state") == "fatal"
                ),
            }
        except Exception:
            time.sleep(1)
    return {"pid": None, "gateway_state": None, "active_agents": None,
            "telegram": None, "fatal": []}


def protokoll(zeile: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {zeile}\n")


def main() -> int:
    # uv-venv-Falle: ein verirrtes PYTHONHOME zieht das venv-Python auf ein fremdes Stdlib.
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env["HERMES_HOME"] = str(HERMES_HOME)

    # --nach-sekunden N: erst warten, dann neu starten ("restarte in 10 Minuten").
    wartezeit = 0
    if "--nach-sekunden" in sys.argv:
        i = sys.argv.index("--nach-sekunden")
        try:
            wartezeit = int(sys.argv[i + 1])
        except (IndexError, ValueError):
            print("--nach-sekunden braucht eine ganze Zahl (Sekunden).")
            return 2

    if wartezeit > 0:
        ziel = time.strftime("%H:%M:%S", time.localtime(time.time() + wartezeit))
        protokoll(f"geplant: Neustart um {ziel} (in {wartezeit} s)")
        print(f"Gateway-Neustart geplant fuer {ziel} (in {wartezeit} s).")
        print(f"  Bericht kommt nach dem Lauf. Protokoll: {LOG}")
        sys.stdout.flush()
        time.sleep(wartezeit)

    vorher = zustand()
    protokoll(f"VORHER: {vorher}")
    print("Gateway-Neustart (geplant)")
    print(f"  vorher: PID {vorher['pid']}, Zustand {vorher['gateway_state']}, "
          f"Telegram {vorher['telegram']}, {len(vorher['fatal'])} fatal")

    if vorher["active_agents"]:
        print(f"  WARNUNG: {vorher['active_agents']} aktive Agenten werden abgebrochen")

    # 1. Neustart
    try:
        r = subprocess.run(
            ["hermes", "gateway", "restart"],
            capture_output=True, text=True, env=env, timeout=240,
            cwd=str(HERMES_HOME),
        )
        rc = r.returncode
        ausgabe = (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        rc, ausgabe = -1, "Zeitueberschreitung nach 240 s"
    except Exception as e:
        rc, ausgabe = -2, f"{type(e).__name__}: {e}"

    kurz = " | ".join(
        z.strip() for z in ausgabe.splitlines()
        if z.strip() and "dashboard" not in z.lower() and "manual restart" not in z.lower()
    )[:300]
    protokoll(f"RESTART rc={rc}: {kurz}")
    print(f"  restart rc={rc}: {kurz}")

    # 2. Auf Telegram warten
    nachher = vorher
    for _ in range(WARTEN_SEK // POLL_SEK):
        time.sleep(POLL_SEK)
        nachher = zustand()
        if nachher["telegram"] == "connected" and nachher["pid"] != vorher["pid"]:
            break

    protokoll(f"NACHHER: {nachher}")
    print(f"  nachher: PID {nachher['pid']}, Zustand {nachher['gateway_state']}, "
          f"Telegram {nachher['telegram']}, {len(nachher['fatal'])} fatal")

    # 3. Bewertung
    print()
    erfolg = (
        nachher["telegram"] == "connected"
        and nachher["pid"] is not None
        and nachher["pid"] != vorher["pid"]
    )
    if erfolg:
        print(f"ERFOLG: Telegram laeuft wieder (PID {vorher['pid']} -> {nachher['pid']}).")
        if nachher["fatal"]:
            print(f"  offen bleiben: {', '.join(nachher['fatal'])}")
        else:
            print("  keine fatalen Plattformen mehr.")
    else:
        print("NICHT BESTAETIGT — Neustart hat Telegram nicht zurueckgebracht.")
        print(f"  Telegram steht auf '{nachher['telegram']}'.")
        print(f"  PID: {vorher['pid']} -> {nachher['pid']} "
              f"({'unveraendert' if nachher['pid'] == vorher['pid'] else 'gewechselt'}).")
        if nachher["fatal"]:
            print(f"  fatal: {', '.join(nachher['fatal'])}")
        print(f"  Protokoll: {LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
