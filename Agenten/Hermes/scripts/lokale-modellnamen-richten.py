#!/usr/bin/env python
"""Lokale Modellnamen in den Hermes-Configs auf den echten Store-Stand ziehen.

Anlass (29.09.2026): Alle 22 Profile trugen als lokalen Rueckfall
`qwen35-8k:cpu` und im providers-Block `gemma4:26b` / `gemma4:e4b` - KEINER
dieser Namen liegt im Ollama-Store. Dort heissen die Modelle heute
`gemma-e4b-8k:latest` und `gemma-e4b-8k:cpu`. Ein Rueckfall auf einen Namen,
den der Dienst nicht kennt, greift nicht - und niemand merkt es, bis der
Primaerpfad wirklich ausfaellt.

Das Werkzeug fragt den laufenden Dienst (`/api/tags`) und ersetzt NUR, wenn
der Zielname dort wirklich steht. Ohne Argument ist es ein TROCKENLAUF.

    python lokale-modellnamen-richten.py              # zeigen, nichts schreiben
    python lokale-modellnamen-richten.py --anwenden   # schreiben (je Datei .bak)
    python lokale-modellnamen-richten.py --zuruecknehmen

Es fasst nur die Zeilen an, die einen lokalen Modellnamen tragen, und erhaelt
Zeilenenden und Kodierung (Bytes lesen, Bytes schreiben).
"""
from __future__ import annotations

import json
import shutil
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent          # Agenten/Hermes/scripts
HERMES = HIER.parent                            # Agenten/Hermes
OLLAMA = "http://127.0.0.1:11434/api/tags"

#: Alter Name -> neuer Name. Der neue Name wird VOR der Ersetzung gegen den
#: laufenden Dienst geprueft; steht er dort nicht, wird die Datei uebersprungen.
ERSATZ = {
    "qwen35-8k:cpu": "gemma-e4b-8k:cpu",
    "qwen35-8k": "gemma-e4b-8k:latest",
    "gemma4:26b": "gemma-e4b-8k:latest",
    "gemma4:e4b": "gemma-e4b-8k:latest",
}


def store_modelle() -> set[str]:
    """Was der laufende Ollama-Dienst WIRKLICH hat (nicht, was in der Config steht)."""
    with urllib.request.urlopen(OLLAMA, timeout=10) as r:
        daten = json.loads(r.read().decode("utf-8"))
    namen = set()
    for m in daten.get("models", []):
        n = m.get("name") or m.get("model") or ""
        if n:
            namen.add(n)
            # Ollama liefert 'gemma-e4b-8k:latest'; ein Eintrag ohne Tag ist
            # derselbe Dienst-Eintrag.
            if ":" in n:
                namen.add(n.split(":", 1)[0])
    return namen


def dateien(nur_profile: bool = False) -> list[Path]:
    p: list[Path] = [] if nur_profile else [HERMES / "config.yaml"]
    p += sorted(HERMES.glob("profiles/*/config.yaml"))
    return [x for x in p if x.exists() and ".staging-" not in str(x)]


def zeilenenden(roh: bytes) -> bytes:
    return b"\r\n" if b"\r\n" in roh else b"\n"


def richte(pfad: Path, vorhanden: set[str], schreiben: bool) -> list[tuple[str, str, int]]:
    """Ersetzt die bekannten Altnamen. Rueckgabe: [(alt, neu, anzahl), ...].

    Arbeitet auf BYTES. Der erste Anlauf ging ueber Text und setzte die
    Zeilenenden danach noch einmal - aus CRLF wurde CRCRLF, und der Diff zeigte
    die ganze Datei (gemessen 29.09.2026: 2248/2248 statt 6/6). Ein Modellname
    ist ASCII, also ist die Byte-Ersetzung hier ohnehin das richtige Mittel:
    sie kann Kodierung und Zeilenenden nicht anfassen.
    """
    roh = pfad.read_bytes()
    treffer: list[tuple[str, str, int]] = []
    neu_roh = roh
    for alt, neu in ERSATZ.items():
        if neu not in vorhanden:
            continue                      # Zielname liegt nicht im Store: nicht raten
        a, n = alt.encode("ascii"), neu.encode("ascii")
        anzahl = neu_roh.count(a)
        if anzahl == 0:
            continue
        neu_roh = neu_roh.replace(a, n)
        treffer.append((alt, neu, anzahl))
    if not treffer or neu_roh == roh:
        return []
    if schreiben:
        shutil.copy2(pfad, pfad.with_name(pfad.name + ".bak-" + datetime.now().strftime("%Y%m%d")))
        pfad.write_bytes(neu_roh)
    return treffer


def zuruecknehmen(nur_profile: bool = False) -> int:
    n = 0
    for p in dateien(nur_profile):
        baks = sorted(p.parent.glob(p.name + ".bak-*"))
        if not baks:
            continue
        letzte = baks[-1]
        shutil.copy2(letzte, p)
        print("  zurueckgenommen: %s  <- %s" % (p.relative_to(HERMES), letzte.name))
        n += 1
    return n


def main() -> int:
    tun = "--anwenden" in sys.argv
    zurueck = "--zuruecknehmen" in sys.argv
    nur_profile = "--nur-profile" in sys.argv
    if zurueck:
        print("Zuruecknehmen:")
        print("  %d Datei(en) wiederhergestellt." % zuruecknehmen(nur_profile))
        return 0

    try:
        vorhanden = store_modelle()
    except Exception as e:                                  # noqa: BLE001
        print("Der Ollama-Dienst antwortet nicht (%s)." % e)
        print("Ohne die echte Modellliste wird NICHT geschrieben - der Ersatz waere geraten.")
        return 2

    print("Ollama-Store: %d Modell(e)" % len(vorhanden))
    print("Ersatzziel vorhanden?  " + ", ".join(
        "%s %s" % (neu, "OK" if neu in vorhanden else "FEHLT") for neu in sorted(set(ERSATZ.values()))))
    print()
    print("TROCKENLAUF - es wird nichts geschrieben." if not tun else "ANWENDEN - es wird geschrieben.")
    print()

    geaendert = 0
    for p in dateien(nur_profile):
        treffer = richte(p, vorhanden, tun)
        if treffer:
            geaendert += 1
            print("  %-30s %s" % (p.relative_to(HERMES),
                                  ", ".join("%s -> %s (%dx)" % t for t in treffer)))
    print()
    print("%d von %d Datei(en) betroffen." % (geaendert, len(dateien(nur_profile))))
    if not tun and geaendert:
        print("Zum Schreiben: --anwenden")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())