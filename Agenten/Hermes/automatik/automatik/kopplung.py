"""Kopplung: Engine-Laeufe in Reaktionen, Reaktions-Bitten zurueck in die Engine.

Die beiden Vorgaenger-Tasks sind absichtlich getrennt gebaut:

    Engine (t_9f7db046)      darf Skills STARTEN, meldet nichts.
    Reaktion (t_f682e5c1)    darf MELDEN und MERKEN, startet nichts.

Damit fehlte genau das Stueck, das diese Datei ist: der Weg dazwischen, in
beide Richtungen.

    laeufe.jsonl  --(neue Zeilen)-->  reagieren()  -->  Log/Board/Telegram/Memory
                                          |
                     nachlauf.jsonl  <----+----> sperren.json
                          |                           |
                          v                           v
                  steuerung.ausfuehren()        zustand.sperren()
                  (Engine prueft erneut)        (Engine haelt an)

Zwei Regeln, die hier NICHT gebrochen werden:

1. Die Kopplung startet nichts selbst. Ein faelliger Nachlauf wird der Engine
   als gewoehnlicher Ausloeser vorgelegt; sie wendet ihre eigenen Regeln an
   (Modus, Rate-Limit, Dauersperre, Bestaetigungspflicht). Damit bleibt es bei
   EINER Stelle, die ueber das Starten entscheidet.
2. Kein zweiter Zustand ueber Laeufe. Die Kopplung fuehrt nur Marken darueber,
   was sie selbst schon weitergereicht hat.

Aufruf:

    python -m automatik durchgang        Log lesen, reagieren, Rueckweg gehen
    python -m automatik durchgang --probe   alles entscheiden, nichts melden
    python -m automatik stand            Marken, offene Nachlaeufe, Sperren
    python -m automatik nachholen        nur den Rueckweg (ohne neue Zeilen)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import pfade

pfade.module_einhaengen()

import reaktion as reaktionsschicht  # noqa: E402  (aus t_f682e5c1)
from engine import registry as engine_registry  # noqa: E402  (aus t_9f7db046)
from engine import steuerung, zustand  # noqa: E402
from engine.quellen import Ausloeser  # noqa: E402

# Ein Nachlauf, der laenger als das hier zurueckliegt, entfaellt. Gleiche
# Haltung wie die Engine bei Zeit-Triggern (BETRIEB.md Abschnitt 5): nach einem
# Stromausfall soll kein Stapel nachgeholter Automatik anlaufen.
NACHLAUF_VERFALL_S = 3600

# Wie viele erledigte Schluessel die Marke behaelt. Nur Schutz gegen unbegrenztes
# Wachstum; der Verfall oben raeumt ohnehin auf.
MARKEN_GEDAECHTNIS = 500


# --- Marken -----------------------------------------------------------------


def marken_laden(pfad: Path | None = None) -> dict[str, Any]:
    ziel = pfad or pfade.marken_datei()
    if not ziel.exists():
        return {"log_zeilen": 0, "nachlauf_erledigt": [], "sperren_uebertragen": []}
    try:
        with open(ziel, encoding="utf-8") as datei:
            daten = json.load(datei)
    except (OSError, json.JSONDecodeError):
        # Eine kaputte Marke darf die Kopplung nicht anhalten. Sie faengt dann
        # beim aktuellen Logende an - lieber eine Reaktion verpassen als jede
        # alte Zeile ein zweites Mal melden.
        return {"log_zeilen": None, "nachlauf_erledigt": [], "sperren_uebertragen": []}
    daten.setdefault("log_zeilen", 0)
    daten.setdefault("nachlauf_erledigt", [])
    daten.setdefault("sperren_uebertragen", [])
    return daten


def marken_speichern(marken: dict[str, Any], pfad: Path | None = None) -> None:
    ziel = pfad or pfade.marken_datei()
    for schluessel in ("nachlauf_erledigt", "sperren_uebertragen"):
        marken[schluessel] = list(marken[schluessel])[-MARKEN_GEDAECHTNIS:]
    vorlaeufig = ziel.with_suffix(".tmp")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with open(vorlaeufig, "w", encoding="utf-8", newline="\n") as datei:
        json.dump(marken, datei, ensure_ascii=False, indent=1, sort_keys=True)
        datei.flush()
    vorlaeufig.replace(ziel)


# --- Hinweg: Engine-Log -> Reaktion ----------------------------------------


def _log_zeilen(datei: Path) -> list[dict[str, Any]]:
    if not datei.exists():
        return []
    zeilen = []
    for roh in datei.read_text(encoding="utf-8", errors="replace").splitlines():
        roh = roh.strip()
        if not roh:
            continue
        try:
            zeilen.append(json.loads(roh))
        except json.JSONDecodeError:
            # Wie die Engine: eine kaputte Zeile haelt den Leser nicht auf.
            continue
    return zeilen


def neue_zeilen(marken: dict[str, Any], datei: Path | None = None) -> list[dict[str, Any]]:
    """Zeilen, die seit dem letzten Durchgang dazugekommen sind.

    Gezaehlt wird, nicht verglichen: das Log wird nur angehaengt, nie
    umgeschrieben (protokoll.schreiben oeffnet mit "a"). Damit genuegt die Zahl
    der bereits gesehenen Zeilen als Marke - und ein Rechner, der mitten im
    Schreiben ausgeht, verliert hoechstens die letzte Zeile, nicht die Marke.
    """
    alle = _log_zeilen(datei or pfade.log_datei())
    gesehen = marken.get("log_zeilen")
    if gesehen is None:
        # Erster Blick nach einer kaputten Marke: nur nachfuehren.
        marken["log_zeilen"] = len(alle)
        return []
    if gesehen > len(alle):
        # Log wurde gedreht oder ersetzt - von vorn, aber ohne Altlast melden.
        marken["log_zeilen"] = len(alle)
        return []
    return alle[gesehen:]


def aktionen_ergaenzen(zeile: dict[str, Any], reg) -> dict[str, Any]:
    """erlaubte_aktionen aus der Registry nachtragen, wenn das Log sie nicht hat.

    Befund dieses Laufs (20.09.2026): engine/steuerung.py schrieb die erlaubten
    Aktionen nicht ins Log, die Reaktionsschicht las darum JEDEN erfolgreichen
    Lauf mit Aktionen als Grenzverletzung - sie vergleicht genutzte gegen
    erlaubte Aktionen, und eine leere Erlaubnisliste laesst alles unerlaubt
    aussehen. Das hat die Engine inzwischen selbst behoben (extra-Feld). Diese
    Ergaenzung bleibt fuer aeltere Zeilen, damit ein Log aus der Zeit davor
    nicht als Sicherheitsvorfall gemeldet wird.
    """
    if zeile.get("erlaubte_aktionen") or reg is None:
        return zeile
    regel = reg.nach_id(zeile.get("regel_id", ""))
    if regel is None:
        return zeile
    angereichert = dict(zeile)
    angereichert["erlaubte_aktionen"] = list(regel.erlaubte_aktionen)
    return angereichert


@dataclass
class Durchgang:
    """Was ein Durchgang getan hat - als Daten, damit --probe echt sein kann."""

    gelesen: int = 0
    reaktionen: list[dict[str, Any]] = field(default_factory=list)
    nachlaeufe: list[dict[str, Any]] = field(default_factory=list)
    sperren: list[dict[str, Any]] = field(default_factory=list)
    fehler: list[str] = field(default_factory=list)


def _protokollieren(eintrag: dict[str, Any], datei: Path | None = None) -> None:
    ziel = datei or pfade.protokoll_datei()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with open(ziel, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(eintrag, ensure_ascii=False) + "\n")


def reagieren_auf_neue(
    marken: dict[str, Any],
    reg=None,
    probe: bool = False,
    ablage=None,
    konfig=None,
    kanaele=None,
    log: Path | None = None,
) -> Durchgang:
    """Hinweg: jede neue Log-Zeile genau einmal der Reaktionsschicht vorlegen."""
    ergebnis = Durchgang()
    ablage = ablage or reaktionsschicht.Ablage(pfade.ablage())
    if konfig is None:
        konfig = reaktionsschicht.konfig_laden(pfade.reaktionskonfig())

    zeilen = neue_zeilen(marken, log)
    ergebnis.gelesen = len(zeilen)

    for roh in zeilen:
        roh = aktionen_ergaenzen(roh, reg)
        try:
            lauf = reaktionsschicht.Ergebnis.aus_dict(roh)
        except ValueError as fehler:
            # Unvollstaendige Zeile: melden, aber weiterzaehlen. Sonst bleibt
            # die Kopplung fuer immer an derselben Zeile stehen.
            ergebnis.fehler.append(f"{roh.get('regel_id', '?')}: {fehler}")
            marken["log_zeilen"] = marken.get("log_zeilen", 0) + 1
            continue

        zusatz = {} if kanaele is None else {"kanaele": kanaele}
        plan, belege = reaktionsschicht.reagieren(
            lauf, konfig, ablage=ablage, probe=probe, **zusatz
        )
        marken["log_zeilen"] = marken.get("log_zeilen", 0) + 1
        ergebnis.reaktionen.append(
            {
                "regel_id": plan.regel_id,
                "befund": plan.befund,
                "kanaele": plan.kanaele,
                "nachlauf_in_s": plan.nachlauf_in_s,
                "gesperrt": bool(plan.regel_sperren),
                "gescheiterte_kanaele": [
                    name for name, (ok, _) in belege.items() if not ok
                ],
            }
        )
    return ergebnis


# --- Rueckweg: Reaktion -> Engine ------------------------------------------


def _auftrag_schluessel(auftrag: dict[str, Any]) -> str:
    return "%s|%s|%s" % (
        auftrag.get("regel_id", "?"),
        auftrag.get("vorgemerkt_am", "?"),
        auftrag.get("versuch", 0),
    )


def offene_nachlaeufe(
    marken: dict[str, Any], datei: Path | None = None, jetzt: float | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(faellige, verfallene) Nachlauf-Auftraege - ohne etwas zu veraendern."""
    ziel = datei or (reaktionsschicht.Ablage(pfade.ablage()).nachlauf)
    if not ziel.exists():
        return [], []
    jetzt = time.time() if jetzt is None else jetzt
    erledigt = set(marken.get("nachlauf_erledigt", []))
    faellig: list[dict[str, Any]] = []
    verfallen: list[dict[str, Any]] = []
    for roh in ziel.read_text(encoding="utf-8", errors="replace").splitlines():
        roh = roh.strip()
        if not roh:
            continue
        try:
            auftrag = json.loads(roh)
        except json.JSONDecodeError:
            continue
        if _auftrag_schluessel(auftrag) in erledigt:
            continue
        ab = float(auftrag.get("faellig_ab", 0) or 0)
        if ab > jetzt:
            continue
        if jetzt - ab > NACHLAUF_VERFALL_S:
            verfallen.append(auftrag)
            continue
        faellig.append(auftrag)
    return faellig, verfallen


