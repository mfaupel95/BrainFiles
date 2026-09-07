"""Prueft Dateien auf zerstoerten Inhalt anhand ihrer Magic Bytes.

Hintergrund: Ein Netzteildefekt hat mehrere Platten gleichzeitig zerstoert.
Die Dateinamen wurden noch geschrieben, die Inhalte nicht - solche Dateien
sind vollstaendig mit 0xFF (oder 0x00) gefuellt.

Standardausgabe ist eine Zusammenfassung. Details nur mit --details.

    python pruefe_signaturen.py                # ganzes Archiv
    python pruefe_signaturen.py Bilder         # nur ein Unterordner
    python pruefe_signaturen.py --details      # jede kaputte Datei einzeln
    python pruefe_signaturen.py --csv out.csv  # Liste zum Weiterverarbeiten
"""

import csv
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Die Archivdaten liegen seit dem 07.09.2026 auf O:\Archiv; ARCHIV_ROOT zeigt
# darauf (User-Umgebungsvariable, wie in index.py). Fallback auf die alte
# Vault-Lage, damit das Tool nach einem SSD-Umzug ohne gesetzte Variable laeuft.
ARCHIV = os.environ.get("ARCHIV_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ordner, die nicht zum eigentlichen Archiv gehoeren
UEBERSPRINGEN = {"ArchivSuche", "Posteingang", ".git", "__pycache__", ".venv"}

# Erwartete Signaturen je Endung.
#   praefix : Bytes ab Offset 0
#   bei_4   : Bytes ab Offset 4 (ISO-BMFF: die ersten 4 Byte sind die Boxlaenge)
SIGNATUREN = {
    ".pdf":  {"praefix": [b"%PDF"]},
    ".png":  {"praefix": [b"\x89PNG"]},
    ".gif":  {"praefix": [b"GIF8"]},
    ".bmp":  {"praefix": [b"BM"]},
    ".tif":  {"praefix": [b"II*\x00", b"MM\x00*"]},
    ".tiff": {"praefix": [b"II*\x00", b"MM\x00*"]},
    ".webp": {"praefix": [b"RIFF"]},
    # JPEG faengt selbst mit FF an - deshalb ist hier die exakte Folge noetig,
    # sonst gilt jedes gesunde Foto als zerstoert.
    ".jpg":  {"praefix": [b"\xff\xd8\xff"]},
    ".jpeg": {"praefix": [b"\xff\xd8\xff"]},
    ".heic": {"bei_4": [b"ftyp"]},
    ".heif": {"bei_4": [b"ftyp"]},
    ".mp4":  {"bei_4": [b"ftyp"]},
    ".mov":  {"bei_4": [b"ftyp"]},
    ".m4a":  {"bei_4": [b"ftyp"]},
    ".zip":  {"praefix": [b"PK\x03\x04", b"PK\x05\x06"]},
    ".docx": {"praefix": [b"PK\x03\x04"]},
    ".xlsx": {"praefix": [b"PK\x03\x04"]},
    ".pptx": {"praefix": [b"PK\x03\x04"]},
    ".doc":  {"praefix": [b"\xd0\xcf\x11\xe0"]},
    ".xls":  {"praefix": [b"\xd0\xcf\x11\xe0"]},
    ".mp3":  {"praefix": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"]},
    ".flac": {"praefix": [b"fLaC"]},
    ".ogg":  {"praefix": [b"OggS"]},
    ".wav":  {"praefix": [b"RIFF"]},
    ".7z":   {"praefix": [b"7z\xbc\xaf"]},
    ".rar":  {"praefix": [b"Rar!"]},
    ".exe":  {"praefix": [b"MZ"]},
}

KOPF = 16          # so viele Bytes lesen wir je Datei
FUELLPROBE = 4096  # so viel fuer die Fuellbyte-Pruefe


def bewerte(pfad, endung):
    """Gibt (befund, detail) zurueck."""
    try:
        with open(pfad, "rb") as f:
            kopf = f.read(KOPF)
            if not kopf:
                return "leer", ""
            probe = kopf + f.read(FUELLPROBE - KOPF)
    except OSError as e:
        return "unlesbar", type(e).__name__

    # Vollstaendig gefuellt? Das ist das Schadensbild des Netzteildefekts.
    einzig = set(probe)
    if len(einzig) == 1:
        b = einzig.pop()
        if b == 0xFF:
            return "zerstoert_ff", "0xFF"
        if b == 0x00:
            return "zerstoert_null", "0x00"
        return "zerstoert_ff", f"0x{b:02X}"

    regel = SIGNATUREN.get(endung)
    if regel is None:
        return "ungeprueft", ""

    for p in regel.get("praefix", []):
        if kopf.startswith(p):
            return "intakt", ""
    for p in regel.get("bei_4", []):
        if kopf[4:4 + len(p)] == p:
            return "intakt", ""

    return "fremde_signatur", kopf[:8].hex(" ")


def main():
    args = [a for a in sys.argv[1:]]
    details = "--details" in args
    if details:
        args.remove("--details")
    csv_pfad = None
    if "--csv" in args:
        i = args.index("--csv")
        csv_pfad = args[i + 1]
        del args[i:i + 2]
    wurzel = os.path.join(ARCHIV, args[0]) if args else ARCHIV

    if not os.path.isdir(wurzel):
        print(f"Kein Ordner: {wurzel}")
        return 1

    zaehler = Counter()
    je_endung = Counter()
    treffer = []
    gesamt = 0

    for ordner, unter, dateien in os.walk(wurzel):
        unter[:] = [u for u in unter if u not in UEBERSPRINGEN]
        for name in dateien:
            pfad = os.path.join(ordner, name)
            endung = os.path.splitext(name)[1].lower()
            befund, detail = bewerte(pfad, endung)
            gesamt += 1
            zaehler[befund] += 1
            if befund.startswith("zerstoert") or befund in ("fremde_signatur", "unlesbar"):
                je_endung[(befund, endung or "(ohne)")] += 1
                treffer.append((befund, detail, os.path.relpath(pfad, ARCHIV)))

    print(f"Geprueft: {gesamt} Dateien unter {os.path.relpath(wurzel, ARCHIV)}\n")
    for befund in ("intakt", "ungeprueft", "zerstoert_ff", "zerstoert_null",
                   "leer", "fremde_signatur", "unlesbar"):
        if zaehler[befund]:
            print(f"  {befund:<16} {zaehler[befund]:>7}")

    if je_endung:
        print("\nAuffaellige Dateien nach Endung:")
        for (befund, endung), n in sorted(je_endung.items(), key=lambda x: -x[1]):
            print(f"  {befund:<16} {endung:<8} {n:>6}")

    if details:
        print("\nEinzeln:")
        for befund, detail, rel in sorted(treffer):
            print(f"  {befund:<16} {detail:<12} {rel}")

    if csv_pfad:
        with open(csv_pfad, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["befund", "detail", "pfad"])
            w.writerows(treffer)
        print(f"\nListe geschrieben: {csv_pfad} ({len(treffer)} Zeilen)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
