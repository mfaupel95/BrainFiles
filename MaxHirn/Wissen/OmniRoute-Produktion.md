---
id: 20260907-omniroute-produktion
title: 'OmniRoute-Produktion'
tags: [betrieb, ki-agenten]
created: 2026-09-07
updated: 2026-09-15
related: [20260831-python-versionen, 20260830-verbindungen, 20260907-omniroute-produktion]
summary: 'Der OmniRoute-Quell-Klon (Werkstatt/OmniRoute) ist als Produktions-Router installiert und verifiziert; der Umstieg gegen die globale npm-Instanz ist vorbereitet, aber noch nicht vollzogen.'
---

# OmniRoute-Produktion

## Gratis-Routing: Diagnose vom 08.09.2026

- `best/free` ist in der laufenden globalen Version 3.8.50 keine Gratis-Route: Der Chat-Test scheitert mit `No active credentials for provider: best.`. Ein Modellname allein belegt keine Kostenfreiheit.
- Gueltige Katalogeintraege sind `auto/best-free` und `auto/coding:free`. Beide Kandidatenvorschauen lieferten hier nur Felo-Modelle, die der installierte Free-Tier-Katalog mit `tos: avoid` markiert. Deshalb nicht als Standard eingerichtet.
- `openrouter/openrouter/free` ist vorhanden, scheitert aber an der als abgelaufen markierten OpenRouter-Verbindung. Anmeldung im Dashboard erneuern und danach Chat- sowie Responses-API testen. Keine Schluessel in Chat oder Protokolle kopieren.
- `freeAccessPolicy: strict` ist strenger als `hidePaidModels`: Nur das Ausblenden bezahlter Modelle prueft keine erschoepften Freikontingente oder Anschlusskosten. Globale Aenderungen betreffen andere Clients und benoetigen eine eigene Freigabe. Kein kostenpflichtiger Fallback aktiviert.
- Sicherungen: `~/.codex/config.toml.bak-20260908-220817`, `~/.omniroute/.env.bak-20260908-220817`, `~/.omniroute/storage.sqlite.bak-20260908-220917`. Dateikopien per SHA-256 verglichen; laufende WAL-Datenbank ueber die SQLite-Online-Backup-API gesichert und mit `PRAGMA quick_check` geprueft. Konfiguration und `.env` unveraendert. Eine Datenbank-Wiederherstellung erfordert gestopptes OmniRoute.

## Autostart-Falle (Fund 09.09.2026)

