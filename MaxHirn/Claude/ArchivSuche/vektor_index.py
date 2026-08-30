"""
Vektor-Indexer fuer das Archiv - semantische Suche, vollstaendig lokal.

Liest den vorhandenen FTS5-Volltextindex (archiv_index.db), zerlegt die Texte in
Abschnitte und legt Einbettungen in einer EIGENEN Datenbank (vektor_index.db) ab.
Der Volltextindex wird dabei nur gelesen und nie veraendert.

Warum eine zweite Datenbank: Ein abgebrochener oder beschaedigter Vektorlauf darf
die funktionierende Volltextsuche nicht gefaehrden. Loeschen von vektor_index.db
setzt den Vektorteil zurueck, sonst passiert nichts.

Warum Ollama: Die Einbettungen laufen auf der GPU, ohne torch/onnxruntime in
diesem venv. Es verlaesst kein Byte den Rechner.

Aufruf:
    python vektor_index.py              # inkrementell, wiederaufnehmbar
    python vektor_index.py --neu        # alles neu einbetten
    python vektor_index.py --limit 200  # nur die ersten N Dateien (Test)
"""

import argparse
import json
import sqlite3
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve().parent
FTS_DB = HIER / "archiv_index.db"
VEK_DB = HIER / "vektor_index.db"

OLLAMA = "http://127.0.0.1:11434"
MODELL = "bge-m3"

# bge-m3 vertraegt 8192 Token. 1200 Zeichen je Abschnitt bleiben deutlich
# darunter und halten die Treffer trotzdem spezifisch - ein ganzes Dokument als
# ein Vektor verwaescht die Bedeutung, einzelne Saetze verlieren den Kontext.
CHUNK_ZEICHEN = 1200
UEBERLAPPUNG = 200
MAX_CHUNKS_JE_DATEI = 40
BATCH = 16

# Nur Dateien mit echtem Text werden eingebettet.
#
# Grund, gemessen am 19.08.2026: Von 7631 Archivdateien haben nur 1076 mehr als
# 200 Zeichen extrahierten Text (1048 Dokumente, 28 Bilder mit OCR-Treffer).
# Musik und Videos haben gar keinen. Bettet man diese Dateien trotzdem ueber
# ihren Dateinamen ein, entstehen Vektoren aus Zeichenketten wie
# "(m=eidYGCjadqg)(mh=kK9HQ...)200x200.jpg" - die sind zu allem maessig
# aehnlich und draengen sich vor jeden echten Treffer. Im ersten Testlauf
# standen genau solche Bilder auf den Plaetzen 1 bis 5 einer Suche nach
# "Rechnung fuer ein Geraet".
#
# Dateien ohne Text findet weiterhin die Volltextsuche ueber Name und Pfad -
# dafuer braucht es keine Bedeutungsaehnlichkeit.
MIN_TEXT_ZEICHEN = 200


