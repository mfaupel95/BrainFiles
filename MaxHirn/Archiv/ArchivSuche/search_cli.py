"""
Kommandozeilen-Suche im Archiv-Index.

Aufruf:
    python search_cli.py "suchbegriff"
    python search_cli.py "rechnung schrauben" --limit 5
    python search_cli.py "kuendigung" --category Dokumente
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Ohne UTF-8 verstuemmelt die Windows-Konsole (cp1252) Umlaute in den
# Trefferausschnitten zu Fragezeichen - unleserlich und unnoetiger Ballast.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = Path(__file__).resolve().parent / "archiv_index.db"


def build_match_query(raw_query):
    terms = raw_query.split()
    if not terms:
        return ""
    escaped = [t.replace('"', '""') for t in terms]
    return " ".join(f'"{t}"' for t in escaped)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Suchbegriff(e)")
    # 5 Treffer reichen fast immer, um die gesuchte Datei zu erkennen; mehr
    # kostet nur Ausgabe. Bei Bedarf hochsetzen.
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--category", default=None, help="Bilder | Videos | Musik | Dokumente")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("Kein Index gefunden. Bitte zuerst 'python index.py' ausfuehren.")
        return 1

    match_query = build_match_query(args.query)
    if not match_query:
        print("Leere Suchanfrage.")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    sql = """
        SELECT path, filename, category,
               snippet(files_fts, 3, '[', ']', ' ... ', 12) AS snip
        FROM files_fts
        WHERE files_fts MATCH ?
    """
    params = [match_query]
    if args.category:
        sql += " AND category = ?"
        params.append(args.category)
    sql += " ORDER BY rank LIMIT ?"
    params.append(args.limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    if not rows:
        print(f"Keine Treffer fuer: {args.query}")
        return 0

    for path, filename, category, snip in rows:
        snip = " ".join(snip.split())
        print(f"[{category}] {path}")
        if snip:
            print(f"    {snip}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
