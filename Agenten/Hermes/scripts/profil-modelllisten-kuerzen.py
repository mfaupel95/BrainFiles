#!/usr/bin/env python
"""Die `models:`-Listen in den BOT-PROFILEN auf das zusammenstreichen, was das Profil benutzt.

Anlass (01.10.2026, Auftrag Max „die botprofile brauchen noch weniger"): 19 der
22 Profile unter `Agenten/Hermes/profiles/<bot>/` trugen je ~1.739
Modelleintraege - die omniroute-`auto/*`-Liste, die aus dem Hauptprofil
mitkopiert wurde. Zusammen 33.030 Eintraege fuer Bots, die ihr Modell aus
`model.default` und `fallback_providers` beziehen und nie einen Waehler
aufklappen.

REGEL: Behalten wird nur, was das Profil SELBST nennt - jedes Modell, das in
`model.default`, `providers.<p>.model`/`default_model`, `fallback_providers`,
`delegation.model` oder `moa` steht. Alles andere faellt aus der Liste. Bleibt
nichts uebrig, verschwindet der ganze `models:`-Block; `discover_models: true`
bleibt stehen, denn der Waehler dieses Profils holt die echte Liste ohnehin
live vom Endpunkt (`_discover_endpoint_models`: ein gesetzter Schluessel
ersetzt den `models:`-Ausschnitt).

    python profil-modelllisten-kuerzen.py                 # Trockenlauf (Standard)
    python profil-modelllisten-kuerzen.py --anwenden      # schreiben (je Datei .bak)
    python profil-modelllisten-kuerzen.py --zuruecknehmen # Sicherungen zurueckholen

Bytes lesen, Bytes schreiben - Zeilenenden (CRLF) bleiben, jede geaenderte
Datei wird mit `yaml.safe_load` geprueft, und danach wird gemessen, dass jedes
referenzierte Modell noch in seiner Liste steht.

Nicht angefasst: das Hauptprofil (`Agenten/Hermes/config.yaml`) und die
Kanalzugangsdaten. Der `models:`-Block eines Profils ist eine ANZEIGELISTE -
wer hier kuerzt, nimmt keinem Bot sein Modell weg.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent          # Agenten/Hermes/scripts
HERMES = HIER.parent                            # Agenten/Hermes
PROFILE = HERMES / "profiles"
REF_SCHLUESSEL = ("model", "default", "default_model")


def _referenzen(daten: dict) -> set[str]:
    """Alle Modellnamen, die dieses Profil selbst nennt (ohne die `models:`-Listen)."""
    out: set[str] = set()

    def lauf(node: object, schluessel: str | None = None) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "models":
                    continue
                lauf(v, k)
        elif isinstance(node, list):
            for v in node:
                lauf(v, schluessel)
        elif isinstance(node, str) and schluessel in REF_SCHLUESSEL:
            if node.strip():
                out.add(node.strip())

    lauf(daten)
    return out


def _block_umfang(zeilen: list[str], i: int) -> tuple[int, int, str]:
    """`models:`-Block ab Zeile i: (ende_exklusiv, einzug_der_eintraege, form)."""
    kopf = zeilen[i]
    einzug = len(kopf) - len(kopf.lstrip(" "))
    j = i + 1
    eintraege: list[str] = []
    while j < len(zeilen):
        z = zeilen[j]
        if z.strip() == "":
            j += 1
            continue
        einzug_z = len(z) - len(z.lstrip(" "))
        # Listenform erlaubt die Eintraege AUF der Hoehe des Schluessels ("- x"), daher
        # beendet erst eine Zeile mit GERINGEREM Einzug oder eine gleich eingerueckte,
        # die kein Listenpunkt ist.
        if einzug_z < einzug or (einzug_z == einzug and not z.lstrip().startswith("- ")):
            break
        eintraege.append(z)
        j += 1
    if not eintraege:
        return i + 1, einzug, "leer"
    form = "liste" if eintraege[0].lstrip().startswith("- ") else "dict"
    return j, einzug, form


def _name_aus_zeile(z: str, form: str) -> str:
    s = z.strip()
    if form == "liste":
        s = s[2:].strip()
    else:
        # Dict-Form "schluessel: wert" - der SCHLUESSEL kann selbst Doppelpunkte tragen
        # (`auto/coding:free: {}`), deshalb am LETZTEN Doppelpunkt trennen.
        s = s.rpartition(":")[0].strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
    return s


def _kuerzen(pfad: Path, anwenden: bool) -> dict:
    roh = pfad.read_bytes()
    text = roh.decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    import yaml  # noqa: PLC0415

    daten = yaml.safe_load(text) or {}
    refs = _referenzen(daten)

    zeilen = text.split(nl)
    behalten: set[str] = set()
    i = 0
    vorher = nachher = 0
    ausgabe: list[str] = []
    geaendert = False
    while i < len(zeilen):
        if re.match(r"^\s+models:\s*$", zeilen[i]):
            ende, _, form = _block_umfang(zeilen, i)
            block = zeilen[i + 1:ende]
            if form == "leer":
                ausgabe.extend(zeilen[i:ende])
                i = ende
                continue
            vorher += len(block)
            treffer = [z for z in block if _name_aus_zeile(z, form) in refs]
            behalten |= {_name_aus_zeile(z, form) for z in treffer}
            if treffer:
                ausgabe.append(zeilen[i])
                ausgabe.extend(treffer)
                nachher += len(treffer)
            if len(treffer) != len(block):
                geaendert = True
            i = ende
            continue
        ausgabe.append(zeilen[i])
        i += 1

    ergebnis = {"vorher": vorher, "nachher": nachher, "refs": refs, "behalten": behalten}
    if not geaendert:
        ergebnis["stand"] = "nichts zu kuerzen"
        return ergebnis

    neu = nl.join(ausgabe)
    pruef = yaml.safe_load(neu) or {}
    alt_prov = daten.get("providers") or {}
    neu_prov = pruef.get("providers") or {}
    for name, blk in neu_prov.items():
        if not (isinstance(blk, dict) and blk.get("models") is not None):
            continue
        drin = set(blk["models"] if isinstance(blk["models"], list) else blk["models"])
        vorher_liste = (alt_prov.get(name) or {}).get("models")
        vorher_set = set(vorher_liste if isinstance(vorher_liste, list) else (vorher_liste or {}))
        fehlend = (refs & vorher_set) - drin
        if fehlend:
            ergebnis["stand"] = "Gegenprobe fehlgeschlagen (%s fehlt in %s)" % (sorted(fehlend), name)
            return ergebnis
    if (pruef.get("model") or {}).get("default") != (daten.get("model") or {}).get("default"):
        ergebnis["stand"] = "Gegenprobe fehlgeschlagen (model.default veraendert)"
        return ergebnis
    if neu.count("\r\r") or (neu.count("\n") - neu.count("\r\n")) > 0:
        ergebnis["stand"] = "Zeilenenden kaputt - nicht geschrieben"
        return ergebnis

    if not anwenden:
        ergebnis["stand"] = "Trockenlauf"
        return ergebnis
    sicherung = pfad.with_name(pfad.name + ".bak-" + datetime.now().strftime("%Y%m%d%H%M"))
    shutil.copy2(pfad, sicherung)
    pfad.write_bytes(neu.encode("utf-8"))
    ergebnis["stand"] = "gekuerzt"
    ergebnis["sicherung"] = sicherung.name
    return ergebnis


def _zuruecknehmen(anwenden: bool) -> int:
    treffer = sorted(PROFILE.glob("*/config.yaml.bak-*"))
    if not treffer:
        print("keine Sicherungen gefunden")
        return 0
    for bak in treffer:
        ziel = bak.with_name("config.yaml")
        print("%-28s <- %s" % (ziel.parent.name, bak.name))
        if anwenden:
            shutil.copy2(bak, ziel)
    if not anwenden:
        print("Trockenlauf - nichts zurueckgeholt")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="models:-Listen der Bot-Profile kuerzen")
    p.add_argument("--anwenden", action="store_true")
    p.add_argument("--zuruecknehmen", action="store_true")
    a = p.parse_args()
    if a.zuruecknehmen:
        return _zuruecknehmen(a.anwenden)

    gesamt_v = gesamt_n = 0
    for pfad in sorted(PROFILE.glob("*/config.yaml")):
        try:
            e = _kuerzen(pfad, a.anwenden)
        except Exception as fehler:
            print("%-26s FEHLER: %s" % (pfad.parent.name, fehler))
            continue
        if e["vorher"] or e["stand"] != "nichts zu kuerzen":
            print("%-26s %4d -> %4d  (%s)" % (pfad.parent.name, e["vorher"], e["nachher"], e["stand"]))
        gesamt_v += e["vorher"]
        gesamt_n += e["nachher"]
    print("Summe Modelleintraege: %d -> %d" % (gesamt_v, gesamt_n))
    if not a.anwenden:
        print("Trockenlauf - nichts geschrieben")
    return 0


if __name__ == "__main__":
    sys.exit(main())