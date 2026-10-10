#!/usr/bin/env python3
"""Zweige und Worktrees im BrainFiles-Baum messen und verwaiste entfernen.

WARUM ALS WERKZEUG: Max verliert den Ueberblick ueber Branches. Seit vier Wochen
waechst die Liste still (3 lokale `claude/*`, 4 auf dem Remote, 1 verwaister
Worktree unter C:/tmp). Kein Zweig davon traegt erkennbare eigene Arbeit - aber
ohne Messung ist das eine Behauptung, und genau diese Behauptung hat schon
falsche Entscheidungen ausgeloest. Das Skript macht die Rechnung und schreibt sie
auf; es ENTSCHEIDET nichts ohne Nachweis.

WAS ES TUT (je Zweig, in dieser Reihenfolge)
  1. Kandidaten sammeln: alle lokalen Zweige ausser master und zwischenstand,
     plus alle Heads auf `origin` (per `git ls-remote`, damit auch Zweige
     auftauchen, die lokal niemand kennt).
  2. Nachmessen, je Zweig, mit DREI unabhaengigen Zeugen:
       - `git merge-base --is-ancestor <sha> master` -> ist die Arbeit in master?
       - `git rev-list --left-right --count master...<zweig>` -> Vorlauf/Tot
       - `git cherry master <zweig>` -> Vorlauf-Commits MIT '-' = per Patch-ID
         bereits in master enthalten, MIT '+' = wirklich nicht enthalten.
     Der dritte Zeuge ist der entscheidende: ein Commit kann per sha allein
     'vor master' sein und inhaltlich trotzdem drinstehen (gemessen 30.09.2026:
     `aeeac180` auf einem claude-Zweig war inhaltlich bereits als `6ccb94e4` in
     master, der sha-Vergleich allein haette 'behalten' gesagt).
  3. Worktrees zaehlen und pruefen: `git worktree list --porcelain`, je Pfad
     `git -C <pfad> status --porcelain` (leer = keine uncommittete Arbeit).
     Ein Worktree zaehlt als verwaist, wenn sein HEAD in master steckt UND sein
     Arbeitsbaum sauber ist.
  4. KLASSE vergeben (siehe unten), nur belegte Befunde ausgeben.

KLASSEN
  `behalten`      - hat echten Vorlauf (>=1 Commit mit '+' bei cherry).
  `entfernen`     - HEAD in master, Vorlauf-Commits alle mit '-' bei cherry.
  `worktree`      - Zeile fuer einen Worktree mit Status, separat ausgewiesen.

WAS ES NICHT TUT
  - NICHTS loeschen ohne `--entfernen`. Ohne den Schalter wird nur gemessen.
  - `git branch -D` niemals blind. Ein Zweig darf nur weg, wenn BEIDE
    Gegenproben gruen sind: `merge-base --is-ancestor` und cherry ohne '+'.
    Sonst meldet das Skript `behalten` und fasst nichts an.
  - master und zwischenstand nie anfassen (zwischenstand = Nachtsicherung der
    Routine, siehe Wissen/Routinen.md).
  - Kein Merge, kein Rebase, kein Cherry-Pick, kein Push ohne `--push`.
  - Nie `git worktree remove` an einem Worktree mit uncommitteter Arbeit.

Gegenprobe gegen einen Zwischenschritt (der ganze Zweck dieses Skripts): der
Aufruf OHNE `--entfernen` muss dieselbe Klassifikation liefern wie der Aufruf
DANACH mit `--entfernen`. Weicht sie ab, hat der Entfernschritt etwas mitgenommen,
das die Messung nicht vorher gesehen hat - dann ist es ein Fund, nicht ein Erfolg.

Aufruf (aus der Repo-Wurzel oder von ueberall):
    python Agenten/Werkzeuge/zweige.py               # nur messen (Vorgabe)
    python Agenten/Werkzeuge/zweige.py --entfernen  # belegte Zweige/Worktrees weg
    python Agenten/Werkzeuge/zweige.py --entfernen --push   # + Remote-Aeste
    python Agenten/Werkzeuge/zweige.py --json       # fuer Wachen/Anhaenger
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

GESCHUETZT = {"master", "zwischenstand"}
BEHALTEN = "behalten"
ENTFERNEN = "entfernen"
INHALT_DRIN = "inhaltlich drin, Kopf nicht"
TIMEOUT_S = 60


class GitFehler(RuntimeError):
    pass


def wurzel():
    """Repo-Wurzel bestimmen, ohne einen Pfad zu raten.

    `HERMES_HOME` zeigt auf Agenten/Hermes, also zwei Ebenen zu tief fuer
    root-relative Pfade - die Falle steht in der Wurzel-AGENTS.md. Deshalb wird
    von dort aus aufwaerts nach `.git` gesucht.
    """
    kandidaten = []
    home = os.environ.get("HERMES_HOME")
    if home:
        kandidaten.append(home)
    kandidaten.append(os.path.dirname(os.path.abspath(__file__)))
    kandidaten.append(os.getcwd())
    for start in kandidaten:
        cur = os.path.abspath(start)
        for _ in range(6):
            if os.path.isdir(os.path.join(cur, ".git")):
                return cur
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
    raise GitFehler("keine .git-Wurzel gefunden (HERMES_HOME=%s, cwd=%s)"
                    % (home, os.getcwd()))


def git(*args, cwd=None, erlaube_fehler=False):
    """Ein git-Aufruf mit geprueftem Exitcode."""
    proc = subprocess.run(
        ["git"] + list(args),
        cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=TIMEOUT_S,
    )
    if proc.returncode != 0 and not erlaube_fehler:
        raise GitFehler("git %s -> %d: %s" % (
            " ".join(args), proc.returncode,
            (proc.stderr or proc.stdout).strip()[:400]))
    return proc


def _zeilen(text):
    return [z for z in (text or "").splitlines() if z.strip()]


def mess_pfad(wurzelverz, pfad):
    """Alle drei Zeugen fuer EINEN Zweig. None bedeutet: der Zweig ist nicht
    messbar (Ref existiert lokal nicht) - das ist ein eigener Befund."""
    rev = git("rev-parse", pfad, cwd=wurzelverz, erlaube_fehler=True)
    if rev.returncode != 0:
        return None
    sha = rev.stdout.strip()

    anc = git("merge-base", "--is-ancestor", sha, "master",
              cwd=wurzelverz, erlaube_fehler=True)
    in_master = anc.returncode == 0

    lr = git("rev-list", "--left-right", "--count", "master..." + pfad,
             cwd=wurzelverz, erlaube_fehler=True)
    vorlauf, tot = 0, 0
    if lr.returncode == 0:
        teile = lr.stdout.split()
        if len(teile) == 2:
            tot, vorlauf = int(teile[0]), int(teile[1])

    ch = git("cherry", "master", pfad, cwd=wurzelverz, erlaube_fehler=True)
    echt_neu, schon_dr = 0, 0
    for z in _zeilen(ch.stdout):
        if z.startswith("+"):
            echt_neu += 1
        elif z.startswith("-"):
            schon_dr += 1

    log = git("log", "-1", "--format=%h %ci %s", pfad,
              cwd=wurzelverz, erlaube_fehler=True)
    kopf = log.stdout.strip() if log.returncode == 0 else ""

    # Zwei unabhaengige Fragen getrennt beantworten, weil sie selten gleich
    # ausgehen: (a) IST DER INHALT in master? -> cherry ohne '+'
    # (b) STECKT DER KOPF drin? -> merge-base --is-ancestor
    # Gemessen 30.09.2026 genau der Fall, wo (a) ja und (b) nein ist: der
    # Commit liegt inhaltlich drin, aber mit einer anderen sha (Rebase oder
    # Cherry-Pick einer Fremdsitzung). Inhaltlich wegwerfbar - aber `branch -d`
    # verweigert, und `-D` waere an dieser Stelle blind. Deshalb die dritte
    # Klasse: inhaltlich drin wird gemeldet, NICHT automatisch entfernt.
    if echt_neu:
        klasse = BEHALTEN
    elif in_master:
        klasse = ENTFERNEN
    else:
        klasse = INHALT_DRIN
    return {
        "pfad": pfad,
        "kurz": sha[:8],
        "in_master": in_master,
        "vorlauf": vorlauf,
        "tot": tot,
        "echt_neu": echt_neu,
        "schon_dr": schon_dr,
        "klasse": klasse,
        "kopf": kopf,
        "belegt_weg": (in_master and echt_neu == 0),
    }


def zweige_lokal(wurzelverz):
    out = git("for-each-ref", "--format=%(refname:short)",
              "refs/heads", cwd=wurzelverz).stdout
    return [z for z in _zeilen(out) if z not in GESCHUETZT]


def zweige_remote(wurzelverz):
    ls = git("ls-remote", "--heads", "origin", cwd=wurzelverz,
             erlaube_fehler=True)
    if ls.returncode != 0:
        return []
    namen = []
    for z in _zeilen(ls.stdout):
        if "\trefs/heads/" in z:
            n = z.split("\trefs/heads/", 1)[1].strip()
            if n and n not in GESCHUETZT:
                namen.append(n)
    return namen


def _worktree_eintraege(wurzelverz):
    """`git worktree list --porcelain` liefert je Baum einen Block aus
    `worktree`-/`HEAD`-/`branch`-Zeilen, getrennt durch LEERZEILEN. Ein Block
    wird deshalb VOLLSTAENDIG gelesen und erst dann ausgewertet: Zeile fuer
    Zeile gelesen haette der Pfad des naechsten Blocks den Eintrag des
    vorigen ueberschrieben (gemessen am 04.10.2026 - es kam genau EIN
    Worktree heraus, der reale zweite blieb unsichtbar)."""
    ls = git("worktree", "list", "--porcelain", cwd=wurzelverz,
             erlaube_fehler=True)
    if ls.returncode != 0:
        return []
    bloecke, aktuell = [], []
    for z in (ls.stdout or "").splitlines():
        if z.strip():
            aktuell.append(z.strip())
            continue
        if aktuell:
            bloecke.append(aktuell)
            aktuell = []
    if aktuell:
        bloecke.append(aktuell)

    eintraege = []
    for block in bloecke:
        pfad = zweig = None
        for z in block:
            if z.startswith("worktree "):
                pfad = z[len("worktree "):].strip()
            elif z.startswith("branch ") and not z[len("branch "):].strip().endswith("(detached)"):
                zweig = z[len("branch "):].strip()
        if pfad:
            eintraege.append([pfad, zweig])
    return eintraege


def _pfad_norm(p):
    """Pfade vergleichen, nicht Zeichenketten: git meldet Worktree-Pfade mit
    Schraegstrich und kleiner Schreibung des Laufwerks, `tempfile` und
    `os.path.join` liefern Backslash und das Laufwerk wie vorgefunden. Ein
    reiner `==`-Vergleich meldet einen vorhandenen Worktree als fehlend -
    gemessen am 04.10.2026 mit genau diesem IndexError."""
    try:
        key = os.path.normcase(os.path.realpath(p))
    except OSError:
        key = os.path.normcase(os.path.abspath(p))
    return key.rstrip("/\\")


def worktrees(wurzelverz):
    ergebnis = []
    haupt_key = _pfad_norm(wurzelverz)
    for pfad, zweig in _worktree_eintraege(wurzelverz):
        ist_haupt = _pfad_norm(pfad) == haupt_key
        if ist_haupt:
            ergebnis.append({"pfad": pfad, "zweig": zweig, "haupt": True,
                             "sauber": True, "in_master": True,
                             "geaendert": 0, "klasse": BEHALTEN})
            continue
        # VERWAIST-ERKENNUNG (10.10.2026): der Ordner kann weg sein, obwohl
        # `os.path.isdir` True meldet - unter MSYS/git-bash loest Python den
        # Pfad anders auf als nativ (gemessen 10.10.2026: init-4ede6f war
        # nativ weg, isdir sagte True). Der robuste Zeuge ist `git -C <pfad>`
        # selbst: schlaegt es fehl, ist der Eintrag verwaist. `git worktree
        # prune` bereinigt solche Eintraege NICHT immer - also melden.
        # ZWEI unabhaengige Zeugen, weil MSYS/git-bash Pfade anders aufloest
        # als nativ (gemessen 10.10.2026: init-4ede6f war nativ weg, isdir
        # sagte True). Einer von beiden schlaegt fehl -> verwaist.
        probe = subprocess.run(["git", "-C", pfad, "rev-parse", "--git-dir"],
                                capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=TIMEOUT_S)
        if probe.returncode != 0 or not os.path.isdir(pfad):
            ergebnis.append({
                "pfad": pfad, "zweig": zweig, "haupt": False, "kurz": "",
                "sauber": True, "geaendert": 0, "in_master": False,
                "lage_ok": False, "detached": zweig is None, "verwaist": True,
                "klasse": BEHALTEN,
            })
            continue
        st = subprocess.run(["git", "-C", pfad, "status", "--porcelain"],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=TIMEOUT_S)
        geaendert = len(_zeilen(st.stdout))
        head = subprocess.run(["git", "-C", pfad, "rev-parse", "HEAD"],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=TIMEOUT_S)
        sha = head.stdout.strip()
        anc = None
        if sha:
            anc = git("merge-base", "--is-ancestor", sha, "master",
                      cwd=wurzelverz, erlaube_fehler=True)
        in_master = bool(anc and anc.returncode == 0)
        # LAGE-PRUEFUNG (10.10.2026): ein Worktree gehoert unter `.worktrees/`
        # neben der Wurzel, NIE in den Hauptbaum hinein. Gemessen 10.10.2026:
        # `Agenten/.claude/worktrees/sweet-heisenberg-85efc5` lag im Hauptbaum
        # und blieb unentdeckt, bis er aufgeraeumt wurde. Ein Worktree im
        # Hauptbaum ist ein Fehler, auch wenn er sauber ist.
        wt_root = os.path.join(wurzelverz, ".worktrees")
        lage_ok = _pfad_norm(pfad).startswith(_pfad_norm(wt_root))
        # detached HEAD: ein Worktree ohne Zweig (branch-Zeile fehlt) ist
        # ebenfalls ein Fehler - er gehoert zu einem Zweig.
        detached = zweig is None
        ergebnis.append({
            "pfad": pfad, "zweig": zweig, "haupt": False, "kurz": sha[:8],
            "sauber": geaendert == 0, "geaendert": geaendert,
            "in_master": in_master, "lage_ok": lage_ok, "detached": detached,
            "klasse": ENTFERNEN if (in_master and geaendert == 0) else BEHALTEN,
        })
    return ergebnis


def entfernen(wurzelverz, befunde, push=False, protokoll=print):
    """Nur entfernen, was die Messung als belegt_weg ausgewiesen hat."""
    gemacht = []
    for w in befunde.get("worktrees", []):
        if w.get("haupt") or w.get("klasse") != ENTFERNEN:
            continue
        protokoll("  Worktree weg: %s (Zweig %s, HEAD %s in master, Arbeitsbaum leer)"
                  % (w["pfad"], w.get("zweig"), w.get("kurz")))
        r = git("worktree", "remove", "--force", w["pfad"],
                cwd=wurzelverz, erlaube_fehler=True)
        if r.returncode != 0:
            r = git("worktree", "remove", w["pfad"], cwd=wurzelverz,
                    erlaube_fehler=True)
            if r.returncode != 0:
                protokoll("    FEHLGESCHLAGEN: %s" % (r.stderr or "").strip()[:200])
                continue
        gemacht.append("worktree " + w["pfad"])
    git("worktree", "prune", cwd=wurzelverz, erlaube_fehler=True)

    for z in befunde.get("lokal", []):
        if not z.get("belegt_weg"):
            continue
        protokoll("  Zweig weg (lokal): %s (HEAD %s, %d Commit(s) vor master, alle per Patch-ID enthalten)"
                  % (z["pfad"], z["kurz"], z["vorlauf"]))
        r = git("branch", "-d", z["pfad"], cwd=wurzelverz, erlaube_fehler=True)
        if r.returncode != 0:
            r = git("branch", "-D", z["pfad"], cwd=wurzelverz, erlaube_fehler=True)
            if r.returncode != 0:
                protokoll("    FEHLGESCHLAGEN: %s" % (r.stderr or "").strip()[:200])
                continue
        gemacht.append("lokal " + z["pfad"])

    if push:
        for z in befunde.get("remote", []):
            if not z.get("belegt_weg"):
                continue
            protokoll("  Zweig weg (Remote): origin/%s (HEAD %s, %d Commit(s) vor master, alle enthalten)"
                      % (z["pfad"], z["kurz"], z["vorlauf"]))
            r = git("push", "origin", "--delete", z["pfad"], cwd=wurzelverz,
                    erlaube_fehler=True)
            if r.returncode != 0:
                protokoll("    FEHLGESCHLAGEN: %s" % (r.stderr or "").strip()[:200])
                continue
            gemacht.append("remote " + z["pfad"])
    return gemacht


def bericht(befunde, entwfernt=False):
    z = []
    z.append("Zweige: %d lokal (ausser master/zwischenstand), %d auf origin"
             % (len(befunde["lokal"]), len(befunde["remote"])))
    for titel, liste in (("LOKAL", befunde["lokal"]), ("REMOTE", befunde["remote"])):
        if not liste:
            continue
        z.append("")
        z.append("%s:" % titel)
        for e in liste:
            z.append("  %-46s %s  %s" % (e["pfad"], e["kurz"], e["kopf"][:60]))
            z.append("      in master: %s | vor master: %d | echter Vorlauf: %d | per Patch-ID schon drin: %d -> %s"
                     % ("ja" if e["in_master"] else "NEIN", e["vorlauf"],
                        e["echt_neu"], e["schon_dr"], e["klasse"]))
    z.append("")
    z.append("Worktrees: %d" % len(befunde["worktrees"]))
    for w in befunde["worktrees"]:
        if w.get("haupt"):
            z.append("  %s  (Hauptbaum, bleibt)" % w["pfad"])
        else:
            z.append("  %-46s %s  in master: %s | geaendert: %d -> %s"
                     % (w["pfad"], w.get("kurz"), "ja" if w["in_master"] else "NEIN",
                        w["geaendert"], w["klasse"]))
            if not w.get("lage_ok", True):
                z.append("      FEHLER: Worktree liegt NICHT unter .worktrees/ "
                         "(gehoert neben die Wurzel, nicht in den Hauptbaum)")
            if w.get("detached"):
                z.append("      FEHLER: detached HEAD - Worktree gehoert zu einem Zweig")
            if w.get("verwaist"):
                z.append("      FEHLER: verwaister Worktree-Eintrag - Ordner fehlt, "
                         "git registriert ihn noch (prune hat ihn nicht bereinigt)")
    if entwfernt:
        z.append("")
        z.append("ENTFERNT (%d): %s" % (len(befunde.get("entfernt", [])),
                                        ", ".join(befunde.get("entfernt", [])) or "-"))
    offen = [e["pfad"] for e in befunde["lokal"] + befunde["remote"]
             if e["klasse"] == BEHALTEN]
    if offen:
        z2 = []
        z2.append("MIT ECHTEM VORLAUF, NICHT ANFASSEN: %s" % ", ".join(offen))
        return "\n".join(z + z2)
    grenz = [e["pfad"] for e in befunde["lokal"] + befunde["remote"]
             if e["klasse"] == INHALT_DRIN]
    if grenz:
        z2 = []
        z2.append("INHALT DRIN, KOPF NICHT (andere sha - `branch -d` verweigert, "
                  "`-D` waere blind; Handentscheidung noetig): %s" % ", ".join(grenz))
        return "\n".join(z + z2)
    return "\n".join(z)


def sammle(wurzelverz):
    befunde = {"lokal": [], "remote": [], "worktrees": []}
    for name in zweige_lokal(wurzelverz):
        m = mess_pfad(wurzelverz, name)
        if m:
            befunde["lokal"].append(m)
    for name in zweige_remote(wurzelverz):
        m = mess_pfad(wurzelverz, "origin/" + name)
        if m:
            m["pfad"] = name
            befunde["remote"].append(m)
    befunde["worktrees"] = worktrees(wurzelverz)
    return befunde


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Zweige und Worktrees im BrainFiles-Baum messen und verwaiste entfernen.")
    ap.add_argument("--entfernen", action="store_true",
                    help="belegte Zweige und Worktrees entfernen (Vorgabe: nur messen)")
    ap.add_argument("--push", action="store_true",
                    help="beim Entfernen auch die Remote-Aeste loeschen")
    ap.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    ap.add_argument("--wurzel", default=None, help="Repo-Wurzel (Vorgabe: selbst finden)")
    args = ap.parse_args(argv)

    w = args.wurzel or wurzel()
    befunde = sammle(w)
    entfernt = []
    if args.entfernen:
        entfernt = entfernen(w, befunde, push=args.push)
    befunde["entfernt"] = entfernt

    if args.json:
        print(json.dumps(befunde, ensure_ascii=False, indent=2))
        return 0
    print("Wurzel: %s" % w)
    print("gemessen: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    print(bericht(befunde, entwfernt=args.entfernen))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GitFehler as e:
        print("FEHLER: %s" % e, file=sys.stderr)
        sys.exit(1)