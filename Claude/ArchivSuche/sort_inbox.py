"""
Sortiert Dateien aus dem Posteingang-Ordner automatisch in die Archiv-Struktur ein.

Erkennung:
  - Bilder/Videos/Musik anhand der Dateiendung
  - bei Bildern zusaetzlich OCR-Check: sieht es wie ein Dokument (Rechnung, Anleitung, ...)
    aus, wird es wie ein Dokument einsortiert statt nach Bilder/
  - Dokumente (PDF/Word/Excel/Text) anhand von Schluesselwoertern in Dateiname + Inhalt

Dateien, die sich nicht sicher zuordnen lassen, bleiben unangetastet im Posteingang
liegen und werden am Ende als Liste ausgegeben (manuelle / KI-gestuetzte Einordnung).

Aufruf:
    python sort_inbox.py
"""

import hashlib
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import index as ix

# Dateinamen enthalten Sonderzeichen wie "Ω" - ohne UTF-8 bricht die Ausgabe auf
# der Windows-Konsole (cp1252) mitten im Lauf ab.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

INBOX = ix.ROOT / "Posteingang"
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v", ".mpg", ".mpeg", ".flv", ".webm", ".3gp"}
# Projektdateien von Musikproduktions-Software gehoeren zum Sound-Geschaeft.
MUSIKPROJEKT_EXTS = {".als", ".flp", ".alp", ".ptx", ".cpr", ".logicx", ".band"}

# Feste Dateinamen-Masken. Sie haben Vorrang vor der inhaltlichen Bewertung:
# wer eine Datei bewusst "Rechnung_..." nennt, hat die Ablage schon entschieden.
PREFIX_RULES = [
    ("rechnung", "Dokumente/Gewerblich/Rechnungen"),
    ("angebot", "Dokumente/Gewerblich/Angebote"),
    ("kostenvoranschlag", "Dokumente/Gewerblich/Angebote"),
]

# Vorsilben, die dem eigentlichen Namen vorangestellt sind und beim Pruefen
# der Maske ignoriert werden ("Kopie von Rechnung_2020.pdf" ist eine Rechnung).
NAME_VORSILBEN = ["kopie von ", "copy of ", "kopie - ", "(kopie) "]

# Ordneruebernahme: Wird ein ganzer, bereits sinnvoll benannter Ordner in den
# Posteingang gezogen, sagt sein Name schon, wohin er gehoert. Die gewachsene
# Unterstruktur ("Uni KL/GLET I/Uebungen") ist dabei wertvoll und bleibt
# erhalten - sie einzeln nach Inhalt zu bewerten wuerde sie zerstoeren.
# Schluessel = Ordnername im Posteingang (klein), Wert = Zielordner.
ORDNER_REGELN = {
    "studium": "Dokumente/Privat/Studium",
    "uni": "Dokumente/Privat/Studium",
    "hochschule": "Dokumente/Privat/Studium",
    "maks": "Dokumente/Gewerblich/Maks Sound",
    "maks sound": "Dokumente/Gewerblich/Maks Sound",
    "verleih von licht, ton- und lasertechnik": "Dokumente/Gewerblich/Maks Sound",
    "akai mpk mini mk2": "Dokumente/Gewerblich/Maks Sound",
    "tattoos": "Dokumente/Privat/Tattoos",
    "tattoo": "Dokumente/Privat/Tattoos",
    "manuals": "Dokumente/Privat/Bedienungsanleitungen",
    "handbuecher": "Dokumente/Privat/Bedienungsanleitungen",
    "handbücher": "Dokumente/Privat/Bedienungsanleitungen",
    "bedienungsanleitungen": "Dokumente/Privat/Bedienungsanleitungen",
    "rezepte": "Dokumente/Privat/Rezepte",
    "bewerbung": "Dokumente/Privat/Bewerbung",
    "gesundheit": "Dokumente/Privat/Gesundheit",
}


def ordner_ziel(rel_pfad_im_posteingang):
    """Prueft, ob die Datei in einem Ordner liegt, dessen Name die Kategorie
    schon verraet. Gibt (Zielordner, Restpfad) zurueck - der Restpfad erhaelt
    die Unterstruktur unterhalb des erkannten Ordners.

    Geprueft wird nur die OBERSTE Ebene im Posteingang: ein Unterordner
    "Bilder" innerhalb von "MAKS" soll bei Maks Sound bleiben und nicht
    ploetzlich nach Bilder/ wandern.
    """
    teile = Path(rel_pfad_im_posteingang).parts
    if len(teile) < 2:
        return None, None
    ziel = ORDNER_REGELN.get(teile[0].lower().strip())
    if not ziel:
        return None, None
    return ziel, str(Path(*teile[1:]))

