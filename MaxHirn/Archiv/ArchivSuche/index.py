"""
Archiv-Indexer: durchsucht die Ordner Bilder/Videos/Musik/Dokumente und baut
einen durchsuchbaren SQLite-Volltextindex (FTS5) inkl. OCR fuer Bilder/Scans.

Aufruf:
    python index.py            # inkrementell (nur neue/geaenderte Dateien)
    python index.py --full     # erzwingt Neuextraktion aller Dateien
"""

import argparse
import os
import shutil
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# Dateinamen enthalten Sonderzeichen (Ω, Rahmenzeichen aus alten Backups) - ohne
# UTF-8 bricht die Ausgabe auf der Windows-Konsole (cp1252) mitten im Lauf ab.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Die zu durchsuchenden Archivordner (Bilder/Dokumente/Musik/Videos/...) liegen
# seit dem echten Umzug (07.09.2026) physisch auf O:\Archiv und sind NICHT mehr
# als Junction im Vault erreichbar. ARCHIV_ROOT zeigt darauf (User-Umgebungs-
# variable, wie OLLAMA_MODELS). Fallback auf die alte Vault-Lage, damit das Tool
# nach einem SSD-Umzug ohne gesetzte Variable weiterlaeuft, solange die Daten
# wieder daneben liegen.
ROOT = Path(os.environ.get("ARCHIV_ROOT") or Path(__file__).resolve().parent.parent)
# Der Index bleibt beim Werkzeug auf C: (git-versionierter Code, neu baubare DB).
DB_PATH = Path(__file__).resolve().parent / "archiv_index.db"

# Ordner, die NICHT zum durchsuchbaren Archiv gehoeren (Tool selbst, Posteingang,
# alte Projektordner, versteckte Ordner). Alles andere auf oberster Ebene wird
# automatisch mitindexiert - auch neu angelegte Hauptordner.
# "Software" enthaelt Installationsdateien (Linux/Windows) und eine iCloud-Sicherung.
# Beides ist kein Archivinhalt, blaeht den Index um ein Vielfaches auf und macht
# jeden Indexlauf um Stunden laenger.
EXCLUDE_DIRS = {"ArchivSuche", "Posteingang", ".claude", "FocusTimer", "Worktrees", "Software"}

# Ordner mit Zugangsdaten gehoeren nicht in einen Volltextindex - sonst stehen
# Passwoerter, Wiederherstellungsschluessel und 2FA-Codes im Klartext in der
# Datenbank und tauchen bei jeder Suche auf. Diese Namen werden auf JEDER Ebene
# uebersprungen, nicht nur direkt unter der Wurzel.
EXCLUDE_ANY_LEVEL = {"Passkeys"}


def get_scan_dirs():
    return sorted(
        p.name for p in ROOT.iterdir()
        if p.is_dir() and p.name not in EXCLUDE_DIRS and not p.name.startswith(".")
    )


SCAN_DIRS = get_scan_dirs()

MAX_CONTENT_CHARS = 300_000

TEXT_EXTS = {".txt", ".md", ".csv", ".log"}
PDF_EXTS = {".pdf"}
DOCX_EXTS = {".docx"}
XLSX_EXTS = {".xlsx", ".xlsm"}
PPTX_EXTS = {".pptx"}
ODF_EXTS = {".odt", ".odp", ".ods"}
AUDIO_EXTS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".wma", ".aif", ".aiff", ".aac", ".opus"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp", ".heic", ".heif"}

DEFAULT_TESSERACT_LOCATIONS = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
]


def find_tesseract_cmd():
    found = shutil.which("tesseract")
    if found:
        return found
    for candidate in DEFAULT_TESSERACT_LOCATIONS:
        if candidate.exists():
            return str(candidate)
    return None


TESSERACT_CMD = find_tesseract_cmd()
TESSERACT_AVAILABLE = TESSERACT_CMD is not None
LOCAL_TESSDATA_DIR = Path(__file__).resolve().parent / "tessdata"

if TESSERACT_AVAILABLE:
    import os

    import pytesseract as _pytesseract

    _pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    if LOCAL_TESSDATA_DIR.exists():
        os.environ["TESSDATA_PREFIX"] = str(LOCAL_TESSDATA_DIR)


