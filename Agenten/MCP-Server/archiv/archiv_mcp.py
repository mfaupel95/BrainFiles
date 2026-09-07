"""
Archiv-MCP: stellt Max' Dateiarchiv als MCP-Server bereit.

Liest ausschliesslich den fertigen Volltextindex aus
Archiv/ArchivSuche/archiv_index.db. Der Server ist bewusst nur lesend - er
verschiebt, loescht und indexiert nichts. Das Einsortieren bleibt beim Skill
`posteingang`, wo Max den Lauf sieht.

Aufruf (stdio):
    .venv\\Scripts\\python.exe archiv_mcp.py

Testen:
    npx -y @modelcontextprotocol/inspector .venv\\Scripts\\python.exe archiv_mcp.py
"""

import sqlite3
import os
import sys
import time
from pathlib import Path

from mcp.server.mcpserver import MCPServer

# stdout gehoert dem JSON-RPC-Protokoll. Jede Ausgabe dorthin zerstoert die
# Verbindung, und der Fehler sieht aus wie ein Verbindungsabbruch - deshalb
# gehen Diagnosemeldungen ausschliesslich nach stderr.
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Zwei getrennte Wurzeln seit dem echten Umzug (07.09.2026):
#   - Der Index und das Werkzeug bleiben beim Vault auf C: (git-versioniert,
#     DB neu baubar). Ueber MAXHIRN_VAULT bzw. den relativen Rueckfall
#     Agenten/MCP-Server/archiv/ -> BrainFiles/ -> MaxHirn/.
#   - Die Archivdaten (Bilder/Dokumente/Musik/Videos/Posteingang) liegen auf
#     O:\Archiv, angebunden ueber ARCHIV_ROOT (User-Umgebungsvariable, wie
#     OLLAMA_MODELS). Rueckfall auf die alte Vault-Lage.
VAULT = Path(os.environ.get("MAXHIRN_VAULT") or (Path(__file__).resolve().parents[3] / "MaxHirn"))
INDEX_DIR = VAULT / "Archiv" / "ArchivSuche"
ARCHIV = Path(os.environ.get("ARCHIV_ROOT") or (VAULT / "Archiv"))
DB_PATH = INDEX_DIR / "archiv_index.db"
POSTEINGANG = ARCHIV / "Posteingang"

KATEGORIEN = ("Bilder", "Videos", "Musik", "Dokumente")

mcp = MCPServer("Archiv")


def _verbinden():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Kein Index unter {DB_PATH}. Zuerst 'python index.py' in ArchivSuche ausfuehren."
        )
    # Nur-Lesen-Verbindung: der Server kann den Index nicht beschaedigen, auch
    # nicht bei einem Fehler. busy_timeout, damit ein laufender Indexlauf
    # (WAL-Modus) die Suche nicht sofort scheitern laesst.
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def _match_query(roh: str) -> str:
    """Baut eine FTS5-MATCH-Anfrage. Jeder Begriff wird gequotet, sonst legen
    Sonderzeichen wie '-' oder ':' den Parser lahm."""
    begriffe = [t.replace('"', '""') for t in roh.split() if t.strip()]
    return " ".join(f'"{t}"' for t in begriffe)


@mcp.tool()
def archiv_suchen(query: str, kategorie: str | None = None, limit: int = 5) -> list[dict]:
    """Durchsucht Max' persoenliches Dateiarchiv im Volltext.

    Enthaelt eigene Rechnungen, Vertraege, Belege, Notizen, Anleitungen,
    Rezepte, Fotos, Screenshots und Musik - auch der Text aus gescannten PDFs
    und Bildern (per OCR). Immer VOR einer Internetsuche benutzen, wenn die
    Frage eigene Unterlagen betreffen koennte.

    Args:
        query: Suchbegriffe, mit Leerzeichen getrennt (UND-verknuepft).
        kategorie: Optional auf Bilder, Videos, Musik oder Dokumente einschraenken.
        limit: Anzahl Treffer, Standard 5.

    Returns:
        Treffer mit Pfad (relativ zum Archiv), Kategorie und Textausschnitt.
    """
    if kategorie and kategorie not in KATEGORIEN:
        raise ValueError(f"Unbekannte Kategorie {kategorie!r}. Erlaubt: {', '.join(KATEGORIEN)}")
    match = _match_query(query)
    if not match:
        raise ValueError("Leere Suchanfrage.")

    sql = """
        SELECT path, filename, category,
               snippet(files_fts, 3, '[', ']', ' ... ', 15) AS snip
        FROM files_fts
        WHERE files_fts MATCH ?
    """
    params: list = [match]
    if kategorie:
        sql += " AND category = ?"
        params.append(kategorie)
    sql += " ORDER BY rank LIMIT ?"
    params.append(max(1, min(limit, 50)))

    conn = _verbinden()
    try:
        zeilen = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    return [
        {
            "pfad": pfad,
            "dateiname": name,
            "kategorie": kat,
            "ausschnitt": " ".join((snip or "").split()),
        }
        for pfad, name, kat, snip in zeilen
    ]