# Reihenfolge = Prioritaet. Erste passende Regel gewinnt.
DOC_RULES = [
    ("Dokumente/Gewerblich/Maks Sound", [
        "maks sound", "maks-sound", "maksound",
        "lautsprecher", "loudspeaker", "subwoofer", "woofer", "tweeter", "kompressionstreiber",
        "frequenzgang", "frequency response", "schalldruck", "impedanz", "impedance",
        "endstufe", "verstaerker", "verstärker", "amplifier", "mischpult", "mixing console",
        "beschallung", "pa-anlage", "line array", "monitorbox", "buehnentechnik", "bühnentechnik",
        "dmx", "lichtpult", "moving head", "traverse", "truss", "rigging",
    ]),
    ("Dokumente/Privat/Ausbildung Tischler", [
        "tischler", "schreiner", "berufsschule", "ausbildung", "ausbildungsvertrag",
        "ausbildungsnachweis", "lehrjahr", "gesellenpruefung", "gesellenprüfung",
        "gesellenstueck", "gesellenstück", "holzbearbeitung", "furnier",
        "holzart", "holzarten", "holzwerkstoff", "schwalbenschwanz", "zinken",
        "handlungsfeld", "lernfeld", "meisterpruefung", "meisterprüfung",
        "meisterschule", "technisches zeichnen", "berichtsheft",
    ]),
    # "praxis" bewusst NICHT aufgenommen: kommt in Fachtexten/Studienunterlagen
    # staendig vor ("in der Praxis zeigt sich ...") und erzeugt Fehltreffer.
    ("Dokumente/Privat/Gesundheit", ["arzt", "aerztlich", "ärztlich", "apotheke", "diagnose", "medikament", "krankenkasse", "krankenversicherung", "attest", "impfung", "befund", "verschreibung", "physiotherapie", "arztpraxis", "klinik"]),
    ("Dokumente/Privat/Bewerbung", [
        "bewerbung", "lebenslauf", "anschreiben", "stellenanzeige", "stellenangebot",
        "stellenausschreibung", "arbeitszeugnis", "praktikumszeugnis", "wir suchen",
        "ihre aufgaben", "ihr profil", "vorarbeiter",
    ]),
    ("Dokumente/Privat/Studium", [
        "immatrikulation", "studienbescheinigung", "klausur", "pruefungsordnung", "prüfungsordnung",
        "vorlesung", "seminar", "hochschule", "universitaet", "universität", "fachhochschule",
        "modulhandbuch", "studiengang", "semester", "hausarbeit", "bachelorarbeit", "masterarbeit",
        "abstract", "literaturverzeichnis", "studienleistung", "leistungsnachweis", "campus",
        "praesenzklausur", "präsenzklausur", "abschlussklausur", "klausurtermin",
        "studienbescheinigung", "immatrikulationsbescheinigung",
        "zoologie", "botanik", "biochemie", "wirtschaftslehre", "pruefungsanmeldung",
        "prüfungsanmeldung", "sose", "wise", "uebungsblatt", "übungsblatt",
    ]),
    ("Dokumente/Privat/Rezepte", ["zutaten", "zubereitung", "backofen", "rezept fuer", "rezept für", "rezept:", "kochen", "esslöffel", "teelöffel"]),
    ("Dokumente/Privat/Wohnen", ["miete", "mietvertrag", "nebenkosten", "hausordnung", "vermieter", "wohnungsgeberbestaetigung", "wohnungsgeberbestätigung", "betriebskostenabrechnung", "kaution"]),
    ("Dokumente/Privat/Fahrzeug-KFZ", ["kfz", "fahrzeugschein", "zulassungsbescheinigung", "tuev", "tüv", "fuehrerschein", "führerschein", "kfz-versicherung", "werkstattrechnung", "hauptuntersuchung"]),
    ("Dokumente/Privat/Finanzen und Versicherungen", [
        "kontoauszug", "versicherungspolice", "police nr", "steuerbescheid", "finanzamt",
        "gehaltsabrechnung", "lohnabrechnung", "lohnsteuerbescheinigung", "einkommensteuer",
        "steuererklaerung", "steuererklärung", "steuerberechnung", "steuernummer",
        "haftpflicht", "hausratversicherung", "rentenversicherung", "bafoeg", "bafög",
        "darlehen", "kapitalertraege", "kapitalerträge", "freistellungsauftrag",
    ]),
    # "antrag"/"bescheid" allein sind zu unspezifisch (stehen in Merkblaettern,
    # Formularvorlagen und Verfahrensbeschreibungen).
    ("Dokumente/Privat/Behoerden und Ausweise", ["personalausweis", "reisepass", "zeugnis", "meldebescheinigung", "geburtsurkunde", "einwohnermeldeamt", "immatrikulation", "hochschulreife"]),
    ("Dokumente/Gewerblich/Rechnungen", ["rechnung", "rechnungsnummer", "invoice", "quittung", "beleg"]),
    ("Dokumente/Gewerblich/Angebote", ["angebot", "kostenvoranschlag", "quotation"]),
    ("Dokumente/Privat/Vertraege", ["vertrag", "kuendigung", "kündigung", "agb", "vertragsbedingungen"]),
    ("Dokumente/Privat/Bedienungsanleitungen", [
        "bedienungsanleitung", "anleitung", "manual", "handbuch", "gebrauchsanweisung",
        "user guide", "quick start", "installationsanleitung", "montageanleitung", "datenblatt", "datasheet",
        "setup guide", "bedienhandbuch", "kurzanleitung", "owner's manual", "reference manual",
    ]),
    # "gmbh" bewusst NICHT aufgenommen: steht im Impressum praktisch jedes
    # deutschen Dokuments (auch in Handbuechern und Lageplaenen).
    ("Dokumente/Gewerblich/Sonstige Dokumente", ["ust-idnr", "handelsregister", "auftragsbestaetigung", "auftragsbestätigung", "geschaeftsbedingungen", "gewerbeanmeldung", "soforthilfe"]),
]

