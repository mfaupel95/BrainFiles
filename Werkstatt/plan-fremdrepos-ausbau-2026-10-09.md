# Plan: Fremd-Repos lokal ausbauen und an Hermes + Handel/ anbinden

Stand: 2026-10-09. Status: Entwurf nach Brainstorm, noch nichts umgesetzt außer der Remote-Bereinigung (siehe unten).

## Ziel
Fremde Repos werden lokal auf Max zugeschnitten, nicht zurückgespielt. Jedes Repo, das handelt oder Märkte liest, wird (1) als Hermes-Agent mit Topic-Delegierung nutzbar, (2) an `Agenten/Handel/` angeschlossen und (3) wenn möglich über eine UI startbar, gegen Börsen-Testumgebungen (OKX-Demo, Papier).

## Bereits erledigt (09.10.)
- `auto-prediction-modest-birch-bridge`: `origin` (TraderAlice) entfernt, Zweig `research/prediction` bleibt lokal. Keine PR.
- 13 Klone in `Werkstatt/` auf eigenen Fork `mfaupel95/<name>` gesetzt; `origin` heißt jetzt `upstream`, **kein `origin`** mehr, also kein versehentlicher Push: Scrapling, EasyCLIProxyAPI, basic-memory, caveman, claude-code, claudian, codex, deepseek-harness, everything-claude-code, gbrain, intelligent-trading-bot, obsidian-skills, one-skill-to-rule-them-all.
- Bewusst NICHT angefasst: die 20 bestehenden Forks (Hausregel: `origin`=Fork, `upstream`=Original), Hermes-verwaltete Klone (`hermes-agent`, `plugins/*`, `skills/.archive/*`; `hermes update` braucht `origin`), TraderAlice-Mirror/Workspaces (du wolltest dort nicht forken), `CLIProxyAPI` in `MaxHirn/`.

## Offene Entscheidungen (Max)
1. Die 20 bestehenden Forks ebenfalls auf "ohne origin" umstellen? Das bricht die Hausregel in `CLAUDE.md` (Fremd-Repos) und müsste dort mitgeändert werden. Empfehlung: nein, Pushen geht ohnehin nur in den eigenen Fork.
2. TraderAlice-Repos (Auto-Prediction, Auto-Quant-V2) ebenfalls forken? Aktuell nein.

## Kandidaten nach Rolle
| Rolle | Repos | Anschluss |
|---|---|---|
| Handel/Signal | intelligent-trading-bot, moon-dev-ai-agents, jev-trader, tradememory-protocol, ziplime, agent-trade-kit (OKX), kraken-cli, Harvard-Algorithmic-Trading-with-AI, fomo-robinhood-radar, osiris, auto-prediction (Prognosemärkte) | `Agenten/Handel/` als Spur; Papier/Demo vor Live |
| Recherche/Daten | Scrapling, jevgrep, awesome-systematic-trading, Agent-Reach | Hermes-Skill, Topic `markt-recherche` |
| Gedächtnis/Infrastruktur | basic-memory, gbrain, claudian, obsidian-skills, caveman | Hermes-Gedächtnis / Vault, kein Handel |
| UI/Terminal | OpenTerminal, OpenTerminalUI, openmontage | UI-Start über Desktop-Verknüpfung, spricht Handel-API |
| Referenz (nur lesen) | claude-code, codex, deepseek-harness, EasyCLIProxyAPI | kein Anschluss |

