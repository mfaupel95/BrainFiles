---
id: 20261006-sitzungsanalyse
title: 'Sitzungsanalyse — Themen, Fehler, offene Punkte, Erfolge'
tags: [betrieb, ki-agenten, handel, system]
created: 2026-10-06
updated: 2026-10-06
related: ['20260830-index', '20260830-hermes', '20260830-routinen', '20260902-handelsregeln', '20260830-handelsbots', '20260916-repo-bots', '20260916-agent-reach', '20260913-projektatlas', '20260830-wiederholbare-aufgaben', '20260902-systempruefung', '20260830-hardware', '20260830-schutzregeln', '20260830-zugaenge', '20260830-passwoerter-quarantaene', '20260830-steuerunterlagen', '20260830-belege-einspruch-2024', '20260830-profil', '20260830-projekte', '20260830-verbundungen', '20260830-werkzeuge', '20260830-portabilitaet', '20260830-ordnerstruktur', '20260830-fristen', '20260916-optimierungen-finden', '20260910-optimierungen-umgesetzt', '20260911-off-site-backup', '20260910-brainfiles-bus', '20260917-openmontage', '20260916-moon-dev-agenten', '20260917-awesome-systematic-trading', '20260921-archiv-trading-skills', '20260921-prognose-backtest', '20260918-handel-stack-repo', '20260919-moon-dev-code-studien', '20260919-nautilus-candle-rust', '20260908-onchainos-backup', '20260908-volumen-drift-signal', '20260908-ausnahme-usdg-live', '20260907-marktbriefing', '20260907-marktlage-september-2026', '20260906-verbesserer', '20260905-btc-analyse-sta', '20260902-xrp-analyse-sta', '20260902-analyse-quellen', '20260902-handelsregeln', '20260901-chip-xperp', '20260901-xperp-handel', '20260901-saisonalitaet-signal', '20260901-globale-npm-tools-path', '20260901-buildix-santiment', '20260913-cvd-divergenz-signal', '20260913-buildix-santiment', '20260917-task-observer-metaskill', '20260917-externe-api-referenz', '20260917-beobachtungslog', '20260902-skill-bibliothek', '20260830-pdf-scans-lesen', '20260830-miniaturansichten', '20260830-ki-ablagen-benutzerordner', '20260830-benutzerprofil', '20260930-systembild', '20260830-hardware-checkliste-d5', '20260919-willkommen', '20260908-studium', '20260908-sound-studio', '20260830-fachkunde-holztechnik', '20260830-projekte', '20260830-verbundungen', '20260830-werkzeuge', '20260830-portabilitaet', '20260830-ordnerstruktur', '20260830-fristen', '20260916-optimierungen-finden', '20260910-optimierungen-umgesetzt', '20260911-off-site-backup', '20260910-brainfiles-bus', '20260917-openmontage', '20260916-moon-dev-agenten', '20260917-awesome-systematic-trading', '20260921-archiv-trading-skills', '20260921-prognose-backtest', '20260918-handel-stack-repo', '20260919-moon-dev-code-studien', '20260919-nautilus-candle-rust', '20260908-onchainos-backup', '20260908-volumen-drift-signal', '20260908-ausnahme-usdg-live', '20260907-marktbriefing', '20260907-marktlage-september-2026', '20260906-verbesserer', '20260905-btc-analyse-sta', '20260902-xrp-analyse-sta', '20260902-analyse-quellen', '20260902-handelsregeln', '20260901-chip-xperp', '20260901-xperp-handel', '20260901-saisonalitaet-signal', '20260901-globale-npm-tools-path', '20260901-buildix-santiment', '20260913-cvd-divergenz-signal', '20260913-buildix-santiment', '20260917-task-observer-metaskill', '20260917-externe-api-referenz', '20260917-beobachtungslog', '20260902-skill-bibliothek', '20260830-pdf-scans-lesen', '20260830-miniaturansichten', '20260830-ki-ablagen-benutzerordner', '20260830-benutzerprofil', '20260930-systembild', '20260830-hardware-checkliste-d5', '20260919-willkommen', '20260908-studium', '20260908-sound-studio', '20260830-fachkunde-holztechnik']
summary: 'Auswertung von 1.479 User-Nachrichten (05.08.-06.10.2026) und TASKS.md (T-001 bis T-371): Themencluster, sieben Fehler-Klassen, priorisierte offene Punkte, belegte Erfolge.'
---