DOCUMENT_EXTS = ix.TEXT_EXTS | ix.PDF_EXTS | ix.DOCX_EXTS | ix.XLSX_EXTS | ix.PPTX_EXTS | ix.ODF_EXTS

# Software-, Treiber- und Systemdateien gehoeren nicht ins Dokumentenarchiv und
# werden bewusst NICHT angefasst.
SKIP_EXTS = {
    ".exe", ".dll", ".sys", ".inf", ".cat", ".msi", ".msix", ".msixbundle",
    ".dmg", ".app", ".pkg", ".nib", ".plist", ".icns", ".ico", ".bin", ".cmd",
    ".bat", ".ps1", ".lnk", ".db", ".ini", ".cfg", ".mmip", ".auz", ".vst3",
    ".component", ".dylib", ".so", ".zip", ".rar", ".7z", ".iso",
    # Python-/PyInstaller-Zwischenprodukte: entstehen beim Bauen neu und haben
    # als Archivinhalt keinen Wert (.spec bleibt bewusst draussen - die Datei
    # wird oft von Hand angepasst und gehoert zum Quellcode).
    ".pyc", ".pyo", ".pyd", ".toc", ".pyz",
}

# Alte Office-Formate: Inhalt laesst sich ohne Zusatzbibliothek nicht auslesen,
# ueber den Dateinamen sind sie aber sehr wohl zuzuordnen.
NUR_NAME_EXTS = {".xls", ".doc", ".ppt", ".rtf", ".pages", ".numbers", ".key"}

# Von Office/LibreOffice angelegte Sperr- und Sicherungsdateien - kein Inhalt,
# nur Restmuell eines geoeffneten Dokuments.
TEMP_NAME_MUSTER = ["~$", ".~lock", ".tmp", "thumbs.db", "desktop.ini"]

# Dateien mit potenziell hochsensiblem Inhalt: nie automatisch verschieben.
SENSITIVE_NAME_PATTERNS = ["passw", "password", "kennwort", "credential", "secret", "private key", "privatekey"]


def ist_temp_datei(name):
    low = name.lower()
    return any(low.startswith(m) or low == m or low.endswith(m) for m in TEMP_NAME_MUSTER)


# Pfadbestandteile, die auf Software-Innereien hinweisen: entpackte Installer,
# macOS-App-Buendel, Programm-Zwischenspeicher. Solche Dateien haben im
# Dokumentenarchiv nichts zu suchen - auch dann nicht, wenn der uebergeordnete
# Ordner ("MAKS", "Handbuecher") an sich richtig zugeordnet waere.
SKIP_PFAD_MUSTER = [
    ".app/", ".app\\",           # macOS-Programmbuendel
    "installer_assets",          # entpackte Installationsdateien
    "/.splice", "\\.splice",     # Splice-Zwischenspeicher
    "/__macosx", "\\__macosx",
    "/node_modules", "\\node_modules",
    "/appdata/", "\\appdata\\",
    "/__pycache__", "\\__pycache__",
    "/build/", "\\build\\",      # PyInstaller-Zwischenstand
    "/dist/", "\\dist\\",        # fertige Programmpakete
    ".egg-info", ".venv/", ".venv\\",
]


def ist_software_pfad(rel_pfad):
    low = str(rel_pfad).lower().replace("\\", "/")
    return any(m.replace("\\", "/") in low for m in SKIP_PFAD_MUSTER)

# Fuer die Klassifizierung reichen die ersten Seiten - das haelt den Lauf schnell
# und verhindert Haenger bei sehr grossen oder beschaedigten PDFs.
PDF_CLASSIFY_PAGES = 4

# Zu generische Woerter, die trotz Laenge NICHT als automatisches Ordner-Schluesselwort
# taugen (zu hohe Fehlalarmquote in beliebigem Fliesstext).
GENERIC_WORD_STOPLIST = {
    "neuer", "neue", "neues", "ordner", "sonstige", "sonstiges", "dokument",
    "dokumente", "allgemein", "allgemeine", "privat", "gewerblich", "eingang",
    "unterlagen", "sonstiger", "diverses", "verschiedenes", "archiv", "ablage",
}


