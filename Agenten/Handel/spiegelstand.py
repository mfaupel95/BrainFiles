"""Spiegelstand der Handelsspuren (Bedingung 4) - lesend, ohne Netz.

Ein `journal_zweitziel` in wachen.json ist eine Absicht: kopiert wird erst im
Zyklus. Dieses Modul vergleicht je Spur die Originale mit den Kopien
BYTE-GENAU (wie `cmp`) und liest daneben den Vermerk aus zustand.json
(`journal_zweitziel_ok` / `_info`) sowie das Alter des Herzschlags.

Zwei Verbraucher, eine Rechnung:

  * `tagesbericht.py` - eine Zeile im Abendbericht (Funktion `kurz()`).
  * Systempruefung, Block 11 - Aufruf als Skript, Tabelle + Rueckgabecode.

Aufruf (Systempruefung, von Hand):

    python spiegelstand.py [--handel ORDNER] [--stunden N]

Rueckgabecode 0 = jede Spur, die der Dauerlauf faehrt, hat ein Ziel und ist
byte-gleich; 1 = mindestens eine Abweichung. Spuren mit `wachen.json`, die
nicht in `dauerlauf.SPUREN` stehen (orb: Altbestand), werden mitgeprueft,
aber gekennzeichnet und nicht gezaehlt. kraken stand bis zum 14.09.2026 in
dieser Liste - seit es der Dauerlauf fuehrt, wird es wie jede andere Spur
gezaehlt.
Das Modul schreibt nichts.
"""

import argparse
import ast
import csv
import json
import os
import time
from datetime import datetime, timezone

HANDEL = os.path.dirname(os.path.abspath(__file__))
DATEIEN = ("handelsjournal.csv", "zustand.json")
# Zusatzdateien je Spur. Der Vergleich ist derselbe (byte-genau), aber eine
# Datei, die nur EINE Spur mitbringt, darf die anderen nicht abweichend
# machen. spiegel fuehrt das Ablehnungsprotokoll - warum Kandidaten NICHT
# gekauft wurden. Es gehoert wie das Journal ausser Haus: faellt die Platte
# aus, fehlt sonst genau die Begruendung, die man spaeter braucht.
ZUSATZ = {"spiegel": ("ablehnungen.csv",)}


def lade(pfad):
    try:
        with open(pfad, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def gleich(a, b):
    """Byte-Vergleich - ein Zeilenende- oder Reihenfolgeunterschied zaehlt."""
    try:
        with open(a, "rb") as fa, open(b, "rb") as fb:
            return fa.read() == fb.read()
    except OSError:
        return False


def zeilen(pfad):
    """Datenzeilen des Journals (ohne Kopfzeile); None, wenn nicht lesbar."""
    try:
        with open(pfad, newline="", encoding="utf-8") as f:
            return max(0, sum(1 for _ in csv.reader(f)) - 1)
    except OSError:
        return None


def alter_minuten(zeitstempel):
    if not zeitstempel:
        return None
    try:
        t = datetime.fromisoformat(str(zeitstempel).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).total_seconds() / 60


def spuren_im_lauf(handel=HANDEL):
    """Die Schluessel von `SPUREN` aus dauerlauf.py - per ast, nicht per import.

    Das Modul zu importieren zieht die halbe Handel-Umgebung; gelesen wird nur
    das Dict-Literal (die Werte enthalten os.path.join, deshalb nur die
    Schluessel). None, wenn die Datei fehlt oder nicht lesbar ist - dann gilt
    jede Spur mit wachen.json als relevant (kein stiller Freibrief).
    """
    try:
        baum = ast.parse(open(os.path.join(handel, "dauerlauf.py"),
                              encoding="utf-8").read())
    except (OSError, SyntaxError):
        return None
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Assign) and any(
                isinstance(z, ast.Name) and z.id == "SPUREN"
                for z in knoten.targets):
            if not isinstance(knoten.value, ast.Dict):
                return None
            namen = {s.value for s in knoten.value.keys
                     if isinstance(s, ast.Constant) and isinstance(s.value, str)}
            return namen or None
    return None


def spur_zeile(handel, spur):
    """Ein Pruefergebnis je Spur: Ziel, Kopiestand, Herzschlag, Journalzeilen.

    Verglichen werden die zwei Pflichtdateien plus die Zusatzdateien DIESER
    Spur (ZUSATZ). Eine fehlende Zusatzdatei liest sich wie ein Unterschied -
    das ist gewollt: sie wird im selben Zyklus mitgespiegelt, in dem sie
    entsteht, also muss sie auf beiden Seiten liegen.
    """
    ordner = os.path.join(handel, spur)
    w = lade(os.path.join(ordner, "wachen.json")) or {}
    z = lade(os.path.join(ordner, "zustand.json")) or {}
    ziel = w.get("journal_zweitziel")
    ziel = ziel.replace("\\", os.sep) if isinstance(ziel, str) else None
    alter = alter_minuten(z.get("letzter_lauf"))
    anzahl = zeilen(os.path.join(ordner, "handelsjournal.csv"))

    if not ziel:
        return {"spur": spur, "stand": "kein Ziel", "grund": "journal_zweitziel leer",
                "ziel": None, "alter": alter, "zeilen": anzahl}
    if not os.path.isdir(ziel):
        return {"spur": spur, "stand": "Ziel fehlt", "grund": "Ordner nicht erreichbar",
                "ziel": ziel, "alter": alter, "zeilen": anzahl}

    dateien = DATEIEN + ZUSATZ.get(spur, ())
    abweichungen = [n for n in dateien
                    if not gleich(os.path.join(ordner, n), os.path.join(ziel, n))]
    return {"spur": spur,
            "stand": "gleich" if not abweichungen else "ABWEICHUNG",
            "grund": ", ".join(abweichungen) if abweichungen else
                     (z.get("journal_zweitziel_info") or ""),
            "ziel": ziel, "alter": alter, "zeilen": anzahl,
            "vermerk": z.get("journal_zweitziel_ok")}


