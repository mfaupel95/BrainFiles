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

- **`status: ok` heisst: gesendet.** `sende()` ruft Telegrams `sendMessage`
  DIREKT auf (nicht ueber den Bus). Ein Sendefehler steht als `status: fehler`
  mit `fehler`-Feld. "Nichts angekommen" bei `status: ok` ist ein
  Empfangsproblem auf dem Geraet - das sagen, statt den Bot neu zu starten.
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
| `/run NAME [Auftrag]` | `BOT_FRIST_S` 1800 s | einen Skill AUSFUEHREN |
| Freitext (kein Slash) | `A2A_TIMEOUT_S` 300 s | endet bei echter Arbeit als `(Aufgabe FAILED)` |

**Regel: nie einem Nutzer einen SATZ zum Abschicken nennen, wenn Arbeit gemeint
ist.** Genau das schickt ihn in das kurze Limit, und er sieht nach fuenf Minuten
eine 16-Zeichen-Antwort - das liest sich wie ein kaputter Bot. Statt dessen den
Slash-Befehl mit der tragenden Frist nennen ODER die Arbeit selbst machen. Die
Grenze des Weges VORHER nachsehen, nicht nach dem Ausfall.

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

## Zwei Fehler, die am 03.10.2026 zusammen "der Bot antwortet nicht" ergaben

Beide ueber `status: ok` im Log unsichtbar - der Bot SANDTE, nur nicht das
Richtige. Vor "der Bot ist kaputt" immer beide pruefen:

1. **`/bot NAME` ohne Auftrag kam beim Hauptagenten an.** `/bot NAME` ohne
   Text ergab eine Syntaxhilfe (71 Zeichen, `zeichen` im Log). Der danach
   gesendete Auftrag - am Handy meist ein **Bild als eigene Nachricht** -
   ging an den Hauptagenten. Der Bot war gesund (Port 9900 offen, A2A in
   10 s, `_bot_fragen` in 43 s PONG). **Abhilfe (Commit 92f2cd52):** `/bot
   NAME` schaltet den Bot als Adressaten ein (`ZIEL_PFAD`, 30 min), der
   naechste Freitext nimmt ihn und wird danach abgeschaltet, `/bot aus`
   schaltet ab. Der Zustand liegt in EINER Datei je Chat.

   **Merksatz: eine Syntaxhilfe ist kein Defekt, aber sie sieht aus wie
   einer.** Ein Weg, der eine Frage stellt statt sie anzunehmen, verlegt
   den Auftrag still auf den anderen Adressaten. Immer pruefen, wohin die
   *naechste* Nachricht geht, nicht nur, ob die aktuelle eine Antwort
   bekam.

2. **`sende()` fehlte in `schleife()`.** Die Antwort wurde `bearbeite()`-t,
   protokolliert und der Offset gespeichert - aber nie an Telegram
   geschickt. Das Log meldet `status: ok`, weil die Verarbeitung erfolgreich
   war. **Gefunden hat es der Test
   `test_netzfehler_nachricht_geht_nicht_verloren`:** er erwartete eine
   gesendete Antwort (`gesendet == [(7, "die antwort")]`) und bekam `[]`.

   **Merksatz: `status: ok` heisst "verarbeitet", nicht "zugestellt".** Ein
   Test, der die SCHLEIFE end-to-end fahren und die *gesendeten* Nachrichten
   zaehlen muss, findet einen fehlenden `sende()`; ein Test auf Protokoll
   und Offset findet ihn nicht.

## Test gegen den echten Subprozess: `run` ist nicht `Popen`

`_bot_fragen` nutzt `subprocess.Popen` + `communicate` (seit 21.09.2026,
damit der Frist-Abbruch den Bot nicht mitten in der Arbeit toetet). Tests,
die `subprocess.run` mocken, treffen damit **nichts** und starteten einen
ECHTEN Bot (Kaltstart 30-60 s je Test). Symptom: die Suite braucht
minuten und die Assertion schlaegt mit der echten Bot-Antwort fehl. Die
Attrappe ersetzt `Popen` und liefert ein Objekt mit `communicate()`,
`returncode` und `kill()`.

## Nach jeder Aenderung: Der Prozess haelt den alten Code

Der SkillsBot laeuft als `pythonw`-Dienst; ohne Neustart des Tasks ist die
Aenderung unsichtbar. Aber Vorsicht: `Stop-ScheduledTask` + `Start` ist der
belegte Weg, und die NEUE PID mit frischer Startzeit ist der Nachweis
(Anweisung aus `a2a-telegram-skills`). Beim End-to-End-Beweis danach die
echten Wege fahren: `_ziel_setzen(chat, "openmontage")`, dann
`bearbeite("Antworte nur mit PONG", chat)` - die Antwort muss vom Bot
kommen, nicht vom Hauptagenten.
