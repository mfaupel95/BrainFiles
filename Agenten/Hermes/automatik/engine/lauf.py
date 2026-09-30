"""Lauf: einen Skill/ein Skript kontrolliert starten und das Ergebnis erfassen.

Kapselung nach Spezifikation Abschnitt 5 Punkt 3: Parameter uebergeben,
timeout_s erzwingen, Exit-Status und Ausgabe erfassen, erlaubte_aktionen als
harte Grenze durchsetzen - nicht als Bitte an das Modell.

Zwei Arten:

  skill_art=skript   Python-Datei aus den Skriptpfaden. Start ueber
                     engine/vorlauf.py, damit der Audit-Hook (wache.py) VOR dem
                     ersten Byte des Skripts steht. Die Grenze ist hier echt.

  skill_art=skill    SKILL.md, also ein Agentenlauf ueber hermes.exe. Die Wache
                     greift dort nicht von innen; darum ist dieser Weg
                     standardmaessig GESPERRT und muss mit
                     HERMES_AUTOMATIK_SKILL_START=1 ausdruecklich freigegeben
                     werden. Ohne Freigabe ist das Ergebnis 'uebersprungen' mit
                     Grund - nicht ein stiller Fehlschlag, und schon gar kein
                     ungebremster Agentenstart.

Exit-Codes, die diese Schicht selbst vergibt:
   97  Wache hat abgebrochen (Aktion ausserhalb erlaubte_aktionen)
   98  Vorlauf kaputt (Skript fehlt, Hook nicht setzbar)
  124  Timeout (wie GNU timeout)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import muster, pfade

VERSTOSS_EXIT = 97
VORLAUF_EXIT = 98
TIMEOUT_EXIT = 124


@dataclass
class Ergebnis:
    ergebnis: str            # erfolg | fehler | timeout | verstoss | uebersprungen
    exit_code: int | None = None
    dauer_ms: int = 0
    ausgabe: str = ""
    aktionen_genutzt: list = field(default_factory=list)
    verstoesse: list = field(default_factory=list)
    netz_ziele: list = field(default_factory=list)
    grund: str = ""
    kommando: list = field(default_factory=list)


def skript_finden(name: str) -> Path | None:
    """Skript aus den Skriptpfaden. Nur der Dateiname zaehlt - ein Registry-
    Eintrag darf nicht per '../..' aus den erlaubten Ordnern herausfuehren."""
    blatt = Path(name).name
    for basis in pfade.skriptpfade():
        kandidat = basis / blatt
        if kandidat.exists() and kandidat.is_file():
            return kandidat
    return None


def _parameter_argumente(parameter: dict) -> list[str]:
    """Flache Registry-Parameter in Kommandozeilen-Argumente.

    Booleans folgen store_true: true wird zur Flagge, false laesst sie weg. Ein
    frueher Entwurf schrieb '--kein-<flagge>' - damit waere die echte Regel
    'inventar-nach-skill-aenderung' (Parameter print: false) an argparse
    gescheitert, weil kein Hermes-Skript diese Gegenflagge kennt. Wer eine
    Verneinung braucht, gibt sie als eigenen Parameter an.
    """
    args: list[str] = []
    for k, v in (parameter or {}).items():
        flagge = "--" + str(k).replace("_", "-")
        if isinstance(v, bool):
            if v:
                args.append(flagge)
        else:
            args.extend([flagge, str(v)])
    return args


def _wache_konfig(regel, laufordner: Path) -> dict:
    """Konfiguration fuer den Audit-Hook im Kindprozess.

    freipfade bleibt bewusst LEER. Ein frueher Entwurf stellte hier das
    Temp-Verzeichnis frei - damit war die Wache unterhalb von %TEMP% blind, und
    eine Probe, die ausserhalb ihrer Schreibpfade schreiben sollte, kam damit
    durch. Braucht ein Skript eine Ablage, bekommt es den Laufordner
    (berichtspfade) oder die Regel nennt den Pfad ausdruecklich.
    """
    return {
        "regel_id": regel.id,
        "erlaubte_aktionen": list(regel.erlaubte_aktionen),
        "schreibpfade": [str(pfade.absolut(p)) for p in regel.schreibpfade],
        "berichtspfade": [str(laufordner)],
        "freipfade": [],
        "verstossdatei": str(laufordner / "verstoesse.jsonl"),
        "beobachtungsdatei": str(laufordner / "beobachtet.jsonl"),
    }


def _zeilen(datei: Path) -> list[dict]:
    if not datei.exists():
        return []
    raus = []
    for zeile in datei.read_text(encoding="utf-8", errors="replace").splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            raus.append(json.loads(zeile))
        except json.JSONDecodeError:
            continue
    return raus


def _laufordner(regel_id: str) -> Path:
    ordner = pfade.basis() / "laeufe" / ("%s_%d" % (regel_id, int(time.time() * 1000)))
    ordner.mkdir(parents=True, exist_ok=True)
    return ordner


def starten(regel, werte: dict | None = None) -> Ergebnis:
    """Regel wirklich ausfuehren. Der Aufrufer hat alle Freigaben geprueft."""
    if regel.skill_art == "skript":
        return _skript_starten(regel, werte or {})
    return _skill_starten(regel, werte or {})


def _skript_starten(regel, werte: dict) -> Ergebnis:
    ziel = skript_finden(regel.skill)
    if ziel is None:
        return Ergebnis(ergebnis="fehler", exit_code=None,
                        grund="Skript nicht gefunden: %s" % regel.skill)

    laufordner = _laufordner(regel.id)
    konfig = _wache_konfig(regel, laufordner)

    vorlauf = Path(__file__).resolve().parent / "vorlauf.py"
    kommando = [sys.executable, str(vorlauf), str(ziel)]
    kommando += _parameter_argumente(regel.parameter)

    env = dict(os.environ)
    env["HERMES_AUTOMATIK_WACHE"] = json.dumps(konfig, ensure_ascii=False)
    env["HERMES_AUTOMATIK_REGEL"] = regel.id
    env["HERMES_AUTOMATIK_LAUFORDNER"] = str(laufordner)
    # Trigger-Werte als Umgebung, damit ein Skript sie lesen kann, ohne dass
    # ungeprueftes Material in die Kommandozeile geraet.
    env["HERMES_AUTOMATIK_TRIGGER"] = json.dumps(werte, ensure_ascii=False)[:8000]
    env["PYTHONIOENCODING"] = "utf-8"

    arbeitsverzeichnis = (
        str(pfade.absolut(regel.arbeitsverzeichnis))
        if regel.arbeitsverzeichnis else str(ziel.parent)
    )

    return _ausfuehren(kommando, env, arbeitsverzeichnis, regel.timeout_s, laufordner)


def _skill_starten(regel, werte: dict) -> Ergebnis:
    if not pfade.skill_start_frei():
        return Ergebnis(
            ergebnis="uebersprungen",
            grund=("skill_art=skill ist ohne HERMES_AUTOMATIK_SKILL_START=1 gesperrt: "
                   "ein Agentenlauf laesst sich von innen nicht bewachen"),
        )

    binaer = pfade.hermes_bin()
    if not binaer.exists():
        return Ergebnis(ergebnis="fehler", grund="hermes-Binary fehlt: %s" % binaer)

    laufordner = _laufordner(regel.id)
    auftrag = {
        "regel": regel.id,
        "skill": regel.skill,
        "parameter": regel.parameter,
        "trigger": werte,
        "erlaubte_aktionen": regel.erlaubte_aktionen,
    }
    auftragsdatei = laufordner / "auftrag.json"
    auftragsdatei.write_text(
        json.dumps(auftrag, ensure_ascii=False, indent=1), encoding="utf-8")

    prompt = (
        "Automatiklauf der Regel '%s'. Fuehre den Skill '%s' aus. "
        "Auftrag und Trigger-Werte stehen in %s. "
        "Erlaubte Aktionen (harte Grenze): %s. "
        "Tue nichts darueber hinaus und frage nicht zurueck."
        % (regel.id, regel.skill, auftragsdatei, ", ".join(regel.erlaubte_aktionen))
    )
    kommando = [str(binaer), "-z", prompt, "--skills", regel.skill, "--safe-mode"]

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    arbeitsverzeichnis = (
        str(pfade.absolut(regel.arbeitsverzeichnis))
        if regel.arbeitsverzeichnis else str(laufordner)
    )
    return _ausfuehren(kommando, env, arbeitsverzeichnis, regel.timeout_s, laufordner,
                       bewacht=False)


def _ausfuehren(kommando, env, cwd, timeout_s, laufordner, bewacht=True) -> Ergebnis:
    start = time.time()
    abgelaufen = False
    try:
        fertig = subprocess.run(
            kommando, cwd=cwd, env=env, capture_output=True, text=True,
            errors="replace", timeout=int(timeout_s),
        )
        exit_code = fertig.returncode
        ausgabe = (fertig.stdout or "") + (
            ("\n[stderr]\n" + fertig.stderr) if fertig.stderr else "")
    except subprocess.TimeoutExpired as e:
        abgelaufen = True
        exit_code = TIMEOUT_EXIT
        ausgabe = "%s\n[stderr]\n%s" % (
            (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes)
            else (e.stdout or ""),
            (e.stderr or b"").decode("utf-8", "replace") if isinstance(e.stderr, bytes)
            else (e.stderr or ""),
        )
    except OSError as e:
        return Ergebnis(ergebnis="fehler", exit_code=None,
                        dauer_ms=int((time.time() - start) * 1000),
                        grund="Start fehlgeschlagen: %s" % e, kommando=kommando)

    dauer_ms = int((time.time() - start) * 1000)
    verstoesse = _zeilen(laufordner / "verstoesse.jsonl")
    beobachtet = _zeilen(laufordner / "beobachtet.jsonl")
    aktionen = sorted({b.get("aktion") for b in beobachtet if b.get("aktion")})
    netz = sorted({
        str(b.get("detail")) for b in beobachtet if b.get("aktion") == "netz"})[:20]

    if abgelaufen:
        ergebnis = "timeout"
    elif exit_code == VERSTOSS_EXIT or verstoesse:
        ergebnis = "verstoss"
    elif exit_code == 0:
        ergebnis = "erfolg"
    else:
        ergebnis = "fehler"

    grund = ""
    if ergebnis == "timeout":
        grund = "timeout_s=%d ueberschritten" % int(timeout_s)
    elif ergebnis == "verstoss" and verstoesse:
        grund = "Wache: %s %s" % (
            verstoesse[0].get("aktion"), str(verstoesse[0].get("detail"))[:200])
    elif ergebnis == "verstoss":
        grund = "Wache hat abgebrochen (Exit 97)"
    elif exit_code == VORLAUF_EXIT:
        grund = "Vorlauf konnte die Wache nicht setzen"
    elif not bewacht:
        grund = "unbewachter Agentenlauf (skill_art=skill)"

    return Ergebnis(
        ergebnis=ergebnis, exit_code=exit_code, dauer_ms=dauer_ms,
        ausgabe=ausgabe.strip(), aktionen_genutzt=aktionen,
        verstoesse=verstoesse[:5], netz_ziele=netz, grund=grund, kommando=kommando,
    )


def trockenlauf(regel, werte: dict | None = None) -> Ergebnis:
    """dry_run: alles pruefen, nichts starten (Spezifikation 5.5).

    Geprueft wird, was ein echter Lauf brauchen wuerde - fehlt das Skript, ist
    auch der Trockenlauf ein Fehler. Ein dry_run, der jeden Unsinn durchwinkt,
    waere wertlos.
    """
    if regel.skill_art == "skript":
        ziel = skript_finden(regel.skill)
        if ziel is None:
            return Ergebnis(ergebnis="fehler",
                            grund="Skript nicht gefunden: %s" % regel.skill)
        kommando = [sys.executable, "engine/vorlauf.py", str(ziel)]
        kommando += _parameter_argumente(regel.parameter)
    else:
        kommando = [str(pfade.hermes_bin()), "-z", "<Skill %s>" % regel.skill]

    fehlend = [p for p in regel.schreibpfade if not pfade.absolut(p).parent.exists()]
    grund = "wuerde starten: %s" % " ".join(kommando)
    if fehlend:
        grund += " | Warnung: Elternordner fehlt fuer %s" % ", ".join(fehlend)
    if muster.kommando_aktionen(kommando) - set(regel.erlaubte_aktionen):
        grund += " | Warnung: Startkommando selbst waere nicht erlaubt"

    return Ergebnis(ergebnis="dry_run", exit_code=None, grund=grund, kommando=kommando)