@mcp.tool()
def archiv_datei_lesen(pfad: str, max_zeichen: int = 5000) -> dict:
    """Liefert den indexierten Volltext einer Archivdatei.

    Der Pfad muss aus einem Treffer von `archiv_suchen` stammen. Gelesen wird
    der bereits extrahierte Text aus dem Index, nicht die Datei selbst - damit
    kann dieses Werkzeug keine beliebigen Dateien vom Rechner ausgeben.

    Args:
        pfad: Pfad aus einem Suchtreffer, relativ zum Archiv.
        max_zeichen: Obergrenze der Rueckgabe, Standard 5000.
    """
    conn = _verbinden()
    try:
        treffer = conn.execute(
            "SELECT path, filename, category, content FROM files_fts WHERE path = ?", (pfad,)
        ).fetchone()
        meta = conn.execute(
            "SELECT ext, size, mtime, ocr_used, extract_status FROM files_meta WHERE path = ?",
            (pfad,),
        ).fetchone()
    finally:
        conn.close()

    if treffer is None:
        raise ValueError(f"Nicht im Index: {pfad!r}. Pfad aus einem Treffer von archiv_suchen nehmen.")

    _, name, kat, inhalt = treffer
    inhalt = inhalt or ""
    gekuerzt = len(inhalt) > max_zeichen
    ergebnis = {
        "pfad": pfad,
        "dateiname": name,
        "kategorie": kat,
        "text": inhalt[:max_zeichen],
        "gekuerzt": gekuerzt,
        "zeichen_gesamt": len(inhalt),
        "vollstaendiger_pfad": str(ARCHIV / pfad),
    }
    if meta:
        ext, size, mtime, ocr, status = meta
        ergebnis |= {
            "endung": ext,
            "groesse_bytes": size,
            "geaendert": time.strftime("%Y-%m-%d", time.localtime(mtime)) if mtime else None,
            "per_ocr_erkannt": bool(ocr),
            "extraktion": status,
        }
    return ergebnis


@mcp.tool()
def archiv_statistik() -> dict:
    """Zeigt Umfang und Aktualitaet des Archivindex.

    Nuetzlich, um zu pruefen, ob eine erfolglose Suche an einem veralteten
    Index liegt.
    """
    conn = _verbinden()
    try:
        gesamt = conn.execute("SELECT COUNT(*) FROM files_meta").fetchone()[0]
        je_kategorie = dict(
            conn.execute(
                "SELECT category, COUNT(*) FROM files_meta GROUP BY category ORDER BY 2 DESC"
            ).fetchall()
        )
        mit_ocr = conn.execute("SELECT COUNT(*) FROM files_meta WHERE ocr_used = 1").fetchone()[0]
        neuester = conn.execute("SELECT MAX(indexed_at) FROM files_meta").fetchone()[0]
    finally:
        conn.close()

    return {
        "dateien_gesamt": gesamt,
        "je_kategorie": je_kategorie,
        "per_ocr_erschlossen": mit_ocr,
        "zuletzt_indexiert": (
            time.strftime("%Y-%m-%d %H:%M", time.localtime(neuester)) if neuester else None
        ),
        "index_datei": str(DB_PATH),
        "index_groesse_mb": round(DB_PATH.stat().st_size / 1024 / 1024, 1),
    }


@mcp.tool()
def posteingang_stand() -> dict:
    """Listet auf, was unversorgt im Posteingang liegt.

    Der Posteingang ist bewusst nicht im Index. Zum Einsortieren dient
    `sort_inbox.py` bzw. der Skill `posteingang` - dieser Server sieht nur nach.
    """
    if not POSTEINGANG.exists():
        return {"vorhanden": False, "anzahl": 0, "dateien": []}

    dateien = [p for p in POSTEINGANG.rglob("*") if p.is_file()]
    groesse = sum(p.stat().st_size for p in dateien)
    return {
        "vorhanden": True,
        "anzahl": len(dateien),
        "groesse_mb": round(groesse / 1024 / 1024, 1),
        "dateien": [
            {
                "name": p.name,
                "unterordner": str(p.parent.relative_to(POSTEINGANG)) if p.parent != POSTEINGANG else "",
                "groesse_kb": round(p.stat().st_size / 1024, 1),
            }
            for p in sorted(dateien, key=lambda x: x.name)[:100]
        ],
        "hinweis": "Nur die ersten 100 Dateien werden gelistet." if len(dateien) > 100 else None,
    }


if __name__ == "__main__":
    mcp.run()
