"""Abschnitt byte-sicher an eine bestehende Textdatei anhaengen.

Aufruf:  python spiegeln.py <zieldatei> <blockdatei> [--crlf|--lf]

Warum es das gibt: ein Rewrite normalisiert die Zeilenenden und erzeugt im Diff
eine Ganzdatei-Aenderung. Der Anhaenge-Weg liest Rohbytes, leitet das Zeilenende
ab und schreibt erst, wenn der fertige Inhalt feststeht.

Eigenschaften, die Absicht sind:
  * idempotent - existiert der Block schon im Rohbytes, wird nichts geschrieben
  * open(pfad,'wb') in der LETZTEN Zeile - Python wertet zuerst aus und kuerzt
    dann, ein Fehler im Ausdruck DANACH laesst die Datei leer
  * eine Hand voll geaenderter Zeilen statt Tausend

Nach jedem Lauf: git diff --numstat -- <ziel>.
"""
from __future__ import annotations

import os
import sys


def zeilenende(roh: bytes) -> bytes:
    """Das dominante Zeilenende der Datei. Ein gemischtes File braucht eine
    ausdrueckliche Entscheidung des Aufrufers (--crlf/--lf) - hier gewinnt die
    Majoritaet, und der Aufruf prueft das Ergebnis mit git diff --numstat."""
    crlf = roh.count(b"\r\n")
    lf = roh.count(b"\n")
    if crlf and crlf == lf:
        return b"\r\n"
    if crlf * 2 >= lf:
        return b"\r\n"
    return b"\n"


def haenge(pfad: str, block: str, ende: bytes | None = None) -> str:
    alt = open(pfad, "rb").read()
    roh_block = block.encode("utf-8")
    assert b"\r" not in roh_block, "Block darf kein CR enthalten"

    if ende is None:
        ende = zeilenende(alt)
    neu = roh_block.replace(b"\n", ende)

    if alt.strip() and neu.strip() in alt:
        return "unveraendert (Block existiert bereits)"

    kopf = alt
    if kopf and not kopf.endswith(b"\n") and not kopf.endswith(b"\r"):
        kopf = kopf + ende

    ergebnis = kopf + neu
    assert ergebnis != alt, "nichts zu schreiben"
    assert len(ergebnis) > len(alt)

    with open(pfad, "wb") as f:
        f.write(ergebnis)
    return "angehaengt: %s (+%d Bytes, Ende %r)" % (
        pfad, len(neu), ende)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ende = None
    if "--crlf" in sys.argv:
        ende = b"\r\n"
    elif "--lf" in sys.argv:
        ende = b"\n"
    if len(args) != 2:
        print(__doc__)
        print("Aufruf: python spiegeln.py <ziel> <block> [--crlf|--lf]")
        return 2
    ziel, blockdatei = args
    if not os.path.isfile(ziel):
        raise FileNotFoundError("Ziel fehlt: %s" % ziel)
    if not os.path.isfile(blockdatei):
        raise FileNotFoundError("Blockdatei fehlt: %s" % blockdatei)
    print(haenge(ziel, open(blockdatei, encoding="utf-8").read(), ende))
    print("Jetzt pruefen: git diff --numstat -- %s" % ziel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())