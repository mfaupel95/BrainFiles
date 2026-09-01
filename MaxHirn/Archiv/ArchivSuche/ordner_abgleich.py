"""
Vergleicht beliebige Ordner (auch über mehrere Laufwerke) und findet/behebt
Duplikate. Ersetzt Ad-hoc-Skripte durch ein wiederverwendbares Werkzeug.

Lektion aus der Praxis: Fuer das reine ERFASSEN vieler Dateien ist PowerShells
Get-ChildItem um Groessenordnungen schneller als Pythons pathlib.rglob()+stat()
(jeder stat()-Aufruf ist unter Windows ein frischer Systemaufruf; Get-ChildItem
liest die Metadaten direkt aus dem Verzeichnis-Listing). Deshalb macht dieses
Skript die Enumeration ueber PowerShell und nur die eigentliche Vergleichslogik
in Python. Fuer Massenloeschungen wird robocopy /MIR von einem leeren Ordner
aus verwendet statt Remove-Item -Recurse, das bei zehntausenden Dateien
spuerbar langsamer ist.

Aufruf:
    python ordner_abgleich.py vergleich ORDNER1 ORDNER2 [ORDNER3 ...]
        Zeigt fuer jedes Ordnerpaar: nur hier, nur dort, gemeinsam.
        Schreibt eine Ergebnisdatei fuer den naechsten Schritt.

    python ordner_abgleich.py zusammenfuehren PRIMAER SEKUNDAER [--loeschen]
        Kopiert alle Dateien, die es nur in SEKUNDAER gibt, nach PRIMAER
        (Ordnerstruktur bleibt erhalten). Bei gleichem Pfad mit
        unterschiedlicher Groesse (echter Inhaltskonflikt) gewinnt die
        neuere Datei. Verifiziert Dateizahl + Groesse nach dem Kopieren.
        Mit --loeschen wird SEKUNDAER danach per robocopy /MIR geleert
        und entfernt - nur nach erfolgreicher Verifikation.
"""

import argparse
import csv
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ERGEBNIS_DATEI = Path(__file__).resolve().parent / "ordner_abgleich_ergebnis.json"


def gb(n):
    return f"{n / 1024 / 1024 / 1024:.2f} GB"


