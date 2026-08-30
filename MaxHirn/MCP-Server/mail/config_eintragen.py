"""
Traegt den Mail-Server in claude_desktop_config.json ein.

Legt vorher eine datierte Sicherung an und laesst alle anderen Eintraege
unangetastet. Mehrfacher Aufruf ist unschaedlich.

Aufruf:
    .venv\\Scripts\\python.exe config_eintragen.py
"""

import json
import shutil
import time
from pathlib import Path

CONFIG = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
HIER = Path(__file__).resolve().parent


def main() -> int:
    if not CONFIG.exists():
        print(f"Nicht gefunden: {CONFIG}")
        return 1

    daten = json.loads(CONFIG.read_text(encoding="utf-8"))
    server = daten.setdefault("mcpServers", {})
    neu = {
        "command": str(HIER / ".venv" / "Scripts" / "python.exe"),
        "args": [str(HIER / "mail_mcp.py")],
    }
    if server.get("mail") == neu:
        print("Eintrag 'mail' ist bereits aktuell.")
        return 0

    sicherung = CONFIG.with_suffix(f".json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(CONFIG, sicherung)
    server["mail"] = neu
    CONFIG.write_text(json.dumps(daten, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Eingetragen. Sicherung: {sicherung.name}")
    print("Claude Desktop neu starten, damit der Server geladen wird.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
