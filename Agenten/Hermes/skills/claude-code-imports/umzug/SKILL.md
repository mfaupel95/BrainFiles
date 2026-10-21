---
name: umzug
description: Verschiebt oder benennt einen Ordner um, ohne dass Pfade still brechen — findet erst alle Verweise, ändert sie gemeinsam, prüft gegen. Benutzen bei "verschieb den Ordner", "benenn um", "das gehört woanders hin", "räum die Struktur auf", "auf die externe SSD", oder wenn ein Programm nach einer Umstellung plötzlich nichts mehr findet.
---

# Ordner umziehen, ohne etwas zu brechen

Ein Ordner mit `Move-Item` zu verschieben dauert eine Sekunde. Was danach nicht
mehr läuft, merkt man Tage später — und zwar meistens gar nicht, weil die
betroffenen Teile **still** ausfallen: Ein MCP-Server ohne Index meldet keinen
Fehler, eine geplante Aufgabe ins Leere meldet Erfolg.

Dieser Skill ist das Verfahren dazu. Die Zahlen und der konkrete Fall vom
30.08.2026 stehen in [[Ordnerstruktur]] — hier steht, **wie** es geht.

## 1. Erst suchen, wer den Ordner kennt

Nie mit dem Verschieben anfangen. Zuerst alle Stellen finden, die den alten
Pfad tragen:

```powershell
# Verweise im Text
rg -n "AlterName[/\\]" --glob '!*.bak-*'

# Absolute Pfade in Konfigurationen
rg -n "AlterName" "$env:APPDATA\Claude\claude_desktop_config.json" Agenten\Hermes\config.yaml

# Laufende Prozesse aus dem Ordner
Get-Process | Where-Object { $_.Path -like "*AlterName*" } | Select-Object Id, Path

# Geplante Aufgaben
Get-ScheduledTask | ? { ($_.Actions.Execute + $_.Actions.Arguments) -match 'AlterName' }

# Umgebungsvariablen
Get-ChildItem Env: | ? { $_.Value -match 'AlterName' }
```

## 2. Die fünf Fallen abklopfen

Alle fünf sind am 30.08.2026 tatsächlich eingetreten. Vollständig mit Belegen
in [[Ordnerstruktur]]; hier die Kurzform als Checkliste:

| Falle | Woran man sie erkennt |
|---|---|
| Programm rechnet seinen Ort aus | `Path(__file__).parents[n]` oder `$PSScriptRoot\..` im Quelltext |
| Zwei Konfigurationen, dieselben Pfade | Claude **und** Hermes starten dieselben Server — nur gemeinsam ändern |
| `.venv` mit editable install | `*.pth` und `__editable__*_finder.py` in `site-packages` tragen absolute Pfade |
| `.exe`-Startprogramm in `Scripts\` | trägt den Pfad zu `python.exe` im Binärcode — Textersetzung hilft nicht |
| laufender Prozess | Windows benennt keinen Ordner um, unter dem eine `.exe` läuft |

**Für `.exe`-Startprogramme gibt es einen billigen Ausweg:** statt das venv neu
zu bauen, den Aufruf auf den Modulweg umstellen. Das Ziel steht in
`site-packages\<paket>.dist-info\entry_points.txt`:

```
[console_scripts]
windows-mcp = windows_mcp.__main__:main
```

wird zu `python.exe -c "from windows_mcp.__main__ import main; main()"`.

## 3. Prozesse beenden — und wissen, wann das nicht geht

**Eine Claude-Sitzung kann sich nicht selbst umziehen.** Läuft der zu
verschiebende Ordner unter Claude Desktop (MCP-Server) oder unter Codex, muss
der Umzug aus einem normalen PowerShell-Fenster laufen, mit beiden Programmen
geschlossen. Vorlage: `Agenten/Routinen/umzug/UMZUG-OFFLINE.ps1`.

Ollama und ähnliche Dienste ohne eigenen Zustand im Programmordner darf man
beenden und danach neu starten — das kostet nichts.

## 4. Verschieben und alles gemeinsam nachziehen

Reihenfolge zählt:

1. **Git-Wurzel zuerst**, falls sie sich mitverschiebt — sonst steht jeder Move
   als „gelöscht + neu angelegt" statt als Umbenennung in der Historie.
2. Ordner verschieben. Auf demselben Laufwerk ist das eine Umbenennung: auch
   51 GB sind in Sekunden umgehängt.
3. Konfigurationen, `.pth`-Dateien, Umgebungsvariablen, geplante Aufgaben —
   **in einem Zug**, nicht über den Tag verteilt.

Bei Stufe-1-Dateien (siehe [[Schutzregeln]]) vorher `.bak-JJJJMMTT` anlegen.

## 5. Gegenprobe — der Schritt, den man weglassen möchte

Ohne Gegenprobe ist der Umzug nicht fertig, sondern nur unbemerkt kaputt.

```powershell
# Bleibt irgendwo der alte Name stehen?
rg -n "AlterName[/\\]" --glob '!*.bak-*'

