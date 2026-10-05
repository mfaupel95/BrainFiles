"""Prueft einen Routing-Plan gegen TASKS.md: Vollstaendigkeit, Felder, Ordnung.

Aufruf (aus der Wurzel):
    python MaxHirn/Archiv/routing_plan_pruefen.py <plan.md>

Der Plan liegt in Agenten/Hermes/cache/scratch/ROUTING_PLAN_probe.md und ist
bewusst NICHT nach MaxHirn/Archiv gesichert - er ist ein Laufzeitstand einer
Sitzung. Dieses Pruefwerkzeug ist der dauerhafte Teil: es sagt, ob ein Plan
ueberhaupt alle offenen Punkte traegt.

Gegenprobe: mit --abschneiden N werden N Tabellenzeilen aus dem Plan geworfen -
das Pruefwerkzeug MUSS dann 'fehlend' melden. Ein Pruefer, der immer gruen
sagt, ist wertlos (Hausregel aus der Spur-Audit-Lektion T-322).
"""

import argparse
import collections
import json
import pathlib
import re
import sys

# Datei liegt <Wurzel>/MaxHirn/Archiv/ - drei Ebenen hoch ist die Wurzel
# (im Kanban-Worktree ist die Wurzel der Worktree-Ordner, nicht die Repo-Wurzel).
WURZEL = pathlib.Path(__file__).resolve().parents[2]
TASKS = WURZEL / "MaxHirn" / "Archiv" / "TASKS.md"

# Zwei Schreibweisen des Eintragskopfes im Haus:
#   Typ A  - [ ] **T-341 - Titel**   (Geviertstrich, der Hausstandard)
#   Typ B  - [ ] **T-335 - Titel**   (ASCII-Bindestrich, von fremden Sitzungen)
KOPF_A = re.compile(r"^\s*- \[(.)\]\s+\*\*(T-\d+) \u2014 ")
KOPF_B = re.compile(r"^\s*- \[(.)\]\s+\*\*(T-\d+) - ")
PLANZEILE = re.compile(r"^\| \d+ \|")
PLANFELDER = ("id", "titel", "quelle", "definition_of_done",
              "blocker", "aufwand", "profil", "begruendung")


def zeilen(text):
    b = text.encode("utf-8")
    nl = "\r\n" if b"\r\n" in b else "\n"
    return text.replace("\r\n", "\n").split("\n"), nl


def offene_eintraege(tasks_md):
    """Alle nicht abgearbeiteten Eintraege des Offen-Abschnitts.

    Fertig ist - [x]. - [?] (wartet auf Max) und - [!] (blockiert) sind OFFEN:
    sie stehen im Haus mit einem eigenen Zeichen da und sind keine Erledigung.
    """
    text = tasks_md.read_text(encoding="utf-8")
    lines, _ = zeilen(text)
    try:
        o = next(i for i, l in enumerate(lines) if l.strip() == "## Offen")
        e = next(i for i, l in enumerate(lines)
                 if i > o and l.strip() == "## Erledigt")
    except StopIteration:
        raise SystemExit("TASKS.md: Abschnitt '## Offen' oder '## Erledigt' fehlt")
    eintraege = {}
    for i, l in enumerate(lines[o:e]):
        if not re.match(r"^\s*- \[(.)\]", l):
            continue
        for kopf in (KOPF_A, KOPF_B):
            m = kopf.match(l)
            if m:
                eintraege[m.group(2)] = dict(
                    zeile=o + i + 1, zeichen=m.group(1),
                    titel=kopf.sub("", l).strip().rstrip("*").strip(),
                    typ=kopf.pattern)
                break
    return eintraege


def plan_items(plan_md, abschneiden=0):
    text = plan_md.read_text(encoding="utf-8")
    rows = [l for l in text.splitlines() if PLANZEILE.match(l)]
    if abschneiden:
        rows = rows[:-abschneiden] if abschneiden < len(rows) else []
    items = []
    for l in rows:
        zellen = [z.strip() for z in l.strip().strip("|").split("|")]
        eintrag = dict(zip(PLANFELDER, zellen))
        # Die T-ID steht je Plan-Schreibweise in der TITLE-Spalte ("Titel (T-341)"),
        # nicht in der id-Spalte - deshalb die ganze Zeile heranziehen.
        m = re.search(r"T-\d+", l)
        eintrag["tid"] = m.group(0) if m else None
        items.append(eintrag)
    return items


