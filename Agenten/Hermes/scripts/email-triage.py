"""
Eingangs-Triage fuer Max' Gmail (NUR LESEND).

Liest den Posteingang seit dem letzten Lauf (Merkdatei in Agenten/Hermes/cache),
filtert nach: benoetigt Antwort heute / von Familie / erwaehnt Frist oder
Termin, bewertet mit einem Stichwort-Klassifizierer und gibt NUR aus, was die
Schwelle erreicht. Leere Ausgabe = nichts zu melden (Watchdog-Muster).

Zugangsdaten kommen aus mailversand.zugang_lesen() (Windows-Anmeldespeicher),
werden nie ausgegeben. Kein \\Seen-Flag wird gesetzt (readonly-Select).
"""
from __future__ import annotations

import argparse
import email
import imaplib
import json
import re
import sys
import time
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from pathlib import Path

HIER = Path(__file__).resolve()

if HIER.name == "email_triage_run.py" or HIER.parent.name == "scratch":
    # Entwicklungs-/Scratch-Lauf: scratch/cache/Hermes/Agenten/MCP-Server/mail
    MAIL_DIR = HIER.parents[3] / "MCP-Server" / "mail"
    CACHE_DIR = HIER.parents[2] / "cache"
else:
    # Regulaerer Lauf aus Agenten/Hermes/scripts/
    MAIL_DIR = HIER.parents[2] / "MCP-Server" / "mail"
    CACHE_DIR = HIER.parents[1] / "cache"

sys.path.insert(0, str(MAIL_DIR))
import mailversand  # noqa: E402

STAND_DATEI = CACHE_DIR / "email-triage-stand.json"

# Einfacher Stichwort-Klassifizierer (de/en). Werte additiv.
AUTOMATIK = re.compile(
    r"no-?reply|donotreply|noreply|notification|notifications|newsletter|"
    r"info@|support@|mailer|daemon|service@|alert@|updates@|billing@|automated",
    re.I,
)
FAMILIE = re.compile(r"\bfaupel\b|mama|papa|oma|opa", re.I)
FRIST = re.compile(
    r"\bfrist\b|\bdeadline\b|bis (spaetestens |zum |zur )?|bis heute|boss?|"
    r"\btermin\b|\bzahlung\b|\brechnung\b|\bmahnung\b|\bbescheid\b|"
    r"\bvorauszahlung\b|\beinwand\b|\beinspruch\b|\bfinanzamt\b|\bkuendigung\b|"
    r"kündigung|\brueckgabe\b|\brückgabe\b|\boepnv\b|abgabe", re.I)
ANTWORT = re.compile(
    r"\bantwort\b|\brückmeldung\b|\brueckmeldung\b|\breply\b|let me know|"
    r"please respond|please reply|\basap\b|so schnell wie möglich|so schnell wie "
    r"moeglich|bis heute|\beod\b|heute (noch|abend|mittag|morgen)|wann (kannst|bekomme|"
    r"kommst|folgt)|brauche (noch|deine)|benötige|benoetige|könntest du|koenntest du|"
    r"bitte (um|zurück|zurueck|antworten|melden)|zurückmelden|zurueckmelden", re.I)
WICHTIG = re.compile(
    r"\bunbedingt\b|\bdringend\b|\bwichtig\b|\bsofort\b|erinnerung|reminder|\bkw\d+\b", re.I)


def kopf_feld(nachricht: email.message.Message, feld: str) -> str:
    roh = nachricht.get(feld, "")
    try:
        return str(make_header(decode_header(roh)))
    except Exception:
        return str(roh)


def adresse_zeile(nachricht: email.message.Message, feld: str) -> str:
    wert = nachricht.get(feld, "")
    if not wert:
        return ""
    match = re.search(r"([^<>\s]+@[^<>\s]+)", str(wert))
    return match.group(1) if match else str(wert).strip()


