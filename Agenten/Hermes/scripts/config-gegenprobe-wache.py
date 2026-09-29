#!/usr/bin/env python
"""Waechter fuer die Hermes-Configs: Behauptung gegen Wirklichkeit.

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut**, es wird nichts gesendet (Watchdog-Muster wie bus-waechter.py).

WARUM ES IHN GIBT
-----------------
Am 29.09.2026 trugen Hauptconfig und 17 Profile vier lokale Modellnamen, die im
Ollama-Store nicht lagen, und zwei Adressen ohne Dienst dahinter. Gefunden hat
das niemand von selbst - der Fehler zeigt sich erst, wenn der lokale Rueckfall
wirklich gebraucht wird, und dann ist er der letzte Ausweg.

Ein Nachweis, den niemand von selbst aufruft, ist keine Wache. Dieses Skript
fuehrt `config-gegenprobe.py` aus und meldet NUR, was sich aendert:

    - ein Programmpfad aus `mcp_servers` verschwindet
    - eine lokale Adresse wird tot oder kommt zurueck
    - ein lokaler Modellname faellt aus dem Store oder ist neu darin

Damit ist die woechentliche Wiederholung desselben Befunds keine Nachricht mehr
(die erste Meldung bleibt stehen, bis sie behoben ist).

Aufruf:
    python Agenten/Hermes/scripts/config-gegenprobe-wache.py            # echter Waechter
    python Agenten/Hermes/scripts/config-gegenprobe-wache.py --alle     # Lage immer zeigen
    python Agenten/Hermes/scripts/config-gegenprobe-wache.py --vergessen  # Merker loeschen
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                       # Agenten/Hermes/scripts/ -> BrainFiles
WERKZEUG = HIER.parent / "config-gegenprobe.py"
MERKDATEI = WURZEL / "Agenten" / "Hermes" / "cache" / "config-gegenprobe-wache.json"


def lade_werkzeug():
    spec = importlib.util.spec_from_file_location("config_gegenprobe", WERKZEUG)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["config_gegenprobe"] = modul
    spec.loader.exec_module(modul)
    return modul


def merker() -> dict:
    try:
        with open(MERKDATEI, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001 - fehlender/kaputter Merker ist kein Fehler
        return {}


def merke(stand: dict) -> None:
    MERKDATEI.parent.mkdir(parents=True, exist_ok=True)
    with open(MERKDATEI, "w", encoding="utf-8", newline="\n") as f:
        json.dump(stand, f, ensure_ascii=False, indent=1, sort_keys=True)


def lage(cp) -> dict:
    """Die drei Befundlisten als Mengen - nur so ist ein Wechsel messbar."""
    store, fehler = cp.store_modelle()
    dienste: dict[int, bool] = {}
    berichte = [cp.pruefe(p, store, dienste) for p in cp.configs()]

    pfade = {f"{b['datei']}:{x['zeile']}:{x['pfad']}"
             for b in berichte for x in b["pfade"] if not x["da"]}
    adressen = {f"{a['host']}:{a['port']}"
                for b in berichte for a in b["adressen"] if not a["offen"]}
    modelle = {m["modell"] for b in berichte for m in b["modelle"] if not m["im_store"]}
    return {"store_fehler": fehler or "", "pfade": sorted(pfade),
            "adressen": sorted(adressen), "modelle": sorted(modelle)}


def zeilen(jetzt: dict, vorher: dict, alle: bool) -> list[str]:
    aus: list[str] = []
    neu_p = [x for x in jetzt["pfade"] if x not in set(vorher.get("pfade", []))]
    neu_a = [x for x in jetzt["adressen"] if x not in set(vorher.get("adressen", []))]
    neu_m = [x for x in jetzt["modelle"] if x not in set(vorher.get("modelle", []))]

    if jetzt["store_fehler"] and jetzt["store_fehler"] != vorher.get("store_fehler"):
        aus.append(f"Ollama-Store nicht abfragbar: {jetzt['store_fehler']}")
    if neu_p:
        aus.append(f"Programmpfad fehlt jetzt ({len(neu_p)}):")
        aus += [f"  {x}" for x in neu_p[:8]]
    if neu_a:
        aus.append(f"Lokale Adresse ohne Dienst ({len(neu_a)}):")
        aus += [f"  {x}" for x in neu_a[:8]]
    if neu_m:
        aus.append(f"Modell nicht mehr im Store ({len(neu_m)}):")
        aus += [f"  {x}" for x in neu_m[:8]]
    if alle and not aus:
        offen = jetzt["pfade"] + jetzt["adressen"] + jetzt["modelle"]
        if offen:
            # WORTWAHL: "keine Aenderung" ist nicht "alles gut" - die offenen
            # Punkte stehen weiter da und gehoeren in denselben Satz.
            aus.append(f"Keine Aenderung. Weiterhin offen ({len(offen)}):")
            aus += [f"  Pfad fehlt:       {x}" for x in jetzt["pfade"]]
            aus += [f"  Adresse ohne Dienst: {x}" for x in jetzt["adressen"]]
            aus += [f"  Modell fehlt:     {x}" for x in jetzt["modelle"]]
        else:
            aus.append("Alles belegt: alle Programmpfade da, alle Adressen erreichbar, "
                       "alle lokalen Modelle im Store.")
    return aus


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Hermes-Configs gegen die Wirklichkeit")
    ap.add_argument("--alle", action="store_true", help="Lage auch ohne Aenderung zeigen")
    ap.add_argument("--vergessen", action="store_true", help="Merker loeschen")
    args = ap.parse_args(argv)

    if args.vergessen:
        MERKDATEI.unlink(missing_ok=True)
        print(f"Merker geloescht: {MERKDATEI}")
        return 0

    cp = lade_werkzeug()
    jetzt = lage(cp)
    vorher = merker()
    aus = zeilen(jetzt, vorher, args.alle)
    merke(jetzt)
    if aus:
        print("Config-Gegenprobe (Hermes):")
        print("\n".join(aus))
    return 0


if __name__ == "__main__":
    sys.exit(main())