# Zeigt jeder Pfad in der Konfiguration auf etwas Vorhandenes?
# (macht 90-pruefen.ps1 für beide Konfigurationen auf einmal)
& Agenten\Routinen\umzug\90-pruefen.ps1
```

Dazu die Dateizahl vor und nach dem Umzug vergleichen
(`00-bestand.ps1`, `00-bestand.ps1 -Nachher`).

**Den Namen in jeder TIEFE suchen.** Die Ersetzungsregel auf den vollen alten
Pfad greift nur, wenn jeder Verweis ihn ganz traegt — verschachtelte Werte
(JSON-Felder wie `"datei": "Unterordner/..."`) tragen oft nur den SCHWANZ.
Deshalb zusaetzlich nach dem blossen Ordnernamen suchen (`rg -n "Repos/"`
neben `rg -n "Werkstatt/Repos"`) und jeden Treffer einzeln lesen, statt die
Trefferzahl als Erfolg zu nehmen.

**Vor jedem `git -C <pfad>` pruefen, dass dort ein Repo liegt.** Ohne eigenes
`.git` liest git still von einem Eltern-Repo weiter — `log`/`status` liefern
dann plausible Werte eines ganz anderen Repos (dieselbe HEAD-Uhr ueberall,
dirty-Zaehler aus dem Hausbaum). Nachweis: `git -C <pfad> rev-parse
--show-toplevel` muss in dem Ordner enden. Ein Zurueckbleibsel ohne `.git`
ist eine leere Huelse, kein Klon — nichts ist zu retten, nur zu entfernen.

**`nul`-Restdateien nur per Geraetepfad loeschen.** Eine Datei namens `nul`
ist ueber normale Pfade nicht adressierbar (`Zugriff verweigert`/`Illegal
function`); das `\\?\`-Praefix wird aus der Bash-Kommandozeile zerschossen —
das Loeschkommando in eine .ps1-Datei schreiben und mit -File ausfuehren:
`[System.IO.File]::Delete('\\?\O:\Pfad\nul')`.

## Zwei Regeln, die Schaden verhindert haben

**Berechtigungsvermerke nicht mitziehen.** In `claude_desktop_config.json`
stehen neben Einstellungen auch Freigaben früherer Sitzungen
(`remoteSessionFolderGrants`, `epitaxy-perm-mode-acks`). Ein Vermerk auf einen
Pfad, den es nicht mehr gibt, gewährt nichts — mitgezogen wäre er eine
Freigabe auf den neuen Ort, die niemand erteilt hat. Deshalb bei solchen
Dateien gezielte Schlüssel ändern statt Text ersetzen.

**Beim Ersetzen den alten Namen als Wort verschonen.** Eine Regel
`Claude/ → Archiv/` schreibt auch den Satz „hieß bis dahin `Claude/`" um und
macht die Geschichte unlesbar. Historische Erwähnungen ohne Schrägstrich
schreiben, dann greift die Regel nicht.

## Wenn es sich lohnt: Skript statt Handarbeit

Ab etwa zwanzig Fundstellen ist ein Skript billiger als Einzelbearbeitung —
nicht wegen der Eleganz, sondern weil das Lesen der Dateien den größten Teil
der Kosten ausmacht. Das Muster liegt fertig in
`Agenten/Routinen/umzug/`: `gemeinsam.ps1` mit `Verschiebe`,
`Sicherungskopie`, `Ersetze-InDatei`, `Bilanz`; `pfade.psd1` als einzige
Tabelle alt→neu; jedes Skript mit Trockenlauf als Voreinstellung, idempotent
und mit einer Bilanzzeile am Ende.

Verwandt: [[Ordnerstruktur]], [[Schutzregeln]], [[Portabilitaet]],
[[Verbindungen]]
