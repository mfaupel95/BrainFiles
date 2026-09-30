"""Registry pruefen: Schema, Existenz der Skills, Sicherheitsregeln.

Der Validator ist die ausfuehrbare Haelfte der Spezifikation. Er prueft drei
Schichten und meldet jeden Verstoss mit Regel-ID:

  1. JSON-Schema (registry.schema.json) - Struktur, Pflichtfelder, Enums.
  2. Existenz - jeder "skill" muss als SKILL.md im Profil bzw. als Skript unter
     Agenten/Hermes/scripts wirklich liegen. Unbekannte Namen sind ein Fehler,
     kein Hinweis: eine Engine, die einen unbekannten Skill startet, tut etwas
     anderes als die Registry sagt.
  3. Sicherheitsregeln (S1-S7, siehe SPEZIFIKATION.md) gegen die im Inventar
     BELEGTE Nebenwirkungsklasse des Skills.

Aufruf:
  python scripts/registry_pruefen.py registry.example.yaml
  python scripts/registry_pruefen.py registry.example.yaml --json

Rueckgabe: 0 = sauber, 1 = Verstoss gefunden, 2 = Registry/Inventar fehlt.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_lesen import SKILLS  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve().parent
ZIEL = HIER.parent
SCHEMA = ZIEL / "registry.schema.json"
INVENTAR = ZIEL / "inventar.json"
SKRIPTE = [
    HIER,
    Path("C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes/scripts"),
]

# Welcher Modus ist bei welcher belegten Nebenwirkungsklasse hoechstens erlaubt.
MAX_MODUS = {
    "none": "auto",
    "local": "auto",
    "extern": "auto",
    "geld": "bestaetigung",
    "destruktiv": "bestaetigung",
}
MODUS_RANG = {"gesperrt": 0, "dry_run": 1, "bestaetigung": 2, "auto": 3}

# Aktionen, die nie im Modus auto stehen duerfen (unabhaengig vom Skill).
AUTO_VERBOTEN = {"handel", "git_push", "loeschen"}


def lade_inventar():
    if not INVENTAR.exists():
        return None
    daten = json.loads(INVENTAR.read_text(encoding="utf-8"))
    return {z["pfad"]: z for z in daten["skills"]}


def skill_pfad(regel):
    """Existenz pruefen. Rueckgabe (gefunden, inventar_schluessel_oder_None)."""
    name = regel.get("skill", "")
    art = regel.get("skill_art", "skill")
    if art == "skript":
        for basis in SKRIPTE:
            kandidat = basis / Path(name).name
            if kandidat.exists():
                return True, None
        return False, None
    kandidat = SKILLS / name / "SKILL.md"
    if kandidat.exists():
        return True, (Path(name) / "SKILL.md").as_posix()
    return False, None


def pruefe_regel(regel, inventar):
    """Liste von Verstoss-Strings fuer eine Regel."""
    fehler = []
    rid = regel.get("id", "<ohne id>")
    modus = regel.get("modus", "dry_run")
    aktionen = set(regel.get("erlaubte_aktionen", []))

    gefunden, schluessel = skill_pfad(regel)
    if not gefunden:
        fehler.append("%s: S1 Skill/Skript '%s' existiert nicht" % (rid, regel.get("skill")))
        return fehler

    # S2: verbotene Aktionen nie automatisch.
    heikel = aktionen & AUTO_VERBOTEN
    if heikel and modus == "auto":
        fehler.append("%s: S2 Aktion %s im Modus auto" % (rid, sorted(heikel)))

    # S3: Modus darf die Nebenwirkungsklasse des Skills nicht ueberschreiten.
    if schluessel and inventar is not None:
        eintrag = inventar.get(schluessel)
        if eintrag is None:
            fehler.append("%s: S3 Skill nicht im Inventar (inventar.py erneut laufen lassen)" % rid)
        else:
            klasse = eintrag["nebenwirkung"]
            grenze = MAX_MODUS[klasse]
            if MODUS_RANG[modus] > MODUS_RANG[grenze]:
                belege = ", ".join(
                    "%s:%s" % (b["fund"], b["zeile"]) for b in eintrag["belege"]
                ) or "kein Beleg"
                fehler.append(
                    "%s: S3 Modus %s ueber Grenze %s fuer Klasse %s (Belege: %s)"
                    % (rid, modus, grenze, klasse, belege)
                )

    # S4: Schreibpfade duerfen nicht die Vault-Wurzel oder ein Laufwerk sein.
    for pfad in regel.get("schreibpfade", []):
        if pfad.strip() in ("", ".", "/", "C:", "C:/", "O:", "O:/") or pfad.count("/") < 1:
            fehler.append("%s: S4 Schreibpfad '%s' ist zu weit" % (rid, pfad))

    # S5: jede auto-Regel braucht ein Rate-Limit mit endlichem Fenster.
    if modus == "auto":
        limit = regel.get("rate_limit")
        if limit is None:
            fehler.append("%s: S5 Modus auto ohne eigenes rate_limit" % rid)

    # S6: jede auto-Regel braucht eine Abbruchbedingung oder eine Eskalation.
    if modus == "auto" and not regel.get("abbruch") and not regel.get("eskalation"):
        fehler.append("%s: S6 Modus auto ohne abbruch und ohne eskalation" % rid)

    # S7: Zeit-Trigger unter 5 Minuten sind Dauerbetrieb, nicht Automatik.
    trigger = regel.get("trigger", {})
    if trigger.get("typ") == "zeit":
        minuten = trigger.get("bedingungen", {}).get("intervall_min")
        if minuten is not None and minuten < 5:
            fehler.append("%s: S7 Intervall %s min ist Dauerbetrieb" % (rid, minuten))

    return fehler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("registry", help="Pfad zur Registry-YAML")
    ap.add_argument("--json", dest="als_json", action="store_true")
    args = ap.parse_args()

    pfad = Path(args.registry)
    if not pfad.is_absolute():
        pfad = ZIEL / pfad
    if not pfad.exists():
        print("Registry fehlt: %s" % pfad)
        return 2
    if not SCHEMA.exists():
        print("Schema fehlt: %s" % SCHEMA)
        return 2

    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    schemafehler = []
    for f in sorted(validator.iter_errors(daten), key=lambda e: list(e.path)):
        ort = "/".join(str(t) for t in f.path) or "<wurzel>"
        schemafehler.append("%s: %s" % (ort, f.message))

    inventar = lade_inventar()
    inventar_hinweis = None
    if inventar is None:
        inventar_hinweis = "inventar.json fehlt - S3 ungeprueft (python scripts/inventar.py)"

    regelfehler = []
    ids = set()
    for regel in (daten or {}).get("regeln", []):
        rid = regel.get("id")
        if rid in ids:
            regelfehler.append("%s: doppelte Regel-ID" % rid)
        ids.add(rid)
        regelfehler.extend(pruefe_regel(regel, inventar))

    # Verkettungen muessen auf existierende IDs zeigen.
    for regel in (daten or {}).get("regeln", []):
        trigger = regel.get("trigger", {})
        if trigger.get("typ") == "skill_ergebnis":
            ziel = trigger.get("bedingungen", {}).get("regel")
            if ziel not in ids:
                regelfehler.append("%s: skill_ergebnis zeigt auf unbekannte Regel '%s'" % (regel.get("id"), ziel))

    ergebnis = {
        "registry": pfad.as_posix(),
        "regeln": len((daten or {}).get("regeln", [])),
        "schemafehler": schemafehler,
        "regelfehler": regelfehler,
        "hinweis": inventar_hinweis,
    }

    if args.als_json:
        print(json.dumps(ergebnis, indent=1, ensure_ascii=False))
    else:
        print("Registry: %s (%d Regeln)" % (ergebnis["registry"], ergebnis["regeln"]))
        if inventar_hinweis:
            print("Hinweis: " + inventar_hinweis)
        if not schemafehler and not regelfehler:
            print("OK - Schema, Existenz und Sicherheitsregeln erfuellt.")
        for f in schemafehler:
            print("SCHEMA  " + f)
        for f in regelfehler:
            print("REGEL   " + f)

    return 1 if (schemafehler or regelfehler) else 0


if __name__ == "__main__":
    raise SystemExit(main())
