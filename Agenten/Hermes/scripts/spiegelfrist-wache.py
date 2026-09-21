"""Fristwaechter fuer Bedingung 4 (Journal ausser Haus).

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut**, und es wird nichts gesendet (Watchdog-Muster wie bus-waechter.py).
Gemeldet wird nur, was eine Frist VERLETZT.

WARUM ES DIESEN WÄCHTER GIBT
----------------------------
Am 21.09.2026 lief scanner ab 19:22 in jedem Zyklus in den Abbruch des
Dauerlaufs (Freigabefenster wartete 600 s, der Abbruch lag bei 300 s). Die
Spiegelung nach Q: steht am ENDE eines Zyklus - sie lief also nie mehr. Das
lokale Ablehnungsprotokoll wuchs weiter, Q:\\Handel_Journal\\scanner stand
still, die Live-Position wurde 2,5 h nicht mehr auf Stop/Ziel geprueft.
Aufgefallen ist das erst beim Nachsehen von Hand.

`spiegelstand.py` kann das messen (byte-genau) - aber niemand ruft es im
Minutentakt auf. Der Tagesbericht zeigt die Zeile einmal am Abend, die
Systempruefung laeuft noch seltener. Dieser Waechter stellt dieselbe Frage
alle 15 Minuten und meldet nur den einen Fall, der zaehlt:

    Eine Datei, die es lokal gibt, steht nach FRIST_MIN Minuten
    (Standard 20) in der Kopie immer noch anders (oder fehlt dort).

Die Frist ist der Unterschied zwischen Rauschen und Befund: Tests und
Handlaeufe schreiben kurzzeitig in echte Spurenordner, das heilt im naechsten
Zyklus (Takt 15 min, Laufzeit je Spur Sekunden bis Minuten). Was nach 20
Minuten noch abweicht, heilt nicht von selbst.

WAS ES NICHT TUT
----------------
Es kopiert NICHTS. Ein Waechter, der selbst nach Q: schreibt, wuerde eine
kaputte Spiegelung verdecken statt sie zu melden - und zwei Schreiber auf ein
Ziel waren schon einmal der Fehler (xperp, 14.09.2026). Reparieren heisst:
Ursache finden, `spiegelstand.py` als Nachweis, dann der naechste echte Zyklus.

Aufruf:
    python Agenten/Hermes/scripts/spiegelfrist-wache.py            # echter Waechter
    python Agenten/Hermes/scripts/spiegelfrist-wache.py --frist 0  # Alarmrichtung pruefen
    python Agenten/Hermes/scripts/spiegelfrist-wache.py --alle     # auch Fristgerechtes zeigen
"""

import argparse
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                     # Agenten/Hermes/scripts/ -> BrainFiles
HANDEL = WURZEL / "Agenten" / "Handel"
SPIEGELSTAND = HANDEL / "spiegelstand.py"
# Merkdatei gegen Dauerrauschen: dieselbe Feststellung wird nicht oefter als
# alle WIEDERHOLUNG_STUNDEN gemeldet. Ohne sie waere ein abgezogenes Q: ein
# Alarm alle 15 Minuten, bis jemand die Platte ansteckt - und solche Meldungen
# liest niemand mehr (genau der Weg, auf dem eine echte Meldung verschwindet).
MERKDATEI = WURZEL / "Agenten" / "Hermes" / "cache" / "spiegelfrist-wache.json"

# Dateien, die eine Spur ausser Haus fuehren MUSS, stehen in spiegelstand.py
# (DATEIEN + ZUSATZ je Spur, dazu die Suffixe der Risikostufen und Arme).
# Hier wird deshalb KEIN Namensmuster geraten: verglichen wird, was
# spiegelstand als abweichend meldet - eine eigene Liste waere eine zweite
# Wahrheit (und zaehlte Archive wie handelsjournal.falsch-skaliert-*.csv mit,
# die bewusst NICHT gespiegelt werden).

FRIST_MIN = 20.0
WIEDERHOLUNG_STUNDEN = 6.0


def lade_spiegelstand():
    """spiegelstand.py per Pfad laden - es ist kein installiertes Modul.

    Geladen wird NUR gelesen (spur_zeile, spuren_ordner, spuren_im_lauf); das
    Modul selbst schreibt nichts.
    """
    spec = importlib.util.spec_from_file_location("spiegelstand_wache",
                                                  str(SPIEGELSTAND))
    if spec is None or spec.loader is None:
        return None
    modul = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HANDEL))
    try:
        spec.loader.exec_module(modul)
    finally:
        sys.path.pop(0)
    return modul


def alter_minuten(pfad):
    try:
        return (time.time() - os.path.getmtime(pfad)) / 60.0
    except OSError:
        return None


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


