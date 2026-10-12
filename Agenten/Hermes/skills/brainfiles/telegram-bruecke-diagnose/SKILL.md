---
name: telegram-bruecke-diagnose
category: brainfiles
description: Use when ein Telegram-Bot nicht geantwortet hat.
version: 0.2.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Diagnose, Telegram, Bruecke, SkillsBot, Belege, Gateway, Adapter]
    related_skills: [a2a-telegram-skills, stille-ausfaelle-eingrenzen, wirkung-nachweisen, hermes-maintenance]
---

# Telegram-Bruecke: "hat nicht funktioniert" eingrenzen

Diagnose einer Telegram-Anbindung, die schweigt: Gateway-Plattform,
Multiplex-Profil und SkillsBot-Bruecke. Dieser Skill **behandelt keinen
Verdrahtungsfehler** (Token, A2A-Wiring, Task-Registrierung — das ist
`a2a-telegram-skills`) und **repariert keinen Upstream-Bug**; er trennt die drei
moeglichen Befunde, benennt den belegten Ausfallbild und fuehrt den Weg, den
der Nutzer am Handy nimmt. Alle Befunde und Werkzeuge sind stdlib-only.

## When to Use

- der Nutzer sagt, ein Befehl im SkillsBot/Handelsbot habe nichts getan
- eine Bot-Antwort ist nicht angekommen, obwohl der Prozess laeuft
- ein Befehl liefert nach ~5 Minuten nur einen Stummel statt einer Antwort
- der Gateway-Status zeigt eine Plattform `retrying` mit `needs_attention`
- bevor "der Bot ist kaputt" gemeldet oder der Task neu gestartet wird

Wenn der Nutzer sagt, ein Befehl im SkillsBot/Handelsbot habe nichts getan oder
eine Antwort sei nicht angekommen. Zwei Grundsaetze vor jeder Aussage:

1. **Das Bruecken-Log beweist die WEITERGABE, nicht die Ankunft.**
2. **Die Wege durch die Bruecke haben verschiedene Fristen** — der falsche Weg
   sieht wie ein Ausfall aus und ist keiner.

Der Aufbau der Bruecke selbst (Token, A2A-Wiring, Task-Registrierung) steht in
`a2a-telegram-skills`; dieser Skill ist die Diagnose.

## Prerequisites

- `HERMES_HOME` gesetzt, darin `gateway_state.json` und `logs/gateway.log`.
- Fuer den SkillsBot: `Agenten/Bus/skillsbot.offset` und `skillsbot.log`.
- Nur lesende Diagnose. Ein Tokenwert wird **nie** ausgegeben — Laenge und
  Existenz genuegen, und Laengen misst man ueber
  `[Environment]::GetEnvironmentVariable($k,'User').Length` bzw. die `.env`,
  nie ueber `reg query` (das gibt Klartext ins Protokoll).

## How to Run

Alles ueber das `terminal`-Werkzeug. Der Einstieg ist ein Skript, kein
Zustandsabfragen-Baukasten:

    cd "<HERMES_HOME>/skills/brainfiles/telegram-bruecke-diagnose"
    python scripts/telegram_status.py --home "<HERMES_HOME>" --bus "<...>/Agenten/Bus"

Exit 0 = jede Anbindung meldet `connected`. Exit 1 = mindestens eine nicht. Der
Aufruf liest nur; er repariert nichts und loest nichts aus.

## Quick Reference

    <HERMES_HOME>/gateway_state.json                      # platforms.telegram.state/error_code
    <HERMES_HOME>/logs/gateway.log                         # nur Logende lesen
    <HERMES_HOME>/skills/brainfiles/telegram-bruecke-diagnose/scripts/telegram_status.py
    <...>/Agenten/Bus/skillsbot.offset                     # Lebenszeichen = mtime
    <...>/Agenten/Bus/skillsbot.log                        # JSONL je Nachricht
    Get-ScheduledTask | Where-Object { $_.TaskName -like 'Hermes_Gateway*' }
    schtasks /run /tn Hermes_Gateway_<suffix>
    Stop-ScheduledTask  -TaskName 'BrainFiles-SkillsBot'
    Start-ScheduledTask -TaskName 'BrainFiles-SkillsBot'
    [Environment]::GetEnvironmentVariable('TELEGRAM_BOT_TOKEN','User').Length

