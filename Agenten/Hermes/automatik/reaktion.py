"""Reaktions- und Benachrichtigungsschicht (Kanban t_f682e5c1).

Sie fuehrt keine Skills aus. Sie liest, was die Engine (t_9f7db046) je Lauf
protokolliert, entscheidet daraus eine Reaktion und benachrichtigt. Diese
Trennung ist der Kern: die Engine darf starten, diese Schicht darf melden und
merken. Deshalb kann sie auch dort laufen, wo kein Skill gestartet werden darf
(unbeaufsichtigte Sitzung, siehe SPEZIFIKATION.md Abschnitt 5).

Datenfluss:

    Engine  --(JSONL-Zeile je Lauf)-->  reaktion.py  --> Kanaele (Log, Board,
                                                         Telegram, Memory)
                                                    --> nachlauf.jsonl (Bitte
                                                        an die Engine: nochmal)
                                                    --> sperren.json (Bitte an
                                                        die Engine: nicht mehr)

Warum die Schicht Wiederholungen nicht selbst startet: ein Prozess, der einen
Skill nachstartet, ist eine zweite Engine mit zweiter Sicherheitspruefung. Es
gaebe dann zwei Stellen, die entscheiden, was laufen darf - genau das verbietet
die Spezifikation (eine Implementierung der Regeln, nicht zwei). Statt zu
starten schreibt diese Schicht einen faelligen Nachlauf-Auftrag; die Engine
liest ihn bei ihrem naechsten Durchgang und wendet ihre eigenen Regeln an.

Aufruf:

    python reaktion.py --ergebnis lauf.json          # eine Lauf-Zeile
    cat laeufe.jsonl | python reaktion.py --stdin    # mehrere
    python reaktion.py --selbsttest                  # ohne Nebenwirkung
    python reaktion.py --ergebnis lauf.json --probe  # entscheidet, meldet nicht
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml

from kanaele import ECHTE_KANAELE, Kanaele

HIER = Path(__file__).resolve().parent

KONFIG_DATEI = HIER / "reaktionen.yaml"

# Die zehn Felder, die die Engine je Lauf schreibt (SPEZIFIKATION.md 5.4).
PFLICHTFELDER = ("zeit", "regel_id", "trigger_typ", "skill", "modus")
KANNFELDER = (
    # exit ist bekannt, aber nicht mehr zwingend: uebersprungene und auf
    # Bestaetigung wartende Laeufe haben keinen Prozess und darum kein exit.
    "exit",
    "ausgeloest_durch",
    "dauer_ms",
    "aktionen_genutzt",
    "abbruchgrund",
    "erlaubte_aktionen",
    "ausgabe",
    "task_id",
    "bericht",
    # Felder, die die Engine (t_9f7db046, engine/protokoll.py) zusaetzlich
    # schreibt. Sie sind hier benannt, damit sie nicht als "Drift" auffallen.
    "ergebnis",
    "zeit_unix",
    "lauf_id",
    "registry_version",
    "versuch",
    "ausgabe_gekuerzt",
    # Befund des Integrationslaufs (t_f7937187, 20.09.2026): der erste echte
    # Durchgang meldete "kommando" als Drift. Die Engine schreibt bei echten
    # Laeufen das Kommando und bei einem Abbruch die Verstossliste mit - beides
    # gehoert dazu und ist keine Drift. Drift bleibt der Sinn dieser Liste,
    # darum werden die Felder benannt statt die Pruefung abzuschalten.
    "kommando",
    "verstoesse",
)

# Bewusst als Zuweisung, nicht als `type`-Statement: auf diesem Rechner liegen
# zwei Python im Pfad (3.14 und 3.11), und die Engine/Cron-Seite darf nicht an
# der Syntaxversion dieser Datei scheitern.
Befund = Literal[
    "erfolg", "fehler", "grenzverletzung", "probelauf", "uebersprungen", "wartet"
]

# Das Feld "ergebnis" der Engine ist genauer als ein Exitcode: es unterscheidet
# einen Lauf, der scheiterte, von einem, der gar nicht stattfand. Diese Tabelle
# ist die einzige Stelle, an der beide Vokabulare aufeinandertreffen.
ENGINE_BEFUND: dict[str, Befund] = {
    "erfolg": "erfolg",
    "fehler": "fehler",
    "uebersprungen": "uebersprungen",
    "dry_run": "probelauf",
    "bestaetigung_offen": "wartet",
    # Befund des Integrationslaufs (t_f7937187, 20.09.2026): die Engine kennt
    # drei weitere Worte, die hier fehlten. Unbekanntes wird als "fehler"
    # gelesen - fuer "verstoss" war das falsch und gefaehrlich: die Wache hatte
    # den Lauf wegen einer unerlaubten Aktion abgebrochen, die Schicht haette
    # ihn aber als gewoehnlichen Fehlschlag WIEDERHOLT statt die Regel zu
    # sperren. aktionen_genutzt ist bei einem Abbruch leer, darum greift der
    # Vergleich genutzte/erlaubte Aktionen in befund_bestimmen hier nicht.
    "verstoss": "grenzverletzung",
    # timeout: ein echter Lauf, der nicht fertig wurde - ein zweiter Versuch
    # ist sinnvoll, also wie ein Fehler.
    "timeout": "fehler",
    # abgelehnt: Bestaetigung verweigert oder verfallen. Es ist nichts
    # passiert und nichts kaputt; eine Eskalation waere eine Strafe dafuer,
    # dass ein Mensch "nein" gesagt hat.
    "abgelehnt": "uebersprungen",
}


# --- Ergebnis der Engine lesen ----------------------------------------------


def _exit_lesen(wert: Any) -> int | None:
    """exit=null ist eine Aussage ("kein Prozess gelaufen"), kein Fehler."""
    if wert is None:
        return None
    return int(wert)


@dataclass(frozen=True, slots=True)
class Ergebnis:
    """Eine Lauf-Zeile der Engine, streng gelesen.

    Fail fast: fehlt ein Pflichtfeld, ist das ein Fehler und keine Vermutung.
    Eine Reaktionsschicht, die ein halbes Ergebnis zurechtbiegt, meldet
    irgendwann Erfolg fuer einen Lauf, von dem sie nichts weiss.
    """

    zeit: str
    regel_id: str
    trigger_typ: str
    skill: str
    modus: str
    exit: int | None = None
    ausgeloest_durch: str = ""
    dauer_ms: int | None = None
    aktionen_genutzt: tuple[str, ...] = ()
    erlaubte_aktionen: tuple[str, ...] = ()
    abbruchgrund: str | None = None
    ausgabe: str = ""
    task_id: str | None = None
    bericht: str | None = None
    engine_ergebnis: str | None = None
    unbekannte_felder: tuple[str, ...] = ()

    @classmethod
    def aus_dict(cls, rohdaten: dict[str, Any]) -> Ergebnis:
        fehlend = [feld for feld in PFLICHTFELDER if feld not in rohdaten]
        # Trigger: Zeile ohne jede Aussage ueber den Ausgang.
        # Warum: exit allein reicht nicht mehr - die Engine schreibt bei
        # uebersprungenen und auf Bestaetigung wartenden Laeufen exit=null und
        # sagt den Ausgang nur im Feld "ergebnis". Eines von beiden muss da sein.
        if "exit" not in rohdaten and "ergebnis" not in rohdaten:
            fehlend.append("exit oder ergebnis")
        if fehlend:
            raise ValueError(f"Lauf-Zeile unvollstaendig, fehlt: {', '.join(fehlend)}")
        bekannt = set(PFLICHTFELDER) | set(KANNFELDER)
        # Unbekannte Felder sind kein Abbruch: die Engine darf ihr Log
        # erweitern. Sie werden aber protokolliert, damit Drift zwischen Engine
        # und Reaktionsschicht sichtbar wird und nicht stumm verschluckt.
        unbekannt = tuple(sorted(set(rohdaten) - bekannt))
        return cls(
            zeit=str(rohdaten["zeit"]),
            regel_id=str(rohdaten["regel_id"]),
            trigger_typ=str(rohdaten["trigger_typ"]),
            skill=str(rohdaten["skill"]),
            modus=str(rohdaten["modus"]),
            exit=_exit_lesen(rohdaten.get("exit")),
            ausgeloest_durch=str(rohdaten.get("ausgeloest_durch", "")),
            dauer_ms=rohdaten.get("dauer_ms"),
            aktionen_genutzt=tuple(rohdaten.get("aktionen_genutzt") or ()),
            erlaubte_aktionen=tuple(rohdaten.get("erlaubte_aktionen") or ()),
            abbruchgrund=rohdaten.get("abbruchgrund") or None,
            ausgabe=str(rohdaten.get("ausgabe") or ""),
            task_id=rohdaten.get("task_id"),
            bericht=rohdaten.get("bericht"),
            engine_ergebnis=rohdaten.get("ergebnis") or None,
            unbekannte_felder=unbekannt,
        )


def befund_bestimmen(ergebnis: Ergebnis) -> Befund:
    """Vier Faelle, in dieser Reihenfolge - die Reihenfolge ist die Aussage.

    Trigger: jede Lauf-Zeile.
    Warum Grenzverletzung zuerst: eine ueberschrittene Aktionsgrenze bedeutet,
    dass der Lauf etwas getan hat, was die Registry nicht erlaubt. Das ist
    schwerer als ein Fehlschlag und darf niemals durch eine Wiederholung
    "geheilt" werden.
    Warum Probelauf vor Erfolg: im dry_run hat nichts gewirkt, also ist auch
    nichts zu melden - sonst erzeugt jede Probe Rauschen auf dem Handy.
    """
    ausserhalb = set(ergebnis.aktionen_genutzt) - set(ergebnis.erlaubte_aktionen) - {"lesen"}
    if ausserhalb or (ergebnis.abbruchgrund or "").startswith("grenze"):
        return "grenzverletzung"
    if ergebnis.modus == "dry_run":
        return "probelauf"
    # Trigger: die Engine hat ihr Feld "ergebnis" gesetzt.
    # Warum es vor dem Exitcode gilt: nur die Engine weiss, ob ueberhaupt ein
    # Prozess lief. exit=null wuerde sonst als Fehler gelesen und eine
    # uebersprungene Regel (Rate-Limit, Sperre) loeste eine Eskalation aus.
    # Outcome: uebersprungen/wartet bleiben leise, erfolg/fehler wie bisher.
    if ergebnis.engine_ergebnis:
        befund = ENGINE_BEFUND.get(ergebnis.engine_ergebnis)
        if befund is None:
            # Unbekanntes Vokabular ist Drift, kein Erfolg: als Fehler melden.
            return "fehler"
        if befund == "erfolg" and ergebnis.abbruchgrund:
            return "fehler"
        return befund
    if ergebnis.exit is None:
        return "fehler"
    if ergebnis.exit == 0 and not ergebnis.abbruchgrund:
        return "erfolg"
    return "fehler"


# --- Konfiguration ----------------------------------------------------------

STANDARD_KONFIG: dict[str, Any] = {
    "konfig_version": "1.0.0",
    "defaults": {
        "kanal": "log",
        "memory_notiz": "automatik/laeufe/{regel_id}",
        "melde_erfolg": "bei_aenderung",
        "eskalation": {"wiederholungen": 0, "wiederhol_abstand_s": 600, "danach": "melden"},
    },
    "regeln": {},
}

ERLAUBTE_KANAELE = {"log", "board", "telegram", "log+board", "log+telegram", "alle"}
ERLAUBTE_DANACH = {"melden", "board_blocken", "regel_sperren", "still"}
ERLAUBTES_MELDEN = {"nie", "immer", "bei_aenderung"}


def konfig_laden(pfad: Path = KONFIG_DATEI) -> dict[str, Any]:
    """Konfiguration lesen und pruefen. Fehlt die Datei, gelten die Defaults."""
    if not pfad.exists():
        return json.loads(json.dumps(STANDARD_KONFIG))
    with open(pfad, encoding="utf-8") as datei:
        konfig = yaml.safe_load(datei) or {}
    fehler = konfig_pruefen(konfig)
    if fehler:
        raise ValueError("Konfiguration fehlerhaft: " + "; ".join(fehler))
    return konfig


def konfig_pruefen(konfig: dict[str, Any]) -> list[str]:
    """Meldungen statt Ausnahmen, damit der Selbsttest alle Fehler zeigt."""
    meldungen: list[str] = []
    if not isinstance(konfig.get("konfig_version"), str):
        meldungen.append("konfig_version fehlt")
    bloecke: list[tuple[str, Any]] = [("defaults", konfig.get("defaults") or {})]
    regeln = konfig.get("regeln") or {}
    if not isinstance(regeln, dict):
        meldungen.append("regeln muss eine Abbildung regel_id -> Einstellungen sein")
        regeln = {}
    bloecke += [(f"regeln.{name}", wert or {}) for name, wert in regeln.items()]
    for name, block in bloecke:
        if not isinstance(block, dict):
            meldungen.append(f"{name}: kein Abschnitt")
            continue
        kanal = block.get("kanal")
        if kanal is not None and kanal not in ERLAUBTE_KANAELE:
            meldungen.append(f"{name}.kanal={kanal!r} unbekannt")
        melden = block.get("melde_erfolg")
        if melden is not None and melden not in ERLAUBTES_MELDEN:
            meldungen.append(f"{name}.melde_erfolg={melden!r} unbekannt")
        eskalation = block.get("eskalation") or {}
        if not isinstance(eskalation, dict):
            meldungen.append(f"{name}.eskalation: kein Abschnitt")
            continue
        danach = eskalation.get("danach")
        if danach is not None and danach not in ERLAUBTE_DANACH:
            meldungen.append(f"{name}.eskalation.danach={danach!r} unbekannt")
        versuche = eskalation.get("wiederholungen")
        if versuche is not None and not (isinstance(versuche, int) and 0 <= versuche <= 5):
            meldungen.append(f"{name}.eskalation.wiederholungen={versuche!r} ausserhalb 0..5")
        abstand = eskalation.get("wiederhol_abstand_s")
        if abstand is not None and not (isinstance(abstand, int) and abstand >= 10):
            meldungen.append(f"{name}.eskalation.wiederhol_abstand_s={abstand!r} < 10")
    return meldungen


def einstellungen_fuer(konfig: dict[str, Any], regel_id: str) -> dict[str, Any]:
    """defaults, von der Regel ueberschrieben - eine Ebene, keine Vererbungskette."""
    zusammen = dict(konfig.get("defaults") or {})
    eigen = dict((konfig.get("regeln") or {}).get(regel_id) or {})
    eskalation = dict(zusammen.get("eskalation") or {})
    eskalation.update(eigen.pop("eskalation", None) or {})
    zusammen.update(eigen)
    zusammen["eskalation"] = eskalation
    return zusammen


# --- Zustand ----------------------------------------------------------------


def zustand_laden(pfad: Path) -> dict[str, Any]:
    if not pfad.exists():
        return {}
    try:
        with open(pfad, encoding="utf-8") as datei:
            return json.load(datei)
    except (OSError, json.JSONDecodeError):
        # Ein kaputter Zustand darf die Meldung nicht verhindern: die Schicht
        # faengt bei Null an und meldet dafuer lieber einmal zu viel.
        return {}


def zustand_speichern(zustand: dict[str, Any], pfad: Path) -> None:
    vorlaeufig = pfad.with_suffix(".tmp")
    with open(vorlaeufig, "w", encoding="utf-8", newline="\n") as datei:
        json.dump(zustand, datei, ensure_ascii=False, indent=1, sort_keys=True)
        datei.flush()
        os.fsync(datei.fileno())
    os.replace(vorlaeufig, pfad)


# --- Plan -------------------------------------------------------------------


@dataclass(slots=True)
class Plan:
    """Was getan werden soll - als Daten, damit --probe echt sein kann."""

    befund: Befund
    regel_id: str
    zusammenfassung: str
    kanaele: list[str] = field(default_factory=list)
    memory_notiz: str | None = None
    memory_zeilen: list[str] = field(default_factory=list)
    nachlauf_in_s: int | None = None
    versuch: int = 0
    board_block: str | None = None
    regel_sperren: str | None = None
    begruendung: list[str] = field(default_factory=list)


def _kanalliste(kanal: str) -> list[str]:
    if kanal == "alle":
        return ["log", "board", "telegram"]
    return kanal.split("+")


def _abdruck(ergebnis: Ergebnis) -> str:
    """Kurzer Fingerabdruck der Ausgabe - Grundlage von melde_erfolg=bei_aenderung."""
    return hashlib.sha256(ergebnis.ausgabe.strip().encode("utf-8")).hexdigest()[:16]


def plan_bauen(ergebnis: Ergebnis, konfig: dict[str, Any], zustand: dict[str, Any]) -> Plan:
    """Reine Entscheidung: kein Schreiben, kein Senden, kein Zeitgeber.

    Genau diese Funktion prueft der Selbsttest. Alles, was hier entschieden
    wird, ist aus (Ergebnis, Konfiguration, Zustand) reproduzierbar.
    """
    einstellung = einstellungen_fuer(konfig, ergebnis.regel_id)
    eskalation = einstellung.get("eskalation") or {}
    befund = befund_bestimmen(ergebnis)
    vorher = dict(zustand.get(ergebnis.regel_id) or {})
    streak = int(vorher.get("fehlerstreak", 0))
    versuch = int(vorher.get("versuch", 0))

    kanaele = _kanalliste(str(einstellung.get("kanal", "log")))
    notiz = str(einstellung.get("memory_notiz") or "").format(
        regel_id=ergebnis.regel_id, skill=Path(ergebnis.skill).name
    )
    plan = Plan(befund=befund, regel_id=ergebnis.regel_id, zusammenfassung="", kanaele=["log"])
    plan.memory_notiz = notiz or None

    if befund == "probelauf":
        # Trigger: modus=dry_run. Nur Log - ein Probelauf hat nichts bewirkt,
        # also gibt es nichts zu melden und nichts zu merken.
        plan.zusammenfassung = (
            f"Probelauf {ergebnis.regel_id} ({ergebnis.skill}) - keine Wirkung, keine Meldung."
        )
        plan.memory_notiz = None
        plan.begruendung.append("modus=dry_run: Reaktion bleibt im Log")
        return plan
    if befund == "uebersprungen":
        # Trigger: ergebnis=uebersprungen (Rate-Limit, Sperre, Bedingung nicht erfuellt).
        # Warum nur Log: es ist nichts passiert und nichts kaputt. Eine Meldung je
        # nicht gelaufener Regel waere genau das Rauschen, das dazu fuehrt, dass
        # die echten Meldungen nicht mehr gelesen werden.
        # Outcome: kein Kanal ausser Log, kein Memory-Eintrag, Zaehler unveraendert.
        plan.zusammenfassung = "Uebersprungen %s (%s)%s" % (
            ergebnis.regel_id,
            ergebnis.skill,
            ": " + ergebnis.abbruchgrund if ergebnis.abbruchgrund else "",
        )
        plan.memory_notiz = None
        plan.begruendung.append("ergebnis=uebersprungen: kein Lauf, keine Meldung")
        return plan

    if befund == "wartet":
        # Trigger: modus=bestaetigung, die Engine wartet auf einen Menschen.
        # Warum gemeldet wird: genau hier haengt der Ablauf, bis jemand antwortet -
        # eine stumme Wartezeile ist ein verlorener Auftrag.
        # Warum es kein Fehler ist: keine Wiederholung, kein Fehlerzaehler, sonst
        # eskaliert das Warten selbst und blockt am Ende einen Task.
        plan.kanaele = sorted(set(kanaele) | {"log"})
        plan.zusammenfassung = "Bestaetigung noetig: %s (%s) wartet auf Freigabe%s" % (
            ergebnis.regel_id,
            ergebnis.skill,
            " - " + ergebnis.abbruchgrund if ergebnis.abbruchgrund else "",
        )
        plan.memory_zeilen = [
            "- [wartet] %s %s Bestaetigung offen trigger=%s:%s"
            % (
                ergebnis.zeit,
                ergebnis.regel_id,
                ergebnis.trigger_typ,
                ergebnis.ausgeloest_durch or "-",
            )
        ]
        plan.begruendung.append("ergebnis=bestaetigung_offen: melden, nicht eskalieren")
        return plan

    if befund == "grenzverletzung":
        ausserhalb = sorted(
            set(ergebnis.aktionen_genutzt) - set(ergebnis.erlaubte_aktionen) - {"lesen"}
        )
        plan.kanaele = sorted(set(kanaele) | {"log", "telegram", "board"})
        plan.zusammenfassung = (
            f"GRENZE VERLETZT: {ergebnis.regel_id} ({ergebnis.skill}) nutzte "
            f"{', '.join(ausserhalb) or ergebnis.abbruchgrund or 'unerlaubte Aktion'}; "
            f"erlaubt war {', '.join(ergebnis.erlaubte_aktionen) or 'nichts'}."
        )
        plan.regel_sperren = plan.zusammenfassung
        plan.board_block = plan.zusammenfassung if ergebnis.task_id else None
        plan.memory_zeilen = [
            f"- [grenzverletzung] {ergebnis.zeit} {ergebnis.regel_id}: "
            f"genutzt={','.join(ergebnis.aktionen_genutzt) or '-'} "
            f"erlaubt={','.join(ergebnis.erlaubte_aktionen) or '-'}"
        ]
        plan.begruendung.append("Grenzverletzung: nie wiederholen, immer sperren und melden")
        return plan

    if befund == "fehler":
        streak += 1
        maximal = int(eskalation.get("wiederholungen", 0))
        danach = str(eskalation.get("danach", "melden"))
        if versuch < maximal:
            plan.versuch = versuch + 1
            plan.nachlauf_in_s = int(eskalation.get("wiederhol_abstand_s", 600))
            plan.kanaele = sorted(set(kanaele) | {"log"})
            plan.zusammenfassung = (
                f"Fehler {ergebnis.regel_id} ({ergebnis.skill}) exit={ergebnis.exit}: "
                f"Wiederholung {plan.versuch}/{maximal} in {plan.nachlauf_in_s}s vorgemerkt."
            )
            plan.begruendung.append(f"Wiederholung erlaubt ({versuch} < {maximal})")
        else:
            plan.kanaele = sorted(set(kanaele) | {"log", "telegram"})
            grund = (
                f"Automatik {ergebnis.regel_id} ({ergebnis.skill}) fehlgeschlagen: "
                f"exit={ergebnis.exit} {ergebnis.abbruchgrund or ''}".strip()
                + f" | Fehler in Folge: {streak}"
            )
            plan.zusammenfassung = grund
            plan.begruendung.append(f"Wiederholungen erschoepft ({versuch}/{maximal}) -> {danach}")
            if danach == "board_blocken" and ergebnis.task_id:
                plan.board_block = grund
                plan.kanaele = sorted(set(plan.kanaele) | {"board"})
            elif danach == "board_blocken":
                plan.begruendung.append("danach=board_blocken, aber keine task_id: nur melden")
            elif danach == "regel_sperren":
                plan.regel_sperren = grund
            elif danach == "still":
                plan.kanaele = ["log"]
                plan.begruendung.append("danach=still: kein Kanal ausser Log")
        plan.memory_zeilen = [
            f"- [fehler] {ergebnis.zeit} {ergebnis.regel_id} exit={ergebnis.exit} "
            f"streak={streak} {(ergebnis.abbruchgrund or ergebnis.ausgabe or '')[:200]}".rstrip()
        ]
        return plan

    # --- Erfolg ---
    melden = str(einstellung.get("melde_erfolg", "bei_aenderung"))
    abdruck = _abdruck(ergebnis)
    geaendert = abdruck != vorher.get("letzter_erfolg_abdruck")
    plan.zusammenfassung = (
        f"Erfolg {ergebnis.regel_id} ({ergebnis.skill}) in "
        f"{ergebnis.dauer_ms if ergebnis.dauer_ms is not None else '?'} ms"
        + (f"; erholt nach {streak} Fehlern" if streak else "")
    )
    plan.memory_zeilen = [
        f"- [lauf] {ergebnis.zeit} {ergebnis.regel_id} erfolg "
        f"trigger={ergebnis.trigger_typ}:{ergebnis.ausgeloest_durch or '-'} "
        f"dauer_ms={ergebnis.dauer_ms} abdruck={abdruck}"
    ]
    if ergebnis.ausgabe.strip():
        plan.memory_zeilen.append(
            "- [ausgabe] " + " ".join(ergebnis.ausgabe.strip().split())[:400]
        )
    # Trigger: melde_erfolg. Warum bei_aenderung die Voreinstellung ist: eine
    # Automatik, die stuendlich "alles in Ordnung" meldet, wird nach zwei Tagen
    # nicht mehr gelesen - dann faellt auch die echte Meldung nicht mehr auf.
    if melden == "immer" or (melden == "bei_aenderung" and (geaendert or streak)):
        plan.kanaele = sorted(set(kanaele) | {"log"})
        plan.begruendung.append(
            f"melde_erfolg={melden}, Ausgabe {'geaendert' if geaendert else 'gleich'}"
            + (", nach Fehlerserie" if streak else "")
        )
    else:
        plan.kanaele = ["log"]
        plan.begruendung.append(f"melde_erfolg={melden}, keine Aenderung: still")
    return plan


# --- Ausfuehren -------------------------------------------------------------


def _jetzt() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class Ablage:
    """Die vier Dateien der Schicht, gebuendelt an einem Ordner.

    Warum nicht vier Modulkonstanten: der erste Testlauf schrieb nachlauf.jsonl
    und sperren.json in den Arbeitsordner, obwohl er einen Temp-Ordner bekommen
    hatte - Zustand und Protokoll waren umstellbar, die Eskalationsdateien
    nicht. Ein Zustandspfad, der nur zur Haelfte umstellbar ist, ist keiner.
    """

    ordner: Path = HIER

    @property
    def protokoll(self) -> Path:
        return self.ordner / "reaktion-log.jsonl"

    @property
    def zustand(self) -> Path:
        return self.ordner / "zustand.json"

    @property
    def nachlauf(self) -> Path:
        return self.ordner / "nachlauf.jsonl"

    @property
    def sperren(self) -> Path:
        return self.ordner / "sperren.json"


def nachlauf_vormerken(plan: Plan, ergebnis: Ergebnis, pfad: Path) -> None:
    """Bitte an die Engine: diese Regel spaeter nochmal starten.

    Bewusst eine Datei und kein Start: die Reaktionsschicht darf nichts
    ausfuehren (siehe Modulkopf). faellig_ab ist eine Untergrenze, kein Termin -
    die Engine entscheidet weiterhin nach ihren eigenen Regeln (Rate-Limit,
    Modus, Sperre).
    """
    auftrag = {
        "vorgemerkt_am": _jetzt(),
        "faellig_ab": time.time() + float(plan.nachlauf_in_s or 0),
        "regel_id": plan.regel_id,
        "versuch": plan.versuch,
        "grund": f"exit={ergebnis.exit} {ergebnis.abbruchgrund or ''}".strip(),
        "trigger_typ": "reaktion_wiederholung",
        "ausgeloest_durch": f"{ergebnis.trigger_typ}:{ergebnis.ausgeloest_durch or '-'}",
    }
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with open(pfad, "a", encoding="utf-8", newline="\n") as datei:
        datei.write(json.dumps(auftrag, ensure_ascii=False) + "\n")
        datei.flush()
        os.fsync(datei.fileno())


def regel_sperren(regel_id: str, grund: str, pfad: Path) -> None:
    """Sperrliste fuehren, die die Engine vor jedem Start liest."""
    sperren: dict[str, Any] = {}
    if pfad.exists():
        try:
            with open(pfad, encoding="utf-8") as datei:
                sperren = json.load(datei)
        except (OSError, json.JSONDecodeError):
            sperren = {}
    sperren[regel_id] = {"seit": _jetzt(), "grund": grund}
    with open(pfad, "w", encoding="utf-8", newline="\n") as datei:
        json.dump(sperren, datei, ensure_ascii=False, indent=1, sort_keys=True)
        datei.flush()
        os.fsync(datei.fileno())


def reagieren(
    ergebnis: Ergebnis,
    konfig: dict[str, Any] | None = None,
    kanaele: Kanaele = ECHTE_KANAELE,
    ablage: Ablage | None = None,
    probe: bool = False,
) -> tuple[Plan, dict[str, Any]]:
    """Entscheiden, ausfuehren, merken. Gibt (Plan, Belege) zurueck."""
    konfig = konfig or konfig_laden()
    ablage = ablage or Ablage()
    zustand = zustand_laden(ablage.zustand)
    plan = plan_bauen(ergebnis, konfig, zustand)
    belege: dict[str, Any] = {}

    eintrag = {
        "zeit": _jetzt(),
        "lauf_zeit": ergebnis.zeit,
        "regel_id": ergebnis.regel_id,
        "skill": ergebnis.skill,
        "modus": ergebnis.modus,
        "trigger_typ": ergebnis.trigger_typ,
        "befund": plan.befund,
        "exit": ergebnis.exit,
        "kanaele": plan.kanaele,
        "nachlauf_in_s": plan.nachlauf_in_s,
        "versuch": plan.versuch,
        "board_block": bool(plan.board_block),
        "regel_gesperrt": bool(plan.regel_sperren),
        "begruendung": plan.begruendung,
        "zusammenfassung": plan.zusammenfassung,
        "unbekannte_felder": list(ergebnis.unbekannte_felder),
        "probe": probe,
    }

    if probe:
        # --probe entscheidet vollstaendig und meldet nichts. Nur das Log wird
        # geschrieben, sonst waere die Probe nicht nachvollziehbar.
        belege["log"] = kanaele.log(ablage.protokoll, eintrag)  # type: ignore[operator]
        return plan, belege

    # --- Kanaele ---
    if "board" in plan.kanaele and ergebnis.task_id:
        belege["board"] = kanaele.board_kommentar(  # type: ignore[operator]
            ergebnis.task_id, f"[automatik/{plan.befund}] {plan.zusammenfassung}"
        )
    elif "board" in plan.kanaele:
        belege["board"] = (False, "keine task_id im Ergebnis")
    if "telegram" in plan.kanaele:
        belege["telegram"] = kanaele.telegram(  # type: ignore[operator]
            f"automatik/{plan.regel_id}", plan.zusammenfassung
        )
    if plan.memory_notiz and plan.memory_zeilen:
        belege["memory"] = kanaele.memory(plan.memory_notiz, plan.memory_zeilen)  # type: ignore[operator]

    # --- Eskalation ---
    if plan.nachlauf_in_s is not None:
        nachlauf_vormerken(plan, ergebnis, ablage.nachlauf)
        belege["nachlauf"] = (True, f"faellig in {plan.nachlauf_in_s}s")
    if plan.regel_sperren:
        regel_sperren(plan.regel_id, plan.regel_sperren, ablage.sperren)
        belege["sperre"] = (True, plan.regel_id)
    if plan.board_block and ergebnis.task_id:
        belege["board_block"] = kanaele.board_blocken(  # type: ignore[operator]
            ergebnis.task_id, plan.board_block
        )

    # --- Zustand fortschreiben ---
    vorher = dict(zustand.get(ergebnis.regel_id) or {})
    if plan.befund == "erfolg":
        neu = {
            "fehlerstreak": 0,
            "versuch": 0,
            "letzter_status": "erfolg",
            "letzter_erfolg_abdruck": _abdruck(ergebnis),
            "letzte_reaktion": eintrag["zeit"],
        }
    elif plan.befund in ("probelauf", "uebersprungen", "wartet"):
        # Kein Lauf oder noch kein Ergebnis: Fehlerstreak und Versuchszaehler
        # bleiben stehen. Wuerden sie zurueckgesetzt, loeschte jede Pause die
        # Eskalationsgeschichte und eine dauerhaft kaputte Regel eskalierte nie.
        neu = {**vorher, "letzter_status": plan.befund, "letzte_reaktion": eintrag["zeit"]}
    else:
        neu = {
            **vorher,
            "fehlerstreak": int(vorher.get("fehlerstreak", 0)) + 1,
            "versuch": plan.versuch,
            "letzter_status": plan.befund,
            "letzte_reaktion": eintrag["zeit"],
        }
        if plan.regel_sperren:
            neu["gesperrt_seit"] = eintrag["zeit"]
    zustand[ergebnis.regel_id] = neu
    zustand_speichern(zustand, ablage.zustand)

    eintrag["belege"] = {name: list(wert) for name, wert in belege.items()}
    belege["log"] = kanaele.log(ablage.protokoll, eintrag)  # type: ignore[operator]
    return plan, belege


# --- CLI --------------------------------------------------------------------


def _zeilen_lesen(argumente: argparse.Namespace) -> list[dict[str, Any]]:
    if argumente.stdin:
        return [json.loads(z) for z in sys.stdin.read().splitlines() if z.strip()]
    text = Path(argumente.ergebnis).read_text(encoding="utf-8").strip()
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(z) for z in text.splitlines() if z.strip()]


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(description=__doc__ or "")
    zerleger.add_argument("--ergebnis", help="Datei mit einer oder mehreren Lauf-Zeilen")
    zerleger.add_argument("--stdin", action="store_true", help="Lauf-Zeilen von stdin")
    zerleger.add_argument("--probe", action="store_true", help="entscheiden, nicht melden")
    zerleger.add_argument("--konfig", default=str(KONFIG_DATEI))
    zerleger.add_argument("--konfig-pruefen", action="store_true")
    argumente = zerleger.parse_args(argv)

    if argumente.konfig_pruefen:
        with open(argumente.konfig, encoding="utf-8") as datei:
            konfig = yaml.safe_load(datei) or {}
        meldungen = konfig_pruefen(konfig)
        for meldung in meldungen:
            print("FEHLER", meldung)
        print("Konfiguration in Ordnung" if not meldungen else f"{len(meldungen)} Fehler")
        return 1 if meldungen else 0

    if not (argumente.ergebnis or argumente.stdin):
        zerleger.error("--ergebnis oder --stdin angeben")

    konfig = konfig_laden(Path(argumente.konfig))
    schlimmster = 0
    for rohdaten in _zeilen_lesen(argumente):
        ergebnis = Ergebnis.aus_dict(rohdaten)
        plan, belege = reagieren(ergebnis, konfig, probe=argumente.probe)
        gescheiterte = [name for name, (ok, _) in belege.items() if not ok]
        print(f"{plan.befund:16} {plan.regel_id:32} {plan.zusammenfassung}")
        print(f"{'':16} kanaele={','.join(plan.kanaele)} belege={belege}")
        if plan.befund in {"fehler", "grenzverletzung"}:
            schlimmster = max(schlimmster, 1)
        if gescheiterte:
            print(f"{'':16} KANAL AUSGEFALLEN: {', '.join(gescheiterte)}")
            schlimmster = max(schlimmster, 2)
    return schlimmster


if __name__ == "__main__":
    raise SystemExit(main())
