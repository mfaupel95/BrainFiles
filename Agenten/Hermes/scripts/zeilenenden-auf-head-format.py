"""Zeilenenden einer Datei auf das Format der HEAD-Fassung ziehen (Hausformat).

Warum: `hermes config set` schreibt die Datei neu, `read_text()` ohne
newline="" dreht CRLF still auf LF; danach zeigt der Diff die ganze Datei.
Dieses Werkzeug liest die dominante Endung aus HEAD und setzt ALLE Zeilen der
aktuellen Fassung darauf um - neue Zeilen bekommen dieselbe Endung.

Aufruf (aus der Repo-Wurzel):
    python Agenten/Hermes/scripts/zeilenenden-auf-head-format.py <pfad> [<pfad>...]
"""
import subprocess
import sys
from pathlib import Path


def head_enden(pfad):
    r = subprocess.run(["git", "show", "HEAD:" + pfad], capture_output=True)
    if r.returncode != 0:
        return None
    b = r.stdout
    return b"\r\n" if b.count(b"\r\n") * 2 > b.count(b"\n") else b"\n"


def main():
    for pfad in sys.argv[1:]:
        p = Path(pfad)
        soll = head_enden(pfad)
        if soll is None:
            print("%-52s nicht in HEAD - uebersprungen" % pfad)
            continue
        roh = p.read_bytes()
        zeilen = roh.split(b"\n")
        if zeilen and zeilen[-1] == b"":
            zeilen = zeilen[:-1]
        zeilen = [z[:-1] if z.endswith(b"\r") else z for z in zeilen]
        neu = soll.join(zeilen) + soll
        geaendert = neu != roh
        if geaendert:
            p.write_bytes(neu)
        print("%-52s Endung %s, %s" % (pfad, soll.decode().replace("\r", "CR"),
                                       "geschrieben" if geaendert else "schon richtig"))
    return 0


if __name__ == "__main__":
    sys.exit(main())