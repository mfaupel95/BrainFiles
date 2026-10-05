"""T-354: Das Feld `modus` in alten Buch-Positionen nachtragen.

WAS DAS PROBLEM IST
-------------------
Jede Position, die `spur_buch.einstieg()` eroeffnet, traegt seit dem
21.09.2026 (Commit f8f269d8, "Orderweg fuer die Buch-Spuren") das Feld
`modus` - "live" oder "papier". Es ist der einzige Massstab, an dem eine
Buch-Position als echte Boersen-Position erkennbar ist:

    scanner/handeln.py:718   altlasten = [p for p in z["positionen"]
                                           if not p.get("kauf_ord_id")]
    xperp/handeln.py:314     alt      = [p for p in z["positionen"]
                                           if p.get("modus") != "live"]

Eine Position OHNE dieses Feld ist fuer beide Bucher eine Position
fremder Herkunft - sie kann nicht ausgebucht werden, und sie wuerde in einem
Live-Buch als Papier behandelt und dort geschlossen, waehrend sie an der
Boerse offen bleibt (der Fehler vom 21.09.2026: HBAR, scanner 26.09.2026).

Altbestand: Positionen, die vor dem 21.09. eroeffnet wurden und seither nie
geschlossen sind.

WAS HIER ANDERS IST ALS AM 21.09.
---------------------------------
Der Befund dieser Karte ist KEINE Buch-Geister-Position im Sinne der damaligen
Lage (xperp 21.09., ZRO 02.10.): das waren Positionen, die das Buch behauptete,
obwohl SIE an der Boerse nie existierten. Hier ist es umgekehrt und deshalb
wichtig:

  * Die Buecher dieser Spuren tragen `modus: papier` auf Buch-Ebene, und ihre
    Journale enthalten NULL Zeilen mit `modus=live` (gemessen 05.10.2026:
    signalwelle 49/38/19 Zeilen Basis/mittel/hoch, alle `papier`; marktlage
    4/3/1). Eine Live-Zeile waere der Beweis fuer eine echte Position.
  * Beide Instrumente sind an KEINER Boerse offen: OKX kennt GENIUS gar nicht
    als Markt (51001), und BTC-USDC hat keine offene Position aus dieser Zeit
    (availBal 0, frozenBal nur aus spaeteren scanner-Kaeufen); Kraken fuehrt
    weder ein BTC- noch ein GENIUS-Paar mit offenem Bestand.
  * Die Positionen sind also echte, laufende PAPIER-Positionen mit Stop und
    Ziel, die der Dauerlauf weiter beobachtet.

Sie auszubuchen waere deshalb ein FABRIKIERTER Ausstieg: eine Verkaufszeile
mit Grund "buchbereinigung" im Journal, eine Auswertung, die eine Runde
zaehlt, die es nie gab, und - schlimmer - das Ende einer Position, deren Stop
heute noch schuetzt. Der richtige Schritt ist der billigere der beiden, den
TASKS.md selbst nennt: DAS FELD NACHTRAGEN.

Die Regel, an der das hier entschieden wird
-------------------------------------------
Ein Buch wird nur angefasst, wenn es ZWEI Dinge belegt sind:

  1. Der Buch-Modus ist nicht "live". Ein Live-Buch (scanner, omniquant,
     mosaic) benutzt `kauf_ord_id` als Herkunftsnachweis und NICHT `modus` -
     dort eine Position auf "papier" zu setzen waere eine FALSCHE Aussage,
     keine Korrektur.
  2. Das zugehoerige Journal enthaelt keine einzige Zeile mit `modus=live`.
     Ohne diesen Beleg bleibt die Position unangetastet und wird gemeldet.

Beide Bedingungen sind aus Dateien lesbar, ohne eine Boerse zu fragen.

WAS DAS WERKZEUG NICHT TUT
--------------------------
Es schreibt KEINE Journalzeile (kein Ausstieg, keine Runde). Es aendert
keinen Einstiegskurs, keinen Stop, kein Ziel, kein `pos_id`. Es schreibt nur
das eine Feld plus einen Vermerk, woraus es kam, und spiegelt nach
Bedingung 4.

AUFRUF
------
    python modus_nachtragen.py                 # Vorschau (Standard)
    python modus_nachtragen.py --anwenden
    python modus_nachtragen.py --spur moondev_marktlage --anwenden

Sicherung: Jede Zustandsdatei, die juenger als SCHONFRIST_S ist, wird NICHT
angefasst - dort laeuft gerade ein Zyklus des Dauerlaufs (drei Stufen,
15-Minuten-Takt). Vor dem Schreiben entsteht eine Sicherung
`<datei>.bak-JJJJMMTT-HHMMSS`.
"""

import argparse
import csv
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))

# Naht fuer Tests: hier schreiben sie ihren Temp-Ordner hin.
HANDEL = HIER

SCHONFRIST_S = 300