## Die Logzeile lesen (`Agenten/Bus/skillsbot.log`)

JSONL je Nachricht: `zeit, chat, kommando, dauer_s, status, zeichen`.

- **`status: ok` heisst: VERARBEITET, nicht zugestellt.** Der Eintrag entsteht
  nach `bearbeite()`, vor bzw. unabhaengig von `sende()`. Ein echter
  Telegram-Fehler steht als `status: fehler` mit `fehler`-Feld - aber ein
  fehlender `sende()`-Aufruf ist in diesem Log **unsichtbar**: nichts wird
  protokolliert, nichts gesendet, der Nutzer sieht nichts. "Nichts
  angekommen" bei `status: ok` ist deshalb entweder ein fehlender
  `sende()`-Aufruf oder ein Empfaengerproblem - das Log kann das nicht
  unterscheiden, nur der End-to-End-Beweis unten.
- **`dauer_s` verraet den Weg:** <5 s = Kurzbefehl (`handel_befehle` ->
  `Handel/befehle.py`), ~300 s = Freitext ueber A2A (`A2A_TIMEOUT_S`).
- **`zeichen` ist die LAENGE der Antwort** - damit laesst sich die Antwort
  identifizieren, ohne sie zu speichern: **16 Zeichen = `(Aufgabe FAILED)`**
  aus `_aufgabe_abholen` (9+6+1), ~230 Zeichen = der A2A-Zeitlimit-Text,
  **~207 Zeichen = "Kein SkillsBot-Befehl. /hilfe zeigt die Liste."** - die
  Nachricht war ein Slash-Befehl, den der Bot NICHT kennt.
- **Lebt der Poller?** `skillsbot.offset` wird bei jedem Umlauf fortgeschrieben
  (Dateizeit = Lebenszeichen). Der INHALT ist die Telegram-`update_id`, keine
  Uhrzeit - nicht als Zeitstempel lesen.

## Wege und Fristen - nicht verwechseln

| Weg | Frist | wofuer |
|---|---|---|
| `/befehl` (Slash) | Sekunden | lesende Auskuenfte: `/lage /live /strategien /bericht /spuren /spur /markt` |
| `/run NAME [Auftrag]` | `A2A_FRIST_S` 1800 s | einen Skill AUSFUEHREN |
| Freitext (kein Slash) | `A2A_FRIST_S` 1800 s | freier Auftrag; gleiche Frist wie `/run`, gleiche Arbeit |
| Freitext mit aktiver Bot-Zuweisung | `BOT_FRIST_S` 1800 s | geht an den Bot (siehe unten), nicht an den Hauptagenten |
| `/bot NAME NACHRICHT` | `BOT_FRIST_S` 1800 s | Frage an einen Repo-Bot |

Die Fristen stehen als `A2A_FRIST_S`/`BOT_FRIST_S` in `skillsbot.py` - beim
Aendern dort den Wert lesen, nicht diese Tabelle.

**Regel: nie einem Nutzer einen SATZ zum Abschicken nennen, wenn Arbeit gemeint
ist.** Genau das schickt ihn in das kurze Limit, und er sieht nach fuenf Minuten
eine 16-Zeichen-Antwort - das liest sich wie ein kaputter Bot. Statt dessen den
Slash-Befehl mit der tragenden Frist nennen ODER die Arbeit selbst machen. Die
Grenze des Weges VORHER nachsehen, nicht nach dem Ausfall.

## Nachricht kam nicht an: Bilduntertitel, Medien, verlorene Updates

