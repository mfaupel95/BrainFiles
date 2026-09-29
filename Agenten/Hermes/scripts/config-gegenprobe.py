#!/usr/bin/env python
"""Gegenprobe: Deklariertes in den Hermes-Configs gegen die Wirklichkeit pruefen.

Warum: Eine Config ist eine Sammlung von Behauptungen ("dieser Pfad existiert",
"dieser Dienst laeuft auf Port X", "dieses Modell ist da"). Faellt eine davon
aus, meldet das Werkzeug nichts - es scheitert erst, wenn der Pfad wirklich
gebraucht wird. Genau dann ist der Rueckfall schon der letzte Ausweg.

Geprueft wird (rein lesend, nichts wird geschrieben):

  1. Jeder `command:`-Pfad in `mcp_servers` der Hauptconfig (Existenz).
  2. Jede lokale Adresse (127.0.0.1/localhost mit Port) in Hauptconfig und
     Profilen: laeuft dort ein Dienst?
  3. Jeder lokale Modellname (Provider ollama-launch) in Hauptconfig und
     Profilen gegen den laufenden Ollama-Store (`/api/tags`).

Aufruf (aus dem Ordner Agenten/Hermes):

    python scripts/config-gegenprobe.py
    python scripts/config-gegenprobe.py --json      # maschinenlesbar

Rueckgabewert: 0 = alles belegt, 1 = mindestens ein Befund.
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
HERMES = HIER.parent
HAUPT = HERMES / "config.yaml"
PROFILE = HERMES / "profiles"
OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"

#: Provider, die auf einem LOKALEN Dienst laufen. Nur deren Modelle lassen
#: sich gegen den Store pruefen - alles andere ist Sache des Anbieters.
LOKALE_PROVIDER = {"ollama-launch", "ollama-local", "ollama", "bonsai", "llamacpp"}

RE_ADRESSE = re.compile(r"https?://(127\.0\.0\.1|localhost):(\d+)")
RE_COMMAND = re.compile(r"^\s+command:\s*(.+?)\s*$")
RE_MODEL = re.compile(r"^\s+(?:model|default_model):\s*(.+?)\s*$")
RE_LISTE = re.compile(r"^\s+-\s+([A-Za-z0-9_./:@+-]+)\s*$")


def store_modelle() -> tuple[set[str], str | None]:
    """Was der laufende Ollama-Dienst hat - oder warum nicht abfragbar."""
    try:
        with urllib.request.urlopen(OLLAMA_TAGS, timeout=8) as r:
            daten = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 - Grund ist Teil des Berichts
        return set(), f"{type(e).__name__}: {e}"
    namen: set[str] = set()
    for m in daten.get("models", []):
        n = m.get("name") or m.get("model") or ""
        if n:
            namen.add(n)
            namen.add(n.split(":", 1)[0])
    return namen, None


def port_offen(port: int, host: str = "127.0.0.1", timeout: float = 1.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def configs() -> list[Path]:
    dateien = [HAUPT] if HAUPT.exists() else []
    if PROFILE.is_dir():
        for p in sorted(PROFILE.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                c = p / "config.yaml"
                if c.exists():
                    dateien.append(c)
    return dateien


def pruefe(pfad: Path, store: set[str], dienste: dict[int, bool]) -> dict:
    """Eine Datei pruefen. Zeilenweise, damit Kommentare und Reihenfolge egal sind."""
    text = pfad.read_text(encoding="utf-8", errors="replace")
    zeilen = text.splitlines()
    befund = {"datei": str(pfad.relative_to(HERMES)), "pfade": [], "adressen": [],
              "modelle": [], "provider_block": False}

    # 1. command:-Pfade (nur Hauptconfig hat mcp_servers)
    for i, z in enumerate(zeilen):
        m = RE_COMMAND.match(z)
        if not m:
            continue
        wert = m.group(1).strip().strip('"\'')
        if wert in ("node", "docker", "npx", "uvx", "python", "pwsh"):
            continue  # Programm aus dem PATH, kein Pfad
        if re.match(r"^[A-Za-z]:[\\/]", wert):
            befund["pfade"].append({"zeile": i + 1, "pfad": wert,
                                    "da": Path(wert).exists()})

    # 2. lokale Adressen
    for i, z in enumerate(zeilen):
        for host, port_s in RE_ADRESSE.findall(z):
            port = int(port_s)
            if port not in dienste:
                dienste[port] = port_offen(port, host)
            befund["adressen"].append({"zeile": i + 1, "host": host, "port": port,
                                       "offen": dienste[port]})

    # 3. lokale Modellnamen - nur innerhalb eines lokalen Provider-Blocks
    # FALLE: ein Block endet nicht nur beim naechsten gleich eingerueckten
    # Schluessel, sondern auch beim naechsten Schluessel in Spalte 0. Ohne das
    # erbt ein top-level `fallback_providers:` die Einstufung des letzten
    # providers-Blocks und fremde Modellnamen (omniroute, llamacpp) gelten
    # faelschlich als lokal - ein Fehlalarm, der eine Reparatur ausloesen kann.
    lokal = False
    liste = False
    for i, z in enumerate(zeilen):
        if z and not z[0].isspace():          # Spalte 0 = neuer Top-Level-Block
            lokal = False
            continue
        if re.match(r"^  \S", z) and z.rstrip().endswith(":"):
            lokal = z.strip().rstrip(":").split(":")[0] in LOKALE_PROVIDER
            if lokal:
                befund["provider_block"] = True
            continue
        if not lokal:
            continue
        m = RE_MODEL.match(z)
        if m:
            wert = m.group(1).strip().strip('"\'')
            if wert and not wert.startswith("${") and wert != "bonsai":
                befund["modelle"].append({"zeile": i + 1, "modell": wert,
                                          "im_store": wert in store})
        # Auch die EINTRAEGE der models:-Liste sind Behauptungen. Sie stehen als
        # "- name: {}" oder "- name" und werden sonst nie geprueft.
        if lokal and re.match(r"^\s+models:\s*$", z):
            liste = True
            continue
        if liste:
            e = RE_LISTE.match(z)
            if not e:
                liste = False
                continue
            wert = e.group(1).strip().strip('"\'')
            if wert and not wert.startswith("${") and wert != "bonsai":
                befund["modelle"].append({"zeile": i + 1, "modell": wert,
                                          "im_store": wert in store})
    return befund


def main() -> int:
    ap = argparse.ArgumentParser(description="Config gegen die Wirklichkeit pruefen")
    ap.add_argument("--json", action="store_true", help="maschinenlesbare Ausgabe")
    args = ap.parse_args()

    store, fehler = store_modelle()
    dienste: dict[int, bool] = {}
    berichte = [pruefe(p, store, dienste) for p in configs()]

    fehlende_pfade = [(b["datei"], x) for b in berichte for x in b["pfade"] if not x["da"]]
    tote_adressen: dict[tuple[str, int], list[str]] = {}
    for b in berichte:
        for a in b["adressen"]:
            if not a["offen"]:
                tote_adressen.setdefault((a["host"], a["port"]), []).append(b["datei"])
    fehlende_modelle: dict[str, list[str]] = {}
    for b in berichte:
        for m in b["modelle"]:
            if not m["im_store"]:
                fehlende_modelle.setdefault(m["modell"], []).append(b["datei"])

    if args.json:
        print(json.dumps({"store_fehler": fehler, "store_modelle": sorted(store),
                          "fehlende_pfade": fehlende_pfade,
                          "tote_adressen": {f"{h}:{p}": sorted(set(d))
                                            for (h, p), d in tote_adressen.items()},
                          "fehlende_modelle": {k: sorted(set(v))
                                               for k, v in fehlende_modelle.items()}},
                         indent=2, ensure_ascii=False))
        return 1 if (fehlende_pfade or tote_adressen or fehlende_modelle or fehler) else 0

    print(f"Configs geprueft: {len(berichte)}")
    print(f"Ollama-Store:     {len(store)} Name(n)"
          + (f"  ABFRAGE FEHLGESCHLAGEN: {fehler}" if fehler else ""))
    print()

    if fehlende_pfade:
        print("FEHLENDE PROGRAMMPFADE (MCP-Server starten nicht):")
        for datei, x in fehlende_pfade:
            print(f"  {datei}:{x['zeile']}  {x['pfad']}")
    else:
        print("Programmpfade:    alle vorhanden")

    if tote_adressen:
        print()
        print("TOTE LOKALE ADRESSEN (Dienst laeuft nicht):")
        for (host, port), dateien in sorted(tote_adressen.items(), key=lambda kv: kv[0][1]):
            print(f"  {host}:{port}  betrifft {len(set(dateien))} Config(s): "
                  f"{', '.join(sorted(set(dateien))[:4])}")
    else:
        print("Lokale Adressen:  alle erreichbar")

    if fehlende_modelle:
        print()
        print("MODELLE NICHT IM STORE (Rueckfall greift nicht):")
        for name, dateien in sorted(fehlende_modelle.items()):
            print(f"  {name:<40} in {len(set(dateien))} Config(s)")
    else:
        print("Lokale Modelle:   alle im Store")

    print()
    offen = bool(fehlende_pfade or tote_adressen or fehlende_modelle or fehler)
    print("Befund: " + ("mindestens ein Punkt ist nicht belegt" if offen else "alles belegt"))
    return 1 if offen else 0


if __name__ == "__main__":
    sys.exit(main())