## Phasen
**Phase 0 – Inventur (je Repo ~15 min, lesend).** Start-Befehl, Abhängigkeiten, Börsen-/API-Anbindung, Testmodus, Lizenz. Ergebnis: Tabelle in `MaxHirn/Wissen/` (Bereich `wissen`, Befund melden) oder Werkstatt-Notiz.
**Phase 1 – Handels-Adapter.** Ein gemeinsamer Auftrags-/Signalvertrag in `Agenten/Handel/` (Bereich `handel`, Sitzung mit Besitz abstimmen, Befund melden). Fremde Repos liefern nur Signale oder Papier-Aufträge; ausgeführt wird ausschließlich über bestehende Wachen (`wachen.json`, Herzschlag 180 min, Stop-Pflicht). Börsen: OKX-DEMO, Kraken nur lesend, Revolut-X lesend.
**Phase 2 – Hermes-Agent je Repo.** Profil unter `Agenten/Hermes/profiles/<bot>/` (Muster wie `moon-dev-agents`, `jev-trader`), Start-Verzeichnis `Werkstatt/<repo>`, Skill unter `Agenten/Hermes/skills/brainfiles/` (Hausformat, Skill `skill`). Pro Rolle ein Topic für die Delegierung (Handel, Recherche, Gedächtnis, UI); Zuordnung in der Hermes-Konfiguration, Kanban-Board `handel` für Aufträge.
**Phase 3 – UI-Start.** Pro Repo ein `start`-Skript (Muster `omnitrade.cmd ui`), Eintrag in Desktop-Verknüpfungen (`Agenten/Werkzeuge/desktop-verknuepfungen.ps1`). Für Repos ohne UI: OpenTerminalUI als gemeinsame Oberfläche vor `Handel/`.
**Phase 4 – Test und Betrieb.** Je Repo: Papierlauf, Eintrag in die Systemprüfung/Wachen, Tests wie `handel-tests.ps1`. Live erst nach Freigabe durch Max, nie automatisch.

## Regeln
- Eigener Zweig je Repo (`claude/<thema>`), nichts nach `master`/`main` ohne abgeschlossene Arbeit; kein `git stash`.
- Keine Keys im Code oder Klartext; Zugangsdaten nur aus Umgebungsvariablen, in Berichten nur Vorhandensein und Länge.
- Handelnde Pfade erst nach Papier-/Demo-Nachweis; Live nur mit ausdrücklichem Ja.
- Lokal bleibt lokal: Push nur in den eigenen Fork und nur auf Zuruf.

## Nächster Schritt
Phase 0 für die Handels-Rolle (7 Repos) als Inventur starten, danach Adaptervertrag entwerfen.

## Phase 0 – Ergebnis Handels-Rolle (09.10., nur gelesen, nichts gestartet)
| Repo | Stack | Lizenz | Börsen (Treffer) | Testmodus | UI | Eignung für Anschluss |
|---|---|---|---|---|---|---|
| agent-trade-kit | TypeScript, pnpm | MIT | OKX (nur) | Demo über OKX-Konto | keine; **MCP-Server** `okx-trade-mcp` | **Hoch**: passt zum bestehenden OKX-Demo-Pfad; direkt als MCP in Hermes einbindbar (Abgleich mit `mcp-sync-check.ps1`) |
| kraken-cli | Rust, ein Binary | MIT | Kraken (nur) | **Papierhandel eingebaut** | keine; eingebauter MCP | **Hoch**: Papier-Futures und -Spot ohne Risiko; ersetzt/ergänzt den lesenden Kraken-MCP |
| intelligent-trading-bot | Python, pyproject, Docker | MIT | Binance (1706), wenig OKX/Alpaca | kein dokumentierter Papiermodus | keine | **Mittel**: ML-Signalpipeline; Börsenadapter (Binance) müsste auf OKX umgeschrieben werden; `itb_pruefstand.py` ist bereits lokaler Zuschnitt |
| tradememory-protocol | Python, Docker, Dashboard | MIT | Binance (Datenquelle) | Dashboard nur synthetisch | `dashboard/` | **Mittel**: Handelsgedächtnis, kein Handeln; passt als Journal zu `handel-journal-forensik`. Projektstatus: Wartungsmodus |
| moon-dev-ai-agents | Python, `moongui.py`, `START_GUI.bat` | **keine Lizenzdatei** | Binance, Kraken, OKX, Hyperliquid, Coinbase, Bybit | nicht dokumentiert | **GUI vorhanden** | **Mittel**: viel Material, viele Agenten, schon als Hermes-Bot geführt; Lizenz klären, Alt-Dateien (`Kopie.env`) nicht anfassen/lesen |
| jev-trader | Bun/TypeScript | MIT | Kuru (Monad-DEX), kaum CEX | **Dry-run ohne Schlüssel** | `web/` | **Niedrig**: DEX-spezifisch, anderes Ökosystem; nur als Vorlage für Blockschleife/Dry-run |
| ziplime | Python 3.12, Poetry, Polars | EULA (kein MIT) | Alpaca, kaum Krypto | Backtest = Live-Datei | keine; **MCP-Server** | **Niedrig-Mittel**: Backtest-Gerüst mit MCP; Lizenz (EULA) vor jeder Weiterverwendung lesen |

