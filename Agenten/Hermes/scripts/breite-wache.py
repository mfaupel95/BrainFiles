"""Waechter fuer die Krypto-Marktbreite (Anteil der Paare ueber der EMA200).

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut**, es wird nichts gesendet (Watchdog-Muster wie bus-waechter.py).

WARUM ES IHN GIBT
-----------------
Am 25.09.2026 lag die Breite bei 100 % - alle 29 gemessenen Paare ueber ihrer
EMA200. Das ist eine spaete Signatur, kein Kaufgrund: es gibt keinen Nachzuegler
mehr, in den Geld rotieren koennte. Ob die Breite SCHRUMPFT, war damals nicht
belegbar - es gab genau EINEN Messpunkt. `Werkzeuge/breite.py --merken` schreibt
die Reihe; dieser Waechter misst taeglich und meldet nur, was sich AENDERT:

    - die Stufe faellt (ok -> achtung -> warnung) oder erholt sich wieder
    - ein Paar faellt NEU unter seine EMA200 (die Fruehwarnzeichen)
    - die Messung deckt zu wenig Paare ab (dann ist die Zahl selbst kaputt)

WAS ES NICHT TUT
----------------
Es handelt nicht, es empfiehlt nicht und es schreibt in keine Spur. Es misst,
haengt an die Reihe an und meldet nur Aenderungen - sonst waere "100 %" eine
taegliche Nachricht, die niemand mehr liest.

Aufruf:
    python Agenten/Hermes/scripts/breite-wache.py             # echter Waechter
    python Agenten/Hermes/scripts/breite-wache.py --alle      # Lage immer zeigen
    python Agenten/Hermes/scripts/breite-wache.py --schwelle 5   # Alarmrichtung
"""

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                      # Agenten/Hermes/scripts/ -> BrainFiles
WERKZEUG = WURZEL / "Agenten" / "Werkzeuge" / "breite.py"
MERKDATEI = WURZEL / "Agenten" / "Hermes" / "cache" / "breite-wache.json"

STUFEN = ((80.0, "ok"), (60.0, "achtung"), (0.0, "warnung"))
DECKUNG_MIN = 0.90                            # weniger = Messung unbrauchbar
# Punkte, um die die Breite gegenueber der letzten MELDUNG fallen muss. 10 ist
# bewusst groesser als das Tagesrauschen: ein Rueckgang in Haeppchen von 2-3
# Punkten pro Tag wird so nach wenigen Tagen EINE Nachricht statt jeden Tag eine.
RUCKGANGS_PP = 10.0


def lade_werkzeug():
    """breite.py per Pfad laden - es ist kein installiertes Modul."""
    spec = importlib.util.spec_from_file_location("breite_werkzeug",
                                                  str(WERKZEUG))
    if spec is None or spec.loader is None:
        return None
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def stufe(breite):
    if breite is None:
        return "unbekannt"
    for grenze, name in STUFEN:
        if breite >= grenze:
            return name
    return "warnung"


