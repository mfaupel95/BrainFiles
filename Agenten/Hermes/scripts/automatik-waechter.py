"""Automatik-Waechter: feuern die Hermes-Cron-Auftraege noch - und kommen sie an?

Laeuft als Hermes-Cron OHNE Modell (`no_agent`, alle 4 Stunden) und meldet nur,
wenn etwas klemmt. **Leere Ausgabe = alles laeuft**, es wird dann nichts
gesendet (Watchdog-Muster wie bus-waechter und omniroute-waechter).

WARUM
-----
Vier Wachen melden Dienste (Bus, Router, Atlas, Verzeichnisse), aber keine
einzige meldet die Wachen selbst. Genau dieser Blindfleck ist schon einmal
eingetreten: der Bus war vom 11.09. bis 15.09.2026 vier Tage stumm, und es
gab keine Wache, die das gefunden haette.

Was hier schiefgehen kann, ist dreierlei und sieht an der Oberflaeche gleich
aus (`state: scheduled`):
  1. der Auftrag feuert nicht mehr (Zeitstempel bleibt stehen),
  2. der Auftrag feuert, aber der Lauf scheitert (`last_status`),
  3. der Auftrag laeuft und meldet - die Nachricht kommt aber nicht an
     (`last_delivery_error`). Fall 3 ist der leiseste: er sieht wie Erfolg aus.

DIE ZWEITE ZUTUER (wichtig)
---------------------------
Ein Waechter darf nicht am selben Mechanismus haengen wie das, was er
bewacht. Faellt der Hermes-Scheduler aus, laeuft dieser Auftrag nicht mehr -
und meldet nichts. Deshalb ruft `optimierungen-finden.py` (eine
Windows-Aufgabe, also der ANDERE Mechanismus) dieselbe Pruefung ueber
`befunde_holen()` mit auf und meldet sie ueber den Bus.

WAS ES TUT (nur lesend)
-----------------------
1. `Agenten/Hermes/cron/jobs.json` lesen - die Datei, aus der der laufende
   Scheduler wirklich feuert (nicht ein zweiter Speicher).
2. Je eingeschaltetem Auftrag die erwartete Luecke aus dem Zeitplan
   ableiten (Intervall bzw. Cron-Ausdruck) und gegen `last_run_at` halten.
3. Zustellfehler, Lauffehler und haengende Termine melden.
4. Nichts aendern, nichts aufwecken, nichts starten - nur melden.

Aufruf:
    python Agenten/Hermes/scripts/automatik-waechter.py
    python Agenten/Hermes/scripts/automatik-waechter.py --alles
        -> auch ohne Befund die Zahlen zeigen (Abnahme)
    python Agenten/Hermes/scripts/automatik-waechter.py --datei <pfad>
        -> eine andere jobs.json pruefen (Gegenprobe der Melderichtung)
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
STANDARD_DATEI = HIER.parents[1] / "cron" / "jobs.json"   # Agenten/Hermes/cron/jobs.json

# Schonfrist je Luecke: ein Lauf darf ausfallen, ohne dass es ein Befund ist
# (Rechner war aus, Termin wurde nachgeholt, Scheduler war beschaeftigt).
TOLERANZ = 2.5
# Ein Auftrag, der noch NIE gelaufen ist, hat keine Ausrede: hier zaehlt schon
# eine volle Luecke plus ein Viertel. Bei 2.5 x waere ein woechentlicher
# Auftrag erst nach 17 Tagen aufgefallen - ein Auftrag, der seit zwei
# Wochenenden nicht gefeuert hat, ist laengst ein Befund.
TOLERANZ_NIE = 1.25
ZUSATZ_MINUTEN = 15
# Ab hier ist eine Verspaetung kein Zufall mehr, sondern ein Befund.
VERSPAETUNG_SEKUNDEN = 900
# So lange darf ein faelliger Termin in der Vergangenheit liegen.
TERMIN_HAENGT_SEKUNDEN = 3600


def jetzt_lokal(zeitpunkt=None):
    if zeitpunkt is None:
        return datetime.now().astimezone()
    if isinstance(zeitpunkt, datetime):
        return zeitpunkt
    dt = datetime.fromisoformat(str(zeitpunkt))
    return dt if dt.tzinfo else dt.astimezone()


def als_zeit(wert, bezug):
    """ISO-Zeichenkette -> bewusste Zeit; None bleibt None."""
    if not wert:
        return None
    try:
        dt = datetime.fromisoformat(str(wert))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=bezug.tzinfo)


def erwartete_luecke(job):
    """(Minuten, Beschreibung) aus dem Zeitplan - None bei Einmalauftraegen.

    Bewusst grob: es geht darum, eine STEHENGEBLIEBENE Uhr zu erkennen, nicht
    den Termin zu Sekunden genau nachzurechnen. Zu grosszuegig gehalten, damit
    ein fehlender Lauf nicht sofort wie ein Ausfall aussieht.
    """
    z = job.get("schedule") or {}
    art = z.get("kind")
    if art == "interval":
        minuten = int(z.get("minutes") or 0)
        return (minuten, "alle %d Min" % minuten) if minuten else (None, "")
    if art == "cron":
        felder = str(z.get("expr") or "").split()
        if len(felder) != 5:
            return None, ""
        _, stunde, tag, _, wochentag = felder
        if tag != "*" or wochentag != "*":
            return 7 * 24 * 60, "woechentlich (%s)" % z.get("expr")
        if stunde == "*":
            return 60, "stuendlich (%s)" % z.get("expr")
        # Mehrere Stunden am Tag ("*/6") -> Abstand aus der Stundenzahl.
        if stunde.startswith("*/"):
            try:
                return int(stunde[2:]) * 60, "alle %s h (%s)" % (stunde[2:], z.get("expr"))
            except ValueError:
                return None, ""
        return 24 * 60, "taeglich (%s)" % z.get("expr")
    return None, ""          # "once" und Unbekanntes: keine Wiederkehr, kein Befund


def befunde_holen(datei=None, zeitpunkt=None):
    """Liste deutscher Befundzeilen - leer, wenn alles laeuft. Nur lesend.

    `AUTOMATIK_WACHTER_DATEI` zeigt auf eine andere jobs.json; das ist der
    Pruefhaken fuer die zweite Zutuer (optimierungen-finden.py) - eine
    Fehlerrichtung, die man nicht ohne Weiteres herstellen kann, muss sich
    herstellen lassen, sonst wird sie nie geprueft.
    """
    pfad = Path(datei or os.environ.get("AUTOMATIK_WACHTER_DATEI") or STANDARD_DATEI)
    jetzt = jetzt_lokal(zeitpunkt)
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return ["Cron-Automatik: %s nicht lesbar (%s)." % (pfad, e)], {}

    auftraege = roh.get("jobs") or []
    befunde = []
    zahl = {"gesamt": len(auftraege), "aktiv": 0, "geprueft": 0, "nie_gelaufen": 0}

    for job in auftraege:
        if not job.get("enabled") or job.get("state") not in ("scheduled", "running"):
            continue
        zahl["aktiv"] += 1
        name = job.get("name") or job.get("id") or "?"
        luecke, beschreibung = erwartete_luecke(job)
        if luecke is None:
            continue
        zahl["geprueft"] += 1
        grenze = timedelta(minutes=luecke * TOLERANZ + ZUSATZ_MINUTEN)

        letzter = als_zeit(job.get("last_run_at"), jetzt)
        if letzter is None:
            zahl["nie_gelaufen"] += 1
            erstellt = als_zeit(job.get("created_at"), jetzt)
            nie_grenze = timedelta(minutes=luecke * TOLERANZ_NIE + ZUSATZ_MINUTEN)
            if erstellt and jetzt - erstellt > nie_grenze:
                befunde.append(
                    "Cron-Auftrag feuert nie: %s (%s) ist seit %s eingerichtet "
                    "und hat noch keinen Lauf gehabt."
                    % (name, beschreibung, erstellt.strftime("%d.%m. %H:%M")))
        elif jetzt - letzter > grenze:
            befunde.append(
                "Cron-Auftrag feuert nicht mehr: %s (%s), letzter Lauf %s - "
                "das sind %s."
                % (name, beschreibung, letzter.strftime("%d.%m. %H:%M"),
                   dauer(jetzt - letzter)))

        status = job.get("last_status")
        if status and status != "ok":
            befunde.append("Cron-Auftrag mit Fehler: %s, letzter Lauf %s - %s"
                           % (name, (letzter or jetzt).strftime("%d.%m. %H:%M"),
                              (job.get("last_error") or status)[:160]))

        if job.get("last_fire_error"):
            befunde.append("Cron-Auftrag startet nicht: %s - %s"
                           % (name, str(job["last_fire_error"])[:160]))

        if job.get("last_delivery_error"):
            befunde.append("Cron-Meldung kommt nicht an: %s (%s) - %s"
                           % (name, job.get("deliver") or "origin",
                              str(job["last_delivery_error"])[:160]))

        verspaetung = (job.get("last_dispatch") or {}).get("lateness_seconds")
        if isinstance(verspaetung, (int, float)) and verspaetung > VERSPAETUNG_SEKUNDEN:
            befunde.append("Cron-Auftrag feuert verspaetet: %s, zuletzt %d Min nach Termin."
                           % (name, int(verspaetung // 60)))

        naechster = als_zeit(job.get("next_run_at"), jetzt)
        if naechster and (jetzt - naechster).total_seconds() > TERMIN_HAENGT_SEKUNDEN:
            befunde.append(
                "Cron-Scheduler tickt nicht: %s haette zuletzt %s laufen sollen "
                "(noch kein neuer Termin gesetzt)."
                % (name, naechster.strftime("%d.%m. %H:%M")))

    return befunde, zahl


def dauer(delta):
    minuten = int(delta.total_seconds() // 60)
    if minuten < 60:
        return "%d Min" % minuten
    if minuten < 48 * 60:
        return "%.1f h" % (minuten / 60.0)
    return "%.1f Tage" % (minuten / 1440.0)


def meldung(befunde, zahl):
    """Der Text, der als Cron-Ausgabe verschickt wird (leer = nichts senden)."""
    if not befunde:
        return ""
    kopf = ("Cron-Automatik: %d von %d eingeschalteten Auftraegen auffaellig "
            "(%d wiederkehrende geprueft)." % (len(befunde), zahl.get("aktiv", 0),
                                               zahl.get("geprueft", 0)))
    return "\n".join([kopf] + ["- %s" % b for b in befunde[:8]] +
                     ["Nichts davon ist geaendert worden; der Waechter meldet nur."])


def main():
    ap = argparse.ArgumentParser(
        description="Hermes-Cron-Auftraege auf Ausfaelle und Zustellfehler pruefen")
    ap.add_argument("--datei", help="andere jobs.json pruefen (Gegenprobe)")
    ap.add_argument("--alles", action="store_true",
                    help="auch ohne Befund die Zahlen zeigen (Abnahme)")
    args = ap.parse_args()

    befunde, zahl = befunde_holen(args.datei)
    text = meldung(befunde, zahl)
    if text:
        print(text)
    elif args.alles:
        print("Cron-Automatik: kein Befund. %d Auftraege, davon %d eingeschaltet, "
              "%d wiederkehrende geprueft, %d ohne Lauf."
              % (zahl.get("gesamt", 0), zahl.get("aktiv", 0),
                 zahl.get("geprueft", 0), zahl.get("nie_gelaufen", 0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