# Sitzungsanalyse — Themen, Fehler, offene Punkte, Erfolge

Stand 2026-10-06. Quellen: 651 Claude-Transkripte (`~/.claude/projects/**/*.jsonl`),
1.479 User-Nachrichten, Zeitraum 05.08. – 06.10.2026. Ergänzt durch
[[20260830-index|Wissen/INDEX]] und `Archiv/TASKS.md` (T-001 bis T-371, 6.412 Zeilen).

## 1. Themencluster

| Cluster | Nachrichten | Anteil |
|---|---|---|
| Trading / Krypto / Handel | 1.151 | 78 % |
| Software Development | 938 | 63 % |
| Andere (Betrieb, Steuer, Profil) | 247 | 17 % |

Die Cluster überlappen sich (viele Handels-Werkzeuge sind Software-Projekte).
Der Schwerpunkt liegt eindeutig auf Trading.

## 2. Trading / Krypto / Handel

### 2.1 Spuren-Bau und -Messung

47 Handels-Spuren im Dauerlauf, davon:

- **8 Feed-Spuren:** moondev_topmovers, signalwelle, funding, liquidation, whale,
  sentiment, listingarb, robinhood_radar
- **3 Wand-Spuren:** iv_wand, liq_wand, trendwende_btc
- **1 Scanner**, **1 XPERP**, **1 Swap**, **1 Mosaic**, **1 Omniquant**,
  **1 Omnitrade**, **1 Nautilus**, **1 Kraken**, **1 Freqtrade**, **1 RLTrader**,
  **1 OpenAlice**

Backtests:

- 7.000 Stundenkerzen (Prognose-Spuren, [[20260921-prognose-backtest]])
- 9 Jahre BTC-Stundenkerzen (TTM-Squeeze+ADX, [[20260921-archiv-trading-skills]])
- 1.287 Fenster (CVD-Kalibrierung, [[20260913-cvd-divergenz-signal]])

Kosten-Wendepunkt je Spur gemessen (z.B. Scanner -0,30 % je Runde,
liq_wand -0,30 %, macd_mtf +0,172 %).

### 2.2 Infrastruktur und Werkzeuge

- [[20260929-omnitrade|omnitrade]] (Rust) als Live-Lauf auf OKX-Demo
- omniquant auf Kraken Futures (erster echter NEAR-Kauf am 05.10.)
- Signal-Executor mit Queue für `trigger_modus=signal`
- Trailing-Stop-Logik mit Mengen-Deckung
- Gebühren-Abgleich (`gebuehr_boerse_abgleich.py`, 16 Tests)
- Buch-Abgleich (`boersenabgleich.py`)
- Stop-Deckung (`stopdeckung.py`)
- Spur-Audit (`spur_audit.py`, 33 Tests)
- Kosten-Wendepunkt-Rechnung (`kosten_wendepunkt.py`)

### 2.3 Strategie-Entscheidungen

- Scanner-Einstieg korrigiert (T-322: Vortagesbericht → Jetzt-Kurs)
- Long/Short-Freqtrade abgelehnt (T-314: short verliert mehr)
- adx_macd nicht freigegeben (T-349: Vorzeichen folgt dem Fenster)
- rsi_long_only abgelehnt (T-349: Ziel zu eng)
- Squeeze auf 3,0 % / 1,5R umgestellt (T-326)
- NEAR freigegeben und gehandelt (T-355)

### 2.4 Wissensquellen

- [[20260913-buildix-santiment|Buildix]] (Hyperliquid-Orderflow) und
  [[20260913-buildix-santiment|Santiment]] (On-Chain-Metriken) als neue Quellen
- [[20260917-awesome-systematic-trading|awesome-systematic-trading]] (136 Bibliotheken, 4.843 Papers)
- [[20260917-externe-api-referenz|public-apis-Liste]] (DefiLlama, Hyperliquid, PumpFunData, Messari, FRED)
- [[20260902-analyse-quellen|Analyse-Quellen]] (STA Solutions, xGhozt Prophecies)

## 3. Software Development

### 3.1 KI-Betriebssystem

