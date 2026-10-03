"""Gestapelte Positionen zusammenfassen (Auftrag Max 03.10.2026).

Wovon: nach dem Bau der Skalierungsregel (Agenten/Handel/skalieren.py) gibt es
neue Signale, die eine bestehende Position vergroessern. Die ALTEN Stapel
blieben aber stehen - supertrend 4 kurze BTC, macd_mtf 4 lange ETH, wavetrend
3 kurze BTC. Sie belegten vier Plaetze fuer dieselbe Richtung.

WAS HIER PASSIERT - und warum es keine erfundene Runde wird:

Fuer jede Gruppe (Instrument + Seite) mit mehr als einer Position:
  * Die groesste bleibt, ihr `pos_id` bleibt.
  * Die uebrigen werden in sie eingerechnet: gewichteter Einstieg, Summe des
    Nominals, Stop und Ziel NEU aus dem gewogenen Einstieg.
  * Jede weggefallene Position bekommt eine `verkauf`-Zeile mit dem Grund
    `buchbereinigung_stapel`. Das ist eine BUCHHALTUNGS-Korrektur
    (`stoerungen.BUCHHALTUNG` enthaelt "buchbereinigung"), damit sie in
    KEINER Kennzahl als Runde erscheint und die Trefferquote unberuehrt
    bleibt. Ihr Erloes ist der neue gewogene Einstieg - der Ausgleich ist
    also exakt null und erfindet weder Gewinn noch Verlust.
  * Die behaltene Position bekommt eine `kauf`-Zeile mit dem KUMULATIVEN
    Nominal und dem gewogenen Einstieg. Die Zuordnung nimmt je pos_id die
    letzte Kaufzeile, das Ergebnis bleibt damit richtig.

VORSCHAU ist der Standard. Erst `--anwenden` schreibt.

    python stapel_raeumen.py                     # alle Spuren, nur ansehen
    python stapel_raeumen.py --anwenden
    python stapel_raeumen.py --spur supertrend --anwenden
"""
import argparse
import csv
import glob
import json
import os
import shutil
import sys
from datetime import datetime

HANDEL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HANDEL)

GRUND = "buchbereinigung_stapel"
VZ = {"long": 1, "short": -1}


def gruppen(positionen):
    """(Instrument, Seite) -> Liste von Positionen, nur mit mehr als einer."""
    aus = {}
    for p in positionen or []:
        if not isinstance(p, dict):
            continue
        schluessel = (p.get("inst"), (p.get("seite") or "long"))
        aus.setdefault(schluessel, []).append(p)
    return {k: v for k, v in aus.items() if len(v) > 1}


def zusammenfassen(gruppe, stop_pct=None, r=None):
    """Die Gruppe auf eine Position rechnen. (neue_position, weg_Liste).

    `stop_pct` und `r` kommen aus der Wachen-Datei; fehlen sie, wird der
    Abstand der groessten Position benutzt, damit nichts erfunden wird.
    """
    behalten = max(gruppe, key=lambda p: float(p.get("nominal") or 0.0))
    weg = [p for p in gruppe if p is not behalten]

    alt_nominal = sum(float(p.get("nominal") or 0.0) for p in gruppe)
    gewicht = sum(float(p.get("einstieg") or 0.0) * float(p.get("nominal") or 0.0)
                  for p in gruppe)
    einstieg = (gewicht / alt_nominal) if alt_nominal > 0 else float(
        behalten.get("einstieg") or 0.0)

    if stop_pct is None:
        b = float(behalten.get("einstieg") or 0.0)
        s = float(behalten.get("stop") or 0.0)
        stop_pct = abs(b - s) / b * 100.0 if b and s else 4.0
    if r is None:
        b = float(behalten.get("einstieg") or 0.0)
        s = float(behalten.get("stop") or 0.0)
        z = float(behalten.get("ziel") or 0.0)
        abstand = abs(b - s)
        r = (abs(z - b) / abstand) if abstand > 0 else 2.0

    vz = VZ.get(behalten.get("seite") or "long", 1)
    abstand = einstieg * (stop_pct / 100.0)
    behalten["einstieg"] = einstieg
    behalten["nominal"] = alt_nominal
    behalten["stop"] = einstieg - vz * abstand
    behalten["ziel"] = einstieg + vz * r * abstand
    behalten["stop_pct"] = stop_pct
    behalten["zusammengefasst"] = int(behalten.get("zusammengefasst") or 0) + len(weg)
    return behalten, weg


