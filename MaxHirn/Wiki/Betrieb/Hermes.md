---
id: 20260921-hermes
title: 'Betrieb — Hermes'
tags: [betrieb, hermes]
created: 2026-09-21
updated: 2026-10-08
related: ['[[Betrieb/Wachen-und-Aufgaben]]', '[[Werkzeuge/Fundus-Skills-Bots]]', '[[Wissen/Hermes]]']
summary: 'Installation, Pfade, Profile, die wiederkehrenden config.yaml-Fallen, Gateway, Kompression und Delegation.'
---

# Hermes

## Orte

| Was | Wo |
|---|---|
| Programmcode (aktiv) | `Agenten/Hermes/hermes-agent` |
| Projekt-Config (**aktiv**) | `Agenten/Hermes/config.yaml` — `hermes config path` zeigt cwd-unabhaengig hierher |
| AppData-Config | `C:\Users\faupe\AppData\Local\hermes\config.yaml` — existiert, ist NICHT mehr aktiv |
| `hermes.exe` | `Agenten/Hermes/bin/hermes.exe` (vor Aufruf `PYTHONHOME`/`PYTHONPATH` entfernen) |
| Profile | `Agenten/Hermes/profiles/<name>/` |
| Bibliothek | `Agenten/Hermes/skills/` (Archiv: `skills/.archive/` — wird nicht geladen) |
| Cron | `hermes`-Scheduler (nicht die Windows-Aufgabenplanung) |

`C:\Hermes` ist stillgelegt (Altanlage, `C:\Hermes.alt-20260916`). Wenn dort noch etwas
Prozesse startet: `Hermes_Gateway.vbs` / `Hermes_Dashboard.vbs` pruefen — die zeigten
Anfang September noch auf die Altanlage.

## Die wiederkehrenden `config.yaml`-Fallen

1. **`hermes config set` schneidet den Kommentar-Schluss ab** (37 Zeilen Security-/Fallback-Doku
   waren weg) **und schreibt LF in eine CRLF-Datei** (2477 statt 2 geaenderte Zeilen).
   → Vorher kopieren, danach byte-genau zurueckholen, `git diff --numstat` pruefen.
2. **Beide Apps ueberschreiben ihre Config aus eigenem Speicher** — am 10.09.2026 verschwand
   so `mcp-memory` aus beiden Configs. Nach `hermes mcp add/remove` gegentesten.
3. **MCP-Wahrheit** ist `Agenten/MCP-Manifest.json`; Abgleich ueber
   `Agenten/mcp-sync-check.ps1` (steht in `systempruefung.ps1`).
4. **`${env:NAME}`** loest Hermes nur aus der **Prozessumgebung** auf, nicht aus `.env`.
   Provider-Zugangsdaten kommen dagegen aus Credential-Pool (`auth.json`) und `.env` —
   dafuer ist KEIN Gateway-Neustart noetig, fuer `${env:…}`-Aenderungen schon.
