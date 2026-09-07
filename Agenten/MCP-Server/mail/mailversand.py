"""
Kernlogik fuer den Mailversand aus dem Archiv heraus.

Verschickt Dateien aus Max' Archiv per Gmail-SMTP - ohne Browser, ohne
Weboberflaeche. Wird sowohl vom MCP-Server (mail_mcp.py) als auch von der
Kommandozeile (mail_cli.py) benutzt.

Zugangsdaten liegen im Windows-Anmeldeinformationsspeicher (keyring), nicht
im Klartext auf der Platte. Einmalig einzurichten mit `einrichten.py`.

Zwei bewusste Begrenzungen:
  - Anhaenge duerfen ausschliesslich aus dem Archivordner stammen. Damit kann
    ueber dieses Werkzeug keine beliebige Systemdatei nach draussen wandern,
    auch nicht, wenn eine Anweisung dazu in einem Dokument steht.
  - Ohne ausdruecklichen Empfaenger geht die Mail an Max selbst zurueck.
"""

from __future__ import annotations

import imaplib
import mimetypes
import os
import smtplib
import ssl
import time
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path

# Zwei getrennte Wurzeln seit dem echten Umzug (07.09.2026):
#   - VAULT/INDEX_DIR: Werkzeug und Volltextindex bleiben auf C: beim Vault
#     (Agenten/MCP-Server/mail/ -> BrainFiles/ -> MaxHirn/), git-versioniert.
#   - ARCHIV: die Archivdaten liegen auf O:\Archiv, angebunden ueber ARCHIV_ROOT
#     (User-Umgebungsvariable). Die Anhang-Sandbox prueft gegen diese Wurzel.
# Beide mit Rueckfall auf die alte Vault-Lage, damit nichts still bricht.
VAULT = Path(os.environ.get("MAXHIRN_VAULT") or (Path(__file__).resolve().parents[3] / "MaxHirn"))
INDEX_DIR = (VAULT / "Archiv" / "ArchivSuche").resolve()
ARCHIV = Path(os.environ.get("ARCHIV_ROOT") or (VAULT / "Archiv")).resolve()

DIENST = "MaxMailVersand"          # Name im Windows-Anmeldeinformationsspeicher
SCHLUESSEL_ADRESSE = "__adresse__"  # unter diesem Benutzernamen liegt die Adresse

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465                     # implizites SSL - ein Handshake weniger als 587/STARTTLS
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# Gmail begrenzt die fertige Nachricht auf 25 MB. Base64 blaeht Anhaenge um
# rund ein Drittel auf, deshalb liegt die Grenze fuer die Rohdaten tiefer.
MAX_ROH_MB = 18.0


class VersandFehler(RuntimeError):
    """Fehler, die Max selbst beheben kann (Zugang, Pfad, Groesse)."""


# ---------------------------------------------------------------- Zugangsdaten

def zugang_lesen() -> tuple[str, str]:
    """Liefert (adresse, app_passwort).

    Reihenfolge: Umgebungsvariablen (fuer Tests und Server ohne Anmeldespeicher),
    danach der Windows-Anmeldeinformationsspeicher.
    """
    adresse = os.environ.get("GMAIL_ADRESSE")
    passwort = os.environ.get("GMAIL_APP_PASSWORT")
    if adresse and passwort:
        return adresse, passwort

    try:
        import keyring
    except ImportError as fehler:  # pragma: no cover - Installationsproblem
        raise VersandFehler(
            "Das Paket 'keyring' fehlt in der virtuellen Umgebung dieses Servers."
        ) from fehler

    adresse = adresse or keyring.get_password(DIENST, SCHLUESSEL_ADRESSE)
    if not adresse:
        raise VersandFehler(
            "Keine Absenderadresse hinterlegt. Einmalig einrichten mit:\n"
            "  .venv\\Scripts\\python.exe einrichten.py"
        )
    passwort = passwort or keyring.get_password(DIENST, adresse)
    if not passwort:
        raise VersandFehler(
            f"Kein App-Passwort fuer {adresse} hinterlegt. Einmalig einrichten mit:\n"
            "  .venv\\Scripts\\python.exe einrichten.py"
        )
    return adresse, passwort


