---
name: email-inbox-triage
description: Use when new mail needs triage by the urgency bar.
---

# Email-Inbox-Triage

Prueft den Gmail-Posteingang auf NEUE Post und meldet nur, was die Treppe
besteht. Leere Ausgabe = nichts senden (Watchdog-Muster, wie die anderen
Wachen im Haus).

## Werkzeug

`Agenten/Hermes/scripts/mail-inbox-triage.py` - ausfuehren mit dem mail-venv,
denn dort liegt `keyring`:

```
Agenten/MCP-Server/mail/.venv/Scripts/python.exe ^
  Agenten/Hermes/scripts/mail-inbox-triage.py            # meldet und speichert
  ... --trocken --stunden 26                            # nur lesen
  ... --alle                                            # jede neue Mail listen
  ... --grenze 2.0                                      # ab dieser Punktzahl melden
```

Zugang: IMAP 993 mit dem App-Passwort aus dem Windows-Anmeldeinformationsspeicher
(`mailversand.zugang_lesen()` -> Tupel `(adresse, app_passwort)`, Dienst
'MaxMailVersand'). Anmeldung vorher pruefen: MCP-Werkzeug `mail_zugang_pruefen`
oder `python mail_cli.py` (ohne Versand).
Ohne Zugang: genau das sagen und hier aufhoeren, nichts bauen.

Die Abholung ist **lesend**: `BODY.PEEK[]`, der Ordner wird nicht auf
`\Seen` gesetzt und nichts verschoben. Merkdatei
`Agenten/Hermes/cache/mail-inbox-triage.json` traegt `zuletzt_gelesen_bis`;
beim ersten Lauf greift `--stunden` als Fenster.

## Die Treppe (Punkte)

