#!/usr/bin/env python3
"""
Liest neue Post im Gmail-Posteingang seit dem letzten Lauf und meldet nur,
was die Treppe besteht: Antwort HEUTE noetig, von Manager/Familie, oder
mit Frist-Bezug. Sonst leere Ausgabe (Watchdog-Muster: leer = nichts senden).

Zugang: IMAP mit dem App-Passwort aus dem Windows-Anmeldeinformationsspeicher
(Agenten/MCP-Server/mail/mailversand.py, Dienst 'MaxMailVersand'). Es wird
nichts gelesen, markiert oder verschoben - nur eine Auswahl aus unveraenderter
Post. Merkdatei: Agenten/Hermes/cache/mail-inbox-triage.json

Aufruf (Interpreter = der mail-.venv, dort liegt keyring):
  mail/.venv/Scripts/python.exe scripts/mail-inbox-triage.py --stunden 26
  ... --trocken   (nur zaehlen, Merkdatei unveraendert)
"""
from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
HERMES = HIER.parent
MERK = HERMES / "cache" / "mail-inbox-triage.json"
MAIL_PAKET = HERMES.parent / "MCP-Server" / "mail"

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# --- Wessen Post ist relevant? (Namen/Adressen eintragen) ---------------------
VORSATZ = [
    # Familie
    "familie", "privat",
    # Chefe/Arbeitgeber
    "chef", "boss", "arbeitgeber", "personal",
    # Behoerde/Steuer/Bank (Fristen kommen von dort)
    "finanzamt", "elster", "steuer", "bank", "versicherung", "rentenversicherung",
]
FRIST_BEGRiffe = [
    r"\bfrist\b", r"\bdeadline\b", r"\bfaellig\b", r"\bfällig\b",
    r"\bbis\s+\d{1,2}\.\s*(januar|februar|m[aä]rz|april|mai|juni|juli|august|"
    r"september|oktober|november|dezember)",
    r"\bbis\s+(montag|dienstag|mittwoch|donnerstag|freitag|heute|morgen|wochenende|"
    r"monatsende|jahresende|quartalsende)",
    r"\bmaßnahme\s+erforderlich\b", r"\bhandlungsbedarf\b", r"\b(letzte|letzter)\s+"
    r"(woche|tag|frist|moeglichkeit|gelegenheit)\b",
    r"\brückmeldung\b", r"\brueckmeldung\b", r"\bbitte\s+(melden|zahlen|bezahlen|"
    r"unterschreiben|best[aä]tigen|einreichen|senden)\b",
    r"\brückstand\b", r"\brueckstand\b", r"\bmahnung\b", r"\bzahlung\s+bis\b",
    r"\bsteuererkl[aä]rung\b", r"\b(\d{1,2}\.\s*(02|03|04|05|06)\.\d{4})\b",
]

AUSSCHLUSS = [
    ("newsletter", r"(newsletter|abmelden|unsubscribe|klickgratis|%\s*off|rabatt)"),
    ("werbung", r"(newsletter|promotion|angebot|werbung|marketing|rabatt|gutschein|"
                r"black ?friday|deal[s]?\b|%\s*off|jetzt kaufen)"),
    # WICHTIG: der Absender gehoert in den Ausschluss-Blick. Ein no-reply
    # im From ist kein Adressat, der antworten kann - ohne das rutscht jede
    # Bestaetigungsmail ueber die Schwelle (gemessen: Anthropic-Zahlungsmail
    # 04.10. mit 'erwartet Antwort', weil das HTML im Body das Wort 'Antwort'
    # irgendwo im Fussnote-Block mitbringt).
    ("automatisierte_benachrichtigung", r"(notification|benachrichtigung|do-not-reply|"
                                       r"noreply|no-reply|nicht\s+antworten)"),
]

DRINGEND_TEXT = [
    r"\bdringend\b", r"\bsofort\b", r"\beilig\b", r"\bheute\b", r"\bdiesen\s+tag\b",
    r"\bpriorit[aä]t\b", r"\bwichtig\b", r"\bmah(nung|n)\b",
]

SCHWELLE_ANFUEHR = 2.0   # Antwort heute noetig
SCHWELLE_FRIST = 1.0     # Frist-Bezug


def _anmeldung() -> tuple[str, str]:
    sys.path.insert(0, str(MAIL_PAKET))
    import mailversand  # noqa: E402
    return mailversand.zugang_lesen()


TAG = re.compile(r"<[^>]+>")
FUSS_NOTE = re.compile(r"(font-size\s*:\s*(1[01]px|10px)|color\s*:\s*#\w{6})",
                       re.IGNORECASE)


