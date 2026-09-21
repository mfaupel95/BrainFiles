#!/usr/bin/env python3
"""Flottenbericht: warum ein Bot-Profil nicht antwortet - alle Profile auf einmal.

Ein einzelnes Profil zu befragen kostet einen Kaltstart (30-60 s); bei 29
Profilen raet man statt zu messen. Dieses Skript liest nur Dateien und sagt je
Profil vier Dinge: welches Modell gilt, ob dazu eine Anmeldung auf der Platte
liegt, wie viele Kanalzeilen es traegt (und wie viele davon das Startprofil
doppelt) und wie viele Rueckfall-Eintraege es hat.

Aufruf (aus Agenten/Hermes mit dem venv-Python von hermes-agent, weil
`hermes_cli.profile_channels` importiert wird; HERMES_HOME setzen, sonst wird
das falsche Home gelesen):

  export HERMES_HOME="<...>/Agenten/Hermes"; unset PYTHONHOME PYTHONPATH
  hermes-agent/venv/Scripts/python.exe skills/brainfiles/hermes-config-ops/scripts/profilflotte-bericht.py
  ... --nur-probleme     zeigt nur Profile mit Befund

Es wird NICHTS geschrieben. Zum Beheben:
`Agenten/Hermes/scripts/profil-kanaele-bereinigen.py` (Kanalzeilen),
`Agenten/Hermes/scripts/bot-modell-auf-router.py` (Modellkennung),
`Agenten/Hermes/scripts/bot-rueckfallkette-bereinigen.py` (Rueckfallkette) -
alle drei erst als Trockenlauf, dann mit `--anwenden`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Provider, die eine ANMELDUNG brauchen (auth.json: providers/credential_pool).
ANMELDE_PROVIDER = {"nous", "gemini", "anthropic", "copilot", "openai-codex",
                    "openrouter", "huggingface"}
LOKALE_PROVIDER = {"custom", "llamacpp", "ollama", "ollama-launch", "local",
                   "vllm", "llama.cpp", "llama-cpp"}
ZUGANGSDATEI_MUSTER = r"_API_KEY$|_TOKEN$|_KEY$|_SECRET$"


def kopfzeilen(config: Path):
    """{provider, model, kette} aus der config.yaml.

    Erst YAML lesen, dann erst das Zeilenmuster: der model:-Block steht nicht
    immer am Dateianfang - ein vorangestellter providers:-Block (z.B. im
    Wartungsbot) verschiebt ihn, und ein Regex ueber die ersten zwoelf Zeilen
    liest dann die falschen Schluessel. Gemessen 21.09.2026: hermes-wartung
    meldete 'kein model-Block; Provider ohne Block und ohne Zugangsdatei',
    obwohl die Datei sauber ist und der Bot antwortet.
    """
    aus = {"provider": "", "model": "", "kette": []}
    if not config.is_file():
        return aus
    text = config.read_text(encoding="utf-8", errors="replace")
    try:
        import yaml
        daten = yaml.safe_load(text) or {}
        block = daten.get("model")
        if isinstance(block, dict):
            aus["model"] = str(block.get("default") or "").strip("'\"")
            aus["provider"] = str(block.get("provider") or "").strip("'\"")
    except Exception:
        pass
    if not (aus["model"] or aus["provider"]):
        for zeile in text.splitlines()[:12]:
            treffer = re.match(r"\s+(default|provider):\s*(\S+)", zeile)
            if treffer:
                schluessel = "model" if treffer.group(1) == "default" else "provider"
                if not aus[schluessel]:
                    aus[schluessel] = treffer.group(2).strip("'\"")
    block = re.search(r"^fallback_providers:\s*(.*?)(?=^\S|\Z)",
                      text.replace("\r\n", "\n"), re.S | re.M)
    if block:
        for eintrag in re.finditer(r"model:\s*(\S+)", block.group(1)):
            aus["kette"].append(eintrag.group(1).strip("'\""))
    return aus


def anmeldungen(profil: Path):
    """Namen der hinterlegten Modellkennungen (keine Werte)."""
    aus = {"providers": [], "pool": [], "env": []}
    auth = profil / "auth.json"
    if auth.is_file():
        try:
            d = json.loads(auth.read_text(encoding="utf-8"))
            aus["providers"] = sorted((d.get("providers") or {}).keys())
            aus["pool"] = sorted((d.get("credential_pool") or {}).keys())
        except Exception:
            aus["providers"] = ["<auth.json unlesbar>"]
    env = profil / ".env"
    if env.is_file():
        for zeile in env.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            treffer = re.match(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", zeile)
            if treffer and treffer.group(2).strip() and re.search(ZUGANGSDATEI_MUSTER, treffer.group(1)):
                aus["env"].append(treffer.group(1))
    return aus


def eigene_provider(config: Path, env_pfad: Path) -> set:
    """Provider-Namen, die das Profil selbst mitbringt: `providers:`-Block
    oder eine Zugangsdatei-Variable, die den Namen traegt
    (`HERMES_CUSTOM_OMNIROUTE_API_KEY` -> `omniroute`)."""
    aus = set()
    if config.is_file():
        im_block = False
        for zeile in config.read_text(encoding="utf-8", errors="replace").splitlines():
            if zeile.rstrip() == "providers:":
                im_block = True
                continue
            if not im_block:
                continue
            if zeile and not zeile[0].isspace():
                break
            treffer = re.match(r"  (\S+):", zeile)
            if treffer:
                aus.add(treffer.group(1).strip("'\"").lower())
    if env_pfad.is_file():
        for zeile in env_pfad.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            treffer = re.match(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", zeile)
            if not treffer or not treffer.group(2).strip():
                continue
            name = treffer.group(1).lower()
            for teil in name.replace("hermes_custom_", "").split("_"):
                if len(teil) > 3:
                    aus.add(teil)
    return aus


def befunde(profil: Path, start: Path, kopf, anmeldung, doppelt, eigene):
    """Kurztexte: was hier nicht stimmen KANN (nur aus Dateien belegt)."""
    aus = []
    if not kopf["provider"]:
        aus.append("kein model-Block")
    if kopf["provider"] in ANMELDE_PROVIDER and \
            not ({kopf["provider"]} & set(anmeldung["providers"] + anmeldung["pool"])):
        aus.append("keine Modellanmeldung (%s)" % kopf["provider"])
    if kopf["provider"] not in ANMELDE_PROVIDER and kopf["provider"] not in LOKALE_PROVIDER \
            and kopf["provider"].lower() not in eigene:
        aus.append("Provider %r ohne Block und ohne Zugangsdatei" % kopf["provider"])
    if doppelt:
        aus.append("Kanalzeilen doppelt: " + ", ".join(doppelt))
    if kopf["kette"]:
        if kopf["kette"][0] == kopf["model"] or (kopf["provider"] == "omniroute" and
                                                any(k.startswith("auto/") for k in kopf["kette"])):
            aus.append("Kette ist keine Reserve (%d Eintraege, erster = Hauptziel)" % len(kopf["kette"]))
        klein = [k for k in kopf["kette"] if re.search(r"-8k|8192|4k", k)]
        if klein:
            aus.append("Kette nennt Kleinmodell: " + ", ".join(klein))
    return aus


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nur-probleme", action="store_true",
                    help="nur Profile mit Befund zeigen")
    args = ap.parse_args()

    hermes_home = Path(os.environ.get("HERMES_HOME") or
                       (Path(__file__).resolve().parents[3]))
    if not (hermes_home / "profiles").is_dir():
        print("HERMES_HOME zeigt nicht auf die Hermes-Wurzel: %s" % hermes_home)
        return 2
    sys.path.insert(0, str(hermes_home / "hermes-agent"))
    try:
        from hermes_cli.profile_channels import ChannelKeyIndex, shared_channel_credentials
    except Exception as fehler:
        print("hermes_cli nicht importierbar (%s) - mit dem venv-Python von "
              "hermes-agent starten." % fehler)
        return 2

    index = ChannelKeyIndex(hermes_home)
    zeilen, mit_befund = [], 0
    for profil in sorted(p for p in (hermes_home / "profiles").iterdir()
                         if p.is_dir() and not p.name.startswith(".")):
        kopf = kopfzeilen(profil / "config.yaml")
        anmeldung = anmeldungen(profil)
        doppelt = shared_channel_credentials(profil, hermes_home)
        kanaele = 0
        env = profil / ".env"
        if env.is_file():
            for zeile in env.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                treffer = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", zeile)
                if treffer and index.platform_for(treffer.group(1)):
                    kanaele += 1
        befunde_liste = befunde(profil, hermes_home, kopf, anmeldung, doppelt,
                                eigene_provider(profil / "config.yaml", env))
        mit_befund += bool(befunde_liste)
        zeilen.append((profil.name, kopf, anmeldung, kanaele, doppelt, befunde_liste))

    if not args.nur_probleme:
        print("%-28s %-26s %-16s %-7s %-6s %s"
              % ("Profil", "Modell", "Anmeldung", "Kanaele", "Kette", "Befund"))
        for name, kopf, anmeldung, kanaele, doppelt, befunde_liste in zeilen:
            anm = ",".join(anmeldung["providers"]) or ("pool:" + ",".join(anmeldung["pool"])
                                                       if anmeldung["pool"] else "-")
            print("%-28s %-26s %-16s %-7d %-6d %s"
                  % (name, "%s/%s" % (kopf["provider"], kopf["model"])[:26], anm[:16],
                     kanaele, len(kopf["kette"]), "; ".join(befunde_liste) or "ok"))
    else:
        for name, kopf, anmeldung, kanaele, doppelt, befunde_liste in zeilen:
            if befunde_liste:
                print("%-28s %s" % (name, "; ".join(befunde_liste)))
    print()
    print("%d Profil(e), %d mit Befund. Es wird nichts geschrieben - zum Beheben "
          "die drei Werkzeuge unter Agenten/Hermes/scripts/ als Trockenlauf starten."
          % (len(zeilen), mit_befund))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
