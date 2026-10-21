---
id: 20260921-sicherung-und-laufwerke
title: 'Betrieb — Sicherung und Laufwerke'
tags: [betrieb, sicherung]
created: 2026-09-21
updated: 2026-10-21
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
- Taeglich 21:00 Zweitkopie nach `O:\MaxHirn-Zweitkopie` (`Agenten/sichern-zweitkopie.ps1`).
  Echter Lauf 30.09.2026 00:01-00:06: robocopy-Code **1** (Erfolg), **200.113 Dateien /
  ~37 GB**, Zielstruktur `...\MaxHirn` mit Archiv und Agenten. `O:` frei 160,6 -> 121,1 GB.
  Die Zweitkopie laeuft ohne `/MIR` wie die Hauptsicherung - eine falsch ueberschriebene
  Datei ist auch dort kaputt. Sie ersetzt **nicht** die Ausser-Haus-Kopie: dieselbe Platte
  im selben Rechner ist kein zweiter Brandabschnitt.
- Ausser Haus nach `Q:` (`sichern-ausser-haus.ps1`, `Q:\MaxHirn-AusserHaus`,
  150.732 Dateien / 63,74 GB, robocopy 0 Fehler, geprueft).
- Textstand zusaetzlich als `BrainFiles.bundle` auf `Q:`.

**Regeln beim Sichern:** `sichern.ps1` laeuft OHNE `/MIR` — eine falsch ueberschriebene
Mediendatei ist um 20:01 auch auf `G:` kaputt. Bei robocopy immer `$LASTEXITCODE` pruefen
(>= 8 = Fehler). `index.py`, `sort_inbox.py`, `sichern.ps1`, `zweitkopie.ps1` nie doppelt starten.

## Zugangsdateien in Klonen sind nicht mitgesichert (30.09.2026)

Beide Sicherungen klammern `Werkstatt` per `/XD` aus — damit liegt **jede**
`.env` in einem geklonten Fremd-Repo ausserhalb der Sicherung, und die
Klartext-Pruefung in `sichern.ps1` sieht sie ebenfalls nicht (dieselbe
Ausschlussliste). Gemessen am 30.09.2026: von 47 Klonen unter `Werkstatt`
tragen 7 eine `.env`, vier davon mit echten Zugangswerten
(`moon-dev-ai-agents` samt `src/`, `openmontage`, `OpenTerminalUI`).

Ablage der Kopien (in `Agenten/` und damit in beiden Sicherungen, in Git
gesperrt): `Agenten/Hermes/.sicherung/<repo>-env.bak-JJJJMMTT`. Die
Bestandsaufnahme mit Namen und Laengen steht in
`Agenten/Hermes/.sicherung/klon-envs-20260930.md`.

Zwei Merksaetze:

- **Die Sicherung ist nicht die einzige Stelle, die `Werkstatt` ausblendet** —
  wer "wird das gesichert?" fragt, muss die Ausschlussliste mitlesen, nicht nur
  das Zielverzeichnis.
- **Eine alte Kopie ist kein Beleg:** unter `Agenten/_Backups/` lagen aeltere
  `.env`-Kopien (moondev 24.09., openmontage 22.09.), kleiner als der heutige
  Stand und in einem Ordner, den die Sicherung ihrerseits ueberspringt.

