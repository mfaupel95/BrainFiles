"""
Semantische Suche im Archiv - findet nach Bedeutung, nicht nach Stichwort.

    python vektor_suche.py "wie war das mit der garantie beim verstaerker"
    python vektor_suche.py "rechnung finanzamt" --limit 10 --kategorie Dokumente
    python vektor_suche.py "..." --hybrid     # zusaetzlich Volltexttreffer mischen

Braucht vektor_index.py (einmal) und den laufenden Ollama-Dienst.
Nichts davon geht ins Internet.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np

from vektor_index import FTS_DB, MODELL, VEK_DB, einbetten

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def lade(kategorie=None):
    """Laedt alle Vektoren in eine Matrix. Bei ~50k Abschnitten sind das rund
    200 MB und knapp eine Sekunde - schnell genug, um auf eine Vektordatenbank
    als zusaetzliches Bauteil zu verzichten."""
    if not VEK_DB.exists():
        sys.exit(f"Kein Vektorindex: {VEK_DB} - zuerst 'python vektor_index.py' laufen lassen.")
    c = sqlite3.connect(f"file:{VEK_DB}?mode=ro", uri=True)
    if kategorie:
        frage = ("SELECT a.path, a.text, a.vektor FROM abschnitte a "
                 "JOIN dateien d ON d.path = a.path WHERE d.category = ?")
        zeilen = c.execute(frage, (kategorie,)).fetchall()
    else:
        zeilen = c.execute("SELECT path, text, vektor FROM abschnitte").fetchall()
    if not zeilen:
        sys.exit("Vektorindex ist leer.")
    pfade = [z[0] for z in zeilen]
    texte = [z[1] for z in zeilen]
    matrix = np.frombuffer(b"".join(z[2] for z in zeilen), dtype=np.float32)
    matrix = matrix.reshape(len(zeilen), -1)
    # normieren, damit das Skalarprodukt der Kosinusaehnlichkeit entspricht
    matrix = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
    return pfade, texte, matrix


def suche(frage, limit=8, kategorie=None):
    pfade, texte, matrix = lade(kategorie)
    v = np.array(einbetten([frage], "query: ")[0], dtype=np.float32)
    v /= np.linalg.norm(v) + 1e-9
    punkte = matrix @ v

    # bester Abschnitt je Datei, damit ein langes Dokument nicht die Liste fuellt
    bestes = {}
    for i, p in enumerate(pfade):
        if p not in bestes or punkte[i] > punkte[bestes[p]]:
            bestes[p] = i
    rang = sorted(bestes.items(), key=lambda kv: -punkte[kv[1]])[:limit]
    return [(p, float(punkte[i]), texte[i]) for p, i in rang]


def volltext(frage, limit=5):
    """Zusatztreffer aus dem FTS5-Index - faengt exakte Namen und Nummern ab,
    bei denen semantische Aehnlichkeit systematisch schwach ist."""
    if not FTS_DB.exists():
        return []
    c = sqlite3.connect(f"file:{FTS_DB}?mode=ro", uri=True)
    begriffe = " OR ".join(w for w in frage.split() if len(w) > 2)
    if not begriffe:
        return []
    try:
        return c.execute(
            "SELECT path, snippet(files_fts, 3, '', '', '...', 20) FROM files_fts "
            "WHERE files_fts MATCH ? ORDER BY rank LIMIT ?", (begriffe, limit)
        ).fetchall()
    except sqlite3.OperationalError:
        return []


def main():
    p = argparse.ArgumentParser()
    p.add_argument("frage", nargs="+")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--kategorie", default=None, help="Bilder | Videos | Musik | Dokumente")
    p.add_argument("--hybrid", action="store_true", help="Volltexttreffer mit anzeigen")
    a = p.parse_args()
    frage = " ".join(a.frage)

    print(f"Semantisch ({MODELL}):\n")
    for pfad, punkte, text in suche(frage, a.limit, a.kategorie):
        print(f"  [{punkte:.3f}] {Path(pfad).name}")
        print(f"          {pfad}")
        print(f"          {text[:200].strip()}...\n")

    if a.hybrid:
        treffer = volltext(frage)
        if treffer:
            print("Volltext (exakte Begriffe):\n")
            for pfad, ausschnitt in treffer:
                print(f"  {Path(pfad).name}\n          {pfad}\n          {ausschnitt}\n")


if __name__ == "__main__":
    main()
