---
id: 20260830-benutzerprofil
title: 'Benutzerprofil `C:\Users\faupe`'
tags: [system, betrieb]
created: 2026-08-26
updated: 2026-08-27
related: []
summary: 'Was im Windows-Benutzerprofil liegt, was davon zum Betrieb gehört und was Altlast ist.'
---

# Benutzerprofil `C:\Users\faupe`

Aufnahme vom 26.08.2026. Zweck: festhalten, was im Profil liegt, was davon
zum Betrieb gehört und was Altlast ist — damit die Frage „kann das weg?"
nicht jedes Mal neu erhoben werden muss.

## Grundsatz: Tool-Konfigurationen bleiben im Profil

Die Punkt-Ordner (`.claude`, `.codex`, `.cache`, `.local`, …) sind **keine
Modelle**, sondern Laufzeit- und Zustandsverzeichnisse. Sie gehören **nicht**
in den Vault, aus vier Gründen:

1. `.claude\.credentials.json` und `.codex\auth.json` enthalten OAuth-Tokens.
   Alles unter `MaxHirn/` wandert per `sichern.ps1` in jede Sicherung.
2. Rund 6 GB täglich neu geschriebener Sitzungsdaten würden den Vault
   aufblähen und die Portabilität brechen.
3. `.codex` hält neun aktive SQLite-Datenbanken mit `-wal`/`-shm`-Dateien.
   Die gehören nicht in einen Git-Arbeitsbaum.
4. Verschieben bei laufenden Prozessen kann diese Datenbanken beschädigen.

**Zugriff der Modelle auf den Vault entsteht nicht durch den Ablageort ihrer
Konfiguration**, sondern über Arbeitsverzeichnis, `CLAUDE.md`/`AGENTS.md` und
die MCP-Server-Einträge.

## Andockstand der Agenten

| Agent | Kontextdatei | MCP-Server | Stand |
|---|---|---|---|
| Claude Desktop | `CLAUDE.md` | 11 in `claude_desktop_config.json` | vollständig |
| Hermes | `AGENTS.md` | 11, identisch, in `Hermes/config.yaml` | vollständig |
| Codex | `~/.codex/AGENTS.md` (global) | 11 + `node_repl`, seit 26.08.2026 | vollständig |

Die elf gemeinsamen Server: `archiv`, `mail`, `kraken`, `tooluniverse`,
`windows-mcp`, `blender`, `desktop-commander`, `pdf-vault`, `revolut-x`,
`affinity`, `mcp-memory`. Dazu kommt für Claude der HTTP-Server
`okx-agent-trade-kit` aus `MaxHirn/.mcp.json` und für Codex sein eigener
`node_repl`.

**Bis 26.08.2026 kannte Codex nur `node_repl`** und erreichte weder Archiv noch
Mail, Kraken oder das Gedächtnis. Die elf Server sind jetzt in
`.codex/config.toml` eingetragen (Sicherung: `config.toml.bak-20260826`,
TOML-Syntax und alle Pfade geprüft), und die globale `.codex/AGENTS.md` verweist
oben auf den Vault und die Reihenfolge `Wissen/` → Archiv → Internet.

Bei `mcp-memory` ist der Schlüssel **absichtlich nicht** in die `config.toml`
geschrieben — Codex erbt `MNEMOVERSE_API_KEY` aus der Benutzerumgebung. Bleibt
der Server ohne Anmeldung, ist das die erste Stelle zum Nachsehen.

**`Documents\Codex` wurde am 26.08.2026 nach `MaxHirn\Codex` zusammengelegt**
(vier Datumsordner, keine Namenskollision). Die dazugehörigen Pfade in
`config.toml` sind mitgezogen: 20 Ersetzungen in zwei Schreibweisen — 17 mit
TOML-escapten doppelten Backslashes, 3 in Literalstrings mit einfachem.
Danach geprüft: 23 Projekteinträge, **alle** zeigen auf existierende Ordner.

Wer künftig Pfade in `config.toml` umschreibt, muss **beide Schreibweisen**
behandeln — sonst bleiben stillschweigend Einträge zurück.

`HERMES_WRITE_SAFE_ROOT` ist **nicht** als Windows-Variable gesetzt, steht aber
in `Hermes/.env` — greift also. Kein Fehler, aber leicht zu übersehen.

## Aktive Ordner im Profil (nicht anfassen)