def nachlaeufe_einspeisen(
    marken: dict[str, Any],
    reg,
    con,
    probe: bool = False,
    jetzt: float | None = None,
    datei: Path | None = None,
) -> list[dict[str, Any]]:
    """Faellige Nachlaeufe der Engine vorlegen - sie entscheidet weiterhin selbst."""
    faellig, verfallen = offene_nachlaeufe(marken, datei, jetzt)
    erledigt = list(marken.get("nachlauf_erledigt", []))
    bericht: list[dict[str, Any]] = []

    for auftrag in verfallen:
        erledigt.append(_auftrag_schluessel(auftrag))
        bericht.append(
            {
                "regel_id": auftrag.get("regel_id"),
                "ergebnis": "verfallen",
                "grund": f"aelter als {NACHLAUF_VERFALL_S}s - nicht nachgeholt",
            }
        )

    for auftrag in faellig:
        rid = str(auftrag.get("regel_id", ""))
        regel = reg.nach_id(rid) if reg is not None else None
        if regel is None:
            erledigt.append(_auftrag_schluessel(auftrag))
            bericht.append(
                {"regel_id": rid, "ergebnis": "unbekannt", "grund": "nicht in der Registry"}
            )
            continue
        if probe:
            bericht.append({"regel_id": rid, "ergebnis": "probe", "grund": "nicht gestartet"})
            continue

        ausloeser = Ausloeser(
            regel_id=regel.id,
            typ=regel.trigger_typ,
            ausgeloest_durch="nachlauf: %s (Versuch %s)"
            % (auftrag.get("ausgeloest_durch", "-"), auftrag.get("versuch", 1)),
            prioritaet=regel.prioritaet,
        )
        eintrag = steuerung.ausfuehren(regel, ausloeser, con, reg.version)
        erledigt.append(_auftrag_schluessel(auftrag))
        bericht.append(
            {
                "regel_id": rid,
                "ergebnis": eintrag.get("ergebnis"),
                "grund": eintrag.get("abbruchgrund"),
            }
        )

    marken["nachlauf_erledigt"] = erledigt
    return bericht