def _merker():
    try:
        with open(MERKDATEI, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _merke(stand):
    try:
        MERKDATEI.parent.mkdir(parents=True, exist_ok=True)
        with open(MERKDATEI, "w", encoding="utf-8", newline="\n") as f:
            json.dump(stand, f, ensure_ascii=False, indent=1, sort_keys=True)
    except OSError:
        pass                                   # Merken ist Komfort


def zeilen(m, merker, schwelle=None):
    """Meldungen bauen. Rueckgabe: (zeilen, neuer_merker)."""
    b = merker.get("breite")
    s_alt = merker.get("stufe") or ("ok" if b is not None else None)
    s_neu = stufe(m["breite"])
    unter = [x["inst"] for x in m["unter"]]
    unter_alt = list(merker.get("unter") or [])
    neu_unter = [i for i in unter if i not in unter_alt]

    raus = []
    deckung = (m["n_gesamt"] / len(m["grundgesamtheit"])
               if m.get("grundgesamtheit") else 0.0)
    if deckung < DECKUNG_MIN:
        raus.append("Messung unvollstaendig: nur %d von %d Paaren messbar"
                    % (m["n_gesamt"], len(m.get("grundgesamtheit") or [])))
        for o in m["offen"][:6]:
            raus.append("  %s: %s" % (o["inst"], o["grund"]))

    stufenwechsel = (s_neu != s_alt)
    # Die Pruefschwelle gehoert IN die Entscheidung, nicht dahinter: sonst
    # schluckt der Stille-Ausstieg sie, und ein dauerhaft niedriger Wert wird
    # nie gemeldet. Gegen Dauerrauschen wird der Zustand gemerkt - gemeldet
    # wird der UEBERGANG unter die Schwelle, nicht jeder Tag darunter.
    unter_schwelle = (schwelle is not None and m["breite"] is not None
                      and m["breite"] < schwelle)
    neu_schwelle = unter_schwelle and not merker.get("schwelle_aktiv")
    # RUCKGANGSMELDUNG (25.09.2026): innerhalb der Stufe "ok" (>= 80 %) war die
    # Wache BLIND - 100 % auf 81 % haette keine Nachricht erzeugt, obwohl genau
    # das "die Breite schrumpft" ist. Verglichen wird gegen den letzten
    # GEMELDETEN Wert, nicht gegen den letzten Messwert: sonst waeren
    # Rueckgaenge in Haeppchen von 2-3 Punkten am Tag nie sichtbar. Nach einer
    # Meldung setzt der Bezug neu auf - so kostet ein Rueckgang EINE Nachricht.
    bezug = merker.get("gemeldet_breite")
    if bezug is None:
        bezug = b
    rueckgang = (bezug is not None and m["breite"] is not None
                 and (bezug - m["breite"]) >= RUCKGANGS_PP)
    if (not stufenwechsel and not neu_unter and not raus and not neu_schwelle
            and not rueckgang):
        return [], {"breite": m["breite"], "stufe": s_neu, "unter": unter,
                    "gemeldet_breite": bezug,
                    "schwelle_aktiv": unter_schwelle, "ts": m["ts"]}

    if stufenwechsel:
        namen = [x[1] for x in STUFEN]
        if s_alt not in namen:
            raus.insert(0, "Krypto-Breite: erste Messung - %.1f %% (%s)"
                        % (m["breite"], s_neu))
        else:
            # STUFEN ist absteigend notiert: kleinerer Index = bessere Stufe.
            gunstig = namen.index(s_neu) < namen.index(s_alt)
            richtung = "erholt" if gunstig else "gefallen"
            raus.insert(0, "Krypto-Breite %s: %.1f %% (vorher %s)"
                        % (richtung, m["breite"],
                           "%.1f %%" % b if b is not None else "unbekannt"))
    else:
        grund = "Breite faellt" if rueckgang else "aber neue Abwaertskreuze"
        raus.insert(0, "Krypto-Breite %.1f %% - Stufe unveraendert (%s), %s:"
                    % (m["breite"], s_neu, grund))
    if rueckgang:
        raus.append("Rueckgang um %.1f Punkte seit der letzten Meldung "
                    "(%.1f %% -> %.1f %%)"
                    % (bezug - m["breite"], bezug, m["breite"]))
    if neu_schwelle:
        raus.append("unter der Pruefschwelle von %.0f %% (%.1f %%)"
                    % (schwelle, m["breite"]))

    if neu_unter:
        raus.append("Neu unter der EMA200:")
        abstand = {x["inst"]: x["abstand"] for x in m["unter"]}
        for i in neu_unter:
            raus.append("  %s  %+.2f %% unter der EMA200" % (i, abstand[i]))
    elif unter:
        raus.append("Weiter unter der EMA200: " + ", ".join(unter))

    raus.append("%d von %d Paaren ueber der EMA200, Kerze %s, gemessen %s"
                % (m["n_ueber"], m["n_gesamt"], m["kerze"], m["ts"]))
    return raus, {"breite": m["breite"], "stufe": s_neu, "unter": unter,
                  "gemeldet_breite": m["breite"],
                  "schwelle_aktiv": unter_schwelle, "ts": m["ts"]}


HEIL_TAGE = 5                                 # so weit zurueck wird geheilt
ABGLEICH_TOLERANZ = 0.5                       # Punkte, ab denen der Abgleich redet


def _luecken_schliessen(w, m):
    """Fehlende Kerzentage nachrechnen - und die zwei Wege gegenpruefen.

    Ein Tag ohne Zeile entsteht, wenn der Rechner aus war. `fuellen` rechnet ihn
    aus DENSELBEN Kerzen nach, die gerade gemessen wurden (`mit_verlauf`), der
    zweite Abruf entfaellt also. Gemeldet wird nur, wenn wirklich etwas fehlte
    oder wenn Live-Weg und Nachrechnung auseinanderlaufen - Letzteres waere der
    Beweis, dass beide Wege NICHT dieselbe Rechenregel benutzen.

    Geschrieben wird auch dann, wenn nichts gemeldet wird: die Wache heilt
    still, und leere Ausgabe heisst weiterhin nur "nichts zu sagen".
    """
    if not m.get("_verlauf"):
        return []
    try:
        r = w.fuellen(tage=HEIL_TAGE, verlauf_je_inst=m["_verlauf"])
    except Exception as f:                      # noqa: BLE001
        return ["Reihe nicht nachgerechnet (%s)" % str(f)[:80]]
    raus = []
    if r["gefuellt"]:
        raus.append("Reihe nachgefuellt: %d Kerzentag(e) aus der vorhandenen "
                    "Geschichte" % r["gefuellt"])
    for a in r["abgleich"]:
        if abs(a["diff"]) > ABGLEICH_TOLERANZ:
            raus.append("Abgleich %s: gemessen %.1f %%, nachgerechnet %.1f %% "
                        "(%+.1f pp)"
                        % (a["kerze"], a["live"], a["nachgerechnet"], a["diff"]))
    return raus[:4]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--alle", action="store_true",
                   help="die Lage auch ohne Aenderung nennen")
    p.add_argument("--schwelle", type=float, default=None,
                   help="zusaetzlich melden, wenn die Breite unter X %% liegt")
    a = p.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not WERKZEUG.exists():
        print("breite-wache: %s fehlt - nicht gemessen" % WERKZEUG)
        return 0
    w = lade_werkzeug()
    if w is None:
        print("breite-wache: breite.py nicht ladbar")
        return 0

    try:
        m = w.messen(mit_verlauf=True)
    except Exception as f:                      # noqa: BLE001
        print("breite-wache: Messung abgebrochen (%s)" % str(f)[:120])
        return 0

    m["grundgesamtheit"] = list(w.PAARE)
    if m["n_gesamt"]:
        try:
            w.merken(m)
        except OSError as f:
            print("breite-wache: Reihe nicht schreibbar (%s)" % f)

    heil = _luecken_schliessen(w, m)

    merker = _merker()
    raus, neu = zeilen(m, merker, a.schwelle)
    raus += heil
    _merke(neu)

    if raus:
        print("Krypto-Marktbreite (EMA200, Tageskerzen):")
        for z in raus:
            print("  " + z if not z.startswith(" ") else z)
        print("Reihe: Agenten/Werkzeuge/breite.py --reihe")
    elif a.alle:
        print("Breite %.1f %% (%d von %d ueber der EMA200), Stufe %s, keine "
              "Aenderung seit %s" % (m["breite"], m["n_ueber"], m["n_gesamt"],
                                     neu["stufe"], (merker.get("ts") or "-")[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())