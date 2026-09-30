"""Registry laden und validieren.

Grundsatz aus der Spezifikation (Abschnitt 5, Punkt 1): die Engine prueft die
Sicherheitsregeln NICHT selbst nach, sondern ruft scripts/registry_pruefen.py
mit --json auf. So gibt es genau eine Implementierung der Regeln S1-S8, die
nicht von einer zweiten Kopie in der Engine auseinanderlaufen kann.

Geladen wird nur, wenn schemafehler UND regelfehler leer sind. Eine Registry
mit unbekanntem Major-Teil in registry_version wird abgelehnt, bevor der
Validator laeuft - die Engine kennt ihre Felder nur fuer Major 1.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import pfade

UNTERSTUETZTE_MAJOR = {1}

# Felder, die eine Regel aus defaults erben darf.
ERBBARE_FELDER = ("modus", "timeout_s", "kanal", "rate_limit", "arbeitsverzeichnis")


class RegistryFehler(Exception):
    """Registry ist unbrauchbar - die Engine startet nichts."""

    def __init__(self, meldung: str, details: list[str] | None = None):
        super().__init__(meldung)
        self.meldung = meldung
        self.details = details or []

    def __str__(self) -> str:  # pragma: no cover - Anzeige
        if not self.details:
            return self.meldung
        return self.meldung + "\n  " + "\n  ".join(self.details)


@dataclass
class Regel:
    id: str
    skill: str
    skill_art: str
    trigger: dict
    erlaubte_aktionen: list[str]
    modus: str
    timeout_s: int
    kanal: str
    rate_limit: dict
    schreibpfade: list[str] = field(default_factory=list)
    parameter: dict = field(default_factory=dict)
    abbruch: dict = field(default_factory=dict)
    eskalation: dict = field(default_factory=dict)
    beschreibung: str = ""
    arbeitsverzeichnis: str | None = None

    @property
    def trigger_typ(self) -> str:
        return self.trigger.get("typ", "")

    @property
    def prioritaet(self) -> int:
        return int(self.trigger.get("prioritaet", 100))

    @property
    def bedingungen(self) -> dict:
        return self.trigger.get("bedingungen", {}) or {}


@dataclass
class Registry:
    pfad: Path
    version: str
    regeln: list[Regel]

    def nach_id(self, rid: str) -> Regel | None:
        for r in self.regeln:
            if r.id == rid:
                return r
        return None

    def fuer_trigger(self, typ: str) -> list[Regel]:
        """Regeln eines Trigger-Typs, nach Prioritaet (0 zuerst), Dateireihenfolge stabil."""
        treffer = [r for r in self.regeln if r.trigger_typ == typ]
        return sorted(treffer, key=lambda r: r.prioritaet)


def _validator_lauf(registry_pfad: Path) -> dict:
    val = pfade.validator()
    if not val.exists():
        raise RegistryFehler("Validator fehlt: %s" % val)
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    try:
        r = subprocess.run(
            [sys.executable, str(val), str(registry_pfad), "--json"],
            capture_output=True, text=True, timeout=180, errors="replace", env=env,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise RegistryFehler("Validator nicht ausfuehrbar: %s" % e) from e
    if r.returncode == 2:
        raise RegistryFehler(
            "Validator: Registry oder Schema fehlt (Exit 2)",
            [(r.stdout or "").strip(), (r.stderr or "").strip()],
        )
    text = (r.stdout or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RegistryFehler(
            "Validator-Ausgabe ist kein JSON (Exit %d): %s" % (r.returncode, e),
            [text[:800], (r.stderr or "").strip()[:800]],
        ) from e


def _regel_bauen(roh: dict, defaults: dict) -> Regel:
    werte = dict(roh)
    for feld in ERBBARE_FELDER:
        if feld not in werte and feld in defaults:
            werte[feld] = defaults[feld]
    return Regel(
        id=werte["id"],
        skill=werte["skill"],
        skill_art=werte.get("skill_art", "skill"),
        trigger=werte.get("trigger", {}),
        erlaubte_aktionen=list(werte.get("erlaubte_aktionen", [])),
        modus=werte.get("modus", "dry_run"),
        timeout_s=int(werte.get("timeout_s", 300)),
        kanal=werte.get("kanal", "log"),
        rate_limit=dict(werte.get("rate_limit", {"max_laeufe": 1, "fenster_s": 86400})),
        schreibpfade=list(werte.get("schreibpfade", [])),
        parameter=dict(werte.get("parameter", {})),
        abbruch=dict(werte.get("abbruch", {})),
        eskalation=dict(werte.get("eskalation", {})),
        beschreibung=(werte.get("beschreibung") or "").strip(),
        arbeitsverzeichnis=werte.get("arbeitsverzeichnis"),
    )


def laden(registry_pfad: Path | str | None = None, pruefen: bool = True) -> Registry:
    """Registry laden. Bei jedem Fehler RegistryFehler - nie halb geladen."""
    p = Path(registry_pfad) if registry_pfad else pfade.standard_registry()
    if not p.exists():
        raise RegistryFehler("Registry fehlt: %s" % p)

    try:
        daten = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise RegistryFehler("Registry ist kein gueltiges YAML: %s" % e) from e
    if not isinstance(daten, dict):
        raise RegistryFehler("Registry-Wurzel ist kein Objekt: %s" % p)

    version = str(daten.get("registry_version", ""))
    major = version.split(".")[0]
    if not major.isdigit() or int(major) not in UNTERSTUETZTE_MAJOR:
        raise RegistryFehler(
            "registry_version '%s' wird von dieser Engine nicht unterstuetzt "
            "(bekannt: Major %s)" % (version, sorted(UNTERSTUETZTE_MAJOR))
        )

    if pruefen:
        bericht = _validator_lauf(p)
        schemafehler = bericht.get("schemafehler") or []
        regelfehler = bericht.get("regelfehler") or []
        if schemafehler or regelfehler:
            raise RegistryFehler(
                "Registry abgelehnt: %d Schemafehler, %d Regelverstoesse"
                % (len(schemafehler), len(regelfehler)),
                list(schemafehler) + list(regelfehler),
            )
        if bericht.get("hinweis"):
            # Ohne Inventar ist S3 ungeprueft - das ist ein Ausfall der
            # Sicherheitskette, nicht ein Hinweis. Die Engine startet nicht.
            raise RegistryFehler(
                "Sicherheitspruefung unvollstaendig: %s" % bericht["hinweis"]
            )

    defaults = daten.get("defaults") or {}
    regeln = [_regel_bauen(r, defaults) for r in daten.get("regeln") or []]
    if not regeln:
        raise RegistryFehler("Registry enthaelt keine Regeln: %s" % p)
    return Registry(pfad=p, version=version, regeln=regeln)