def sperren_uebertragen(
    marken: dict[str, Any], con, probe: bool = False, datei: Path | None = None
) -> list[dict[str, Any]]:
    """Sperrbitten der Reaktionsschicht in die Zustands-DB der Engine tragen.

    Die Reaktionsschicht schreibt sperren.json, weil sie die Engine nicht
    kennt. Ohne diese Uebertragung war die Sperre eine Datei, die niemand liest
    - eine Regel, die nachweislich ihre Grenze verletzt hat, waere beim
    naechsten Trigger einfach wieder gelaufen.
    """
    ziel = datei or (reaktionsschicht.Ablage(pfade.ablage()).sperren)
    if not ziel.exists():
        return []
    try:
        with open(ziel, encoding="utf-8") as fh:
            sperren = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(sperren, dict):
        return []

    schon = list(marken.get("sperren_uebertragen", []))
    bericht: list[dict[str, Any]] = []
    for regel_id, eintrag in sorted(sperren.items()):
        if not isinstance(eintrag, dict):
            continue
        schluessel = "%s|%s" % (regel_id, eintrag.get("seit", "?"))
        if schluessel in schon:
            continue
        grund = str(eintrag.get("grund", "Reaktionsschicht: Grenzverletzung"))[:500]
        if not probe:
            zustand.sperren(con, regel_id, "Reaktionsschicht: " + grund)
        schon.append(schluessel)
        bericht.append({"regel_id": regel_id, "grund": grund, "probe": probe})
    marken["sperren_uebertragen"] = schon
    return bericht


