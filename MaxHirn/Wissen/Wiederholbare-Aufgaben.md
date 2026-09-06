---
id: 20260830-wiederholbare-aufgaben
title: 'Wiederholbare Aufgaben'
tags: [betrieb]
created: 2026-08-28
updated: 2026-09-06
related: [20260830-routinen, 20260902-skill-bibliothek]
summary: 'Welche Arbeit sich wiederholt hat und welche Skills daraus entstanden sind.'
---

# Wiederholbare Aufgaben

Welche Arbeit sich in den bisherigen Sitzungen tatsächlich wiederholt hat — und
welche Skills daraus entstanden sind.

**Warum:** Bis zum 28.08.2026 gab es Skills nur für Max' Sachthemen (Archiv,
Fristen, Belege, Geld). Der Betrieb des Systems selbst — Windows-Diagnose,
MCP-Server, Laufwerksvergleich, Committen — lief in jeder Sitzung neu und
suchte dieselben Wege erneut, obwohl das Wissen längst in Notizen stand. Es
fehlten nicht die Kenntnisse, sondern die Abrufwege.

**Stand:** 2026-08-28

## Die Messung

53 Sitzungen, 74 MB, 362 Nutzer-Anweisungen (davon 200 eigenständige),
4.017 ausgeführte Befehle. Laufzeit der Auswertung: unter zehn Sekunden.

Nachrechenbar mit:

```
.venv\Scripts\python.exe .claude\skills\rueckschau\sitzungen_auswerten.py
```

Befehle je Thema, ganzer Zeitraum bis 28.08.2026 — und zum Vergleich nur die
letzten acht Tage (`--seit 2026-08-20`), weil sich die Schwerpunkte verschoben
haben:

| Thema | gesamt | seit 20.08. | Skill |
|---|---|---|---|
| Python/venv | 979 | 72 | (Werkzeugebene, kein eigener Skill) |
| Archiv-Index/Suche | 462 | 32 | `archiv`, `posteingang` |
| Prozesse | 215 | 45 | `system` |
| MCP/Claude-Konfig | 133 | **91** | `verbindungen` |
| Registry | 113 | 75 | `system` |
| Laufwerksvergleich | 112 | 16 | `vergleich` |
| Git/Sichern | 106 | **103** | `sichern` |
| Umgebungsvariablen | 79 | 52 | `system` |
| Ereignisanzeige/Absturz | 69 | 28 | `system` |
| Speicherplatz | 68 | 19 | `vergleich` |
| Dienste/Treiber | 28 | 10 | `system` |
| Aufgabenplanung | 21 | 22 | (Routinen, siehe [[Routinen]]) |

Die beiden fetten Zeilen sind der Befund: **Git und MCP-Konfiguration sind fast
vollständig Arbeit der letzten acht Tage** — 103 von 106 beziehungsweise 91 von
133 Befehlen. Das sind keine Altlasten, sondern der laufende Betrieb.

## Daraus entstanden

Sechs Skills am 28.08.2026: `system`, `verbindungen`, `vergleich`, `sichern`,
`skill`, `rueckschau`. Sie enthalten **kein** neues Wissen — sie verweisen auf
[[Hardware]], [[Miniaturansichten]], [[Verbindungen]] und [[Schutzregeln]], wo
es bereits stand. Neu ist nur der Abrufweg und das Verfahren.

Ein Skript war neu: `Routinen/arbeitsbaum-pruefen.ps1` trennt den Git-Arbeitsbaum
nach der 10-Minuten-Schwelle in ruhend und in Arbeit — die Handarbeit, die vor
jedem der 103 Git-Befehle nötig war.

## Nachtrag 30.08.2026: `umzug`

Der siebte Skill ist **nicht** aus dieser Messung entstanden, sondern aus einem
Anlassfall: dem Umbau von `BrainFiles/` in vier Ordner. Er zählt trotzdem als
wiederkehrend, und zwar mit Beleg — im August sind die MCP-Server schon einmal
umgezogen, von `%APPDATA%` nach `MCP-Server/` (siehe [[Verbindungen]], Stand
13.08.2026). Beim zweiten Mal am 30.08. brachen dieselben fünf Dinge wie beim
ersten. Genau das ist das Kriterium aus dem Skill `skill`: nicht die Häufigkeit
schätzen, sondern einen zweiten Fall vorweisen.

Was er kostet, wenn er fehlt: still ausfallende MCP-Server und geplante
Aufgaben, die Erfolg melden, während sie ins Leere laufen. Details in
[[Ordnerstruktur]].

## Nachtrag 02.09.2026: `videoanalyse`

Achter Skill, wieder aus einem zweiten Fall statt aus der Messung: Am
11.08.2026 wurde ein YouTube-Beitrag von STA Solutions zur Marktlage
ausgewertet ([[Marktlage-August-2026]]), am 02.09.2026 einer desselben Kanals
zu XRP ([[XRP-Analyse-STA-September-2026]]). Beim zweiten Mal kostete allein das
Transkript-Ziehen drei Sackgassen (veränderte `YouTubeTranscriptApi`-API, leere
`timedtext`-Antworten, unbrauchbare Fremdseiten). Der Weg steckt jetzt in
`.claude/skills/videoanalyse/transkript.py`; die Auswertung folgt der Struktur
der beiden bestehenden Notizen.

## Fallen bei einer erneuten Auswertung

**Über Befehle zählen, nicht über Anweisungen.** Bei einem Fork trägt jede Kopie
die volle Vorgeschichte; die Anweisungen vom 05./06.08. stehen wortgleich in vier
Sitzungsdateien und verzerren jede Häufigkeit über Nachrichten.

**Die Hälfte der Anweisungen ist Mechanik** („Continue from where you left off",
eingespielte Skill-Texte, Nachrichten anderer Sitzungen). Das Skript filtert sie.

**In den Transkripten stehen Zugangsdaten im Klartext** — API-Schlüssel und
Tokens, weil Max sie eingetippt hat. Ausgabedateien der Auswertung gehören ins
Scratchpad, nie in den Vault und nie in einen Commit.

Verwandt: [[Werkzeuge]], [[Schutzregeln]], [[Routinen]], [[Portabilitaet]], [[Skill-Bibliothek]]
