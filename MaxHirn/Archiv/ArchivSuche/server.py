"""
Lokaler Webserver fuer die Archiv-Suche (nur 127.0.0.1, kein Netzwerkzugriff von aussen).

Aufruf:
    python server.py            # startet auf http://127.0.0.1:8756 und oeffnet den Browser
"""

import json
import os
import sqlite3
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import index as ix

HOST = "127.0.0.1"
PORT = 8756

SELF_DIR = Path(__file__).resolve().parent
# Wurzel der Archivdaten: seit dem echten Umzug (07.09.2026) auf O:\Archiv, per
# ARCHIV_ROOT angebunden. Fallback auf die alte Vault-Lage. Der Webserver
# liefert echte Dateien aus (safe_resolve), deshalb muss ROOT auf die Daten
# zeigen, nicht auf das Werkzeugverzeichnis.
ROOT = Path(os.environ.get("ARCHIV_ROOT") or SELF_DIR.parent)
DB_PATH = SELF_DIR / "archiv_index.db"
STATIC_DIR = SELF_DIR / "static"


def build_match_query(raw_query):
    terms = raw_query.split()
    escaped = [t.replace('"', '""') for t in terms]
    return " ".join(f'"{t}"' for t in escaped)


def do_search(q, category, limit):
    if not DB_PATH.exists():
        return {"error": "Kein Index gefunden. Bitte zuerst indexieren."}
    match_query = build_match_query(q)
    if not match_query:
        return {"results": []}
    conn = sqlite3.connect(str(DB_PATH))
    sql = """
        SELECT path, filename, category,
               snippet(files_fts, 3, '<mark>', '</mark>', ' ... ', 14) AS snip
        FROM files_fts
        WHERE files_fts MATCH ?
    """
    params = [match_query]
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        conn.close()
        return {"error": f"Ungueltige Suchanfrage: {e}"}
    conn.close()
    results = [
        {"path": p, "filename": f, "category": c, "snippet": " ".join(s.split())}
        for p, f, c, s in rows
    ]
    return {"results": results}


def do_reindex():
    python_exe = sys.executable
    proc = subprocess.run(
        [python_exe, str(SELF_DIR / "index.py")],
        cwd=str(SELF_DIR),
        capture_output=True,
        text=True,
        timeout=1800,
    )
    return {"stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(), "returncode": proc.returncode}


def do_sort_inbox():
    python_exe = sys.executable
    proc = subprocess.run(
        [python_exe, str(SELF_DIR / "sort_inbox.py")],
        cwd=str(SELF_DIR),
        capture_output=True,
        text=True,
        timeout=1800,
    )
    return {"stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(), "returncode": proc.returncode}


def safe_resolve(rel_path):
    target = (ROOT / rel_path).resolve()
    if ROOT.resolve() not in target.parents and target != ROOT.resolve():
        return None
    if not target.exists():
        return None
    return target


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            html = (STATIC_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        if parsed.path == "/api/categories":
            self._send_json({"categories": ix.get_scan_dirs()})
            return

        if parsed.path == "/api/search":
            qs = parse_qs(parsed.query)
            q = qs.get("q", [""])[0]
            category = qs.get("category", [""])[0] or None
            limit = int(qs.get("limit", ["25"])[0])
            self._send_json(do_search(q, category, limit))
            return

        if parsed.path == "/api/open":
            qs = parse_qs(parsed.query)
            rel_path = qs.get("path", [""])[0]
            target = safe_resolve(rel_path)
            if not target:
                self._send_json({"error": "Datei nicht gefunden"}, 404)
                return
            try:
                os.startfile(str(target))
                self._send_json({"ok": True})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        if parsed.path == "/api/open_folder":
            qs = parse_qs(parsed.query)
            rel_path = qs.get("path", [""])[0]
            target = safe_resolve(rel_path)
            if not target:
                self._send_json({"error": "Datei nicht gefunden"}, 404)
                return
            try:
                subprocess.run(["explorer", "/select,", str(target)])
                self._send_json({"ok": True})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/reindex":
            self._send_json(do_reindex())
            return
        if parsed.path == "/api/sort_inbox":
            self._send_json(do_sort_inbox())
            return
        self.send_response(404)
        self.end_headers()


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print(f"Archiv-Suche laeuft auf {url} (Strg+C zum Beenden)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