- [[20260830-hermes|Hermes-Agent]] (Python) als Hauptagent
- Claude-Code (CLI) als zweiter Agent
- Codex (Rust) als dritter Agent
- [[20260916-repo-bots|26 Repo-Bots]] (je Profil in Werkstatt/Repos)
- [[20260916-agent-reach|Agent-Reach]] (lesender Internet-Zugang)
- 13 MCP-Server (4-18 je Gruppe)
- [[20260910-brainfiles-bus|Telegram-Bus]] (BrainFiles-Bus)
- Gateway (Named Pipe, Webhooks)
- 54 Cron-Jobs
- Kanban (Task-Observer)

### 3.2 Skills und Routinen

12+ Skills (archiv, frist, schaden, dokument, belege, geld, auftrag,
posteingang, notiz, tagesbriefing, wochenrueckblick, system, verbindungen,
vergleich, sichern, skill, rueckschau, umzug)

Routinen (PowerShell): `sichern.ps1`, `zweitkopie.ps1`, `ausserhaus-kopie.ps1`,
`systempruefung.ps1`, `fremdarbeit-einziehen.ps1`, `handel-dauerlauf.ps1`,
`handel-tests.ps1`, `gateway-waechter.ps1`, `docker-wache.py`,
`dateischwund-wache.py`, `konfig-doktor-wache.py`, `ausserhaus-aufgabe-wache.py`,
`mcp-zombie-wache.py`, `spiegelstand.py`, `signal-executor.py`,
`omnitrade-lauf-wache.py`, `gebuehr_boerse_abgleich.py`, `spur_audit.py`,
`stopdeckung.py`, `boerenabgleich.py`, `buch_bereinigen.py`, `pos_kennung.py`,
`journalpaarung.py`, `kosten_wendepunkt.py`, `skalieren.py`, `trailing.py`,
`spur_buch.py`, `dauerlauf.py`, `handeln.py`, `live_perp.py`, `kraken_perp.py`,
`okx.py`, `guthaben_abgleich.py`, `anbindung_pruefen.py`, `freigabebeleg.py`,
`beleg_hand.py`, `pruefe_ratschen.py`, `auswertung_alle.py`, `lage.py`, `befele.py`

### 3.3 Infrastruktur

- Docker-Container (nautilus-demo, freqtrade-*, rltrader-*, openterminalui-*)
- Windows-System (Aufgabenplanung, Registry, Ereignisprotokoll, PowerToys,
  LogiOptions, ROCCAT SWARM, cua-driver)
- Python-Versionen (3.13, 3.14, venv-Konfigurationen)
- Node.js/npm (Volta, globale Tools, PATH)
- Git/GitHub (BrainFiles-Repo, Handel-Stack-Repo, 47 Klone in Werkstatt/Repos)
- SQLite-Datenbanken (state.db, zustand.db, *_index.db)
- Obsidian-Vault (Wissen/, Archiv/, Wiki/, Dashboard.md, INDEX.md, TASKS.md)
- [[20260913-projektatlas|Projektatlas]] (Rust-Werkzeug, SQLite-Karte je Repo)
- OmniRoute (Router, 1.739 Modelle, 428 Nous-Modelle)
- Paperclip-CLI (Agent-Dashboard, PostgreSQL)
- [[20260917-openmontage|OpenMontage]] (Video-Produktions-Framework)
- RLTrader (RL-Optimization, Optuna)
- [[20260919-nautilus-candle-rust|NautilusTrader + candle]] (Rust-KI-Stack)
- Freqtrade (3 Bots, 24 Paare, 1h)
- [[20260929-omnitrade|omnitrade]] (Rust, OKX-Demo)
- omniquant (Kraken Futures)
- OpenAlice (Auto-Prediction, Auto-Quant)
- [[20260919-moon-dev-code-studien|Moon-Dev-Code]] (3 Strategie-PDFs)
- [[20260916-moon-dev-agenten|Moon-Dev-Agenten]] (46 Agenten, TradingView-MCP)

## 4. Wiederkehrende Fehler — sieben Klassen

Aus der TASKS.md (T-001 bis T-371) lassen sich sieben Fehler-Klassen identifizieren,
die mehrfach auftreten:

### Klasse 1: Buch-Geister (Positionen ohne echte Order)

- T-319 (ZRO-Position, erledigt), T-354 (GENIUS/BTC), T-355 (9 Positionen, erledigt)
- Muster: Papier-Einstiege, die als live gebucht werden, aber nie an der Boerse existierten
- Ursache: fehlende `modus`-Felder, fehlende `bueche_papier_altlasten_aus()`

### Klasse 2: Gebühren-Fehlberechnung

