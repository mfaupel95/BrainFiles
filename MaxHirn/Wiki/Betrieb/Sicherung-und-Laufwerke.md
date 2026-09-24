---
id: 20260921-sicherung-und-laufwerke
title: 'Betrieb — Sicherung und Laufwerke'
tags: [betrieb, sicherung]
created: 2026-09-21
updated: 2026-09-23
related: ['[[Wissen/Off-Site-Backup]]', '[[Wissen/Ordnerstruktur]]', '[[Wissen/Hardware]]']
summary: 'Welches Laufwerk was ist, welche Ordner gesichert werden, wie die Junctions funktionieren, wohin der Plattenplatz geht (pagefile, Logs) und was die Sicherung NICHT kann.'
---

# Sicherung und Laufwerke

## Laufwerke (Stand 21.09.2026)

| Laufwerk | Was | Platz frei |
|---|---|---|
| `C:` | System, BrainFiles (Vault + Agenten), App-Daten | ~52 GB |
| `O:` | eigene physische Platte (Disk 1): `Archiv`, `Modelle`, `Werkstatt`, Wiki (Junction), `Documents` | ~214 GB |
| `G:` | Sicherungsplatte — taegliche Sicherung 20:00 | ~551 GB |
| `Q:` | SanDisk Portable SSD, **ausser Haus**, exFAT, **nicht verschluesselt** | ~204 GB |

`G:`, `H:`, `I:` sind DIESELBE physische Platte (Disk 2) — kein zweiter Datentraeger.
`J:` (WD My Book) hat 479 unkorrigierte Lesefehler: nicht als Sicherung verwenden.

## Was gesichert wird

- Taeglich 20:00 nach `G:`: **`MaxHirn/` und `Agenten/`**. `Modelle/` und `Werkstatt/`
  nicht (neu herunterladbar / Durchgangsware) — das spart ~52 GB je Lauf.
- Taeglich 21:00 Zweitkopie nach `O:`.
- Ausser Haus nach `Q:` (`sichern-ausser-haus.ps1`, `Q:\MaxHirn-AusserHaus`,
  150.732 Dateien / 63,74 GB, robocopy 0 Fehler, geprueft).
- Textstand zusaetzlich als `BrainFiles.bundle` auf `Q:`.

**Regeln beim Sichern:** `sichern.ps1` laeuft OHNE `/MIR` — eine falsch ueberschriebene
Mediendatei ist um 20:01 auch auf `G:` kaputt. Bei robocopy immer `$LASTEXITCODE` pruefen
(>= 8 = Fehler). `index.py`, `sort_inbox.py`, `sichern.ps1`, `zweitkopie.ps1` nie doppelt starten.

## Junctions

`BrainFiles\Modelle` → `O:\Modelle`, `BrainFiles\Werkstatt` → `O:\Werkstatt`,
`O:\Wiki` → `BrainFiles\MaxHirn\Wiki` (angelegt 21.09.2026).

**Warum die Richtung so gewaehlt ist:** Das Wiki liegt als echte Datei im Vault, damit es
**git-versioniert** und **mitgesichert** ist; `O:\Wiki` ist nur der zweite Weg dorthin.
Umgekehrt (Dateien auf `O:`, Junction im Vault) waere der Inhalt weder versioniert noch
in der Sicherung. Fuer `Modelle`/`Werkstatt` gilt das absichtlich nicht: die sind gross
und wiederherstellbar.

Pruefen: `Get-ChildItem <ordner> -Force | ? LinkType | Select Name,LinkType,Target`.
Junctions brauchen **keine** Adminrechte — Symlinks schon (`auth-verknuepfen.ps1` fragt UAC).

## Wohin der Platz geht (nachgemessen 23.09.2026)

Freier Platz schwankt ohne Zutun. Vier Funde, alle gemessen:

