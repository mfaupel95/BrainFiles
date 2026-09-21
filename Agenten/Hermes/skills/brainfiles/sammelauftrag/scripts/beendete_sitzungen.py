"""Beendete, noch nicht archivierte Sitzungen auflisten - NUR LESEND.

Ergaenzt scripts/offene_sitzungen.py um die andere Haelfte des Abschlusses:
welche Sitzungen sind BEENDET (ended_at IS NOT NULL), aber noch nicht
archiviert? Das sind die natuerlichen Kandidaten fuer `hermes sessions archive`.

Es wird NICHTS geschrieben, NICHTS archiviert, NICHTS geloescht - der Abschluss
laeuft ueber `hermes sessions archive` und erst nach dessen Trockenlauf.

Aufruf ueber das terminal-Werkzeug, aus der Repo-Wurzel:
    python Agenten/Hermes/skills/brainfiles/sammelauftrag/scripts/beendete_sitzungen.py

Optionen:
    --db PFAD        andere state.db (Vorgabe: Agenten/Hermes/state.db)
    --alle-profile   zusaetzlich jede profiles/<name>/state.db
    --kurz           nur Zahlen und Abschlussvorschlag
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# end_reason-Werte, die NICHT endgueltig sind: die Wiederaufnahme holt solche
# Zeilen zurueck (hermes_state_common._RECOVERABLE_END_REASONS).
RECOVERABLE_ENDS = ("agent_close", "ws_orphan_reap", "superseded_by_resume",
                    "startup_orphan_reap")


def wurzel_finden(start: Path) -> Path:
    p = start.resolve()
    for _ in range(10):
        if (p / "MaxHirn").is_dir() and (p / "Agenten").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise SystemExit("Repo-Wurzel nicht gefunden (MaxHirn/ + Agenten/ fehlen) - --db nutzen")


def verbinden(pfad: Path):
    return sqlite3.connect("file:%s?mode=ro" % pfad.as_posix(), uri=True)


def alter_text(minuten):
    if minuten < 60:
        return "%4.0f min" % minuten
    if minuten < 60 * 48:
        return "%4.1f h  " % (minuten / 60.0)
    return "%4.1f d  " % (minuten / 1440.0)


def main():
    ap = argparse.ArgumentParser(description="Beendete, nicht archivierte Hermes-Sitzungen auflisten (nur lesend)")
    ap.add_argument("--db", help="state.db (Vorgabe: Agenten/Hermes/state.db)")
    ap.add_argument("--alle-profile", action="store_true",
                    help="zusaetzlich jede profiles/<name>/state.db")
    ap.add_argument("--kurz", action="store_true", help="nur Zahlen und Vorschlag")
    args = ap.parse_args()

    w = wurzel_finden(Path(__file__).parent)
    jetzt = datetime.now()
    pfade = []
    if args.db:
        pfade.append((Path(args.db), "(--db)"))
    else:
        pfade.append((w / "Agenten" / "Hermes" / "state.db", "default"))
    if args.alle_profile:
        for d in sorted((w / "Agenten" / "Hermes" / "profiles").glob("*/state.db")):
            pfade.append((d, d.parent.name))

    print("# Beendete, nicht archivierte Sitzungen - Bestandsaufnahme %s"
          % jetzt.strftime("%Y-%m-%d %H:%M"))
    print("# Dieses Skript liest nur. Archivieren tut der Agent nach dem Trockenlauf.")

    for pfad, name in pfade:
        if not pfad.is_file():
            print("\n=== %s ===\n(fehlende Datei: %s)" % (name, pfad))
            continue
        print("\n=== Sitzungsspeicher: %s  (%s) ===" % (name, pfad))
        c = verbinden(pfad)
        gesamt = list(c.execute("select count(*) from sessions"))[0][0]
        beendet = list(c.execute("select count(*) from sessions where ended_at is not null"))[0][0]
        archiviert = list(c.execute("select count(*) from sessions where archived=1"))[0][0]
        angeheftet = list(c.execute("select count(*) from sessions where pinned=1"))[0][0]
        print("  Sitzungen gesamt: %d   |   beendet: %d   |   archiviert: %d   |   angeheftet: %d"
              % (gesamt, beendet, archiviert, angeheftet))

        # Beendet UND nicht archiviert = natuerlicher Abschluss-Kandidat.
        sql = ("select id, source, title, cwd, started_at, ended_at, end_reason, "
               "message_count, tool_call_count, pinned, hidden "
               "from sessions where ended_at is not null and archived=0 "
               "order by coalesce(ended_at, started_at) desc")
        zeilen = list(c.execute(sql))
        print("  Beendet, noch nicht archiviert: %d" % len(zeilen))
        if not args.kurz and zeilen:
            print("  %-30s %-9s %-9s %5s %5s  %s" % ("id", "quelle", "alter", "msgs", "tools", "hinweis"))
            for (sid, quelle, titel, cwd, start, ende, grund, msgs, tools, pin, hid) in zeilen:
                bezug = ende or start or jetzt.timestamp()
                alter = (jetzt.timestamp() - bezug) / 60.0
                hinw = []
                if pin:
                    hinw.append("ANGEHEFTET")
                if hid:
                    hinw.append("versteckt")
                if msgs == 0:
                    hinw.append("leer")
                if grund in RECOVERABLE_ENDS:
                    hinw.append("wiederaufnehmbar(%s)" % grund)
                print("  %-30s %-9s %-9s %5d %5d  %s"
                      % (sid[:30], (quelle or "?")[:9], alter_text(alter),
                         msgs or 0, tools or 0, " ".join(hinw) or "-"))
        if zeilen:
            print("""
  Abschluss zuerst TROCKENLAUFEN, dann ohne --dry-run wiederholen:
    hermes sessions archive --older-than 30d --dry-run
    hermes sessions archive --older-than 30d --yes
  Merke: `archive` versteckt nur (umkehrbar, kein Datenverlust). Angeheftete
  Sitzungen sind Keep-Flags und werden von archive/prune geschuetzt.""")
        c.close()


if __name__ == "__main__":
    main()
