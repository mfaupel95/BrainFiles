"""Eine Aussage je Ausstieg: die Doppelbuchungen im echten Buch aufloesen
(T-356, 05.10.2026).

DER BEFUND
----------
Zwei Positionen trug das Journal UND den Zustand zugleich:

    NIGHT  pos_id 20261002T172950-b356a4
           Journal 05.10. 00:26:36  verkauf  grund=stop  0.04441202
           Zustand: Position weiter offen (einstieg 0.04799818)
    AI     pos_id 20261002T011219-969294
           Journal 02.10. 03:03:05  verkauf  grund=ziel  0.18346100
           Journal 02.10. 10:25:10  verkauf  grund=stop  0.15071000
           Zustand: keine Position offen

URSACHE (durch die Elternkarten gemessen, hier nicht neu ermittelt)
    `spur_buch.zyklus()` kehrte im `--vorschau`-Zweig vor
    `schreibe_zustand()` zurueck, waehrend `pruefe_ausstiege()` die
    Verkaufszeile schon geschrieben hatte. Ein Vorschau-Aufruf
    (`dauerlauf.nur_fenster_fehlt()`, Handelszentrale, Auswertung) buchte den
    Ausstieg also ins Journal und liess die Position im Zustand stehen. Seit
    Commit `ee3ff9be` ist `spur_buch.buche()` die einzige Schreibstelle
    (Journalzeile UND Zustand in einem Aufruf) und die Vorschau steht vor
    jeder Buchung: ein NEUER Geist kann nicht mehr entstehen. Hier wird der
    Altbestand aufgeloest, nicht der Code.

DIE REGEL, UND IHRE BEGRUENDUNG
-------------------------------
Je `pos_id` gehoert genau EINE Aussage in das Buch: entweder eine
Verkaufszeile und die Position ist aus dem Zustand, oder gar nichts. Wer
falsch ist, entscheidet die Art des Fehlers - nicht die Bequemlichkeit:

  geist         - Verkaufszeile UND Position weiter offen im Zustand
                  -> die Verkaufszeile wird VERWORFEN, die Position bleibt.
                  Warum der Zustand fuehrt: er ist die Datei, die ein
                  ECHTER Zyklus schreibt. Eine Verkaufszeile ohne
                  Zustandsgehaeuse ist genau das, was dieser Befund ist, und
                  seit `ee3ff9be` ist sie ohne Zustand gar nicht mehr
                  erzeugbar. Die Position zu loeschen hiesse die Behauptung
                  "der Verkauf galt" aufstellen - ohne einen Zyklus, der sie
                  getroffen hat.

  doppelverkauf - mehr als eine Verkaufszeile fuer eine `pos_id`
                  -> die ERSTE bleibt, jede weitere wird verworfen.
                  Warum die erste fuehrt: die Position steht nicht mehr im
                  Zustand, es gibt also keinen Zustandseintrag, der sagen
                  koennte, welche Zeile gilt. Die frueheste Ausstiegsnotiz
                  ist die beste verfuegbare Aussage; ein spaeterer Kurs gehoert
                  zu einer Runde, die es so nie gab.

  Zeilen OHNE `pos_id` werden nie angefasst: Altjournal vor der
  Kennungsspalte (vor dem 30.09.2026), nicht zuordenbar. Sie werden gezaehlt
  und gemeldet, nicht repariert - eine Reparatur ohne Kennung waere Raten.

WAS DIESES WERKZEUG NICHT TUT
----------------------------
  * keine Positionszeile im Zustand loeschen
  * keine Zahl in einer Zeile aendern (das waere `geister_nachziehen.py`
    in xperp, ein anderer Befund)
  * keine Zeile loeschen - sie wandert nach `handelsjournal.verworfen-JJJJMMTT.csv`
  * keine andere Spur, keine andere Risikostufe ausser der genannten
  * keinen Live-Schalter, keine Order, keine Freigabe

SICHERUNG UND SPIEGELUNG
    Vor dem Schreiben: `handelsjournal.bak-JJJJMMTT.csv` und
    `zustand.bak-JJJJMMTT.json`, die verworfenen Zeilen in
    `handelsjournal.verworfen-JJJJMMTT.csv`. Danach
    wird wie im Betrieb gespiegelt (Ziel aus wachen.json), sonst meldet
    `spiegelstand.py` eine Abweichung, weil das Journal kuerzer geworden ist.
    `letzter_lauf` bleibt UNBERUEHRT - ein Werkzeug ist kein Zyklus und darf
    den Herzschlag nicht verjuengen.

AUFRUF
    python buch_reconcile.py                    (alle Stufen, Vorschau)
    python buch_reconcile.py --stufe basis
    python buch_reconcile.py --anwenden
Rueckgabecode 0 = nichts zu tun oder alles geschrieben, 1 = Befund blieb.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)

def _setze_ordner(pfad):
    """Setzt HIER (und HANDEL) auf einen anderen Spur-Ordner um.
    Nur fuer Aufrufe mit --ordner, die Standardlage bleibt unveraendert."""
    global HIER, HANDEL
    HIER = os.path.abspath(pfad)
    HANDEL = os.path.dirname(HIER)

STUFEN = ("basis", "mittel", "hoch")
VERWORFEN = "handelsjournal.verworfen-%s.csv"
AKTION_SPALTE = 2          # zeit,modus,aktion,...
INST_SPALTE = 3
POS_ID_SPALTE = 11


def _lade(name, ordner):
    """Ein Hausmodul ueber den PFAD laden - nie ueber sys.path.

    `wachen_pruefung` liegt in `scanner/`, `atomar` in `Agenten/Handel/`. Ein
    sys.path-Eintrag vorn wuerde ein gleichnamiges Modul einer anderen Spur
    verdecken (dieselbe Falle wie in xperp und trendwende_btc).
    """
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location(name, os.path.join(ordner, name + ".py"))
    m = module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


atomar = _lade("atomar", HANDEL)
wp = _lade("wachen_pruefung", os.path.join(HANDEL, "scanner"))


# --- Die Regel als reine Funktion -----------------------------------------

def befunde(daten, spalten, positionen):
    """Die Regel auf reinen Daten. Schreibt nichts.

    `daten`      = Journalzeilen OHNE Kopfzeile
    `spalten`    = Kopfzeile
    `positionen` = `zustand["positionen"]`

    Rueckgabe: (befunde, ohne_kennung) mit
      befund = {"art", "pos_id", "inst", "zeilen": [Index in daten],
                "behalten": Index in daten oder None}
      art = "geist"        -> alle Zeilen dieser pos_id sind zu verwerfen,
                              die Position bleibt (sie ist offen)
      art = "doppelverkauf" -> nur die Zeilen nach der ersten sind zu
                              verwerfen, `behalten` traegt deren Index
    """
    akz = spalten.index("aktion") if "aktion" in spalten else AKTION_SPALTE
    izz = spalten.index("inst") if "inst" in spalten else INST_SPALTE
    pkz = spalten.index("pos_id") if "pos_id" in spalten else POS_ID_SPALTE
    verkaeufe, ohne_kennung = {}, 0
    for i, z in enumerate(daten):
        if len(z) <= akz or z[akz] != "verkauf":
            continue
        pid = z[pkz].strip() if len(z) > pkz else ""
        if not pid:
            ohne_kennung += 1
            continue
        verkaeufe.setdefault(pid, []).append(i)
    offen = set()
    for p in positionen or []:
        pid = (p.get("pos_id") or "").strip()
        if pid:
            offen.add(pid)
    raus = []
    for pid, indizes in sorted(verkaeufe.items()):
        erste = daten[indizes[0]]
        inst = erste[izz] if len(erste) > izz else "?"
        if pid in offen:
            # GEIST: das Journal fuehrt nicht, die Zeile(n) wandert raus.
            for i in indizes:
                raus.append({"art": "geist", "pos_id": pid, "inst": inst,
                             "zeilen": [i], "behalten": None})
        elif len(indizes) > 1:
            # DOPPELVERKAUF: die erste Ausstiegsnotiz fuehrt.
            for i in indizes[1:]:
                raus.append({"art": "doppelverkauf", "pos_id": pid,
                             "inst": inst, "zeilen": [i],
                             "behalten": indizes[0]})
    return raus, ohne_kennung


def lies(pfad):
    if not os.path.exists(pfad):
        return [], []
    with open(pfad, encoding="utf-8", newline="") as f:
        zeilen = list(csv.reader(f))
    return (zeilen[:1], zeilen[1:]) if zeilen else ([], [])


def schreibe(pfad, kopf, daten):
    """CSV mit CRLF und OHNE BOM - die Form, die `spur_buch.journal()`
    erzeugt und die `spiegelstand` byteweise gegen Q: vergleicht.

    `kopf` ist eine Liste mit der Kopfzeile (sie kommt aus `lies()`).
    """
    out = io.StringIO(newline="")
    w = csv.writer(out)
    w.writerow(kopf[0] if kopf else [])
    w.writerows(daten)
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        f.write(out.getvalue())


def stempel():
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def pfade(stufe):
    """Die zwei Dateien einer Stufe (Suffix wie `risikostufe.datei_fuer`)."""
    s = "" if stufe == "basis" else "." + stufe
    return (os.path.join(HIER, "handelsjournal%s.csv" % s),
            os.path.join(HIER, "zustand%s.json" % s))


def lade_zustand(pfad):
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


# --- Lauf ------------------------------------------------------------------

def lauf(stufe, anwenden=False):
    jp, zp = pfade(stufe)
    if not os.path.exists(jp) or not os.path.exists(zp):
        print("Stufe %s: Journal oder Zustand fehlt (%s) - uebersprungen."
              % (stufe, jp))
        return 0
    kopf, daten = lies(jp)
    z = lade_zustand(zp)
    raus, ohne_kennung = befunde(daten, kopf, z.get("positionen"))

    print("Stufe %s: %d Befund(e), %d Verkaufszeile(n) ohne pos_id "
          "(Altjournal, nicht zuordenbar, nicht angefasst)"
          % (stufe, len(raus), ohne_kennung))
    for b in raus:
        print("  %-14s %-24s inst=%-8s Zeile %s -> verworfen"
              % (b["art"], b["pos_id"], b["inst"],
                 ", ".join(str(i + 2) for i in b["zeilen"])))
    if not raus:
        print("  nichts zu tun (idempotent).")
        return 0
    if not anwenden:
        print("  VORSCHAU - nichts geschrieben. Mit --anwenden ausfuehren.")
        return 0

    st = stempel()
    shutil.copy2(jp, jp.replace(".csv", ".bak-%s.csv" % st))
    shutil.copy2(zp, zp.replace(".json", ".bak-%s.json" % st))

    weg = sorted(i for b in raus for i in b["zeilen"])
    wegset = set(weg)
    behalten = [zeile for i, zeile in enumerate(daten) if i not in wegset]
    with open(os.path.join(HIER, VERWORFEN % st), "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(kopf[0] if kopf else [])
        for i in weg:
            w.writerow(daten[i])
    schreibe(jp, kopf, behalten)

    # Vermerk im Zustand. `letzter_lauf` bleibt unberuehrt.
    z.setdefault("buch_reconciliation", []).append(
        {"zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "grund": "doppelbuchung aufgeloest (T-356)",
         "verworfen": [{"art": b["art"], "pos_id": b["pos_id"],
                        "inst": b["inst"], "zeilen": len(b["zeilen"]),
                        "behalten": b["behalten"]} for b in raus]})
    atomar.schreibe_json(zp, z)

    # Bedingung 4: das Journal ist kuerzer geworden, Q: muss mitziehen.
    ziel, hinweis = None, None
    try:
        with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
            ziel = json.load(f).get("journal_zweitziel")
    except (OSError, ValueError) as e:
        hinweis = "wachen.json unlesbar: %s" % e
    if ziel:
        ok, info = wp.spiegele_journal([jp, zp], ziel)
        print("  Spiegelung nach %s: %s"
              % (ziel, "ok" if ok else "FEHLER " + str(info)))
        if not ok and hinweis is None:
            hinweis = str(info)

    kopf2, daten2 = lies(jp)
    rest, ohne_rest = befunde(daten2, kopf2, lade_zustand(zp).get("positionen"))
    print("\nGeschrieben: %d Zeile(n) nach %s"
          % (len(weg), os.path.basename(VERWORFEN % st)))
    if hinweis:
        print("Achtung: %s" % hinweis)
    print("Gegenprobe: %d Befund(e) uebrig (muss 0 sein), %d Verkaufszeile(n) "
          "ohne pos_id." % (len(rest), ohne_rest))
    return 0 if not rest else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Eine Aussage je Ausstieg (T-356, Vorschau Standard)")
    ap.add_argument("--anwenden", action="store_true", help="wirklich schreiben")
    ap.add_argument("--stufe", choices=STUFEN, default=None,
                    help="nur diese Risikostufe (Vorgabe: alle drei)")
    ap.add_argument("--ordner", default=None,
                    help="Spur-Ordner (Vorgabe: Verzeichnis des Skripts)")
    a = ap.parse_args(argv)
    if a.ordner:
        _setze_ordner(a.ordner)
    rc = 0
    for s in ((a.stufe,) if a.stufe else STUFEN):
        rc |= lauf(s, anwenden=a.anwenden)
    return rc


if __name__ == "__main__":
    sys.exit(main())