def datum_parsen(nachricht: email.message.Message, uid: str, imap) -> str:
    try:
        dt = parsedate_to_datetime(nachricht.get("Date"))
        return dt.astimezone().isoformat()
    except Exception:
        pass
    # Rueckfall INTERNALDATE
    try:
        status, daten = imap.uid("FETCH", uid, "(INTERNALDATE)")
        for teil in daten or []:
            if isinstance(teil, tuple) and len(teil) > 1:
                from email.utils import parsedate_to_datetime as pd2
                return pd2(teil[1].decode("utf-8", "replace")).astimezone().isoformat()
    except Exception:
        pass
    return ""


def bewerten(adresse: str, betreff: str, text: str, alter_h: float) -> int:
    punkt = 0
    feld = f"{betreff} {text}"
    if AUTOMATIK.search(feld):
        punkt -= 3
    if FAMILIE.search(feld):
        punkt += 3
    if FRIST.search(feld):
        punkt += 2
    if ANTWORT.search(feld):
        punkt += 2
    if WICHTIG.search(feld):
        punkt += 1
    if alter_h <= 24:
        punkt += 1
    return punkt


def haupttext(roh_teil: bytes) -> str:
    """Bester Textteil des rohen Nachrichtenkörpers: text/plain zuerst, sonst
    text/html (Tags entfernt). Nimmt den laengsten nicht-leeren Teil."""
    try:
        msg = email.message_from_bytes(roh_teil)
    except Exception:
        return roh_teil.decode("utf-8", "replace")
    texte_plain: list[str] = []
    texte_html: list[str] = []
    for teil in msg.walk():
        ctype = teil.get_content_type()
        try:
            payload = teil.get_payload(decode=True)
        except Exception:
            payload = None
        if not payload:
            continue
        try:
            text = payload.decode(teil.get_content_charset() or "utf-8", "replace")
        except Exception:
            text = payload.decode("utf-8", "replace")
        if ctype == "text/plain":
            texte_plain.append(text)
        elif ctype == "text/html":
            texte_html.append(re.sub(r"<[^>]+>", " ", text))
    auswahl = texte_plain or texte_html
    if not auswahl:
        return ""
    if texte_plain and any(len(t) > 80 for t in texte_plain):
        return max(texte_plain, key=len)
    return max(auswahl, key=len)


