"""Stille Spuren finden - fuer alle Spuren im Dauerlauf, auch kuenftige.

Eine stille Spur ist nicht automatisch kaputt. Das Werkzeug unterscheidet
die Faelle, die man ohne Nachsehen verwechselt:

  WARTET       Zustand frisch, noch kein Buch - die Spur hatte schlicht kein
               Signal. Gesund; jede neue Spur startet hier.
  HAELT        offene Positionen, kein Ausstieg faellig - Stop/Ziel/Frist
               sind noch nicht erreicht. Gesund.
  UEBERFAELLIG offene Position, deren Frist abgelaufen ist, ohne dass ein
               Ausstieg gebucht wurde. Das ist ein Befund.
  TOT          Zustand veraltet (Spur laeuft nicht mehr) oder Ordner fehlt.
  LAEUFT       hat gebuchte Ausstiege.

Die Spurliste kommt aus dauerlauf.SPUREN, nicht aus einer eigenen Liste -
eine neue Spur erscheint dadurch von selbst, ohne dieses Skript zu aendern.
Die Einstiegs-/Ausstiegswoerter kommen aus stoerungen.py, der einzigen
Stelle, die das im Haus definiert (orbk fuehrt keine aktion-Spalte, sondern
ausgang - stoerungen.teile() kennt diese Eigenheit bereits).

Aufruf:
    python stille_spuren.py            Bericht auf die Konsole
    python stille_spuren.py --kurz     nur die Zeilen, die auffallen
    python stille_spuren.py --wache    leere Ausgabe, wenn alles gesund ist
"""
import argparse
import ast
import datetime
import importlib.util
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
JETZT = datetime.datetime.now(datetime.timezone.utc)

# Zustand aelter als das heisst: die Spur laeuft nicht mehr mit.
TOT_STUNDEN = 6.0


def _modul(name, datei):
    """Ueber den PFAD laden, nicht ueber sys.path: mehrere Spuren fuehren
    gleichnamige Module (handeln.py, scan.py), und ein sys.path-Eintrag
    wuerde das falsche erwischen."""
    spec = importlib.util.spec_from_file_location(name, datei)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


stoerungen = _modul("stoerungen_fuer_stille",
                    os.path.join(HIER, "stoerungen.py"))


def spuren():
    """(name, ordner) je Spur aus dauerlauf.SPUREN.

    Wird aus dem Quelltext gelesen (AST) statt importiert: dauerlauf.py
    startet beim Import Prozesse. literal_eval scheitert, weil der Wert
    os.path.join-Aufrufe enthaelt - deshalb Schluessel und 'ordner' einzeln
    aus dem Baum ziehen.
    """
    quelle = ""
    with open(os.path.join(HIER, "dauerlauf.py"), encoding="utf-8") as f:
        quelle = f.read()
    for knoten in ast.walk(ast.parse(quelle)):
        if not isinstance(knoten, ast.Assign):
            continue
        if not any(isinstance(z, ast.Name) and z.id == "SPUREN"
                   for z in knoten.targets):
            continue
        if not isinstance(knoten.value, ast.Dict):
            continue
        raus = []
        for schluessel, wert in zip(knoten.value.keys, knoten.value.values):
            name = getattr(schluessel, "value", None)
            if name is None or not isinstance(wert, ast.Dict):
                continue
            ordner = name
            for k, v in zip(wert.keys, wert.values):
                if getattr(k, "value", None) == "ordner":
                    ordner = getattr(v, "value", None) or ordner
            raus.append((name, ordner))
        return raus
    return []


def _zeit(wert):
    if not wert:
        return None
    try:
        t = datetime.datetime.fromisoformat(str(wert))
    except Exception:
        return None
    return t.replace(tzinfo=datetime.timezone.utc) if t.tzinfo is None else t


def _stunden_her(wert):
    t = _zeit(wert)
    return None if t is None else (JETZT - t).total_seconds() / 3600


def _zustand(ordner):
    """Den Zustand mit dem JUENGSTEN `letzter_lauf` liefern.

    Gelesen werden BEIDE Staende: das Papierbuch (zustand.json) und das
    Live-Buch (zustand.live.json). Eine Spur, die live laeuft, schreibt den
    Papierzweig nicht mehr - sie wurde sonst als "TOT" gemeldet, obwohl sie
    alle 15 Minuten arbeitete (23.09.2026, moondev_marktlage; dieselbe Falle
    wie beim Herzschlag, siehe Wiki/Handel/Gates-und-Freigabe.md).
    Fehlt jede Datei, gibt es keinen Zustand - das bleibt "TOT".
    """
    staende = []
    for name in ("zustand.json", "zustand.live.json"):
        p = os.path.join(ordner, name)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                staende.append(json.loads(f.read()))
        except Exception:
            continue
    if not staende:
        return None
    return max(staende, key=lambda z: (z or {}).get("letzter_lauf") or "")


