#!/usr/bin/env python3
"""Bot-Profile ohne eigene Modellanmeldung auf den lokalen Router umstellen.

Warum: Profile sind Inseln - sie lesen nur ihr eigenes `auth.json`/`.env`. 24
Bot-Profile stehen auf `provider: nous` (Nous-Portal), haben aber keine
Portal-Anmeldung im `auth.json`; jeder `/bot`-Aufruf endet mit "Hermes is not
logged into Nous Portal". Die Portal-Anmeldung in jedes Profil zu KOPIEREN
waere eine Vervielfaeltigung derselben Kennung (dieselbe Klasse Fehler wie bei
Telegram/Photon) und laut `auth.json` des Hauptprofils fragil (dort stand
`Refresh session has been revoked`). Stattdessen zeigen diese Profile auf den
lokalen OmniRoute-Router - dessen Schluessel steht als
`HERMES_CUSTOM_*_20128_API_KEY` schon in jeder Profil-`.env`, der
`providers.omniroute`-Block steht schon in jeder Profil-`config.yaml` (die
Unteragenten des Hauptprofils fahren denselben Weg).

Was gesetzt wird: `model.provider=omniroute`, `model.default=auto/best-coding`
und - falls gesetzt - der veraltete `model.base_url` auf das Portal entfernt.

Aufruf (aus Agenten/Hermes):

  python scripts/bot-modell-auf-router.py              # nur zeigen
  python scripts/bot-modell-auf-router.py --anwenden   # schreiben
  python scripts/bot-modell-auf-router.py --zuruecknehmen

Je Profil entsteht vorher `config.yaml.bak-JJJJMMTT`. Profile mit eigener
Portal-Anmeldung im `auth.json` und Profile, die schon auf dem Router laufen,
bleiben unberuehrt; alles andere wird mit Begruendung gemeldet.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

PORTAL_BASE = "https://inference-api.nousresearch.com/v1"
ZIEL_PROVIDER = "omniroute"
ZIEL_MODELL = "auto/best-coding"
# Provider, die eine Anmeldung beim Anbieter brauchen - nur die werden umgestellt.
UMSTELLBAR = ("nous", "gemini")


def hermes_aufruf(exe: Path, hermes_home: Path, *args):
    umgebung = dict(os.environ)
    umgebung.pop("PYTHONHOME", None)
    umgebung.pop("PYTHONPATH", None)
    umgebung["HERMES_HOME"] = str(hermes_home)
    lauf = subprocess.run([str(exe), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=umgebung)
    return lauf.returncode, (lauf.stdout or ""), (lauf.stderr or "")


def model_block(config: Path):
    """Die ersten Zeilen des model:-Blocks als dict."""
    felder = {}
    if not config.is_file():
        return felder
    for zeile in config.read_text(encoding="utf-8", errors="replace").splitlines()[:12]:
        treffer = re.match(r"\s+(default|provider|base_url):\s*(.*)", zeile)
        if treffer and treffer.group(1) not in felder:
            felder[treffer.group(1)] = treffer.group(2).strip().strip("'\"")
    return felder


def hat_portal_anmeldung(profil: Path) -> bool:
    auth = profil / "auth.json"
    if not auth.is_file():
        return False
    try:
        return bool((json.loads(auth.read_text(encoding="utf-8")).get("providers") or {}).get("nous"))
    except Exception:
        return False


def kommentar_schluss_zurueckholen(config: Path, sicherung: Path) -> int:
    """`hermes config set` schreibt die Datei neu und laesst den auskommentierten
    Doku-Block am Dateiende weg (gemessen: 38 Zeilen in 6 Profilen). Der Fix ist
    nicht "Block anhaengen", sondern die Ziel-Fassung exakt bauen: Sicherung
    uebernehmen und nur den model-Block ersetzen. Rueckgabe: zurueckgeholte Zeilen.
    """
    alt = sicherung.read_text(encoding="utf-8").splitlines(keepends=True)
    ist = config.read_text(encoding="utf-8")
    zeilen = alt
    for i, z in enumerate(zeilen):
        if z.rstrip("\r\n") == "model:":
            kopf, rest, ersetzt = zeilen[:i + 1], zeilen[i + 1:], 0
            while rest and re.match(r"\s+(default|provider|base_url):", rest[0]):
                rest, ersetzt = rest[1:], ersetzt + 1
            if ersetzt < 2:
                return 0
            neu = "".join(kopf + ["  default: %s\r\n" % ZIEL_MODELL,
                                  "  provider: %s\r\n" % ZIEL_PROVIDER] + rest)
            if neu == ist:
                return 0
            fehlend = len(alt) - len(ist.splitlines(keepends=True))
            config.write_text(neu, encoding="utf-8", newline="")
            return max(fehlend, 0)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anwenden", action="store_true", help="schreiben")
    ap.add_argument("--zuruecknehmen", action="store_true",
                    help="config.yaml.bak-JJJJMMTT zuruecklegen")
    args = ap.parse_args()
    if args.anwenden and args.zuruecknehmen:
        print("--anwenden und --zuruecknehmen schliessen sich aus.")
        return 2

    hermes_home = Path(__file__).resolve().parent.parent      # Agenten/Hermes
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
        print()
        print(("%d Profil(e) zurueckgenommen." % zurueck) if zurueck
              else "Keine Sicherung config.yaml.bak-* gefunden.")
        return 0

    umgestellt, uebersprungen, fehler = [], [], []
    for p in profile:
        config = p / "config.yaml"
        block = model_block(config)
        frisch = block.get("provider")
        if hat_portal_anmeldung(p):
            uebersprungen.append((p.name, "eigene Portal-Anmeldung im auth.json"))
            continue
        if frisch == ZIEL_PROVIDER:
            uebersprungen.append((p.name, "laeuft schon ueber den Router"))
            continue
        if frisch not in UMSTELLBAR:
            uebersprungen.append((p.name, "Provider %r braucht keine Anmeldung" % frisch))
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
        if block.get("base_url", "") == PORTAL_BASE:
            hermes_aufruf(exe, hermes_home, "-p", p.name, "config", "unset", "model.base_url")
        zeilen_nachher = len(config.read_text(encoding="utf-8", errors="replace").splitlines())
        hinweis = ""
        if zeilen_vorher - zeilen_nachher > 1:      # mehr als die base_url-Zeile kann nur
            zurueck = kommentar_schluss_zurueckholen(config, sicherung)   # der Kommentar-Schluss sein
            hinweis = ("  Kommentar-Schluss zurueckgeholt (%d Zeile(n))" % zurueck
                       if zurueck else
                       "  ACHTUNG Zeilen %d -> %d" % (zeilen_vorher, zeilen_nachher))
        neu = model_block(config)
        if neu.get("provider") != ZIEL_PROVIDER or neu.get("default") != ZIEL_MODELL:
            fehler.append((p.name, "nicht angekommen: %s" % neu))
            continue
        umgestellt.append((p.name, frisch, neu.get("default", "?")))
        print("%-28s %-8s -> %s%s" % (p.name, frisch, ZIEL_MODELL, hinweis))

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
        print("Wirklich schreiben: --anwenden   (je Profil vorher config.yaml.bak-%s)"
              % date.today().strftime("%Y%m%d"))
    for name, grund in fehler:
        print("FEHLER %-24s %s" % (name, grund))
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
