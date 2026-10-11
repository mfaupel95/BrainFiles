#!/usr/bin/env python3
"""platforms.photon.enabled: false in die 6 Profile ohne platforms-Block setzen.

Befund 11.10.2026: 25 von 33 Profilen tragen den Block bereits, 6 nicht.
Ein Profil OHNE den Block erbt die PHOTON_*-Werte der Haupt-.env (es hat
keine eigenen) und gilt damit als photon-aktiv - der Gateway lehnt es dann
als doppelte Kennung ab (error_code duplicate_credential). Es gibt nur EINE
Photon-Kennung im Haus; sie gehoert `default`. Die 25 anderen Profile sind
deshalb richtig konfiguriert.

Aenderung: am Dateiende anhaengen (jeweils eigene Zeilenenden erhalten)

    platforms:
      photon:
        enabled: false
"""
from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

import yaml

HOME = Path(r"C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes")
PROFILE = HOME / "profiles"
STAMP = date.today().strftime("%Y%m%d")

ZIEL = ["basic-memory", "bots", "findusarbeitus", "fomo-radar", "lokal-first", "recherche"]

BLOCK = {"platforms": {"photon": {"enabled": False}}}


def block_text(zeilenende: str) -> str:
    return (
        f"platforms:{zeilenende}"
        f"  photon:{zeilenende}"
        f"    enabled: false{zeilenende}"
    )


def main() -> int:
    anwenden = "--anwenden" in sys.argv
    gesamt_diff = []

    for name in ZIEL:
        cfg = PROFILE / name / "config.yaml"
        if not cfg.is_file():
            print(f"  {name:20} FEHLT")
            continue

        roh = cfg.read_bytes()
        crlf = b"\r\n" in roh
        zeilenende = "\r\n" if crlf else "\n"
        text = roh.decode("utf-8")

        vorher = yaml.safe_load(text)
        if vorher is None:
            print(f"  {name:20} UEBERSPRUNGEN: Datei leer")
            continue

        # Schon vorhanden? Dann nichts tun.
        if isinstance(vorher.get("platforms"), dict) and "photon" in vorher["platforms"]:
            print(f"  {name:20} schon konfiguriert - uebersprungen")
            continue

        neu_text = text
        if not neu_text.endswith(("\n", "\r")):
            neu_text += zeilenende
        neu_text += block_text(zeilenende)

        nachher = yaml.safe_load(neu_text)

        # Invarianten: nur `platforms` ist dazugekommen, sonst nichts geaendert
        assert nachher.get("platforms") == BLOCK["platforms"], f"{name}: platforms falsch"
        rest_vor = {k: v for k, v in vorher.items() if k != "platforms"}
        rest_nach = {k: v for k, v in nachher.items() if k != "platforms"}
        assert rest_vor == rest_nach, f"{name}: ausserhalb platforms hat sich etwas geaendert!"

        vor_zeilen = text.count("\n")
        nach_zeilen = neu_text.count("\n")
        zuwachs = nach_zeilen - vor_zeilen

        print(f"  {name:20} {'CRLF' if crlf else 'LF  '}  +{zuwachs} Zeilen  "
              f"Schluessel {len(vorher)} -> {len(nachher)}")

        if anwenden:
            sicherung = cfg.with_name(cfg.name + f".bak-{STAMP}")
            if not sicherung.exists():
                shutil.copy2(cfg, sicherung)
            cfg.write_bytes(neu_text.encode("utf-8"))
            gesamt_diff.append(name)

    print()
    if anwenden:
        print(f"Geschrieben: {len(gesamt_diff)} Datei(en). Sicherungen: config.yaml.bak-{STAMP}")
    else:
        print("Trockenlauf - schreiben mit --anwenden")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