def get_tesseract_lang():
    if not TESSERACT_AVAILABLE:
        return "eng"
    try:
        if LOCAL_TESSDATA_DIR.exists():
            available = {p.stem for p in LOCAL_TESSDATA_DIR.glob("*.traineddata")}
        else:
            import pytesseract

            available = set(pytesseract.get_languages(config=""))
        if "deu" in available and "eng" in available:
            return "deu+eng"
        if "deu" in available:
            return "deu"
        return "eng"
    except Exception:
        return "eng"


# Grenzen, damit ein einzelnes riesiges oder beschaedigtes PDF den Indexlauf
# nicht faktisch anhaelt. Fuer die Suche sind die ersten Seiten das Wesentliche;
# 200-seitige Kataloge werden bewusst nur teilweise erfasst.
PDF_MAX_PAGES = 60
PDF_MAX_MB = 60

# Gescannte PDFs enthalten nur Bilder: page.extract_text() liefert dann 0 bis 30
# Zeichen und die Datei ist im Volltextindex faktisch leer. Unterhalb dieser
# Schwelle (Zeichen je gelesener Seite) wird auf Texterkennung umgeschaltet.
PDF_OCR_MIN_CHARS_PER_PAGE = 100
# Deutlich kleiner als PDF_MAX_PAGES: Texterkennung kostet Sekunden je Seite,
# 60 Seiten waeren im schlechtesten Fall 20 Minuten fuer eine einzige Datei.
# Fuer die Suche reichen die ersten Seiten (Vertragsart, Namen, Datum).
PDF_OCR_MAX_PAGES = 20
# Harte Obergrenze fuer die gesamte Texterkennung EINER Datei. Das Zeitlimit je
# Seite allein genuegt nicht: viele langsame Seiten summieren sich trotzdem.
PDF_OCR_TOTAL_SECONDS = 180
# Aufloesung fuer das Rendern. 200 dpi ist der uebliche Kompromiss - darunter
# leidet die Erkennungsrate bei kleiner Schrift deutlich.
PDF_OCR_DPI = 200
# Obergrenze fuer die Gesamtflaeche einer gerenderten Seite, damit eine
# ueberformatige Seite nicht den Speicher sprengt.
PDF_OCR_MAX_MEGAPIXEL = 40


def _seite_verkleinern(bild):
    """Begrenzt eine gerenderte PDF-Seite ueber ihre BREITE, nicht ueber die
    laengste Kante. thumbnail() wuerde bei ungewoehnlich hohen Seiten die Breite
    mit herunterziehen: das Xcube-Handbuch (710 x 2129 pt) landete so bei 68 dpi
    und die Texterkennung fand null Zeichen auf einer voll bedruckten Seite."""
    breite, hoehe = bild.size
    faktor = 1.0
    if breite > OCR_MAX_PIXELS:
        faktor = OCR_MAX_PIXELS / breite
    grenze = PDF_OCR_MAX_MEGAPIXEL * 1_000_000
    if breite * hoehe * faktor * faktor > grenze:
        faktor = (grenze / (breite * hoehe)) ** 0.5
    if faktor >= 1.0:
        return bild
    return bild.resize((max(1, int(breite * faktor)), max(1, int(hoehe * faktor))))


def _ocr_pdf_pages(path, lang, max_pages):
    """Rendert die ersten Seiten eines PDFs zu Bildern und schickt sie durch
    Tesseract. Zeitlimit je Seite steckt in run_tesseract, dazu ein Gesamtbudget
    fuer die Datei - sonst blockiert ein einzelner schlechter Scan den Lauf."""
    import pypdfium2 as pdfium

    parts = []
    start = time.time()
    pdf = pdfium.PdfDocument(str(path))
    try:
        for seite in range(min(len(pdf), max_pages)):
            if time.time() - start > PDF_OCR_TOTAL_SECONDS:
                break
            try:
                bitmap = pdf[seite].render(scale=PDF_OCR_DPI / 72)
                bild = _seite_verkleinern(bitmap.to_pil().convert("RGB"))
                parts.append(run_tesseract(bild, lang))
            except Exception:
                # Eine kaputte Seite darf die restlichen nicht verhindern.
                continue
    finally:
        pdf.close()
    return "\n".join(parts)


