"""Sucht intakte Fassungen zerstoerter Archivdateien und spielt sie zurueck.

Findet zu jeder mit 0xFF gefuellten Datei gleichnamige Kandidaten in einem
Suchpfad (externe Platte, Sicherung) und prueft **jeden einzelnen**, bevor er
als Rettung zaehlt. Namensgleichheit allein sagt nichts: von 261 Kandidaten
waren am 08.08.2026 ganze 220 selbst zerstoert.

    python rette_dateien.py O:\\                    # nur suchen und berichten
    python rette_dateien.py O:\\ --details          # jeden Treffer einzeln
    python rette_dateien.py O:\\ --uebernehmen      # gefundene zurueckspielen
    python rette_dateien.py O:\\ --bereich Bilder   # nur ein Archivteil

Ohne --uebernehmen wird nichts geschrieben. Das ist die Voreinstellung.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = os.path.dirname(os.path.abspath(__file__))
# Archivdaten seit 07.09.2026 auf O:\Archiv (ARCHIV_ROOT), Fallback alte Lage.
ARCHIV = os.environ.get("ARCHIV_ROOT") or os.path.dirname(HIER)
sys.path.insert(0, HIER)

from pruefe_signaturen import bewerte, UEBERSPRINGEN  # noqa: E402


def schluessel(name):
    """Vergleichsname: Unicode-Normalform angleichen, Gross/Klein egal.

    Ohne NFC-Angleich gelten Dateien mit Umlaut als verschieden, obwohl sie
    identisch heissen - macOS legt sie zerlegt ab (NFD), Windows zusammen (NFC).
    """
    return unicodedata.normalize("NFC", name).casefold()


def hashe(pfad):
    """SHA1 des Inhalts. Entscheidet, ob zwei Funde dieselbe Datei sind.

    Name und Groesse genuegen dafuer nicht: vier verschiedene Aufzeichnungen
    hatten schon einmal identischen Namen UND identische Groesse (1024,0 MB)
    und waren per Hash voellig unterschiedlich.
    """
    h = hashlib.sha1()
    try:
        with open(pfad, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
    except OSError:
        return pfad  # unlesbar: als eigener Wert behandeln, nie zusammenfassen
    return h.hexdigest()


def finde_schaeden(bereich):
    """Alle zerstoerten Dateien im Archiv."""
    wurzel = os.path.join(ARCHIV, bereich) if bereich else ARCHIV
    treffer = []
    for ordner, unter, dateien in os.walk(wurzel):
        unter[:] = [u for u in unter if u not in UEBERSPRINGEN]
        for name in dateien:
            pfad = os.path.join(ordner, name)
            befund, _ = bewerte(pfad, os.path.splitext(name)[1].lower())
            if befund.startswith("zerstoert"):
                treffer.append(pfad)
    return treffer


def liste_suchpfad(suchpfad):
    """Dateien im Suchpfad auflisten - ueber PowerShell.

    Get-ChildItem ist hier um Groessenordnungen schneller als os.walk oder
    pathlib: gemessen 65.939 Dateien in 6,5 Sekunden, wofuer Python auf einer
    externen Platte stundenlang haengt (jeder stat() ist ein Systemaufruf).
    """
    tmp = os.path.join(tempfile.gettempdir(), "rette_index.csv")
    ps = (
        f"Get-ChildItem -LiteralPath '{suchpfad}' -Recurse -File "
        f"-ErrorAction SilentlyContinue | "
        f"Select-Object Name,Length,FullName | "
        f"Export-Csv -LiteralPath '{tmp}' -Encoding UTF8 -NoTypeInformation"
    )
    print(f"Lese {suchpfad} ein (PowerShell) ...", flush=True)
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                       timeout=3600, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        print("  Abbruch: Einlesen dauerte laenger als eine Stunde.")
        return None

    if not os.path.exists(tmp):
        print("  Nichts eingelesen - Pfad erreichbar?")
        return None

    import csv
    nach_name = defaultdict(list)
    with open(tmp, encoding="utf-8-sig", newline="") as f:
        for zeile in csv.DictReader(f):
            try:
                nach_name[schluessel(zeile["Name"])].append(
                    (zeile["FullName"], int(zeile["Length"])))
            except (KeyError, ValueError):
                continue
    os.remove(tmp)
    print(f"  {sum(len(v) for v in nach_name.values())} Dateien erfasst.\n")
    return nach_name


def main():
    args = sys.argv[1:]
    details = "--details" in args
    uebernehmen = "--uebernehmen" in args
    args = [a for a in args if not a.startswith("--") or a == "--bereich"]
    bereich = ""
    if "--bereich" in args:
        i = args.index("--bereich")
        bereich = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    if not args:
        print(__doc__)
        return 1
    suchpfad = args[0]

    if not os.path.isdir(suchpfad):
        print(f"Suchpfad nicht erreichbar: {suchpfad}")
        return 1

    print("Suche zerstoerte Dateien im Archiv ...", flush=True)
    schaeden = finde_schaeden(bereich)
    print(f"  {len(schaeden)} zerstoerte Dateien.\n")
    if not schaeden:
        return 0

    nach_name = liste_suchpfad(suchpfad)
    if nach_name is None:
        return 1

    rettbar, mehrdeutig, nur_kaputt, kein_treffer = [], [], [], []

    for ziel in schaeden:
        name = os.path.basename(ziel)
        kandidaten = nach_name.get(schluessel(name), [])
        if not kandidaten:
            kein_treffer.append(ziel)
            continue
        heil = []
        for pfad, groesse in kandidaten:
            befund, _ = bewerte(pfad, os.path.splitext(pfad)[1].lower())
            if befund in ("intakt", "ungeprueft"):
                heil.append((pfad, groesse))
        if not heil:
            nur_kaputt.append((ziel, len(kandidaten)))
        elif len(set(hashe(p) for p, _ in heil)) == 1:
            # ein Kandidat, oder mehrere mit identischem Inhalt
            rettbar.append((ziel, heil))
        else:
            # verschiedene Fassungen - welche die richtige ist, entscheidet Max
            mehrdeutig.append((ziel, heil))

    print(f"eindeutig rettbar  {len(rettbar):>6}")
    print(f"mehrdeutig         {len(mehrdeutig):>6}   (verschiedene Fassungen)")
    print(f"nur kaputte Funde  {len(nur_kaputt):>6}")
    print(f"kein Kandidat      {len(kein_treffer):>6}")

    if mehrdeutig:
        print("\nMehrdeutig - hier wird nichts automatisch uebernommen:")
        for ziel, heil in mehrdeutig:
            print(f"  {os.path.relpath(ziel, ARCHIV)}")
            for pfad, groesse in sorted(heil, key=lambda x: -x[1]):
                print(f"       {groesse:>10} Byte  {pfad}")

    if details:
        for ziel, heil in rettbar:
            print(f"\n  ZIEL {os.path.relpath(ziel, ARCHIV)}")
            for pfad, groesse in heil:
                print(f"       <- {pfad}  ({groesse} Byte)")
        for ziel, n in nur_kaputt:
            print(f"  {n} Fund(e), alle zerstoert: {os.path.relpath(ziel, ARCHIV)}")

    if not uebernehmen:
        if rettbar:
            print("\nNichts geschrieben. Zum Zurueckspielen: --uebernehmen")
        return 0

    print("\nSpiele zurueck ...")
    zurueck = 0
    for ziel, heil in rettbar:
        quelle = heil[0][0]  # alle inhaltsgleich - geprueft per Hash
        befund, _ = bewerte(ziel, os.path.splitext(ziel)[1].lower())
        if not befund.startswith("zerstoert"):
            print(f"  UEBERSPRUNGEN (nicht mehr zerstoert): {os.path.basename(ziel)}")
            continue
        try:
            shutil.copy2(quelle, ziel)
        except OSError as e:
            print(f"  FEHLER {os.path.basename(ziel)}: {e}")
            continue
        nachher, _ = bewerte(ziel, os.path.splitext(ziel)[1].lower())
        if nachher.startswith("zerstoert"):
            print(f"  FEHLGESCHLAGEN, immer noch zerstoert: {os.path.basename(ziel)}")
        else:
            zurueck += 1

    print(f"\n{zurueck} von {len(rettbar)} zurueckgespielt und nachgeprueft.")
    print("Jetzt index.py laufen lassen, sonst bleiben sie unauffindbar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
