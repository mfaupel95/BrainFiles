#!/usr/bin/env python3
"""Bot-Profile auf das Nous-Portal umstellen (deepseek-v4-flash-0731).

Warum: Der lokale Router faellt als Traeger aus, sobald seine Combo auf einen
toten Zweig zeigt (gemessen 21.09.2026: `auto/best-coding` -> `oc/big-pickle`,
403 "OpenCode's free tier can only be used from within OpenCode" + 500
server_error) - dann stehen ALLE Bots still. Das Nous-Portal ist die Quelle,
die das Hauptprofil ohnehin benutzt.

Voraussetzung: die Profil-Sitzung. Ein Profil ohne eigene `auth.json` kommt
nicht an den Anbieter ("Hermes is not logged into Nous Portal"). Werkzeug
dafuer: `scripts/auth-verknuepfen.ps1` (Symlink auf den Root-Store, erhoehte
Shell) - NICHT die Sitzung kopieren (dieselbe Refresh-Kennung in vielen
Dateien, eine Rotation entwertet die anderen).

Aufruf (aus Agenten/Hermes):

  python scripts/bot-modell-auf-nous.py              # nur zeigen
  python scripts/bot-modell-auf-nous.py --anwenden   # schreiben
  python scripts/bot-modell-auf-nous.py --auch-lokale --anwenden
  python scripts/bot-modell-auf-nous.py --zuruecknehmen

Ohne `--auch-lokale` bleiben Profile auf lokalen Providern (llamacpp, docker,
ollama) stehen; mit dem Schalter kommen sie mit (Max 21.09.2026: "alle auf nous").
Ein lokales `base_url` wird beim Umstellen entfernt, sonst zeigt der Aufruf
weiter auf den lokalen Endpunkt.

Je Profil entsteht vorher `config.yaml.bak-JJJJMMTT`. Profile mit eigener
Portal-Anmeldung und Profile, die schon auf nous laufen, bleiben unberuehrt.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

ZIEL_PROVIDER = "nous"
ZIEL_MODELL = "deepseek/deepseek-v4-flash-0731"
PORTAL_BASE = "https://inference-api.nousresearch.com/v1"
# Provider, die eine Anmeldung beim Anbieter brauchen - nur die werden umgestellt.
UMSTELLBAR = ("omniroute", "nous", "gemini")
# Lokale Provider (llamacpp, docker) laufen ohne Anmeldefrei und brauchen kein
# Portal - sie werden nur mit --auch-lokale angefasst (Max: "alle auf nous").
UMSTELLBAR_LOKAL = ("llamacpp", "docker", "ollama-launch", "llama.cpp", "ollama",
                    "vllm", "custom")


def hermes_aufruf(exe: Path, hermes_home: Path, *args):
    umgebung = dict(os.environ)
    umgebung.pop("PYTHONHOME", None)
    umgebung.pop("PYTHONPATH", None)
    umgebung["HERMES_HOME"] = str(hermes_home)
    lauf = subprocess.run([str(exe), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=umgebung)
    return lauf.returncode, (lauf.stdout or ""), (lauf.stderr or "")


def model_block(config: Path):
    """model:-Block per YAML lesen (der Block steht nicht immer am Dateianfang -
    ein vorangestellter providers:-Block verschiebt ihn; ein Regex ueber die
    ersten Zeilen liest dann die falschen Schluessel)."""
    if not config.is_file():
        return {}
    try:
        import yaml
        daten = yaml.safe_load(config.read_text(encoding="utf-8", errors="replace")) or {}
    except Exception:
        return {}
    block = daten.get("model")
    if not isinstance(block, dict):
        return {}
    return {k: str(v).strip().strip("'\"") for k, v in block.items() if isinstance(v, (str, int, float))}


def auth_lage(profil: Path):
    """(hat_eigene_sitzung, ist_verknuepft) - Sitzung im eigenen oder im Root-Store."""
    auth = profil / "auth.json"
    if not auth.exists():
        return False, False
    try:
        verknuepft = auth.is_symlink()
    except OSError:
        verknuepft = False
    if verknuepft:
        return True, True
    try:
        return bool((json.loads(auth.read_text(encoding="utf-8")).get("providers") or {}).get("nous")), False
    except Exception:
        return False, False


def kommentar_schluss_zurueckholen(config: Path, sicherung: Path) -> int:
    """`hermes config set` schreibt die Datei neu und laesst den auskommentierten
    Doku-Block am Dateiende weg. Fix: die Ziel-Fassung exakt bauen - Sicherung
    uebernehmen, nur den model-Block ersetzen. Rueckgabe: zurueckgeholte Zeilen.

    BINAER lesen und schreiben: `read_text()` ohne `newline=""` uebersetzt CRLF
    zu LF - danach zeigt der Diff die GANZE Datei (5 Profile, 21.09.2026).
    """
    roh = sicherung.read_bytes()
    nl = b"\r\n" if b"\r\n" in roh else b"\n"
    alt = roh.split(nl)
    if alt and alt[-1] == b"":
        alt.pop()
    ist = config.read_bytes()
    for i, z in enumerate(alt):
        if z == b"model:":
            kopf, rest, ersetzt = alt[:i + 1], alt[i + 1:], 0
            while rest and re.match(rb"\s+(default|provider|base_url):", rest[0]):
                rest, ersetzt = rest[1:], ersetzt + 1
            if ersetzt < 2:
                return 0
            neu = nl.join(kopf + [b"  default: " + ZIEL_MODELL.encode(),
                                  b"  provider: " + ZIEL_PROVIDER.encode()] + rest) + nl
            if neu == ist:
                return 0
            fehlend = len(alt) - len(ist.split(nl))
            config.write_bytes(neu)
            return max(fehlend, 0)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anwenden", action="store_true", help="schreiben")
    ap.add_argument("--zuruecknehmen", action="store_true",
                    help="config.yaml.bak-JJJJMMTT zuruecklegen")
    ap.add_argument("--auch-lokale", action="store_true",
                    help="auch Profile auf lokalen Providern (llamacpp, docker, ollama) umstellen")
    args = ap.parse_args()
    if args.anwenden and args.zuruecknehmen:
        print("--anwenden und --zuruecknehmen schliessen sich aus.")
        return 2

    hermes_home = Path(__file__).resolve().parent.parent
    exe = hermes_home / "bin" / "hermes.exe"
    if not exe.is_file():
        print("hermes.exe nicht gefunden: %s" % exe)
        return 2
    profile = sorted(p for p in (hermes_home / "profiles").iterdir()
                     if p.is_dir() and not p.name.startswith("."))
    if not profile:
        print("Keine Profile unter %s" % (hermes_home / "profiles"))
        return 1

    if args.zuruecknehmen:
        zurueck = 0
        for p in profile:
            sicherungen = sorted(p.glob("config.yaml.bak-*"))
            if not sicherungen:
                continue
            shutil.copy2(sicherungen[-1], p / "config.yaml")
            print("%-28s zurueck aus %s" % (p.name, sicherungen[-1].name))
            zurueck += 1
        print("\n%d Profil(e) zurueckgenommen." % zurueck)
        return 0

    umstellbar = tuple(UMSTELLBAR) + (UMSTELLBAR_LOKAL if args.auch_lokale else ())
    umgestellt, uebersprungen, fehler = [], [], []
    for p in profile:
        config = p / "config.yaml"
        block = model_block(config)
        frisch = block.get("provider")
        sitzung, verknuepft = auth_lage(p)
        if frisch not in umstellbar:
            uebersprungen.append((p.name, "Provider %r braucht keine Anmeldung" % frisch))
            continue
        if frisch == ZIEL_PROVIDER and block.get("default") == ZIEL_MODELL:
            uebersprungen.append((p.name, "laeuft schon auf %s" % ZIEL_MODELL))
            continue
        if not sitzung:
            uebersprungen.append((p.name, "ohne Anmeldung (auth-verknuepfen.ps1 fehlt)"))
            continue
        if not args.anwenden:
            umgestellt.append((p.name, frisch, block.get("default", "?")))
            continue

        zeilen_vorher = len(config.read_text(encoding="utf-8", errors="replace").splitlines())
        sicherung = config.with_name("config.yaml.bak-" + date.today().strftime("%Y%m%d"))
        if not sicherung.exists():
            shutil.copy2(config, sicherung)
        rc, _, err = hermes_aufruf(exe, hermes_home, "-p", p.name,
                                   "config", "set", "model.provider", ZIEL_PROVIDER)
        if rc:
            fehler.append((p.name, "provider: " + err.strip()[-160:]))
            continue
        rc, _, err = hermes_aufruf(exe, hermes_home, "-p", p.name,
                                   "config", "set", "model.default", ZIEL_MODELL)
        if rc:
            fehler.append((p.name, "default: " + err.strip()[-160:]))
            continue
        base = block.get("base_url", "")
        if base and base != PORTAL_BASE:
            # lokaler Endpunkt (llamacpp/docker/ollama) zeigt sonst weiter dorthin
            hermes_aufruf(exe, hermes_home, "-p", p.name, "config", "unset", "model.base_url")
        zeilen_nachher = len(config.read_text(encoding="utf-8", errors="replace").splitlines())
        hinweis = ""
        if zeilen_vorher - zeilen_nachher > 1:
            zurueck = kommentar_schluss_zurueckholen(config, sicherung)
            hinweis = ("  Kommentar-Schluss zurueckgeholt (%d Zeile(n))" % zurueck
                       if zurueck else "  ACHTUNG Zeilen %d -> %d" % (zeilen_vorher, zeilen_nachher))
        neu = model_block(config)
        if (neu.get("provider") != ZIEL_PROVIDER or neu.get("default") != ZIEL_MODELL
                or neu.get("base_url", "") not in ("", PORTAL_BASE)):
            fehler.append((p.name, "nicht angekommen: %s" % neu))
            continue
        umgestellt.append((p.name, frisch, neu.get("default", "?")))
        print("%-28s %-10s -> %s%s" % (p.name, frisch, ZIEL_MODELL, hinweis))

    for name, grund in uebersprungen:
        print("%-28s unberuehrt: %s" % (name, grund))
    if not args.anwenden and umgestellt:
        print()
        for name, alt, modell in umgestellt:
            print("%-28s waere: %s -> %s   (vorher %s)" % (name, alt, ZIEL_MODELL, modell))
    print()
    print("%d Profil(e) %s, %d uebersprungen, %d Fehler."
          % (len(umgestellt), "umgestellt" if args.anwenden else "umzustellen",
             len(uebersprungen), len(fehler)))
    if not args.anwenden and umgestellt:
        print("Wirklich schreiben: --anwenden   (je Profil vorher config.yaml.bak-JJJJMMTT)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())