---
name: verbindungen
description: Prüft und repariert die Anbindung externer Dienste — MCP-Server, Erweiterungen, Anmeldungen. Benutzen bei "prüfe die MCP-Server", "Server ist nicht da", "Verbindung fehlgeschlagen", "trag den Server ein", "welche Dienste sind aktiv", "Werkzeug fehlt", oder wenn ein erwartetes Werkzeug in der Werkzeugliste nicht auftaucht.
---

# Dienste und MCP-Server

Stand, Serverliste und Anmeldestatus stehen in [[Verbindungen]] (310 Zeilen).
**Zuerst dort nachsehen** — die Frage „läuft Dienst X?" ist dort oft schon
beantwortet, mitsamt Datum der letzten Einzelprüfung.

## 1. Reihenfolge beim Prüfen

```bash
claude mcp list
```

Das ist die einzige verlässliche Aussage darüber, was diese Sitzung erreicht.
Ein Eintrag in einer Konfigurationsdatei ist **kein** Beleg für eine laufende
Verbindung, und ein fehlender Eintrag kein Beleg für das Gegenteil.

Drei Ebenen tragen Server, und sie widersprechen sich regelmäßig:

| Ebene | Datei | Reichweite |
|---|---|---|
| Benutzer | `~/.claude.json` | überall, auch außerhalb des Vaults |
| Projekt | `.mcp.json` (Vault-Wurzel) | Sitzungen, die im Vault wurzeln |
| Projekt | `Archiv/.mcp.json` | Sitzungen, die in `Archiv/` wurzeln |
| Desktop | `%APPDATA%\Claude\claude_desktop_config.json` | die Desktop-Anwendung |

Ein Server, der nur auf Projekt-Ebene steht, ist unsichtbar, sobald `claude` im
Heimatverzeichnis startet. Genau das kostete am 25.08.2026 Zeit. Deshalb wird
wichtiges **bewusst dreifach** eingetragen — das ist Absicht, keine Dublette.
Bei einer Adressänderung müssen alle drei von Hand nachgezogen werden.

## 2. Die vier wiederkehrenden Fehlerbilder

**„Der Server ist nicht da."** Erst die Ebene prüfen, nicht neu eintragen. Ein
zweiter `claude mcp add` legt eine Dublette an, statt das Problem zu lösen.

**Erweiterung und Konfiguration laufen doppelt.** Am 27.08.2026 standen
`windows-mcp` und `desktopcommandermcp` wieder auf `isEnabled: true` und liefen
zweimal. **Das hält nicht von allein** — nach Updates erneut prüfen:

```powershell
Get-ChildItem "$env:APPDATA\Claude\Claude Extensions Settings\*.json" | Select-String isEnabled
```

**„Verbindung konnte nicht hergestellt werden."** Beim OKX-Server schlug der
erste Anlauf fehl, der zweite lief durch; der Endpunkt antwortete die ganze Zeit
regulär mit `HTTP 401`. **Erst noch einmal versuchen, bevor die Konfiguration
umgebaut wird.**

**Die Anmeldung geht nur interaktiv.** `/mcp` in einer gestarteten `claude`-Sitzung
— nicht aus einer laufenden Sitzung heraus. Ein Umzug zwischen den Ebenen
verliert sie. Diese Sitzung kann also einrichten, aber nicht anmelden; dann wird
Max gesagt, was er auszuführen hat, statt es zu versuchen.

## 3. Vor jedem Schreibzugriff

Die Konfigurationsdateien liegen **außerhalb des Vaults** — damit gilt die
Ansagepflicht: Pfad, Befehl und Rückweg nennen, dann bestätigen lassen.

Vorher eine datierte Sicherung anlegen und den Pfad nennen:

```powershell
Copy-Item ~/.claude.json ~/.claude.json.bak-$(Get-Date -f yyyyMMdd)
```

Die Sicherungen sind mehr als Vorsicht: Der Nachweis, dass `--scope user`
tatsächlich in `~/.claude.json` geschrieben hatte, ließ sich am 25.08.2026 nur
über das Paar `bak-20260824`/`bak-20260825` führen — die laufende Datei war
inzwischen bereinigt und hätte das Gegenteil nahegelegt.

**Servereinträge sind gefahrlos versionierbar.** Sie enthalten nur Name, Typ und
öffentliche Adresse. Der Zugangsschlüssel liegt getrennt in
`~/.claude/.credentials.json` und gehört **nie** in ein Repository.

## 4. Fremde Schreibzugriffe einkalkulieren

Am 25.08.2026 erschien ein Eintrag in `Archiv/.mcp.json`, den kein Befehl dieser
Sitzung geschrieben hat. Mehrere Sitzungen und Hermes greifen auf dieselben
Dateien zu. Vor dem Schreiben deshalb `LastWriteTime` ansehen — ist die Datei
jünger als zehn Minuten, arbeitet vermutlich jemand anders daran.