- T-329 (mosaic, erledigt), T-330 (kein Werkzeug, erledigt), T-350 (5 moondev-Spuren)
- Muster: Gebührensatz passt nicht zur aktiven Boerse
- Ursache: Spur wechselt Boerse, Satz bleibt stehen

### Klasse 3: Signal-Executor-Ausfälle

- T-346 (ModuleNotFoundError, erledigt), T-353 (Import vor sys.path, erledigt),
  T-351 (Queue ohne Abholung)
- Muster: Import-Fehler, Queue wächst ohne Executor
- Ursache: falsche Reihenfolge, fehlende sys.path-Eintrag

### Klasse 4: Pfad- und Import-Fehler

- T-327 (HANDEL = HIER, erledigt), T-337 (Cache, erledigt), T-348 (fremde Änderungen)
- Muster: falsche Pfade, Caches ohne Zurücksetzung, fremde Änderungen
- Ursache: fehlende Prüfung, fehlende Gegenprobe

### Klasse 5: Task-ID-Kollisionen

- T-364 (Doppelvergabe, erledigt), T-357/T-358/T-359 (Umnummerierung)
- Muster: parallele Sitzungen vergeben `max+1` unabhängig
- Ursache: keine zentrale Vergabe

### Klasse 6: Infrastruktur-Ausfälle

- T-369 (Junction-Verlust), T-370 (Docker-Terminal), T-367 (Ausser-Haus-Aufgabe),
  T-306 (docker-wache), T-152 (MCP-Spawn-Kette), T-228 (Regex-Amoklauf),
  T-194 (Dateischwund)
- Muster: Junction verschwindet, Docker-Ausfälle, Aufgaben verschwinden,
  MCP-Spawn-Kette, Regex-Amoklauf, Dateischwund
- Ursache: Windows-System, Docker, MCP-Server, Regex, Dateisystem

### Klasse 7: Config-Überschreibung

- T-297 (Hermes-App überschreibt Config), T-223 (deepwiki uncommittet),
  T-224 (Kompressionsschwelle)
- Muster: App überschreibt Config, uncommittete Einträge, falsche Schwellen
- Ursache: fehlende Sicherung, fehlende Commits, fehlende Messung

## 5. Offene Punkte — priorisiert

Die TASKS.md enthält 6.412 Zeilen mit T-001 bis T-371. Die wichtigsten
offenen Punkte:

### Blockierend (müssen zuerst erledigt werden)

- **T-371:** OmniRoute-Log fehlt (Gegenprobe-Test rot)
- **T-369:** Junction-Verlust der Wurzel (Ursache unbewiesen)
- **T-370:** Docker-Terminal (Gateway hat Fix noch nicht gelesen)
- **T-367:** Ausser-Haus-Aufgabe verschwindet täglich

### Handel (warten auf Messung oder Entscheidung)

- **T-355:** Omniquant `signal_quelle` (toter Schalter)
- **T-354:** Zwei Positionen ohne `modus`
- **T-352:** omnitrade.cmd Stand veraltet
- **T-351:** signal-executor Queue
- **T-350:** moondev-Spuren Perp-Satz
- **T-349:** adx_macd Vorzeichen
- **T-347:** omnitrade_futures Papierrunden
- **T-345:** Leitstand-Reiter ohne Takt
- **T-344:** nautilus_trader zwei venv
- **T-341:** omnitrade_futures kein Rust-Lauf
- **T-338:** QQQ-Tageskerzen
- **T-336:** `trigger_modus: signal` Backtest
- **T-335:** Bereichs-Besitz
- **T-333:** Zweigbestand
- **T-326:** Offene squeeze-Positionen
- **T-324:** Spur-Audit
- **T-323:** Welche Spur hat Edge
- **T-322:** Scanner-Einstieg
- **T-321:** kopier1zu1 Errno 22
- **T-320:** Update-Waisen
- **T-316:** iv_wand Runden
- **T-317:** Hebel bei Ein-Platz-Spur
- **T-314:** Long/Short Freqtrade
- **T-312:** futures_probe Stop
- **T-311:** Scanner-USDC-Umstellung
- **T-307:** RLTrader update-static-data
- **T-306:** docker-wache
- **T-305:** rltrader-optimize1
- **T-302:** Hauptconfig-Modellliste
- **T-297:** Config-Block sichern
- **T-228:** Regex-Amoklauf
- **T-227:** Nautilus-Arme Abgleich
- **T-225:** Handstart Dauerlauf
- **T-224:** Kompressionsschwelle
- **T-223:** deepwiki uncommittet
- **T-221:** Erhoehte Wrapper
- **T-203:** Backtest-Zahlen alt
- **T-202:** Docht-Ausstieg
- **T-194:** Dateischwund-Wache
- **T-189:** claude-red Defender
- **T-188:** OpenTerminal osiris
- **T-187:** Zwei Klone eigenem Zweig
- **T-186:** OmniRoute .omniroute
- **T-185:** Klon-.env-Kopien
- **T-183:** NODE_ENV=production
- **T-181:** Bonsai Port 8080
- **T-176:** Kill-Schalter
- **T-178:** Einstiegsgrund Platzhalter
- **T-166:** Zehn neue Repos kein Bot-Profil
- **T-168:** deepseek-harness ungebaut
- **T-169:** tradememory-protocol Dashboard
- **T-170:** ziplime OpenRouter_API_KEY
- **T-171:** O:\Werkstatt 2
- **T-160:** Acht Feed-Spuren Kurs
- **T-159:** affinity-SSE-Adresse
- **T-155:** Bonsai-Dienst ungeprueft
- **T-152:** MCP-Spawn-Kette
- **T-148:** Web-Bau Dashboard vitest
- **T-142:** Einstiegsgrund Platzhalter
- **T-143:** Funding-Ruecklauf Ratsche
- **T-144:** Signalwelle kleineres Universum
- **T-145:** CoinGecko 403
- **T-141:** TCP 9900
- **T-140:** Gateway-Wache nur 08:15
- **T-122:** iv_wand Wandweg