# --- Ein vollstaendiger Durchgang ------------------------------------------


def durchgang(
    probe: bool = False,
    registry_pfad: Path | None = None,
    pruefen: bool = True,
    jetzt: float | None = None,
    kanaele=None,
) -> Durchgang:
    """Hinweg und Rueckweg in einem Aufruf. Reihenfolge ist Absicht:

    erst reagieren (dabei entstehen Nachlaeufe und Sperren), dann Sperren
    uebertragen, dann Nachlaeufe einspeisen. Eine Regel, die sich in diesem
    Durchgang gerade gesperrt hat, wird damit im selben Durchgang nicht mehr
    nachgestartet.

    kanaele ist nur fuer den Testlauf da (tests/ende_zu_ende.py setzt eine
    Attrappe ein). Im Betrieb bleibt es None, dann gelten die echten Kanaele der
    Reaktionsschicht - ein Test, der einen eigenen Codepfad faehrt, belegt den
    Betrieb nicht.
    """
    marken = marken_laden()
    reg = None
    ergebnis = Durchgang()
    try:
        reg = engine_registry.laden(registry_pfad or pfade.registry(), pruefen=pruefen)
    except engine_registry.RegistryFehler as fehler:
        # Ohne Registry keine Anreicherung und kein Nachstart - aber melden
        # darf die Schicht trotzdem. Ein Automatiksystem, das bei kaputter
        # Registry auch noch stumm wird, verbirgt genau den Fehler.
        ergebnis.fehler.append("Registry abgelehnt: %s" % fehler.meldung)

    hin = reagieren_auf_neue(marken, reg, probe=probe, kanaele=kanaele)
    ergebnis.gelesen = hin.gelesen
    ergebnis.reaktionen = hin.reaktionen
    ergebnis.fehler.extend(hin.fehler)

    with zustand.offen() as con:
        ergebnis.sperren = sperren_uebertragen(marken, con, probe=probe)
        if reg is not None:
            ergebnis.nachlaeufe = nachlaeufe_einspeisen(
                marken, reg, con, probe=probe, jetzt=jetzt
            )

    # Eine Probe darf nichts verbrauchen. Befund des Integrationslaufs
    # (20.09.2026): der erste echte `durchgang --probe` schrieb die Marken
    # trotzdem fort - die geprueften Zeilen galten danach als beantwortet und
    # der naechste ECHTE Durchgang haette sie nie gemeldet. Eine Probe, die
    # Meldungen verschluckt, ist schlimmer als keine Probe.
    if not probe:
        marken_speichern(marken)
    _protokollieren(
        {
            "zeit": reaktionsschicht._jetzt(),
            "probe": probe,
            "gelesen": ergebnis.gelesen,
            "reaktionen": ergebnis.reaktionen,
            "sperren": ergebnis.sperren,
            "nachlaeufe": ergebnis.nachlaeufe,
            "fehler": ergebnis.fehler,
        }
    )
    return ergebnis
