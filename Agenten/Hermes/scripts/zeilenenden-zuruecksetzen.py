"""Setzt die Zeilenenden einer Textdatei auf den Stand von HEAD zurueck.

WARUM
-----
Das Patch-Werkzeug (und jedes andere Werkzeug, das die Datei neu schreibt)
normalisiert Zeilenenden: es schreibt CRLF, wo LF stand. In Dateien mit
GEMISCHTEN Enden - `MaxHirn/Wissen/Routinen.md` ist CRLF mit einzelnen
LF-Zeilen - entstehen dadurch Aenderungen, die niemand gemacht hat. Sie sind im
Diff nicht von echten Aenderungen zu unterscheiden und gehen beim naechsten Mal
als "gehoert so" durch.

Das Skript vergleicht die aktuelle Datei Zeile fuer Zeile mit HEAD: findet es
denselben Zeileninhalt in HEAD mit einem anderen Ende, stellt es das HEAD-Ende
wieder her. Neue Zeilen (in HEAD nicht vorhanden) bleiben unangetastet.

Aufruf ueber das terminal-Werkzeug, aus der Repo-Wurzel:
    python Agenten/Hermes/scripts/zeilenenden-zuruecksetzen.py <pfad> [<pfad>...]

Danach IMMER `git diff --stat <pfad>` pruefen: es darf nur noch die gewollte
Zeile zeigen.
"""
import subprocess
import sys
from pathlib import Path


def teile(text):
    """[(inhalt, ende)] je Zeile; ende ist '\\n', '\\r\\n' oder '' (letzte)."""
    stuecke = text.split("\n")
    out = []
    for i, zeile in enumerate(stuecke):
        letzte = (i == len(stuecke) - 1)
        if zeile.endswith("\r"):
            out.append((zeile[:-1], "\r\n"))
        elif letzte:
            out.append((zeile, ""))
        else:
            out.append((zeile, "\n"))
    return out


def head_fassung(pfad):
    r = subprocess.run(["git", "show", "HEAD:" + pfad], capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", errors="replace")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    fehler = 0
    for pfad in sys.argv[1:]:
        head = head_fassung(pfad)
        if head is None:
            print("%-46s nicht in HEAD - uebersprungen" % pfad)
            fehler = 1
            continue
        enden = {}
        for inhalt, ende in teile(head):
            enden.setdefault(inhalt, ende)
        jetzt = Path(pfad).read_text(encoding="utf-8")
        neu, korrigiert = [], 0
        for inhalt, ende in teile(jetzt):
            soll = enden.get(inhalt)
            if soll is not None and soll != ende:
                neu.append(inhalt + soll)
                korrigiert += 1
            else:
                neu.append(inhalt + ende)
        Path(pfad).write_text("".join(neu), encoding="utf-8", newline="")
        print("%-46s %d Zeilenende(n) zurueckgesetzt" % (pfad, korrigiert))
    return fehler


if __name__ == "__main__":
    sys.exit(main())
