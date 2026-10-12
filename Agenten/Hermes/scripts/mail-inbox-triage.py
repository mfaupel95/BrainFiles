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
                                       r"noreply|no-reply|nicht\s+antworten|@paypal\.(de|com))"),
    # Kaltakquise: ein einseitiger Verkaufs-Pitch ohne Auftrag, weder
    # Newsletter noch Werbung. Gemessen 10.10.: 'Mein neuer Skill fuer deine
    # eigene Website' (julian@ki-automatisierungs-community.de) sammelte 2,5
    # Punkte ("heute zehn Minuten" + Antwort-Floskel) und waere ueber die
    # Schwelle gerutscht, weil keines der Werbe-Muster griff.
    ("kaltakquise", r"(ki-automatisierungs-community|von null bis online|website mit ki)"),
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

    muster_antwort = [
        # Deutsch (Stammtreppe)
        r"\b(frage|fragen)\b", r"\bantwort\w*\b", r"\brückfrage\b",
        r"\brueckfrage\b", r"\bwir\s+warten\b", r"\bbitte\s+(melden|"
        r"bestätigen|best[aä]tigen|unterschreiben|zahlen|bezahlen)",
        r"\bfehlt\s+(noch|ihre?)\b", r"\bnoch\s+nicht\s+(beantwortet|"
        r"gesendet|erledigt)\b",
        # Englisch: Fragen, die eine Antwort erwarten (Absender ist ein Mensch,
        # kein no-reply - der kommt ueber AUSSCHLUSS). Gemessen 12.10.2026:
        # "A quick question ... What were you hoping to ..." scorte 0,0, weil
        # nur deutsche Muster griffen.
        r"\b(quick\s+)?question\b", r"\basking\b", r"\bcurious\b",
        r"\bwhat\s+(were|are|do|did|would|can|could|have)\s+you\b",
        r"\b(your\s+)?(thoughts|input|feedback|opinion)\b",
        r"\bwould\s+you\s+(be\s+)?(willing|able)\b",
        r"\bhow\s+(do|would|can)\s+you\b",
    ]
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
    ap.add_argument("--fenster-erzwingen", action="store_true",
                    help="--stunden auch bei vorhandener Merkdatei nutzen "
                         "(Gegenlesen); sonst gilt UID-Fortschritt")
    ap.add_argument("--grenze", type=float, default=SCHWELLE_FRIST,
                    help="ab dieser Punktzahl wird gemeldet")
    ap.add_argument("--alle", action="store_true", help="jede neue Mail listen")
    ap.add_argument("--trocken", action="store_true",
                    help="nur lesen, Merkdatei unveraendert")
    args = ap.parse_args()

    adresse, passwort = _anmeldung()

    merk = _merkdatei()
    jetzt = datetime.now(timezone.utc)
    # T-375 (07.10.2026): SEARCH SINCE arbeitet auf INTERNALDATE und
    # verwirft Mails, deren Date-KOPF alt ist (Gmail legt nachtraeglich
    # Mails in die INBOX, deren Ankunftsdatum weit zurueckliegt). Der
    # Fortschritt laeuft deshalb ueber die UID: "alle Mails, die seit der
    # zuletzt gesehenen UID dazu kamen" ist die richtige Menge fuer
    # "seit dem letzten Lauf", unabhaengig von Ankunfts- und Absendedatum.
    # --fenster-erzwingen schaltet fuer ein Gegenlesen zurueck auf das
    # Zeitfenster (auch bei vorhandener Merkdatei). Beide Wege fahren
    # UID SEARCH - der Datum-Weg nur mit zusaetzlichem SINCE-Kriterium.
    zuletzt_uid = merk.get("zuletzt_uid")
    if args.fenster_erzwingen or not zuletzt_uid:
        if merk.get("zuletzt_gelesen_bis") and not args.fenster_erzwingen:
            try:
                bis = datetime.fromisoformat(merk["zuletzt_gelesen_bis"])
            except ValueError:
                bis = jetzt - timedelta(hours=args.stunden)
            # Auch im Datum-Weg die UIDs mitlesen: so schaltet der Betrieb
            # nach dem ERSTEN Lauf mit gesehener UID automatisch auf den
            # UID-Anker um (sonst bliebe der Fix fuer immer wirkungslos).
            kriterium = f'(SINCE "{bis.astimezone().strftime("%d-%b-%Y")}")'
        else:
            bis = jetzt - timedelta(hours=args.stunden)
            kriterium = f'(SINCE "{bis.astimezone().strftime("%d-%b-%Y")}")'
    else:
        bis = None
        kriterium = None
    kandidaten: list[dict] = []
    newest_bis = bis
    newest_uid = int(zuletzt_uid or 0)

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
        # Immer UID SEARCH: auch der Datum-Weg liefert UIDs zurueck, damit
        # der Betrieb nach dem ersten Lauf auf den UID-Anker umschaltet.
        if kriterium:
            typ, daten = imap.uid("SEARCH", None, kriterium)
        else:
            # UID-Suche: alles, was seit der zuletzt gesehenen UID dazu kam.
            # Nachricht 1905 (altes INTERNALDATE, neu in der INBOX) hat eine
            # hohe UID und wird so gefunden, obwohl SINCE sie ueberspringt.
            typ, daten = imap.uid("SEARCH", None, f"UID {int(zuletzt_uid) + 1}:*")
        ids = (daten[0].split() if typ == "OK" and daten else [])
        # Nur die letzten 60 holen - es geht um NEUE Post, nicht um Historie
        for nummer in ids[-60:]:
            # UID aus der Suche mitlesen: bei UID SEARCH sind die ids selbst
            # die UIDs - kein Parsen der FETCH-Antwort noetig (T-375).
            uid_aktuell = int(nummer) if nummer.isdigit() else 0
            # UID-Weg (kriterium ist None): Gmail liefert bei einem leeren
            # Bereich die HOECHSTE vorhandene UID zurueck (gemessen 09.10.:
            # 'UID SEARCH 13368:*' -> ['13367']). Eine UID <= zuletzt_uid
            # ist schon gesehen - ohne den Sprung zaehlte sie als Kandidat,
            # der Schreibblock verglich newest_uid > zuletzt_uid (13367 >
            # 13367 = falsch) und die Merkdatei verlor BEIDE Anker.
            if kriterium is None and uid_aktuell <= int(zuletzt_uid or 0):
                continue
            typ, voll = imap.uid(
                "FETCH", nummer,
                "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
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
            # T-375: der Date-Kopf entscheidet im UID-Weg NICHT mehr - eine
            # Mail mit altem Kopf ist trotzdem NEU in der INBOX und muss
            # geprueft werden. Nur im Zeitfenster-Weg (--fenster-erzwingen
            # bzw. ohne Merkdatei) bleibt der Kopf-Filter als zweiter
            # Zeuge gegen den Ankunftszeitraum.
            if bis is not None and datum and datum <= bis:
                continue
            typ2, roh = imap.uid("FETCH", nummer, "(BODY.PEEK[])")
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
            if datum and (newest_bis is None or datum > newest_bis):
                newest_bis = datum
            if uid_aktuell > newest_uid:
                newest_uid = uid_aktuell

    kandidaten.sort(key=lambda m: (-m["punkte"], m["datum"] or ""), reverse=False)
    gemeldet = [m for m in kandidaten if args.alle or m["punkte"] >= args.grenze]

    if not args.trocken and not args.fenster_erzwingen and kandidaten:
        merk_neu = {"zuletzt_lauf": jetzt.isoformat(),
                    "gelesen": len(kandidaten)}
        # Die UID ist der dauerhafte Anker: auch im Datum-Weg wird sie
        # mitgeschrieben, damit der naechste Lauf auf UID umschaltet.
        if newest_uid > int(zuletzt_uid or 0):
            merk_neu["zuletzt_uid"] = newest_uid
        # Der Datum-Fortschritt bleibt als Rueckfall erhalten (nur im
        # Zeitfenster-Weg sinnvoll; beim Gegenlesen mit --fenster-erzwingen
        # wird die Merkdatei bewusst NICHT veraendert - das Waere das
        # festgeschriebene Gegenlese-Datum).
        if bis is not None and not args.fenster_erzwingen:
            merk_neu["zuletzt_gelesen_bis"] = newest_bis.isoformat()
        _merk_schreiben(merk_neu)

    if not gemeldet:
        return 0   # leere Ausgabe = nichts senden

    if bis is not None:
        anker = f"seit {bis.astimezone().strftime('%d.%m. %H:%M')}"
    else:
        anker = f"ab UID {zuletzt_uid}+"
    zeilen = [f"**Post {anker}: "
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
