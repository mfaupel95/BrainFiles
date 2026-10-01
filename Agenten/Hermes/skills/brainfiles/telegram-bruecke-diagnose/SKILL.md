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
  aus `_aufgabe_abholen` (9+6+1), ~230 Zeichen = der A2A-Zeitlimit-Text.
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