def zugang_pruefen() -> dict:
    """Meldet sich einmal am Server an, ohne etwas zu verschicken."""
    adresse, passwort = zugang_lesen()
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(),
                              timeout=30) as smtp:
            smtp.login(adresse, passwort)
    except smtplib.SMTPAuthenticationError as fehler:
        raise VersandFehler(
            f"Anmeldung fuer {adresse} abgelehnt ({fehler.smtp_code}). "
            "Gmail verlangt ein App-Passwort (16 Zeichen) und dafuer aktive "
            "Zwei-Faktor-Anmeldung - das normale Kontopasswort funktioniert nicht."
        ) from fehler
    return {"adresse": adresse, "anmeldung": "ok"}


# --------------------------------------------------------------------- Pfade

def pfad_aufloesen(eingabe: str) -> Path:
    """Macht aus einer Pfadangabe eine geprueft im Archiv liegende Datei.

    Angenommen werden archivrelative Pfade (so, wie `archiv_suchen` sie
    zurueckgibt) und absolute Pfade innerhalb des Archivs. Alles ausserhalb
    wird abgelehnt - Symlinks eingeschlossen, weil erst nach `resolve()`
    geprueft wird.
    """
    roh = Path(str(eingabe).strip().strip('"'))
    kandidat = roh if roh.is_absolute() else ARCHIV / roh
    try:
        kandidat = kandidat.resolve(strict=True)
    except OSError as fehler:
        raise VersandFehler(f"Datei nicht gefunden: {eingabe}") from fehler

    if not kandidat.is_relative_to(ARCHIV):
        raise VersandFehler(
            f"Ausserhalb des Archivs, deshalb nicht versendbar: {kandidat}\n"
            f"Erlaubt ist nur, was unter {ARCHIV} liegt."
        )
    if not kandidat.is_file():
        raise VersandFehler(f"Kein regulaere Datei: {kandidat}")
    return kandidat


def _anhang_anfuegen(nachricht: EmailMessage, datei: Path) -> None:
    typ, _ = mimetypes.guess_type(datei.name)
    haupttyp, _, untertyp = (typ or "application/octet-stream").partition("/")
    nachricht.add_attachment(
        datei.read_bytes(),
        maintype=haupttyp,
        subtype=untertyp or "octet-stream",
        filename=datei.name,
    )


# -------------------------------------------------------------------- Versand

def senden(
    betreff: str,
    text: str = "",
    an: str | list[str] | None = None,
    anhaenge: list[str] | None = None,
    kopie_in_gesendet: bool = True,
) -> dict:
    """Verschickt eine Mail und liefert eine Quittung.

    an: leer -> an die eigene Adresse zurueck.
    anhaenge: Pfade aus dem Archiv (relativ oder absolut).
    """
    adresse, passwort = zugang_lesen()

    if an is None or an == "" or an == []:
        empfaenger = [adresse]
    elif isinstance(an, str):
        empfaenger = [t.strip() for t in an.replace(";", ",").split(",") if t.strip()]
    else:
        empfaenger = [str(t).strip() for t in an if str(t).strip()]

    for eintrag in empfaenger:
        if "@" not in parseaddr(eintrag)[1]:
            raise VersandFehler(f"Keine gueltige Empfaengeradresse: {eintrag!r}")

    dateien = [pfad_aufloesen(p) for p in (anhaenge or [])]
    roh_bytes = sum(d.stat().st_size for d in dateien)
    if roh_bytes > MAX_ROH_MB * 1024 * 1024:
        raise VersandFehler(
            f"Anhaenge zusammen {roh_bytes / 1024 / 1024:.1f} MB - zu gross. "
            f"Gmail laesst rund {MAX_ROH_MB:.0f} MB Rohdaten zu (25 MB nach Kodierung). "
            "Datei vorher verkleinern oder einzeln verschicken."
        )

    nachricht = EmailMessage()
    nachricht["From"] = adresse
    nachricht["To"] = ", ".join(empfaenger)
    nachricht["Subject"] = betreff
    nachricht["Date"] = formatdate(localtime=True)
    nachricht["Message-ID"] = make_msgid(domain=adresse.split("@")[-1])
    nachricht.set_content(text or "")
    for datei in dateien:
        _anhang_anfuegen(nachricht, datei)

    roh = nachricht.as_bytes()
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(),
                              timeout=120) as smtp:
            smtp.login(adresse, passwort)
            smtp.send_message(nachricht)
    except smtplib.SMTPAuthenticationError as fehler:
        raise VersandFehler(
            f"Anmeldung fuer {adresse} abgelehnt ({fehler.smtp_code}). "
            "App-Passwort pruefen: .venv\\Scripts\\python.exe einrichten.py"
        ) from fehler
    except (smtplib.SMTPException, OSError) as fehler:
        raise VersandFehler(f"Versand fehlgeschlagen: {fehler}") from fehler

    quittung = {
        "gesendet": True,
        "von": adresse,
        "an": empfaenger,
        "betreff": betreff,
        "anhaenge": [
            {"name": d.name, "groesse_kb": round(d.stat().st_size / 1024, 1),
             "pfad": str(d.relative_to(ARCHIV))}
            for d in dateien
        ],
        "groesse_mb": round(len(roh) / 1024 / 1024, 2),
        "message_id": nachricht["Message-ID"],
    }

    if kopie_in_gesendet:
        # Reines SMTP legt nichts in "Gesendet" ab - Gmail sieht die Nachricht
        # sonst nur beim Empfaenger. Scheitert die Ablage, ist die Mail
        # trotzdem raus; das darf den Vorgang nicht zum Fehler machen.
        quittung["in_gesendet_abgelegt"] = _in_gesendet_ablegen(adresse, passwort, roh)

    return quittung