def extract_pdf(path, lang="deu+eng"):
    try:
        # pypdf meldet jede beschaedigte Datei ueber das logging-Modul ("invalid
        # pdf header", "EOF marker not found"). Bei den 123 bekannten Nullbyte-
        # PDFs sind das hunderte Zeilen pro Lauf ohne jeden Erkenntniswert -
        # der Fehler steht ohnehin im extract_status.
        import logging

        logging.getLogger("pypdf").setLevel(logging.CRITICAL)

        groesse = path.stat().st_size
        if groesse > PDF_MAX_MB * 1024 * 1024:
            return "", "skipped_too_large"

        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = []
        seiten = 0
        for page in reader.pages[:PDF_MAX_PAGES]:
            seiten += 1
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(parts)

        # --- Rueckfall auf Texterkennung bei Scans --------------------------
        if seiten and len(text.strip()) / seiten >= PDF_OCR_MIN_CHARS_PER_PAGE:
            return text, "ok"
        if not TESSERACT_AVAILABLE:
            return text, "ok"
        if groesse > OCR_MAX_MB * 1024 * 1024:
            return text, "ok_ocr_skipped_too_large"

        ocr_text = _ocr_pdf_pages(path, lang, min(PDF_MAX_PAGES, PDF_OCR_MAX_PAGES))
        if len(ocr_text.strip()) > len(text.strip()):
            return ocr_text, "ok_ocr"
        return text, "ok"
    except Exception as e:
        return "", f"error: {type(e).__name__}"


def extract_docx(path):
    try:
        import docx

        d = docx.Document(str(path))
        parts = [p.text for p in d.paragraphs]
        for table in d.tables:
            for row in table.rows:
                for cell in row.cells:
                    parts.append(cell.text)
        return "\n".join(parts), "ok"
    except Exception as e:
        return "", f"error: {e}"


def extract_xlsx(path):
    try:
        import openpyxl

        wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
        parts = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                for val in row:
                    if val is not None:
                        parts.append(str(val))
        return " ".join(parts), "ok"
    except Exception as e:
        return "", f"error: {e}"


def extract_pptx(path):
    try:
        from pptx import Presentation

        prs = Presentation(str(path))
        parts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    parts.append(shape.text_frame.text)
        return "\n".join(parts), "ok"
    except Exception as e:
        return "", f"error: {type(e).__name__}"


def extract_odf(path):
    try:
        from odf import teletype, text
        from odf.opendocument import load

        doc = load(str(path))
        parts = [teletype.extractText(p) for p in doc.getElementsByType(text.P)]
        return "\n".join(parts), "ok"
    except Exception as e:
        return "", f"error: {type(e).__name__}"