def discover_dynamic_rules():
    """Neu angelegte Unterordner unter Dokumente/ werden automatisch als
    Sortierziel erkannt: der Ordnername (und laengere, nicht-generische Woerter
    darin) dient als Schluesselwort. Greift nur, wenn kein festes Rezept oben
    zutrifft."""
    known_dests = {dest for dest, _ in DOC_RULES}
    dynamic = []
    for base in ("Dokumente/Gewerblich", "Dokumente/Privat"):
        base_path = ix.ROOT / base
        if not base_path.exists():
            continue
        # Nur direkte Unterordner: tiefer liegende Ordner sind meist Inhalt
        # (z.B. entpackte Software), keine eigenstaendige Ablage-Kategorie.
        for p in sorted(base_path.iterdir()):
            if not p.is_dir():
                continue
            rel = str(p.relative_to(ix.ROOT)).replace("\\", "/")
            if rel in known_dests:
                continue
            name_lower = p.name.lower()
            keywords = set()
            if len(name_lower) >= 5 and name_lower not in GENERIC_WORD_STOPLIST:
                keywords.add(name_lower)
            keywords.update(
                w for w in (word.lower() for word in p.name.split())
                if len(w) >= 5 and w not in GENERIC_WORD_STOPLIST
            )
            if keywords:
                dynamic.append((rel, sorted(keywords)))
    return dynamic


# Nur der Anfang des Inhalts wird fuer die Klassifizierung durchsucht: Rechnungen,
# Vertraege, Anleitungen etc. nennen ihren eigenen Typ typischerweise auf der ersten
# Seite/im Kopf. Bei langen Dokumenten (z.B. 100-seitige Handbuecher mit Lizenztext)
# verhindert das Fehltreffer durch beilaeufig erwaehnte Begriffe tief im Dokument.
CONTENT_SEARCH_CHARS = 4000


# Ab wieviel extrahiertem Text ein PDF als "hat echte Textebene" gilt. Darunter
# ist es praktisch sicher ein Scan und nur per OCR lesbar.
PDF_TEXT_MIN_CHARS = 120
OCR_PDF_PAGES = 1
# Harte Grenzen, damit ein einzelnes riesiges oder kaputtes PDF den Lauf nicht
# blockiert: sehr grosse Dateien werden gar nicht erst per OCR gelesen, und
# Tesseract wird nach einer festen Zeit abgebrochen.
OCR_PDF_MAX_MB = 25
OCR_TIMEOUT_SECONDS = 25
OCR_RENDER_SCALE = 1.5


def ocr_pdf_first_pages(path, lang):
    """Rendert die erste Seite eines gescannten PDFs und liest sie per OCR."""
    try:
        if path.stat().st_size > OCR_PDF_MAX_MB * 1024 * 1024:
            return "", "ocr_skipped_too_large"

        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(path))
        parts = []
        try:
            for i in range(min(OCR_PDF_PAGES, len(pdf))):
                bitmap = pdf[i].render(scale=OCR_RENDER_SCALE)
                img = bitmap.to_pil()
                img.thumbnail((ix.OCR_MAX_PIXELS, ix.OCR_MAX_PIXELS))
                # ix.run_tesseract statt pytesseract: dessen Zeitlimit beendet
                # haengende Tesseract-Prozesse unter Windows nicht zuverlaessig.
                parts.append(ix.run_tesseract(img, lang))
        finally:
            pdf.close()
        return "\n".join(parts), "ocr"
    except Exception as e:
        return "", f"ocr_error: {type(e).__name__}"


def extract_for_classification(path, ext, lang):
    """Wie ix.extract_content, aber bei PDFs nur die ersten Seiten - schnell und
    robust gegen sehr grosse oder beschaedigte Dateien. Liefert ein PDF keinen
    verwertbaren Text (Scan), wird auf OCR zurueckgefallen."""
    if ext not in ix.PDF_EXTS:
        return ix.extract_content(path, ext, lang)
    text = ""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages[:PDF_CLASSIFY_PAGES]:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(parts)
    except Exception as e:
        text = ""

    if len(text.strip()) >= PDF_TEXT_MIN_CHARS or not ix.TESSERACT_AVAILABLE:
        return text, "ok"
    return ocr_pdf_first_pages(path, lang)


def _count_matches(keyword, haystack):
    return len(re.findall(r"(?<![a-z0-9äöüß])" + re.escape(keyword) + r"(?![a-z0-9äöüß])", haystack))


# Ein Treffer im Dateinamen wiegt schwerer als einer im Fliesstext: der Dateiname
# beschreibt meist wirklich das Dokument, waehrend ein Wort im Text auch beilaeufig
# erwaehnt sein kann.
NAME_WEIGHT = 10
CONTENT_FIRST_HIT = 3
CONTENT_REPEAT_HIT = 1
MAX_CONTENT_SCORE_PER_KEYWORD = 8
# Ein einzelner Treffer irgendwo im Fliesstext (=3) reicht bewusst NICHT aus:
# eine Stellenanzeige, die "Fuehrerschein" als Anforderung nennt, ist kein
# KFZ-Dokument. Noetig ist ein Treffer im Dateinamen oder mehrere Signale.
MIN_SCORE = 6


