---
name: telegram-bruecke-diagnose
category: brainfiles
description: Use when ein Telegram-Bot nicht geantwortet hat.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Diagnose, Telegram, Bruecke, SkillsBot, Belege]
    related_skills: [a2a-telegram-skills, stille-ausfaelle-eingrenzen, wirkung-nachweisen]
---

# Telegram-Bruecke: "hat nicht funktioniert" eingrenzen

## When to Use

- der Nutzer sagt, ein Befehl im SkillsBot/Handelsbot habe nichts getan
- eine Bot-Antwort ist nicht angekommen, obwohl der Prozess laeuft
- ein Befehl liefert nach ~5 Minuten nur einen Stummel statt einer Antwort
- bevor "der Bot ist kaputt" gemeldet oder der Task neu gestartet wird

Wenn der Nutzer sagt, ein Befehl im SkillsBot/Handelsbot habe nichts getan oder
eine Antwort sei nicht angekommen. Zwei Grundsaetze vor jeder Aussage:

1. **Das Bruecken-Log beweist die WEITERGABE, nicht die Ankunft.**
2. **Die Wege durch die Bruecke haben verschiedene Fristen** — der falsche Weg
   sieht wie ein Ausfall aus und ist keiner.

Der Aufbau der Bruecke selbst (Token, A2A-Wiring, Task-Registrierung) steht in
`a2a-telegram-skills`; dieser Skill ist die Diagnose.

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

## End-to-End-Beweis, bevor "repariert" gemeldet wird

Nach der Aenderung den WEG fahren, den der Nutzer am Handy nimmt - nicht
nur die Funktion, die man geaendert hat:

1. Ziel setzen: `_ziel_setzen(chat, "openmontage")`
2. Freitext: `bearbeite("Antworte nur mit PONG", chat)`
3. Die Antwort muss **vom Bot** kommen, nicht vom Hauptagenten, und das
   Ziel muss danach `None` sein (ein Auftrag je Bot).

**Merksatz: ein Beweis an der geaenderten Funktion ist kein Beweis fuer den
Weg.** "Die Funktion tut es" und "der Nutzer sieht es" sind zwei Aussagen;
nur der zweite Weg belegt die zweite.