def extract_text_file(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore"), "ok"
    except Exception as e:
        return "", f"error: {e}"


def extract_audio_tags(path):
    try:
        import mutagen

        f = mutagen.File(str(path), easy=True)
        if not f:
            return "", "no_tags"
        parts = []
        for key in ("title", "artist", "album", "genre", "date"):
            vals = f.get(key)
            if vals:
                parts.append(f"{key}: {', '.join(vals)}")
        return " | ".join(parts), "ok"
    except Exception as e:
        return "", f"error: {e}"


# Ohne diese Grenzen kann ein einzelnes sehr grosses Bild die Texterkennung
# blockieren und damit den kompletten Indexlauf zum Stillstand bringen.
OCR_MAX_MB = 30
OCR_TIMEOUT_SECONDS = 20
# Handyfotos haben oft 4000px+ Kantenlaenge. Fuer die Texterkennung bringt das
# nichts, kostet aber ein Vielfaches an Rechenzeit - 2000px reichen fuer
# abfotografierte oder gescannte Dokumente aus.
OCR_MAX_PIXELS = 2000
# Sehr kleine Bilder sind Symbole, Strichzeichnungen, Vorschaubilder oder
# Grafikschnipsel - lesbaren Text enthalten sie praktisch nie. Der OCR-Aufruf
# kostet aber trotzdem Sekunden pro Datei, was bei tausenden solcher Dateien
# (z.B. Vorlagensammlungen) Stunden verschlingt.
OCR_MIN_BYTES = 20 * 1024


def run_tesseract(image, lang):
    """Ruft Tesseract als eigenen Prozess auf. Bewusst nicht ueber pytesseract:
    dessen Zeitlimit beendet unter Windows haengende Tesseract-Prozesse nicht
    zuverlaessig, wodurch ein einziges Bild den kompletten Indexlauf blockiert.
    subprocess.run(timeout=...) raeumt den Prozess dagegen sicher ab."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "ocr.png"
        image.save(png)
        proc = subprocess.run(
            [TESSERACT_CMD, str(png), "stdout", "-l", lang],
            capture_output=True,
            timeout=OCR_TIMEOUT_SECONDS,
            env={**os.environ, "TESSDATA_PREFIX": str(LOCAL_TESSDATA_DIR)},
        )
        return proc.stdout.decode("utf-8", errors="replace")


def extract_image_ocr(path, lang):
    if not TESSERACT_AVAILABLE:
        return "", "no_ocr_engine"
    try:
        groesse = path.stat().st_size
        if groesse > OCR_MAX_MB * 1024 * 1024:
            return "", "ocr_skipped_too_large"
        if groesse < OCR_MIN_BYTES:
            return "", "ocr_skipped_too_small"

        from PIL import Image

        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail((OCR_MAX_PIXELS, OCR_MAX_PIXELS))
            text = run_tesseract(img, lang)
        return text, "ok"
    except Exception as e:
        return "", f"error: {type(e).__name__}"


def extract_content(path, ext, lang):
    if ext in PDF_EXTS:
        return extract_pdf(path, lang)
    if ext in DOCX_EXTS:
        return extract_docx(path)
    if ext in XLSX_EXTS:
        return extract_xlsx(path)
    if ext in PPTX_EXTS:
        return extract_pptx(path)
    if ext in ODF_EXTS:
        return extract_odf(path)
    if ext in TEXT_EXTS:
        return extract_text_file(path)
    if ext in AUDIO_EXTS:
        return extract_audio_tags(path)
    if ext in IMAGE_EXTS:
        return extract_image_ocr(path, lang)
    return "", "no_extractor"


def init_db(conn):
    # WAL erlaubt Lesen waehrend geschrieben wird. Ohne das blockiert schon eine
    # einzelne Suchanfrage waehrend eines laufenden Indexlaufs das Schreiben.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS files_meta (
            path TEXT PRIMARY KEY,
            filename TEXT,
            folder TEXT,
            category TEXT,
            ext TEXT,
            size INTEGER,
            mtime REAL,
            indexed_at REAL,
            ocr_used INTEGER,
            extract_status TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
            path UNINDEXED,
            filename,
            category UNINDEXED,
            content,
            tokenize = 'unicode61'
        )
        """
    )
    conn.commit()


# Die Textextraktion (OCR, PDF-Parsing) ist der teure Teil und laeuft daher
# parallel. Reserve lassen, damit der Rechner waehrend eines grossen Laufs
# bedienbar bleibt.
def worker_anzahl():
    kerne = os.cpu_count() or 4
    return max(1, min(12, kerne - 2))


def extrahiere_eine(auftrag):
    """Laeuft im Arbeitsprozess: liest den Inhalt EINER Datei aus.
    Gibt nur einfache Werte zurueck, damit sie sich zwischen Prozessen
    uebertragen lassen."""
    rel_path, ext, lang = auftrag
    path = ROOT / rel_path
    try:
        content, status = extract_content(path, ext, lang)
    except Exception as e:
        content, status = "", f"error: {type(e).__name__}"
    # Bilder laufen immer ueber OCR; bei PDFs nur dann, wenn der Rueckfall
    # tatsaechlich gegriffen hat ("ok_ocr") - sonst stimmt die Statistik nicht.
    ocr_used = 1 if TESSERACT_AVAILABLE and (
        status == "ok_ocr" or (ext in IMAGE_EXTS and status == "ok")
    ) else 0
    return rel_path, content[:MAX_CONTENT_CHARS], status, ocr_used