def classify_by_prefix(filename):
    """Prueft die festen Dateinamen-Masken.

    Bewusst nicht auf 'Rechnung_' festgenagelt: in der Praxis heissen die
    Dateien 'Rechnung20190801.pdf', 'Rechnung2020.02.1.pdf' oder
    'Kopie von Rechnung_Mueller.xls'. Nach der Maske muss lediglich ein
    Nicht-Buchstabe folgen (Ziffer, Unterstrich, Punkt, Leerzeichen) oder
    der Name zu Ende sein - so wird 'Rechnungswesen.pdf' (ein Fachthema,
    keine Rechnung) korrekt NICHT erfasst.
    """
    stamm = Path(filename).stem.strip()
    low = stamm.lower()
    for vorsilbe in NAME_VORSILBEN:
        if low.startswith(vorsilbe):
            schnitt = len(vorsilbe)
            stamm, low = stamm[schnitt:].lstrip(), low[schnitt:].lstrip()

    for prefix, dest in PREFIX_RULES:
        if not low.startswith(prefix):
            continue
        rest = stamm[len(prefix):]
        # Wortgrenze: Ende des Namens, ein Nicht-Buchstabe (Ziffer, Unterstrich,
        # Punkt, Leerzeichen) - oder ein Grossbuchstabe, denn in
        # zusammengeschriebenen Namen wie "RechnungAnugaFaupel" markiert der
        # die naechste Wortgrenze. So bleibt "Rechnungswesen" (klein
        # weitergeschrieben, also ein eigenes Wort) korrekt aussen vor.
        if rest == "" or not rest[0].isalpha() or rest[0].isupper():
            return dest, f"Dateiname beginnt mit '{prefix}'"
    return None, None


def classify_text(filename, content, rules):
    """Bewertet alle Kategorien und waehlt die mit der hoechsten Punktzahl, statt
    beim ersten Treffer stehenzubleiben. So gewinnt bei einer Rechnung, die eine
    Bedienungsanleitung erwaehnt, trotzdem die Kategorie mit den meisten Signalen."""
    name_low = (
        filename.lower()
        .replace("_", " ").replace("-", " ")
        .replace("\\", " ").replace("/", " ")
    )
    content_low = content[:CONTENT_SEARCH_CHARS].lower()

    scored = []
    for dest, keywords in rules:
        score = 0
        hits = []
        for kw in keywords:
            n_name = _count_matches(kw, name_low)
            if n_name:
                score += NAME_WEIGHT
                hits.append(f"Dateiname '{kw}'")
            n_content = _count_matches(kw, content_low)
            if n_content:
                score += min(
                    CONTENT_FIRST_HIT + (n_content - 1) * CONTENT_REPEAT_HIT,
                    MAX_CONTENT_SCORE_PER_KEYWORD,
                )
                hits.append(f"Inhalt '{kw}'x{n_content}")
        if score:
            scored.append((score, dest, hits))

    if not scored:
        return None, None, 0

    scored.sort(key=lambda t: -t[0])
    best_score, best_dest, best_hits = scored[0]
    if best_score < MIN_SCORE:
        return None, None, best_score
    return best_dest, ", ".join(best_hits[:3]), best_score


def _sha1(path, chunk=1024 * 1024):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while c := f.read(chunk):
            h.update(c)
    return h.hexdigest()


def inhaltsgleich(a, b):
    """Erst Groesse (billig), dann Hash. Gleicher Dateiname allein sagt nichts:
    identische Namen mit voellig verschiedenem Inhalt sind haeufig (Rechnung.pdf,
    Handbuch.pdf, IMG_1234.jpg). Bei Lesefehlern bewusst False - im Zweifel wird
    nichts geloescht."""
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
        return _sha1(a) == _sha1(b)
    except OSError:
        return False


def freier_name(ziel):
    """'bericht.pdf' -> 'bericht (2).pdf', falls schon belegt."""
    if not ziel.exists():
        return ziel
    n = 2
    while True:
        kandidat = ziel.with_name(f"{ziel.stem} ({n}){ziel.suffix}")
        if not kandidat.exists():
            return kandidat
        n += 1


def move(path, dest_rel, unterpfad=None):
    """Verschiebt eine Datei ins Archiv. Liegt dort bereits eine Datei gleichen
    Namens, entscheidet der INHALT (Groesse + SHA1), nicht das Aenderungsdatum:

      - inhaltsgleich  -> Posteingang-Kopie wird geloescht, Archivdatei bleibt
      - Inhalt weicht ab -> nichts wird geloescht, Ablage als "(2)"

    unterpfad erhaelt bei der Ordneruebernahme die gewachsene Struktur
    (z.B. "Uni KL/GLET I/Uebungen/blatt1.pdf").

    Rueckgabe: (Zielpfad relativ zur Wurzel, Hinweis oder None, Art)
    Art ist "dedup", "variante" oder None.
    """
    if unterpfad:
        ziel = ix.ROOT / dest_rel / unterpfad
        ziel.parent.mkdir(parents=True, exist_ok=True)
    else:
        dest_dir = ix.ROOT / dest_rel
        dest_dir.mkdir(parents=True, exist_ok=True)
        ziel = dest_dir / path.name

    if ziel.exists():
        if inhaltsgleich(path, ziel):
            path.unlink()
            return ziel.relative_to(ix.ROOT), "Duplikat geloescht (inhaltsgleich)", "dedup"
        # Gleicher Name, anderer Inhalt: nichts loeschen, beide behalten.
        ziel = freier_name(ziel)
        shutil.move(str(path), str(ziel))
        return (ziel.relative_to(ix.ROOT),
                f"abweichender Inhalt - als '{ziel.name}' abgelegt", "variante")

    shutil.move(str(path), str(ziel))
    return ziel.relative_to(ix.ROOT), None, None


