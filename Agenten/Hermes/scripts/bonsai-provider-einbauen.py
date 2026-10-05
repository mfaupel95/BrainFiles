"""Fuegt den Provider `bonsai` in die Hermes-config.yaml ein (byte-genau, CRLF bleibt).

Hintergrund: `hermes config set` schneidet den Kommentar-Schluss der Datei ab und
schreibt LF statt CRLF - deshalb hier ein gezielter Einfuegesatz mit Sicherung.
Ohne Argument: Trockenlauf. --anwenden schreibt. --zuruecknehmen holt die Sicherung zurueck.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Kein fester Benutzerpfad: dieses Skript liegt in Agenten\Hermes\scripts.
CONFIG = Path(__file__).resolve().parents[1] / "config.yaml"
MARKER = b"providers:\r\n"
BLOCK = (
    "  bonsai:\r\n"
    "    api: http://127.0.0.1:8081/v1\r\n"
    "    base_url: http://127.0.0.1:8081/v1\r\n"
    "    default_model: bonsai\r\n"
    "    model: bonsai\r\n"
    "    name: Bonsai 2 27B (lokal, PrismML-Fork)\r\n"
    "    discover_models: true\r\n"
).encode("utf-8")


def ist_drin(text: bytes) -> bool:
    return b"\r\n  bonsai:\r\n" in text


def schreiben(roh: bytes, ziel: Path) -> None:
    ziel.write_bytes(roh)


def main() -> int:
    anwenden = "--anwenden" in sys.argv
    zurueck = "--zuruecknehmen" in sys.argv
    roh = CONFIG.read_bytes()

    if zurueck:
        sicherungen = sorted(CONFIG.parent.glob("config.yaml.bak-*"))
        if not sicherungen:
            print("keine Sicherung gefunden")
            return 1
        schreiben(sicherungen[-1].read_bytes(), CONFIG)
        print("zurueckgenommen aus", sicherungen[-1].name)
        return 0

    crlf = "CRLF" if b"\r\n" in roh else "LF"
    zeilen = roh.count(b"\n")
    print(f"{CONFIG} - {len(roh)} Bytes, {zeilen} Zeilen, {crlf}")

    if ist_drin(roh):
        print("Provider `bonsai` steht schon drin - nichts zu tun")
        return 0

    if MARKER not in roh:
        print("Anker 'providers:' nicht gefunden - abgebrochen")
        return 1

    neu = roh.replace(MARKER, MARKER + BLOCK, 1)
    if not anwenden:
        print("Trockenlauf. Einzufuegen nach 'providers:' ->")
        print(BLOCK.decode("utf-8"))
        print(f"danach {len(neu)} Bytes (Diff {len(neu) - len(roh):+d})")
        return 0

    stempel = datetime.now().strftime("%Y%m%d%H%M%S")
    sicherung = CONFIG.with_name(f"config.yaml.bak-{stempel}")
    shutil.copy2(CONFIG, sicherung)
    schreiben(neu, CONFIG)

    geprueft = CONFIG.read_bytes()
    nach = geprueft.count(b"\n")
    crlf_neu = "CRLF" if b"\r\n" in geprueft else "LF"
    print("Sicherung:", sicherung.name)
    print(f"geschrieben: {len(geprueft)} Bytes, {nach} Zeilen, {crlf_neu} (vorher {zeilen} Zeilen)")
    print("bonsai drin:", ist_drin(geprueft))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())