| Ordner | Größe | Inhalt |
|---|---|---|
| `.cache` | 3,2 GB | claude, codex-runtimes, huggingface, puppeteer |
| `.local` | 1,5 GB | `bin\claude.exe`, `uv`, `onchainos` — steht im PATH |
| `.codex` | 1,0 GB | Codex-Zustand, 9 SQLite-Datenbanken |
| `scoop` | 1,0 GB | Paketverwaltung, `GIT_INSTALL_ROOT` zeigt darauf |
| `.claude` | 441 MB | Claude-Code-Zustand, Skills, Sitzungen |
| `.ollama` | klein | Cache + `id_ed25519`. Die Modelle liegen im Vault unter `Modelle\Ollama\` (`OLLAMA_MODELS`) |
| `.onchainos` | 7 MB | `keyring.enc`, `session.json` — Wallet-Werkzeug |
| `.perseus-vault` | 0,5 MB | `secret.key` |
| `.android` | klein | `adbkey` |

`.ollama`, `.onchainos`, `.perseus-vault`, `.android` enthalten Schlüsseldateien.
Nach der Schutzregel: melden, nicht automatisch verschieben.

## Am 26.08.2026 ausgemustert

20 restlos leere Ordner nach `C:\Users\faupe\_Ausgemustert\2026-08-26\`
verschoben (nicht gelöscht): `.aider-desk`, `.astrbot`, `.augment`,
`.autohand`, `.bob`, `.codeartsdoer`, `.codebuddy`, `.codemaker`,
`.codestudio`, `.commandcode`, `.continue`, `.hermes`, `.iflow`, `.mcp-auth`,
`.mcpjam`, `.minimax`, `.tinycloud`, `.vibe`, `ansel`, `Apple`.

Legt ein Programm seinen Ordner neu an, war es doch in Benutzung — dann
gehört es hier vermerkt statt erneut ausgemustert.

**`ansel` wurde noch am selben Tag leer neu angelegt.** Ein laufendes Programm
erzeugt ihn beim Start (Ansel ist ein Darktable-Abkömmling). Erneutes
Ausmustern ist zwecklos — der Ordner kommt wieder.

## Umgebungsvariablen: am 26.08.2026 bereinigt

PowerToys hatte 34 Kopien mit dem Suffix `_PowerToys_Max 2026` angelegt, teils
doppelt angehängt, darunter Zweitkopien von `KRAKEN_API_KEY`,
`KRAKEN_API_SECRET` und `OKX_API_KEY`. Alle entfernt: 61 → 30 Variablen.
Sicherung: `C:\Temp\Aufraeumen\Sicherung\HKCU-Environment-20260826.reg`.

Ebenfalls korrigiert: `TEMP` zeigte auf `C:\WINDOWS\TEMP`, `TMP` war leer.
Beide stehen jetzt als `REG_EXPAND_SZ` auf `%USERPROFILE%\AppData\Local\Temp`.
`USERNAME` stand in `HKCU\Environment` auf `SYSTEM` und wurde entfernt.

Ebenfalls entfernt: 13 Systemvariablen, die fälschlich in `HKCU\Environment`
standen und dort die Maschinenwerte überschrieben — `ComSpec`, `DriverData`,
`NUMBER_OF_PROCESSORS`, `OS`, `PATHEXT`, `PROCESSOR_*` (4), `PSModulePath`,
`windir`, `POWERSHELL_DISTRIBUTION_CHANNEL`, `asl.log`. Vor dem Löschen gegen
HKLM abgeglichen: zwölf waren identisch, **`PATHEXT` nicht**.

> Die Benutzerkopie von `PATHEXT` war veraltet und enthielt `.PY;.PYW` nicht.
> Python-Skripte ließen sich dadurch nicht ohne vorangestelltes `python`
> aufrufen. Der theoretische Schaden war also längst eingetreten — ein Beleg
> dafür, dass verwaiste Benutzerkopien von Systemvariablen nicht harmlos sind.

Endstand: **61 → 17 Benutzervariablen.**

## Ordner-Aufräumung am 26.08.2026

| Ordner | Größe | Wohin |
|---|---|---|
| `Europa` | 3,27 GB | Lehrmaterial ins Archiv, Rest entfernt → [[Fachkunde-Holztechnik]] |
| `odysseus` | 393 MB | mit `MaxHirn\GitHub\odysseus` zusammengeführt, Profil-Kopie entfernt |
| `Documents\Codex` | 10,5 MB | nach `MaxHirn\Codex`, Codex-Pfade mitgezogen |
| `Books` | 30 MB | ausgemustert — alle elf PDFs lagen bereits im Archiv |
| `Neuer Ordner` | 3,3 MB | sechs Bilder in den `Posteingang/`, Rest ausgemustert |
| `dwhelper`, `DeNoise Projects Pro`, `Projects Series`, `Intel` | 49 MB | ausgemustert |
| `Documents\GitHub\{superpowers,obsidian-skills}` | — | ausgemustert, MaxHirn-Klone sind neuer |

**`CAD` und `Autodesk` bleiben** (3,9 GB) — Max nutzt AutoCAD 2014 weiter.

**`plugins\odysseus` bleibt** — das ist ein Codex-Plugin
(`.codex-plugin\plugin.json`, `skills\odysseus\SKILL.md`), kein Rest.

### odysseus: was beim Zusammenführen zu beachten war

Beide Klone standen auf demselben Commit (`d8a2059`, Branch `dev`, gleiches
Remote) und waren sauber. Dateivergleich ohne `venv`/`.git`: 1.367 Dateien
identisch nach Name und Größe, **nichts** nur in der Vault-Version. Nur im
Profil lagen `.env` (enthält lediglich `LLM_HOST` und `SEARXNG_INSTANCE`,
keine Zugangsdaten) und `data/app.db` (leeres Schema, alle 32 Tabellen ohne
Zeilen) — beide übernommen, `app.db` per SHA-256 gegengeprüft.

Die 321 MB `venv` wurden **nicht** übernommen: an ihren Pfad gebunden und aus
`requirements.txt` / `pyproject.toml` reproduzierbar. Wird odysseus wieder
betrieben, muss das venv am neuen Ort einmal neu erzeugt werden — dieselbe
Falle wie bei `Archiv/ArchivSuche/.venv`, siehe [[Portabilitaet]].

## Verwandte Notizen

- [[Fachkunde-Holztechnik]] — Tischler-Lehrmaterial, seit 26.08.2026 im Archiv
- [[Portabilitaet]] — was beim SSD-Umzug bricht
- [[Verbindungen]] — MCP-Server und Anmeldestatus
- [[Hermes]] — zweiter Agent
- [[Schutzregeln]]
