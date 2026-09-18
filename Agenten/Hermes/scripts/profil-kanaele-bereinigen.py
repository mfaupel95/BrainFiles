#!/usr/bin/env python3
"""Kanal-Zugangsdaten aus Bot-Profilen entfernen - "alles auf default".

Ein Telegram-/Photon-Token gehoert genau EINEM Profil: derselbe Bot kann nicht
gleichzeitig default und einem Repo-Bot gehoeren. `hermes profile list` warnt
darum je Profil, und `hermes gateway migrate --multiplex` verweigert, solange
die Dopplung steht.

Die Repo-Bots BRAUCHEN die Zugangsdaten nicht: der SkillsBot reicht Fragen per
`hermes -p <name> chat -q` durch (Agenten/Bus/skillsbot.py) - ohne Gateway,
ohne Telegram. Die Bots sind damit weiter erreichbar, nur eben ueber den einen
Bot von `default`.

Aufruf (aus Agenten/Hermes/hermes-agent mit dessen venv, weil hermes_cli
importiert wird):

  venv/Scripts/python.exe ../scripts/profil-kanaele-bereinigen.py            # nur zeigen
  venv/Scripts/python.exe ../scripts/profil-kanaele-bereinigen.py --anwenden # schreiben

Beim Schreiben: je Profil erst `.env.bak-JJJJMMTT` (nur wenn noch nicht da),
dann die Kanalzeilen strichen. Zeilenenden bleiben, wie sie sind (CRLF bleibt
CRLF) - geschrieben wird Byte fuer Byte dieselbe Datei ohne die gestrichenen
Zeilen.

Welche Zeile ein Kanal ist, entscheidet NICHT dieses Skript, sondern Hermes
selbst: `hermes_cli.profile_channels.ChannelKeyIndex` - dieselbe Zuordnung, mit
der `hermes profile create --clone` die Kanaele aus einer Kopie entfernt. Die
Quelle des Vergleichs ist das Profil `default` (sein Plugin-Geltungsbereich).

Gestrichen werden standardmaessig nur `telegram` und `photon` - die beiden
Kanaele aus der Warnung. Andere geteilte Kanalzeilen (z.B. A2A_*) werden
gemeldet, aber nicht angefasst; sie sind eine eigene Entscheidung.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

# Haus-Standard: der Kanal ist der, den Hermes selbst als Kanal ansieht.
STANDARD_KANAELE = ("telegram", "photon")

_ENV_ZEILE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


def schluessel_der_zeile(zeile: str):
    """Der Variablenname einer .env-Zeile oder None (Kommentar, Leerzeile)."""
    treffer = _ENV_ZEILE.match(zeile)
    return treffer.group(1) if treffer else None


def zerlege(text: str):
    """Zeilen MIT ihren Enden - so bleibt CRLF beim Zusammensetzen erhalten."""
    return text.splitlines(keepends=True)


def striechen(env_pfad: Path, kanaele, index, anwenden: bool):
    """Kanaleilen aus einer .env entfernen.

    Rueckgabe: (gestrichene_zeilen, {kanal: [schluessel]}, treffer_anderer).
    """
    roh = env_pfad.read_bytes()
    bom = roh.startswith(b"\xef\xbb\xbf")
    text = roh.decode("utf-8-sig")
    behalten, gestrichen, andere = [], {}, {}
    for zeile in zerlege(text):
        schluessel = schluessel_der_zeile(zeile)
        plattform = index.platform_for(schluessel) if schluessel else None
        if plattform in kanaele:
            gestrichen.setdefault(plattform, []).append(schluessel)
            continue
        if plattform and plattform != "gateway":
            andere.setdefault(plattform, []).append(schluessel)
        behalten.append(zeile)
    if gestrichen and anwenden:
        sicherung = env_pfad.with_name(
            env_pfad.name + ".bak-" + date.today().strftime("%Y%m%d"))
        if not sicherung.exists():
            shutil.copy2(env_pfad, sicherung)
        neu = "".join(behalten).encode("utf-8")
        env_pfad.write_bytes((b"\xef\xbb\xbf" if bom else b"") + neu)
    return behalten, gestrichen, andere


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anwenden", action="store_true",
                    help="schreiben (ohne: nur zeigen)")
    ap.add_argument("--zuruecknehmen", action="store_true",
                    help="Sicherung .env.bak-JJJJMMTT zurueck auf .env legen")
    ap.add_argument("--plattformen", default=",".join(STANDARD_KANAELE),
                    help="zu streichende Kanaele (Standard: %s)"
                         % ",".join(STANDARD_KANAELE))
    args = ap.parse_args()
    kanaele = tuple(p.strip().lower() for p in args.plattformen.split(",") if p.strip())
    if "default" in kanaele:
        print("'default' kann nicht gestrichen werden - dort sollen die "
              "Zugangsdaten ja liegen.")
        return 2
    if args.anwenden and args.zuruecknehmen:
        print("--anwenden und --zuruecknehmen schliessen sich aus.")
        return 2

    hier = Path(__file__).resolve().parent          # Agenten/Hermes/scripts
    hermes = hier.parent                            # Agenten/Hermes
    repo = hermes / "hermes-agent"
    if not (repo / "hermes_cli" / "profile_channels.py").is_file():
        print("hermes-agent nicht gefunden: %s" % repo)
        return 2
    sys.path.insert(0, str(repo))

    from hermes_cli.profile_channels import ChannelKeyIndex  # noqa: E402

    index = ChannelKeyIndex(hermes)                 # Quelle/geltung: default
    profile = sorted(p for p in (hermes / "profiles").iterdir()
                     if p.is_dir() and not p.name.startswith("."))
    if not profile:
        print("Keine Profile unter %s" % (hermes / "profiles"))
        return 1

    if args.zuruecknehmen:
        zurueck = 0
        for p in profile:
            sicherungen = sorted(p.glob(".env.bak-*"))
            if not sicherungen:
                continue
            neueste = sicherungen[-1]            # JJJJMMTT sortiert = neueste
            shutil.copy2(neueste, p / ".env")
            print("%-28s zurueck aus %s" % (p.name, neueste.name))
            zurueck += 1
        print()
        if zurueck:
            print("%d Profil(e) zurueckgenommen." % zurueck)
        else:
            print("Keine Sicherung .env.bak-* gefunden.")
        return 0

    zeilen_summe, profile_mit, andere_summe = 0, 0, {}
    for p in profile:
        env = p / ".env"
        if not env.is_file():
            continue
        behalten, gestrichen, andere = striechen(env, kanaele, index, args.anwenden)
        if andere:
            for kanal, schluessel in andere.items():
                andere_summe.setdefault(kanal, set()).update(schluessel)
        if not gestrichen:
            continue
        profile_mit += 1
        teile = []
        for kanal in sorted(gestrichen):
            schluessel = gestrichen[kanal]
            zeilen_summe += len(schluessel)
            teile.append("%s(%d)" % (kanal, len(schluessel)))
        print("%-28s %s" % (p.name, "  ".join(teile)))
        for kanal in sorted(gestrichen):
            print("%-28s   %s" % ("", ", ".join(gestrichen[kanal])))

    if not profile_mit:
        print("Nichts zu tun - kein Profil traegt diese Kanaele (%s)."
              % ", ".join(kanaele))
    else:
        print()
        print("%d Profil(e), %d Zeile(n) %s."
              % (profile_mit, zeilen_summe,
                 "geschrieben" if args.anwenden else "zu strichen (Trockenlauf)"))
        if args.anwenden:
            print("Sicherungen: <profil>/.env.bak-%s"
                  % date.today().strftime("%Y%m%d"))
        else:
            print("Wirklich schreiben: --anwenden")
    if andere_summe:
        print()
        print("NICHT angefasst (eigene Entscheidung, keine Warnung von Hermes):")
        for kanal in sorted(andere_summe):
            schluessel = sorted(andere_summe[kanal])
            print("  %-14s %d Zeile(n): %s"
                  % (kanal, len(schluessel), ", ".join(schluessel[:8])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