## 5. Benutzt wird, was abgerufen wird

Ein eingetragener Server ist kein Werkzeug, solange ihn niemand aufruft — er
kostet dann nur Kontext. Wie oft welcher tatsächlich lief:

```
.venv\Scripts\python.exe .claude\skills\rueckschau\sitzungen_auswerten.py --werkzeuge
```

Der Stand vom 28.08.2026 steht in [[Werkzeuge]]: 242 Aufrufe in 53 Sitzungen,
drei Viertel davon Browser, 18 claude.ai-Connectors mit **null** Aufrufen.

Zwei Schlüsse daraus, die bei jeder Prüfung mitlaufen:

- **Vor dem Browser prüfen, ob es einen Server oder eine CLI gibt.** Ein
  Seitenaufruf kostet mehrere Runden, ein Werkzeugaufruf eine.
- **Ein Weg, der in einer CLAUDE.md steht, ist damit noch nicht benutzbar.**
  `mail` war dort als vorgesehener Versandweg beschrieben und meldete
  „Keine Absenderadresse hinterlegt". Bei einem Werkzeug, das noch nie lief,
  vor dem ersten Einsatz die Prüffunktion aufrufen, nicht den Ernstfall.

## 6. Danach

Jede Änderung am Serverbestand gehört mit Datum nach [[Verbindungen]] — auch das
Abschalten. Ein „aktiv", das seit Wochen niemand nachgemessen hat, ist die
teuerste Zeile in der Tabelle.

## 7. Der automatische Abgleich der zwei Agenten

Für den Bestand in diesem Rechner gibt es eine Prüfung, die Manifest,
Claude-Konfiguration und alle Hermes-Konfigurationen gegeneinander hält und den
Exit-Code als Abnahme liefert. Sie läuft in `MaxHirn-Systempruefung` mit:

```powershell
cd "$HERMES_HOME/../.." && powershell -ExecutionPolicy Bypass -File Agenten/mcp-sync-check.ps1 -Streng
```

Exit 0 = kein Widerspruch, Exit 1 = Namensliste der Widersprüche. Der Prüflauf
wird nach jeder Änderung an einem Server gezeigt, nicht behauptet. Der Soll-Bestand
steht in `Agenten/MCP-Manifest.json` (Feld `agenten` = bewusst nur bei einem
Agenten, `braucht_port` = Begleitprogramm muss laufen).

Drei Fallen, die dort Zeit gekostet haben:

- **Die Claude-Konfiguration liegt im MSIX-Container.**
  `%APPDATA%\Claude\claude_desktop_config.json` existiert hier nicht; richtig ist
  `%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude_desktop_config.json`.
  Pfade immer erst suchen, dann lesen.
- **Hermes hat Profil-Configs.** Server können in `Agenten/Hermes/profiles/<name>/config.yaml`
  stehen statt in der Haupt-Config. Wer nur die Haupt-Config liest, meldet vorhandene
  Server als fehlend.
- **Windows PowerShell 5.1 ist nicht PowerShell 7.** Skripte für die Aufgabenplanung
  rein ASCII ohne BOM halten und `\"` als Escape nie verwenden — 5.1 bricht daran
  schon beim Parsen ab und meldet dann jahrelang falschen Alarm. Beide Versionen
  laufen lassen, bevor ein Prüfskript als fertig gilt.
- **Ein geparkter Server ist kein Ausfall.** Server mit Begleitprogramm
  (Blender 28015, Affinity 6767) scheitern im Log im Minutentakt, solange das
  Programm zu ist. Vor dem Melden den Port prüfen, sonst wird Erwartetes als Störung
  gemeldet.
- **NordVPN-Exit kann Anthropic blocken (16.09.2026).** Clara Desktop meldete
  „keine Verbindung“: alle Anthropic-Domains (claude.ai, api.anthropic.com,
  www/docs.anthropic.com, platform.claude.com — alle auf 160.79.104.10)
  timeouteten, Google/GitHub/OKX liefen. Der NordLynx-Exit (Frankfurt,
  AS207137 PacketHub) konnte das Anthropic-Netz nicht routen; check-host.net
  erreichte dieselbe IP von DE aus in 1 ms. Behebung: VPN trennen (NordVPN-App
  oder Tray-Kontextmenü), dann api.anthropic.com antwortet in 0,1 s und Claude
  verbindet nach Neustart. Vor solchen Meldungen: `curl -s -o /dev/null -w
  "%{http_code}" https://api.anthropic.com` und `curl ipinfo.io/json` —
  Exit-IP/Land prüfen, Gegenprobe mit check-host.net. VPN wieder verbinden
  erst über einen ANDEREN Server, nie denselben Exit. Kein Admin nötig für
  Trennen; ICMP-Ping ist durch den Tunnel grundsätzlich blockiert (kein
  Diagnosemittel).