def _positionen(z):
    """Positionen liegen je nach Spur als Liste oder als Dict (orbk fuehrt
    genau einen Platz)."""
    p = z.get("positionen") if z else None
    if isinstance(p, dict):
        return [p] if p else []
    return list(p or [])


def _frist_ueberfaellig(pos):
    """Positionen, deren Frist abgelaufen ist. Feldname variiert je Spur."""
    raus = []
    for p in pos:
        for feld in ("frist", "frist_bis", "gueltig_bis"):
            t = _zeit(p.get(feld))
            if t is not None and t <= JETZT:
                raus.append((p.get("symbol") or p.get("inst")
                             or p.get("token") or p.get("paar") or "?",
                             round((JETZT - t).total_seconds() / 3600, 1)))
                break
    return raus


def pruefe(name, ordner_name):
    ordner = os.path.join(HIER, ordner_name)
    if not os.path.isdir(ordner):
        return {"spur": name, "lage": "TOT", "text": "Ordner fehlt",
                "auffaellig": True}

    z = _zustand(ordner)
    alter = _stunden_her((z or {}).get("letzter_lauf")
                         or (z or {}).get("letzter_zyklus"))
    pos = _positionen(z)

    try:
        echt, stoer = stoerungen.teile(ordner_name)
    except Exception:
        echt, stoer = [], []
    ausstiege = len(echt) + len(stoer)

    if z is None:
        return {"spur": name, "lage": "TOT", "text": "kein Zustand",
                "auffaellig": True}

    if alter is not None and alter > TOT_STUNDEN:
        return {"spur": name, "lage": "TOT",
                "text": "Zustand %.1f h alt" % alter, "auffaellig": True}

    faellig = _frist_ueberfaellig(pos)
    if faellig:
        namen = ", ".join("%s (%+.1f h)" % (s, h) for s, h in faellig[:3])
        return {"spur": name, "lage": "UEBERFAELLIG",
                "text": "%d Position(en) ueber der Frist: %s"
                        % (len(faellig), namen), "auffaellig": True}

    if ausstiege == 0 and not pos:
        return {"spur": name, "lage": "WARTET",
                "text": "kein Signal bisher (Zustand %s)"
                        % ("frisch" if alter is not None
                           and alter <= TOT_STUNDEN else "?"),
                "auffaellig": False}

    if ausstiege == 0 and pos:
        return {"spur": name, "lage": "HAELT",
                "text": "%d Position(en), noch kein Ausstieg faellig"
                        % len(pos), "auffaellig": False}

    return {"spur": name, "lage": "LAEUFT",
            "text": "%d Ausstiege (%d echt, %d Stoerung), %d offen"
                    % (ausstiege, len(echt), len(stoer), len(pos)),
            "auffaellig": False}


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--kurz", action="store_true",
                   help="nur auffaellige Zeilen")
    p.add_argument("--wache", action="store_true",
                   help="leere Ausgabe, wenn nichts auffaellt (fuer Cron)")
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ergebnisse = [pruefe(n, o) for n, o in spuren()]
    auffaellig = [e for e in ergebnisse if e["auffaellig"]]

    if a.wache:
        if not auffaellig:
            return 0
        print("Stille Spuren: %d auffaellig" % len(auffaellig))
        for e in auffaellig:
            print("  %-24s %-12s %s" % (e["spur"], e["lage"], e["text"]))
        return 0

    zeigen = auffaellig if a.kurz else ergebnisse
    if not zeigen:
        print("Keine auffaellige Spur (%d geprueft)." % len(ergebnisse))
        return 0

    rang = {"TOT": 0, "UEBERFAELLIG": 1, "WARTET": 2, "HAELT": 3, "LAEUFT": 4}
    print("%-24s %-13s %s" % ("Spur", "Lage", "Befund"))
    print("-" * 92)
    for e in sorted(zeigen, key=lambda x: (rang.get(x["lage"], 9), x["spur"])):
        print("%-24s %-13s %s" % (e["spur"], e["lage"], e["text"]))

    zahl = {}
    for e in ergebnisse:
        zahl[e["lage"]] = zahl.get(e["lage"], 0) + 1
    print("\n%d Spuren: %s" % (len(ergebnisse), ", ".join(
        "%s %d" % (k, v) for k, v in sorted(zahl.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
