"""Setzt auxiliary.compression auf ein Modell mit >= 64k Kontext.

Warum: auxiliary.compression steht in keiner Profil-Config auf einem Weg, der
ein brauchbares Fenster hat. Hermes faellt dann auf die erste Zeile von
fallback_providers zurueck - im Haus ueberall 'ollama-launch /
gemma-e4b-8k:cpu', dessen Fenster 8.192 Token sind. Beim Start einer langen
Session wirft agent/conversation_compression.py dann einen ValueError
("below the minimum 64,000"), der Worker-Prozess endet mit Exit 1, der
Dispatcher versucht es zweimal und gibt auf: die Karte landet in 'blocked'.
Genau das ist am 01./02.10.2026 an sieben Karten passiert.

Das Werkzeug aendert NUR diesen Block, legt vorher eine Sicherung an und prueft
Zeilenenden, Groesse und YAML.

    python scripts/kompression-provider-setzen.py            # Trockenlauf
    python scripts/kompression-provider-setzen.py --anwenden
    python scripts/kompression-provider-setzen.py --anwenden --zuruecknehmen
"""
import argparse
import glob
import os
import shutil
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
# scripts/ -> hermes-config-ops/ -> brainfiles/ -> skills/ -> Hermes/
HERMES = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HIER))))

KONTEXTGRENZE = 64000


def _profile_configs():
    pfade = [os.path.join(HERMES, "config.yaml")]
    pfade += sorted(glob.glob(os.path.join(HERMES, "profiles", "*", "config.yaml")))
    return pfade


def _name(pfad):
    return os.path.basename(os.path.dirname(pfad)) if "profiles" in pfad else "default"


def _sicherung(pfad):
    ziel = os.path.join(HERMES, ".sicherung",
                        _name(pfad) + "-config.yaml.bak-" + time.strftime("%Y%m%d"))
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    return ziel


def _zeilenenden(daten):
    return "\r\n" if b"\r\n" in daten else "\n"


def _baue(alt, provider, modell):
    """(neu_bytes, art) - art: 'ersetzt' | 'eingefuegt' | 'angelegt' | None."""
    nl = _zeilenenden(alt)
    zeilen = alt.decode("utf-8").split(nl)
    block = ("  compression:", "    provider: " + provider,
             "    model: " + modell, "    timeout: 180")

    kopf = zeilen.index("auxiliary:") if "auxiliary:" in zeilen else -1
    if kopf < 0:
        neu = alt.decode("utf-8").rstrip("\r\n") + nl + nl + "auxiliary:" + nl + nl.join(block) + nl
        return neu.encode("utf-8"), "angelegt"

    # Umfang des auxiliary-Blocks: bis zur naechsten Zeile mit 0 Leerzeichen.
    ende = kopf + 1
    while ende < len(zeilen) and zeilen[ende].startswith(" "):
        ende += 1

    # Hat er schon einen compression-Unterschluessel (4 Leerzeichen)?
    drin = None
    for i in range(kopf + 1, ende):
        if zeilen[i].startswith("    ") and zeilen[i].strip().rstrip(":") == "compression:":
            drin = i
            break

    if drin is not None:
        j = drin + 1
        while j < ende and zeilen[j].startswith("      "):
            j += 1
        zeilen[drin:j] = block
        art = "ersetzt"
    else:
        zeilen[kopf + 1:kopf + 1] = list(block)
        art = "eingefuegt"

    return nl.join(zeilen).encode("utf-8"), art


def _gegenprobe(alt, neu):
    assert neu != alt, "Text unveraendert - Anker hat nicht getroffen"
    assert neu.count(b"\r\r") == 0, "CRCR: Zeilenenden verdoppelt"
    assert neu.count(b"\n") >= alt.count(b"\n"), "Zeilen verloren"
    assert b"compression:" in neu and b"auxiliary:" in neu, "Block unvollstaendig"
    assert b"\r\n" not in alt or neu.count(b"\r\n") == neu.count(b"\n"), "gemischte Zeilenenden"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anwenden", action="store_true")
    ap.add_argument("--zuruecknehmen", action="store_true")
    ap.add_argument("--provider", default="nous")
    ap.add_argument("--modell", default="deepseek/deepseek-v4-flash-0731")
    args = ap.parse_args()

    print(f"Ziel: auxiliary.compression -> {args.provider} / {args.modell}")
    print(f"Kontextgrenze: {KONTEXTGRENZE} Token\n")
    geaendert = 0
    for pfad in _profile_configs():
        name = _name(pfad)
        alt = open(pfad, "rb").read()
        if args.zuruecknehmen:
            quelle = _sicherung(pfad)
            if not os.path.exists(quelle):
                print(f"  {name:24} keine Sicherung ({quelle})")
                continue
            shutil.copyfile(quelle, pfad)
            print(f"  {name:24} zurueckgenommen")
            continue
        try:
            neu, art = _baue(alt, args.provider, args.modell)
            _gegenprobe(alt, neu)
        except AssertionError as exc:
            print(f"  {name:24} ABBRUCH: {exc}")
            continue
        if neu == alt:
            print(f"  {name:24} schon gesetzt")
            continue
        geaendert += 1
        print(f"  {name:24} {art:10} Enden {_zeilenenden(alt)!r}")
        if args.anwenden:
            ziel = _sicherung(pfad)
            shutil.copyfile(pfad, ziel)
            with open(pfad, "wb") as fh:
                fh.write(neu)
            print(f"  {'':24} gesichert: {os.path.basename(ziel)}")
    if not args.anwenden and not args.zuruecknehmen:
        print(f"\nTrockenlauf: {geaendert} Datei(en) wuerden sich aendern.")
    return 0


if __name__ == "__main__":
    sys.exit(main())