---
name: data-guard-audit
description: Prueft Pfade gegen die Schutzstufen vor Dateioperationen.
version: 1.0.0
author: Max Faupel (faupel), Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [schutz, sicherheit, dateien, schutzstufen]
    related_skills: [protecting-irreplaceable-data]
---

# Schutzstufen-Pruefung

Macht die Prosa aus `Wissen/Schutzregeln.md` abfragbar, BEVOR geschrieben wird.
Beantwortet genau eine Frage: in welche Schutzstufe faellt dieser Pfad, und was
darf damit geschehen. Geurteilt wird, nicht aufgeraeumt - der Waechter liest
keine Dateiinhalte und loescht nie aus eigenem Antrieb.

## Wann

- Vor jedem `Remove-Item`, `Move-Item`, Robocopy mit `/MIR`, `git clean`.
- Bevor eine Routine oder ein Agent aufraeumt, sortiert oder umbaut.
- Wenn unklar ist, ob ein Pfad noch Original ist oder schon in Git liegt.

**Don't use for:** einzelne Lesevorgaenge, neue Dateien in Stufe 2, das
Erschliessen eines Dokuments (dafuer `archiv`).

## Woher die Stufen kommen

`Wissen/Schutzregeln.md` ist die Quelle der Wahrheit. Bei Abweichung gilt die
Notiz, nicht dieses Skript. Die Zuordnung in Kurzform:

| Stufe | Bedeutung | Beispiele |
|---|---|---|
| **0** | Original ohne Zweitquelle, nur lesen | `O:\Archiv\{Dokumente,Bilder,Videos,Musik,Software,Posteingang}`, `Zugaenge.md`, `.env`, `*.pem`, `*.pfx`, `*.kdbx`, `*.key`, `*.ovpn`, 0xFF-Platzhalter-PDFs |
| **1** | Betrieblich: erst `.bak-JJJJMMTT`, dann aendern, dann echten Lauf zeigen | `Routinen/*.ps1`, `ArchivSuche/*.py`, `AGENTS.md`, `CLAUDE.md`, `Dashboard.md`, `.claude/skills/`, `.obsidian/`, `MCP-Server/`, `Handel/`, `Hermes/`, `Bus/` |
| **2** | Reproduzierbar oder in Git, freie Hand | ausdruecklich auch **`Wissen/`**, dazu `Routinen/logs/`, `.venv`, `__pycache__`, `node_modules`, `Modelle/`, `Werkstatt/`, Index-Datenbanken |

Zwei Punkte, die man falsch erwartet:

- **`Wissen/` ist Stufe 2**, nicht Stufe 0. Die Notizen liegen in Git und sind
  mit `git restore` zurueckholbar. Wer sie sperrt, blockiert die normale Arbeit.
- **Protokolle bleiben Stufe 2**, obwohl sie unter `Routinen/` liegen. Sonst
  zoege die Stufe-1-Regel jeden Logschreiber in die Sicherungspflicht.

## Wie

Der operative Waechter liegt bei den Routinen, nicht im Skill:

```powershell
$r = 'C:\Users\faupe\Documents\BrainFiles'
& "$r\Agenten\Routinen\safe-file-ops.ps1" -Pfad "<pfad>" -Aktion <aktion>
```

Ohne `-Ausfuehren` wird nur geurteilt - das ist die Vorgabe. Mit `-Ausfuehren`
legt er bei Bedarf die `.bak`-Kopie an oder verschiebt in die Quarantaene.

Aktionen: `lesen`, `loeschen`, `massenhaft_loeschen`, `ueberschreiben`,
`verschieben`, `umbenennen`.

Der tragbare Zwilling fuer Sitzungen ohne PowerShell:

```powershell
& "$r\MaxHirn\Archiv\ArchivSuche\.venv\Scripts\python.exe" `
  "$r\MaxHirn\optional-skills\productivity\data-guard-audit\scripts\audit_logic.py" `
  --path "<pfad>" --action <aktion>
```

Andere Routinen koennen die Funktion direkt laden statt das Skript zu starten:

```powershell
. "$r\Agenten\Routinen\safe-file-ops.ps1"
Get-Schutzurteil -Pfad '<pfad>' -Aktion 'loeschen'
```

## Urteile und Exitcodes

| Urteil | Code | Bedeutung |
|---|---|---|
| `ERLAUBT` | 0 | Nichts spricht dagegen |
| `ABBRUCH` | 1 | Stufe 0 oder Schluesseldatei, nicht anfassen |
| `SICHERUNG_PFLICHT` | 2 | Erst `.bak-JJJJMMTT`, dann aendern |
| `QUARANTAENE` | 3 | Nur nach `Posteingang/_zu_loeschen/`, nie loeschen |

## Fallen

- **Erst urteilen, dann handeln.** Eine Kopie nach dem Ueberschreiben ist keine
  Sicherung. Die Stufe-0-Sperre ist der einzige Schutz, der noch greift, wenn
  die Datei schon verloren waere.
- **`sichern.ps1` laeuft ohne `/MIR`.** Eine falsch ueberschriebene Datei ist um
  20:01 auch auf `G:` kaputt - die Sicherung propagiert den Schaden, sie faengt
  ihn nicht ab.
- **Quarantaene nicht neben die Datei legen.** `_zu_loeschen` gehoert unter
  `Posteingang/`. Liegt der Ordner im Archiv selbst, sammelt ihn der naechste
  Sortierlauf wieder ein und die beiseitegelegten Dateien sind still zurueck.
- **Ein blockierter Versuch gehoert ins Protokoll, ein Trockenlauf nicht.**
  Sonst ist `Routinen/logs/sicherheitspruefung.log` nach einer Woche unlesbar.
- **Die Docker-Sitzung sieht den Vault nicht.** Laeuft die Werkzeugsitzung in
  einem Linux-Sandkasten, landen `read_file`/`write_file` nicht auf dem
  Arbeitsrechner, und `HERMES_WRITE_SAFE_ROOT` weist jeden Schreibversuch ab.
  Dann ueber `windows-mcp` arbeiten, siehe Skill `windows-host-zugriff`.
- **Zwei Fassungen, eine Regel.** Der Waechter existiert als PowerShell und als
  Python. Wer eine Stufe aendert, aendert beide und prueft sie gegeneinander.

## Nachweis

Der Waechter gilt als geprueft, wenn beide Fassungen fuer dieselben Faelle
dasselbe Urteil liefern - je Stufe einer und die beiden Ausnahmen:

| Pfad | Aktion | Erwartet |
|---|---|---|
| `O:\Archiv\Bilder\<datei>` | `loeschen` | `ABBRUCH` (1) |
| `O:\Archiv\Bilder\<datei>` | `verschieben` | `QUARANTAENE` (3) |
| `MaxHirn\Wissen\Zugaenge.md` | `lesen` | `ABBRUCH` (1) |
| `Agenten\Routinen\bus.ps1` | `loeschen` | `SICHERUNG_PFLICHT` (2) |
| `MaxHirn\Wissen\INDEX.md` | `loeschen` | `ERLAUBT` (0) |
| `Agenten\Routinen\logs\x.log` | `loeschen` | `ERLAUBT` (0) |

Alle ohne `-Ausfuehren` aufrufen: geaendert wird dabei nichts.
