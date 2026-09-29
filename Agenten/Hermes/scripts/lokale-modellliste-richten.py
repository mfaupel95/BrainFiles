#!/usr/bin/env python
"""Die `models:`-Liste lokaler Provider auf den echten Ollama-Stand ziehen.

Anlass (29.09.2026): Hauptconfig und 17 Profile trugen in `providers:
ollama-launch: models:` vier Namen, die im Store NICHT liegen
(`qwen3.8:27b`, `qwen3.8:latest`, `huihui_ai/qwen3-abliterated:32b`,
`kimi-k2.7-code:cloud`). Der Eintrag `model:`/`default_model:` war bereits
gerichtet, die Liste nicht - sie ist die zweite Behauptung derselben Sache.

Ein Listen-Eintrag wird nirgends erzwungen, aber er wird gelesen: die Liste ist
die Auswahl, aus der ein Mensch oder ein Modell einen lokalen Namen waehlt.
Steht dort ein Name, den der Dienst nicht kennt, faellt die Wahl erst beim
Aufruf auf - und dann ist der lokale Weg der Notausgang, der gerade gebraucht
wird.

Die Zielnamen stehen in KURATIERT und werden VOR jeder Aenderung gegen den
laufenden Dienst geprueft. Ohne Argument ist es ein TROCKENLAUF.

    python lokale-modellliste-richten.py               # zeigen, nichts schreiben
    python lokale-modellliste-richten.py --anwenden     # schreiben (je Datei .bak)
    python lokale-modellliste-richten.py --zuruecknehmen

Es werden NUR Zeilen innerhalb eines `models:`-Blocks eines LOKALEN Providers
angefasst (ollama-launch, ollama-local, ollama, llamacpp). Alles andere - etwa
die lange `auto/*`-Liste von omniroute - bleibt unberuehrt. Zeilenenden und
Kodierung bleiben erhalten (Bytes lesen, Bytes schreiben).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
HERMES = HIER.parent
PROFILE = HERMES / "profiles"
OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"

LOKALE_PROVIDER = {"ollama-launch", "ollama-local", "ollama"}

#: Was in der Liste stehen SOLL - nur Modelle, die sich fuer Agentenarbeit
#: eignen. Reihenfolge = Empfehlung: erst der Vorgabewert, dann die kleinen
#: schnellen, dann die grossen langsamen. Alles wird gegen den Store geprueft;
#: fehlt einer, wird er NICHT eingetragen, sondern gemeldet.
KURATIERT = [
    "gemma-e4b-8k:latest",
    "gemma-e4b-8k:cpu",
    "deepseek-chat:latest",
    "glm4:9b",
    "qwen3.5:9b",
    "deepseek-reasoner:latest",
]

RE_BLOCK = re.compile(r"^(  [A-Za-z0-9_.-]+):\s*$")          # provider-Ebene
RE_MODELS = re.compile(r"^(\s+)models:\s*$")
RE_EINTRAG = re.compile(r"^\s+-\s+\S")


def store_modelle() -> set[str]:
    with urllib.request.urlopen(OLLAMA_TAGS, timeout=10) as r:
        daten = json.loads(r.read().decode("utf-8"))
    namen: set[str] = set()
    for m in daten.get("models", []):
        n = m.get("name") or m.get("model") or ""
        if n:
            namen.add(n)
    return namen


def dateien() -> list[Path]:
    aus = [HERMES / "config.yaml"]
    if PROFILE.is_dir():
        for p in sorted(PROFILE.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                c = p / "config.yaml"
                if c.exists():
                    aus.append(c)
    return [p for p in aus if p.exists()]


def richten(pfad: Path, store: set[str], ziele: list[str], schreiben: bool) -> dict:
    roh = pfad.read_bytes()
    nl = b"\r\n" if b"\r\n" in roh else b"\n"
    text = roh.decode("utf-8")
    zeilen = text.split(nl.decode())
    aus: list[str] = []
    lokal = False
    i = 0
    ersetzt = 0
    while i < len(zeilen):
        z = zeilen[i]
        if z and not z[0].isspace():
            lokal = False
        m = RE_BLOCK.match(z)
        if m:
            lokal = m.group(1).strip() in LOKALE_PROVIDER
        aus.append(z)
        mm = RE_MODELS.match(z)
        if mm and lokal:
            einzug = mm.group(1)
            # alten Block ueberspringen
            j = i + 1
            alt: list[str] = []
            while j < len(zeilen) and RE_EINTRAG.match(zeilen[j]):
                alt.append(zeilen[j].strip().lstrip("-").strip())
                j += 1
            if alt != ziele:
                ersetzt += 1
                for name in ziele:
                    aus.append(f"{einzug}- {name}")
            else:
                aus.extend(zeilen[i + 1:j])
            i = j
            continue
        i += 1
    if not ersetzt:
        return {"datei": str(pfad.relative_to(HERMES)), "geaendert": False}
    if schreiben:
        stempel = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(pfad, pfad.with_name(pfad.name + f".bak-{stempel}"))
        pfad.write_bytes(nl.join(x.encode("utf-8") for x in aus))
    return {"datei": str(pfad.relative_to(HERMES)), "geaendert": True}


def zuruecknehmen() -> int:
    sicherungen = sorted(HERMES.glob("config.yaml.bak-*")) + \
        sorted(PROFILE.glob("*/config.yaml.bak-*"))
    if not sicherungen:
        print("Keine Sicherung gefunden.")
        return 1
    for s in sicherungen:
        ziel = s.with_name(s.name.split(".bak-")[0])
        shutil.copy2(s, ziel)
        print(f"zurueck: {ziel.relative_to(HERMES)}  <- {s.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="models:-Liste lokaler Provider richten")
    ap.add_argument("--anwenden", action="store_true", help="wirklich schreiben")
    ap.add_argument("--zuruecknehmen", action="store_true", help="Sicherungen zurueckspielen")
    args = ap.parse_args()
    if args.zuruecknehmen:
        return zuruecknehmen()

    store = store_modelle()
    fehlend = [n for n in KURATIERT if n not in store]
    ziele = [n for n in KURATIERT if n in store]
    print(f"Ollama-Store: {len(store)} Modell(e)")
    if fehlend:
        print(f"NICHT im Store, wird ausgelassen: {', '.join(fehlend)}")
    if not ziele:
        print("Kein einziger Zielname ist im Store - es wird nichts geaendert.")
        return 1
    print(f"Ziel-Liste ({len(ziele)}): {', '.join(ziele)}")
    print()
    print(("ANWENDEN - es wird geschrieben." if args.anwenden
           else "TROCKENLAUF - es wird nichts geschrieben."))
    print()
    betroffen = 0
    for p in dateien():
        r = richten(p, store, ziele, args.anwenden)
        if r["geaendert"]:
            betroffen += 1
            print(f"  {r['datei']}")
    print()
    print(f"{betroffen} Datei(en) {'geaendert' if args.anwenden else 'zu aendern'}.")
    if not args.anwenden and betroffen:
        print("Zum Schreiben: --anwenden")
    return 0


if __name__ == "__main__":
    sys.exit(main())