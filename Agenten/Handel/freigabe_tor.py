"""Das Gebuehren-Tor: eine Spur wird erst live, wenn die Zahl es traegt.

WARUM EIN TOR UND KEIN SETZER
------------------------------
`freigabe.erfuellt` bleibt der von Hand gesetzte Haken von Max. Das Tor
ist eine ZUSAETZLICHE Sperre in derselben Kette, und es rechnet. Es setzt
nichts - es verweigert. Der Unterschied ist der ganze Punkt: ein Werkzeug,
das Freigaben VERGIBT, ist eine Behauptung; eins, das sie VERWEIGERT,
kann nur falsch liegen, indem es zu streng ist, und das sieht man sofort.

DIE DREI BEDINGUNGEN
--------------------
1. `runden >= min_runden` (Vorgabe 30, vorher 8). Unter dreissig Runden
   ist die Streuung des Mittelwerts zu gross, um einen Edge von einer
   Glueckssträhne zu trennen. Der scanner hat 161 und trotzdem keinen Edge; eine
   Spur mit 16 Runden hat noch gar keinerlei.
2. `excess_nach_gebuehr > 0`, wobei `excess` die Basislinie schon
   abzieht: das Rundenergebnis MINUS "dasselbe Instrument einfach halten".
   Die Gebuehr kommt aus der wachen.json (`gebuehr_taker` ist der Anteil
   JE SEITE, eine Runde ist Kauf+Verkauf = doppelt). Ohne Basislinie gibt
   es keine Zahl, also keine Freigabe.
3. Konfidenz (seit 09.10.2026): die UNTERE Grenze des Netto-Excess muss
   positiv sein, `netto - z * std / sqrt(n) > 0`. `z` ist die Bonferroni-
   Korrektur fuer die Zahl der geprueften Spuren (einseitig, alpha 5 %
   durch K): wer aus 42 Spuren die mit positivem Mittel herausgreift,
   findet allein durch Zufall Gewinner. Fehlt `std_excess` im Auditstand
   (aelterer Lauf), entfaellt diese Bedingung bis zur naechsten Messung.
4. Out-of-Sample (seit 09.10.2026): der Netto-Excess muss in der fruehen UND
   der spaeten Haelfte der Runden positiv sein (je Haelfte mindestens
   `MIN_RUNDEN_HAELFTE`). Fehlen die Felder, entfaellt die Bedingung.
5. `trigger_modus == "signal"`. Eine Spur, die im 15-Minuten-Takt handelt,
   darf nicht live: sie wuerde Gebuehren zahlen, fuer die es keinen
   Edge gibt.

WAS DAS TOR MIT EINER SPUR MACHT, DIE ES NICHT GIBT
----------------------------------------------------
Nichts. Eine Spur ohne Auditrundlage ist nicht gesperrt, sondern
unbewiesen - sie wird gemeldet, und ihre Freigabe bleibt eine Entscheidung
von Max. Das Tor verweigert nie eine Spur, die es nicht kennt; das waere
ein Wächter, der wegen seiner eigenen Unkenntnis schweigt.

WOHER DIE ZAHLEN
----------------
`spur_audit.py --json` (T-322, aus der parallelen Sitzung). Die Auswertung
kommt aus EINEM Lauf und wird nicht je Spur neu gerechnet - sonst hinge
das Tor an einem Abruf, der beim Nachladen der Kerzen anders ausfaellt als
der Lauf von heute frueh. Die Merkdatei traegt den Zeitstempel des
Laufs; ein Tor ohne frischen Lauf ist nicht frisch und verweigert.
"""

import json
import os

HIER = os.path.dirname(os.path.abspath(__file__))
# Diese Datei liegt IN Agenten/Handel - `dirname(HIER)` waere Agenten/ und
# damit eine Ebene zu hoch. Derselbe Fehler wie in spur_buch (Handel ist
# dort eine Ebene tiefer). Der venv und der Audit liegen beide hier.
HANDEL = HIER
MERK = os.path.join(HANDEL, "cache", "freigabe-tor.json")
VENV = os.path.join(HANDEL, "scanner", ".venv", "Scripts", "python.exe")