### Befunde
- Für **Börsenanschluss** ist die Reihenfolge klar: `agent-trade-kit` (OKX-Demo) und `kraken-cli` (Papier). Beide bringen MCP mit, damit entfällt eigener Adapterbau.
- **Signale/ML**: `intelligent-trading-bot` ist der einzige Kandidat mit eigener Modellpipeline, braucht aber den Börsenwechsel.
- **UI**: nur `moon-dev-ai-agents` (GUI), `tradememory-protocol` (Dashboard), `jev-trader` (web) bringen eine mit; die anderen laufen über OpenTerminalUI oder eine Hermes-Oberfläche.
- **Lizenz-Vorbehalt**: `moon-dev-ai-agents` ohne Lizenz, `ziplime` unter EULA. Nur lokal nutzen, nichts veröffentlichen.
- Nicht geprüft (Phase 1): Laufzeit, Abhängigkeitsinstallation, tatsächliche Vollständigkeit des Papiermodus, Schlüsselhandling je Repo.

### Ergebnis Phase 1 – Adaptervertrag (09.10., fertig)

Atlas-Konsultation (agentic-atlas:designing-agent-systems) ergab 6 Muster:
Effect Discipline, Contract Keystone, LLM Dispatch, Subagent Offload,
Unsent Thunderstorm, Cost Relocation.

Artefakte erstellt (BEFUND bot-Bereich gemeldet, nicht blockiert):
- `Agenten/Hermes/profiles/kraken-cli/config.yaml` — dediziertes Profil,
  kraken-native MCP mit market,paper,workspace (kein dangerous, kein live).
- `Agenten/Hermes/skills/brainfiles/fremdrepos-signal/SKILL.md` — Adapter-Contract:
  Signal-Schema, Dispatch-Regeln, Stale-Verwurf, Gate-Übergabe.

Signal-Schema (Contract Keystone): instrument, venue, direction, size_pct,
source, ts_utc, expiry_s (180 s = Heartbeat-Fenster), mode (paper|demo), confidence.

### Ergebnis Phase 2a – Telegram-Route + Topic-Routing (09.10., fertig)

`gateway.profile_routes[0].enabled: true` gesetzt — Gateway liefert Telegram-Nachrichten
nun an das `default`-Profil aus. Gateway neu gestartet (PID neu).

`platforms.telegram.extra.dm_topics` konfiguriert für chat_id 7648512088:
- Allgemein (blau) — kein Skill, allgemein
- Handel (grün) — `skill: brainfiles/fremdrepos-signal` (Adapter-Contract auto-load)
- Markt (orange) — kein Skill, Recherche
- Wissen (rot) — kein Skill, Vault

Hermes erstellt die Topics beim nächsten DM-Kontakt automatisch über die Telegram-API
(kein thread_id manuell nötig). Topics-Modus muss noch per `/topic` im DM aktiviert werden
(einmalig, nutzerseitig — Voraussetzung laut Doku).

Hinweis: `profile_routes` unterstützt kein `thread_id`-Matching — Topic→Profil-Routing
(z. B. Handel-Topic direkt an `agent-trade-kit`-Profil) ist nativ nicht möglich.
Lösung: `fremdrepos-signal`-Skill delegiert im "Handel"-Topic via `hermes kanban`
an das richtige Bot-Profil.