def pruefe(tasks_md, plan_md, abschneiden=0):
    eintraege = offene_eintraege(tasks_md)
    offen = {k: v for k, v in eintraege.items() if v["zeichen"] != "x"}
    items = plan_items(plan_md, abschneiden)
    plan_ids = [i["tid"] for i in items if i["tid"]]

    fehlend = sorted(set(offen) - set(plan_ids), key=lambda k: int(k[2:]))
    ueberzaehlig = sorted(set(plan_ids) - set(offen))
    doppelt = sorted(k for k, v in collections.Counter(plan_ids).items() if v > 1)
    leer = collections.Counter()
    for i in items:
        for feld in PLANFELDER:
            if not (i.get(feld) or "").strip():
                leer[feld] += 1

    zeichen = collections.Counter(v["zeichen"] for v in offen.values())
    typen = collections.Counter(
        "A" if v["typ"] == KOPF_A.pattern else "B" for v in offen.values())
    befunde = []
    if fehlend:
        nach_typ = collections.Counter(
            "A" if eintraege[k]["typ"] == KOPF_A.pattern else "B"
            for k in fehlend)
        befunde.append(
            f"{len(fehlend)} offene Punkte stehen NICHT im Plan "
            f"(Schreibweise A: {nach_typ['A']}, B: {nach_typ['B']})")
    if ueberzaehlig:
        befunde.append(f"{len(ueberzaehlig)} Planzeilen ohne offenen Punkt: {ueberzaehlig}")
    if doppelt:
        befunde.append(f"{len(doppelt)} T-IDs mehrfach im Plan: {doppelt}")
    if leer:
        befunde.append(f"leere Felder: {dict(leer)}")

    return dict(
        tasks=str(tasks_md), plan=str(plan_md),
        eintraege_offen_gesamt=len(eintraege),
        offen=len(offen), zeichen=dict(zeichen), schreibweisen=dict(typen),
        planzeilen=len(items), plan_ids_eindeutig=len(set(plan_ids)),
        fehlend=fehlend, ueberzaehlig=ueberzaehlig, doppelt=doppelt,
        leere_felder=dict(leer), befunde=befunde,
        ok=not befunde)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", nargs="?",
                    default=str(WURZEL / "Agenten" / "Hermes" / "cache"
                                / "scratch" / "ROUTING_PLAN_probe.md"))
    ap.add_argument("--abschneiden", type=int, default=0,
                    help="N Planzeilen entfernen - Gegenprobe auf den Pruefer")
    ap.add_argument("--tasks", default=str(TASKS))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ergebnis = pruefe(pathlib.Path(args.tasks), pathlib.Path(args.plan),
                      args.abschneiden)
    if args.json:
        print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
    else:
        print(f"TASKS.md  : {ergebnis['tasks']}")
        print(f"Plan      : {ergebnis['plan']}")
        print(f"offen     : {ergebnis['offen']} "
              f"(Zeichen {ergebnis['zeichen']}, Schreibweise "
              f"{ergebnis['schreibweisen']})")
        print(f"Planzeilen: {ergebnis['planzeilen']} / "
              f"{ergebnis['plan_ids_eindeutig']} eindeutige T-IDs")
        if ergebnis["fehlend"]:
            print(f"FEHLEND   : {len(ergebnis['fehlend'])}")
            print("            " + ", ".join(ergebnis["fehlend"]))
        for b in ergebnis["befunde"]:
            print("BEFUND    :", b)
        print("ERGEBNIS  :", "PLAN VOLLSTAENDIG" if ergebnis["ok"]
              else "PLAN UNVOLLSTAENDIG")
    return 0 if ergebnis["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())