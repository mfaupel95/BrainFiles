"""Papier-Altlasten aus den Kraken-Buechern buchen.

WAS DAS PROBLEM IST
-------------------
Drei Spuren handeln (auch) auf Kraken und fuehren Papier und Live in EINEM
Buch. Eine Papier-Position ohne Order belegt darin einen Platz - bei
`max_offene_positionen 4` sind dann alle vier Plaetze weg und ein Live-Lauf
kauft nie etwas. Genau das war am 25.09.2026 der Stand:

    kraken           4 Papier-Positionen, 4 Plaetze   (handel_erlaubt=false)
    nautilus_kraken  4 Papier-Positionen, 4 Plaetze   (armiert: true, freigabe true)
    mosaic           1 Papier-Position von 5 Live-Plaetzen (live, 3 echte Kraken-Positionen)

Ein Live-Zyklus raeumt das seit dem 25.09.2026 selbst auf (die Funktion
`bueche_papier_altlasten_aus` jeder Spur laeuft am Anfang eines Live-Laufs) -
bei `handel_erlaubt=false` bzw. ohne offenes Freigabefenster passiert das aber
nie. Dieses Werkzeug bucht die Altlasten JETZT aus, damit die Live-Schaltung
sofort kaufen kann.

Es rechnet NICHT selbst: gerufen wird immer die Funktion der Spur, damit die
Buchung dieselbe ist wie im Betrieb (Lehre: eine Nachbildung prueft die
Nachbildung, nicht die Spur).

AUFRUF
------
    python papierbuch_schliessen.py                 # Vorschau (Standard)
    python papierbuch_schliessen.py --anwenden
    python papierbuch_schliessen.py --spur kraken --anwenden

Sicherungen: Eine Zustandsdatei, die juenger als SCHONFRIST_S ist, wird NICHT
angefasst - dort laeuft gerade ein Zyklus des Dauerlaufs. Live-Positionen
(modus=live, txid) bleiben in jedem Fall stehen.
"""

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))

# Naht fuer Tests: hier schreiben sie ihren Temp-Ordner hin.
HANDEL = HIER

SCHONFRIST_S = 300

SPUREN = {
    "kraken": {"ordner": "kraken", "mit_wachen": False},
    "nautilus_kraken": {"ordner": "nautilus_kraken", "mit_wachen": True},
    "mosaic": {"ordner": "mosaic", "mit_wachen": True},
}


def _lade(ordner, datei, wurzel=None):
    pfad = os.path.join(wurzel or HANDEL, ordner, datei)
    spec = importlib.util.spec_from_file_location(
        "papierbuch_%s" % ordner, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _alter_s(pfad):
    if not os.path.exists(pfad):
        return None
    return max(0.0, datetime.now().timestamp() - os.path.getmtime(pfad))


def _spiegeln(modul, z, ziel, schreibe_zustand):
    """Bedingung 4 nachziehen - mit der EINEN Spiegel-Implementierung des
    Hauses (scanner/wachen_pruefung.py), nicht mit einer eigenen."""
    pfad = os.path.join(HANDEL, "scanner", "wachen_pruefung.py")
    spec = importlib.util.spec_from_file_location("wp_papierbuch", pfad)
    wp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wp)
    dateien = [str(getattr(modul, "JOURNAL")), str(getattr(modul, "ZUSTAND"))]
    ok, info = wp.spiegele_journal(dateien, ziel)
    wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand)
    if ok:
        wp.spiegele_journal([str(getattr(modul, "ZUSTAND"))], ziel)
    return ok, info


def lauf(spur, anwenden=False, wurzel=None):
    """EINE Spur aufraeumen. Rueckgabe: dict mit dem Befund dieser Spur."""
    eintrag = SPUREN[spur]
    ordner = eintrag["ordner"]
    pfad = os.path.join(wurzel or HANDEL, ordner)
    sys.path.insert(0, pfad)
    try:
        modul = _lade(ordner, "handeln.py", wurzel)
    finally:
        sys.path.pop(0)

    zustand_pfad = str(modul.ZUSTAND)
    journal_pfad = str(modul.JOURNAL)
    alter = _alter_s(zustand_pfad)
    if anwenden and alter is not None and alter < SCHONFRIST_S:
        print("  %-16s uebersprungen: Zustand ist %.0f s alt (Grenze %d s) - "
              "dort laeuft ein Zyklus" % (spur, alter, SCHONFRIST_S))
        return {"spur": spur, "gebucht": 0, "uebersprungen": True}

    z = modul.lade_zustand()
    vorher = len(z.get("positionen") or [])
    papier = [p for p in (z.get("positionen") or [])
              if p.get("modus") != "live"]
    print("  %-16s %d Position(en), davon %d Papier  (%s)"
          % (spur, vorher, len(papier), os.path.basename(zustand_pfad)))
    if not papier:
        return {"spur": spur, "gebucht": 0, "vorher": vorher, "nachher": vorher}
    if not anwenden:
        # Vorschau: die Journalzeile der Spur abfangen statt sie zu schreiben.
        gesammelt = []
        echt = modul.journal
        modul.journal = lambda *a, **k: gesammelt.append((a, k))
        try:
            w = modul.lade_wachen() if eintrag["mit_wachen"] else None
            if eintrag["mit_wachen"]:
                modul.bueche_papier_altlasten_aus(z, w)
            else:
                modul.bueche_papier_altlasten_aus(z)
        finally:
            modul.journal = echt
        for a, k in gesammelt:
            felder = {n: str(v) for n, v in zip(
                ("zeit", "modus", "aktion", "inst", "preis", "eur",
                 "menge", "stop", "ziel", "grund"), a)}
            felder.update(k)
            print("      wuerde buchen: %s" % json.dumps(
                felder, ensure_ascii=False))
        return {"spur": spur, "gebucht": len(gesammelt),
                "vorher": vorher, "nachher": vorher - len(gesammelt)}

    w = modul.lade_wachen() if eintrag["mit_wachen"] else None
    if eintrag["mit_wachen"]:
        gebucht = modul.bueche_papier_altlasten_aus(z, w)
    else:
        gebucht = modul.bueche_papier_altlasten_aus(z)
    if gebucht:
        modul.schreibe_zustand(z)
    nachher = len(z.get("positionen") or [])
    ziel = None
    try:
        ziel = (modul.lade_wachen() or {}).get("journal_zweitziel")
    except Exception:                                          # noqa: BLE001
        ziel = None
    if gebucht:
        print("      %d gebucht, Buch %d -> %d" % (gebucht, vorher, nachher))
        if ziel:
            ok, info = _spiegeln(modul, z, ziel, modul.schreibe_zustand)
            print("      Journal ausser Haus: %s"
                  % (info if ok else "nicht kopiert - %s" % info))
    return {"spur": spur, "gebucht": gebucht, "vorher": vorher,
            "nachher": nachher, "journal": str(journal_pfad)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anwenden", action="store_true",
                    help="wirklich buchen und Zustand schreiben (Standard: Vorschau)")
    ap.add_argument("--spur", choices=sorted(SPUREN), default=None,
                    help="nur diese Spur (Standard: alle)")
    a = ap.parse_args()

    namen = [a.spur] if a.spur else sorted(SPUREN)
    print("=== Papier-Altlasten %s ==="
          % ("ANWENDEN" if a.anwenden else "Vorschau (nichts geschrieben)"))
    ergebnis = [lauf(n, anwenden=a.anwenden) for n in namen]
    gesamt = sum(e["gebucht"] for e in ergebnis)
    print("=== %d Buchung(en) %s ==="
          % (gesamt, "geschrieben" if a.anwenden else "waeren dran"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())