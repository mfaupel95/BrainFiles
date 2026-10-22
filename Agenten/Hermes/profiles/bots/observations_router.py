"""Observations-Router: serieller Beobachtungs-Handoff (Einmal-Dispatcher).

Was er tut
----------
Liest die Markdown-Beobachtungen aus der User-Scope
`~/.claude/skill-observations/observation-log/` (eine Datei je Beobachtung,
YAML-Frontmatter, KEINE observations.jsonl). Pro Lauf verarbeitet er
HOECHSTENS EINE `status: open`-Beobachtung, die nicht geparkt ist:

  1. Recherche synchron aufrufen und auf das Ergebnis warten.
  2. Nur bei eindeutigem, allowlist-validem `target_profile` genau EINEN
     bestehenden Fachbot danach aufrufen (keine Parallelitaet, keine
     Selbstverstaerkung/Chat-Schleife).

Idempotent ueber eine stabile Observation-ID und ein Statefile: eine bereits
verarbeitete Beobachtung wird nicht erneut ausgefuehrt.

Sicherheit
----------
- Die Observation wird als UNTRUSTED data gelesen: nur das YAML-Frontmatter
  wird geparst, kein Inhalt wird als Befehl ausgefuehrt, keine Outputs werden
  als Befehle interpretiert.
- Keine Orders/Live-Aktionen, keine Dateiaenderungen im One-Skill-Repo, keine
  SkillsBot-Runtime-Aenderung, kein Cron, keine Gateway-/Bot-Neustarts.
- `--dry-run` ist der Default; `--dispatch` fuehrt die Kette aus.

Aufruf
------
    python observations_router.py                 # dry-run (Default)
    python observations_router.py --dispatch      # verarbeitet EINE Beobachtung
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - nur wenn PyYAML fehlt
    yaml = None

# --- Pfade ----------------------------------------------------------------

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[3]  # BrainFiles/
PROFILES = WURZEL / "Agenten" / "Hermes" / "profiles"

# User-Scope der Beobachtungen (dokumentiert in one-skill-to-rule-them-all).
OBS_ROOT = Path(os.environ.get(
    "OBSERVATION_LOG",
    str(Path.home() / ".claude" / "skill-observations" / "observation-log"),
))
STATE_PFAD = HIER / "observations_router.state.json"

# Allowlist der Fachbots, die der Dispatcher nach der Recherche ansteuern darf.
# Nur hier eingetragene Profile werden gestartet; alles andere wird abgelehnt.
ALLOWLIST = {
    "jev-trader",
    "recherche",
    "obsidian-skills",
    "gbrain",
    "hermes-wartung",
    "markt-recherche",
    "one-skill-to-rule-them-all",
}

HERMES_EXE = WURZEL / "Agenten" / "Hermes" / "bin" / "hermes.exe"

# Statuswerte laut One-Skill-Doku: open, actioned, declined, superseded, parked.
STATUS_OFFEN = {"open"}
STATUS_PARKED = {"parked"}


class RouterFehler(RuntimeError):
    """Fachlicher Fehler im Dispatcher."""


# --- Zustand --------------------------------------------------------------

def _lade_state():
    try:
        with open(STATE_PFAD, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _speichere_state(state):
    tmp = str(STATE_PFAD) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PFAD)


def _ist_verarbeitet(state, obs_id):
    return bool(state.get("verarbeitet", {}).get(str(obs_id)))


def _markiere_verarbeitet(state, obs_id, ergebnis):
    state.setdefault("verarbeitet", {})[str(obs_id)] = ergebnis
    _speichere_state(state)


# --- Observation lesen (untrusted) ---------------------------------------

def _parse_frontmatter(text):
    """YAML-Frontmatter zwischen zwei `---`-Zeilen parsen.

    Liefert (frontmatter_dict, fehler). Bei fehlendem/ungueltigem Frontmatter
    wird die Beobachtung NICHT verarbeitet (untrusted: nichts raten).
    """
    if yaml is None:
        return None, "PyYAML nicht installiert"
    zeilen = text.splitlines()
    if not zeilen or zeilen[0].strip() != "---":
        return None, "kein YAML-Frontmatter (erste Zeile ist nicht '---')"
    # Ende des Frontmatters: zweite '---'-Zeile.
    ende = None
    for i in range(1, len(zeilen)):
        if zeilen[i].strip() == "---":
            ende = i
            break
    if ende is None:
        return None, "Frontmatter nicht abgeschlossen (keine zweite '---')"
    block = "\n".join(zeilen[1:ende])
    try:
        data = yaml.safe_load(block)
    except Exception as e:  # noqa: BLE001 - untrusted, kein Raten
        return None, "Frontmatter nicht parsebar: %s" % str(e)[:120]
    if not isinstance(data, dict):
        return None, "Frontmatter ist kein Mapping"
    return data, None


def _observation_id(datei, frontmatter):
    """Stabile ID: `id:`-Feld, sonst Dateiname ohne Endung."""
    fid = frontmatter.get("id")
    if isinstance(fid, int) or (isinstance(fid, str) and fid.strip()):
        return str(fid).strip()
    return Path(datei).stem


def _ist_offen(frontmatter):
    """status fehlt = open (Doku); parked ist NICHT offen."""
    status = str(frontmatter.get("status", "open")).strip().lower()
    if status in STATUS_PARKED:
        return False
    return status in STATUS_OFFEN


def _target_profile(frontmatter):
    """Eindeutiger, allowlist-valider Fachbot aus `target_profile`.

    Rueckgabe (name, fehler). Fehler wenn: Feld fehlt, kein String, nicht in
    der Allowlist, oder kein bestehendes Profil auf der Platte.
    """
    tp = frontmatter.get("target_profile")
    if tp is None:
        return None, "kein target_profile-Feld"
    if not isinstance(tp, str) or not tp.strip():
        return None, "target_profile ist kein gueltiger Name"
    name = tp.strip()
    if name not in ALLOWLIST:
        return None, "target_profile %r nicht in der Allowlist" % name
    if not (PROFILES / name / "config.yaml").is_file():
        return None, "Profil %r existiert nicht auf der Platte" % name
    return name, None


def _sammle_offene(obs_root):
    """Alle offenen, nicht geparkten Beobachtungen, sortiert nach Dateiname."""
    if not obs_root.is_dir():
        return []
    offene = []
    for datei in sorted(obs_root.glob("*.md")):
        try:
            text = datei.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, fehler = _parse_frontmatter(text)
        if fehler or fm is None:
            continue  # unparsebar = nicht verarbeiten
        if not _ist_offen(fm):
            continue
        offene.append((datei, fm))
    return offene


# --- Hermes-Aufruf (synchron) ---------------------------------------------

def _hermes_umgebung():
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env["HERMES_HOME"] = str(WURZEL / "Agenten" / "Hermes")
    return env


def _rufe_bot(name, text, frist=1800):
    """Einen Fachbot synchron aufrufen und auf das Ergebnis warten.

    `hermes -p NAME chat -q TEXT -Q` - derselbe Weg wie skillsbot._bot_fragen.
    """
    exe = str(HERMES_EXE)
    if not os.path.isfile(exe):
        raise RouterFehler("hermes.exe nicht gefunden: %s" % exe)
    try:
        lauf = subprocess.Popen(
            [exe, "-p", name, "chat", "-q", text, "-Q"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", env=_hermes_umgebung(),
            cwd=str(WURZEL),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as e:
        raise RouterFehler("Bot %s nicht startbar: %s" % (name, e))
    try:
        aus, fehler = lauf.communicate(timeout=frist)
    except subprocess.TimeoutExpired:
        lauf.kill()
        lauf.communicate()
        raise RouterFehler(
            "Bot %s hat nach %d Minuten nicht geantwortet"
            % (name, frist // 60))
    if lauf.returncode != 0:
        stderr = (fehler or "").strip().splitlines()
        grund = stderr[-1][:200] if stderr else "Exit-Code %s" % lauf.returncode
        raise RouterFehler("Bot %s gescheitert: %s" % (name, grund))
    antwort = (aus or "").strip()
    zeilen = [z for z in antwort.splitlines()
              if not z.startswith("session_id:")]
    return "\n".join(zeilen).strip() or "(leere Antwort)"


# --- Kernlogik ------------------------------------------------------------

def _prompt_recherche(frontmatter):
    """Der Recherche-Auftrag aus der Observation (untrusted, nur Felder)."""
    titel = str(frontmatter.get("title", "")).strip()
    bereich = str(frontmatter.get("area", "")).strip()
    session = str(frontmatter.get("session_context", "")).strip()
    teile = ["Beobachtung aus dem Observation-Log; recherchiere den Sachverhalt."]
    if titel:
        teile.append("Titel: %s" % titel)
    if bereich:
        teile.append("Bereich: %s" % bereich)
    if session:
        teile.append("Kontext: %s" % session)
    teile.append("Antworte knapp: was ist der Stand, was ist zu tun.")
    return "\n".join(teile)


def _prompt_fachbot(frontmatter, recherche_ergebnis):
    """Der Fachbot-Auftrag: Recherche-Ergebnis + Beobachtungskontext."""
    titel = str(frontmatter.get("title", "")).strip()
    teile = ["Beobachtung (aus dem Observation-Log):"]
    if titel:
        teile.append("Titel: %s" % titel)
    teile.append("")
    teile.append("Recherche-Ergebnis:")
    teile.append(recherche_ergebnis)
    teile.append("")
    teile.append("Bewerte und schlage die konkrete naechste Aktion vor.")
    return "\n".join(teile)


def _verarbeite_eine(obs_root, dispatch):
    """Eine offene Beobachtung verarbeiten. Rueckgabe: (obs_id, ergebnis, fehler)."""
    state = _lade_state()
    offene = _sammle_offene(obs_root)
    for datei, fm in offene:
        obs_id = _observation_id(datei, fm)
        if _ist_verarbeitet(state, obs_id):
            continue  # idempotent: bereits verarbeitet ueberspringen
        # Routing-Vertrag pruefen, BEVOR irgendetwas gestartet wird.
        ziel, fehler = _target_profile(fm)
        if fehler:
            return obs_id, None, fehler
        if not dispatch:
            return obs_id, "dry-run: wuerde Recherche + Fachbot %s starten" % ziel, None
        # 1) Recherche synchron.
        try:
            recherche = _rufe_bot("recherche", _prompt_recherche(fm))
        except RouterFehler as e:
            return obs_id, None, "Recherche fehlgeschlagen: %s" % e
        # 2) Genau EIN Fachbot danach.
        try:
            fachbot = _rufe_bot(ziel, _prompt_fachbot(fm, recherche))
        except RouterFehler as e:
            return obs_id, None, "Fachbot %s fehlgeschlagen: %s" % (ziel, e)
        ergebnis = {
            "ziel": ziel,
            "recherche": recherche,
            "fachbot": fachbot,
        }
        _markiere_verarbeitet(state, obs_id, ergebnis)
        return obs_id, ergebnis, None
    return None, None, None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Observations-Router")
    parser.add_argument("--dispatch", action="store_true",
                        help="verarbeitet EINE offene Beobachtung (Default: dry-run)")
    parser.add_argument("--dry-run", action="store_true",
                        help="nur anzeigen, nichts starten (Default)")
    args = parser.parse_args(argv)

    if not OBS_ROOT.is_dir():
        print("Observation-Log fehlt: %s" % OBS_ROOT)
        return 2

    obs_id, ergebnis, fehler = _verarbeite_eine(OBS_ROOT, args.dispatch)

    if obs_id is None:
        print("Keine offene, nicht geparkte Beobachtung gefunden.")
        return 0
    if fehler:
        print("Beobachtung %s: %s" % (obs_id, fehler))
        return 1
    if isinstance(ergebnis, str):  # dry-run
        print("Beobachtung %s: %s" % (obs_id, ergebnis))
        return 0
    print("Beobachtung %s verarbeitet -> Fachbot %s" % (obs_id, ergebnis["ziel"]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