**Der wahrscheinlichste Ausfall mit dem saubersten Log: die Nachricht wurde
nie verarbeitet.** Ein `continue` vor dem `_log`-Aufruf ist unsichtbar — der
Poller laeuft, `/bots` antwortet, das Protokoll wirkt ruhig. Bevor „der
Agent hat nicht geantwortet" gesagt wird, ist die Frage **„ist die Nachricht
ueberhaupt angekommen"** — und das steht nur an EINER Stelle feststellbar.

**Telegram schickt den Text von Medien in `message.caption`, nicht in
`message.text`.** Ein Foto mit Unterschrift hat `text = None` und
`caption = "/bot openmontage ..."`. Eine Schleife, die nur `.get("text")`
liest, verwirft genau diese Nachrichten. Das ist bei diesem Nutzer der
Normalfall, nicht die Ausnahme: am Handy wird ein Auftrag mit einem Bild
geschickt. Regel fuer jede Nachrichtenverarbeitung:
`text = msg.get("text") or msg.get("caption") or ""`.

### Den verlorenen Auftrag wiederfinden (Diagnose, kein Umbau)

Der gespeicherte Offset in `skillsbot.offset` ist die Telegram-`update_id`
des letzten VERARBEITETEN Updates. Alles davor ist fuer Telegram
weggerollt — der Bot kann es nicht mehr sehen, der Nutzer aber durchaus
noch. Die Nachrichten selbst sind mit dem Bot-Token abrufbar, solange
niemand den Offset darueber gesetzt hat:

```python
off = json.load(open("Agenten/Bus/skillsbot.offset"))
# Update-Ids >= off kommen zurueck, mit timeout:0 (kein Warten)
post("getUpdates", {"offset": off, "timeout": 0})
```

Je Update `message.caption` **und** `message.photo` ausgeben — ein
verworfener Auftrag ist an der nichtleeren `caption` erkennbar, ein Bild
an mehreren `photo`-Eintraegen. **Das ist ein Diagnosewerkzeug: den
gefundenen Auftrag dem Nutzer bestaetigen und den Weg selbst fahren, nicht
den Offset zuruecksetzen und den Bot alte Nachrichten nachholen lassen**
(nur das ist sinnvoll, wenn der Bot nach dem Fix genau einmal live geprueft
werden soll: `skillsbot.offset` auf die `update_id` zuruecksetzen, Bot
neu starten, Log und Ablage lesen).

### Medien: was Telegram wirklich liefert

- **Eine `photo`-Liste enthaelt 4-5 Stufen DESSELBEN Bildes** (thumb,
  klein, mittel, gross), nicht mehrere Bilder. Die Auswahl lautet
  `max(photo, key=file_size)`. Wer alle nimmt, laedt dieselbe Datei
  fuenfmal und meldet sie als fuenf Bilder — beim Auftrag „Muster im 2.
  Bild" ist Bild 2 dann eine winzige Vorschau.
