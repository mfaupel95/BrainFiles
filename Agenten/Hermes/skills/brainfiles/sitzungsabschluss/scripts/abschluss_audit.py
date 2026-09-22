"""Abschluss-Audit fuer eine Sitzungsaufgabe - NUR LESEND.

Beantwortet die eine Frage des Sitzungsabschlusses: "Steht alles da, wo es
wiederfindbar ist - und ist die Aufgabenliste in Ordnung?" Es sammelt die Spur
der Sitzung (Git), prueft MaxHirn/Archiv/TASKS.md auf Formfehler und offene
Punkte, liest den Zustand von Wiki/Offen/Entscheidungen.md, sucht ENDE FEHLER in
Agenten/Routinen/logs/ und nennt Aufgaben ohne Fortschritt.

Es schreibt NICHTS, legt NICHTS an, kopiert NICHTS und braucht kein Netz.

Aufruf ueber das terminal-Werkzeug, aus der Repo-Wurzel:
    python Agenten/Hermes/skills/brainfiles/sitzungsabschluss/scripts/abschluss_audit.py

Optionen:
    --seit MINUTEN   "frisch angefasst" ab welchem Alter (Standard 360)
    --wurzel PFAD    abweichende Repo-Wurzel (sonst automatisch gesucht)
    --ruhig          nur Befunde und Zusammenfassung

Rueckgabewert: 0 = keine Befunde, 1 = mindestens ein Befund (Formfehler in der
Aufgabenliste, Reste im Arbeitsbaum, ENDE FEHLER).
"""
import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EINTRAG = re.compile(r"^- \[([ x~?!])\]\s+\*\*(T-\d+)\s*[—–-]\s*(.+?)\*\*\s*$")
ABSCHNITT = re.compile(r"^##\s+(.+?)\s*$")
JOURNAL = re.compile(r"ENDE FEHLER")
ERLEDIGT_DATUM = re.compile(r"Erledigt\s+\d{4}-\d{2}-\d{2}|Erledigt\s+\d{2}\.\d{2}\.\d{4}")


def wurzel_finden(start: Path) -> Path:
    p = start.resolve()
    for _ in range(10):
        if (p / "MaxHirn").is_dir() and (p / "Agenten").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise SystemExit("Repo-Wurzel nicht gefunden (MaxHirn/ + Agenten/ fehlen) - --wurzel nutzen")


def lauf(cmd, cwd=None, zeit=60):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           errors="replace", timeout=zeit, shell=False)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:                                    # noqa: BLE001
        return "<nicht lesbar: %s>" % e


def zeilen_lesen(pfad: Path):
    """Text und Zeilenende aus dem ROHEN Text ableiten (CRLF nicht umdrehen)."""
    roh = pfad.read_bytes()
    nl = "\r\n" if b"\r\n" in roh else "\n"
    return roh.decode("utf-8", "replace").split(nl), nl


class Bericht:
    def __init__(self, ruhig=False):
        self.befunde = []
        self.ruhig = ruhig

    def kopf(self, text):
        if not self.ruhig:
            print("\n=== %s ===" % text)

    def zeile(self, text):
        if not self.ruhig:
            print(text)

    def befund(self, text):
        self.befunde.append(text)
        print("BEFUND: %s" % text)


# ------------------------------------------------------------------ Git-Spur

def git_spur(w: Path, b: Bericht, minuten: int):
    b.kopf("Git: Spur der Sitzung")
    uncommittet = lauf(["git", "status", "--porcelain"], cwd=w).strip()
    if uncommittet:
        b.zeile(uncommittet)
        b.befund("%d uncommittete(r) Pfad(e) - vor dem Abschluss namentlich stagen"
                 % len(uncommittet.splitlines()))
    else:
        b.zeile("(Arbeitsbaum sauber)")
    b.zeile("--- letzte Commits ---")
    b.zeile(lauf(["git", "log", "--oneline", "-8"], cwd=w).strip())
    vorlauf = lauf(["git", "log", "--oneline", "@{u}..HEAD"], cwd=w).strip()
    if vorlauf.startswith("<?") or "fatal" in vorlauf or "error" in vorlauf:
        b.zeile("--- kein Upstream gesetzt (Push-Stand nicht messbar) ---")
    elif vorlauf:
        b.zeile("--- nicht gepusht ---")
        b.zeile(vorlauf)

    b.kopf("Frisch angefasst (juenger als %d min)" % minuten)
    grenze = dt.datetime.now() - dt.timedelta(minutes=minuten)
    frisch = []
    for zeile in uncommittet.splitlines():
        pfad = zeile[3:].strip().strip('"')
        if not pfad:
            continue
        p = w / pfad
        try:
            if p.is_file() and dt.datetime.fromtimestamp(p.stat().st_mtime) > grenze:
                frisch.append(pfad)
        except OSError:
            continue
    b.zeile("\n".join(frisch) if frisch else "(nichts frisch von mir angefasst)")
    return uncommittet