# Das Vermerk-Feld, damit spaeter sichtbar ist, dass das `modus` nicht vom
# Einstieg stammt, sondern aus dieser Bereinigung.
VERMERK = "modus_nachtragen"

# Das Merkmal, an dem eine echte (live gekaufte) Buch-Position erkennbar ist.
LIVE_MARKER = "modus"


# --- Die Buch-Spuren bestimmen sich selbst ----------------------------------

_ZYKLUS = re.compile(r"spur_buch|buch\.zyklus")


def spur_mit_buchkern(wurzel=None):
    """Ordner, deren handeln.py das gemeinsame Buch (spur_buch) benutzt.

    Bestimmt aus dem QUELLTEXT statt aus einer Liste: eine Liste hier waere
    eine zweite Wahrheit, die bei jeder neuen Spur veraltet.
    """
    basis = wurzel or HANDEL
    gefunden = []
    for name in sorted(os.listdir(basis)):
        ordner = os.path.join(basis, name)
        datei = os.path.join(ordner, "handeln.py")
        if not (os.path.isdir(ordner) and os.path.isfile(datei)):
            continue
        with open(datei, encoding="utf-8") as f:
            if _ZYKLUS.search(f.read()):
                gefunden.append(name)
    return gefunden


def zustand_dateien(ordner, wurzel=None):
    """Die Zustandsdateien EINER Spur: Basis, mittel, hoch (fehlende ausgelassen)."""
    basis = os.path.join(wurzel or HANDEL, ordner)
    raus = []
    for name in sorted(os.listdir(basis)):
        if re.fullmatch(r"zustand(\.[a-z]+)*\.json", name):
            raus.append(os.path.join(basis, name))
    return raus


def journal_zu(zustand_pfad):
    """Das Journal, das zu einer Zustandsdatei gehoert (Suffix-Regel der Stufe).

    `zustand.mittel.json` -> `handelsjournal.mittel.csv`. Die Endung gehoert an
    das Suffix, nicht an den Basisnamen - sonst hiess die Spiegel-Datei der
    Stufen ohne `.csv` und Bedingung 4 schickte an das falsche Ziel.
    """
    ordner = os.path.dirname(zustand_pfad)
    basis, _ = os.path.splitext(os.path.basename(zustand_pfad))
    return os.path.join(ordner, "handelsjournal" + basis[len("zustand"):]
                        + ".csv")


# --- Die beiden Belege -------------------------------------------------------

def journal_hat_live(journal_pfad):
    """True, wenn das Journal eine Zeile mit modus=live enthaelt.

    Solche Zeile ist der Beweis, dass die Spur an der Boerse GEKAUFT hat. Dann
    ist eine Position ohne `modus` nicht automatisch Papier, und dieses
    Werkzeug fasst das Buch nicht an.
    """
    if not os.path.isfile(journal_pfad):
        return False
    with open(journal_pfad, newline="", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            if (z.get(LIVE_MARKER) or "").strip() == "live":
                return True
    return False


def fehlende_modus(positionen):
    """Die Positionen ohne Herkunftsfeld."""
    return [p for p in (positionen or []) if p.get(LIVE_MARKER) is None]


# --- Was eine Datei blockiert -----------------------------------------------

def sperrgrund(z, journal_pfad, zustand_pfad, alter_s):
    """'' = handlungsfaehig, sonst der Grund (als Zeile)."""
    if (z.get("modus") or "papier") == "live":
        return "Buch-Modus live - dort ist kauf_ord_id der Herkunftsnachweis"
    if journal_hat_live(journal_pfad):
        return "Journal hat eine live-Zeile - Herkunft nicht belegbar"
    if alter_s is not None and alter_s < SCHONFRIST_S:
        return "Zustand ist %.0f s alt (Grenze %d s) - dort laeuft ein Zyklus" % (
            alter_s, SCHONFRIST_S)
    return ""


def _alter_s(pfad):
    if not os.path.exists(pfad):
        return None
    return max(0.0, datetime.now().timestamp() - os.path.getmtime(pfad))


def _sichern(pfad):
    stempel = datetime.now().strftime("%Y%m%d-%H%M%S")
    ziel = "%s.bak-%s" % (pfad, stempel)
    with open(pfad, "rb") as f:
        inhalt = f.read()
    with open(ziel, "wb") as f:
        f.write(inhalt)
    return ziel


def spiegeln(spur, zustand_pfad, journal_pfad):
    """Bedingung 4 nachziehen - mit der EINEN Spiegel-Implementierung des
    Hauses (`scanner/wachen_pruefung`), nicht mit einer eigenen. Das Ziel steht
    in der Wache der Spur (`journal_zweitziel`); es wird auch in den Zustand
    geschrieben, damit eine ausgefallene Kopie sichtbar bleibt.
    """
    wachen_pfad = os.path.join(os.path.dirname(zustand_pfad), "wachen.json")
    with open(wachen_pfad, encoding="utf-8") as f:
        ziel = (json.load(f) or {}).get("journal_zweitziel")
    pfad = os.path.join(HANDEL, "scanner", "wachen_pruefung.py")
    spec = importlib.util.spec_from_file_location("wp_modusnachtrag", pfad)
    wp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wp)
    z = lade(zustand_pfad)

    def schreiben(zz):
        for k, v in (("journal_zweitziel", ziel),
                     ("journal_zweitziel_ok", wp_ok),
                     ("journal_zweitziel_info", wp_info)):
            zz[k] = v
        with open(zustand_pfad, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(zz, ensure_ascii=False, indent=2) + "\n")

    wp_ok, wp_info = wp.spiegele_journal([zustand_pfad, journal_pfad], ziel)
    schreiben(z)
    return wp_ok, wp_info