def lauf(vorschau: bool = False) -> list[dict]:
    adresse, passwort = mailversand.zugang_lesen()

    stand = {"letzte_pruefung": None, "message_ids": []}
    if STAND_DATEI.exists():
        try:
            stand = json.loads(STAND_DATEI.read_text(encoding="utf-8"))
        except Exception:
            stand = {"letzte_pruefung": None, "message_ids": []}

    seither = stand.get("letzte_pruefung")
    seither = float(seither) if seither else (time.time() - 72 * 3600)
    seither = max(seither, time.time() - 72 * 3600)  # nie weiter als 72 h zurueck
    bekannte = set(stand.get("message_ids", []))

    neue = []
    with imaplib.IMAP4_SSL(mailversand.IMAP_HOST, mailversand.IMAP_PORT, timeout=60) as imap:
        imap.login(adresse, passwort)
        typ, status_d = imap.select("INBOX", readonly=True)
        if typ != "OK" or not status_d:
            return neue
        n = int(status_d[0].decode())
        # Gmail-UIDs sind NICHT stabil (werden bei Expunge neu vergeben) - deshalb
        # ueber SEQUENZNUMMERN vom aktuellen Ende des Posteingangs arbeiten.
        start = max(1, n - 60)
        status, daten = imap.fetch(
            f"{start}:{n}",
            "(INTERNALDATE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])",
        )
        if status != "OK":
            return neue
        for teil in daten or []:
            if not isinstance(teil, tuple) or len(teil) < 2:
                continue
            label, kopf_roh = teil[0], teil[1]
            label_txt = label.decode("utf-8", "replace")
            treffer = re.search(r"INTERNALDATE \"([^\"]+)\"", label_txt)
            if not treffer or not kopf_roh:
                continue
            try:
                eingang_epoch = parsedate_to_datetime(treffer.group(1)).timestamp()
            except Exception:
                continue
            if eingang_epoch < seither - 6 * 3600:  # 6 h Ueberlappung gegen Zeitdrift
                continue
            if not kopf_roh.strip():
                continue
            try:
                nachricht = email.message_from_bytes(kopf_roh)
            except Exception:
                continue
            message_id = (nachricht.get("Message-ID") or f"seq-{label_txt.split()[0]}").strip()
            if message_id in bekannte:
                continue
            seq = label_txt.split(maxsplit=1)[0]
            text_roh = b""
            try:
                # Ganze Nachricht (gedeckelt) holen, damit die MIME-Struktur
                # wirklich geparst werden kann - BODY[TEXT] liefert bei
                # Multipart das rohe Blob MIT Boundary-Marken als "text/plain".
                status_b, text_daten = imap.fetch(seq, "(BODY.PEEK[]<0.30000>)")
                for teil_b in text_daten or []:
                    if isinstance(teil_b, tuple) and len(teil_b) > 1:
                        text_roh = teil_b[1]
            except Exception:
                pass
            von = adresse_zeile(nachricht, "From")
            betreff = kopf_feld(nachricht, "Subject")
            iso = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(eingang_epoch))
            alter_h = (time.time() - eingang_epoch) / 3600
            text = haupttext(text_roh)[:2500]
            punkt = bewerten(von, betreff, text, alter_h)
            neue.append({
                "von": von,
                "betreff": betreff,
                "datum": iso,
                "alter_h": round(alter_h, 1),
                "score": punkt,
                "text": text[:800],
                "message_id": message_id,
            })

    # Merkstand fortschreiben (auch bei Vorschau nicht - Merken ist ein Schreibvorgang)
    if not vorschau:
        neue_ids = [m["message_id"] for m in neue]
        bekannte.update(neue_ids)
        bekannte = list(bekannte)[-800:]
        stand["message_ids"] = bekannte
        stand["letzte_pruefung"] = time.time()
        STAND_DATEI.parent.mkdir(parents=True, exist_ok=True)
        STAND_DATEI.write_text(json.dumps(stand, ensure_ascii=False, indent=1), encoding="utf-8")

    return neue


def bericht(kandidaten: list[dict]) -> str:
    if not kandidaten:
        return ""
    zeilen = ["📬 Eingang (nur das, was durch den Filter fällt):"]
    for k in kandidaten:
        zeilen.append(f"\n• {k['betreff'] or '(ohne Betreff)'}")
        zeilen.append(f"  Von: {k['von']} · {k['datum'][:16].replace('T', ' ')} "
                      f"({k['alter_h']:.0f} h alt) · Score {k['score']}")
        text = k["text"].replace("\r", " ").replace("\n", " ").strip()
        text = re.sub(r"\s{2,}", " ", text)
        if text:
            zeilen.append(f"  {text[:200]}")
    return "\n".join(zeilen)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eingangs-Triage (nur lesend)")
    parser.add_argument("--vorschau", action="store_true",
                        help="liest, schreibt den Merkstand NICHT fort")
    parser.add_argument("--schwelle", type=int, default=3,
                        help="Score-Schwelle (Standard 3)")
    parser.add_argument("--debug", action="store_true",
                        help="zeigt ALLE Kandidaten ohne Score-Filter")
    args = parser.parse_args()
    try:
        kandidaten = lauf(vorschau=args.vorschau)
    except Exception as fehler:
        print(f"FEHLER bei der Eingangs-Triage: {fehler}")
        sys.exit(2)
    if args.debug:
        for k in sorted(kandidaten, key=lambda x: x["score"], reverse=True):
            print(f"[{k['score']:+d}] {k['datum'][:16]} {k['von']} | {k['betreff']}")
        sys.exit(0)
    kandidaten = [k for k in kandidaten if k["score"] >= args.schwelle]
    ausgabe = bericht(kandidaten)
    print(ausgabe)
