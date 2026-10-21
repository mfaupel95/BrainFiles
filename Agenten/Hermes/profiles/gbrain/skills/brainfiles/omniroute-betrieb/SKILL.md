---
name: omniroute-betrieb
description: "Use when OmniRoute-Gateway optimieren: Routing, Kosten."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [omniroute, gateway, routing, kosten, provider, brainfiles]
    related_skills: [hermes-config-ops]
---

# OmniRoute-Gateway betreiben

OmniRoute (Port 20128, Quell-Klon `Werkstatt/OmniRoute`) ist Max' AI-Gateway:
ein Endpunkt fuer viele Provider, mit auto/*-Routing, Combos, Caching,
Komprimierung und Budgets. Hermes, Claude Desktop und die Bots haengen daran.

## Kernwissen: Wo die Config liegt

- **Die Config liegt in `~/.omniroute/storage.sqlite`** (SQLite, vom Dashboard
  verwaltet) — NICHT in YAML. Die `.env` daneben haelt nur Laufzeit-Schalter
  (Cache-TTL, Rate-Limit, Kompression, Host/Port).
- Wichtige Tabellen:
  - `key_value` — Routing-Eintraege (`auto/best-coding:auto/best-coding` ->
    {provider, connectionId}), Preiskataloge je Provider, Settings wie
    `promptCacheEnabled`, `semanticCacheEnabled`, `activeComboId`.
    **Enthaelt auch Tokens/Secrets** — Dumps redigieren (Laenge statt Wert),
    nie ungefiltert ausgeben.
  - `provider_connections` — die einzige Wahrheit ueber angeschlossene
    Anbieter: `is_active`, `test_status`, `error_code`, `default_model`.
    **Credential-Spalten nie selektieren** (`api_key`, `access_token`,
    `refresh_token`, `id_token`, `provider_specific_data`): erst die
    Spaltenliste holen und nach Namensmuster filtern
    (`key|token|secret|auth|password|credential|encrypt|signature`), dann
    gezielt selektieren — ein `SELECT *` schreibt Zugangsdaten in die Ausgabe.
  - `usage_history` hat **andere Spaltennamen** als `call_logs`
    (`tokens_input`/`tokens_output` gegen `tokens_in`/`tokens_out`) — ein aus
    dem anderen Log abgeschriebener Ausdruck scheitert mit „no such column“.
  - `domain_budgets` — Monatsdeckel je API-Key (bei Max 5 $/15 $). Vor der
    Aussage "alles gratis" pruefen, ob ein Key-Limit schon erreicht ist
    (403 "Key limit exceeded").
  - `call_logs` / `usage_history` — Ground Truth je Request: provider, model,
    status, Tokens, Cache-Reads. Quelle jeder Kosten-/Fehlerdiagnose.
- Read-only zugreifen:
  `sqlite3.connect('file:C:/Users/faupe/.omniroute/storage.sqlite?mode=ro', uri=True)`.
- **Die Regeln von `auto/*`, die Zero-Cost-Politik und das Kosten-Tracking
  stehen in den Docs des Quell-Klons**: `Werkstatt/OmniRoute/docs/routing/AUTO-COMBO.md`,
  `docs/routing/STRICT_ZERO_COST.md`, `docs/guides/COST_TRACKING.md`. Vor dem
  Nachbauen lesen — das Dashboard zeigt den Ist-Stand, nicht die Regel.

## Ablauf: Optimierung auf kostenlose, gesunde Pfade

1. **Backup vor jedem Schreibzugriff**: `src.backup(dst)` ueber die
   SQLite-Backup-API (WAL-sicher, der laufende Server bleibt unberuehrt) nach
   `~/.omniroute/db_backups/db_<ts>_<grund>.sqlite`. Keine rohe Dateikopie.
2. **Diagnose**: `scripts/router-diagnose.py` (read-only) — Fehler je
   Provider (7 Tage), Top-Modelle je Combo, Verbindungsstatus, Budgets.
   Auf `path='/v1/chat/completions'` filtern — Health-Check-Laeufe je Stunde
   erzeugen `connection-test`/`model-sync`-Noise in den Logs.
3. **Tote Verbindungen deaktivieren** (`is_active=0`): abgelaufene OAuth
   (`no_refresh_token`), unerreichbare Server (ECONNREFUSED), erschoepfte
   Credits (402). Sie verstopfen die auto/*-Pools und erzeugen tausende
   Fehlversuche pro Woche (belegt: github 7.950 Versuche, 6.980 Fehler).
   Der klassische Fall in `call_logs` sind hunderte Aufrufe und fast keine
   Erfolge, deren Fehler **alle** aus einer Guthaben-/Limit-Klasse stammen
   (402 `requires more credits`, 403 `Key limit exceeded (monthly limit)`,
   401 `No cookie auth credentials`) — die ist ohne Geld nicht zu reparieren und
   kostet bei jedem Dispatch Zeit. Ablauf: erst Backup (Schritt 1), dann
   `UPDATE provider_connections SET is_active=0 WHERE provider='<name>'` plus
   `commit`; der laufende Server liest die Pools frisch aus der DB, ein Neustart
   ist weder noetig noch erwünscht. Danach den Pool erneut zeigen — die Modelle
   der stillgelegten Verbindung muessen aus
   `GET /v1/auto-combo/<channel>/candidates` verschwunden sein.
   Eine Verbindung mit echten Erfolgen in den letzten Tagen NICHT
   deaktivieren, auch wenn der Health-Test 401 meldet (belegt: gemini 40 OK-
   Calls bei „Missing API key“ im Test-Endpunkt) — `call_logs` ist die
   Wahrheit, nicht der Test-Endpunkt.
4. **Lokale Modellnamen am Dienst pruefen**, nicht aus Configs abschreiben:
   `curl -s http://127.0.0.1:11434/api/tags`. `default_model` der
   ollama-local-Verbindung korrigieren, wenn er auf nicht existierende Namen
   zeigt (`gemma4:26b` statt `gemma-e4b-8k:latest` -> 166/173 Fehler).
5. **Live-Nachweis** (niemals nur den DB-Stand melden):
   - Key aus der Registry in eine Variable, nie ausgeben:
     `KEY=$(powershell.exe -NoProfile -Command "[Environment]::GetEnvironmentVariable('OMNIROUTE_API_KEY','User')" | tr -d '\r')`
   - Pool zeigen: `GET /v1/auto-combo/<channel>/candidates` (z. B.
     `best-coding`) — Kandidaten tragen `freeAccessExclusion` (null = nicht
     ausgeschlossen).
   - Request: `POST /v1/chat/completions` mit `model: auto/best-fast` und
     kleinem Prompt -> 200 plus gemeldetes Zielmodell.

## Betrieb: starten, pruefen, Varianten unterscheiden

- **Zwei Varianten, nie beide gleichzeitig**: der Quell-Klon
  (`Werkstatt/OmniRoute`) und die globale npm-Installation teilen sich
  `~/.omniroute/storage.sqlite`. Erst die laufende stoppen, dann die andere
  starten.
- **Startskript**: `Werkstatt/Projekte/OmniRoute/omniroute-quell-produktion.ps1`
  (Quell-Klon -> Produktion). Es **bricht mit Exit 1 ab, wenn Port 20128 belegt
  ist** — das ist der gewollte Schutz der laufenden Instanz, kein Fehler.
  Niemals umgehen, auch nicht auf Ansage „starte das Skript“: erst pruefen, ob
  schon einer laeuft, und den Abbruch selbst als Befund melden.
- **Den Router nie ueber eine Pipe starten.** `Agenten/Routinen/omniroute-start.ps1`
  darf das Startskript nicht mit `& ... | Add-Content` aufrufen: das Startskript
  startet einen Dauerprozess, der diese Pipe offen haelt - der Aufrufer kehrt nie
  zurueck. Folgen (Fall 16.09.2026): die Aufgabe blieb „Running“, das eigene
  Protokoll war von aussen gesperrt (`Get-Content`: „Device or resource busy“),
  und als die Aufgabe beendet wurde (das Startprotokoll endet mit `^C`), starb der
  Router mit - 5,5 Stunden Ausfall, den niemand bemerkte. Richtig:
  `Start-Process -WindowStyle Hidden` (eigene Konsole, eigener Prozessbaum) und
  **selbst** auf den Port warten; die Rueckkehr des Wrappers ist der Befund
  (Nachweis: Router gestoppt, Wrapper von Hand - Exit 0 nach 18 s).
- **Wache: Hermes-Cron `omniroute-waechter`** (alle 15 Minuten, `no_agent`,
  Skript `Agenten/Hermes/scripts/omniroute-waechter.py`). Leere Ausgabe heisst
  „Router laeuft“; faellt er aus, kommt eine Telegram-Nachricht mit
  Aufgaben-Zustand, Startversuch und Nachmessung. Sie meldet ueber den
  Scheduler, nicht ueber den Router - eine Wache darf nicht den Weg benutzen,
  den sie ueberwacht. Alarmrichtung ohne Eingriff pruefen:
  `--port 9999 --nicht-starten`.
- **Welche Variante laeuft?** Nicht raten, den Lauscher fragen:
  `Get-NetTCPConnection -LocalPort 20128 -State Listen`, dann die `CommandLine`
  des PID. `node scripts/dev/run-next.mjs start` aus `Werkstatt/OmniRoute` =
  Quell-Klon; ein Pfad aus dem globalen npm-Prefix = globale Installation.
  `netstat` nicht parsen: die deutsche Anzeige schreibt „ABHOEREN“ mit Umlaut
  und wird als Binaer fehlgedeutet.
- **Logs**: `~/.omniroute/logs/quell-produktion/start-<ts>.log` und `.log.err`
  daneben. Bei Start- und Betriebsproblemen zuerst diese beiden, nicht das
  Dashboard.
- **Ein gemeldeter Startfehler ist kein Beleg fuer einen toten Router.** Der
  Starter hat eine eigene Verifikationsstufe; bricht sie ab (`Verification: FAIL
  (This operation was aborted)`), schreibt der Wrapper
  „ENDE FEHLER: Router kam auf Port 20128 nicht hoch“, **waehrend der Router
  traegt**. Das Dienstprotokoll zeigt dann laufende Anfragen (`status=200`,
  `Model ... succeeded`, Combo-Zeilen). Vor jedem Neustart deshalb: nach
  solchen Erfolgen im *Dienst*-Protokoll suchen **und**
  `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:20128/v1/models`
  proben (401 = laeuft). Erst wenn beides fehlt, ist er wirklich nicht
  hochgekommen; die ungeduldige Verifikationsstufe ist dann ein eigener Befund,
  kein Router-Ausfall.
- **Lebendnachweis ohne Secret-Ausgabe**:
  `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:20128/v1/models`
  -> **401 ohne Key** (laeuft, verlangt Auth), **200 mit gueltigem Key**. Ein
  401 heisst also *nicht* „Router tot“.
- **Das Netzwerk ist die haeufigste Wurzel, nicht der Provider.** Die `.env`
  kann alle ausgehenden Abrufe ueber einen lokalen Proxy schicken. Laeuft der
  nicht, scheitert **jeder** Fetch doppelt (`ECONNREFUSED` auf `::1:<port>`
  *und* `127.0.0.1:<port>`) und es sieht nach Provider-Ausfall aus: ModelSync
  424/502, leere `auto/*`-Pools, „no plan-included connection has verified
  quota headroom“. Vor jeder Provider-Diagnose pruefen, ob der Proxy-Port
  wirklich lauscht — und den Port tot nennen, nicht den Anbieter.

## Pitfalls

- **GGUF-Modellnamen (Q4_K_M, Q8_0, ...) sind lokale Namen.** Als Default in
  einer Client-Config landen sie als 403/402-Sackgassen, weil der Router ein
  bezahltes Pendant probiert (Fall: `Qwen3.6-35B-A3B-UD-Q4_K_M` -> OpenRouter
  403 Key-Limit, HuggingFace 402 Credits leer). Modellnamen immer am Dienst
  holen.
- **auto/*-Pools enthalten Kandidaten ALLER aktiven Verbindungen.** Eine tote
  Verbindung muss deshalb aktiv deaktiviert werden — sonst bleiben ihre
  Modelle Kandidaten und scheitern bei jedem Dispatch (Erfolgsrate + Latenz).
- **`group` ist SQL-Schluesselwort** — in SELECTs auf `provider_connections`
  als `"group"` quoten, sonst SyntaxError.
- **Fehlerklassen im error_summary lesen statt raten**: 402/403 = Guthaben
  leer/Key-Limit, 404 = Modellname/Modell weg, 400 „prompt token count
  exceeds“ = Kontext ueber der Modellgrenze, 429 = Rate-Limit. Eine
  Verbindung, deren Fehler nur aus einer Klasse besteht, ist gezielt
  reparierbar statt pauschal „tot“.
- **Katalog-Provider ohne Verbindungszeile** (felo-web, opencode-zen) sind
  nicht ueber `provider_connections` abschaltbar; sie tauchen weiter in den
  Logs auf, werden aber vom Circuit-Breaker/LKGP gemieden. Nicht daran
  festbeissen.
- **Cache ist der groesste Hebel und bleibt stehen**: `promptCacheEnabled` +
  Upstream-Cache-Reads (90 %+ der Input-Tokens bei laengeren Sessions). Der
  semantische Cache kann 0 Hits haben, ohne dass etwas kaputt ist
  (Embedding-Quelle fehlt still) — nicht als Fehler behandeln.
- **Eigene Fehlerheilung nicht mit einem Ausfall verwechseln.** Der Router
  raeumt selbst auf (`[ConnectionRecovery] proactively restored N
  connection(s)`, `[CredentialHealth] Testing n/n`,
  `[ProviderLimitsSync] Cycle complete`, `Account ... error cleared`). Immer
  die **neuesten** Logzeilen lesen, bevor ein Provider fuer tot erklaert wird.
- **`[Encryption] Failed to decrypt credential(s)` / „Decryption failed … Auth
  tag validation likely failed“ = Schluesselwechsel.** Die betroffenen
  Verbindungen sind dauerhaft unlesbar, bis neu authentifiziert wird oder
  `STORAGE_ENCRYPTION_KEY` wieder zum gespeicherten Ciphertext passt. Das ist
  **kein** Provider-Ausfall und durch Routing-Reparatur nicht zu beheben —
  als eigenen Befund melden.
- **`REQUIRE_API_KEY=false`** laesst einen ungueltigen Bearer anonym
  durchfallen („falling through to anonymous“, `key_id=…`). Lokal vertretbar,
  aber im Bericht nennen, sobald der Router nicht nur auf 127.0.0.1 lauscht.
- **Hermes-Clients lesen je nach HERMES_HOME eine andere Config**; die
  laufende Gateway-Instanz die Projekt-Config, CLI ohne HERMES_HOME die
  AppData-Config. Nach Router-Fixes beide Ablagen auf denselben Stand ziehen
  (Details: Skill `hermes-config-ops`).

## Eine Provider-Verbindung anlegen oder reparieren (Admin-API)

Der Dashboard-Weg ist nicht der einzige; die Management-API ist scriptbar:

1. **Schluessel lesen, nie ausgeben.** Werte aus `HKCU\Environment` per
   `winreg` holen (nicht aus der Kommandozeile), in die Variable laden und den
   Request im selben Prozess bauen — dann steht kein Secret in `argv` oder im
   Verlauf. Fertig: `scripts/verbindung-setzen.py`
   (`--sichern|--setzen|--pruefen|--anfrage`).
2. **Sichern** ueber die SQLite-Backup-API nach `~/.omniroute/db_backups/`.
3. **`PUT /api/providers/<id>`** mit `Authorization: Bearer
   <OMNIROUTE_ADMIN_API_KEY>` (Scope `manage`) und Rumpf `{"apiKey": …, "name":
   …, "priority": …, "providerSpecificData": {…}}`. Der Key wird serverseitig
   mit `STORAGE_ENCRYPTION_KEY` verschluesselt; nie selbst in die DB schreiben.
4. **`POST /api/providers/<id>/test`** — der Verbindungstest ist gleichzeitig
   der Aktivierer: `POST /api/providers` legt jede Verbindung mit
   `isActive: false` an, erst ein erfolgreicher Test schaltet sie frei.
5. **Erst danach Pool und echtes Modell pruefen** (`/v1/models`, dann eine
   Anfrage mit dem *vollen* Namen `<prefix>/<model>`).

Fallen dabei:

- **`providerSpecificData` wird gemerged, nicht ersetzt.** Ein falscher Wert
  muss gezielt ueberschrieben werden; ihn wegzulassen laesst ihn stehen (Fall:
  eine anthropic-Verbindung trug `baseUrl: http://localhost:20128/v1`, also den
  Router selbst als Upstream — eine Schleife).
- **Leerstring ist kein gueltiger `baseUrl`** („must be a valid http(s) URL").
  Fuer den offiziellen Anthropic-Sitz den Wert nehmen, den der Code selbst
  fuehrt: `ANTHROPIC_COMPATIBLE_DEFAULTS.baseUrl` =
  `https://api.anthropic.com/v1`.
- **Erschoepftes Guthaben deaktiviert die Verbindung von selbst.** Antwortet der
  Health-Test mit `400 … credit balance is too low`, setzt die
  Credential-Health `is_active=0` und `test_status=credits_exhausted` — gewollt,
  damit `auto/*` nicht mit Fehlversuchen geflutet wird. Die Verbindung bleibt
  also konfiguriert, aber ausserhalb der Pools; nach dem Aufladen erneut testen.
- **Eine aktive Verbindung heisst nicht, dass die Route traegt.** Der
  Verbindungstest prueft die Anmeldung, nicht ein Modell: `valid: true` kann mit
  einem Aufruf zusammenfallen, der am Guthaben scheitert. Immer beides zeigen —
  Test **und** einen echten Chat-Aufruf.
- **Der fuer den Health-Test benutzte Schluessel entscheidet.** Hermes traegt
  eine Anthropic-Anfrage ueber sein OAuth-Abo (Credential-Pool in `auth.json`),
  der Router ueber den eingetragenen API-Key — derselbe Anbieter kann links
  laufen und rechts nicht.

## Nicht anfassen

- Persistierte Kombos (`combos`) nur aktivieren, wenn ihre Modelle am Dienst
  nachgewiesen existieren — veraltete Kombos verweisen auf nicht vorhandene
  Modelle (Fall: `hermes-free-local` mit `ornith-1.5:*`).
- Budgets in `domain_budgets` — der Deckel ist die gewollte Grenze, kein
  Optimierungsziel.
- Den laufenden Server nie neu starten; Aenderungen an `provider_connections`
  liest er pro Pool-Bau frisch aus der DB.