def _text(nachricht) -> str:
    """Nur der fuer einen Menschen lesbare Teil.

    Gmail liefert bei HTML-Mails oft NUR <BODY.PEEK[TEXT]> als HTML-Rumpf mit
    tausend Zeichen Layout und Fussnoten ('Antworten Sie an ...', 'warum diese
    Mail'). Solcher Text erzeugt Punkte fuer Woerter, die inhaltlich nichts
    tragen - der erste echte Lauf dieses Werkzeugs meldete genau daran eine
    Zahlungsbestaetigung. Deshalb: HTML auf Text, dann alles ab der Fussnote
    abschneiden und laengere Unsinnsbloecke (Base64/quasi-groessere
    Signaturen) kuerzen.
    """
    teile = []
    if nachricht.is_multipart():
        for stueck in nachricht.walk():
            if stueck.get_content_type() in ("text/plain", "text/html"):
                payload = stueck.get_payload(decode=True)
                if payload:
                    teile.append(payload.decode(stueck.get_content_charset() or "utf-8",
                                                "replace"))
    else:
        payload = nachricht.get_payload(decode=True)
        if payload:
            teile.append(payload.decode(nachricht.get_content_charset() or "utf-8",
                                        "replace"))
    text = "\n".join(teile)
    if "<" in text and ">" in text:
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
        text = TAG.sub(" ", text)
        text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                    .replace("&quot;", '"').replace("&#39;", "'")
                    .replace("&lt;", "<").replace("&gt;", ">"))
    # Fussnote/Disclaimer abschneiden
    treffer = FUSS_NOTE.search(text)
    if treffer and treffer.start() > 200:
        text = text[:treffer.start()]
    # Alles, was keine Buchstaben hat (Signatur-Base64), raus
    text = "\n".join(zeile for zeile in text.splitlines()
                     if sum(c.isalpha() for c in zeile) > len(zeile) * 0.4)
    return text[:6000]


def _trifft(text: str, muster: list[str]) -> list[str]:
    treffer = []
    for m in muster:
        if re.search(m, text, re.IGNORECASE):
            treffer.append(m)
    return treffer


def einordnen(absender: str, betreff: str, koerper: str) -> dict:
    """Punkte = drei Filter ODER-verknuepft, dazu Belastung durch Muell.

    Wichtig: der VORSATZ gehoert in den ABSENDER, nicht in den Koerper. Mit
    dem Koerper traf jedes Wort 'Bank' in einer Zahlungsmail den Behoerden-Filter
    (gemessen 04.10.: 'failed-payments@' wurde dadurch als Behoerde gewertet).
    """
    absender_klein = absender.lower()
    inhalt = f"{betreff}\n{koerper}".lower()
    punkte = 0.0
    gruende = []

    muster_antwort = [r"\b(frage|fragen)\b", r"\bantwort\w*\b", r"\brückfrage\b",
                      r"\brueckfrage\b", r"\bwir\s+warten\b", r"\bbitte\s+(melden|"
                      r"bestätigen|best[aä]tigen|unterschreiben|zahlen|bezahlen)",
                      r"\bfehlt\s+(noch|ihre?)\b", r"\bnoch\s+nicht\s+(beantwortet|"
                      r"gesendet|erledigt)\b"]
    if _trifft(inhalt, muster_antwort):
        punkte += 1.5
        gruende.append("erwartet Antwort")

    if _trifft(absender_klein, VORSATZ):
        punkte += 1.0
        gruende.append("Vorsatz/Familie/Behoerde")

    if _trifft(inhalt, FRIST_BEGRiffe):
        punkte += SCHWELLE_FRIST
        gruende.append("Frist-Bezug")

    if _trifft(inhalt, DRINGEND_TEXT):
        punkte += 1.0
        gruende.append("Dringlichkeit im Text")

    # Muell belastet. Ein Absender ohne Antwortweg ist kein Pruefstein fuer
    # 'erwartet Antwort' - deshalb traegt die Automatik-Minderung VOR der
    # positiven Bewertung und kann sie neutralisieren.
    for name, muster in AUSSCHLUSS:
        if re.search(muster, absender_klein, re.IGNORECASE):
            punkte -= 2.5
            gruende.append(f"aussortiert (Absender): {name}")
            continue
        if re.search(muster, inhalt[:1200], re.IGNORECASE):
            punkte -= 2.5
            gruende.append(f"aussortiert: {name}")

    return {"punkte": round(punkte, 2), "gruende": gruende}