MIN_RUNDEN = 30
MIN_RUNDEN_HAELFTE = 8        # so viele Runden braucht jede Haelfte, sonst keine Pruefung
ALPHA = 0.05                  # Familienfehler ueber alle geprueften Spuren
ALTER_MAX_S = 6 * 3600        # der Audit laeuft alle 6 Stunden

ERLAEUT = "Gebuehren-Tor: Excess nach Gebuehr positiv, genug Runden, Signal-Modus"


def _lade():
    try:
        with open(MERK, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def messen():
    """Den Audit einmal laufen lassen und die Zahlen merken.

    Schreibt NICHT in die Spuren - der einzige Schreibzugriff ist die
    Merkdatei, und sie ist reproduzierbar: sie entsteht aus einem Lauf
    heraus, dessen Werkzeug man nochmal starten kann.
    """
    import subprocess
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    try:
        p = subprocess.run([VENV, "spur_audit.py", "--json"], cwd=HANDEL,
                           capture_output=True, text=True, timeout=900, env=env)
        daten = json.loads(p.stdout)
    except Exception as e:                                   # noqa: BLE001
        return {}, "Audit nicht lesbar: %s" % str(e)[:120]
    if not isinstance(daten, list):
        return {}, "unerwartete Form aus spur_audit.py --json"
    import time
    stand = {"_zeit": time.time(), "spuren": {}}
    for d in daten:
        spur = d.get("spur")
        if not spur:
            continue
        stand["spuren"][spur] = {
            "n": int(d.get("n") or 0),
            "n_basis": int(d.get("basislinie_n") or 0),
            "n_excess": int(d.get("n_excess") or 0),
            "mean_excess": float(d.get("mean_excess") or 0.0),
            "std_excess": (None if d.get("std_excess") is None
                           else float(d["std_excess"])),
            "n_frueh": int(d.get("n_frueh") or 0),
            "n_spaet": int(d.get("n_spaet") or 0),
            "mean_excess_frueh": (None if d.get("mean_excess_frueh") is None
                                  else float(d["mean_excess_frueh"])),
            "mean_excess_spaet": (None if d.get("mean_excess_spaet") is None
                                  else float(d["mean_excess_spaet"])),
            "befunde": [str(b) for b in (d.get("befunde") or [])],
            "mean": float((d.get("roh") or {}).get("mean") or 0.0),
            "treffer": float((d.get("roh") or {}).get("treffer") or 0.0),
        }
    os.makedirs(os.path.dirname(MERK), exist_ok=True)
    with open(MERK, "w", encoding="utf-8") as fh:
        json.dump(stand, fh, ensure_ascii=False, indent=1)
    return stand, ""


def gebuehr_pro_runde(w):
    """Die Gebuehr EINES kompletten Ein- und Ausstiegs, in Prozent."""
    g = w.get("gebuehr_taker")
    if g is None:
        g = 0.001                      # OKX-Spot als sicherer Rueckfall
    return float(g) * 2.0 * 100.0


def pruefe(spur, w=None):
    """(erfuellt, gruende). Aufrufer haengt `gruende` an sperren_live."""
    if w is None:
        try:
            with open(os.path.join(HANDEL, spur, "wachen.json"), encoding="utf-8") as fh:
                w = json.load(fh)
        except (OSError, ValueError):
            return True, []              # keine Wache: nichts zu sperren
    stand = _lade()
    spuren = stand.get("spuren") or {}
    if spur not in spuren:
        # Kein Auditrundlage: nicht sperren, aber auch nicht fuer "gemessen"
        # halten. Das Tor schweigt ueber Spuren, die es nicht kennt.
        return True, []
    d = spuren[spur]
    geb = gebuehr_pro_runde(w)
    netto = d["mean_excess"] - geb
    gruende = []
    if d["n"] < MIN_RUNDEN:
        gruende.append("Gebuehren-Tor: %d Runden, brauche %d"
                       % (d["n"], MIN_RUNDEN))
    if d["n_basis"] < MIN_RUNDEN:
        gruende.append("Gebuehren-Tor: %d Runden mit Basislinie, brauche %d"
                       % (d["n_basis"], MIN_RUNDEN))
    if netto <= 0:
        gruende.append("Gebuehren-Tor: Excess %+.2f %% minus Gebuehr %.2f %% "
                       "= %+.2f %%" % (d["mean_excess"], geb, netto))
    std = d.get("std_excess")
    if std is not None and d.get("n_excess", 0) >= 2:
        from math import sqrt
        from statistics import NormalDist
        k = max(1, len(spuren))
        z = NormalDist().inv_cdf(1.0 - ALPHA / k)
        untere = netto - z * std / sqrt(d["n_excess"])
        if untere <= 0:
            gruende.append("Gebuehren-Tor: untere Konfidenzgrenze des Netto-"
                           "Excess %+.2f %% (z=%.2f bei %d Spuren, Std %.2f %%, "
                           "n=%d) - vom Zufall nicht zu trennen"
                           % (untere, z, k, std, d["n_excess"]))
    # Out-of-Sample (Halbierung): der Netto-Excess muss in der fruehen UND in
    # der spaeten Haelfte der Runden positiv sein. Ein Edge, der nur in einer
    # Haelfte steht, ist ein Zufalls- oder Regimebefund. Fehlen die Felder
    # (aelterer Auditstand) oder ist eine Haelfte zu klein, entfaellt die
    # Bedingung.
    mf, ms = d.get("mean_excess_frueh"), d.get("mean_excess_spaet")
    if (mf is not None and ms is not None
            and d.get("n_frueh", 0) >= MIN_RUNDEN_HAELFTE
            and d.get("n_spaet", 0) >= MIN_RUNDEN_HAELFTE):
        if mf - geb <= 0 or ms - geb <= 0:
            gruende.append("Gebuehren-Tor: Netto-Excess nicht in beiden "
                           "Haelften positiv (frueh %+.2f %%, spaet %+.2f %% "
                           "nach Gebuehr %.2f %%)" % (mf - geb, ms - geb, geb))
    # Die vierte Bedingung, und die wichtigste: eine Spur mit einem
    # BEFUND im Audit ist nicht gemessen, sondern beanstandet. Der scanner
    # haette die drei anderen Bedingungen mit +8,52 % Excess klar
    # bestanden - dabei traegt sein Audit den Befund "misst die Auswahl,
    # nicht die Spur" (87 von 161 Runden auf einem Instrument, uebernommener
    # Einstiegspreis). Ohne diese Zeile haette das Tor die groesste Zahl im
    # Haus abgesegnet.
    if d.get("befunde"):
        gruende.append("Gebuehren-Tor: Audit meldet %d Befund(e) - die Spur "
                       "ist beanstandet, nicht gemessen: %s"
                       % (len(d["befunde"]), "; ".join(d["befunde"])[:150]))
    if str(w.get("trigger_modus") or "").lower() != "signal":
        gruende.append("Gebuehren-Tor: Spur haelt nicht den Signal-Modus "
                       "(trigger_modus=%r)" % w.get("trigger_modus"))
    return (not gruende), gruende


def bericht():
    """Alle Spuren mit their verdict - fuer den Aufruf von Hand."""
    stand = _lade()
    if not stand:
        return "Kein Auditstand (%s). Erst messen: freigabe_tor.py --messen" % MERK
    zeilen = ["%-24s %5s %9s %8s %9s  %s"
              % ("Spur", "n", "Excess", "Geb", "netto", "Tor")]
    for spur in sorted(stand.get("spuren") or {}):
        d = stand["spuren"][spur]
        w = {}
        try:
            with open(os.path.join(HANDEL, spur, "wachen.json"), encoding="utf-8") as fh:
                w = json.load(fh)
        except (OSError, ValueError):
            pass
        geb = gebuehr_pro_runde(w)
        netto = d["mean_excess"] - geb
        ok, _ = pruefe(spur, w)
        zeilen.append("%-24s %5d %8.2f%% %7.2f%% %8.2f%%  %s"
                      % (spur, d["n"], d["mean_excess"], geb, netto,
                         "offen" if ok else "ZU"))
    return "\n".join(zeilen)


if __name__ == "__main__":
    import sys
    if "--messen" in sys.argv:
        stand, fehler = messen()
        print("Audit: %d Spuren, %s" % (len(stand.get("spuren") or {}),
                                        fehler or "ohne Fehler"))
    elif "--pruefe" in sys.argv:
        for name in sys.argv[2:]:
            ok, g = pruefe(name)
            print("%s: %s%s" % (name, "offen" if ok else "ZU",
                                "" if ok else "  " + "; ".join(g)))
    else:
        print(bericht())