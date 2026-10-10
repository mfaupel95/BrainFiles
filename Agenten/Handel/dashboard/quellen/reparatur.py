# dashboard/quellen/reparatur.py
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

_HIER = Path(__file__).resolve().parent.parent.parent  # Agenten/Handel/
_LOG_VERALTET_SEKUNDEN = 3600  # 60 Minuten


def _befund(id_: str, titel: str, beschreibung: str, behebbar: bool) -> dict:
    return {"id": id_, "titel": titel, "beschreibung": beschreibung, "behebbar": behebbar}


def _pid() -> int | None:
    try:
        return int((_HIER / "dauerlauf.pid").read_text(encoding="ascii").strip().split()[0])
    except Exception:
        return None


def alle_checks() -> list[dict]:
    from dashboard.quellen import prozesse

    befunde = []
    pid = _pid()
    laeuft = pid is not None and prozesse._prozess_lebt(pid)

    # Check 1: Zombie-PID
    if pid is not None and not laeuft:
        befunde.append(_befund(
            "zombie_pid", "Zombie-PID",
            f"dauerlauf.pid enthält PID {pid}, aber kein laufender Prozess gefunden.",
            behebbar=True))

    # Check 2: Log veraltet
    log = _HIER / "dauerlauf.log"
    if log.is_file():
        alter_s = time.time() - log.stat().st_mtime
        if alter_s > _LOG_VERALTET_SEKUNDEN:
            befunde.append(_befund(
                "log_veraltet", "Log veraltet",
                f"dauerlauf.log wurde vor {int(alter_s / 60)} Minuten zuletzt geschrieben.",
                behebbar=False))

    # Check 3: Fenster offen, kein Prozess
    fp = _HIER / "freigabe_fenster.json"
    if fp.is_file() and not laeuft:
        try:
            fenster = json.loads(fp.read_text(encoding="utf-8"))
            jetzt = dt.datetime.now(dt.timezone.utc)
            for spur, eintrag in fenster.items():
                bis = (eintrag or {}).get("offen_bis")
                if not bis:
                    continue
                try:
                    d = dt.datetime.fromisoformat(bis)
                    if d.tzinfo is None:
                        d = d.replace(tzinfo=dt.timezone.utc)
                    if d > jetzt:
                        befunde.append(_befund(
                            f"fenster_offen_{spur}", f"Fenster offen, kein Prozess: {spur}",
                            f"Freigabefenster für {spur} ist offen bis {bis}, dauerlauf.py läuft nicht.",
                            behebbar=False))
                except ValueError:
                    pass
        except Exception:
            pass

    return befunde


def fix_ausfuehren(check_id: str) -> dict:
    if check_id == "zombie_pid":
        try:
            (_HIER / "dauerlauf.pid").unlink(missing_ok=True)
            return {"ok": True, "meldung": "dauerlauf.pid gelöscht"}
        except Exception as ex:
            return {"ok": False, "meldung": str(ex)}
    return {"ok": False, "meldung": f"Kein Fix für {check_id} bekannt"}
