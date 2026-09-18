# BrainFiles

Wurzel von Max' KI-Betriebssystem. Vier Ordner, vier Aufgaben. Dieses README
ist die **Karte** der Struktur — die maßgeblichen Regeln stehen in
[AGENTS.md](AGENTS.md) und [MaxHirn/CLAUDE.md](MaxHirn/CLAUDE.md), nicht hier.

## Die vier Ordner

| Ordner | Aufgabe | Größe |
|---|---|---|
| **`MaxHirn/`** | Wissen und persönliches Archiv. Obsidian-Vault. **Hier liegt nichts, was startet.** | 45 GB |
| **`Modelle/`** | Modellgewichte und Laufzeiten. Neu herunterladbar, deshalb **nicht in der Sicherung**. | 51 GB |
| **`Agenten/`** | Was läuft: MCP-Server, Hermes, Handelsagent, Routinen, Sicherungsskripte. | 4 GB |
| **`Werkstatt/`** | Gemeinsamer Arbeitsplatz aller Modelle. Übergaben, Zwischenstände, Fremd-Repos. Durchgangsware. | 1 GB |

`Modelle/` und `Werkstatt/` sind **Junctions** auf `O:\Modelle` bzw.
`O:\Werkstatt` — ein "Umzug aus der Werkstatt heraus" heißt also: von O: nach C:.

## Baumkarte

### Top-Level

- `AGENTS.md` — Karte + Arbeitsregeln (Hermes/Codex). LF.
- `CLAUDE.md` — ältere Kopie der Regeln (maßgeblich ist MaxHirn/CLAUDE.md).
- `.env.template` — Vorlage für Umgebungsvariablen (keine echten Schlüssel).
- `.gitignore` — Whitelist-Logik: erst alles ignorieren, dann einzeln freigeben.
- `.gitignore.bak-*` — historische Sicherungen der Whitelist (12 Stück, nicht anfassen).
- `docs/` — Design-Spezifikationen (z. B. Archiv-nach-O-Junctions).
- `_ai_diagnose/` — Diagnose-/Reparatur-Skripte (2026-09, einmalig).
- `.claude/`, `.superpowers/`, `.projectatlas/`, `.worktrees/`, `.vscode/` — Werkzeug-Konfiguration.
- `node_modules/`, `package.json` — Wurzel-npm-Manifest.
- `nul` — 388-B-Altlast (ollama-list-Ausgabe), über normale Pfade nicht löschbar.
- `report.20260918.*.json` — Laufzeit-Report (Systemprüfung/ProjectAtlas), Wegwerfdatei.
- `proxy.yaml` / `proxy.yaml.txt` — Proxy-Konfiguration.

### `MaxHirn/` — Wissen und Archiv

- `Wissen/` — **einzige Wahrheit**: Profil, Projekte, Fristen, Hardware, Verbindungen,
  Routinen, Steuerunterlagen, Schutzregeln. Einstieg: `Wissen/INDEX.md`.
- `Archiv/` — durchsuchbares Dateiarchiv mit `ArchivSuche/` (Volltext + semantisch).
- `Claude/` — Claude-Arbeitsbereich (aktuell nur `Worktrees/PC`, leer).
- `Dashboard.md` — Startseite des KI-Betriebssystems (Obsidian-Standardnotiz).
- `skills/` — Skill-Fundus: 660 MB geklonte Fremd-Repos mit 238 SKILL.md.
- `Daten/` — Embeddings, Prompts, Trainingsdaten.
- `downloads/`, `Referenz/`, `docs/`, `Checkpoints/` — Ablagen.
- `AGENTS.md` / `CLAUDE.md` — Arbeitsanweisung (identischer Inhalt).
- `optional-skills/`, `CLIProxyAPI/`, `codex/` — Werkzeug-Ablagen.

### `Agenten/` — was läuft

- `Bus/` — Telegram-Bus (Port 8787): `bus.py`, `skillsbot.py`, `skillkatalog.py`, Journal.
- `Handel/` — Handelsagent: `dauerlauf.py` (Treiber), `handelszentrale.py` (GUI),
  `spiegelstand.py` (Bedingung-4-Prüfung), `auswertung_alle.py`, `ratschen.py`,
  `risikostufe.py`, `risikovorfilter.py`, `stoerungen.py`, `spur_buch.py`.
  26 Spur-Ordner (xperp, swap, scanner, kraken, orbk, spiegel, kopier, gitter,
  nautilus, mosaic, squeeze, wavetrend, macd_mtf, supertrend, moondev_*, iv_wand, …).