| Fund | Groesse | Was es ist |
|---|---|---|
| `O:\pagefile.sys` | **15,96 GB** | Auslagerungsdatei (eingestellt 4096–16384 MB, stand am Maximum; zuletzt geaendert 22.09. 23:16). Ein Ausbau um 12 GB sieht wie Datenzuwachs aus, ist aber Systemverhalten. |
| `Agenten/_Backups/` + `Hermes/state-snapshots/` | 1,17 GB + 410 MB | Notfallkopien der Hermes-`state.db` vom Update 22.09. (15:20 und 15:37) |
| `AppData\Local` + `AppData\Roaming` | **~86 GB + ~30 GB** | Die echten C:-Fresser sind App-Daten, nicht BrainFiles (`MaxHirn` 6,5 GB). Nachgemessen 23.09.2026 mit PowerShell (Reparse-Punkte aussortiert): Local `Packages` 24,5 GB, `Programs` 8,7 GB, `NVIDIA` 5,9 GB, `Microsoft` 5,7 GB, **`pip` 5,4 GB**, `hermes` 4,2 GB, `Google` 4,0 GB, **`pnpm` 3,4 GB**, **`ms-playwright` 2,6 GB**, **`npm-cache` 2,4 GB**, `uv` 2,2 GB, `wsl` 1,9 GB, **`CrashDumps` 1,7 GB**, **`Temp` 1,6 GB**. Roaming: `Pioneer` 11,9 GB, **`npm` 4,8 GB**, `Cemu` 4,5 GB, `Mozilla` 4,1 GB. Fett = reproduzierbarer Cache/Muell. |
| `Agenten/Handel/moondev_*.log` | 172 MB | Agenten-Logs des Moon-Dev-Treibers, ~50 MB je Tag |

**Cache-Lauf 23.09.2026** (nur reproduzierbare Posten, `Packages`/`Programs`/`Roaming/npm`/`ms-playwright` unangetastet):
`pip` 5.428 → **1 MB** · `uv` 2.164 → **1 MB** (`uv cache clean`, meldet „No cache found" und
raeumt trotzdem) · `npm-cache` 2.381 → **951 MB** · `pnpm` 3.398 → **2.970 MB** · `CrashDumps`
1.663 → **0 MB** · `Temp` 1.596 → **255 MB**. Summe der Posten ~12,4 GB, an `df` gemessen
**+11,2 GB** (Differenz: `Temp` und Nachbarprozesse schreiben weiter). `C:` danach ~61,7 GB frei.

**Platz-Wache (neu 24.09.2026).** Cron `platz-wache` (Job 2404f4a15149, Montag 08:45,
`no_agent`, Telegram) ruft `Agenten/Hermes/scripts/platz-wache.py`: freier Platz C:/Q:,
Caches (pip/npm/pnpm/uv), Muell (CrashDumps/Temp), groesste Agenten-Logs,
`Agenten/_Backups` und ein liegengebliebenes `.git/index.lock`. Gemeldet wird nur, was
eine Schwelle reisst (Zahlen in `SCHWELLEN` im Skript) - leere Ausgabe = nichts senden.
Volle Tabelle jederzeit: `python Agenten/Hermes/scripts/platz-wache.py --immer`.
Gemessene Laufzeit des ganzen Messlaufs: **7 s** (18:39) - die Wache ist billig,
weil jede Messung eine eigene Zeitgrenze hat und "nicht gemessen" nie als 0 zaehlt.
Die Systempruefung (Block 7) misst weiterhin nur den Endstand je Laufwerk, die Wache
liefert die Ursachen.
**Log-Rotation (neu 23.09.2026).** `moondev_dauerlauf.py` dreht eine Agenten-Logdatei beim Start ab
50 MB nach `<name>.log.1` (`_log_drehen`). Gedreht wird **beim Start**, nicht im Betrieb: ein
laufender Agent haelt die Datei offen, Windows verweigert dann jedes Umbenennen (nachgemessen).
Merksatz: **Wachstum von Dauerprozessen faellt nicht an RAM oder Prozesszahl auf, sondern nur am
Plattenplatz** — wer Platz sucht, sieht zuerst Prozesstabellen an und findet dort nichts.

## Was offen bleibt

Eine Kopie ausser Haus existiert, aber **`Q:` ist nicht verschluesselt** und enthaelt
Klartext-Zugangsdaten (`Wissen/Zugaenge.md`, `Wissen/OKX_API.env`). Alle drei Kopien
stecken im selben Rechner, wenn `Q:` nicht angesteckt ist. Das ist der wichtigste offene
Punkt der Sicherung.

**Gefahrenlage Hardware:** Der Rechner geht schlagartig aus (Kernel-Power 41, BugcheckCode 0,
kein Minidump, kein WHEA); Netzteiltausch war erfolglos. Solange: keine langen Schreiblaeufe
ohne Sicherung, keine Windows-Reparaturinstallation.