def stand(handel=HANDEL, stunden=30.0):
    """Alle Spuren pruefen. Schluessel: spuren, geprueft, abweichend, ausserhalb,
    alt (Herzschlag ueber der Grenze), spurenliste."""
    alle = []
    if not os.path.isdir(handel):
        return {"spuren": [], "geprueft": 0, "abweichend": [], "ausserhalb": [],
                "alt": [], "handel": handel, "im_lauf_lesbar": False,
                "fehler": "Ordner nicht erreichbar"}
    alle = sorted(d for d in os.listdir(handel)
                  if os.path.isfile(os.path.join(handel, d, "wachen.json")))
    im_lauf = spuren_im_lauf(handel)
    ergebnis = {"spuren": [], "geprueft": 0, "abweichend": [], "ausserhalb": [],
                "alt": [], "handel": handel, "im_lauf_lesbar": im_lauf is not None}
    for spur in alle:
        e = spur_zeile(handel, spur)
        im_dienst = im_lauf is None or spur in im_lauf
        if not im_dienst:
            ergebnis["ausserhalb"].append(spur)
            note = "[nicht in dauerlauf.SPUREN]"
            e["grund"] = (e["grund"] + "  " + note) if e["grund"] else note
        else:
            ergebnis["geprueft"] += 1
            if e["stand"] != "gleich":
                ergebnis["abweichend"].append(spur)
            if e["alter"] is not None and e["alter"] > stunden * 60:
                ergebnis["alt"].append((spur, e["alter"]))
        ergebnis["spuren"].append(e)
    return ergebnis


def kurz(e):
    """Eine Zeile fuer den Tagesbericht - nie eine Behauptung ohne Deckung."""
    if e.get("fehler"):
        return "nicht geprueft: %s" % e["fehler"]
    if not e["spuren"]:
        return "keine Spur mit wachen.json gefunden"
    if e["geprueft"] == 0 and e["ausserhalb"]:
        return "keine Spur im Dauerlauf gefunden (%s ausserhalb)" % ", ".join(e["ausserhalb"])
    if e["abweichend"]:
        return ("%d von %d Spuren ABWEICHEND (%s) - Q: pruefen"
                % (len(e["abweichend"]), e["geprueft"], ", ".join(e["abweichend"])))
    if not e["im_lauf_lesbar"]:
        return ("%d Spuren geprueft, alle byte-gleich (SPUREN nicht lesbar - "
                "auch Spuren ausserhalb des Dauerlaufs gezaehlt)" % e["geprueft"])
    return "%d von %d Spuren byte-gleich (Q:)" % (e["geprueft"], e["geprueft"])


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--handel", default=HANDEL,
                   help="Handel-Verzeichnis (Vorgabe: dieses Verzeichnis)")
    p.add_argument("--stunden", type=float, default=30.0,
                   help="ab wann der Herzschlag als alt gemeldet wird")
    a = p.parse_args()

    e = stand(a.handel, a.stunden)
    if e.get("fehler"):
        print("Spiegelstand nicht pruefbar: %s (%s)" % (e["fehler"], a.handel))
        return 1
    if not e["spuren"]:
        print("keine Spur mit wachen.json unter %s" % a.handel)
        return 1

    if not e["im_lauf_lesbar"]:
        print("Hinweis: SPUREN aus dauerlauf.py nicht lesbar - alle Spuren mit "
              "wachen.json werden geprueft.")
    print("Spiegelstand Bedingung 4 - %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Handel: %s" % a.handel)
    print()
    print("%-10s %-12s %7s %7s  %s" % ("Spur", "Stand", "Zeilen", "Alter",
                                       "Ziel / Grund"))
    for x in e["spuren"]:
        alter = "--" if x["alter"] is None else "%.0f min" % x["alter"]
        anzahl = "--" if x["zeilen"] is None else str(x["zeilen"])
        print("%-10s %-12s %7s %7s  %s%s" % (
            x["spur"], x["stand"], anzahl, alter, x["ziel"] or "--",
            "   [%s]" % x["grund"] if x["grund"] else ""))
        if x["alter"] is not None and x["spur"] not in e["ausserhalb"] \
                and x["alter"] > a.stunden * 60:
            print("%-10s   Hinweis: Herzschlag %.0f min alt (> %.0f h) - laeuft die "
                  "Spur ueberhaupt?" % ("", x["alter"], a.stunden))
    print()
    print("Ergebnis: %s" % kurz(e))
    if e["ausserhalb"]:
        print("ausserhalb des Dauerlaufs mitgeprueft: %s" % ", ".join(e["ausserhalb"]))
    return 0 if not e["abweichend"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