Ein Windows-Neustart (Docker-Reparatur) hat die globale Installation wieder
hochgefahren, obwohl seit 08.09.2026 der Quell-Klon Produktion ist: der
**Autostart-Ordner** (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`)
enthielt `OmniRoute.vbs` und `OmniRoute Server.lnk`, beide starten
`omniroute serve` aus der globalen npm-Installation. Der Umstieg vom
08.09.2026 hatte nur den laufenden Prozess gestoppt, nicht diese Einträge.

Folge: globale Instanz blockierte Port 20128, ihre Provider-Credentials
(github/claude) waren nicht mehr entschlüsselbar (`STORAGE_ENCRYPTION_KEY`
passte nicht mehr) → Hermes bekam `HTTP 401: User not found`.

**Fix:** Beide Autostart-Dateien umbenannt (`.disabled-20260909`-Suffix,
nicht gelöscht), globale Prozesse gestoppt, Quell-Klon über
`omniroute-quell-produktion.ps1` neu gestartet. Verifiziert: `/v1/models`
200, `auto/best-coding` liefert eine echte Antwort.

**Wenn der Quell-Klon je wieder als Autostart gewünscht wird:** einen neuen
Eintrag anlegen, der `npm run start` in `Werkstatt/OmniRoute` aufruft — nicht
die alten Dateien reaktivieren, die zeigen auf die globale Installation.

Siehe auch [[Verbindungen]].

Stand 07.09.2026. Der OmniRoute-Router laeuft als **globale npm-Installation**
(`omniroute serve`, Port 20128) und wird von allen Agenten benutzt (Hermes,
Claude Code, Codex). Zusaetzlich ist der **Quell-Klon**
`Werkstatt/OmniRoute/` (Branch `release/v3.8.51`) als Produktions-Kandidat
vorbereitet.

## Quell-Installation (abgeschlossen 07.09.2026)

- `npm install`: 2518 Pakete, `.env` aus `.env.example` erzeugt (47 Keys).
- Native Module verifiziert (`libxmljs2`, `onnxruntime-node` laden; node-gyp
  brauchte MSVC — installiert).
- Smoke-Test + `npm run omniroute:verify`:
  **Gateway PASS, Catalog PASS (1940 Modelle), Pools/Allocations/Status PASS.**
  Der Quell-Klon ist damit nachweislich produktionsfaehig, inkl. Kernmodule.
- **5 Install-Skripte** sind von `allow-scripts` uebersprungen (playwright,
  bun, libxmljs2, onnxruntime-node, opencode-ai). Die nativen laden auch ohne;
  die restlichen sind optionale Dev-/Browser-Module. **Blockieren nichts.**

## Umstieg Global -> Quell (vorbereitet, NICHT vollzogen)

**Entscheidung steht noch aus**, und zwar: WANN. Es gibt keinen technischen
Hinderungsgrund mehr. Aber Quell und global teilen sich
`~/.omniroute/storage.sqlite` — **nie beide gleichzeitig laufen lassen.**

Abwaegeung (Vor-/Nachteile): Fuer Quell spricht eine zentrale git-versionierte
Code-Quelle, update/patch unter Kontrolle (`git pull` + `npm install` statt
`npm update -g`), debugbarer Stacktrace, Konsistenz mit dem Rest des Systems
unter `BrainFiles/`. Dagegen: kurzes Betriebsfenster beim Umschalten (Router
muss stoppen; Agents sind kurz unterbrochen), mehr eigene Wartung nach
Updates.

Wechsel-Skript: `Werkstatt/Projekte/OmniRoute/omniroute-quell-produktion.ps1`
(bricht ab, wenn Port 20128 belegt ist → schuetzt die laufende Instanz vor
Doppelstart; startet sonst Quell-`npm run start`, wartet auf Port, laesst
`omniroute:verify` laufen). **Wichtig: Nur ausfuehren, wenn keine
Hermes-Agenten am Router arbeiten.**

**Umstieg vollzogen (08.09.2026):** Der Quell-Klon ist jetzt die Produktion.
`npm run build` war erfolgreich (BUILD_ID, Standalone-Bundle komplett), und der
Wechsel wurde durchgefuehrt: globale npm-Instanz samt Auto-Restart-Launcher
(`serve --max-restarts 10`) gestoppt, Quell-Router via
`omniroute-quell-produktion.ps1` gestartet. Verifiziert: PID 49024 =
`node scripts/dev/run-next.mjs start` (Quell-Klon), `/v1/models` -> 200,
Katalog 1943 Modelle inkl. `auto/best-coding`. **Achtung** die globale
Installation startete sich selbst neu (`--max-restarts 10`); beim Wechsel
musste die gesamte Prozesskette (cmd-wrapper 36972, Launcher 37240/37332,
Worker) gestoppt werden, nicht nur der Server.

## Betriebsregeln

- **Never zwei OmniRoute-Instanzen auf derselben SQLite.** Quell und global
  teilen `~/.omniroute/storage.sqlite`.
- Quell-Produktion startet per `npm run start` aus dem Quell-Klon (kein
  separates build noetig; bundelt selbst, `bundler=production`).
- `npm run dev` braucht Schreibplatz fuer `.build/` (Turbopack-Cache); bei
  vollem Datentraeger bricht es mit os error 112 ab.

## Anthropic-Verbindung (14.09.2026)

- Die Verbindung `anthropic` (id `e5573eb3-97dd-456c-9830-9721cf54caa5`) war seit
  dem 01.09.2026 **inaktiv** und trug in `provider_specific_data`
  `baseUrl: http://localhost:20128/v1` — also den Router selbst als Ziel.
  Korrigiert auf `https://api.anthropic.com/v1`, den Wert, den der Code selbst
  als `ANTHROPIC_COMPATIBLE_DEFAULTS.baseUrl` fuehrt.
- **Weg ohne Dashboard:** `PUT /api/providers/<id>` mit
  `Authorization: Bearer <OMNIROUTE_ADMIN_API_KEY>` und Rumpf
  `{"apiKey": …, "name": …, "providerSpecificData": {…}}`, danach
  `POST /api/providers/<id>/test`. Der Key wird serverseitig mit
  `STORAGE_ENCRYPTION_KEY` verschluesselt abgelegt. Fertiges Skript:
  Hermes-Skill `omniroute-betrieb` →
  `scripts/anthropic-verbindung-setzen.py` (liest die Werte aus
  `HKCU\Environment`, gibt nie Schluessel aus).
- Ein **leerer** `baseUrl` wird abgelehnt („providerSpecificData.baseUrl must be a
  valid http(s) URL"), und die Felder werden gemerged — einen falschen Wert also
  gezielt ueberschreiben, nicht weglassen.
- **Zustand:** Anmeldung in Ordnung (Verbindungstest `valid: true`), aber die
  Route traegt nicht: der Console-Key hat kein Guthaben, ein Chat-Aufruf
  antwortet `400 [anthropic] Your credit balance is too low…`. Die
  Credential-Health hat die Verbindung daraufhin selbst wieder auf
  `is_active=0`, `test_status=credits_exhausted` gesetzt — das ist gewollt, sie
  soll `auto/*` nicht mit Fehlversuchen fluten. Nach dem Aufladen: im Dashboard
  testen (oder das Skript erneut laufen lassen), dann kommt sie von selbst in die
  Pools. `auto/claude-opus` antwortet bis dahin `503 Maximum combo retry limit
  reached` (Pool 817, 30 Versuche).
- Daneben liegen zwei weitere Eintraege: `main-2` (ohne Key, inaktiv) und
  `claude` (OAuth aus dem Claude-Abo, `test_status: expired`,
  `no_refresh_token`). **Letzterer ist der kostenlose Weg fuer den Router** — er
  braucht nur Max' Browser-Anmeldung im Dashboard.
- Nicht angefasst: `domain_budgets`, die beiden Alt-Eintraege und der laufende
  Router. Sicherung vor dem Eingriff:
  `~/.omniroute/db_backups/db_20260914-200033_anthropic-schluessel.sqlite`.

## Verbindungen und Combos (15.09.2026)

- **Der Router lief — die Startmeldung war falsch.** Das Protokoll
  `~/.omniroute/logs/quell-produktion/start-20260915-161749.log` zeigt zwischen
  16:17 und 18:56 laufende Anfragen mit `status=200` (Combo `auto/best-free`
  über `oc/big-pickle`); die Verifikation des Starters meldete trotzdem
  `Verification: FAIL (This operation was aborted)` und der Wrapper schrieb
  „ENDE FEHLER: Router kam auf Port 20128 nicht hoch". Um 21:26 neu gestartet
  (Aufgabe `MaxHirn-OmniRoute`): Port offen, PID 57492, `/v1/models` = 401.
  **Offen:** die Verifikationsstufe im Starter bricht zu früh ab und erzeugt
  einen Fehlalarm, während der Router trägt.
- **`openrouter` deaktiviert** (`is_active=0`, id `1c6046da-…`): in 7 Tagen 530
  Chat-Aufrufe, davon **2 erfolgreich**. Alle Fehler aus Guthaben-/Limit-Klassen
  (`402 requires more credits`, `403 Key limit exceeded (monthly limit)`,
  `401 No cookie auth credentials`, `504 Model test deadline exceeded`). Nach
  der Regel „tote Verbindungen deaktivieren" fallen seine Modelle damit aus den
  `auto/*`-Pools; vorher kosteten sie bei jedem Dispatch Fehlversuche und
  Latenz. Aktiv bleiben: `claude`, `gemini`, `ollama-local`, `opencode`.
- **Pool `auto/best-coding` danach:** 10 Kandidaten — neun `claude/*` (Abo) und
  `oc/big-pickle`. Keiner ausgeschlossen (`freeAccessExclusion: null`).
- **Live-Nachweis:** `auto/best-coding` → HTTP 200 in 3,5 s, Zielmodell
  **`claude-opus-5`**; `auto/best-free` → HTTP 200 in 1,6 s über `big-pickle`.
  Damit trägt auch die Hermes-Delegation wieder, die beide Configs auf
  `delegation.provider: omniroute` / `model: auto/best-coding` stehen haben.
- **Die Claude-Abo-Verbindung ist nicht mehr abgelaufen:** `claude` ist
  `is_active=1`, `test_status=active` (am 14.09.2026 noch `expired` /
  `no_refresh_token`) und jetzt der Träger von `auto/best-coding`.
- Sicherung vor dem Eingriff:
  `~/.omniroute/db_backups/db_20260915-212415_gegen-probefunde.sqlite` (77,5 MB,
  SQLite-Online-Backup). Nicht angefasst: `domain_budgets`, die übrigen
  inaktiven Verbindungen (`anthropic` 2×, `github`, `huggingface`, `mlx-qwen`,
  `nous-research`), der laufende Router.
