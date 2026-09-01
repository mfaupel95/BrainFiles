---
id: 20260830-werkzeuge
title: 'Werkzeuge'
tags: [mcp, betrieb]
created: 2026-08-28
updated: 2026-08-28
related: [20260830-verbindungen]
summary: 'Welche Werkzeuge tatsächlich abgerufen werden - gemessen an den bisherigen Sitzungen.'
---

# Werkzeuge

Was tatsächlich benutzt wird — gemessen, nicht vermutet. Gegenstück zu
[[Verbindungen]]: dort steht, was **erreichbar** ist, hier, was **abgerufen**
wird. Das ist nicht dasselbe.

**Warum:** Am 28.08.2026 zeigte die Auswertung der 53 gespeicherten Sitzungen,
dass nicht Werkzeuge fehlen, sondern Abrufwege. 32 Server sind eingetragen,
242 MCP-Aufrufe gab es insgesamt — drei Viertel davon an den Browser. Der
eigene Archivserver kam auf acht Aufrufe, während 462 Befehle Archivarbeit von
Hand erledigten.

**Stand:** 2026-08-28

Nachrechenbar mit:

```
.venv\Scripts\python.exe .claude\skills\rueckschau\sitzungen_auswerten.py --werkzeuge
```

## Nutzung, 53 Sitzungen

| Server | Aufrufe | Anteil |
|---|---|---|
| Claude_Browser | 120 | 49,6 % |
| claude-in-chrome | 61 | 25,2 % |
| windows-mcp | 11 | 4,5 % |
| revolut-x | 10 | 4,1 % |
| okx-agent-trade-kit | 10 | 4,1 % |
| archiv | 8 | 3,3 % |
| kraken | 3 | 1,2 % |
| mcp-memory, pdf-vault, filesystem, pdf-viewer | je 2 | je 0,8 % |
| desktop-commander, tooluniverse, mail, mcp-registry | je 1 | je 0,4 % |
| Kalender, Gmail, Drive | je 1 | je 0,4 % |
| **affinity, blender** | **0** | — |

Skills wurden in denselben 53 Sitzungen **zehnmal** aufgerufen: `notiz` (3),
`okx-dex-market` (2), `sprache` (2), `update-config`, `okx-agentic-wallet`,
`posteingang` (je 1). Die übrigen elf Vault-Skills: kein einziges Mal.

## Was daraus folgt

**Der Browser frisst drei Viertel der Werkzeugarbeit.** 181 von 242 Aufrufen.
Jeder Seitenaufruf kostet mehrere Runden (navigieren, lesen, klicken), wo eine
API oder CLI eine Antwort liefert. Vor jedem Browsereinsatz prüfen, ob es einen
Server oder eine CLI für dieselbe Sache gibt.

**Der `archiv`-Server wird umgangen.** Er funktioniert (9.712 Dateien, Index
vom 27.08.2026 22:00, 4.699 per OCR erschlossen) und beantwortet eine Suche in
einem Aufruf. Stattdessen liefen 462 Befehle über den venv-Umweg. Der Server
ist der kürzere Weg — `archiv_suchen`, `archiv_statistik`, `posteingang_stand`.

**18 claude.ai-Connectors haben null Aufrufe** (Uber, PayPal, HubSpot,
monday.com, tldraw, Excalidraw …). Sie belegen in jeder Sitzung Kontext, bevor
ein Wort gesagt ist. Abschalten geht nur in den Connector-Einstellungen auf
claude.ai — siehe `Archiv/TASKS.md`, T-007.

**`mail` ist nicht eingerichtet**, obwohl `Archiv/CLAUDE.md` den Versand
darüber beschrieb: `mail_zugang_pruefen` meldet „Keine Absenderadresse
hinterlegt". Der dokumentierte Weg existierte nur auf dem Papier; die CLAUDE.md
ist korrigiert, die Einrichtung ist T-008.

**`affinity` und `blender` wurden nie aufgerufen.** Beide bleiben eingetragen,
solange kein Grund dagegen spricht — aber sie zählen zum Ballast, wenn Kontext
knapp wird.

## Regel

Ein Werkzeug, das niemand aufruft, ist keins. Fällt beim Arbeiten auf, dass
eine Aufgabe von Hand lief, obwohl ein Server, eine CLI oder ein Skript sie
erledigt hätte, wird das gemeldet und der Weg dorthin in dem Skill verankert,
der die Aufgabe auslöst — sonst wiederholt sich der Umweg beim nächsten Mal.

Verwandt: [[Verbindungen]], [[Wiederholbare-Aufgaben]], [[Routinen]]
