"""Fristwaechter fuer die AUSSER-HAUS-Kopie (Q:\\MaxHirn-AusserHaus).

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut** und es wird nichts gesendet (Watchdog-Muster wie spiegelfrist-wache.py).

WARUM ES DIESEN WÄCHTER GIBT
----------------------------
Die Kopie ausser Haus ist die EINZIGE Sicherung, die nicht im selben Rechner
steckt (G: und O: haengen am selben Netzteil, ein Defekt hat 2026 schon 691
Archivdateien zerstoert). Sie laeuft aber von Hand - `Agenten/sichern-ausser-
haus.ps1`, bewusst ohne geplante Aufgabe, weil das Ziel eine USB-Platte ist,
die meist nicht angesteckt ist. Ohne Wache faellt eine veraltete Kopie erst
auf, wenn man sie braucht; am 29.09.2026 war der letzte Lauf 17 Tage her, und
NIEMAND hat es gemeldet - `spiegelstand.py` prueft nur das Handels-Journal.

Gemeldet wird genau der Fall, der zaehlt:

    Die juengste Spur im Ziel ist aelter als FRIST_TAGE (Vorgabe 14).

Dazu drei Faelle, die keine Frist mehr sind, sondern ein Ausfall: Q: haengt
nicht dran, das Ziel fehlt ganz, das Ziel ist leer.

WAS ES NICHT TUT
----------------
Es kopiert NICHTS und laesst Q: unberuehrt (nur lesend). Ein Waechter, der
selbst sichert, wuerde eine kaputte Sicherung verdecken statt sie zu melden.

WIE GEMESSEN WIRD (billig und ehrlich)
--------------------------------------
Nicht 150.000 Dateien jeden Lauf: es wird nur bis TIEFE=2 gelesen und die
JUENGSTE Aenderungszeit dieses Ausschnitts genommen ("das juengste, was im Ziel
sichtbar ist"). Ein Baum, in dem seit 14 Tagen nichts passiert ist, laesst auch
oben keine neue Zeit entstehen - eine Kopie, die heute gelaufen ist, dagegen
schon (jeder Quellordner wird beim Kopieren angefasst).

Aufruf:
    python Agenten/Hermes/scripts/ausserhaus-frist-wache.py             # echter Waechter
    python Agenten/Hermes/scripts/ausserhaus-frist-wache.py --alle      # auch Fristgerechtes zeigen
    python Agenten/Hermes/scripts/ausserhaus-frist-wache.py --frist-tage 0   # Alarmrichtung pruefen
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                     # Agenten/Hermes/scripts/ -> BrainFiles
ZIEL = Path("Q:/MaxHirn-AusserHaus")
QUELLE_ANLEITUNG = "Agenten/sichern-ausser-haus.ps1"

# Merkdatei gegen Dauerrauschen: dieselbe Feststellung nicht oefter als alle
# WIEDERHOLUNG_STUNDEN. Eine 17 Tage alte Kopie ist morgen dieselbe Meldung -
# taeglich wiederholt liest sie niemand mehr.
MERKDATEI = WURZEL / "Agenten" / "Hermes" / "cache" / "ausserhaus-frist-wache.json"

FRIST_TAGE = 14.0
WIEDERHOLUNG_STUNDEN = 72.0
TIEFE = 2


def messe(ziel, tiefe=TIEFE):
    """(juengste_mtime, eintraege, fehler) im Baum bis `tiefe` - nur lesend.

    `fehler` ist gesetzt, wenn das Ziel nicht lesbar ist (Platte weg, Rechte).
    """
    juengste, eintraege, fehler = None, 0, None
    stapel = [(str(ziel), 0)]
    while stapel:
        ordner, t = stapel.pop()
        try:
            with os.scandir(ordner) as it:
                for e in it:
                    eintraege += 1
                    try:
                        m = e.stat(follow_symlinks=False).st_mtime
                    except OSError:
                        continue
                    if juengste is None or m > juengste:
                        juengste = m
                    try:
                        ist_ordner = e.is_dir(follow_symlinks=False)
                    except OSError:
                        ist_ordner = False
                    if ist_ordner and t + 1 < tiefe:
                        stapel.append((e.path, t + 1))
        except OSError as ex:
            fehler = str(ex)
            break
    return juengste, eintraege, fehler


def befund(ziel=ZIEL, frist_tage=FRIST_TAGE, jetzt=None, tiefe=TIEFE):
    """Zeilen fuer den Fall, dass die Kopie die Frist reisst. Leer = alles gut.

    Rueckgabe: (zeilen, kennzahl) - `kennzahl` sind Messwerte fuer --alle.
    """
    jetzt = jetzt or time.time()
    laufwerk = os.path.splitdrive(str(ziel))[0] + os.sep
    if not os.path.isdir(laufwerk):
        return (["%s nicht angeschlossen - die Ausser-Haus-Kopie ist weder "
                 "aktuell noch pruefbar (%s fahren, sobald die Platte haengt)"
                 % (laufwerk, QUELLE_ANLEITUNG)], {"alter_tage": None})
    if not os.path.isdir(str(ziel)):
        return (["Ziel %s fehlt - es gibt keine Ausser-Haus-Kopie (%s fahren)"
                 % (ziel, QUELLE_ANLEITUNG)], {"alter_tage": None})

    juengste, eintraege, fehler = messe(ziel, tiefe)
    if fehler:
        return (["Ziel %s nicht lesbar (%s) - Kopie nicht pruefbar" % (ziel, fehler)],
                {"alter_tage": None})
    if not eintraege:
        return (["Ziel %s ist LEER - die Ausser-Haus-Kopie hat keinen Inhalt "
                 "(%s fahren)" % (ziel, QUELLE_ANLEITUNG)], {"alter_tage": None})

    alter_tage = (jetzt - juengste) / 86400.0
    kennzahl = {"alter_tage": alter_tage, "eintraege": eintraege}
    if alter_tage < frist_tage:
        return ([], kennzahl)
    return (["Ausser-Haus-Kopie ist %.1f Tage alt (Frist %.0f) - %s fahren "
             "(%d Eintraege bis Tiefe %d im Ziel, juengste Spur %s)"
             % (alter_tage, frist_tage, QUELLE_ANLEITUNG, eintraege, tiefe,
                datetime.fromtimestamp(juengste).strftime("%d.%m.%Y %H:%M"))],
            kennzahl)


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
    (zu_melden, neuer_merker). Schluessel ist die Meldung OHNE Zahlen - das
    Alter aendert sich mit jeder Stunde, die Feststellung nicht; 'Ziel fehlt'
    und 'Ziel ist LEER' bleiben dagegen zwei verschiedene Schluessel.
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
    p = argparse.ArgumentParser(description="Fristwaechter Ausser-Haus-Kopie")
    p.add_argument("--frist-tage", type=float, default=FRIST_TAGE,
                   help="Tage, die die Kopie hoechstens alt sein darf "
                        "(0 = alles melden, Alarmrichtung pruefen)")
    p.add_argument("--alle", action="store_true",
                   help="auch den geprueften Umfang nennen")
    a = p.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    zeilen, kennzahl = befund(ziel=ZIEL, frist_tage=a.frist_tage)

    if zeilen:
        zu_melden, neuer_merker = entdopple(zeilen, _merker())
        _merke(neuer_merker)
    else:
        zu_melden = []

    if zu_melden:
        print("Ausser-Haus-Sicherung:")
        for z in zu_melden:
            print("  " + z)
    elif a.alle:
        if kennzahl.get("alter_tage") is None:
            print("keine Kopie vorhanden - nichts zu melden")
        else:
            print("Kopie %.1f Tage alt (%d Eintraege), Frist %.0f Tage - in Ordnung"
                  % (kennzahl["alter_tage"], kennzahl.get("eintraege", 0), a.frist_tage))
    return 0


if __name__ == "__main__":
    sys.exit(main())
