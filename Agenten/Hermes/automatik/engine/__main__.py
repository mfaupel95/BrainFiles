"""CLI der Auto-Ausfuehrungs-Engine.

    python -m engine pruefen [registry.yaml]     Registry laden und anzeigen
    python -m engine tick [registry.yaml]        einmal Quellen fragen + abarbeiten
    python -m engine lauf <regel-id> [registry]  eine Regel von Hand ausloesen
    python -m engine log [-n 20]                 letzte Laeufe anzeigen
    python -m engine antwort <regel-id> ja|nein  Bestaetigung beantworten
    python -m engine entsperren <regel-id>       Dauersperre aufheben

'tick' ist der Normalbetrieb: der Hermes-Cron ruft ihn auf (script + no_agent),
die Engine fragt alle Quellen, arbeitet die Treffer nach Prioritaet ab und
beendet sich. Kein Dauerdienst - der Rechner geht schlagartig aus, und ein
Prozess, der nichts festhaelt, hat dabei nichts zu verlieren.

--nur-lesen erzwingt fuer diesen Aufruf dry_run, auch wenn Regeln auto sagen.
Das ist der sichere Weg, eine geaenderte Registry im Betrieb anzusehen.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys

from . import pfade, protokoll, registry, steuerung, zustand
from .quellen import Ausloeser, sammeln


def _registry_laden(pfad, pruefen=True):
    try:
        return registry.laden(pfad, pruefen=pruefen)
    except registry.RegistryFehler as e:
        sys.stderr.write("Registry abgelehnt: %s\n" % e.meldung)
        for d in e.details:
            if d:
                sys.stderr.write("  - %s\n" % d)
        return None


def _als_dry_run(reg):
    for r in reg.regeln:
        if r.modus == "auto":
            r.modus = "dry_run"
    return reg


def befehl_pruefen(args) -> int:
    reg = _registry_laden(args.registry)
    if reg is None:
        return 1
    print("Registry %s  Version %s  %d Regeln" % (reg.pfad, reg.version, len(reg.regeln)))
    for r in reg.regeln:
        print("  [%3d] %-32s %-14s %-13s %s" % (
            r.prioritaet, r.id, r.trigger_typ, r.modus, r.skill))
    return 0


def befehl_tick(args) -> int:
    reg = _registry_laden(args.registry)
    if reg is None:
        return 1
    if args.nur_lesen:
        reg = _als_dry_run(reg)

    with zustand.offen() as con:
        entfernt = zustand.belegung_aufraeumen(con)
        if entfernt:
            print("verwaiste Belegungen entfernt: %d" % entfernt)

        treffer = sammeln(reg, con)
        if not treffer:
            print("keine Ausloeser")
            return 0

        for a in treffer:
            r = reg.nach_id(a.regel_id)
            if r is None:
                continue
            eintrag = steuerung.ausfuehren(r, a, con, reg.version)
            print("%-32s %-14s %-16s %s" % (
                a.regel_id, a.typ, eintrag["ergebnis"],
                eintrag.get("abbruchgrund") or a.ausgeloest_durch))
    return 0


def befehl_lauf(args) -> int:
    reg = _registry_laden(args.registry)
    if reg is None:
        return 1
    if args.nur_lesen:
        reg = _als_dry_run(reg)
    r = reg.nach_id(args.regel_id)
    if r is None:
        sys.stderr.write("Regel unbekannt: %s\n" % args.regel_id)
        return 1
    a = Ausloeser(regel_id=r.id, typ=r.trigger_typ,
                  ausgeloest_durch="von Hand (CLI)", prioritaet=r.prioritaet)
    with zustand.offen() as con:
        eintrag = steuerung.ausfuehren(r, a, con, reg.version)
    print(json.dumps(eintrag, ensure_ascii=False, indent=1))
    return 0 if eintrag["ergebnis"] in ("erfolg", "dry_run") else 1


def befehl_log(args) -> int:
    zeilen = protokoll.zeilen_lesen(letzte=args.anzahl)
    if not zeilen:
        print("kein Log unter %s" % pfade.log_datei())
        return 0
    for z in zeilen:
        print("%s %-30s %-13s %-16s %6sms %s" % (
            z.get("zeit", "")[:19], z.get("regel_id", ""), z.get("trigger_typ", ""),
            z.get("ergebnis", ""), z.get("dauer_ms", 0),
            z.get("abbruchgrund") or z.get("ausgeloest_durch", "")))
    return 0


def befehl_antwort(args) -> int:
    with zustand.offen() as con:
        con.execute(
            "UPDATE bestaetigungen SET antwort=? WHERE id=("
            " SELECT id FROM bestaetigungen WHERE regel_id=? AND antwort IS NULL"
            " ORDER BY id DESC LIMIT 1)",
            (args.wert, args.regel_id))
        con.commit()
    print("Antwort '%s' fuer %s vermerkt" % (args.wert, args.regel_id))
    return 0


def befehl_entsperren(args) -> int:
    with zustand.offen() as con:
        zustand.entsperren(con, args.regel_id)
    print("Dauersperre fuer %s aufgehoben" % args.regel_id)
    return 0


def bauen() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m engine",
                                description="Auto-Ausfuehrungs-Engine fuer Skills")
    p.add_argument("--nur-lesen", action="store_true", dest="nur_lesen",
                   help="alle auto-Regeln fuer diesen Aufruf als dry_run behandeln")
    unter = p.add_subparsers(dest="befehl", required=True)

    a = unter.add_parser("pruefen", help="Registry laden und Regeln anzeigen")
    a.add_argument("registry", nargs="?")
    a.set_defaults(fn=befehl_pruefen)

    b = unter.add_parser("tick", help="Quellen fragen und Treffer abarbeiten")
    b.add_argument("registry", nargs="?")
    b.set_defaults(fn=befehl_tick)

    c = unter.add_parser("lauf", help="eine Regel von Hand ausloesen")
    c.add_argument("regel_id")
    c.add_argument("registry", nargs="?")
    c.set_defaults(fn=befehl_lauf)

    d = unter.add_parser("log", help="letzte Laeufe anzeigen")
    d.add_argument("-n", "--anzahl", type=int, default=20)
    d.set_defaults(fn=befehl_log)

    e = unter.add_parser("antwort", help="offene Bestaetigung beantworten")
    e.add_argument("regel_id")
    e.add_argument("wert", choices=["ja", "nein"])
    e.set_defaults(fn=befehl_antwort)

    f = unter.add_parser("entsperren", help="Dauersperre einer Regel aufheben")
    f.add_argument("regel_id")
    f.set_defaults(fn=befehl_entsperren)
    return p


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    args = bauen().parse_args(argv)
    return int(args.fn(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
