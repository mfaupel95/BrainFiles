#!/usr/bin/env python3
"""Bot-Profile und Haupt-Config auf nous/meituan/longcat-2.5-preview:free umstellen.

Auftrag Max 05.10.2026: alle Standardmodelle der Bots auf longcat 2.5 preview
free, und ueberall wo stealth/space-bunny-alpha stand jetzt longcat 2.5.

Was das Werkzeug aendert (bytegenau, Zeilenenden bleiben erhalten):
  1. Jedes profil/config.yaml: der `model.default`-Wert -> ZIEL (provider bleibt
     nous; Profile auf anderen Providern werden gemeldet, nicht angefasst).
  2. Jede config.yaml (Haupt UND Profile): jeder Rest `stealth/space-bunny-alpha`
     -> ZIEL (Delegation, MoA-Aggregatoren, fallback_providers).
  3. Haupt config.yaml: der Katalog-Eintrag `stealth/space-bunny-alpha: {}` wird
     ENTFERNT - meituan/longcat-2.5-preview:free steht dort bereits (Zeile ~152),
     ein Duplikat wuerde still den LETZTEN Key gewinnen lassen.
  4. Kommentar-Erwaehungen von space-bunny-alpha in config.yaml werden mitgezogen
     (Doku soll zur Konfiguration passen).

NICHT angefasst: delegation.fallback_providers, MoA-referenz_modelle, Einstellungen
der Profile (bleiben wie sie sind - es geht nur um das Standardmodell).

Aufruf (aus Agenten/Hermes):

  python scripts/bot-modell-auf-longcat.py              # nur zeigen
  python scripts/bot-modell-auf-longcat.py --anwenden   # schreiben
  python scripts/bot-modell-auf-longcat.py --zuruecknehmen

Je config.yaml entsteht vorher config.yaml.bak-JJJJMMTT (nur wenn keine da ist).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ZIEL = "meituan/longcat-2.5-preview:free"
ALT = "stealth/space-bunny-alpha"
HAUPT = Path(__file__).resolve().parent.parent / "config.yaml"
# Skill-Doku, die den alten Modellnamen in einer Tabelle traegt (nur Doku).
DOKU = (Path(__file__).resolve().parent.parent /
        "skills" / "brainfiles" / "hermes-config-ops" /
        "references" / "auxiliary-kompression.md")

DEFAULT_RE = re.compile(r"(?m)^(model:\r?\n[ \t]+default: )\S+")


def lese_zeilenenden(p: Path) -> bytes:
    roh = p.read_bytes()
    return b"\r\n" if b"\r\n" in roh else b"\n"


def ersetze_default(roh: bytes) -> tuple[bytes, bool]:
    text = roh.decode("utf-8", errors="replace")
    m = DEFAULT_RE.search(text)
    if not m:
        return roh, False
    neu = DEFAULT_RE.sub(lambda mm: mm.group(1) + ZIEL, text, count=1)
    return neu.encode("utf-8"), True


def ersetze_alt(roh: bytes) -> tuple[bytes, int]:
    """Alle Rest-Vorkommen von stealth/space-bunny-alpha -> ZIEL."""
    text = roh.decode("utf-8", errors="replace")
    n = text.count(ALT)
    if not n:
        return roh, 0
    return text.replace(ALT, ZIEL).encode("utf-8"), n


def katalog_eintrag_entfernen(roh: bytes, nl: bytes) -> tuple[bytes, bool]:
    """Loescht die Zeile '<einrueckung>stealth/space-bunny-alpha: {}' aus einem
    Modell-Katalog (providers.nous.models) - longcat steht dort schon."""
    zeilen = roh.split(nl)
    neu = [z for z in zeilen if b"space-bunny-alpha: {}" not in z]
    if len(neu) == len(zeilen):
        return roh, False
    return nl.join(neu), True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anwenden", action="store_true", help="schreiben")
    ap.add_argument("--zuruecknehmen", action="store_true",
                    help="config.yaml.bak-JJJJMMTT zuruecklegen")
    args = ap.parse_args()
    if args.anwenden and args.zuruecknehmen:
        print("--anwenden und --zuruecknehmen schliessen sich aus.")
        return 2

    hermes_home = Path(__file__).resolve().parent.parent
    datei_satz = [HAUPT] + sorted(p / "config.yaml"
                                  for p in (hermes_home / "profiles").iterdir()
                                  if p.is_dir() and not p.name.startswith(".")
                                  and (p / "config.yaml").is_file())
    if DOKU.is_file():
        datei_satz.append(DOKU)

    if args.zuruecknehmen:
        zurueck = 0
        for datei in datei_satz:
            sicherungen = sorted(datei.parent.glob(datei.name + ".bak-*"))
            if not sicherungen:
                continue
            shutil.copy2(sicherungen[-1], datei)
            print("%-46s zurueck aus %s" % (datei.name, sicherungen[-1].name))
            zurueck += 1
        print("\n%d Datei(en) zurueckgenommen." % zurueck)
        return 0

    geaendert, unveraendert, fehler = [], [], []
    for datei in datei_satz:
        if not datei.is_file():
            fehler.append((datei.name, "fehlt"))
            continue
        roh = datei.read_bytes()
        nl = lese_zeilenenden(datei)
        ist_haupt = datei == HAUPT
        aenderungen: list[str] = []

        if ist_haupt:
            # Katalog-Eintrag ZUERST entfernen, sonst schreibt ersetze_alt ihn zu
            # longcat um und es entsteht ein Duplikat (longcat steht schon im Katalog).
            neu, entf = katalog_eintrag_entfernen(roh, nl)
            if entf:
                aenderungen.append("Katalog-Eintrag entfernt (longcat ist schon gelistet)")
                roh = neu
        else:
            neu, geaendert_d = ersetze_default(roh)
            if geaendert_d:
                aenderungen.append("default -> %s" % ZIEL)
                roh = neu
        neu, n_alt = ersetze_alt(roh)
        if n_alt:
            aenderungen.append("space-bunny (%d) -> %s" % (n_alt, ZIEL))
            roh = neu

        if not aenderungen:
            unveraendert.append(datei.name)
            continue
        if not args.anwenden:
            geaendert.append((datei.name, ", ".join(aenderungen)))
            continue
        sicherung = datei.with_name(datei.name + ".bak-" + date.today().strftime("%Y%m%d"))
        if not sicherung.exists():
            shutil.copy2(datei, sicherung)
        datei.write_bytes(roh)
        geaendert.append((datei.name, ", ".join(aenderungen)))

    for name, was in geaendert:
        print("%-46s %s" % (name, was))
    if unveraendert:
        print("\nUnveraendert (%d): %s" % (len(unveraendert), ", ".join(unveraendert[:8])
                                           + (" …" if len(unveraendert) > 8 else "")))
    if fehler:
        print("\nFehler:")
        for name, was in fehler:
            print("  %-46s %s" % (name, was))
    print("\n%d Datei(en) %s." % (len(geaendert),
                                  "zu aendern (Trockenlauf)" if not args.anwenden
                                  else "geschrieben"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
