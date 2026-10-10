# dashboard/quellen/prozesse.py
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

_HIER = Path(__file__).resolve().parent.parent.parent  # Agenten/Handel/
_WURZEL = _HIER.parent.parent  # BrainFiles/
_PY = _HIER / "scanner" / ".venv" / "Scripts" / "python.exe"
_SYS32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
_CREATE_NEW_CONSOLE = 0x00000010
_SPURNAME = re.compile(r"^[A-Za-z0-9_-]+$")


def _prozess_lebt(pid: int) -> bool:
    try:
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x100000, False, pid)
        if not handle:
            return False
        result = ctypes.c_ulong(0)
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(result))
        ctypes.windll.kernel32.CloseHandle(handle)
        return result.value == 259  # STILL_ACTIVE
    except Exception:
        return False


def _pid_dauerlauf() -> int | None:
    try:
        return int((_HIER / "dauerlauf.pid").read_text(encoding="ascii").strip().split()[0])
    except Exception:
        return None


def _omnitrade_lage() -> dict:
    try:
        if str(_HIER) not in sys.path:
            sys.path.insert(0, str(_HIER))
        import omnitrade_lauf  # type: ignore
        return omnitrade_lauf.beurteile()
    except Exception:
        return {}


def _omnitrade_laeuft() -> bool:
    return bool(_omnitrade_lage().get("laeuft", False))


def _taskkill(pid: int) -> None:
    subprocess.run([os.path.join(_SYS32, "taskkill.exe"), "/F", "/PID", str(pid)],
                   capture_output=True)


def systemprozesse() -> list[dict]:
    pid = _pid_dauerlauf()
    dauerlauf_laeuft = pid is not None and _prozess_lebt(pid)
    return [
        {"name": "dauerlauf", "laeuft": dauerlauf_laeuft, "pid": pid},
        {"name": "omnitrade", "laeuft": _omnitrade_laeuft(), "pid": None},
    ]


def system_starten(name: str) -> None:
    if name == "dauerlauf":
        subprocess.Popen([str(_PY), str(_HIER / "dauerlauf.py")],
                         creationflags=_CREATE_NEW_CONSOLE, cwd=str(_HIER), close_fds=True)
    elif name == "omnitrade":
        subprocess.Popen(["cmd.exe", "/c", str(_WURZEL / "omnitrade.cmd"), "start"],
                         creationflags=_CREATE_NEW_CONSOLE, close_fds=True)


def system_stoppen(name: str) -> None:
    if name == "dauerlauf":
        pid = _pid_dauerlauf()
        if pid:
            _taskkill(pid)
    elif name == "omnitrade":
        pid = _omnitrade_lage().get("pid")
        if pid:
            _taskkill(pid)


def spur_not_aus(spur: str) -> dict:
    """Schreibt handel_erlaubt=false in die wachen.json der Spur. Ruft keine externe API."""
    if not _SPURNAME.match(spur or ""):
        return {"ok": False, "meldung": "ungueltiger Spurname"}
    wachen_pfad = _HIER / spur / "wachen.json"
    if not wachen_pfad.is_file():
        return {"ok": False, "meldung": f"wachen.json für {spur} nicht gefunden"}
    try:
        d = json.loads(wachen_pfad.read_text(encoding="utf-8"))
        d["handel_erlaubt"] = False
        wachen_pfad.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"ok": True, "meldung": f"{spur}: handel_erlaubt=false gesetzt"}
    except Exception as ex:
        return {"ok": False, "meldung": str(ex)}
