#!/usr/bin/env python3
"""Ungueltige Rueckfallkette (lokales 8k-Modell) aus Bot-Profilen entfernen.

Befund 18.09.2026: 14 Bot-Profile erbten vom Startprofil eine
`fallback_providers`-Kette, deren letzter Eintrag auf ein lokales Modell mit
8.192 Token Kontext zeigt (`gemma-e4b-8k:latest`, Ollama). Hermes verlangt
mindestens 64.000 Token; faellt die Hauptverbindung aus, laeuft der Aufruf in
genau diese Kette und endet mit

  "Hermes couldn't start the model connection: Model gemma-e4b-8k:latest has a
   context window of 8,192 tokens ..."

statt mit der ehrlichen Meldung, dass der Router nicht antwortet. Der erste
Ketteneintrag zeigt ausserdem auf denselben Router wie das Hauptmodell und
bringt nichts.

Der ganze Block wird deshalb entfernt - nicht per `hermes config set` (das
schneidet den Kommentar-Schluss der Datei ab und kann keine Listeneintraege
einzeln aendern), sondern byte-genau: die Zeile `fallback_providers:` in Spalte 0
plus die eingerueckten Folgezeilen. Vorher/nachher wird die Datei als YAML
geparst; eingerueckte Ketten (z. B. unter `delegation:`) bleiben unberuehrt.

Aufruf (aus Agenten/Hermes):

  python scripts/bot-rueckfallkette-bereinigen.py              # nur zeigen
  python scripts/bot-rueckfallkette-bereinigen.py --anwenden   # schreiben
  python scripts/bot-rueckfallkette-bereinigen.py --zuruecknehmen

Je Profil entsteht vorher `config.yaml.bak-JJJJMMTT` (nur, wenn noch keine
vorhanden ist - die Sicherung des Modellwechsels wird nicht ueberschrieben).
Unberuehrt bleiben Profile, deren Kette kein lokales Kleinmodell nennt
(`awesome-systematic-trading`, `openmontage`), und `default`.
"""

from __future__ import annotations

import argparse
import difflib
import shutil
from datetime import date
from pathlib import Path

import yaml

ZIEL = "fallback_providers:"
KLEINMODELLE = ("gemma-e4b-8k",)          # Kontext < 64k, von Hermes abgelehnt


def kette_entfernen(config: Path):
    """Zeile + eingerueckte Folgezeilen des obersten `fallback_providers:` entfernen.

    Rueckgabe: (Anzahl entfernter Zeilen, entfernter Text). 0 = nichts zu tun.
    """
    roh = config.read_bytes()
    text = roh.decode("utf-8")
    vorher = yaml.safe_load(text)
    if not isinstance(vorher, dict) or not vorher.get(ZIEL[:-1]):
        return 0, ""
    zeilen = text.splitlines(keepends=True)
    for i, zeile in enumerate(zeilen):
        if zeile.rstrip("\r\n") != ZIEL:
            continue
        j = i + 1
        while j < len(zeilen) and zeilen[j][:1].isspace():
            j += 1
        rest = zeilen[:i] + zeilen[j:]
        neu = "".join(rest)
        nachher = yaml.safe_load(neu)
        assert isinstance(nachher, dict), "%s: YAML kaputt nach dem Entfernen" % config
        assert not nachher.get(ZIEL[:-1]), "%s: Kette steht noch" % config
        if "model" in vorher:
            assert nachher.get("model") == vorher["model"], "%s: model-Block veraendert" % config
        assert {k: v for k, v in vorher.items() if k != ZIEL[:-1]} == nachher, \
            "%s: mehr als die Kette entfernt" % config
        config.write_bytes(neu.encode("utf-8"))
        return j - i, "".join(zeilen[i:j])
    return 0, ""


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
    profile = sorted(p for p in (hermes_home / "profiles").iterdir()
                     if p.is_dir() and not p.name.startswith("."))
    if args.zuruecknehmen:
        zurueck = 0
        for p in profile:
            sicherungen = sorted(p.glob("config.yaml.bak-*"))
            if not sicherungen:
                continue
            shutil.copy2(sicherungen[-1], p / "config.yaml")
            print("%-28s zurueck aus %s" % (p.name, sicherungen[-1].name))
            zurueck += 1
        print()
        print("%d Profil(e) zurueckgenommen." % zurueck if zurueck else "Nichts zu tun.")
        return 0

    betroffen, unberuehrt = [], []
    for p in profile:
        config = p / "config.yaml"
        if not config.is_file():
            continue
        text = config.read_text(encoding="utf-8", errors="replace")
        if ("\n" + ZIEL + "\n") not in text.replace("\r\n", "\n"):
            unberuehrt.append((p.name, "keine Rueckfallkette"))
            continue
        klein = [m for m in KLEINMODELLE if m in text]
        if not klein:
            unberuehrt.append((p.name, "Kette ohne lokales Kleinmodell"))
            continue
        betroffen.append((p.name, klein))
    for name, klein in betroffen:
        print("%-28s Kette nennt %s" % (name, ", ".join(klein)))
    for name, grund in unberuehrt:
        print("%-28s unberuehrt: %s" % (name, grund))
    print()
    print("%d Profil(e) %s." % (len(betroffen),
                                "bereinigt" if args.anwenden else "zu bereinigen"))
    if not args.anwenden:
        if betroffen:
            print("Wirklich schreiben: --anwenden")
        return 0

    for p in profile:
        config = p / "config.yaml"
        if not config.is_file() or not any(p.name == n for n, _ in betroffen):
            continue
        sicherung = config.with_name("config.yaml.bak-" + date.today().strftime("%Y%m%d"))
        if not sicherung.exists():
            shutil.copy2(config, sicherung)
        entfert, block = kette_entfernen(config)
        if not entfert:
            continue
        zeilen = [z for z in difflib.unified_diff(
            sicherung.read_text(encoding="utf-8").splitlines(),
            config.read_text(encoding="utf-8").splitlines(), n=0)
            if z.startswith(("+", "-")) and not z.startswith(("+++", "---"))]
        print("%-28s %d Zeile(n) entfernt, Diff %d" % (p.name, entfert, len(zeilen)))
        for z in zeilen:
            print("      " + z[:100])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