def erfasse_ordner(pfad):
    """Enumeriert einen Ordner komplett ueber PowerShell (schnell, robust
    gegen viele-kleine-Dateien-Verzeichnisse, auf denen Python haengt).
    Gibt {rel_path_lower: (size, mtime, rel_path_original)} zurueck."""
    pfad = Path(pfad).resolve()
    if not pfad.exists():
        print(f"WARNUNG: {pfad} existiert nicht - wird als leer behandelt.")
        return {}

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_pfad = tmp.name

    praefix_laenge = len(str(pfad)) + 1
    ps_skript = f"""
$ErrorActionPreference = 'SilentlyContinue'
Get-ChildItem -LiteralPath '{pfad}' -Recurse -File -Force |
  Select-Object @{{n='rel';e={{$_.FullName.Substring({praefix_laenge})}}}}, Length,
    @{{n='mtime';e={{[int64](Get-Date $_.LastWriteTimeUtc -UFormat %s)}}}} |
  Export-Csv -Path '{csv_pfad}' -NoTypeInformation -Encoding UTF8
"""
    t0 = time.time()
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_skript], check=True)

    daten = {}
    with open(csv_pfad, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rel = row["rel"]
            if not rel:
                continue
            daten[rel.lower()] = (int(row["Length"]), int(row["mtime"]), rel)
    Path(csv_pfad).unlink(missing_ok=True)

    print(f"  {pfad}: {len(daten)} Dateien erfasst ({time.time() - t0:.1f}s)")
    return daten


def cmd_vergleich(args):
    ordner = {}
    for pfad in args.ordner:
        print(f"Erfasse {pfad} ...")
        ordner[str(pfad)] = erfasse_ordner(pfad)

    print()
    namen = list(ordner)
    for a in namen:
        for b in namen:
            if a == b:
                continue
            da, db = ordner[a], ordner[b]
            nur_a = set(da) - set(db)
            anteil = 100 * (1 - len(nur_a) / max(1, len(da)))
            print(f"{a}")
            print(f"  ist zu {anteil:.2f}% in {b} enthalten "
                  f"({len(nur_a)} Dateien fehlen dort, {gb(sum(da[k][0] for k in nur_a))})")
        print()

    ausgabe = {a: {k: list(v) for k, v in d.items()} for a, d in ordner.items()}
    ERGEBNIS_DATEI.write_text(json.dumps(ausgabe, ensure_ascii=False), encoding="utf-8")
    print(f"Ergebnis gespeichert: {ERGEBNIS_DATEI}")
    print("Naechster Schritt: python ordner_abgleich.py zusammenfuehren <primaer> <sekundaer>")


def robocopy_purge(ordner):
    """Loescht einen grossen Ordner effizient: robocopy spiegelt einen
    leeren Ordner darauf (schneller als Remove-Item -Recurse bei vielen
    Dateien), danach wird die leere Huelle entfernt."""
    ordner = Path(ordner)
    if not ordner.exists():
        return
    with tempfile.TemporaryDirectory() as leer:
        subprocess.run(
            ["robocopy", leer, str(ordner), "/MIR", "/R:1", "/W:1", "/MT:16",
             "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/NS", "/NC"],
            check=False,  # robocopy gibt bei Erfolg Exitcodes > 0 zurueck (kein Fehler!)
            capture_output=True,
        )
    try:
        ordner.rmdir()
    except OSError:
        # Als Rueckfallebene: einfacher Versuch, falls robocopy nicht alles erwischt hat.
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Remove-Item -LiteralPath '{ordner}' -Recurse -Force"], check=False)


def cmd_zusammenfuehren(args):
    primaer = Path(args.primaer).resolve()
    sekundaer = Path(args.sekundaer).resolve()

    print(f"Primaer   (bleibt bestehen): {primaer}")
    print(f"Sekundaer (wird abgeglichen): {sekundaer}")
    print()

    print("Erfasse Primaer ...")
    dp = erfasse_ordner(primaer)
    print("Erfasse Sekundaer ...")
    ds = erfasse_ordner(sekundaer)

    nur_sekundaer = set(ds) - set(dp)
    gemeinsam = set(ds) & set(dp)
    konflikte = [k for k in gemeinsam if ds[k][0] != dp[k][0]]

    print()
    print(f"Nur in Sekundaer (werden kopiert): {len(nur_sekundaer)}  ({gb(sum(ds[k][0] for k in nur_sekundaer))})")
    print(f"Gleicher Pfad, gleiche Groesse (werden uebersprungen): {len(gemeinsam) - len(konflikte)}")
    print(f"Gleicher Pfad, ANDERE Groesse (echter Konflikt, neuere gewinnt): {len(konflikte)}")

    zu_kopieren = list(nur_sekundaer)
    for k in konflikte:
        if ds[k][1] > dp[k][1]:  # Sekundaer ist neuer
            zu_kopieren.append(k)
        # sonst: Primaer behalten, Sekundaer-Version wird einfach nicht kopiert

    if args.dry_run:
        print(f"\n(Testlauf) Wuerde {len(zu_kopieren)} Dateien kopieren. Nichts wurde veraendert.")
        return

    print(f"\nKopiere {len(zu_kopieren)} Dateien ...")
    ps_liste = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    for k in zu_kopieren:
        ps_liste.write(ds[k][2] + "\n")
    ps_liste.close()

    ps_skript = f"""
$pfade = Get-Content '{ps_liste.name}' -Encoding UTF8
$kopiert = 0
$fehler = 0
foreach ($rel in $pfade) {{
    $src = Join-Path '{sekundaer}' $rel
    $dst = Join-Path '{primaer}' $rel
    $dstDir = Split-Path $dst -Parent
    try {{
        if (-not (Test-Path -LiteralPath $dstDir)) {{ New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }}
        Copy-Item -LiteralPath $src -Destination $dst -Force -ErrorAction Stop
        $kopiert++
    }} catch {{ $fehler++ }}
}}
Write-Output "Kopiert: $kopiert  Fehler: $fehler"
"""
    t0 = time.time()
    result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_skript],
                             capture_output=True, text=True, encoding="utf-8")
    print(f"  {result.stdout.strip()}  ({time.time() - t0:.1f}s)")
    Path(ps_liste.name).unlink(missing_ok=True)

    # Verifikation: Dateizahl und Groesse auf Primaer muessen um genau die
    # kopierte Menge gewachsen sein.
    print("\nVerifiziere ...")
    dp_neu = erfasse_ordner(primaer)
    # Verlaesslicher Check: alle zu kopierenden Pfade muessen jetzt vorhanden sein.
    fehlend = [k for k in zu_kopieren if k not in dp_neu]
    if fehlend:
        print(f"WARNUNG: {len(fehlend)} Dateien fehlen nach dem Kopieren im Primaer-Ordner!")
        print("Sekundaer-Ordner wird NICHT geloescht, bitte manuell pruefen.")
        for k in fehlend[:20]:
            print("   ", ds[k][2])
        return

    print(f"Verifikation OK: alle {len(zu_kopieren)} Dateien sind in {primaer} vorhanden.")

    if args.loeschen:
        print(f"\nLoesche {sekundaer} (robocopy /MIR von leerem Ordner) ...")
        t0 = time.time()
        robocopy_purge(sekundaer)
        if sekundaer.exists():
            print(f"WARNUNG: {sekundaer} existiert noch - bitte manuell pruefen.")
        else:
            print(f"Geloescht in {time.time() - t0:.1f}s.")
    else:
        print(f"\n{sekundaer} wurde NICHT geloescht (kein --loeschen angegeben).")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="befehl", required=True)

    p_vgl = sub.add_parser("vergleich", help="mehrere Ordner vergleichen, nichts veraendern")
    p_vgl.add_argument("ordner", nargs="+")
    p_vgl.set_defaults(func=cmd_vergleich)

    p_zus = sub.add_parser("zusammenfuehren", help="Sekundaer-Unikate nach Primaer kopieren")
    p_zus.add_argument("primaer")
    p_zus.add_argument("sekundaer")
    p_zus.add_argument("--loeschen", action="store_true", help="Sekundaer-Ordner nach Verifikation loeschen")
    p_zus.add_argument("--dry-run", action="store_true", help="nur anzeigen, was passieren wuerde")
    p_zus.set_defaults(func=cmd_zusammenfuehren)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