def vektor_db(pfad=VEK_DB):
    """Oeffnet die Vektordatenbank und legt das Schema an, falls noetig."""
    c = sqlite3.connect(str(pfad))
    # WAL: Ein harter Stromausfall - auf diesem Rechner ein reales Risiko -
    # laesst die Datenbank so mit dem letzten abgeschlossenen Stand zurueck
    # statt beschaedigt.
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS dateien (
            path        TEXT PRIMARY KEY,
            filename    TEXT,
            category    TEXT,
            mtime       REAL,
            chunks      INTEGER,
            stand       REAL
        );
        CREATE TABLE IF NOT EXISTS abschnitte (
            id      INTEGER PRIMARY KEY,
            path    TEXT NOT NULL,
            nr      INTEGER NOT NULL,
            text    TEXT NOT NULL,
            vektor  BLOB NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_abschnitte_path ON abschnitte(path);
        CREATE TABLE IF NOT EXISTS info (k TEXT PRIMARY KEY, v TEXT);
        """
    )
    c.commit()
    return c


def pack(werte):
    return struct.pack(f"<{len(werte)}f", *werte)


def entpacke(blob):
    return struct.unpack(f"<{len(blob) // 4}f", blob)


def einbetten(texte, praefix):
    """Ruft Ollama auf. praefix: 'passage: ' beim Indexieren, 'query: ' beim Suchen.

    bge-m3 braucht diese Praefixe nicht zwingend, sie schaden aber nicht und
    halten den Aufbau kompatibel, falls spaeter auf ein e5-Modell gewechselt wird.
    """
    rumpf = json.dumps({"model": MODELL, "input": [praefix + t for t in texte]}).encode("utf-8")
    anfrage = urllib.request.Request(
        f"{OLLAMA}/api/embed", data=rumpf, headers={"Content-Type": "application/json"}
    )
    for versuch in range(3):
        try:
            with urllib.request.urlopen(anfrage, timeout=300) as antwort:
                return json.loads(antwort.read())["embeddings"]
        except (urllib.error.URLError, TimeoutError) as fehler:
            if versuch == 2:
                raise
            print(f"    Ollama-Fehler ({fehler}), neuer Versuch in 5 s", flush=True)
            time.sleep(5)


def zerlege(text):
    """Zerlegt Text in ueberlappende Abschnitte an Absatzgrenzen, wo moeglich."""
    text = " ".join(text.split())
    if not text:
        return []
    stuecke = []
    start = 0
    while start < len(text) and len(stuecke) < MAX_CHUNKS_JE_DATEI:
        ende = min(start + CHUNK_ZEICHEN, len(text))
        if ende < len(text):
            # an der letzten Satzgrenze im hinteren Drittel trennen
            fenster = text.rfind(". ", start + (CHUNK_ZEICHEN * 2) // 3, ende)
            if fenster > 0:
                ende = fenster + 1
        stuecke.append(text[start:ende].strip())
        if ende >= len(text):
            break
        start = ende - UEBERLAPPUNG
    return [s for s in stuecke if len(s) > 30]


def zu_erledigen(fts, vek, alles, limit):
    """Dateien, die neu oder seit dem letzten Lauf geaendert sind."""
    bekannt = {p: m for p, m in vek.execute("SELECT path, mtime FROM dateien")}
    offen = []
    frage = """
        SELECT m.path, m.filename, m.category, m.mtime, f.content
        FROM files_meta m JOIN files_fts f ON f.path = m.path
        WHERE LENGTH(f.content) >= ?
    """
    for path, name, kat, mtime, inhalt in fts.execute(frage, (MIN_TEXT_ZEICHEN,)):
        if not alles and bekannt.get(path) == mtime:
            continue
        offen.append((path, name, kat, mtime, inhalt or ""))
        if limit and len(offen) >= limit:
            break
    return offen


def aufraeumen(fts, vek):
    """Entfernt Eintraege, die die Textschwelle nicht (mehr) erfuellen oder deren
    Datei aus dem Volltextindex verschwunden ist. Haelt den Vektorindex sauber,
    ohne dass er komplett neu gebaut werden muss."""
    gueltig = {
        p for (p,) in fts.execute(
            "SELECT path FROM files_fts WHERE LENGTH(content) >= ?", (MIN_TEXT_ZEICHEN,)
        )
    }
    weg = [p for (p,) in vek.execute("SELECT path FROM dateien") if p not in gueltig]
    if weg:
        vek.executemany("DELETE FROM abschnitte WHERE path = ?", [(p,) for p in weg])
        vek.executemany("DELETE FROM dateien   WHERE path = ?", [(p,) for p in weg])
        vek.commit()
        print(f"{len(weg)} Eintraege ohne verwertbaren Text entfernt")
    return len(weg)


def lauf(alles=False, limit=0):
    if not FTS_DB.exists():
        sys.exit(f"Volltextindex fehlt: {FTS_DB} - zuerst index.py laufen lassen.")

    fts = sqlite3.connect(f"file:{FTS_DB}?mode=ro", uri=True)
    vek = vektor_db()
    vek.execute(
        "INSERT OR REPLACE INTO info(k, v) VALUES('modell', ?)", (MODELL,)
    )
    vek.commit()

    aufraeumen(fts, vek)
    offen = zu_erledigen(fts, vek, alles, limit)
    gesamt = len(offen)
    if not gesamt:
        print("Nichts zu tun - alle Dateien sind eingebettet.")
        return

    print(f"{gesamt} Dateien einzubetten (Modell {MODELL})", flush=True)
    begonnen = time.time()
    chunks_gesamt = 0

    for i, (path, name, kat, mtime, inhalt) in enumerate(offen, 1):
        # Dateiname mitindexieren: viele Archivdateien haben wenig Text, aber
        # einen sprechenden Namen.
        basis = f"{name}\n{inhalt}" if inhalt.strip() else name
        stuecke = zerlege(basis)
        if not stuecke:
            continue

        vektoren = []
        for start in range(0, len(stuecke), BATCH):
            vektoren.extend(einbetten(stuecke[start:start + BATCH], "passage: "))

        # Pro Datei eine Transaktion: bricht der Lauf ab, ist jede bis dahin
        # fertige Datei vollstaendig und wird beim naechsten Mal uebersprungen.
        vek.execute("DELETE FROM abschnitte WHERE path = ?", (path,))
        vek.executemany(
            "INSERT INTO abschnitte(path, nr, text, vektor) VALUES(?,?,?,?)",
            [(path, nr, s, pack(v)) for nr, (s, v) in enumerate(zip(stuecke, vektoren))],
        )
        vek.execute(
            "INSERT OR REPLACE INTO dateien(path, filename, category, mtime, chunks, stand)"
            " VALUES(?,?,?,?,?,?)",
            (path, name, kat, mtime, len(stuecke), time.time()),
        )
        vek.commit()
        chunks_gesamt += len(stuecke)

        if i % 25 == 0 or i == gesamt:
            verbraucht = time.time() - begonnen
            rest = verbraucht / i * (gesamt - i)
            print(
                f"  {i}/{gesamt} Dateien, {chunks_gesamt} Abschnitte, "
                f"{verbraucht/60:.1f} min verbraucht, ~{rest/60:.1f} min Rest",
                flush=True,
            )

    print(f"Fertig: {chunks_gesamt} Abschnitte in {(time.time()-begonnen)/60:.1f} min")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--neu", action="store_true", help="alles neu einbetten")
    p.add_argument("--limit", type=int, default=0, help="nur N Dateien (Test)")
    a = p.parse_args()
    lauf(alles=a.neu, limit=a.limit)