# --- Der Lauf ----------------------------------------------------------------

def lade(pfad):
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


def datei_lauf(spur, zustand_pfad, anwenden, spiegel=False):
    """Eine Zustandsdatei pruefen und (mit --anwenden) das Feld nachtragen."""
    z = lade(zustand_pfad)
    journal_pfad = journal_zu(zustand_pfad)
    fehlt = fehlende_modus(z.get("positionen"))
    befund = {"spur": spur, "datei": os.path.basename(zustand_pfad),
              "geaendert": 0, "fehlt": len(fehlt), "grund": ""}
    if not fehlt:
        befund["grund"] = "alle Positionen tragen modus"
        return befund
    for p in fehlt:
        inst = p.get("inst") or "?"
        eroeffnet = (p.get("eroeffnet_zeit") or "?")[:16]
        befund.setdefault("betroffen", []).append((inst, eroeffnet))
    grund = sperrgrund(z, journal_pfad, zustand_pfad, _alter_s(zustand_pfad))
    if grund:
        # `betroffen` ist auch im gesperrten Fall gesetzt: wer nur weiss, dass
        # irgendein Buch ein `modus` vermisst, muss die Positionen SEHEN
        # koennen, um sie von Hand pruefen zu koennen.
        befund["grund"] = grund
        return befund
    for p in fehlt:
        if anwenden:
            p[LIVE_MARKER] = "papier"
            p[VERMERK] = ("T-354 05.10.2026: Herkunft nachtragen - Buch-Modus "
                          "papier, Journal ohne live-Zeile")
    if anwenden:
        befund["sicherung"] = _sichern(zustand_pfad)
        neu = json.dumps(z, ensure_ascii=False, indent=2)
        # ZUERST den Inhalt bauen, DANN oeffnen: open(pfad,"w") schneidet die
        # Datei auf 0 Byte, bevor der Ausdruck fertig ist (TASKS.md-Gau vom
        # 01.10.2026).
        assert neu and neu != "{}", "leerer Zustand - nicht geschrieben"
        with open(zustand_pfad, "w", encoding="utf-8", newline="\n") as f:
            f.write(neu + "\n")
        befund["geaendert"] = len(fehlt)
        if spiegel:
            ok, info = spiegeln(spur, zustand_pfad, journal_pfad)
            befund["spiegel"] = info if ok else "nicht kopiert - %s" % info
    return befund


def lauf(spuren=None, anwenden=False, spiegel=False, wurzel=None):
    basis = wurzel or HANDEL
    namen = spuren or spur_mit_buchkern(basis)
    befunde = []
    for spur in namen:
        for zustand_pfad in zustand_dateien(spur, basis):
            befunde.append(datei_lauf(spur, zustand_pfad, anwenden, spiegel))
    return befunde


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anwenden", action="store_true",
                    help="wirklich schreiben (Standard: Vorschau)")
    ap.add_argument("--spiegeln", action="store_true",
                    help="nach dem Schreiben ausser Haus kopieren (Bedingung 4)")
    ap.add_argument("--spur", default=None, help="nur diese Spur")
    a = ap.parse_args()

    print("=== modus nachragen: %s ==="
          % ("ANWENDEN" if a.anwenden else "Vorschau (nichts geschrieben)"))
    befunde = lauf([a.spur] if a.spur else None, a.anwenden, a.spiegeln)
    geaendert = 0
    for b in befunde:
        if not b["fehlt"]:
            continue
        kopf = "  %-20s %-22s %d ohne modus" % (
            b["spur"], b["datei"], b["fehlt"])
        if b["grund"]:
            print(kopf + "  -> nicht angefasst: %s" % b["grund"])
            continue
        print(kopf)
        for inst, eroeffnet in b.get("betroffen", []):
            print("        %-22s eroeffnet %s" % (inst, eroeffnet))
        if a.anwenden:
            geaendert += b["geaendert"]
            print("        -> %d Position(en) auf modus=papier gesetzt"
                  % b["geaendert"])
            if b.get("spiegel"):
                print("        -> ausser Haus: %s" % b["spiegel"])
        else:
            print("        -> wuerde auf modus=papier gesetzt")
    print("=== %d Position(en) %s ==="
          % (geaendert, "geschrieben" if a.anwenden else "waeren dran"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())