# ------------------------------------------------------------ Aufgabenliste

def tasks_audit(w: Path, b: Bericht):
    pfad = w / "MaxHirn" / "Archiv" / "TASKS.md"
    b.kopf("Aufgabenliste %s" % pfad.relative_to(w))
    if not pfad.is_file():
        b.befund("Aufgabenliste fehlt: %s" % pfad)
        return []
    zeilen, nl = zeilen_lesen(pfad)
    b.zeile("Zeilen: %d, Zeilenende: %s" % (len(zeilen), "CRLF" if nl == "\r\n" else "LF"))

    abschnitt = "(vor der ersten Ueberschrift)"
    im_block = False
    eintraege = []
    for nr, zeile in enumerate(zeilen, 1):
        if zeile.lstrip().startswith("```"):
            im_block = not im_block
            continue
        if im_block:
            continue
        m = ABSCHNITT.match(zeile)
        if m:
            abschnitt = m.group(1)
            continue
        m = EINTRAG.match(zeile)
        if m:
            eintraege.append({"status": m.group(1), "id": m.group(2),
                              "titel": m.group(3).strip(), "zeile": nr,
                              "abschnitt": abschnitt, "koerper": []})
            continue
        if eintraege and zeile.strip():
            eintraege[-1]["koerper"].append(zeile)

    ids = [e["id"] for e in eintraege]
    b.zeile("Eintraege: %d (ausserhalb von Code-Bloecken)" % len(eintraege))

    doppelt = sorted({i for i in ids if ids.count(i) > 1})
    if doppelt:
        b.befund("ID mehrfach vergeben: %s" % ", ".join(doppelt))
    nummern = sorted(int(i.split("-")[1]) for i in set(ids))
    if nummern:
        fehlend = [n for n in range(1, nummern[-1] + 1) if n not in nummern]
        b.zeile("IDs vergeben: %d (hoechste T-%03d)" % (len(nummern), nummern[-1]))
        if fehlend:
            b.zeile("  (nicht vergeben: %s - in Ordnung, wenn bewusst)"
                    % ", ".join("T-%03d" % n for n in fehlend))

    offen, erledigt, falsch_ort = [], [], []
    for e in eintraege:
        if e["abschnitt"] == "Offen":
            offen.append(e)
        elif e["abschnitt"] == "Erledigt":
            erledigt.append(e)
        else:
            falsch_ort.append(e)

    # Pflichtfelder gelten fuer OFFENE Punkte; erledigte Bloecke aelterer Bauart
    # tragen stattdessen nur das Erledigt-Datum - das ist kein Fehler.
    for e in offen:
        text = "\n".join(e["koerper"])
        if e["status"] == "x":
            if not ERLEDIGT_DATUM.search(text):
                b.befund("%s ist [x] ohne lesbares Erledigt-Datum" % e["id"])
            continue
        fehlt = [f for f in ("Kontext", "Angelegt") if f not in text]
        hat_schritt = "Naechster Schritt" in text or "Nächster Schritt" in text
        if e["status"] in " ~" and not hat_schritt:
            fehlt.append("Naechster Schritt")
        if e["status"] in "?!" and not hat_schritt and "Wartet auf" not in text:
            fehlt.append("Wartet auf (oder Naechster Schritt)")
        if fehlt:
            b.befund("%s (%s) ohne Pflichtfeld(er): %s"
                     % (e["id"], e["titel"][:40], ", ".join(fehlt)))

    ohne_datum = [e["id"] for e in erledigt
                  if e["status"] == "x" and not ERLEDIGT_DATUM.search("\n".join(e["koerper"]))]
    if ohne_datum:
        b.befund("erledigt ohne Datum: %s" % ", ".join(ohne_datum))

    for e in falsch_ort:
        b.befund("%s liegt im Abschnitt '%s' statt 'Offen'/'Erledigt'" % (e["id"], e["abschnitt"]))
    for e in offen:
        if e["status"] == "x":
            b.befund("%s ist [x], liegt aber noch unter '## Offen' - nach '## Erledigt' verschieben"
                     % e["id"])
    for e in erledigt:
        if e["status"] != "x":
            b.befund("%s ist [%s], liegt aber unter '## Erledigt'" % (e["id"], e["status"]))

    b.zeile("Offen: %d, Erledigt: %d" % (len(offen), len(erledigt)))
    heute = dt.date.today()
    schlafend = []
    for e in offen:
        treffer = re.search(r"Zuletzt:\s*(\d{4}-\d{2}-\d{2})", "\n".join(e["koerper"]))
        if not treffer:
            continue
        try:
            alter = (heute - dt.date.fromisoformat(treffer.group(1))).days
        except ValueError:
            continue
        if alter > 14:
            schlafend.append("%s (%d Tage, [%s]): %s"
                             % (e["id"], alter, e["status"], e["titel"][:50]))
    if schlafend:
        b.zeile("--- offen ohne Fortschritt > 14 Tage (Wiedervorlage) ---")
        b.zeile("\n".join(sorted(schlafend,
                                 key=lambda s: -int(re.search(r"\((\d+) Tage", s).group(1)))))
    return offen


