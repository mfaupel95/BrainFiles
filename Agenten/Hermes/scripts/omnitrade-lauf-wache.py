"""Wache fuer den omnitrade-Demo-Lauf (`Werkstatt/omnitrade`).

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut** und es wird nichts gesendet (Watchdog-Muster wie ausserhaus-frist-wache.py
und dashboard-wache.py). Der Hermes-Scheduler laeuft am Gateway vorbei und
liefert direkt nach Telegram.

WARUM ES DIESE WACHE GIBT
-------------------------
Der OKX-Demo-Lauf schreibt laufend `status/live.json` (Schema 1, Zustand, PID,
Kerzen, Orders). Am 30.09.2026 gab es in zwei Stunden FUENF PIDs
(76116, 63732, 64440, 62416, 69800) - und nach jedem harten Ende blieb die
Statusdatei auf `"state": "running"` mit einer TOTEN PID stehen. Wer nur die
Datei liest, glaubt an laufenden Handel. Es gab keine Wache, die das gemeldet
haette (offener Punkt T-211).

WAS ES TUT
----------
Es fragt NICHT die Datei allein, sondern benutzt `Agenten/Handel/omnitrade_lauf.py`
- dort entscheiden ZWEI Zeugen dieselbe Frage (Statusdatei UND PID in der
Prozessliste). Die Datei existiert genau deshalb: der Programmname beweist
nichts (`omnitrade-cli.exe` faehrt auch Backtests), und die Statusdatei allein
luegt nach einem harten Ende. Kein zweiter Code, nur ein Aufruf.

Gemeldet werden vier Lagen:

    beendet   PID aus der Statusdatei lebt nicht (Zustand bleibt 'running')
    beendet   Zustand ist nicht mehr 'running' (sauberes Ende)
    haengt    PID lebt, aber die Datei bekommt kein Lebenszeichen
              (Alter ueber der Grenze - 300 s, bei laengeren Kerzen mehr)
    fehlt/kaputt  keine Statusdatei, unlesbares JSON, fremdes Schema

Der haertere Zeuge gewinnt: ist die PID tot, heisst es 'beendet' - auch wenn
die Datei zugleich alt ist. Sonst stuende in der Meldung 'PID lebt noch',
waehrend der Prozess laengst weg ist.

WAS ES NICHT TUT
----------------
* **Es startet nichts.** Ob der Lauf neu startet, entscheidet Max - die Wache
  nennt nur den Befehl.
* **Ein PID-Wechsel ist kein Fehler.** Der Lauf wird auch von Hand neu
  gestartet; die Wache fuehrt keine PID-Historie und vergleicht keine Staende.
  Sie meldet die Lage, nicht die Vorgeschichte.
* Es fasst die Statusdatei nicht an (nur lesend) und beendet keinen Prozess.

RUHIG BLEIBEN
-------------
Dieselbe Feststellung hoechstens einmal je WIEDERHOLUNG_STUNDEN (Merkdatei
`Agenten/Hermes/cache/omnitrade-lauf-wache.json`). Schluessel ist die Meldung
OHNE Zahlen - ein fortlaufendes Alter oder eine andere PID ist dieselbe
Feststellung, nicht eine neue.

Aufruf:
    python Agenten/Hermes/scripts/omnitrade-lauf-wache.py            # echter Waechter
    python ... --alle                                                # auch den gesunden Stand zeigen
    python ... --grenze-s 0                                          # Alarmrichtung pruefen
    python ... --status PFAD                                         # andere Statusdatei (Probe)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                      # scripts -> Hermes -> Agenten -> BrainFiles
HANDEL = WURZEL / "Agenten" / "Handel"

if str(HANDEL) not in sys.path:
    sys.path.insert(0, str(HANDEL))

import omnitrade_bridge as BRUECKE            # noqa: E402  (Pfad oben gesetzt)
import omnitrade_lauf as LAUF                 # noqa: E402  (die zwei Zeugen)

# Merkdatei gegen Dauerrauschen: dieselbe Feststellung nicht oefter als alle
# WIEDERHOLUNG_STUNDEN. Ein stehender Lauf ist morgen dieselbe Meldung -
# alle 15 Minuten wiederholt liest sie niemand mehr.
MERKDATEI = WURZEL / "Agenten" / "Hermes" / "cache" / "omnitrade-lauf-wache.json"

WIEDERHOLUNG_STUNDEN = 6.0
STARTBEFEHL = "omnitrade.cmd start"

# Testnaht: eine eigene `lebt(pid)`-Funktion (siehe omnitrade_lauf.beurteile).
LEBT = None


def urteil(lage=None, grenze_s=None):
    """Die Entscheidung von `omnitrade_lauf.beurteile()` - hier nur durchgereicht."""
    kw = {}
    if LEBT is not None:
        kw["lebt"] = LEBT
    if grenze_s is not None:
        kw["alt_grenze_s"] = grenze_s
    return LAUF.beurteile(lage=lage, **kw)


def _alter_text(alter_s):
    if alter_s is None:
        return "Alter unbekannt"
    if alter_s < 120:
        return "%.0f s alt" % alter_s
    return "%.0f min alt" % (alter_s / 60.0)


def _lebt(pid):
    """Lebt genau diese PID? Ueber die Testnaht LEBT oder den echten zweiten Zeugen."""
    if LEBT is not None:
        return bool(LEBT(pid))
    return LAUF.pid_lebt(pid)


def befund(lage=None, grenze_s=None, jetzt=None):
    """Zeilen fuer den Fall, dass der Lauf steht. Leer = er laeuft.

    Rueckgabe: (zeilen, kennzahl) - `kennzahl` sind Messwerte fuer --alle.
    """
    jetzt = jetzt or time.time()
    lage = lage if lage is not None else BRUECKE.lage()
    u = urteil(lage=lage, grenze_s=grenze_s)

    pid = u.get("pid")
    alter = u.get("alter_s")
    state = lage.get("state")
    datei = lage.get("datei")
    vorhanden = bool(datei) and os.path.exists(datei)
    lebt = _lebt(pid) if pid else False
    kennzahl = {"art": None, "pid": pid, "alter_s": alter, "state": state,
                "datei": datei, "pid_lebt": lebt}

    if u.get("laeuft"):
        kennzahl["art"] = "laeuft"
        return [], kennzahl

    grund = u.get("grund") or "unbekannt"
    fehler = lage.get("fehler") or ""
    wo = "%s (%s, okx/%s)" % (lage.get("symbol") or "?", _alter_text(alter),
                              lage.get("network") or "?")
    zeilen = []

    if not vorhanden:
        kennzahl["art"] = "fehlt"
        zeilen.append("Lauf beendet: es gibt keine Statusdatei mehr (%s) - "
                      "der Demo-Lauf laeuft nicht (%s)" % (grund, datei))
    elif lebt and ("veraltet" in fehler or "haengt" in grund):
        # Die PID lebt, aber es kommt kein Lebenszeichen. Beide Wege zaehlen:
        # die Grenze aus der Datei (Bruecke) und die von aussen gesetzte
        # (--grenze-s), die nur im Urteil sichtbar ist.
        kennzahl["art"] = "haengt"
        zeilen.append("Statusdatei HAENGT: kein Lebenszeichen seit %s, PID %s lebt "
                      "noch - der Lauf steht, die Datei steht still (%s)"
                      % (_alter_text(alter), pid, wo))
    elif "veraltet" in fehler:
        # Alter UND tote PID: der haertere Zeuge gewinnt, sonst behauptet die
        # Meldung 'PID lebt noch', waehrend der Prozess weg ist.
        kennzahl["art"] = "beendet"
        zeilen.append("Lauf beendet: PID %s lebt nicht, die Statusdatei bleibt auf "
                      "'running' stehen (letztes Lebenszeichen %s) - es handelt "
                      "nichts mehr (%s)" % (pid, _alter_text(alter), wo))
    elif not lage.get("ok"):
        kennzahl["art"] = "kaputt"
        zeilen.append("Statusdatei KAPUTT: %s - Lage nicht pruefbar (%s)"
                      % (grund, datei))
    elif state != "running":
        kennzahl["art"] = "beendet"
        zeilen.append("Lauf beendet: Zustand ist %r, nicht 'running' (PID %s, %s)"
                      % (state, pid, wo))
    elif not lebt:
        kennzahl["art"] = "beendet"
        zeilen.append("Lauf beendet: PID %s aus der Statusdatei lebt nicht - die "
                      "Datei bleibt auf 'running' stehen, es handelt nichts (%s)"
                      % (pid, wo))
    else:
        kennzahl["art"] = "beendet"
        zeilen.append("Lauf beendet: %s (%s)" % (grund, wo))

    zeilen.append("Starten (nur wenn Max es will): %s   [%s]" % (STARTBEFEHL, datei))
    return zeilen, kennzahl


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
        pass                                        # Merken ist Komfort


def entdopple(zeilen, merker, stunden=WIEDERHOLUNG_STUNDEN, jetzt=None):
    """Weg, was innerhalb der Frist schon gemeldet wurde. Rueckgabe:
    (zu_melden, neuer_merker). Schluessel ist die Meldung OHNE Zahlen: ein
    fortlaufendes Alter oder eine andere PID ist dieselbe Feststellung.
    """
    jetzt = jetzt or datetime.now(timezone.utc)
    neu, zu = {}, []
    for z in zeilen:
        schluessel = re.sub(r"\d+", "#", z)[:90]
        alt = merker.get(schluessel)
        faellig = True
        if alt:
            try:
                t = datetime.fromisoformat(alt)
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                faellig = (jetzt - t).total_seconds() >= stunden * 3600
            except ValueError:
                faellig = True
        neu[schluessel] = jetzt.isoformat(timespec="seconds") if faellig else alt
        if faellig:
            zu.append(z)
    for schluessel, t in list(neu.items()):
        try:
            ti = datetime.fromisoformat(t)
            if ti.tzinfo is None:
                ti = ti.replace(tzinfo=timezone.utc)
            if (jetzt - ti).days > 30:
                del neu[schluessel]
        except (ValueError, TypeError):
            del neu[schluessel]
    return zu, neu


def main(argv=None):
    p = argparse.ArgumentParser(description="Wache fuer den omnitrade-Demo-Lauf")
    p.add_argument("--grenze-s", type=float, default=None,
                   help="Alter, ab dem die Statusdatei als haengend gilt "
                        "(0 = alles melden, Alarmrichtung pruefen)")
    p.add_argument("--status", default=None,
                   help="andere Statusdatei lesen (sonst OMNITRADE_STATUS bzw. "
                        "Werkstatt/omnitrade/status/live.json)")
    p.add_argument("--alle", action="store_true",
                   help="auch den gesunden Stand nennen")
    a = p.parse_args(argv)

    if a.status:
        os.environ["OMNITRADE_STATUS"] = a.status

    zeilen, kennzahl = befund(grenze_s=a.grenze_s)

    if zeilen:
        zu_melden, neuer_merker = entdopple(zeilen, _merker())
        _merke(neuer_merker)
    else:
        zu_melden = []

    if zu_melden:
        print("omnitrade-Demo-Lauf steht:")
        for z in zu_melden:
            print("  " + z)
    elif a.alle:
        print("omnitrade-Demo-Lauf laeuft (PID %s, Statusdatei %s, Zustand %r)"
              % (kennzahl.get("pid"), _alter_text(kennzahl.get("alter_s")),
                 kennzahl.get("state")))
    return 0


if __name__ == "__main__":
    sys.exit(main())