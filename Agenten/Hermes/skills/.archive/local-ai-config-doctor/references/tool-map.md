# Wo lokale KI-Werkzeuge ihre Konfiguration ablegen

Diese Tabelle ist ein **Startpunkt für die Suche, kein Beleg**. Pfade und Kommandos ändern sich mit Versionen. Prüf jeden Eintrag am konkreten System nach (Schritt 1 und 2 des Skills), bevor du darauf aufbaust — und korrigiere sie im Bericht, wenn die Realität abweicht.

## Hermes (Nous Research)

*Am Stand 0.20.6 unter Windows verifiziert.*

| Was | Wo |
|---|---|
| Home-Verzeichnis | `%LOCALAPPDATA%\hermes` per Default, **überschrieben durch `HERMES_HOME`** |
| Hauptkonfiguration | `<home>\config.yaml` (enthält u. a. `model`, `providers`, `mcp_servers`, `moa`, `approvals`) |
| Secrets | `<home>\.env` |
| Anmeldungen | `<home>\auth.json` (Provider, `expires_at`, aktiver Provider) |
| Zustand | `<home>\state.db` (Sessions, Nachrichten) |
| Selbstprüfung | `hermes doctor`, dazu `hermes mcp list`, `hermes profile list`, `hermes status` |
| CLI | `<home>\bin\hermes.exe` |

**Profile:** `hermes profile` verwaltet *isolierte* Instanzen. Ein Profil unter `<home>\profiles\<name>` hat eigene `config.yaml`, `auth.json`, `state.db` und **erbt die Hauptconfig nicht** — fehlende `mcp_servers` im Profil bedeuten null MCP-Server, egal was im Root steht. Welches Profil die Desktop-App nutzt, steht in `%APPDATA%\Hermes\active-profile.json`; die CLI folgt `HERMES_HOME`. Beide können auseinanderlaufen.

**Bekannte Stolperstellen:**
- `${env:NAME}` in `config.yaml` wird nur aus echten Prozess-Umgebungsvariablen aufgelöst (`hermes_cli/config.py`, Funktion um die Auflösung von Config-Refs). Ein Key, der nur in der `.env` steht, bleibt Literal — sichtbar als Warnung „keeping the literal placeholder" beim Start.
- `compression.threshold` ist ein Anteil des Kontextfensters (0…1). Für Modelle unter 512K greift ein Boden von 0,75, ein zu kleiner oder negativer Wert wird dadurch stillschweigend angehoben.
- `browser`-Tools werden absichtlich ausgeblendet, wenn ein Browser-Use-/Cloud-Backend aktiv ist (`browser.cloud_provider`). Die Diagnosemeldung „system dependency not met" legt dann fälschlich eine Chromium-Installation nahe.
- `%APPDATA%\Hermes` (Electron-Daten der Desktop-App) und `%LOCALAPPDATA%\hermes` (CLI-Home) sind verschiedene Dinge — nicht verwechseln.

## Claude Desktop / MCP-Server

| Was | Wo |
|---|---|
| MCP-Konfiguration | Windows: `%APPDATA%\Claude\claude_desktop_config.json`; macOS: `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Logs | `%APPDATA%\Claude\logs` bzw. `~/Library/Logs/Claude` |

MCP-Server werden als `command` + `args` + `env` deklariert. Häufige Ursachen dafür, dass ein Server nicht auftaucht: Pfad existiert nicht, falscher Interpreter (System-Python statt venv), JSON-Syntaxfehler, oder die App wurde nach der Änderung nicht neu gestartet. Ein Server, dessen Prozess sofort beendet, taucht ohne Fehlermeldung einfach nicht auf — Logs lesen.

## Ollama

| Was | Wo |
|---|---|
| Modelle | `~/.ollama` bzw. `OLLAMA_MODELS` |
| API | `http://127.0.0.1:11434` |
| Modelliste | `ollama list` oder `GET /api/tags` |

Konfigurierte Modellnamen gegen diese Liste prüfen. Achte auf die **Art** des Modells: Embedding-Modelle (`bge-*`, `nomic-embed-*`, `*-embed*`) gehören nicht in Chat-Slots. Cloud-Varianten (`:cloud`) brauchen einen hinterlegten Key.

## Claude Code / Codex CLI

| Was | Wo |
|---|---|
| Claude Code | `~/.claude/` (Settings, Skills, Plugins), Projekt: `.claude/`, `CLAUDE.md` |
| Codex CLI | `~/.codex/` |
| Selbstprüfung | `claude doctor`, `claude mcp list` |

## Generisches Vorgehen für unbekannte Werkzeuge

1. Prozessliste nach dem Produktnamen filtern; vom Prozesspfad zum Installationsort.
2. Umgebungsvariablen mit dem Produktnamen im Schlüssel auflisten (`Get-ChildItem Env:` bzw. User-/Machine-Scope einzeln) — dort steckt oft das Home-Override.
3. Nach `config.*`, `*.yaml`, `*.toml`, `settings.json` unterhalb der Kandidaten suchen, nach Änderungszeit sortieren.
4. `<tool> --help` lesen und nach `doctor`, `status`, `config`, `profile`, `mcp` suchen — die Selbstprüfung ist fast immer vorhanden.
5. Wenn das Werkzeug Open Source ist und lokal im Quelltext liegt: die Prüffunktion direkt lesen. Das ist der schnellste Weg von einer unklaren Meldung zur tatsächlichen Bedingung.
