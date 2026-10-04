#!/usr/bin/env python
"""Die VOLLE Nous-Modellliste in den Modellwaehler eintragen (`providers: nous: models:`).

Anlass (01.10.2026): Der Waehler zeigte fuer den Anbieter nous nur die
kuratierte Liste - 50 Eintraege aus dem Manifest plus die Empfehlungen des
Portals, also 58. Das Portal liefert ueber `/v1/models` aber **428** Modelle.
Hermes tut das absichtlich: `model_switch_providers._nous_picker_model_ids`
sagt "the picker shows ONLY the curated agentic list". Die von Hermes
vorgesehene Stelle zum Erweitern ist der Config-Block

    providers:
      nous:
        models:
          "<modell>": {}

`_lap_overlay_rows` haengt ihn der Waehler-Zeile VORAN ("A
providers.<overlay>.models block extends the row"); die Zeile bleibt
`source: hermes` und behaelt ihre Anmeldung.

Das Werkzeug holt die Liste LIVE vom Portal (mit dem hinterlegten Schluessel)
und schreibt sie in die Hauptconfig. Ohne Argument ist es ein TROCKENLAUF.

    python nous-modellliste-richten.py                 # zeigen, nichts schreiben
    python nous-modellliste-richten.py --anwenden      # schreiben (Sicherung .bak)
    python nous-modellliste-richten.py --zuruecknehmen # Block wieder entfernen
    python nous-modellliste-richten.py --profile       # zusaetzlich alle Profile

Bytes lesen, Bytes schreiben - Zeilenenden (CRLF) bleiben erhalten. Vor dem
Schreiben wird die neue Fassung mit yaml.safe_load geprueft.

MERKSATZ: Der Block ist eine ANZEIGELISTE, keine Freigabe - er aendert weder
das aktive Modell noch die Anmeldung. Und: die Desktop-/Gateway-App schreibt
die Config aus ihrem eigenen Speicher zurueck; nach einer Einstellungsaenderung
in der App pruefen, ob der Block noch da ist.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent          # Agenten/Hermes/scripts
HERMES = HIER.parent                            # Agenten/Hermes
sys.path.insert(0, str(HERMES / "hermes-agent"))

ANFANG = b"providers:\r\n"
KENNUNG = b"  nous:\r\n    models:\r\n"
NEUZEILE = bytes([10])


def _modelle_holen() -> list[str]:
    """Rohe Nous-Liste des Portals (ohne Chat-Filter), Reihenfolge wie geliefert."""
    from hermes_cli.models import _load_provider_models_cache, provider_model_ids

    frisch = provider_model_ids("nous", force_refresh=True)
    roh: list[str] = []
    try:
        for key, eintrag in (_load_provider_models_cache() or {}).items():
            if str(key).strip().lower().startswith("nous"):
                roh = [m for m in (eintrag or {}).get("models", []) if isinstance(m, str)]
    except Exception as fehler:  # pragma: no cover
        print("rohe Liste nicht lesbar (%s) - nehme die gefilterte" % fehler)
    return list(dict.fromkeys(roh or frisch))


def _block(models: list[str]) -> bytes:
    zeilen = [KENNUNG.decode("ascii").rstrip("\r\n")]
    for mid in models:
        zeilen.append(f'      "{mid}": {{}}' if ": " in mid else f"      {mid}: {{}}")
    return ("\r\n".join(zeilen) + "\r\n").encode("utf-8")


def _dateien(mit_profilen: bool) -> list[Path]:
    dateien = [HERMES / "config.yaml"]
    if mit_profilen:
        dateien += sorted((HERMES / "profiles").glob("*/config.yaml"))
    return [p for p in dateien if p.is_file()]


def _sicherung(pfad: Path) -> Path:
    ziel = pfad.with_name(pfad.name + ".bak-" + datetime.now().strftime("%Y%m%d%H%M"))
    shutil.copy2(pfad, ziel)
    return ziel


def _eintragen(pfad: Path, models: list[str], anwenden: bool) -> str:
    roh = pfad.read_bytes()
    if KENNUNG in roh:
        return "schon eingetragen"
    if ANFANG not in roh:
        return "kein 'providers:'-Anker - uebersprungen"
    neu = roh.replace(ANFANG, ANFANG + _block(models), 1)
    import yaml  # noqa: PLC0415

    daten = yaml.safe_load(neu.decode("utf-8"))
    drin = daten["providers"]["nous"]["models"]
    if len(drin) != len(models) or daten["model"]["provider"] != "nous":
        return "Gegenprobe fehlgeschlagen - NICHT geschrieben"
    if not anwenden:
        return "Trockenlauf: %d Modelle, %d -> %d Zeilen" % (
            len(drin), roh.count(NEUZEILE), neu.count(NEUZEILE))
    sicherung = _sicherung(pfad)
    pfad.write_bytes(neu)
    return "%d Modelle eingetragen (Sicherung %s)" % (len(drin), sicherung.name)


def _zuruecknehmen(pfad: Path, anwenden: bool) -> str:
    roh = pfad.read_bytes()
    if KENNUNG not in roh:
        return "kein nous-Block"
    kopf, rest = roh.split(KENNUNG, 1)
    # Blockende = naechste Zeile mit GENAU zwei Leerzeichen Einrueckung ("\r\n  X", X kein Space).
    # Ein split auf "\r\n  " traefe schon die erste Modellzeile (die hat sechs Leerzeichen).
    treffer = re.search(rb"\r\n  (?=[^ ])", rest)
    if treffer is None:
        return "Blockende nicht gefunden - nicht angefasst"
    neu = kopf + rest[treffer.start() + 2:]
    if not anwenden:
        return "Trockenlauf: Block wuerde entfernt"
    sicherung = _sicherung(pfad)
    pfad.write_bytes(neu)
    return "Block entfernt (Sicherung %s)" % sicherung.name


def main() -> int:
    p = argparse.ArgumentParser(description="Nous-Modellliste in die Config eintragen")
    p.add_argument("--anwenden", action="store_true", help="wirklich schreiben")
    p.add_argument("--zuruecknehmen", action="store_true", help="Block wieder entfernen")
    p.add_argument("--profile", action="store_true", help="auch alle Profile")
    p.add_argument("--json", action="store_true", help="Liste als JSON ausgeben")
    p.add_argument("--pfad", action="append", default=None,
                   help="nur diese Datei(en); wiederholbar. Ohne: die "
                        "Hauptconfig (plus --profile: alle Profil-Configs)")
    a = p.parse_args()

    # `--zuruecknehmen` braucht die Liste NICHT: es loescht einen Block, dessen
    # Inhalt es nicht kennen muss. Vorher wurde auch da zuerst das Portal
    # befragt - und genau dort brach der Lauf ab, weil hermes_cli.models in
    # dieser Umgebung `ruamel` nicht findet (gemessen 04.10.2026: der Weg
    # `--zuruecknehmen` war damit unbenutzbar, obwohl genau er ohne Portal
    # auskommt). Jetzt: nur fuer das Eintragen wird das Portal befragt.
    models: list[str] = []
    if not a.zuruecknehmen:
        models = _modelle_holen()
        if a.json:
            print(json.dumps({"anzahl": len(models), "models": models}, ensure_ascii=False))
            return 0
        if not models:
            print("Portal liefert eine leere Liste - abgebrochen")
            return 1
        print("Portal liefert %d Modelle (erste: %s)" % (len(models), models[0]))
    elif a.json:
        print(json.dumps({"anzahl": 0, "models": [],
                          "hinweis": "--zuruecknehmen braucht keine Portalliste"},
                         ensure_ascii=False))
        return 0
    else:
        print("Block entfernen - das Portal wird dafuer nicht befragt")

    for pfad in (_dateien(a.profile) if not a.pfad
                 else [Path(q) for q in a.pfad]):
        try:
            kurz = str(pfad.relative_to(HERMES.parent.parent))
        except ValueError:
            kurz = str(pfad)
        try:
            if a.zuruecknehmen:
                ergebnis = _zuruecknehmen(pfad, a.anwenden)
            else:
                ergebnis = _eintragen(pfad, models, a.anwenden)
        except Exception as fehler:
            ergebnis = "FEHLER: %s" % fehler
        print("%s: %s" % (kurz, ergebnis))
    return 0


if __name__ == "__main__":
    sys.exit(main())