# Zertifikate, Schluessel und Passwort-Tresore. Der Dateiname verraet hier
# nichts (ein ELSTER-Zertifikat heisst schlicht "Ann21_elster_....pfx"), also
# entscheidet die Endung. Solche Dateien werden nie automatisch verschoben -
# sie werden gemeldet und bleiben liegen.
SENSITIVE_EXTS = {
    ".pfx", ".p12", ".pem", ".key", ".jks", ".keystore", ".crt", ".cer",
    ".kdbx", ".kdb", ".asc", ".gpg", ".ppk", ".ovpn",
}


def is_sensitive(filename):
    low = filename.lower()
    if Path(low).suffix in SENSITIVE_EXTS:
        return True
    return any(pat in low for pat in SENSITIVE_NAME_PATTERNS)


ICON_EXTS      = {".ico", ".icns", ".cur", ".ani"}
ICON_ZIEL      = "Software/Windows/Icon"
# 64 KB empirisch ermittelt: faengt 1151 von 1152 bekannten Icons, ohne einen
# einzigen zusaetzlichen Fehltreffer bei den 2927 echten Bildern im Archiv.
ICON_MAX_BYTES = 64 * 1024
ICON_MAX_KANTE = 512


def _png_masse(path):
    """Breite/Hoehe direkt aus dem PNG-Header (IHDR), ohne Bildbibliothek."""
    try:
        with open(path, "rb") as f:
            kopf = f.read(24)
    except OSError:
        return None
    if len(kopf) < 24 or kopf[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(kopf[16:20], "big"), int.from_bytes(kopf[20:24], "big")


def _svg_masse(path):
    """Breite/Hoehe aus dem <svg>-Tag - erst width/height, sonst viewBox."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            kopf = f.read(2048)
    except OSError:
        return None
    tag = re.search(r"<svg\b[^>]*>", kopf, re.S | re.I)
    if not tag:
        return None
    tag = tag.group(0)
    # Inkscape schreibt einfache Anfuehrungszeichen, andere Werkzeuge doppelte.
    b = re.search(r"""\bwidth\s*=\s*["']\s*([\d.]+)""", tag)
    h = re.search(r"""\bheight\s*=\s*["']\s*([\d.]+)""", tag)
    if b and h:
        return float(b.group(1)), float(h.group(1))
    vb = re.search(
        r"""\bviewBox\s*=\s*["']\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)""", tag)
    if vb:
        return float(vb.group(1)), float(vb.group(2))
    return None


def ist_icon(path):
    """Icon-/UI-Grafik statt Foto?

    .ico & Co. sind eindeutig. Bei PNG/SVG reicht die Dateigroesse allein NICHT -
    ein kleines echtes Foto waere sonst betroffen. Deshalb zusaetzlich die
    Bildmasse: quadratisch und hoechstens 512px ist praktisch immer ein Icon.
    Hintergrund: Icon-Sets bringen hunderte gleichnamige Dateien mit
    (agenda.png, document-save-symbolic.svg ...), die sonst in Bilder/ landen.
    """
    ext = path.suffix.lower()
    if ext in ICON_EXTS:
        return True
    if ext not in (".png", ".svg"):
        return False
    try:
        if path.stat().st_size > ICON_MAX_BYTES:
            return False
    except OSError:
        return False
    masse = _png_masse(path) if ext == ".png" else _svg_masse(path)
    if not masse:
        return False
    breite, hoehe = masse
    if breite <= 0 or hoehe <= 0:
        return False
    # Nicht auf exakte Gleichheit pruefen: SVG-Werkzeuge schreiben 16.000002
    # statt 16, und manche Icons sind minimal unsymmetrisch.
    if abs(breite - hoehe) > max(1.0, 0.02 * max(breite, hoehe)):
        return False
    return max(breite, hoehe) <= ICON_MAX_KANTE


def entscheide_eine(auftrag):
    """Laeuft im Arbeitsprozess: entscheidet fuer EINE Datei, wohin sie soll -
    ohne sie zu verschieben (das bleibt dem Hauptprozess vorbehalten, damit
    sich parallele Prozesse nicht gegenseitig beim Verschieben in die Quere
    kommen). Gibt nur einfache Werte zurueck (Prozessgrenze)."""
    rel, lang, rules = auftrag
    path = ix.ROOT / rel
    ext = path.suffix.lower()

    if ext in SKIP_EXTS:
        return rel, "skip", None, "Software-/Systemdatei", ""

    if ist_software_pfad(rel):
        return rel, "skip", None, "Software-Innereien (Installer/App-Buendel)", ""

    if ist_temp_datei(path.name):
        return rel, "skip", None, "Sperr-/Sicherungsdatei von Office (kein Inhalt)", ""

    if is_sensitive(path.name):
        return rel, "skip", None, "moeglicherweise sensibel (Passwoerter/Zugangsdaten)", ""

    # Ordneruebernahme vor allem anderen: liegt die Datei in einem Ordner,
    # dessen Name die Kategorie schon verraet, zaehlt das mehr als jeder
    # Inhaltstreffer - und die Unterstruktur bleibt erhalten.
    rel_in_inbox = str(path.relative_to(INBOX)) if INBOX in path.parents else path.name
    o_ziel, o_unterpfad = ordner_ziel(rel_in_inbox)
    if o_ziel:
        return rel, "move_tree", o_ziel, f"aus Ordner '{Path(rel_in_inbox).parts[0]}'", o_unterpfad

    prefix_dest, prefix_grund = classify_by_prefix(path.name)
    if prefix_dest:
        return rel, "move", prefix_dest, prefix_grund, ""

    if ext in NUR_NAME_EXTS:
        # Altes Office-Format: Inhalt nicht lesbar, also nur ueber den Namen
        # (inklusive Unterordner-Pfad, der oft die Kategorie verraet).
        rel_in_inbox = str(path.relative_to(INBOX)) if INBOX in path.parents else path.name
        dest, rule, score = classify_text(rel_in_inbox, "", rules)
        if dest:
            return rel, "move", dest, f"[{score}] nur Dateiname/Pfad: {rule}", ""
        return rel, "unsorted", None, f"altes Office-Format, Name ohne Signal (Punktzahl {score})", ""

    if ist_icon(path):
        return rel, "move", ICON_ZIEL, "Icon-/UI-Grafik (kein Foto)", ""

    if ext in ix.IMAGE_EXTS:
        content, _ = ix.extract_image_ocr(path, lang) if ix.TESSERACT_AVAILABLE else ("", "no_ocr_engine")
        dest, rule, score = classify_text(path.name, content, rules)
        if dest:
            return rel, "move", dest, f"Bild als Dokument erkannt [{score}]: {rule}", ""
        return rel, "move", "Bilder", "Bild", ""

    if ext in VIDEO_EXTS:
        return rel, "move", "Videos", "Video", ""

    if ext in MUSIKPROJEKT_EXTS:
        return rel, "move", "Dokumente/Gewerblich/Maks Sound", f"Musikprojekt ({ext})", ""

    if ext in ix.AUDIO_EXTS:
        if "maks" in path.name.lower():
            return rel, "move", "Dokumente/Gewerblich/Maks Sound", "Audio, Maks Sound", ""
        return rel, "move", "Musik", "Musik", ""

    if ext in DOCUMENT_EXTS:
        content, _ = extract_for_classification(path, ext, lang)
        # Auch der Pfad innerhalb des Posteingangs zaehlt: liegt eine Datei in
        # einem Unterordner "Rechnungen", ist das ein starkes Signal.
        rel_in_inbox = str(path.relative_to(INBOX)) if INBOX in path.parents else path.name
        dest, rule, score = classify_text(rel_in_inbox, content, rules)
        if dest:
            return rel, "move", dest, f"[{score}] {rule}", ""
        preview = " ".join(content.split())[:150]
        return rel, "unsorted", None, f"kein klares Signal (max. Punktzahl {score})", preview

    return rel, "unsorted", None, "unbekannter Dateityp", ""


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="nur anzeigen, was passieren wuerde - nichts verschieben")
    parser.add_argument("--verbose", action="store_true", help="jede Datei waehrend der Pruefung ausgeben")
    parser.add_argument("--details", action="store_true",
                        help="im Bericht jede Datei einzeln auflisten (Standard: nur Zahlen)")
    args = parser.parse_args()

    if not INBOX.exists():
        print("Posteingang-Ordner existiert nicht.")
        return 1

    dry = args.dry_run
    moved = []
    unsorted = []
    skipped = []
    dedup = []
    varianten = []
    lang = ix.get_tesseract_lang()
    rules = DOC_RULES + discover_dynamic_rules()

    def plan(path, dest_rel, reason, unterpfad=None):
        if dry:
            ziel = ix.ROOT / dest_rel / (unterpfad or path.name)
            if ziel.exists():
                if inhaltsgleich(path, ziel):
                    dedup.append((path.name, dest_rel, "wuerde geloescht (inhaltsgleich)"))
                else:
                    varianten.append((path.name, dest_rel,
                                      f"wuerde als '{freier_name(ziel).name}' abgelegt"))
                return
            moved.append((path.name, dest_rel + "/" + (unterpfad or path.name), reason))
            return
        try:
            ziel, hinweis, art = move(path, dest_rel, unterpfad)
            if art == "dedup":
                dedup.append((path.name, dest_rel, hinweis))
            elif art == "variante":
                varianten.append((path.name, dest_rel, hinweis))
            else:
                moved.append((path.name, str(ziel), reason))
        except PermissionError:
            # Datei ist gerade in einem anderen Programm geoeffnet - ueberspringen,
            # damit ein einzelner offener Excel-Tab nicht den ganzen Lauf abbricht.
            skipped.append((str(path.relative_to(ix.ROOT)), "gesperrt (in anderem Programm geoeffnet)"))
        except OSError as e:
            skipped.append((str(path.relative_to(ix.ROOT)), f"Verschieben fehlgeschlagen ({type(e).__name__})"))

    # _zu_loeschen/ ist die Quarantaene aus Wissen/Schutzregeln.md: dort legt ein
    # Agent ab, was er loeschen wuerde, statt es zu loeschen. Wuerde die Sortierung
    # den Ordner mitnehmen, landete genau das Fragliche wieder unbemerkt im Archiv.
    files = [
        p for p in sorted(INBOX.rglob("*"))
        if p.is_file() and "_zu_loeschen" not in p.relative_to(INBOX).parts
    ]
    total = len(files)

    # --- Klassifizierung parallel ---------------------------------------
    # Der teure Teil (OCR, PDF-Text) laeuft auf mehreren Kernen; verschoben
    # wird anschliessend zentral, damit sich die Prozesse nicht in die Quere
    # kommen.
    n = ix.worker_anzahl()
    if total > 4 and n > 1:
        print(f"{total} Dateien pruefen (auf {n} Kernen parallel) ...", flush=True)
        auftraege = [(str(p.relative_to(ix.ROOT)), lang, rules) for p in files]
        entscheidungen = []
        schritt = max(100, total // 10)
        with ProcessPoolExecutor(max_workers=n) as pool:
            for e in pool.map(entscheide_eine, auftraege, chunksize=4):
                entscheidungen.append(e)
                if len(entscheidungen) % schritt == 0:
                    print(f"  ... {len(entscheidungen)}/{total}", flush=True)
    else:
        entscheidungen = [entscheide_eine((str(p.relative_to(ix.ROOT)), lang, rules)) for p in files]

    # --- Ergebnisse umsetzen --------------------------------------------
    for rel, art, ziel, grund, vorschau in entscheidungen:
        path = ix.ROOT / rel
        if art == "skip":
            skipped.append((rel, grund))
        elif art == "unsorted":
            unsorted.append((rel, grund, vorschau))
        elif art == "move_tree":
            # Bei der Ordneruebernahme steht im letzten Feld der Unterpfad,
            # der die gewachsene Struktur erhaelt.
            plan(path, ziel, grund, vorschau)
        else:
            plan(path, ziel, grund)

    # --- Bericht ---------------------------------------------------------
    # Standard ist die Kurzfassung: nur Zahlen je Zielordner. Die vollstaendige
    # Auflistung jeder einzelnen Datei blaeht die Ausgabe bei grossen Laeufen
    # auf tausende Zeilen auf - mit --details anfordern, wenn wirklich noetig.
    header = "WUERDE einsortieren (Testlauf, nichts wurde verschoben)" if dry else "Einsortiert"
    print(f"\n{header}: {len(moved)}")

    by_dest = {}
    for name, new_path, reason in moved:
        by_dest.setdefault(str(Path(new_path).parent), []).append((name, reason))

    if args.details:
        for dest in sorted(by_dest):
            print(f"\n  {dest}  ({len(by_dest[dest])})")
            for name, reason in by_dest[dest]:
                print(f"    {name}   [{reason}]")
    else:
        # Auf Hauptkategorie zusammenfassen (max. 3 Pfadebenen), damit auch
        # tief verschachtelte Uebernahmen nur eine Zeile ergeben.
        grob = {}
        for dest, eintraege in by_dest.items():
            schluessel = "/".join(Path(dest).parts[:3])
            grob[schluessel] = grob.get(schluessel, 0) + len(eintraege)
        for k in sorted(grob):
            print(f"  {grob[k]:5d}  {k}")

    if dedup:
        print(f"\nEchte Duplikate ({'wuerden ' if dry else ''}geloescht): {len(dedup)}"
              "  - Inhalt per SHA1 geprueft")
        if args.details:
            for name, dest_rel, hinweis in dedup:
                print(f"  {name}   ->  {dest_rel}   [{hinweis}]")

    if varianten:
        print(f"\nGleicher Name, ANDERER Inhalt: {len(varianten)}"
              "  - nichts geloescht, Ablage als '(2)'")
        if args.details:
            for name, dest_rel, hinweis in varianten:
                print(f"  {name}   ->  {dest_rel}   [{hinweis}]")
        else:
            print("  (mit --details auflisten)")

    if skipped:
        gruende = {}
        for _, reason in skipped:
            gruende[reason] = gruende.get(reason, 0) + 1
        print(f"\nBewusst NICHT angefasst: {len(skipped)}")
        for g, n in sorted(gruende.items(), key=lambda x: -x[1]):
            print(f"  {n:5d}  {g}")
        if args.details:
            for rel_path, reason in skipped:
                print(f"    {rel_path}   [{reason}]")

    if unsorted:
        print(f"\nNicht zugeordnet, bleibt im Posteingang: {len(unsorted)}")
        if args.details:
            for rel_path, reason, preview in unsorted:
                print(f"  {rel_path}   [{reason}]")
                if preview:
                    print(f"    Vorschau: {preview}")
        else:
            print("  (mit --details auflisten)")

    if (moved or dedup or varianten) and not dry:
        print("\nAktualisiere Suchindex ...")
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "index.py")])

    return 0


if __name__ == "__main__":
    sys.exit(main())