- **Ein Auftrag mit Bildverweis kommt als mehrere Nachrichten** („Muster im
  2. Bild, Boden im 1. Bild"). Die Ablage ist darum ein rollierendes
  FENSTER je Chat (`bild1`, `bild2`, …), kein Ordner je Nachricht — sonst
  loescht das Eintreffen von Bild 2 genau Bild 1. Beim Antworten die Bilder
  in Sendereihenfolge nummerieren.
- **Der Agent muss den PFAD sehen, nicht die Bytezahl.** Die Pfade an den
  Auftrag haengen und ausdruecklich auffordern, die Datei mit dem
  vision/image-Werkzeug zu lesen.
- **Ein Ladefehler darf nie eine leere Liste ergeben**, sondern
  `(pfad, grund)`: halb geschriebene Datei loeschen, Grund mit eigenem
  Log-Status protokollieren. Sonst gilt ein fehlgeschlagener Abruf als
  „Bot kann keine Bilder" und der Auftrag laeuft still ohne Bild.

### Zwei Fallen, die als „Bild kam nicht" aussehen

1. **Der HTTP-Wrapper gibt das API-`result` bereits entpackt zurueck.**
   Ein darueber gesetztes `.get("result")` ergibt `{}` — kein Netzproblem,
   sondern ein leeres Dict, das als fehlender Pfad durchlaeuft. Der
   Datei-Download geht ueber `https://api.telegram.org/file/bot<token>/<pfad>`,
   nicht ueber `/bot<token>/` (404).
2. **Die Testattrappe muss die Form liefern, die der Wrapper wirklich
   zurueckgibt.** Eine Attrappe mit `{"result": {...}` gegen einen Wrapper,
   der schon entpackt, bestaetigt den falschen Vertrag gruen — genau so
   bleibt der echte Fehler unentdeckt. **Netzpfade laufen im Test immer
   gegen Attrappen, nie gegen Telegram**; der Live-Beweis ist eine echte
   Datei in der Ablage nach einem Prozessneustart.

**Nach jeder Codeaenderung am Bot: Prozess neu starten, dann den
LOGENDZEITPUNKT lesen.** Ein alter Prozess verarbeitet die Regel nicht, und
der Befund „wirkt nicht" ist dann eine Falschmeldung ueber den alten Code.

## 207 Zeichen: erst die SCHREIBWEISE pruefen, dann den Bot

Der Bot kennt Befehlsnamen WOERTLICH; es gibt keine unscharfe Suche. Die
Hausbefehle sind mehrzahlig (`/strategien`, `/indikatoren`), am Handy getippt
wird die Einzahl - `/strategie` bekommt 207 Zeichen, waehrend `/strategien`
denselben Bericht in Sekunden liefert. Das ist Bedienung, kein Ausfall.

- **Vor jedem "der Bot kann X nicht" die Namensliste nachsehen**
  (`Agenten/Bus/skillsbot.py`, `_handelsantwort`) und den Namen aus dem
  Protokoll damit vergleichen - der Log zeigt `kommando` wortwoertlich.
- **Fix ist ein Alias, nicht eine Belehrung:** Schreibweisen an EINER Stelle
  buendeln (`HANDELS_ALIASE` in `skillsbot.py`), der kanonische Name bleibt bei
  `handel_befehle`/`Handel/befehle.py`. Danach ist die Einzahl derselbe Befehl -
  ein anderer Name darf keine Auskunft kosten. Test: jeder Alias zeigt auf
  einen Befehl, den `_handelsantwort` wirklich kennt, und ein unbekanntes Wort
  bleibt unbekannt (sonst wird jeder Tippfehler still ein Befehl).

## Nach jeder Code-Aenderung an der Bruecke

Die Module (`skillsbot.py`, `handel_befehle.py`, `Handel/befehle.py`,
`skillkatalog.py`) liegen im laufenden `pythonw`-Prozess im Speicher. Ohne
Neustart des Tasks ist die Aenderung unsichtbar und die naechste Meldung lautet
faelschlich "wirkt nicht":

    Stop-ScheduledTask  -TaskName 'BrainFiles-SkillsBot'
    Start-ScheduledTask -TaskName 'BrainFiles-SkillsBot'
    Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" |
      Where-Object { $_.CommandLine -match 'skillsbot.py' } |
      Select-Object ProcessId,CreationDate

Beleg ist die neue PID mit frischer Startzeit. **Und die Antwortlaenge messen:**
`MAX_ZEICHEN` ist 4000, ein Zusatz je Zeile summiert sich ueber ~40 Spuren -
`len(befehle.strategien())` aufrufen, statt sich auf "passt schon" zu verlassen.

## Falle

- Nicht "der Bot ist kaputt" melden, ohne Prozess (pythonw + `skillsbot.py` in
  der CommandLine), Task-State und Port 8787 geprueft zu haben.
- Der Fehler kann auf der EIGENEN Seite liegen: ein genannter Weg, der die
  Arbeit nicht tragen kann. Das zuerst ausschliessen, dann den Bot verdaechtigen.

## Zwei Fehler, die zusammen wie "der Bot antwortet nicht" aussehen

Beide bleiben im Log unter `status: ok` unsichtbar. Vor "der Bot ist
kaputt" immer beide pruefen:

1. **Eine Syntaxhilfe verlegt den Auftrag auf den falschen Adressaten.**
   `/bot NAME` ohne Text antwortete mit "Was soll ich Bot X fragen? Syntax:
   /bot NAME NACHRICHT" (71 Zeichen im Log). Der danach gesendete Auftrag -
   am Handy meist ein **Bild als eigene Nachricht** - ging an den
   Hauptagenten, der Bot bekam ihn nie.

   **Regel: immer pruefen, wohin die *naechste* Nachricht geht, nicht nur,
   ob die aktuelle eine Antwort bekam.** Ein Weg, der eine Frage stellt
   statt den Auftrag anzunehmen, ist kein Defekt, aber er sieht aus wie
   einer. Der Nutzer sendet daraufhin an den anderen Adressaten.

   **Abhilfe: `/bot NAME` ohne Auftrag schaltet den Bot als Adressaten
   ein** (Zustand in `ZIEL_PFAD`, eine Datei je Chat, `ZIEL_FRIST_S`
   Minuten). Der naechste Freitext - mit oder ohne Bild - nimmt ihn und wird
   danach abgeschaltet, damit nichts im falschen Bot landet. `/bot aus`
   schaltet ab, ein abgelaufenes Ziel gilt als keins, ein geloeschtes Profil
   ebenfalls.

2. **Ein fehlender `sende()`-Aufruf in der Poll-Schleife.** Die Antwort
   wurde verarbeitet, protokolliert und der Offset gespeichert - aber nie
   an Telegram geschickt. Das Log meldet `status: ok`, weil die
   Verarbeitung erfolgreich war.

   **Regel: ein Test, der die Schleife end-to-end fahren und die
   *gesendeten* Nachrichten zaehlen muss, findet einen fehlenden
   `sende()`.** Ein Test auf Protokoll und Offset findet ihn nicht. Form:
   die Attrappe sammelt `sende(chat, text)` in eine Liste, nach dem Lauf
   wird die Liste verglichen - nicht der Log.

## Test gegen den echten Subprozess: `run` ist nicht `Popen`

`_bot_fragen` nutzt `subprocess.Popen` + `communicate`, damit der
Frist-Abbruch den Bot nicht mitten in der Arbeit toetet (`run(timeout=)`
wuerde genau das). Tests, die `subprocess.run` mocken, treffen damit
**nichts** und starteten einen ECHTEN Bot.

**Regel: der Test mockt die Aufrufform, die im Code steht.** Ein
Run-Mock auf einem Popen-Code sieht aus wie ein Test und ist keiner - die
Assertion schlaegt mit der echten Bot-Antwort fehl, die Suite braucht
Minuten. Die Popen-Attrappe liefert ein Objekt mit `communicate()`,
`returncode` und `kill()`; fuer den Abbruchpfad wirft `communicate`
`TimeoutExpired`.

## Alle drei Anbindungen in einem Durchgang pruefen

"Telegram antwortet nicht" ist auf diesem Rechner **drei** Befunde mit einem
Symptom. Der Gateway-Bot, der Multiplexer-Eintrag `bots:telegram` und die
SkillsBot-Bruecke unter `Agenten/Bus` laufen als getrennte Prozesse - ein
Neustart des einen heilt die anderen nicht, und ein Fehlen in der Statusdatei
beweist nichts ueber die anderen.

Einstieg: ueber das `terminal`-Werkzeug

    python scripts/telegram_status.py --home "<HERMES_HOME>" --bus "<...>/Agenten/Bus"

Exit 0 = mindestens eine Anbindung lebt. Das Skript liest `gateway_state.json`,
sucht die vier entscheidenden Logzeilen (nur das Logende) und misst das
Lebenszeichen `skillsbot.offset`. Es gibt **niemals** einen Tokenwert aus, nur
Existenz und Laenge - Tokenabfragen laufen ueber `[Environment]::GetEnvironmentVariable`-
Laenge, nie ueber `reg query` (das gibt Klartext aus).

Der Mehrwert liegt im Zeitvergleich, den das Skript ausdruecklich ausweist:

    missing   2026-10-05 03:36:56,898  'No adapter available for telegram'
    connected 2026-10-05 06:55:44,030  '✓ telegram connected'

Ohne Uhrzeiten sieht man nur zwei Zeilen und haelt sie fuer einen Widerspruch.

## Ausfallbild: der Gateway startet OHNE Adapter (Zustand, nicht Datei)

Der haeufigste Befund bei "Telegram antwortet nicht" ist **kein** Netz-, Token-
 oder Paketproblem, sondern ein Prozess, der beim Start den Adapter nicht gebaut
hat. `gateway_state.json` zeigt dann:

    "telegram": {"state": "retrying", "error_code": "adapter_unavailable",
                 "error_message": "No adapter available for enabled telegram;
                  check the plugin, dependencies, and credentials.",
                 "needs_attention": true}

`logs/gateway.log` dazu, ab dem ERSTEN Auftreten:

    WARNING gateway.run: No adapter available for telegram
    INFO    gateway.run: Reconnecting telegram (attempt 1)...
    INFO    gateway.run: Reconnect telegram: no adapter yet, next retry in 300s
    WARNING gateway.run: telegram has been failing/reconnecting continuously for 2.0 hours (26 attempts)

`gateway/run_startup.py:1213-1234` ist die Quelle: `_create_adapter` lieferte
`None`, der Plattform wird `error_code=adapter_unavailable` geschrieben, und der
Reconnect-Watcher versucht es alle 300 s weiter - **ohne** den Prozesszustand zu
reparieren. Die Schleife heilt nichts; sie sieht nur aktiv aus.

Der komplette Befund dieser Klasse mit allen vier widerlegten Hypothesen
(Paket, Credentials, Plugins, Rechner), dem Quelltext, der Reihenfolge der
Belege und der End-to-End-Zustellung liegt in
`references/gateway-adapter-ausfall-0510.md` (laden mit
`skill_view(name='telegram-bruecke-diagnose', file_path='references/gateway-adapter-ausfall-0510.md')`).

### Die drei Fehlalarme, die man NICHT mitbringen darf

1. **"Das Paket fehlt."** Nicht aus dem Dateisystem schliessen. Der Gateway laeuft
   aus `<HERMES_HOME>/tools/python-3.14.7…/python.exe`, dessen `site-packages` nur
   `pip` enthaelt; die Fremdpakete kommen ueber `hermes_bootstrap` ->
   `pm/environments.py::activate_dependencies` aus dem gestagten Umfeld
   `<HERMES_HOME>/installs/<hash>/environments/<id>/venv/Lib/site-packages`. Eine
   leere Paketliste ist **kein** Befund. Gemessen: Paket da (Import-Probe
   `import telegram` gruen), Adapter trotzdem `None`.
2. **"Die Credentials sind falsch."** Der Token liegt in `.env` (46 Zeichen
   vorhanden), ein User-Store-Eintrag fehlt dafuer - richtig und harmlos. Ein
   credential-fehler zeigt sich als `failed to connect` mit Telegram-HTTP-Fehler,
   **nicht** als `adapter_unavailable`.
3. **"Die Plugins sind nicht geladen."** Der Startpfad ruft
   `discover_plugins()` (`run_startup.py:1061-1064`) korrekt auf. Eine Probe, die
   `discover_plugins()` + `platform_registry` von Hand nachstellt, registriert
   `telegram` fehlerfrei und `check_fn`/`ensure_deps_fn` liefern beide `True`.

### Der heilende Neustart, richtig gefahren

Ein Neustart heilt diesen Zustand. Er wird aber zum zweiten Fehler, wenn man ihn
falsch macht:

- **Nie ueber Port 9900 auf "laeuft" testen.** Der frisch gestartete Gateway
  braucht ~5 Minuten, bis er hochgefahren ist; 9900 und `curl` liefern dann
  `000`. Wer in diesem Fenster erneut startet, legt eine **zweite** Instanz an.
- **Genau einen Prozess beenden, nicht die Kommandozeile filtern.** `stop` auf die
  PID aus `gateway_state.json`, danach per `schtasks /run /tn Hermes_Gateway_<suffix>`
  starten (Suffix ueber
  `Get-ScheduledTask | Where-Object { $_.TaskName -like 'Hermes_Gateway*' }` - der
  Task-Name aendert sich mit dem Update).
- **Startzeit als Beleg**, nicht die Erfolgsmeldung: `gateway_state.json` mit neuer
  `pid` und frischem `updated_at`.
- **Der Erfolg ist die `✓ telegram connected`-Zeile im Log**, zusammen mit
  `[Telegram] Telegram polling confirmed healthy: getUpdates progressing (generation 1)`.
  Beides zusammen heisst: Adapter gebaut UND der Kanal pollt wirklich.

Nebenbefund beim selben Neustart: `lifecycle_ledger` meldet die alte Lebensphase
als `exited UNCLEANLY (… a pkill/taskkill of the host interpreter image)` - das
ist die **eigene** Beendigung, kein unabhaengiger Crash, und wird nicht als
zweiter Befund gefuehrt.

### Was ich dabei NICHT gefunden habe (offen und so benannt)

Der Grund, warum `_create_adapter` im laufenden Prozess `None` lieferte, obwohl
Paket, `check_fn` und Plugin-Registrierung gruen waren, ist **nicht** belegt. Eine
Probe mit exakt dem Bootstrap-Weg liefert den Adapter korrekt. Das gehoert als
offenes Feld weiter, nicht in eine Erklaerung, die man sich aus dem Fehlerbild
zusammenreimt - wer das Baums anfasst, muss den Zustands IM Gateway-Prozess
messen, nicht eine Attrappe daneben.

## Zwei Abgrenzungen, die man explizit zieht

- **Ein Fehlalarm im Log bleibt ein Fehlalarm.** `telemetry/shared_metrics/outbox`
  wirft `FileExistsError: [WinError 183]` im Sekundentakt (`exist_ok=True` gegen
  ein als **Datei** existierendes Verzeichnis). Das ist beobachtbar, hat aber mit
  keinem Plattform-Adapter zu tun - die Zeilen wuerden das Bild sonst verfaelschen.
- **Ein Symptom, das man nicht reproduzieren kann, wird nicht repariert.** Wenn
  alle drei Anbindungen `connected` melden und der Nutzer nichts bekommt, ist der
  Weg zu fahren (siehe Ende), nicht eine dritte Bereinigung zu erfinden.

## End-to-End-Beweis, bevor "repariert" gemeldet wird

Nach der Aenderung den WEG fahren, den der Nutzer am Handy nimmt - nicht
nur die Funktion, die man geaendert hat:

1. Ziel setzen: `_ziel_setzen(chat, "openmontage")`
2. Freitext: `bearbeite("Antworte nur mit PONG", chat)`
3. Die Antwort muss **vom Bot** kommen, nicht vom Hauptagenten, und das
   Ziel muss danach `None` sein (ein Auftrag je Bot).

**Merksatz: ein Beweis an der geaenderten Funktion ist kein Beweis fuer den
Weg.** "Die Funktion tut es" und "Der Nutzer sieht es" sind zwei Aussagen;
nur der zweite Weg belegt die zweite.

Fuer den **Gateway-Kanal** ist dieser Weg eine echte Zustellung ueber genau den
Sender, den der Dienst benutzt - nicht die eigene Testfunktion. Token nur aus der
`.env` lesen, nie ausgeben. Beleg ist die Antwort des Senders, nicht ein
`status: connected`:

    {'success': True, 'platform': 'telegram', 'chat_id': '…', 'message_id': '10888'}

Gemessen am 05.10.2026: `message_id 10888` nach dem Neustart bei
`code_version 0.21.5`. Der Tokenwert wird dabei **nie** ausgegeben - nur seine
Laenge, sonst landet er im Sitzungsprotokoll.

Der vollstaendige Ausfallbild-Beleg steht in
`references/gateway-adapter-ausfall-0510.md` (laden mit
`skill_view(name='telegram-bruecke-diagnose', file_path='references/gateway-adapter-ausfall-0510.md')`);
die **ueber** den Einzelfall hinausgehenden Regeln — Aggregation, Gegenlauf-Pfad,
Schleife-als-Aktivitaet, Belegpflicht fuer Erklaerungen — stehen in
`messwerkzeug-gegenprobe` und `trugschluesse`.

## Mention-Pflicht je Profil-Bot: `TELEGRAM_REQUIRE_MENTION` (Stand 11.10.2026)

In der Gruppe `-1003980261765` teilen sich mehrere Bot-Profile einen Chat. Der
Verteiler-Bot (Mikesch = `profiles/bots`, `@Maximilian420_bot`) nimmt `/bot NAME`
an und verteilt an Fachbots; deshalb antwortet **nur er** ohne @-Mention, alle
anderen Profil-Bots nur auf explizite Erwähnung.

- **`true` gesetzt (seit 11.10.2026, 14:16–16:26):** `auto-prediction`,
  `fomo-radar`, `nerd`, `recherche`, `kraken-cli`, `hermes-wartung` — in
  `profiles/<name>/.env`. recherche trägt zusätzlich
  `TELEGRAM_OBSERVE_UNMENTIONED_GROUP_MESSAGES=true`.
- **`false` (kein Schlüssel):** `profiles/bots/.env` — der Verteiler bleibt ohne
  Mention-Pflicht.

**Warum `bots` das globale `true` NICHT erbt (Beleg):** Die Env-Rung liest
profil-scoped über `get_scoped_secret` (`gateway/platforms/_shared.py:106`,
`extra_or_secret`); ein Scope-Miss fällt auf YAML-`extra` → Default `"false"`,
nie auf das globale `os.environ` (Multiplex-Regel, `gateway/AGENTS.md`). Das
bots-Profil läuft im selben Multiplex-Gateway (PID 89684, `multiplex_profiles:
true`), liest aber nur `profiles/bots/.env`. Empirisch: `TELEGRAM_ALLOWED_CHATS`
musste am 10.10. in **beide** `.env`-Dateien (global UND `profiles/bots/.env`),
weil das Profil das globale `.env` nicht erbt — derselbe Mechanismus gilt für
`TELEGRAM_REQUIRE_MENTION`.

## Verification

Ein Lauf beweist die ganze Diagnose:

    cd "<HERMES_HOME>/skills/brainfiles/telegram-bruecke-diagnose"
    python scripts/telegram_status.py --home "<HERMES_HOME>" --bus "<...>/Agenten/Bus"

Exit 0 **und** alle drei Zeilen `OK` **und** im Log `✓ telegram connected` mit
`getUpdates progressing` nach einer neueren Uhrzeit als das letzte
`No adapter available`. Das allein ist noch kein Weg-Beweis — `connected` ist ein
Zustandszeuge. Der Weg-Beweis ist eine echte Zustellung
(`{'success': True, … 'message_id': '…'}`) ueber den Sender, den der Dienst
selbst benutzt.

**Die Gegenprobe des Werkzeugs** (ohne sie ist Exit 0 ein unbekanntes Urteil):
eine Attrappe, in der **genau ein** Telegram-Eintrag `retrying` ist und alle
anderen `connected` — der Aufruf muss Exit 1 liefern und den toten Eintrag
**namentlich** nennen. Ein weiches „irgendwas lebt" faellt daran nicht durch.
