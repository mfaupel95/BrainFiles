"""Belegt, dass ein ${VAR}-Verweis in Hermes' config.yaml sich aufloest - und beim
Speichern nicht in Klartext zurueckfaellt. Gibt nie Werte aus, nur Laenge und
SHA-256-Anfang.

Aufruf auf dem Windows-Host mit dem Hermes-venv:
  $env:HERMES_HOME='C:\\...\\Agenten\\Hermes'
  & '<venv>\\Scripts\\python.exe' config-wert-pruefen.py --pfad <punktpfad>
  & '<venv>\\Scripts\\python.exe' config-wert-pruefen.py --pfad <punktpfad> --speicherprobe

Exit 0 = wie erwartet, 1 = Abweichung, 2 = Pfad oder Verweis fehlt.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

# Ohne HERMES_HOME aus dem eigenen Ort ableiten statt aus einem festen
# Benutzerpfad. Dieselbe Datei liegt in der Skill-Bibliothek
# (.../Hermes/skills/brainfiles/<skill>/scripts/) und in jeder Profilkopie
# (.../Hermes/profiles/<bot>/skills/brainfiles/<skill>/scripts/). Vier Ebenen
# ueber der Datei liegt beide Male genau ein Hermes-Zuhause - in der
# Bibliothek Agenten/Hermes, im Profil Agenten/Hermes/profiles/<bot>.
HOME = Path(os.environ.get("HERMES_HOME") or Path(__file__).resolve().parents[4])
CODE = HOME / "hermes-agent"


def sha8(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def hole(cfg, pfad: str):
    knoten = cfg
    for teil in pfad.split("."):
        knoten = knoten[teil]
    return knoten


def speicherprobe(pfad: str) -> int:
    ziel_home = Path(tempfile.mkdtemp(prefix="hermes-configprobe-"))
    try:
        ziel = ziel_home / "config.yaml"
        shutil.copy2(HOME / "config.yaml", ziel)
        text = ziel.read_text(encoding="utf-8")
        treffer = re.search(r"\$\{([^}]+)\}", text)
        if not treffer:
            print("Kein ${VAR}-Verweis in der config.yaml - Speicherprobe nicht sinnvoll.")
            return 2
        name = treffer.group(1)
        name = name[4:] if name.startswith("env:") else name
        os.environ[name] = "dummy-" + "x" * 29
        os.environ["HERMES_HOME"] = str(ziel_home)  # muss vor dem Import stehen
        sys.path.insert(0, str(CODE))
        import hermes_cli.config as cfgmod

        cfg = cfgmod.load_config()
        try:
            wert = hole(cfg, pfad)
        except (KeyError, TypeError):
            print("Pfad nicht gefunden: %s" % pfad)
            return 2
        print("aufgeloest im Temp-Zuhause: Laenge %d sha8 %s" % (len(wert), sha8(wert)))
        cfgmod.save_config(cfg)

        nachher = ziel.read_text(encoding="utf-8")
        verweis_ok = "${%s}" % treffer.group(1) in nachher
        verdaechtig = []
        for zeile in nachher.splitlines():
            if "token:" in zeile or "api_key:" in zeile:
                wert_teil = zeile.split(":", 1)[1].strip()
                if wert_teil and not wert_teil.startswith("${"):
                    verdaechtig.append(zeile.strip())
        print("Verweis nach dem Speichern erhalten:", verweis_ok)
        print("Klartext-Zeilen nach dem Speichern:", len(verdaechtig))
        for zeile in verdaechtig:
            print("  " + zeile[:60])
        return 0 if (verweis_ok and not verdaechtig) else 1
    finally:
        shutil.rmtree(ziel_home, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pfad", required=True,
                        help="Punktpfad in der config.yaml, z. B. a2a_agents.omniroute.auth.token")
    parser.add_argument("--speicherprobe", action="store_true",
                        help="Rundlauf in einem Temp-HERMES_HOME statt nur lesen")
    args = parser.parse_args()
    if args.speicherprobe:
        return speicherprobe(args.pfad)

    sys.path.insert(0, str(CODE))
    from hermes_cli.config import load_config
    from hermes_cli.env_loader import load_hermes_dotenv

    load_hermes_dotenv(hermes_home=HOME)
    try:
        wert = hole(load_config(), args.pfad)
    except (KeyError, TypeError):
        print("Pfad nicht gefunden: %s" % args.pfad)
        return 2
    print("%s: Laenge %d sha8 %s istVerweis %s"
          % (args.pfad, len(wert), sha8(wert), str(wert).startswith("${")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
