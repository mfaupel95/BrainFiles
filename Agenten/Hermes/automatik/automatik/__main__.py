"""CLI der Kopplungsschicht.

    python -m automatik durchgang [--probe]   Log lesen, reagieren, Rueckweg gehen
    python -m automatik nachholen [--probe]   nur den Rueckweg (Sperren, Nachlaeufe)
    python -m automatik stand                 Marken, offene Nachlaeufe, Sperren

'durchgang' ist der Normalbetrieb und laeuft nach jedem Engine-Tick. Die
Reihenfolge Tick -> Durchgang ist Absicht: der Tick schreibt Lauf-Zeilen, der
Durchgang beantwortet sie. Beide sind kurze Prozesse ohne Speicherzustand -
derselbe Grund wie in BETRIEB.md (der Rechner geht schlagartig aus).

--probe entscheidet vollstaendig, meldet nichts und startet nichts. Das ist der
sichere Weg, eine geaenderte reaktionen.yaml oder Registry anzusehen.

Ausgabe-Haltung wie beim Cron-Tick der Engine: nur schreiben, wenn wirklich
etwas passiert ist. Eine leere Ausgabe heisst 'nichts zu melden' und wird vom
Hermes-Cron nicht zugestellt. Fehler gehoeren dagegen IMMER in die Ausgabe -
eine Automatik, die ihren eigenen Ausfall verschweigt, ist schlimmer als keine.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from . import kopplung, pfade

pfade.module_einhaengen()

from engine import registry as engine_registry  # noqa: E402
from engine import zustand  # noqa: E402


def _zeile(text: str) -> None:
    sys.stdout.write(text + "\n")


def _durchgang(argumente: argparse.Namespace) -> int:
    ergebnis = kopplung.durchgang(probe=argumente.probe, pruefen=not argumente.ohne_pruefung)
    gemeldet = [r for r in ergebnis.reaktionen if r.get("kanaele")]
    etwas = bool(ergebnis.reaktionen or ergebnis.nachlaeufe or ergebnis.sperren or ergebnis.fehler)

    if argumente.json:
        _zeile(json.dumps(
            {
                "probe": argumente.probe,
                "gelesen": ergebnis.gelesen,
                "reaktionen": ergebnis.reaktionen,
                "nachlaeufe": ergebnis.nachlaeufe,
                "sperren": ergebnis.sperren,
                "fehler": ergebnis.fehler,
            },
            ensure_ascii=False,
        ))
        return 1 if ergebnis.fehler else 0

    if not etwas:
        return 0

    kopf = "Kopplung (Probe)" if argumente.probe else "Kopplung"
    _zeile("%s: %d neue Lauf-Zeile(n), %d gemeldet" % (kopf, ergebnis.gelesen, len(gemeldet)))
    for r in ergebnis.reaktionen:
        _zeile("  %s -> %s%s%s" % (
            r.get("regel_id"),
            r.get("befund"),
            " via " + "+".join(r.get("kanaele") or []) if r.get("kanaele") else " (still)",
            " [gesperrt]" if r.get("gesperrt") else "",
        ))
        for kanal in r.get("gescheiterte_kanaele") or []:
            _zeile("     Kanal versagt: %s" % (kanal,))
    for s in ergebnis.sperren:
        _zeile("  Sperre uebertragen: %s - %s" % (s.get("regel_id"), s.get("grund")))
    for n in ergebnis.nachlaeufe:
        _zeile("  Nachlauf %s: %s%s" % (
            n.get("regel_id"), n.get("ergebnis"),
            " (%s)" % n.get("grund") if n.get("grund") else "",
        ))
    for f in ergebnis.fehler:
        _zeile("  FEHLER: %s" % (f,))
    return 1 if ergebnis.fehler else 0


def _nachholen(argumente: argparse.Namespace) -> int:
    """Nur der Rueckweg: Sperren uebertragen, faellige Nachlaeufe vorlegen.

    Getrennt vom Durchgang, weil ein Nachlauf faellig wird, ohne dass eine neue
    Lauf-Zeile entsteht - wer nur auf neue Zeilen wartet, holt ihn nie nach.
    """
    marken = kopplung.marken_laden()
    reg = None
    fehler: list[str] = []
    try:
        reg = engine_registry.laden(pfade.registry(), pruefen=not argumente.ohne_pruefung)
    except engine_registry.RegistryFehler as e:
        fehler.append("Registry abgelehnt: %s" % e.meldung)

    with zustand.offen() as con:
        sperren = kopplung.sperren_uebertragen(marken, con, probe=argumente.probe)
        nachlaeufe = []
        if reg is not None:
            nachlaeufe = kopplung.nachlaeufe_einspeisen(marken, reg, con, probe=argumente.probe)
    # Wie im Durchgang: eine Probe verbraucht keine Marke (siehe kopplung.py).
    if not argumente.probe:
        kopplung.marken_speichern(marken)

    for s in sperren:
        _zeile("Sperre uebertragen: %s - %s" % (s.get("regel_id"), s.get("grund")))
    for n in nachlaeufe:
        _zeile("Nachlauf %s: %s%s" % (
            n.get("regel_id"), n.get("ergebnis"),
            " (%s)" % n.get("grund") if n.get("grund") else "",
        ))
    for f in fehler:
        _zeile("FEHLER: %s" % (f,))
    return 1 if fehler else 0


def _stand(argumente: argparse.Namespace) -> int:
    marken = kopplung.marken_laden()
    alle = kopplung.neue_zeilen(dict(marken, log_zeilen=0))
    faellig, verfallen = kopplung.offene_nachlaeufe(marken)
    jetzt = time.time()

    _zeile("Engine-Log:     %s" % pfade.log_datei())
    _zeile("Reaktionsdaten: %s" % pfade.ablage())
    _zeile("Registry:       %s" % pfade.registry())
    _zeile("Marken:         %s" % pfade.marken_datei())
    _zeile("")
    _zeile("Lauf-Zeilen gesamt: %d, davon beantwortet: %s" % (
        len(alle), marken.get("log_zeilen")))
    _zeile("Nachlaeufe faellig: %d, verfallen: %d, erledigt gemerkt: %d" % (
        len(faellig), len(verfallen), len(marken.get("nachlauf_erledigt", []))))
    for a in faellig:
        _zeile("  faellig seit %ds: %s (Versuch %s)" % (
            int(jetzt - float(a.get("faellig_ab", jetzt))),
            a.get("regel_id"), a.get("versuch")))

    with zustand.offen() as con:
        gesperrt = []
        try:
            reg = engine_registry.laden(pfade.registry(), pruefen=False)
            for regel in reg.regeln:
                if zustand.ist_gesperrt(con, regel.id):
                    gesperrt.append(regel.id)
        except engine_registry.RegistryFehler as e:
            _zeile("Registry abgelehnt: %s" % e.meldung)
    _zeile("In der Engine gesperrt: %s" % (", ".join(gesperrt) if gesperrt else "keine"))
    return 0


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(prog="automatik", description=__doc__ or "")
    zerleger.add_argument("--ohne-pruefung", action="store_true",
                          help="Registry ohne Validator laden (nur fuer Tests)")
    unter = zerleger.add_subparsers(dest="befehl")

    d = unter.add_parser("durchgang", help="Log lesen, reagieren, Rueckweg gehen")
    d.add_argument("--probe", action="store_true", help="entscheiden, nichts bewirken")
    d.add_argument("--json", action="store_true", help="Maschinenausgabe")
    d.set_defaults(funktion=_durchgang)

    n = unter.add_parser("nachholen", help="nur Sperren und faellige Nachlaeufe")
    n.add_argument("--probe", action="store_true")
    n.set_defaults(funktion=_nachholen)

    s = unter.add_parser("stand", help="Marken, offene Nachlaeufe, Sperren")
    s.set_defaults(funktion=_stand)

    argumente = zerleger.parse_args(argv)
    if not getattr(argumente, "funktion", None):
        zerleger.print_help()
        return 2
    for name in ("probe", "json"):
        if not hasattr(argumente, name):
            setattr(argumente, name, False)
    return argumente.funktion(argumente)


if __name__ == "__main__":
    raise SystemExit(main())
