"""
Kommandozeile fuer den Mailversand - dieselbe Logik wie der MCP-Server.

Beispiele:
    .venv\\Scripts\\python.exe mail_cli.py --suche "ADHS Diagnostik" --betreff "Diagnose"
    .venv\\Scripts\\python.exe mail_cli.py --datei "Dokumente\\Privat\\Miete.pdf" --an chef@firma.de
    .venv\\Scripts\\python.exe mail_cli.py --pruefen

Ohne --an geht die Mail an die eigene Adresse zurueck.
"""

import argparse
import sys

import mailversand


def main() -> int:
    p = argparse.ArgumentParser(description="Datei aus dem Archiv per Mail verschicken.")
    p.add_argument("--datei", action="append", default=[],
                   help="Pfad im Archiv, mehrfach angebbar.")
    p.add_argument("--suche", help="Statt Pfad: Volltextsuche, bester Treffer wird angehaengt.")
    p.add_argument("--an", help="Empfaenger, mehrere durch Komma. Standard: man selbst.")
    p.add_argument("--betreff", default="", help="Betreffzeile.")
    p.add_argument("--text", default="", help="Nachrichtentext.")
    p.add_argument("--pruefen", action="store_true", help="Nur Anmeldung testen.")
    p.add_argument("--trockenlauf", action="store_true",
                   help="Anhaenge aufloesen und anzeigen, nichts verschicken.")
    args = p.parse_args()

    try:
        if args.pruefen:
            print(mailversand.zugang_pruefen())
            return 0

        anhaenge = list(args.datei)
        if args.suche:
            treffer = [t for t in mailversand.archiv_finden(args.suche, limit=5) if t["vorhanden"]]
            if not treffer:
                print(f"Kein Treffer fuer {args.suche!r}.", file=sys.stderr)
                return 1
            if len(treffer) > 1:
                print("Mehrere Treffer, genommen wird der erste:")
                for i, t in enumerate(treffer[:5]):
                    marke = "->" if i == 0 else "  "
                    print(f"  {marke} {t['pfad']}  ({t['groesse_kb']} KB)")
            anhaenge.append(treffer[0]["pfad"])

        if not anhaenge and not args.betreff and not args.text:
            print("Nichts zu senden: weder Anhang noch Betreff noch Text.", file=sys.stderr)
            return 1

        betreff = args.betreff
        if not betreff and anhaenge:
            betreff = mailversand.pfad_aufloesen(anhaenge[0]).stem

        if args.trockenlauf:
            for pfad in anhaenge:
                datei = mailversand.pfad_aufloesen(pfad)
                print(f"{datei}  ({datei.stat().st_size / 1024:.1f} KB)")
            print(f"Betreff: {betreff}")
            print("Trockenlauf - nichts verschickt.")
            return 0

        quittung = mailversand.senden(betreff=betreff, text=args.text, an=args.an,
                                      anhaenge=anhaenge)
        ziele = ", ".join(quittung["an"])
        namen = ", ".join(a["name"] for a in quittung["anhaenge"]) or "keine"
        print(f"Gesendet an {ziele} | Anhaenge: {namen} | {quittung['groesse_mb']} MB")
        if quittung.get("in_gesendet_abgelegt") is False:
            print("Hinweis: Ablage in 'Gesendet' fehlgeschlagen, die Mail ist trotzdem raus.")
        return 0

    except mailversand.VersandFehler as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