- `Hermes/` — Hermes-Installation: `config.yaml`, `hermes-agent/`, `bin/`, `profiles/`
  (26 Repo-Bots), `skills/`, `cron/`, `memories/`, `state.db`.
- `MCP-Server/` — MCP-Server-venvs (archiv, kraken, mail, okx, tooluniverse, …).
- `Routinen/` — geplante Aufgaben-Wrapper (`.ps1`) + `logs/`.
- `Werkzeuge/` — `fundus-suche.ps1`, `repos-zentrale/`, `repos-launcher.ps1`, `projectatlas/`.
- `MCP-Manifest.json` — MCP-Wahrheit; `mcp-sync-check.ps1` prüft den Abgleich.
- `sichern*.ps1` — Sicherungsskripte (G:, O:, außer Haus).

### `Werkstatt/` — Durchgangsware

- `Projekte/` — OmniRoute, NautilusTrader, Invest, Checkpoints, Daten, GGUF, HuggingFace.
- `Repos/` — 30 Fremd-Repos (Forks, `origin`=mfaupel95, `upstream`=Original, shallow).
- `Austausch/`, `Ausgabe/`, `Protokolle/`, `Sitzungen/`, `Worktrees/` — Übergaben und Zwischenstände.
- `AGENTS.md` / `CLAUDE.md` — Spielregeln für den gemeinsamen Arbeitsordner.
- `omnitrade/`, `OmniRoute/`, `freqtrade/`, `RLTrader/`, `FinRL/`, `CryptoPredictions/` — Handels-Projekte.
- `plan-*.md`, `spec-*.md` — Design-Dokumente.

### `Modelle/` — Gewichte und Laufzeiten

- `blobs/`, `manifests/` — Ollama-Modellstore.
- `GGUF/`, `HuggingFace/`, `hub/`, `xet/` — Modell-Downloads.
- `Ollama/`, `hermes/`, `Programme/`, `Checkpoints/`, `Daten/` — Laufzeiten und Ablagen.
- `copilot-worktrees/` — Worktree-Sammlung (kein Repo).

## Wo die Regeln stehen

- `AGENTS.md` — Karte + Arbeitsregeln (Hermes/Codex).
- `MaxHirn/CLAUDE.md` — Arbeitsanweisung (Claude), identisch mit `MaxHirn/AGENTS.md`.
- `Werkstatt/AGENTS.md` — Spielregeln für den gemeinsamen Arbeitsordner.
- `MaxHirn/Wissen/Schutzregeln.md` — **vor jedem schreibenden Zugriff lesen** (Stufen 0/1/2).
- `MaxHirn/Dashboard.md` — Einstieg ins KI-Betriebssystem.
- `MaxHirn/Wissen/Ordnerstruktur.md` — Ordnerstruktur mit ihren Fallen.
- `MaxHirn/Wissen/Portabilitaet.md` — was ein Umzug auf externe SSD kostet.

## Was NICHT versioniert ist

Git arbeitet nach Whitelist: erst alles ignorieren, dann einzeln freigeben.
Nicht versioniert (Sperrliste, spätere Regel gewinnt):

- `.env`, `auth.json`, alle `*.db` (inkl. `state.db`, `kanban.db`).
- `zustand*.json`, `handelsjournal.csv` je Spur (Laufzeitstände).
- `Modelle/` (neu ladbar), `Werkstatt/` (Durchgangsware).
- `skillsbot.kontext.json`, `Bus/stand.json` (ändern sich mit jeder Nachricht).

## Sicherung / Laufwerke

- `G:` — Sicherung von `MaxHirn/` + `Agenten/` (20:00).
- `O:` — Zweitkopie (21:00); `Modelle/` und `Werkstatt/` liegen hier als Junctions.
- `Q:` — Außer-Haus-Kopie (SanDisk Portable SSD, exFAT), `Q:\MaxHirn-AusserHaus`.
- `G:`, `H:`, `I:` sind dieselbe physische Platte (Disk 2) — kein zweiter Datenträger.
