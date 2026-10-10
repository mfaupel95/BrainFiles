---
name: windows-host-zugriff
description: "Use when Tools den Windows-Host nicht erreichen."
category: brainfiles
---

# Auf dem echten Rechner arbeiten (Windows-Host)

Wenn `terminal`, `read_file` oder `write_file` nicht auf dem Arbeitsrechner
landen: Befehle und Dateizugriffe über `windows-mcp` ausführen — Aufgabenplanung,
Dienste, Ports, Prozesse, Registry, alles unter `C:\Users\faupe\`.

## Wann

- `terminal`, `read_file` oder `write_file` finden `C:\...` nicht, oder der
  Aufruf landet offensichtlich in einem Linux-Sandkasten statt auf dem Rechner.
- Ein Befehl **muss** auf dem Arbeitsrechner laufen: Aufgabenplanung, Dienste,
  Ports, Prozesse, Registry, Pfade unter `C:\Users\faupe\`.
- Ein Skript soll geprüft werden, das auf dem Host liegt (Routinen, Sicherungen,
  Bus).

## Zuerst feststellen, wo die Sitzung steht

```bash
uname -a; pwd; ls /; which powershell
df -h; cat /proc/mounts | head -20
```

Antwortet das mit Linux, ohne `C:\` und ohne `powershell` auf dem PATH, dann ist
die Werkzeugsitzung nicht auf dem Host. Nicht weiter mit Pfadraten versuchen —
der Host kommt dann nur über `windows-mcp`.

## Der Weg: windows-mcp

```
tool_describe(["mcp__windows_mcp__PowerShell", "mcp__windows_mcp__FileSystem"])
tool_call([{"name": "mcp__windows_mcp__PowerShell", "arguments": {"command": "..."}}])
```

- `mcp__windows_mcp__PowerShell` — beliebige PowerShell-Befehle auf dem Host, mit
  Max' Benutzerrechten (nicht erhöht). Ausgabe kommt als Text zurück.
- `mcp__windows_mcp__FileSystem` — `read`, `write`, `copy`, `move`, `delete`,
  `list`, `search`, `info`. Relative Pfade lösen vom Desktop auf, also **absolute
  Pfade** verwenden.
- Lokale Werkzeuge lassen sich nicht mit anderen in einem `tool_call` mischen:
  ein Eintrag pro Aufruf.

## Regeln

1. **Schmal abfragen.** Große Ausgaben werden abgeschnitten und als Datei
   abgelegt (der Pfad steht im Ergebnis). Dann den Hinweis dort befolgen: gezielt
   mit `read_file` nachlesen, **nicht** dieselbe Abfrage erneut stellen —
   filtern, zählen, ein `in`-Ergebnis drucken statt ganze Dateien auszugeben.
2. **Erhöhte Rechte bleiben Handarbeit.** Aufgabenplanung mit `-RunLevel Highest`
   kann eine nicht erhöhte Sitzung nicht registrieren („Zugriff verweigert").
   Dann Max den einen Befehl ausführen lassen und danach **lesend** belegen:
   `Get-ScheduledTask`, `Get-ScheduledTaskInfo`, Port prüfen.
3. **Kein Geheimnis in eine Kommandozeile.** PowerShell gibt Argumente in
   Fehlermeldungen im Klartext aus. Werte in der Datei lassen und nur Länge oder
   Hash ausgeben.
4. **Versionierte Textdateien nie per Python-Rewrite ändern** — das stellt CRLF
   auf LF um. Für `.ps1` und Vault-Markdown gezielter Ersatz (patch/sed), und
   danach den Diff ansehen.
5. **Ergebnis zeigen, nicht behaupten.** Ein Befehlsaufruf ist kein Nachweis:
   Zustand über eine zweite, lesende Abfrage belegen (Status, Zähler, ID).

## Aufgabenplanung beurteilen

`Get-ScheduledTaskInfo` je Aufgabe liefert `LastRunTime`, `NextRunTime` und
`LastTaskResult`:

| Wert | Bedeutung |
|---|---|
| `0` | sauber beendet |
| `267009` (0x41301) | läuft gerade |
| `3221225786` (0xC000013A) | von außen beendet (Kill, Herunterfahren, Absturz) |

Ein Ledger-Skript kann nach einem Kill keine Schlusszeile mehr schreiben: Eine
angefangene Meldung ohne Ende ist dann kein Skriptfehler, sondern die Folge des
Abbruchs. Deshalb vor jedem Befund erst `LastTaskResult` ansehen.

## Abgrenzung

- Bus-Meldungen und ihre Abnahme: `bus-integration`
- MCP-Server zwischen Claude und Hermes abgleichen: `mcp-sync`
- Hermes' eigene `config.yaml`/`.env`: `hermes-config-ops`
