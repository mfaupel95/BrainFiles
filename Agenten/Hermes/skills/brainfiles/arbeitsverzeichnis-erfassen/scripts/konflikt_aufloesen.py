#!/usr/bin/env python3
"""Loest einen Git-Konflikt zugunsten der NEUEREN Seite (Stashed changes) auf.

Aufruf:  python konflikt_aufloesen.py <pfad>

Verhalten: entfernt die Konfliktmarker (<<<<<<< / ======= / >>>>>>>) und
behaelt die Seite NACH "=======" (Stashed changes). Vorher selbst entscheiden,
welche Seite gewinnt (generiert_at/Zeitstempel vergleichen), sonst ruft man
das Script in die falsche Richtung. Validiert JSON-Dateien, erhaelt CRLF/LF.

Exitcode 0 = geschrieben, 2 = JSON kaputt (nichts geschrieben).
"""

import json
import sys
from pathlib import Path


def resolve(text: str) -> str:
    """Behaelt die Stashed-changes-Seite (nach ======= bis >>>>>>>)."""
    out: list[str] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("<<<<<<<"):
            j = i
            while j < len(lines) and not lines[j].startswith("======="):
                j += 1
            k = j
            while k < len(lines) and not lines[k].startswith(">>>>>>>"):
                k += 1
            out.extend(lines[j + 1 : k])  # Stashed side
            i = k + 1
        else:
            out.append(line)
            i += 1
    return "\n".join(out)


def main() -> int:
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    resolved = resolve(text)

    if path.suffix.lower() == ".json":
        try:
            json.loads(resolved)
        except json.JSONDecodeError as exc:
            print(f"JSON INVALID - nichts geschrieben: {exc}")
            return 2

    # Zeilenenden der Quelldatei erhalten (sonst Ganzdatei-Diff)
    if "\r\n" in text:
        resolved = resolved.replace("\n", "\r\n")
    path.write_bytes(resolved.encode("utf-8"))
    print(f"Konflikt aufgeloest: {path} ({len(resolved.encode('utf-8'))} Bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
