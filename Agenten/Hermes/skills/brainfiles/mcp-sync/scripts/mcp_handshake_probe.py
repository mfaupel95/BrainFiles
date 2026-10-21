"""MCP-Server ohne Client pruefen: initialize + notifications/initialized + tools/list.

Aufruf (aus einem beliebigen Ordner, bevorzugt NICHT dem Serverordner):
    python mcp_handshake_probe.py <befehl> [args...]

Beispiele:
    python mcp_handshake_probe.py C:/.../Werkstatt/ziplime/.venv/Scripts/python.exe -m ziplime.mcp
    python mcp_handshake_probe.py node C:/.../pdf-server-mcp/dist/index.js --stdio <vault-ordner>

Wozu: beweist, dass der Server mit GENAU der command/args-Folge aus der Config
startet und wie viele Werkzeuge er anbietet - ohne Claude Desktop oder Hermes.

Zwei Dinge macht das Skript bewusst:
  * PYTHONPATH/PYTHONHOME/PYTHONSTARTUP werden im Kind ENTFERNT. Sonst erbt ein
    Python-Server die site-packages des Aufrufer-venv und scheitert an fremdem
    pydantic (sieht wie ein Serverfehler aus, ist Umgebungsvererbung).
  * Es laeuft NICHT im Serverordner (cwd = hier). Ein Server, der nur dort
    importierbar ist, hat eine tote editable-.pth - genau der Fehler, den man
    sucht, wird durch cwd aber verdeckt.

Exit-Codes: 0 = initialize und tools/list beantwortet
            2 = keine Antwort auf initialize
            3 = keine Antwort auf tools/list
"""
import json
import os
import subprocess
import sys
import threading

FRIST_S = 45


def lies(p, frist=FRIST_S):
    """Eine Zeile von stdout, oder None nach Frist (Blockade = toter Server)."""
    erg = {}

    def _lesen():
        erg["zeile"] = p.stdout.readline()

    th = threading.Thread(target=_lesen, daemon=True)
    th.start()
    th.join(frist)
    return None if th.is_alive() else erg.get("zeile")


def sende(p, obj):
    p.stdin.write(json.dumps(obj) + "\n")
    p.stdin.flush()


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    umgebung = {k: v for k, v in os.environ.items()
                if k.upper() not in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP")}
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8",
                         bufsize=0, env=umgebung)
    try:
        sende(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                             "clientInfo": {"name": "handshake-probe", "version": "0"}}})
        zeile = lies(p)
        if not zeile:
            print("KEINE ANTWORT auf initialize")
            print("stderr:", p.stderr.read()[:2000])
            return 2
        antwort = json.loads(zeile)
        print("initialize ok:", antwort.get("result", {}).get("serverInfo", {}))

        sende(p, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        sende(p, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        zeile = lies(p)
        if not zeile:
            print("KEINE ANTWORT auf tools/list")
            print("stderr:", p.stderr.read()[:2000])
            return 3
        werkzeuge = json.loads(zeile).get("result", {}).get("tools", [])
        print("tools:", len(werkzeuge))
        print("namen:", ", ".join(w.get("name", "?") for w in werkzeuge))
        return 0
    finally:
        p.kill()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