5. **Profile sind Inseln:** sie lesen NUR ihr eigenes `auth.json`; ein Root-`auth.json`
   wird nie geerbt. Loesung ist ein **Symlink** `profiles/<bot>/auth.json` → `Agenten/Hermes/auth.json`
   (Hermes unterstuetzt das ausdruecklich: „ein Symlink auf den Root-Store ist kein Klon").
   Werkzeug: `Agenten/Hermes/scripts/auth-verknuepfen.ps1` (braucht Adminrechte).
6. **`hermes profile create <name>` ohne `--clone`** erzeugt nur eine 45-Zeilen-Config:
   kein `providers`-, kein `terminal`-Block, `profile.yaml` fehlt ganz. Nacharbeiten:
   `providers.omniroute` kopieren, `model.provider`/`model.default` setzen, `terminal.cwd`,
   Router-Schluesselnamen in die eigene `.env`, Beschreibung per `hermes profile describe`.

7. **Der Modellwaehler zeigt je Anbieter nicht die volle Liste.** Fuer `nous` zeigt Hermes
   absichtlich nur die kuratierte Liste des Manifests (`model_switch_providers._nous_picker_model_ids`:
   „the picker shows ONLY the curated agentic list") - 50 Eintraege plus die Empfehlungen des
   Portals, waehrend das Portal ueber `/v1/models` **428** Modelle liefert. Die von Hermes
   vorgesehene Stelle zum Erweitern ist `providers: nous: models:`; die Waehler-Zeile bleibt
   `source: hermes` und behaelt ihre Anmeldung. Werkzeug:
   `Agenten/Hermes/scripts/nous-modellliste-richten.py` (Trockenlauf / `--anwenden` /
   `--zuruecknehmen` / `--profile`), eingetragen am 01.10.2026 (428 Zeilen, Commit `fc395e3`).
   Derselbe Mechanismus gilt fuer JEDEN Anbieter mit kuratierter Liste.
8. **Die App schreibt die Config aus ihrem eigenen Speicher zurueck.** Am 01.10.2026 um 18:45
   stand ein Diff von 19/26 Zeilen gegen HEAD im Arbeitsbaum, den keine Sitzung geschrieben
   hatte: `bonsai`- und `smart`-Provider-Block entfernt, `moa.enabled` false -> true,
   `personality` creative -> helpful, telemetry, `desktop.repo_scan_roots`. Ein so
   zurueckgeschriebener Stand loescht auch frisch eingetragene Bloecke - nach jeder
   Einstellungsaenderung in Desktop/TUI nachzaehlen (`grep -c "claude-opus-4.1:batch"
   Agenten/Hermes/config.yaml` muss 1 sein). Offen als T-297.

8. **Ausgeschaltete MCP-Eintraege sind seit 21.10.2026 sichtbar (T-434).** Sieben
   OAuth-Kandidaten (gitlab, airtable, deepwiki, buildkite, circleci, algolia, postman)
   standen in `Agenten/Hermes/config.yaml` als `enabled: false`, fehlten im Manifest und
   wurden vom Pruefer nie genannt - er strich ausgeschaltete Eintraege aus BEIDEN
   Namenslisten. Entfernt per `hermes -p default mcp remove <name>` (raeumt auch die
   OAuth-Tokens; ein reiner Textschnitt liesse sie stehen - die Meldung lautet
   'Cleaned up OAuth tokens'), dokumentiert unter `disabled` im Manifest mit URL, Grund
   und Rueckholbefehl. Der Pruefer meldet einen ausgeschalteten Eintrag ohne
   Manifest-Eintrag jetzt als `HINWEIS` (Exit bleibt 0, es ist keine Drift). Beleg:
   `Agenten/Routinen/tests/mcp-sync-check.test.ps1` (19 Pruefungen).

**Nachtrag 01.10.2026: die BOT-PROFILE tragen jetzt das Gegenteil.** Auf Auftrag Max
(„die botprofile brauchen noch weniger") sind die `models:`-Listen der 19 Profile, die je
~1.739 Eintraege aus der omniroute-Liste mitkopiert hatten, auf das gekuerzt, was das Profil
selbst nennt (`model.default`, `providers.<p>.model`/`default_model`, `fallback_providers`,
`delegation.model`, `moa`): **33.064 -> 125 Eintraege**, caveman 2248 -> 514 Zeilen,
hermes-wartung 1811 -> 79. Der `models:`-Block eines Profils ist eine Anzeigeliste; die Wahl
bleibt vollstaendig, weil `discover_models: true` bleibt und der Waehler mit gesetztem
Schluessel die echte Liste live vom Endpunkt holt (`_discover_endpoint_models`). Werkzeug:
`Agenten/Hermes/scripts/profil-modelllisten-kuerzen.py` (Trockenlauf Standard, `--anwenden`,
`--zuruecknehmen`), Pruefungen `Agenten/Hermes/scripts/test_profil_modelllisten_kuerzen.py`
(17, auf Kopien). Offen fuer die HAUPTconfig: T-302.

## Gateway

- Der A2A-Gateway ist `python.exe -m hermes_cli.main gateway run` (Launcher-venv → Kind
  `.hermes-runtime-python`), bindet **Port 9900**. `python -m tui_gateway.entry` ist das
  Desktop-JSON-RPC-Backend, lauscht NICHT auf 9900 und ist NICHT der Gateway.
- **Falle (19.09.2026), zweimal schiefgegangen:** Das Waechter-Muster `hermes_cli.main gateway`
  war zu eng (startete alle ~16 min neu, 90 s Ausfall), das „breitere" `tui_gateway` zu
  breit (hielt Desktop-Backends fuer den Gateway, ~12 h echter Ausfall blieb UNERKANNT).
  **Richtig:** Port 9900 ist die erste Wahrheit; nur `hermes_cli.main gateway` zaehlt als
  Prozess; 120 s Boot-Gnadenfrist gegen Churn.
- `Test-NetConnection 127.0.0.1 -Port 9900` als Schnellprobe.

### Gemessener Stand 30.09.2026 (eine Kette, drei PIDs)

Der laufende Gateway ist **eine** Prozesskette, nicht mehrere Dienste:

| PID | Was | Herkunft |
|---|---|---|
| 73620 | Launcher | `hermes-agent\venv\Scripts\python.exe -m hermes_cli.main gateway run` |
| 36840 | Runtime-Kind | `hermes-agent\.hermes-runtime\python\cpython-3.11...\python.exe` |
| 73852 | der eigentliche Dienst | `tools\python-3.14.7+...\python.exe -I -c "... runpy.run_module('hermes_cli.main')"` |

Der Dienstprozess 73852 haelt **`127.0.0.1:9900`** (A2A) und **`0.0.0.0:8644` plus
`[::]:8644`** (Webhook-Plattform) und schreibt `gateway_state.json`. Die Identitaet
steht dort: `pid`, `gateway_state: running`, `code_version`.

Zwei Folgerungen, die beide schon einmal Zeit gekostet haben:

- **Ein Prozessfilter auf `*gateway run*` findet nur 73620 und 36840** - der
  Dienstprozess 73852 traegt wegen der `runpy`-Form gar kein `gateway run` in der
  Kommandozeile. Wer die Prozesszahl prueft, muss beide Formen kennen (Waechter
  lesen deshalb zuerst `gateway_state.json`).
- **`TCP 9900` ist NICHT dauerhaft zu.** Die Notiz vom 29.09.2026 ("lauscht nur
  noch auf dem Control-Pipe") war eine Momentaufnahme: am 30.09.2026 hoert 73852
  wieder auf `127.0.0.1:9900`. Der Port taugt damit weiter als Schnellprobe, aber
  nicht als Beweis fuer einen Ausfall - massgeblich ist Prozess UND Antwort.

**Vor jeder Freigabe ins LAN pruefen:** der Webhook hoert auf `0.0.0.0:8644`, der
OmniRoute-Router auf `0.0.0.0:20128` - beide sind im lokalen Netz erreichbar, nicht
nur auf `127.0.0.1`. Gemessen am 30.09.2026, nicht geaendert.

## Kompression

`compression.threshold` steht auf **0.19**, weil das Kompressionsmodell
(`auto/coding:free`) nur 200k Kontext traegt und die Schwelle darauf deckelt — das
Hauptmodell traegt 786k. Mit einem groesseren Kompressionsmodell darf die Schwelle wieder hoch.

## Delegation (Subagenten)

- Haus-Delegation: `provider=nous`, `model=deepseek/deepseek-v4-flash-0731`;
  `claude-opus-5` bleibt erster Fallback.
- **Kritisch:** Subagenten mit `provider=omniroute` haengen am lokalen Router
  (Port 20128). Ohne Router scheitern ALLE `delegate_task`.
- `max_concurrent_children: 3`.
- **`delegate_task`-JSON-Falle:** `context`/`goal` als EINZEILIGE Strings formulieren;
  Literal-Zeilenumbrueche und lange verschachtelte `output_schema` kippen das Parsing
  („Expecting ',' delimiter"). Absolute Pfade mitgeben — der Subagent sucht sonst relativ
  zu seinem eigenen Arbeitsordner.
- Subagenten-Selbstberichte sind Selbstauskuenfte, kein Beweis: externe Wirkungen
  (Upload, Remote-Schreibvorgang) immer selbst nachpruefen.
## Update und Reparatur (Stand 25.09.2026)

- **Ablauf eines `hermes update`:** Halter-Pruefung -> `git pull` (Autostash) -> Bau von
  Node/TUI/Web/Desktop -> Python-Abhaengigkeiten + Gateway-Neustart. Belegquelle ist
  `logs/update-*.log`; die Wahrheit ueber den Codestand ist `git log -1 --oneline` **im
  Checkout**, nicht die Zeile "Update available: N commits behind" (die zaehlt ab der
  installierten Version und laeuft weit voraus).
- **Exit 1 heisst nicht "Update fehlgeschlagen".** Der Lauf am 25.09.2026 endete mit Exit 1,
  weil EIN Dienst nicht automatisch zurueckkam: "A web dashboard/serve process was stopped
  during update and could not be auto-restarted". Der Code war da schon gepullt und gebaut
  (HEAD 60 Commits weiter, `rev-list --count HEAD..origin/main` = 0). Nachziehen:
  `Start-ScheduledTask -TaskName 'Hermes_Dashboard'`, Beleg danach
  `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119/` = `200`.
- **Abgeloest starten ist Pflicht**, wenn das Update aus einer Sitzung heraus angestossen wird
  (das Update pausiert und startet das Gateway neu). Skript: `Remove-Item Env:PYTHONHOME,
  Env:PYTHONPATH`, `HERMES_HOME` setzen, `venv\Scripts\python.exe -m hermes_cli.main update
  --yes` aus dem Checkout, alles mit `Out-File -Encoding UTF8` in eine Logdatei, Start per
  `Start-Process -WindowStyle Hidden`. PS 5.1 `Tee-Object` schreibt UTF-16 - dann findet
  `grep "Log-Ende"` nichts.
- **Halter zaehlen, nicht raten.** Kanonisch sind
  `hermes_cli.update_cmd_windows._detect_venv_python_processes` und `_hermes_holder_subcommand`.
  Halter sind das Dashboard-PID-Paar (venv-python + `.hermes-runtime`-python), die
  Desktop-Backends und jeder Bot-Lauf `hermes -p <name> chat -q`; das Gateway pausiert das
  Update selbst.
- **Falle (25.09.2026):** Eine Halter-Probe als PYTHON-DATEI (`tmp/venv_halter.py` mit
  `sys.path.insert(0, <checkout>)`) brach in jedem Lauf mit
  `ModuleNotFoundError: No module named 'ruamel'` ab, waehrend derselbe Import per
  `python -c "..."` und `python -m hermes_cli.main` aus demselben venv fehlerfrei lief.
  Eine Probe, die beim Import stirbt, meldet nie "0 Halter" - die Warteaufgabe
  `Hermes-Update-20260921` wartete 45 min und tat nichts. Probe deshalb von aussen aufrufen
  (`-m`/`-c`, cwd = Checkout) und EINMAL gegen einen bekannten Halter gegenpruefen.
- **npm-Audit im Checkout:** `js-yaml` steht doppelt - als direkte Abhaengigkeit und im
  `overrides`-Block (`"js-yaml@^4"`). Nur eins zu heben laesst `npm install` mit
  `EOVERRIDE ... conflicts with direct dependency` abbrechen; beide auf dieselbe Fassung
  (4.3.2), danach `npm audit --json --workspaces=false` = 0. Der Fix liegt nur im Arbeitsbaum
  des Checkouts und wird bei jedem Update mitgestasht/zurueckerstattet.
- **Neu im Lauf vom 25.09.2026: Hermes bringt eine eigene Werkzeugkette mit.** Nach dem Lauf
  liegt `Agenten/Hermes/tools/` mit `python-3.14.7+…`, `git-2.53.0+3`, `node-26.7.0`,
  `npm-12.0.2`, `ripgrep-15.2.0`, `uv-0.12.3`, ffmpeg, chromium und agent-browser, und der
  aktualisierte Launcher `gateway-service/Hermes_Gateway_2ef9d0b7.vbs` startet den Gateway aus
  `tools\python-3.14.7+…\python.exe` mit `VIRTUAL_ENV=<HERMES_HOME>\tools`. Der **Gateway laeuft
  damit nicht mehr aus dem Checkout-venv**; das venv traegt weiter die Desktop-/Dashboard-Backends.
  Halter-Listen also am `ExecutablePath` pruefen, nicht am venv-Pfad festmachen.
- **Doctor-Stand nach dem 25.09.2026:** Python 3.14.7 (Launcher) / SQLite 3.53.1 = **kein**
  WAL-Reset-Bug, Browser-Tools "no known vulnerabilities", `web`/`ui-tui` je 3 moderate
  Advisories (nur zur Kenntnis). Die 18 Restmeldungen sind die Photon-Doppelkennungen aus dem
  gemeinsamen Credential-Store (`profiles/<bot>/auth.json` ist ein Symlink auf
  `Agenten/Hermes/auth.json`) - siehe T-107, T-108, T-109 in `Archiv/TASKS.md`.

### Legacy-Gateway-Starter (T-108, erledigt 25.09.2026)

`hermes gateway status` warnt nach einem Update, wenn noch Starter aus der Zeit VOR den
Pro-Profil-Namen liegen: `gateway-service/Hermes_Gateway.vbs`, `Hermes_Gateway.cmd` und die
gleichnamige geplante Aufgabe. Am 25.09.2026 gemessen:

- Die **Aufgabe `Hermes_Gateway` existierte nicht mehr** - `Get-ScheduledTask` kennt nur
  `Hermes-Update-20260921`, `Hermes_Dashboard` und `Hermes_Gateway_2ef9d0b7`; ein
  `Unregister-ScheduledTask -TaskName Hermes_Gateway` meldet woertlich "keine
  MSFT_ScheduledTask-Objekte mit TaskName Hermes_Gateway". Wer die Warnung liest, also erst
  messen, dann handeln.
- Geblieben waren nur die **Dateien**: `Hermes_Gateway.cmd` zeigte noch auf das stillgelegte
  `C:\Hermes\venv` (Doppelstart-Quelle, falls sie je ausgefuehrt wird), das VBS war schon
  entschaerft. Beide plus die `.alt-20260916`-Kopie liegen jetzt in
  `.sicherung\gateway-service-legacy-20260925\` - nichts geloescht.
- Werkzeug: `Agenten/Hermes/cache/scratch/t108_legacy_gateway.ps1` (verschiebt, meldet ab,
  schreibt jeden Schritt nach `logs/gateway-legacy-entfernen-20260925.log`).
- **Nicht** noetig war der vom Doctor vorgeschlagene Weg `hermes gateway uninstall` +
  `install`: der haette den LAUFENDEN Launcher `Hermes_Gateway_2ef9d0b7` mit ersetzt. Das
  Hausmittel "Datei verschieben, Aufgabe pruefen, laufenden Starter in Ruhe lassen" ist
  kleiner und nachweisbar.
- Danach: Gateway unveraendert (pid 64192, Port 9900, aus `tools\python-3.14.7`),
  `hermes doctor` meldet keine Legacy-Sachen mehr.

### Photon-Doppelkennungen im Doctor sind (fuer die Bots) ein Fehlalarm (25.09.2026)

`hermes doctor` meldet je Bot-Profil "Profiles 'default' and '<bot>' both hold the same photon
credential ... gateway is STANDALONE: profiles NOT served". Gemessen: `PHOTON_PROJECT_ID`,
`PHOTON_PROJECT_SECRET`, `PHOTON_ALLOWED_USERS` und `PHOTON_HOME_CHANNEL` stehen **nur** in der
Haupt-`.env`; kein Bot-Profil hat eigene Photon-Werte. Die Meldung entsteht allein daraus, dass
die `profiles/<bot>/auth.json` **Symlinks** auf `Agenten/Hermes/auth.json` sind - dieselbe
Kennung, je Profil gezaehlt. Die Bots fahren als Einzelauftraege (`hermes -p <name> chat -q`),
nicht als Multiplex-Adapter; es geht dabei nichts verloren. **Nicht** in Versuchung geraten, die
Kennung aus den Profilen zu loeschen - dort steht sie nicht.
Ein echter Fall bleibt zu pruefen: `profiles/awesome-systematic-trading/config.yaml` traegt
einen eigenen `photon:`-Block (dieses Profil hat auch eine eigene `auth.json`) - siehe T-107.

**Erledigt 29.09.2026.** Die Falschmeldung ist stillgelegt: die 18 gemeldeten Profile tragen
jetzt einen eigenen Block

    platforms:
      photon:
        enabled: false

gesetzt mit `hermes -p <profil> config set platforms.photon.enabled false` - das Werkzeug
waehlt die Stelle selbst und schreibt CRLF (18 Dateien je +3 Zeilen, keine Loeschung ausser der
`_config_version`-Zeile, die Hermes ohnehin fortschreibt). Es meldet dabei den Vorrang aus:
"the top-level platforms.photon block outranks gateway.platforms - saved as
platforms.photon.enabled" - wer den Schalter unter `gateway:` setzt, setzt ihn ins Leere.
`hermes doctor` meldet danach **1 Befund statt 19** (offen bleibt nur "Browser tools
(agent-browser) has 1 npm vulnerability"). Der eigene `photon:`-Block von
`awesome-systematic-trading` blieb unangetastet - dieses Profil stand nie in der Liste, was die
Wirkung des Schalters belegt.

### Gateway-Identitaet: warum `hermes update` abbrach - und die Wache dafuer (29.09.2026)

**Symptom.** Jeder Update-Lauf endete nach dem Pre-update-Snapshot mit `exit_code 1` und
`stop_reason: RuntimeError: Could not map Windows gateway PIDs to profiles: Could not inspect
gateway PID for profile default`. Der Code wurde also gepullt, aber nicht gebaut/installiert.

**Zwei Ursachen, beide gemessen:**

1. **Startform.** Der Update-Restart-Watcher startet den Gateway selbst als
   `python -I -c "<bootstrap>" … gateway run`. `gateway.status.looks_like_gateway_runtime_command_line`
   verweigert diese `-c`-Form **absichtlich** (#107002) - der laufende Gateway ist fuer den
   Updater damit unsichtbar. Heilung: den Gateway **klassisch** starten
   (`-m hermes_cli.main gateway run`, so wie es der Launcher
   `gateway-service/Hermes_Gateway_2ef9d0b7.vbs` tut).
2. **Fehlende Identitaetsdatei.** `Agenten/Hermes/gateway.pid` fehlte; die Pruefung brach schon
   mit "active gateway lock has no PID metadata" ab, obwohl `gateway.lock` den laufenden
   Gateway beschrieb. Reparatur: die PID-Datei aus dem Lock rekonstruieren
   (`cache/scratch/gateway-pid-reparieren.py`) - sie ist abgeleitete Angabe, kein Ersatzbeleg.

**Beleg nach der Reparatur.** `find_profile_gateway_processes(strict=True)` ->
`OK: default pid <n>`, und der naechste `hermes update`-Lauf pausiert den Gateway sauber
("1 gateway(s) ACKed socket pause") statt abzubrechen.

**Die Wache.** `Agenten/Hermes/scripts/gateway-identitaet-wache.py`, Cron
`gateway-identitaet-wache` taeglich 08:15 (no_agent, Telegram, **leere Ausgabe = nichts senden**).
Sie prueft GENAU die Bedingung, an der das Update scheiterte (Discovery des laufenden
Gateways), rekonstruiert fehlende PID-Metadaten und startet im Blindfall den Gateway EINMAL
pro Tag klassisch neu - aber nie, solange ein `hermes update` laeuft. Wiederholte gleiche
Feststellungen unterdrueckt sie 6 h lang; ein Neustart wird immer gemeldet.
Tests: `Agenten/Handel/tests/test_gateway_identitaet_wache.py`.

**Der Waechter darf NICHT den Port befragen.** `gateway-identitaet-wache.py` nutzt seit dem
29.09.2026 die Prozessliste (und den Port nur als Rueckfall fuer alte Fassungen): die neue
Fassung lauscht auf einem Named Pipe (`\\.\pipe\hermes-gateway-*`) und bedient Webhooks auf
8644 - **TCP 9900 ist offen oder zu, ohne etwas ueber die Gesundheit zu sagen.** Wer ihn
prueft, haelt einen gesunden Gateway fuer tot (siehe Lektion 10 in
[[Lektionen/Wahrheit-pruefen]]).


### Der Gateway-Waechter hat sich selbst im 2-Minuten-Takt neu gestartet (29.09.2026)

**Symptom.** Nach dem Update startete der Gateway immer wieder neu: `Routinen/logs/gateway-waechter.log`
trug am 29.09.2026 **148 Zeilen** "kein Gateway-Prozess - Neustart ausgeloest" (eine alle zwei
Minuten), `errors.log` dazu 19-mal `exited UNCLEANLY`. Jeder Start reisst die laufenden
Verbindungen mit; Telegram und A2A waren mehrfach kurz weg.

**Ursache (gemessen).** Der Waechter erkannte den Dienst an der Kommandozeile:
`-match 'hermes_cli\.main gateway'`. Diese Zeichenfolge steht nur in der **Launcher**-Form
(`-m hermes_cli.main gateway run`). Der Update-Weg startet den Gateway dagegen als
`-I -c "…runpy.run_module('hermes_cli.main', run_name=…) …" gateway run --replace` - zwischen
`hermes_cli.main` und `gateway run` steht `, run_name=`, das Muster trifft **nicht**
(nachgemessen: 0 Treffer, obwohl der Gateway lief). Der Waechter hielt den gesunden Gateway
fuer tot und startete ihn im Takt seiner eigenen Aufgabe neu.

**Fix.** Zuerst die **Identitaet** aus `Hermes/gateway_state.json` (`pid` + `gateway_state:
running`, vom Gateway selbst geschrieben; der Prozess muss existieren und `python` sein),
die Kommandozeile nur als Rueckfall - und die deckt jetzt **beide** Startformen ab
(`hermes_cli\.main gateway run` ODER `run_module\('hermes_cli\.main'`).
Beleg: die geplanten Laeufe 19:15:13 und 19:15:59 (2-Minuten-Takt) schreiben
"Gateway laeuft (Pipe: True, Port 9900: True), kein Start"; die Neustartzeile endet 19:13:56.
Vorfassung gesichert als `Routinen/gateway-waechter.ps1.bak-20260929`.

**Herkunft.** Die Erkennung wurde an diesem Tag zweimal angefasst. Die erste Reparatur (T-139,
parallele Sitzung) stellte die Pruefung von "Port 9900 ist die Wahrheit" auf die Bedingung um
(laeuft ein Prozess `hermes_cli.main gateway run` ohne `--profile` UND antwortet er per
Control-Pipe oder Port?) und brachte den Merker gegen Dauer-Neustarts. Diese Fassung hier macht
zusaetzlich die **Identitaet** aus `gateway_state.json` zum ersten Zeugen und erweitert den
Rueckfall auf **beide** Starter-Formen. Beide Aenderungen standen beim Commit 51e233f
uncommittet im selben Arbeitsbaum und sind gemeinsam hineingegangen; T-139 nennt den ersten
Teil, dieser Abschnitt den zweiten.

**Merksatz.** Eine Wache, die einen Dienst an der Kommandozeile eines bestimmten Starters
erkennt, faellt bei jedem Starterwechsel um - und danach im Takt der Wache. Wer den Dienst
schon selbst eine Zustandsdatei schreiben laesst, fragt die.

### `hermes update` endet mit `outcome: partial` - und laesst das Dashboard tot (29.09.2026)

Der Lauf um 18:46 war **teilweise** erfolgreich: `logs/update_receipts/latest.json` traegt
`outcome: "partial"`, `gateway_restart.incomplete: true`, `phase_error: "Could not restart
every paused Windows gateway"`, `killed_pids: [60532]`. Der Gateway kam zurueck (Launcher),
das **Dashboard nicht**: Port 9119 war zu, `http://127.0.0.1:9119/` nicht erreichbar - bis
`Start-ScheduledTask -TaskName 'Hermes_Dashboard'` von Hand lief und HTTP 200 lieferte.

**Falle beim Nachpruefen.** Sekunden nach dem Start ist 9119 noch zu: der Dienstprozess
entsteht erst ~13 s nach dem Ausloesen, fertig ist er nach ~45 s. Wer zu frueh misst, meldet
einen Ausfall, den es nicht gibt. Fuer den Dienst selbst ist nichts zu tun (Aufgabe laeuft bei
Anmeldung, `wscript //B` versteckt, LastTaskResult 0); die **Wache fuer das Dashboard** fehlt
(der Gateway hat eine, das Dashboard nicht) - siehe `Archiv/TASKS.md` T-147.

**Offener Rueckstand.** `hermes-agent` steht 18 Commits hinter `origin/main` (HEAD
`ca705dbf7e`, 0.21.5). Der Rest des Update-Wegs ist in Ordnung:
`pm_sync_outcome: ok`, `pm_exit_code: 0`, Arbeitsbaum sauber.

### Zwei Python-Laufzeiten: die im `tools/` hat absichtlich keine Pakete

`Agenten/Hermes/tools/python-3.14.7…/Lib/site-packages` enthaelt **nur `pip`** - und trotzdem
fahren Gateway, Dashboard und Update-Laeufe daraus. Die Fremdpakete kommen zur Laufzeit aus dem
gestagten Umfeld `installs/<hash>/environments/<id>/venv/Lib/site-packages`, das
`hermes_bootstrap` in `sys.path` setzt (nachgemessen: `httpx` und `ruamel.yaml` liegen dort,
`hermes_bootstrap` schiebt den Pfad nach vorn). Wer in diesem Python etwas importiert, **ohne**
den Bootstrap zu laden, sieht `ModuleNotFoundError` und haelt die Installation fuer kaputt -
sie ist es nicht. Fuer Handproben die Checkout-venv `hermes-agent/venv/Scripts/python.exe`
nehmen (3.11.16, 303 Pakete, `ruamel.yaml` vorhanden).

### Leichen im Anmeldeordner: 14 Alias-Wrapper ohne Profil (29.09.2026)

`hermes doctor` meldete 14 "Orphan alias" - die Wrapper liegen nicht im Hermes-Baum, sondern in
`C:\Users\faupe\.local\bin` (`_get_wrapper_dir()`): `agent-reach.bat`, `coder.bat`,
`graphify.bat`, `max.bat`, `nous.bat`, `projectatlas.bat`, `scrapling.bat`,
`superpowers.bat`, `tradingview-mcp.bat`, `winget-cli.bat` u.a. - je ein Profil, das nicht mehr
existiert (sie liegen unter `profiles/.deleted/`). Am 29.09.2026 nach
`~/.local/bin/.orphan-20260929/` verschoben (nicht geloescht), 19 gueltige Wrapper bleiben.

**Nebenbefund, der 18 "Photon"-Befunde erklaert.** Der Doctor zaehlt bei **jedem** Profil die
Photon-Kennung der Haupt-`.env` als eigene - kein Bot-Profil traegt `PHOTON_PROJECT_ID`
(nachgemessen: 0 von 30 Profil-`.env`), ebenso wenig eine Windows-Benutzervariable. Damit ist
die bereits am 25.09.2026 notierte Falschmeldung bestaetigt; sie blaeht den Doctor-Bericht auf
19 Befunde auf und verdeckte die echten. **Behoben am 29.09.2026** (Abschnitt "Photon-Doppelkennungen" oben): die 18 Profile tragen jetzt `platforms.photon.enabled: false`, der Doctor meldet 1 statt 19 Befunde.
## Desktop-Verbindungsfehler: ECONNRESET / 500-Flut auf `/api/*` (08.10.2026)

**Regel: die wiederholte 500-Zeile im Desktop-Log IST die Ursache, der
ECONNRESET nur die Folge.** Electron-Main verliert die HTTP-Verbindung zum
Backend waehrend des Lesens, wenn ein Endpoint 500er spuckt. Die einzige
bekannte (und haeufige) Quelle: `GET /api/local-models/status` poollt im
2-s-Takt, und der Endpoint (`hermes_cli/web_routers/local_models.py`,
`_staged_row`) macht `stat()` auf jede stagede GGUF in
`Agenten/Hermes/models/` — ein **toter Symlink** (Ziel fehlt) wirft dort
ungefangen `FileNotFoundError` -> 500-Flut. `Timed out connecting to Hermes
backend after 30000ms` ist der Nachhall, kein zweiter Fehler.

**Diagnose-Reihenfolge.** (1) `gateway_state.json` — `running` + Plattformen
`connected` heisst: Ursache sitzt im Desktop-Backend-Pfad, ein Gateway-Restart
hilft nicht. (2) `grep -n "hermes:api.*Error" logs/desktop.log | tail` — die
500er finden. (3) `ls -la Agenten/Hermes/models/` auf tote Links pruefen
(erscheinen als `lrwxrwxrwx`). (4) Fix: den toten Symlink loeschen — der
Katalogeintrag bleibt als klickbares Modell im Picker stehen und legt die Datei
beim Download neu an. (5) Nachweis ohne Auth-Token: der Desktop poollt selbst —
keine NEUEN `hermes:api … Error`-Zeilen nach dem Fix (Zeitstempel vergleichen)
ist der Beleg, nicht ein `curl`.

**`models/`-Ordner: drei Schichten getrennt halten.** (1) Katalogeintrag
(`hermes_cli/local_runtime/catalog.json`) ist committeter Quelltext — lassen,
der Picker zeigt ihn nur als Download. (2) Symlink in `Agenten/Hermes/models/`
— NUR diese zaehlt der Status-Endpoint beim `stat()`. (3) Config-Referenz
`qwen/qwen3.6-35b-a3b` in config.yaml ist ein ROUTER-SLUG (Cloud), kein Verweis
auf das lokale GGUF — ein Grep-Treffer in Configs beweist keine lokale Nutzung.
Erst alle drei Fragen beantworten (referenziert jemand die LOCALE Datei? ist der
Eintrag Checkout-Quelltext? passt die Datei in den VRAM?), dann einen Symlink
loeschen — und die Wirkung mit einem Beobachtungsfenster belegen (Anzahl der
`preset skip`-Warnzeilen vorher/nachher, Uhrzeitquellen je Log-Datei nicht
mischen).

**Harmlose Nachbarn, keine Reparatur noetig:** `preset skip Ternary-Bonsai-…`
(der verwaltete llama-server 18434 kann ternäre Gewichte nicht laden; Bonsai
laeuft separat auf 8080) und MCP-Test-500er `POST /api/mcp/servers/<name>/test`
auf nicht angemeldete Server.

**Telemetry-Ordner blockiert:** `telemetry/shared_metrics/` mit `WinError 5`
(selbst der eigene Benutzer kann nicht lesen/loeschen, ein fremder Prozesskontext
hat ihn angelegt) loggt laufend `shared metrics initialization failed` — die
Warnung ist harmlos, der Log-Rauschen bleibt. Reparatur in EINEM erhoehten Lauf:
`icacls <pfad> /grant <user>:(OI)(CI)F /T /C` — kein `takeown` noetig (`takeown
/D Y` ist ungueltige Syntax). Ergebnis am ZIEL belegen, nicht am Log des
elevated Skripts.
