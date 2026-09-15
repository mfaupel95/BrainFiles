# Einmaliger Eintrag: projectatlas ins MCP-Manifest schreiben (gezielter Ersatz, kein Rewrite).
# Nutzt chr(92) fuer Backslashes, damit die Pfade nicht durch Shell-Escaping zerstoert werden.
import json, pathlib

BS = chr(92)
p = pathlib.Path("MCP-Manifest.json")
raw = p.read_bytes()
anchor = b'\r\n  ],\r\n  "disabled": ['
assert raw.count(anchor) == 1, f"Anker {raw.count(anchor)}x gefunden"

base = "C:" + BS + BS.join(["Users", "faupe", "Documents", "BrainFiles", "Werkstatt", "omnitrade", ".projectatlas"])
entry = {
    "name": "projectatlas",
    "enabled": True,
    "agent": "hermes",
    "type": "stdio",
    "command": BS.join(["Agenten", "Werkzeuge", "projectatlas", "bin", "projectatlas.exe"]),
    "args": [
        "--require-version", "0.4.5",
        "--db", base + BS + "projectatlas.db",
        "--config", base + BS + "config.toml",
        "mcp",
    ],
    "cwd": BS.join(["Agenten", "Werkzeuge", "projectatlas"]),
    "description": ("Repository-Karte fuer Agenten (Rust-CLI + SQLite, MIT): 43 atlas_*-Werkzeuge fuehren den Agenten "
                    "zur richtigen Datei, statt breit zu lesen. EIN Server bedient jedes indexierte Repo; "
                    "Standard-Atlas ist Werkstatt/omnitrade, umschalten mit project_path bzw. atlas_set_project_path. "
                    "Laufzeit, Grenzen und Bedienung: Wissen/Projektatlas.md. Nur bei Hermes eingetragen; "
                    "Claude Desktop/Claude Code bekommen den Server projektweise."),
}
body = json.dumps(entry, indent=2, ensure_ascii=True).replace("\n", "\r\n    ").encode("utf-8")
block = b",\r\n" + body
assert body.count(b'  "name"') == 1

# Zeile fuer Zeile einfuegen: der Anker wird nicht verschoben, wenn eine zweite Sitzung ihn anfasst
new = raw.replace(anchor, block + anchor, 1)
new = new.replace(b'"version": "1.1"', b'"version": "1.2"', 1)
new = new.replace(b'"updated": "2026-09-11"', b'"updated": "2026-09-13"', 1)
d = json.loads(new.decode("utf-8"))
names = [s["name"] for s in d["servers"]]
print("Server im Manifest:", len(names))
print("neu dabei:", "projectatlas" in names)
p.write_bytes(new)
print("Bytes", len(raw), "->", len(new))
