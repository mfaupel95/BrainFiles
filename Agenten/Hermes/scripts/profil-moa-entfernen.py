#!/usr/bin/env python
"""Den `moa:`-Block aus allen BOT-PROFILEN entfernen - nur das Hauptprofil
(= Profil `default`, `Agenten/Hermes/config.yaml`) behaelt seine MoA-Presets.

Anlass (02.10.2026, Auftrag Max "delete moa aus allen bot profilen. nur default
moa an"): 17 der 23 Profile unter `Agenten/Hermes/profiles/<bot>/` trugen einen
kopierten `moa:`-Block (58-132 Zeilen, 2-4 Presets). Ein Bot hat keinen
Aggregator, der seine Presets auswaehlt - der Block ist Ballast und macht die
Profil-Config unlesbar. Das Hauptprofil ist NICHT betroffen: dort wird MoA
tatsaechlich benutzt (Slash-Befehl, Preset-Wahl).

REGEL: entfernt wird NUR der Block `moa:` bis zur naechsten Zeile ohne
Einrueckung. Nichts wird neu formatiert, keine andere Zeile angefasst, keine
Kanalzugangsdaten, kein `models:`-Block. Das Hauptprofil wird nie angefasst.

    python profil-moa-entfernen.py                  # Trockenlauf (Standard)
    python profil-moa-entfernen.py --anwenden       # schreiben (je Datei .bak)
    python profil-moa-entfernen.py --zuruecknehmen  # Sicherungen zurueckholen

Bytes lesen, Bytes schreiben - die Zeilenenden (CRLF) der Profil-Configs
bleiben unveraendert. Vor dem Schreiben prueft `yaml.safe_load` die neue Datei,
und eine Gegenprobe vergleicht die Liste der Top-Level-Schluessel vorher/nachher
(kein Schluessel darf dazu- oder wegfallen). Zuletzt wird gemeldet, wie viele
Modelleintraege in `models:` nur wegen `moa` noch stehen -
`profil-modelllisten-kuerzen.py` raeumt die bei Bedarf nach.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

HIER = Path(__file__).resolve().parent          # Agenten/Hermes/scripts
HERMES = HIER.parent                            # Agenten/Hermes
PROFILE = HERMES / "profiles"
HAUPT = HERMES / "config.yaml"                  # Profil `default` - bleibt


def _block_zeilen(zeilen: list[str]) -> tuple[int, int] | None:
    """(start, ende_exklusiv) des `moa:`-Blocks, oder None wenn keiner da ist.

    Nur ein `moa:` in SPALTE 1 zaehlt - ein eingeruecktes `moa:` gehoert zu
    einem anderen Abschnitt (z. B. unter `providers.<p>.`) und bleibt stehen.
    """
    start = None
    for i, z in enumerate(zeilen):
        if z.rstrip() == "moa:" and not z.startswith(" "):
            start = i
            break
    if start is None:
        return None
    j = start + 1
    while j < len(zeilen):
        z = zeilen[j]
        if z.strip() == "":
            j += 1
            continue
        if not z.startswith(" "):
            break
        j += 1
    return start, j


def _gepresets(text: str) -> list[str]:
    """Namen der Presets im Block (Einrueckung 4 unter `moa:` -> `presets:`)."""
    daten = yaml.safe_load(text) or {}
    moa = daten.get("moa") or {}
    presets = (moa.get("presets") or {}) if isinstance(moa, dict) else {}
    return sorted(presets) if isinstance(presets, dict) else []


def _models_zeilen(text: str) -> int:
    """Modelleintraege in ALLEN `models:`-Bloecken (auch `providers.<p>.models:`,
    die um zwei Ebenen eingerueckt sind)."""
    zeilen = text.split("\r\n" if "\r\n" in text else "\n")
    n = 0
    i = 0
    while i < len(zeilen):
        z = zeilen[i]
        if z.strip() == "models:" and z.endswith("models:"):
            basis = len(z) - len(z.lstrip(" "))
            j = i + 1
            while j < len(zeilen):
                w = zeilen[j]
                if w.strip() == "":
                    j += 1
                    continue
                if len(w) - len(w.lstrip(" ")) <= basis:
                    break
                n += 1
                j += 1
            i = j
            continue
        i += 1
    return n


def bearbeite(pfad: Path, anwenden: bool) -> dict:
    roh = pfad.read_bytes()
    text = roh.decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    zeilen = text.split(nl)
    spanne = _block_zeilen(zeilen)
    if spanne is None:
        return {"stand": "kein moa-Block"}
    start, ende = spanne
    presets = _gepresets(text)

    # Ein Leer-BLOCK direkt ueber dem `moa:`-Anfang gehoert mit zum Block.
    von = start
    while von > 0 and zeilen[von - 1].strip() == "":
        von -= 1
    neue_zeilen = zeilen[:von] + zeilen[ende:]
    neu = nl.join(neue_zeilen)

    alt = yaml.safe_load(text) or {}
    pruef = yaml.safe_load(neu) or {}
    # ERWARTUNG: genau `moa` faellt weg, jeder andere Top-Level-Schluessel bleibt.
    erwartet = sorted(k for k in alt if k != "moa")
    neu_keys = sorted(pruef)
    if erwartet != neu_keys:
        return {"stand": "Gegenprobe fehlgeschlagen (Top-Level-Schluessel: weg %s, dazu %s)"
                           % (sorted(set(erwartet) - set(neu_keys)), sorted(set(neu_keys) - set(erwartet)))}
    if "moa" in pruef:
        return {"stand": "Gegenprobe fehlgeschlagen (moa noch da)"}
    # HARTE Gegenprobe: jeder andere Top-Level-Abschnitt muss IDENTISCH
    # geblieben sein (YAML-Vergleich, nicht Zeilengleichheit) - damit faellt
    # jeder Fehler auf, der ausserhalb des `moa:`-Blocks passiert.
    for k in erwartet:
        if alt.get(k) != pruef.get(k):
            return {"stand": "Gegenprobe fehlgeschlagen (Abschnitt %s veraendert)" % k}
    if neu.count("\r\r") or (neu.count("\n") - neu.count("\r\n")) > 0:
        return {"stand": "Zeilenenden kaputt - nicht geschrieben"}
    if neu.encode("utf-8") == roh:
        return {"stand": "unveraendert"}

    erg = {
        "stand": "Trockenlauf",
        "zeilen_entfernt": ende - von,
        "presets": presets,
        "models_vorher": _models_zeilen(text),
        "models_nachher": _models_zeilen(neu),
    }
    if not anwenden:
        return erg

    sicherung = pfad.with_name(pfad.name + ".bak-" + datetime.now().strftime("%Y%m%d%H%M"))
    shutil.copy2(pfad, sicherung)
    pfad.write_bytes(neu.encode("utf-8"))
    erg["stand"] = "entfernt"
    erg["sicherung"] = sicherung.name
    return erg


def _zuruecknehmen(anwenden: bool) -> int:
    """Nur die NEUESTE Sicherung je Profil - die aelteren stammen aus anderen
    Laeufen (z. B. `profil-modelllisten-kuerzen.py`) und wuerden sonst den
    Stand von vor dem Listen-Kuerzen zurueckbringen."""
    neueste: dict[str, Path] = {}
    for bak in sorted(PROFILE.glob("*/config.yaml.bak-*")):
        neueste[bak.parent.name] = bak          # sortiert -> letzter gewinnt
    if not neueste:
        print("keine Sicherungen gefunden")
        return 0
    for name in sorted(neueste):
        bak = neueste[name]
        ziel = bak.with_name("config.yaml")
        print("%-28s <- %s" % (name, bak.name))
        if anwenden:
            shutil.copy2(bak, ziel)
    if not anwenden:
        print("Trockenlauf - nichts zurueckgeholt")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="moa-Block aus den Bot-Profilen entfernen")
    p.add_argument("--anwenden", action="store_true", help="schreiben (Standard: Trockenlauf)")
    p.add_argument("--zuruecknehmen", action="store_true", help="Sicherungen zurueckholen")
    a = p.parse_args()
    if a.zuruecknehmen:
        return _zuruecknehmen(a.anwenden)

    print("Hauptprofil (bleibt unangetastet): %s  moa: %s"
          % (HAUPT.name, "ja" if "moa:" in HAUPT.read_text(encoding="utf-8") else "nein"))
    zeilen_gesamt = 0
    modelleisten = 0
    for pfad in sorted(PROFILE.glob("*/config.yaml")):
        try:
            e = bearbeite(pfad, a.anwenden)
        except Exception as fehler:  # noqa: BLE001
            print("%-26s FEHLER: %s" % (pfad.parent.name, fehler))
            return 1
        if e["stand"] in ("kein moa-Block",):
            continue
        if e["stand"] not in ("entfernt", "Trockenlauf"):
            print("%-26s %s" % (pfad.parent.name, e["stand"]))
            continue
        zeilen_gesamt += e["zeilen_entfernt"]
        modelleisten += e["models_vorher"] - e["models_nachher"]
        print("%-26s -%3d Zeilen  presets=%-28s models: %d -> %d  (%s)"
              % (pfad.parent.name, e["zeilen_entfernt"], ",".join(e["presets"]),
                 e["models_vorher"], e["models_nachher"], e["stand"]))
    print("Summe entfernte Zeilen: %d | Modelleintraege, die nur wegen moa stehen: %d"
          % (zeilen_gesamt, modelleisten))
    if not a.anwenden:
        print("Trockenlauf - nichts geschrieben")
    return 0


if __name__ == "__main__":
    sys.exit(main())
