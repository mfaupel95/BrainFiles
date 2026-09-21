"""Offene Sitzungen bestandsaufnehmen - NUR LESEND.

Liest den Hermes-Sitzungsspeicher (`state.db`, Tabelle `sessions`) und
beantwortet drei Fragen, die vor jedem Zusammenfuehren und Abschliessen
stehen:

  1. Welche Sitzungen sind OFFEN (`ended_at IS NULL`) und wie frisch sind sie?
  2. Was steht in ihnen drin (letzte Nutzer- und Assistentenzeile je Sitzung)?
  3. Welche sind reif fuer den Abschluss, und mit welchem Befehl?

Es wird NICHTS geschrieben, NICHTS archiviert, NICHTS geloescht - der Abschluss
laeuft ueber `hermes sessions archive` und erst nach dessen Trockenlauf.

Aufruf ueber das terminal-Werkzeug, aus der Repo-Wurzel:
    python Agenten/Hermes/skills/brainfiles/sammelauftrag/scripts/offene_sitzungen.py

Optionen:
    --db PFAD        andere state.db (Vorgabe: Agenten/Hermes/state.db)
    --alle-profile   zusaetzlich jede profiles/<name>/state.db
    --minuten N      Grenze "lebendig" in Minuten (Vorgabe 30)
    --je N           Sitzungen mit Inhalt zeigen (Vorgabe 12)
    --kurz           nur Zahlen, Kandidaten und Abschlussvorschlag
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# end_reason-Werte, die NICHT endgueltig sind: die Wiederaufnahme holt solche
# Zeilen zurueck (hermes_state_common._RECOVERABLE_END_REASONS).
RECOVERABLE_ENDS = ("agent_close", "ws_orphan_reap", "superseded_by_resume",
                    "startup_orphan_reap")
INHALT_ROLLEN = ("user", "assistant")


def wurzel_finden(start: Path) -> Path:
    """Aufwaerts bis zu dem Ordner, der MaxHirn und Agenten enthaelt."""
    p = start.resolve()
    for _ in range(10):
        if (p / "MaxHirn").is_dir() and (p / "Agenten").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise SystemExit("Repo-Wurzel nicht gefunden (MaxHirn/ + Agenten/ fehlen) - --db nutzen")


def kopf(text):
    print("\n=== %s ===" % text)


def verbinden(pfad: Path):
    """Nur lesend oeffnen. Ein fehlendes WAL ist kein Fehler."""
    return sqlite3.connect("file:%s?mode=ro" % pfad.as_posix(), uri=True)


def text_aus(content):
    """Nachrichtentext flach machen: str, oder Blockliste mit text-Teilen."""
    if not content:
        return ""
    if isinstance(content, (bytes, bytearray)):
        content = content.decode("utf-8", "replace")
    if isinstance(content, str):
        roh = content.strip()
        if roh[:1] in "[{":
            try:
                geladen = json.loads(roh)
            except ValueError:
                return roh
            return text_aus(geladen)
        return roh
    if isinstance(content, list):
        teile = []
        for b in content:
            if isinstance(b, dict) and isinstance(b.get("text"), str):
                teile.append(b["text"])
            elif isinstance(b, str):
                teile.append(b)
        return "\n".join(teile).strip()
    if isinstance(content, dict):
        return text_aus(content.get("text") or content.get("content"))
    return str(content)


def ein_zeiler(text, grenze=180):
    text = " ".join(text_aus(text).split())
    return text[:grenze] + (" ..." if len(text) > grenze else "")


def zahlen(c, name):
    def q(sql, *p):
        return list(c.execute(sql, p))[0][0]
    offen = q("select count(*) from sessions where ended_at is null")
    print("Quelle: %-42s Sitzungen gesamt: %d" % (name, q("select count(*) from sessions")))
    print("  offen (ended_at IS NULL): %d   |   beendet: %d   |   archiviert: %d"
          % (offen, q("select count(*) from sessions where ended_at is not null"),
             q("select count(*) from sessions where archived=1")))
    print("  angeheftet (pin, Keep-Flag): %d   |   versteckt (hidden): %d"
          % (q("select count(*) from sessions where pinned=1"),
             q("select count(*) from sessions where hidden=1")))
    return offen


def offene_liste(c, jetzt, minuten, still_stunden):
    """Offene Sitzungen mit Alter, Umfang und Einordnung."""
    grenze_alt = jetzt.timestamp() - still_stunden * 3600
    zeilen = []
    sql = ("select id, source, title, cwd, started_at, last_activity_at, message_count, "
           "tool_call_count, archived, hidden, pinned, end_reason, profile_name "
           "from sessions where ended_at is null "
           "order by coalesce(last_activity_at, started_at) desc")
    for (sid, quelle, titel, cwd, start, letzte, msgs, tools, arch, hid, pin,
         grund, profil) in c.execute(sql):
        bezug = letzte or start or jetzt.timestamp()
        alter_min = (jetzt.timestamp() - bezug) / 60.0
        if alter_min <= minuten:
            lage = "lebendig"
        elif bezug < grenze_alt:
            lage = "still"
        else:
            lage = "abgebrochen"
        zeilen.append(dict(id=sid, quelle=quelle or "?", titel=titel or "", cwd=cwd or "",
                           alter_min=alter_min, msgs=msgs or 0, tools=tools or 0,
                           archiviert=arch, versteckt=hid, angeheftet=pin,
                           grund=grund, profil=profil or "", lage=lage))
    return zeilen


def alter_text(minuten):
    if minuten < 60:
        return "%4.0f min" % minuten
    if minuten < 60 * 48:
        return "%4.1f h  " % (minuten / 60.0)
    return "%4.1f d  " % (minuten / 1440.0)


def _letzte_zeile(c, sid, rolle, aktiv):
    """Letzter nicht-leerer Text dieser Rolle. Leere Assistentenzeilen sind reine
    Werkzeugaufruf-Turns und wuerden die Antwort sonst verdraengen."""
    bedingung = " and active=1" if aktiv else ""
    try:
        reihe = list(c.execute(
            "select content from messages where session_id=? and role=?" + bedingung +
            " and content is not null and length(content)>0 "
            "order by timestamp desc limit 1", (sid, rolle)))
    except sqlite3.Error:
        return ""
    return ein_zeiler(reihe[0][0]) if reihe else ""


def inhalt_je_sitzung(c, kennungen, rollen=INHALT_ROLLEN):
    """(letzte Nutzerzeile, letzte Assistentenzeile) je Sitzung - fuer das Zusammenfuehren.

    Je Rolle eine Abfrage mit `order by timestamp desc limit 1`: eine gemeinsame
    Abfrage mit Fenster liefert bei werkzeuglastigen Sitzungen nur leere
    Assistentenzeilen und Werkzeugausgaben. `id` ist global ueber alle Sitzungen,
    ein `id > N` wuerde willkuerlich schneiden - darum ueber `session_id`.
    """
    ergebnis = {}
    for sid in kennungen:
        letzte = {r: _letzte_zeile(c, sid, r, True) for r in rollen}
        if not any(letzte.values()):
            letzte = {r: _letzte_zeile(c, sid, r, False) for r in rollen}
        ergebnis[sid] = letzte
    return ergebnis


def kandidaten(zeilen, still_stunden):
    """Sitzungen, die zum Abschluss reif sind: still, nicht angeheftet, nicht versteckt."""
    reif = [z for z in zeilen if z["lage"] == "still" and not z["angeheftet"] and not z["versteckt"]]
    print("%d Sitzung(en) still seit ueber %d h und nicht angeheftet." % (len(reif), still_stunden))
    if not reif:
        return reif
    je_quelle = {}
    for z in reif:
        je_quelle[z["quelle"]] = je_quelle.get(z["quelle"], 0) + 1
    print("  nach Quelle: %s" % ", ".join("%s=%d" % kv for kv in sorted(je_quelle.items(),
                                                                     key=lambda kv: -kv[1])))
    print("  aeltestes offen seit: %s   |   nie benutzt (0 msgs): %d"
          % (max(alter_text(z["alter_min"]) for z in reif),
             sum(1 for z in reif if z["msgs"] == 0)))
    print("""
  Abschluss zuerst TROCKENLAUFEN, dann ohne --dry-run wiederholen:
    hermes sessions archive --older-than 1d --source a2a --dry-run
    hermes sessions archive --older-than 30d --dry-run
    hermes sessions prune --never-active --older-than 30d --dry-run
  Merke: `archive` versteckt nur (umkehrbar, kein Datenverlust). `prune` LOESCHT und
  schliesst archivierte und angeheftete Sitzungen nur mit --include-archived /
  --include-pinned ein - ohne diese Schalter sind sie geschuetzt.""")
    return reif


def auffaelligkeiten(c, zeilen):
    hinweise = []
    tot_und_offen = [z for z in zeilen if z["archiviert"] and not z["versteckt"]]
    if tot_und_offen:
        hinweise.append("%d offene Sitzung(en) sind zugleich archiviert - Archiv und "
                        "ended_at sind unabhaengig, das ist kein Widerspruch." % len(tot_und_offen))
    wiederbelebbar = list(c.execute(
        "select end_reason, count(*) from sessions where end_reason is not null "
        "group by end_reason order by 2 desc"))
    if wiederbelebbar:
        print("  end_reason-Verteilung (beendete Sitzungen): %s"
              % ", ".join("%s=%d" % (g, n) for g, n in wiederbelebbar))
        verdaechtig = [g for g, _ in wiederbelebbar if g in RECOVERABLE_ENDS]
        if verdaechtig:
            hinweise.append("wiederaufnahmefaehige Enden vorhanden (%s): diese Zeilen holt die "
                            "Sitzungswiederaufnahme zurueck - sie sind nicht 'erledigt', "
                            "nur verlassen." % ", ".join(verdaechtig))
    leer = [z for z in zeilen if z["msgs"] == 0]
    if leer:
        hinweise.append("%d offene Sitzung(en) ohne eine einzige Nachricht - reine Huellen "
                        "(Gateway-Schluessel), Kandidat fuer `prune --never-active`." % len(leer))
    for h in hinweise:
        print("- %s" % h)
    if not hinweise:
        print("(nichts Auffaelliges)")


def main():
    ap = argparse.ArgumentParser(description="Offene Hermes-Sitzungen bestandsaufnehmen (nur lesend)")
    ap.add_argument("--db", help="state.db (Vorgabe: Agenten/Hermes/state.db)")
    ap.add_argument("--alle-profile", action="store_true",
                    help="zusaetzlich jede profiles/<name>/state.db")
    ap.add_argument("--minuten", type=int, default=30, help="Grenze 'lebendig' (Vorgabe 30)")
    ap.add_argument("--still-stunden", type=int, default=24, help="ab wann 'still' (Vorgabe 24)")
    ap.add_argument("--je", type=int, default=12, help="Sitzungen mit Inhalt zeigen (Vorgabe 12)")
    ap.add_argument("--kurz", action="store_true", help="nur Zahlen, Kandidaten, Vorschlag")
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

    print("# Offene Sitzungen - Bestandsaufnahme %s" % jetzt.strftime("%Y-%m-%d %H:%M"))
    print("# Dieses Skript liest nur. Archivieren/Loeschen tut der Agent nach dem Trockenlauf.")

    for pfad, name in pfade:
        if not pfad.is_file():
            print("\n=== %s ===\n(fehlende Datei: %s)" % (name, pfad))
            continue
        kopf("Sitzungsspeicher: %s  (%s)" % (name, pfad))
        c = verbinden(pfad)
        offen = zahlen(c, name)
        zeilen = offene_liste(c, jetzt, args.minuten, args.still_stunden)
        if not offen:
            c.close()
            continue
        lebendig = sum(1 for z in zeilen if z["lage"] == "lebendig")
        abgebrochen = sum(1 for z in zeilen if z["lage"] == "abgebrochen")
        still = sum(1 for z in zeilen if z["lage"] == "still")
        print("  Einordnung: lebendig (< %d min) %d   |   abgebrochen %d   |   still (> %d h) %d"
              % (args.minuten, lebendig, abgebrochen, args.still_stunden, still))
        if not args.kurz:
            kopf("Offene Sitzungen")
            print("  %-30s %-9s %-9s %5s %5s  %s" % ("id", "quelle", "alter", "msgs", "tools", "hinweis"))
            for z in zeilen:
                hinw = []
                if z["angeheftet"]:
                    hinw.append("ANGEHEFTET")
                if z["versteckt"]:
                    hinw.append("versteckt")
                if z["msgs"] == 0:
                    hinw.append("leer")
                if z["profil"]:
                    hinw.append("profil=%s" % z["profil"])
                print("  %-30s %-9s %-9s %5d %5d  %s"
                      % (z["id"][:30], z["quelle"][:9], alter_text(z["alter_min"]),
                         z["msgs"], z["tools"], " ".join(hinw) or "-"))
            kopf("Inhalt der juengsten offenen Sitzungen (Grundlage des Zusammenfuehrens)")
            for z in zeilen[:args.je]:
                print("- %s  %s  [%s, %s]" % (z["id"], z["titel"][:60] or "(ohne Titel)",
                                              z["quelle"], alter_text(z["alter_min"]).strip()))
                if z["cwd"]:
                    print("    Ordner: %s" % z["cwd"])
                for rolle, text in inhalt_je_sitzung(c, [z["id"]]).get(z["id"], {}).items():
                    print("    zuletzt %-9s %s" % (rolle + ":", text or "(nichts)"))
            kopf("Auffaelligkeiten")
            auffaelligkeiten(c, zeilen)
        kopf("Abschluss-Kandidaten")
        kandidaten(zeilen, args.still_stunden)
        c.close()


if __name__ == "__main__":
    main()