| Bedingung | Punkte |
|---|---|
| erwartet Antwort (Frage/Rueckfrage/„bitte melden/bestaetigen") | 1,5 |
| Absender passt zu Vorsatz/Familie/Behoerde (Liste `VORSATZ`) | 1,0 |
| Frist-Bezug im Inhalt (`FRIST_BEGRiffe`) | 1,0 |
| Dringlichkeit im Text (dringend/sofort/heute/wichtig) | 1,0 |
| Newsletter / Werbung / Automatik-Absender (`AUSSCHLUSS`) | −2,5 |

Gemeldet wird ab `--grenze` (Vorgabe 1,0). Fuer „Antwort heute noetig" als
harter Massstab `--grenze 2.0` setzen.

## Fallen, alle am 04.10.2026 gemessen

1. **`BODY.PEEK[TEXT]` ist bei multipart-Mails unbrauchbar.** Es liefert den
   rohen MIME-Block, der Body bleibt `=E2=82=AC`. Immer `BODY.PEEK[]` holen und
   ueber `email.message_from_bytes` + `_text()` gehen.
2. **HTML-Rumpf erzeugt Punkte fuer Nichts.** Ein Wort 'Antwort' irgendwo in
   tausend Zeichen Layout liess eine Zahlungsbestaetigung als „erwartet
   Antwort" durchlaufen. `_text()` macht Tags zu Text, schneidet ab der
   Fussnote (font-size 10/11px) ab und wirft Zeilen ohne Buchstabenquote raus.
3. **Der Absender gehoert in den Behoerden-Filter, nicht der Koerper.** Sonst
   wurde `failed-payments@mail.anthropic.com` zur Behoerde, weil im Text 'Bank'
   stand. `VORSATZ` nur gegen den Absender laufen lassen.
4. **Ein Automatik-Absender darf die Antwortpunkte nicht behalten.** Die
   Minderung traegt vor der positiven Bewertung - sonst gewinnt eine
   Bestaetigungsmail mit einem Fussnoten-'Antwort'.
5. **`--alle` zum Gegenlesen**, nie zum Melden: es zeigt, was die Treppe
   verworfen hat und mit welcher Begruendung. Erst wenn dort ein
   Fehlalarm steht, ist der Filter falsch und nicht die Post.
6. **Leere Ausgabe beweist nicht, dass die Quelle lebt** (gemessen 05.10.2026).
   Der letzte Lauf meldete nichts; die Frage war 'keine Post' oder 'Zugang tot'.
   Gegenprobe mit einer eigenen IMAP-Sonde: `LOGIN` OK melden,
   `post gesamt` aus `SEARCH ALL`, und die KOPFzeilen der fuenf juengsten
   Nachrichten - **aber erst nach `SELECT`**. `SEARCH` im Zustand `AUTH` wirft
   `imaplib.IMAP4.error: command SEARCH illegal in state AUTH, only allowed in
   states SELECTED` (Reihenfolge in der Sonde: LOGIN -> LIST -> SELECT -> SEARCH).
   Standort-Anker der Merkdatei: der Betrieb haengt seit T-375 (07.10.2026) an
   `zuletzt_uid`, NICHT an `zuletzt_gelesen_bis` - letzteres ist nur der
   Rueckfallpfad fuer den ersten Lauf. `zuletzt_lauf` in UTC gegen das
   Datum der juengsten Mail halten; erst daraus folgt 'wirklich nichts neu'.
   `SEARCH ALL` liefert SEQUENZnummern, `UID SEARCH` UIDs - die beiden
   Nummernfolgen nicht verwechseln (hoechste Sequenz 1943, UID 13391 sind
   im selben Postfach beides normal).
   **Ein unveraendertes `zuletzt_lauf` ist KEIN Fehlschlag** (gemessen
   19.10.2026): der Schreibblock steht unter `... and kandidaten:` - ohne
   Treffer bleibt die Merkdatei absichtlich stehen, inklusive `zuletzt_lauf`.
   Der Beweis fuer 'nichts neu' ist deshalb die Gleichheit von `zuletzt_uid`
   und der hoechsten UID aus `UID SEARCH ALL`, nicht der Zeitstempel.

7. **Die Antwort-Muster sind deutsch; englische Fragen fallen durch** (gemessen
   12.10.2026): "A quick question from Denis at DEBYKO" scorte 0,0 und blieb
   stumm, weil `muster_antwort` nur (frage|antwort|bitte melden|...) kannte.
   Englische Muster (\b(quick\s+)?question\b, \bwhat\s+(were|are|do|did|would)\s+you\b,
   \bthoughts|input|feedback\b, \basking\b, \bcurious\b) sind jetzt ergaenzt.
   Gegenprobe beim Gegenlesen: eine englische Frage, eine Werbemail mit
   englischer Frage (muss negativ bleiben - die AUSSCHLUSS-Minderung traegt),
   eine no-reply-Bestaetigung (netto 0,0).

8. **Dienst-Automatik-Absender ohne no-reply im Namen fallen durch** (gemessen
   12.10.2026): service@paypal.de traegt kein no-reply/notification, also gab
   der Footer "bitte antworten sie nicht auf diese e-mail" 1,5 Antwortpunkte
   und "kann sofort genutzt werden" 1,0 Dringlichkeit - zwei
   PayPal-Zahlungsbestaetigungen (Ueberweisung, 10-EUR-Einzahlung) wurden als
   "erwartet Antwort" gemeldet. Fix: `@paypal\.(de|com)` in den AUSSCHLUSS
   automatisierte_benachrichtigung, danach -1,0/0,0 (stumm). Gegenprobe: eine
   echte englische Frage (DEBYKO, 1.5) bleibt positiv.

9. **`--alle --fenster-erzwingen` (Gegenlesen) ueberschreibt die Merkdatei
   und verliert den UID-Anker** (gemessen 12.10.2026): der Schreibblock schrieb
   auch beim Gegenlesen, und `zuletzt_uid` wurde nur geschrieben, wenn
   `newest_uid > zuletzt_uid` - beim Wiederlesen derselben Mails sind sie
   gleich, also fiel zuletzt_uid weg und der naechste Betriebslauf haette das
   ganze 26h-Fenster erneut gemeldet (Doppelmeldung). Fix: Schreibblock
   bedingt `not args.fenster_erzwingen`. Gegenprobe: Gegenlesen laufen lassen
   und Merkdatei vorher/nachher vergleichen - sie muss unveraendert sein.

## Gehoert NICHT gemeldet

Newsletter, Werbung, Bank-/OpenAI-/Anthropic-Bestaetigungen, Reiseplanaenderungen
ohne eigene Handlung. Ein fehlgeschlagener Abo-Zahlvorgang ist eine Zahlungs-
sache fuer Max selbst, keine Mail mit Fristbezug - er kommt nur durch, wenn
Max ihn ausdruecklich zur Treppe gezaehlt haben will (dann eigene Zeile in
`VORSATZ` oder eigene Bedingung, nicht die Schwelle senken).