def upsert_fts(conn, rel_path, filename, category, content):
    conn.execute("DELETE FROM files_fts WHERE path = ?", (rel_path,))
    conn.execute(
        "INSERT INTO files_fts (path, filename, category, content) VALUES (?, ?, ?, ?)",
        (rel_path, filename, category, content[:MAX_CONTENT_CHARS]),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="alle Dateien neu extrahieren")
    parser.add_argument("--verbose", action="store_true", help="jede Datei einzeln ausgeben")
    args = parser.parse_args()

    lang = get_tesseract_lang() if TESSERACT_AVAILABLE else "eng"
    if not TESSERACT_AVAILABLE:
        print("Hinweis: Tesseract OCR ist nicht installiert - Bilder werden nur nach Dateiname indexiert (kein Text aus Scans).")

    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    existing = {}
    for row in conn.execute("SELECT path, size, mtime FROM files_meta"):
        existing[row[0]] = (row[1], row[2])

    seen_paths = set()
    stats = {"new": 0, "updated": 0, "unchanged": 0, "errors": 0, "ocr": 0}
    t0 = time.time()
    todo = []

    for scan_dir in SCAN_DIRS:
        base = ROOT / scan_dir
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_dir():
                continue
            if EXCLUDE_ANY_LEVEL.intersection(path.parts):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue

            rel_path = str(path.relative_to(ROOT))
            seen_paths.add(rel_path)
            ext = path.suffix.lower()
            category = scan_dir
            folder = str(path.parent.relative_to(ROOT))

            prev = existing.get(rel_path)
            unchanged = (
                not args.full
                and prev is not None
                and prev[0] == stat.st_size
                and prev[1] == stat.st_mtime
            )
            if unchanged:
                stats["unchanged"] += 1
                continue

            todo.append((rel_path, path.name, folder, category, ext,
                         stat.st_size, stat.st_mtime, prev is None))

    # --- Textextraktion parallel ---------------------------------------
    n = worker_anzahl()
    if todo:
        print(f"{len(todo)} Dateien einzulesen (auf {n} Kernen parallel) ...", flush=True)

    auftraege = [(t[0], t[4], lang) for t in todo]
    infos = {t[0]: t for t in todo}
    fertig = 0
    schritt = max(100, len(auftraege) // 10)

    def ergebnisse_liefern():
        """Gibt die Ergebnisse einzeln zurueck, sobald sie vorliegen - nicht erst
        wenn alle Dateien durch sind. Bei PDF-Texterkennung dauert eine einzelne
        Datei Minuten; erst am Ende zu schreiben hiesse, dass ein Abbruch den
        gesamten Lauf verwirft."""
        if len(auftraege) <= 4 or n == 1:
            for a in auftraege:
                yield extrahiere_eine(a)
        else:
            with ProcessPoolExecutor(max_workers=n) as pool:
                yield from pool.map(extrahiere_eine, auftraege, chunksize=4)

    # --- Ergebnisse schreiben (nur hier, sonst kollidieren die Prozesse) --
    for rel_path, content, status, ocr_used in ergebnisse_liefern():
            (_, filename, folder, category, ext,
             size, mtime, ist_neu) = infos[rel_path]
            if ocr_used:
                stats["ocr"] += 1
            if status.startswith("error"):
                stats["errors"] += 1

            conn.execute(
                """
                INSERT INTO files_meta (path, filename, folder, category, ext, size, mtime, indexed_at, ocr_used, extract_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    filename=excluded.filename, folder=excluded.folder, category=excluded.category,
                    ext=excluded.ext, size=excluded.size, mtime=excluded.mtime, indexed_at=excluded.indexed_at,
                    ocr_used=excluded.ocr_used, extract_status=excluded.extract_status
                """,
                (
                    rel_path, filename, folder, category, ext,
                    size, mtime, time.time(), ocr_used, status,
                ),
            )
            upsert_fts(conn, rel_path, filename, category, content)

            if ist_neu:
                stats["new"] += 1
            else:
                stats["updated"] += 1

            # Fortschritt in etwa 10 Schritten statt alle 100 Dateien:
            # bei grossen Laeufen sonst hunderte Zeilen ohne Mehrwert.
            fertig += 1
            if fertig % schritt == 0:
                print(f"  ... {fertig}/{len(auftraege)}", flush=True)

            # Regelmaessig sichern: sonst geht bei einem Abbruch mitten im Lauf
            # die gesamte bisherige Arbeit verloren. 25 statt 200, weil eine
            # einzelne PDF-Texterkennung Minuten dauern kann.
            if fertig % 25 == 0:
                conn.commit()

    # Aufraeumen: Dateien, die nicht mehr existieren, aus dem Index entfernen
    removed = 0
    for old_path in list(existing.keys()):
        if old_path not in seen_paths:
            conn.execute("DELETE FROM files_meta WHERE path = ?", (old_path,))
            conn.execute("DELETE FROM files_fts WHERE path = ?", (old_path,))
            removed += 1

    conn.commit()
    conn.close()

    dt = time.time() - t0
    print(
        f"Fertig in {dt:.1f}s | neu: {stats['new']} | aktualisiert: {stats['updated']} | "
        f"unveraendert: {stats['unchanged']} | entfernt: {removed} | OCR: {stats['ocr']} | Fehler: {stats['errors']}"
    )


if __name__ == "__main__":
    sys.exit(main())