def spur_daten(spur):
    ordner = os.path.join(HANDEL, spur)
    zp = os.path.join(ordner, "zustand.json")
    jp = os.path.join(ordner, "handelsjournal.csv")
    if not os.path.isfile(zp):
        return None
    try:
        z = json.load(open(zp, encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        print("  %-14s Zustand unlesbar: %s" % (spur, str(e)[:60]))
        return None
    w = {}
    for name in sorted(glob.glob(os.path.join(ordner, "wachen*.json"))):
        try:
            w = json.load(open(name, encoding="utf-8"))
            break
        except Exception:                                    # noqa: BLE001
            continue
    return ordner, zp, jp, z, w


def zeilen_schreiben(pfad, zeilen):
    """Zeilen anhaengen; die Kopfzeile wird bei Bedarf neu geschrieben."""
    vorhanden = os.path.isfile(pfad)
    if vorhanden:
        with open(pfad, encoding="utf-8", newline="") as fh:
            leser = csv.DictReader(fh)
            felder = leser.fieldnames or []
            raus = list(leser)
        raus.extend(zeilen)
    else:
        felder = ["zeit", "modus", "aktion", "inst", "seite", "preis",
                  "einsatz_usd", "stop", "ziel", "stop_pct", "grund", "pos_id"]
        raus = list(zeilen)
    sicherung = pfad + ".bak-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(pfad, sicherung) if vorhanden else None
    with open(pfad, "w", encoding="utf-8", newline="") as fh:
        schreiber = csv.DictWriter(fh, fieldnames=felder, extrasaction="ignore")
        schreiber.writeheader()
        for z in raus:
            schreiber.writerow(z)


def spur_raeumen(spur, anwenden=False):
    daten = spur_daten(spur)
    if not daten:
        return False
    ordner, zp, jp, z, w = daten
    positionen = z.get("positionen") or []
    staffeln = gruppen(positionen)
    if not staffeln:
        return False

    jetzt = datetime.now().astimezone().isoformat(timespec="seconds")
    stop_pct = w.get("stop_prozent")
    r = w.get("ziel_r_vielfaches")
    print("%-14s %d Positionen, %d Gruppe(n) zu staffeln"
          % (spur, len(positionen), len(staffeln)))

    for (inst, seite), gruppe in sorted(staffeln.items(), key=lambda x: str(x[0])):
        behalten, weg = zusammenfassen(gruppe, stop_pct, r)
        summe = sum(float(p.get("nominal") or 0.0) for p in gruppe)
        print("    %-14s %-6s %d Positionen -> 1   %.2f -> %.2f USD   "
              "Einstieg %.4f  Stop %.4f  Ziel %.4f"
              % (inst, seite, len(gruppe), summe, behalten["nominal"],
                 behalten["einstieg"], behalten["stop"], behalten["ziel"]))
        if not anwenden:
            continue
        # 1. die weggefallenden ausbuchen - Erloes = neuer gewogener Einstieg,
        #    damit der Ausgleich exakt null ist
        neue = []
        for p in weg:
            neue.append({"zeit": jetzt, "modus": "papier", "aktion": "verkauf",
                         "inst": inst, "seite": seite,
                         "preis": "%.6f" % behalten["einstieg"],
                         "einsatz_usd": "%.2f" % float(p.get("nominal") or 0.0),
                         "stop": "", "ziel": "",
                         "stop_pct": "%.2f" % behalten["stop_pct"],
                         "grund": GRUND, "pos_id": p.get("pos_id") or ""})
        # 2. die behaltene auf den kumulativen Stand bringen
        neue.append({"zeit": jetzt, "modus": "papier", "aktion": "kauf",
                     "inst": inst, "seite": seite,
                     "preis": "%.6f" % behalten["einstieg"],
                     "einsatz_usd": "%.2f" % behalten["nominal"],
                     "stop": "%.6f" % behalten["stop"],
                     "ziel": "%.6f" % behalten["ziel"],
                     "stop_pct": "%.2f" % behalten["stop_pct"],
                     "grund": "stapel_zusammengefasst", "pos_id": behalten.get("pos_id") or ""})
        zeilen_schreiben(jp, neue)

    if anwenden:
        behalten_ids = {p.get("pos_id") for p in (z.get("positionen") or [])}
        for gruppe in staffeln.values():
            beh, weg = zusammenfassen([dict(p) for p in gruppe], stop_pct, r)
            z["positionen"] = [p for p in z["positionen"] if p not in weg]
        with open(zp, "w", encoding="utf-8", newline="") as fh:
            json.dump(z, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("    -> %d Positionen nachher" % len(z.get("positionen") or []))
    return True


def spiegeln(spur):
    """Bedingung 4: Journal und Zustand nach Q: (mit der Wache als Quelle)."""
    ordner, zp, jp, z, w = spur_daten(spur)
    ziel = w.get("journal_zweitziel")
    if not ziel:
        return False
    try:
        os.makedirs(ziel, exist_ok=True)
        for quelle in (jp, zp):
            if os.path.isfile(quelle):
                shutil.copy2(quelle, os.path.join(ziel, os.path.basename(quelle)))
        return True
    except OSError as e:
        print("    Spiegelung %s: %s" % (spur, str(e)[:60]))
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spur", help="nur diese Spur (Default: alle)")
    ap.add_argument("--anwenden", action="store_true",
                    help="schreiben (Vorschau ist der Standard)")
    args = ap.parse_args()

    spuren = ([args.spur] if args.spur else
              sorted(os.path.basename(os.path.dirname(p))
                     for p in glob.glob(os.path.join(HANDEL, "*", "zustand.json"))))
    print("Vorschau" if not args.anwenden else "ANWENDEN")
    print("-" * 78)
    getroffen = []
    for spur in spuren:
        if spur_raeumen(spur, args.anwenden):
            getroffen.append(spur)
            if args.anwenden:
                spiegeln(spur)
    print("-" * 78)
    if not getroffen:
        print("kein Stapel gefunden")
    else:
        print("betroffen: %s" % ", ".join(getroffen))


if __name__ == "__main__":
    main()