### Nächster Schritt
1. Im Telegram-DM `/topic` senden um Topics-Modus zu aktivieren (einmalig).
2. Phase 2b: `agent-trade-kit` MCP-Server eintragen (nach `pnpm build`),
   Bus-Integration (Signal-Schema als Nachrichtentyp), `wachen.json`-Gate erweitern,
   Tests `test_signal_schema.py`. Bereich `handel` BEFUND vor Gate-Änderungen.

## Phase 1 – Stand (10.10.)
- `kraken-papier` (MCP, an): kraken-cli, nur Markt/Konto lesen + Papierhandel; Futures-Papierkonto 10 000 USD angelegt. Sync-Check OK.
- `okx-agentkit` (MCP, **aus**): agent-trade-kit gebaut, startet nur mit `--demo --profile demo`. Wartet auf Demo-Key von Max (Profil `demo` in `~/.okx/config.toml`; `default_profile` bleibt `okx-prod`). Ein erster Versuch mit dem Live-Profil im Lesemodus wurde vom Klassifizierer abgelehnt und nicht wiederholt.
- Skill `fremd-handel-papier` unter `Agenten/Hermes/skills/brainfiles/` beschreibt Nutzung und Fallen.

### Adaptervertrag (Entwurf, noch nicht in `Agenten/Handel/` umgesetzt)
Ein Fremd-Werkzeug liefert nur ein **Signal** oder eine **Papier-Order** im Format der bestehenden Spuren; es ruft nie selbst Live-Endpunkte.
1. Signal: `{spur, symbol, richtung, einstieg, stop, hebel, quelle, zeit}` - Stop Pflicht, sonst verworfen.
2. Ausfuehrung: Papier/Demo ueber die MCPs; Live nur ueber die bestehende Kette (`handeln.py --wachen`, `handel_erlaubt`, Herzschlag 180 min).
3. Journal: jede Order landet im Journal der Spur (Bus), Fremdquelle im Feld `quelle`.
4. Umsetzung erst nach Abstimmung mit dem Bereich `handel`; Befund via `bereiche.py --aufrufer bot --pfad Agenten/Handel/...`.

### Offen
- Demo-Key (Max). Danach `okx-agentkit` einschalten und gegen die Demo-Umgebung testen.
- Topic-Delegierung: Zuordnung in der Hermes-Konfiguration (`dm_topics`) noch nicht angefasst.
- Naechste Repos: intelligent-trading-bot (Signalpipeline auf OKX umbauen), tradememory-protocol (Journal).

## Stand 11.10.2026 - Demo-Kette und offenes Tor

- Tor `Agenten/Handel/fremd_signale/wachen.json` auf Max' Ansage **geoeffnet** (nur paper/demo, nie live); 59 Instrumente (OKX `-USDC` Spot, Kraken `/USD`), 11 Quellen.
- OKX-Demo im EWR: Swap/Perps gesperrt (Fehler 50124), nur Spot. Durchlauf BTC-USDC (Kauf 50 USDC mit Stop 4 %, Verkauf, Stop-Storno) fehlerfrei.
- Neu: `Agenten/Handel/fremd_demo.py` (rechnet Plan), `fremd_signale/demo_plan.py` (`--vorschau|--vormerken|--verwerfen`), Hermes-Ausfuehrungsschritt im Skill `fremd-handel-papier`. Hermes-MCP okx-agentkit schreibend (ohne `--read-only`), nur Demo.
- Offen: Hermes als Ausfuehrer noch nicht mit echtem Signal erprobt; Task `MaxHirn-Fremd-Papier` nicht registriert; Adapter fuer die neuen Quellen fehlen.

## Stand 11.10.2026 abends - Kette laeuft (Papier)