## 6. Erfolge — belegt

### Erledigte Aufgaben (Auswahl)

- T-226: pos_id in restlichen Journalen (06.10.)
- T-229: Rueckschau liest state.db (06.10.)
- T-319: ZRO-Ausstieg (04.10.)
- T-360: Repos-Zentrale Manifest-Einträge
- T-364: Doppelverkäufe
- T-348: Vier Tests rot
- T-337: moondev_historie Cache
- T-331: satz_pct_fuer
- T-327: anbindung_pruefen
- T-328: Zwei Schattenarme
- T-329: mosaic Gebuehr
- T-330: Gebühr-Abgleich
- T-325: Drei Spuren
- T-320: Update-Waisen
- T-303: Omniquant-Test
- T-271: kopier-Familie
- T-242: Fremd-Grenze
- T-230: Zahlen gemischt
- T-222: Wache deckt alle
- T-194: Dateischwund-Wache
- T-156: Bonsai aus
- T-146: Gateway-Waechter
- T-044: Gateway-Waechter registriert

### Messbare Ergebnisse

| Spur | Runden | Treffer | Ergebnis |
|---|---|---|---|
| Scanner | 124 | 85 % | +17,49 % (aber T-322: Einstieg war falsch) |
| macd_mtf | 1.209 | — | +0,172 % je Runde |
| squeeze | 854 | — | +0,158 % je Runde |
| TTM-Squeeze+ADX | 9 Jahre | — | Kosten-Wendepunkt ≈ 0,10 % je Runde |
| liq_wand | 32 | 66 % | -10,83 USD brutto |
| moondev_topmovers | 27 | 56 % | +48,12 |
| moondev_signalwelle | 16 | 56 % | +35,72 |
| adx_macd | 44 | 29,6 % | +755,71 USD |
| Squeeze (nach Umstellung) | 759 | — | -6,34 % |
| omnitrade | 1 Order | — | 0,0058 BTC |
| omniquant | 1 NEAR-Kauf | — | 61 Kontrakte, Stop 4,2856, Ziel 5,592 |

## 7. Empfehlung

Die vier blockierenden Punkte (T-371, T-369, T-370, T-367) sollten zuerst
erledigt werden, da sie die Infrastruktur betreffen. Danach die Handels-Punkte,
die auf Messung warten (T-347, T-349, T-355). Die Fehler-Klassen 1-7 sollten
als Checkliste in die [[20260902-systempruefung|Systemprüfung]] aufgenommen
werden, damit sie beim nächsten Auftreten sofort erkannt werden.

## Verwandte Notizen

