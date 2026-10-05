"""Omniquants Buch bereinigen: 8 Papier-Geiste neutral ausbuchen (05.10.2026).

AUFTRAG Max: "buch bereinigen".

ANLASS, gemessen am 05.10.2026 (Befund in T-355): `zustand.json` fuehrt 9
Positionen im Modus `live`, und AN DER BOERSE IST NULL davon - 9x "0 offene"
ueber openpositions je Symbol. 8 Positionen tragen kein `modus`-Feld und
kein `einsatz_usd`; sie stammen alle aus `papier`-EINSTIEGen vom
28.09.-03.10. Am 01.10.2026 wurde `z["modus"]` auf `live` geschaltet, und
die Positionen sind mitgegangen - diese Spur hat (anders als scanner,
xperp, swap, mosaic) keine `bueche_papier_altlasten_aus()`, kann sie also
selbst nicht ausbuchen.

WAS DAS WERKZEUG TUT, je Position:
  1. prueft ZWEIMAL gegen die Boerse, nicht gegen das Buch (der Grund
     des Auftrags): 0 offene Positionen heisst "Geist", >0 heisst "echt -
     die wird NICHT angefasst", weil sie dann einen Stop und einen
     Ausstieg braucht, den nur der Live-Zweig stellen kann;
  2. schreibt eine Journalzeile `papier,schliessen,...,buchbereinigung`
     mit dem EINSTEIGSPREIS - NEUTRAL (Wert = Einsatz), damit die
     Bereinigung die Bilanz nicht veraendert;
  3. nimmt die Position aus dem Zustand.

WAS ES NICHT TUT: nichts loeschen, keine Historie antasten, keine
Freigabe aendern, keine Live-Position anfassen. Die Journal-Zeile traegt
den Grund `buchbereinigung`, den `stoerungen.ist_stoerung` erkennt - sie
zaehlt damit NICHT als Handelsrunde (gemessen: kosten_wendepunkt.py
Zeile 115 filtert sie heraus). Genau das ist der Unterschied zu einem
Verkauf und der Grund fuer den Grund-Text.

HBAR bleibt unangetastet: die einzige Position mit `modus: live` und
Einsatz 50. Sie wird nur gemeldet.

SICHERUNG: zustand.json.bak-JJJJMMTT und handelsjournal.csv.bak-JJJJMMTT
TROCKENLAUF ist Vorgabe, --anwenden schreibt.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import shutil
import sys

HIER = os.path.dirname(os.path.abspath(__file__))   # = der Spurordner
SPUR = HIER
HANDEL = os.path.dirname(HIER)                      # = Agenten/Handel

ZUSTAND = os.path.join(SPUR, "zustand.json")
JOURNAL = os.path.join(SPUR, "handelsjournal.csv")

# Die Spalten der Spur - aus handeln.py, nicht geraten. Eine falsche
# Kopfzeile haette die Journal-Datei unlesbar gemacht.
SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis", "einsatz_usd",
           "wert_usd", "stop", "ziel", "grund", "score", "cr", "mfe_pct",
           "mae_pct", "haltetage", "pos_id"]

GRUND = "buchbereinigung"


def _zahl(wert, default=0.0):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return default


def _preis(p):
    """Der Einstiegspreis einer Position - aus dem FELD, das die Spur setzt.

    ANLASS, gemessen 05.10.2026: mein erstes Werkzeug las `preis` und
    bekam fuer alle 9 Positionen 0.00. Die Spur schreibt aber `einstieg`
    (`eroeffne()`, handeln.py:366) und den Betrag als `nominal`, nicht
    `einsatz_usd`. Eine Zeile mit `preis=0.00` waere zwar formal neutral
    (Wert = Einsatz), aber sie wuerde eine Position mit Kurs 0 in die
    Historie schreiben - und die naechste Auswertung, die nach Kursen
    sortiert, bekommt einen Null-Eintrag.

    Deshalb wird JEDES Feld geprueft und der Fall offen benannt statt
    geraten:
      `einstieg`  -> der Kurs der Position
      `nominal`   -> der Einsatz, mit dem die Position eroeffnet wurde
    Fehlen beide, ist das ein BEFUND (kein Wert, kein Raten) und die
    Position bleibt stehen - sie wird nicht mit Null gebucht.
    """
    for feld in ("einstieg", "preis", "einstiegspreis"):
        w = p.get(feld)
        if w not in (None, ""):
            return _zahl(w), feld
    return None, None


def _einsatz(p):
    for feld in ("einsatz_usd", "nominal", "einsatz"):
        w = p.get(feld)
        if w not in (None, ""):
            return _zahl(w), feld
    return 0.0, None


def _lade_kp():
    """kraken_perp ueber den PFAD - der Ordner ist sys.path[0]."""
    import importlib.util
    pfad = os.path.join(SPUR, "kraken_perp.py")
    spec = importlib.util.spec_from_file_location("omni_kraken_perp", pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules["omni_kraken_perp"] = m
    spec.loader.exec_module(m)
    return m


def boersen_bestaetigung(kp, anwenden):
    """Je Position: fuehrt die Boerse sie? Nur das ist der Beleg.

    EIN Aufruf, EIN Ergebnis: es wird nicht geraten und nicht aus dem Buch
    abgeleitet. Ein Symbol ohne `pf_markt` (kein PF_-Markt) zaehlt als
    "nicht pruefbar" und wird NICHT angefasst - eine Position, deren Weg
    man nicht kennt, ist keine Geisterposition, sie ist eine unbekannte.
    """
    kp.lade_maerkte()
    kp.setze_ableitung(True)          # nur LESEN: loest Namen auf
    ergebnis = []
    for p in (lade_zustand().get("positionen") or []):
        inst = p.get("inst")
        try:
            pos = kp.offene_positionen(inst)
            n = len(pos) if isinstance(pos, (list, dict)) else 0
            ergebnis.append({"inst": inst, "n": n,
                             "art": "echt" if n else "geist"})
        except Exception as e:                            # noqa: BLE001
            ergebnis.append({"inst": inst, "n": None, "art": "unklar",
                             "grund": str(e)[:70]})
    return ergebnis


def lade_zustand():
    with open(ZUSTAND, encoding="utf-8") as f:
        return json.load(f)


def aufraeumen(anwenden, nur_geister=True, rest=False):
    kp = _lade_kp()
    zustand = lade_zustand()
    offen = list(zustand.get("positionen") or [])
    if not offen:
        print("Buch ist bereits leer.")
        return 0

    befund = {b["inst"]: b for b in boersen_bestaetigung(kp, anwenden)}

    # --- 1. Klassifizieren. Nur zweimal belegtes Zaehlen hier. ---
    geister, echt, unklar, ohne_wert = [], [], [], []
    for p in offen:
        inst = p.get("inst")
        b = befund.get(inst) or {"art": "unklar"}
        preis, preisfeld = _preis(p)
        if b["art"] == "echt":
            echt.append(p)
        elif b["art"] == "geist":
            # Ein Geist OHNE Kurs ist kein normaler Fall: ohne Einstiegs-
            # preis laesst sich die Ausgleichszeile nicht ehrlich fuellen.
            # Er bleibt stehen und wird als BEFUND gemeldet - eine Zeile mit
            # Preis 0.00 waere geraten, und geraten wird hier nichts.
            if preis is None:
                ohne_wert.append(p)
            else:
                geister.append(p)
        else:
            unklar.append((p, b.get("grund", "?")))

    print("\n=== Befund (Buch gegen Boerse) ===")
    print("  Buch: %d Positionen" % len(offen))
    print("    Geister (0 offene), mit Kurs:  %d" % len(geister))
    print("    Geister OHNE Kurs (Befund):    %d" % len(ohne_wert))
    print("    echt  (>0 offene):             %d" % len(echt))
    print("    unklar (nicht pruefbar):       %d" % len(unklar))
    for p in echt:
        print("      ECHT, bleibt stehen: %-12s modus=%s einsatz=%s"
              % (p.get("inst"), p.get("modus") or "FEHLT",
                 p.get("einsatz_usd", "FEHLT")))
    for p in ohne_wert:
        print("      OHNE EINSTIEGSKURS, bleibt stehen: %-12s (Felder: %s)"
              % (p.get("inst"), ", ".join(sorted(p.keys()))[:60]))
    for p, g in unklar:
        print("      UNKLAR, bleibt stehen: %-12s %s" % (p.get("inst"), g))

    ziel = geister if nur_geister else (geister + echt)
    if not ziel:
        print("\nNichts auszubuchen.")
        return 0

    # --- 2. Die Bilanz vorher/nachher: der Wert darf sich NICHT bewegen.
    einsatz_gesamt = sum(_einsatz(p)[0] for p in ziel)
    bilanz_vor = _rechnungsbestand(zustand, offen)
    print("\n=== Bilanz-Gegenprobe ===")
    print("  Einsatz der %d Positionen:        %.2f USD" % (len(ziel), einsatz_gesamt))
    print("  Runden-Bestand vorher:            %.2f USD" % bilanz_vor)

    # Jede Position mit ihrem Kurs und Einsatz - lesbar, bevor geschrieben wird
    print("\n=== Was gebucht wird (neutral: Wert = Einsatz) ===")
    for p in ziel:
        pr, pf = _preis(p)
        ei, ef = _einsatz(p)
        print("  %-12s Kurs %-12.6g (%s)  Einsatz %.2f (%s)  %s"
              % (p.get("inst"), pr, pf, ei, ef, GRUND))

    if not anwenden:
        print("\nTROCKENLAUF - nichts geschrieben. Mit --anwenden schreiben.")
        return len(ziel)

    # --- 3. Schreiben. Sicherung ZUERST, Zustand zuletzt.
    stempel = dt.datetime.now().strftime("%Y%m%d")
    shutil.copy2(ZUSTAND, ZUSTAND + ".bak-" + stempel)
    shutil.copy2(JOURNAL, JOURNAL + ".bak-" + stempel)
    print("\n  Sicherung: %s.bak-%s" % (os.path.basename(ZUSTAND), stempel))

    jetzt = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN)
        for p in ziel:
            # NEUTRAL: Einstiegspreis, Wert = Einsatz. Es gab keinen Verkauf,
            # also darf die Bereinigung das Ergebnis nicht verschieben.
            preis, _pf = _preis(p)
            einsatz, _ef = _einsatz(p)
            w.writerow({
                "zeit": jetzt, "modus": "papier", "aktion": "schliessen",
                "inst": p.get("inst") or "", "seite": p.get("seite") or "long",
                "preis": repr(preis), "einsatz_usd": einsatz,
                "wert_usd": einsatz, "stop": "", "ziel": "",
                # `stoerungen.ist_stoerung` erkennt "buchbereinigung" - die
                # Zeile zaehlt damit NICHT als Handelsrunde (kosten_
                # wendepunkt.py:115). Ohne diesen Grund waere es eine.
                "grund": GRUND, "score": "", "cr": "", "mfe_pct": "",
                "mae_pct": "", "haltetage": "", "pos_id": p.get("pos_id") or "",
            })

    rest_pos = offen if rest else [p for p in offen if p not in ziel]
    zustand["positionen"] = rest_pos
    zustand.setdefault("buchbereinigung", []).append({
        "zeit": jetzt, "anzahl": len(ziel),
        "grund": "Papier-Altlasten im Live-Buch, an der Boerse nicht "
                 "vorhanden (Max 05.10.2026: 'buch bereinigen')",
        "instrumente": sorted(p.get("inst") for p in ziel),
    })
    with open(ZUSTAND, "w", encoding="utf-8") as f:
        json.dump(zustand, f, ensure_ascii=False, indent=2)

    print("  %d Zeilen mit grund=%s geschrieben" % (len(ziel), GRUND))
    print("  Buch jetzt: %d Positionen" % len(rest_pos))

    # --- 4. Gegenprobe NACH dem Schreiben.
    nach = lade_zustand()
    bilanz_nach = _rechnungsbestand(nach, nach.get("positionen") or [])
    print("\n=== Gegenprobe nach dem Schreiben ===")
    print("  Buch: %d -> %d Positionen" % (len(offen), len(nach.get("positionen") or [])))
    print("  Runden-Bestand nachher:            %.2f USD" % bilanz_nach)
    print("  Bilanz unveraendert: %s (Differenz %.2f)"
          % ("JA" if abs(bilanz_vor - bilanz_nach) < 0.01 else "NEIN",
             bilanz_nach - bilanz_vor))
    return len(ziel)


def _rechnungsbestand(zustand, positionen):
    """Womit die Spur ihren Bestand rechnet - dieselbe Zahl wie im Lauf."""
    z = dict(zustand)
    z["positionen"] = positionen
    return sum(_einsatz(p)[0] for p in positionen) + \
        _zahl(zustand.get("verluste_usd"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anwenden", action="store_true",
                    help="schreiben (Vorgabe ist der Trockenlauf)")
    ap.add_argument("--auch-echte", action="store_true",
                    help="ACHT: raeumt AUCH Positionen ab, die an der "
                         "Boerse stehen - nur mit Absicht")
    ap.add_argument("--mit-rest", action="store_true",
                    help="(unbenutzt) Positionen behalten statt leeren")
    a = ap.parse_args()
    n = aufraeumen(a.anwenden, nur_geister=not a.auch_echte)
    if a.anwenden:
        print("\nBereinigung fertig. HBAR und alle echten Positionen sind "
              "unangetastet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())