# ------------------------------------------------------- Wiedervorlage/logs

def offen_seite(w: Path, b: Bericht):
    pfad = w / "MaxHirn" / "Wiki" / "Offen" / "Entscheidungen.md"
    b.kopf("Wiedervorlage %s" % pfad.relative_to(w))
    if not pfad.is_file():
        b.zeile("(fehlt - es gibt keine Wiedervorlage)")
        return
    zeilen, nl = zeilen_lesen(pfad)
    abschnitte = [z for z in zeilen if re.match(r"^##\s+\d+\.", z)]
    stand = [z for z in zeilen if z.startswith("updated:")]
    b.zeile("Punkte: %d, Zeilenende: %s"
            % (len(abschnitte), "CRLF" if nl == "\r\n" else "LF"))
    b.zeile("\n".join(abschnitte) if abschnitte else "(keine nummerierten Punkte)")
    b.zeile("Stand: %s" % (stand[0].strip() if stand else "(kein updated-Feld)"))
    if stand:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", stand[0])
        if m:
            alter = (dt.date.today() - dt.date.fromisoformat(m.group(1))).days
            if alter > 7:
                b.befund("Wiedervorlage ist %d Tage alt (updated: %s) - Stand mit dem Abschluss nachziehen"
                         % (alter, m.group(1)))


def log_fehler(w: Path, b: Bericht):
    b.kopf("Agenten/Routinen/logs/ - ENDE FEHLER")
    ordner = w / "Agenten" / "Routinen" / "logs"
    treffer = []
    if ordner.is_dir():
        for log in sorted(ordner.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:40]:
            try:
                text = log.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for zeile in text.splitlines():
                if JOURNAL.search(zeile):
                    treffer.append("%s: %s" % (log.name, zeile.strip()[:120]))
    if treffer:
        b.zeile("\n".join(treffer[-8:]))
        b.befund("%d ENDE-FEHLER-Zeile(n) in den Logs - gehoeren als Punkt in die Aufgabenliste"
                 % len(treffer))
    else:
        b.zeile("(keine ENDE FEHLER in den letzten 40 Logs)")


def checkliste():
    print("""
=== Checkliste fuer den Abschluss (in die Aufgabe schreiben) ===""")
    for zeile in (
        "erledigte Teilschritte - mit Beleg (Datei, Befehl, Commit-Hash)",
        "Messwerte und Zustaende - mit Datum",
        "Entscheidungen mit Begruendung - woertlich, nicht nacherzaehlt",
        "gefunden, aber nicht behoben - eigener Punkt [ ] oder [!]",
        "absichtlich NICHT angefasst - und warum",
        "warten auf Max - Wiki/Offen/Entscheidungen.md mit Messung + naechstem Schritt",
        "naechste Aktion - genau eine, ausfuehrbar in unter zwei Minuten",
    ):
        print("  [ ] %s" % zeile)
    print("""  Wohin: MaxHirn/Archiv/TASKS.md | MaxHirn/Wiki/Offen/Entscheidungen.md
  Vorlage: templates/aufgaben-eintrag.md (skill_view)""")


def main():
    ap = argparse.ArgumentParser(description="Abschluss-Audit (nur lesend)")
    ap.add_argument("--seit", type=int, default=360,
                    help="frisch angefasst ab diesem Alter in Minuten")
    ap.add_argument("--wurzel", default=None, help="abweichende Repo-Wurzel")
    ap.add_argument("--ruhig", action="store_true", help="nur Befunde und Zusammenfassung")
    args = ap.parse_args()

    w = Path(args.wurzel).resolve() if args.wurzel else wurzel_finden(Path.cwd())
    b = Bericht(ruhig=args.ruhig)
    print("Abschluss-Audit (nur lesend) - Wurzel: %s" % w)
    git_spur(w, b, args.seit)
    tasks_audit(w, b)
    offen_seite(w, b)
    log_fehler(w, b)
    if not args.ruhig:
        checkliste()
    print("\n=== Zusammenfassung ===")
    if b.befunde:
        print("AUDIT: %d Befund(e) - jeden in der Abschlussmeldung benennen" % len(b.befunde))
        return 1
    print("AUDIT: 0 Befunde")
    return 0


if __name__ == "__main__":
    sys.exit(main())