- [[20260830-index|Wissen/INDEX]]
- [[20260830-hermes|Hermes Agent]]
- [[20260830-routinen|Routinen]]
- [[20260902-handelsregeln|Handelsregeln]]
- [[20260830-handelsbots|Handelsbots auf OKX]]
- [[20260916-repo-bots|Repo-Bots]]
- [[20260916-agent-reach|Agent Reach]]
- [[20260913-projektatlas|ProjectAtlas]]
- [[20260830-wiederholbare-aufgaben|Wiederholbare Aufgaben]]
- [[20260902-systempruefung|Systemprüfung]]
- [[20260830-hardware|Hardware]]
- [[20260830-schutzregeln|Schutzregeln]]
- [[20260830-zugaenge|Zugänge]]
- [[20260830-passwoerter-quarantaene|Passwörter-Quarantäne]]
- [[20260830-steuerunterlagen|Steuerunterlagen]]
- [[20260830-belege-einspruch-2024|Belege zum Einspruch ESt 2024]]
- [[20260830-profil|Profil]]
- [[20260830-projekte|Projekte]]
- [[20260830-verbundungen|Verbindungen]]
- [[20260830-werkzeuge|Werkzeuge]]
- [[20260830-portabilitaet|Portabilität]]
- [[20260830-ordnerstruktur|Ordnerstruktur]]
- [[20260830-fristen|Fristen]]
- [[20260916-optimierungen-finden|Optimierungen finden]]
- [[20260910-optimierungen-umgesetzt|Optimierungen — Umgesetzt]]
- [[20260911-off-site-backup|Off-Site Backup]]
- [[20260910-brainfiles-bus|BrainFiles Bus]]
- [[20260917-openmontage|OpenMontage]]
- [[20260916-moon-dev-agenten|Moon-Dev-Agenten]]
- [[20260917-awesome-systematic-trading|awesome-systematic-trading]]
- [[20260921-archiv-trading-skills|Archiv-Trading-Skills]]
- [[20260921-prognose-backtest|Prognose-Spuren-Backtest]]
- [[20260918-handel-stack-repo|Handel-Stack-Repo]]
- [[20260919-moon-dev-code-studien|Moon-Dev-Code-Studien]]
- [[20260919-nautilus-candle-rust|NautilusTrader + candle]]
- [[20260908-onchainos-backup|OnChainOS Backup]]
- [[20260908-volumen-drift-signal|Volumen-Drift-Momentum]]
- [[20260908-ausnahme-usdg-live|Ausnahme — 100 USDG als Live-Start]]
- [[20260907-marktbriefing|Marktbriefing]]
- [[20260907-marktlage-september-2026|Marktlage September 2026]]
- [[20260906-verbesserer|Verbesserer — Spur 1]]
- [[20260905-btc-analyse-sta|BTC-Analyse STA Solutions]]
- [[20260902-xrp-analyse-sta|XRP-Analyse STA Solutions]]
- [[20260902-analyse-quellen|Analyse-Quellen]]
- [[20260902-handelsregeln|Handelsregeln]]
- [[20260901-chip-xperp|CHIP XPERP auf OKX]]
- [[20260901-xperp-handel|XPERP-Handel auf OKX]]
- [[20260901-saisonalitaet-signal|Saisonalität im XPERP-Signal]]
- [[20260901-globale-npm-tools-path|Globale npm-Tools und PATH]]
- [[20260901-buildix-santiment|Orderflow- und Verhaltensdaten]]
- [[20260913-cvd-divergenz-signal|CVD-4h-Divergenz im XPERP/SWAP-Signal]]
- [[20260913-buildix-santiment|Buildix & Santiment]]
- [[20260917-task-observer-metaskill|Task-Observer — Meta-Skill]]
- [[20260917-externe-api-referenz|Externe API-Referenz]]
- [[20260917-beobachtungslog|Beobachtungslog]]
- [[20260902-skill-bibliothek|Skill-Bibliothek]]
- [[20260830-pdf-scans-lesen|Gescannte PDFs lesen]]
- [[20260830-miniaturansichten|Miniaturansichten]]
- [[20260830-ki-ablagen-benutzerordner|KI-Ablagen im Benutzerordner]]
- [[20260830-benutzerprofil|Benutzerprofil]]
- [[20260930-systembild|Systembild]]
- [[20260830-hardware-checkliste-d5|Hardware-Checkliste D5]]
- [[20260919-willkommen|Willkommen für KI]]
- [[20260908-studium|Studium]]
- [[20260908-sound-studio|Maks Sound]]
- [[20260830-fachkunde-holztechnik|Fachkunde Holztechnik]]
