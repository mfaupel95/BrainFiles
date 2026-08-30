r"""
Generisches Werkzeug zum Aufraeumen loser Dateien im WURZELVERZEICHNIS eines
beliebigen Ordners - unabhaengig vom BrainFiles-Archiv (kann auf jedem
Laufwerk/Ordner laufen, auch ausserhalb dieses Projekts).

Entstanden aus einer Claude-Code-Sitzung, in der lose Dateien in
G:\Maximilian, G:\Carina und G:\Mary Ann manuell in Themenordner sortiert
wurden - dieses Skript macht dieselbe Sortierlogik wiederholbar, ohne dass
dafuer wieder eine KI-Sitzung noetig ist.

Unterschiede zu sort_inbox.py (das den Posteingang in die zentrale
Dokumente/-Struktur einsortiert):
  - arbeitet auf einem beliebigen Zielordner (Kommandozeilenargument), nicht
    auf Posteingang/
  - verschiebt NICHT in eine zentrale Archiv-Struktur, sondern legt die
    Themenordner direkt IM Zielordner an
  - ruehrt NUR lose Dateien im Wurzelverzeichnis an. Bestehende Unterordner
    werden nie betreten oder umbenannt - weder inhaltlich geprueft noch
    verschoben. Das ist bewusst so: Unterordner koennen bereits gewachsene,
    sinnvolle Strukturen sein (oder, wie bei diesem Anlass entdeckt, Inhalte
    enthalten, die man nicht automatisiert anfassen will).
  - reine Dateiname-Klassifizierung (kein OCR, kein Lesen von Dateiinhalten) -
    dadurch lauffaehig ohne die Zusatzabhaengigkeiten von index.py

Sicherheitsnetz:
  - Zertifikate/Schluessel/Passwort-aehnliche Dateien werden NIE automatisch
    verschoben, nur gemeldet (gleiche Regel wie in CLAUDE.md fuer das ganze
    Archiv: "nie automatisch verschieben oder archivieren - melden und
    liegen lassen").
  - Dateinamen mit deutlichen Hinweisen auf nicht jugendfreie Inhalte werden
    ebenfalls nur gemeldet, nicht einsortiert - das entscheidet der Mensch.
  - Bei Zielkollision gewinnt die neuere Datei (gleiches Verhalten wie
    sort_inbox.py); mit --dry-run laesst sich das vorher pruefen.

Aufruf:
    python sort_ordner.py "G:\\Pfad\\Zielordner" --dry-run
    python sort_ordner.py "G:\\Pfad\\Zielordner"
    python sort_ordner.py "G:\\Pfad\\Zielordner" --details
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

# Dateinamen mit Sonderzeichen (Umlaute etc.) wuerden ohne UTF-8 die Ausgabe
# auf der Windows-Konsole (cp1252) mitten im Lauf abbrechen.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic", ".tif", ".tiff", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v", ".mpg", ".mpeg", ".flv", ".webm", ".3gp"}
DOCUMENT_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp", ".txt", ".rtf"}
SOFTWARE_EXTS = {
    ".exe", ".msi", ".msix", ".msixbundle", ".dmg", ".app", ".pkg", ".dll", ".sys",
    ".inf", ".cat", ".bin", ".lnk", ".rdp", ".cmd", ".bat", ".ps1",
}

# Zertifikate/Schluessel/Zugangsdaten: nie automatisch verschieben, nur melden.
SENSITIVE_EXTS = {".pfx", ".p12", ".key", ".pem", ".crt", ".cer"}
SENSITIVE_NAME_PATTERNS = [
    "passw", "password", "kennwort", "credential", "secret",
    "private key", "privatekey", "zertifikat", "certificate",
]

# Deutliche Hinweise auf nicht jugendfreie Inhalte im Dateinamen selbst -
# solche Dateien werden nur gemeldet, nie automatisch einsortiert. Bewusst
# knapp gehalten, um Fehlalarme bei harmlosen Woertern zu vermeiden.
ADULT_HINT_PATTERNS = [
    "xhamster", "spankbang", "eporner", "pornhub", "onlyfans", "hentai",
    "xxx", "nsfw", "deepfake", " porn", "porn ", "porn.", "porn_", "porn-",
    "porno", " sex ", "gefickt", "ficken", "fickt", "bondage", "erotik",
]

# Sperr-/Sicherungsdateien von Office - kein Inhalt, nur Restmuell.
TEMP_NAME_MUSTER = ["~$", ".~lock", ".tmp", "thumbs.db", "desktop.ini"]

MACOS_JUNK_DEST = "macOS-Metadaten (kann geloescht werden)"

# Reihenfolge = Prioritaet. Erste passende Regel gewinnt. Schluesselwoerter
# werden gegen den Dateinamen geprueft (Unterstriche/Bindestriche wie
# Leerzeichen behandelt), Gross-/Kleinschreibung spielt keine Rolle.
KEYWORD_RULES = [
    ("Bewerbung", [
        "bewerbung", "lebenslauf", "lebenlauf", "anschreiben", "motivationsschreiben",
    ]),
    ("Finanzen und Versicherungen", [
        "kontoauszug", "gehaltsabrechnung", "lohnabrechnung", "kreditkarte",
        "ueberweisung", "überweisung", "rechnungsabschluss", "arbeitszeit",
        "azkto", "bafoeg", "bafög", "krankenkasse", "versicherung",
        "steuerbescheid", "elster", "dienstplan", "schichtplan", "gehalt",
    ]),
    ("Behoerden und Ausweise", [
        "personalausweis", "reisepass", "fuehrungszeugnis", "führungszeugnis",
        "meldebescheinigung", "geburtsurkunde", "gewerbeanmeldung", "registration",
        "zeugnis", "diplom", "hochschulreife",
    ]),
    ("Wohnen", ["mietvertrag", "nebenkosten", "kaution", "hausordnung", "vermieter"]),
    ("Gesundheit", ["arzt", "aerztlich", "ärztlich", "medikament", "attest", "diagnose", "befund"]),
    ("Studium", [
        "klausur", "seminar", "vorlesung", "immatrikulation", "hochschule",
        "universitaet", "universität", "bachelorarbeit", "masterarbeit",
        "pruefungsan", "prüfungsan", "modulhandbuch", "studienbescheinigung",
    ]),
    ("Bedienungsanleitungen", ["anleitung", "handbuch", "manual", "datenblatt", "faq"]),
    ("Belege und Tickets", ["rechnung", "beleg", "ticket", "quittung"]),
]


def normalisiert(name):
    return name.lower().replace("_", " ").replace("-", " ")


def ist_temp_datei(name):
    low = name.lower()
    return any(low.startswith(m) or low == m or low.endswith(m) for m in TEMP_NAME_MUSTER)


def ist_macos_junk(name):
    return name.startswith("._") or name in (".DS_Store", ".localized")


def ist_sensibel(name, ext):
    if ext in SENSITIVE_EXTS:
        return True
    low = name.lower()
    return any(p in low for p in SENSITIVE_NAME_PATTERNS)


def ist_adult_hint(name):
    low = f" {name.lower()} "
    return any(p in low for p in ADULT_HINT_PATTERNS)


def klassifiziere(path):
    """Entscheidet fuer eine Datei die Zielkategorie (Ordnername) - oder None,
    wenn sie unangetastet bleiben soll. Gibt (ziel_oder_None, grund) zurueck."""
    name = path.name
    ext = path.suffix.lower()

    if ist_temp_datei(name):
        return None, "Sperr-/Sicherungsdatei (kein Inhalt)"

    if ist_macos_junk(name):
        return MACOS_JUNK_DEST, "macOS-Metadatendatei"

    if ist_sensibel(name, ext):
        return None, "moeglicherweise sensibel (Zertifikat/Schluessel/Zugangsdaten) - manuell pruefen"

    if ist_adult_hint(name):
        return None, "moeglicherweise nicht jugendfreier Inhalt - manuell pruefen"

    name_norm = normalisiert(name)
    for ziel, keywords in KEYWORD_RULES:
        for kw in keywords:
            if kw in name_norm:
                return ziel, f"Dateiname enthaelt '{kw}'"

    if ext in SOFTWARE_EXTS:
        return "Alte Software und Treiber", f"Software-/Systemdatei ({ext})"

    if ext in IMAGE_EXTS:
        return "Fotos", "Bilddatei ohne weiteres Signal"

    if ext in VIDEO_EXTS:
        return "Videos", "Videodatei ohne weiteres Signal"

    if ext in DOCUMENT_EXTS:
        return None, f"Dokument ohne erkennbares Thema ({ext}) - manuell einsortieren"

    return None, f"unbekannter Dateityp ({ext or 'ohne Endung'}) - manuell pruefen"


def verschiebe(path, ziel_dir, dry):
    """Verschiebt eine Datei in ziel_dir. Bei Namenskollision gewinnt die
    neuere Datei (gleiches Verhalten wie sort_inbox.py) - kein automatisches
    Ueberschreiben ohne Vergleich.

    Systemgeschuetzte Dateien (Zugriff verweigert, in Benutzung durch ein
    anderes Programm o.ae.) duerfen den Lauf nicht abbrechen - eine einzelne
    gesperrte Datei wird stattdessen als uebersprungen gemeldet."""
    ziel = ziel_dir / path.name
    try:
        if ziel.exists():
            neuer = path.stat().st_mtime > ziel.stat().st_mtime
            if dry:
                return "dedup", "wuerde ersetzen (Quelle neuer)" if neuer else "wuerde geloescht (Ziel neuer)"
            if neuer:
                ziel.unlink()
                shutil.move(str(path), str(ziel))
                return "dedup", "ersetzt (Quelle war neuer)"
            path.unlink()
            return "dedup", "Duplikat geloescht (Ziel war neuer)"

        if dry:
            return "moved", None
        ziel_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(ziel))
        return "moved", None
    except PermissionError:
        return "skip", "gesperrt/geschuetzt (Zugriff verweigert)"
    except OSError as e:
        return "skip", f"Verschieben fehlgeschlagen ({type(e).__name__})"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pfad", help="Zielordner, dessen lose Root-Dateien sortiert werden sollen")
    parser.add_argument("--dry-run", action="store_true", help="nur anzeigen, was passieren wuerde - nichts verschieben")
    parser.add_argument("--details", action="store_true", help="jede Datei einzeln auflisten (Standard: nur Zahlen)")
    args = parser.parse_args()

    ziel_ordner = Path(args.pfad)
    if not ziel_ordner.is_dir():
        print(f"Ordner existiert nicht: {ziel_ordner}")
        return 1

    dateien = [p for p in sorted(ziel_ordner.iterdir()) if p.is_file()]
    if not dateien:
        print("Keine losen Dateien im Wurzelverzeichnis gefunden.")
        return 0

    dry = args.dry_run
    moved_by_dest = {}
    unsorted = []
    dedup = []

    for path in dateien:
        ziel, grund = klassifiziere(path)
        if ziel is None:
            unsorted.append((path.name, grund))
            continue

        ziel_dir = ziel_ordner / ziel
        art, hinweis = verschiebe(path, ziel_dir, dry)
        if art == "dedup":
            dedup.append((path.name, ziel, hinweis))
        elif art == "skip":
            unsorted.append((path.name, hinweis))
        else:
            moved_by_dest.setdefault(ziel, []).append((path.name, grund))

    header = "WUERDE einsortieren (Testlauf, nichts wurde verschoben)" if dry else "Einsortiert"
    gesamt = sum(len(v) for v in moved_by_dest.values())
    print(f"\n{header}: {gesamt}")
    if args.details:
        for ziel in sorted(moved_by_dest):
            eintraege = moved_by_dest[ziel]
            print(f"\n  {ziel}  ({len(eintraege)})")
            for name, grund in eintraege:
                print(f"    {name}   [{grund}]")
    else:
        for ziel in sorted(moved_by_dest):
            print(f"  {len(moved_by_dest[ziel]):5d}  {ziel}")

    if dedup:
        print(f"\nDuplikate bereinigt: {len(dedup)} (jeweils neuere Datei behalten)")
        if args.details:
            for name, ziel, hinweis in dedup:
                print(f"  {name}   ->  {ziel}   [{hinweis}]")

    if unsorted:
        print(f"\nBewusst NICHT angefasst, bleibt im Wurzelverzeichnis liegen: {len(unsorted)}")
        gruende = {}
        for _, grund in unsorted:
            gruende[grund] = gruende.get(grund, 0) + 1
        for g, n in sorted(gruende.items(), key=lambda x: -x[1]):
            print(f"  {n:5d}  {g}")
        if args.details:
            print()
            for name, grund in unsorted:
                print(f"    {name}   [{grund}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
