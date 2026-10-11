#!/usr/bin/env python3
"""Wache fuer den n8n-Container (lokal, 127.0.0.1:5678).

Watchdog-Muster: leere Ausgabe = nichts senden.
- UI kaputt + Container tot          -> docker start, Befund melden
- UI kaputt + Container laeuft      -> docker restart (Port-Weiterleitung haengt oft),
                                        Befund melden
- UI wieder da                       -> Erholung melden (immer)
Derselbe Befund hoechstens alle 6 h (zuletzt_tot). n8n ist stateful im Volume
(cache/n8n-data) — ein Neustart verliert keine Workflows/Credentials.

Aufruf: python n8n-wache.py [--vorschau]
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent          # Agenten/Hermes/scripts
MERK = HIER.parent / "cache" / "n8n-wache.json"  # Agenten/Hermes/cache
HEALTH_URL = "http://127.0.0.1:5678/healthz"
CONTAINER = "n8n"
STILLE_S = 6 * 3600  # derselbe Befund hoechstens alle 6 h


def health_ok():
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def container_laeuft():
    try:
        p = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER],
            capture_output=True, text=True, timeout=30,
        )
        return p.returncode == 0 and p.stdout.strip() == "true"
    except Exception:
        return False


def container_starten():
    try:
        p = subprocess.run(["docker", "start", CONTAINER],
                           capture_output=True, text=True, timeout=60)
        return p.returncode == 0
    except Exception:
        return False


def container_neustarten():
    try:
        p = subprocess.run(["docker", "restart", CONTAINER],
                           capture_output=True, text=True, timeout=90)
        return p.returncode == 0
    except Exception:
        return False


def lade_merk():
    if MERK.exists():
        try:
            return json.loads(MERK.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def main(heilen=None, neustarten=None, vorschau=False):
    if heilen is None:
        heilen = container_starten
    if neustarten is None:
        neustarten = container_neustarten
    merk = lade_merk()
    jetzt = time.time()
    meldungen = []

    if health_ok():
        if merk.get("zustand") == "tot":
            meldungen.append("n8n ist wieder da (UI antwortet wieder, Workflows aktiv).")
        merk["zustand"] = "ok"
    else:
        laeuft = container_laeuft()
        letzte = merk.get("zuletzt_tot", 0)
        if vorschau:
            if laeuft:
                meldungen.append("[vorschau] n8n laeuft, aber UI antwortet nicht — wuerde neu gestartet.")
            else:
                meldungen.append("[vorschau] n8n-Container laeuft nicht, wuerde gestartet.")
        elif jetzt - letzte > STILLE_S:
            # Heilversuch (start oder restart), hoechstens alle 6 h.
            if laeuft:
                if neustarten():
                    meldungen.append("n8n-Container hing (UI antwortete nicht), wurde neu gestartet.")
                    merk["zustand"] = "ok"
                else:
                    meldungen.append("n8n-Container laeuft, aber die Web-UI antwortet nicht und der Neustart scheiterte.")
                    merk["zustand"] = "tot"
            else:
                if heilen():
                    meldungen.append("n8n-Container war tot, wurde gestartet. UI prueft sich selbst.")
                    merk["zustand"] = "ok"
                else:
                    meldungen.append("n8n-Container ist tot und liess sich nicht starten (docker start fehlgeschlagen).")
                    merk["zustand"] = "tot"
            merk["zuletzt_tot"] = jetzt
        elif merk.get("zustand") != "tot":
            merk["zustand"] = "tot"

    MERK.parent.mkdir(parents=True, exist_ok=True)
    MERK.write_text(json.dumps(merk, ensure_ascii=False, indent=2), encoding="utf-8")
    for m in meldungen:
        print(m)
    return 0 if not meldungen else 2


if __name__ == "__main__":
    vorschau = "--vorschau" in sys.argv
    sys.exit(main(vorschau=vorschau))