def entdopple(zeilen, merker, stunden=WIEDERHOLUNG_STUNDEN):
    """Weg, was innerhalb der Frist schon gemeldet wurde.

    Schluessel ist der Text VOR dem Rueckstand ('spur: datei'), nicht die
    ganze Zeile: ein wachsender Rueckstand bleibt dieselbe Feststellung und
    wird nicht mit jeder Minute zu einer neuen Meldung. Rueckgabe:
    (zu_melden, neuer_merker).
    """
    jetzt = datetime.now(timezone.utc)
    neu, zu = {}, []
    for z in zeilen:
        schluessel = z.split(" seit ")[0].split(" NICHT ERREICHBAR")[0]
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
        neu[schluessel] = jetzt.isoformat(timespec="seconds") if faellig \
            else alt
        if faellig:
            zu.append(z)
    # Alte Schluessel nach einer Woche fallen lassen, sonst waechst die
    # Merkdatei mit jedem umbenannten Instrument weiter.
    for schluessel, t in list(neu.items()):
        try:
            ti = datetime.fromisoformat(t)
            if ti.tzinfo is None:
                ti = ti.replace(tzinfo=timezone.utc)
            if (jetzt - ti).days > 7:
                del neu[schluessel]
        except (ValueError, TypeError):
            del neu[schluessel]
    return zu, neu


def befund_je_spur(sp, handel=HANDEL, frist=FRIST_MIN):
    """Zeilen fuer Spuren, deren Kopie die Frist reisst.

    Rueckgabe: (zeilen, geprueft, abweichend) - `zeilen` ist leer, wenn alles
    innerhalb der Frist liegt.
    """
    handel = str(handel)
    ordner_zu = sp.spuren_ordner(handel) or {}
    im_lauf = sp.spuren_im_lauf(handel)
    zeilen, geprueft, abweichend = [], 0, 0

    kandidaten = sorted(d for d in os.listdir(handel)
                        if os.path.isfile(os.path.join(handel, d, "wachen.json")))
    if ordner_zu:
        for spur, ordner in ordner_zu.items():
            if ordner in kandidaten and spur not in kandidaten:
                for wname in ("wachen.knapp.json", "wachen.weit.json"):
                    if os.path.isfile(os.path.join(handel, ordner, wname)):
                        kandidaten.append(spur)
    kandidaten = sorted(set(kandidaten))

    for spur in kandidaten:
        ordner = ordner_zu.get(spur, spur)
        e = sp.spur_zeile(handel, spur, ordner=ordner)
        ziel = e.get("ziel")
        if not ziel:
            continue                        # Spur ohne Zweitziel ueberspringen
        if im_lauf is not None and spur not in im_lauf:
            continue                        # laeuft nicht -> keine Frist
        geprueft += 1
        if e.get("stand") == "Ziel fehlt":
            zeilen.append("%s: Ziel %s NICHT ERREICHBAR (Q: weg?)" % (spur, ziel))
            abweichend += 1
            continue
        spurordner = os.path.join(handel, ordner)
        if e.get("stand") != "ABWEICHUNG":
            continue
        # spur_zeile nennt die abweichenden Dateien namentlich in `grund`
        # (komma-getrennt) - dieselbe Liste, die spiegelstand byte-genau
        # verglichen hat. Nur sie wird auf die Frist geprueft.
        namen = [n.strip() for n in (e.get("grund") or "").split(",")
                 if n.strip()]
        for name in namen:
            lokal = os.path.join(spurordner, name)
            kopie = os.path.join(ziel, name)
            if not os.path.exists(lokal):
                continue                    # nur lokal Fehlendes ist keine Frist
            alter = alter_minuten(lokal)
            if alter is None or alter < frist:
                continue                    # Test-/Laufrauschen, heilt selbst
            abweichend += 1
            fehlt = " (Kopie fehlt)" if not os.path.exists(kopie) else ""
            zeilen.append("%s: %s seit %.0f min nicht gespiegelt%s"
                          % (spur, name, alter, fehlt))
    return zeilen, geprueft, abweichend


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frist", type=float, default=FRIST_MIN,
                   help="Minuten, die eine Abweichung alt sein muss "
                        "(0 = alles melden, Alarmrichtung pruefen)")
    p.add_argument("--alle", action="store_true",
                   help="auch den geprueften Umfang nennen")
    a = p.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not SPIEGELSTAND.exists():
        print("spiegelfrist-wache: %s fehlt - nicht geprueft" % SPIEGELSTAND)
        return 0
    sp = lade_spiegelstand()
    if sp is None:
        print("spiegelfrist-wache: spiegelstand.py nicht ladbar")
        return 0

    try:
        zeilen, geprueft, abweichend = befund_je_spur(sp, frist=a.frist)
    except OSError as e:
        print("spiegelfrist-wache: Pruefung abgebrochen (%s)" % e)
        return 0

    if zeilen:
        merker = _merker()
        zu_melden, neuer_merker = entdopple(zeilen, merker)
        _merke(neuer_merker)
    else:
        zu_melden = []

    if zu_melden:
        print("Bedingung 4 (Journal ausser Haus) verletzt:")
        for z in zu_melden:
            print("  " + z)
        print("Nachweis: Agenten/Handel/spiegelstand.py - Ursache finden, "
              "nicht nachkopieren.")
    elif a.alle:
        print("%d Spuren mit Zweitziel geprueft, alle Kopien aktuell" % geprueft)
    return 0


if __name__ == "__main__":
    sys.exit(main())