- Adapter gemergt: `adapter_nautilus.py`, `adapter_moondev.py` (Konsens zweier Agenten), Aufrufer `adapter_lauf.py` + `adapter_quellen.json` (ITB aus).
- `Bus/nautilus_signalgeber.py` (EMA-Kreuzung, schreibt nur Absichtszeilen) und `Bus/nautilus_okx_lauf.py` (echte OKX-Kerzen BTC-USDC 5m). Umgebung `Werkstatt/nautilus-venv` (Nautilus 1.231 aus PyPI; der Fork hat eine neuere API).
- Registriert: `MaxHirn-Nautilus-OKX` (5 Min), `MaxHirn-Fremd-Adapter` (2 Min), `MaxHirn-Fremd-Papier` (2 Min). Alles Papier, nie live.
- Beobachten: `stale`-Verwuerfe im Journal (Fenster 180 s knapp), erste Papier-Positionen in `fremd_signale/zustand.json`.

## Auswertung 12.10.2026 - EMA-Kreuzung (nautilus_signalgeber), Walk-forward

Skript `Werkstatt/ema_walkforward.py` (unversioniert). BTC-USDC, OKX-Kerzen, Long/Flat, Kosten 0,07 %/Seite (Gebuehr 0,05 + Slippage 0,02), 1 Kerze Verzug. Raster fast {5,8,10,13,20} x slow {20..120}, IS 30 Tage waehlt, OOS naechste 7 Tage. Kriterium vorab: OOS-Summe > 0 UND >= 60 % der Fenster positiv.

| Lauf | OOS gewaehlt | OOS fix 10/20 | Buy&Hold |
|---|---|---|---|
| 1H, 367 Tage, 48 Fenster | -36,96 % (14/48 positiv) | -47,47 % (17/48) | -13,47 % |
| 5m, 120 Tage, 12 Fenster | -4,76 % (3/12 positiv) | **-74,69 %** (1/12) | +33,84 % |

**Ergebnis: Kriterium in beiden Laeufen NICHT erfuellt.** Die live laufende Einstellung (5m, 10/20) verliert Out-of-sample praktisch alles an Kosten und Fehlsignalen. Die Walk-forward-Wahl landet bei langsamen Paaren (20/120), d. h. das Raster flieht vor den Kosten. Kein Vorteil; Strategie taugt nur als Rohrleitungs-Test der Kette. Grenzen: kein Stop simuliert (4 %-Stop aendert auf 5m wenig), ein Instrument, eine Marktphase.

## Auswertung 12.10.2026 - moon-dev-ai-agents (nicht durchfuehrbar)

`ai_analysis_buys.csv`: 95 Zeilen, nur 12.-31.01.2025 (Memecoins). 47x BUY/BUY, 35x BUY/DO NOTHING, 13x DO NOTHING/BUY; keine SELL-Zeilen, keine Ergebnisspalte. **Kein einziges Symbol steht in der Tor-Liste** (kein Token auf OKX-/Kraken-Spot). Kursverlauf zur Pruefung: CoinGecko-Gratisschnittstelle liefert fuer Daten aelter als 365 Tage HTTP 401 (28 von 28 Abfragen), danach 429. Eine Auswertung ist ohne bezahlten Schluessel nicht moeglich; `Werkstatt/moondev_auswertung.py` bleibt als Vorlage (unversioniert). Selbst mit Daten waeren die Signale nicht handelbar (Token nicht gelistet, Survivorship-Bias, Alter der Daten). Der Adapter bleibt, hat aber nichts zu tun, bis das Repo frische Empfehlungen fuer gelistete Paare schreibt.

## Auswertung 12.10.2026 - handelsarme Trendvarianten (BTC-USDT, OKX)

Skript `Werkstatt/trend_wenighandel.py` (unversioniert). Fuenf Varianten VORAB festgelegt, nicht optimiert: A SMA 50/200 1D, B Donchian 55/20 1D, C Donchian 20/10 1D, D EMA 20/50 4H, E Donchian 55d/20d 4H. Long/Flat, Kosten 0,07 %/Seite, 1 Kerze Verzug, 5,8 Jahre (1D) bzw. 4,2 Jahre (4H). Kriterium vorab: netto > 0 in BEIDEN Zeithaelften, maxDD kleiner als Buy&Hold, <= 30 Wechsel/Jahr.