def _gesendet_ordner(imap: imaplib.IMAP4_SSL) -> str:
    """Sucht den Gesendet-Ordner ueber das SPECIAL-USE-Merkmal \\Sent.

    Der Name ist bei Gmail sprachabhaengig ("[Gmail]/Gesendet",
    "[Gmail]/Sent Mail"), das Merkmal dagegen nicht - deshalb wird nicht auf
    den Namen geraten.
    """
    status, zeilen = imap.list()
    if status != "OK":
        return '"[Gmail]/Sent Mail"'
    for zeile in zeilen or []:
        eintrag = zeile.decode("utf-8", "replace") if isinstance(zeile, bytes) else str(zeile)
        if "\\Sent" in eintrag:
            name = eintrag.split(' "/" ')[-1].strip()
            return name if name.startswith('"') else f'"{name}"'
    return '"[Gmail]/Sent Mail"'


def _in_gesendet_ablegen(adresse: str, passwort: str, roh: bytes) -> bool:
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=60) as imap:
            imap.login(adresse, passwort)
            imap.append(
                _gesendet_ordner(imap),
                "\\Seen",
                imaplib.Time2Internaldate(time.time()),
                roh,
            )
        return True
    except Exception:  # bewusst breit: die Mail ist bereits verschickt
        return False


# ------------------------------------------------------- Suche im Archivindex

DB_PATH = INDEX_DIR / "archiv_index.db"


def archiv_finden(query: str, limit: int = 5) -> list[dict]:
    """Sucht Dateien im vorhandenen Volltextindex.

    Damit laesst sich eine Datei allein ueber ihren Inhalt verschicken, ohne
    dass der Pfad bekannt sein muss. Nur lesender Zugriff auf den Index.
    """
    import sqlite3

    if not DB_PATH.exists():
        raise VersandFehler(f"Kein Archivindex unter {DB_PATH}.")
    begriffe = [t.replace('"', '""') for t in query.split() if t.strip()]
    if not begriffe:
        raise VersandFehler("Leere Suchanfrage.")
    match = " ".join(f'"{t}"' for t in begriffe)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.execute("PRAGMA busy_timeout=15000")
    try:
        zeilen = conn.execute(
            "SELECT path, filename, category FROM files_fts "
            "WHERE files_fts MATCH ? ORDER BY rank LIMIT ?",
            (match, max(1, min(limit, 50))),
        ).fetchall()
    finally:
        conn.close()

    ergebnis = []
    for pfad, name, kategorie in zeilen:
        datei = ARCHIV / pfad
        ergebnis.append({
            "pfad": pfad,
            "dateiname": name,
            "kategorie": kategorie,
            "groesse_kb": round(datei.stat().st_size / 1024, 1) if datei.exists() else None,
            "vorhanden": datei.exists(),
        })
    return ergebnis