def _merkdatei() -> dict:
    try:
        return json.loads(MERK.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _merk_schreiben(daten: dict) -> None:
    MERK.parent.mkdir(parents=True, exist_ok=True)
    # Inhalt ZUERST zusammenbauen (TASKS.md-Lektion: nicht mitten im Schreiben
    # die Datei kuerzen).
    roh = json.dumps(daten, ensure_ascii=False, indent=2)
    assert roh and len(roh) > 10
    MERK.write_text(roh, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stunden", type=float, default=26.0,
                    help="Fenster, wenn keine Merkdatei vorliegt")
    ap.add_argument("--grenze", type=float, default=SCHWELLE_FRIST,
                    help="ab dieser Punktzahl wird gemeldet")
    ap.add_argument("--alle", action="store_true", help="jede neue Mail listen")
    ap.add_argument("--trocken", action="store_true",
                    help="nur lesen, Merkdatei unveraendert")
    args = ap.parse_args()

    adresse, passwort = _anmeldung()

    merk = _merkdatei()
    jetzt = datetime.now(timezone.utc)
    if merk.get("zuletzt_gelesen_bis"):
        try:
            bis = datetime.fromisoformat(merk["zuletzt_gelesen_bis"])
        except ValueError:
            bis = jetzt - timedelta(hours=args.stunden)
    else:
        bis = jetzt - timedelta(hours=args.stunden)

    suche = f'(SINCE "{bis.astimezone().strftime("%d-%b-%Y")}")'
    kandidaten: list[dict] = []
    newest_bis = bis

    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=60) as imap:
        imap.login(adresse, passwort)
        typ, ordner = imap.list()
        inbox_name = '"INBOX"'
        for zeile in ordner or []:
            text = zeile.decode("utf-8", "replace") if isinstance(zeile, bytes) else str(zeile)
            if "\\Inbox" in text:
                inbox_name = text.split(' "/" ')[-1].strip()
                break
        imap.select(inbox_name)
        typ, daten = imap.search(None, suche)
        ids = (daten[0].split() if typ == "OK" and daten else [])
        # Nur die letzten 60 holen - es geht um NEUE Post, nicht um Historie
        for nummer in ids[-60:]:
            typ, voll = imap.fetch(nummer, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if typ != "OK" or not voll or not isinstance(voll[0], tuple):
                continue
            kopf = email.message_from_bytes(voll[0][1])
            datum = None
            try:
                datum = parsedate_to_datetime(kopf.get("Date", ""))
                if datum.tzinfo is None:
                    datum = datum.replace(tzinfo=timezone.utc)
                datum = datum.astimezone(timezone.utc)
            except Exception:
                pass
            if datum and datum <= bis:
                continue
            typ2, roh = imap.fetch(nummer, "(BODY.PEEK[])")
            koerper = ""
            if typ2 == "OK" and roh and isinstance(roh[0], tuple):
                # Die VOLLE Nachricht holen, nicht BODY.PEEK[TEXT]: bei einer
                # multipart-Mail liefert TEXT nur den rohen MIME-Block mit den
                # Part-Headern ("Content-Transfer-Encoding: quoted-printable")
                # als Text - der echte Inhalt blieb dann unlesbar (=E2=82=AC).
                koerper = _text(email.message_from_bytes(roh[0][1]))
            absender = str(make_header(decode_header(kopf.get("From", ""))))
            betreff = str(make_header(decode_header(kopf.get("Subject", ""))))
            urteil = einordnen(absender, betreff, koerper)
            kandidaten.append({
                "von": absender, "betreff": betreff,
                "datum": datum.isoformat() if datum else None,
                "ausschnitt": " ".join(koerper.split())[:400],
                **urteil,
            })
            if datum and datum > newest_bis:
                newest_bis = datum

    kandidaten.sort(key=lambda m: (-m["punkte"], m["datum"] or ""), reverse=False)
    gemeldet = [m for m in kandidaten if args.alle or m["punkte"] >= args.grenze]

    if not args.trocken and kandidaten:
        _merk_schreiben({"zuletzt_gelesen_bis": newest_bis.isoformat(),
                        "zuletzt_lauf": jetzt.isoformat(),
                        "gelesen": len(kandidaten)})

    if not gemeldet:
        return 0   # leere Ausgabe = nichts senden

    zeilen = [f"**Post seit {bis.astimezone().strftime('%d.%m. %H:%M')}: "
              f"{len(gemeldet)} von {len(kandidaten)} neuen Mails ueber der Schwelle**", ""]
    for m in gemeldet[:12]:
        zeilen.append(f"- **{m['betreff'][:90]}**")
        zeilen.append(f"  {m['von']} | {m['datum']} | Score {m['punkte']} "
                      f"({', '.join(m['gruende'])})")
        if m["ausschnitt"]:
            zeilen.append(f"  _{m['ausschnitt'][:220]}_")
    if len(gemeldet) > 12:
        zeilen.append(f"- ... und {len(gemeldet) - 12} weitere")
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