| Variante | Gesamt (B&H) | maxDD (B&H) | Wechsel/Jahr | Kriterium |
|---|---|---|---|---|
| A SMA 50/200 1D | +84 % (+139 %) | 44,6 % (76,4 %) | 1,9 | erfuellt |
| B Donchian 55/20 1D | +151 % (+139 %) | 35,2 % (76,4 %) | 7,1 | erfuellt |
| C Donchian 20/10 1D | +46 % | 65,1 % | 16,3 | nicht |
| D EMA 20/50 4H | +198 % (+253 %) | 30,2 % (53,4 %) | 39,5 | nicht (zu viele Wechsel) |
| E Donchian 55/20 4H | +107 % | 41,3 % | 8,4 | nicht (2. Haelfte -3 %) |

Lesart: A und B bestehen die Vorab-Hurde; die Wirkung ist vor allem **halbierter Drawdown**, nicht Mehrertrag (A bleibt unter Buy&Hold, B liegt knapp darueber). Grenzen: ein Instrument, eine Bullenphase mit zwei grossen Rueckschlaegen, 5 Varianten getestet (Auswahlrisiko, 2 bestanden), keine Aussicht auf Zukunft. Naechster Schritt waere B als Nautilus-Strategie auf Tageskerzen (7 Wechsel/Jahr) zur Papier-Beobachtung, kein Geld.

## Suche nach besserer Strategie 13.10.2026 - Ensemble-Donchian (Online-Recherche + Test)

Recherche: Zarattini/Pagani/Barbon, "Catching Crypto Trends" (SFI Research Paper 25-80; Mehrfach-Donchian-Ensemble, Long-only, Vola-Skalierung; Autoren berichten Sharpe > 1,5 netto auf einem Top-20-Korb - nicht von uns nachgeprueft). Quantpedia-Nachtest: Breakout-Signale ("buy near highs") halten out-of-sample besser als Kauf-am-Tief; Grayscale: einfache Long-only-Trendregeln halbieren Drawdowns. TradingView-/MQL5-Skripte = Verkaufs-Backtests ohne Out-of-sample, nicht verwertet.

Skript `Werkstatt/trend_ensemble.py` (unversioniert), vorab festgelegt: Lookbacks {5,10,20,30,60,90,150,250,360} Tage, rein ueber Max(n), raus unter Min(n/2), Position = Anteil der Modelle im Markt; Kosten 0,07 %/Seite. Kriterium: netto > 0 in beiden Haelften UND maxDD < B&H UND Sharpe >= B&H.

| Variante | Gesamt (B&H) | maxDD (B&H) | Sharpe (B&H) | Umschichtungen/Jahr | Kriterium |
|---|---|---|---|---|---|
| B Donchian 55/20 1D (Ref) | +151 % (+139 %) | 35 % (76 %) | 0,73 (0,55) | 7 | erfuellt |
| F Ensemble 1D | +85 % | 36 % | 0,60 | 15 | erfuellt |
| G Ensemble 1D + Vola 40 % | +81 % | 25 % | 0,65 | 13 | erfuellt |
| H Ensemble 4H | +137 % (+253 %) | 26 % (53 %) | 0,98 (0,90) | 15 | erfuellt |
| H2 Ensemble 4H + Vola 40 % | +131 % (+253 %) | 23 % (53 %) | **1,07 (0,90)** | 15 | erfuellt |

Lesart: H2 (4H-Ensemble mit Vola-Skalierung) hat die beste Risikokennzahl (Sharpe 1,07, halbierter Drawdown), bleibt aber im Gesamtertrag klar unter Buy&Hold (Bullenphase). Grenzen: ein Instrument, 4,2 Jahre, insgesamt ~11 Varianten gesichtet (Auswahlrisiko), Papier-Stop 4 % nicht simuliert. Umsetzung im Signalweg waere nicht trivial: Ensemble liefert Positionsanteile 0..1, der Bus kennt long/flat mit size_pct; naechster Schritt waere Uebersetzung Anteil -> size_pct (nur bei Aenderung melden).