Ausserdem ausserhalb beider Quellen: `C:\Users\faupe\.omniroute\` (1,2 GB).
Die `.env` dort traegt `STORAGE_ENCRYPTION_KEY`, `JWT_SECRET` und
`API_KEY_SECRET`; der Schluessel entschluesselt die Anbieter-Verbindungen in
`storage.sqlite` — ohne ihn ist der Router nach einem Wiederaufbau leer.
Eine Kopie liegt seit 30.09.2026 in `.sicherung/omniroute-home-env.bak-20260930`.

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

## Reserve auf C: und die Auslagerungsdatei (30.09.2026)

**Entscheidung Max:** auf C: werden **30 GB frei gehalten**, und die Auslagerungsdatei zieht
von C: nach O:.

Anlass war ein Ausfall am selben Tag: ein Desktop-Build braucht rund **20 GB transient**,
C: lief dabei auf 0,1 GB, der Update-Schwanz brach mit `No space left on device` ab und der
Desktop kam in eine Bootschleife (Gateway 73 min aus). Der erste Notausgang war Aufraeumen
(uv-Cache 9,2 GB, Temp 4,6 GB).

**Die Wache haelt die Reserve selbst.** `Agenten/Hermes/scripts/platz-wache.py` laeuft
**taeglich 07:45** (Cron `platz-wache`, Telegram, leere Ausgabe = nichts senden). Faellt der
freie Platz unter 30 GB, raeumt sie auf - aber nur die vier erlaubten, reproduzierbaren
Posten:

| Posten | Schwelle |
|---|---|
| Temp-Dateien | aelter als 24 h |
| CrashDumps | alle |
| uv-Cache (`uv cache clean`) | nur ohne laufenden Bau |
| npm-Cache (`npm cache clean --force`) | nur ohne laufenden Bau |

`node_modules` und `.venv` werden **nie** angefasst. **Waehrend eines laufenden Baus oder
Updates wird gar nicht geloescht** - Zeugen sind die Marker
`$HERMES_HOME/.hermes-update-in-progress` und `installs/*/source-completion-pending` sowie
Kommandozeilen (`source_completion`, `hermes_cli.main update`, `electron-builder`,
`npm run build`, `vite build`, `uv`). Ein `uv cache clean` mitten im Build zerstoert den Build.
Schalter: `--ohne-aufraeumen` (nur messen), `--trocken` (nur anzeigen), `--immer` (Tabelle),
`--json`. Tests: `scripts/test_platz_wache.py`, 15 gruen.

**Vor jedem Bau/Update einmal nachsehen:**

    python Agenten/Hermes/scripts/platz-wache.py --ohne-aufraeumen

**Auslagerungsdatei (Zustand 30.09.2026):** `C:\pagefile.sys` ist auf **8192/8192 fest**
gesetzt, `O:\pagefile.sys` auf **32768/32768** angelegt - beide Eintraege stehen in
`HKLM\...\Memory Management\PagingFiles` und in WMI. Die Commit-Grenze steht damit bei
84,5 GB und **erst nach einem Neustart** bei rund 103,7 GB. Zusaetzlicher Nebeneffekt: C:
traegt derzeit noch eine selbstverwaltete 21 GB grosse Datei; nach dem Neustart sind es 8 GB,
das Laufwerk gewinnt also rund 13 GB. Werkzeug (idempotent, mit `-Testlauf` und
`-Rueckgaengig`): `Agenten/Routinen/einmalig-20260930-auslagerung.ps1`.

## Was offen bleibt

Eine Kopie ausser Haus existiert, aber **`Q:` ist nicht verschluesselt** und enthaelt
Klartext-Zugangsdaten (`Wissen/Zugaenge.md`, `Wissen/OKX_API.env`). Alle drei Kopien
stecken im selben Rechner, wenn `Q:` nicht angesteckt ist. Das ist der wichtigste offene
Punkt der Sicherung.

**Gefahrenlage Hardware:** Der Rechner geht schlagartig aus (Kernel-Power 41, BugcheckCode 0,
kein Minidump, kein WHEA); Netzteiltausch war erfolglos. Solange: keine langen Schreiblaeufe
ohne Sicherung, keine Windows-Reparaturinstallation.

## C:-Notlage und Documents-Aufraeumung (13.10.2026)

**Befund:** `C:` nur noch 1,2 GB frei (von 475 GB), `O:` nur 6,9 GB (von 551 GB) - rote Zone.
Groesster Einzelposten: `BrainFiles/.claude/blobs` mit 70 GB (OCI/Docker-Layer-Cache des
MCP-Docker-Gateways, git-ignoriert, versehentlich im Repo-Arbeitsbaum statt im
Docker-Datenverzeichnis). Dazu `AppData\Local\Temp` 4,7 GB und `CrashDumps` 2,76 GB.
Volle Bestandsaufnahme: `Werkstatt/Austausch/2026-10-13-c-laufwerk-audit.md`.

**Sofortmassnahme:** `.claude/blobs` geleert, `Temp` + `CrashDumps` geleert - `C:` danach
**79,1 GB frei**. Die Loeschung von `.claude/blobs` wurde vom Auto-Mode-Klassifikator erst
als "Irreversible Local Destruction" blockiert; nach Rueckfrage bei Max per erneutem Versuch
(explizite Freigabe) durchgefuehrt. Ursache (Docker-Datenverzeichnis falsch konfiguriert)
ist noch **nicht** behoben - der Cache kann sich wieder fuellen, das ist Teil des
Struktur-Neuentwurfs (Teilprojekt B, `Werkstatt/Projekte/`).

**Documents-Aufraeumung (derselbe Tag):** Drei fast identische iTunes-Mediathek-Exporte lagen
im Profil-`Documents`-Root (`Mediathek.xml` 14.03., `Mediathek_itunes_Feb26.xml` 17.03.,
`Mediathek_itunes_märz26.xml` 26.03., **393.970.624 Byte** - deutlich groesser als die beiden
aelteren, also der vollstaendigste Stand). Max wollte nur **ein** gesichertes Original.
Maerz-Stand nach `O:\Archiv\Musik\iTunes-Mediathek\Mediathek_itunes_maerz26.xml` verschoben
und per Dateigroesse verifiziert, die beiden aelteren plus ein verwaister `iTunes Export.tmp`
geloescht. Verwaiste Musik-Dedupe-Listen und eigene `top_fresser*`-Scanreste (19 Dateien, u.a.
`doppppelt.m3u8`, `delete_list.m3u`, `keep_list.m3u`) nicht geloescht, sondern nach
`Werkstatt/Altlasten-Dokumente-Musikdedupe-2026-10-13/` verschoben (reversibel).

**Offen geblieben, nicht angefasst:** `Documents\Windows11` (16,3 GB) ist entgegen der
ersten Audit-Vermutung **kein** reiner ISO-Rest, sondern eine alte Profilmigration mit
`(Kopie)`-Dopplungen, darunter `Scanned Documents` - also moeglicher persoenlicher Inhalt
unter Loeschsperre. Mehrere als "leer" vermutete App-Ordner (`MuseScore3`, `PowerToys`, u.a.)
enthalten tatsaechlich 1-11 Elemente, nicht 0 - nachgemessen, nicht geloescht. `Documents\WPA
Files` ist bestaetigt leer (0 Elemente), die Loeschung wurde vom Auto-Mode-Klassifikator
blockiert ("Irreversible Local Destruction") und liegt bei Max.

## Stand 21.10.2026: Sicherung repariert, O: knapp

**Sicherung `MaxHirn-Sicherung`:** Exitcode 1 am 06.10.2026 war NICHT der Plattenplatz (G: hatte
509 GB frei), sondern robocopy Code 11 durch vier **fluechtige** Hermes-Dateien (`projects.db-shm`,
`projects.db-wal`, `*.lock`, `.leases\*`): FEHLER 2, sie verschwinden zwischen Auflisten und
Kopieren, keine Nutzdatei fehlte. Fix in `Agenten/sichern.ps1` (`/XF *.db-shm *.db-wal *.lock`,
`/XD .leases`), Commit `20e445cb`. Lauf am 20.10.2026: Code 3 (erfolgreich), 762 s statt 1870 s.
**Merksatz:** Code 11 mit lauter `FEHLER 2`/`FEHLER 32` auf Laufzeitdateien laufender Prozesse
(SQLite-Nebendateien, Locks, Cookies, Snapshots) ist ein Ausschluss-Befund, kein Datenverlust.
Erst die Fehlerzeilen im Log lesen (`Select-String 'FEHLER [0-9]'`), dann den Pfad ausschliessen.

**Offen: `MaxHirn-Ausserhaus-Kopie`** (Code 1 am 19. und 20.10.). Gleiches Muster, Archiv-Teil
sonst sauber (242.086 Dateien, 2 Fehler): `Hermes\browser-profile\chrome\Default\Network\Cookies`
(gesperrt, FEHLER 32) und `Hermes\profiles\bots\cache\terminal\hermes-snap-*.sh` (verschwunden,
FEHLER 2). `sichern.ps1` schliesst `browser-profile` schon aus, `Agenten/Routinen/ausserhaus-kopie.ps1`
noch nicht. **Fix umgesetzt 21.10.2026** - nicht in `ausserhaus-kopie.ps1` (nur Wrapper), sondern
in `Agenten/sichern-ausser-haus.ps1`: `browser-profile` in `$fluechtig`, `profiles\*\cache\terminal`
(29 Treffer) ueber die aufgeloeste Liste `$waisen` (Wildcards sind in `/XD` verboten). Die Meldung
"Gesperrte Update-Reste ausgeschlossen: N" zaehlt dadurch auch diese Ordner mit. **Noch nicht durch
einen echten Lauf bestaetigt** - erst der naechste `MaxHirn-Ausserhaus-Kopie`-Lauf (21:30) zeigt es.
Ziel `Q:` hatte 75,6 GB frei.

**O: Belegung (gemessen 21.10.2026, rund 550 GB, frei 29,3 -> 21,8 GB, Tendenz fallend):**
Modelle 248,7 | Werkstatt 106,5 | Documents 61,8 | Archiv 44,9 | MaxHirn-Zweitkopie 43,2 |
iTunes 36,6 | privkopie-cache 7,5 | .pnpm-store 1,9. Messung: Skriptzeile mit
`Get-ChildItem -Recurse -File` je Top-Ordner, Summe der `Length` (dauert Minuten, daher im
Hintergrund starten; ein 300-s-Vordergrund-Lauf bricht ab).
- `Documents`: Ableton 24,8, Native Instruments 20,0, Maximilian 7,8, FREEDB 2,2 (Musik-/Spielesoftware).
- `iTunes`: 36,1 GB davon `iTunes.BackupByiTunesPortable`, Rest leer.
- `Werkstatt`: Ausgemustert 19,8 | omnitrade-pr 16,1 | omnitrade 12,1 | OmniRoute 11,8 | openmontage 4,6.
  `omnitrade-pr` besteht fast nur aus `target` (16,1 GB Rust-Build-Cache), `omnitrade` aus
  `target` 9,9 + `.git` 1,2 + `target-live` 0,8. **Die `target`-Ordner (rund 27 GB) sind der
  groesste neu erzeugbare Posten** (cargo baut sie neu), danach `Ausgemustert` (eigene
  Quarantaene der letzten Wochen, groesste: `windows11-20261014` 6,6, `c-entlasten-20260930` 3,6).
- **Nichts davon geloescht.** Loeschen nur nach ausdruecklichem Ja von Max, vorher Inhalt
  pruefen (nicht nur Groesse). `target` unter einem laufenden Handelslauf nicht anfassen
  (13 `omnitrade-cli`-Prozesse laufen aus diesem Baum).

**Nachtrag 21.10.2026 abends - O: nur noch 9,0 GB frei:**
- Der Freiraum sprang im Tagesverlauf 29,3 -> 21,8 -> 9,2 GB. Eine **laufende** Schreiblast war
  um 22:40 nicht zu finden: Freiraum ueber 189 s unveraendert, in den letzten 20 min nur
  `jev-trader\data\events.jsonl` (0,73 GB, wachst ~0,1 MB/min) und `omnitrade` (242 MB) beschrieben.
  Der Verursacher des Tagessprungs ist **nicht belegt**; Kandidaten waren Cargo-Builds und die
  Zweitkopie (21:00), beide ohne Dauerzuwachs gemessen.
- **Docker-Platten sind nicht gewachsen:** `DockerDesktopVMM\DockerDesktop.vhdx` 31,4 GB und
  `DockerDesktopWSL\disk\docker_data.vhdx` 27,4 GB, beide identisch zum 19.10. (zusammen 58,8 GB).
  `docker system df`: Images 16,1 GB (5,5 GB freigebbar), 29 Container, 27 laufen. VHDX schrumpfen nie
  von selbst; am 11.10.2026 brachte das Kompaktieren 14 GB (8,8 -> 22,7 GB frei). Routine
  `Agenten/Routinen/docker-platten-kompaktieren.ps1` (Aufgabe `MaxHirn-Docker-Platten`, woechentlich,
  **Admin**, nur wenn O: unter 15 GB). Sie **stoppt alle Container** (laufen u.a. 20 freqtrade-Bots und
  `nautilus-demo`) und Docker/WSL - darum nicht ohne Max' Ja und nicht mitten im Handel von Hand starten.
  Log: `Werkstatt\Logs\docker-platten.log` (zuletzt 19.10.: "genug Platz", 26,4 GB frei).
- **Docker kompaktiert 21.10.2026 22:45-22:47 (Max, Admin-Shell, `-Erzwingen`):** `docker_data.vhdx`
  27,4 -> **19,6 GB**, `DockerDesktop.vhdx` unveraendert 31,4 GB (der Hyper-V-Datentraeger schrumpft
  nicht - vermutlich ungenutzt, nicht geprueft), **O: 9,0 -> 23,8 GB frei**. Dauer ~2 min, 27 von 27
  Containern liefen danach wieder ohne Neustart (`nautilus-demo` streamt Kurse, `freqtrade-orb`
  `state=RUNNING`). **Pruefweg:** gemerkte Namen aus `Werkstatt\Logs\docker-platten-container.txt` gegen
  `docker ps -a --format '{{.Names}}|{{.Status}}'` halten, `unhealthy`/`Restarting` suchen; das Skript meldet
  nur "gestartet", nicht "gesund". Nach dem Lauf ist `wsl -l -v` kurz "Stopped" - das ist normal.
  **`DockerDesktop.vhdx` (31,4 GB) ist nach Befund ungenutzt:** Docker laeuft mit `WslEngineEnabled: true`
  und `CustomWslDistroDir=O:\Modelle\DockerDesktopWSL` (dort liegt die benutzte `docker_data.vhdx`); die
  Datei liegt im `SailorDataFolder` (`DockerDesktopVMM`), wurde zuletzt am 11.10. 22:17 geschrieben, am
  21.10. nur vom Kompaktieren gelesen und ist bei laufendem Docker **nicht gesperrt**. Erstellt 02.10.2026.
  Nicht geloescht (Entscheidung Max; vorher Docker-Desktop-Einstellungen auf VMM-Backend gegenpruefen).
  **Unabhaengig davon kaputt:** `puter` und `puter-s3` beendeten sich schon um 21:16 (Exit 1,
  `mkdir volatile/runtime` bzw. rustfs `Permission denied`, os error 13) - Bind-Mount-Rechte, nicht
  das Kompaktieren; nicht repariert.
- **Zweitkopie 21.10. 21:00 Code 1:** gleiche Ursache wie die Ausserhaus-Kopie, `hermes-snap-*.sh.tmp.*`
  unter `profiles\*\cache\terminal` verschwand (FEHLER 2). Fix in `sichern-zweitkopie.ps1` und
  `sichern-ausser-haus.ps1` (`.leases` zusaetzlich), Commit `eaea7184`. Alle drei Kopier-Skripte
  (`sichern`, `sichern-ausser-haus`, `sichern-zweitkopie`) halten diese Ausschlussliste jetzt gleich;
  bei einem neuen fluechtigen Pfad **alle drei** anfassen. Bestaetigung steht aus (naechste Laeufe 21:00/21:30).