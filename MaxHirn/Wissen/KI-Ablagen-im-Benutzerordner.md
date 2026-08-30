---
id: 20260830-ki-ablagen-benutzerordner
title: 'KI-Ablagen im Benutzerordner'
tags: [betrieb, struktur]
created: 2026-08-30
updated: 2026-08-30
related: [20260830-ordnerstruktur, 20260830-schutzregeln]
summary: 'Welche KI-Daten außerhalb von BrainFiles liegen, warum sie dort bleiben müssen und was bei einem Neuaufsetzen verlorenginge.'
---

# KI-Ablagen im Benutzerordner

Beim Umbau am 30.08.2026 stand die Frage, ob die KI-Sachen aus
`C:\Users\faupe\` nach `BrainFiles/` wandern sollen. **Entscheidung: nein.**
Sie bleiben, wo die Programme sie suchen. Diese Notiz sagt, was dort liegt —
damit das Chaos wenigstens beschrieben ist statt nur ertragen.

## Der Bestand (gemessen 30.08.2026)

| Größe | Dateien | Ort | Was |
|---:|---:|---|---|
| **12,0 GB** | 100.835 | `%APPDATA%\Claude` | Claude Desktop: MCP-Konfiguration, Erweiterungen, Cache |
| **1,5 GB** | 10.472 | `~\.codex` | Codex: Sitzungen, Konfiguration, Automationen |
| **1,5 GB** | **17** | `%LOCALAPPDATA%\Ollama` | nur Protokolle — 17 Dateien, im Schnitt 88 MB je Datei |
| 714 MB | 4.686 | `%LOCALAPPDATA%\OpenAI\Codex` | Codex: Programm und Laufzeiten |
| 110 MB | 3.753 | `~\.claude` | Claude Code: Sitzungen, Projekte, Skills, Plugins |
| 49 MB | 10 | `~\.cua-driver` | Computer-Use-Treiber |
| 10 MB | 23 | `%LOCALAPPDATA%\Claude` | Claude Desktop: Programmstand |
| 6 MB | 118 | `%APPDATA%\Hermes` | Hermes: Programmstand (die Daten liegen in `Agenten\Hermes`) |
| 1 MB | 135 | `~\.agents` | gemeinsame Agenten-Skills |
| < 1 MB | 4 | `~\.claude-server-commander` | Desktop Commander: Konfiguration, Aufrufprotokoll |
| < 1 MB | 3 | `~\.tooluniverse` | ToolUniverse: Cache |
| < 1 MB | 6 | `~\.ollama` | Ollama: Schlüsselpaar und Konfiguration — **nicht** die Modelle |

Erneut erheben: `Agenten\Routinen\umzug\70-benutzerordner.ps1`

## Warum das nicht wandert

Alle diese Pfade sind in den Programmen **fest verdrahtet**. Ein Umzug ginge
nur über Verzeichnis-Junctions (`mklink /J`) — ein zusätzlicher Mechanismus,
der bei jedem Rechnerwechsel und jedem SSD-Umzug erneut gerichtet werden muss
und der still bricht, wenn ihn jemand vergisst. Der Gewinn wäre kosmetisch: die
Daten wären an einem Ort. Der Preis wäre ein weiterer Punkt, an dem etwas
kaputtgehen kann, ohne dass es jemand merkt.

## Was bei einem Neuaufsetzen verlorenginge

Nicht alles davon ist gleich wertvoll:

- **`~\.claude` und `~\.codex` sind die einzigen Kopien der Sitzungsverläufe.**
  Sie stehen in keiner Sicherung — `sichern.ps1` kopiert `BrainFiles/`, nicht
  den Benutzerordner. Der Skill `rueckschau` wertet genau diese Verläufe aus,
  um wiederkehrende Arbeit zu finden. Wer den Benutzerordner neu aufsetzt,
  verliert die Grundlage dafür.
- **`%APPDATA%\Claude` ist zu 12 GB Cache und Erweiterungen** und
  reproduzierbar — mit einer Ausnahme: `claude_desktop_config.json` trägt die
  MCP-Konfiguration mit ~30 absoluten Pfaden. Sie steht zweitverwertet in
  `Agenten/Hermes/config.yaml`, ist also nicht die einzige Quelle.
- Alles andere ist Cache, Protokoll oder Programm und kommt bei einer
  Neuinstallation von selbst zurück.

## Zwei Auffälligkeiten

**1,5 GB Ollama-Protokolle in 17 Dateien.** Das ist kein Betriebszustand,
sondern eine Protokolldatei, die nie rotiert wurde. Sie lässt sich gefahrlos
löschen; sie wächst nur wieder nach.

**Reste falscher Installationen.** `%LOCALAPPDATA%\Claude-3p` (seit 26.07.2026)
und `Claude-Data` (seit 18.08.2026) enthielten **null Dateien** und wurden am
30.08.2026 entfernt. Es waren die einzigen nachweislich toten Ordner — alles
andere in der Tabelle wird benutzt.

## Regel für die Zukunft

Was ein Programm an einem festen Ort im Benutzerordner sucht, bleibt dort und
wird **hier** eingetragen. Was frei wählbar ist, gehört nach `BrainFiles/` —
so wie der Ollama-Modellstore, der über `OLLAMA_MODELS` frei liegt und deshalb
nach `Modelle/Ollama/Store` gewandert ist. Siehe [[Ordnerstruktur]].

Verwandt: [[Ordnerstruktur]], [[Schutzregeln]], [[Portabilitaet]], [[Hardware]]
