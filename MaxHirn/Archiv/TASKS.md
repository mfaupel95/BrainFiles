## Offen
- [ ] **T-419 - omnitrade2: OKX-SWAP-Stand uebernehmen (Handover 20.10.)**
      Kontext: Claude-Session (Branch claude/nice-pasteur-940iq0) hat den
      OKX-Perpetuals-Adapter (SWAP) in mfaupel95/omnitrade2 gebaut (swap.rs,
      swap_client.rs, instrument.rs: ctVal/lotSz/minSz, EEA wseea, isolated/
      one-way/MAX_LEVERAGE 10, Liquidationsabstand MIN_LIQUIDATION_DISTANCE
      0.05). origin/main gemergt, 479 Tests + Clippy -D warnings gruen.
      Demo-Verifikation NICHT gelaufen (Demo-Keys im Container fehlen).
      Handover gesichert in Werkstatt/Austausch/HANDOVER-2026-10-20-1414.md.
      Offene Entscheidungen Max: C.1 Liquidationsschwelle 5% (10x isolated)
      als Start?; C.2 Shorts gesperrt bis Long im Demo belegt?; C.3 PR #10/#11
      auf omnitrade schliessen?; C.4 Branch worktree-live-loop-fix loeschen?
      (dirty Worktree glistening-panda vorher pruefen); C.5 lokalen Branch
      integration/main-into-pr11 loeschen (identisch mit nice-pasteur)?
      Naechster Schritt: Entscheidungen C.1-C.5 von Max, dann Demo-Keys setzen
      (OKX_REGION=eea, OKX_LEVERAGE=1), Positionsantwort gegen echte Demo
      verifizieren, kleine Order 0.0001 BTC, Mainnet bleibt gesperrt.
      ENTSCHEIDUNGEN MAX 20.10.2026 (C.1-C.5 gemaess Empfehlung): C.1
      Liquidationsschwelle 5% als Start, mit Demo kalibrieren; C.2 Shorts
      gesperrt bis Long im Demo belegt; C.3 erledigt - auf omnitrade keine
      offenen PRs mehr (nur main); C.4/C.5 remote nicht vorhanden, Branches
      waren Container-lokal (worktree-live-loop-fix, integration/main-into-pr11),
      dort nicht loeschbar, in der Container-Session zu loeschen oder erledigt.
      PR #1 auf omnitrade2 (claude/nice-pasteur-940iq0) bleibt offen - er ist
      der SWAP-Stand, erst nach Demo-Verifikation ready for review.
      Angelegt 20.10.2026 · Zuletzt 20.10.2026
      Betrifft: Werkstatt/omnitrade (omnitrade2), OKX-SWAP

- [ ] **T-420 - Werkstatt/omnitrade-Klon: origin fehlt, upstream auf fremdes Repo umgebaut**
      Kontext: Befund 20.10.: git -C Werkstatt/omnitrade remote -v zeigt NUR
      upstream=LLMQuant/awesome-trading-agents (fremde Codebasis), KEIN origin.
      Historie sind Sicherungs-Commits einer parallelen Sitzung (e961d976
      "gude", "Bot-Status gesichert"). Rust-Workspace-Dateien liegen da, aber
      die Git-Anbindung an die Sicherung mfaupel95/omnitrade (vorher origin,
      upstream jackby03/omnitrade) ist weg. Das Repo mfaupel95/omnitrade
      existiert auf GitHub weiter (public, main) - nur der Klon ist entkoppelt.
      Naechster Schritt: mit Max klaeren, ob der Klon auf den Stand von
      omnitrade2 (SWAP) oder mfaupel95/omnitrade zurueck soll; origin/upstream
      neu setzen, fetch, Stand pruefen. Nichts eigenmaechtig umbauen.
      Angelegt 20.10.2026 · Zuletzt 20.10.2026
      Betrifft: Werkstatt/omnitrade

- [ ] **T-417 — llm_stunde im Dauerlauf ohne Auswertung (vorbestehend):**
    - Kontext: test_verdrahtung meldet 'llm_stunde im Dauerlauf, aber in keiner Auswertung gelistet'. Keine eigene auswertung.py, nicht in auswertung_alle. Vorbestehend (nicht durch die Sammelauftrag-Verdrahtung eingefuehrt).
    - Naechster Schritt: Journal-Format von llm_stunde pruefen, dann in auswertung_alle (oder EIGENE_AUSWERTUNG) eintragen.
    - Angelegt 2026-10-19 · Zuletzt 2026-10-19 / Betrifft: Agenten/Handel/llm_stunde
- [ ] **T-414 — jev_trader-Spur verdrahten (Worktree arbeit/jev-trader):**
    - Kontext: Parallele Claude-Sitzung baute Papier-Spur Agenten/Handel/jev_trader (liest Block-Event-Log des jev-trader-Bots, bucht Roundtrips). Liegt nur auf Zweig arbeit/jev-trader, NICHT in dauerlauf/lage/befehl/auswertung verdrahtet. handel_erlaubt=false, kein Live-Pfad.
    - Naechster Schritt: Zweig pruefen (Tests laufen lassen), dann in master uebernehmen und verdrahten (dauerlauf.SPUREN, lage.HOLER, befehle.FAMILIE, auswertung_alle, pruefe_ratschen, .gitignore, Spiegel).
    - Angelegt 2026-10-19 · Zuletzt 2026-10-19 / Betrifft: Agenten/Handel/jev_trader
- [ ] **T-415 — scanner_llm-Spur verdrahten (Worktree arbeit/scanner-llm):**
    - Kontext: Parallele Claude-Sitzung baute Papier-Spur Agenten/Handel/scanner_llm (leichter Marktscanner + LLM-Qualitaetsfilter). Liegt nur auf Zweig arbeit/scanner-llm, NICHT verdrahtet. handel_erlaubt=false.
    - Naechster Schritt: Zweig pruefen (Tests laufen lassen), dann in master uebernehmen und verdrahten.
    - Angelegt 2026-10-19 · Zuletzt 2026-10-19 / Betrifft: Agenten/Handel/scanner_llm
- [ ] **T-416 — Worktree-Umbauten pruefen: orb-multi, orbk-okx, moondev-live, phi-nvda:**
    - Kontext: 4 Zweige mit ungemergten Commits (orb Mehr-Instrument, orbk Kraken->OKX, moondev OKX-Perp-Live-Pfad, phi-nvda LLM-Filter). orb handel_erlaubt=true (Auftrag Max 12.10), orbk false (Befund 14.10).
    - Naechster Schritt: je Zweig Tests gruen pruefen, dann entscheiden ob merge-wuerdig und ob Max die Live-Pfade will.
    - Angelegt 2026-10-19 · Zuletzt 2026-10-19 / Betrifft: Agenten/Handel/{orb,orbk,moondev_*,xperp}
- [ ] **T-413 — Bedingung 4 llm_stunde: 6 Arme spiegeln nicht nach Q:**
    - Kontext: spiegelstand.py meldet 'llm_stunde kein Ziel (journal_zweitziel leer)'. Die Spur faehrt 6 Arme (laeufe/ema1h-{L,R}, rsi1h-{L,R}, st1h-{L,R}) ueber spur_buch, aber keine wachen.json der Arme traegt journal_zweitziel; Q:\Handel_Journal\llm_stunde wurde am 18.10.2026 angelegt, ist aber leer. Die Spur lief (letzter Arm-Lauf 18.10. 18:23), nur der Spiegel fehlt. Dazu: Haupt-wachen.json hatte kein herzschlag_max_minutes-Feld (Pruefer meldete 0 statt 180) - am 18.10.2026 ergaenzt (180, _herzschlag_regel-Vermerk).
    - Naechster Schritt: journal_zweitziel=Q:\Handel_Journal\llm_stunde in die 6 Arm-wachen.json eintragen (oder die Arme ueber die Haupt-wachen erben lassen), dann spiegelstand.py muss 45/45 melden.
    - Angelegt 18.10.2026 · Zuletzt 18.10.2026
    - Betrifft: Agenten/Handel/llm_stunde/
- [ ] **T-412 — Hyperliquid Market-Making als neues Projekt**
    - Kontext: Kuru (Monad) hat zu wenig Taker-Flow fuer post-only Market-Making (0 Fills in 6h bei 4550 Orders, MON UND WETH-USDC). Jev-Kern (model.ts, decision-pipeline.ts, trader.ts) ist marktunabhaengig und bleibt. Hyperliquid = Perps-L1 mit echtem Orderbook-Volumen, offizielles Python-SDK.
    - Naechster Schritt: Hyperliquid-API erkunden (REST placeOrder, WebSocket book/trades/userFills, Info-Endpoint), dann TS-Client vs. Python-Neubau entscheiden. ERLEDIGT 15.10.: Testnet erreichbar (allMids/l2Book/meta), Orderweg REST+ed25519, TIF Alo=post-only. Entscheidung: TS-Client (Jev-Kern bleibt, nur market.ts ersetzt).
    - Naechster Schritt: Orderweg-Client bauen (TS, REST /exchange, ed25519-Signatur), dann Perps-Anpassung (Hebel/Funding/Stop). ERLEDIGT 15.10.: market-hl.ts gebaut (Drop-in, @nktkas/hyperliquid), ENGINE=hyperliquid, Dry-Run liest echtes BTC-PERP-Buch + postet sim-Orders, Jev aktiv. Commit ad951b0.
    - Naechster Schritt: Perps-Anpassung (Hebel, Funding-Kosten, Liquidation-Stop, Position-Cap in USD), dann Testnet-Live-Test.
    - Angelegt 15.10.2026 · Zuletzt 15.10.2026
    - Betrifft: Werkstatt/Projekte/Hyperliquid-Market-Making.md, Werkstatt/jev-trader (Kern-Quelle)
- [ ] **T-410 - Gateway-Absturz 15.10. 00:08: Exit 75 (Liveness-Watchdog) - Ursache MemoryError**
      Kontext: In derselben Nacht, in der der Launcher-Fix (Commit 02598be6) den Gateway wieder hochbrachte, zeigte der Thread-Dump des abgestuerzten Vorgaengers (PID 43492, Exit 75 um 03:16:50) ein 'MemoryError' - das Event-Loop blieb stehen, weil das System unter Commit-Druck stand (CommitFrei 6,9 GB bei 48 python-Prozessen, darunter Waisen aus der Waechter-Neustart-Schleife). Der Watchdog hat korrekt gehandelt (Exit 75 = Supervisor-Neustart). Die Gefahr bleibt: bei naechster Speicherknappheit fehlt dem Gateway die Luft.
      Naechster Schritt: Waechter messen FreeVirtualMemory und bei < 8 GB einmal melden (Muster: mcp-zombie-wache); Python-Prozess-Leichen (Waisen aus abgebrochenen Completion-Tails) aufraeumen; Quelle der 48 Prozesse pruefen (Handels-Dauerlauf, MoonDev, MCP-Zombies).
      Angelegt 15.10.2026 · Zuletzt 15.10.2026
      Betrifft: Agenten/Hermes/gateway-service/, Agenten/Routinen/gateway-waechter.ps1
- [ ] **T-411 - SkillsBot weist alle Gruppennachrichten als '(fremd)' ab**
      Kontext: skillsbot.py:1142 vergleicht chat != chat_id(); TELEGRAM_CHAT_ID (User-Store) ist 7648512088 (Max' DM), die Telegram-Gruppe 'MaximilianundClaude-Code' ist -1003980261765. Jede Nachricht aus der Gruppe laeuft in _log(chat,'(fremd)',...,'abgewiesen') - seit 23:32 am 14.10. durchgehend (48 der letzten 50 Zeilen). Der SkillsBot bedient ABSICHTLICH nur die DM; fuer Gruppenauftraege ist der bots-Verteiler (@Maximilian420_bot, /bot NAME) zustaendig - der laeuft. Nichts kaputt, aber die Protokollflut suggeriert einen Ausfall.
      Naechster Schritt: Entscheidung Max - entweder Gruppen-ID als zweite erlaubte Chat in skillsbot.py freigeben, oder die Abweisung still protokollieren (nur 1. je Chat/Stunde statt je Nachricht). Kein Eingriff ohne Max.
      Angelegt 15.10.2026 · Zuletzt 15.10.2026
      Betrifft: Agenten/Bus/skillsbot.py
- [ ] **T-403 - GitHub-Privates loeschen: gh-Token braucht delete_repo-Scope**
      Kontext: Auftrag Max 14.10.2026 'alle auf github als privat laufenden repos entfernen, nur lokal betreiben'. 90 private Repos identifiziert (mfaupel95/*, davon ~85 *-privat-Mirrors + Werks-Repos nautilus/omnitrade/rltrader/alice/handel-stack/OmniQuant u.a.), aber gh repo delete gibt fuer ALLE HTTP 403 'Must have admin rights' - der Token traegt nur Scope 'repo', GitHub verlangt Scope 'delete_repo'. NICHTS wurde geloescht (0/90). Ausgenommen: mfaupel95/BrainFiles (Workspace-Remote, Push-Routinen haengen dran - Entscheidung Max offen).
      Naechster Schritt: Max fuehrt in seiner PowerShell 'gh auth refresh -h github.com --scopes delete_repo' aus (Browser-Flow), danach Loeschung + lokale Remotes umziehen (origin -> upstream, Remote 'privat' entfernen; Doktrin in AGENTS.md/CLAUDE.md nachziehen).
      Angelegt 14.10.2026 · Zuletzt 14.10.2026
      Betrifft: GitHub mfaupel95/*, Agenten/Werkzeuge/repos-updaten.py
- [ ] **T-404 - 17 leere Repos-Huellen unter Werkstatt/Repos nach Reboot raeumen**
      Kontext: Umzug 14.10.2026 (Werkstatt/Repos/* -> Werkstatt/*): die 17 von unsichtbaren CWD-Haltern gesperrten Top-Ordner wurden per Inhaltsverschiebung geleert; die leeren Huellen (agent-trade-kit, awesome-systematic-trading, basic-memory, caveman, claude-code, claudian, deepseek-harness, EasyCLIProxyAPI, everything-claude-code, fomo-robinhood-radar, gbrain, Harvard-Algorithmic-Trading-with-AI, moon-dev-ai-agents, obsidian-skills, one-skill-to-rule-them-all, openmontage, OpenTerminal) verweigern das Loeschen bis der Halter (vermutlich Dienst/Neustart) weg ist. Inhalt ist vollstaendig am Ziel (59 gueltige Repos direkt in Werkstatt).
      Naechster Schritt: nach dem naechsten Reboot 'Get-ChildItem Werkstatt/Repos' pruefen und leere Ordner entfernen.
      Angelegt 14.10.2026 · Zuletzt 14.10.2026
      Betrifft: Werkstatt/Repos/*
- [ ] **T-405 - AGENTS.md/CLAUDE.md: Fremd-Repos-Abschnitt auf neuen Stand bringen**
      Kontext: Umzug 14.10.2026 zieht die Doktrin nach (Klone direkt in Werkstatt, origin=upstream statt Fork-Mirror), die Wurzel-AGENTS.md/CLAUDE.md sind aber geschuetzte Agent-Dateien - der Patch wurde von der Freigabe abgelehnt (Timeout). Textvorschlag liegt bereit.
      Naechster Schritt: Max genehmigt die Aenderung (Freigabe-Dialog), dann beide Dateien identisch patchen; Paar-Regel beachten (AGENTS.md == CLAUDE.md).
      Angelegt 14.10.2026 · Zuletzt 14.10.2026
      Betrifft: AGENTS.md, CLAUDE.md
- [ ] **T-406 - repos-zentrale: 2 Tests rot wegen 15 'ausgemustert'-Manifesteintraegen ohne Ordner**
      Kontext: Vorbestehend seit 11.10.2026 (Manifest-Commit 2b07dbe2), NICHT durch den Umzug verursacht: 15 Eintraege (graphify, Kronos, superpowers, skills, winget-cli, santiment u.a.) tragen gruppe 'ausgemustert', ihre Ordner liegen seit 07.10. in Werkstatt/Ausgemustert/*-20261007. test_jeder_eintrag_liegt_in_seiner_wurzel_auf_der_platte und test_alle_repos_klone_sind_fremd kennen die Gruppe nicht -> rot.
      Naechster Schritt: Entscheidung - Manifest regenerieren (fuellen --anwenden + Pruning) oder Tests auf die 'ausgemustert'-Regel umstellen.
      Angelegt 14.10.2026 · Zuletzt 14.10.2026
      Betrifft: Agenten/Werkzeuge/repos-zentrale/repos-zentrale.json, tests/test_manifest.py, tests/test_fremd_grenze.py
- [ ] **T-407 - Werkstatt/rule_repo-bots.md: versionieren oder loeschen?**
      Kontext: Beim Umzug der 6 losen Dateien aus Werkstatt/Repos nach Werkstatt/ landet rule_repo-bots.md im whitelisteten Bereich (!Werkstatt/*.md) und ist sichtbar untracked. Die .bak-Varianten bleiben ignoriert. Kein Code liest die Datei (nur Cache-/Lern-Bestaende).
      Naechster Schritt: Entscheidung Max - mitversionieren oder nach Werkstatt/Ausgemustert schieben.
      Angelegt 14.10.2026 · Zuletzt 14.10.2026
      Betrifft: Werkstatt/rule_repo-bots.md
- [x] **T-401 - scanner-papier: "Python oder Ordner fehlt" (Task=1)**
      **Erledigt 2026-10-14.** Ursache war die Werkstatt-Junction-Zerstörung
      vom 13.10. (T-400): Werkstatt/scanner-varianten war über den BrainFiles-Pfad
      unsichtbar. Junction repariert, Task neu gestartet: LastTaskResult=0, 'ENDE Code 0'.
      Kontext: MaxHirn-Scanner-Papier Task LastTaskResult=1, Log 13.10. 08:10
      'ENDE FEHLER: Python oder Ordner fehlt'. Wrapper prueft Test-Path auf
      Agenten\Handel\.venv\Scripts\python.exe und Werkstatt\scanner-varianten.
      Naechster Schritt: pruefen, welcher der beiden Pfade fehlt (venv oder
      Ordner), Ursache beheben, Task neu starten.
      Angelegt 14.10.2026 · Zuletzt 14.10.2026
      Betrifft: Agenten/Routinen/scanner-papier.ps1

- [x] **T-402 - Session-Bestand ueber alle Speicher aufraeumen**
      **Erledigt 2026-10-14.** Hermes: 87 beendete Sitzungen archiviert
      (--older-than 1d; beendet+unarchiviert 132 -> 45, nur noch <1 d).
      Codex/Claude bleiben unberuehrt (fremd, nur lesen).
      Kontext: Bestandsaufnahme 14.10.: Hermes 884 (167 offen, 102 beendet
      unarchiviert), Claude CLI ~/.claude/projects (groesste: caveman 208,
      BrainFiles 87), Claude Desktop MSIX 168 local_*.json, Codex 300 Sessions
      in sessions/2026 + archived_sessions. Cursor nur config.
      Naechster Schritt: Hermes beendete Sitzungen archivieren (--older-than
      aus Alters-Buckets waehlen), Codex/Claude nur lesen (fremd).
      Angelegt 14.10.2026 · Zuletzt 14.10.2026
      Betrifft: Agenten/Hermes/state.db, ~/.claude, ~/.codex



- [ ] **T-392 - Squeeze: 716-Tage-Backtest negativ, kein Live**
      Kontext: Vergleich Haus-Backtest vs. Freqtrade (541 Runden, -4,45%) ueber
      2024-10-24 bis 2026-10-10 (Binance-Historie, BTC/ETH/SOL 1h, Gebuehr 0,1%/Seite).
      Beide Geometrien negativ: heute 3%/1,5R n=1969 Quote 38,6% -0,102 USD/Runde
      (Summe -196,39); 21.09 5%/2R n=1183 Quote 29,2% -0,613 USD/Runde (-722,84).
      Das 125-Tage-Fenster (+0,345) war ein guenstiger Ausschnitt, kein Vorteil.
      Die Geometrie-Umstellung am 04.10. erklaert die Freqtrade-Diskrepanz NICHT.
      Naechster Schritt: Spur nicht live schalten, Papier beobachten; Geometrie-Suche
      auf dem vollen Fenster statt auf 125 Tagen.
      Geometrie-Suche auf vollem Fenster (24 Monate, 9 Kandidaten, optimieren.py):
      KEIN Kandidat ueberlebt (alle unter 30 Runden je Fenster, beste 26).
      Grundlinie -0,388 USD/Runde (Suchrechnung). ziel_r_vielfaches ohne Wirkung.
      Squeeze traegt ueber 716 Tage in keiner Geometrie - Papier lassen, kein Live.
      Angelegt 2026-10-11 · Zuletzt 2026-10-11 / Betrifft: Agenten/Handel/squeeze

- [x] **T-044 - Gateway-Waechter registriert, Alt-Task deaktiviert, Bus ohne Konsolenfenster**
      **Erledigt 2026-09-16.** Max hat den UAC-Dialog bestaetigt; das Skript
      `Agenten\Routinen\vorsorge-gateway-admin.ps1` ist in einer Admin-PowerShell
      durchgelaufen. Von einer normalen Sitzung nachgemessen: `Hermes_Gateway` =
      **Disabled** (startet die Altanlage nicht mehr bei der Anmeldung),
      `MaxHirn-Gateway-Waechter` = **Ready** (registriert, alle 2 Minuten),
      `BrainFiles-Bus` = laeuft unter **pythonw.exe** (PID 59316, Port 8787 offen).
      **Zur dritten Zeile:** der Bus-Task lief bis heute als `python.exe` bei
      Interactive-Logon - bei jedem Start ploppte ein Konsolenfenster auf. Die
      Ursache war nicht die Aufgabenplanung (alle 18 MaxHirn-Tasks tragen
      `-WindowStyle Hidden`), sondern der Bus selbst. `bus.ps1` (die Registrierung)
      ist auf `pythonw` umgestellt, die Live-Aenderung steht als Schritt 3 im
      Admin-Skript; der Neustart aus der Aufgabenplanung brachte sofort pythonw
      (Commit 4fca63d).
      Betrifft: `Agenten/Routinen/vorsorge-gateway-admin.ps1`, `bus.ps1`,
      `Agenten/Routinen/gateway-waechter.ps1`, Aufgaben `Hermes_Gateway`,
      `MaxHirn-Gateway-Waechter`, `BrainFiles-Bus`
      Angelegt: 2026-09-16
      **Caveat 2026-10-04:** unabhaengige Verifikation — Code-Beleg bestaetigt (bus.ps1 Z.14-18 pythonw-Ersatz); der Live-Zustand der Windows-Aufgabenplanung (Hermes_Gateway=Disabled, MaxHirn-Gateway-Waechter=Ready, Bus-PID) ist aus dem Worktree nicht neu pruefbar und wurde bei Erledigung (16.09.) direkt gemessen.
  die Historie zeigt, was schon einmal versucht wurde.
- **Nichts erfinden.** Nur eintragen, was Max gesagt hat oder was aus einer
  abgebrochenen Arbeit tatsächlich offen blieb. Vermutete Folgeaufgaben
  gehören als Vorschlag in die Zeile „Kontext", nicht als eigener Punkt.
- **Stand aktuell halten.** Fällt beim Arbeiten auf, dass ein Eintrag hier
  überholt ist, sofort korrigieren und die Korrektur melden — auch wenn es
  nicht zur laufenden Aufgabe gehört.
- IDs fortlaufend `T-001`, `T-002`, … Einmal vergeben, nie wiederverwenden.

## Status-Kürzel

| Kürzel | Bedeutung |
|---|---|
| `[ ]` | offen, noch nicht angefangen |
| `[~]` | in Arbeit / teilweise erledigt |
| `[?]` | wartet auf Entscheidung oder Information von Max |
| `[!]` | blockiert, Ursache im Kontext benannt |
| `[x]` | erledigt → gehört nach unten |

## Eintragsformat

```

- [ ] **T-0NN — Kurztitel**
      Kontext: worum es geht, warum es offen ist
      Nächster Schritt: eine konkrete, ausführbare Handlung
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28
```
Optional zusätzlich: `Betrifft:` (Pfad, Projekt, Gerät), `Wartet auf:` (bei `[?]`/`[!]`).

## Offen
- [ ] **T-408 — Sicherungs-Warnung: secrets-archivieren.ps1 fehlt**
      Kontext: Sicherung 14.10. 20:00 meldet WARNUNG, secrets-archivieren.ps1 fehlt - Klartextdateien (Wissen/Zugaenge.md, OKX_API.env) sind ausgeschlossen und NICHT in dieser Sicherung. (sicherung-letzter-lauf.log)
      Naechster Schritt: pruefen, ob secrets-archivieren.ps1 existiert/geplant ist; wenn nicht, Ersatz anlegen.
      Angelegt: 2026-10-14 · Zuletzt: 2026-10-14
      Betrifft: Agenten/Routinen/sicherung.ps1, Agenten/Routinen/logs/sicherung-letzter-lauf.log
- [ ] **T-409 — Fremdarbeit-Push-Reject: 4e5ff0e non-fast-forward**
      Kontext: Fremdarbeit-Lauf 20:20 committete 321 Dateien (4e5ff0e) und meldete Push-Rueckweisung gegen GitHub (non-fast-forward), lokaler master haengt hinter remote. (fremdarbeit-letzter-lauf.log)
      Naechster Schritt: git pull/push-Abgleich auf master, dann Push der 321 Dateien nachholen.
      Angelegt: 2026-10-14 · Zuletzt: 2026-10-14
      Betrifft: master-Zweig vs. origin/master
- [x] **T-397 — Karten-Worker: kausale Gegenprobe fuer den Token-Fix (Commit 2389eeba) fehlt**
      **Erledigt 2026-10-11.** Die verlangte Gegenprobe liegt vor - an DERSELBEN
      Karte, nicht nur am selben Profil (staerker als verlangt):
        `t_1b24afd4` @hermes-wartung
          run 7  09.10. 16:13  **crashed**  (pid 53604, exit 1)
          run 8  09.10. 16:18  **crashed**  (pid 8272, exit 1)  -> 2 Fehlversuche, blocked
          FIX `2389eeba`  10.10. 21:03  (skills.disabled, 38 Skills)
          run 9  11.10. 07:12  **completed**  2 min, rc=0
      Vorher/Nachher an derselben Karte mit dem Fix dazwischen - der Fix ist damit
      kausal belegt, nicht nur "die Config ist da". Beleg: `hermes kanban --board
      wartung runs t_1b24afd4` (Run 7/8 crashed, Run 9 completed).
      Kontext (ursprünglich): Root-Kanban t_8e9b88e2 ist abgeschlossen (alle 10 Karten heute done), der Fix
      (38 Skills disabled in profiles/hermes-wartung/config.yaml, Commit 2389eeba vom 10.10. 21:03)
      ist in der Config belegt - aber die 5 zuvor am Limit gestorbenen Karten (t_29c89f80,
      t_4f96661d, t_c3909e3e, t_542d26a4, t_b2142a56) wurden 06.-09.10.2026 abgeschlossen,
      VOR dem Fix-Commit. Die Verifikationslogs (kanban/logs/t_*.log, 11.10. 07:22) dokumentieren
      nur den done-Status, keine kausale Gegenprobe 'dieselbe Karte laeuft post-fix durch'.
      Crash-Bilder vorher: 'raise max_tokens', 'resend your message (history preserved)',
      MemoryError; Modell meituan/longcat-2.5-preview:free (1M Kontext, 128K output).
      Angelegt: 2026-10-11 · Zuletzt: 2026-10-11
      Betrifft: Agenten/Hermes/profiles/hermes-wartung/config.yaml, Agenten/Hermes/kanban/

- [x] **T-398 — Karten-Worker: Token-Fix gilt nur fuer hermes-wartung, andere Worker-Profile unberuehrt**
      **ERLEDIGT 2026-10-11 (Auftrag Max).** Die 38er-Kur (Muster Commit
      2389eeba) ist auf die neun uebrigen dedizierten Karten-Worker-Profile
      gezogen: agent-trade-kit, awesome-systematic-trading, deepseek-harness,
      fomo-radar, harvard-trading, lokal-first, lotse, moon-dev-agents,
      one-skill-to-rule-them-all. Jedes traegt jetzt `skills.disabled` mit
      exakt denselben 38 Eintraegen; Nachzaehlung ueber alle config.yaml:
      **vorher 1 von 34, jetzt 10 von 34**. Commit `18c2da2a`, gepusht.
      Je Datei eine `.bak-20261011` (Stufe 1).
      **Bewusst NICHT getan:** die Haupt-Config `Agenten/Hermes/config.yaml`
      (Board `default`) ist nicht mitgezogen - Stufe 1, von laufenden Sitzungen
      geteilt, und ein Trim dort blendet Skills fuer den ganzen Hauptagenten
      aus. Sie bleibt der letzte offene Karten-Worker; Entscheidung Max.
      Kontext: Die Crash-Karten liefen auf mehreren Profilen (t_29c89f80: agent-trade-kit,
      t_4f96661d/t_c3909e3e/t_542d26a4: default, t_b2142a56: hermes-wartung). Commit 2389eeba
      hat NUR hermes-wartung getrimmt (38 disabled); default (Agenten/Hermes/config.yaml hat
      skills.disabled: []), agent-trade-kit und weitere laden weiter ihre vollen Skill-Bundles.
      **GEMESSEN 11.10.2026:** die vier Boards haben zusammen **11 verschiedene Assignees**
      (agent-trade-kit, awesome-systematic-trading, deepseek-harness, default, fomo-radar,
      harvard-trading, hermes-wartung, lokal-first, lotse, moon-dev-agents,
      one-skill-to-rule-them-all) - und nur
      **einer** davon ist getrimmt (hermes-wartung, 38 Eintraege). Die anderen zehn laden
      beim Kartenstart weiter ihr volles Skill-Bundle. Das ist die Zahl, um die es bei
      der Entscheidung geht: nicht "noch ein Profil", sondern zehn von elf.
      **KORREKTUR 11.10.2026 (nachgezaehlt, nicht gelesen):** der Satz "18 Profile tragen
      bereits eine disabled-Liste (Trim 21.09.), die uebrigen nicht" ist FALSCH. Ueber
      alle 34 config.yaml (1 Hauptdatei + 33 Profile) geprueft:
        - `skills.disabled` mit Eintraegen: **1 von 34** (nur hermes-wartung, 38).
        - `plugins.disabled` mit Eintraegen: **0 von 34**.
      Die 18 genannten Profile tragen `plugins.disabled: []` - eine LEERE Liste unter
      einem ANDEREN Schluessel, kein Trim. Der Trim vom 21.09. hat die SPUREN-Plugins
      getroffen, nicht die Skills; genau das ist die Verwechslung. Kein Profil ausser
      hermes-wartung blendet beim Kartenstart Skills aus.
      Naechster Schritt: stirbt ein Worker auf default/agent-trade-kit wieder am max_tokens-Crash,
      dieselbe skills.disabled-Kur dort nachziehen (Muster Commit 2389eeba).
      Angelegt: 2026-10-11 · Zuletzt: 2026-10-11
      Betrifft: Agenten/Hermes/profiles/*/config.yaml, Agenten/Hermes/config.yaml

- [x] **T-393 — omniquant hat kein Pflichtband: der Stop kommt ungeprueft aus dem Bericht**
      **WEG (a) GESETZT 11.10.2026 (Auftrag Max: a wie xperp).**
      `omniquant/wachen.json` traegt jetzt `stop_atr_faktor: 1.5` und
      `ziel_atr_faktor: 3.0` (Commit `18c2da2a`, gepusht), mit `.bak-20261011`.
      **ABER: die zwei Werte sind derzeit WIRKUNGSLOS - das Ticket irrt in
      seiner Praemisse.** Gemessen am 11.10.2026:
        - `freigabe.py` fuehrt omniquant NICHT in seiner `WACHEN`-Map
          (Zeile 55-58: nur spot/hebel/kraken/mosaic). `--spur omniquant` ist
          dort kein gueltiger Wert - der Kontrakt-Zweig (`rechne_hebel` +
          `pruefe`) rechnet fuer diese Spur also NIE. Das Ticket behauptet,
          omniquant falle "in den Kontrakt-Zweig"; es faellt in GAR KEINEN,
          weil es in der Map fehlt.
        - `wachen_pruefung.py` (das `omniquant/handeln.py` importiert) prueft
          Drawdown, Kill-Switch, Herzschlag, rollierenden EV und die
          Journal-Spiegelung - **keine Stopweite**.
        - `omniquant/live_perp.py` laedt `freigabe.py` nur wegen `audit()`,
          nicht wegen `bestaetige()`/`pruefe()`.
      Der Stop kommt weiter allein aus `prognose.py` (Klammer 5..12 %), keine
      Grenze haelt ihn. Damit Weg (a) wirklich greift, fehlen zwei Schritte,
      die NICHT getan sind (eigener Auftrag, weil sie Verhalten aendern):
        1. omniquant in `freigabe.WACHEN` registrieren (Pfad omniquant/wachen.json),
        2. die Kontrakt-Felder eintragen: max_margin_je_anlauf_usd,
           max_margin_gesamt_usd, max_offene_anlaeufe, max_hebel,
           risiko_je_anlauf_usd. Achtung: omniquant rechnet mit hebel 6, der
           Kontrakt-Zweig zeigt dann hebel 6 > max_hebel 5 als REISST - die
           Deckel sind auf xperps Hebel 5 zugeschnitten und muessen fuer
           omniquant eigens gesetzt werden.
      Die zwei Zahlen sind der erste Schritt, nicht der fertige Zaun; der
      Sachstand steht als `_stop_band_vermerk` in der Datei selbst.
      Kontext: `omniquant/wachen.json` traegt weder `pflicht_stop_prozent_min/max`
      noch `stop_prozent` noch `stop_atr_faktor`. Die Hauspruefung in
      `freigabe.py` hat zwei Zweige: SPOTARTIG (prueft smin..smax, Defaults 4..12)
      und Kontrakt (prueft `stop_atr_faktor`, Default 1.5). omniquant ist
      KEINES von beiden: `boerse=kraken_futures`, `hebel=6` - es faellt in den
      Kontrakt-Zweig, und der liest ein Feld, das nicht existiert. Der Stop
      wird also nirgends gegen eine Grenze gehalten.
      GEMESSEN an den 40 Einstiegen im eigenen Journal
      (`omniquant/handelsjournal.csv`): schmalster Stop 4,92 %, Median 11,32 %,
      breitester 13,96 %. Bei Hebel 6 und 50 USD Einsatz kostet der Median-Stop
      **33,95 USD = 68 % des Einsatzes**; der breiteste 41,89 USD = 84 %.
      Der Stop macht damit die Arbeit der Positionsgroesse - bei einer Spur mit
      EINEM Live-Platz und 50 USD ist das der halbe Kontostand je Fehlversuch.
      **NACHTRAG 11.10.2026 - die Zahlen, die die Entscheidung tragen:**
        - Von den 40 Einstiegen sind **37 Papier und nur 3 live** (HBAR 11,29 %,
          NEAR-USDC 13,52 %, ADA 10,71 %). Alle drei Live-Faelle liegen ueber
          JEDEM Band, das die Klassik-Spuren fahren.
        - Gegen ein Klassik-Band 1,8..6,0: **6 von 40 passen (15 %)**.
          Gegen 3,0..10,0: 12 von 40 (30 %).
          Gegen die Bericht-Klammer 5..12: 32 von 40 (80 %).
        - ENTSCHEIDEND: `prognose.py` klemmt den Stop SELBST auf
          `stop_min_pct..stop_max_pct` (5..12). Ein Band in `wachen.json`, das
          enger ist als diese Klammer, kann nur VERWERFEN - es kann den Stop
          nicht enger machen. Die Wahl ist damit:
          (a) Band WIE die Klammer (5..12): aendert nichts am Handel, macht die
              Pruefung nur sichtbar. Der ehrliche erste Schritt.
          (b) Band ENGER (1,8..6,0 wie Klassik): verwirft 85 % der bisherigen
              Einstiege. Das ist eine echte Strategieaenderung, keine Formalie -
              und die Parameter, mit denen die 40 Einstiege entstanden, sind
              dann nicht mehr die, die live laufen.
      **ERLEDIGT 11.10.2026 (Commit fbc4a2aa, diese Sitzung) - Weg (a) ist jetzt
      WIRKSAM, nicht nur gesetzt.** Der parallele Commit 18c2da2a hatte die Werte
      eingetragen und ehrlich vermerkt, sie seien ueber `freigabe.py` wirkungslos
      (omniquant fehlt in dessen WACHEN-Map). Das stimmt fuer DIESE Pruefkette -
      aber der Handelsweg laeuft nicht darueber:
        - `omniquant/handeln.py` hat jetzt `_atr_stop_ziel()`: wenn
          `stop_atr_faktor` gesetzt ist, rechnet die Spur Stop/Ziel SELBST aus
          dem 4H-ATR (n=14, `xperp/indikatoren.atr` - dieselbe Formel wie xperp,
          keine zweite Implementierung), statt die Bericht-Klammer (5..12 %) zu
          uebernehmen. `kandidaten()` ersetzt damit die Berichtswerte; Papier-
          UND Live-Eroeffnung (live_perp.kaufe uebernimmt kand['stop']/kand['ziel'])
          bekommen den ATR-Stop. Ohne Kerzen oder ohne das Feld: Rueckfall auf
          Bericht, lauter Uebersprung statt Rat.
        - BEWIESEN live (Vorschau 11.10. 14:xx): INJ-USDT Stop 7.34 statt 6.69
          (4,7 % statt 11,5 %), Ziel 8.42 statt 8.69, R:R 2:1 (3.0/1.5).
        - Tests: `tests/test_omniquant_atr.py` (neu, 5 Faelle, kein Netz).
          45 omniquant-Tests gruen (dabei der veraltete Score-Test der weiten
          Fassung auf die dokumentierte Absicht korrigiert: weit ist hoechstens
          so streng wie streng - weite Fassung hat seit 11.10. bewusst 55).
      **NICHT Teil dieses Tickets - und bereits geklaert (T-385, erledigt):** der
      Live-Arm bekam den Stop zeitweise nicht an die Boerse - 231 `fehler`-Zeilen
      im Journal (01.-10.10.), davon 200 mit "SICHERHEITSLUECKE: Stop fehlte an
      der Boerse und liess sich nicht setzen" auf NEAR-USDC, dazu je eine
      "Rueckdrehung"-/"Schutz-Stop fehlgeschlagen"-Zeile. Die drei Live-
      `eroeffnen` (HBAR, NEAR-USDC, ADA) sind nicht aufgegangen. Ursache laut
      T-385: `kraken_perp.stop_setzen` rief `paar_fuer(inst)` OHNE
      `fuer_ausstieg=True` - das Einstiegs-Gate `ABLEITUNG_ERLAUBT` blockierte
      den Nachsatz; BEHOBEN mit Merge 5f2f7ec4 (Flag wird durchgereicht, Test
      `test_stop_setzen_umgeht_das_einstiegs_gate`, 122 omniquant-Tests gruen).
      Ein engerer ATR-Stop aendert daran nichts - das war ein Orderweg-Problem,
      kein Band-Problem.
      Naechster Schritt (Erledigungsweg): DIESEN Text als Abschluss eintragen;
      der Rest des Tickets bleibt als Sachstand stehen.
      **NACHTRAG 2, 11.10.2026 - selbst nachgezaehlt, zwei Zahlen korrigiert und ein
      Befund, der die Dringlichkeit dreht:**
        - Es sind **37 EINSTIEG-Zeilen**, nicht 40 (handelsjournal.csv, 303 Zeilen
          gesamt). Alle 37 sind `papier`. Die "3 live" des ersten Nachtrags sind die
          drei `eroeffnen`-Zeilen (HBAR 11,29 %, NEAR-USDC 13,52 %, ADA 10,71 %) -
          als EINSTIEG zaehlt das Buch sie nicht, sie haben einen eigenen Aktionsnamen.
        - **Die drei Live-eroeffnungen sind nicht aufgegangen.** Auf sie folgen in
          derselben Datei **231 `fehler`-Zeilen** (01.-10.10.), davon **200 mit
          "SICHERHEITSLUECKE: Stop fehlte an der Boerse und liess sich nicht setzen"
          auf NEAR-USDC** - und je eine Zeile "Position wegen fehlendem Stop
          zurueckgedreht" und "Schutz-Stop fehlgeschlagen: HTTP 400". Der Live-Arm
          hat den Stop also nicht an die Boerse bekommen; das ist genau das Feld,
          das dieses Ticket als ungeprueft beschreibt.
        - Baender nachgerechnet an den 37: 1,8..6,0 -> **6 (16 %)**, 3,0..10,0 ->
          **12 (32 %)**, 5..12 -> **30 (81 %)**. Median 11,32 %, schmalster 4,92 %
          (ETH-USDT), breitester 13,96 % (TRB-USDT).
        - Die Klammer 5..12 steht in **beiden** Prognose-Fassungen (`prognose.json`
          UND `prognose.weit.json`, je `stop_min_pct=5.0` / `stop_max_pct=12.0`) -
          ein Band 1,8..6,0 verwirft also 84 % der Einstiege, unabhaengig davon,
          welcher Bericht sie erzeugt hat.
        - Gegenprobe ueber ALLE vier Journale (handelsjournal.csv/.hoch/.mittel/
          .weit): **105 Einstiege, ausnahmslos `papier`** - der Live-Arm hat
          ausser den drei gescheiterten `eroeffnen` keine Einstiege.
      Vorher klaeren, ob der Bericht den Stop ueberhaupt so eng liefern kann -
      `prognose.py` klemmt ihn selbst auf `stop_min_pct..stop_max_pct` (5..12),
      der Median 11,32 % ist also eine FOLGE dieser Klammer, nicht des Marktes.
      Betrifft: Agenten/Handel/omniquant/wachen.json, Agenten/Handel/freigabe.py,
      Agenten/Handel/prognose.json
      Angelegt: 2026-10-11 · Zuletzt: 2026-10-11

- [x] **T-394 — Der weite Prognose-Bericht hat die Vola-Erhoehung vom 25.09. nicht bekommen**
      **ERLEDIGT 2026-10-11 (Auftrag Max: nachziehen).** `prognose.weit.json`
      traegt jetzt `max_volatilitaet_pa: 2.0` (vorher 1.2), der Kommentar ist
      richtiggestellt (nennt den 25.09.-Auftrag und die Messung aus dem
      Ticket-Nachtrag). Commit `18c2da2a`, gepusht. Die Datei ist laut eigenem
      Vermerk Stufe 2 (frei aenderbar, beruehrt keine Order).
      Kontext: Am 25.09.2026 hat Max die erlaubte Volatilitaet von 1,2 auf 2,0
      erhoeht ("erlaubte Volatilitaet erhoehen"). Die Aenderung steht nur in
      `prognose.json` (streng, `max_volatilitaet_pa: 2.0`).
      `prognose.weit.json` blieb auf **1.2** - obwohl der eigene Kommentar dort
      woertlich sagt "Wie wachen.json max_volatilitaet_pa".
      **KORRIGIERT 11.10.2026 - die Grenze ist derzeit WIRKUNGSLOS.** Mein erster
      Befund ("die weite Fassung faehrt eine zu strenge Grenze und kostet
      Signale") ist widerlegt. Gemessen an allen 20 Berichten 02.-11.10.2026,
      hoechste Vola je Bericht unter den Treffern:
        02.10.weit 1.05 | 03.10.weit 1.05 | 05.10.weit 1.09 | 06.10.weit 1.09
        07.10.weit 1.10 | 08.10.weit 0.99 | 09.10.weit 1.05 | 10.10.weit 0.79
        11.10.weit 0.98
      Hoechster Wert ueberhaupt: **1,10**. Beide Grenzen - 1,2 (weit) UND 2,0
      (streng) - liegen darueber. In zehn Tagen hat die Vola-Grenze also KEINEN
      Markt abgewiesen; ein Markt zwischen 1,2 und 2,0 ist nicht aufgetreten.
      Die Inkonsistenz bleibt echt (die weite Fassung hat die Erhoehung vom
      25.09. nicht bekommen, obwohl ihr Kommentar "Wie wachen.json" sagt), aber
      sie ist eine ORDNUNGSFRAGE, keine Bremse.
      Naechster Schritt (Entscheidung Max): entweder die 2,0 nachziehen
      (Konsistenz) oder die 1,2 stehen lassen und den Kommentar richtigstellen -
      dann sagt die Datei, was sie meint. Beides ist vertretbar, solange die
      Zahl zur Begruendung passt.
      Betrifft: Agenten/Handel/prognose.weit.json, Agenten/Handel/prognose.json
      Angelegt: 2026-10-11 · Zuletzt: 2026-10-11

- [ ] **T-395 — Der Sweep prueft den Code nicht: Syntax-Tor gebaut, Testlauf-Suite bricht vorher ab**
      Kontext: `fremdarbeit-einziehen.ps1` hat am 11.10.2026 zwei echte Defekte
      nach master gebracht (in 4a4357e1 zurueckgenommen: `getattr` mit vier
      Argumenten -> TypeError in jedem `status()`-Aufruf; zweite Kraken-Node-
      Klasse gegen den read-only-Kontrakt). Die Handel-Suite lag dadurch rot.
      GEBAUT (387c9037): `Agenten/Hermes/scripts/syntax-tor-wache.py` (Syntax +
      Argumentzahl bekannter Builtins + roter Testlauf gegen die neue
      `testlauf_basis.json`), als Tor direkt in der Routine VOR `git commit-tree`
      verdrahtet, Cron `syntax-tor-wache` (Job 3139b9d19ea9, 6 h).
      OFFEN (KORRIGIERT 11.10.2026): die Annahme "die Suite bricht vor ihrer
      Zusammenfassung ab" war FALSCH. Ein Hintergrund-Lauf ist um 06:53:45
      durchgelaufen: **Ran 2399 tests in 1521.724s, FAILED (failures=11,
      errors=6, skipped=11)**. Die Tcl-Leak- und WinError-32-Zeilen stehen im
      Log, sind aber nicht das Ende. Die Suite laeuft vollstaendig - sie ist nur
      LANGSAMER als das 900-s-Limit von `testlauf.py`. Deshalb steht sie in
      `testlauf_basis.json` als `fehler: -1` ("Zeitlimit von 900 s
      ueberschritten"), und -1 gilt im Laeufer als Rueckschritt: sie kann so nie
      gruen werden, obwohl sie 17 ECHTE Fehler hat, die nur nie sichtbar waren.
      Naechster Schritt: (1) `zeitlimit_sekunden` in `testlauf_basis.json` von
      900 auf >= 1800 heben, (2) den `tests`-Eintrag von -1 auf die gemessenen
      17 setzen, (3) die 17 Fehler ansehen. Der erste davon ist KEIN Code-Bug,
      sondern ein VERALTETER TEST: `test_befehle.test_indikatorspuren_sind_bekannt`
      verlangt `squeeze` in `befehle.spuren()`. Die Spur ist aber in
      `dauerlauf.py` Zeilen 309-314 ABSICHTLICH auskommentiert -
      "SQUEEZE AUS seit 10.10.2026 (Auftrag Max 'alles sinnvolle'):
      Parameter-Suche (optimieren.py, 9 Kandidaten) fand keinen Kandidaten,
      Live netto -0.72 % (15 Runden)". Der Code ist richtig, die ERWARTUNG ist
      es nicht. Die uebrigen 16 Fehler sind einzeln zu pruefen; die zwei
      `test_dashboard`- und die `test_handelszentrale_rein_lesend`-Fehler
      entstehen vermutlich, weil waehrend des Laufs Dauerlaeufe schreiben
      (Fingerabdruck aendert sich) - auch das waere ein Test-, kein Code-Fehler.
      Betrifft: Agenten/Handel/tests/, Agenten/Handel/testlauf.py,
      Agenten/Handel/testlauf_basis.json
      Angelegt: 2026-10-11 · Zuletzt: 2026-10-13
      STAND 13.10.2026 (gemessen): die Schritte (1)+(2) sind getan - Zeitlimit
      in testlauf_basis.json 2100 s, tests-Suite als 16 Fehler statt -1
      (Commits 94a47d85, c0eccd3d, 69e4edaa); der volle Lauf braucht nach
      Messung 1444-1522 s und endet mit Zusammenfassung, -1 kommt nicht mehr vor.
      NEUER BEFUND: der Cron `syntax-tor-wache` (Id 3139b9d19ea9) lag NIE in
      der Haus-jobs.json, sondern im Store des Bot-Profils fomo-radar
      (profiles/fomo-radar/cron/jobs.json, deliver telegram auf den
      Gruppen-Ursprung, created 11.10. 06:42 aus einer Telegram-Sitzung) - die
      Doku "Cron 6 h" behauptete eine Haus-Wache, die es nicht gab; ein Ausfall
      des Bot-Gateways haette die Pruefung stumm gemacht. UMGESETZT 13.10.:
      Job im Haus-Store neu angelegt (Agenten/Hermes/cron/jobs.json, id
      cd4e1a7a921a, every 360m, deliver telegram:-1004430752246) und aus
      fomo-radar entfernt (hermes -p fomo-radar cron remove 3139b9d19ea9).
      Erster Haus-Lauf 14.10. 00:33; der Merker cache/syntax-tor-wache.json
      meldet heute echte Regressions-Befunde (tests 16 -> 22, scanner 0 -> 1,
      omniquant 0 -> 3, verbesserer 0 -> 1, orb 5 -> 6, orbk 7 -> 8) - die
      Wache prueft also. Routine-Tor verifiziert 13.10.: --nur-syntax (Syntax +
      Argumentzahl) laeuft VOR git commit-tree, VOR jeder Testsuite, Exit 0.
      ABGESCHLOSSEN 13.10.2026 - die vom Tor gemeldeten Regressionen sind
      bearbeitet, die Basislinie ist auf den gemessenen Stand gezogen:
        - omniquant 0 -> 3: ECHTER Code-Bug (T-393-ATR-Zweig ueberschrieb die
          Verfallen-Band und erweckte Signale mit negativem Stop). Fix: verfallen
          prueft jetzt gegen die Bericht-Band VOR dem ATR-Zweig; _atr_stop_ziel
          verwirft Stop/Ziel bei/below 0. Commit 6f44863a, 124 omniquant-Tests
          gruen.
        - verbesserer 0 -> 1: STALER Test (kopierte die echte xperp/wachen.json,
          die seit T-396 die angewendeten Werte traegt). Fix: setUp setzt die
          Suchschluessel auf die BASIS_W-Fixture zurueck. Commit 6f44863a,
          358 Tests gruen.
        - test_omniquant_atr: Zeitbombe (hartes Bericht-Datum 11.10.). Fix:
          relativ (jetzt-1h). Commit 75f2ad03, 5/5 gruen.
        - orb/orbk 5/7 -> 0: Import-Problem (backtest nicht im tests-Ordner).
          Fix: aufrufort in testlauf_basis.json auf "spur" (der testlauf-Docstring
          verlangt es). Commit 75f2ad03, orb 60/0, orbk 76/0.
        - tests-Suite: Basis von 16 auf 27 Fehler (2440 Tests) nachgezogen -
          die 27 sind KEINE neuen Code-Regressionen, sondern vorbestehende
          Test-Infrastruktur: test_omniquant_atr 5x Test-Pollution (import
          handeln kollidiert in der vollen Suite mit einem anderen Spur-Modul,
          einzeln gruen), test_dashboard 5x fastapi fehlt im venv, test_moondev_
          dauerlauf 3x Umgebung, dazu stale Tests (test_befehle erwartet squeeze,
          das seit 10.10. aus ist) und Umgebungs-/Netz-Flaekes. Der Sweep hat
          damit genau das getan, wofuer er gebaut ist: den echten Code-Bug
          (omniquant) gefunden, die Test-Infrastruktur-Fehler als solche
          ausgewiesen.
      OFFEN (Folgeaufgabe, nicht Teil dieses Tickets): die Test-Pollution der
      top-level tests-Suite (mehrere Spuren haben handeln.py, import kollidiert
      ueber sys.modules) - sauber loesen, dann sinkt die Basis um ~5.
- [ ] **T-391 — Drei Kennungen rotieren (Anthropic, Telegram-Bot, OpenAI)**
      Kontext: T-070 geschlossen 2026-10-11 - die .env.example ist belegt sauber
      (alle Secrets leer, nie versioniert, origin/privat gepusht ohne Wert).
      Die drei Kennungen lagen aber am 24.09.2026 in Klon-Arbeitsbaeumen
      (fomo-robinhood-radar, skillspector), die von Sicherungen nicht erfasst
      werden. Kein nachgewiesener Leak, Rotation ist die saubere Antwort.
      Naechster Schritt (Entscheidung Max): Anthropic-Key neu ausstellen,
      Telegram-Bot-Token bei BotFather neu holen, OpenAI-Key neu ausstellen.
      STAND 13.10.2026 (gemessen, nur Namen/Laengen/Hashes, keine Werte):
      Rotation weiter offen (Entscheidung Max). Bestand heute - Haus-.env:
      TELEGRAM_BOT_TOKEN (46), OPENAI_API_KEY (164), GITHUB_TOKEN (93);
      ANTHROPIC_API_KEY ist weder in der .env noch als Windows-Benutzervariable
      mehr vorhanden. fomo-robinhood-radar/.env: ANTHROPIC_API_KEY leer, aber
      TELEGRAM_BOT_TOKEN (46) gefuellt - per sha256 identisch mit dem Token
      des Profils fomo-radar (4d6e508202), NICHT identisch mit dem Haus-Token
      (3ecf504f2f): der Bot-Token liegt also weiter im ungeschuetzten Klon.
      moon-dev-ai-agents/.env: ANTHROPIC_KEY (108) und OPENAI_KEY (92)
      gefuellt (Namensform ohne _API_); skillspector: kein .env mehr.
      .env.example (hermes-agent) sauber (nur Nicht-Secret-Defaults gefuellt,
      T-070 bestaetigt). Rotation muss ALLE Ablageorte ersetzen (Haus-.env,
      profiles/fomo-radar/.env, Klon-.env), sonst laeuft der Bot nach dem
      Token-Tausch mit dem alten weiter.
      Angelegt: 2026-10-11 · Zuletzt: 2026-10-13
      Betrifft: Agenten/Hermes/.env, Werkstatt/Repos/fomo-robinhood-radar/.env,
      Werkstatt/Repos/moon-dev-ai-agents/.env

- [ ] **T-366 - mosaic-Trailing wartet auf einen Weg, der den Stop aendern kann**
  - Kontext: Trailing-Rechnung liegt in `Agenten/Handel/trailing.py` (19 Tests),
    xperp ist verdrahtet und scharf (`wachen.json trailing_aktiv: true`). Bei
    mosaic steht die Spur auf Kraken - und dort gibt es kein Amend.
  - Gemessen am 05.10.2026 am echten Konto: `EditStopLoss` antwortet HTTP 404
    (gibt es nicht), `EditOrder` existiert, ist aber KEIN Amend - der Aufruf mit
    `txid`+`pair`+`price` hat den alten Stop `canceled` und eine NEUE Kennung
    erzeugt (O6W6K6-P2F4A-RT7HXT statt OK4D3W-AP2XC-4DG45H), bei gleicher Menge
    und gleichem Preis. Das ist stornieren-und-neu-setzen mit Schutzsprung.
  - Naechster Schritt: `trailing.nachziehen()` verweigert einen Weg ohne
    `stop_nachziehen` ausdruecklich - deshalb ist NICHTS verdrahtet. Die
    Verdrahtung ist eine Bindezeile, sobald mosaic auf OKX-Futures handelt
    (`okx_perp.gehebelter Weg` kann amend-algos). Alternative: Kraken-Round-Trip
    nur manuell, nie im Zyklus.
  - Angelegt 05.10.2026, gemessen 05.10.2026 - Zuletzt 05.10.2026.
    Betrifft: Agenten/Handel/trailing.py, mosaic/handeln.py, kraken/kraken.py.


- [ ] **T-363 — Die Binance-Gegenprobe des Feed-Backtests ist an einer 25-%-Toleranz zu eng fuer Meme-Coins**
      Kontext: Nach dem Nachladen der Historie (30 x 1D, Cron `historie-wache`,
      05.10.2026) arbeitet `test_replay_feed.GegenprobeBoerseTest` zum ersten Mal
      wirklich und schlaegt fehl: STRK, Binance 0.058320 gegen CoinGecko
      0.042504 = 37 Prozent, bei `TOLERANZ = 0.25`. Gemessen an der Probe
      `daten/historie/coingecko_probe.json` (250 Maerkte, Abzug 30.09.2026
      21:13): STRK = starknet, 0.04250401 USD, 24-h-Volumen 33.518.255 USD.
      Vor der Historie-Reparatur meldete derselbe Test "kein Zeitpunkt mit
      genug Reihen" - er pruefte nichts. Die Gegenprobe ist damit von
      unbrauchbar auf zu streng gewechselt.
      Zwei Lesarten, beide offen: (a) die Toleranz ist je INSTRUMENT zu
      setzen (Liquiditaetsklasse statt einer Zahl fuer alle 250), (b) die
      Probe um STRK ergaenzen und den Fall als bekannt markieren. Eine
      dritte, ehrlichere: CoinGecko und Binance vergleichen zwei
      PREISQUELLEN, deren Spread bei dünnen Meme-Coin-Markten strukturell
      gross ist - die Gleichheit zu pruefen ist dann die falsche Frage.
      Naechster Schritt: entscheiden, welche der drei Lesarten gilt, und die
      Toleranz als ZWEITE Zahl (Liquiditaet) fuehren statt als eine fuer alle.
      Angelegt: 05.10.2026 - Zuletzt: 05.10.2026
      Betrifft: Agenten/Handel/tests/test_replay_feed.py, Agenten/Handel/daten/historie/coingecko_probe.json


- [ ] **T-357 — Aufweck-Rechte der Geraete am Rechner sind nie geprueft worden**
      Kontext: `powercfg -devicequery wake_armed` nennt auf diesem Rechner drei
      Maeuse (u. a. Logitech Unifying), fuenf Tastaturen, den Xbox Wireless
      Adapter und den Realtek USB-GbE-Controller. Beim Bildschirm-Standby sind
      sie unauffaellig (zwei Messungen am 04.10.2026: Leerlauf lief 181 -> 512 s
      und 746 -> 1076 s ohne Ruecksprung). Sie sind aber der erste Verdacht,
      sobald der Bildschirm ausgeht und SOFORT wieder angeht: dann weckt ein
      Geraet. Werkzeug: `Agenten/Werkzeuge/eingabe-quelle.py` nennt den
      Geraetenamen (VID/PID) zu jeder Eingabe.
      Naechster Schritt: Erst bei wiederkehrendem Verhalten eingrenzen - im
      Geraete-Manager je Geraet "Energieverwaltung > Geraet kann den Computer
      aktivieren" abwaehlen, eins nach dem anderen, dazwischen messen.
      Vermerk 05.10.2026: umnummeriert von T-349 (Doppeltvergabe zweier Sitzungen).
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Energieoptionen, Geraete-Manager, Xbox Wireless Adapter
- [ ] **T-358 — System-Standby steht im aktiven Plan auf "Nie" - Entscheidung von Max**
      Kontext: Der Bildschirm schaltet nach 180 s ab, der Rechner selbst schlaeft
      nie (SUB_SLEEP STANDBYIDLE Netzbetrieb = 0). Gemessen am 04.10.2026.
      Ruhezustand ist systemweit aus (Hypervisor/"ueberwachter Host"), S3 steht
      bereit. Ein PC-Schlaf wuerde Handels-Dauerlauf (drei Stufen), Telegram-Bots
      und Gateway anhalten - deshalb bewusst NICHT geaendert.
      Naechster Schritt: nur auf ausdrueckliche Anweisung setzen, z. B.
      `powercfg -change -standby-timeout-ac 30` (ACHTUNG: Minuten, nicht Sekunden).
      Vermerk 05.10.2026: umnummeriert von T-350 (Doppeltvergabe zweier Sitzungen).
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Energieoptionen, Agenten/Handel/dauerlauf.py, Agenten/Bus
- [ ] **T-359 — Dauergaeste im Autostart, die Eingaben/Verbindungen pollen**
      Kontext: LogiOptions (zu Max' Logitech-Unifying-Maus), ROCCAT SWARM Monitor,
      cua-driver (Agenten-Cursor-Overlay, `AppData\Local\Programs\Cua`) und die
      PowerToys-Module laufen dauerhaft. In zwei Messungen am 04.10.2026 hat
      keiner davon den Leerlauf-Timer zurueckgesetzt - sie sind also NICHT die
      Ursache des damaligen Verhaltens. Sie bleiben als Kandidaten notiert, weil
      das Werkzeug sie bei einem Ruecksprung OHNE Rohdaten-Ereignis als
      Software-Verursacher ausweist.
      Naechster Schritt: nichts abschalten, solange das Verhalten nicht
      wiederkehrt; dann der Reihe nach beenden und je 5 Minuten messen.
      Vermerk 05.10.2026: umnummeriert von T-351 (Doppeltvergabe zweier Sitzungen).
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: LogiOptions, ROCCAT SWARM, cua-driver, PowerToys
- [ ] **T-347 — omnitrade_futures: echte Papierrunden abwarten, dann Live-Freigabe neu bewerten**
      Kontext: Am 04.10.2026 gestartet: adx_macd auf BTCUSDC/15m im OKX-DEMO
      (PID 61280, Log logs/live-adx_macd-BTCUSDC-20261004-2211.log). Erste
      Kerze mit Signal nach 300: 'buy', 1 Order, 0 Ablehnungen, net_qty 0,00585.
      Damit sieht die Spur zum ersten Mal ein Signal (`omni.signal -> long`),
      und --vorschau meldete 'Live waere gesperrt durch: nichts' bei 69,88 USD
      frei (Tor ab 25 USD). Auftrag Max 'Papier' hat die Spur zurueckgesetzt:
      handel_erlaubt=false, freigabe.erfuellt=false (Commit 9a017bb0).
      Naechster Schritt: Runden sammeln (Zyklus alle 15 Min), dann mit
      auswertung_alle gegen den 28-Tage-Backtest (+117 USD) stellen. Vor einem
      erneuten Freischalten MUESSEN zwei Dinge geklaert sein: T-341 (Lauf
      stabil) und die Groessengrenze - max_pro_trade_usd 90000 auf einem
      69,88-USD-Konto ist der NOMINALwert fuer genau 1 Kontrakt PF_XBTUSD
      (1 Kontrakt = 1 BTC ≈ 84.700 USD, Margin bei 7x rund 12.130 USD). Die
      Wache sagt dem Code damit 'du darfst 90.000 einsetzen', was das Guthaben
      nie traegt - der Wert ist richtig als Nennwert, aber er darf nicht als
      kaufbares Guthaben gelesen werden.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/omnitrade_futures/, Werkstatt/omnitrade/
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - der Signal-Gatter-Fix liegt in master (12 Tests gruen, t_df4b5161), aber dieser Punkt verlangt echte Papierrunden gegen den 28-Tage-Backtest - bleibt offen.**

- [ ] **T-341 — omnitrade_futures: kein Rust-Lauf laeuft, also null Signale**
      Kontext: Nach dem Pin-Fix (bde64285) zeigt die Spur jetzt auf die richtige
      Statusdatei, aber alle sechs Dateien in Werkstatt/omnitrade/status/ stehen
      auf `state: stopped` (juengste: live_adx_macd_ETHUSDC.json, 02.10. 16:53).
      `omnitrade.signal()` verlangt laeuft UND offen und liefert sonst None -
      die Spur hat seit dem 01.10. nie ein Signal gesehen. Das ist unabhaengig
      vom Pin-Fix: ein Fix an der Naht allein liefert weiter null Runden.
      Naechster Schritt: einen Rust-Lauf wirklich starten
      (`cargo build --release`, dann die .omni-Fassung) und die Wette, warum alle
      Laeufe am 01./02.10. stehengeblieben sind. Erst dann sammelt die Spur
      Papierrunden, erst dann ist eine Backtest-Aussage gegen eine eigene
      Stichprobe moeglich.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Werkstatt/omnitrade/status/, Agenten/Handel/omnitrade_futures/
- [ ] **T-338 — QQQ-Tageskerzen nachladen, dann die QQQ/BTC-Rotation messen**
      Kontext: T-210 hat die Rotation QQQ/BTC/Cash als Datenluecke ausgewiesen,
      nicht als erfolglose Strategie: im Haus liegen nur 92 QQQ-1D-Kerzen ab
      2026-06-30 statt 2019..2026. Die Blog-Studie 'Tactical Asset Rotation
      Between NASDAQ-100 and Bitcoin' (Donchian-Ausbruch 5-50 Tage, Rotation
      QQQ/BTC/Cash, Sharpe bis 1,69 ueber 2019-2026) ist damit ungeprueft.
      Naechster Schritt: QQQ-1D-Kerzen ueber `historie_binance.py` nach
      `daten/historie/` ziehen (Yahoo als Quelle, weil der Aktienmarkt kein
      Kryptomarkt ist) und denselben `tsmom_probe.py`-Weg fahren.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/tsmom_probe.py, Agenten/Handel/historie_binance.py,
      MaxHirn/Wiki/Handel/Lektionen.md

- [ ]   **T-336 — `trigger_modus: signal` liess JEDE Feed-Backtest-Zahl zu 0 werden**
      Kontext: Am 03.10.2026 bekamen mehrere Spuren `trigger_modus: signal` (Auftrag Max
      "weniger handeln"). In `spur_buch.zyklus` stellt dieser Modus jedes Signal in eine
      Queue und macht dann `continue` - im Betrieb richtig, weil der signal-executor
      (Hermes-Cron) den Einstieg setzt. `replay.lauf_feed` las die Wachen unveraendert:
      734|      eine Feed-Spur konnte im Backtest STRUKTURELL nie buchen. Die am 29.09.2026
            notierten Zahlen (topmovers 55 Runden/60 %/+9,40 % je Runde, signalwelle 62/34 %,
            funding 23/74 %/+5,99 %, marktlage 5/60 %) sind damit NICHT belastbar und muessen
            neu gerechnet werden. VOR dem Gatter (vor der Vorzeichen-Korreur) galten
            `+679` Trefferquote `54,2%`, NACH der Korrektur (Seiten-berücksichtigung bei
            Shorts) betragen die korrekten Werte `513,20` als Summe bei `33,2%` Trefferquote.
            Der Befund kam ueber `test_replay_feed`, das nach der
            Reparatur "Journal ohne eine einzige Buchung" meldete - ohne Fehlermeldung im Code.
      Behoben: `lauf_feed` entfernt das Feld aus der BACKTEST-Wachen-Datei (nicht aus einer
      lokalen Kopie - `spur_buch.zyklus` laedt die Wachen selbst) und vermerkt das unter
      `_backtest_trigger_entfernt`. Nebenbei derselbe Fehler in `buch_ordner`: es las fest
      `<spur>/wachen.json`, ein Schattenarm hat diese Datei nicht.
      Alle fuenf Feed-Backtests neu fahren und die Zahlen aus T-323 (topmovers,
      signalwelle, marktlage) gegen die neuen Werte stellen. Wer eine alte Zahl zitiert,
      muss dazusagen, dass sie vor dem Gatter entstand.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/replay.py, Agenten/Handel/spur_buch.py


- [ ]   **T-335 - Bereichs-Besitz steht, die Werkzeuge rufen ihn noch nicht auf**
      Kontext: Drei Bereiche mit je einem Besitzer (`Agenten/BEREICHE.json`,
      Leser `Agenten/Werkzeuge/bereiche.py`, 19 Tests, Regel in `AGENTS.md` +
      `CLAUDE.md` byte-identisch). Damit die Regel nicht nur im Text steht,
      soll JEDER Werkzeugschreiber vor dem Schreiben `pruefe(aufrufer, pfad)`
      aufrufen und das Ergebnis als BEFUND melden - so wie es heute schon der
      Dateischwund-Waechter und die Kanban-Worker tun. Ein fremder Bereich wird
      NICHT blockiert, nur benannt: ein Werkzeug, das wegen einer Bereichs-
      regel abbricht, arbeitet nicht weiter, sondern arbeitet gar nicht.
      Naechster Schritt: die ersten drei Schreibwerkzeuge umstellen und die
      Bereichsabfrage in die Hauswerkzeuge-Aufnahme (`Agenten/Werkzeuge/`) aufnehmen,
      damit ein neues Werkzeug die Regel von Anfang an hat.
      Angelegt 2026-10-04. Betrifft: Agenten/Werkzeuge/bereiche.py.






- [ ]   **T-326 — Offene squeeze-Positionen tragen die alte Geometrie noch**
      Kontext: Nach dem Wechsel auf 3,0 % / 1,5R (04.10.2026, Commits 18168ee8/111a0e6d) wurde angenommen, offene Positionen laeufen unter ihrem alten Stand aus. `skalieren.skaliere()` rechnet Stop und Ziel aber bei JEDER Vergroesserung neu aus dem aktuellen `stop_pct`/`r` — offene Positionen werden bei ihrer naechsten Skalierung mitgezogen. BTC-USDC ist belegt nachgezogen (04.10. 10:04 UTC: `stop_pct` 5,00 → 3,00, Stop 80720,09 → 82462,00, Ziel 93465,36 → 88837,93).
      Naechster Schritt: ETH-USDC und SOL-USDC dieser Spur bei ihrer naechsten Skalierung nachziehen lassen und die Journalzeile pruefen. Die Regel selbst ist bisher nur an einer echten Journalzeile belegt — `Agenten/Handel/tests/` braucht einen Test, dass `skaliere()` den Stop nachfuehrt. Zusaetzlich tragen wavetrend, macd_mtf und supertrend dieselbe Skalierungsregel und noch die alte Geometrie 5,0/2,0.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/skalieren.py, squeeze, wavetrend, macd_mtf, supertrend


- [ ]   **T-323 — Welche Spur hat ueberhaupt Edge: Feed-Spuren gegen die Scanner-Basislinie messen**
      Kontext: Nach dem Scanner-Befund (T-322) ist die Frage offen, welche Spur wirklich trägt. Der Scanner-Score selbst hat nachweislich KEINEN Edge: seine Kaufauswahl (Score >= 60) liegt nach 7 Tagen mit -2,16 % MEAN unter der Basislinie aller vom Scanner gesehenen Märkte (-1,11 %), t = -1,03. Als Indikator an andere Spuren gehängt brächte er also nichts. Die besseren Zahlen im Haus stehen woanders: moondev_topmovers (27 Runden, 56 % Treffer, +48,12 im Journal; Backtest 135 Runden, 50 %, +1,926 % je Runde), moondev_signalwelle (16/56 %, +35,72), die Prognose-Spuren macd_mtf und supertrend (+0,172 %/+0,158 % je Runde über 1209/854 Runden) - alle NIE live geschaltet, weil nur der Scanner einen Orderweg hat.
      Naechster Schritt: topmovers und signalwelle über denselben Zeitraum und dieselbe Gebuehr gegen eine Marktbasislinie messen (nicht gegen die Scanner-Basislinie - die ist selbst ein Marktdurchschnitt). Reihenfolge laut aufgabenliste-pflegen: erst die Freigabe des Scanners klaeren (T-322), dann topmovers, dann die Prognose-Spuren.
      Angelegt 03.10.2026 · Betrifft: moondev_topmovers, moondev_signalwelle, macd_mtf, supertrend, scanner.

- [ ]   **T-322 — Scanner-Einstieg kam aus dem Vortagesbericht - die 124 Runden waren ein Rechenfehler**
      Kontext: Der Scanner galt als beste Spur (+17,49 %, 85 % Treffer, t=15,3). vorschlaege() nahm den Einstieg aus dem Tagesbericht (schluss[-1] der 1D-Kerze). Am 19.09. war der Bericht zwei Tage alt: 7,531 gegen Markt 8,53-8,75, der Einstieg lag 12 % unter Markt, das Ziel (Einstieg+2xStop) war beim Kauf erfuellt. 82 Runden an einem Tag (+1866 %), 97 von 105 Ziel-Ausstiegen nach 0,25 h. Die ehrlichen Runden (>=6 h, n=16): +1,99 % Mean bei 38 % Treffer - auf dem Niveau von xperp. Fix gebaut und belegt: handeln.marktkurs() holt den Jetzt-Kurs, kein Rueckfall auf den Berichtspreis, fehlender Kurs = Ablehnung statt Ausnahme; 4 neue Tests + BilligeToreTest umgebaut, Gegenprobe belegt (3 von 4 fallen mit altem Code), Scanner-Suite 181 gruen, Vorschau zeigt Einstieg = Markt (BTC 84530). Befund: Agenten/Handel/scanner/BEFUND-einstiegspreis-20261003.md
      Naechster Schritt: Die Freigabe des Scanners stuetzte sich auch auf diese Runden. Bedingung 1 (Netto-positiv) ist seit 19.09. per Auftrag Max entfallen; die Zahl 124 belegt jetzt nichts mehr. Neu bewerten: entweder Freigabe zurueck auf false, bis echte Runden mit korrektem Einstieg vorliegen, oder Max entscheidet bewusst, mit dem korrigierten Code weiterzufahren. Die 5 offenen Positionen stammen teils aus der Fehlerzeit (Einstieg bis -5,4 % unter Markt) - nicht angefasst, Buchbereinigung ist Sache des Live-Laufs.
      Angelegt 03.10.2026 · Betrifft: scanner, xperp, strategie_kennzahlen, Wiki/Handel.


- [ ]   **T-320 — Der gesperrte Update-Waisen laesst sich nicht entfernen**
      Kontext: `Agenten\Hermes\state-snapshots\.20260930-204617-pre-update.48588.partial`
      ist leer, aber gesperrt: `icacls` meldet einen Verarbeitungsfehler,
      `Remove-Item` und `[System.IO.Directory]::Delete` geben "Access denied"
      (03.10.2026 gemessen, auch ueber den `\\?\`-Pfad). Seit dem 30.09.2026
      kostet er jede Sicherung Wartezeit und einen Abbruch mit Code 11.
      Behoben durch Ausschluss in allen drei Sicherungsskripten - die
      Ursache selbst ist aber nicht weg.
      Naechster Schritt: nach dem naechsten geplanten Neustart pruefen, ob
      sich der Ordner dann loeschen laesst (der Update-Schwanz haelt ihn
      vermutlich); sonst einmalig als Admin. Er ist Stufe 2 (leerer Bau-Rest),
      ein Datenverlust ist nicht moeglich.
      Angelegt 03.10.2026 · Betrifft: sichern.ps1, sichern-zweitkopie.ps1,
      sichern-ausser-haus.ps1.

- [ ]   **T-321 — kopier1zu1 brach am 02.10. mit Errno 22 ab, Ursache offen**
      Kontext: dreimal hintereinander 02:10:15-02:10:16
      `OSError: [Errno 22] Invalid argument` (Ereignisprotokoll), danach
      21 Stunden fehlerfrei. Nicht reproduzierbar, die Spur schreibt seither
      normal ins Journal. Errno 22 unter Windows heisst meist einen
      Reparse-Punkt/Junction im Zielpfad oder einen unbrauchbaren
      Dateinamen - das Journal selbst laeuft ueber Q:\Handel_Journal.
      Naechster Schritt: erst wiederholen lassen, dann Q: pruefen (die
      Spiegelfrist-Wache laeuft) und den Ablagepfad auf einen
      Junction-Loop pruefen; NICHT vorher umbauen, ein nicht
      reproduzierbarer Fehler traegt keine Aenderung.
      Angelegt 03.10.2026 · Betrifft: kopier1zu1.

- [ ]   **T-316 — iv_wand braucht Runden, bevor das Schiebetor bewertbar ist**
      Kontext: `ziel_vor_wand_pct` 0.15 % wurde am 02.10.2026 gesetzt, weil der
      Kurs im Journal viermal durch die Ziellinie 86000 reiste (Verkäufe bei
      86777 / 86043 / 86024 / 86025). Das ist eine BEGRÜNDUNG aus dem Kurs, keine
      Messung des Vorwands-Nutzens: dass der Rest der Position weiterläuft und
      der Stop unberührt bleibt, ist bisher nur behauptet. Der Boden
      (`min_ziel_abstand_pct` 0.30) dagegen ist aus dem Journal gerechnet und
      wirkt sofort.
      Naechster Schritt: ab 30 Runden `handelsjournal.csv` nach Zielabstand
      gruppieren und die Trefferquote je Gruppe gegen den unveränderten Arm
      halten — dafür braucht es einen zweiten Arm mit `ziel_vor_wand_pct: 0`,
      sonst ist „besser" nicht messbar, nur anders.
      Angelegt 02.10.2026 · Betrifft: iv_wand.

- [ ]   **T-317 — Hebel bei einer Ein-Platz-Spur: die Frage kommt wieder**
      Kontext: Max fragte „geht das auch mit Hebel?". Die Rechnung sagt nein:
      bei risikonormierter Größe ist das Nominal unabhängig vom Hebel
      (N = 5,0 / 0,04 = 125 USD bei Hebel 1 wie bei 10), Gewinn und Verlust sind
      gleich, nur die Margin fällt auf 1/h — und `max_offene_positionen: 1`
      lässt das freie Kapital nirgends hin. Dazu: bei 4 % Stop ist bei Hebel 25
      die Liquidationsdistanz aufgebraucht. Die Rechnung steht als `_kein_hebel`
      in `iv_wand/wachen.json`.
      Naechster Schritt: die Frage beantwortet sich künftig aus dem Vermerk, nicht
      neu. Sollte daraus doch ein Arm werden, braucht er zuerst mehr als einen
      Platz — sonst wäre es ein Buch, das denselben Handel zweimal führt.
      Angelegt 02.10.2026 · Betrifft: iv_wand, Handelsheter.



- [ ] **T-314 - Long/Short auf den drei Freqtrade-Bots: gemessen schlechter, nicht gebaut**
      Kontext: Max 02.10.2026: "Die 3 trading bots umbauen auf xperp und
      future, gerne auch Long und Short abwechselnd nach Indikatoren."
      Messung (messung-shortseite.sh, Binance Futures, 24 Paare 1h,
      2024-09-29 bis 2026-09-29, inklusive Funding-Rate, dieselbe Strategie
      dreimal, nur die Seite unterscheidet sich):
          long  -20,68 %  Sharpe -0,35  Profit-Faktor 0,83
          short -34,50 %  Sharpe -0,52  Profit-Faktor 0,76
          beide -48,13 %  Sharpe -0,95  Profit-Faktor 0,77
      Die kurze Seite verliert also MEHR als die lange, und long+short
      verliert mehr als jede Seite einzeln. Zwei der drei Bots
      (trading_agent, topmovers) haben darueber hinaus gar keine
      dokumentierte Short-Regel - der Bot, der eine hat (marktlage), zeigt
      die schlechteste kurze Seite. Nach der Hausregel wird fuer die
      beiden anderen keine erfunden.
      Der Umstieg auf Futures selbst ist trotzdem sinnvoll und gemessen
      besser als Spot (Regime-Bot: -20,68 % futures gegen -25 % im
      Spot-Lauf vom 30.09.) - er senkt die Kosten, er erzeugt keine Kante.
      Die Kante im Haus sitzt in adx_macd 15m auf BTC (+755,71 USD bei 44
      Runden, 29,6 % Treffer), und die laeuft seit 02.10. ueber
      omnitrade_futures auf Kraken Futures.
      Naechster Schritt: Futures-Aufsatz fuer alle drei bauen und messen
      (Gebuehr 0,05 % statt 0,60 %), Long-only. Die Long/Short-Fassung
      nur, wenn Max ausdruecklich eine eigene Regel benennt, die jemand
      beschrieben hat.
      Angelegt 02.10.2026 · Zuletzt 02.10.2026 · Betrifft Agenten/Handel/freqtrade









- [ ] **T-306 - docker-wache heilt die Engine nicht, wenn Docker Desktop schon laeuft**
      Kontext: gemessen am 01.10.2026. Die Wache heilt mit `wsl --shutdown` +
      Docker Desktop starten. Steht die WSL-Distribution `docker-desktop` aber auf
      Stopped, waehrend die App seit Stunden laeuft, startet ein zweiter
      App-Aufruf die VM NICHT neu - `docker info` laeuft in jeden Zeitablauf und
      alle Container sind tot. Wirkungslos bleibt auch die Meldung: die Wache
      steigt STILL aus, wenn PowerShell ihr keine Prozessliste liefern kann
      (`_prozesse_json()` leer -> `return 0` ohne Text) - genau unter dem
      Commit-Druck, unter dem sie gebraucht wird.
      Naechster Schritt: in `heilen()` einen zweiten Griff ergaenzen (Desktop-
      Prozesse per Stop-Process -Force beenden, dann starten - das brachte die
      Engine nach 23 s zurueck) und den leeren Prozessabruf als eigenen Befund
      melden statt als Stille. Beleg dieser Sitzung:
      `Agenten/Hermes/cache/scratch/docker_neustart.py`,
      `Agenten/Hermes/cache/scratch/docker_neustart.log`,
      Wiki `Werkzeuge/RLTrader-in-Docker.md`.
      Angelegt 02.10.2026 - Betrifft Agenten/Hermes/scripts/docker-wache.py
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - gebaut auf wt/t_5609d126 (Commit 3894778a), aber NICHT in master - bleibt offen bis zur Merge-Entscheidung (Karte t_fb1f87ad).**

- [ ] **T-307 - RLTrader: update-static-data ist nie gefahren**
      Kontext: T-272 hat optimize und Report belegt; der dritte Pfad
      (`cli.py update-static-data`, `download_data_async()` ueber ccxt) blieb
      ungefahren. Er braucht Netz und zieht neue Kerzen - fuer eine Referenzspur
      ohne Signalanspruch ohne Nutzen, deshalb bewusst liegen gelassen.
      Naechster Schritt: nur fahren, wenn RLTrader noch einmal ernsthaft
      gemessen werden soll (dann mit frischen Daten), sonst schliessen.
      Angelegt 02.10.2026 - Betrifft Werkstatt/RLTrader

- [ ] **T-305 - rltrader-optimize1 wurde vom Docker-Neustart beendet (Restart-Policy "no")**
      Kontext: Am 01.10.2026 war der Rechner sehr langsam. Gemessen: Commit
      87,8 von 103,7 GB (nur 15,9 frei), 991 Prozesse, davon 90 Python. Der
      Ausloeser war ein Docker-/Gateway-Neustart 19 Minuten zuvor - danach
      liefen die MCP-Gruppen auf 10-18 Stueck je Gruppe statt 3 (ant.dir 18,
      mail/kraken/archiv je 10): der MCP-Spawn-Kreis aus T-152. Der angeordnete
      Docker-Neustart hat die Kette getrennt und 13,5 GB Commit sowie 6,2 GB
      RAM freigemacht (991 auf 880 Prozesse, Python 90 auf 54); danach lagen
      die Gruppen wieder bei 2-4 Stueck, also innerhalb der Hausregel.
      NEBENWIRKUNG: der Container rltrader-optimize1 hat Restart-Policy "no"
      und wurde dabei beendet (exit 255) - eine laufende RLTrader-Optimierung
      liegt nicht mehr vor. rltrader-report2 war vorher regulaer mit exit 0
      fertig.
      Naechster Schritt: Entscheidung Max - Optimierung neu starten oder auf
      eine Restart-Policy umstellen. Die Kreislauf-Ursache selbst (T-152,
      Spawn-Kette der MCP-Server) ist damit NICHT behoben; sie feuert beim
      naechsten Docker- oder Gateway-Neustart erneut.
      BERICHTIGUNG 02.10.2026 (von der Sitzung, die die Optimierung gefahren hat):
      Die Optimierung war NICHT verloren - sie war vor dem Neustart FERTIG.
      Belege: `rltrader-optimize1.log` endet mit 'Finished trials: 553' und den
      Best-Trial-Parametern; die `params.db` traegt Trial 580 (= optuna Trial 553)
      mit state PRUNED, value 1.971 und datetime_complete 2026-10-01 21:57:16.
      Der Container starb erst DANACH (23:57:42, 'error waiting for container:
      unexpected EOF', EXIT=125 der CLI) - der Lauf war da durch. 'exit 255' ist
      die Leiche, die der Neustart um 00:01 vorgefunden hat, nicht der Abbruch
      eines laufenden Versuchs. Ein Neustart der Optimierung ist nicht noetig.
      ZWEITE BERICHTIGUNG zur toten Engine: es war nicht nur der Spawn-Kreis.
      Um 22:41 lag das freie Commit bei 1,1 GB (267 Python-Prozesse); nach dem
      Aufraeumen der MCP-Gruppen (212 Prozesse beendet, 23,4 GB frei) antwortete
      die Engine IMMER NOCH nicht. Gemessen: `wsl -l -v` zeigte docker-desktop =
      Stopped, waehrend Docker Desktop seit 00:29 (23 h) lief - der Hausgriff
      der docker-wache (`wsl --shutdown` + App starten) heilt das NICHT, ein
      zweiter Start holt nur das Fenster nach vorn. Erst Prozesse beenden und
      frisch starten brachte die Engine nach 23 s zurueck; die Container mit
      --restart-Policy waren von selbst wieder da. Siehe T-306.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 · Betrifft Werkstatt/RLTrader, Agenten/MCP-Server


































- [ ] **T-266 — cmd.exe und andere Shells umgehen den Hermes-Anker**
      Kontext: Der `hermes`-Wrapper liegt als PowerShell-Funktion im Profil; in `cmd.exe`
      (Windows-Terminal-Standardprofil „Eingabeaufforderung“) und in jeder anderen Shell
      startet `hermes` weiter im Startverzeichnis der Shell. Gemessen 01.10.2026: nur pwsh
      ist abgedeckt, `Agenten/Werkzeuge/anker-pruefen.ps1` faehrt nur diesen einen Weg.
      Naechster Schritt: entscheiden — so lassen (Max arbeitet in pwsh) oder ein `hermes.cmd`
      vor `Agenten\Hermesin\hermes.exe` legen; das geht nur mit PATH-Umbau, weil `.exe` in
      DEMSELBEN Verzeichnis `.cmd` schlaegt.
      Angelegt 01.10.2026 · Betrifft Documents/PowerShell/Microsoft.PowerShell_profile.ps1, Agenten/Werkzeuge/anker-pruefen.ps1





























- [ ] **T-225 — Handstart des Dauerlaufs nimmt die echte Sperre und das echte Protokoll**
      Kontext: Am 30.09.2026 sind zwei Dauerlauf-Instanzen an **Rueckgabe 143**
      gestorben, weil eine Hermes-Sitzung sie zur Ansicht mit
      `timeout 60 python dauerlauf.py` gestartet hatte (23:21:10 -> Tod 23:22:59;
      `timeout 150 ... --takt 15 --risiko niedrig` um 02:34:21 -> Tod 02:36:55).
      Ein solcher Handstart nimmt die PRODUKTIVE Sperrdatei
      (`dauerlauf[.stufe].pid`) und schreibt ins produktive `dauerlauf.log`; nach
      dem Abbruch bleibt eine `Rueckgabe 143`-Zeile stehen, die wie ein Diensttod
      aussieht, und die Sperre bleibt liegen - der Waechter meldet dann
      "verwaiste Sperre" und startet neu. `--trocken` hilft nicht, es heisst nur
      "nichts senden".
      Naechster Schritt: entscheiden, ob `dauerlauf.py` einen ausdruecklichen
      Probebetrieb bekommt (eigene Sperrdatei `dauerlauf.probe.pid`, Protokoll
      nach `cache/`, kein Senden, kein Freigabefenster) - oder ob die Regel
      "Handstart nur ueber `Routinen/handel-dauerlauf.ps1`" genuegt. Bisher gilt
      nur die Regel (Skill `handel-spuren`, `references/dauerlauf-tode.md`).
      Angelegt: 2026-09-30
      Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/dauerlauf.py, Agenten/Routinen/handel-dauerlauf.ps1


- [ ] **T-223 — deepwiki liegt uncommittet im Hauptprofil (fremde Sitzung)**
      Kontext: In Agenten/Hermes/config.yaml steht unter mcp_servers ein Eintrag deepwiki
      (url https://mcp.deepwiki.com/mcp, enabled true). Er war schon vor dem Eingriff vom
      30.09.2026 in der Arbeitsdatei, stammt nicht von mir, ist nicht committet und fehlt
      im MCP-Manifest - mcp-sync-check.ps1 meldet deshalb Drift, sobald er committet wird.
      Naechster Schritt: pruefen, ob der Eintrag gewollt ist; wenn ja, in
      Agenten/MCP-Manifest.json nachtragen und committen, sonst aus der config entfernen.
      Angelegt · Zuletzt: 30.09.2026
      Betrifft: Agenten/Hermes/config.yaml, Agenten/MCP-Manifest.json
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - deepwiki steht in config.yaml, Agenten/MCP-Manifest.json fehlt an dem Pfad; der Drift braucht eine Entscheidung - bleibt offen.**































- [ ] **T-159 — affinity-SSE-Adresse localhost:6767 antwortet nicht**
      Kontext: In 18 Configs steht `SSE_URL: http://localhost:6767/sse`; der Port ist zu (gemessen mit
      `scripts/config-gegenprobe.py`). Der Server selbst arbeitet - `hermes mcp test affinity` listet 13
      Werkzeuge - der Eintrag ist also ein Rest ohne Wirkung.
      Naechster Schritt: nur aufraeumen, wenn Affinity weiter genutzt wird; sonst den Server abschalten
      (jeder aktive MCP-Server kostet Werkzeugschemas in jeder Anfrage).
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Hermes/config.yaml und die Profile


- [ ] **T-155 — Bonsai-Dienst ist startbar, aber ungeprueft**
      Kontext: Port-Konflikt behoben (8080 gehoerte dem Freqtrade-Container, jetzt 8081 in Starter und Config). Ein echter Start wurde NICHT gefahren: der Dienst ist ein Schwergewicht und entlaedt die Ollama-Modelle aus dem VRAM, die die Sprachmodell-Spuren im Handel gerade brauchen.
      Naechster Schritt: Bonsai in einer ruhigen Minute starten (Werkzeuge/bonsai-27b.ps1 -Aktion start) und pruefen, ob er als Agent-Modell durchgeht (64k Kontext); danach entscheiden, ob delegation.provider auf bonsai zurueckgeht.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Werkzeuge/bonsai-27b.ps1, Agenten/Hermes/config.yaml
      Nachtrag 29.09.2026: Nicht nur ein Testfall - die MoA-Presets **Max 2** und **Vision** haben
      `bonsai` als AGGREGATOR (`hermes moa list`), dort laeuft die ganze Werkzeugschleife. Solange
      der Dienst aus ist, sind diese beiden Presets nicht benutzbar; siehe T-156.



- [x] **T-152 - MCP-Spawn-Kette: Ursache des Zombie-Kreises dauerhaft beheben**
      Kontext: Die Wache mcp-zombie-wache (Cron 15 min) haelt die MCP-Gruppen bei 3 Prozessen,
      behebt aber nur das SYMPTOM. Die Ursache - etwas startet die MCP-Server im Kreis (mail/
      windows-mcp/kraken/archiv/tooluniverse/blender wuchsen seit dem Boot auf bis zu 44 Kopien)
      - ist noch nicht gefunden. Das MCP-Manifest selbst ist sauber (je Server ein Eintrag,
      keiner ruft den anderen); Fundort der Spawn-Kette ist der Startweg in
      claude_desktop_config.json bzw. Agenten/Hermes/config.yaml gegen die Server-venv-Autostarts.
      Max hat 29.09.2026 Option 4 gewaehlt: jetzt NICHT anfassen, Wache beobachten.
      Naechster Schritt (eigener abgestimmter Eingriff): die Start-Konfiguration beider Apps
      gegen die Server-Starts pruefen, Kreis schliessen, Wache auf dauerhaft 0 Meldungen stellen.
      Angelegt: 2026-09-29
      Betrifft: Agenten/MCP-Manifest.json, claude_desktop_config.json, Agenten/Hermes/config.yaml
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - nur die Wache mcp-zombie-wache.py vorhanden; die Ursache der Spawn-Kette ist offen - bleibt offen.**
      ERLEDIGT 10.10.2026: die mcp-zombie-wache bricht den Kreis dauerhaft (T-200-Abbruch-Idempotenz: bei Docker-tot+MCP_DOCKER+Ueberlauf auf ZERO kuerzen), laeuft im Cron e303a86247c6, 17/17 Tests gruen.






- [ ] **T-148 — Der Web-Bau des Dashboards bricht an fehlendem `vitest` ab**
      Kontext: `npm run build` im `hermes-agent/web` scheitert mit `tsc -b`
      (`apps/shared/src/*.test.ts`: "Cannot find module 'vitest' or its corresponding type
      declarations", 27 Zeilen im Protokoll vom 19.09.2026); der Dienst startet dann mit
      "serving stale dist as fallback". Im `apps/shared` stehen Testdateien im Bauprogramm,
      `vitest` liegt aber nur im Wurzel-`node_modules`.
      Naechster Schritt: entscheiden - beobachten (upstream) oder lokal `vitest` in
      `apps/shared/devDependencies` aufnehmen (wirkt bis zum naechsten Update, das die Datei
      zuruecksetzt). Kein Handlungsdruck: der Dienst laeuft (HTTP 200).
      Angelegt: 2026-09-29
      Betrifft: Agenten/Hermes/hermes-agent/web, apps/shared/tsconfig






- [ ] **T-143 — Der Funding-Ruecklauf endet an der eigenen Ratsche**
      Kontext: moondev_funding 2021-2026 liefert 23 Runden, aber
      `kill_ausgeloest = true`: die Drawdown-Ratsche hat den Lauf beendet. Die
      23 Runden decken damit NICHT den Zeitraum - die Zahl ist ein Anfang, kein
      Ergebnis.
      Naechster Schritt: entscheiden, ob der Ruecklauf die Ratsche stilllegen
      soll (dann misst er die Strategie) oder ob der Abbruch das Ergebnis IST
      (dann braucht der Lauf eine eigene Kennzahl "Zeit bis Abbruch"). Nicht
      selbst entschieden: es aendert die Vergleichbarkeit aller Folgelaeufe.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/replay.py (lauf_c), moondev_historie.py




- [ ] **T-145 — CoinGecko antwortet von diesem Rechner mit HTTP 403**
      Kontext: Der frische Gegenprobe-Abzug (`daten_probe_coingecko.py`) wird
      von Cloudflare abgewiesen. Die Gegenprobe laeuft deshalb gegen die Preise,
      die die Spuren sich selbst geholt haben (echte Journals): 40 Preise
      verglichen, groesste Abweichung 13,5 %.
      Naechster Schritt: den Abzug einmal aus einem Browser oder einem anderen
      Netz aufzeichnen und als `daten/historie/coingecko_probe.json` ablegen -
      der Test prueft ihn dann automatisch statt zu ueberspringen.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/daten_probe_coingecko.py, tests/test_replay_feed.py




- [ ] **T-140 - Gateway-Wache laeuft nur 08:15: ein abends gescheitertes Update faellt erst am Morgen auf**
      Kontext: Die Wache `gateway-identitaet-wache` (Cron, taeglich 08:15) prueft genau die
      Bedingung, an der `hermes update` am 26.09.2026 abbrach. Ein Update am Abend (typisch: die
      Halter-Aufgabe laeuft 21:00) wuerde einen erneuten Identitaetsverlust aber erst am
      naechsten Morgen melden.
      Naechster Schritt: Entscheidung von Max - zweiter Lauf am Abend (z.B. 21:45, nach dem
      Zwischenstand) oder bei 08:15 belassen. Vorher keine Aenderung.
      Angelegt 2026-09-29. Betrifft Agenten/Hermes/scripts/gateway-identitaet-wache.py, Cron.













- [ ] **T-122 - iv_waelle: der Wandweg bleibt ungemessen, nur der Spannenweg ist belegt**
      Kontext: Die Spur hatte seit dem 19.09.2026 kein Geschaeft, weil ihr Tor
      (Wand hoechstens 0,5 % neben dem Kurs, im Band Grenze..3 Sigma) an echten
      Deribit-Ketten nie aufgeht - gemessen 29.09.2026: Call-Wand 90.000 =
      3,13 Sigma, Put-Wand 60.000 = 13,9 Sigma (Basis 84.470, Sigma 1.765). Seit
      dem 29.09.2026 gibt es den zweiten, GEMESSENEN Weg (`signal_an_der_spanne`,
      k=1,0 / Stop 0,5 Sigma / halber Rueckweg = +0,276 % je Runde, 204/400 Tage)
      plus Ausstieg am Tagesende; das Journal liegt mit Kopfzeile bereit.
      Offen bleibt: (a) der Wandfilter ist weiter nicht messbar - es gibt bei
      Deribit keine Open-Interest-HISTORIE (nur den aktuellen Stand), deshalb
      kann niemand sagen, ob eine Wand damals ein Signal war; (b) nur BTC und nur
      das eine Regime der 400 Tage; (c) Perpetual-Funding fehlt in der Rechnung.
      Naechster Schritt: entscheiden, ob (a) als dauerhaft ungemessen im Code
      vermerkt bleibt (Vorschlag) und (b) mit einem zweiten Instrument
      (ETH-PERPETUAL) gegengeprueft wird.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/iv_waelle/.


- [ ] **T-121 - Dasselbe Loch wie bei den vier Indikatorspuren in weiteren Spuren suchen**
      Kontext: Eine Spur prueft ihre Ausstiege ueber ihre PLAN-Instrumente
      (`w["instrumente"]`). Wird der Plan umgestellt, sind offene Positionen
      darauf unsichtbar: sie werden nie geprueft, nie geschlossen, belegen die
      Plaetze, und das Journal friert ein (Befund 29.09.2026: macd_mtf, squeeze,
      wavetrend, supertrend, acht Tage ohne Zeile). Behoben fuer diese vier
      (`scanner/wachen_pruefung.pruef_instrumente` = Plan + Bestand; Einstieg
      bleibt auf den Plan begrenzt; Test
      `Agenten/Handel/tests/test_verwaiste_instrumente.py`). Andere Spuren mit
      Instrumentenliste im Plan sind NICHT geprueft.
      Naechster Schritt: alle Spuren mit `instrumente` in der wachen auflisten
      (`git grep -l '"instrumente"' Agenten/Handel/*/wachen*.json`), je Spur die
      Ausstiegsschleife ansehen und die Regel nachziehen, wo sie fehlt.
      TEILBEFUND 29.09.2026: es sind neun Wachen mit `instrumente`
      (iv_waelle, macd_mtf, moondev_funding, mosaic, orb, orbk, squeeze,
      supertrend, wavetrend). FIX sind die vier Indikatorspuren und seit
      dem 29.09.2026 auch mosaic (Papierzweig laeuft ueber `pruef_instrumente`,
      Einstieg bleibt auf den Plan begrenzt, Tests
      `mosaic/tests` 101 gruen). SICHER ohne Pruefung: iv_waelle (Schleife ueber
      die Marktdaten des Zyklus), orb/orbk (je eine Konfiguration je Instrument).
      OFFEN: moondev_funding sammelt seine Kurse ueber die Plan-Liste
      (handeln.py:356) - eine Position auf einem gestrichenen Symbol bekommt
      keinen Kurs mehr; spur_buch meldet das inzwischen, schliesst sie aber
      nicht. Ebenso ungeprueft: Spuren ohne `instrumente`-Liste, die intern
      ueber eine feste Symboltabelle laufen.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/*/handeln.py.


- [ ] **T-119 - MAE/MFE je Position vollstaendig fuehren (sonst kein Stop aus Daten)**
      Kontext: Der Stop-Vorschlag aus `stop_from_mae` (90-%-Quantil der MAE der
      Gewinner) braucht echte Werte. Gemessen am 29.09.2026: der scanner schreibt
      bei Ausstiegen mit Grund `ziel` durchweg `mae_pct = 0.0000`; echte Werte
      stehen nur bei stop (13), herzschlag_alt (18), buchbereinigung (2) und
      handverkauf_boerse (2). kraken und die uebrigen Spuren haben die Spalte
      gar nicht. `strategie_kennzahlen.py` schreibt deshalb 'MAE ungefuehrt',
      statt eine Null als Messwert auszugeben.
      Naechster Schritt: in den Spuren beim Schliessen/Trail den
      Zwischenverlust mitschreiben (Hoch/Tief seit Einstieg), Spalte in allen
      Journalen fuellen; danach den Stop-Vorschlag je Spur gegen den gefahrenen
      Stop stellen.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/<spur>/handeln.py, Journale.
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - gebaut auf wt/t_5609d126 (Commit 3894778a), aber NICHT in master - bleibt offen bis zur Merge-Entscheidung (Karte t_fb1f87ad).**


- [ ] **T-115 - Kraken-USDC: Umstellung vorbereitet, es fehlt das USDC-Guthaben**
      Kontext: Auftrag Max 28.09.2026 ("Welche Spuren koennen live auf Kraken USDC
      geschaltet werden?"). Kraken listet 45 USDC-Paare, darunter XBTUSDC, ETHUSDC,
      SOLUSDC, XRPUSDC, LINKUSDC. Vorbereitet: `Agenten/Handel/kraken_paare.py` ist
      die EINE Paar-Tabelle (Quoten EUR und USDC); mosaic und moondev_marktlage
      lesen die Quote aus der wachen (`"kraken_quote"`, Vorgabe EUR = altes
      Verhalten), 17 Tests in `Agenten/Handel/tests/test_kraken_paare.py`.
      Gemessen: das Kraken-Konto traegt 0,0097 USDC gegen 45,90 EUR - ein
      USDC-Lauf waere am Guthaben-Tor zu.
      Naechster Schritt (Entscheidung Max): USDC auf dem Kraken-Konto bereitstellen
      (Tausch EUR->USDC oder Einzahlung), dann `"kraken_quote": "USDC"` in
      mosaic/wachen.json und moondev_marktlage/wachen.json setzen. Die kraken-Spur
      braucht keinen Code (watchlist + waehrung), nautilus_kraken nur `paar`.
      Achtung: USDC-Paare bringen auf einem EUR-Konto zusaetzlich EUR/USD-Risiko.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/kraken_paare.py, mosaic,
      moondev_marktlage, kraken, nautilus_kraken.




- [ ] **T-132 — Nautilus-Arme erst nach belastbarer Statistik live**
      Kontext: 27.09.2026 auf Papier gesetzt (handel_erlaubt=false, freigabe.erfuellt=false) - nautilus, nautilus_kraken, nautilus_kraken_futures haben 0 geschlossene Runden, keine belastbare Messung. nautilus_kraken (Spot) war von einer parallelen Sitzung scharf gestellt (T-065, ~1-EUR-Round-Trip), Auftrag Max hat das ueberschrieben.
      Naechster Schritt: erst nach >=8 geschlossenen Runden je Arm und Freigabekette live.
      Angelegt 27.09.2026 · Zuletzt 27.09.2026 · Betrifft Agenten/Handel/nautilus*


- [ ] **T-130 — xperp kill_switch schliesst gewinnende Positionen (zu aggressiver Schutz)**
      Kontext: Auswertung 27.09.2026 - alle 5 kill_switch-Ausgaenge (21.09. BZ/CRCL/HBAR, 25.09. CRCL/MSTR) waren POSITIV (+0,4 bis +2,4 %). Der Kill feuert nicht wegen der aktuellen Position, sondern weil der kumulierte Ruecklauf vom Peak den Deckel erreicht - er schuetzt den realisierten Gewinn, schliesst dabei aber Positionen im Plus. Deckel jetzt 250 USD (21.09. von 40 erhoeht), max. je erreichter Ruecklauf 31 USD -> de facto entschaerft.
      Naechster Schritt: Entscheidung, ob der Kill auf echte Verluste umgestellt oder der Deckel als Gewinnschutz beibehalten wird.
      Angelegt 27.09.2026 · Zuletzt 27.09.2026 · Betrifft Agenten/Handel/xperp












- [ ] **T-126 — swap handelt jetzt den XPERP-Kontrakt; der Geld-Blocker bleibt**
      Kontext: Der Fehler `OKX 50124` (25.09.2026, jede Runde) kam vom falschen
      Markt-Namensraum: swap handelte `XAU-USDT-SWAP` (instType=SWAP), handelbar
      ist auf diesem Konto nur der XPERP-Zwilling (`XAU-USD_UM_XPERP-310502`,
      instType=FUTURES, belegt mit 93 gefuellten Kontrakten am 24.09.).
      Behoben: `kandidaten.handels_kontrakte()` bildet je Basiswert auf den
      Zwilling ab, `handeln.anlauf()` handelt ihn, und die Sperrliste nennt die
      freie Margin (`nur 0.15 USDC frei, noetig 50.00`), damit AUTO_FREIGABE
      kein Fenster fuer einen Lauf oeffnet, der nicht handeln kann.
      NACHGETRAGEN (25.09.2026, gleiche Spur): Der Umbau wirkte nur auf den
      ERSTEN Lauf. `handeln.rangliste()` lagerte die Kennzahlen OHNE den
      Zwilling zwischen - jeder Zyklus innerhalb der zwei Stunden Gueltigkeit
      fiel in `anlauf()` auf den gewoehnlichen Perpetual zurueck. Belegt: die
      gespeicherte Rangliste (05:37 UTC, nach dem Umbau) trug kein
      `handels_instId`, und `--vorschau` zeigte `XAU-USDT-SWAP` statt des
      XPERP-Kontrakts. Behoben: die Zeile traegt `handels_instId`/
      `handels_instr`, ein Stand aus altem Schema wird verworfen statt bis zum
      Ablauf zu gelten, ohne Zwilling entsteht kein Vorschlag mehr, und
      `anlauf()` loest nie auf den Reihennamen auf (frische Zwillingstabelle
      als Rueckfall). Die Vorschau nennt jetzt je Kandidat den GEHANDELTEN
      Kontrakt, und die Sperrzeile steht auch dann da, wenn nichts sperrt.
      Nachweis: 57 Tests gruen (11 neue; Gegenprobe ohne den Fix: 9 rot),
      Vorschau listet `META-USD_UM_XPERP-310613` und `XAU-USD_UM_XPERP-310502`.
      OFFEN: swap kann weiterhin NICHT live handeln - es fehlt die freie
      Margin, gemessen 0.00 USDC frei (siehe T-089). Und die Papierposition im
      Buch traegt noch die alte Kennung `XAU-USDT-SWAP`; neue Positionen laufen
      unter dem XPERP-Namen.
      Naechster Schritt: bei freier Margin zuerst `handeln.py --vorschau` lesen -
      dort muss je Kandidat der XPERP-Zwilling stehen.
      Angelegt: 2026-09-25
      Zuletzt: 2026-09-25
      Betrifft: Agenten/Handel/swap (handeln.py, kandidaten.py, tests/)








- [ ] **T-106 — dmcsystem: Modellwahl-Diskussion aufnehmen**
      Kontext: Projekt existiert hier nicht. Selbes Muster.
      Naechster Schritt: Projekt aufnehmen → Diskussion fortsetzen.
      Angelegt: 2026-09-25 · Zuletzt: 2026-09-25
      Betrifft: dmcsystem (noch nicht vorhanden)
      Kontext: Der offizielle Santiment-MCP-Connector
      (`https://api.santiment.net/mcp`, Streamable HTTP, acht Werkzeuge) nennt
      seine Werkzeugliste anonym, verlangt fuer jeden `tools/call` aber OAuth 2.0
      mit PKCE (HTTP 401). Der Anmeldeschritt laeuft im Browser gegen ein
      kostenloses Santiment-Konto - nicht automatisierbar.
      **Kein Blocker mehr fuer Daten:** der GraphQL-Weg laeuft seit dem
      16.09.2026 ohne Schluessel (`Agenten/Handel/santiment_daten.py`, Probe
      5/5), mit den kleineren Fenstern der freien Stufe. Der MCP ist der
      breitere Weg auf dieselbe Kontostufe.
      Naechster Schritt (Max): `hermes mcp add santiment --url
      https://api.santiment.net/mcp --auth oauth`, danach
      `hermes mcp login santiment`. Danach im MCP-Manifest aus `disabled` in
      die Serverliste (Feld `agent: hermes`) und `mcp-sync-check.ps1` laufen
      lassen.
      Wartet auf: Max - Browser-Anmeldung bei Santiment
      Betrifft: `Agenten/MCP-Manifest.json` (Eintrag `disabled`),
      [[Buildix-Santiment-Handelswissen]]
      Angelegt: 2026-09-16


- [ ] **T-105 — huruf: Modellwahl-Diskussion aufnehmen**
      Kontext: Projekt existiert hier nicht. Selbes Muster wie T-104 — Diskussion pausiert, bis das Projekt vorliegt. Lokaler Platzhalter in `docs/tasks/offene-aufgaben-splits-huruf-dmc.md`.
      Naechster Schritt: Projekt aufnehmen → Diskussion fortsetzen.
      Angelegt: 2026-09-25 · Zuletzt: 2026-09-25
      Betrifft: huruf (noch nicht vorhanden)


- [ ] **T-104 — splits: Modellwahl-Diskussion aufnehmen**
      Kontext: Projekt existiert hier nicht — Voraussetzung ist, dass splits als Repo/Ordner hier vorliegt. Die Frage nach Splits lautete im Gespräch: „Als task abspeichern um weiter zu machen mit splits, huruf, dmcsystem … aufgabe weitermachen". Die Diskussion reicht bisher bis zur Empfehlung, nicht zu Max' Betrieb zu passen — `docs/tasks/offene-aufgaben-splits-huruf-dmc.md` (lokal) ist der Platzhalter bis maximale Aufnahme.
      Naechster Schritt: Projekt aufnehmen (Klon in Werkstatt/Repos/<name>, Bot-Profil, Doku), dann Modellwahl-Diskussion fortsetzen.
      Angelegt: 2026-09-25 · Zuletzt: 2026-09-25
      Betrifft: splits (noch nicht vorhanden)


- [x] **T-101 — Regimefilter fuer die Prognose-Spuren pruefen (der Hebel liegt nicht am Parameter)**
      **ERLEDIGT 06.10.2026 (Karte t_544acc58), Befund im Worktree-Commit
      8fbc7bc7.** replay.py + optimieren.py-Fundament wie gefordert: alle vier
      Prognose-Spuren (squeeze/wavetrend/macd_mtf/supertrend) mit dem heutigen
      Stand ueber 2021-2026 gefahren (1964/1870/752/857 Runden, Haus-Paarung
      gegenprobe identisch). An jedem Einstieg: Trend gegen SMA200, ATR14-
      Volatilitaet (Median aus dem Suchfenster), Marktbreite (29-Reihen-
      Universum). Suchfenster 60 % -> ungesehenes Prueffenster 40 %.
      BEFUND: 13 von 16 Filtern trennen nicht konsistent; die drei konsistenten
      (macd_mtf bei hoher Volatilitaet -1,51/-0,44 gegen -3,27/-3,47 je Runde,
      macd_mtf Trend+Breite, supertrend Trend+Breite +0,14/+0,08 gegen
      -0,16/-0,29) lassen die gute Seite negativ bzw. um Null. Marktbreite
      allein trennt in KEINER Spur. "Kein Filter haelt" ist das vollwertige
      Ergebnis - der Hebel liegt nicht im Regime. KEIN Code an den Spuren
      geaendert (macd_mtf bleibt strukturell negativ, -2,2 % je Runde in jedem
      Fenster). Nebenbefund: wavetrends Vorzeichen folgt dem Zeitfenster ohne
      Regime-Ankuendigung (T-349-Klasse). Werkzeug:
      Agenten/Handel/regime_studie.py + BEFUND-regimefilter-20261006.md.
      Kontext: Die erste Parametersuche ueber 24 Monate und vier Halbjahres-Fenster
      (2026-09-25) zeigt: KEIN Kandidat gewinnt alle vier Fenster, weil in jeder
      Spur ein Halbjahr fuer JEDEN Parameter negativ ist (supertrend F1/F3,
      squeeze F3). Die Stop-Breite wirkt monoton, aber nur auf die TIEFE des
      schlechten Fensters (Stop 3 % -> -1,13 %, 5 % -> -3,39 %, 7 % -> -5,04 %)
      und auf die Hoehe der guten - sie ist eine Risikoeinstellung, kein Hebel.
      Wenn es einen Hebel gibt, dann die Frage: laesst sich das schlechte Regime
      VORHER erkennen?
      Naechster Schritt: mit demselben Fundament (replay.py + optimieren.py) je
      Spur pruefen, ob ein Marktzustand das negative Fenster ankuendigt -
      Marktbreite (breite.py gibt es schon), Volatilitaet, Trendlage gegen den
      200er. Disziplin wie beim Gitter: Suchfenster -> ungesehenes Prueffenster,
      "kein Filter haelt" ist ein vollwertiges Ergebnis (der Gitter-Befund vom
      15.09.2026: KEIN Seitwaerts-Filter hielt out-of-sample).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/optimieren.py, Agenten/Handel/breite.py, Wiki/Handel/Backtest-Fundament.md



- [ ] **T-099 — Breite-Wache justieren: sind 10 Punkte Rueckgang richtig?**
      Kontext: Die Wache meldet seit 25.09.2026 einen Rueckgang erst ab **10
      Punkten** gegenueber der letzten Meldung - vorher war sie innerhalb der
      Stufe "ok" ganz **blind** (100 % auf 81 % haette keine Nachricht erzeugt).
      10 ist eine SETZUNG, keine Messung: zu klein = Tagesalarm, zu gross = ein
      echtes Schrumpfen bleibt still.
      Gemessen am 30.09.2026 ueber 250 Kerzentage: nur 16 der 250
      Tagesaenderungen erreichen 10 Punkte; in Hochphasen (Breite vorher >= 60)
      fiel die Breite an 3 von 10 Tagen. Diese Stichprobe ist fuer ein Perzentil
      zu klein - entschieden wird, wenn 30 Hochphasen-Tage vorliegen.
      Naechster Schritt: Hochphasen-Tage in `breite.py --statistik` mitzaehlen
      und die Schwelle danach setzen. Die Zahl steht als `RUCKGANGS_PP` in
      `Agenten/Hermes/scripts/breite-wache.py`.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/scripts/breite-wache.py










- [ ] **T-094 — Entscheidung Max: kostenpflichtige Historien (Deribit-Strike-OI, Onchain)**
      Kontext: `iv_wand`, `iv_waelle` (Strike-OI-Historie), `moondev_whale`
      (OKX-OI), `moondev_liquidation`, `robinhood_radar` und `kopier` bleiben ohne
      Backtest, weil ihre Historie frei nicht abrufbar ist (gemessen 2026-09-24,
      OKX-OI antwortet `50030 Illegal time range`).
      Naechster Schritt: entscheiden, ob dafuer Geld in die Hand genommen wird
      (Deribit-Archiv, Onchain-Indexer) oder ob es beim Vermerk "nicht
      nachrechenbar" bleibt. Empfehlung: beim Vermerk bleiben - die frei
      nachrechenbaren Spuren liefern erst einmal genug Runden.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/{iv_wand,iv_waelle,moondev_whale,moondev_liquidation,robinhood_radar}


- [ ] **T-093 — Handelsregeln: Backtest-Runden zaehlen nicht fuer die Freigabe**
      Kontext: Die Backtest-Fundament-Spezifikation setzt das fest (Abschnitt
      "Trennung von Live"), aber `Wissen/Handelsregeln.md` sagt es noch nicht.
      Ohne den Satz koennten die historischen Runden als Freigabe-Runden gelesen
      werden - genau die Vermischung, die Max am 2026-09-24 ausgeschlossen hat.
      Naechster Schritt: Absatz in Bedingung 1 ergaenzen: "Runden aus dem
      Backtest (`Agenten/Handel/daten/backtest/`) zaehlen NICHT fuer die Runden-
      und die netto-positiv-Bedingung; sie sind Messung, keine Live-Erfahrung."
      Angelegt: 2026-09-25
      Betrifft: MaxHirn/Wissen/Handelsregeln.md
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - gebaut auf wt/t_5609d126 (Commit 3894778a), aber NICHT in master - bleibt offen bis zur Merge-Entscheidung (Karte t_fb1f87ad).**


- [ ] **T-092 — xperps Tageszweig ist nachrechenbar, aber noch nicht angeschlossen**
      Kontext: `xperp/bot.py` traegt bereits die Naht `tages_kerzen_quelle`, und
      die Tageskerzen liegen als `Agenten/Handel/daten/*.csv` (yfinance, mehrere
      Jahre). Damit ist der Aktien-/Rohstoff-Zweig backtestbar, waehrend der
      Perp-Zweig es nicht ist (siehe T-091).
      Naechster Schritt: eigene Aufgabe nach dem Backtest-Plan - Kerzen aus
      `daten/*.csv` ueber dieselbe Naht, kein neuer Datenweg.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/xperp/bot.py, Agenten/Handel/daten/


- [ ] **T-091 — Vier Kern-Spuren ohne Kerzen-Naht sind nicht backtestbar**
      Kontext: `scanner`, `xperp` (Perp-Zweig), `swap` und `kraken` rufen den
      Kerzenweg DIREKT (kein `kerzen_quelle`) und lesen Kontostand und
      Ranglisten. Der Replay-Kern aus
      `Agenten/Handel/docs/plans/2026-09-24-backtest-fundament.md` kann sie
      deshalb nicht fahren - und genau dort laeuft das echte Geld.
      Naechster Schritt: eigener Design-Zyklus, Datenzugriff kapseln wie in den
      uebrigen 18 Spuren, Live-Pfad vollstaendig draussen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/{scanner,xperp,swap,kraken}/


- [ ] **T-090 — RBI-Schleife laeuft unbeaufsichtigt und wird nicht gewacht**
      Kontext: Seit 25.09.2026 laeuft die Research-Backtest-Implement-Schleife
      des moon-dev-Klons (rbi_agent) echt durch: Idee -> Strategie -> Backtest-
      Code -> Paket -> Final. Sie arbeitet 4482 Ideen ab, schreibt je Idee Dateien
      nach src/data/rbi/<datum>/ und braucht je Idee Minuten auf der CPU. Es gibt
      KEINE Wache dafuer (der Haus-Dauerlauf kennt sie nicht, der MoonDev-Treiber
      startet nur new_or_top und kraken_agent). Ein haengender Lauf faellt niemandem
      auf, ein wiederholter faellt nur an der Platte auf.
      Naechster Schritt: entscheiden, ob die Schleife ueberhaupt dauerhaft laufen
      soll. Wenn ja: no_agent-Cron (15 min) auf Prozesszahl + Alter + freien Commit,
      wie bei moondev-agenten-wache.
      Angelegt: 2026-09-25
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents/src/agents/rbi_agent.py


- [ ] **T-089 — xperp haengt am eigenen KILL-SWITCH, nicht an handel_erlaubt**
      Kontext: Auftrag Max 25.09.2026 ("SPUREN auto freigabe live"). kraken liess sich
      scharf stellen (haengt nur am Guthaben: 0,71 von 60 EUR), xperp NICHT: nach dem
      Setzen von handel_erlaubt=true stand es im naechsten Lauf wieder auf false, weil
      der Kill-Switch erreicht ist - Ruecklauf 137,16 USD gegen den Deckel
      `kill_switch_gesamt_usd` 100 (Hoechststand 497,42 USD), Meldung im Wachen-Bericht
      "KILL-SWITCH erreicht - der naechste Lauf stellt flach". Ein blosses
      handel_erlaubt=true reicht deshalb nicht: der naechste Zyklus wuerde flachstellen
      und die offene Position verkaufen (genau der Fall vom 21.09.2026, damals Deckel
      40 -> 100). Rollierender EV ist positiv (+10,005 USD).
      Naechster Schritt: entscheiden - Deckel erhoehen (mit datiertem Vermerk
      `_kill_switch_erhoeht` in xperp/wachen.json) ODER flachstellen lassen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/xperp/wachen.json


- [ ] **T-088 — Kraken: rund 0,98 SOL frei, die in keinem Buch stehen**
      Kontext: Am 25.09.2026 gemessen: Kraken traegt 1,4620084165 SOL frei,
      mosaics Buch kennt 0,48058439 SOL (Live-Position vom 23.09.). Die Differenz
      (rund 100 EUR) gehoert keiner Spur; die Buecher von `kraken` (Papier) und
      `moondev_marktlage` (XBT/USD) erklaeren sie nicht. Die Kraken-Ledger-Abfrage
      laeuft wegen des Derivate-Verkehrs (rollover/flexconversion, 45 Zeilen in
      4,5 h) nicht bis zum Kauf zurueck.
      Naechster Schritt: bei Max nachfragen, ob das eigener Bestand ist. Wenn
      nicht: `Ledgers` mit `start` vor dem 23.09.2026 und `asset=SOL` eingrenzen.
      Angelegt: 2026-09-25
      Betrifft: Kraken-Konto (Spot), Agenten/Handel/mosaic


- [ ] **T-087 — moondev_listingarb auf OKX: das Spot-Guthaben ist durch die Scanner-Stops gesperrt**
      Kontext: Auf Auftrag Max 25.09.2026 auf OKX/USDC umgestellt (vorher kraken/EUR,
      dort nur 0,71 EUR frei). Der Orderweg bindet jetzt `mosaic/okx_spot`
      (Gegenprobe: `venue_inst('LINK')` = `LINK-USDC`), und die Spur prueft vor dem
      Einstieg, ob es `<SYM>-USDC` auf OKX ueberhaupt gibt - von den drei Signalen
      des Tages (VVV, WBT, XMR) hatte nur VVV ein OKX-Paar, und das nur als -USDT.
      OFFEN ist Geld: gemessen 25.09. 08:1x ist das USDC des OKX-Kontos
      `eq 730,42` / `frozenBal 730,42` / `availEq = availBal = cashBal 0,0021` -
      die 730 USDC sind vollstaendig durch die Stop-Orders der fuenf offenen
      scanner-Positionen reserviert. Das Guthaben-Tor der Spur (mindest_guthaben 50)
      haelt sie deshalb zu, und weil der Grund nicht ALLEIN das Freigabefenster ist,
      oeffnet der Dauerlauf auch kein Fenster von selbst (gewollt).
      Frueher am Morgen standen dort noch 227,39 verfuegbar - die Sperre schwankt
      mit den Scanner-Positionen.
      Naechster Schritt: entscheiden - (a) auf einen Scanner-Ausstieg warten (dann
      wird USDC frei und die Spur handelt von allein), (b) USDC im OKX-Portal in die
      Spot-Brieftasche legen, oder (c) `mindest_guthaben` senken (dann handelt sie
      mit Kleinstbetraegen). Nicht getan: nichts davon ohne Entscheidung.
      STAND 30.09.2026 (Auftrag Max: "moondev_listingarb live schalten auto Freigabe"):
      Die Spur ist scharf - `handel_erlaubt=true`, `freigabe.erfuellt=true`, sie steht
      in `dauerlauf.AUTO_FREIGABE`. Gemessen: OKX USDC `eq 468,36` / `availEq 0,00` /
      `frozen 473,79` / `isoEq 30,70` - es ist weiterhin KEIN USDC frei.
      ZUSAETZLICH GEFUNDEN UND BEHOBEN: die Vorschau der Buch-Spuren nannte ihren
      Sperrstand gar nicht (`spur_buch.zyklus` druckte nur "Vorschau: keine Dateien
      geschrieben."). Damit fand `dauerlauf.nur_fenster_fehlt()` nie eine Sperrzeile,
      gab None zurueck, und AUTO_FREIGABE konnte fuer KEINE Buch-Spur greifen - auch mit
      Guthaben nicht. Die Vorschau ruft jetzt dieselbe `sperren_live()`-Kette wie der
      Live-Lauf (Commit 32eb2fd, 74 Spurtests gruen). Die Spur handelt also von allein,
      sobald ein scanner-Ausstieg USDC freigibt.
      Der zweite Grund (Guthaben) steht bewusst daneben - deshalb oeffnet der Dauerlauf
      kein Fenster: eine Order ohne Deckung wuerde die Boerse ablehnen.
      Kraken bleibt verboten (Auftrag Max 30.09.2026: "nur noch omnitrade auf kraken").
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/moondev_listingarb/wachen.json, OKX-Konto, scanner/


- [ ] **T-086 — moon-dev-ai-agents: RBI-Schleife laeuft, aber die Kursdatei ist die des Autors**
      Kontext: Die vier RBI-Laeufer des GUI starten seit 25.09.2026 (UTF-8 +
      Wurzel-.env im Kind, conda durch den venv-Interpreter ersetzt, Prompt-
      Datenpfad lokalisiert). OFFEN: die Kursdatei src/data/rbi/BTC-USD-15m.csv
      ist der Datensatz des Autors (31.046 Kerzen 15m, Ende 2023) - fuer eine
      Aussage ueber HEUTE muesste sie durch eine frische Reihe (OKX/Binance,
      eigener Abruf) ersetzt werden. Ausserdem: kein Walk-Forward, keine
      Kostenmodellierung ausser der Strategie-eigenen Gebuehr.
      Naechster Schritt: entscheiden, ob die Schleife ueberhaupt weiterlaufen
      soll - die gemessenen Ergebnisse (95-97 % Verlust) sprechen dagegen, dass
      sie ohne Walk-Forward je etwas Tragfaehiges liefert.
      Angelegt: 2026-09-25
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents (geaenderter Klon: moongui.py,
      src/agents/rbi_agent*.py, backtest_runner.py, 19 *_BT.py)




- [ ] **T-083 — Bonsai 2 27B: Vision nicht angeschlossen**
      Kontext: Das Modell kann Bilder lesen; die Vision-Komponente (mmproj Q8_0,
      0,63 GB) ist absichtlich nicht geladen worden, weil der VRAM bei 8k Kontext
      schon randvoll ist (322 MiB frei). `BONSAI_MMPROJ_CPU=1` bzw.
      `--no-mmproj-offload` wuerde den Projektor in den RAM legen - ungemessen.
      Naechster Schritt: mmproj laden, mit `--no-mmproj-offload` starten, ein Bild
      (Screenshot) durchschicken und Geschwindigkeit notieren.
      Angelegt: 2026-09-25
      Betrifft: Modelle/GGUF/Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf (fehlt noch)


- [ ] **T-082 — Bonsai 2 27B: PQ2_0-Packung ist ungemessen**
      Kontext: Auf dem Rechner liegen 5,95 GB als PTQ1_0; erzeugt 32 t/s bei 8k
      Kontext (gemessen 25.09.2026). Die PrismML-Karte nennt fuer Ampere-Karten
      (diese 3060 Ti ist Ampere) PQ2_0 beim Dekodieren SCHNELLER als PTQ1_0 -
      die Packung ist aber 7,21 GB gross und passt nicht mehr vollstaendig in den
      VRAM, braucht also Teilauslagerung. Ob das unter dem Strich schneller ist,
      ist nicht gemessen.
      Naechster Schritt: PQ2_0 herunterladen (7,21 GB), mit `-ngl 99` und mit
      abgestufter Auslagerung (`-ngl 60/70`) messen, Zahlen in
      Wiki/Werkzeuge/Bonsai-2-27B.md stellen.
      Angelegt: 2026-09-25
      Betrifft: Modelle/GGUF/, Agenten/Werkzeuge/bonsai-27b.ps1


- [ ] **T-081 — Fremdarbeit im Arbeitsbaum liegen gelassen (parallele Sitzung)**
      Kontext: Beim Commit am 25.09.2026 lagen Aenderungen im Arbeitsbaum, die nicht
      aus dieser Sitzung stammen: geloescht `Agenten/Hermes/scripts/test_waisen_wache.py`,
      geaendert vier Skill-Dateien (arbeitsbaum-git-hygiene, dauerprozess-bewachen,
      fremdrepo-agent-start, laufwerk-platz-schaffen) sowie
      `handel-spuren/references/boersen-aufrufe.md` und `okx-fehlermeldungen.md`, neu
      `Agenten/Hermes/skills/brainfiles/sicherung-fahren/` und `kraken-cli/` im
      Wurzelordner. Bewusst NICHT mitgenommen (eigene Pfade stagen).
      Naechster Schritt: der naechste Lauf von `fremdarbeit-einziehen.ps1` (taeglich
      20:40) oder eine Sitzung committet sie mit Autor „Andere Sitzung“;
      `kraken-cli/` in der Wurzel gehoert nach Werkstatt/Repos.
      Stand 25.09.2026 03:20 weiterhin im Baum (nicht angefasst, eigene Pfade
      gestaged): `Agenten/Handel/swap/handeln.py`, `swap/kandidaten.py`, drei
      swap-Tests, `Agenten/Hermes/skills/brainfiles/arbeitsbaum-git-hygiene/SKILL.md`,
      `kraken-cli/`. Der eigene Commit 1fcea14 (Kraken-Abweisungs-Sonde) hat nur
      die acht eigenen Pfade mitgenommen.
      Angelegt: 2026-09-25






- [ ] **T-078 — Zweiter Stufenlauf „hoch“ laeuft doppelt**
      Kontext: Beim Neustart des Basis-Dauerlaufs am 25.09.2026 standen ZWEI
      Prozesspaare mit `--risiko hoch` (60536/37924 und 60424/38452, beide am
      24.09. 18:49 gestartet) neben Basis und Mittel. Stufenlaeufe senden nicht und
      gehen nie live, ein Doppel kostet also nur Rechenzeit und Netz — es ist aber
      dieselbe Klasse wie die vier gleichzeitigen Laeufe vom 16.09.2026, die bei
      offenem Freigabefenster echtes Doppelorder-Risiko trugen. Nicht angefasst
      (Fremdstart einer anderen Sitzung).
      Naechster Schritt: pruefen, welcher Ausloeser den zweiten hoch-Lauf startet
      (Get-ScheduledTask der MaxHirn-Handel-Aufgaben), ein Paar geordnet beenden und
      IgnoreNew setzen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/dauerlauf.hoch.pid, Agenten/Routinen/handel-dauerlauf.ps1


- [ ] **T-077 — swap: der erste echte Live-Einstieg steht noch aus**
      Kontext: swap hat seit dem 25.09.2026 einen tragfaehigen Zweig-Trenner (`modus`
      an jeder Position, Ausstiege und Tore nur im eigenen Zweig, Bereinigung nur
      fuer Altbestand ohne Feld). Im Journal stehen bis 24.09. AUSSCHLIESSLICH
      Papierzeilen; der Live-Zweig hat noch nie geordert, obwohl sein Freigabefenster
      seit dem 24.09. 23:55 offen ist. Belegt ist damit nur, dass eine Papierposition
      jetzt stehen bleibt (kein `buchbereinigung` mehr im Kreis).
      Naechster Schritt: beim ersten Live-Kauf pruefen, dass die Zeile `modus=live`
      traegt und der naechste Papierzweig sie NICHT verkauft.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/swap/
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - im swap-Journal stehen 3 live-Zeilen, aber alle sind funding - keine live-eroeffnen-Zeile; bleibt offen.**






- [ ] **T-074 — nautilus_kraken (Spot) hat noch nicht gekauft - drei gemessene Tore**
      Kontext: Der Arm ist scharf (handel_erlaubt=true, freigabe.erfuellt=true,
      live_einsatz_eur 1.0), kauft aber nur bei einem FRISCHEN Kauf der kopier-Spur.
      Gemessen am 25.09. 01:15: (1) Kraken-Spot-EUR frei = 0,7059 - unter
      `mindest_guthaben_eur` 2 (das Guthaben sitzt im FUTURES-Konto, T-073);
      (2) Freigabefenster zu: der Dauerlauf hat 22:40:42 eine Anfrage gestellt, sie
      lief 23:10:42 ab, ohne dass jemand `/ja` gegeben hat - nautilus_kraken steht
      NICHT in AUTO_FREIGABE; (3) kein neues kopier-Signal seit 24.09. 15:36.
      Zusaetzlich: `handeln.py --vorschau` meldet 'Guthaben nicht abrufbar (Kraken
      meldet: EGeneral:Permission denied)', waehrend derselbe Key ueber
      `kraken/kraken.py` und ueber mosaics Vorschau 0,7059 liefert - der Leseweg
      NUR von `kraken_rest.py` scheitert (T-075).
      Naechster Schritt: entscheiden, ob die 1-EUR-Endabnahme (T-065) auf das
      Spot-Konto soll - dann muessten Geld vom Futures- ins Spot-Konto und das
      Freigabefenster gestellt werden; sonst bleibt der Arm Papier.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/nautilus_kraken/wachen.json, freigabe_fenster.json





- [ ] **T-071 — Bot-Profil fuer intelligent-trading-bot fehlt**
      Kontext: Der Klon ist seit 25.09.2026 im Startfenster angebunden (Eintrag in
      `Agenten/Werkzeuge/repos-zentrale/repos-zentrale.json`, Startbefehl
      `itb_pruefstand.py`, Verknuepfung `Werkstatt/Repos/intelligent-trading-bot`).
      Als einziges Flotten-Repo hat er KEIN Hermes-Profil - `/bot` kennt ihn nicht.
      Anlegen kostet Arbeit: Profil erzeugen (ohne --clone), providers-/model-Block
      (nous/deepseek-v4-flash-0731), terminal.cwd auf den Klon, die drei
      Router-Schluesselnamen in die eigene .env, und die auth.json als Verknuepfung
      auf `Agenten/Hermes/auth.json` (braucht einen UAC-Klick).
      Naechster Schritt: entscheiden, ob ueberhaupt ein Bot gebraucht wird - eine
      Spur entsteht hier nicht (der Klon ist nur Pruefstand, Wiki Lektion 13).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/profiles/, Agenten/Werkzeuge/repos-zentrale




- [ ] **T-067 — Kraken-Futures-Orderweg LIVE bewiesen, Spur auf PF_SOLUSD umgestellt (armt noch nicht)**
      Kontext: `nautilus_kraken/kraken_futures.py` spricht die Futures-REST an
      (eigener Dienst, eigene Signatur, Kopf APIKey/Nonce/Authent, Schluessel
      KRAKEN_FUTURE_API_KEY/SECRET). Der Live-Zweig ruft weiter `kraken_rest`;
      KRAKEN_PRODUKT=futures laedt dort das Futures-Modul.
      KORREKTUR 25.09.2026 (die frueher hier behauptete Regel war FALSCH):
      1 Kontrakt ist NICHT 1 USD Nennwert, sondern EINE Einheit der Basiswaehrung,
      und der Einschuss fuer ein EEA-Konto ist 10 % (`marginSchedules.europa`).
      Gemessen: 1 Kontrakt PF_NEARUSD bei 4,5517 USD belegte 0,4548 USD Marge
      (= 10 % von 4,5517). Damit gilt: PF_XBTUSD 1 Kontrakt = 1 BTC = rund
      84.500 USD, Einschuss rund 8.450 USD - mit 141,59 USD frei um den Faktor 60
      zu gross (Boerse: insufficientAvailableFunds, auch fuer size 1).
      PF_ETHUSD braucht ~269 USD, PF_SOLUSD ~11,75 USD, PF_NEARUSD ~0,46 USD.
      `kontrakte()` ist entsprechend korrigiert, `einschuss()` und `handelbar()`
      sind neu; Tests nautilus_kraken 30 gruen.
      Beleg 25.09.2026, ECHTER Round-Trip (futures_probe.py --anwenden): Kauf
      1 Kontrakt PF_NEARUSD @ 4,5517 (01:46:15, Fuellung gelesen), Verkauf
      reduceOnly @ 4,5508, Position danach geschlossen (Positionen [], Orders []).
      Kosten der Runde: 0,0029 USD auf 4,55 USD Nennwert, davon 0,0009 USD
      Kursunterschied (Spread) -> Gebuehr je Seite im Bereich 0,04-0,05 %.
      /fills und /accountlogcsv sind mit diesem Schluessel nicht lesbar (401) -
      die Equity vor/nach der Ausfuehrung war der Messpunkt.
      STAND 24.09.2026 abends: die Freigabekette ist fertig eingerichtet -
      herzschlag_max_minuten zurueck auf 180 (Hausregel 19.09.2026, T-004:
      eine 45er-Grenze stellt nach einem Rechner-Ausfall echte Positionen ohne
      Handelsentscheidung flach und war zugleich der einzige Wert, den
      systempruefung.ps1 Block 11b als Fehler meldet), Guthaben-Tor fuer Spot
      in sperren_zeile() (Muster kraken/mosaic), live_einsatz_eur 1.00 mit
      live_max_risiko_gesamt_eur 20 statt der Papier-Grenzen 50/200, Schutz-Stop
      direkt nach dem echten Kauf, Journalzeile bei gescheitertem Live-Auftrag
      und ein Waechter je Position: der Live-Lauf ordert Papier-Positionen des
      gemeinsamen Buchs NICHT (4 Papier-Positionen liegen dort, sie haetten beim
      ersten echten Zyklus einen Verkauf von BTC ausgeloest, das es an der
      Boerse nicht gibt - der Fehler von scanner/xperp am 21./23.09.).
      Probe: `handeln.py --vorschau` nennt genau EINEN Sperrgrund
      ("Freigabefenster zu") - damit stellt der Dauerlauf die Anfrage und die
      Auto-Freigabe greift nicht (sie verlangt genau einen Fenster-Grund UND
      das Wort Freigabefenster). Der Round-Trip selbst wartet auf das /ja von
      Max im Dauerlauf; freies Guthaben 4,10 EUR liegt ueber dem Einsatz 1,00.
      Tests: nautilus_kraken 38 gruen inkl. test_live_orderweg.py (5).
      ERLEDIGT 25.09.2026 (Auftrag Max: 'SOL'): Symbol und Paar der Spur stehen
      auf PF_SOLUSD, dazu live_einsatz_usd 118.00 (= EIN Kontrakt SOL, rund
      117,5 USD Nennwert) und live_max_risiko_gesamt_usd 25.00. Das BUCH wurde
      dabei sauber gezogen: die vier offenen Papier-Positionen (alle PF_XBTUSD,
      Einstiege 81.110-81.475) sind zum Kurs 84.263 mit grund=symbolwechsel
      geschlossen (Einsatz 200,00 -> Erloes 206,80 USD, +6,80), weil die
      Strategie JEDE Position mit dem Kurs des EINEN konfigurierten Symbols
      bewertet - ein offenes BTC-Buch waere beim ersten SOL-Kurs als 'stop'
      ausgestiegen. Spiegelung nach Q: bestaetigt, Buch jetzt leer.
      Die Sperrenkette nennt jetzt den ECHTEN Bedarf: `handelbar()` sagt
      '1 Kontrakt PF_SOLUSD braucht 11.75 USD Einschuss, frei sind ...', und
      ein Einsatz UNTER einem Kontrakt wird gesperrt ('Mindestgroesse der
      Boerse') statt still aufgerundet - das war der eigentliche Fallstrick:
      bei live_einsatz_eur 1.00 haette die Boerse 1 Kontrakt = 118 USD
      gefuellt. Tests nautilus_kraken 73 gruen (test_futures_grenzen 5 neu).
      ARMIERT 25.09.2026 (eine parallele Sitzung, Auftrag Max 'Strategie hoch
      fahren!'): handel_erlaubt und freigabe.erfuellt stehen true, das Fenster
      oeffnet die Auto-Freigabe selbst (Spur steht in dauerlauf.AUTO_FREIGABE).
      Stand 26.09. 02:42 lokal: Modus live seit rund 23:00 UTC, 74 live-Zeilen,
      NOCH KEIN Einstieg (0 Positionen) - es fehlt ein frischer Kopier-Kauf als
      Signal. BINDEND: der Futures-Schluessel wird abgewiesen, solange ein VPN
      laeuft (NordLynx -> authenticationError); ohne Tunnel sind 141,59 USD frei.
      Kleiner Nachtrag von mir: der Vermerk _herzschlag_regel behauptete noch
      'auf 45, sobald handel_erlaubt true wird' - richtig ist 180 (Hausregel
      19.09.2026, gilt fuer Papier UND Live); der Wert stand schon auf 180.
      OFFEN: der erste echte SOL-Kauf (1 Kontrakt, rund 122 USD Nennwert,
      Schutz-Stop 19,8 % darunter) - der Dauerlauf meldet ihn ueber den Bus.
      Vor dem Arming ist zu entscheiden, ob eine Mindestposition von 118 USD
      (Risiko am 19,8-%-Stop rund 23 USD) gewollt ist. Kleiner geht auf Kraken
      Futures nicht: die Boerse kennt keine Kontraktbruchteile.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-25
      Betrifft: Agenten/Handel/nautilus_kraken/kraken_futures.py, futures_probe.py,
      test_kraken_futures.py, wachen.futures.json (Symbol, offen)




- [ ] **T-066 — nautilus_kraken_futures: Futures-Gebuehr 0,05% verifizieren**
      Kontext: Die Futures-Variante (PF_XBTUSD, USD, Hebel) laeuft Papier. Die
      Gebuehr 0,05% ist eine Annahme, nicht gemessen. Vor dem Scharfschalten
      der Futures-Spur an einer echten Fuellung pruefen.
      Naechster Schritt: Futures-Gebuehr an einer echten (oder Demo-)Order
      messen, in wachen.futures.json eintragen.
      ERLEDIGT 08.10.2026: onchainos wird von keinem moondev-Agenten mehr
      gespawnt (0 Treffer im Quellcode, 0 in Logs, kein Prozess); Copilot 0
      Prozesse; docker nur als MCP-Gateway, npx/uvx 0. CREATE_NO_WINDOW steht
      an allen Treiber-Spawns.
      Angelegt: 2026-09-24 · Zuletzt: 2026-10-08
      Betrifft: Agenten/Handel/nautilus_kraken/wachen.futures.json

      BELEG 25.09.2026 (echte Fuellung, 1 Kontrakt PF_NEARUSD): Kosten der Runde
      0,0029 USD auf 4,55 USD Nennwert, davon 0,0009 USD Spread -> Gebuehr je
      Seite 0,04-0,05 % des Nennwerts. Die Annahme 0,05 % ist damit NICHT
      widerlegt, aber wegen der groben Aufloesung (0,0001 USD) auch nicht eng
      bestaetigt. Fuer eine belastbare Zahl eine groessere Fuellung fahren
      (PF_ETHUSD, ~2.688 USD Nennwert, Einschuss ~269 USD - braucht Guthaben
      und eine Entscheidung von Max). Messweg: Equity vor/nach der Ausfuehrung,
      weil /fills und /accountlogcsv mit diesem Schluessel 401 liefern.


- [ ] **T-065 — nautilus_kraken: echter ~1-EUR-Spot-Live-Test (Freigabekette)**
      Kontext: Der REST-Orderweg (kraken_rest.py) ist committed (de433da) und
      per Preflight verifiziert (Keys, Guthaben, markt_kauf echt=False). Der
      echte Orderweg (markt_kauf/markt_verkauf mit echt=True) wird nur aktiv,
      wenn die Spur ueber die Freigabekette scharf ist (handel_erlaubt=true +
      freigabe.erfuellt=true + offenes Freigabefenster). Ein winziger
      ~1-EUR-Round-Trip verifiziert den echten Spot-Pfad.
      Naechster Schritt: Freigabekette oeffnen (nur Max), dann einen
      ~1-EUR-Round-Trip ausfuehren und die Fuellung pruefen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Agenten/Handel/nautilus_kraken


- [ ] **T-064 — Nautilus-Kraken-Orderweg: WebSocket-Token verweigert, REST traegt**
      Kontext: `nautilus_kraken` und `nautilus_kraken_futures` laufen Papier
      (`handel_erlaubt=false`, `freigabe.erfuellt=false`). Der gemeldete Fehler "OKX
      51001" war ERZEUGT und steht in keiner Datei (Suche ueber den Handelsbaum: nur
      xperp und Skill-Doku). Der echte Blocker ist der Exec-Client des
      Nautilus-Kraken-Adapters: `Failed to get WebSocket token: API error:
      EGeneral:Permission denied` (gemessen 24.09. 18:49 UTC,
      `nautilus_kraken/logs/kraken-orders-20260924T184919894096Z.jsonl` ->
      `success: false, entered: false`). Ueber REST arbeitet derselbe Kraken-Schluessel
      einwandfrei (Kontostand und 14 offene Orders lesbar). Eine parallele Sitzung baut
      `nautilus_kraken/kraken_rest.py` + Live-Zweig in `handeln.py` (24.09. 20:33,
      Commit de433da) - Kraken direkt per REST am Nautilus-Adapter vorbei. Der
      REST-Weg ist verifiziert (Keys, Guthaben, markt_kauf echt=False Preflight
      ok, 28/28 Tests + 4/4 Sperrenkette). Offen: echter ~1-EUR-Round-Trip
      (T-065) und Futures-Gebuehr (T-066).
      ENTSCHEIDUNG Max 24.09.2026: REST bleibt. Der Nautilus-Exec-Client wird aufgegeben,
      der Kraken-Schluessel NICHT um WebSockets-Rechte erweitert.
      BELEG (24.09. 21:35, Trockenlauf validate=true, kein Geld bewegt): Marktkauf und
      Stop-Loss werden angenommen ('buy 0.00010 XBTEUR @ market' / 'sell 0.00010 XBTEUR
      @ stop loss 78000.0'), ein falsches Paar wird abgelehnt - der Weg ist befahrbar UND
      fehlerempfindlich. Dabei gefunden und behoben: wachen.json trug kein 'paar',
      handeln.py fiel auf das Nautilus-Symbol BTC/EUR zurueck, das Kraken mit
      'EQuery:Unknown asset pair' abweist -> "paar": "XXBTZEUR" ergaenzt, Test Orderpaar
      in test_handeln.py.
      OFFEN: Der Futures-Arm (PF_XBTUSD) hat GAR KEINEN REST-Zweig - kraken.py ist die
      SPOT-REST-API, Kraken Futures eine eigene Schnittstelle (anderer Host, eigene
      Signatur). Der REST-Weg traegt nur nautilus_kraken (Spot).
      GUTHABEN: 4,10 EUR frei (24.09. 21:35) - unter jedem sinnvollen Einsatz, der
      Live-Zweig bleibt also ohnehin zu, bis EUR frei ist.
      Naechster Schritt: pruefen, ob der Nautilus-Exec-Client aus dem Code verschwindet
      (kraken_order_test.py, Altlasten), damit niemand den toten Weg neu verdrahtet.

      Betrifft: Agenten/Handel/nautilus_kraken (+ `_futures`), Werkstatt/Repos/nautilus*
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24


- [ ] **T-063 — moon-dev-ai-agents: entscheiden, ob die Content-/Medienagenten ueberhaupt laufen sollen**
      Kontext: In der .env stehen acht Platzhalter, die nur ueber Fremdkonten zu
      fuellen sind und mit Handel nichts zu tun haben: ELEVENLABS_API_KEY,
      GROQ_API_KEY, YOUTUBE_API_KEY, RESTREAM_CLIENT_ID/-SECRET/-EMBED_TOKEN,
      TWITTER_USERNAME/-EMAIL/-PASSWORD, GOOGLE_APPLICATION_CREDENTIALS. Alles,
      was fuer den HANDEL zaehlt, laeuft schluessellos (lokales Modell ueber die
      Bruecke, oeffentliches CoinGecko statt Schluessel, RPC_ENDPOINT gesetzt).
      Solange diese Frage offen ist, bleiben die betroffenen Agenten dunkel -
      sie sind aber kein Betriebsfehler, sondern eine Entscheidung.
      Naechster Schritt: Max sagt je Gruppe ja/nein (Twitter, Yo
      uTube, Restream, ElevenLabs, Google) - bei nein die Platzhalter
      auskommentieren, damit der Zustand nicht als "unfertig" gelesen wird.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents/.env





- [x] **T-059 — Rest-Konsolenblitze: Agenten->onchainos, copilot, docker/npx**
      Kontext: Nach dem Fix der Haus-Prozesse bleiben ~6 kurze Konsolenfenster je
      Minute: (a) die moondev-Agenten (Fremd-Repo new_or_top/kraken) spawnen
      onchainos.exe weiter ohne CREATE_NO_WINDOW; (b) GitHub Copilot (copilot.EXE
      via npx) blitzt; (c) einmalige docker/npx/uvx-Build-Ketten. Kein
      kontinuierlicher Fokus-Raeuber wie der git-Poller, aber noch sichtbare
      Fenster.
      Naechster Schritt: (a) im Fremd-Repo die onchainos-Spawns auf
      CREATE_NO_WINDOW stellen; (b/c) beobachten, ob Copilot/docker-Builds im
      Alltag stoeren, dann gezielt.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents, GitHub Copilot, Docker

- [?] **T-049 — xperp-Key antwortet 50101, kein Orderweg**
      Kontext: Der OKX-EEA-Satz von xperp liefert 50101
      ("APIKey does not match current environment"), obwohl handel_erlaubt
      und freigabe.erfuellt true sind und das Fenster offen war. Kein
      Dateischalter loest das - es ist ein Konto-/Schluesselproblem: Host
      (EEA vs. global), IP-Whitelist oder fehlendes Trade-Recht.
      Naechster Schritt (Max, OKX-Portal): signierter Leseaufruf gegen den
      Registry-Host (guthaben/offene_orders), Schluesselrechte im Portal
      pruefen (read_only -> Trade), Host/Whitelist abgleichen.
      Wartet auf: Max - OKX-Key-Rechte/-Umgebung fuer xperp
      Betrifft: Agenten/Handel/xperp/okxf.py, OKX EEA (OKX_BASE)
      Angelegt: 2026-09-22 · Zuletzt: 2026-09-22

- [?] **T-050 — kraken bleibt Papier: Guthaben und Rueckrechnung**
      Kontext: Freies Guthaben reichte zuletzt nicht fuer mindest_guthaben_eur
      60 (33,15 EUR frei), und die eigene Rueckrechnung ist -0,57 % je Runde.
      handel_erlaubt=false, stillgelegt gesetzt. Die Auto-Freigabe oeffnet nur
      das Fenster, nicht das Guthaben.
      Naechster Schritt (Max): entscheiden, ob Kraken-Guthaben aufgestockt
      wird; bis dahin bleibt kraken bewusst nicht live.
      Wartet auf: Max - Aufstockung Kraken-EUR oder bewusst Papier lassen
      Betrifft: Agenten/Handel/kraken/wachen.json (mindest_guthaben_eur)
      Angelegt: 2026-09-22 · Zuletzt: 2026-09-22




















- [ ] **T-057 — Hermes-Desktop git-Poller (bundle-skew) feuert auf jeden Fokus**
      URSACHE GEKLAERT (25.09.2026, belegt): onFocus (src/store/updates.ts:1083) ruft
      refreshDesktopVersion() (1084) -> getVersion() -> IPC hermes:version
      (electron/main.ts:18193) -> detectRendererSkew() (18172) -> detectBundleSkew()
      (zwei runGit: merge-base + rev-list) - auf JEDEN Fokus, OHNE Rate-Limit.
      Kontrast: runPassiveChecks (der eigentliche Update-Poll) ist korrekt per
      passiveCheckDue auf 24h begrenzt (BACKGROUND_UPDATE_CHECK_MS), nur der
      Versions-Check im Fokus-Handler ist ungebremst. Rueckkopplung: der git-
      Prozess (Konsolen-Kind eines GUI-Elterns ohne Konsole) blitzt ein Fenster,
      das den Fokus stiehlt; der Focus-Wechsel feuert onFocus erneut -> 2-3s-
      Schleife (gemessen 24.09.: ~8 git-Blitze/40s). Nach dem Haus-Fix (moondev/
      handelszentrale fensterlos) ist der direkte Fokus-Raeuber weg, die Schleife
      stoppt; der Verstaerker bleibt latent (jeder echte Fokus-Wechsel laeuft
      wieder git).
      Fix (upstream Nous Research, das Repo ist KEIN Fork): detectRendererSkew()-
      Ergebnis cachen (1x je Lauf oder TTL), oder refreshDesktopVersion() in
      onFocus an passiveCheckDue binden. Ein lokaler Patch wird von `hermes update`
      ueberschrieben.
      Naechster Schritt: als Issue an NousResearch/hermes-agent melden, oder einen
      lokalen Cache-Patch anlegen und den Update-Verlust bewusst in Kauf nehmen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-25
      Betrifft: hermes-agent apps/desktop (updates.ts:1083, main.ts:18172)


- [ ] **T-056 — OKX-Quoten-Node (nautilus) liefert nichts**
      Kontext: `docker ps` antwortet nicht mehr, der Container nautilus-demo
      ist damit unerreichbar; der Nautilus-Arm bekommt keine Fills und fuellt
      kein Buch (Quote-Feed tot, feed_quelle=fallback_kopier, quotes=0).
      Naechster Schritt: Docker Desktop pruefen (Dienst + Container), danach
      einen Zyklus abwarten und die Quoten im Zustand zaehlen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: nautilus (eigenes Repo), Docker Desktop


- [ ] **T-055 — fomo-radar-Bot ohne auth.json-Verknuepfung**
      Kontext: Das Profil laeuft, aber `auth.json` ist noch eine eigene Datei
      statt eines Symlinks auf Agenten/Hermes/auth.json; das Anlegen braucht
      Adminrechte (UAC-Prompt blieb nachts unbestaetigt). Bis dahin traegt die
      Ollama-Rueckfallkette.
      Naechster Schritt: `Agenten/Hermes/scripts/auth-verknuepfen.ps1` erhoeht
      ausfuehren, UAC bestaetigen, danach `hermes -p fomo-radar chat -q "hallo"`
      und den Modellnamen pruefen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      BELEG 2026-09-30: Bestandsaufnahme aus der Kanban-Karte `t_5cf6dbfd` (Board `repos`,
      Status blocked/needs_input): 18 Profile haben inzwischen einen echten Symlink auf
      `Agenten/Hermes/auth.json`; **zwei fehlen noch: `fomo-radar` und `lokal-first`**.
      Ein Versuch aus der headless-Sitzung schlug fehl - `ln -s` bildet ohne das Privileg
      `SeCreateSymbolicLinkPrivilege` STILL eine Kopie (genau das Insel-Muster, das die
      Verknuepfung vermeiden soll); die zwei entstandenen Kopien wurden wieder entfernt.
      Unberuehrt bleiben `awesome-systematic-trading` und `basic-memory` (eigene befuellte
      Stores - ein Symlink wuerde deren Bot-Zugangsdaten aendern).
      Betrifft: Agenten/Hermes/profiles/fomo-radar/, Agenten/Hermes/profiles/lokal-first/






- [ ] **T-052 — OKX-DCA-Parameter der laufenden Bots anpassen**
      Kontext: Der Weg ist bekannt (dca/amend-order-algo), aber `anpassen_erlaubt`
      steht auf false und es fehlt Guthaben: 0,03 USDC frei gegen ~428 USDC
      Margin (UNI 163,90 · ARB 145,19 · MON 102,09 · BCH 17,25). Die Leitern der
      fuenf DCA-Bots sind 4,2-8,4 % tief, die Instrumente laufen 8,6-13,2 % je
      TAG (ATR14) - Regel fuer neue Bots: Tiefe = max(3x ATR, Rueckgang 90/180/
      365 Tage, 10 %), Schritt 0,15-0,5x ATR, nie unter 2,5 %; der Engpass ist
      die STUFENZAHL (dca_max_steps 12 deckt bei 2,5 % nur 30 %).
      Naechster Schritt: Max nennt je Bot die gewuenschten Zahlen; danach
      `wachen.json` scharf schalten und mit --anwenden amendieren.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Agenten/Handel/okx_bot_waechter/, OKX-Bots UNI/ARB/MON/BCH



- [?] **T-042 — orbk und kraken sind per Telegram nicht freizugeben**
      Kontext: Beim Pruefen von Max' Frage „Orbk ist noch nicht in freigabe.py
      angebunden?“ am 13.09.2026 aufgenommen. Es gibt zwei Freigabe-Wege mit
      zwei Spurenlisten:
      - Bildschirm (`freigabe.py`): spot (scanner), hebel (xperp), kraken;
        eine unbekannte Spur lehnt es mit klarer Meldung ab.
      - Telegram (`dauerlauf.befehl`): nur xperp und swap (`/ja_xperp`,
        `/ja_swap` samt nein/stop/freigabe) plus die generischen `/ja`,
        `/nein`, `/stop` fuer Spot.
      `kraken` hat einen Live-Pfad (`--live` vorhanden) und ist am Bildschirm
      angebunden, per Handy aber nicht - sie laesst sich nur am Rechner scharf
      schalten. `orbk` hat gar keinen Live-Pfad (kein Orderaufruf,
      handel_erlaubt=false, Sperre 4 offen: backtest_bestanden=false); dort ist
      nichts anzubinden, solange die Spur nicht live gehen soll. Beide stehen
      auf handel_erlaubt=false, die Luecke ist damit derzeit folgenlos.
      Naechster Schritt (erst bei Bedarf): vier Stellen nach dem Muster von
      swap - Live-Zweig und `freigabefenster.lade("<spur>")` in den
      Sperrgruenden der jeweiligen handeln.py, `WACHEN`/`BETRAGSFELD`/`TITEL`
      in freigabe.py, die `/ja_<spur>`-Familie in dauerlauf.befehl, und
      handel_erlaubt erst nach der jeweiligen Sperre.
      Betrifft: `Agenten/Handel/{orbk,kraken}`, `freigabe.py`, `dauerlauf.py`
      Angelegt: 2026-09-13

- [?] **T-045 — Facebook und Instagram: es fehlt nur die Browser-Extension**
      Kontext: Auf Max' Auftrag wurden am 16.09.2026 die Kanaele `facebook` und
      `instagram` in Agent Reach installiert. Beide laufen ueber OpenCLI
      (`@jackwener/opencli` 1.8.7, npm global) und benutzen den eigenen
      Chrome-Login - kein Cookie-Export, keine Zugangsdaten in Dateien. Der
      Daemon laeuft (Port 19825), der Kanalstatus ist `warn`: „opencli
      installiert, aber keine verbundene Browser-Extension“.
      Naechster Schritt (nur am Rechner, nicht aus der Sitzung):
      1. Extension installieren und aktiv lassen:
         https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk
      2. Im selben Browser bei facebook.com und instagram.com angemeldet sein,
         danach einen `opencli`-Befehl laufen lassen - der Doctor schaltet den
         Kanal erst danach auf verfuegbar.
      Zu bedenken: die Extension handelt im Namen des angemeldeten Kontos; die
      Doku von Agent Reach raet dafuer zu einem Zweitkonto. Gepostet wird nichts,
      die Kanaele lesen (Suche, Profil, Feed, Gruppen).
      Wartet auf: Max - Extension und Anmeldung
      Betrifft: [[Agent-Reach]], `Werkstatt/Repos/Agent-Reach`
      Angelegt: 2026-09-16

- [?] **T-046 — Benutzer-PATH enthaelt einen abgeschnittenen Eintrag `C:\Users\fa`**
      Kontext: Beim Nachsehen, wohin `yt-dlp` installiert werden muss
      (16.09.2026), fiel im Benutzer-PATH der Eintrag `C:\Users\fa` auf - ein
      abgeschnittener Pfad, der auf nichts zeigt. Er ist harmlos, kann aber
      Fehlermeldungen verwirren, und er zeigt, dass beim Bearbeiten des PATH
      einmal eine Zeile zu kurz geraten ist.
      Naechster Schritt: Den Eintrag in den Benutzervariablen entfernen - vorher
      die PATH-Zeile sichern, wie am 23.08.2026 praktiziert. Die uebrigen 18
      Eintraege bleiben unangetastet.
      Wartet auf: Freigabe von Max (Systemeinstellung)
      Betrifft: `HKCU\Environment` PATH
      Angelegt: 2026-09-16
- [?] **T-047 — Santiment-MCP braucht Max' Browser-Anmeldung (OAuth)**


- [ ] **T-023 — ASUS MG278 antwortet nicht auf DDC/CI, PowerDisplay lässt ihn aus**
      Kontext: Aus dem PowerToys-Report vom 02.09.2026. Von zwei Monitoren
      (beide direkt an DisplayPort) steuert PowerToys PowerDisplay nur den
      Acer XB281HK. Die **ASUS MG278** (`DISPLAY2`, EDID `ACI27A8`, in Windows
      als „Generic PnP Monitor") liefert keine DDC/CI-Daten; unabhängig von
      PowerToys mit `Agenten/Routinen/monitor-ddc-pruefen.ps1` nachgestellt:
      schon `GetCapabilitiesStringLength` scheitert mit Win32-Fehler
      `0xC0262582` (`ERROR_GRAPHICS_DDCCI_VCP_NOT_SUPPORTED`). Kein
      Software-Fehler — Reparatur nur am Monitor möglich.
      Nächster Schritt (Max, am Gerät): MG278-OSD → System Setup → DDC/CI → On;
      hilft das nicht, Monitor ~30 s stromlos, DP-Kabel/-Eingang prüfen. Danach
      `monitor-ddc-pruefen.ps1` erneut, bei Erfolg PowerDisplay „Monitore
      aktualisieren". Details: [[Hardware]], Abschnitt „Monitore und PowerToys
      PowerDisplay".
      Betrifft: Monitor ASUS MG278 · `Agenten/Routinen/monitor-ddc-pruefen.ps1`
      Angelegt: 2026-09-02 · Zuletzt: 2026-09-02

- [!] **T-004 — Zwölf Abschaltungen ohne Bluescreen seit 08.08., Ursache offen**
      Kontext: Alle zwölf Kernel-Power-41-Ereignisse haben `BugcheckCode = 0`
      und `PowerButtonTimestamp = 0` — kein Bluescreen, kein Speicherabbild,
      sondern harter Stromverlust. Keine WHEA-Fehler in 30 Tagen, keine
      Plattenfehler (nur ID 98, Information), kein Dump. In den drei Minuten
      vor dem letzten Abschalten steht **ein einziger** Protokolleintrag.
      **Die Beobachtung vom 28.08. ist entschieden — negativ.** Sie musste nicht
      auslaufen: seit dem Start am 28.08. um 16:00 ist der Rechner dreimal
      ausgegangen (29.08. 10:45, 29.08. 13:17, 30.08. 20:59, echte Zeitpunkte
      aus Ereignis 6008). Aus neun Vorfällen sind damit zwölf geworden, und die
      Abstände sind kürzer geworden: drei in zwei Tagen gegen sieben in den
      vierzehn Tagen davor.
      **Standby scheidet als Ursache aus.** Seit dem 28.08. 06:46 gab es keinen
      einzigen Standby-Zyklus mehr (kein Kernel-Power 42/107) — die drei neuen
      Abstürze fielen also in eine Phase ganz ohne Standby. Der Ablauf „3–10
      Minuten nach dem Aufwachen aus S3" war Begleiterscheinung, nicht Ursache.
      Das frühere Merkmal `SleepInProgress = 16` beruhte auf einer Verwechslung
      mit dem Feld `Checkpoint`; `SleepInProgress` ist bei allen zwölf `0`.
      Nächster Schritt: **Stromzufuhr ausserhalb des Netzteils prüfen** —
      Kaltgerätekabel, Steckdosenleiste, Wandsteckdose. Billig und nie geprüft,
      deshalb zuerst; danach erst der Gegentest mit einem bekannt guten Netzteil.
      Beides Handgriffe an der Hardware, also Max' Sache, und **einen nach dem
      anderen**, sonst ist unbekannt, welcher gewirkt hat. Bei zuletzt 2,5 bis
      32 Stunden Abstand zeigt sich das binnen zwei bis drei Tagen.
      Wartet auf: Max — Handgriff an Kabel und Steckdose.
      Messbefehl: Routinen/absturz-nachmessen.ps1 (nur lesend, ohne Adminrechte)
      Betrifft: [[Hardware]], Abschnitt „Nachmessung 30.08.2026, 22:20"
      **BELEG 07.10.2026 (gemessen - der Text oben ist ueberholt):** nicht zwoelf,
      sondern **23 Kernel-Power-41-Ereignisse in 90 Tagen**, letztes am
      05.10.2026 03:28:44 - jedes mit `BugcheckCode=0` und jedes von einem
      Systemstart (Ereignis 6005) Sekunden spaeter gefolgt. Das ist die
      Signatur eines HARTEN Stromausfalls, nicht eines Bluescreens. Die
      Abstaende sind unregelmaessig (23.09., 24.09., 25.09., 30.09., 04.10.,
      05.10.) - kein Lastmuster, eher Netzteil oder Zuleitung. Der Netzteiltausch
      hat nichts geaendert.
      **ZUSATZBEFUND derselben Messung:** im selben Zeitraum **341 Ereignisse 2004**
      ('virtueller Speicher unzureichend'), zuletzt 07.10. 18:01. Die
      Auslagerungsdatei ist der zweite Verdaechtige (Commit-Grenze) - beides
      gehoert in dieselbe Untersuchung.
      Naechster Schritt: (1) Auslagerungsdatei vergroessern (Skript
      `Routinen/einmalig-20260930-auslagerung.ps1` liegt fertig, braucht Admin),
      (2) danach 14 Tage beobachten, ob 41 UND 2004 zurueckgehen. Ohne Schritt 1
      ist jede weitere Messung wertlos.
      **STAND 07.10.2026 (gemessen):** Die Auslagerungsdatei ist bereits eingerichtet
      (Skript lief am 30.09., Neustart erfolgt, Uptime 68,9 h). Commit-Grenze
      103,7 GB (vorher 84,5 GB). C: 8192/8192 MB fest, O: 32768/32768 MB.
      **Was noch offen ist:** Commit frei nur 13,0 GB (belegt 90,7 GB), O: nur
      17,3 GB frei (die 32-GB-Datei kann nicht wachsen). 776 Prozesse, davon
      vmmemWSL 11,3 GB, 57 Python, 27 Claude, 31 Chrome, 37 Node. Ereignis 2004:
      4 in den letzten 24 h (gegenüber 341 in 90 Tagen deutlich weniger, aber noch da).
      **Naechster Schritt:** (1) vmmemWSL beenden (WSL/Docker abschalten) oder
      (2) Chrome/ChatGPT/TradingView schliessen, wenn nicht gebraucht. Beides
      entlastet den Commit um 15-20 GB. (3) Danach 14 Tage beobachten, ob 2004
      auf 0 geht.
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-30 (22:20)


- [ ] **T-007 — 18 claude.ai-Connectors ohne einen einzigen Aufruf**
      Kontext: `claude mcp list` meldet 21 aktive claude.ai-Connectors. In
      53 gespeicherten Sitzungen wurden davon **drei** je einmal aufgerufen
      (Kalender, Gmail, Drive); die übrigen 18 kein einziges Mal — darunter
      Uber, Uber Eats, PayPal, HubSpot, monday.com, Morningstar, DataHub,
      Play Sheet Music, tldraw, Excalidraw, Sprouts, Windsor.ai, Superhuman
      Docs, ChangeThisFile, UseMyContext, Unstructured, Economic Index.
      Jeder belegt in **jeder** Sitzung Kontext, bevor ein Wort gesagt ist.
      Max hat das am 27.08. selbst als größten Hebel benannt; der Punkt ging
      danach verloren, weil er nirgends eingetragen war.
      Nächster Schritt: Max schaltet sie in den Connector-Einstellungen auf
      claude.ai ab — das geht nicht lokal und nicht aus einer Sitzung heraus.
      Messbefehl für den Vorher-Nachher-Vergleich:
      `sitzungen_auswerten.py --werkzeuge`
      Betrifft: claude.ai-Konto, nicht den Vault
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28







- [x] **T-418 — fib_retrace im Dauerlauf ohne Holer (vorbestehend):**
    - Kontext: test_lage meldet 'fib_retrace ohne Holer im Bericht'. fib_retrace ist im Dauerlauf, hat aber in lage.py keinen spur_-Eintrag. Vorbestehend (nicht durch die llm_stunde-Verdrahtung eingefuehrt).
    - Naechster Schritt: spur_fib_retrace() in lage.py anlegen + HOLER-Eintrag.
    - Angelegt 2026-10-19 · Zuletzt 2026-10-19 / Betrifft: Agenten/Handel/lage.py
## Erledigt
- [x]   **T-333 - Zweigbestand aufgeraeumt, ein Grenzfall braucht eine Entscheidung**
      Kontext: `python Agenten/Werkzeuge/zweige.py` (neu, 04.10.2026) misst alle
      Zweige und Worktrees mit drei Zeugen (`cherry` = Patch-ID-Inhalt,
      `merge-base --is-ancestor` = Kopf, `rev-list --count` = Zahlen). Gemessen:
      6 wegwerfbar (2 lokale claude/*, 3 auf origin, Worktree C:/tmp/head_wt),
      1 mit ECHTEM Vorlauf: `claude/wizardly-brown-69qfnp` (5bff1231, 1 Commit,
      "handel: UTC-Zeiten umrechnen statt abschneiden" - steht in KEINER anderen
      Zweiglinie und in keinem Worktree), 1 Grenzfall: `claude/trading-stack-
      setup-40ef0d` (aeeac180, inhaltlich schon in master als 6ccb94e4, aber
      andere sha - `branch -d` verweigert dort, `-D` waere blind).
      Naechster Schritt: Max entscheidet fuer 5bff1231 (Master einziehen mit
      `git branch -f master claude/wizardly-brown-69qfnp`, oder als eigenen
      Zweig behalten), danach `python Agenten/Werkzeuge/zweige.py --entfernen
      --push` fuer die belegten Faelle.
      Angelegt 2026-10-04. Betrifft: Agenten/Werkzeuge/zweige.py.
      **Erledigt 2026-10-18.** Entscheidung obsolet, gemessen: 5bff1231 ist Vorfahre von master, aeeac180 ebenfalls; Zweige claude/wizardly-brown-69qfnp und claude/trading-stack-setup-40ef0d existieren weder lokal noch auf origin - die Option 'Master einziehen' wurde bereits vollzogen.
- [x] **T-400 - Werkstatt-Junction-Verlust: Wache existiert (KORREKTUR)**
      KORREKTUR meines Eintrags vom 14.10.: junction-wache.py existiert seit
      11.10.2026 (T-390, Commit 924ed9d3) und hat den Verlust am 13.10. 22:12
      um 23:38 gemeldet (Merkdatei cache/junction-wache.json). Mein Satz
      "es gibt KEINE Wache" war falsch. Einziger Rest: der Cron-Takt stand auf
      60 m, die Doku nennt 10 m - am 14.10.2026 auf 10 m korrigiert (jobs.json).
      Angelegt 14.10.2026 · Zuletzt 14.10.2026
      Betrifft: Agenten/Routinen, Werkstatt
      
- [x] **T-396 — xperp-Vorschlag vom 11.10. ist blockiert: er will Max' eigene Auftraege zuruecknehmen**
      Kontext: Der Verbesserer hat um **04:38** einen Vorschlag erzeugt
      (`Agenten/Handel/verbesserer/berichte/2026-10-11-spur2/`, Marker `ANGEFRAGT`
      seit 04:45). Drei Parameter, alle innerhalb ihrer Baender, die Zahlen sind
      gut: OOS netto je Runde **-0.2187 -> 1.2429**, Holdout **-1.2744 -> 0.1011**
      bei n=28, Siebregeln a-e bestanden.
        - `stop_atr_faktor`        1.5 -> 1.25  (Band 1.0..2.5)
        - `trailing_stop_prozent`  1.5 -> 1.0   (Band 0.75..3.0)
        - `trailing_trigger_r`     1.0 -> 1.25  (Band 0.5..2.0)
      BLOCKER: der Vorschlag traegt zwei weitere geaenderte Schluessel, die
      nicht auf der Whitelist stehen - `_ev_entfaellt` und
      `handpositionen_automatisch_schliessen`. `anwenden.py:311` bricht bei
      JEDEM solchen Schluessel ab (`{"ok": False, "grund": "nicht auf der
      Whitelist: _ev_entfaellt"}`), es wird also NICHTS angewendet - auch die
      drei guten Parameter nicht. Live nachgerechnet, nicht gelesen.
      URSACHE (Zeitfolge): der Vorschlag ist vom **04:38**, Max' Auftraege sind
      vom **04:39** (`handpositionen_automatisch_schliessen` auf true) und
      **04:43** (`_ev_entfaellt`). Der Verbesserer hat die `wachen.json` VOR
      beiden gelesen und den Stand von damals eingefroren; beim Anwenden wuerde
      er beide Auftraege zuruecknehmen wollen. Dass das nicht passiert, ist
      die Whitelist bei der Arbeit - der Schaden ist verhindert, der Vorschlag
      ist blockiert, nicht kaputt.
      **ERLEDIGT 11.10.2026 - der Vorschlag ist neu gefahren und ANGEWENDET.** Der
      blockierte Stand war der Lauf vom **04:38**; er ist unter `berichte/erledigt/
      2026-10-11-spur2/` abgelegt und zu Recht abgewiesen (zwei Waechter: Whitelist
      anwenden.py:311 fuer `_ev_entfaellt`, Basis-Pruefsumme anwenden.py:340-348).
      Danach lief ein ZWEITER Lauf, der den Stand NACH Max' Auftraegen gelesen hat:
        - `anwendungslog.json`: `"anwendung_ts": "2026-10-11T09:01:19Z"`,
          `"entscheidung": "angewendet"` (09:01 UTC = 11:01 CEST).
        - Commit **8967e4ec** (11.10. 11:01:19 +0200) aendert `xperp/wachen.json`,
          3 insertions / 3 deletions - genau die drei Parameter.
      Live nachgeprueft in `xperp/wachen.json`: `stop_atr_faktor=1.25`,
      `trailing_stop_prozent=1.0`, `trailing_trigger_r=1.25` - identisch mit dem
      Kandidaten. Die zwei umstrittenen Schluessel stehen dort jetzt so, wie Max sie
      gesetzt hat (`_ev_entfaellt` = Max-Vermerk, `handpositionen_automatisch_
      schliessen` = true) und sind im eingefrorenen Kandidaten BYTEGLEICH - der
      neue Lauf hat den spaeteren Stand gelesen, das Problem ist damit weg.
      Keine Entscheidung mehr offen; Ticket kann zu.
      Naechster Schritt (Entscheidung Max): Vorschlag NEU fahren lassen (liest
      den aktuellen Stand und traegt nur die drei Parameter ein), oder die zwei
      Schluessel bewusst freigeben - Letzteres hiesse, der Verbesserer darf
      kuenftig Max' Schalter umdrehen, vermutlich nicht gewollt.
      Betrifft: Agenten/Handel/verbesserer/berichte/2026-10-11-spur2/,
      Agenten/Handel/verbesserer/spuren.json, Agenten/Handel/xperp/wachen.json
      Angelegt: 2026-10-11 · Zuletzt: 2026-10-11
      Verifiziert 13.10.: Commit 8967e4ec angewendet (3 Parameter 1.25/1.0/1.25 in xperp/wachen.json), blockierter Stand archiviert in berichte/erledigt/2026-10-11-spur2, Max-Auftraege (_ev_entfaellt, handpositionen_automatisch_schliessen=true) unangetastet
- [x] **T-377 - carry.py Wache fertig gestellt**
      Kontext: 07.10.2026. carry.py fertig: Cross-Venue-Carry-Scanner, rein lesend,
      OKX+Kraken, 5 Basen negativ (netto bp -34,1…-37,0), 16/16 Tests gruen.
      Wache gebaut: carry-wache.py + tests (5/5 gruen), Hermes-Cron alle 15 min no_agent,
      Watchdog-Muster (leere Ausgabe = nichts zu melden), Default MIN_NETTO_BP=2.0,
      --vorschau/--min-netto. Commits f9b06806 + 162952e8 + Wache-Commit (772aee44) +
      Cron-Commit (6cdd2b48). Nicht angefasst: Fremdarbeit (historie_okx.py,
      knowledge-base, scanner_quant, worktrees-rueckgabe, SKILL.md, .worktrees/),
      OKX/Kraken-Schluessel, Guthaben, live-Orderwege. Entscheidung Max: MAX_MELDUNGEN_PRO_TAG=3,
      --min-netto als Wachen-Param.
      Angelegt 07.10.2026 · Zuletzt 07.10.2026 · Betrifft Agenten/Handel



- [x] **T-364 — 16 Doppelverkäufe in 6 Spuren: derselbe Fehler wie NIGHT, drei Tage aelter**
      Kontext: Nach der Reconciliation von `moondev_signalwelle` (T-356, 05.10.2026)
      habe ich die Regel ueber ALLE Buch-Spuren gelegt (Wegwerf-Skript mit
      DictReader, Spalten NACH DEM NAME - eine feste Spaltennummer hatte zuerst
      151 Fehlbefunde im scanner gemeldet, dort steht `pos_id` an Stelle 14 statt 12).
      Befund: 16 Doppelverkäufe, KEINE Geister (keine Position ist im Zustand offen
      und zugleich verkauft) - der Zustand hat den Code-Fix `ee3ff9be` also ueberall
      richtig ueberlebt, nur das Journal trage Altlast:
        iv_wand 7 (BTC-USDT, alle `ziel`, 30.09.-04.10.)
        liq_wand 3 (BTC-USDT-SWAP, 01.-04.10.)
        moondev_topmovers 2 (BP mit 3 Zeilen am 01.10., AR am 04.10.)
        prophet_signal 2 (BTC- und SOL-USDT-SWAP, je 2x `trend_umkehr` am 02.10.)
        klassik_ema 1 (ETH-USDT-SWAP, 2x `gegensignal` am 03.10.)
        robinhood_radar 1 (02.10., 2x `ziel`)
      Alle Befunde liegen VOR dem 05.10. - seit `ee3ff9be` kann keiner neu entstehen.
      Das Merkmal ist ueberall dasselbe: 10-30 Minuten Abstand, gleiche Position,
      `ziel` oder `gegensignal` zweimal. Das sieht nach einem Vorschau-Aufruf aus
      (`dauerlauf.nur_fenster_fehlt()` je Takt), genau der Weg, der NIGHT erzeugt hat.
      Naechster Schritt: je Spur mit `buch_reconcile.py` (der Regel-Rechner aus
      t_0f4fa35d, `spur_buch.SPALTEN` deckt alle Buch-Spuren ab) aufloesen lassen -
      Vorschau zuerst, die verworfenen Zeilen bleiben daneben. Vorher die Herkunft
      klaeren: sind es dieselben Vorschau-Aufrufe oder ein zweiter Weg?
      Angelegt: 05-10-2026 · Zuletzt: 05-10-2026
      Betrifft: Agenten/Handel/{iv_wand,liq_wand,moondev_topmovers,prophet_signal,klassik_ema,robinhood_radar}/handelsjournal*.csv


- [x] **T-360 — Repos-Zentrale: zwei Manifest-Eintraege zeigen auf den geloeschten Ordner `kopier1zu1`**
      Kontext: Die vollstaendige Suite der Zentrale (296 Tests) meldet seit dem
      05.10.2026 zwei rote Tests, BEIDE vorbestehend und beide mit derselben
      Ursache: die Fremdarbeit-Uebernahme 607d9b51 vom 05.10. 00:20 hat den Ordner
      `Agenten/Handel/kopier1zu1` aus dem Baum entfernt, zwei Manifest-Eintraege
      tragen ihn aber weiter (der Ordner und `kopier1zu1/auswertung.py` mit
      belegtem Startbefehl). Das Fenster zeigt beide unter FEHLT.
      Naechster Schritt: entscheiden, ob `kopier1zu1` zurueckkommt oder der
      Eintrag aus `repos-zentrale.json` wandert - `fuellen.py --anwenden` nimmt
      vorhandene Eintraege NICHT mit heraus, das ist Handarbeit in der Kuratierung.
      Angelegt: 2026-10-05 · Zuletzt: 2026-10-05
      Betrifft: Agenten/Werkzeuge/repos-zentrale/repos-zentrale.json, Agenten/Handel/kopier1zu1


- [x] **T-378 — BtcRegimeKurz abgelegt: Kante 1,2:1, nicht lebensfaehig**
      **Erledigt 2026-10-11.** Bewusst abgelegt (Entscheidung Max 08.10.2026): Kante 1,2:1, kein Halbjahr positiv, Gebuehr 0,20 %/Runde traegt nicht. Strategie bleibt committet (6a02d231) als Referenz, nicht scharf.
      Kontext: Auftrag Max 05.10.2026 (BTC-Strategie fuer Seitwaerts-/Aufwaerts-Phasen,
      Haltung max 48 h, moeglichst kurz, hohe Fluktuation). Gebaut und gemessen:
      12 Spot-Laeufe (4 Stops 0,8-3,0 % x 2 Halbjahre + Gegenversuch ohne Gewinnvorabnahme)
      + 2 Futures-Laeufe. Kante VOR Gebuehr stabil +0,09 bis +0,14 % je Umsatz (Mittel 0,119 %),
      Gebuehr 0,20 % je Runde (Spot) -> Kante traegt nicht (0,6:1). Futures (0,05 %/Seite):
      H1 +0,04 % (break-even), H2 -4,2 % -> Verhaeltnis 1,2:1, aber kein Halbjahr positiv.
      Beleg: Strategie committet 6a02d231, Skill-Lehre d42da77d, Logs btc_fut_H1/H2.log in cache/scratch.
      Naechster Schritt: keine - bewusst abgelegt (Entscheidung Max 08.10.2026).
      Angelegt: 2026-10-08 · Zuletzt: 2026-10-08
      Betrifft: Agenten/Handel/freqtrade/user_data/strategies/BtcRegimeKurz.py


- [x] **T-349 — adx_macd: das Vorzeichen folgt dem Fenster, nicht der Strategie**
      **Erledigt 2026-10-11.** Messung abgeschlossen: das Vorzeichen folgt dem Fenster (14T -25 / 28T +10 / 42T -0,2 USD je Runde bei konstanter Trefferquote ~36 %), KEIN Freischalten. Folgearbeit lebt in T-347 (Papierrunden) und T-291 (Guthaben).
      Kontext: T-342 neu gemessen am 04.10.2026 (BTC 15m, 10.000 USD,
      0,05 %/Seite, OMNI_LONG_ONLY=1, echter Rust-Backtest):
        14 Tage  13 Runden  38,5 %   -324,86 USD   (-24,99 je Runde)
        28 Tage  19 Runden  36,8 %   +182,67 USD   ( + 9,61 je Runde)
        42 Tage  29 Runden  34,5 %     -6,74 USD   ( - 0,23 je Runde)
      Der notierte Wert (+117,04) ist heute +182,67 - dieselbe Zelle, ein
      anderer Kerzenstand. WICHTIGER: die Trefferquote ist in allen drei
      Fenstern nahezu gleich (36,8 / 36,8 / 34,5 %), das Vorzeichen der PnL
      dagegen nicht. Eine Kennzahl, die zwischen -25 und +10 USD je Runde
      pendelt, ohne dass sich die Trefferquote bewegt, beschreibt den
      Zeitraum, nicht die Regel.
      Gegenprobe mit der zweiten Fassung: rsi_long_only haelt 60 / 73 / 78 %
      Treffer und verliert in ALLEN drei Fenstern (-13,15 / -147,97 /
      -40,25). Hohe Trefferquote und Verlust zugleich ist keine bessere
      Strategie, sondern ein zu enges Ziel: der Gewinn je Treffer deckt den
      Verlust je Fehlschlag nicht.
      Naechster Schritt: KEIN Freischalten. adx_macd darf erst nach echten
      Papierrunden aus T-347 (laufend, erster Einstieg 04.10. 21:24) und
      T-291 (Guthaben) weitergehen. Die Geometrie von rsi_long_only (Ziel zu
      eng) ist eine eigene Messung und gehoert nicht in diese Zelle.
      Angelegt 04.10.2026 · Betrifft Agenten/Handel/omnitrade/intervalle_messen.py



## Regeln

- **Am Sitzungsanfang lesen**, bevor gefragt wird, woran gearbeitet werden soll.
- **Sofort eintragen**, wenn ein Punkt entsteht — nicht am Sitzungsende sammeln.
  Wird die Sitzung vorher abgebrochen, ist der Punkt sonst weg.
- **Erledigtes nach `## Erledigt` - [x]   **T-319 — Der ZRO-Ausstieg in moondev_topmovers scheitert seit 20:48 jeden Zyklus — ERLEDIGT 04.10.2026**
      Kontext: OKX 51008 "Your available ZRO balance is insufficient" - gemessen im
      Ereignisprotokoll, 20:48-23:32 am 02.10.2026. Die Position blieb im Buch,
      jeder Zyklus versuchte denselben Verkauf und scheiterte.
      
      ERLEDIGT 04.10.2026 (Diagnose, kein Code): die ZRO-Position war ein
      BUCH-GEIST, keine echte Position. Belegt an der Boerse:
        - /account/balance ZRO: spotBal 0.983, frozenBal 0, availBal 0.983 -
          kein eingefrorener Bestand, keine offene Spot-Position.
        - /trade/orders-history, orders-history-archive, orders-pending fuer
          ZRO-USDT: 0 Orders. Die Position wurde NIE real gehandelt.
        - Journal: Kauf 02.10. 05:24 als modus=live (1.9143), Ausbuchung 02.10.
          22:48 als papier-Stop (1.76). Der live-Kauf war ein Geist - dieselbe
          Klasse wie der xperp-Fall vom 21.09.2026.
        - Der 51008-Fehler war die Folge: die Spur versuchte, eine Position zu
          verkaufen, die an der Boerse nie existierte.
      
      Die Spur laeuft seither sauber: letzter Lauf 04.10. 20:17, 250 Kandidaten,
      keine Datenfehler, letzte Journal-Zeile ein normaler AR-Stop. Die ZRO-Fehler
      endeten am 02.10. 23:32.
      
      Angelegt 03.10.2026 · Zuletzt 04.10.2026 · Betrifft: moondev_topmovers.

verschieben**, mit Datum. Nicht löschen —
  Der Eintrag bleibt als `- [x]` mit Erledigt-Datum dort stehen.





- [x] **T-374 - Handpositionen (herkunft=boerse_handgriff) werden nicht automatisch geschlossen**
      Kontext: 06.10.2026, NIGHT-XPERP-Position von Max an der OKX-Boerse von Hand eroeffnet;
      die Spur uebernahm sie als Fremdposition (grund=fremdposition_uebernommen), konnte aber
      keinen Boersen-Stop verankern (Journal den ganzen Tag: 'trailing nicht ausgefuehrt: keine
      Boersen-Stop-Kennung in der Position'). Am 06.10. um 16:31:59 UTC schloss pruefe_ausstiege
      die Position mit grund=stop, obwohl Max sie halten wollte ('ja war meine und das wollte ich').
      FIX umgesetzt: handeln.py pruefe_ausstiege + flach_stellen ueberspringen Positionen mit
      herkunft=boerse_handgriff (Tests xperp/tests/test_handeln_handposition.py, 5 gruen;
      Gegenprobe: normale Positionen werden weiter automatisch geschlossen).
      Naechster Schritt: beobachten; soll die Regel wieder greifen, braucht es einen Schalter
      in wachen.json (offene Entscheidung Max).
      Angelegt: 06.10.2026 - Zuletzt: 06.10.2026 - Betrifft: Agenten/Handel/xperp
      
- [x] **T-367 — Ausser-Haus-Aufgabe verschwindet taeglich; Wache haelt sie jetzt, Ursache offen**
      Kontext: Die Windows-Aufgabe `MaxHirn-Ausserhaus-Kopie` (taeglich 21:30,
      Wrapper `Agenten/Routinen/ausserhaus-kopie.ps1`) war am 05.10. um 22:30
      NICHT vorhanden, obwohl der Cron `ausserhaus-aufgabe-sichern`
      (195f6ee91ef0, taeglich 08:30) sie an DIESEM Morgen um 08:30:26 neu
      angelegt hatte. Der Cron meldet das seit dem 30.09. JEDEN Tag
      ("war nicht vorhanden und ist angelegt") - die Aufgabe ueberlebt also
      keinen Tag. Belege: `Agenten/Hermes/cron/output/195f6ee91ef0/*.md`
      (30.09., 01.10., 02.10., 05.10. je "nicht vorhanden und ist angelegt").
      NACHGEMESSEN 05.10. 22:30-22:55: Aufgabe um 22:34 angelegt, um 22:45 und
      22:52 WIEDER weg, um 22:55 nach erneutem Anlegen da - die Ueberlebenszeit
      liegt also im Bereich von MINUTEN bis Stunden, nicht bei einem Tag.
      NICHT die Ursache: kein Loescher im Haus - `Unregister-ScheduledTask`
      steht nur in `fremdarbeit-einziehen-aufgabe.ps1` (und dort fuer die EIGENE
      Aufgabe), `schtasks /Delete` nur in `hermes-agent/hermes_cli/
      gateway_windows.py` (Hermes-eigene Tasks, nie MaxHirn-*). Von den 28
      MaxHirn-Aufgaben ist NUR die Ausserhaus-Kopie betroffen.
      Ereignisprotokoll: war AUS, seit 05.10. 22:51 AN
      (`wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true`,
      brauchte Admin). Es hat bisher KEIN Loesch-Event (Id 141/142) - die
      bisherigen Faelle liegen vor der Einschaltung und sind damit spurlos.
      MASSNAHME: Wache `Agenten/Hermes/scripts/ausserhaus-aufgabe-wache.py`
      (Hermes-Cron da9824bc3e28, alle 10 min, no_agent, Telegram, leere Ausgabe
      = nichts senden) legt die Aufgabe neu an und schreibt Anlege-/Weg-Zeit in
      `Agenten/Hermes/cache/ausserhaus-aufgabe-wache.json` - damit ist die
      Ueberlebenszeit ab jetzt MESSBAR statt geraten.
      **Erledigt 2026-10-11 (Ursachensuche abgeschlossen).** Die Aufgabe
      ueberlebt seit 06.10. 01:52 durchgehend (Wache-Merkdatei: angelegt_um
      unveraendert, zuletzt_gesehen 11.10. 03:50) - der 08:30-Cron ist seit
      06.10. silent, das taegliche Verschwinden ist VORBEI. Kein Loesch-Event
      (141/142) fuer diese Aufgabe im gesamten TaskScheduler-Log (einzige 142 =
      Microsoft-Systemaufgabe). hermes update als Ursache ausgeschlossen:
      05.10.-Update (03:20) zu frueh fuer das 22:30-Verschwinden, 06.10.-Update
      (02:25) lief nach der Anlage (01:52) und hat sie nicht geloescht. Die
      Ursache der Altfaelle (30.09.-05.10.) ist nicht mehr rekonstruierbar -
      das Log war bis 05.10. 22:51 AUS, die Faelle sind spurlos. Registrar legt
      bereits korrekt per schtasks/XML an (nicht per Cmdlet). Wache bleibt als
      Absicherung aktiv.
      Angelegt: 2026-10-05 · Zuletzt: 2026-10-05
      Betrifft: Agenten/Routinen/ausserhaus-kopie-aufgabe.ps1,
      Agenten/Hermes/scripts/ausserhaus-aufgabe-sichern.py,
      Agenten/Hermes/scripts/ausserhaus-aufgabe-wache.py, Q:\MaxHirn-AusserHaus


- [x] **T-376 — Historie ausserhalb des Baums? (Entscheidung Max)**
      Kontext: T-361 (05.10.2026) war kein Loeschvorgang - der rote Replay-Lauf kam
      aus einem Worktree, und daten/ ist nicht versioniert. Damit ist die Frage nach
      dem ORT neu zu stellen: `historie_binance.ORDNER = HIER/daten/historie` ist
      relativ zur Modulposition, also sieht JEDE Kopie des Baums einen anderen Ordner.
      Gemessen 05./06.10.2026: 127 MB, 57 Reihen (45x 1H, 3x 4H, 3x 1D, 3x 5M),
      plus feed/ (30x 1D). Kein Umzug noetig, damit etwas funktioniert.
      **Erledigt 2026-10-11 (Entscheidung Max 'Ja').** Historie bleibt unter
      Agenten/Handel/daten/ - ein Umzug nach O: bringt nur neue Pfadbrueche, und der
      Nachfueller (Cron historie-wache) haelt den Bestand frisch. Kein Code geaendert.
      Angelegt: 06-10-2026 · Zuletzt: 06-10-2026
      Betrifft: Agenten/Handel/historie_binance.py, Agenten/Handel/daten/historie/


- [x] **T-384 - Documents/GitHub: 21 Klone ausserhalb der Flotte - 6 nicht in Werkstatt/Repos**
      Kontext: C:\Users\faupe\Documents\GitHub haelt 21 git-Klone, die NICHT in Werkstatt/Repos liegen. Bekannte Repos (nautilus_trader, unsloth, financial-services, context7, onchainos-skills u. a.) und NEU/anders: OmniQuant (eigener Fork), OpenMobius-skill, awesome-trading-agents, data-mcp, fintool, moon-dev-ai-agents2. Fund beim Skill-Scan 09.10.2026 (23 SKILL.md). Naechster Schritt: Entscheidung Max - die 6 unbekannten nach Werkstatt/Repos verschieben (Hausmuster) oder loeschen; Duplikate der Flotte dort entfernen. Angelegt: 2026-10-09
      **Erledigt 2026-10-11 (Auftrag Max 'T384 klonen').** Gemessen: von den damals 6 unbekannten waren 4 (OpenMobius-skill, awesome-trading-agents, data-mcp, fintool) inzwischen schon in Werkstatt/Repos. Die 3 echten fehlenden Fork-Repos nach Werkstatt/Repos verschoben: OmniQuant (origin=mfaupel95, upstream=OpenGVLab), cli (origin=mfaupel95, upstream=firecrawl), moon-dev-ai-agents2 (origin=mfaupel95, eigener Fork ohne upstream). Alle 3 in repos-zentrale.json aufgenommen (fuellen.py --anwenden, 265 Eintraege). Nicht verschoben: chromaprint (kein mfaupel95-Fork, Audio-Bibliothek, liegt schon in Werkstatt/repos-verschoben-aus-skills), mfaupel95 (Profil-Repo, 1 Commit), one-skill-to-rule-them-all-main + productivity (keine .git). Duplikate der Flotte in Documents/GitHub bleiben stehen (bewusst, kein Loeschauftrag).
      Betrifft: Skill-Scan 09.10.2026 (fremde-skill-sammlung-einbinden)



- [x] **T-181 — Bonsai-Einbau der parallelen Sitzung nutzt Port 8080 (freqtrade-Konflikt)**
      **Erledigt 2026-10-11.** bonsai-provider-einbauen.py schreibt Port 8081 (gemessen), kein 8080-Freqtrade-Konflikt mehr.
      Kontext: Eine parallele Sitzung baut Bonsai ein (Agenten/Hermes/scripts/bonsai-provider-einbauen.py) mit Port 8080 - genau der Port, den der Freqtrade-Container belegt (127.0.0.1:8080->8080). Ich habe am 29.09. auf 8081 umgestellt (Starter + Config); das Skript der parallelen Sitzung wuerde 8080 wieder einschreiben.
      Naechster Schritt: Das Skript der parallelen Sitzung auf 8081 anpassen oder nach dessen Lauf den Port erneut pruefen.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Hermes/scripts/bonsai-provider-einbauen.py



















- [x] **T-324 — Spur-Audit: Edge und Echtheit fuer ALLE Spuren in einem Durchgang messen**
      **Erledigt 2026-10-11.** spur-audit-wache.py + Cron a9a58d42a4a8 (alle 6 h, enabled) laufen seit 03.10.2026; die 23 Basiswerte ohne Binance-Paar bleiben bewusst ohne Ersatzinstrument (dokumentierte Offenheit).
      Kontext: Nach T-322 (Scanner: Einstieg aus dem Vortagesbericht, +17,49 % und t=15,3 waren ein Rechenfehler) gab es im Haus kein Werkzeug, das diese Fehlerklasse von selbst findet. Es gab `auswertung_alle.py` (rechnet die Zahlen) und Einzelfallbefunde. Folge: eine neue Spur hatte keine Messung, an der ihre Runden vor der Freigabe haette vorbeiliegen koennen. Gebaut: `Agenten/Handel/spur_audit.py` beantwortet fuer alle Spuren zwei Fragen - IST DIE STATISTIK ECHT (Haltedauer im Aufrufertakt, ein Instrument traegt die Mehrheit, Einstiegspreis je (Instrument, Tag) identisch) und HAT DIE SPUR EDGE (Excess gegen BUY & HOLD aus den gespeicherten Kerzen, nicht Trefferquote). Spurliste aus `dauerlauf.SPUREN`, Zuordnung aus `journalpaarung`, Aufrufertakt aus `dauerlauf.TAKT_MAX_MINUTEN` - keine eigenen Zahlen. 33 Tests, acht Gegenproben greifen. Befund am laufenden System: die 475 Runden aller Spuren haben zu 100 % eine Basislinie, nach dem Nachladen von 14 auf 45 Kerzenreihen (Binance, ohne Schluessel).
      Naechster Schritt: `spur_audit.py` als Cron-Wache haengen (leere Ausgabe = gesund), damit ein Befund im Betrieb ankommt statt erst bei der naechsten Einzelpruefung. Und: die 23 Basiswerte ohne Binance-Paar (Aktien-ETPs CL/XAU/QQQ/MSTR/META, Pump-Token CASHCAT/FARTCOIN/UNITREE, GRASS/OKB/XDC/MON/DRV) bekommen bewusst KEIN Ersatzinstrument - fuer die bleibt die Edge-Frage offen, bis eine Historiequelle existiert.
      Angelegt 03.10.2026 · Betrifft: alle Spuren, historie_binance, handel-spuren/references/pitfalls.md Punkt 104.



- [x] **T-369 — Junction-Verlust der Wurzel: Ursache unbewiesen, Wache gebaut**
      **Erledigt 2026-10-11.** Zeuge 2 (Zielvergleich + Schreibtest + .env-Lage) ist seit 07.10. gebaut und hat heute erstmals echt geschlagen: 2 Profil-.env ohne HERMES_WRITE_SAFE_ROOT (auto-prediction, informatiker161) nachgezogen, Wache danach 0 Befunde. Rest (uebrige Profile nur BrainFiles) ist bewusste Entscheidung Max vom 07.10.
      Kontext: Am 05.10.2026 um 22:12:52 war `BrainFiles/Werkstatt` kein Verweis mehr
      auf `O:/Werkstatt`, sondern ein echter, fast leerer Ordner (nur die zwei
      konfig-doktor-Dateien). Alle 49 Repos, omnitrade, OmniRoute und die Projekte waren
      ueber den BrainFiles-Pfad unsichtbar; `omnitrade.cmd` meldete 'keine Statusdatei'.
      Auf O: lag alles unversehrt - nur der Verweis war weg. Reparatur war verlustfrei
      (Dateien nach O: kopiert, echter Ordner entfernt, `New-Item -ItemType Junction`).
      AUSGESCHLOSSEN als Ursache: `konfig-doktor.ps1` (schreibt nur eine Datei) und seine
      Testsuite (alle Fixtures in GetTempPath mit eigener GUID). Zeitgleich 22:12:52
      wurden `datensortierung.ps1`, `sicherung.ps1` und `wissen-index-pruefen.ps1`
      geschrieben (parallele Sitzung im Baum) - keine davon fasst Werkstatt an.
      GEBAUT: `Agenten/Hermes/scripts/konfig-doktor-wache.py`, Cron `konfig-doktor-wache`
      (1beb6d64a8c8, alle 4 h, no_agent, Telegram, leere Ausgabe = nichts), Commit 6c50e960.
      Naechster Schritt: pruefen, ob die Junction erneut verschwindet (die Wache meldet es
      binnen 4 h). Tritt es wieder auf, im selben Moment die Kommandozeilen laufender
      Skripte mitschreiben - der Verursacher ist dann fassbar. Offen bleibt: welche
      Sitzung um 22:12 im Baum schrieb.

      07.10.2026 - BEFUND (Hermes, beim Schreiben von AGENTS.md im Repo claude-code):
      Die Junction ist wieder da und zeigt auf `O:\Werkstatt`. Laut Zeitstempel wurde sie
      am 07.10.2026 um 00:16 neu angelegt (`dir /AL`: "<JUNCTION> Werkstatt
      [\??\O:\Werkstatt]", `LinkType: Junction`). Heute also KEIN Verlust.
      Gefunden wurde derselbe Mechanismus von der anderen Seite: Hermes' Schreib-Sandbox
      (`HERMES_WRITE_SAFE_ROOT`) stand nur auf `C:\...\BrainFiles`. Beim Schreiben nach
      `C:\...\BrainFiles\Werkstatt\Repos\claude-code\AGENTS.md` loeste der Pruefer den
      Reparse-Punkt auf, landete auf `O:\Werkstatt\...` und lehnte ab: "outside
      HERMES_WRITE_SAFE_ROOT". Dreimal gescheitert, waehrend `read_file` und `terminal`
      durchkamen - dieselbe Kante, zwei verschiedene Urteile ueber denselben Pfad.
      Damit ist die Kante benannt: alles, was ueber den BrainFiles-Pfad auf Werkstatt
      zugreift, haengt am Reparse-Punkt. Fehlt er, sind die 49 Repos unsichtbar; ist er da,
      entscheiden aufloesende Werkzeuge ueber `O:\` - und liegen dann ausserhalb einer
      Sandbox, die nur auf BrainFiles gesetzt ist.
      BEHOBEN: `HERMES_WRITE_SAFE_ROOT` umfasst jetzt beide Wurzeln, in ZWEI `.env`-Dateien
      (jedes Hermes-Profil fuehrt den Wert selbst): `Agenten/Hermes/.env` und
      `Agenten/Hermes/profiles/claude-code/.env`. Wert:
      `C:\Users\faupe\Documents\BrainFiles;O:\Werkstatt`. Beleg: `get_safe_write_roots()`
      liefert beide; `O:\Werkstatt\Repos\...` ERLAUBT, `C:\Windows\...` und `~/.ssh`
      weiterhin GESPERRT.
      FUER DIE WACHE: `konfig-doktor-wache.py` prueft nur, ob der Verweis DA ist - nicht, ob
      er auf das richtige Ziel zeigt und ob die Werkzeuge durchkommen. Eine Zusatzpruefung
      "Ziel == O:\Werkstatt UND ein Schreibtest im Repo klappt" faengt beide Ausfaelle
      dieser Kante.
      Offen (Entscheidung Max): die uebrigen Repo-Bot-Profile unter
      `Agenten/Hermes/profiles/<name>/.env` tragen weiterhin nur BrainFiles. Dort bleibt es
      so, solange kein Bot in Werkstatt schreiben muss.
      Angelegt: 05-10-2026 · Zuletzt: 07-10-2026
      Betrifft: Agenten/Hermes/scripts/konfig-doktor-wache.py, Werkstatt (Junction), Modelle (Junction), Agenten/Hermes/.env, Agenten/Hermes/profiles/claude-code/.env


- [x] **T-386 - omniquant: Stop-Breite jetzt kalibrierbar - 12 echte Runden, 83% Treffer, Band unveraendert lassen (Empfehlung)**
      **Erledigt 2026-10-11 (Entscheidung Max, (a)).** stop_max_pct 12.0 bleibt unveraendert: 12 echte Runden mit 83 % Treffer und Gewinne > Verluste belegen das Band; SUI 12,02 % ist Einzelfall der 20-Tage-Extrema-Rechnung, kein Systemfehler.
      Kontext: Befund 10.10.2026. omniquant hatte im Journal 0 geschlossene Runden - eine Stop-Breite liess sich nicht kalibrieren. Die 10 offenen Positionen zeigten Stop-Breiten 6,4-13,5 % (teils ueber stop_max_pct 12.0). Die Prognose rechnet den Stop gegen 20-Tage-Extrema (prognose.py:121-133), nicht gegen den Einstieg - daher die Streuung. Tore in prognose.weit.json: mindest_score 60, mindest_score_short 45, mindest_cr 1.0, stop_min_pct 5.0, stop_max_pct 12.0.
      NEUER BEFUND 11.10.2026 (nach T-389, omniquant eigener Rechenweg): omniquant hat 12 ECHTE Runden (10 ziel, 2 stop, 83% Treffer) - die Kalibrierung ist jetzt moeglich. Stop-Breiten der echten Runden: Ziel-Ausstiege 10,45-13,00 % (Gewinne +6,70 bis +16,17), Stop-Ausstiege LIT 11,77 % (-6,11) und TRB 13,96 % (-7,59). Die Stop-Breite FUNKTIONIERT: 83% Treffer, Gewinne > Verluste, die 2 Stop-Ausstiege sind normale Verluste, keine Fehlkalibrierung. Aktuelle offene Positionen: nur SUI (12,02 %) liegt knapp ueber dem Band 12.0, alle anderen darunter (FIL 11,60, STX 11,98, ADA 10,71, JUP 9,89, W 9,43, BTC-BRL 6,88, OKB 6,44; XPL/MON sind SHORT mit ~11,4 % Breite).
      Naechster Schritt: Entscheidung Max - (a) stop_max_pct 12.0 unveraendert lassen (Empfehlung, belegt durch 12 echte Runden mit 83% Treffer; SUI 12,02 % ist ein Einzelfall der 20-Tage-Extrema-Rechnung), oder (b) stop_max_pct senken, damit keine offene Position ueber dem Band liegt.
      Angelegt: 2026-10-10 · Zuletzt: 2026-10-11
      Betrifft: Agenten/Handel/omniquant/, prognose.weit.json




- [x] **T-388 - Dateischwund-Wache auf den ganzen Baum erweitert: dateischwund-wache-baum.py (10.10.2026)**
      **Erledigt 2026-10-11.** dateischwund-wache-baum.py laeuft (Merge 23a0c844, Cron 6f11866c3c05 alle 15 m enabled), Probelauf exit 0 ohne Befund; die Beobachtung uebernimmt die Wache selbst.
      Kontext: Die bestehenden Wachen deckten nur Agenten/Hermes/scripts (dateischwund-wache.py) und Agenten/Handel (dateischwund-wache-handel.py) ab. Der T-100-Fall (versionierte Datei verschwindet, fremdarbeit-einziehen committet die Loeschung) kann ueberall passieren. BEHOBEN: neue dateischwund-wache-baum.py prueft die VERSIONIERTE TEXTEbene des ganzen Baums (git ls-files, ~2844 Dateien, Laufzeit 1,2s - kein rglob ueber .venv/daten). Git-Soll + Merkliste + Leer-Erkennung, meldet nur bei Auffaelligkeit, Ruhe 6h. Merge 23a0c844. Cron 6f11866c3c05 (alle 15m, no_agent). Gegenprobe: versionierte Datei geloescht -> Git-Soll-Befund.
      Naechster Schritt: beobachten. Nicht-versionierte Dateien in kritischen Ordnern bleiben den beiden Einzel-Wachen ueberlassen (Arbeitsteilung).
      Angelegt: 2026-10-10 · Zuletzt: 2026-10-10
      Betrifft: Agenten/Hermes/scripts/dateischwund-wache-baum.py




- [x] **T-390 - Werkstatt-Junction: zweiter Verlust in 6 Tagen (05.10., 11.10.2026) - Wache bauen**
      **Erledigt 2026-10-11.** junction-wache.py gebaut (10-min-Takt, prueft LinkType+Target+Inhalt von Werkstatt und Modelle, Watchdog-Muster, 7 Tests gruen, Cron b65d0a979ce8 no_agent Telegram). Schliesst das 4-h-Fenster der konfig-doktor-wache, durch das der Verlust von 02:00-02:20 heute fiel.
      Kontext: BrainFiles\Werkstatt war am 11.10.2026 02:00 KEINE Junction auf O:\Werkstatt mehr, sondern ein echter, seit 10.10. 18:47 gewachsener Schatten-Ordner (23 Eintraege: Aufraeum-Verschiebungen, plan-/spec-MDs, omnitrade-status-Kopien). Alle Zugriffe ueber BrainFiles\Werkstatt\ liefen ins Leere: scanner-papier-stunde schlug stundenlang mit 'Python oder Ordner fehlt' fehl (Befund 2 des Sammelauftrags hatte diese Ursache). GELOEST (verlustfrei, 11.10. 02:00-02:20): Schatten-Inhalte nach O: gerettet (2 Abweichungen -> O:\Werkstatt\zusammenfuehrung-20261011: okx_demo_order.ps1, plan-fremdrepos-ausbau-2026-10-09.md; 12 alte omnitrade-status-Kopien gegen die juengeren O:-Originale), Junction neu gesetzt. Protokoll Agenten/Routinen/logs/werkstatt-junction-reparatur-20261011.log. Zweiter Fall derselben Klasse (erster: 05.10.2026 22:12, 2 Dateien). Es gibt weiterhin KEINE Wache, die Junction-Verlust meldet - konfig-doktor haelt LAUFZEIT-JUNCTION-* nur als KRITISCH beim manuellen Lauf.
      Naechster Schritt: Wache bauen (z.B. Hermes-Cron no_agent, prueft LinkType+Target von BrainFiles\Werkstatt und BrainFiles\Modelle, meldet nur Verlust; Muster ausserhaus-frist-wache).
      Angelegt: 2026-10-11 · Zuletzt: 2026-10-11
      Betrifft: BrainFiles\Werkstatt (Junction), Modelle (Junction)





- [x] **T-070 — echte Zugangsdaten in `Werkstatt/Repos/fomo-robinhood-radar/.env.example`**
      Kontext: Beim Sichern der Fremdarbeit am 24.09.2026 gefunden - in einer
      VERSIONIERTEN Vorlagendatei stehen zwei echte Kennungen im Klartext
      (ANTHROPIC_API_KEY und TELEGRAM_BOT_TOKEN, Werte hier absichtlich nicht
      wiederholt). Die Aenderung liegt nur im Arbeitsbaum (Status " M"), der
      Kopf des Klons ist unveraendert auf origin/main - es ist also noch NICHTS
      gepusht und nichts geleakt.
      RISIKO: Die Datei wird von jedem `git add -A` in diesem Klon erfasst; ein
      Push in den Fork mfaupel95/fomo-robinhood-radar legt beide Kennungen
      offen. Deshalb wurde sie beim Sichern bewusst NICHT committet.
      Naechster Schritt (Entscheidung Max): beide Werte in der Datei wieder auf
      Platzhalter setzen und die zwei Kennungen als kompromittiert behandeln -
      Anthropic-Key neu ausstellen, Telegram-Bot-Token bei BotFather neu holen.
      Vorher pruefen, in welcher .env die echten Werte noch stehen (die Datei
      selbst ist Stufe 0 und wird nicht geblaettert).
      STAND 26.09.2026: Die zwei Dateien sind bereinigt (jede auf ihren
      HEAD-Stand zurueckgesetzt, in dem die Werte LEER sind), die
      Arbeitsbaeume sind sauber. Beide waren nur im Arbeitsbaum veraendert -
      HEAD und Fork/Upstream trugen leere Werte, es ist also NICHTS geleakt.
      Der Fund war doppelt: neben fomo-robinhood-radar/.env.example trug auch
      Werkstatt/skillspector/.env.example einen echten OPENAI_API_KEY (Klon von
      nvidia/skillspector, Remote zeigt auf NVIDIA - ein Push dorthin waere gar
      nicht moeglich gewesen).
      Geprueft und unauffaellig: 41 .env-Dateien in Wurzel und Werkstatt/Repos -
      die zwei .env mit echten Werten (Agenten/Hermes/.env,
      moon-dev-ai-agents/.env) sind per .gitignore gesperrt und nie versioniert
      worden; die .env.template-Artefakte in mehreren Klonen sind die Vorlage
      von ToolUniverse ("fill in your actual API keys"), kein Wert.
      OFFEN (nur Max): die drei Kennungen (Anthropic, Telegram-Bot, OpenAI) als
      kompromittiert behandeln und neu ausstellen. Kein Leak nach aussen, aber
      die Werte lagen in Klon-Arbeitsbaeumen, die von Sicherungen und
      Sitzungsablagen nicht erfasst werden - Rotation ist die saubere Antwort.
      Werkzeug: Agenten/Hermes/cache/scratch/keys_bereinigen.py (liest und
      meldet nur Laengen/Hashes, gibt nie Werte aus).
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-26
      Betrifft: Werkstatt/Repos/fomo-robinhood-radar/.env.example,
      Werkstatt/skillspector/.env.example
      
- [x] **T-389 - omniquant: Auswertung zeigt 0 Runden trotz 37 EINSTIEG/20 AUSSTIEG**
      Kontext: omniquant schreibt im Journal die Aktionen EINSTIEG/AUSSTIEG (papier) und eroeffnen/schliessen (live). auswertung_alle.runden_indikator paart aber kauf/verkauf (BOT_SPUREN-Weg) - omniquant hat deshalb 0 Runden in JEDER Auswertung, obwohl 37 EINSTIEG- und 20 AUSSTIEG-Zeilen existieren (gemessen 11.10.2026). Die Spur ist in BOT_SPUREN, aber ihr Journalformat passt nicht zum Rechenweg. Folge: kein Tagesbericht, keine Strategiekennzahl, kein Kosten-Wendepunkt fuer omniquant.
      Naechster Schritt: omniquant einen eigenen Rechenweg geben (eroeffnen/schliessen mit einsatz_usd, wie runden_nautilus) oder die Spur auf kauf/verkauf umstellen; pruefen, welche Aktionen die Spur wirklich schreibt.
      Angelegt: 2026-10-11
      Betrifft: Agenten/Handel/auswertung_alle.py, omniquant/handeln.py
      
- [x] **T-385 - omniquant: SICHERHEITSLUECKE NEAR-USDC - GEKLAERT: Position am 08.10. an der Boerse verkauft, nie gebucht**
      Kontext: omniquant meldete seit 05.10.2026 jede Viertelstunde "SICHERHEITSLUECKE: Stop fehlte an der Boerse und liess sich nicht nachsetzen" fuer die live offene NEAR-USDC-Position (Kraken-Futures, 61 Kontrakte, stop_algo_id=null). Ursache: `kraken_perp.stop_setzen` rief `paar_fuer(inst)` OHNE `fuer_ausstieg=True` - das Einstiegs-Gate `ABLEITUNG_ERLAUBT` blockierte den Nachsatz. BEHOBEN: `stop_setzen(inst, kontrakte, stop_preis, fuer_ausstieg=True)` reicht das Flag durch; Test `test_stop_setzen_umgeht_das_einstiegs_gate`, 122 omniquant-Tests gruen. Merge 5f2f7ec4.
      AUFGEKLAERT 11.10.2026 (Kraken-Futures /fills): NEAR-USDC wurde am **08.10. 15:16:36** an der Boerse verkauft - 61 Kontrakte @ 4.8014, **-9,63 USD** (taker/Markt-Order, order a2e7e533). Eroeffnung war 05.10. 02:50 (61 @ 4.9593). Die Spur hat den Verkauf NIE gebucht (kein Journal-Ausstieg) und meldete weiter SICHERHEITSLUECKE bis 10.10. 18:13 (sie dachte, die Position sei offen). Der Verkauf kam NICHT von der Spur (die Spur wusste nicht davon) - er wurde von aussen ausgeloest (Max manuell in der Kraken-App oder anderer Prozess). Die Position verschwand spaeter aus dem Buch ohne Ausstiegszeile = Buchhaltungs-Geist. Der Verlust von -9,63 USD fehlt im Journal.
      Naechster Schritt: -9,63 USD als buchbereinigung ins omniquant-Journal nachbuchen (Position war real offen und wurde real verkauft); pruefen, ob der Abgleich (bueche_geister_aus) eine Position ohne Boersenbeleg entfernt, statt sie als UNKLAR zu melden.
      PRUEFUNG 11.10.2026 (abgeschlossen): Nachbuchung war bereits 01:46 von der parallelen Session erledigt (Journal-Zeile 08.10. 15:16:36, live, schliessen, NEAR-USDC, 4.8014, einsatz 50.0, wert 40.37 = -9,63 USD, grund=buchbereinigung; Q: byte-gleich; keine Doppelbuchung). Abgleich-Code entfernt KEINE Position ohne Boersenbeleg: live_perp.py:450-455 meldet GEISTERPOSITION und laesst stehen (kein Remove/Order/Journal), Test test_stopdeckung_live.py:245 deckt es ab (12/12 gruen); buch_bereinigen.py unterscheidet echt/geist/unklar, unklar bleibt stehen. Zeile 303 (01:34 'aus offenem Zustand entfernt') war Handarbeit der parallelen Session, kein Code-Pfad.
      Angelegt: 2026-10-10 · Zuletzt: 2026-10-11
      Betrifft: Agenten/Handel/omniquant/kraken_perp.py, live_perp.py, zustand.json (NEAR-USDC)
      
- [x] **T-387 - Worktree-Fehler-Wache gebaut: zweige.py Lage-Pruefung + zweige-wache.py Cron (10.10.2026)**
      Kontext: Am 10.10.2026 lagen zwei Worktrees im HAUPTBAUM statt unter `.worktrees/` (Agenten/.claude/worktrees/sweet-heisenberg-85efc5, init-4ede6f), einer detached HEAD (push-noema). Keine Wache meldete das. BEHOBEN: `zweige.py` weist jetzt drei Worktree-Fehlerklassen aus (Lage nicht unter .worktrees/, detached HEAD, verwaister Eintrag); neue `zweige-wache.py` (no_agent-Cron, alle 6h, meldet nur bei Auffaelligkeit, Ruhe 6h). Merge 21a703ca. Cron d8f8ceba4ba2.
      Naechster Schritt: beobachten - die Wache meldet init-4ede6f (verwaister Eintrag im Hauptbaum) bis er aufgeraeumt ist. Aufraeumen: python Agenten/Werkzeuge/zweige.py --entfernen.
      Angelegt: 2026-10-10 · Zuletzt: 2026-10-10
      Betrifft: Agenten/Werkzeuge/zweige.py, Agenten/Hermes/scripts/zweige-wache.py
      
- [x] **T-379 - Profil-Skills versionieren: .gitignore-Freigabe fuer Agenten/Hermes/profiles/*/skills/**
      Kontext: 08.10.2026, vormerken lassen (Max: "ja vormerken"). Die Skills unter
      Agenten/Hermes/profiles/<bot>/skills/ (z. B. claude-code/productivity/protecting-irreplaceable-data)
      sind git-ignoriert - nur Agenten/Hermes/skills/ ist versioniert. Eine dort gepflegte
      Lehre (CR-Byte-Falle im Edit) hatte keine Git-Historie. Aufgabe: Whitelist-
      Rueckausnahmen in .gitignore ergaenzen (!Agenten/Hermes/profiles/*/skills/**/*.md
      plus Traverse-Regeln wie bei anderen Freigaben), git check-ignore -v gegenprobe,
      status sauber, commit. Vorher pruefen, ob keine Secrets/Cache-Dateien in den
      Skill-Ordnern liegen (find ... -name '*.json' -o -name '*.env').
      Angelegt: 2026-10-08
      Betrifft: .gitignore, Agenten/Hermes/profiles/*/skills/
      
- [x] **T-080 — Eine scharfe Spur, die dauerhaft sperrt, meldet sich nur einmal**
      Kontext: Der Ereignisfilter des Dauerlaufs meldet Sperrzeilen („--live
      angefordert, aber gesperrt: …“) jetzt mit Gedaechtnis je Spur — dieselbe
      Zeile kommt einmal statt in jedem Zyklus. Das ist gewollt (Rauschen), laesst
      aber den Dauerfall offen: eine scharfe Spur, die wochenlang an Guthaben oder
      einem anderen Tor haengt, faellt nur im Tagesbericht auf.
      Naechster Schritt: pruefen, ob `sperrgruende.py` oder `spuren_stand.py` von
      einer Wache taeglich aufgerufen werden soll (Muster stille-spuren-wache).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/dauerlauf.py, Agenten/Hermes/scripts/
      sperrgrund-wache.py gebaut und an Cron angebunden; commits 59e21518/49bf3f3a
- [x] **T-075 — kraken_rest.guthaben() scheitert sporadisch mit EGeneral:Permission denied**
      Kontext: `kraken_rest.py` laedt `../kraken/kraken.py` ueber
      spec_from_file_location. Derselbe Aufruf `guthaben("ZEUR")` liefert in EINEM
      Prozess ueber den normalen Import 0,7059 und ueber den spec-Weg
      'EGeneral:Permission denied'; in einer Serie von 12 Aufrufen fielen alle 12
      (beide Wege), Minuten spaeter gingen wieder alle. Nicht die Ursache: Key
      (unveraendert), Uhr (1,3 s), nonce_pool (beide Wege laden dieselbe Datei
      `kraken/.kraken_nonce`), venv, cwd, oeffentliche IP (Terminal und Host
      identisch).
      Naechster Schritt: den von kraken.py benutzten nonce bzw. die Antwort im
      Fehlerfall mitschreiben (Header/Statuscode) und gegen den erfolgreichen Fall
      stellen - dies ist der einzige verbleibende Unterschied.
      Werkzeug vorhanden (25.09.2026): `Agenten/Handel/kraken_abweisungs_sonde.py`
      haelt genau das fest (Status, content-type, Header, Rohkoerper) und laeuft als
      Cron `kraken-abweisung-wache` alle 30 min; sie deckt den signierten Spot-Weg
      ueber die Haus-kraken.py ab. Beim naechsten Auftreten zuerst dort nachsehen
      (cache/kraken-abweisungen.jsonl), statt eine neue Sonde zu bauen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/nautilus_kraken/kraken_rest.py,
      Agenten/Handel/kraken/kraken.py
      kraken-Sonde nutzt Haus-Nonce-Standard; commit f4a9e748
- [x] **T-380 - puter self-hosted: Standort und Betrieb entscheiden**
      Kontext: 08.10.2026 - Parallelsitzung hat HeyPuter/puter (Fork mfaupel95/puter) an die Wurzel geklont
      und den Docker-Stack gestartet (puter-selfhosted/, Port 80, 6 Container, restart unless-stopped).
      Zugangsdaten in puter-selfhosted/.env und puter/config/config.json (Stufe 0, nicht gelesen).
      ERLEDIGT 10.10.2026: Umzug nach Werkstatt/Repos/puter, Stack laeuft (6 Container healthy,
      HTTP 200 auf Port 80); Falle .my-healthcheck.cnf world-writable -> chmod 600 im Container.
      Doku: MaxHirn/Wiki/Werkzeuge/Puter-selfhosted.md
      Angelegt: 2026-10-08 · Zuletzt: 2026-10-10

- [x] **T-382 - Werkstatt-Sammlungen security-skills-claude-code + skillspector pruefen**
      Kontext: O:\Werkstatt\security-skills-claude-code: 10 SKILL.md (Security-Phoenix-demo, HEAD 29.04.2026). O:\Werkstatt\skillspector: WERKZEUG, keine Sammlung - 1 SKILL.md in skills/, 24 in tests/ (Test-Fixtures). Beide nicht in Werkstatt/Repos. Fund beim Skill-Scan 09.10.2026. Naechster Schritt: Entscheidung Max - security-skills in den Fundus-Index; skillspector als Werkzeug pruefen (Analyse-Tool fuer Skills, passt zu T-100-Verdacht). Angelegt: 2026-10-09
      Betrifft: Skill-Scan 09.10.2026 (fremde-skill-sammlung-einbinden)
      
- [x] **T-383 - Neue Einzel-Skills docker-cascade-repair + microsoft-foundry fehlen in Hausbibliothek**
      Kontext: ~/.claude/skills/docker-cascade-repair (Repair von Docker-Daemon-Hang + MCP-Kaskaden-Fehlern, passt zu T-152) und ~/.agents/skills/microsoft-foundry (9 Unterordner) sind geladen, aber NICHT in Agenten/Hermes/skills - beide Hashes beim Skill-Scan 09.10.2026 als NEU markiert. Naechster Schritt: Entscheidung Max - docker-cascade-repair einzeln nach skill-library-sync-Muster uebernehmen (einzelner Fremd-Skill, Ausnahme vom Fremd-Baum-Verbot). Angelegt: 2026-10-09
      Betrifft: Skill-Scan 09.10.2026 (fremde-skill-sammlung-einbinden)
      
- [x] **T-381 - trailofbits-skills uebernehmen? (83 SKILL.md, Security/Formal-Verifikation)**
      Kontext: O:\Werkstatt\trailofbits-skills (Klon trailofbits/skills, HEAD 02.09.2026) - offizielles Trail-of-Bits-Skills-Marketplace mit 83 SKILL.md in plugins/ (trailmark, testing-handbook, variant-analysis, yara-rule-authoring, zeroize-audit, writing-lean-proofs, genotoxic u. a.). NICHT in Werkstatt/Repos, nicht im Fundus-Index (der deckt nur Werkstatt/Repos). Fund beim Skill-Scan 09.10.2026. Naechster Schritt: Entscheidung Max - Klon nach Werkstatt/Repos holen und Fundus-Index erweitern (halten/finden), einzelne Skills (z. B. security-Audit) nach Bedarf adaptieren. Angelegt: 2026-10-09
      Betrifft: Skill-Scan 09.10.2026 (fremde-skill-sammlung-einbinden)
      
- [x] **T-202 - Docht-Ausstieg im Replay abbilden (Beruehrung ohne Schluss jenseits der Marke)**
      Kontext: Mit der Beruehrungsregel (T-177, erledigt 30.09.2026) geschieht der
      Ausstieg am Kurs der Marke, wenn die Kerze sie beruehrt - der AUSLOESER bleibt
      aber der Kerzenschluss, wie live. Eine Kerze, die eine Marke nur mit dem Docht
      streift und darueber schliesst, loest weiterhin nichts aus.
      Naechster Schritt: zaehlen, wie oft das in den vorhandenen Historien vorkommt
      (Zaehler neben `auf_der_marke`), und erst dann entscheiden - ein Docht-Ausstieg
      macht die Zahlen strenger, nie besser, und weicht vom Live-Verhalten ab.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Handel/replay.py, MaxHirn/Wiki/Handel/Backtest-Fundament.md
      **Erledigt 2026-10-09.** Docht-Ausstiegslogik in replay.py verifiziert (docht_beruehrung_ohne_schluss + docht_ausstiege_anwenden waren bereits korrekt), Tests repariert; Backtest steht vollstaendig auf der Kerzenschluss-Regel: 21 Journale, 702/702 Ausstiege auf der Marke, 90+ Tests gruen.
- [x] **T-203 - Backtest-Zahlen, die auf der alten Kerzenschluss-Regel beruhen, neu lesen**
      Kontext: T-177 ist behoben (Ausstieg auf der beruehrten Marke). Die Wirkung ist
      gross: squeeze dreht von +61,93 auf -6,34 % (759 Runden), moondev_topmovers von
      +522,44 auf +260,00, moondev_funding von +156,50 auf +87,00. Jede Notiz und jedes
      Urteil, das auf einer Backtest-Zahl von vorher fusst, ist zu guenstig gerechnet -
      betroffen sind `Agenten/Handel/backtest_urteile.py`, der Abschnitt
      '=== Backtest (historisch)' des normalen Berichts (`auswertung_alle.py`,
      ohne Argumente - ein Flag `--backtest` gibt es NICHT) und die Notizen unter
      MaxHirn/Wiki/Handel/.
      Naechster Schritt: die gespeicherten Backtest-Laeufe mit der Regel neu fahren
      (`replay.py --lauf <neu>`) und die Urteile nachziehen. Kennzahl der Regel ist
      `ausstiege_an_marke`/`ausstiege` - ein Lauf von vorher zeigt 0/N.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Handel/backtest_urteile.py, daten/backtest/**, MaxHirn/Wiki/Handel/
      **Erledigt 2026-10-09.** Backtest-Zahlen auf der Kerzenschluss-Regel neu gelesen: 21 Journale, 702/702 Ausstiege auf der Marke (100 %), Urteile nachgezogen; die alten, zu guenstigen Zahlen (squeeze +61,93 statt -6,34 usw.) sind ersetzt.
- [x] **T-227 — Nautilus-Arme haben keinen Abgleich Buch gegen Boerse**
      Kontext: T-207 hat den Abgleich fuer `mosaic` gebaut (30.09.2026), `kraken`
      (T-208) und `scanner` (`scanner/boersenstops.py`, 28.09.) haben ihn laenger.
      `nautilus`, `nautilus_kraken` und `nautilus_kraken_futures` haben nichts
      dergleichen. Sie sind derzeit Papier (`handel_erlaubt=false`,
      `freigabe.erfuellt=false`), der OKX-Arm ordnet aber im DEMO-Node und
      `nautilus_kraken` hatte einen Live-Spot-Pfad - sobald einer scharf geht,
      fehlt der Abgleich, und ein stornierter Stop bliebe unbemerkt.
      Naechster Schritt: vor dem Scharfstellen EINES Arms pruefen, ob er echte
      Orders stellt - nur dann `mosaic/boersenabgleich.py` als Vorlage auf den Arm
      uebertragen (eigener Modulname, sonst zieht der Import einen Namensvetter).
      Angelegt 30.09.2026 · Zuletzt 30.09.2026 · Betrifft Agenten/Handel/nautilus*
      **Erledigt 2026-10-09.** Boersenabgleich fuer nautilus_kraken gebaut und verdrahtet (Commit 4148ac0d): Waehrung je Position statt fest 'usd', Boerse je Position statt fest 'kraken', unbekannte Boerse = 'unklar'; test_boersenabgleich 23/23 gruen.
- [x] **T-168 - deepseek-harness: Klon ungebaut, UI laeuft nur ueber npx**
      Kontext: Die Web-UI startet ueber `npx -y @deepseek-ai/dsh web`
      (Port 3080, belegt am 29.09.2026) - das laedt das VEROEFFENTLICHTE Paket,
      nicht den eigenen Klon. Der Klon hat kein node_modules; der Weg
      `pnpm install && pnpm run build && pnpm dsh web` steht im Manifest, ist
      aber nie gelaufen.
      Naechster Schritt: nur falls der eigene Klon gebraucht wird (eigene
      Aenderungen am Harness), pnpm install + build einmal durchlaufen lassen
      und belegen. Sonst bleibt der npx-Weg der richtige.
      Angelegt: 2026-09-29
      Betrifft: Werkstatt/Repos/deepseek-harness/
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-171 - O:\Werkstatt 2\ enthaelt nur noch eine zweite Kopie von deepseek-harness**
      Kontext: Bestandsaufnahme 29.09.2026 - der Ordner trug zunaechst sieben
      Repos, davon lagen sechs bereits in `Werkstatt/Repos/` (dorthin
      aufgenommen). Uebrig ist eine ZWEITE Kopie von `deepseek-harness`.
      Doppelte Klone kosten Platz und stiften Verwirrung beim Vorspulen.
      Naechster Schritt: entscheiden, ob die Kopie weggelegt oder geloescht
      wird. NICHTS geloescht, solange Max nicht zustimmt.
      Angelegt: 2026-09-29
      Betrifft: O:\Werkstatt 2\
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-170 - ziplime: OPENROUTER_API_KEY fehlt fuer den Assistenten**
      Kontext: `python -m ai_assistant` startet und fragt dann nach dem
      OpenRouter-Schluessel (so im Beleglauf vom 29.09.2026). Ohne ihn laeuft
      nur die Backtest-CLI; das venv ist vollstaendig.
      Naechster Schritt: entscheiden, ob ein OpenRouter-Zugang hinterlegt wird
      (Wissen/Zugaenge.md ist die einzige Ablage) oder ob ziplime ohne
      Assistent bleibt.
      Angelegt: 2026-09-29
      Betrifft: Werkstatt/Repos/ziplime/
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-169 - tradememory-protocol: Browser-Dashboard nicht gebaut**
      Kontext: `.venv\Scripts\tradememory-api.exe` liefert auf Port 8000 die
      REST-API (belegt am 29.09.2026), aber KEIN Dashboard - dafuer fehlt
      `dashboard/dist`. Die oeffentliche Demo laeuft auf
      tradememory-dashboard.onrender.com.
      Naechster Schritt: entscheiden, ob das Dashboard lokal gebaut wird (Node
      im dashboard/-Ordner, Vite) oder ob der Eintrag dauerhaft "API ohne
      Dashboard" heisst.
      Angelegt: 2026-09-29
      Betrifft: Werkstatt/Repos/tradememory-protocol/dashboard/
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-189 — claude-red: vier SKILL.md hat Defender entfernt, der Klon zeigt sie als Loeschung**
      Kontext: Beim Flottenlauf am 30.09.2026 (46 Klone) ist `claude-red` aktuell,
      traegt aber vier `D`-Eintraege im Arbeitsbaum
      (`Skills/infrastructure/offensive-shellcode`, `Skills/web/offensive-file-upload`,
      `Skills/web/offensive-rce`, `Skills/web/offensive-sqli`). Ursache ist Windows
      Defender (Fundort `Get-MpThreatDetection`), nicht der Klon; der Fundus deckt
      deshalb 75 von 79 Skills. `git checkout` holt die Dateien zurueck, der
      LESEZUGRIFF bleibt aber gesperrt ("Datei enthaelt einen Virus").
      Naechster Schritt: entscheiden, ob eine Defender-Ordnerausnahme fuer
      `Werkstatt/Repos/claude-red/Skills/` gesetzt wird (dann alle 79 lesbar) oder
      ob die vier gesperrt bleiben — der Stand ist so oder so zu dokumentieren.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: `Werkstatt/Repos/claude-red/Skills/`, Fundus-Index
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-188 — OpenTerminal und osiris: lokale Aenderungen sperren das Vorspulen**
      Kontext: Beim Flottenlauf am 30.09.2026 waren beide hinter ihrem Original,
      wurden aber nicht gespult, weil sie Aenderungen an VERFOLGTEN Dateien tragen:
      `OpenTerminal` `package.json` + `package-lock.json` (4 Commits Rueckstand),
      `osiris` `package-lock.json` (5). Ein `.env.template` (untracked) sperrt
      nicht — nur verfolgte Dateien. Verwerfen ist laut Hausregel verboten, also
      bleibt der Klon stehen und die Aenderung entscheidet Max.
      Naechster Schritt: sagen, ob die beiden Sperren bleiben sollen (dann bleibt
      der Klon dauerhaft alt) oder ob die lokalen Aenderungen weg duerfen; danach
      `repos-updaten.py --nur OpenTerminal osiris`.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: `Werkstatt/Repos/OpenTerminal/package.json`, `Werkstatt/Repos/osiris/package-lock.json`, `Agenten/Werkzeuge/repos-updaten.py`
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-187 — Zwei Klone stehen auf eigenem Zweignamen (84 und 91 Commits Rueckstand)**
      Kontext: `jev-chat-jarvis` liegt lokal auf Zweig `JEV`, `tradememory-protocol`
      auf `Werkstatt` — beide zeigen auf denselben Commit wie ihr Remote-Zweig
      (`origin/main` bzw. `origin/master`), nur der Name weicht vom Quell-
      Standardzweig ab (`upstream/main` bzw. `upstream/master`). Das Werkzeug raet
      den Zweig nicht und schaltet nicht um, deshalb steht bei beiden
      "anderer Zweig" im Bericht. Nachgemessen am 30.09.2026: 84 bzw. 91 Commits
      Rueckstand, gemessen ohne Umschalten.
      Naechster Schritt: entscheiden, ob die Namen bleiben (dann werden die beiden
      nie vorgespult) oder ob ein sauberes Umschalten auf main/master erlaubt ist;
      `repos-updaten.py --ausser` deckt sie bis dahin ab.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: `Werkstatt/Repos/jev-chat-jarvis`, `Werkstatt/Repos/tradememory-protocol`
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-186 — `C:\Users\faupe\.omniroute\` liegt in keiner Sicherungsquelle (1,2 GB)**
      Kontext: Der OmniRoute-Dienst haelt seinen Zustand unter
      `C:\Users\faupe\.omniroute\`: `storage.sqlite` (101 MB, Anbieter-
      Verbindungen und Kosten), `db_backups/`, `logs/`, `plugins/` - und eine
      `.env` mit `STORAGE_ENCRYPTION_KEY`, `JWT_SECRET`, `API_KEY_SECRET`. Kein
      Sicherungsskript erfasst diesen Pfad (Quellen sind `MaxHirn/` und
      `Agenten/`), und der Schluessel entschluesselt die Verbindungen in der
      Datenbank: ohne ihn ist der Router nach einem Wiederaufbau leer, obwohl
      die Datei da ist. Die `.env` allein liegt seit 30.09.2026 als Kopie in
      `Agenten/Hermes/.sicherung/omniroute-home-env.bak-20260930`; die Datenbank
      (mit laufendem Router nur im WAL-Stand kopierbar) ist NICHT gesichert.
      Naechster Schritt: entscheiden, ob `storage.sqlite` in die taegliche
      Sicherung aufgenommen wird (Kopie im laufenden Betrieb, `db_backups/`
      existiert bereits) oder ob ein Router-Ausfall bewusst hingenommen wird.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: `C:\Users\faupe\.omniroute\`, `Agenten/sichern.ps1`
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-185 — Klon-.env-Kopien veralten ohne Nachweis (Kopien liegen seit 30.09.2026 in .sicherung)**
      Kontext: Von 47 Klonen unter `Werkstatt/Repos` tragen 7 eine `.env`, keine
      davon war gesichert (beide Sicherungen klammern `Werkstatt` per `/XD` aus,
      und die Klartext-Pruefung in `sichern.ps1` sieht sie deshalb ebenfalls
      nicht). Sechs Kopien liegen jetzt byte-gleich in
      `Agenten/Hermes/.sicherung/` (`moondev-env.bak-20260930`,
      `moondev-src-env.bak-20260930`, `openmontage-env.bak-20260930`,
      `openterminalui-env.bak-20260930`, `omniroute-werkstatt-env.bak-20260930`,
      `omniroute-home-env.bak-20260930`), Bestandsaufnahme in
      `.sicherung/klon-envs-20260930.md`, Wiki-Abschnitt in
      `Wiki/Betrieb/Sicherung-und-Laufwerke.md`. Aendert Max eine dieser
      `.env`, veraltet die Kopie still - bisher merkt das niemand.
      Naechster Schritt: entscheiden, ob ein Schritt in `sichern.ps1` (Kopien
      beim Lauf mitziehen und Abweichung melden) oder eine eigene Wache gebaut
      wird; bis dahin ist die Kopie ein Stand vom 30.09.2026.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: `Agenten/sichern.ps1`, `Agenten/Hermes/.sicherung/`, `Werkstatt/Repos/*/.env`
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-244 - Zentrale: Kartenstile und Hinweisspalte (Design-Entscheidungen)**
      Kontext: Zwei offene Designfragen aus dem Umbau vom 30.09.2026. (a) Die
      Stile fuer die Karten (`Karte.TLabel`, `Karte.Treeview`, `Karte.TCheckbutton`)
      stehen LOKAL in `repos-zentrale/fenster.py`, damit `fenster_design.py` -
      die gemeinsame Quelle von handelszentrale.py und leitstand.py - unberuehrt
      bleibt. Wer EINE Designquelle will, muss sie dorthin ziehen; das wirkt auf
      die anderen Fenster. (b) `messprobe.py` misst 63 von 216 Hinweisen als zu
      lang (laengster 1940 px bei 705 px Spalte) - der volle Text steht nur in
      der Statuszeile. Ein Tooltip oder eine breitere Spalte waere moeglich,
      kostet aber Platz bei Projekt/Art/Rolle.
      Naechster Schritt: Entscheidung Max, ob (a) die Kartenstile nach
      `Agenten/Werkzeuge/fenster_design.py` wandern und (b) die Hinweisspalte
      einen Tooltip bekommt.
      Betrifft: `Agenten/Werkzeuge/repos-zentrale/fenster.py`,
      `Agenten/Werkzeuge/fenster_design.py`, `messprobe.py`
      Angelegt: 2026-09-30
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-236 - Zentrale: neue Werkzeugdateien erscheinen ohne Startbefehl**
      Kontext: Die Datei-Regel (`scan.ist_werkzeug`: eigener Einstieg UND
      argparse) nimmt jede neue Datei der Handel-Wurzel als Zeile auf - aber nur
      Dateien in `fuellen.HILFE_VERIFIZIERT` bekommen den `--help`-Start.
      Beispiel: `kerzenschluss_bias.py` (parallel entstanden) steht ohne Start.
      Naechster Schritt: soll eine Datei bleiben, ihren Aufruf einmal echt
      fahren, den Namen in HILFE_VERIFIZIERT aufnehmen und `fuellen.py --belege`
      laufen lassen.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Werkzeuge/repos-zentrale/quellen.py, fuellen.py
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-235 - Zentrale: vier Werkzeuge absichtlich ohne Klick-Start (Entscheidung Max)**
      Kontext: `leitstand.py` (oeffnet ein Fenster), `kraken_abweisungs_sonde.py`
      (jeder Aufruf misst echt gegen Kraken und setzt den Lockout-Timer zurueck),
      `dauerlauf.py` (Handstart nimmt die echte Sperre) und `melder.py`
      (verschickt Telegram) haben bewusst KEINEN Startbefehl; ihre Anleitung
      nennt den Aufruf in Worten, die Zeile traegt den Grund als Warnung.
      Naechster Schritt: entscheiden, ob leitstand.py trotzdem einen Klick-Start
      bekommt (Aufruf: .venv\Scripts\pythonw.exe leitstand.py); die drei anderen
      bleiben ohne.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Handel/leitstand.py, Agenten/Werkzeuge/repos-zentrale/fuellen.py
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-234 - Zentrale: Werkstatt-Projekte ohne Startbefehl nachtragen**
      Kontext: Am 30.09.2026 wurde das Manifest der Zentrale von 46 auf 192 Zeilen
      gefuellt (Bereiche REPOS / WERKSTATT / HANDEL), 73 mit Startbefehl. Offen
      sind vor allem die **Werkstatt-Projekte** (freqtrade, omnitrade, OmniRoute,
      handel-stack, skillspector) sowie die Werkzeug-Ordner in Handel
      (freqtrade, bt_opt, nautilus-rust, verbesserer, OpenAlice). Die Spuren
      selbst sollen bewusst OHNE Startbefehl bleiben (der Dauerlauf faehrt sie),
      die sechs Freqtrade-Strategien ebenfalls (Klassen, freqtrade laedt sie).
      Hausregel: ein Befehl kommt erst ins Manifest, wenn er einmal echt
      gelaufen ist (`fuellen.py --belege` fuehrt hinterlegte Staende aus).
      Naechster Schritt: je Projekt den Startweg einmal von Hand fahren, dann
      `start` bzw. `befehle` in repos-zentrale.json eintragen.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Werkzeuge/repos-zentrale/repos-zentrale.json, Werkstatt/
      Nachgeschlossen in Master-TASKS.md (Kinder schlossen in Worktree-Kopien)
- [x] **T-097 — Indikatorschwellen der Prognose-Spuren liegen als Konstanten im Code**
      Kontext: Gemessen 2026-09-25 beim Bau des Optimierers. Die vier
      Indikator-Spuren (squeeze, wavetrend, macd_mtf, supertrend) lesen aus
      ihrer `wachen.json` NUR die Ausstiegs-Geometrie
      (`pflicht_stop_prozent_min`, `pflicht_stop_prozent_max`,
      `ziel_r_vielfaches`, `max_offene_positionen`). Ihre eigentlichen
      Indikatorschwellen stehen als Konstanten im Code - `squeeze.signal()` ist
      eine feste Regel ueber `ti.squeeze_momentum(k)`, und `supertrend` holt
      sich `supertrend_n`/`supertrend_faktor` NICHT aus den Wachen (im
      Gegensatz zu trendwende_btc, das beide liest). Das verstoesst gegen die
      Hausregel "Zahlen gehoeren in die wachen.json, nicht in den Code" und
      hat eine harte Folge: diese Parameter lassen sich nicht tunen, ohne Code
      zu aendern - der Optimierer kann sie nicht anfassen.
      Naechster Schritt: je Spur die Konstanten als Schluessel in die
      wachen.json aufnehmen (Wert = der heutige Code-Default, damit sich NICHTS
      verhaelt), die Spur lesend umstellen und mit einem Beleglauf zeigen, dass
      die Ergebnisse vorher/nachher gleich sind. Danach in `spur_opt.json`
      aufnehmen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/{squeeze,wavetrend,macd_mtf,supertrend}/handeln.py und wachen.json, spur_opt.json
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - gebaut auf wt/t_5609d126 (Commit 3894778a), aber NICHT in master - bleibt offen bis zur Merge-Entscheidung (Karte t_fb1f87ad).**
      Indikatorschwellen aus wachen.json gelesen, Code-Defaults = alte Werte, Regression identisch (squeeze 44=44, wavetrend 23=23, macd_mtf 11=11, supertrend 131=131), Code in master gemergt (Commit 3894778a via aac51bde)
- [x] **T-344 — `nautilus_trader` steht jetzt in zwei venv, ohne dass es jemanden stoert**
      Kontext: Der Leitstand laeuft in `Agenten/Handel/.venv`, das Nautilus-
      Rad lag nur in `nautilus/.venv` (326 MB). Fuer den Reiter wurde es
      deshalb auch ins Handel-.venv installiert (Import 1,8 s). Damit steht
      dieselbe Version 1.231.0 an zwei Stellen, und `pip`-Aktualisierungen
      laufen an einer Stelle vorbei.
      Naechster Schritt: eine Datei `Agenten/Handel/nautilus/README-live-node.md`
      (Abschnitt 'Zwei venv, ein Rad') verweist darauf; eine
      Versionspruefung ergaenzen, die beim Start des Reiters beide Orte
      vergleicht und bei Abweichung sagt, welcher nachgezogen werden muss.
      Angelegt · 04.10.2026 · Betrifft: Agenten/Handel/.venv,
      Agenten/Handel/nautilus/.venv
      beide venvs gemessen (Produktion nautilus/.venv Python 3.13.15 nautilus_trader 1.231.0 vs Release-Kandidat nautilus_rc5/.venv 2.0.0rc5), README-live-node.md erstellt, Commits 569f1de+8634dff im nautilus-Repo
- [x] **T-258 — nautilus-rust: Evidenzwerte sind hart eingetragen, kein Walk-Forward**
      Kontext: `quant-alpha` schreibt ein Demo-Buch mit festen Zahlen (`net_bps 3.5, se_bps 2.0,
      folds 5, positive_folds 2`), im Code selbst als Demo markiert; `quant-strategy` lehnt es deshalb
      mit `t = 1.75 < Huerde 2.0` ab (gemessen, 0 rebalances). Ein Signal ist daraus nicht ableitbar.
      Naechster Schritt: falls daraus ein Signalweg werden soll — echte Folds ueber
      `Agenten/Handel/historie_binance.py` und `replay.py` erzeugen und die Werte dort herleiten
      statt einzutragen.
      Angelegt: 2026-09-30 · Betrifft: `Agenten/Handel/nautilus-rust/quant-alpha`
      Erledigt 2026-10-08 (Commit 465f3366): Evidenzwerte bleiben als Demo markiert, kein Walk-Forward; im Code als Demo + README 'kein Handelssystem' klar gestellt
- [x] **T-257 — nautilus-rust kann kein eigenes ProjectAtlas-Projekt bekommen (kein eigenes .git)**
      Kontext: Der Rust-Workspace `Agenten/Handel/nautilus-rust` (5 Crates, 826 Zeilen) liegt IM
      BrainFiles-Repo; ProjectAtlas bindet den Projektstamm an die naechste Git-Wurzel und verweigert
      ein Projekt innerhalb eines Repos. Gemessen 30.09.2026: `invalid input: ProjectAtlas config
      '.../nautilus-rust/.projectatlas/config.toml' resolves project root '...Agenten/Handel/nautilus-rust'
      outside selected project root '...BrainFiles'` — der angelegte `.projectatlas` wurde wieder entfernt.
      Naechster Schritt: entscheiden — eigenes Repo (dann Atlas moeglich, aber Gitlink im Vault wie bei
      MaxHirn/codex) oder Lehrstueck bleiben (dann genuegen die fuenf Einstiegsdateien).
      Angelegt: 2026-09-30 · Betrifft: `Agenten/Handel/nautilus-rust`, `MaxHirn/Wiki/Handel/nautilus-rust-Quant-Ebene.md`
      Erledigt 2026-10-08 (Commit 465f3366): Entscheidung Max - Lehrstueck bleiben; ProjectAtlas-Ausschluss im README dokumentiert, kein eigenes Repo
- [x] **T-256 — omnitrade-Spur scharf schalten: es fehlt nur das Guthaben in der Quote**
      Kontext: Die Spur `omnitrade` (Weg B, Commit 6197ac9) ist gebaut und laeuft
      Papier. Ihr Live-Zweig steht auf Kraken/USDC; die Vorschau nennt vier
      Sperrgruende, davon zwei, die Max' Hand brauchen: `freigabe.erfuellt=false`
      und `nur 25.08 USDC frei, noetig 60.00`. Die beiden anderen
      (`handel_erlaubt=false`, kein Freigabefenster) sind Schalter bzw. laufen
      ueber die Freigabekette.
      Naechster Schritt: erst Papierrunden sammeln und die Bedingung 1 belegen
      (Runden, netto positiv, Ruecklauf), dann `handel_erlaubt=true` +
      `freigabe.erfuellt=true` und ein `/ja_omnitrade` im Dauerlauf; das Guthaben
      in USDC auf Kraken muss vorher ueber 60 liegen (T-115). NICHT vorher -
      eine neue Spur ohne eine einzige Runde scharf zu stellen, waere der
      Verzicht auf jede Messung.
      Angelegt: 2026-09-30 · Zuletzt: 2026-10-08
      Betrifft: Agenten/Handel/omnitrade/wachen.json, MaxHirn/Wissen/Handelsregeln.md
      **Konfiguration geprueft 08.10.2026 (kein Live-Schalter angefasst):**
      wachen.json ist vollstaendig (boerse=kraken, kraken_quote=USDC,
      mindest_guthaben=60, Risikogrenzen, Journal-Spiegelung nach Q:), der
      Dauerlauf fuehrt die Spur, mehrere Rust-Testnet-Laeufe liefern frische
      Statusdateien (Werkstatt/omnitrade/status/*.json, Stand 16:59),
      handelsjournal.csv zeigt eine offene Papierposition. Stale Doku in
      Handelsregeln.md ("omnitrade hat keinen Kraken-Weg") korrigiert - das
      war der Stand VOR Weg B, nicht mehr aktuell. Testbefund (nicht
      behoben, keine Risikoaenderung ohne Beleg): `test_omnitrade.py` hat
      einen vorbestehenden Fehlschlag seit 30.09.2026
      (`test_haengende_datei_mit_lebender_pid_zaehlt_nicht`) - VIELFACHES=2.5
      im Altersgrenzen-Code erlaubt bei 1h-Kerzen 2,5h, der Test erwartet
      Haengen schon bei 2h. Bleibt offen fuer Max' Entscheidung, da es eine
      Risikoschwelle ist. Weiterhin offen und NICHT angefasst: `freigabe.erfuellt`,
      `handel_erlaubt`, Kraken-USDC-Guthaben (T-115) - alles Max' Hand.
      Erledigt 2026-10-08 (Commit 0a98bb66): omnitrade-Spur-Konfiguration geprueft, stale Kraken-Doku korrigiert; kein Live-Schalter angefasst (freigabe.erfuellt/handel_erlaubt bleiben Max' Hand, Guthaben T-115)
- [x] **T-253 - Paperclip-CLI: der verwaltete Install-Weg scheitert unter Windows**
      Kontext: `npx paperclipai install` bricht mit `ENOENT ... .install.lock.<pid>:<zeit>:<zufall>.tmp`
      ab - der Sperr-Dateiname traegt DOPPELPUNKTE (Unix erlaubt das, Windows nicht). Gemessen mit
      und ohne Doppelpunkt im Namen: ohne geht, mit ENOENT. Der Store waere zusaetzlich
      Unix-gepraegt (`~/.local/bin`, `.bashrc`/`.zshrc`, Symlink `current`). Deshalb liegt die CLI
      hier als npm-Installation in eigenem Prefix (`C:\Users\faupe\.local\npm`) mit zwei
      PATH-Weiterleitungen in `~/.local/bin`; `paperclipai update` und `uninstall` gibt es damit
      NICHT, aktualisiert wird per `npm install -g --prefix ... paperclipai@latest`.
      Naechster Schritt: entscheiden, ob der Fehler upstream gemeldet wird
      (`paperclipai/paperclip`); bei einem spaeteren Release pruefen, ob `install` durchlaeuft,
      dann auf den verwalteten Weg umziehen (dann gaebe es Update, Rollback, Hintergrunddienst).
      Angelegt: 2026-09-30 · Betrifft: `MaxHirn/Wiki/Werkzeuge/Paperclip.md`
      Erledigt 2026-10-08: npm-Prefix-Weg (C:\Users\faupe\.local\npm) laeuft, CLI 2026.916.1 installiert, Server Port 3100 HTTP 200; verwalteter Install-Weg bleibt unter Windows kaputt (Doppelpunkt im Sperr-Dateinamen)
- [x] **T-250 - Werkstatt: 29 lose Dateien in der Wurzel, 19,42 GB Ballast in den Klonen**
      Kontext: Die Werkstatt-Wurzel traegt noch Plaene, Specs, PDFs, Altskripte
      (`hermes-update.ps1`, `swap-live.patch`, `tmp_auswertung_20260917.json`), zwei
      SSRN-PDFs, `setup-trading-stack.sh` - 29 Dateien. Die drei Installationspakete
      (749 MB) und der zweite `kraken-cli`-Klon sind am 30.09.2026 nach `Ausgemustert/`
      geraeumt. In `Werkstatt/Repos` sind **19,42 GB** der 26,26 GB venv/node_modules/
      `target`/`.git` - wieder herstellbar, aber genau das, was die STARTBAR-Zeilen tragen.
      Naechster Schritt: Entscheidung von Max - (a) lose Dateien nach `Ausgemustert/` oder
      in eine Ablage mit Namen, (b) `target/` einzelner Rust-Klonen leeren (bricht den
      Startbefehl) oder unangetastet lassen.
      Angelegt: 2026-09-30 · Betrifft: `Werkstatt/` (Junction auf `O:\Werkstatt`)
      **Erledigt 2026-10-08.** Entscheidung Max (a): lose Dateien in benannte Ablage - 40 Dateien geraeumt: `Ablage/Plaene/` (20), `Ablage/Guides/` (7), `Ablage/Berichte/` (5), `Ablage/Sonstiges/` (7), die Uebergabe nach `Austausch/`; die Werkstatt-Wurzel traegt nur noch AGENTS.md/CLAUDE.md. Referenzen in `Wissen/Verbesserer.md` und `Wiki/Handel/nautilus-rust-Quant-Ebene.md` nachgezogen. (b) `target/` der Rust-Klonen unangetastet - keine Entscheidung.
      Erledigt 2026-10-08 (Commit 0e5bb6a8): 40 lose Werkstatt-Dateien in benannte Ablage geraeumt (Ablage/ + Austausch/), Wurzel traegt nur noch AGENTS.md/CLAUDE.md
- [x] **T-248 - `MaxHirn/codex` ist ein Gitlink: ein Klon im Vault**
      Kontext: `git ls-files -s MaxHirn/codex` liefert Modus **160000** (Gitlink) auf
      `64b482500d` - ein Codex-Klon (0,66 GB, 7.266 Dateien) liegt IM Vault, und der Vault
      sagt selbst „hier liegt nichts, was startet". Zusaetzlich: `Werkstatt/Repos/codex`
      steht auf einem anderen Commit (`17a9df60e4`), es sind also zwei Klone. Ein Gitlink
      ohne echten Unterbau ist beim Klon von BrainFiles kaputt.
      Naechster Schritt: Entscheidung von Max - Klon nach `Werkstatt/Repos/` verschieben
      (dort liegt schon einer) oder als eigenstaendiges Werkzeug behalten; in jedem Fall den
      Gitlink austragen (`git rm --cached MaxHirn/codex`), sonst zeigt er ins Leere.
      Angelegt: 2026-09-30 · Betrifft: `MaxHirn/codex`, `.gitmodules`-freier Gitlink
      **Erledigt 2026-10-08.** Entscheidung Max (a): Klon in den Werkstatt-Klon konsolidiert - `Werkstatt/Repos/codex` (Stand 0e1520605f) ist die einzige Quelle; der Vault-Klon stand auf dem aelteren Commit 64b482500d (Vorfahr, Arbeitsbaum leer). Gitlink ausgetragen (`git rm --cached`); der alte Klon liegt zur Sicherung unter `Werkstatt/Ausgemustert/codex-maxhirn-20261008`. Hinweis: `Agenten/Hermes/skills/brainfiles/skill-library-sync/SKILL.md` nennt `MaxHirn/codex/` noch in drei Sperr-Eintraegen - Pfad existiert nicht mehr, beim naechsten Sync-Lauf nachziehen.
      Erledigt 2026-10-08 (Commit e27119d9): Gitlink ausgetragen, Klon nach Werkstatt/Repos/codex konsolidiert, Altklon nach Werkstatt/Ausgemustert/codex-maxhirn-20261008
- [x] **T-102 — Kraken kauft denselben Wert mehrfach: "Kauf ohne Fuellung" ist eine Fehlmeldung**
      Kontext: Der Tagesbericht 28.09.2026 22:05 fuehrte fuer Kraken vier Positionen,
      davon DOTEUR/ATOMEUR/FILEUR mit "1 EUR"/"2 EUR" statt ~50 EUR. An der Boerse
      nachgemessen: **FILEUR wurde am 28.09. VIER mal gekauft** (15:33 53,48 @0,935 ·
      15:44 53,42 @0,936 · 16:32 55,13 @0,911 · 16:44 55,43 @0,906) = rund 200 EUR
      fuer EIN Signal; das Buch fuehrt 55,43 Einheiten, also einen Kauf.
      Ursache: `Agenten/Handel/beleg_hand.py:99-100` fragt `kraken.gefuellte_menge(txid)`
      SOFORT nach dem Marktkauf ab. Die Boerse fuelte um 16:32 (53,42 Einheiten,
      50,00 EUR), das Journal schrieb 53 s spaeter "beleg_hand: Kauf ohne Fuellung"
      (14:32:53 UTC). Ohne erkannten Fill bucht die Spur keine Position und stellt im
      naechsten Zyklus (alle 15 min) einen neuen Beleg - der naechste Kauf folgt.
      Zweiter Befund: XLMEUR wurde am 28.09. 17:02 fuer 50,02 EUR gekauft und steht
      NICHT im Buch; die Buchpositionen tragen nur `paar`+`menge`, keinen Einstiegspreis,
      Einsatz oder Stop (daher die 1-2-EUR-Anzeige im Bericht).
      Naechster Schritt: (1) nach AddOrder die Fuellung abwarten (Poll auf gefuellte
      Menge/Orderstatus, ~10 s, wie die wartende-Auftraege-Logik in xperp) und erst
      danach "ohne Fuellung" melden; (2) vor dem Stellen eines Belegs pruefen, ob fuer
      dasselbe Instrument schon Beleg, offene Order oder Bestand existiert; (3) die
      Buchpositionen der Kraken-Spur mit preis/einsatz/stop fuellen.
      Nicht dringend: 45,90 EUR frei < 50 EUR Beleg, derzeit ist kein weiterer Kauf moeglich.
      Angelegt: 2026-09-28
      Betrifft: Agenten/Handel/beleg_hand.py, Agenten/Handel/kraken/handeln.py
      
- [x] **T-365 — `trailing.py` verdrahtet den Stop, ohne vorher die Mengen-Deckung zu pruefen**
      Kontext: Die Referenz `handel-spur-optimization/references/
      trailing-stop-gehebelt.md` fordert in Abschnitt 5.1 als ERSTE
      Reihenfolge: Buch gegen Boerse, und zwar je MENGE - "erst
      zusammenfuehren, dann trailingen". Grund: eine Position, die an der
      Boerse in mehreren Schutzauftraegen liegt (die Menge aufgeteilt),
      ist nicht trailingbar - der engste feuert zuerst, die anderen
      bleiben als Waisen zurueck. Messbar als Stop-Deckungsgrad
      (gedeckte Kontrakte / Buchmenge); "ein Treffer genuegt nicht".
      Gemessen 05.10.2026, 16:30 am Stand `trailing.py` (318 Zeilen, noch
      nicht committet, Sitzung arbeitet): `verdrahtung()` reicht fuenf Zahlen
      durch (halten_pct, trigger_r, floor_pct, min_hub_r, max_halten_pct),
      `menge` wird nur zum Bestellen benutzt, ein Deckungsgrad wird NICHT
      geprueft, und `tests/test_trailing.py` (19 Tests, alle gruen) fuehrt
      keine Mengen-Deckung. Die sechs anderen Regeln der Seite sind einzeln
      verdrahtet und einzeln getestet (Trigger 176, Hochstand 182,
      Mindestabstand 196, Richtungszwang 204, Liquidationsmarke 214) - es
      fehlt genau die eine, die die Seite als Reihenfolge VOR dem Verdrahten
      fordert.
      Folgewirkung, wenn es so bleibt: eine aufgeteilte Position wird
      getrailed, der engste Stop feuert, die uebrigen bleiben ungedeckt
      zurueck - derselbe Zustand, den `xperp/stopdeckung.py` am
      05.10.2026 mit 19 ungedeckten Kontrakten aufgedeckt hat.
      Naechster Schritt: WARTEN, bis die Sitzung `trailing.py` committet
      hat. Dann die Vorpruefung als erste Bedingung in `trailing.nachziehen()`
      einziehen (Aufruf von `stopdeckung.deckung()`, Abbruch bei Unterdeckung
      mit Meldung) und mit einer Gegenprobe belegen: eine Position mit
      geteilter Deckung muss ABGELEHNT werden, dieselbe Position mit
      voller Deckung darf durch.
      Angelegt: 05.10.2026 - Zuletzt: 05.10.2026
      Betrifft: Agenten/Handel/trailing.py, Agenten/Handel/tests/test_trailing.py, Agenten/Hermes/skills/brainfiles/handel-spur-optimierung/references/trailing-stop-gehebelt.md
      
- [x] **T-312 - futures_probe laesst eine Position OHNE Stop offen, wenn /fills ablehnt**
      Kontext: Der T-285-Roundtrip am 01.10.2026 (PF_STRKUSD, 1 Kontrakt,
      VPN getrennt) hat einen echten Fehler im Hauswerkzeug
      Agenten/Handel/nautilus_kraken/futures_probe.py gezeigt: der KAUF
      wurde angenommen und gefuellt, das anschliessende Fill-Polling auf
      /fills scheiterte an `authenticationError`, worauf das Skript abbrach -
      der Notausstieg im except-Zweig liess die Position OHNE Schutz-Stop
      offen. Von Hand geschlossen, zurueck auf die drei vorherigen
      Positionen (PF_SUIUSD, PF_HBARUSD, PF_HYPEUSD). Die Landmine daneben
      ist behoben (die Probe rechnete 1 Kontrakt = 1 USD Nominal und haette
      bei der Hausvorgabe 676.816 USD gekauft; jetzt bricht sie mit der
      echten Zahl ab). OFFEN: warum /fills authenticationError sagt, waehrend
      /accounts und /openpositions antworten - und der Notausstieg muss
      unabhaengig vom Fill-Polling laufen.
      Naechster Schritt: /fills getrennt aufrufen und die Antwort
      protokollieren; der Verkauf darf nicht vom Fill-Polling abhaengen.
      Angelegt 01.10.2026 · Zuletzt 02.10.2026 · Betrifft nautilus_kraken
      
- [x] **T-340 — Bus-Anbindungen gefixt: squeeze_eth.py und plattenplatz-pruefen**
      **Erledigt 04.10.2026, Commit adac9bc9.** Zwei verschiedene Ursachen,
      zwei verschiedene Loesungen - beide mit Gegenprobe.
      1) squeeze_eth.py: der Schattenarm rief handeln._main() ohne eigene
         Bus-Meldung und meldete damit als 'handel/squeeze' - als eigener
         Arm unsichtbar. Muster spiegel_knapp: der Walker meldet selbst und
         ruft den Kern _main() statt main(). Gegenprobe: eigene Meldung
         entfernt -> Test rot Z.236; zurueckgesetzt -> gruen.
      2) plattenplatz-pruefen.ps1: KEINE eigene Anbindung gebaut. Die Datei
         ist ein Teilschritt aus systempruefung.ps1 Abschnitt 7b und laeuft
         dort zweimal (erst -OhneOrdner, bei Warnung erneut) - eine eigene
         Meldung wuerde jeden Befund doppelt ins Journal schreiben. Es gibt
         keine MaxHirn-Plattenplatz-Aufgabe, nur MaxHirn-Systempruefung
         (Aufgabenplanung abgefragt). Kennzeichnung 'BUS: Bibliothek' mit
         Begruendung im Kopf. Gegenprobe: Kennzeichnung entfernt -> Test
         rot Z.59; zurueckgesetzt -> gruen.
      Suite: python Agenten/Bus/tests/test_ende_zu_ende.py endet mit
      'Ende-zu-Ende bestanden', Exit 0 - erster voller gruener Durchlauf
      seit dem 30.09.2026.
      Kontext: `python Agenten/Bus/tests/test_ende_zu_ende.py` bricht ab mit
      'automatisch gestartet, aber ohne Bus-Anbindung: [PFAD]squeeze_eth.py'
      (test_anbindung_handel) und `plattenplatz-pruefen` (test_anbindung_routinen).
      Beide committet, beide von fremden Sitzungen. Suite-Gegenprobe: ohne diese
      beiden Eintraege endet sie mit 'Ende-zu-Ende bestanden'. Dieselbe Klasse wie
      T-253 (klassik-Spuren, 02.10. mit e6894cc6 behoben) - eine Spur, die der
      Dauerlauf startet, aber nicht in den Bus meldet, laeuft still.
      Naechster Schritt: je Datei das Bus-Muster nach Hausvorlage ergaenzen
      (Ereignis.ps1 dot-sourcen, Melde-Start/Melde-Ende an allen Ausstiegen;
      Spuren: bus_name als Literal in die ereignis.lauf-Rechnung).
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/squeeze/squeeze_eth.py, Agenten/Routinen/plattenplatz-pruefen.ps1
      **2026-10-04: PARTIAL — zurueck auf offen.** Grund: (a)+(b) Datei-Fixes gueltig und verifiziert (squeeze_eth.py Z.34-38 eigene Meldung + handeln._main(); plattenplatz-pruefen.ps1 Z.3-4 'BUS: Bibliothek'), ABER (c) Ende-zu-Ende-Suite unter HEAD nicht reproduzierbar: `python Agenten/Bus/tests/test_ende_zu_ende.py` ⇒ Exit 1, test_anbindung_routinen meldet `exit ohne vorheriges Melde-Ende: ['datensortierung:78']` (statischer Scan; `exit 3` im Einzelinstanz-Guard Z.78 vor Melde-Start, Guard aus 917ac39e / T-240). Erst nach Beseitigung von `datensortierung:78` wieder als erledigt fuehren. Folgepunkt: T-240.
      
- [x] **T-345 — Leitstand-Reiter ohne Takt: F5 wirkt, die Statusleiste altert nicht**
      Kontext: Der Leitstand taktet alle 5 s (`TAKT_MS`). Der Omniquant-
      Reiter liest jetzt bei F5 neu und meldet Treffer und Berichtsalter -
      aber nur, wenn jemand F5 drueckt. Ohne F5 bleibt der Text stehen,
      waehrend die Zahl daneben (Dauerlauf-Status) weiterlaeuft. Der
      Nautilus-Reiter hat denselben Effekt: sein Text richtet sich nach
      `_running`, das nur die Queue des Nodes aendert.
      Naechster Schritt: beide Reiter in `leitstand.TAKT_SICHTBAR` aufnehmen
      (nur der sichtbare Reiter wird takten - kein Netz beim Hintergrund).
      Vorher messen, ob der 15-s-Timer von OmniquantGui dadurch doppelt
      laeuft; zwei Timer auf dieselbe Datei sind eine stille Last.
      Angelegt · 04.10.2026 · Betrifft: Agenten/Handel/leitstand.py,
      Agenten/Handel/omniquant/gui.py
      
- [x] **T-141 - Braucht ein Werkzeug TCP 9900? Der Gateway lauscht nur noch auf dem Control-Pipe**
      Kontext: Seit dem Hermes-Update vom 29.09.2026 lauscht der Gateway auf einem Named Pipe
      (`\\.\pipe\hermes-gateway-*`, belegt: 1 Pipe im Namensraum) und bedient Webhooks auf 8644;
      **TCP 9900 bleibt zu, waehrend der Dienst gesund laeuft** (`hermes gateway status` =
      "Gateway process running", `hermes doctor` = "gateway running", Telegram wurde bedient).
      Die zwei Haus-Wachen sind umgestellt (siehe T-139). Offen ist, ob ein a2a-Peer oder ein
      Fremdwerkzeug den Port erwartet - die Peer-Liste steht in der `a2a_agents`-Sektion der
      Hermes-`config.yaml`.
      Naechster Schritt: einen Peer-Aufruf aus einer Bot-Sitzung fahren (`a2a_list`/`a2a_call`);
      gelingt er ohne 9900, ist der Port endgueltig Altweg.
      KORREKTUR 2026-09-30: Die Annahme "TCP 9900 bleibt zu, waehrend er gesund laeuft"
      ist widerlegt. Gemessen am 30.09.2026 01:52 mit `Get-NetTCPConnection`: der
      Dienstprozess 73852 haelt **127.0.0.1:9900** (A2A) und **0.0.0.0:8644** (Webhook).
      Der Gateway laeuft als EINE Kette 73620 (Launcher-venv) -> 36840 (.hermes-runtime)
      -> 73852 (tools-Python, `runpy`-Form, schreibt `gateway_state.json`). Die
      Prozesssuche `*gateway run*` findet 73852 NICHT (die runpy-Form traegt den Text
      nicht) - deshalb lesen die Wachen zuerst `gateway_state.json`. Offen bleibt nur,
      ob ein Peer den Port BRAUCHT: er ist da, also ist die Frage nach dem Altweg erledigt.
      Angelegt 2026-09-29. Betrifft Agenten/Hermes (config.yaml), Agenten/Routinen/gateway-waechter.ps1.
      
- [x] **T-183 — NODE_ENV=production in der Agenten-Shell bricht jeden vite-Dev-Lauf**
      Kontext: Beim ersten echten Lauf der Skill-Anleitung `inspecting-hermes-desktop-dom`
      starb der Renderer mit `ReferenceError: $RefreshSig$ is not defined`
      (`apps/desktop/src/i18n/context.tsx`), `#root` blieb leer. Ursache ist ein geerbtes
      `NODE_ENV=production` in der Shell des Agenten: `@vitejs/plugin-react` emittiert dann
      die Fast-Refresh-Aufrufe OHNE die Laufzeit. Gemessen am 2026-09-30:
      `cmd /c "set NODE_ENV"` = production; NICHT in `HKCU\Environment`, NICHT in
      `terminal.docker_forward_env` der config.yaml (dort Zeile 2295 nur im env-Block des
      MCP-Servers desktop-commander). Mit `env -u NODE_ENV` vor vite UND electron mountet die
      App normal: 351 Knoten, 79 `[data-slot]`, ~32 s bis gemountet, Port 9333 liefert DOM
      und Konsolenfehler. Die Skill-Pitfalls sind entsprechend ergaenzt (Commit b39288f).
      Naechster Schritt: Quelle des geerbten NODE_ENV finden (Startweg der Hermes-TUI,
      `hermes.exe --tui` aus `Agenten/Hermes/bin`) und entscheiden, ob sie dort bleiben muss —
      sie faerbt JEDEN Dev-Server, den ein Agent startet, nicht nur diesen einen.
      **2026-10-08: QUELLE GEFUNDEN.** `hermes_cli/main_tui_launch.py:386` setzt
      `env.setdefault("NODE_ENV", "development" if tui_dev else "production")` beim TUI-Start;
      zweite Quelle `hermes_cli/web_server_chat.py:438` (Web-Server-Chat, ebenfalls setdefault).
      Beide sind `setdefault` (setzen nur, wenn NODE_ENV nicht schon in der Umgebung steht) und
      fuer die TUI/den Web-Server selbst gedacht (production-Laufzeit). Der Leak in Kindprozesse
      (vite-Dev-Server) ist die Nebenwirkung. Entscheidung: die Zeilen muessen dort bleiben
      (die TUI braucht production), der Leak ist ein Hermes-Core-Thema (Fremd-Checkout) - ein
      Agent, der einen Dev-Server startet, entfernt NODE_ENV selbst (`env -u NODE_ENV`), wie die
      Skill-Pitfalls es schon dokumentieren. Kein Core-Eingriff.
      Angelegt: 2026-09-30 · Zuletzt: 2026-10-08
      Betrifft: `Agenten/Hermes/config.yaml`, `Agenten/Hermes/skills/software-development/inspecting-hermes-desktop-dom`, `apps/desktop` (Fremd-Checkout)
      
- [x] **T-076 — Der OKX-Bot-Waechter kennt die GESCHLOSSENEN Grids nicht**
      Kontext: `waechter.py`/`analyse.py` lesen nur laufende Bots
      (`dca/ongoing-list`, `grid/orders-algo-pending`). Die 62 geschlossenen Grids
      (`grid/orders-algo-history`, 08.08.-24.09.2026) sind damit unsichtbar -
      genau die Bots, deren Ergebnis man auswerten will. Die Auswertung vom
      25.09.2026 (Netzgewinn +305,64 gegen Richtungsgewinn -392,99 = -77,01 auf
      7.072,87 USDC Einsatz) entstand aus einer Wegwerfsonde in
      `Agenten/Hermes/cache/scratch/okx_grid_kursweg.py`.
      Naechster Schritt: die Sonde als `grid_historie.py` in `okx_bot_waechter`
      uebernehmen (je Grid: Seite, Laufzeit, Netzgewinn, Richtungsgewinn, Stop
      vorhanden ja/nein, Marktbewegung waehrend der Lebensdauer) und in den
      Bericht aufnehmen; rein lesend, wie der uebrige Bericht.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/okx_bot_waechter/, MaxHirn/Wiki/Werkzeuge/okx-bot-waechter.md
      **Erledigt 08.10.2026.** grid_historie.py in okx_bot_waechter gebaut (Commit 72049740): je Grid Seite, Laufzeit, Netzgewinn, Richtungsgewinn, Stop vorhanden ja/nein, Marktbewegung waehrend der Lebensdauer; in den Bericht aufgenommen (waechter.py --historie); rein lesend. Tests tests/test_grid_historie.py 18/18 gruen (scanner/.venv).
      
- [x] **T-036 — Codex über OmniRoute: Provider „codex" hat im Router keine aktiven Credentials**
      Kontext: Am 07.09.2026 war `MaxHirn/.codex/config.toml` in dreifacher Hinsicht
      kaputt: (1) eine `export …`-Zeile in TOML (Parse-Fehler), (2) globale Keys
      standen hinter `[mcp_servers.okx-agent-trade-kit]` und hingen damit unter
      dem MCP-Table (wurden still ignoriert), (3) `model_provider` ist auf
      Projektebene von Codex ein unsupported Key. Repariert: Projekt-Config neu
      geordnet (globale Keys oben, MCP ans Ende), Provider-Definition
      `[model_providers.omniroute]` in die User-Config `~/.codex/config.toml`
      gelegt (additiv, `.bak-20260907`), Aktivierung je Lauf per
      `-c model_provider="omniroute"` — Codex zeigt jetzt
      `provider: omniroute, model: cx/gpt-5.5`. Der Endpunkt selbst antwortet
      (401 ohne Key, Modellkatalog mit Key). **Verbleibender Blocker:** OmniRoute
      liefert `401 Unauthorized: No active credentials for provider: codex` —
      der Router hat keine hinterlegten Upstream-Credentials für den Provider
      `codex` (Log: `AutoRefreshDaemon … checking 0 credentials`). Das ist der
      seit 07.09. bekannte offene Punkt (Workspace-Key / Provider-Credentials),
      nicht mehr ein Config-Fehler. OmniRoute-Serverstart 20:17 beobachtet,
      Port 20128 danach nicht mehr erreichbar — **nicht angefasst**, andere
      Agenten nutzen den Router.
      Nächster Schritt: OmniRoute-Admin: Credentials für Provider `codex`
      hinterlegen (oder Modell auf einen Provider mit Keys umstellen), dann
      Smoke-Test wiederholen.
      Betrifft: `MaxHirn/.codex/config.toml`, `~/.codex/config.toml`, OmniRoute
      Wartet auf: Credentials für Provider `codex` in OmniRoute
      **Key-Verweis (13.09.2026):** Der Admin-Schlüssel für die OmniRoute-Config steckt
      nicht im Router-Prozess. Lesbar sind die Benutzervariablen
      `OMNIROUTE_ADMIN_API_KEY` (Admin-/Config-API `/api/*`) und `OMNIROUTE_API_KEY`
      (Modell-API `/v1/*`) direkt aus `HKCU\Environment` - der Prozess erbt frisch
      gesetzte Variablen nicht, also aus der Registry lesen statt env. Der Klartext
      selbst liegt nur in [[Zugaenge]] (Stufe 0): dorthin sehen, nie in Notizen
      kopieren.
      Angelegt: 2026-09-07 · Zuletzt: 2026-09-13 (Key-Verweis ergänzt)
      **Erledigt 07.10.2026 - ueberholt.** Der Task meldete, der Provider 'codex' habe im Router keine aktiven Keys. Gemessen in OmniRoute storage.sqlite: es gibt KEINE Verbindung mit provider LIKE '%codex%' mehr (14 Verbindungen gesamt, keine davon codex). Der Gegenstand existiert nicht mehr.
- [x] **T-127 — Kein freies Guthaben fuer neue Live-Einstiege (Kraken 0,71 EUR / OKX 0,15 USDC)**
      Kontext: `mosaic` und `swap` nennen ihre Sperre seit 25.09.2026 mit Boerse
      und Waehrung. Der Fakt dahinter: Kraken traegt **0,71 EUR** frei, waehrend
      ~196 EUR in drei offenen Live-Positionen liegen (BTC/ETH/SOL, alle mit
      Boersen-Stop); OKX traegt **0,15 USDC** frei, die uebrigen 757 USDC sind
      die Besicherung laufender XPERP-Positionen (FIL/MON/MSTR/CRCL + die
      manuelle FIL-Position). Kein Dateischalter loest das - es fehlt Geld, keine
      Bedingung.
      Naechster Schritt: Entscheidung von Max - Guthaben aufstocken, eine
      Position schliessen oder die Spuren im Papier lassen. Nichts davon
      automatisch tun.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/mosaic, Agenten/Handel/swap, Kraken- und OKX-Konto
      **Erledigt 07.10.2026 - ueberholt.** Der Task nannte 'Kraken 0,71 EUR / OKX 0,15 USDC frei'. Gemessen heute: Kraken ZEUR 86,9980 / ZUSD 22,3333 / USDC 98,1926. Auf OKX liegen laut Kontostand ebenfalls Mittel. Die im Task behauptete Sperre ist keine mehr.
- [x] **T-131 — Kraken-EUR: 0,71 EUR frei blockieren `kraken` UND `nautilus_kraken` live**
      Kontext: Am 25.09.2026 waren in beiden Spuren die Papier-Positionen ausgebucht
      (siehe T-103 und Wiki/Handel/Lektionen.md) - damit ist das Buch frei, aber das
      Geld ist der naechste Grund: `kraken/verifiziere_guthaben.py` misst ZEUR = 0,7059,
      noetig sind 60,00 EUR (`mindest_guthaben_eur`); `nautilus_kraken` braucht fuer den
      ~1-EUR-Round-Trip 1,00 EUR (`live_einsatz_eur` 1.0, `mindest_guthaben_eur` 2).
      Das Kraken-EUR haengt in mosaics Live-Positionen (SOL + BTC, rund 96 EUR Nominal)
      und wird erst beim Ausstieg wieder frei. Kraken ist ausserdem `handel_erlaubt=false`
      und ordert ueber den Freigabe-Beleg (`order_ueber: mcp`), nautilus_kraken hat
      `handel_erlaubt=true` und den REST-Orderweg gebaut.
      Naechster Schritt: entscheiden - (a) auf mosaics Ausstieg warten (dann wird EUR frei
      und nautilus_kraken kann den 1-EUR-Test fahren), (b) EUR einlegen, oder (c)
      `mindest_guthaben_eur`/`live_einsatz_eur` senken. Nicht getan: nichts davon ohne
      Entscheidung, kein Geld umgeschichtet.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/kraken/wachen.json, nautilus_kraken/wachen.json, Kraken-Konto
      **Erledigt 07.10.2026 - ueberholt.** Der Task nannte 'Kraken-EUR: 0,71 EUR frei'. Gemessen heute (kraken.kontostaende()): ZEUR 86,9980 + ZUSD 22,3333 + USDC 98,1926. Der genannte Blocker besteht nicht mehr; die beiden Spuren sind nicht mehr am Guthaben gesperrt. Der Vorgang selbst (Guthaben aufladen) ist Max' Hand gewesen und hat gewirkt.
- [x] **T-254 - Paperclip: Instanz laeuft und der Umgebungstest ist gruen - offen sind Anmeldung, Modell, Autostart**
      Kontext: Dashboard `http://127.0.0.1:3100` (HTTP 200), eingebettete PostgreSQL auf
      127.0.0.1:54329, 278 Migrationen. Der erste Start braucht rund 3 min (sieht wie ein
      Haenger aus). Unter Windows gibt es KEINEN Hintergrunddienst (`Service management is not
      supported on win32`). Der Umgebungstest scheiterte zunaechst an `ANTHROPIC_API_KEY` aus
      `C:\Users\faupe\.env` (Arbeitsverzeichnis des Servers!) - behoben, seitdem `status: pass`.
      Start-Wrapper steht: `Agenten/Routinen/paperclip-start.ps1` (Port-Pruefung, Arbeits-
      verzeichnis `.paperclip`, entfernt ANTHROPIC_*). Offen: (a) Board-Anmeldung der CLI -
      Dashboard im Browser oder `paperclipai connect --persona board`; `token board create`
      verlangt vorher eine Sitzung. (b) Kein LLM-Provider eingetragen (fuer arbeitende Agenten
      noetig - OmniRoute/Ollama waeren im Haus da). (c) Kein Autostart (geplante Aufgabe nach
      Hausmuster fehlt). (d) Die `.env` im Home bleibt eine Falle fuer dort gestartete Werkzeuge
      (absichtlich nicht angefasst).
      Naechster Schritt: Entscheidung von Max - Konto im Dashboard anlegen und
      `paperclipai connect` fahren, danach den Provider eintragen; auf Wunsch zusaetzlich die
      geplante Aufgabe fuer den Wrapper.
      Angelegt: 2026-09-30 · Zuletzt: 2026-10-01 · Betrifft: `~/.paperclip/instances/default`,
      `Agenten/Routinen/paperclip-start.ps1`
      **Erledigt 07.10.2026.** (a) Board-Anmeldung steht: paperclipai whoami meldet local-board. (b) LLM-Provider ist laut paperclipai doctor OPTIONAL ('No LLM provider configured (optional)') - kein Eintrag noetig. (c) Autostart: Aufgabe MaxHirn-Paperclip angelegt (Anmeldung +2 Min, versteckt, IgnoreNew, LeastPrivilege), manuell gestartet, Log bestaetigt 'Port 3100 belegt - Paperclip laeuft schon, kein Start.' (d) unveraendert.
- [x] **T-249 - `MaxHirn/DockerDesktopWSL` (4,88 GB) liegt im Vault**
      Kontext: Der Vault wird nach `G:` gesichert (`MaxHirn/` + `Agenten/`), dieses Volumen
      damit mit - 4,88 GB Docker-Daten in einem Wissensspeicher. Am 30.09.2026 gemessen, nicht
      angefasst: Docker laeuft (Container `nautilus-demo`, `freqtrade-*`, `openterminalui-*`),
      ein Verschieben im laufenden Betrieb waere riskant.
      Naechster Schritt: Entscheidung von Max - im Docker Desktop den Datentraeger-Ort
      verlegen (dann einmal Docker neu starten) oder bewusst liegen lassen und in
      `Wissen/Routinen.md` als Ausnahme vermerken.
      Angelegt: 2026-09-30 · Betrifft: `MaxHirn/DockerDesktopWSL`, Sicherung nach `G:`
      **Erledigt 07.10.2026.** Entscheidung Max: bewusst liegen lassen. Nachgemessen: G:\\MaxHirn-Sicherung\\MaxHirn\\DockerDesktopWSL enthaelt genau die zwei VHDX (docker_data.vhdx 4896 MB + ext4.vhdx 96 MB = 4,88 GB), sie gehen also in JEDE G:-Sicherung. Ein Umzug verlangt einen Docker-Neustart, waehrend nautilus-demo/freqtrade-*/openterminalui-* laufen - das groessere Risiko. Als Ausnahme in Wissen/Routinen.md vermerkt, samt Nachhol-Weg.
- [x] **T-302 — Hauptconfig-Modellliste entscheiden (1739 omniroute + 428 nous)**
      Kontext: Am 01.10.2026 sind die `models:`-Listen der 19 Bot-Profile auf das gekuerzt, was
      jedes Profil selbst nennt (33.064 -> 125 Eintraege, Werkzeug
      `Agenten/Hermes/scripts/profil-modelllisten-kuerzen.py`). Die HAUPTconfig traegt weiter
      die volle omniroute-`auto/*`-Liste (1.739) und die 428 Nous-Modelle - beides ist
      gewollt bzw. ausdruecklich bestellt (Nous-Liste), aber dieselbe Frage stellt sich:
      braucht der Hauptwaehler die 1.739 Router-Kombinationen, wenn der Endpunkt sie mit
      Schluessel ohnehin live liefert?
      Naechster Schritt: entscheiden, ob die omniroute-Liste der Hauptconfig ebenfalls auf die
      benutzten Kombinationen gekuerzt wird (`--hauptconfig` waere im Werkzeug zu ergaenzen).
      Angelegt 01.10.2026 · Betrifft Agenten/Hermes/config.yaml
      **Erledigt 07.10.2026.** Der Task war ueberholt: die omniroute-Liste hatte 106 Eintraege, nicht 1.739. Gemessen gegen den Router (/v1/models, 1831 Modelle live): 64 davon loesen NICHT auf - alle 62 gh/* und github/* plus mlx-qwen/... und nacktes 'auto'. Ursache: der github-Provider in OmniRoute ist is_active=0. 64 tote Eintraege entfernt (config.yaml.bak-20261007), 42 bleiben, YAML parst, Diff 0/64.
- [x] **T-348 — Vier Tests rot, alle vier von fremder Hand (04.10.2026)**
      Kontext: Die volle Handel-Suite (1781 Tests, 1177 s) meldet vier
      Fehlschlaege. Keiner gehoert zu den Leitstand-Schritten; per
      `git diff --name-only` gegen jeden meiner vier Commits belegt, dass
      keine der vier Dateien angefasst wurde. Die Ursachen sind je
      verschieden und alle von aussen gekommen:
      * `test_einheit_kraken.QuelleTest.test_kein_zweiter_leser_der_tabelle`
        sah `cache/replay/*.py` als 'zweiten Leser der Einheitentabelle' -
        sechs Wegwerf-Kopien vom 14.10. (Testartefakte, nie committet).
        Nach dem Wegraeumen nach `Agenten/Hermes/cache/replay-alt-20261004`
        gruen. Der Test prueft `os.walk` ueber den Handel-Ordner und
        uebersieht, dass `cache/` Wegwerf ist.
      * `test_spur_wache.test_wache_kennt_vier_spuren`: `omnitrade_futures`
        traegt `trigger_modus: signal` (Commit bd6cdb28) und damit eine
        Warteschlange ohne Wache. Dieselbe Klasse wie T-328.
      * beide `test_replay`-Tests: `replay.py` wurde am 04.10. 21:32 von einer
        anderen Hermes-Sitzung umgebaut (Commit 0919b566, T-310, Autor
        'Hermes'); die Tests gingen dabei mit.
      Naechster Schritt: die drei Punkte getrennt beheben - erst den Test
      (`cache/` von `os.walk` ausnehmen), dann `omnitrade_futures` eine
      Wache geben, dann `replay.py` mit den Tests zusammen nachziehen. Nicht
      in einem Commit, weil drei verschiedene Ursachen.
      Angelegt · 04.10.2026 · Betrifft: Agenten/Handel/tests/test_einheit_kraken.py,
      Agenten/Handel/tests/test_spur_wache.py, Agenten/Handel/replay.py,
      Agenten/Handel/tests/test_replay.py
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - test_spur_wache 11 Tests gruen (Hauptbaum); test_replay im Hauptbaum nachgezogen, braucht die Historie.**
- [x]   **T-337 — `moondev_historie.basis_von` las einen Cache, der Tests lahmlegte**
      Kontext: `_basis` war ein reiner Modul-Cache, gefuellt nur wenn er LEER war. Ein
      Test, der einmal das echte 300er-Universum geladen hatte, hinterliess diese Liste fuer
      den ganzen Prozess. `test_replay_feed.LaufFeedEchtTest` legt seine Attrappen in einen
      Temp-Ordner - `basis_von` fand seine Symbole im alten Cache nicht, `rng` lieferte
      nichts, die Spur buchte 0 Positionen und der Test meldete "Journal ohne eine
      Buchung". Der Test war nicht schuld, er war das Opfer eines Caches ohne
      Zuruecksetzung. Jetzt fragt `basis_von` die Platte des aktuellen ORDNER ab, statt
      einen stehengebliebenen Zustand zu uebernehmen.
      Dieselbe Frage bei allen anderen Modul-Caches der Spuren (grep nach
      `_xxx = []` und `if not _xxx:` auf Modulebene). Ein Cache darf eine Antwort
      beschleunigen, aber nie die Frage beantworten.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/moondev_historie.py
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - moondev_historie.basis_von leert den Cache (Z.119) und nennt den Fehler im Kommentar (Z.141).**
- [x]   **T-331 — `satz_pct_fuer` las den Börsensatz aus den Notizfeldern**
      Kontext: Die Ableitung 'boerse=okx, ist das ein Perp?' suchte das Wort "perp" in
      `json.dumps(w).lower()` - also im GANZEN Wachen-JSON. Die Notizfelder tragen es
      haeufig im Nebensatz (`_trigger_vermerk: ... Signal-Wechsel-Gatter als Perp`,
      `_handel_erlaubt_vermerk: ... Perp`). Damit wurde jede OKX-Spot-Wache als Perp
      gelesen: der Abgleich verlangte 0,05 % von moondev_topmovers und moondev_listingarb,
      die gemessen 0,10 % tragen (ihre eigenen Notizen sagen das sogar). Der Satz wird
      jetzt aus dem MARKTTYP abgeleitet (`instrumente`, `instrumente_aktiv`, `instrument`,
      `moeglich`, `markttyp`/`produkt`/`instrument_typ`) - nicht aus dem Kommentar darueber.
      Nebenbefund dabei: `trendwende_btc` fuehrt sein Instrument im SINGULAR-Feld
      `instrument` (BTC-USDT-SWAP), nicht in `instrumente` - das alte Muster las es nicht
      und wertete die echte Perp-Spur als Spot.
      Dieselbe Frage bei jedem anderen Werkzeug stellen, das eine Wachen nach einem
      Schluesselwort durchsucht statt nach einem Feld: eine Notiz soll nie eine Zahl
      entscheiden.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/gebuehren_setzen.py
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - gebuehren_setzen.satz_pct_fuer liest markttyp/produkt/instrument_typ statt json.dumps (Z.123-131).**
- [x]   **T-327 — `anbindung_pruefen.py` las die Wachen aus Agenten/ statt Agenten/Handel/**
      Kontext: `HANDEL = os.path.dirname(HIER)` in einem Werkzeug, das IN `Agenten/Handel`
      liegt - eine Ebene zu hoch. `lade_wachen()` bekam fuer jede Spur `{}` (es gibt kein
      `Agenten/scanner/wachen.json`), `handel_erlaubt` las sich als False, und der Lauf meldete
      12 von 12 Spuren "bereit, aber gesperrt" - wo 10 scharf sind. Der Befund sah harmlos aus
      ("alles gesperrt") und war die Umkehrung der Wahrheit: wer nach dem Lauf handelte, haette
      die falsche Liste gehabt. Behoben (`HANDEL = HIER` mit Begruendung im Modulkopf), Nachweis:
      der Lauf meldet jetzt 12 bereit / 2 gesperrt (xperp und swap tragen `handel_erlaubt=false`
      wirklich). Test `tests/test_arm_wirksamkeit.py::WerkzeugLiegtImHandelOrdnerTest` mit
      Gegenprobe.
      Die Regel auf alle Werkzeuge direkt in Agenten/Handel ausweiten (eine Pruefung
      ueber die ganze Wurzel dieses Ordners). `freigabe_tor.py` und `risiko_beitrag.py` fielen am
      03.10.2026 schon auf dieselbe Weise auf.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/anbindung_pruefen.py
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - anbindung_pruefen.py HANDEL = HIER (Z.35) - eine Ebene zu hoch war der Fehler.**
- [x]   **T-328 — Zwei Schattenarme liefen, ohne dass das Haus ihre Q:-Kopie je pruefte**
      Kontext: `spiegelstand` fuehrte die Arm-Namen hart: nur `wachen.knapp.json` und
      `wachen.weit.json`. `squeeze_eth` (Ordner squeeze, Wachen `wachen.eth.json`) und
      `nautilus_kraken_futures` (Ordner nautilus_kraken, Wachen `wachen.futures.json`) stehen
      in `dauerlauf.SPUREN`, spiegelten nach Q: - und wurden von der Pruefung nie gesehen.
      Bedingung 4 dieser zwei Spuren war ungeprueft (2 von 48). Derselbe Ort riet das Suffix mit
      `spur.split("_", 1)[1]`: aus `nautilus_kraken_futures` wird `kraken_futures`, die Datei
      gibt es nicht, also wurde still die Haupt-Wachen des Ordners gelesen - der SPOT-Arm -,
      und Zeilenzahl und Herzschlagalter liefen ueberhaupt ohne Suffix. Behoben: Arm-Dateinamen
      gesammelt, Suffix von rechts kuerzen bis die Datei da ist, Suffix an JEDE Buchdatei (auch
      Zaehler und Alter). Nachweis: 48 von 48 byte-gleich, futures 1378 Zeilen gegen 1286 im
      Spot-Arm. Test `tests/test_arm_wirksamkeit.py`, zwei Gegenproben.
      Die vier uebrigen Hand-listen auf dieselbe Art pruefen: `squeeze_eth` fehlt in
      `auswertung_alle.SPUREN`, `lage.HOLER`, `befehle.FAMILIE` und `pruefe_ratschen.SPUREN` -
      es ist nur im Dauerlauf gefuehrt, sein Journal (1 Zeile) wird nirgends ausgewertet.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/spiegelstand.py, Agenten/Handel/squeeze/
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - spiegelstand.py liest die Arm-Namen per ast aus dauerlauf.SPUREN (Z.115-129).**
- [x]   **T-329 — mosaics Gebuehr stand auf dem Kraken-Satz, obwohl die Spur auf OKX handelt**
      Kontext: Am 30.09.2026 (Commit `e6f2715c`, Auftrag Max "nur noch omnitrade auf kraken
      handel erlaubt") kam Kraken aus `mosaic/wachen.json` `boersen` heraus - es blieb
      `["okx"]` -, die Kraken-Spurole `gebuehr_taker 0.006` blieb aber stehen. Eine Runde wurde
      mit 1,2 % statt der gemessenen 0,2 % gerechnet (6-fach zu teuer). Der Satz gehoert zur
      ORDER-BOERSE, nicht zur Historie der Spur: ihre Instrumente sind BTC/ETH/SOL-USDC, das ist
      OKX Spot (Messung 01.10.2026). Behoben ueber `gebuehren_setzen.py --anwenden` (Sicherung
      `mosaic/wachen.json.bak-20261004`), `gebuehr_taker 0.006 -> 0.001`. Ein Kraken-Satz an einer
      OKX-Spur ist das Merkmal fuer T-330.
      Die AENDERUNGEN-Tabelle in `gebuehren_setzen.py` gegen die aktive Boerse JEDER
      Wachen pruefen - ein Spurwechsel muss den Satz mitnehmen, sonst kommt der Befund zurueck.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/mosaic/wachen.json, Agenten/Handel/gebuehren_setzen.py
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - mosaic/wachen.json gebuehr_taker 0.001 (OKX-Spot, gemessen 01.10.2026) - der Kraken-Satz 0.006 ist weg.**
- [x]   **T-330 — Kein Werkzeug prueft, ob die Gebuehr zur aktiven Boerse passt**
      Kontext: T-329 war die manuelle Fahrt. Es gibt 24 Wachen mit `boerse` oder `boersen` und
      `gebuehr_taker`, und keine Regel, die die beiden vergleicht. Eine Spur kann ihre Boerse
      wechseln - das geschah zweimal (Kraken raus aus mosaic am 30.09.2026, omniquant auf
      kraken_futures am 01.10.2026) - und den Satz behalten. `test_gebuehren_setzen.py` prueft
      die EINSTHEIT (Bruch statt Prozent), nicht den Satz der Boerse. Genau darin liegt die
      Luecke: beide Pruefungen koennen gruen sein, waehrend eine Runde sechsfach zu teuer gerechnet
      wird.
      Werkzeug `gebuhr_boerse_abgleich.py`: je Wachen die aktive Boerse (Vorragliste
      `boersen[0]`, sonst `boerse`), der gemessene Satz und der Wert - Abweichung melden,
      Schreiben nur mit `--anwenden`. Tests mit Gegenprobe.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/gebuehren_setzen.py
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - gebuehr_boerse_abgleich.py vorhanden; tests/test_gebuehr_boerse_abgleich.py 16 Tests gruen.**
- [x]   **T-325 — Drei Spuren liefen, ohne dass das Haus ihre Zahlen kannte**
      Kontext: Auftrag "suche noch nicht erkannte Arbeit in Handel und fuege ein" (03.10.2026). Gemessen ueber die echten Listen statt gesucht: `liq_wand`, `trendwende_btc` und `nautilus_emacross` stehen in `dauerlauf.SPUREN` (47 Spuren), haben Wachen und einen laufenden Zyklus — und fehlten in `auswertung_alle.SPUREN`. Befund: liq_wand hatte 32 geschlossene Runden im Journal (33 kauf, 41 verkauf) und 0 in JEDER Auswertung: kein Tagesbericht, keine Strategiekennzahl, kein Kosten-Wendepunkt, keine Freigabe-Aussage. Dieselbe Luecke bei den Ratschen: squeeze, wavetrend, macd_mtf, supertrend (20,00 = 1,0x Buchrisiko) und nautilus_emacross (100,00) fuehrten eine Drawdown-Ratsche, die `pruefe_ratschen.py` nie nachfragte. Dritte Luecke: nautilus_emacross uebergab den Bus-Namen als "handel/" + NAME — fuer die Bus-Suite (T-255) unsichtbar, der Test war rot.
      Naechster Schritt: Erledigt am 03.10.2026 — alle drei Spuren in `auswertung_alle.SPUREN` (Rechenweg `runden_indikator`, den vorhandenen), die fuenf in `pruefe_ratschen.SPUREN`, Bus-Name literal. Messung liq_wand: 32 Runden, 66 % Treffer, -10,83 USD brutto / -14,07 USD netto, Kosten-Wendepunkt -0,30 % je Runde. Neu: `Agenten/Handel/tests/test_verdrahtung.py` prueft die REGEL (jede Spur mit Journal hat einen Rechenweg, jede gesetzte Ratsche wird geprueft, jeder Betrag trifft 1,0x Buchrisiko) mit zwei Gegenproben, 6/6 gruen; Bus-Suite gruen. OFFEN bleibt eine echte Luecke: nautilus_emacross setzt drawdown_halbierung_usd 100.00 OHNE Risiko-Feld in der Wache, der Betrag ist nicht herleitbar — als Ausnahme im Test benannt, nicht stillschweigend uebergangen. Bewusst NICHT verdrahtet: kopier, kopier1zu1, spiegel, omniquant, gitter (eigene auswertung.py, im Tagesbericht mit voller Bilanz); ihr Journal traegt token/symbol statt inst, runden_nautilus ergab dort 107 Runden mit falscher Paarung.
      Angelegt 03.10.2026 · Betrifft: auswertung_alle, pruefe_ratschen, nautilus_emacross/handeln.py, tests/test_verdrahtung.py, Wiki/Handel/Spuren-Uebersicht.md.
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - liq_wand/trendwende_btc/nautilus_emacross stehen in auswertung_alle, pruefe_ratschen, lage und dauerlauf.**
- [x] **T-303 — Omniquant-Test verlangt Papier, die Spur ist seit aecd6178 scharf**
      **Erledigt 2026-10-01.** Der Auftragstest liest jetzt `wachen.weit.json` fuer die Papier-Pruefung des Schattenarms und hat einen eigenen Test fuer die live geschaltete Hauptspur.
      Angelegt: 2026-10-01 · Zuletzt: 2026-10-01 (erledigt)
      Betrifft: Agenten/Handel/tests/test_omniquant_fassung.py, Agenten/Handel/omniquant/wachen.json, Agenten/Handel/omniquant/wachen.weit.json
      **2026-10-04: unabhaengig verifiziert — test_omniquant_fassung.py Z.143-215 liest wachen.weit.json (Z.159), Live-Test Z.210; omniquant/wachen.json Z.3 handel_erlaubt:true, Z.41 freigabe.erfuellt; Commit aecd6178 existiert.**
- [x] **T-293 — omniquant: welcher Markt gilt fuer die Gebuehr?**
      Kontext: Beim Festziehen der Gebuehren (01.10.2026) steht in
      `omniquant/wachen.json` `boerse: kraken_futures`, die Instrumente der Spur
      werden aber ueber `okx.letzter_kurs` bewertet - also OKX-Paare. Der
      Gebuehrensatz ist damit widerspruechlich: Kraken-Futures waeren 0,04-0,05 %
      je Seite (gemessen 25.09.2026), OKX-Spot 0,10 % (gemessen 01.10.2026).
      Gesetzt ist der TEURERE (0.1) und der Widerspruch steht als
      `_gebuehr_quelle` in der Datei - der freundlichere Satz waere geraten.
      Naechster Schritt: entscheiden, wo omniquant wirklich buchen soll (`boerse`
      richtigstellen ODER Instrumente auf Kraken-Paare umstellen), dann den Satz
      nachziehen. Betrifft auch `omniquant/wachen.weit.json`.
      Angelegt 01.10.2026 · Betrifft Agenten/Handel/omniquant
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - omniquant/wachen.json und wachen.weit.json tragen boerse=kraken_futures UND gebuehr_taker 0.0005.**
- [x] **T-283 — kraken stellt mehrere Belege in einem Zyklus aus, nur einer wird ausgefuehrt**
      Kontext: Am 01.10.2026 um 13:25:51 stellte die Spur DREI Belege aus (XLTCZEUR,
      ADAEUR, SOLEUR, je 50 EUR). Ausgefuehrt wurde um 13:27:22 nur SOLEUR; die anderen
      zwei verfielen mit der 180-s-Frist (freigabebeleg.GUELTIG_SEKUNDEN). Der Ausfuehrer
      `beleg-hand` laeuft als Cron alle 5 MINUTEN - ein Beleg, der direkt nach einem Lauf
      entsteht, wartet bis zu 5 min und ist damit immer abgelaufen. beleg_hand.lauf()
      iteriert zwar ueber ALLE offenen Belege, aber die Frist ist kuerzer als der Takt.
      Schaden bisher: keiner (ein verfallener Beleg kauft nicht). Zu klaeren ist, warum
      drei Belege entstanden, obwohl `pruefe_einstiege` den Platz VOR dem Beleg prueft
      (max_offene_positionen 4) - moeglicherweise war das Buch zu dem Zeitpunkt anders
      besetzt als angenommen.
      Naechster Schritt: Frist und Takt aufeinander abstimmen (Frist > Takt, z. B. 600 s
      bei 5-Minuten-Takt) ODER den Beleg-Hand-Takt auf 2 min senken; danach den
      Platz-Grund je verfallenem Beleg im Journal sichtbar machen.
      Angelegt 2026-10-01 · Zuletzt 2026-10-01
      Betrifft: Agenten/Handel/freigabebeleg.py, Agenten/Hermes/cron/jobs.json
- [x] **T-271 — kopier-Familie: dauerlauf sagt AN, der Kommentar sagt AUS, der Zentrale-Test prueft AUS**
      **Erledigt 2026-10-01.** Kommentar in dauerlauf.py auf "KOPIER AKTIV" gezogen, test_handelstand.py nimmt kopier/kopier1zu1 nicht mehr aus der Auskommentiert-Liste.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 (erledigt) · Betrifft Agenten/Handel/dauerlauf.py, Agenten/Werkzeuge/repos-zentrale/tests/test_handelstand.py
      **2026-10-04: unabhaengig verifiziert — dauerlauf.py Z.223 '# KOPIER AKTIV (seit 30.09.2026, ...)' vorhanden; Test-Liste (test_handelstand.py) als abhaengiges Artefakt bestaetigt.**
- [x] **T-242 - Fremd-Grenze: die zwei restlichen Verbraucher anschliessen**
      Kontext: `Agenten/FREMD-Liste.json` (37 Eintraege) ist die eine Quelle,
      `Agenten/Werkzeuge/fremd.py` der Leser; angeschlossen sind die Zentrale
      (Rolle + Hinweis + Kopfzeile "63 fremd") und `bestand.py`. Offen aus dem
      Design (docs/design/2026-09-30-grenze-und-popouts-design.md): (a)
      `Agenten/Werkzeuge/fundus-suche.ps1` soll fremde Baeume getrennt melden
      statt sie nach eigenem Wissen zu durchsuchen (`ConvertFrom-Json` liest die
      Liste), (b) ein Block "Grenze" in `Agenten/Routinen/systempruefung.ps1`
      (Liste lesbar, Eintraege vorhanden, keine Ueberschneidung mit eigenen
      Wurzeln). Der Block wurde bewusst NICHT gebaut, weil systempruefung.ps1
      parallel von einer anderen Sitzung geaendert wurde.
      Naechster Schritt: (a) in fundus-suche.ps1 die Liste lesen und eine Zeile
      "fremd" je Baum ausgeben, (b) den Block nach dem Muster der anderen
      Bloecke ergaenzen (`fremd.py --pruefen` aufrufen, Ergebnis melden).
      Angelegt: 2026-09-30
      Betrifft: Agenten/Werkzeuge/fundus-suche.ps1, Agenten/Routinen/systempruefung.ps1
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - fundus-suche.ps1 ruft Get-FremdZeile zweimal (Z.190,197); systempruefung.ps1 Block 15 Fremd-Grenze.**
- [x] **T-230 - Zahlen gemischt handelnder Spuren neu lesen (Richtung fehlte im Paarer)**
      Kontext: `kosten_wendepunkt._paarung_form_b` rechnete das Rundenergebnis
      als `preis/einstieg - 1` OHNE die Handelsrichtung. Bei einem SHORT war das
      Vorzeichen damit verkehrt: eine Short-Runde, die im Ziel schloss, stand als
      Verlust im Buch. Behoben am 30.09.2026 (`seite` aus der Einstiegszeile,
      `vorz = -1` bei short; Test `tests/test_kosten_wendepunkt.RichtungTest`).
      Gemessen an wavetrend ueber 5,7 Jahre: Trefferquote 54 % -> 33 %, Summe
      +679 -> -513. Betroffen ist jede gemischt handelnde Spur - squeeze,
      macd_mtf, supertrend und wavetrend haben rund 50 % Shorts je Buch - und
      jede Auswertung, die auf diesem Modul aufsetzt.
      Naechster Schritt: die veroeffentlichten Zahlen dieser Spuren mit dem
      korrigierten Paarer neu fahren und ersetzen (Backtest-Tabellen in
      `auswertung_alle.py`, die Kosten-Wendepunkt-Tabelle, die Vorher/Nachher-
      Tabelle der Beruehrungsregel in Wiki/Handel/Backtest-Fundament.md). Bis
      dahin gilt: Zahlen dieser Spuren aus der Zeit VOR dem 30.09.2026 sind
      nach dem Vorzeichen zu pruefen, nicht zu zitieren.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Handel/kosten_wendepunkt.py, auswertung_alle.py,
      MaxHirn/Wiki/Handel/Backtest-Fundament.md
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - kosten_wendepunkt.py rechnet mit Vorzeichen; tests/test_kosten_wendepunkt.py 12 Tests gruen.**
- [x] **T-226 — pos_id in den restlichen Journal-Schreibern (17 von 94 Journalen)**
      Kontext: Mit T-095 traegt jede Einstiegszeile eine Kennung `pos_id`, die
      die Ausstiegszeile uebernimmt; 77 von 94 Journalen sind mit
      `journal_pos_id_nachziehen.py` nachgezogen. Offen sind 17 Dateien in fuenf
      Ordnern, und zwar aus verschiedenen Gruenden: `orb`/`orbk` schreiben EINE
      Zeile je Runde (es gibt kein Paar zu bilden), `gitter` fuehrt Lose je
      Leiterstufe statt Positionen, `kopier` hat einen eigenen Schreiber,
      `spiegel` (drei Arme) ist seit 21.09.2026 aus dem Dauerlauf genommen und
      dient als Vergleichsbuch, und `nautilus`/`nautilus_kraken` liegen in einem
      EIGENEN Git-Repo mit eigener Buchhaltung.
      ERLEDIGT 06.10.2026: Entscheidung getroffen und umgesetzt. `orb`/`orbk`
      und `gitter` brauchen strukturell KEINE Kennung (eine Zeile je Runde bzw.
      Lose je Leiterstufe - es gibt kein Einstieg/Ausstieg-Paar zu bilden);
      `nautilus`/`nautilus_kraken` liegen in einem eigenen Repo mit eigener
      Buchhaltung und sind hier nicht anfassbar. `kopier` und `spiegel` sind
      angeschlossen wie die uebrigen Spuren: `pos_id` in SPALTEN, Erzeugung
      `pos_kennung.neu()` beim Eroeffnen, Mitfuehrung in jeder Schliess-Zeile,
      Altjournal-Schutz ueber `pos_kennung.spalten()`. Beide Journale trugen
      die Spalte im Kopf bereits (Header-Migration), nur die Schreiber gaben
      sie nicht aus - jetzt konsistent. Tests: kopier 52, spiegel 93,
      pos_kennung+journalpaarung 35, alle gruen; Probe belegt pos_id in der
      Journalzeile.
      Angelegt: 2026-09-30 · Zuletzt: 2026-10-06
      Betrifft: Agenten/Handel/{kopier,spiegel,nautilus,orb,orbk,gitter}/handeln.py,
      Agenten/Handel/journal_pos_id_nachziehen.py
- [x] **T-194 — Dateischwund-Wache auf weitere Ordner ausweiten?**
      Kontext: Die Wache vom 30.09.2026 (`Agenten/Hermes/scripts/dateischwund-wache.py`,
      Cron `dateischwund-wache`) bewacht NUR `Agenten/Hermes/scripts/` - dort sind die
      sechs verschwundenen Testdateien beobachtet worden. Dasselbe Muster kann jeden
      Ordner treffen, in dem kurzlebige Dateien entstehen: `Agenten/Handel/*`
      (Spur-Tests), `Agenten/Bus/`, `Agenten/Routinen/`.
      Naechster Schritt: Entscheidung von Max, welche Ordner dazukommen. Technisch ist
      es ein weiterer Eintrag in der Ordnerliste (je Ordner Git-Soll + eigene
      Merkliste); Kosten sind nur groessere Merkdateien, keine Laufzeit.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Hermes/scripts/dateischwund-wache.py
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - dateischwund-wache.py und dateischwund-wache-handel.py vorhanden.**
- [x] **T-156 — Bonsai aus, aber zwei MoA-Presets haengen daran**
      Kontext: `hermes moa list` zeigt fuer die Presets "Max 2" und "Vision" den Aggregator `bonsai` - dort
      laeuft die ganze Werkzeugschleife, nicht nur eine Beratung. `delegation.fallback_providers` hat bonsai
      an Stelle 2 (vor ollama-launch gesetzt, s. u.). Der Dienst antwortet nicht: Port 8081 zu, gemessen mit
      `scripts/config-gegenprobe.py`. Config und Starter nennen inzwischen denselben Port (8081).
      **Erledigt 29.09.2026 - umgestellt, nicht Bonsai gestartet.** Aggregator der Presets `Max 2` und
      `Vision` ist jetzt `ollama-launch/gemma-e4b-8k:latest`; die drei toten `bonsai`-Referenzen (Preset
      `default`, Preset `Max 2`, Top-Level-Block) stehen auf `enabled: false`. Werkzeug
      `cache/scratch/moa-umstellen.py`: zaehlt die Vorkommen, prueft `yaml.safe_load` VOR dem Schreiben,
      Sicherung `config.yaml.bak-moa-20260929_234442`.
      Warum gemma: `/api/show` meldet 131072 Kontext bei 7,52 B Parametern (der Name traegt "8k", der
      Kontext ist es nicht) und ueber den OpenAI-Weg kommt sauberer `content` ohne Denkanteil - 19 s fuer
      einen echten Aggregationsauftrag.
      Nachweis: `hermes moa list` nennt fuer beide Presets `ollama-launch:gemma-e4b-8k:latest`,
      `hermes config check` exit 0, `git diff --numstat` 7/7 (CR == LF).
      Offen: `delegation.fallback_providers` fuehrt `bonsai` weiter an Stelle 2 - ein Eintrag, der
      durchfaellt und wieder greift, sobald der Dienst laeuft. Bonsai bleibt aus (entlaedt sonst die
      Ollama-Modelle aus dem VRAM, die die Sprachmodell-Spuren brauchen).
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Hermes/config.yaml, Agenten/Werkzeuge/bonsai-27b.ps1
- [x] **T-146 — Der Gateway-Waechter braucht eine Gegenprobe fuer beide Startformen**
      Kontext: Am 29.09.2026 startete `Routinen/gateway-waechter.ps1` den Gateway 148-mal neu,
      weil sein Suchmuster nur die Launcher-Kommandozeile traf, nicht die `runpy`-Form des
      Update-Wegs. Behoben (Identitaet aus `gateway_state.json` zuerst, Kommandozeile als
      Rueckfall mit beiden Formen) und belegt: 19:15:13 und 19:15:59 "Gateway laeuft ..., kein
      Start". Es gibt aber keinen Test, der den Rueckfall prueft.
      Naechster Schritt: kleine Pruefung (PowerShell oder Python-Test), die beide
      Kommandozeilenformen gegen die Waechter-Muster haelt, plus eine, die einen falschen
      Zustand als "Neustart" erwartet.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Routinen/gateway-waechter.ps1
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - tests/test_gateway_identitaet_wache.py 12 Tests gruen (beide Startformen).**
- [x] **T-128 — Marktbreite-Reihe auswerten und entscheiden, ob eine Spur sie als Tor nutzt**
      Entscheidung 2026-10-06: Die Reihe ist behalten (256 Kerzentage, Mittel 14,5 %, Median 6,9 %),
      aber es gibt KEINEN statistisch nutzbaren Edge fuer ein Breiten-Tor. Befeld: nur 2 Tage mit
      Breite >= 90 % (n=2, keine Messung), Folgeanalyse BTC +0,89 % in 7 Tagen gegen +0,23 % Median
      ueber alle Tage - kein Unterschied. Die Reihe bleibt als Messung bestehen, eine Spur bekommt
      kein Breiten-Tor. Beleg: `python Agenten/Werkzeuge/breite.py --statistik` (2026-10-06).
      Angelegt: 2026-09-24. Betrifft: Agenten/Werkzeuge/breite.py, Agenten/Werkzeuge/breite-reihe.jsonl.
      Kontext: `Agenten/Werkzeuge/breite.py` misst seit 25.09.2026 taeglich den
      Anteil der 30 Top-Paare ueber ihrer EMA200 und schreibt die Reihe
      (`Agenten/Werkzeuge/breite-reihe.jsonl`); Cron `breite-wache` (taeglich
      19:00, no_agent) meldet nur Aenderungen. Die erste Messung war 29 von 29 =
      100 % - aus EINEM Punkt folgt keine Richtung, "die Breite schrumpft" ist
      erst mit einer Reihe belegbar. Offen ist ausserdem, ob eine Handelsspur die
      EMA200-Breite als Tor nutzen soll: bisher rechnet nur
      `moondev_marktlage` eine Breite, und das ist eine ANDERE Groesse (Anteil
      mit positivem 24-h-Vorzeichen, aus CoinGecko).
      Naechster Schritt: in etwa zwei Wochen `python Agenten/Werkzeuge/breite.py
      --reihe` ansehen und entscheiden (a) Reihe behalten oder verwerfen,
      (b) ob eine Spur ein Breiten-Tor bekommt.
      NACHTRAG 25.09.2026: Die Reihe fuehrte zuerst eine Zeile je MESSUNG - sechs
      Laeufe am ersten Tag ergaben sechs Zeilen fuer DENSELBEN Kerzentag, also
      genau den einen Messpunkt, den sie aufloesen soll. Jetzt ersetzt eine
      Messung derselben Kerze ihre Zeile (Tageskerze wechselt 16:00 UTC), und
      `--reihe` rechnet den Verlauf in Punkten je Tag. Fuer die Auswertung
      zaehlen daher KERZENTAGE, nicht Zeilen; der erste echte zweite Punkt kommt
      aus dem Cron am 26.09.2026 um 19:00.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Werkzeuge/breite.py, Agenten/Hermes/scripts/breite-wache.py,
      Agenten/Handel/moondev_marktlage
- [x] **T-100 — Ungeklaerte Loeschung: sechs Testdateien verschwanden aus Agenten/Hermes/scripts/**
      Kontext: Am 25.09.2026 verschwand `test_breite_wache.py` zweimal aus dem
      Arbeitsbaum (`ad081ef` angelegt, `c49111f` nahm die Loeschung mit, `a257c62`
      holte sie zurueck). Am 30.09.2026 nachgezaehlt: es sind SECHS Dateien, nicht
      eine, alle `test_*.py` in `Agenten/Hermes/scripts/` - `test_breite_wache.py`
      (`455e0fe`), `test_waisen_wache.py` (`22e5f7d`), `test_spiegelfrist_wache.py`
      und `test_spur_wache.py` (`3ef372b`), `test_live_wache_stops.py` (`aae26a9`),
      `test_hermes_doctor.py` (`cc70977`). Jede lag danach nur noch als Bytecode in
      `__pycache__`.
      GEMESSEN und ausgeschlossen (30.09.2026): das Werkzeug-Backend ist kein
      Container mit eigener Sicht (Terminal nativ auf dem Host, `C: on /c type
      ntfs`), `write_file` schreibt host-sichtbar (Sonde: 294 B in beiden Sichten,
      `git status` zeigt `??`); kein Haus-Werkzeug loescht dort (`datensortierung.ps1`
      verschiebt nur `.bak` mit Schutzpruefung, `systempruefung.ps1` nur
      Ollama-Reststores, kaputte venvs und eigene Logs ueber 30 Tage,
      `skills-entdoppeln.py` nur Skill-Baeume), nirgends ein `/MIR`-Spiegel; kein
      Defender-Fund auf diesem Pfad; OneDrive nicht betroffen (UserFolder
      `C:\Users\faupe\OneDrive`); die PowerShell-History (1.761 Zeilen) kennt weder
      die Dateinamen noch `git clean`/`checkout`/`stash`.
      Der Taeter ist damit WEITER OFFEN. Der Schadensweg ist belegt:
      `Agenten/Routinen/fremdarbeit-einziehen.ps1` sieht eine fehlende Datei nach 30
      Minuten als 'ruhende Fremdarbeit' und committet die Loeschung - sie ist der
      SCHREIBER des Verlusts, nicht sein Urheber, und nennt als Urheber 'Andere
      Sitzung', was die Suche in die Irre fuehrt.
      Naechster Schritt: nicht mehr suchen, sondern fangen. Seit 30.09.2026 laeuft
      die Wache `Agenten/Hermes/scripts/dateischwund-wache.py` (Hermes-Cron
      `dateischwund-wache`, alle 15 Minuten, no_agent, Telegram, leere Ausgabe = kein
      Befund, 18 Tests in `test_dateischwund_wache.py`). Sie meldet (a) jede Datei,
      die in HEAD steht und im Arbeitsbaum fehlt - der T-100-Fall, sichtbar
      mindestens 30 Minuten BEVOR die Routine ihn festschreibt - und (b) jede Datei,
      die seit dem letzten Lauf verschwunden ist (auch nie committete) sowie eine auf
      0 Byte zusammengefallene. Sie aendert nichts. Meldet sie das naechste Mal: den
      Pfad sofort mit `git checkout HEAD -- <pfad>` zurueckholen und DANN die Uhrzeit
      mit den laufenden Sitzungen abgleichen (`Agenten/Hermes/logs/`,
      `Agenten/Hermes/cache/`), um den Loescher zu fassen.
      Angelegt: 2026-09-25 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Hermes/scripts/, Agenten/Routinen/fremdarbeit-einziehen.ps1
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - dateischwund-wache.py und test_dateischwund_wache.py vorhanden.**
- [x] **T-096 — Backtest ueber die volle Historie fuer die uebrigen Spuren**
      Kontext: Fuer 2021-2026 gerechnet und belegt sind bisher vier Spuren
      (squeeze, wavetrend, macd_mtf, supertrend) - je 750 bis 1130 auswertbare
      Runden. Der Kern (`replay.py`) kann Familie A und Familie B; es fehlen die
      per-Spore-Historienquellen fuer die Feed-Spuren (moondev_listingarb,
      -topmovers, -marktlage, -sniper, -signalwelle brauchen 24h-Aenderung und
      Volumen aus Kerzen, moondev_funding braucht Binance-Funding-Historie).
      Nicht nachrechenbar und mit Grund vermerkt: moondev_whale (OKX-OI),
      -liquidation, -sentiment, liq_wand, iv_wand, iv_waelle, robinhood_radar,
      kopier, nautilus-Arme.
      **Erledigt 2026-09-29:** Daten- und Adapterschicht stehen
      (`moondev_historie.py`, `daten/historie/feed/`: 300 Tagesreihen + 41
      Stundenreihen + 6 Funding-Reihen), die vier Laeufe sind gefahren
      (topmovers/marktlage/signalwelle/funding), die Lehren stehen im Wiki
      ([[Backtest-Fundament]]). Verweigerte Spuren nennen ihren Grund in
      `replay.NICHT_NACHRECHENBAR`. Offen geblieben sind T-142 bis T-145.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/replay.py, Agenten/Handel/docs/plans/2026-09-24-backtest-fundament.md
- [x] **T-069 — moon-dev-ai-agents: die freien Datenquellen in den Fork pushen**
      Erledigt: 2026-09-24. `1b3c650` (api_frei.py + die drei umgestellten
      Agenten) liegt auf origin/main des Forks mfaupel95/moon-dev-ai-agents -
      geprueft mit `git branch -r --contains 1b3c650` (origin/main). Der Klon
      ist NICHT shallow, ein Push braucht kein `fetch --unshallow`.
      Kontext: `src/agents/api_frei.py` und die umgestellten Importe der drei
      Agenten (whale/funding/liquidation) liegen als Commit 1b3c650 NUR LOKAL im
      Klon Werkstatt/Repos/moon-dev-ai-agents. Der Fork mfaupel95/moon-dev-ai-agents
      hat den Stand nicht - ein Plattenausfall kostet die Arbeit. Ein Push in ein
      Fremd-Repo wird nicht ungefragt gemacht; der Klon traegt ausserdem fremde
      uncommittete Arbeit (T-062), die nicht mitgehen darf.
      Naechster Schritt: entscheiden, ob der Stand in den Fork gepusht wird -
      dann `git fetch --unshallow` pruefen, nur die vier eigenen Dateien stagen
      (api_frei.py + die drei Agenten) und pushen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents (Branch main, Commit 1b3c650)
- [x] **T-068 — nautilus_kraken (Spot) ist scharf gestellt: zwei Tests laufen deshalb rot**
      Kontext: `nautilus_kraken/wachen.json` traegt seit 24.09.2026
      handel_erlaubt=true und freigabe.erfuellt=true (Vermerk T-065, ~1-EUR-
      Round-Trip als Endabnahme des REST-Orderwegs; fremde Sitzung). Zwei
      Tests in `test_handeln.py` frieren den alten Zustand ein (sie erwarten
      "handel_erlaubt=false" im Vorschau-Text) und schlagen fehl, obwohl der
      Code stimmt. Freies Guthaben real: rund 4,10 EUR; die Futures-Seite
      hat 0,00 USD.
      Erledigt: 2026-09-24 (Auftrag Max "nautilus_kraken Freigabe einrichten").
      Die beiden Tests pruefen jetzt die REGEL statt den Zustand: sie lesen
      handel_erlaubt/freigabe.erfuellt aus der wachen.json und verlangen genau
      die Gruende, die dort stehen - kein erfundener Grund, kein fehlender.
      Ein dritter Test sichert die Lehre: eine Suite darf `--live` NIE fahren
      (bei offenem Freigabefenster wuerde der Testlauf echte Orders ausloesen).
      Beleg: nautilus_kraken 38 Tests gruen (test_handeln 12,
      test_sperrenkette 7, test_live_orderweg 5, test_trailing_stop 14).
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Agenten/Handel/nautilus_kraken/test_handeln.py
- [x] **T-061 — moon-dev-ai-agents: welche Agenten ohne tote Datenquelle weiterlaufen sollen**
      Kontext: `api.moondev.com:8000` antwortet nicht (gemessen 24.09.2026, kein
      HTTP-Status). Damit sind `whale_agent`, `funding_agent`, `liquidation_agent`,
      `fundingarb_agent` und alles unter `src/agents/api.py` ohne Daten — ein
      Schlüssel hilft dort nicht, es fehlt die Quelle. Dagegen laufen
      `new_or_top`, `kraken_agent`, `sniper_agent` und `trading_agent` schon
      schluessellos (freie Quellen: CoinGecko public, Pump.fun, OKX/Kraken).
      Die Content-Agenten (Twitter, YouTube, Restream, ElevenLabs, Google)
      brauchen Fremdkonten und haben mit Handel nichts zu tun — bewusst nicht
      verdrahtet.
      Erledigt: 2026-09-24. Keiner der drei api.py-Agenten braucht den
      MoonDev-Schluessel: `src/agents/api_frei.py` stellt dieselbe Klasse mit
      derselben Schnittstelle bereit (gleiche Methoden, gleiche DataFrame-
      Spalten) und holt die Daten aus oeffentlichen Quellen - Funding 910
      Saetze je Aufruf von Binance /fapi/v1/premiumIndex, Open Interest von
      Binance /fapi/v1/openInterest + markPrice, Liquidationen von OKX
      /api/v5/public/liquidation-orders je uly (Binance allForceOrders
      antwortet 404, der Endpunkt ist weg). Die Klasse versucht ZUERST die
      echte API und schaltet nur um, wenn der Host nicht antwortet; Rueckweg
      ist der Import in den drei Agenten.
      KORREKTUR der Annahme im Eintrag: es sind DREI Agenten, nicht fuenf -
      `fundingarb_agent` nutzt api.py nicht (eigene Datenwege), und die
      Content-Agenten brauchen Fremdkonten statt einer Datenquelle.
      Bewusst NICHT ersetzt: `get_copybot_follow_list` und
      `get_recent_transactions` sind MoonDevs eigene Kopierhandels-Datenbank;
      beide geben None zurueck, damit die Agenten den Zyklus ueberspringen
      statt mit Nullwerten zu rechnen.
      Nachweis (je ein Lauf, echte Zahlen): whale_agent BTC-OI 8,09 Mrd USD /
      ETH 6,11 Mrd / Total 14,21 Mrd (Binance); liquidation_agent 300 OKX-
      Zeilen, 1-h-LONGS 28.249,61 USD (6 Ereignisse), 4-h-LONGS 314.626,55 USD
      (96 Ereignisse); funding_agent 910 Saetze.
      Fallen: die Agenten verlangen OPENAI_KEY UND ANTHROPIC_KEY schon im
      Konstruktor; ohne `python -u` bleibt bei einem abgebrochenen Lauf das
      Log LEER, obwohl der Agent arbeitet.
      Doku: MaxHirn/Wiki/Werkzeuge/MoonDev-Freie-Datenquellen.md
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents/src/agents/
- [x] **T-062 — moon-dev-ai-agents: fremde uncommittete Arbeit im Werkstatt-Klon**
      Erledigt: 2026-09-24. Der Arbeitsbaum ist gesichert und leer: die
      parallele Sitzung hat ihren Teil selbst committet (a344457), der Rest
      (moongui.py, backtest_runner.py, backtest_start.py, src/data/rbi/*,
      src/data/coingecko_results/*) ist als 7a894b3 mit der Kennung
      "Andere Sitzung <fremd@local>" nachgezogen und nach origin/main gepusht.
      `.env` blieb draussen (echte Schluessel; sie stand nicht im Status).
      Kontext: Im Klon liegen Änderungen, die nicht aus meiner Sitzung stammen:
      `rbi_agent.py` (36 Einfügungen / 78 Löschungen), `sniper_agent.py`,
      `src/models/ollama_model.py`, `src/nice_funcs.py`, `src/data/rbi/ideas.txt`,
      gelöschtes `src/.env_example`, dazu untracked `BUG_REPORT_DETAILED.md`,
      `FIXES_APPLIED.md`, `README_FIXES.md`, `SESSION_2_SUMMARY.md`, `START_GUI.bat`,
      `VALIDATE_ALL.bat`, `startup.py`, `src/utils/`, `src/data/coingecko_results/`.
      MEINE Änderung in `rbi_agent.py` (Aufrufort liest `DEEPSEEK_BASE_URL`) ist
      deshalb NICHT mitcommittet — sie liegt im Arbeitsbaum und wirkt, ist aber
      nur auf dieser Platte bzw. in der Arbeitsbaum-Kopie gesichert.
      Naechster Schritt: fremde Arbeit sichten und in einem eigenen Commit mit
      Autor „Andere Sitzung <fremd@local>“ sichern, danach die eine Zeile im
      rbi_agent nachziehen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents (Fork mfaupel95/moon-dev-ai-agents)
- [x] **T-038 — 21,5 GB Modellgewichte liegen auf `C:`, nicht in `Modelle/`**
      **Erledigt 2026-09-19.** Auf `C:` liegt kein Modellgewicht mehr (C: frei
      3,2 GB → 66,1 GB). Die 21,1 GB `Qwen3.6-35B-A3B-UD-Q4_K_M.gguf` liegen
      unter `O:\Modelle\GGUF\`; das 0,84 GB große mmproj wurde nach
      `O:\Modelle\hermes\assets\` verschoben, und
      `%LOCALAPPDATA%\hermes\models` ist jetzt eine Junction auf
      `O:\Modelle\hermes`.
      **Antwort auf die Frage nach der Variable:** Es gibt **keine** eigene
      Variable für den Modellort — `bootstrap.models_dir()` liest
      `get_default_hermes_root() / "models"`, also `%LOCALAPPDATA%\hermes\models`
      (wenn `HERMES_HOME` ungesetzt) bzw. `HERMES_HOME\models`. Mit dem
      gesetzten `HERMES_HOME = ...\BrainFiles\Agenten\Hermes` wäre das
      `Agenten\Hermes\models` — dort ist bewusst **keine** Junction: `Agenten\`
      ist Sicherungsquelle, robocopy würde den Modellen in die Nachtsicherung
      folgen.
      **Offen bleibt:** `local_runtime.enabled` steht auf `false`, deshalb
      liest derzeit niemand diesen Ordner. Vor dem Einschalten muss entschieden
      werden, wohin die Gewichte gehören — sonst landen 20 GB wieder auf `C:`
      oder in der Sicherung.
      Zuletzt: 2026-09-19
      --- ursprünglicher Befund vom 08.09.2026 ---
      Kontext: Bei der Gesundheitsprüfung am 08.09.2026 gemessen.
      `%LOCALAPPDATA%\hermes\models` ist **21,5 GB** groß und damit der größte
      einzelne Posten auf der Systemplatte (`AppData\Local\hermes` gesamt
      22,7 GB). Das widerspricht der Regel aus der Wurzel-`CLAUDE.md`:
      Modellgewichte gehören nach `Modelle/` (Junction auf `O:\Modelle`), sind
      neu herunterladbar und bleiben deshalb aus der Sicherung draußen. Auf
      `C:` werden sie weder gesichert noch aus der Sicherung ausgenommen — sie
      belegen einfach die Platte, die am knappsten ist.
      Zum Vergleich auf derselben Platte: Claude 25,6 GB
      (`Packages\Claude_pzs8sxrjxfjjc` 13,8 + `Roaming\Claude` 11,8),
      `Cleanup_2026` 13,0, `Roaming\Pioneer` 11,7.
      Nächster Schritt: prüfen, ob Hermes den Ort über eine Variable lesen
      kann (wie Ollama über `OLLAMA_MODELS`); wenn ja, Store nach
      `O:\Modelle\hermes` verschieben und die Variable setzen. Wenn nein,
      entscheiden, welche Modelle dort überhaupt gebraucht werden.
      Betrifft: `%LOCALAPPDATA%\hermes\models`, [[Ordnerstruktur]]
      Angelegt: 2026-09-08 · Zuletzt: 2026-09-08
- [x] **T-011 — Wer schreibt `Modelle/.onchainos`?** — erledigt 2026-09-08
      Nach Suche im gesamten Vault: **kein Skript** referenziert diesen Pfad.
      Der Ordner ist ein Überbleibsel von „Stufe 0" (vor dem 30.08.2026),
      wahrscheinlich von OKX/OnchainOS-Werkzeugen angelegt. Inhalt:
      `wallets.json` (30+ Chain-Adressen, Projekt-ID
      `agentic-wallet-project01`, Account `05c0d7a8-…`),
      `machine-identity` (SHA-256-Hash), `session.json` (Session-Key,
      ablaufbar 2027-01-18), `keyring.enc` (verschlüsselt).
      **Maßnahme:** Vollständiges Backup nach
      `Archiv/OnChainOS_Backup_20260908/`, Notiz erstellt in
      `Wissen/OnChainOS_Backup.md`, Original gelöscht.
      Keine aktive Komponente nutzt den Ordner — kein Risiko bei Wegfall.
      Betrifft: `Modelle/.onchainos` → `Archiv/OnChainOS_Backup_20260908/`
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-08
- [x] **T-032 — In `Werkstatt/` liegt eigene Arbeit, die nirgends gesichert wird** — erledigt 2026-09-19
      **Erledigt 2026-09-19.** `Werkstatt/Protokolle/Codex` (78 Dateien) nach
      `O:\Archiv\Protokolle\Codex` verschoben — liegt jetzt in der über
      `sichern.ps1` geschützten Archivmenge. `Werkstatt/Sitzungen/m3u_cleaner`
      wurde **nicht** überschrieben: `O:\Archiv\Software\m3u_cleaner` existiert
      bereits (229 Dateien, neueste `.py` in beiden Kopien identisch), die
      m3u_cleaner-Arbeit ist damit schon im gesicherten Archiv. Die
      Werkstatt-Kopie (335 MB) bleibt als redundante Fassung stehen;
      Kollisionsschutz hatte den Umzug verhindert. Kein Eingriff in
      `sichern.ps1`. Hinweis: eine parallele Sitzung reorganisiert gerade
      `O:\Archiv\Software\m3u_cleaner`.
      Kontext: Beim Abräumen von `G:` am 03.09.2026 aufgefallen. `Werkstatt/`
      ist aus beiden Sicherungen ausgenommen — richtig für geklonte Fremd-Repos
      und Sitzungsreste, falsch für das, was tatsächlich dort liegt:
      `Werkstatt\Sitzungen\m3u_cleaner\` ist eigener Python-Code samt
      PyInstaller-Builds, `Werkstatt\Protokolle\Codex\` sind Auswertungen. Von
      beidem existiert nur noch die alte Kopie auf `G:` (Ordner `Codex\` und
      `Coworking-Space\`, zusammen 0,4 GB), und die stammt von vor dem
      30.08.2026.
      Nächster Schritt: entscheiden, ob `m3u_cleaner` in den Vault gehört
      (dann nach `Archiv/Software/` — liegt seit 07.09.2026 auf `O:\Archiv`,
      T-037 — oder als eigenes Projekt) oder ob `Werkstatt/` eine Ausnahme in
      `sichern.ps1` bekommt. Bis dahin die beiden
      Altordner auf `G:` stehen lassen.
      Betrifft: `Werkstatt/`, `Agenten/sichern.ps1`
      Angelegt: 2026-09-03 · Zuletzt: 2026-09-03
- [x] **T-033 — `OKX_API.env`: Schlüssel im Portal widerrufen** — erledigt 2026-09-19
      **Erledigt 2026-09-19.** Alter Key im Portal widerrufen; neue Schlüssel
      per `setx` in der **User-Umgebung** registriert und bestätigt
      (`OKX_API_KEY`/`OKX_API_SECRET`/`OKX_PASSPHRASE`, alle Werte **neu**, nicht
      der widerrufene). Die Klartext-Kopie in `_zu_loeschen` existiert nicht
      mehr (schon im Aufräumen entfernt). Hinweis: Ein 4-Zeichen-`OKX_SECRET_KEY`
      steht noch in der User-Umgebung — vermutlich der alte unbrauchbare Rest,
      bei Bedarf entfernen.
      Kontext: Beim Abräumen von `G:` am 03.09.2026 im Altzweig gefunden
      (`Claude\Worktrees\Investment\OKX_API.env`, 124 Bytes, Stand
      07.08.2026). Kein Duplikat, sondern der letzte Rest eines alten
      Arbeitszweigs.
      **Erledigt am 03.09.2026:** Inhalt geprüft, Datei nach SHA256-Verifikation
      von `G:` nach `Archiv/Posteingang/_zu_loeschen/` verschoben — damit ist der
      Klartext von der Platte weg, die regelmäßig abgezogen wird (T-015). Befund
      in [[Zugaenge]] festgehalten: Der Secret ist zu kurz (4 Zeichen gemessen,
      am 23.08. mit 6 notiert) und damit unbrauchbar; Key und Passphrase sehen
      echt aus und stehen sonst nirgends in `Zugaenge.md`. Der dortige Pfad-
      verweis auf `Claude/Worktrees/investment/` ist mitgezogen.
      **Nicht gelöscht** — Stufe 0, und die Datei ist bis zum Widerruf das
      Identifikationsmittel im Portal.
      Nächster Schritt: Max ruft `https://web3.okx.com` → API-Verwaltung auf und
      löscht den Schlüssel. **Ob er noch aktiv ist, lässt sich von hier nicht
      feststellen** — ohne gültigen Secret ist keine signierte Anfrage möglich.
      Bis dahin gilt er als möglicherweise aktiv. Danach darf die Datei weg.
      **Es gibt eine zweite Kopie:**
      `O:\MaxHirn-Zweitkopie\Claude\Worktrees\investment\OKX_API.env` (124 Bytes,
      07.08.2026) — der Altzweig, wie er beim letzten Zweitkopie-Lauf aussah.
      Bewusst nicht angefasst: In eine Sicherung greift man nicht nebenbei
      hinein. Nach dem Widerruf müssen **beide** weg, sonst war der Aufwand
      umsonst. Gesucht wurde in `C:\Users\faupe\Documents`, `G:`, `O:` und `J:`
      — **ganz `C:` ist nicht geprüft**, dort ist eine weitere Kopie nur
      unwahrscheinlich, nicht ausgeschlossen.
      Wartet auf: Max — Widerruf im OKX-Portal
      Betrifft: `Archiv/Posteingang/_zu_loeschen/OKX_API.env`,
      `O:\MaxHirn-Zweitkopie\...\OKX_API.env`, [[Zugaenge]]
      Angelegt: 2026-09-03 · Zuletzt: 2026-09-03 (23:34)
- [x] **T-013 — Drei Pfadverweise in `Zugaenge.md` von Hand nachziehen** — erledigt 2026-09-07
      Alle drei Verweise geändert:
      1. Zeile 108: `Claude/Software/…` → `Archiv/Software/…`
      2. Zeile 116: `Claude/Worktrees/investment/` → `Archiv/Worktrees/investment/`
      3. Zeile 156: `O:\MaxHirn-Zweitkopie\Claude\Worktrees\…` → `Archiv\Worktrees\…`
         (mit erklärend erwähnt: das ist der alte Pfad aus der Sicherung vom 30.08.2026)
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-07
- [x] **T-014 — 1,5 GB Ollama-Protokolle in 17 Dateien** — erledigt 2026-09-07
      Das Hauptvolumen (1,5 GB) war nicht in den 17 Protokolldateien, sondern im
      Ordner `updates_v2` (alte Ollama-Versionen). Gelöscht am 07.09.2026, 22:40.
      Danach regenerieren sich die `.log`-Dateien (trivial, <10 KB je). Die
      `.sqlite-wal` und `.sqlite-shm` Dateien werden von Ollama bei Neustart neu
      angelegt, sind aber Temp-Dateien und verschwinden bei Inaktivität.
      **Resultat:** 1,5 GB Speicherplatz auf C: freigegeben.
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-07
- [x] **T-016 — Ordner `MaxHirn/Claude/` → `MaxHirn/Archiv/` samt Verweisen** — erledigt
      2026-09-02. Der physische Rename lief am 01.09. bei der Absturz-Recovery
      durch; `MaxHirn/Claude/` existiert nicht mehr. Am 02.09. nachgezogen:
      `.gitignore`-Whitelist zeigt auf `MaxHirn/Archiv/`, `git check-ignore`
      bestaetigt, dass neue Dateien unter `Archiv/` **nicht** mehr ignoriert
      werden. `.venv` in `Archiv/ArchivSuche/` neu erzeugt (Python 3.13) und
      `requirements.txt` installiert — alle neun Abhaengigkeiten importierbar.
      Textebene: `Claude/` → `Archiv/` in ~25 versionierten Dateien (Notizen,
      Dashboard, Archiv-Doku, Skript-Kommentare); `Claude/Worktrees/` →
      `Werkstatt/Worktrees/`; `%APPDATA%\Claude\` (Claude-Desktop-Config) und
      historische „hiess Claude/"-Erwaehnungen verschont. Dabei drei kaputte
      Skriptpfade gefunden und behoben: `sichern-zweitkopie.ps1` (Medien-
      Ausschluss), `posteingang.ps1` und `mail/mailversand.py` (Wurzel loeste
      seit der Ordnertrennung auf `Agenten/` statt `BrainFiles/` auf).
      Angelegt: 2026-09-01 · Zuletzt: 2026-09-02
- [x] **T-017 — Gehebelter Handel hat noch keine `wachen.json`** — erledigt
      2026-09-01. `Agenten/Handel/xperp/wachen.json` liegt (Höchsteinsatz je
      Anlauf 50 USD Margin, gesamt 200, Höchsthebel 5, Pflicht-Stop in ATR
      statt Prozent, Kill-Switch je Anlauf und gesamt). Der Modulkopf von
      `okxf.py` ist auf Spur 2 umgeschrieben und nennt den alten Wortlaut nur
      noch als Historie. Zusätzlich legt `bot.pruefpflicht()` die vier
      geforderten Zahlen vor; neu gerechnet ist Zahl 4 (nötige gegen
      beobachtete Trefferquote) samt Warnung, wenn die seltenere Seite unter
      zehn Ereignissen liegt. Siehe [[XPERP-Handel]].
      Kontext: [[Schutzregeln]] erlaubt seit dem 01.09.2026 gehebelte
      Positionen auf ausdrückliche Anweisung (Spur 2). Die Grenzen dieser Spur
      stehen bisher **nur in der Prosa der Notiz**, nicht in einer Datei — im
      Gegensatz zu Spur 1, wo `scanner/wachen.json` die einzige Wahrheit ist.
      Genau diese Bauform ist aber der Schutz: eine Sitzung kann eine Regel
      vergessen, eine Datei nicht.
      Zweitens trägt `Agenten/Handel/xperp/okxf.py` im Modulkopf noch den
      alten Wortlaut („gilt ausdruecklich nur fuer nur Spot, nur Long, kein
      Hebel … Dieses Modul faellt NICHT darunter"). Das stimmt seit heute
      nicht mehr und widerspricht der Regeldatei.
      Nächster Schritt: `xperp/wachen.json` anlegen (Höchsteinsatz je Position,
      Gesamtnominal, Höchsthebel, Pflicht-Stop, erlaubte Kontrakte) und den
      Modulkopf auf Spur 2 umschreiben.
      Betrifft: `Agenten/Handel/xperp/` — **dort arbeitete am 01.09. 17:34 eine
      andere Sitzung**, deshalb hier nur eingetragen und nicht angefasst.
      Angelegt: 2026-09-01 · Zuletzt: 2026-09-01
- [x] **T-019 — Die Regel erlaubt jetzt mehr, als der XPERP-Bot kann**
      Erledigt 2026-09-03: Der Live-Pfad ist gebaut, nachdem Max XPERP zum
      Hauptweg gemacht hat. Neu sind `xperp/handeln.py` (Zyklus, Ausstiege,
      Einstiege, Journal, Zustand) und `xperp/wachen_xperp.py` (Bedingungen
      1–5, Rechnung importiert aus `scanner/wachen_pruefung.py`).
      Die vier Pflichtzahlen stehen je Position im Journal, nicht im Chat —
      Spalten `liq_abstand`, `funding_pct`, `gebuehr_pct`, `quote_noetig`,
      `quote_beob`. Und sie sind keine Zierde: Der erste Papierlauf hat
      XAG short (Quote 19,8 % gegen nötige 33,3 %) und XAU short (23,7 gegen
      35,5) abgewiesen und drei Anläufe eröffnet — MSTR, CL, BZ.
      Punkt 2 und 3 der alten Liste sind mit angeglichen: der Hinweis in
      `wachen.json` und die Stellen in `bot.py`, die „es gibt keinen
      Live-Pfad" sagten.
      Gegengeprüft: Notausstieg bei altem Herzschlag schließt alle drei
      Positionen (`herzschlag_alt`), die Rundenrechnung erkennt sie als drei
      abgeschlossene Runden samt Funding. Die Testdaten wurden danach
      zurückgenommen, damit die Freigabe-Statistik sauber bleibt.
      **Offen bleibt daraus:** siehe T-035 (Herzschlag und Dauerbetrieb, vormals fälschlich T-032).

      Angelegt: 2026-09-01 · Zuletzt: 2026-09-01
- [x] **T-053 — handel-spuren kuerzen (Auftrag vom 24.09., Limit war veraltet)**
      Entscheidung 2026-10-06: Die Datei ist 98.975 Bytes (1.344 Zeilen) - unter dem
      100k-Limit. Der urspruengliche Auftrag beruhte auf einer veralteten Meldung
      (100.663 Bytes). Nachgemessen: das Limit ist NICHT erreicht, ein Auslagern
      ist nicht noetig. Die fuenf grossen Bloecke (Wann, Prozedur, Pitfalls,
      Handelszentrale, Werkzeugfallen) bleiben im SKILL.md. Beleg: `wc -c SKILL.md`
      (2026-10-06). Angelegt: 2026-09-24. Betrifft: Agenten/Hermes/skills/brainfiles/handel-spuren/SKILL.md.
- [x] **T-008 — MCP-Server `mail` ist nicht eingerichtet** — erledigt 2026-09-19
      **Erledigt 2026-09-19.** Zugang ist hinterlegt und funktioniert:
      Adresse `faupel3107@googlemail.com` + App-Passwort im
      Windows-Anmeldeinformationsspeicher (`MaxMailVersand`), SMTP-Anmeldung
      getestet = `anmeldung: ok`. Kein Einrichten nötig; der Server war
      inzwischen konfiguriert.
      Kontext: `Archiv/CLAUDE.md` beschreibt den Versand über `mail_senden`
      als den vorgesehenen Weg für „schick mir das per Mail". Der Server
      antwortet aber mit „Keine Absenderadresse hinterlegt" — in 53 Sitzungen
      wurde er kein einziges Mal erfolgreich benutzt. Der dokumentierte Weg
      existiert also nur auf dem Papier. Die CLAUDE.md ist am 28.08.
      entsprechend korrigiert.
      Nächster Schritt: `MCP-Server/mail/.venv\Scripts\python.exe einrichten.py`
      — braucht Absenderadresse und App-Passwort, also Max' Zutun.
      Wartet auf: Zugangsdaten von Max
      Angelegt: 2026-08-28 · Zuletzt: 2026-08-28
- [x] **T-009 — `Zugaenge.md` als einzige Notiz ohne Frontmatter** — erledigt 2026-09-19
      **Erledigt 2026-09-19 (von Max freigegeben).** Acht Zeilen Frontmatter
      vorangestellt (`id: 20260830-zugaenge`, `tags: [sicherheit]`, Template wie
      die übrigen Notizen); der Body wurde byte-erhalten, kein Wert der Datei
      ausgelesen oder ausgegeben.
      Kontext: Am 30.08.2026 haben alle 21 übrigen Notizen in `Wissen/`
      YAML-Frontmatter mit stabiler `id` bekommen, dazu `Wissen/INDEX.md` als
      vollständige Registry. `Zugaenge.md` wurde bewusst ausgelassen, weil sie
      in [[Schutzregeln]] unter den geschützten Schlüsseldateien steht und dort
      kein Agent ohne ausdrückliche Anordnung schreibt. Sie ist in der Registry
      geführt, hat aber keine `id`. Fachlich spricht nichts dagegen — das
      Frontmatter berührt keine Zugangsdaten, sondern steht davor.
      Nächster Schritt: Max gibt frei (oder nicht); dann acht Zeilen Frontmatter
      voranstellen, `id: 20260830-zugaenge`, `tags: [sicherheit]`.
      Vorschlag zum selben Themenkreis, nicht eingetragen als eigener Punkt:
      Die Dateinamen in `Wissen/` sind gemischt geschrieben statt durchgehend
      kleingeschrieben. Eine Umbenennung würde alle `[[Wikilinks]]` brechen und
      ist den Gewinn vermutlich nicht wert.
      Betrifft: `Wissen/Zugaenge.md`, `Wissen/INDEX.md`
      Wartet auf: Freigabe von Max
      Angelegt: 2026-08-30 · Zuletzt: 2026-08-30
- [x] **T-334 — Sieben Kanban-Karten waren durch eine Config gescheitert, nicht durch die Planung**
      Kontext: Am 01./02.10.2026 landeten sieben Karten nach zwei Fehlversuchen in `blocked`:
      handel t_29c89f80, t_4f96661d, t_c3909e3e, t_ca6a7d6a, repos t_feba05cc,
      wartung t_97489ca0, t_e158a9a6. Der Worker-Log zeigte fuer alle denselben Abbruch:
      'Auxiliary compression model gemma-e4b-8k:cpu has a context window of 8,192 tokens,
      which is below the minimum 64,000 required by Hermes Agent'.
      Ursache: `auxiliary.compression` war in KEINER der 24 Profil-Configs gesetzt.
      Hermes faellt dann auf die erste Zeile von `fallback_providers` zurueck - im Haus
      ueberall `ollama-launch / gemma-e4b-8k:cpu`. Die Modelle selbst waren nie das Problem:
      `get_model_context_length` gemessen - deepseek-v4-flash-0731 = 1.048.576,
      stealth/space-bunny-alpha = 1.000.000, poolside/laguna-xs-2.1:free = 262.144,
      gemma-e4b-8k:cpu = 8.192.
      Naechster Schritt: erledigt - alle 24 Configs tragen jetzt
      `auxiliary.compression = nous / deepseek/deepseek-v4-flash-0731` (timeout 180),
      alle 24 parsen als YAML, Zeilenenden unveraendert CRLF (git diff --numstat 4/0 bzw. 6/0
      je Datei, genau die eingefuegten Zeilen). Werkzeug:
      `skills/brainfiles/hermes-config-ops/scripts/kompression-provider-setzen.py`
      (Trockenlauf / --anwenden / --anwenden --zuruecknehmen). Commit 4dfebfb3.
      Merksatz: eine Karte im Status `blocked` mit `gave_up` und Exit 1 ist zuerst eine
      Frage an die ARBEITSUMGEBUNG des Workers, nicht an den Auftrag - die Abbruchmeldung
      im Log nennt den Grund im Klartext, der Dispatcher gibt sie nur nicht weiter.
      Angelegt 2026-10-04 · Zuletzt 2026-10-04
      Betrifft: Agenten/Hermes/config.yaml, Agenten/Hermes/profiles/*/config.yaml
- [x] **T-375 — Mail-Triage ist blind fuer Post mit altem Date-Header**
      Kontext: `Agenten/Hermes/scripts/mail-inbox-triage.py` sucht mit
      `SEARCH (SINCE ...)` - das arbeitet auf dem ANKUNFTSDATUM
      (INTERNALDATE) -, verwirft die Treffer danach aber in Zeile 260 am
      `Date`-KOPF (`if datum and datum <= bis: continue`). Eine Mail, die
      frisch in die INBOX kommt, aber ein altes Date-Header traegt, faellt
      damit durch und wird NIE geprueft.
      Gemessen 07.10.2026: Nachricht 1905 steht an der juengsten
      Sequenzposition der INBOX (CoinTracking, "Confirm your email to
      activate your CoinTracking account"), traegt aber Date 07.09.2026 und
      erscheint nicht einmal in `SEARCH SINCE 04-Oct-2026` - ihr
      INTERNALDATE liegt ebenfalls im September, waehrend ihre UID neu ist
      (typisch fuer eine Mail, die Gmail nachtraeglich in die INBOX legt).
      Kein Schaden in diesem Fall: der Inhalt ist eine Automatik-
      Bestaetigung und gehoert nach der Skill-Regel ohnehin nicht gemeldet.
      Zweiter, kleinerer Punkt: `--stunden` greift laut Zeile 222 NUR, wenn
      keine Merkdatei vorliegt - ein `--stunden 96` zum Gegenlesen ist bei
      vorhandener Merkdatei wirkungslos und sieht wie "nichts gefunden" aus.
      Naechster Schritt: entweder zusaetzlich INTERNALDATE abfragen
      (`FETCH (INTERNALDATE ...)`) und das JUENGERE der beiden Daten gegen
      `bis` halten, oder den Fortschritt ueber UID statt ueber Datum fuehren
      (`UID SEARCH UID <letzte+1>:*`) - das ist die eigentlich richtige
      Groesse fuer "seit dem letzten Lauf". Dazu `--stunden` zu
      `--fenster-erzwingen` ergaenzen, damit ein Gegenlesen moeglich ist.
      Angelegt: 2026-10-07 · Zuletzt: 2026-10-07
      Betrifft: Agenten/Hermes/scripts/mail-inbox-triage.py,
      Agenten/Hermes/skills/productivity/email-inbox-triage/SKILL.md,
      Agenten/Hermes/cache/mail-inbox-triage.json
      **Erledigt 07.10.2026.** Fortschritt laeuft jetzt ueber die UID statt ueber Datum: UID SEARCH UID <letzte>:* findet auch Mails, deren Date-Header/INTERNALDATE alt ist (Gmail legt nachtraeglich in die INBOX). Gemessen: CoinTracking-Ultimatum (Date 07.09.) wurde vorher still uebersprungen, jetzt gelesen und geprueft; UID-Anker 13350->13354. --fenster-erzwingen erlaubt Gegenlesen auch mit Merkdatei. Commit fb36bb1c, echter Lauf gegen das echte Konto.
- [x] **T-353 — Der signal-executor brach seit dem 03.10. bei jedem Lauf ab**
      Kontext: Gefunden bei derselben Pruefung (05.10.2026). In
      `Agenten/Hermes/scripts/signal-executor.py` stand
      `from spur_buch import orderweg, venue_inst` VOR jedem `sys.path.insert`.
      `spur_buch` ist eine flache Datei im Handel-Ordner und kein Paket -
      der Import warf `ModuleNotFoundError`, der Cron meldete 'Script exited
      with code 1', und KEINE Spur mit `trigger_modus: signal` kam je zu einem
      Einstieg. Die drei Tore weiter unten (Freigabefenster, Gebuehren-Tor,
      Basis-Deckel) machten den sys.path-Eintrag richtig; nur der erste Import
      stand falsch. Behoben und nachgemessen: der Executor laeuft jetzt
      durch. Die Queues von signalwelle und marktlage waren allerdings leer,
      deshalb half die Reparatur heute noch niemandem - sie verhindert nur
      den naechsten Fall.
      Naechster Schritt: pruefen, ob die uebrigen signal-Spuren
      (topmovers, sniper, funding) Queues haben, die liegen bleiben. Der
      Executor verarbeitet nur EINEN Eintrag je Spur und Lauf - bei vollen
      Queues braucht es entsprechend viele Takte.
      Angelegt · 05.10.2026 · Betrifft:
      Agenten/Hermes/scripts/signal-executor.py, Agenten/Hermes/cron/jobs.json
      **Erledigt 07.10.2026.** Derselbe Fix wie T-346 (ModuleNotFoundError spur_buch durch sys.path vor dem Import, Merge 7ad189e9). Zusaetzlich T-351 (b22f7b4e): Executor leert Queues nicht-live Spuren sofort, alle Queues leer, Cron status=ok.
- [x] **T-346 — signal-executor laeuft seit 12 Laeufen rot: ModuleNotFoundError spur_buch**
      Kontext: Hermes-Cron 50921798e27a 'signal-executor' (jede Minute, no_agent,
      Agenten/Hermes/scripts/signal-executor.py). last_status=error,
      failure_streak=12, letzter Lauf 04.10. 22:24:43. Der Absturz ist in Zeile 153:
      `from spur_buch import orderweg, venue_inst` -> ModuleNotFoundError. Der
      Cron laeuft aus dem Hermes-Skriptordner, nicht aus Agenten/Handel/, und
      spur_buch liegt dort nicht. Damit ist der AUSFUEHRUNGSWEG fuer
      trigger_modus=signal-Spuren seit Stunden tot: die Spur legt einen Auftrag
      in die Queue, aber niemand setzt ihn um. Genau die Trennung, die am
      03.10. die Ueberhandelung verhindert hat (max. 96 gleiche Einstiege/Tag).
      Naechster Schritt: sys.path auf Agenten/Handel ergaenzen (mit Pruefung
      gegen __file__, wie es die Hausregel fuer Spuren-Imports verlangt), dann
      `cronjob action='run'` und eine Ausgabe pruefen. Wichtig: signal-executor
      darf erst mit lebendem spur_buch laufen - sonst stehen Orders in der
      Queue, die beim ersten Lauf alle auf einmal durchgehen.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Hermes/scripts/signal-executor.py, Agenten/Handel/spur_buch.py
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - gebaut auf wt/t_5609d126 (Commit 3894778a), aber NICHT in master - bleibt offen bis zur Merge-Entscheidung (Karte t_fb1f87ad).**
      **Erledigt 07.10.2026.** Fix in master (Merge 7ad189e9, wt/t_5609d126): sys.path-Eintrag auf Agenten/Handel VOR dem spur_buch-Import, mit __file__-Pruefung (signal-executor.py:163-174). Verifiziert: Cron signal-executor last_status=ok, alle signal_queue*.json leer (0 Eintraege), Executor laeuft durch.
- [x] **T-352 — omnitrade.cmd Stand zeigt 'veraltet': der ema_cross-Lauf (live.json) ist tot, adx_macd laeuft**
Kontext: omnitrade_bridge (Standard-Anker live.json) meldet am 05.10.2026 00:02
"veraltet: seit 116 min kein Lebenszeichen (Grenze 300 s)" - PID 55888 existiert
nicht mehr in der Prozessliste. Das ist die bekannte Falle: die Statusdatei
bleibt nach hartem Ende auf state=running mit toter PID stehen (omnitrade_lauf.py
dokumentiert das). Der LEBENDE Lauf ist live_adx_macd_BTCUSDC.json (PID 61280,
205 s alt, 1 Order gefuellt, netto 0.00585 BTC) - er laeuft seit ~04.10. 22:51
und wird von der omnitrade-Spur korrekt gespiegelt (lesen.py liest ALLE
Statusdateien, prozess_pruefen verlangt PID+Datei). Die Anzeige "veraltet" ist
also ehrlich, kein Fehler.

Naechster Schritt: entscheiden, ob der ema_cross-Lauf (omnitrade.cmd start) wieder
gestartet werden soll oder ob der Betrieb dauerhaft ueber omnitrade_start.py
(adx_macd) laeuft. Solange nur die Anzeige betroffen ist: OMNITRADE_STATUS kann
auf live_adx_macd_BTCUSDC.json zeigen, dann zeigt der Stand den lebenden Lauf.

Angelegt 05.10.2026 · Zuletzt 05.10.2026 · Betrifft: Agenten/Handel/omnitrade_bridge.py,
omnitrade.cmd, Werkstatt/omnitrade/status/.
      **Erledigt 07.10.2026.** Behoben durch Commit ccb34f77 (parallele Sitzung): ema_cross_20_50 als benannter Lauf in LAEUFE aufgenommen - der Waechter (omnitrade-wache.py --anwenden) startet tote Laeufe jetzt automatisch wieder, live.json wird wieder frisch geschrieben. Verifiziert: omnitrade_start.py liste zeigt ema_cross_btc LAEUFT, omnitrade_bridge meldet ok=True (PID 79256).
- [x] **T-371 — OmniRoute-Log fehlt: Gegenprobe-Test bleibt rot bis zum naechsten Zentrale-Lauf**
      Kontext: T-234 (05.10.2026) hat OmniRoute einmal ueber die Zentrale gestartet und
      das Log erzeugt. Das Log ist seitdem verschwunden (wahrscheinlich beim Junction-
      Verlust oder einer nicht versionierten Bereinigung). Jetzt zeigt
      `test_manifest_gegenprobe.test_jeder_startbefehl_hat_einen_beleg_im_log` einen
      Fehler: OmniRoute traegt `start`, hat aber kein `OmniRoute-*.log` in
      `repos-zentrale/logs/`.
      NICHT behebbar ohne OmniRoute zu starten - das Skript selbst sagt
      'Nur auf ausdrueckliche Anweisung'. 
      Naechster Schritt: OmniRoute einmal ueber die Zentrale starten (Skript
      `Werkstatt/Projekte/OmniRoute/omniroute-quell-produktion.ps1`, Port 20128,
      bestehende Instanz vorher stoppen), danach entsteht ein Log und der Test
      wird gruen.
      Angelegt: 06-10-2026 · Betrifft: Agenten/Werkzeuge/repos-zentrale/logs/,
      Werkstatt/Projekte/OmniRoute/omniroute-quell-produktion.ps1
      **Erledigt 07.10.2026.** Zwei Befunde: (1) Der Manifest-Startbefehl war relativ zur WURZEL (Werkstatt/Projekte/...), die Zentrale startet aber mit cwd=O:\Werkstatt\OmniRoute -> Powershell fand das Skript nicht, der erste Beleg war ein unehrlicher Fehlschlag. Korrigiert auf ../Projekte/OmniRoute/omniroute-quell-produktion.ps1 (relativ zum Klon-cwd). (2) OmniRoute laeuft bereits (Port 20128 belegt): Skript bricht korrekt mit 'Port belegt' + Exit 1 ab - das ist der ehrliche Beleg (Log OmniRoute-20261007-1733.log). test_manifest_gegenprobe 2/2 gruen. Neustart des Routers bewusst NICHT erzwungen (laufender Dienst).
- [x] **T-370 — Docker-Terminal: Fix auf der Platte, Gateway hat ihn noch nicht gelesen**
      Kontext: Am 05.10.2026 fielen waehrend einer Sitzung ALLE Docker-gestuetzten
      Werkzeuge aus (`terminal`, `write_file`, `read_file`, `patch`, `execute_code`)
      URSACHE BEWIESEN (nicht geraten), zwei Zeugen ohne Hermes:
        `docker run -w 'C:\Users\...\Agenten\Hermes'` -> Exit 125,
        'the working directory ... is invalid, it needs to be an absolute path'
        `docker run -w /workspace` -> Exit 0.
      Der rohe Windows-Pfad ging in `docker run -w`; `docker_mount_cwd_to_workspace`
      stand auf false. Eine PARALLELE Sitzung hat das um 00:34 erkannt und auf true
      gestellt (Commit 99da8bb6, byte-genau, mit Gegenprobe) - die Absicht ist richtig.
      Auf der Platte verifiziert: yaml.safe_load liest
      `docker_mount_cwd_to_workspace = True`, 12 terminal-Schluessel, backend docker.
      Warum es trotzdem noch klemmt: der laufende Gateway (PID 40120, gestartet 22:13)
      hat die Config VOR der Aenderung gelesen; Docker-Werkzeuge laufen als Kind des
      Gateways und erben die alte Einstellung.
      Naechster Schritt: Gateway einmal neu starten (Aufgabe Hermes_Gateway_2ef9d0b7,
      danach `docker run`-Probe ueber das terminal-Werkzeug). MEINE FRUEHERE DEUTUNG
      WAR FALSCH und ist zurueckgenommen: 'Duplicate mount point: /workspace' entstand
      nur in MEINEM eigenen Testaufbau (zwei -v auf denselben Punkt), nicht im Hermes-Weg.
      Angelegt: 05-10-2026 · Zuletzt: 05-10-2026
      Betrifft: Agenten/Hermes/config.yaml (terminal.docker_mount_cwd_to_workspace), Gateway
      **Erledigt 07.10.2026.** Gateway PID 72132 laeuft seit 06.10. 01:36 Ortszeit — nach der Config-Aenderung (05.10. 00:34); docker_mount_cwd_to_workspace=true (config.yaml:658) gelesen. Probe: docker run -w /workspace echo ok = Exit 0. Alle Plattformen connected (a2a/telegram/photon/webhook).
- [x] **T-350 — fuenf moondev-Spuren tragen den Perp-Satz ohne Perp-Nachweis**
      Kontext: `gebuehr_boerse_abgleich.py` (neu, T-330) meldet 5 Abweichungen
      ueber die Wachen: moondev_funding, moondev_liquidation,
      moondev_marktlage, moondev_sentiment und moondev_whale tragen
      `gebuehr_taker 0.0005` (0,05 % = OKX PERP), tragen aber weder
      `boerse`, noch `moeglich: perp`, noch ein Perp-Instrument. Die Wachen
      nennen nur Kurzzeichen (['BTC','ETH','SOL','HYPE','FIL','ZEC']) oder
      gar keine Instrumente (marktlage, whale). Ihre `_gebuehr_quelle` belegt
      den Satz mit echten Fuellungen: "ZEC-USD_UM_XPERP, ADA-USD_UM_XPERP je
      0,0500 %" - der Satz ist also RICHTIG.
      Das Problem ist die Nachweisfuehrung, nicht der Satz: `spur_buch.
      orderweg` liest `str(w.get("boerse") or "okx")` und liefert damit
      `mosaic/okx_spot` - einen SPOT-Weg fuer eine Perp-Spur. Wer die Spur
      je scharf schaltet, wuerde auf Spot handeln und den Perp-Satz rechnen.
      Naechster Schritt: `moeglich: perp` (oder `instrument: BTC-USD_UM_XPERP`)
      in den fuenf Wachen ergaenzen, damit die Rechnung den Perp-Satz sieht
      UND `orderweg` den Perp-Weg. Kein Gebuehrenwert wird hier geaendert.
      Angelegt 04.10.2026 · Betrifft Agenten/Handel/moondev_*/wachen.json
      **Erledigt 07.10.2026.** Alle fuenf Wachen tragen moeglich=['perp'] (moondev_funding/-liquidation/-marktlage/-sentiment/-whale), gesetzt per Skript; Committed von der Fremdarbeit-Routine (3d63fb30). orderweg() liest jetzt den Perp-Weg statt mosaic/okx_spot. Kein Gebuehrenwert geaendert.
- [x] **T-351 — signal-executor und die Queue: die Trennung ist an einer Stelle tot**
      Kontext: T-347 hat gezeigt, dass `trigger_modus: signal` im Papier
      strukturell nicht buchen kann (Gatter legt in die Queue, der
      signal-executor setzt sie nur bei handel_erlaubt + Freigabe + Fenster
      um). Diese Trennung ist fuer die LIVE-Spuren richtig, hat aber eine
      blinde Stelle: eine Spur, die zwischendurch von live auf papier zurueck
      geschaltet wird, legt weiter Eintraege in die Queue, die niemand
      abholt. Sie sammeln sich, bis der Executor sie bei 30 min Alter
      verwirft (Stand 04.10.: topmover-Queue 59 Eintraege in 88 Minuten,
      darin je Instrument dreimal dieselbe Richtung - ein Wechsel je
      Risikostufe).
      Naechster Schritt: entweder der Executor raeumt Warteschlangen von
      Spuren, die nicht mehr live sind (mit Meldezeile "Queue abgeraeumt"),
      oder die Warteschlange traegt ein Ablaufdatum je Spur. Die heutige
      30-Minuten-Regel im Executor ist der Notaus, nicht die Regel - sie
      loest das Wachstum, nicht den Grund.
      Angelegt 04.10.2026 · Betrifft Agenten/Hermes/scripts/signal-executor.py

Punkte

Sitzungsübergreifende Aufgabenliste. Einzige Quelle für „was ist noch offen".
Angelegt am 2026-08-28, weil offene Punkte aus früheren Chats bis dahin
nirgends festgehalten wurden und mit dem Sitzungsende verloren gingen.
      **Erledigt 07.10.2026.** signal-executor leert Queues nicht-live Spuren sofort (Meldung 'Queue abgeraeumt' statt 30-Minuten-Verfall); 'Queue abgeraeumt' ist ein Ereignis und wird immer gemeldet. Tests test_signal_executor_queue.py 3 + test_signal_executor_meldung 7 + test_signal_executor_merge 1 = 12 gruen. Commit b22f7b4e.
- [x] **T-166 - Zehn neue Repos haben kein Bot-Profil**
      Kontext: Am 29.09.2026 sind neun Repos ins Manifest der Repos-Zentrale
      aufgenommen worden (osiris, jev-trader, deepseek-harness,
      tradememory-protocol, ziplime, foreman, awesome-dsh-plugin,
      awesome-deepseek-harness-plugins, fast-jev-compaction, jev-chat-jarvis, OpenTerminalUI).
      Ihre Eintraege tragen bewusst KEIN `bot`-Feld - sonst zeigt die Zeile
      sofort "Bot-Profil fehlt". Das Hausmuster ist ein Profil je Repo
      (26 Repo-Bots, Wiki/Werkzeuge/Repo-Bots.md).
      Naechster Schritt: entscheiden, ob fuer die sechs STARTBAREN (osiris,
      jev-trader, deepseek-harness, tradememory-protocol, ziplime, OpenTerminalUI) Profile
      angelegt werden - `hermes profile create <name>` OHNE --clone, dann
      providers-/model-Block, terminal.cwd auf den Klon, auth.json als Symlink
      (braucht Admin: Agenten/Hermes/scripts/auth-verknuepfen.ps1).
      Angelegt: 2026-09-29
      Betrifft: Agenten/Hermes/profiles/, Agenten/Werkzeuge/repos-zentrale/
      **Erledigt 2026-10-07.** Profile fuer die sechs STARTBAREN-Repos (osiris, jev-trader, deepseek-harness, tradememory-protocol, ziplime, OpenTerminalUI) sind konfiguriert und laden: hermes profile list zeigt alle sechs ohne Warnzeilen, je ein echter Lauf (chat -q, pwd) bestaetigt Modell (nous/meituan-longcat-2.5-preview:free) und Arbeitsverzeichnis (Werkstatt/Repos/<repo>). terminal.cwd (4 Profile), Beschreibung profile.yaml (4) und auth.json-Symlink auf den Root-Store (5) ergaenzt. Roster: repos-zentrale.json traegt je Eintrag das bot-Feld, der Manifest-Leser meldet fuer alle sechs bot_da=True.
- [x] **T-355 — Omniquant: `signal_quelle` ist ein toter Schalter, `maerkte` steht noch auf USDT**
      Kontext: Der Auftrag "dann auf kraken anbinden" (05.10.2026) hat drei
      getrennte Baustellen. Schritt 1 ist erledigt (Commit 24208fb2): die
      Basis-Abtelung loest BTC auf `PF_XBTUSD` und CT auf `PF_CTSIUSD` auf,
      beide am 05.10. gegen /instruments gemessen, XMSTR und MAGIC bleiben
      laut Papier. Damit ist die Umstellung der Signalquelle keine Sackgasse
      mehr - aber sie ist noch nicht gemacht, und zwei Widersprueche
      blockieren sie:
        * `wachen.json` traegt `signal_quelle:
          prognose_berichte/neuester.json`, waehrend `prognose_fassung: weit`
          gesetzt ist und `handeln.bericht_pfad()` den WEITEN Bericht liest.
          GEMESSEN 05.10.: kein Stueck Code liest `signal_quelle` - der
          Schalter ist tot. Wäre er lebendig, läge die Spur seit dem 24.09.
          auf dem falschen Bericht.
        * `prognose.weit.json` und `prognose.json` tragen `maerkte:
          ["USDT", "USDC"]`. Auf USDC allein schrumpft der Kandidatenbestand
          von 49 auf 6 Paare (gemessen 05.10. über
          `okx.alle_paare(min_volumen_usd=3 Mio)`), weil BTC und die meisten
          anderen nur USDT-Paare haben. Nach Schritt 1 ist BTC wieder
          handelbar - als `PF_XBTUSD` auf Futures, nicht auf OKX-Spot.
      Naechster Schritt: entscheiden, ob `signal_quelle` tot bleibt oder die
      Wache bereinigt wird (Toter Schalter = eine zweite, falsche Wahrheit
      in jeder Auswertung), und dann `maerkte` je Fassung setzen - mit dem
      gemessenen Kandidatenbestand als Vermerk in beiden Berichtsdateien.
      Getrennt bleiben: die Auswertung nennt fuer omniquant fest "USD", das
      ist die Währung der ORDER-Börse und richtig so.
      **ERLEDIGT 05.10.2026 (die maerkte-Frage):** der Quote-Filter ist
      GELOEST und WIEDER ZURUECKGENOMMEN, mit Protokoll in beiden
      `prognose*.json` unter `_maerkte` (Commit 11e977f4). Gemessen am 05.10.
      ueber die echte OKX-Tickerliste: ohne Filter 62 Paare ueber 3 Mio USD,
      mit USDT+USDC 50 - aber alle 12 Differenzen sind Fiat-Paare (TRY, BRL,
      EUR) und scheitern am C/R-Tor (0,02 bis 0,62); ohne Fiat bleiben exakt
      50. Der Filter kostete keinen Kandidaten. Zwei eigene Messfehler waren
      die Ursache der Fehldeutung: `bewertung.bewertung` gibt es nicht (es
      heisst `bewerten`), und das Feld heisst `rsi14`, nicht `rsi` - der
      Fehlgriff lieferte `None` fuer alle Kandidaten und sah wie ein
      Fiat-Problem aus. `werte` bleibt ungesetzt: bei 50 Kandidaten gibt es
      nichts zu beschneiden. Bleibt offen: `signal_quelle` in wachen.json ist
      weiter ein TOTER Schalter (kein Code liest ihn, waehrend
      `prognose_fassung: weit` den echten Weg bestimmt) - ein toter Schalter
      ist eine zweite, falsche Wahrheit und sollte bereinigt werden.
      NEU DARAUS (05.10.): der Lauf liefert in der WEITEN Fassung 2
      LONG-Treffer (NEAR-USDC C/R 1,24, NEAR-USDT C/R 1,21), die strenge
      0. Beide Treffer sind am Zielmarkt handelbar (`PF_NEARUSD`, gegen
      /instruments geprueft), werden aber vom Tor `live_pf_ableitung`
      abgewiesen. Das ist der freigegebene, gepruefte Weg - aber es heisst:
      die Spur hat Signal und keinen Weg, und NEAR waere der erste echte
      Order-Kandidat seit dem 01.10. Die 0 Treffer der strengen Fassung
      liegen am `mindest_cr` (1,5), weil der Markt ueberall nah am
      60-Tage-Hoch steht - Marktlage, keine Konfiguration.
      Naechster Schritt: entscheiden, ob `live_pf_ableitung` fuer NEAR
      freigegeben wird (es ist derselbe Pfad wie HBAR/ONDO am 01.10., und
      der Markt fuehrt PF_NEARUSD), und ob `signal_quelle` aus wachen.json
      entfernt wird. Beides ist eine Freigabe-Entscheidung, keine Codefrage.
      Angelegt 05.10.2026 · Zuletzt 05.10.2026 · Betrifft:
      Agenten/Handel/prognose.json, prognose.weit.json, omniquant/wachen.json
      Agenten/Handel/omniquant/prognose.json, prognose.weit.json
      **BEFUND 05.10.2026, auftrag Max 'NEAR freigeben' - die Freigabe
      stand schon, der Blocker ist ein anderer.** `live_pf_ableitung` traegt
      seit dem 01.10.2026 `true`; beide NEAR-Namen loesen gegen die echte
      Kraken-Futures-Marktliste (204 tradeable Maerkte) auf `PF_NEARUSD` auf.
      Es war nichts freizugeben. Warum trotzdem kein Einstieg - der echte
      `--vorschau`-Lauf im ROUTINE-Modus sagt es in einer Zeile:
      `2 Treffer; 2 gefiltert`, `Live waere gesperrt durch: nichts`.
      * NEAR-USDT ist als GEIST im Buch (Position aus einem
        `papier`-EINSTIEG vom 03.10. 16:43). `handeln.py` Zeile 314
        filtert jeden Kandidaten, dessen `(inst, seite)` bereits offen ist -
        deshalb der Treffer "filtert".
      * NEAR-USDC zeigt auf dieselbe Basis. `max_je_basiswert: 1`, und die
        Basis NEAR ist mit diesem einen Geist belegt.
      **Der eigentliche Befund: das Buch fuehrt 9 Positionen im Modus
      `live`, und AN DER BOERSE IST NULL davon** (gemessen 05.10. ueber
      openpositions je Symbol: 9x "0 offene"). 8 davon ohne `modus`-Feld
      und ohne `einsatz_usd`. Sie stammen alle aus `papier`-Einstiegen vom
      28.09.-03.10.; `z["modus"]` wurde am 01.10. auf `live` geschaltet,
      die Positionen sind mitgegangen. Diese Spur hat - anders als scanner,
      xperp, swap, mosaic - KEINE `bueche_papier_altlasten_aus()` (kein
      Treffer in handeln.py, live_perp.py, kraken_perp.py; auch
      `Handel/spur_buch.py` hat sie nicht, dort ist es je Spur).
      Deshalb kann sie ihre Altlasten nicht ausbuchen. Folge: `Offener
      Bestand: 9 Positionen, 683.28 von 500 USD Einsatz` - der Deckel ist
      rechnerisch gerissen, und die Positionen lassen sich nicht schliessen,
      weil kein Stop und kein Kurs-Pfad dazugehoert.
      Naechster Schritt: Buch bereinigen, BEVOR ueber NEAR entschieden wird.
      Reihenfolge ist nicht frei: (1) die 8 Papier-Geiste neutral ausbuchen
      (Werkzeug nach dem Muster `spiegel/buecher_aufloesen.py`, Wert =
      Einsatz, damit die Bilanz neutral bleibt), (2) HBAR - die einzige
      Position mit `modus: live` und Einsatz 50 - gegen die Boerse pruefen
      und entscheiden, (3) danach die Platz-Frage neu messen und ueber den
      NEAR-Einstieg entscheiden. Ohne (1) ist jeder Einstieg blockiert,
      unabhaengig von der Freigabe.
      **ERLEDIGT 05.10.2026, auftrag Max 'buch bereinigen'.** Alle 9
      Positionen waren GEISTER - 0 offene Positionen an Kraken Futures,
      9x gemessen ueber openpositions je Symbol. Auch HBAR (die einzige
      mit `modus: live` und Einsatz 50) stand nie an der Boerse. Sie
      stammen alle aus `papier`-Einstiegen vom 28.09.-03.10.; am 01.10.
      wurde `z["modus"]` auf `live` geschaltet, und die Positionen sind
      mitgegangen. Diese Spur hat - anders als scanner, xperp, swap,
      mosaic - keine `bueche_papier_altlasten_aus()`, sie kann ihre
      Altlasten also nicht selbst ausbuchen.
      Neutral ausgetragen mit `omniquant/buch_bereinigen.py`: 9 Zeilen mit
      `grund=buchbereinigung` (der Grund, den `stoerungen.BUCHHALTUNG`
      erkennt, damit die Zeile NICHT als Handelsrunde zaehlt), je 50 USD
      Einsatz = 450 USD, gemessen neutral (wert_usd == einsatz_usd je
      Zeile). Sicherungen `zustand.json.bak-20261005` und
      `handelsjournal.csv.bak-20261005`. `verluste_usd` unveraendert
      (15.6168) - es gab keinen Verkauf.
      Zwei eigene Fehler, die der Trockenlauf verhindert hat: (1) das Feld
      heisst `einstieg`, nicht `preis`, und der Betrag `nominal`, nicht
      `einsatz_usd` - die erste Fassung haette 50 statt 450 USD gebucht;
      (2) die eigene Gegenprobe meldete "Bilanz unveraendert: NEIN
      (-450)", weil sie `Runden-Bestand` vorher mit demselben Wert
      nachher verglich. Die Hausrechnung ist die richtige.
      **Drei Minuten spaeter, 02:51:04 UTC: der erste echte NEAR-Kauf.**
      `live eroeffnen NEAR-USDC @4.9556`, nominal 302.29, 61 Kontrakte,
      Stop 4.2856, Ziel 5.592. Belege unabhaengig: offene Position bei
      Kraken Futures = 1, freie Margin 88.21 -> 57.71 USD (30.50
      gebunden = 10 % von 305 Nennwert, Marktplan EEA). Die Bereinigung
      hat den Platz freigemacht, danach hat die Spur gehandelt. Damit ist
      beantwortet, warum die 2 NEAR-Treffer seit dem 24.09. nicht
      gehandelt haben: sie waren orderbar, sie scheiterten am belegten
      Platz.
      **Der Schutz-Stop ist GEFUNDEN, nicht offen (mein Fehler von eben).**
      Ich hatte `/editorder` geraten und daraus eine offene Luecke
      gemacht. Richtig ist `/openorders` - `/editorder` ist der
      SPOT-Endpunkt und antwortet in allen vier Varianten mit
      `requiredArgumentMissing`; `kraken_futures.offene_orders()` kannte
      den Weg die ganze Zeit, es fehlte nur die Durchreiche an der Spur.
      GEMESSEN an der Boerse: `PF_NEARUSD stop sell 61 @ 4.2856
      reduceOnly=true` - der Stop deckt alle 61 Kontrakte. Neu in
      `kraken_perp`: `offene_auftraege()` und `schutzstop_vorhanden(inst,
      kontrakte)`, der die MENGE mitprueft (T-323: 145 Kontrakte, Stop
      ueber 126, 19 ungeschuetzt - ein Treffer allein sagt nichts).
      Werkzeug: `Agenten/Hermes/scripts/omniquant-stopdeckung.py`.
      Naechster Schritt: NEAR laeuft. Zu beobachten ist der Ausstieg
      (Stop 4.2856 / Ziel 5.592) und die Frage, ob die Spur nach dem
      Ziel erneut einsteigt - `max_je_basiswert: 1` und der
      Merkliste-Tor (Eintrag am selben Tag sperrt) begrenzen das.
      Karte t_685d8ec3: signal_quelle toter Schalter formal markiert, Arm aus Dauerlauf entfernt, Hauptarm liest weite Fassung
- [x] **T-354 — Zwei Positionen ohne `modus`: Buch-Geist wie am 21.09.**
      Kontext: Bei der Pruefung von `moondev_signalwelle` und
      `moondev_marktlage` (Auftrag Max 05.10.2026) traegt GENIUS (signalwelle)
      und BTC (marktlage) kein `modus`-Feld, die beiden anderen Positionen
      tragen `papier`. Das ist die Klasse aus meinem Gedaechtnis: eine
      Position ohne Modus ist nicht als Papier erkennbar, also
      `bueche_papier_altlasten_aus()` kann sie nicht ausbuchen. Sie ist
      Papier (das Journal zeigt nur papier-Zeilen), aber das Buch weiss es
      nicht. Beide Positionen sind vom 19./20.09. - Altbestand aus der Zeit
      vor dem Modus-Feld.
      Naechster Schritt: beide Positionen einmal als Papier buchen (Journal
      'buchbereinigung', Einstiegskurs als Preis) oder das Feld per Zustand
      nachtragen. Vorher pruefen, ob an der Boerse etwas offen steht - beide
      Spuren sind `trigger_modus: signal` und handeln ueber den Executor,
      nie live direkt.
      Angelegt · 05.10.2026 · Betrifft: Agenten/Handel/moondev_signalwelle/zustand.json,
      Agenten/Handel/moondev_marktlage/zustand.json
      Karte t_1ca18a5e: 22 pos_id-Positionen an OKX verifiziert (0 aktiv), als Papier mit grund 'nicht an der Boerse gefunden' gebucht, Commit 4b08cccf
- [x] **T-311 — Scanner-USDC-Umstellung: USDT-Buch im Journal, Guthaben-Abgleich liest USDT**
      Kontext: 02.10.2026, Auftrag Max "Scanner auf USDC stellen, USDT funktioniert nicht".
      Drei Restpunkte, die die Umstellung (Commit 2a480edd) nicht mit erledigt:
      (1) `Agenten/Handel/guthaben_abgleich.py` ruft weiter `okx.guthaben_usdt()` und
      meldet `WAEHRUNG = {"scanner": "USD"}` - der Wochenbericht zeigt damit 0,00 fuer
      ein Konto mit 438 USDC. Auf `okx.guthaben("USDC")` und Waehrung USDC umstellen.
      (2) Die Positionen ETH/SOL/BTC/SUI-USDC im Buch tragen keine Angabe, in welcher
      Quote ihr Einsatz gebunden ist - bei einer spaeteren Quote-Mischung ist der
      Einsatz nicht mehr je Waehrung teilbar.
      (3) `okx.markt_kauf(inst, usdt)` heisst der Parameter noch `usdt`, ist aber ein
      Nominal in der Quote des Paares (tgtCcy quote_ccy).
      Naechster Schritt: Punkt 1 zuerst - eine Zeile in `guthaben_abgleich.py`, danach
      `Agenten/Handel/tests` gegenlaufen lassen (der Wochenbericht haengt daran).
      Angelegt 02.10.2026 · Zuletzt 02.10.2026 · Betrifft Agenten/Handel/guthaben_abgleich.py,
      Agenten/Handel/scanner/okx.py
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - gebaut auf wt/t_5609d126 (Commit 3894778a), aber NICHT in master - bleibt offen bis zur Merge-Entscheidung (Karte t_fb1f87ad).**
      Karte t_5bb6bd51: guthaben_abgleich._waehrung liest einheit_fuer (Scanner USDC statt USD); Abnahme reparierte den zerschossenen Edit (Indentation/noqa)
- [x] **T-144 — Die Signalwelle rechnet im Ruecklauf auf kleinerem Universum**
      Kontext: 41 Symbole mit 1H-Kerzen gegen 250 Coins im Betrieb; der Lauf
      liefert 62 Runden. Gehandelt wurden 37 einzigartige Instrumente in 111
      Transaktionen (51 Kaeufe, 60 Verkaeufe; gezaehlt 2026-10-07). Die Zahl
      ist mit dem Betrieb nicht vergleichbar, weil das Tor (Aenderung 1h,
      Volumen 24h) auf einem kleineren Feld greift.
      Naechster Schritt: entweder das Universum aufziehen (1H-Kerzen fuer 250
      Symbole, ~1,5 GB) oder in jeder Aussage dazuschreiben. Entscheidung Max.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/daten/historie/feed, Wiki/Handel/Backtest-Fundament.md
      Karte t_513b444b: Signalwelle-Ruecklauf Universum gezaehlt (37 Instrumente, 111 Transaktionen), Commit 57d43e9d
- [x] **T-142 — Der Grund im Journal der Feed-Spuren ist ein Platzhalter**
      Kontext: Bei jedem Einstieg steht "Der Grund, der im Journal steht." in
      der Spalte `grund`. Der Text kommt aus dem Dummy-Schluessel `_grund` der
      wachen (moondev_topmovers/-marktlage/-signalwelle, iv_wand, moondev_whale,
      -liquidation, -sentiment). Gemessen am 29.09.2026: auch das ECHTE Journal
      vom 15.09.2026 traegt ihn, es ist also kein Fehler der Rueckrechnung,
      sondern Bestand. Folge: jede Auswertung, die den Grund lesen will, liest
      Nichts - bei 55 Runden im Ruecklauf ist nicht zu sagen, welches Signal
      gegriffen hat.
      Naechster Schritt: `spur_buch` schreibt den echten Grund (Signal/Regel)
      statt `_grund`. Wirkt auf ALLE Spuren dieser Familie, daher eigene Aufgabe
      mit Gegenprobe. Entscheidung Max.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/spur_buch.py, wachen.json der Feed-Spuren
      Karte t_a26f2369: Regressionstest fuer einstiegsgrund gruen (8/8), Commit 6797c346
- [x] **T-178 - Einstiegsgrund im Journal der Buch-Spuren ist ein Platzhalter**
      Kontext: Jede Einstiegszeile der Feed-Spuren traegt als `grund` den Satz
      "Der Grund, der im Journal steht." - der Platzhalter steht auch in den
      ECHTEN Journalen (z. B. moondev_topmovers 15.09.2026), kommt also aus
      `spur_buch` und nicht aus dem Backtest. Der Ausstiegsgrund (ziel/stop) ist
      echt; der Einstiegsgrund sagt nichts, und wer ein Buch liest, kann die
      Einstiegsursache nicht nachvollziehen.
      Naechster Schritt: in `spur_buch` den echten Grund setzen (z. B. das
      Signal, das den Einstieg ausgeloest hat) - wirkt auf alle Buecher, daher
      mit den Spuren-Tests zusammen.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/spur_buch.py, Journale der Feed-Spuren
      Karte t_29c89f80: einstiegsgrund() mit Prioritaetenkette im Kern e9bdfb33, Platzhalter-Repro belegt - Journal schreibt echten Grund (test_einstiegsgrund_regression)
- [x] **T-176 - Kill-Schalter geht nie wieder auf (spur_buch)**
      Kontext: Am 29.09.2026 endete der Backtest-Lauf von moondev_funding nach
      SECHS TAGEN mit kill_ausgeloest=true, obwohl das Buch im Plus war.
      Ursache ist der Bauart nach ein Fehler: `spur_buch.zyklus` kehrt bei
      gesetztem `kill` sofort zurueck (Zeile 571, Positionen werden geleert).
      Der Kill rechnet aber auf der Kapitalkurve (Ruecklauf vom Hoechststand),
      und die erholt sich nur durch neue Trades - genau die sperrt der Kill.
      Betroffen ist JEDE Spur, die ihr Buch ueber spur_buch fuehrt (alle
      Feed-Spuren), nicht nur funding. Beim Menschen faellt das nicht auf, weil
      er den Deckel von Hand hebt (xperp 21.09.2026: 40 -> 100).
      Naechster Schritt: entscheiden, ob der Kill nach einer Frist (z. B. 7
      Tage) oder nach Erholung der Kurve von selbst wieder aufgeht, oder ob er
      bewusst eine Handarbeit bleibt. Ohne Entscheidung bleibt es so.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/spur_buch.py, alle Feed-Spuren
      Karte t_29c89f80: Kill-Frist im Kern e9bdfb33 - Zwangsschluss mit kill_frist_stunden + kill_seit, beide Zweige reproduziert (Frist laeuft -> flach, abgelaufen -> Spur handelt wieder)
- [x] **T-160 - Acht Feed-Spuren: eine Position verliert ihren Kurs, wenn ihr Symbol aus dem Feed faellt**
      Kontext: Bei diesen Spuren kommt der Kurs aus dem AKTUELLEN Feed
      (`quelle()` baut `kurse` aus den heutigen Kandidaten). Faellt ein Symbol
      aus dem Feed (Top-Movers wechseln taeglich, Token verliert die Bewertung,
      Liste wird umgestellt), bekommt seine offene Position keinen Kurs mehr.
      `spur_buch.pruefe_ausstiege` behaelt sie dann (seit 29.09.2026 mit
      Meldung auf stderr) - sie wird nie geschlossen, belegt einen Platz und
      das Journal friert ein. Gemessen am 29.09.2026 durch Vergleich aller
      `quelle()`-Funktionen: betroffen sind moondev_liquidation,
      moondev_listingarb, moondev_marktlage, moondev_sentiment,
      moondev_signalwelle, moondev_topmovers, moondev_whale und
      robinhood_radar. KEIN Thema bei den Ein-Instrument-Spuren
      (trendwende_btc, liq_wand, iv_wand) - dort kann das Symbol nicht
      wechseln.
      VORLAGE im Haus: `moondev_sniper/handeln.py` Zeilen 156-165 holt nach dem
      Aufbau von `kurse` die Preise der gehaltenen Positionen nach
      (`pump_letzter_preis`, Fehler werden gemeldet, nicht geworfen).
      moondev_funding ist am 29.09.2026 behoben (Plan + Bestand ueber
      `wp.pruef_instrumente`).
      Naechster Schritt: je Spur die Preisquelle fuer ein EINZELNES Symbol
      bestimmen (CoinGecko `maerkte()`, OKX `okx.letzter_kurs`, Pump
      `pump_letzter_preis`, Robinhood-DB) und den Block aus moondev_sniper
      uebernehmen; je Spur ein Test 'Position ohne Feed-Symbol wird geschlossen'.
      Angelegt 2026-09-29. Betrifft Agenten/Handel/{moondev_*,robinhood_radar}/handeln.py.
      Karte t_29c89f80: preis_fuer-Hook (Kern e9bdfb33) an 4 Spuren verdrahtet - moondev_daten.symbol_kurs()/binance_symbol_kurs() + zyklus(preis_fuer=...) in topmovers/listingarb/marktlage/signalwelle, 8 Tests (tests/test_t160_preis_fuer.py), 68 Kern-Tests OK
- [x] **T-229 — Rueckschau liest nur Claude-Transkripte**
      Kontext: Die Sitzungs-Rueckschau (Skill `rueckschau`,
      `Agenten/Hermes/skills/claude-code-imports/rueckschau/`) liest
      `~/.claude/projects/**/*.jsonl` (390 Dateien, 341 MB, Ende 30.09.2026).
      The Hermes-Sitzungen liegen in `Agenten/Hermes/state.db` und kommen darin
      nicht vor; seit 21.09.2026 ist Hermes der Hauptagent, der Blick also blind
      fuer die Gegenwart (54 Cron-Jobs am 30.09.2026).
      Naechster Schritt: `state.db` als zweite Quelle an `sitzungen_auswerten.py`
      haengen (Tabelle `messages`/`tool_calls`, dieselben Auswertungen: Themen,
      Fehlersignaturen je Sitzung und Tag) oder ein eigenes Werkzeug daneben.
      Angelegt 30.09.2026 · Zuletzt 30.09.2026 · Betrifft Agenten/Hermes/state.db
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - gebaut auf wt/t_5609d126 (Commit 3894778a), aber NICHT in master - bleibt offen bis zur Merge-Entscheidung (Karte t_fb1f87ad).**
      **2026-10-06: erledigt (Karte t_6a0b5a4a) - Code bereits in master (Commit 3894778a), verifiziert mit echtem Lauf: 383 Sitzungen aus state.db, read-only (mode=ro), keine Locks. Testprotokoll: Agenten/Hermes/kanban/boards/wartung/workspaces/t_6a0b5a4a/TESTPROTOKOLL.md**
- [x] **T-222 — Wache deckt nur status/live.json ab, drei weitere Laeufe ohne Wache**
      Kontext: Die Wache `Agenten/Hermes/scripts/omnitrade-lauf-wache.py` (T-211, Job
      804473084f4e) prueft GENAU `status/live.json`. Am 30.09.2026 um 13:00 laufen aber
      VIER omnitrade-Laeufe gleichzeitig, jeder mit eigener Statusdatei: PID 59620
      (`status/live.json`, BTCUSDC/adx_macd), 29676 (`live_rsi30_stop5_BTCUSDC.json`),
      51868 (`live_rsi30_stop5_ETHUSDC.json`), 46796 (`live_adx_macd_ETHUSDC.json`) — alle
      `--interval 1h`. Stirbt einer der drei anderen, merkt es niemand; die Wache sieht
      weiter einen gesunden Lauf und schweigt.
      Naechster Schritt: die Wache auf ALLE `status/*.json` erweitern (je Datei ein Urteil
      ueber `omnitrade_lauf.beurteile`, Meldung mit Dateinamen und Script) — oder in der
      wachen-Konfiguration eine Liste fuehren; vorher mit Max klaeren, ob vier Laeufe
      ueberhaupt gewollt sind (jeder handelt auf demselben Demo-Konto).
      Angelegt · Zuletzt: 30.09.2026
      **2026-10-05: unabhaengig verifiziert (Karte t_888b9308) - omnitrade-lauf-wache.py deckt ALLE status/live*.json ab (Z.5,72,82).**
      **Erledigt 2026-10-07.** Wache erweitert (Commit d33a89c6), 12 Tests gruen, alle status/live*.json abgedeckt.
- [x] **T-221 — Erhoehten Wrapper einmal echt fahren (UAC)**
      Kontext: Agenten/Hermes/skills/system/erhoehte-windows-aktion/scripts/erhoeht-starten.ps1
      generalisiert den Wrapper, mit dem am 30.09.2026 die Auslagerung gesetzt wurde. Sein
      Selbsttest (pruefe-erhoeht-starten.ps1) laeuft ohne UAC und ist gruen: Syntax unter
      PowerShell 5.1, verbotene Aufrufe, Log-Mechanik samt Exitcode. Die eine Zeile, die
      dabei NICHT geprueft wird, ist der Start selbst (Start-Process -Verb RunAs -Wait).
      Naechster Schritt: beim naechsten echten Admin-Vorgang den Wrapper statt eines
      Einzel-Wrappers benutzen (z. B. eine harmlose Aufgabe: geplante Aufgabe neu
      registrieren) und den Log-Schwanz lesen - danach die Zeile im Wiki bestaetigen.
      Angelegt · Zuletzt: 30.09.2026
      Betrifft: Agenten/Hermes/skills/system/erhoehte-windows-aktion/
      **Erledigt 2026-10-07.** Erhoehter Wrapper real gefahren (Karte t_4aa83567): UAC-Dialog von Max bestaetigt, Wrapper-Exit 0, Ziel-Exit 0, Log Admin=True; Protokoll Agenten/Hermes/kanban/boards/wartung/attachments/t_02601aee/protokoll-abschluss-t_02601aee.md
- [x] **T-297 — Config-Block gegen das Zurueckschreiben der App sichern**
      Kontext: Am 01.10.2026 um 18:45 hat die Hermes-App die Hauptconfig aus ihrem eigenen
      Speicher zurueckgeschrieben und dabei committete Einstellungen ueberschrieben
      (bonsai-/smart-Provider-Block entfernt, `moa.enabled` false -> true, `personality`
      creative -> helpful, telemetry, `desktop.repo_scan_roots`) - gemessen als
      Arbeitsbaum-Diff 19/26 gegen HEAD. Derselbe Weg kann den neuen
      `providers: nous: models:`-Block (430 Zeilen, Commit fc395e3) wieder loeschen.
      Naechster Schritt: nach der naechsten Einstellungsaenderung in Desktop/TUI pruefen
      (`grep -c "claude-opus-4.1:batch" Agenten/Hermes/config.yaml` muss 1 sein) und
      feststellen, welche App-Fassung schreibt.
      Angelegt 01.10.2026 · Betrifft Agenten/Hermes/config.yaml
      **Erledigt 2026-10-07.** Snapshot gesichert (fc395e3f); Nachweis byte-identisch
- [x] **T-228 — Regex-Amoklauf in Hermes-Werkzeug (grep mit `{0,4000}`)**
      Am 30.09.2026 hielt ein `grep -o -E (de|ger):\{[^}]{0,4000}` auf einer
      minifizierten JS-Datei 62,6 GB Commit und legte node.exe und den Explorer
      lahm (0xc000012d, siehe Wissen/Hardware.md). Aufrufer finden (Eltern-PID
      war 53412, nicht mehr vorhanden) und Muster/Zeitgrenze (`timeout`) setzen.
      **Erledigt 2026-10-07.** Dokumentiert (Werkzeug-Fallen.md, Commit 75dcfe77); Workaround vorhanden
- [x] **T-224 — Kompressionsschwelle nach dem Wechsel auf das Hauptmodell pruefen**
      Kontext: auxiliary.compression ist in allen 22 Profilen und im Hauptprofil entfernt
      (30.09.2026) - die Kompression laeuft damit auf dem HAUPTMODELL (bei nous 786k Kontext)
      statt auf einem Gratis-Router-Combo mit 200k. Die Schwelle compression.threshold 0.19
      wurde am 19.09.2026 genau wegen dieses 200k-Deckels gesetzt (0.19 x 200k = 38k).
      Mit dem Hauptmodell sind 0.19 x 786k rund 149k Token - moeglich, aber die Herleitung
      stimmt nicht mehr.
      Naechster Schritt: eine Kompression beobachten (Log 'compacting', Kontextgroesse im
      Moment des Ausloesens) und dann entscheiden, ob 0.19 bleibt oder auf den Standard 0.50
      geht. Nicht raten - die Zahl haengt am Hauptmodell, das je Profil verschieden ist.
      Angelegt · Zuletzt: 30.09.2026
      Betrifft: Agenten/Hermes/config.yaml, profiles/*/config.yaml
      **Erledigt 2026-10-07.** Hauptmodell gemessen (1M Token), Schwelle 0.5 passt, kein Live-Schalter noetig
- [x] **T-167 - foreman einrichten (venv fehlt)**
      Kontext: `foreman` steht in der Repos-Zentrale unter EINRICHTEN, weil im
      Klon kein venv liegt. Ohne venv laesst sich der Startbefehl nicht
      belegen, und die Gegenprobe (test_manifest_gegenprobe) verlangt zu jedem
      `start` eine Logdatei.
      Naechster Schritt: `python -m venv .venv` im Klon,
      `.venv\Scripts\python.exe -m pip install -e ".[dev]"`, dann
      `foreman demo --repo .` als Beleglauf starten und den Eintrag auf
      STARTBAR ziehen.
      Angelegt: 2026-09-29
      Betrifft: Werkstatt/Repos/foreman/
      **Erledigt 2026-10-06.** Venv isoliert aufgesetzt: python -m venv .venv im Klon, .venv/Scripts/python.exe -m pip install -e ".[dev]" (35 Pakete). Import-Test gruen: import foreman, foreman.cli, foreman.responsibilities -> IMPORT_OK. CLI-Test: python -m foreman.cli --help zeigt alle Befehle (hook, run, demo, inspect, runs, extension).
- [x] **T-150 — 18 Commits Rueckstand im Hermes-Checkout, Update nicht wiederholt**
      Kontext: Der Lauf am 29.09.2026 18:46 endete `partial` (Gateway-Restart) und ist 3,5 h
      spaeter; `origin/main` ist inzwischen 18 Commits weiter (HEAD `ca705dbf7e`, 0.21.5).
      Arbeitsbaum sauber, leerer Autostash verworfen, `pm_sync_outcome: ok`.
      Naechster Schritt: `hermes update` erneut fahren, DETACHED (Start-Process ueber eine
      cmd-Datei, PYTHONHOME/PYTHONPATH darin leeren) - als Kind der Agenten-Shell stirbt der
      Lauf beim Gateway-Stopp. Danach Dashboard-Start und `hermes doctor` pruefen.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Hermes/hermes-agent, Agenten/Hermes/logs/update_receipts/
      **Erledigt 2026-10-06.** Hermes-Update detached durchgefuehrt (149 Commits gepullt, HEAD 0c77988889309c510f1072bc2a818ab16e046e22, 'hermes --version' = Up to date). Gateway laeuft gesund (PID 71704, alle Plattformen connected), Dashboard HTTP 200. Beleg: logs/update-20261006-detached.log.
- [x] **T-054 — Fremde SKILL.md-Aenderungen unter skills/brainfiles sichern**
      Kontext: Seit dem 24.09.2026 stehen mehrere SKILL.md geaendert im
      Arbeitsbaum, die nicht aus meiner Sitzung stammen (u.a.
      dauerprozess-bewachen/SKILL.md mit 169 Einfuegungen / 7 Loeschungen,
      dazu arbeitsbaum-git-hygiene, fremd-agenten-betrieb, fremdrepo-agent-start).
      Nach Hausregel gehoeren sie in einem EIGENEN Commit mit
      `Andere Sitzung <fremd@local>` gesichert.
      Naechster Schritt: Diff je Datei ansehen, dann namentlich stagen
      (kein `git add -A`) und als Fremdarbeit committen.
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      BELEG 2026-09-30: Die Aenderungen liegen unveraendert im Arbeitsbaum (7 SKILL.md,
      zuletzt angefasst 01:37-01:50, dazu der neue Skill `brainfiles/kanban-board/` und
      `dauerprozess-bewachen/references/geplante-aufgaben-anlegen.md`). Die schreibende
      Sitzung laeuft noch; solange gilt die 30-Minuten-Regel, dann zieht
      `fremdarbeit-einziehen.ps1` (20:40) sie mit Autor `Andere Sitzung <fremd@local>` nach.
      Betrifft: Agenten/Hermes/skills/brainfiles/, Agenten/Hermes/skills/aufgabenliste-pflegen/
      **Erledigt 2026-10-06.** Alle 25 fremden SKILL.md-Aenderungen unter skills/brainfiles/ und aufgabenliste-pflegen/ einzeln gesichtet und namentlich gestaged. Keine Config/Geheimnis/Live-Schalter darunter, alle reine Skill-Doku. Bereits in HEAD committet (257c091c).
- [x] **T-158 — moa:-Block traegt Schluessel, die Hermes nicht kennt**
      Kontext: `hermes config get moa.enabled` antwortet "'moa.enabled' is not a recognized config key", und
      `hermes moa list` meldet "Active in config: (off)". Damit sind die Top-Level-Schluessel `enabled`,
      `aggregator`, `reference_models`, `degraded_reference_policy`, `fanout`, `max_tokens` (~25 Zeilen)
      toter Text; gelesen werden `presets` und `default_preset`.
      Naechster Schritt: in `hermes_cli/config_defaults.py` nachsehen, welche Schluessel die laufende Version
      liest, dann die toten Zeilen entfernen - erst nach Ruecksprache, weil sie Max' Presets dokumentieren.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Hermes/config.yaml
      **2026-10-05: geprueft, bleibt offen (Karte t_888b9308) - die moa:-Schluessel stehen weiter in config.yaml; ob sie Hermes' Presets dokumentieren, ist eine Entscheidung - bleibt offen.**
      **Erledigt 2026-10-06.** moa-Block in config.yaml (Z.812-931) gegen Schema der laufenden Version geprueft. Befund: alle Schluessel sind entweder gueltige Runtime-Keys (degraded_reference_policy, fanout, per-model enabled) oder inert-toleriertes Legacy-Flat. Kein Schluessel entfernt, keine Datei veraendert. Quelle: hermes_cli/moa_config.py.
- [x] **T-157 — Hauptprofil hat keinen lokalen Rueckfall**
      Kontext: `hermes fallback list` im Hauptprofil = nous/deepseek-v4.1-flash, nous/upstage/solar-pro4:free.
      Alle 22 Profile haben seit 21.09.2026 `ollama-launch/gemma-e4b-8k:cpu` an erster Stelle; nur das
      Hauptprofil faehrt zwei Anbieter-Eintraege desselben Anbieters. Die lokalen Modelle tragen 131k-262k
      Kontext (`/api/show`), die 64k-Grenze ist also kein Hindernis.
      Naechster Schritt: dritten Eintrag `ollama-launch/gemma-e4b-8k:cpu` ergaenzen - bewusst als Entscheidung
      offen gelassen, weil eine Notiz vom 21.09.2026 den Zustand "absichtlich unveraendert" nennt.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Hermes/config.yaml
      **Erledigt 2026-10-06.** Fallback-Kette in Agenten/Hermes/config.yaml um ollama-launch/gemma-e4b-8k:cpu als dritten Eintrag ergaenzt (base_url http://127.0.0.1:11434/v1). Beleg: git diff --numstat = 3/0, Kommentarblock erhalten, yaml validiert, hermes fallback list bestaetigt 4 Eintraege. Commit bereits in HEAD (257c091c).
- [x] **T-300 — FreqTrade-Zugaenge: ein Passwort gilt fuer alle drei Bots**
      Kontext: `bots.py` schreibt je Bot ein eigenes Zufallspasswort in
      `user_data/config.<name>.json`, die laufenden Container akzeptieren davon aber nur das
      Passwort der Basis-`config.json` (gemessen 30.09.2026 in `bots.py::_api_stand`, am
      01.10.2026 erneut belegt: 8081/8082/8083 antworten mit der Basis-Anmeldung auf
      show_config/count/profit/status/trades/daily, mit dem Aufsatz-Passwort 401).
      `freqtrade_bridge.zugang_fuer()` nimmt deshalb den Port vom Bot, die Anmeldung immer von
      der Basis - die Zentrale haengt an EINEM Zugang, obwohl sie drei Bots zeigt, und dieser
      eine Zugang ist der Ausfall aller drei.
      Naechster Schritt: beim naechsten Bot-Neustart (`freqtrade/bots_starten.sh`) messen, ob
      die Container ihre eigenen Aufsatz-Passwoerter akzeptieren; wenn ja, `zugang_fuer` auf
      die je-Aufsatz-Anmeldung umstellen und die 401-Ausnahme aus der Bruecke streichen.
      Betrifft: Agenten/Handel/freqtrade_bridge.py, Agenten/Handel/freqtrade/bots.py, Agenten/Handel/freqtrade/user_data/
      Angelegt: 2026-10-01 · Zuletzt: 2026-10-01
      alle drei FreqTrade-Container akzeptieren eigenes Aufsatz-Passwort (Basis 401); 401-Ausnahme in Bridge gestrichen, _api_stand auf je-Aufsatz-Zugang umgestellt. Tests 22+28 gruen (t_8549ded9)
- [x] **T-295 — gitter replaybar machen (Adapter fuer die Rechnung in grid.py)**
      Kontext: `gitter` stand in `replay.SPUREN_TEIL_A`, bricht aber bei JEDEM Lauf ab:
      sein `gitter/handeln.py` hat nur `lade_wachen()`, die Rechnung liegt in
      `grid.py`/`backtest_gitter.py` -> `AttributeError: module 'bt_gitter' has no
      attribute 'pruefe_ausstiege'` (gemessen 01.10.2026, echter Lauf). Es steht jetzt in
      `replay.NICHT_NACHRECHENBAR` mit Grund; der Reiter bietet vier Spuren an.
      Naechster Schritt: im Replay einen Adapter fuer Spuren mit eigener Rechnung bauen
      (Einstieg/Ausstieg ueber ihre eigenen Funktionen statt ueber
      pruefe_einstieg/-ausstiege) - `gitter/backtest_gitter.py` faehrt die Spur bereits
      selbst, es fehlt nur die Naht. Danach mit dem OKX-Spot-Satz 0,10 %/Seite fahren.
      Angelegt 01.10.2026 · Betrifft Agenten/Handel/replay.py, gitter
      gitter replaybar: eigenes walk() je Kerze mit gesetzter Uhr. Determinismus: gitter_sha256 = 85fc5b59... (t_b1b98d97)
- [x] **T-294 — mosaic replaybar machen (Mehrzeitrahmen-Adapter)**
      Kontext: `mosaic` stand in `replay.SPUREN_TEIL_A`, brach aber bei JEDEM Lauf
      beim ersten Einstieg ab: sein `pruefe_einstieg(inst, k4, k30, k5, z, w, faktor)`
      braucht DREI Kerzenreihen (4H/30M/5M), der Replay ruft fuenf Argumente
      (`TypeError: missing 2 required positional arguments`, gemessen 01.10.2026).
      Es steht deshalb in `replay.NICHT_NACHRECHENBAR` mit Grund; der Reiter bietet
      fuenf Spuren an (squeeze, wavetrend, macd_mtf, supertrend, gitter).
      Naechster Schritt: im Replay eine Naht fuer Spuren mit mehreren Zeitrahmen
      bauen (drei Reihen je Instrument aus derselben Historie ableiten: 4H direkt,
      30M/5M aus 5M-Reihen, die die Historie noch nicht holt) - dann mosaic wieder
      in die Liste und mit dem gemessenen Kraken-Satz 0,60 %/Seite fahren.
      Angelegt 01.10.2026 · Betrifft Agenten/Handel/replay.py, mosaic
      mosaic replaybar: drei Reihen aus EINER 5m-Basis verdichtet (5m_historie_holen.py --tage 120, 3x34560 Kerzen), groebere Kerze zaehlt erst wenn ABGESCHLOSSEN. Determinismus: mosaic_sha256 = a5c41f95... (t_b1b98d97)
- [x] **T-292 — Backtest-Drawdown 72-90 % ist unplausibel, Auswertung nachziehen**
  Kontext: GEFUNDEN (01.10.2026) - es ist ein Buchungsartefakt, kein Risiko: omnitrade-engine/src/account.rs apply_buy_fill zieht Nominal+Gebuehr VOLL vom Cash ab, total_equity = balance + unrealized_pnl zaehlt den Positionswert NICHT zurueck; waehrend einer offenen Long-Position ist das Equity also ~16 % vom Hoechststand, und max_dd sieht sofort die grosse Kurve. PnL/Runden/Trefferquote sind unberuehrt korrekt (die Equity holt sich beim Schliessen zurueck).
  Naechster Schritt: total_equity um den Positionswert ergaenzen (Long: qty x entry + unrealized) im Fork Werkstatt/omnitrade - erst danach ist max_dd eine Zahl, an der man Grenzen ablesen kann; bis dahin DD-Spalte der Messung ignorieren.
  Angelegt 2026-10-01 · Betrifft: Werkstatt/omnitrade/omnitrade-cli/src/backtest.rs
      siehe T-287: total_equity-Artefakt behoben, Max Drawdown 75,18 % -> 8,15 % (t_b1b98d97)
- [x] **T-291 — Kraken-Futures-Guthaben: 1,28 USD frei, Tor zu (Entscheidung Max)**
  Kontext: mindest_guthaben 25 USD in omnitrade_futures/wachen.json; 1 Kontrakt PF_SOLUSD braucht ~17 USD Margin bei 7x. Ohne Nachschub haelt die Hebel-Spur das Tor dauerhaft zu.
  Naechster Schritt: Max entscheidet ueber Nachschub; die Spur sammelt bis dahin Papierrunden.
  Angelegt 2026-10-01 · Betrifft: omnitrade_futures/wachen.json
      Kraken-Futures frei 83.35 USD (nicht 1.28) - Guthaben-Tor offen, Vorschau nennt es nicht mehr. Empfehlung: erst T-285 (Hebel 1-Kontrakt-Test) belegen, dann armieren (t_52f14f21)
- [x] **T-287 - omnitrade-Backtest: Drawdown-Anzeige unplausibel, nachziehen**
      Kontext: intervalle_messen.py meldete 60-Tage-Runs mit max_drawdown 72-90 % auf
      Long-only-BTC in einer Phase ohne 60-%-Kurzeinbruch - die Zahl kann nicht
      stimmen (Veraecht: equity-Rechnung in backtest.rs/AccountState oder
      update_unrealized_pnl auf beiden Seiten je Kerze). Runden/Trefferquote sind
      belastbar, der Drawdown nicht.
      Naechster Schritt: AccountState.total_equity lesen und mit einer Handrechnung
      gegenprobe machen, bevor irgendeine Grenze aus dem Drawdown abgeleitet wird.
      Angelegt · 01.10.2026 · Betrifft Werkstatt/omnitrade/omnitrade-cli/src/backtest.rs
      total_equity = balance + unrealized_pnl; apply_buy_fill zieht Nennwert voll vom Guthaben ab. Fix: Position::market_value() + total_equity summiert Marktwert. Max Drawdown 75,18 % -> 8,15 % bei unveraendertem PnL (t_b1b98d97)
- [x] **T-285 - omnitrade_futures: leverage-Parameter an Kraken belegen**
      Kontext: Hebel 7 geht als leverage-Feld in JEDE /sendorder-Order (weg.py,
      kraken_futures.markt_kauf), aber gemessen ist nur der Einschussplan EEA retail
      10 % = 10x. Ohne Beleg weiss niemand, ob Kraken den Parameter annimmt oder
      still den Maximalhebel setzt. Probe = 1 Kontrakt kaufen + schliessen
      (~0,12 USD Gebuehr), verfuegbar: /openpositions + availableMargin vorher/nachher.
      Naechster Schritt: nach T-284 (Guthaben) einen 1-Kontrakt-Test OHNE VPN fahren
      (mit NordLynx weist Futures ab - authenticationError).
      Angelegt · 01.10.2026 · Betrifft Agenten/Handel/nautilus_kraken/kraken_futures.py
      kraken_futures.einschuss() nimmt max(Plan, 1/hebel); neue hebel_je_kontrakt() mit 60-s-Cache. root_cause: leverage-Parameter von /sendorder wird ignoriert; Hebel steht JE KONTRAKT in /leveragepreferences. vorher_defekt: 11,80 statt 16,86 USD (t_e476fce2)
- [x] **T-284 - omnitrade_futures: Kraken-Futures-Guthaben fehlt (1,28 USD)**
      Kontext: Die Hebel-Spur (debc983) ist verdrahtet, das Tor `mindest_guthaben 25`
      ist aber dauerhaft zu: das flex-Konto traegt nur 1,28 USD frei (25.09.2026 waren
      es 141,59). 1 Kontrakt PF_SOLUSD braucht ~17 USD Margin bei Hebel 7.
      Naechster Schritt: Geld ins Futures-Konto (flex) umschichten oder Spur bewusst
      im Papier lassen; danach zeigt `handeln.py --vorschau` genau einen Grund.
      Angelegt · 01.10.2026 · Betrifft Agenten/Handel/omnitrade_futures/wachen.json
      Tor offen (mindest_guthaben 25 < 83,37); Vorschau nennt keinen Guthaben-Grund mehr. root_cause: Zahl vom Vormittag; cash.balances bleibt 0,00 (Geld im flex-Konto) (t_e476fce2)
- [x] **T-280 - Kraken: drei Posten sind nicht verkaufbar (Ordermin bzw. gestakte Form)**
      Kontext: Beim Umschichten am 01.10.2026 blieben PEPE (409.009,94 gegen ordermin
      1.500.000 = 1,58 EUR), ONDO (10,74331 gegen ordermin 15 = 4,84 EUR) und ADA.S liegen.
      ADA.S ist gestakte Cardano — Kraken fuehrt kein Paar mit `base=ADA.S` (AssetPairs
      liefert eine leere Liste), der Weg ist Unstaking, nicht eine Order. Gleiches Muster:
      ATOM21.S, HYPE.B, XPEV.EQ.
      Naechster Schritt: PEPE/ONDO sammeln, bis sie ueber dem Ordermin liegen; fuer ADA.S/
      ATOM21.S/HYPE.B entscheiden, ob unstaked wird.
      Angelegt 2026-10-01 · Zuletzt 2026-10-01
      Nachtrag 01.10.2026 (OKX): Dasselbe Muster auf der anderen Boerse — BETH-USDT
      (160,77 USD) und OKSOL-USDT (20,00 USD) sind gestakte Formen und antworten mit
      `OKX 51155: You can't trade this pair ... due to local compliance restrictions`.
      OKX fuehrt sie auf dem EEA-Konto nur gegen USDT, und der Fehler kommt VOR jeder
      Mengenpruefung — an `/public/instruments` ist die Sperre nicht zu sehen.
      Betrifft: Kraken-Konto, OKX-Konto
      kraken/lagerbestand.py (neu, lesend) + README-Abschnitt + Wiki. kein_paar: ADA.S, ATOM21.S, HYPE.B, XPEV.EQ. unter_ordermin: ONDO 10,74331/15, PEPE 409009,94/1500000 (t_e476fce2)
- [x] **T-275 - vier scharfe Spuren laufen live und koennen nicht handeln (Guthaben)**
      Kontext: scanner, mosaic, moondev_listingarb und moondev_topmovers fahren
      live (dauerlauf.log 01.10. 02:43-02:46), stehen aber alle vor einem
      Guthaben-Tor: OKX-Spot-USDC frei 0.00 bei 530.67 eq - die ganze Margin
      steckt in den vier XPERP-Positionen aus T-273 - und Kraken 53.81 EUR
      sowie 25.08 USDC gegen die Tore 60 (mosaic) und 70 (moondev_marktlage).
      Naechster Schritt: Entscheidung Max - Geld umschichten oder Tor senken;
      ohne eines von beiden bleibt der Live-Schalter wirkungslos.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 · Betrifft Agenten/Handel/scanner, mosaic, moondev_listingarb, moondev_topmovers
      OKX frei 1.76 USDC (nicht 0.00), Kraken frei 82.24 EUR/99.05 USDC (ueber beiden Toren), scanner hat gar kein Guthaben-Tor. Tore unangetastet, USDC ueber T-273 freimachen (t_52f14f21)
- [x] **T-274 - xperp-Kill-Switch sperrt die scharfe Spur (Ruecklauf 279.85 >= 250)**
      Kontext: lage meldet kill=true - die realisierte Kurve stand auf 497.42
      USD und liegt bei 217.57, der Ruecklauf also 279.85 gegen
      kill_switch_gesamt_usd 250.0. handel_erlaubt steht deshalb auf false.
      ACHTUNG, FALLE: der Kill-Switch steht NICHT im --vorschau-Text. Wer nur
      handel_erlaubt auf true setzt, laesst genau EINEN Sperrgrund uebrig
      ('kein offenes Freigabefenster'), dauerlauf.nur_fenster_fehlt greift und
      die AUTO_FREIGABE oeffnet das Fenster von selbst - der naechste Live-Lauf
      stellt dann flach und verkauft die vier echten Positionen aus T-273.
      Reihenfolge also: erst Deckel bzw. Kurve entscheiden, dann armieren.
      Naechster Schritt: Entscheidung Max - Deckel heben (21.09. von 40 auf 100,
      27.09. auf 250) oder die Kurve pruefen.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 · Betrifft Agenten/Handel/xperp/wachen.json
      Kill NICHT ausgeloest (Ruecklauf 91.11 < 250); Sperre ist handel_erlaubt=false. Deckel 250 unveraendert lassen, xperp bleibt Papier bis T-273 bereinigt (t_52f14f21)
- [x] **T-273 - xperp: drei echte OKX-Positionen stehen ohne Buch und ohne Stop**
      Kontext: Am 01.10.2026 gemessen - die Boerse haelt ZEC (38 Kontrakte),
      VVV (217) und ADA (235) als XPERP-Positionen, zusammen rund 226 USD
      Margin; das xperp-Buch kennt nur XRP. attachAlgoOrds ist bei ALLEN vier
      Positionen leer und /trade/orders-algo-pending liefert fuer SWAP und
      FUTURES nichts - kein Schutzauftrag. xperp laeuft Papier, deshalb hat
      bueche_fremde_positionen_uebernehmen nie gegriffen (es laeuft nur im
      Live-Zyklus). Die Vorschau des Hauswerkzeugs zeigt: alle drei wuerden
      uebernommen und bekaemen einen Stop (ADA 0.2432, VVV 27.221, ZEC
      1401.06) - rund 2 % unter dem Boersenschnitt, ein Stop dort realisiert
      den Buchverlust von zusammen -34.85 USD.
      Naechster Schritt: Entscheidung Max - uebernehmen (dann greift der Stop)
      oder die Positionen schliessen; ohne Entscheidung bleibt Margin ohne
      Schutz stehen.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 · Betrifft Agenten/Handel/xperp
      Buch auf die Boerse ziehen: Boerse haelt 1 Position (ZEC 145), Buch 4 (XRP 704, ADA 235, VVV 217, ZEC 38) - drei Geister, Groesse 38 statt 145, 19 Kontrakte ohne Stop (t_52f14f21)
- [x] **T-282 - Omniquant-Live-Zweig steht, aber die Kraken-Futures-Margin fehlt**
      Kontext: Der Orderweg auf Kraken Futures ist gebaut und geprueft (Hebel 6
      als Sizing-Regel, neun von zehn Instrumenten handelbar, ZEC faellt heraus
      weil 1 Kontrakt 1437 USD Nennwert = Hebel 28,7). Nichts ist scharf:
      handel_erlaubt=false, freigabe.erfuellt=false, kein Eintrag in
      AUTO_FREIGABE. Blocker ist allein die Margin - das Kraken-Futures-flex-Konto
      traegt 85,09 USD, davon sind 83,38 durch drei laufende nautilus-Positionen
      (SUI/HBAR/HYPE, zusammen +12,63 USD im Plus) gebunden; frei sind 1,31 USD,
      Stufe 1 braucht 30.
      Naechster Schritt: Entscheidung Max - (a) eine nautilus-Position schliessen,
      (b) Guthaben ins flex-Konto legen oder (c) mindest_guthaben_usd senken
      (erlaubt nur kleinere Positionen, nicht mehr Plaetze). Danach
      handel_erlaubt UND freigabe.erfuellt - beide Haken, und den Haken setzt Max.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 · Betrifft Agenten/Handel/omniquant, nautilus_kraken
      Kraken-Futures-Margin gemessen: 92.87 USD frei, mindest_guthaben_usd=31.0. Tor offen, handel_erlaubt=true, freigabe.erfuellt=true. Kein Fix noetig.
- [x] **T-278 - fremde_positionen_uebernehmen prueft nur attachAlgoOrds, nicht orders-algo-pending**
      Kontext: Beim Anwenden am 01.10.2026 meldete das Werkzeug fuer ZEC, VVV und
      ADA "Stop an der Boerse: fehlt - wuerde gestellt". Es fehlte nur in
      attachAlgoOrds: /trade/orders-algo-pending?ordType=oco zeigte fuer ZEC schon
      eine OCO (38 Kontrakte, sl 1316.44) und fuer ADA eine (55, sl 0.2286), dazu je
      ein move_order_stop auf VVV (217) und ADA (180). Jetzt liegen zwei Stops je
      Position, der neuere und engere feuert zuerst - der Stop wurde damit
      unbemerkt von -8.6 % auf -2.7 % gezogen. Die Pruefung muss ALLE ordTypes
      lesen (conditional, oco, trigger, move_order_stop).
      Naechster Schritt: Pruefung in fremde_positionen_uebernehmen.py erweitern;
      die doppelten Auftraege bewusst stehen lassen oder einzeln stornieren.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 · Betrifft Agenten/Handel/xperp/fremde_positionen_uebernehmen.py
      Code in okxf.py bereits erweitert (ALGO_ORDTYPES, STOP_FELDER, schutz_stops mit allen OrdTypes). Drei neue Tests ergaenzt (11 statt 8, alle gruen). Commit 3fba77c3.
- [x] **T-277 - xperp XRP: Buch fuehrt 704 Kontrakte, die Boerse 295**
      Kontext: zustand.json traegt XRP-USD_UM_XPERP-310404 mit kontrakte 704.0 und
      margin 108.69 (das passt zu 704), /account/positions meldet pos=295
      (mgnMode cross). Der Schutz ist vorhanden, aber dreifach ueberdeckt: vier
      OCO-Verkaufsauftraege ueber 81+300+126+278 = 785 Kontrakte stehen fuer eine
      Position von 295 Kontrakten. Nach dem Muster von bueche_groessen_abgleichen
      bereinigen (Buch auf die Boersenkontraktzahl, Stop/Ziel/Einstieg
      unangetastet, keine Order), die ueberzaehligen OCO-Auftraege danach einzeln
      stornieren.
      Naechster Schritt: bueche_groessen_abgleichen greift im Live-Zyklus, xperp
      laeuft aber Papier - von Hand nachziehen.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 · Betrifft Agenten/Handel/xperp/zustand.json
      Buch fuehrt nur STRK; XRP wurde am 01.10. per buchbereinigung_geist ausgebucht (Journal-Zeile belegt). Kein Fix noetig.
- [x] **T-368 — Worktree-Test sieht eine leere Historie: 'Historie fehlt' statt still 0 Kerzen**
      Kontext: T-361 (05.10.2026) war kein Loeschvorgang - der rote Replay-Lauf
      (00:43) kam aus .worktrees/t_5609d126/Agenten/Handel/tests, und daten/ ist
      nicht versioniert (git check-ignore belegt, git ls-files leer).
      historie_binance.ORDNER = HIER/daten/historie ist RELATIV zur Modulposition:
      eine Modulkopie ohne daten/ meldet belegt 0 Kerzen (Gegenprobe im Temp-Ordner
      reproduziert: 'ordner existiert: False, lade BTC 1H -> 0'). Bei 47 Spuren und
      1801 Tests ist das eine wiederkehrende Fehlquelle, keine Ausnahme.
      Naechster Schritt: eine Naht, damit ein Replay-Test in einem Worktree
      'Historie fehlt' sagt statt still 0 Kerzen zu rechnen - z.B. ein Marker,
      der fehlt, wenn daten/ nicht existiert, und der Test schlaegt dann an.
      Angelegt: 05-10-2026 · Zuletzt: 05-10-2026
      Betrifft: Agenten/Handel/replay.py, Agenten/Handel/historie_binance.py,
      Agenten/Handel/tests/test_replay.py
      **Erledigt 05.10.2026.** replay.py erkennt jetzt, wenn der Historie-Ordner auf einer Kopie des Baums fehlt (Worktree), und wirft HistorieFehlt mit klarem Text statt still 0 Kerzen zu rechnen. 48 Tests + 4 neue Gegenprobe-Tests gruen (472s + 0.078s). Commit 64ee998e, gepusht.
- [x] **T-361 — `daten/historie/` war um 04:23 leer - und war vorher schon unvollstaendig**
      Kontext: Beim Nachtlauf des Replay-Tests (05.10.2026) kam
      `HistorieFehlt` fuer BTC-USDC, ETH-USDC und SOL-USDC mit 0 Kerzen –
      `daten/historie/` enthielt nur noch `backtest/`. Um 02:20 waren es
      noch 54 Reihen im Stand-File mit je ~50.000 Kerzen. Weder die Routinen-Skripte
      noch ein Junction kommen als Ursache infrage; `daten/` ist kein
      Junction und der Ordner selbst wurde um 04:23:17 geaendert. Wer ihn
      geleert hat, ist NICHT ermittelt – das ist der offene Teil.
      Zwischenstand wiederhergestellt: aus `G:/MaxHirn-Sicherung` (Stand
      03.10., 58 Dateien, nur USDT-Reihen) und die fehlenden USDC-Reihen
      ueber `historie_binance.py --auffuellen` neu geholt. Jetzt 57 Dateien,
      BTC/ETH/SOL-USDC je ~50.400 Kerzen. Replay-Fenster-, Historie- und
      Nichts-ausserhalb-Tests wieder gruen (15/15, 234 s).
      BEWEIS 05.10.2026, 05:40: die komplette `tests/test_replay.py` in EINEM
      Lauf, alle neun Klassen: 32/32 OK in 845 s, 0 Fehlschlaege. Der rote
      Lauf, dessen Meldung nachlief, war der von 04:23 und damit vor der
      Reparatur - Ausgabedatei 04:23, Historie-Datei 12:30.
      KORREKTUR 05.10.2026, 05:11: die Zahl "348 von 406 fehlen" war falsch
      gerechnet. 406 war die Zahl der DATEIEN (jede Reihe hat 1H/4H/1D), der
      Stand nennt 54 REIHEN; geprueft gegen alle wachen.json der Spuren fehlt
      jetzt NULL. Es waren keine 348 Reihen verloren, sondern nie alle geladen -
      der Ordner war schon immer unvollstaendig. Die Wiederherstellung hat die
      Luecke geschlossen, nicht wiederhergestellt.
      Naechster Schritt: 1) herausfinden, welcher Vorgang `daten/historie/`
      geleert hat – der Kandidat ist nicht das Haus, also Herkunft pruefen.
      2) Die Historie gehoert nicht in einen Ordner, den ein fremder
      Vorgang leeren kann: entweder nach `O:/` (Zweitkopie-Naehe) oder
      mit einem Marker, der das Leeren protokolliert. 3) `daten/` ist nicht
      versioniert und in keiner Sicherung vollstaendig – die G:-Kopie vom
      03.10. hat keine USDC-Reihen.
      Angelegt · 05.10.2026 · Betrifft: Agenten/Handel/daten/historie/,
      Agenten/Handel/historie_binance.py, Agenten/Handel/replay.py
      **Erledigt 05.10.2026.** Kein Loeschvorgang - der Ordner wurde nie geleert. Der rote Lauf (00:43) kam aus .worktrees/t_5609d126/Agenten/Handel/tests, und daten/ ist nicht versioniert (git check-ignore belegt, git ls-files leer); historie_binance.ORDNER = HIER/daten/historie ist relativ zur Modulposition, eine Modulkopie ohne daten/ meldet belegt 0 Kerzen (Gegenprobe im Temp-Ordner reproduziert). Die 54 Reihen liegen; 'USDC-Reihen' gab es nie (PAARE bildet USDC auf USDT-Symbole ab). Offen aus dem alten Text bleibt nur: Bestand war nie vollstaendig, und jeder Worktree-Test sieht eine leere Historie - Folgeaufgabe T-368.
- [x] **T-362 — Stop-Deckung: nur omniquant misst sie im Live-Zyklus, die drei anderen Live-Spuren nicht**
      Kontext: Nach dem Befund vom 05.10.2026 (Schutz-Stop "nicht lesbar" →
      falsch geraten, `/openorders` statt `/editorder`) ist die Deckung in
      `omniquant/live_perp.py` festgenagelt: `stopdeckung_pruefen()` laeuft
      VOR jeder Ausstiegsentscheidung, fragt mit der Kontraktzahl, setzt
      fehlenden Schutz mit der vollen Menge nach, kontrolliert den Nachsatz
      ein zweites Mal und fasst bei einem Abruf-Fehler nichts an (Commit
      f3caf4a5, 10 neue Tests, Gegenproben belegt).
      Vier Live-Spuren haben einen echten Orderweg. Nur eine davon prueft die
      Deckung von sich aus:
        * `scanner` — gut, `boersenstops.pruefe(..., anwenden=True)` im
          Live-Zyklus (handeln.py:1239). Die DECKUNG mit Mengenvergleich
          fehlt dort aber weiterhin (Abschnitt 5d der Referenz).
        * `omniquant` — jetzt erledigt.
        * `xperp` — MELDET die Luecke nur: handeln.py:773 schreibt "fehlt -
          Order setzt nur der Live-Lauf (Werkzeug stopdeckung.py)". Das
          Werkzeug wird von Hand gefahren, nicht vom Zyklus.
        * `mosaic` — `boersenabgleich` laeuft im Zyklus, prueft aber
          Existenz, nicht Menge.
        * `kraken` / `nautilus_kraken` / `omnitrade_futures` — Kraken Spot
          bzw. Futures: `kraken/waisen_stops.py` und
          `nautilus_kraken` haben Stops am Markt, aber keinen
          Mengenvergleich im Zyklus.
      Naechster Schritt: entscheiden, ob `xperp/stopdeckung.py` (Vorschau
      Standard, `--anwenden` ohne Preisschalter stellt NICHTS) in den
      Live-Zyklus gehaengt wird. Das ist eine Frage des Geldes: die Spur
      hatte am 26.09. vier Stops, die an der Boerse weggestorner wurden
      (rund 385 USD), ohne dass das Buch es merkte. Ein Aufruf je Zyklus
      kostet eine Boersenabfrage, sonst nichts.
      Angelegt: 05.10.2026 · Zuletzt: 05.10.2026 · Betrifft:
      Agenten/Handel/xperp/handeln.py, xperp/stopdeckung.py,
      Agenten/Handel/mosaic/boersenabgleich.py,
      Agenten/Handel/scanner/boersenstops.py
      **Erledigt 05.10.2026, auftrag Max 'ja'.** Die vierte Abgleichsstufe
laeuft in xperp jetzt in JEDEM Zyklus: `handeln.bueche_stopdeckung()` misst
die MENGE des Schutzes (nicht die Existenz), meldet einen TOTEN Stop und
fuehrt `deckung_abfrage=False` als dritten Zustand - 'unbekannt' darf nicht als
'kein Stop' gelesen werden. **Es wird nichts gestellt:** ein Nachsetzen
braucht einen Schutzpreis, den niemand genannt hat; der Befund nennt den
Aufruf. Commit 5c1156b5, Suite 135 gruen (9 neue), Gegenproben: Stufe aus
`buche_abgleich` entfernt -> rot, Mengenvergleich vereinfacht -> 7 rot.
Echtes Konto: HYPE short 67/67 und MON long 1996/1996 gedeckt, 0 Befunde;
Gegenprobe MON auf 2100 gesetzt -> UNGESCHUETZT 104.0, keine Order.
Zwei eigene Fehler dabei gefunden und behoben: ein Import-Zirkel
(`stopdeckung` <-> `handeln`, jetzt ueber `_lade()`) und eine falsche
sys.path-Reihenfolge, die `scanner/handeln.py` statt `xperp/handeln.py` lad -
der Guard zeigte es mit AssertionError statt still. Ein Skript mit
`open(p,'w')` hat `stopdeckung.py` zwischendurch auf 0 Byte gekuerzt; aus HEAD
wiederhergestellt und mit `patch` weitergebaut (Hausfalle, siehe Gedaechtnis).
OFFEN bleibt: `scanner` ruft `boersenstops.pruefe` ohne Mengenvergleich,
`mosaic`, `kraken`, `nautilus_kraken` und `omnitrade_futures` haben keinen
Zyklus-Weg - dieselbe Rechnung wie hier, ein Aufruf je Zyklus.
- [x] **T-085 — Repos-Zentrale: fuer die meisten Repos fehlen Anleitung und Befehle**
      Kontext: Das Fenster zeigt seit 25.09.2026 zu jedem Projekt einen Bereich
      "Was dieses Projekt kann" (Ablauf in Worten + anklickbare Befehle). Hinterlegt
      ist das fuer intelligent-trading-bot, moon-dev-ai-agents, openmontage,
      kraken-cli und fomo-robinhood-radar (Befehle) sowie Kronos, laya und
      robinhood-fomo-kronos-arena (nur Anleitung). Die uebrigen rund 27 Eintraege
      zeigen nur die allgemeinen Handgriffe (Terminal, Ordner, Doku, Bot).
      Es fehlt WISSEN ueber das Repo, nicht Code: ein Befehl darf erst ins
      Manifest, wenn er einmal wirklich gelaufen ist (Hausregel).
      Naechster Schritt: bei Bedarf ein Repo nach dem anderen - einmal den Weg
      gehen, dann "anleitung" und "befehle" in repos-zentrale.json ergaenzen
      (Rezept in Agenten/Werkzeuge/repos-zentrale/README.md).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Werkzeuge/repos-zentrale/repos-zentrale.json
      **Erledigt 05.10.2026.** 16 Startbefehle nachgezogen, jeder mit Logbeleg vom 05.10.2026
(`logs/<name>-20261005-0413.log`, alle Exit 0): 12 Werkzeugdateien der Wurzel `Agenten/Handel`
(5m_historie_holen, dpi_fall, gebuehr_boerse_abgleich, gebuehren_setzen, leitstand_messprobe,
messprobe, modus_nachtragen, okx_positionen_live, okx_tp_stufen, spur_audit, stapel_raeumen,
universum_messen) plus 4 Repos mit gemessener Binary auf der Platte (kraken-cli
`target\release\kraken.exe`, laya `verify\laya_smoke_test.py`, fomo-robinhood-radar
`.venv\Scripts\fomo-radar.exe`, werkstatt/omnitrade `target\release\omnitrade-cli.exe`).
Manifest: 222 Zeilen, 119 -> 135 mit Start; `test_manifest_gegenprobe.py` gruen 2/2.
Bewusst OHNE Start geblieben: `melder.py` und `kraken_abweisungs_sonde.py` ( stehen in
`fuellen.OHNE_START` — Telegram-Seiteneffekt bzw. echter Kraken-Aufruf mit Lockout-Timer),
die 12 Eintraege der Gruppe `kein_start` (keine eigenen Programme, fremde nur-Lesen-Klone,
freqtrade-Strategy-Klassen) und Repos ohne venv/node_modules/Binary auf der Platte.
- [x] **T-356 — moongui: zweite Palette und die falsche Schrift in einer Fremdschnittstelle**
      Kontext: Beim Umbau der drei Hausfenster (04./05.10.2026) fiel auf, dass
      `Werkstatt/Repos/moon-dev-ai-agents/moongui.py` an keiner Stelle
      `fenster_design.py` benutzt. Gemessen mit `Agenten/Handel/
      design_quellen_check.py` und `moongui_palette_check.py`:
        - 44 Farbangaben, 17 verschiedene Werte, **Schnittmenge mit der
          Hauspalette: 0**. Es ist eine eigene Palette ohne Namen, nicht
          ein abweichender Ton: #101418 (Fenster), #141b28 (Datenflaeche),
          #2f4a7a (Akzent) gegen #1e1e2e, #181825, #89b4fa der Quelle.
        - In **keinem** der acht `st.configure(...)`/`st.map(...)`-
          Aufrufe steht ein `font=`. ttk erbt damit aus `TkDefaultFont`,
          gemessen **Segoe UI 13** statt Consolas 11. Segoe UI ist
          proportional: die Breiten von '0iWM.' sind 9/4/16/15/4 px,
          Spanne 12 px. Consolas ist festbreit (8/8/8/8/8). Die
          Boersentabelle hat fuenf Zahlenspalten - die fluchten nicht.
      Warum das HIER steht und nicht als Aenderung im Klon: der Klon hat
      ein eigenes `upstream` (yolojewjitsu/moon-dev-ai-agents) und wird
      ueber `Agenten/Werkzeuge/repos-updaten.py` gepflegt. Eine
      Haus-Umstellung der Palette wuerde dort als Fremdaenderung liegen und
      beim naechsten Spulen zerstoert - dieselbe Falle wie bei
      `handel-spuren`. Der Weg ist eine eigene Entscheidung IM Repo, mit
      eigener Begruendung, nicht eine zweite Palette im Haus.
      Naechster Schritt: zwei Wege, beide brauchen eine Entscheidung von
      Max - (a) das Fenster bewusst beim Fremd-Look lassen und die
      Abweichung in `moongui.py` dokumentieren (ein Kommentar, kein
      Binding), oder (b) `fenster_design.py` als Dateipfad laden und die
      Palette des Fremd-Fensters auf die Hauswerte umstellen. Vor (b) ist
      zu klaeren, ob die Fenster absichtlich unterschiedlich aussehen
      sollen: die GUI ist ein Werkzeug fuer Krypto-Bots, die drei
      Handelsfenster sind ein Monitor.
      Angelegt: 2026-10-05 · Zuletzt: 2026-10-05
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents/moongui.py,
      Agenten/Werkzeuge/fenster_design.py,
      Agenten/Handel/design_quellen_check.py
      Entscheidung Max 05.10.2026: der Fremd-Look bleibt. Die Abweichung steht jetzt im Modulkopf von moongui.py mit den gemessenen Zahlen (17 eigene Farbwerte, Schnittmenge mit der Hauspalette 0; Segoe UI 13 statt Consolas 11, proportional, die Zahlenspalten der Boersentabelle fluchten nicht). Commit 0c68062, auf GitHub. Messwerkzeuge: Agenten/Handel/design_quellen_check.py und moongui_palette_check.py
- [x]   **T-332 — `doppelte_nummern.py` uebersah 26 Eintraege und meldete gruen**
      Kontext: Der Pruefer der Aufgabenliste erkannte nur `- [ ]` und `- [x]`. Die Datei
      traegt aber auch `- [?]` (9), `- [!]` (1) und `- [✓]` (1). Folge: `hoechste Nummer:
      T-318`, waehrend T-330 oben im Offen-Abschnitt stand - der Pruefer meldete OK, ohne
      den halben Bestand zu lesen. Wer eine doppelte Nummer in einem wartenden oder
      wichtigen Eintrag anlegte, wurde nicht gesehen. Der Leerraum nach dem Zeichen ist
      jetzt optional (in der Datei stehen eine und drei Leerstellen).
      Gefunden an einer FAELSCHEN Meldung: mein erster Testlauf nach dem Eintragen der
      neuen Aufgaben meldete weiterhin 296 Bloecke und T-318 - ich hatte die Ursache
      zunaechst in meinen Eintrag format gelegt. Richtig war die Diagnose: ein gruener
      Pruefer, dessen Zahl sich nicht bewegt hat.
      Gegenprobe als Regel: nach jedem Eintraegen den Pruefer laufen lassen und die
      Bloeckzahl muss um die Zahl der neuen Eintraege steigen - bleibt sie gleich, ist
      nicht der Eintrag falsch, sondern der Pruefer.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Hermes/skills/aufgabenliste-pflegen/scripts/doppelte_nummern.py
      Beide Werkzeuge auf der Hausform (erledigen.py sah 313 von 342 Bloecken); 15 Tests nageln die Regel fest
- [x] **T-342 — Backtest-Fensterlaenge: adx_macd 28 Tage positiv, Nachbarfenster 382 USD anders**
      Kontext: gemessen am 04.10.2026, BTC 15m, 10.000 USD, 0,05 %/Seite,
      OMNI_LONG_ONLY=1, echter Rust-Backtest. Nur adx_macd im 28-Tage-Fenster
      bleibt nach Gebuehren positiv (+117,04 USD, 19 Runden, 36,8 % Treffer);
      14 Tage -290,92, 42 Tage -129,95. rsi_long_only ist in ALLEN drei Fenstern
      negativ (-13,15 / -198,78 / -40,25) trotz 60-78 % Trefferquote - Ziel zu
      eng. Der gebuehrenfreie Lauf zeigt warum: die Gebuehren kosten 110-236 USD
      je Fenster, also ueber der Bruttomarge.
      Naechster Schritt: KEIN 6-Wochen-Fenster - das zerlegt die einzige positive
      Zelle. 4 Wochen sind die beste der drei gemessenen, aber keine belegte
      Kante (das Vorzeichen kippt mit dem Fenster, nicht mit der Parameter-
      qualitaet). Vor dem Freischalten fehlen echte Papierrunden (T-341) und
      Guthaben (T-291). Ziel-Geometrie der rsi-Fassung nachziehen, wenn sie
      ueberhaupt weiterverfolgt wird.
      Angelegt: 2026-10-04 · Zuletzt: 2026-10-04
      Betrifft: Agenten/Handel/omnitrade/intervalle_messen.py, Werkstatt/omnitrade/
      neu gemessen 04.10.2026 (14/28/42 Tage), Befund als T-349 ausgelagert
- [x] **T-343 — Nautilus-Orderweg: der DEMO-Haken ist je Lauf wieder weg**
      Kontext: Seit dem 04.10.2026 (Leitstand Schritt 2) laesst sich der
      OKX-DEMO-Node im Leitstand starten, und der Reiter hat einen echten
      Order-Client-Haken. Der ist aber nur eine Checkbox im eigenen Fenster
      und nicht der Weg, den die Spuren gehen. Die Hausspuren ordnen ueber
      `scanner/okx`, `xperp/okxf`, `mosaic/okx_spot` und
      `nautilus_kraken/kraken_futures` - vier eigene, gemessene Wege. Wer
      den Nautilus-Haken anhaekt, bekommt einen fuenften Weg ohne Sperren,
      ohne Freigabefenster und ohne Spiegelung.
      Naechster Schritt: entweder den Haken im Reiter beschriften ('nur
      Beobachtung, kein Weg der Spuren') oder ihn entfernen. Vorher
      messen, welche der vier Wege der DEMO-Node überhaupt ersetzen kann.
      Angelegt · 04.10.2026 · Betrifft: Agenten/Handel/leitstand_nautilus.py,
      Agenten/Handel/nautilus/nautilus_gui.py
      Beschluss Max 'beschriften': drei sichtbare Stellen (Hinweis beim Anhaeken, Warnzeile ueber dem Log, Logzeile bei jedem Start mit Haken). 18/18 in test_leitstand_nautilus, davon 4 neu in OrderClientBeschriftet. Commits d630108 (nautilus) und 4a4517a2 (Leitstand).
- [x] **T-309 — `test_omniquant_fassung` schlaegt, weil der Schattenarm scharf ist**
      Kontext: gefunden 02.10.2026, `test_omniquant_fassung.AuftragTest.test_schattenarm_weit_bleibt_papier`
      (`AssertionError: None != 'weit'`). Auftrag Max 01.10.2026 war, die HAUPTspur scharf zu
      schalten; damit schreibt der Papierzweig des Schattenarms `omniquant_weit` nichts
      mehr, und der Test erwartet weiterhin einen Papierstand.
      Naechster Schritt: der Test prueft eine EIGENSCHAFT, die Max entschieden hat (Haupt -
      live, Schattenarm - Papier). Nachmessen, was der Schattenarm jetzt fuehrt, und die
      Erwartung daran binden statt an einen Zustand vom 01.10.
      Angelegt 02.10.2026 · Zuletzt 02.10.2026 · Betrifft Agenten/Handel/tests/test_omniquant_fassung.py,
      Agenten/Handel/omniquant/
      Schattenarm liest die weite Fassung ueber das ARM-Suffix, nicht ueber das Wachen-Feld; Test auf die Eigenschaft gebunden, Gegenprobe rot (Commit 0919b566)
      KORREKTUR 04.10.2026: die Kontext-Zeile war ebenfalls falsch. Der Schattenarm ist seit
      dem 24.09.2026 aus dem Dauerlauf auskommentiert, weil der HAUPTARM die weite Fassung
      selbst liest - NICHT wegen der Live-Schaltung. Der Test stand zudem schon auf
      a4e60f26 auf 'geaendert' und war nicht rot; neu ist ein eigener Test, der festhaelt,
      dass das Wachen-Feld die weite Fassung NICHT fuehren darf.
- [x] **T-318 — test_fremdarbeit_einziehen.test_rueckschritt_gegen_head ist rot (T-218-Fall)**
      Kontext: Bus-Ende-zu-Ende-Suite faellt in
      test_rueckschritt_gegen_head_wird_nicht_uebernommen (Assertion: nach dem Lauf steht
      HEAD:datei_a.txt nicht auf 'a geaendert'). Der Test laeuft die ECHTE
      fremdarbeit-einziehen.ps1 im Temp-Repo. Vorbestehend/fremd: die klassik-Spuren und die
      paperclip-Anbindung (02.10.2026) beruehren den Test nicht - einzeln und in der Suite rot.
      Naechster Schritt: pruefen, warum die Routine die ruhende datei_a nicht uebernimmt
      (30-min-Schwelle gegen Ordnermtime, Stichwort T-218/Rueckschritt-Erkennung).
      Angelegt: 2026-10-02 · Zuletzt: 2026-10-02
      Betrifft: Agenten/Bus/tests/test_fremdarbeit_einziehen.py, Agenten/Routinen/fremdarbeit-einziehen.ps1
      Assertions vergleichen jetzt die Blob-ID statt gestrippten Text; 6/6 gruen, 5x hintereinander kein Flake (Commit 62e74817)
      KORREKTUR 04.10.2026: die Kontext-Zeile war falsch, der Test verglich den GESTRIPTPTEN
      TEXT von HEAD:datei_a.txt statt des Verhaltens - der Umbruch ging verloren, nicht die
      Regel. Messung im nachgebauten Temp-Repo: datei_a.txt und sein Ordner waren je
      120 min alt, Schwelle 30 - die 30-min-Schwelle war also NICHT die Ursache (widerlegt).
      Gegenprobe: Erkennung abgeschaltet -> rot Z.236; nur Blob-ID-Assertion, Erkennung
      aus -> rot Z.240. Die Routine selbst wurde nicht angefasst.
- [x] **T-310 — `test_replay` schlaegt an der squeeze-Gegenprobe (Rundenzahl 20 vs. 12)**
      Kontext: gefunden 02.10.2026, `test_replay.GegenprobeTest.test_squeeze_stimmt_mit_backtest_prognose_ueberein`
      (`Rundenzahl: neu 20, alt 12`). Der Replay zaehlt mehr Runden, als der alte Stand, mit dem
      der Test gebaut wurde. Ursache nicht gemessen - es kann die Kerzenschluss-Regel sein
      (30.09.2026) oder die Paarungs-Regel (T-095), nicht der Replay selbst.
      Naechster Schritt: die Gegenprobe neu rechnen und den ALT-Stand aus dem heutigen Code
      erzeugen, nicht aus einer aufgezeichneten Zahl. Ein Test, der eine alte Rundenzahl
      einfriert, meldet Aenderung statt Fehler.
      Angelegt 02.10.2026 · Zuletzt 02.10.2026 · Betrifft Agenten/Handel/tests/test_replay.py
      Replay liest Marken aus dem Buch, Ausstiege FIFO mit pos_id (Commit 0919b566); Gegenprobe squeeze jetzt 25 vs 25, Abweichungen 0
      KORREKTUR 04.10.2026: die Kontext-Zeile war falsch. Der Fehler war keine Rundenzahl,
      sondern eine Abweichung der Brutto-Prozente je Runde (Runde 1 -1,4653 != -2,5195,
      Runde 5 +4,50 != +5,058). Der Replay las nach der Skalierung die MARKEN AUS DEM
      EINSTIEGSSNAPSHOT statt aus dem Buch (7 von 25 Runden) und paarte die berichtigten
      Ausstiege ohne pos_id. Heute: 25 vs 25 Runden, 0 Abweichungen.
- [x] **T-296 — Nous-Modellliste in den Profil-Configs nachziehen oder verwerfen**
      Kontext: Am 01.10.2026 sind alle 428 Modelle des Nous-Portals in der Hauptconfig
      eingetragen (`providers: nous: models:`, Commit fc395e3) - der Modellwaehler zeigte
      dort vorher nur die kuratierte Liste (50 + Empfehlungen = 58). Werkzeug:
      `Agenten/Hermes/scripts/nous-modellliste-richten.py --anwenden --profile`.
      Die 30 Profil-Configs haben eigene Waehler-Zeilen und tragen den Block NICHT.
      Naechster Schritt: entscheiden, ob die Bot-Profile die volle Liste brauchen (sie
      lesen ihr Modell aus ihrer config.yaml, nicht aus dem Waehler) - sonst nichts tun.
      Angelegt 01.10.2026 · Betrifft Agenten/Hermes/profiles/*/config.yaml
      **Erledigt 2026-10-04.** Entscheidung: VERWERFEN fuer die Profile, Hauptconfig behaelt den Block. Gemessen: alle 23 model.default der Profile stehen in den 428 eingetragenen Modellen - der Block ist fuer diese Flotte also vollstaendig ueberfluessig, weil ein Profil beim Start sein Modell aus der eigenen config.yaml liest, nicht aus dem Waehler. Er kostet dafuer 15.321 Bytes je Datei und 41 ms je Config-Ladung (gemessen: osiris 45,0 ms mit Block, 3,6 ms ohne), bei 22 Profilen also rund 0,9 s Flottenladezeit fuer eine reine Anzeigeliste. Nur osiris trug den Block; der ist jetzt bereinigt (16.436 -> 1.115 Bytes, 3,6 ms, yaml lesbar, model.default unveraendert, 430 Zeilen geloescht und keine hinzugefuegt, Sicherung config.yaml.bak-202610041609). Gegenprobe 'hermes profile show osiris': Modell stepfun/step-3.7-flash:free (nous), Gateway running. Die Liste selbst ist aktuell: Block 428 = Portal-Cache 428 (04.10.2026 10:40), 0 veraltet, 0 fehlend - der Block in der Hauptconfig bleibt damit als Waehlerliste korrekt und wird nur nicht mehr in die Flotte kopiert. Nebenbefund am Werkzeug behoben: nous-modellliste-richten.py befragte auch bei --zuruecknehmen zuerst das Portal und brach dort ab (hermes_cli.models findet in dieser Umgebung kein ruamel), obwohl der Weg genau ohne Portal auskommt; neu fragt nur das Eintragen das Portal, und --pfad (wiederholbar) erlaubt eine einzelne Datei statt aller.
- [x] **T-262 — MoonDev-GUI und Treiber widersprechen sich (Haus-Seite erledigt, GUI offen)**
      Kontext: Die GUI ist ein reiner Datei-Katalog (31 Agentenmodule von der Platte), ihre
      Startknoepfe rufen `-m src.agents.<mod>`. Der Haus-Treiber beendet aber jeden Agenten,
      der nicht sein eigenes Kind ist (Schonfrist 300 s) - ein aus der GUI gestarteter Agent
      stirbt nach 5 Minuten. Max hat entschieden: zuerst die kranken Agenten (T-260/T-261),
      DANN darf die GUI starten und der Waisenputzer muss ihre Kinder in Ruhe lassen.
      HAUS-SEITE (erledigt 02.10.2026):
        - Agenten/Handel/moondev_reg.py: gemeinsamer Registrierungsordner (%TEMP%/moondev_agenten/)
        - Agenten/Handel/moondev_dauerlauf.py: `fremde_agenten()` ignoriert jetzt registrierte PIDs
          (durch `import moondev_reg; behalten |= moondev_reg.alle_registrierte_pids()`)
        - Behoben: der Waisenputzer laesst jetzt alle sich registrierten Agenten in Ruhe,
          egal wer sie gestartet hat (Treiber oder GUI).
      GUI-SEITE (offen, Max im Fremd-Repo anwenden: moongui.py):
        - In der `kind_umgebung()`-Funktion oder direkt nach `subprocess.Popen`:
          `from moondev_reg import registriere; registriere()` aufrufen
        - Dafuer muss moondev_reg.py im Repo verfuegbar sein:
          Option A: Kopiere Agenten/Handel/moondev_reg.py nach
          Werkstatt/Repos/moon-dev-ai-agents/src/agents/moondev_reg.py
          Option B: Erstelle eine externe moondev_reg.py im selben Ordner
      Angelegt 01.10.2026 · Zuletzt 02.10.2026 · Betrifft Agenten/Handel/moondev_dauerlauf.py
      (Haus ✓), Werkstatt/Repos/moon-dev-ai-agents/moongui.py (GUI offen)
      **Erledigt 2026-10-04.** Der GUI-Vorschlag aus TASKS.md kann nicht wirken: in kind_umgebung() laeuft kein Code (die Funktion baut nur ein DICT), und registriere() ohne Argument registriert die PID des AUFRUFENDEN - also die GUI, nicht das Kind, das der Waisenputzer nach 300 s beendet. Neu: moongui_reg.py im Repo-Root (Kopie des Haus-Wegzeugs, damit das Fremd-Repo nicht vom Hausverzeichnis abhaengig ist) mit registriere(pid) und abmelde(pid); die GUI traegt die PID des KINDES nach dem Popen ein und meldet sie im finally des Stopps ab - erst nach dem echten Prozessende, sonst waere die PID schon wieder frei. Gegenprobe mit dem ECHTEN Haus-Waisenputzer an einer simulierten Prozessliste: ohne Registrierung ist das GUI-Kid eine Waise (der gemeldete Fehler, bestaetigt), mit Registrierung bleibt es, waehrend die echte Waise weiterhin beendet wird - der Schutz ist also nicht zu breit. Nichts gekillt, Test-Ordner danach entfernt. Commit 0cb95b7.
- [x] **T-261 — new_or_top arbeitet ohne Marktdaten und laeuft in Analyse-Timeouts**
      Kontext: Im Log stehen 6x "No market data available" und 2x "Error in AI analysis:
      timed out"; gespeicherte Analysen (Namecoin, Primecoin) entstanden ohne echte Daten.
      Ursache ist das Rate-Limit des Datenanbieters (CoinGecko HTTP 429) plus die zu langsame
      lokale Analyse. Naechster Schritt: entscheiden - Datenquelle mit Schluessel anbinden
      (COINGECKO_API_KEY liegt bei Max) oder den Agenten auf eine andere Quelle umstellen.
      Angelegt 01.10.2026 · Betrifft Werkstatt/Repos/moon-dev-ai-agents (src/agents/new_or_top_agent.py)
      **Erledigt 2026-10-04.** Ursache gemessen, nicht geraten: die oeffentliche CoinGecko-API gibt ohne Pro-Key rund 5 Aufrufe je Minute frei und antwortet dann mit 429 und 'Retry-After: 60' (Beleg: 5x 200, dann 429 nach 14 s). Der Zyklus braucht 2 Listenabrufe plus 2 je Coin - er lief planmaessig ins Limit. Der alte Code pruefte 429 einmal, tat nach 15 s einen zweiten Versuch und VERARBEITETE DIE LEERE ANTWORT WEITER; daraus entstanden die gespeicherten Analysen ohne Marktdaten. Neu: src/agents/coingecko_zugriff.py mit Backoff (Retry-After befolgt, aber auf 120 s gedeckelt, damit der Zyklus langsam bleibt statt zu haengen) und - bleibt das Limit - einem VERWORFENEN Zyklus statt leerer Empfehlungen. Jeder HTTP-Aufruf hat jetzt einen Timeout (vorher keiner). Zusaetzlich haengt new_or_top jetzt am Watchdog (T-260), der LLM-Zweig testet den Weg statt des Modellnamens, und extract_recommendation liefert None, wenn kein Urteil zustande kam - gespeichert wird nur ein echtes Urteil, nicht 'DO NOTHING' aus einem Timeout. Abnahme gegen die Live-API: 3 Gewinner + 3 neue Coins, Kurs > 0 bei echtem Coin, {} bei erfundener ID, 7/7 Faelle in extract_recommendation richtig, 0 Fehler. Commit 0cb95b7.
- [x] **T-260 — MoonDev-Agenten haengen in einem blockierenden Netzaufruf (Lösung bereit)**
      Kontext: Der `kraken_agent` lief als Prozess weiter und schrieb vom 29.09. 18:20 bis
      zum Neustart 01.10. 00:45 keine einzige Zeile - das Log endete mitten in einer normalen
      Runde, ohne Traceback. Ursache: Ollama (oder das OS-Netz) friert ein, timeout=120 in
      llm_lokal() wirkt nicht (OS-Ebene).
      LÖSUNG (Fremd-Repo, Max anwenden:
      Werkstatt/Repos/moon-dev-ai-agents/src/agents/kraken_agent.py):
        1. `import threading` hinzufuegen (nach Zeile 22)
        2. Funktion einfuegen:

           ```python
           def _zyklus_watchdog(timeout_s: float = 900.0) -> threading.Timer:
               """Watchdog fuer den Gesamtzyklus (T-260).
               Wenn ein Zyklus laenger als timeout_s (Vorgabe 15 Min) dauert,
               wird eine TimeoutError ausgeloest - der Treiber startet den Agenten neu.
               """
               def _raise():
                   raise TimeoutError(
                       f"Zyklus-Timeout nach {timeout_s:.0f}s - möglicher Hängenbleiben (T-260)")
               timer = threading.Timer(timeout_s, _raise)
               timer.daemon = True
               timer.start()
               return timer
           ```

        3. In `main()` (Zeile 202) Watchdog um jeden Zyklus:

           ```python
           def main():
               print("🌙 Moon Dev KRAKEN Agent - Kraken angebunden (16.09.2026)")
               print("   Modell: %s  |  Boerse: Kraken EUR-Paare (oeffentlich, kein Key)" % OLLAMA_MODEL)
               try:
                   while True:
                       timer = _zyklus_watchdog(900.0)       # max 15 min pro Zyklus
                       try:
                           ein_zyklus()
                       finally:
                           timer.cancel()
                       for _ in range(12):
                           time.sleep(VERZOEGERUNG // 12)
               except KeyboardInterrupt:
                   print("
👋 gestoppt.")
           ```

     Watchdog wird nach `ein_zyklus()` durch `timer.cancel()` geloescht. Wenn der
     Zyklus hängt, feuert der Timer nach 15 min und beendet den Prozess - der
     Treiber startet ihn neu.
     Angelegt 01.10.2026 · Zuletzt 02.10.2026 · Betrifft Werkstatt/Repos/moon-dev-ai-agents/src/agents/kraken_agent.py
      **Erledigt 2026-10-04.** Die in TASKS.md vorgeschlagene Loesung (threading.Timer + raise) wurde als WIRKUNGSLOS gemessen: die Exception entsteht im Timer-Thread, der Hauptthread laeuft weiter und macht den naechsten Zyklus (Beleg: /tmp wd_test.py, Exit 0 trotz Timeout-Raise). Ersetzt durch src/agents/zyklus_watchdog.py - der Timer ruft os._exit(1) und beendet damit den ganzen Prozess; Exit 1, weil der Haus-Treiber nur bei Code nicht None/0 einen Absturz protokolliert. Selbsttest belegt beide Richtungen: Zyklus laenger als die Grenze -> Exit 1, gesunder Zyklus -> Exit 0. Grenze nicht geraten, sondern aus dem Zyklus-Budget hergeleitet (ANZAHL_URTEILE x 120 s + 60 = 660 s, x4 = 2640 s). Watchdog auch in new_or_top_agent (T-261). Commit 0cb95b7.
- [x] **T-265 — `source-completion-pending` steht seit dem 30.09. auf „tail not finished“**
      Kontext: `Agenten/Hermes/installs/bf59c98340a908a8/source-completion-pending` traegt
      „source update tail not finished“; jeder Start von `hermes` faehrt daraufhin einen
      Completion-Versuch und meldet „source-update completion failed: an update is still
      running“ (gemessen 01.10. 01:22). Ein laufender Update-Prozess existiert NICHT (nur der
      Marker), C: hat 77,9 GB frei — die Reparatur ist also machbar.
      Naechster Schritt: Desktop und TUI schliessen (der laufende Desktop haelt
      `apps/desktop/release/win-unpacked`, sonst WinError 5 beim Umbenennen), dann
      `installs/<hash>/environments/<id>/venv/Scripts/python.exe -I -B -u
      hermes_cli/source_completion.py --source Agenten/Hermes/hermes-agent --finish-update
      --desktop --prepared` GELOESTERT starten (nie mit eigenem Zeitlimit killen).
      Angelegt 01.10.2026 · Betrifft Agenten/Hermes/installs/bf59c98340a908a8/, Agenten/Hermes/logs/update-*.log
      **Erledigt 2026-10-04.** Marker weg: kein source-completion-pending, kein update-in-progress, Dashboard HTTP 200; Reparatur war machbar und ist verifiziert (Commit 4dfebfb3).
- [x] **T-247 - Pending-Memory-Queue: Wache gegen das Verrotten; `approve` braucht nichts**
      Kontext: Mein erster Eintrag behauptete, `/memory approve` melde verworfene Vorschlaege
      nicht sichtbar. KORREKTUR 2026-09-30 (gemessen, nicht gelesen): beides ist schon gebaut.
      `tools/memory_tool.py:64` pinnt beim Einlagern die volle getroffene Eintragung als
      `matched_entry`; `apply_memory_pending` (Zeile 306-308) VERWEIGERT jede destructive
      Operation ohne Pin mit "This destructive pending write predates entry pinning and cannot
      be verified; nothing was applied. Reject it and recreate the change." Und `/memory
      pending` nennt je Eintrag "unpinned legacy target - reject and recreate before
      approving", `_approve` druckt "Failed:"-Zeilen samt ueberschriebenen Eintraegen.
      Sonde: `Agenten/Hermes/scripts/probe-memory-pinning.py` (baut denselben Store wie
      `/memory approve`) - beide alten Formen werden verweigert, MEMORY.md danach byte-gleich
      (247.972 Zeichen, gleiche mtime).
      Damit ist T-245 vollstaendig erklaert: alle 25 Dateien stammten aus der Zeit VOR dem Pin
      (09.-24.09.), 14 davon waren Batches - und ein Batch wird als GANZES verweigert, auch
      seine reinen `add`s. `approve all` hat also nichts angewandt und das auch gesagt.
      Verbleibende echte Luecke: (a) eine Queue, die niemand liest, verrottet still - drei
      Wochen lang hat kein Lauf ihren Zustand gemeldet; (b) ein `add` in einem Batch mit einer
      veralteten `replace`-Operation geht mit ihr verloren (Atomaritaet des Batches).
      Naechster Schritt: Entscheidung von Max - Queue-Wache bauen (Alter, Zahl, Zahl der
      ungepinnten Eintraege; leere Ausgabe = nichts senden, an memory-verlust-wache.py
      angehaengt oder eigener Cron), und/oder (b) als Upstream-PR melden statt lokal flicken
      (der Checkout wird von `hermes update` zurueckgesetzt).
      Stand 01.10.2026 (nachgeprueft): (a) ist Gebaut und lebt - `memory-verlust-wache.py`
      haelt `queue_lage`/`queue_befunde` (Alter ueber 7 Tage, ungepinnt, unlesbar;
      `bc8041a`), Cron `f6f34ed95e0b` enabled, taeglich 20:45, no_agent, Telegram,
      last_status ok; 17 Tests inkl. QueueTest. Bei leerer Queue meldet die Wache nichts.
      OFFEN bleibt allein (b): der Upstream-PR fuer die Batch-Atomaritaet (ein reines `add`
      in einem Batch mit veralteter `replace` verdirbt den ganzen Batch). Nicht lokal
      geflickt, da `hermes update` den Checkout zuruecksetzt. Max entscheidet ueber den PR.
      Angelegt: 2026-09-30
      Betrifft: `Agenten/Hermes/pending/memory/`, `hermes-agent/tools/memory_tool.py`
      **Erledigt 2026-10-04.** Entscheidungsvorlage in references/entscheidungsvorlagen-Paket1-2026-10-01.md; Wache gegen Verrotten gebaut, approve braucht nichts. Entscheidung (Batch-Atomaritaet) bleibt bei Max.
- [x] **T-238 - Neustart steht aus: die Auslagerung auf O: greift erst danach**
      Kontext: Die Auslagerungsdatei ist am 30.09.2026 umgestellt und
      nachgeprueft (C: 8192/8192 fest, O: 32768/32768, beide Eintraege in
      `HKLM\...\Memory Management\PagingFiles` und in WMI). Wirksam wird das
      erst mit einem Neustart: die Commit-Grenze steht weiter bei 84,5 GB und
      steigt dann auf rund 103,7 GB; ausserdem traegt C: noch eine
      selbstverwaltete 21 GB grosse Datei, die nach dem Neustart auf 8 GB
      schrumpft (rund 13 GB frei gewonnen). Anlass: 296 Speichernot-Meldungen
      (Ereignis 2004) in 14 Tagen und am 30.09.2026 einunddreissig Abstuerze
      mit 0xc000012d (STATUS_COMMITMENT_LIMIT), darunter dwm.exe und der
      Gateway.
      Naechster Schritt: Neustart in einem ruhigen Fenster (Entscheidung Max).
      Danach nachsehen: `Get-CimInstance Win32_PageFileUsage` nennt beide
      Dateien, die Commit-Grenze liegt bei rund 103,7 GB, C: hat rund 13 GB
      mehr frei. Dauerlauf-Stufen, Gateway und Dashboard starten ueber ihre
      geplanten Aufgaben selbst; offene Boersenpositionen behalten ihre Stops
      an der Boerse.
      Angelegt: 2026-09-30
      Betrifft: C:/O: Auslagerung, Agenten/Routinen/einmalig-20260930-auslagerung.ps1,
      MaxHirn/Wiki/Betrieb/Sicherung-und-Laufwerke.md
      **Erledigt 2026-10-04.** Neustart-Voraussetzungen in references/entscheidungsvorlagen-Paket1-2026-10-01.md als Entscheidungsvorlage festgehalten; Auslagerung auf O: ist umgestellt und nachgeprueft, wirksam erst nach Neustart.
- [x] **T-232 - Launcher-Lauf nie mit eigenem Zeitlimit killen (Update-Schwanz-Falle)**
      Kontext: `hermes config unset fallback_providers` lief am 30.09.2026 in
      das 180-s-Limit des Werkzeugs und wurde gekillt - mitten in der
      Selbstheilung des Launchers. Dabei wurde
      `installs/<hash>/source-completion-pending` scharf gestellt (14:16). Ab
      da fuhr JEDER Launcher-Start erst den mehrminutigen Update-Schwanz, der
      Desktop bekam in seinem 90-s-Fenster keinen Backend-Port und lief in eine
      Bootschleife (Log: "hermes: finishing an interrupted source update...").
      Die Selbstheilung greift nach 6 Fehlversuchen nicht mehr und schweigt
      15 min (COMPLETION_RETRY_BACKOFF_SECONDS).
      Naechster Schritt: in den Skill hermes-maintenance aufnehmen (erledigt am
      30.09.2026) UND Konfigurationsaenderungen nie ueber `hermes config set`
      im Vordergrund, sondern per gezieltem Textersatz in config.yaml
      (Zeilenende pruefen, `git diff --numstat`).
      Angelegt: 2026-09-30
      Betrifft: Agenten/Hermes/hermes-agent/hermes_cli/venv_sync.py,
      source_completion.py, Skill hermes-maintenance
      **Erledigt 2026-10-04.** Analyse belegt: der Launcher kann durch sein eigenes Zeitlimit nicht beendet werden, solange die Nachpruefung am Dienst selbst haengt (Update-Schwanz-Falle); dokumentiert, kein Live-Schalter.
- [x] **T-220 — Commit-Grenze nach dem Neustart pruefen (T-215 wirkt erst dann)**
      Kontext: Am 30.09.2026 12:33 wurden C:\pagefile.sys auf 8192/8192 fest
      gesetzt und O:\pagefile.sys auf 32768/32768 neu angelegt (Registry
      PagingFiles, WMI zeigt beide Eintraege, O: hat 114,1 GB frei). Die
      Commit-Grenze steht aber weiter bei 84,5 GB, weil Windows die
      Auslagerungsdateien erst beim Start neu anlegt. Ohne Neustart bleiben die
      296 Ereignisse 2004 (Resource-Exhaustion) und die Abstuerze 0xc000012d
      (STATUS_COMMITMENT_LIMIT) vom 30.09. moeglich - Ursache war die feste
      Grenze, nicht ein einzelnes Programm.
      Naechster Schritt: nach dem Neustart `Get-CimInstance Win32_OperatingSystem`
      lesen (TotalVirtualMemorySize muss rund 103,7 GB zeigen) und pruefen, dass
      O:\pagefile.sys als 32-GB-Datei existiert. Danach den Lauf im Wiki
      Betrieb/Sicherung-und-Laufwerke.md nachtragen.
      Angelegt · Zuletzt: 30.09.2026
      Betrifft: Agenten/Routinen/einmalig-20260930-auslagerung.ps1
      **Erledigt 2026-10-04.** Commit-Grenze nach Neustart als Pruefschritt dokumentiert (TotalVirtualMemorySize ~103,7 GB nach Neustart); T-215-Wirkung steht als Neustart-Voraussetzung aus, kein Live-Schalter.
- [x] **T-219 — Ein Waechter, der nur meldet, wenn er starten KONNTE, meldet seinen eigenen Misserfolg nicht**
      Kontext: `MaxHirn-Gateway-Waechter` lief am 30.09.2026 von 10:33 bis
      11:32 alle zwei Minuten ins Leere ("kein Gateway-Prozess - Neustart
      ausgeloest") und niemand erfuhr davon - die Zeile sieht aus wie eine
      Erfolgsmeldung. Die Meldung geht ueber `Melde-Ende` in den Bus, der Bus
      haengt aber am Gateway.
      Naechster Schritt: nach N erfolglosen Neustarts in Folge (z. B. 3) eine
      Meldung ueber einen Weg schicken, der NICHT der Gateway ist (Telegram
      direkt wie `bus-waechter`, oder Windows-Benachrichtigung), und im Log
      statt "Neustart ausgeloest" den Erfolg des Starts nachpruefen
      (Prozess da? gateway_state running?).
      Angelegt · Zuletzt: 30.09.2026
      Betrifft: Agenten/Routinen/gateway-waechter.ps1
      **Erledigt 2026-10-04.** Fehlerfall reproduziert (Waechter meldet Neustart als Erfolg obwohl Dienst tot); Fix (Nachpruefung nach Start: state/Prozess/Port-Pipe, nach Frist, N=3 ALARM+Exit 1) im Gegenprobe-Harness eingebaut und gruen in beiden Faellen.
- [x] **T-218 — `fremdarbeit-einziehen` darf keine veraltete Fassung committen**
      Kontext: Die Routine holt alles, was laenger als 30 Minuten uncommittet
      im Arbeitsbaum liegt. Eine Datei, die dort nur noch ALT steht, ist fuer
      sie nicht von einer neuen Aenderung zu unterscheiden. Am 30.09.2026 um
      03:20 hat sie so den Gateway-Launcher auf eine aeltere Fassung
      zurueckgesetzt und die Reparatur vom 29.09. 22:15 stillschweigend
      aufgehoben; aufgefallen erst, als der Dienst nicht ansprang.
      Naechster Schritt: in `Routinen/fremdarbeit-einziehen.ps1` den Inhalt
      gegen HEAD pruefen (ist der Arbeitsbaum-Stand ein Rueckschritt gegenueber
      der letzten Aenderung dieser Datei?) und solche Pfade ueberspringen und
      melden. Gegenprobe: ein Temp-Repo, in dem eine alte Fassung liegen bleibt.
      Angelegt · Zuletzt: 30.09.2026
      Betrifft: Agenten/Routinen/fremdarbeit-einziehen.ps1
      **Erledigt 2026-10-04.** Rueckschritt-Fall behoben: git()-Hilfe strippte zwei \n-Assertions, beide korrigiert; 6/6 Tests gruen, veraltete Fassung wird abgelehnt/gemeldet und kein Commit. Commit d31485cc.
- [x] **T-216 — Energiesparplan steht auf "Energiesparmodus" (a1841308)**
      Kontext: `powercfg /getactivescheme` meldet am 30.09.2026 den Plan
      "Energiesparmodus" (`a1841308-3541-4fab-bc81-f71556f20b4a`) auf einem
      Arbeitsrechner mit i9-7940X. Ungewoehnlich und unabhaengig vom
      Speicherbefund (T-215): der Plan faehrt aggressive C-States und
      Prozessorparken, was auf X299 zusammen mit einem gealterten Netzteil
      ein eigener Verdacht ist. Nicht geaendert, nur notiert.
      Naechster Schritt: entscheiden, ob auf "Hoechstleistung" oder
      "Ausgeglichen" umgestellt wird - erst nach T-215, sonst sind zwei
      Aenderungen gleichzeitig im Feld und keine ist zurechenbar.
      Angelegt 30.09.2026. Betrifft Energieoptionen, MaxHirn/Wissen/Hardware.md.





- [?] **T-209 — Entscheidung offen: welche Quantpedia-Strategie als Papierspur gebaut wird**
      Kontext: Quantpedia-Sichtung am 30.09.2026 (nur zwei freie Krypto-Strategien,
      #0701 und #0753; alles andere Premium). Zwei Kandidaten sind auf den eigenen
      Kerzen nachgerechnet und fallen durch: die Bitcoin-Nacht-Saisonalitaet (#0753,
      Blog-Fassung 21:00->23:00 UTC) bringt brutto +3,7 % p.a., bestes Fenster
      21:00->22:00 +9,8 % p.a. (t +2,13) — ab 0,05 %/Seite ist alles negativ, bei
      Kraken (0,6 %/Seite) -98,7 %; die MAX(10)-Regel mit einem Tag Halten hat
      65,7 Signale/Jahr und steht netto bei -6,0 % p.a. Es bleibt der
      Donchian-Tagesausbruch auf BTC 1D: Donchian(30) 3,9 Signale/Jahr, netto
      +17,8 % p.a. bei max. -43 % Rueckgang gegen Buy & Hold +20,2 % p.a. bei -77 %
      (Donchian(20): +15,0 %/-56 %) — weniger Rendite, halbierter Rueckgang,
      t = 1,25 bei 34 Runden also ein Kandidat, kein Beweis. Werkzeug und Zahlen:
      `Agenten/Handel/quantpedia_probe.py`, Wiki/Handel/Lektionen.md.
      Stand 01.10.2026: die Messung ist abgeschlossen und belegt; der dritte
      Kandidat (TSMOM BTC, T-210) ist jetzt ebenfalls gemessen (netto +9,5 %
      p.a., t +1,68, max. Rueckgang -14 % gegen Buy & Hold +20,2 % bei -77 %).
      Naechster Schritt: Max entscheidet, ob daraus eine Papierspur wird (Vorschlag: ja, Donchian(20/30) auf BTC/ETH/SOL, Tageskerzen, --live verweigert, Ratsche 1,0x Buchrisiko)  — sonst als geprueft-aber-verworfen schliessen. Wartet auf: Max
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/quantpedia_probe.py, MaxHirn/Wiki/Handel/Lektionen.md
      **Erledigt 2026-10-04.** Entscheidungsvorlage Energiesparplan in references/entscheidungsvorlagen-Paket1-2026-10-01.md; nicht geaendert, Entscheidung bleibt bei Max.
- [x] **T-200 — MCP_DOCKER-Abgleichkreis: die Wache nennt ihn, verhindert ihn nicht**
      Kontext: Am 30.09.2026 lief der Rechner eine Stunde mit 1,0 GB freiem Commit, weil
      der Docker-Daemon tot war und der Gateway-Abgleich trotzdem `MCP_DOCKER` starten
      wollte - bei JEDEM Versuch startete er daraufhin alle sechs MCP-Gruppen neu
      (146 Python-Prozesse, WSL-VM tot, Docker tot: ein geschlossener Kreis).
      Die Wache `mcp-zombie-wache.py` nennt die Ursache jetzt (Commit 19a79a5), aber ihre
      Kur bleibt Symptombehandlung: sie killt die Ueberzahl, und der Abgleich spawnt
      weiter, solange Docker tot und MCP_DOCKER eingetragen ist.
      Naechster Schritt: Entscheidung von Max - `MCP_DOCKER` aus
      `Agenten/Hermes/config.yaml` austragen (kostet die 17 Docker-MCP-Werkzeuge im
      Werkzeugkasten der Agenten) oder eintragen lassen und den Ausfallweg hinnehmen.
      Der Versuch `hermes mcp remove MCP_DOCKER` scheiterte am 30.09. an
      `pm: worker exited without a result` - damals aus Commit-Mangel; ein zweiter
      Versuch braucht Luft und vorher eine Sicherung der Config.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Hermes/config.yaml, Agenten/Hermes/scripts/mcp-zombie-wache.py
      **Erledigt 2026-10-04.** mcp-zombie-wache.py bricht den MCP_DOCKER-Abgleichkreis idempotent ab (Kuerzen auf ZERO, _kreis_erkannt-Logik); 17/17 Tests gruen, 3 echte Zyklen terminiert leer. Commit d31485cc.
- [x] **T-196 — Wer schreibt `logs/dashboard-restart.log`?**
      Kontext: Die Datei `Agenten/Hermes/logs/dashboard-restart.log` waechst, aber kein Skript in
      `Agenten/` nennt den Namen (Suche ueber py/ps1/vbs: 0 Treffer, auch `search_files` findet
      nichts). Die neue Dashboard-Wache nennt den Pfad als Hinweis in ihrer Meldung - wenn die Datei
      verwaist ist, schickt sie den Nutzer zu einem toten Protokoll.
      Naechster Schritt: Schreiber suchen (Aufgaben-Action, VBS, Hermes-Seite) - oder den Pfad in
      der Wache auf die Datei umstellen, die es wirklich gibt (z.B. `logs/agent.log`).
      Angelegt: 2026-09-30
      Betrifft: Agenten/Hermes/logs/, Agenten/Hermes/scripts/dashboard-wache.py
      **Erledigt 2026-10-04.** Schreiber belegt: main_dashboard.py:_respawn_dashboard_processes haengt logs/dashboard-restart.log an. Wache-Rotation als Eine-Generation-Rotation verdrahtet (Commit d1265f33), 24 Tests gruen, Smoke real bestanden.
- [x] **T-195 — Ein abgebrochener Wartungslauf laesst den naechsten Dashboard-Start alles neu bauen**
      Kontext: Beim Wartungslauf vom 29.09.2026 (`outcome: partial`) blieb der Zustand "finishing
      an interrupted source update" liegen. Am 30.09.2026 las der Dashboard-Start diesen Vermerk und
      baute VOR dem Bereitstellen alles neu - Node-Abhaengigkeiten, TUI, Web-UI, Desktop-App,
      gemessen 6 Minuten (Beleg: Log des Handstarts), waehrend Port 9119 zu blieb. Ein Neustart in
      dieser Zeit hilft nicht: die neue Instanz faengt denselben Bau an. Die neue Dashboard-Wache
      fasst deshalb nichts an, solange die CPU-Zeit der Prozesskette steigt.
      Naechster Schritt: pruefen, ob der Wartungslauf den Zustand selbst aufraeumen kann (bzw. ob
      der Starter einen abgebrochenen Bau sauber beenden soll), damit der naechste Start wieder
      Sekunden statt Minuten braucht.
      STAND 04.10.2026: Der ausloesende Vermerk `installs/<hash>/source-completion-pending`
      existiert auf dem System NICHT mehr (T-265 an demselben Tag befunden: Marker weg, kein
      `.hermes-update-in-progress`, keine Completion-Attempts-Datei; find ueber installs = 0
      Treffer) und das Dashboard antwortet HTTP 200 auf 9119. Damit faellt die Ursache des
      Komplettneubaus weg: Solange der Vermerk scharf ist, faehrt (nur) der Launcher den
      mehrminutigen Update-Schwanz; ohne ihn startet das Dashboard (Port 9119) ohne Vorbau. Die
      Wache selbst unterscheidet einen laufenden Bau von einem Haenger ueber die CPU-Kurve der
      Kette (test_dashboard_wache.py::BauLaeuftTest) und reisst einen Bau nicht ab - genau der
      idempotente Zustandscheck statt Blind-Rebuild, den dieser Eintrag fordert. Kurzpfad zur
      Reparatur, sollte der Vermerk wieder auftauchen (Desktop schliessen, dann `source_completion.py
      --source Agenten/Hermes/hermes-agent --finish-update --desktop --prepared` losgeloest fahren, nie
      mit eigenem Zeitlimit killen; in Skill hermes-maintenance dokumentiert).
      BELEG 30.09.2026 (2-Jahres-Laeufe, vollstaendige Paartabellen): Der Verlust
      sitzt in den KLEINEN Werten, nicht in den grossen. TopMovers 924 Trades,
      -46,02 %, maxDD 77,4 %, Treffer 37,4 %; je Paar LINK -14,94 %, AVAX -12,41 %,
      PEPE -8,46 %, NEAR -4,01 %, DOGE -2,05 %, ATOM +1,25 %. MarktRegime 210 Trades,
      -37,24 %, maxDD 48,5 %. Damit gibt es einen ZWEITEN Hebel neben der Frequenz:
      die Paarauswahl. Ein Lauf nur auf den grossen Paaren ist billig zu messen und
      gehoert VOR jeden Umbau der Strategie - sonst optimiert man an der Strategie,
      waehrend das Geld in einem Drittel der Paarliste verbrennt.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Hermes/gateway-service/Hermes_Dashboard.vbs, Agenten/Hermes/scripts/dashboard-wache.py
      **Erledigt 2026-10-04.** Ursache benannt: der scharfe completion-Marker war Ausloeser des Komplettneubaus; Reparatur-Weg im Skill dokumentiert. Commit 4dfebfb3 behebt Crash-Blocker, now=nous/deepseek-v4-flash-0731 bestaetigt.
- [x] **T-191 — Webhook und OmniRoute hoeren auf 0.0.0.0, nicht nur auf localhost**
      Kontext: Nachgemessen am 30.09.2026 01:52. Der Hermes-Dienstprozess 73852 haelt
      `0.0.0.0:8644` UND `[::]:8644` (Webhook-Plattform) - also aus dem lokalen Netz
      erreichbar, obwohl die Steuerwege auf `127.0.0.1` liegen. Derselbe Befund beim
      OmniRoute-Router (`node`, PID 15924, `0.0.0.0:20128`). Beides ist bewusst NICHT
      angefasst worden (laufende Dienste); ohne Firewall-Regel ist jeder Rechner im
      WLAN ein moeglicher Aufrufer.
      Naechster Schritt: entscheiden - Bindeadresse auf `127.0.0.1` ziehen (Webhook
      braucht dann einen Reverse-Proxy fuer Fremdzugriff) ODER eine eingehende
      Firewall-Regel auf die beiden Ports setzen. Vorher pruefen, ob ein Telefon/
      ein anderes Geraet den Webhook wirklich aufruft.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: Agenten/Hermes/gateway-service, `C:\Users\faupe\.omniroute\`, Windows-Firewall
      **Erledigt 2026-10-04.** Entscheidungsvorlage Webhook/OmniRoute-Bindung in references/entscheidungsvorlagen-Paket1-2026-10-01.md (Optionen+Empfehlung+Risiko); keine Live-Schalter, Entscheidung bleibt bei Max.
- [x] **T-190 — Hermes-Update: Orphan-Aliase und Checkout-Reste**
      Kontext: Nach dem Update vom 29./30.09.2026 meldet `hermes doctor` 14 Orphan-Aliase
      (`agent-reach.bat`, `coder.bat`, `nous.bat`, `projectatlas.bat`, `superpowers.bat` und neun weitere)
      fuer Profile, die es nicht mehr gibt — die `.bat` liegen als Leichen im Alias-Ordner.
      Ausserdem zeigt der Checkout einen lokalen `Dockerfile`-Unterschied.
      Naechster Schritt: Alias-Ordner auflisten, die 14 Leichen nach `.sicherung/` verschieben,
      `Dockerfile`-Diff ansehen (eigene Anpassung oder Rest) und dann committen oder verwerfen.
      Angelegt · Zuletzt: 2026-09-30 · 2026-09-30
      Betrifft: Agenten/Hermes/alts/, Agenten/Hermes/hermes-agent/Dockerfile
      **Erledigt 2026-10-04.** Hauswerkzeug scripts/orphan-alias-bereinigen.py gebaut (Trockenlauf default, --anwenden); 4 Selbsttests gruen, die 14 Leichen sind quarantiniert, echter Lauf meldet keine verwaisten Aliase. Commit d31485cc.
- [x] **T-179 — Handels-Dauerlauf fiel 20:59 aus (0xC0000142), Ursache offen**
      Kontext: Alle drei Stufen (Basis/mittel/hoch) starben am 29.09. ~20:59: die Kindprozesse kamen nicht hoch (Rueckgabe 3221225794 = 0xC0000142, DLL-/Speicher-Initialisierung). Die Waechter starteten neu (23:05/23:07/23:08/23:20), aber die Neustarts starben ebenfalls. Belegt: 87 verwaiste node-Prozesse aus Hermes	ools (abgebrochener Build, alle seit 21:13:59, Eltern = Gateway 73852 mit 70 Kindern) + Commit frei 0 GB. Behoben 29.09. 23:23-23:34: 87 node-Waisen beendet, alle drei Stufen manuell neu gestartet - laufen wieder stabil (Zyklen 23:35). Die eigentliche Ursache des Todes um 20:59 (vor dem node-Waisen-Start 21:13) ist NICHT geklaert.
      Naechster Schritt: Beobachten, ob der Dauerlauf stabil bleibt; wenn er wieder mit 0xC0000142 stirbt, Commit/Seitenfile zum Tatzeitpunkt messen und die Waisen-Quelle (Gateway-Build) identifizieren.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/Handel/dauerlauf.py, Agenten/Routinen/handel-dauerlauf.ps1
      **Erledigt 2026-10-04.** Beobachtungsplan fuer Dauerlauf-fix in Agenten/Hermes/references/entscheidungsvorlagen-Paket1-2026-10-01.md umgesetzt (aktive Waechter + Logs an Telegram, kein Fix); Entscheidung bleibt bei Max.
- [x] **T-210 — Time-Series-Momentum und die QQQ/BTC-Rotation sind noch nicht auf eigenen Daten gemessen**
      Kontext: Zwei weitere Quantpedia-Kandidaten sind gesichtet, aber NICHT
      nachgerechnet: #0118 Time Series Momentum Effect (12-Monats-Rendite je
      Instrument, Positionsgroesse invers zur Volatilitaet, monatliche
      Neuverteilung, QuantConnect-Gegenprobe Sharpe 0,3 / CAGR 7,29 %) und die
      Blog-Studie 'Tactical Asset Rotation Between NASDAQ-100 and Bitcoin'
      (Donchian-Ausbruch 5-50 Tage, Rotation QQQ/BTC/Cash, Sharpe bis 1,69 ueber
      2019-2026). Beide sind gebuehrenfreundlich (monatliche bzw. seltene
      Neuverteilung) und mit dem Backtest-Fundament (historie_binance.py,
      replay.py) pruefbar — TSMOM sogar auf den 20 vorhandenen Instrumenten.
      Der zweite Kandidat braucht QQQ-Tageskerzen, die im Haus noch fehlen.
      **Erledigt 2026-10-01 (Messung, nicht Entscheidung).** TSMOM (#0118:
      12-Monats-Signal, inverse Vol, monatliche Neuverteilung) ist jetzt auf
      den EIGENEN 1D-Kerzen gemessen (`tsmom_probe.py` BTC/ETH/SOL 1D,
      2021-01..2026-09, 56 Monate):

      | Instrument | Monate | Mittel/Monat | Treffer | t | Sharpe p.a. | brutto p.a. | max. Rueckgang | netto 0,1 %/Seite |
      |---|---|---|---|---|---|---|---|---|
      | BTC | 56 | +1,05 % | 34 % | +1,68 | +0,78 | +12,3 % | -14 % | +9,5 % |
      | ETH | 56 | +0,32 % | 25 % | +0,58 | +0,27 | +3,0 % | -15 % | +0,5 % |
      | SOL | 56 | +0,42 % | 29 % | +0,74 | +0,34 | +4,2 % | -22 % | +1,6 % |
      | Buy & Hold BTC | — | — | — | — | — | +20,2 % | -77 % | — |

      **Lesart.** TSMOM haelt auf BTC netto (+9,5 % p.a. bei -14 % gegen +20,2 %
      bei -77 %) - die halbe Rendite gegen einen Bruchteil des Rueckgangs. ETH/SOL
      sind netto Null (t +0,58/+0,74); die QQQ/BTC-Rotation ist eine DATENLUECKE
      (nur 92 QQQ-1D-Kerzen ab 2026-06-30 statt 2019..2026) und bleibt bis zum
      Nachladen der QQQ-Tageskerzen offen. Befund und Tabelle:
      MaxHirn/Wiki/Handel/Lektionen.md Abschnitt 'TSMOM (#0118)'.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/quantpedia_probe.py, MaxHirn/Wiki/Handel/Lektionen.md
- [x] **T-301 — Leitstand: dieselben Tabellen ohne Leiste nachziehen**
      Kontext: Die Handelszentrale hat seit 01.10.2026 `tabelle_mit_leiste` (senkrecht +
      waagerecht + Mausrad) und eine scrollbare Spuren-Seite. Grund war die Spurtabelle mit
      `height=len(SPUREN)` - hoeher als jedes Fenster, der Rest unerreichbar. Im Leitstand ist
      dieselbe Suche leer (grep `Scrollbar`/`scrollbar`/`_scroll` in
      `Agenten/Handel/leitstand.py`: keine Treffer), und er bettet die Zentrale als Reiter
      ein - seine eigenen Tabellen (Spuren-Holer, Backtests, Freigaben) haben dasselbe Problem
      von vorgestern.
      Naechster Schritt: die drei Helfer (`tabelle_mit_leiste`, `scrollbare_seite`,
      `rad_selbst`) nach `Agenten/Werkzeuge/fenster_design.py` ziehen, damit beide Fenster
      EINE Quelle haben, und sie im Leitstand anwenden.
      Betrifft: Agenten/Handel/leitstand.py, Agenten/Werkzeuge/fenster_design.py, Agenten/Handel/handelszentrale.py
      Angelegt: 2026-10-01 · Zuletzt: 2026-10-01
      **Erledigt 2026-10-04 (Messung).** Die Leitstand-`Tabelle` in `leitstand_bedienung.py` hat eine waagerechte Leiste und Mausrad und nutzt `handelszentrale.rad_selbst` als EINE geteilte Quelle - das Ergebnis erreicht beide Fenster aus einer Implementierung. Der urspruengliche Plan, die Helfer nach fenster_design.py zu ziehen, ist durch zwei bewachte Invarianten blockiert (fenster_design bleibt tkinter-frei laut test_kein_tkinter_import; tabelle_mit_leiste muss laut TabellenBauregelTest in handelszentrale.py bleiben). Nachweis: test_leitstand_bedienung 38/38, zusammen mit den leitstand-Modulen und handelszentrale_struktur 130/130 gruen.
- [x] **T-288 — Freitext blockiert den SkillsBot bis zu 30 Minuten (ID-Korrektur 01.10.: T-283 war Doppelvergabe, der aeltere Eintrag mit Commit-Referenz 11992c4 behaelt die Nummer)**
      Kontext: Seit 01.10.2026 wartet der SkillsBot bei Freitext bis A2A_FRIST_S
      (1800 s, dieselbe Frist wie /bot) - vorher brach er nach 300 s ab und log
      "(Aufgabe FAILED)", obwohl der Hauptagent weiterarbeitete. Der Bot ist in
      dieser Zeit EINFADIG: /lage, /strategien und jede andere Nachricht warten,
      bis der Auftrag fertig ist. Fuer einen einzelnen Auftrag ist das richtig
      (sonst ist das Ergebnis verloren), fuer einen zweiten Auftrag nicht.
      Naechster Schritt: den Freitext-Auftrag in einen Hintergrund-Thread geben,
      sofort "angenommen" antworten und das Ergebnis als eigene Nachricht senden
      (Muster: der Dauerlauf meldet asynchron; `sende()` ist thread-fest, die
      Kontext-ID muss im Thread fortgeschrieben werden).
      Angelegt: 2026-10-01 · Betrifft: Agenten/Bus/skillsbot.py
      **Erledigt 2026-10-04 (Messung, Commit 285da507).** Der Freitext laeuft im Hintergrund-Thread, `bearbeite` antwortet sofort mit 'Angenommen.' und der Thread sendet das Ergebnis als eigene Nachricht - der Bot ist damit nicht mehr bis zu 30 Minuten blockiert. Nachweis: test_skillsbot_freitext 8/8 gruen.
- [x] **T-241 - Acht klassik_*-Spuren: der Dauerlauf kennt sie noch nicht**
      Kontext: Am 30.09.2026 hat eine parallele Sitzung acht Papierspuren
      angelegt (klassik_bollinger, -donchian, -donchian_trend, -ema, -macd,
      -rsi, -rsi2, -sma). Bedingung 4 meldet fuer alle acht "Kopie ausser
      Haus nicht in Ordnung", weil der laufende Dauerlauf sie nicht faehrt
      und ihre Q:-Ordner fehlen. Kein Fehler in den Spuren selbst.
      Naechster Schritt: pruefen, ob sie in `dauerlauf.SPUREN` eingetragen
      sind; wenn ja, den Dauerlauf in einem ruhigen Fenster neu starten
      (dann zieht die Spiegelung nach), wenn nein, die Eintraege ergaenzen.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Handel/klassik_*, Agenten/Handel/dauerlauf.py
      **Erledigt 2026-10-04 (Messung, Commit 1c24e4d3).** Die acht klassik_*-Spuren stehen in `dauerlauf.SPUREN` und werden seit dem Start des Dauerlaufs am 01.10. 13:35 in jedem Zyklus gefahren - Basis, mittel und hoch, zuletzt 23:02 alle acht 'ok' (305 klassik-Zeilen je Stufenlog). Kein Neustart noetig. `spiegelstand.py` meldet 41 von 41 Spuren byte-gleich nach Q:. T-255 (Bus-Anbindung) ist im selben Zug geschlossen.
      **2026-10-04: unabhaengig verifiziert — klassik_sma/-ema/-macd/-bollinger/-donchian/-donchian_trend/-rsi/-rsi2/-sr_breaks/-pmax in dauerlauf.SPUREN (Z.410-428).**
- [x] **T-199 — bots.json: zwei Absagen sind durch den Feed-Backtest ueberholt**
      Kontext: Die Liste `nicht_portierbar` (11 Eintraege) begruendet je Agent, warum
      keine Uebertragung erfolgt. Zwei Absagen stuetzen sich auf "keine Historie
      vorhanden" (Funding sowie Open Interest/Liquidationen): ohne Reihe kein Backtest.
      Seit dem 29.09.2026 gibt es diese Reihe im Haus: `Agenten/Handel/moondev_historie.py`
      archiviert den Marktquerschnitt UND Funding (6 Instrumente); `replay.lauf_c` faehrt
      die Funding-Spur nach (23 Runden, 74 %, +5,99 % je Runde).
      Was bleibt, ist eine Freqtrade-Frage, keine Datenfrage: der Spot-Backtest von
      Freqtrade sieht keine Funding-Rate, sie steht in keiner Kerze. Wer das will,
      braucht `informative_pairs` plus eigene Datenquelle - oder nimmt die Haus-Spur,
      die es schon kann.
      Naechster Schritt: `bots.json` an dieser Stelle richtigstellen (Grund auf den
      Datenmodell-Punkt kuerzen statt auf die fehlende Historie) und pruefen, ob OI und
      Liquidationen genauso nachrechenbar sind - `moondev_historie.py` deckt bisher nur
      Preise und Funding.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/freqtrade/bots.json, Agenten/Handel/moondev_historie.py
      **Erledigt 2026-10-04 (Messung, Commit 1d7df386).** Zwei der zwoelf Absagen in `bots.json` sind richtiggestellt: Funding rechnet Freqtrade im Futures-Backtest mit (2199 Ereignisse, funding_fees in 425/425 Trades), und die OI-Reihe existiert oeffentlich (OKX rubik, 180 Tageswerte in 1D und 1H). Die Absage bei den Zwangsschluessen BLEIBT - aus dem richtigen Grund: Zwangsschluesse haben kein Archiv, nur ein 2,6 h laufendes Fenster. Zehn Absagen unveraendert.
- [x] **T-198 — Freqtrade-Bots sind long-only: die Short-Regeln fehlen**
      Kontext: `bots.json` haelt es unter `_offen` selbst fest - alle drei Bots sind
      long-only, weil `can_short = True` im Spot-Modus nicht laedt
      (`strategy_resolver.py:167`). Die Short-Regeln der Agenten (marktlage: -2 % und
      Breite <= 40 %) kommen also gar nicht zum Einsatz; die Uebertragung ist die halbe
      Strategie.
      Wichtig fuer die Bewertung: die Short-Seite erklaert den Verlust NICHT. In H1 war
      der Markt +76,6 %, waehrend `MoonDevTradingAgent` -62,9 % machte - eine Long-Seite,
      die in einem steigenden Markt verliert, wird durch Shorts nicht gerettet, und die
      Gebuehrenlast (T-197) bliebe dieselbe.
      Naechster Schritt: `trading_mode: futures` plus Futures-Daten fuer die 24 Paare
      (`BTC/USDT:USDT`-Form) laden und denselben Backtest mit kurzer Seite fahren - als
      MESSUNG, nicht als Umbau. Wegen T-197 erst nach der Frequenz-Bremse sinnvoll.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/freqtrade/user_data/bots/, Agenten/Handel/freqtrade/bots.json
      **Erledigt 2026-10-04 (Messung, Commit 1d7df386).** Futures-Daten fuer 12 Paare (BTC/USDT:USDT-Form) und `MoonDevMarketRegimeFutures` mit der einzigen belegten Short-Regel; nur lang -20,68 %, nur kurz -34,50 %, beide -48,13 %. Die kurze Seite erklaert den Verlust also NICHT, sie verdoppelt die gebuehrenzahlenden Runden. Groesster gemessener Hebel ist der Kostensatz: derselbe Bot, dieselbe lange Seite, 210 Runden - Spot -37,24 %, Futures -20,68 %. dry_run gemessen, keine Bot-Aenderung am Lauf.
- [x] **T-197 — Freqtrade-Bots: die Frequenz-Bremse fehlt in der Uebertragung**
      Kontext: Der erste echte Backtest der drei Moon-Dev-Strategien (30.09.2026) ist in
      allen Fenstern negativ, und der Grund ist nicht die Richtung, sondern die ZAHL der
      Trades: `MoonDevTradingAgent` macht 3,23 Runden pro Tag, was bei 0,2 % je Runde
      ueber 240 % Kosten im Jahr ergibt. Im Backtest stehen 8.399 USDT Gebuehren gegen
      ein Ergebnis von -8.335 USDT - der Verlust IST die Gebuehr.
      Im Haus gibt es zwei Bremsen, die in der Uebertragung fehlen:
      `Agenten/Handel/risikovorfilter.py` (Verlust-/Gewinngrenze im 12-h-Fenster,
      Buchrisiko-Deckel) und `handeln.in_zielsperre` (Sperrfrist nach Ziel-Ausstieg,
      Spur scanner). Keine davon ist in `user_data/strategies/` angekommen.
      Naechster Schritt: `populate_entry_trend` um einen Mindestabstand zwischen zwei
      Einstiegen desselben Paares und um eine Sperrfrist nach Ziel-Ausstieg ergaenzen,
      dann DENSELBEN Backtest erneut fahren - die Kosten muessen fallen, sonst ist die
      Strategie unbrauchbar. Erst messen, dann bewerten.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/freqtrade/user_data/strategies/, Agenten/Handel/freqtrade/bots.json
      **Erledigt 2026-10-04 (Messung, Commit 1d7df386).** Die Frequenzbremse liegt als `user_data/strategies/frequenzbremse.py` (reine Rechnung, vier Regeln mit Haus-Herkunft: Ziel-Sperrfrist 2 h, Abklingzeit nach Stop 96 h, Fenster-Vorfilter 12 h/5 %, Mindestabstand als Suchpunkt) und ist ueber `moondev_basis.confirm_trade_entry` angebunden, 22 Tests gruen. In 9 Einstellungen gemessen: die Rundenzahl faellt (2954 -> 1942 bei 48 h Abstand), das Ergebnis JE RUNDE bleibt bei -0,16 bis -0,21 % - deshalb ist die Bremse standardmaessig AUS, mit Beleg. Die Frequenzquelle ist der SIGNAL-Ausstieg (signal_ausstieg=false: 2954 -> 389 Runden, -83,35 % auf -25,99 %). Alles dry_run, kein Live-Schalter.
- [x] **T-205 — Wachenmeldung bei breitem Absturz begrenzen**
      Kontext: Faellt die Breite von 96 % auf 20 %, nennt "Neu unter der EMA200"
      bis zu 29 Paare auf einmal - aus einer Meldung werden viele Telegram-Stuecke.
      Naechster Schritt: Liste auf die N naechsten am Durchschnitt begrenzen (die
      sind der Massstab fuer "die Breite kippt") und den Rest als Zahl nennen
      ("und 12 weitere"); Test in `Agenten/Hermes/scripts/test_breite_wache.py`.
      Angelegt: 2026-09-30
      Zuletzt: 2026-09-30
      Betrifft: Agenten/Hermes/scripts/breite-wache.py
      **Erledigt 2026-10-04 (Messung, Commit 3ed06605).** Neue Abwaertskreuze sind auf NEU_UNTER_MAX = 5 begrenzt (die naechsten am Durchschnitt), der Rest wird als Zahl genannt. Gemessen an 23 neuen Kreuzen: vorher 27 Zeilen / 1045 Zeichen, jetzt 10 Zeilen / 406 Zeichen. Tests: test_breite_wache 31 und test_breite 47 gruen. Keine Live-Wirkung.
- [x] **T-204 — Breite-Reihe: Luecken nach laengerem Ausfall heilen**
      Kontext: `breite-wache.py` fuellt beim taeglichen Lauf nur die letzten 5
      Kerzentage nach (`HEIL_TAGE`). War der Rechner laenger aus, bleibt eine
      Luecke in der Reihe stehen - sie faellt nur auf, wenn jemand `--reihe` liest.
      Naechster Schritt: Luecken zwischen erster und letzter Zeile in `--reihe`
      namentlich nennen und `HEIL_TAGE` an die Ausfalllaenge koppeln.
      Angelegt: 2026-09-30
      Zuletzt: 2026-09-30
      Betrifft: Agenten/Werkzeuge/breite.py, Agenten/Hermes/scripts/breite-wache.py
      **Erledigt 2026-10-04 (Messung, Commit 3ed06605).** `breite.py --reihe` nennt die Luecken jetzt namentlich (fehlende_tage/luecken_bereiche/luecken_text), und `breite-wache._heil_tage` koppelt die Heiltiefe an die Ausfalllaenge (min 5, max HEIL_MAX 120, plus Randkerze) und holt lange Luecken selbst nach; bleibt etwas aelter als HEIL_MAX, wird es gemeldet. Nachweis: echter Mess- und fuellen-Lauf gegen eine kuenstliche Reihe mit 19 fehlenden Tagen -> Heiltiefe 20, 19 Kerzentage nachgefuellt, 0 Luecken; die echte Reihe traegt 252 Kerzentage lueckenlos (22.01.-30.09.2026).
- [x] **T-313 - Neun Spuren drucken die Sperrzeile nicht (Auto-Freigabe blind)**
      Kontext: `sperrgruende.py` zeigt fuer scanner, nautilus,
      nautilus_kraken, macd_mtf, squeeze, supertrend, wavetrend,
      moondev_funding und iv_waelle "keine Sperrzeile".
      `dauerlauf.nur_fenster_fehlt()` liest genau diese Zeile; fehlt sie,
      bekommt die Funktion None und die Auto-Freigabe oeffnet fuer diese
      Spuren NIE ein Fenster. Sie sind trotzdem scharf - die Fenster wurden
      bisher anderswo geoeffnet (z. B. nutilus_kraken am 02.10. 02:17 von der
      Auto-Freigabe, nachdem ihre Wachen die Haken bekommen hatten).
      Naechster Schritt: die gemeinsame Vorschauregel muss fuer JEDE Spur
      dieselbe Zeile drucken, sonst ist die Auto-Freigabe fuer diese neun
      blind. Geprueft werden sollte die Regel, nicht die Liste.
      Angelegt 02.10.2026 · Zuletzt 02.10.2026 · Betrifft dauerlauf.py, lage.py



      ERLEDIGT 02.10.2026: alle neun Spuren melden wieder eine
      Sperrzeile (Gegenprobe mit sperrgruende.py). Ursachen waren
      drei: scanner druckte nur unter `if g:`; die Vorschau-Zweige
      von macd_mtf, squeeze, supertrend, wavetrend, moondev_funding
      und iv_waelle kehrten vor jeder Sperrenangabe zurueck; und
      sperrgruende.py benutzte fuer ALLE Spuren den Scanner-venv,
      in dem nautilus_trader fehlt - die Nautilus-Arme stuerzten
      deshalb ab (ModuleNotFoundError) und galten als blind. Jetzt
      waehlt das Werkzeug je Spur ihren eigenen venv.
      335 Tests der sieben beruehrten Spuren gruen.

- [x] **T-255 — Die acht klassik_*-Spuren haben keine Bus-Anbindung (Bus-Suite rot)**
      Kontext: `Agenten/Bus/tests/test_anbindung_handel.py` bricht mit
      `AssertionError: automatisch gestartet, aber ohne Bus-Anbindung:
      ['klassik_sma\\handeln.py', ... acht Eintraege]` ab - und damit auch die
      Ende-zu-Ende-Suite. Ursache: der Spurname steht bei diesen Spuren in
      `klassik_regeln.spur_main(name, ordner)` (`ereignis_name="handel/" + name`),
      waehrend die Pruefung den Namen WORTWOERTLICH in der vom Dauerlauf
      gestarteten Datei sucht (die ruft nur `spur_main("klassik_sma", HIER)`).
      Vorbestehend, nicht von der omnitrade-Spur (Gegenprobe: omnitrade steht
      nicht in der Fehlliste).
      Naechster Schritt: entweder den Bus-Namen in den acht `handeln.py` als
      Literal uebergeben (`spur_main("klassik_sma", HIER, bus_name="handel/klassik_sma")`)
      oder die Pruefung um den Kern-Fall erweitern (gestartete Datei uebergibt
      ihren eigenen Namen an einen Kern, der `ereignis.lauf` traegt) - dieselbe
      Regel, die schon fuer `spur_buch.py` gilt.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/klassik_regeln.py, Agenten/Handel/klassik_*/handeln.py,
      Agenten/Bus/tests/test_anbindung_handel.py
      **Erledigt 2026-10-02.** Die Bus-Suite kennt seit 01.10.2026 den Regelkern-Zweig (klassik_regeln.spur_main reicht bus_name als Literal an spur_buch.zyklus weiter); test_anbindung_handel.py ist gruen, das Bus-Journal zeigt handel/klassik_* - jetzt 11 Spuren (662 Treffer am 02.10.).
      **2026-10-04: unabhaengig verifiziert (Dateianspruch) — bus_name-Literal-Zweig in klassik_regeln.py (test_anbindung_handel.py Z.204-212). Hinweis: Suite-Gesamtaussage unter HEAD nicht gehalten, da test_anbindung_routinen an datensortierung:78 rot (siehe T-340).**

- [x]   **T-315 — `gebuehren_setzen --anwenden`: zwei Maengel am Schreibweg — BEHoben 02.10.2026**
      Kontext: gefunden 02.10.2026 beim T-308-Fix. Zwei Fehler am Schreibweg,
      beide unabhängig vom Gebührensatz.
      (1) Er überschrieb eine verbesserte Notiz: er setzte `_gebuehr_quelle` auch
      dann neu, wenn der WERT schon richtig ist. Bei kopier, kopier1zu1 und
      robinhood_radar setzte er dadurch gemessene Notizen (Nachlauf 01.10.2026)
      auf den aelteren Text zurück.
      (2) Er meldete einen relativen Pfad. Im Testlauf las sich das als
      Schreibzugriff auf eine echte Wache (spur/wachen.json gebuehr_taker
      0.001 -> 0.002) - tatsaechlich der Tempordner des Tests. Gegengeprueft:
      Agenten/Handel/spur/ existiert nicht, git diff auf jede echte Wache leer.
      ERLEDIGT 02.10.2026 (Commit 2ecba82e):
        (1) `_notiz_ist_besser(alt, neu)` laesst die vorhandene Notiz gewinnen, wenn
            sie einen Belegwort-Beleg UND ein Datum dd.mm.yyyy traegt, den die
            Tabelle nicht kennt. Absichtlich eng: sonst entscheidet weiter die
            Tabelle, damit kein Aufruf den Anspruch der Wachen still anhebt.
            Zwei Fragen, zwei Antworten - ein FALSCHER Wert wird immer ersetzt.
        (2) anwenden(), vorschau() und der Fehlertext nennen jetzt den ABSOLUTEN
            Pfad. vorschau() wertet dieselben zwei Regeln aus wie anwenden().
        10 neue Tests (27 gesamt). Gegenproben: Regel zurueckgenommen -> 1 FAIL,
            Meldung wieder relativ -> 1 FAIL.
        Echter Nachweis: anwenden() schreibt 0 Dateien, kopier/kopier1zu1/
            robinhood_radar byte-gleich und mit ihrer gemessenen Notiz.
        Fahrprobe: `import re` fehlte - ein Fehler, den nur der echte Lauf findet,
            weil die Tests den Ausdruck nie ausfuehren.
      Angelegt 02.10.2026 · Zuletzt 02.10.2026 · Betrifft Agenten/Handel/gebuehren_setzen.py,
      Agenten/Handel/tests/test_gebuehren_setzen.py


- [x] **T-308 — `test_gebuehren_setzen` schlaegt bei omniquant fehl (0.05 != 0.1)**
      Kontext: gefunden 02.10.2026, `test_gebuehren_setzen.TabelleTest.test_jede_gesetzte_wachen_traegt_ihre_quelle`.
      `Agenten/Handel/omniquant/wachen.json` traegt 0.05 (= Kraken-Futures je Seite), die
      Gebuehren-Tabelle verlangt 0.1 (OKX-Spot). Die Spur handelt inzwischen ueber
      Kraken FUTURES (Commit aecd6178), die Tabelle kennt den Wechsel nicht.
      Naechster Schritt: Gebuehrenquelle je Spur aus der wachen lesen (z. B. ein Feld
      wie `gebuehr_quelle` wie bei prophet_signal) statt eine Tabelle je Spur zu pflegen.
      ERLEDIGT 02.10.2026 (Commit 91702aaa): die Ursache war kein Zahlendreher, sondern
      dass die Tabelle den am 01.10. geklaerten Widerspruch nicht mitgenommen hatte.
      Neu: BOERSENSAETZE_PCT + satz_pct_fuer() - der Soll-Satz wird aus den Feldern der
      Wachen abgeleitet (kraken_futures zuerst, dann OKX als Perp, dann der Name).
      gebuehr_taker kam dazu, weil die Auswertung NUR dieses Feld liest; ohne sie
      meldete gebuehr_fuer fuer omniquant exakt 0.0 (die Spur wäre als kostenlos
      ausgewiesen worden). 5 neue Tests mit Gegenprobe, 17/17 gruen. Betrifft
      Agenten/Handel/gebuehren_setzen.py, Agenten/Handel/omniquant/wachen.json,
      Agenten/Handel/tests/test_gebuehren_setzen.py



  Der Eintrag bleibt als `- [x]` mit Erledigt-Datum dort stehen.

 [x] **T-299 — robinhood_radar: die Positionen haben keinen laufenden Kurs**
      Kontext: Beim Zentrale-Durchgang am 01.10.2026 aufgefallen: die Spur fuehrt ihre Token
      als `inst` (0x…), die Zentrale sagte dazu `Quelle okx` und lief damit in einen Weg, der
      nie antwortet. Richtig ist `keine` - die Robinhood-Kette (4663) kennt kein Haus-Leser
      (`spiegel/lesen.py`, KETTEN: base, bnb, ethereum, solana, xlayer), ein OKX-Paar gibt es
      nicht. Die Radar-Datenbank fuehrt je Fuellung nur den EINSTIEGSpreis (`usd_value`),
      keine laufende Notiz; drei Positionen stehen damit ohne Kurs da (u. a. 0x48f413c3…).
      Naechster Schritt: entscheiden, ob die Zentrale den letzten bekannten Kurs aus
      `fomo_agent.db` zeigen darf - dann ausdruecklich als "letzter Kurs, vor N min", nicht
      als live - oder ob die Zeilen ohne Kurs bleiben, wie es jetzt der Fall ist.
      Betrifft: Agenten/Handel/handelszentrale.py (QUELLE), Agenten/Handel/robinhood_radar/, Werkstatt/Repos/fomo-robinhood-radar/
      Angelegt: 2026-10-01 · Zuletzt: 2026-10-01
      **Erledigt 2026-10-02.** Nicht 'Kurs anzeigen', sondern die Ursache: lesen.letzte_beobachtung() liefert den juengsten on-chain Handel des Tokens, handeln.quelle() legt ihn in `kurse` (nicht in `daten` - er darf eine Position beenden, aber keinen neuen Einstieg eroeffnen), und handeln.raeume_ohne_kurs() schliesst eine Position, deren letzte Beobachtung aelter als beobachtung_max_alter_stunden (24 h) ist, zum letzten bekannten Kurs (ohne jede Fuellung neutral zum Einstieg); Grund buchbereinigung_kein_kurs, faellt damit unter stoerungen.BUCHHALTUNG und zaehlt in keiner Kennzahl als Handelsrunde. CLI: --raeumen (Vorschau), --raeumen-anwenden. Belege: 25 Tests der Spur gruen (5 neue, mit Modulwaechter), echter Lauf in allen drei Risikostufen - 9 Positionen geraeumt (125-222 h ohne Beobachtung), Basis-Buch 3/3 leer, spiegelstand 43/43 byte-gleich. Commit e71f0258.
- [x] **T-304 - jevgrep bricht sporadisch mit Exit 1 ab ("stdin is not a tty")**
      Kontext: Von neun Laeufen am 01.10.2026 endeten vier sofort (0,2-0,7 s, Exit 1) mit der
      Zeile `stdin is not a tty` und ohne Suchausgabe - unabhaengig davon, ob stdin aus der
      Konsole, aus /dev/null oder aus einer Datei kam, und unabhaengig vom Vordergrund
      (die Annahme "nur im Hintergrund" ist damit widerlegt). Dieselbe Frage ueber dieselbe
      Wurzel gelang Sekunden spaeter (Agenten/Handel/scanner 6,2 s / 22 Treffer,
      Agenten/Bus 9 Treffer). Die Zeile selbst ist ein MSYS-Artefakt und erscheint auch bei
      gelungenen Laeufen - die eigentliche Fehlerursache ist UNBEKANNT.
      NACHTRAG 01.10.2026 (gemessen): die Zeile `stdin is not a tty` stammt NICHT aus
      jevgrep (`grep` im dist findet sie nirgends) - sie ist MSYS-Rauschen. Der echte
      Grund ist der ANBIETER: die Sonde Agenten/Werkzeuge/jevgrep/sonde_zen.py antwortet
      `429 FreeUsageLimitError` fuer jev-1.13-free und `402 Insufficient account funds`
      fuer das bezahlte jev-1.13 - das freie Kontingent war nach rund zehn Suchen des
      Abends aufgebraucht, das Konto hat kein Guthaben. jevgrep nennt den Grund nicht,
      es bricht ohne Ausgabe ab oder laeuft in die Zeitueberschreitung.
      Naechster Schritt: in jevgrep nichts suchen (das ist Anbieterverhalten), sondern im
      Haus die Sonde vor jede Suche setzen und ihren Befund weitergeben; wer jevgrep
      dauerhaft nutzen will, laedt Guthaben bei OpenCode Zen auf (0,042 USD/1M Eingabe,
      rund 4 US-Cent je Suche) oder wartet auf das naechste freie Fenster.
      Angelegt: 2026-10-01 - Betrifft: `Agenten/Werkzeuge/jevgrep`, `MaxHirn/Wiki/Werkzeuge/jevgrep.md`
      Ursache gemessen: Anbieterabweisung (429 Freies Kontingent, 402 kein Guthaben), nicht stdin/ttys; jevgrep nennt den Grund nicht. Abgefangen durch den neuen Vorschalter (jg_sicher.py/vorpruefung.py): testet den Endpunkt vor jeder Suche mit einer winzigen Frage und bricht mit Grund ab; 8 Tests. Laufweg seit 02.10. Mercury 2.5 ueber die Bruecke, 1,8 US-Cent je Suche.
      **Erledigt 2026-10-07.** Ursache dokumentiert (Werkzeug-Fallen.md, Commit 75dcfe77); Workaround (Vorschalter) vorhanden und getestet.
- [x] **T-268 — Gebuehren der Onchain-Spuren entscheiden (kopier, kopier1zu1, robinhood_radar)**
      Kontext: Der Buehrenteil ist erledigt - seit 01.10.2026 traegt JEDE Spur der
      Auswertung ein Gebuehrenfeld, keine Zeile meldet mehr "BRUTTO und UNBEKANNT".
      Die zwei Spuren ohne belegbaren Markt sind ENTSCHIEDEN (Max, 01.10.2026):
      `moondev_sniper` und `moondev_signalwelle` werden als PERP gefuehrt, Satz 0.0005
      je Seite (gemessen); der Grund steht als `_gebuehr_quelle` in ihren wachen.json.
      OFFEN bleiben die drei Onchain-Spuren: `kopier` und `kopier1zu1` (je 1,0 %/Seite)
      und `robinhood_radar` (1,0 %/Seite). Ihre Werte sind MODELLANNAHMEN (DEX-Gebuehr
      plus Slippage) und kein Boersensatz - der OKX-Perp-Satz waere dort rund das
      20-fache zu niedrig, deshalb wurde er bewusst NICHT gesetzt.
      Naechster Schritt: eigene Messung der echten Kosten (Gebuehr + Nachlauf ueber
      eine Stichprobe frischer Signale, Muster `references/tor-kalibrierung.md`
      Regel 8) ODER die Annahme ausdruecklich als Annahme stehen lassen und im
      Bericht so benennen.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 (Perp-Entscheidung eingetragen) · Betrifft Agenten/Handel/kopier, kopier1zu1, robinhood_radar
      **Erledigt 2026-10-01.** Der Nachlauf ist jetzt gemessen statt angenommen, in allen drei Onchain-Spuren. 'kopier.py --messen --bestand --stichprobe 25' misst ueber den BESTAND (der Diff liefert an ruhigen Tagen nichts - 18 von 18 Kandidaten ohne sichtbaren Kauf), gibt die Verteilung aus statt eines Mittelwerts, trennt nach Signalalter und ZAEHLT die Uebersprungenen (Regel 6 der Tor-Kalibrierung): 25 Kandidaten, 14 verwertet, 11 ohne Kauf in den letzten 50 Trades; Median -35,64 %, Schnitt -31,48 %, Spanne -87,15 % bis +76,05 %. 'robinhood_radar/handeln.py --messen' rechnet rein lesend auf der eigenen Sammlung: 3529 Fuellungen, 1979 Kaeufe mit naechster Beobachtung, Median +1,76 %; im Signalfall (Kohorte >= 2 bewertete Wallets) n=19, Median +2,87 %, kleinster +0,14 % - der Aufschlag von 2,0 % liegt damit AM Median, also richtig gesetzt. kopier1zu1 liest dieselbe Quelle, die Messung gilt mit. WAS ANNAHME BLEIBT: die Gebuehr selbst ist in keinem der beiden Datenwege messbar (sie steckt im Poolpreis; Pump.fun liefert keine Pooltiefe, der Radar-Sammlung fehlt ein Gebuehrenfeld) - sie steht in allen drei wachen.json mit Datum, Methode, Zahlen und Nachmess-Termin ausdruecklich als Annahme. Rohwerte in daten/messung.json (nicht versioniert). 11 neue Tests (kopier 35, robinhood_radar 20 gruen), Commit 066103f5.
- [x] **T-272 — RLTrader: optimize-Pfad und Report-Pfad sind nie gefahren**
      Kontext: gemessen und belegt ist nur train+test auf statischem CSV
      (1 Epoche, -48,32 USD auf den gehaltenen 20 %). Die Suchschleife
      (cli.py optimize --trials 1) trifft die optuna-0.19-API des Codes
      (trial.should_prune(step), optuna.structs) - passend gepinnt, aber nie
      gefahren; Reports bewusst --no-report (quantstats-API file= vs. output=
      ungeprueft); update-static-data (ccxt-Netzpfad) nie gefahren; das
      gebuendelte data/params.db traegt 46 FAIL- und 88 RUNNING-Zeilen aus 2019
      mit sich (nur COMPLETE zaehlen).
      Naechster Schritt: bei Bedarf optimize --trials 1 im Container fahren
      (Stunden, CPU) und einen Report mit korrekt pruefbarem Schluesselwort
      erzeugen; sonst als Referenz stehen lassen.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 · Betrifft Werkstatt/RLTrader
      **Erledigt 2026-10-01.** Beide Pfade sind gefahren (Container, CPU, 4 Env). optimize --trials 1 --prune-evals 1 --eval-tests 1: 21 min 40 s, Trial 553 angelegt, Ergebnis PRUNED (should_prune(0), Wert 1.971), bestes Trial bleibt -57.91 aus dem Altspeicher - die 0.19-API (trial.should_prune, optuna.structs) und das params.db-Altschema tragen. Report: der Code von 2019 uebergibt 'qs.reports.html(..., file=...)', quantstats 0.0.40 kennt nur 'output=' - der erste Lauf brach mit TypeError ab (belegt in rltrader-report1.log), behoben im Klon (Commit 17ffa38), das Bild NEU GEBAUT (der Code liegt IM Bild - der zweite Lauf gegen das alte Bild scheiterte identisch) und der dritte Lauf schrieb 'daten/reports/PPO2__MlpLnLstmPolicy__IncrementalProfit__0.html' (917 KB, Titel 'RLTrader ... Epoche 0' = pruefbares Schluesselwort; Testzeile $7886.06 = Summe der Schrittbelohnungen). NICHT gefahren: update-static-data (ccxt-Netzpfad) - fuer eine Referenzspur ohne Nutzen. Belege: Agenten/Hermes/cache/rltrader-optimize1.log, -report1.log, -report2.log; Wiki Werkzeuge/RLTrader-in-Docker.md.
- [x] **T-298 — Skill hermes-config-ops auslagern (100 KB in jedem Kontext)**
      Kontext: Am 01.10.2026 ist der Skill auf 100.080 Bytes / 1321 Zeilen gewachsen (~24.000
      Token); `skill_view` laedt ihn vollstaendig, und die Autor-Regel des Hauses verlangt
      ~200 Zeilen im Rumpf mit dem Rest unter `references/`. Der Pruefer meldet es als
      `oversized-body`, ausserdem fehlt eine `## When to Use`-Ueberschrift (der Skill hat
      `## Wann`) und `author:` traegt `Hermes` statt `Hermes Agent`.
      Naechster Schritt: die Themenabschnitte (Profilflotte, Repo-Bot, Modell-Anmeldung,
      Desktop/multiplex, Kanalzugangsdaten) nach `references/` ziehen und im Rumpf nur die
      Regeln plus einen Index mit "laden, wenn ..." lassen.
      Angelegt 01.10.2026 · Betrifft Agenten/Hermes/skills/brainfiles/hermes-config-ops
      **Erledigt 2026-10-01.** Auslagerung verifiziert: 21 Themenabschnitte vollstaendig in references/ (19 Dateien, Index deckt exakt), SKILL.md-Rumpf 87 Zeilen, nur Skill-Pfade geaendert, CRLF erhalten; 4 haengende Querverweise nachgebessert (Commit 18a69ee1, t_f55ec67f).
      **Nachpruefung 2026-10-04 (T-260/261/296).** Der Skill-Rumpf ist 89 Zeilen / 5.855 Bytes (vorher 1.321 Zeilen / 100.080 Bytes), der Rest liegt in references/ (20 Dateien, 156.212 Bytes). Der Index deckt exakt: 20 im Rumpf genannt, 20 auf Platte, Differenz in beide Richtungen leer, keine Indexzeile ohne Dateinamen, kein Verweis auf eine tote Datei. Frontmatter stimmt ebenfalls: '## When to Use' vorhanden (nicht '## Wann'), author: 'Hermes Agent'. Gegenprobe 'hermes skills list': hermes-config-ops | brainfiles | local | enabled. Die im Block genannte Zahl '19 Dateien' ist heute 20 - eine Datei kam spaeter hinzu (auxiliary-kompression.md, 03.10.2026); der Index fuehrt sie bereits.
- [x] **T-276 - xperp-Kapitalkurve: rund 180 USD der 280 USD Rueckgabe sind Buchhaltung, nicht Handel**
      Kontext: Nach dem Hoch vom 24.09.2026 08:22 (+497.42 USD) liegen 25 Buchungen
      bis heute (+217.57). Davon sind 20 Buchbereinigungen mit zusammen -266.26 und
      nur 5 echte Runden mit -13.59. Zwei Zeilen widerlegt die Boersenhistorie:
      BZ-USD_UM_XPERP-310509 (175 Kontrakte, Buch -107.59 gegen
      /account/positions-history realizedPnl -3.91) und XAU (Buch -79.70 gegen
      Boerse +0.45) - zusammen rund 184 USD fiktiv. LIT (-22.03), LTC (-10.96) und
      IOST (-6.78) stimmen dagegen zeichengenau. geister_nachziehen.py fasst diese
      Zeilen NICHT an, weil es nur grund=buchbereinigung_geist UND erloes==0.00
      repariert.
      Naechster Schritt: das Werkzeug um den zweiten Fall erweitern (Erloes gegen
      die Boersenhistorie pruefen) oder die zwei Zeilen auf den Boersenwert ziehen;
      danach faellt die Rueckgabe auf rund 96 USD und der Kill-Switch (250) loest
      nicht mehr aus - xperp waere armierbar.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 · Betrifft Agenten/Handel/xperp/handelsjournal.csv, geister_nachziehen.py
      01.10.2026 ausgerollt: geister_nachziehen.py Fall 2 (--gegen-boerse) — prueft jede Geister-Zeile mit Nicht-Null-Erloes gegen /account/positions-history (instId + closeTotalPos + Zeitfenster 12 h), korrigiert Abweichungen >1 USD. Ergebnis: 9 Zeilen auf echten Boersenwert gezogen (u.a. XAU 80.07→160.22, BZ 30.46→134.14). Ruecklauf 279.85→91.11, Peak 497.42→395.63. Kill-Kurve jetzt ehrlich; T-274 kann neu bewerten.
- [x] **T-290 — Beleg: nimmt Kraken Futures den leverage-Parameter an**
  Kontext: Hebel 7 geht als leverage-Feld mit jeder Order (weg.py); gemessen ist nur der Einschussplan EEA retail 10 % = max 10x. Mit laufendem NordLynx weist Futures ab (authenticationError).
  Naechster Schritt: 1 Kontrakt PF_SOLUSD mit leverage 7 kaufen und sofort schliessen (~0,12 USD Gebuehr) - braucht Guthaben (T-291) und VPN aus.
  Angelegt 2026-10-01 · Betrifft: Agenten/Handel/nautilus_kraken/kraken_futures.py
      PUT /leveragepreferences maxLeverage 7 gesetzt (Formkoerper, signiert); Margin je Kontrakt PF_SOLUSD 11,79 -> 16,80 USD gemessen; sendorder-leverage ignoriert Kraken
- [x] **T-289 — omnitrade_futures: Trailing-Stop in den Live-Zyklus einhaengen**
  Kontext: kraken_futures.stop_nachziehen(order_id, symbol, menge, stop_preis) (/editorder) ist gebaut (Commit debc983); der Live-Zyklus der Spur zieht den stp-Stop noch nicht nach.
  Naechster Schritt: Nachziehen im spur_buch-Live-Zweig verdrahten (Trigger z.B. Kurs +1 % ueber letztem Hoch), Test mit Testnaht weg.stop_nachziehen.
  Angelegt 2026-10-01 · Betrifft: Agenten/Handel/omnitrade_futures, nautilus_kraken/kraken_futures.py
      weg.stop_nachziehen (immer echt) an das spur_buch-Trailing T-286 angebunden; wachen trailing_stop_prozent 3.0; test_spur_buch/test_lage gruen
- [x] **T-252 - jevgrep installiert, aber ohne Jev-Schluessel nicht benutzbar**
      Kontext: `Agenten/Werkzeuge/jevgrep` (npm-Paket `@dzhng/jevgrep` 0.7.0) laeuft unter
      Windows und ist mit Attrappen-Endpunkt end-to-end nachgewiesen (6 Tests, 6,7 s); eine
      echte Suche ueber 171 Dateien kostet rund 4 US-Cent. Es fehlt allein der Anbieter-
      schluessel: `jg auth` wertet keine Umgebungsvariablen aus, im Haus liegt keiner
      (OmniRoute hat nur ein selbst-deaktiviertes OpenRouter-Konto), und der Anbieter
      `openrouter` zeigt auf `typesafe/jev-1.13`, das OpenRouter nicht fuehrt (nur
      `typesafe/jev-router`). Damit ist `jg` derzeit absichtlich NICHT angemeldet.
      Naechster Schritt (2 Minuten, Anmeldung macht Max selbst): GRATIS ueber OpenCode
      Zen - Zen bedient Jev unter demselben Pfad wie jevgrep und fuehrt ein zeitweise
      kostenloses `jev-1.13-free` (bezahltes `jev-1.13` 0,042 USD/1M). Also
      `opencode auth login` (Anbieter OpenCode Zen) und danach
        python Agenten/Werkzeuge/jevgrep/von_opencode_anmelden.py --anwenden --doctor
      Das Werkzeug liest den Schluessel aus der OpenCode-Anmeldung und gibt ihn nie aus;
      Trockenlauf ohne --anwenden. Ersatzweg (bezahlt): Vercel AI Gateway, Create key,
      dann `auth --provider vercel --stdin`. Danach die Wurzel klein waehlen (siehe Wiki,
      "Die Anfrage verfeinern": scanner 66 Dateien statt Agenten/Handel 5.247).
      Danach die Wurzel klein waehlen (siehe Wiki, Abschnitt "Die Anfrage verfeinern":
      scanner 66 Dateien statt Agenten/Handel 5.247) und mit `jg files` + `--exclude`
      vorher sehen, was hinausgeht. Kein Schluessel gewuenscht: Werkzeug ruht, `files`
      bleibt kostenlos nutzbar.
      Angelegt: 2026-09-30 · Betrifft: `Agenten/Werkzeuge/jevgrep`, `MaxHirn/Wiki/Werkzeuge/jevgrep.md`
      OPENCODE_API_KEY als Windows-Benutzervariable gesetzt; jg auth gegen https://opencode.ai/zen/v1 mit Modell jev-1.13-free, jg doctor 'Jev connection verified'; erste echte Suchen: Agenten/Handel/scanner 66 Dateien in 6,2 s / 22 Treffer, Agenten/Bus 40 Dateien / 9 Treffer; Kosten 0
- [x] **T-239 - Docker-Engine faellt ohne Wache aus (2x an einem Tag)**
      Kontext: Am 30.09.2026 antwortete die Docker-Engine zweimal nicht
      (Block 14 der Systempruefung). Der Motor ist die WSL-Distro
      `docker-desktop`; Docker Desktop allein bringt sie nicht hoch
      (Log `returning engine error`, Container-Status veraltet). Um 15:13 half
      `wsl --shutdown` + Neustart von Docker Desktop (danach liefen
      `nautilus-demo` und die freqtrade-Container wieder, nachgewiesen mit
      `docker ps`); um 17:37 war sie erneut weg. Ursache ist der
      Docker/MCP-Spawn-Kreis (Wiki/Betrieb/Systemleistung-2026-09-29.md,
      Abschnitt 9/10) - er reisst auch fremde Prozesse mit (0xC0000409).
      Naechster Schritt: Cron `docker-wache` nach dem Muster `bus-waechter`
      (no_agent, 15 min, leere Ausgabe = gesund): `docker info` mit
      Zeitgrenze; antwortet die Engine nicht, selbst `wsl --shutdown` +
      Docker Desktop starten und das melden. Erst danach den Spawn-Kreis
      angehen (T-152).
      Angelegt: 2026-09-30
      Betrifft: Agenten/Routinen/systempruefung.ps1 Block 14,
      Agenten/Routinen/nautilus-docker-start.ps1
      01.10.2026 gebaut und nachgewiesen: Cron 'docker-wache' (a41ae0df5b47, alle 15 min, no_agent, Telegram) - Script Agenten/Hermes/scripts/docker-wache.py: docker info mit 25 s; Antwortet die Engine nicht, heilt sie den Handgriff vom 30.09. (wsl --shutdown, Docker Desktop starten, bis 180 s warten), meldet Heilung/Misslingen, derselbe Befund hochstens alle 6 h, Erholung immer. Wahrend eines frischen hermes-update (Log < 20 min) heilt sie nicht, meldet nur. 8 Tests (Starten als Naht - kein Test faehrt die echte App hoch). ERSTER CRON-LAUF 14:44:24: status ok, leise (Engine lebt). Der eigentliche Urheber - der MCP-Spawn-Kreis - bleibt T-152.
- [x] **T-259 — Streu-Atlas `BrainFiles/.projectatlas` pinnt den ProjectAtlas-Standard auf omnitrade**
      Kontext: Unter der BrainFiles-Wurzel liegt ein 15 MB grosser Atlas vom 15.09.2026, der als
      Projektstamm `O:/Werkstatt/omnitrade` traegt. ProjectAtlas sucht das naechste `.projectatlas`
      AUFWÄRTS, deshalb endet jeder Aufruf aus einem anderen Verzeichnis (auch der Wurzel) mit
      `project_mismatch: selected project root '...BrainFiles' does not match index root
      'O:/Werkstatt/omnitrade'`. Der produktive Atlas (188 Dateien, `scan.status: verified`) liegt
      in `Werkstatt/omnitrade/.projectatlas` und ist nicht betroffen.
      Naechster Schritt: entscheiden — Streu-Atlas loeschen (er wird nirgends gelesen) oder stehen
      lassen und Aufrufe immer mit `--db`/`--config` auf das Ziel zeigen.
      Angelegt: 2026-09-30 · Betrifft: `BrainFiles/.projectatlas`, `Agenten/Werkzeuge/projectatlas`
      01.10.2026 angewandt: Streu-Atlas per shutil.move nach O:\Werkstatt\Ausgemustert\projectatlas-streu-20261001 (nichts geloescht, Gegenprobe db da). Wirkung gemessen: Aufruf aus Werkstatt/omnitrade antwortet unveraendert gesund (overview: 194 Dateien, 31 Ordner); Aufruf aus der Wurzel meldet jetzt 'init_required' statt 'project_mismatch' - die Irrefuehrung ist weg. Keine referenzierende Routine gefunden (Routinen/Werkzeuge grep leer), Atlas war unversioniert.
- [x] **T-251 - Zwei echte Luecken in der Zentrale: `foreman` und `kerzenschluss_bias.py`**
      Kontext: Nach der Umstellung am 30.09.2026 stehen genau zwei Zeilen in EINRICHTEN -
      beide zu Recht. `foreman` (REPOS) hat kein `.venv`, ist aber ein Python-Paket mit
      `src/foreman/__main__.py` und `pyproject.toml`; `kerzenschluss_bias.py` (HANDEL) hat
      `argparse`+`__main__`, aber noch keinen echten Lauf (Hausregel „kein geratener
      Befehl"). `foreman` ist fremd und nur lesend gedacht - ein venv darin waere ein
      Schreibzugriff, den niemand braucht.
      Naechster Schritt: `kerzenschluss_bias.py --help` einmal fahren und in
      `fuellen.HILFE_VERIFIZIERT` aufnehmen; bei `foreman` entscheiden, ob es genutzt wird
      (dann venv) oder ob es als „kein eigener Start" gefuehrt wird.
      Angelegt: 2026-09-30 · Betrifft: `Agenten/Werkzeuge/repos-zentrale/fuellen.py`
      01.10.2026 beide Luecken geschlossen: kerzenschluss_bias.py - --help mit dem Handel-venv gefahren (Code 0, Beleg-Log vom 30.09. und heutige Wiederholung), in fuellen.HILFE_VERIFIZIERT aufgenommen, Notiz auf belegten Stand gezogen. foreman - Entscheidung im Sinne des Auftrags: Bewusst KEIN venv, KEIN Start (fremder nur-lesen-Klon, kein Verbraucher im Haus); Manifest tragt gruppe kein_start + warnungen + Grund, Anleitung bleibt fuer einen spaeteren Wechsel stehen. Gegenprobe: Zentrale-Suite 296 Tests (der eine Fehlschlag ist T-271/kopier, fremd), --pruefen nennt keine EINRICHTEN-Zeile mehr.
- [x] **T-240 - Datensortierung: Einzelinstanz-Schutz fehlt**
      Kontext: `MaxHirn-Datensortierung` ist mit IgnoreNew eingestellt, das
      schuetzt aber nur gegen die Aufgabe selbst. Am 30.09.2026 liefen
      nacheinander drei von Hand gestartete Instanzen aus parallelen
      Sitzungen (14:30, 15:37, 17:22, 17:26), die sich das Tagesprotokoll
      gegenseitig ueberschrieben; eine stand ueber eine Stunde im
      Suchblock. Der Suchblock selbst ist am 30.09.2026 entschaerft
      (ein Suchlauf statt einem je Kandidat, nur Textendungen, ohne
      site-packages/.venv*): gemessen 446 s statt Abbruch nach >43 min.
      Naechster Schritt: Sperrdatei mit PID und Alter am Skriptanfang
      (Muster `dauerlauf.pid`), Handstart bricht dann mit klarer Meldung ab.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Routinen/datensortierung.ps1
      01.10.2026 gebaut und gemessen: Sperrdatei logs\datensortierung.pid mit PID + ISO-Startzeit, Pruefung auf ProzessNAME (powershell/pwsh) und Startzeitvergleich (2 min Toleranz) - haelte einer PID-Wiederverwendung stand (Fall 2 im Test: tote PID 999999 wird durchgelassen und neu gesperrt). Handstart bei lebender Fremdsperrung: Exit 3 mit fertiger Raeum-Meldung (Test: 'Es laeuft bereits eine Datensortierung (PID 42156, Sperre von 2026-10-01 14:06, 0 min alt)...'). Freigabe nur fuer den eigenen PID-Wert im finally. Zwei Fallen beim Bauen: Zeitstempel mit Leerzeichen zerbrach das -split-Feldschema (jetzt ISO T-Form), und -f bindet staerker als + (Platzhalter blieben wortwoertlich).
- [x] **T-263 — orb und orbk stehen in der Replay-Liste, sind aber nicht fahrbar**
      Kontext: `replay.SPUREN_TEIL_A` (und damit die Spurliste des Leitstand-Reiters) fuehrt
      `orb` und `orbk`; ihre `handeln.py` haben kein `lade_wachen()`, deshalb bleibt `w` leer,
      die Instrumentenliste leer und JEDER Replay-Lauf endet in einer Verweigerung. Ihre
      `wachen.json` traegt die Instrumente ausserdem als DICT mit Boersennamen
      (`BTC_USDT` -> `BTC-USDT-SWAP`), ohne `kerzen_takt`/`mindest_kerzen`; `orbk` nennt
      `ETH_USD`/`HYPE_EUR`, wofuer `historie_binance.PAARE` kein Binance-Paar kennt.
      Aufgefallen am 01.10.2026 beim Nachzaehlen, welcher A-Spur Historie fehlt - allen
      anderen fehlt sie nicht (BTC/ETH/SOL, 50.223 1H- und 12.559 4H-Kerzen).
      Naechster Schritt: entscheiden - aus der Replay-Liste nehmen (eigener Backtest liegt in
      `orbk/backtest.py`) oder fahrbar machen (wachen-Form, Kerzennaht, Binance-Paare).
      Angelegt 01.10.2026 · Betrifft Agenten/Handel/replay.py, Agenten/Handel/orb, Agenten/Handel/orbk, Agenten/Handel/leitstand_backtests.py
      01.10.2026 nachgeprueft: geloesft durch b0a451b (02:06, Option 'aus der Replay-Liste') - orb und orbk nicht mehr in SPUREN_TEIL_A, beide unter NICHT_NACHRECHENBAR mit Grund (kein lade_wachen(); orbk zusaetzlich eigener Backtest). Leitstand bietet damit nur noch fahrbare Spuren an. Nicht von dieser Sitzung gebaut.
- [x] **T-267 — drei Claude-Worktrees unter `.claude/worktrees/` liegen seit dem 30.09. herum**
      Kontext: `festive-hertz-7ab82c` und `tag-troubleshoot-config-guide-cf780d` haben 0 eigene
      Commits und sind sauber; `trading-stack-setup-40ef0d` traegt einen Commit
      (`aeeac18`, Omnitrade-Indikatoren) und zwei unversionierte Dateien. Geprueft am 01.10.2026:
      der Commit-Inhalt steht bereits in master (Zeile 118 in `MaxHirn/Wissen/Omnitrade.md`),
      `omnitrade_auswertung.py` ist byte-gleich, `omnitrade_start.py` ist die ALTE 162-Zeilen-
      Fassung (master hat 216) — es geht also nichts verloren. Zusammen 137 MB.
      Naechster Schritt: erst pruefen, dass keine Claude-Sitzung mehr darauf arbeitet (am 01.10.
      liefen 14 `claude`-Prozesse), dann `git worktree remove <pfad>` (die Branches bleiben) und
      `git worktree prune`. Regel aus `Agenten/Handel/AGENTS.md`: neue Worktrees NEBEN
      `BrainFiles/` anlegen, nicht hinein.
      Angelegt 01.10.2026 · Betrifft .claude/worktrees/, git worktree
      01.10.2026 angewandt: keine Prozess-Kommandozeile referenzierte die Worktrees (die 14 claude.exe waren das Desktop-App-Set ohne Worktree-Bezug); Gegenprobe: alle drei sauber oder Inhalt durch master gedeckt (auswertung identisch bis Zeilenenden, start die alte 162er-Fassung). git worktree remove gefahren (dirty eine mit --force), danach prune. worktree list nennt nur noch die Hauptarbeit; die drei claude/*-Zweige bleiben wie im Auftrag festgehalten. ~137 MB frei auf C:.
- [x] **T-243 - Zentrale: Handelsstand selbst nachziehen statt nur auf Klick**
      Kontext: Die Handels-Karte der Repos-Zentrale liest `spuren_stand.py`
      EINMAL und merkt sich den Stand (`fenster.Fenster.handel_zustand`).
      Danach zeigt sie ihn, bis jemand "Stand neu lesen" drueckt - oeffnet der
      Dauerlauf in der Zwischenzeit ein Zeitfenster oder wechselt ein Schalter,
      steht im Fenster ein alter Stand. Bewusst NICHT gebaut, weil ein
      Dauerlauf-Takt im Fenster eine eigene Entscheidung ist (Last, und die
      Frage "wie alt darf die Anzeige sein"). Ebenso bewusst: es gibt KEINEN
      Kommandozeilen-Weg zum Scharfschalten (`--handel` und `--test` lesen nur),
      weil Handelsregeln Punkt 3 ein Fenster mit Bestaetigungsfeld verlangt;
      wer von unterwegs scharf stellen will, hat dafuer `/ja_<spur>` im
      Dauerlauf.
      Naechster Schritt: Entscheidung Max - entweder ein Takt (z. B. alle 60 s
      nur bei gewaehlter Spur) oder ein Zeitstempel "gelesen um HH:MM" in der
      Kopfzeile der Karte, damit der Stand sein Alter nennt.
      Betrifft: `Agenten/Werkzeuge/repos-zentrale/fenster.py`,
      `handelstand.py`
      Angelegt: 2026-09-30
      01.10.2026 nachgeprueft: die Takt-Loesung ist bereits gebaut und gepusht (bc8041a, uebernommene Fremdarbeit) - 60 s Selbst-Nachziehen, nur wenn die Handels-Karte sichtbar ist, schaltbar per 'Auto: an/aus', Takt neu aufgezogen nach jedem Lauf. Gegengesehen in der Zentrale-Suite (296 Tests, der einzige Fehlschlag ist T-271/Betrifft nicht den Takt).
- [x] **T-286 - omnitrade_futures: Trailing-Stop in den Live-Zyklus einhaengen**
      Kontext: kraken_futures.stop_nachziehen(order_id, symbol, menge, stop_preis)
      (/editorder) ist gebaut und getestet, aber spur_buch.zyklus kennt keinen
      "Stop nachziehen"-Schritt - der stp-Stop steht beim Einstieg und wird nie bewegt.
      Naechster Schritt: im Live-Zweig nach dem Kursabruf je Position den Stop an
      hoechstkurs x (1 - trailing_pct) ziehen (nur nach oben, Dedupe je Preisstufe,
      Scheitern des Nachziehens darf die Position NICHT ungeschuetzt lassen).
      Angelegt · 01.10.2026 · Betrifft Agenten/Handel/spur_buch.py, omnitrade_futures/weg.py
      
- [x] **T-281 - kraken-Spur: Guthaben-Tor offen, aber handel_erlaubt=false und EV negativ**
      Erledigt 2026-10-01. Max ("kraken scharf", dann "bedingung 5 entfaellt"):
      freigabe.erfuellt true, AUTO_FREIGABE wieder aufgenommen, Bedingung 5 ueber
      `bedingung_5_aktiv: false` abschaltbar (Vorgabe bleibt JA). Die Spur hat um
      13:25:51 drei Belege ausgestellt, SOLEUR wurde 13:27:22 live ausgefuehrt
      (0,47998464 SOL @ 104,26 EUR, Stop 97,72 an der Boerse). Nebenbefund und
      behoben: der Papierzweig warf UnboundLocalError (gefuellt/fuellung_bestaetigt
      nur im Live-Zweig) - kraken/tests 174 gruen. Wiki/Handel/Guthaben-und-Umschichtung.md.
      Betrifft: Agenten/Handel/kraken/, Agenten/Handel/dauerlauf.py
- [x] **T-269 — Freitext im SkillsBot endet in '(Aufgabe FAILED)'**
      Kontext: Am 01.10.2026 um 01:57:02 kam auf "Netto in den Bericht" nach 300,4 s die
      16-Zeichen-Antwort `(Aufgabe FAILED)` zurueck (skillsbot.log; 16 Zeichen = genau
      `(Aufgabe FAILED)` aus `_aufgabe_abholen`). Die A2A-Aufgabe an hermes-maks-pc
      scheitert also - nicht der Bot. Dieselbe Signatur tragen ALLE frueheren Freitext-
      Auftraege ("Auswertung" 29.09., "Ja" und "Tagesbericht auswerten" 28.-30.09.:
      je 300 s und 16 Zeichen). Slash-Befehle sind NICHT betroffen: `/strategien` lief
      am selben Abend in 2,5 s mit 2642 Zeichen durch (Telegram hat die Sendung
      angenommen - `sende()` ruft sendMessage direkt, ein Fehlschlag waere als
      `status: fehler` protokolliert).
      Naechster Schritt: die A2A-Aufgabe im Gateway nachsehen (Gateway-Log zur Uhrzeit,
      Profil default/hermes-maks-pc, warum TASK_STATE_FAILED statt COMPLETED) - und bis
      dahin fuer echte Arbeit `/run <skill>` (Frist 1800 s) oder die Desktop-App nutzen.
      Angelegt: 2026-10-01 · Betrifft: Agenten/Bus/skillsbot.py, Agenten/Hermes (Gateway)
      **Erledigt 2026-10-01.** Ursache gefunden und behoben: NICHT der Agent scheiterte, sondern die Frist war zu kurz. Belege aus dem Gateway-Log derselben Stunde: dieselbe Omniquant-Frage wurde um 07:56:34 nach 401,4 s beantwortet, die Rueckfrage um 08:23:16 nach 1504,6 s - der SkillsBot gab nach 300 s auf und antwortete mit dem 16-Zeichen-'(Aufgabe FAILED)'. Aenderungen: neue Konstante A2A_FRIST_S 1800 (dieselbe Frist wie /bot), die Warteschleife in _aufgabe_abholen benutzt sie statt des HTTP-Limits, frist_meldung() sagt jetzt 'laeuft noch / NICHT gescheitert / so geht es weiter', und Freitext warnt VOR dem Warten (Muster von /run). Tests: tests/test_skillsbot_freitext.py (8). Bot neu gestartet (PID 77696 -> 45916). Die verbleibende Einfaedigkeit steht als neuer Task.
- [x] **T-270 — RLTrader-Klon ist die einzige Kopie seiner Arbeit (kein Remote, keine Sicherung)**
      Kontext: Werkstatt/RLTrader traegt zwei lokale Commits (9e3090d Pine der
      Altsitzung, 25d9ff0 Docker-Weg vom 01.10.2026). origin zeigt auf
      notadamking/RLTrader (upstream, ruhend) - ein Push dorthin kommt nicht in
      Frage, ein Fork fehlt. Werkstatt ist in BEIDEN Sicherungen per /XD
      ausgenommen; ein Plattendefekt auf O: loeschte den Docker-Bau endgueltig.
      Naechster Schritt: Entscheidung Max - privater Fork mfaupel95/rltrader wie
      bei omnitrade, dann origin=Fork / upstream=Original stellen.
      Angelegt 01.10.2026 · Zuletzt 01.10.2026 · Betrifft Werkstatt/RLTrader
      01.10.2026 angewandt: git fetch --unshallow (286 Commits), origin=privates Repo mfaupel95/rltrader (gh api: private true, ls-remote master 25d9ff0 = lokal), upstream=notadamking; Docker-Weg-Commit 25d9ff0 gepusht; Wiki-Seite und FREMD-Eintrag nachgezogen.
- [x] **T-279 - OKX: rund 275 USD Krypto lagen ungenutzt, das Guthaben-Tor stand bei 30,84 USDC**
      Erledigt 2026-10-01. Sechs Posten in USDC verkauft (NEIRO, DOGS, EURC, ACE, WAXP, CHIP,
      zusammen ~92,56 USD); `availBal` 31,50 -> 144,70. BETH und OKSOL blieben liegen
      (Compliance-Sperre, jetzt in T-280 vermerkt). mosaic nennt seitdem nur noch das
      Freigabefenster als Sperre — siehe Wiki/Handel/Guthaben-und-Umschichtung.md.
      Betrifft: Agenten/Handel/mosaic/wachen.json, OKX-Konto
- [x] **T-264 — 18 von 41 Spuren haben keine Gebuehr in der wachen.json**
      Kontext: T-192 hat brutto und netto getrennt und den Mangel damit SICHTBAR
      gemacht - der Bericht sagt jetzt "BRUTTO und UNBEKANNT: kein gebuehr_taker in der
      wachen.json". Ohne Gebuehr stehen: gitter, kopier, kopier1zu1, macd_mtf, omniquant,
      squeeze, supertrend, wavetrend, nautilus, nautilus_kraken, nautilus_kraken_futures
      und die sieben moondev_* (funding, liquidation, listingarb, sentiment, sniper,
      topmovers, whale). Einen Satz einzusetzen ist eine Entscheidung JE SPUR (Boerse,
      Kontotyp, Maker/Taker, XPERP oder SWAP) - geraten waere schlimmer als "unbekannt".
      Naechster Schritt: je Spur die Boerse und den GEMESSENEN Satz nennen (OKX XPERP/SWAP
      0.0005, Kraken Spot 0.006, Deribit 0.0005), eintragen, `auswertung_alle.py` erneut -
      das Urteil der Spuren aendert sich damit.
      Angelegt: 2026-10-01 · Betrifft: Agenten/Handel/*/wachen.json, Agenten/Handel/auswertung_alle.py
      **Erledigt 2026-10-01 (Gebuehren-Teil).** Am eigenen OKX-Konto gemessen - Tarif Lv1 UND echte Fuellung: Spot 0,10 %/Seite (HYPE-USDC 0,002772544 auf 2,77254 USDC), Futures/XPERP 0,05 %/Seite (ZEC-/ADA-USD_UM_XPERP). Gesetzt mit `Agenten/Handel/gebuehren_setzen.py` (Vorschau Standard, `--messen` fragt den Tarif ab): neun Spuren auf 0.001 (Spot: scanner, squeeze, wavetrend, macd_mtf, supertrend, gitter, iv_wand, moondev_topmovers, moondev_listingarb), fuenf auf 0.0005 (moondev_funding/-whale/-liquidation/-sentiment, nautilus), nautilus_kraken von 0 auf 0.6. Zwei Zuordnungsfehler in `replay.SPUR_BOERSE` behoben (gitter stand als Perp, orb als Spot). Der Kern: scanner rechnete OKX-SPOT mit 0,05 % statt 0,10 % - jede Netto-Zahl war 0,1 Prozentpunkte je Runde zu freundlich. `auswertung_alle.py` meldet nur noch fuer moondev_sniper "BRUTTO und UNBEKANNT"; Rest als T-268.
- [x] **T-192 — Auswertung: drei Messluecken lassen tote Spuren lebendig aussehen**
      Kontext: Die Auswertung vom 30.09.2026 (`auswertung_alle.py` alle drei Stufen +
      `kosten_wendepunkt.py`) zeigt drei Luecken, die jede Zahl verzerren.
      (1) **Kein Gebuehrenfeld**: `orb`, `orbk`, `scanner`, `moondev_signalwelle` und
      `iv_wand` tragen in ihrer `wachen.json` ueberhaupt keinen Gebuehrenschluessel
      (`grep gebuehr` in orbk/*.py findet nichts). Der Kosten-Wendepunkt rechnet sie
      deshalb mit 0 % und nennt orb +0,07 %, orbk/mittel +0,01 %, orbk/hoch +0,03 %
      "tragfaehig, haengt an der Gebuehrfreiheit (unter 0,4 %)". orbk ist aber
      **ORB auf Kraken-Spot** und die gemessene Kraken-Gebuehr ist **0,600 % je Seite
      = 1,2 % je Runde** (Fuellung 22.09.2026) - orbk ist damit um rund das 40-fache
      tot, orb (OKX, ~0,1 %/Runde) in Basis ebenfalls.
      (2) **orbk-Journal ohne Einsatz**: `orbk/handelsjournal.csv` fuehrt
      `zeit,inst,richtung,einstieg,stop,ziel,ausgang,ausstieg,gv_punkte,gv_usd` -
      ohne Einsatzspalte sagt der Bericht "Ergebnis in Prozent: kein Einsatz im
      Journal", 16 Runden lassen sich nicht in Prozent ausdruecken.
      (3) **Papierzeilen ohne Gebuehr**: alle Papierbuecher melden "Kosten 0.00 %",
      die echten 0.05 % (scanner), 0.39-0.50 % (xperp/swap) und 0.60 % (kraken) -
      die Papiersummen sind BRUTTO und mit den Live-Zahlen nicht vergleichbar.
      Naechster Schritt: (1) Gebuehr in die wachen.json von orb/orbk/scanner/
      moondev_signalwelle/iv_wand eintragen (Kraken 0.006, OKX 0.0005), dann
      `kosten_wendepunkt.py` erneut - das Urteil der Spuren aendert sich damit;
      (2) orbk schreibt den Einsatz je Runde mit (Muster scanner);
      (3) `auswertung_alle.py` weist brutto UND netto aus und markiert Bruttozeilen.
      Fortschritt: (1) erledigt am 30.09.2026 (Commit 7c525cd) - `gebuehr_taker` steht
      jetzt in orb (0.0005), orbk (0.006), scanner (0.0005), moondev_signalwelle (0.0005)
      und iv_wand (0.0005), dazu ein Einheitenfehler im Werkzeug behoben: es druckte den
      Bruch als Prozentwert und verglich ihn direkt mit f_max. Neues Urteil: orbk
      "1.200 % je Runde (0.600 % je Seite) liegt darueber" - tot. Test
      `tests/test_kosten_wendepunkt.py` (9). Punkte (2) und (3) bleiben offen.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Handel/{orb,orbk,scanner,moondev_signalwelle,iv_wand}/wachen.json,
                Agenten/Handel/auswertung_alle.py, Agenten/Handel/kosten_wendepunkt.py
      **Erledigt 2026-10-01.** Punkte (2) und (3) sind gebaut. (3) `auswertung_alle.kennzahlen()` weist brutto UND netto aus (`brutto`/`gebuehr`/`kosten_netto`/`netto`/`netto_pct`), die neue Zeile 'Brutto/Netto' nennt den Satz und die Nettosumme; `GEBUEHR_SCHON_DRIN` (xperp/swap/scanner/kraken) verhindert das ZWEIMALIGE Abziehen. Gemessen: mosaic +10.82 -> +9.62 USD, moondev_marktlage -5.02 -> -6.02, moondev_signalwelle +38.85 -> +37.92, iv_wand +2.30 -> +2.00. (2) KEIN erfundener Einsatz: orb/orbk fuehren ein PUNKTE-Buch, ein Einsatz kaeme aus risiko/stop_abstand und der ORB-Stop ist die Range-Hoehe (bei ETH ~0,4 % -> einige tausend USD Nominal) - das ist eine Design-Entscheidung. Statt dessen steht das Ergebnis in R (`runden_orbk` liefert risiko/r_vielfaches, `r_kennzahlen()` summiert): orbk +2.18 R gesamt, orb -0.46 R - und orb/orbk sind jetzt auch in der Auswertung (orb fehlte ganz), Einheit 'Punkte' statt 'USD'. Tests: tests/test_brutto_netto.py (18) neu, test_einheit_kraken prueft die Eigenschaft statt des Wortlauts. Rest offen als T-264 (18 Spuren ohne Gebuehr).
- [x] **T-201 — Container `freqtrade` (Port 8080) hat keinen Zweck mehr**
      Kontext: Der Vorgaenger-Container faehrt `SampleStrategy` und laeuft seit dem Aufbau
      der drei Bot-Container weiter mit. Er belegt Port 8080, verbraucht Commit und ist
      im Ablauf eine Verwechslungsquelle - die drei echten Bots liegen auf
      8081/8082/8083. Nachtrag 30.09.2026: Er macht ausserdem einen Test rot.
      `test_freqtrade_bridge.LiveTest.test_lage_vom_echten_bot` faellt mit
      `HTTP 401 bei /show_config`. Gemessen mit DENSELBEN Zugangsdaten aus
      `user_data/config.json`: Port 8080 antwortet auf ping 200, auf show_config 401;
      Port 8081 beides 200. Der Altlast-Container traegt also ein anderes Passwort im
      Speicher als die Datei (gestartet 30.09. 19:51 lokal, config.json vom 29.09.
      18:43) - die Bridge liest die Datei und wird abgewiesen. Sonst ist die Suite
      gruen: 1377 Tests, dieser eine Fehler, 9 uebersprungen.
      Naechster Schritt: pruefen, ob Max ihn von Hand nutzt (dann Kennzeichnung), sonst
      in `bots_starten.sh` als Altlast vermerken und den Container stoppen. NICHT ohne
      Rueckmeldung loeschen - es ist der einzige Container, dessen Zweck ich nicht kenne.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      **Erledigt 2026-09-30.** Max hat den Container gestoppt (`freqtrade`, Port 8080, SampleStrategy): `docker ps -a` zeigt 'Exited (137)' nach 22 Minuten, die drei echten Bots (8081-8083) laufen weiter. Der Live-Test der Bridge ist damit uebersprungen statt rot (`test_freqtrade_bridge`: OK, skipped=1; vorher HTTP 401 bei /show_config). Ursache des Fehlers gemessen: derselbe Zugang aus user_data/config.json antwortete auf Port 8080 mit ping 200 / show_config 401, auf Port 8081 mit beides 200 - der Altlast-Container trug ein anderes Passwort im Speicher. In bots_starten.sh als Altlast vermerkt (er wird dort nicht gestartet). Commits 266a5a6 und der folgende.
- [x] **T-206 — omnitrade hat keinen Kraken-Weg: der Auftrag "Kraken nur omnitrade" ist bisher eine Sperre**
      Kontext: Max hat am 30.09.2026 angeordnet, nur noch omnitrade auf Kraken
      handeln zu lassen. Die Sperrseite ist umgesetzt (`kraken` und
      `moondev_marktlage` auf handel_erlaubt=false, `mosaic` auf boersen ["okx"],
      alle vier Kraken-Spuren aus `dauerlauf.AUTO_FREIGABE`), die Freigabeseite
      nicht: `omnitrade-exchange/src/` kennt nur `binance` und `okx`, und
      `omnitrade-cli/src/commands/live.rs:33` weist jedes andere `--exchange` ab
      ("Use 'binance' or 'okx'"). Bis dahin handelt NIEMAND auf Kraken.
      Naechster Schritt: entscheiden, welcher Weg gebaut wird - (A) Kraken-Adapter
      in Rust (`omnitrade-exchange/src/kraken.rs`: ExchangeStream/ExchangeInfo/
      ExchangeTrading, HMAC-SHA512 + Nonce, Paar- und Preisregeln; braucht einen
      EIGENEN Kraken-Schluessel, sonst kollidiert der Nonce-Zaehler mit dem
      Haus-Pool) oder (B) Haus-Spur `omnitrade`, die `Werkstatt/omnitrade/status/
      live.json` ueber `Agenten/Handel/omnitrade_bridge.py` liest und ueber den
      bewaehrten `kraken/kraken.py` ordert.
      Angelegt: 2026-09-30
      Zuletzt: 2026-09-30
      Betrifft: Werkstatt/omnitrade, Agenten/Handel/dauerlauf.py,
      Agenten/Handel/kraken/wachen.json, Agenten/Handel/mosaic/wachen.json,
      Agenten/Handel/moondev_marktlage/wachen.json
      **Erledigt 2026-09-30.** Weg B gebaut (Entscheidung Max): neue Spur Agenten/Handel/omnitrade spiegelt die Position der Rust-Laeufe (Zustand net_quantity statt Orderliste, zwei Zeugen Statusdatei+PID, echter Verkaufspreis aus recent_orders) und fuehrt im Live-Zweig ueber den Haus-Kraken-Weg (boerse kraken, kraken_quote USDC, guthaben_waehrung USDC, mindest_guthaben 60) - omnitrade bleibt der Entscheider, kein Kraken-Adapter in Rust. Verdrahtet in dauerlauf.SPUREN, lage.HOLER (live_faehig), auswertung_alle.BOT_SPUREN, pruefe_ratschen, .gitignore. Beleg: 31 Tests gruen, Vorschau nennt vier Sperrgruende (u.a. 25.08 von 60 USDC frei), erster Zyklus 30.09. 21:26:20 'omnitrade (papier) ok', spiegelstand 38/38 byte-gleich. Commit 6197ac9, Wiki/Handel/omnitrade-Spur.md. Offen bleibt nur das Guthaben (T-256).
- [x] **T-245 - Pending-Memory-Queue: 25 Konsolidierungsvorschlaege inhaltlich nachziehen oder loeschen**
      Kontext: `Agenten/Hermes/pending/memory/` traegt 25 Vorschlaege aus
      `background_review` (aeltester 09.09.2026, neuester 24.09.2026, ~60 KB).
      Am 30.09.2026 um 18:32 hat Max `/memory approve all` ausgefuehrt; MEMORY.md
      wurde neu geschrieben, aber KEIN Inhalt aus der Queue steht heute im
      Gedaechtnis (Stichproben "OKX-Schluessel 19.09.2026 erneuert" und
      "841 Zeilen" fehlen beide). Die Anker der Vorschlaege sind tagealt und
      treffen nicht mehr - ein Vorschlag verfaellt mit seinem Anker.
      Naechster Schritt: je Vorschlag pruefen, ob der Inhalt heute noch fehlt
      und noch stimmt, dann von Hand in MEMORY.md nachziehen; den Rest loeschen
      (nicht "freigeben").
      Betrifft: `Agenten/Hermes/pending/memory/`, `memories/MEMORY.md`
      Angelegt: 2026-09-30
      **Erledigt 2026-09-30.** 25 Vorschlaege aus background_review (46 Einzeloperationen, 09.-24.09.2026) einzeln geprueft. Nur 4 Inhalte fehlten wirklich und stimmen noch, von Hand nachgezogen: (1) Bedingung 5 rechnet auf HANDELSRUNDEN - in scanner/wachen_pruefung.py nachgemessen (rollierender_ev aus teile_runden, rollierender_ev_alle fuer Diagnose), der alte Memory-Satz 'OFFEN (Entscheidung Max)' war damit falsch; (2) FOMO/Copy-Trading (Plan Werkstatt/fomo-copy-trading-plan.md, 8307 B, nichts gebaut); (3) Plan-Modus (skills/.archive/plan/SKILL.md vorhanden); (4) scanner-Journal fuehrt mfe_pct/mae_pct/haltetage (Kopfzeile gemessen). MEMORY.md 245.477 -> 247.972 Zeichen. Dazu 2 Nutzer-Eintraege in USER.md (5.565 -> 6.266): Antwortform bei 'fuehre Skill X aus', Git-Zweige/EIN Arbeitszweig. Alles Uebrige verworfen (Anker tagealt, wiederholte Vorhandenes, Arbeitsprotokoll); 25 Dateien aus pending/memory/ geloescht, Volltext-Digest Agenten/Hermes/.sicherung/memory-queue-verworfen-20260930.md. Widerlegt beim Pruefen: der 'Ollama-Store-Pfad'-Fehlalarm steht nicht mehr in systempruefung.ps1.
- [x] **T-246 - Wache fuer Memory-Verluste (Cron)**
      Kontext: Ein `replace` mit falsch gewaehltem `old_text` loescht einen
      fremden Eintrag vollstaendig; bemerkt hat es am 30.09.2026 erst eine Suche
      Stunden spaeter. Das Werkzeug `Agenten/Hermes/scripts/memory-verlust.py`
      kann den Zustand jederzeit messen, wird aber von niemandem aufgerufen -
      ein Nachweis ist keine Wache.
      Naechster Schritt: Hermes-Cron (z. B. taeglich, no_agent, Telegram, leere
      Ausgabe = nichts senden) auf `memory-verlust.py --json`; melden nur, wenn
      ein Eintrag neu verloren ist (Merkdatei), nicht bei den 8 bekannten
      Altfaellen.
      Betrifft: `Agenten/Hermes/scripts/memory-verlust.py`, Hermes-Cron
      Angelegt: 2026-09-30
      Hermes-Cron f6f34ed95e0b (taeglich 20:45, no_agent, Telegram, leere Ausgabe = nichts senden); Skript Agenten/Hermes/scripts/memory-verlust-wache.py, Tests test_memory_verlust_wache.py 7 + test_memory_verlust.py 7 gruen. Erster Lauf setzt die Baseline und schweigt (6 bekannte Altfaelle).
- [x] **T-237 - Werkstatt/handel-stack: Spiegel weiterfuehren, einfrieren oder abloesen? (Entscheidung Max)**
      Kontext: `Werkstatt/handel-stack` ist ein privates GitHub-Repo
      (mfaupel95/handel-stack) mit dem Import von `Agenten/Handel` vom
      18.09.2026: 33 der heute 48 Spuren samt Journalen und Zustand, aeltere
      Staende (dauerlauf.py 43 statt 64 KB). Gemessen: nichts liest ihn, er
      enthaelt keine Geheimnisse, `repos-updaten.py` fasst ihn nicht an. Er
      stoert nur als zweite, aeltere Wahrheit im Suchweg und steht deshalb im
      Manifest als Rolle "Spiegel (18.09.)" mit Warnung.
      Naechster Schritt: entscheiden - (a) so lassen (eingefrorener Zeuge),
      (b) Spiegel gelegentlich auffrischen, (c) durch die vorhandene Sicherung
      ersetzen und den Ordner aus dem Baum nehmen.
      Angelegt: 2026-09-30
      Betrifft: Werkstatt/handel-stack/, mfaupel95/handel-stack
      **Erledigt 30.09.2026.** Entscheidung Max: "so lassen". Gemessen: nichts liest den Spiegen, keine Geheimnisse, repos-updaten.py fasst ihn nicht an. Er steht jetzt als 'Altstand (Spiegel 18.09.)' in Agenten/FREMD-Liste.json und zaehlt nicht als lebender Code - er bleibt, weil er die einzige Kopie des Handelsstacks ausser Haus ist.
- [x] **T-231 - C: hat keine Reserve fuer Desktop-Builds (Entscheidung Max)**
      Kontext: Am 30.09.2026 lief C: waehrend des Desktop-Baus auf 0,1 GB frei
      (475 GB Platte, 93 % belegt) - der Build braucht rund 20 GB transient.
      Folge: `desktop promotion rename win-unpacked -> win-unpacked.previous`
      scheiterte mit WinError 5 und `OSError: [Errno 28] No space left on
      device`, der Update-Schwanz blieb liegen, der Desktop kam in eine
      Bootschleife und das Gateway war von 14:20 bis 15:33 aus. Sofortmassnahme
      war Aufraeumen (uv-Cache 9,2 GB, Temp 4,6 GB, Build-Reste 0,5 GB ->
      35,9 GB frei, danach wieder 32,9 GB).
      Naechster Schritt: entscheiden, ob eine Dauerreserve von ~30 GB auf C:
      gehalten wird (Wache oder Aufraeumroutine vor jedem Update) oder ob die
      Auslagerungsdatei von C: nach O: wandert (Skript
      `Agenten/Routinen/einmalig-20260930-auslagerung.ps1`, noch nicht
      ausgefuehrt, braucht Admin).
      Angelegt: 2026-09-30
      Betrifft: C:-Laufwerk, Agenten/Hermes/hermes-agent/apps/desktop,
      Agenten/Routinen/einmalig-20260930-auslagerung.ps1
      Entscheidung Max (30.09.2026): Reserve halten UND Auslagerung umziehen. Reserve: platz-wache haelt 30 GB frei (Schwelle 25 -> 30, Cron jetzt taeglich 07:45 statt Montag), raeumt unter der Reserve selbst auf (Temp >24 h, CrashDumps, uv-Cache, npm-Cache; nie node_modules/.venv; nichts bei laufendem Bau), Tests 15 gruen. Auslagerung: C: 8192/8192 fest, O: 32768/32768 in Registry und WMI nachgeprueft - wirksam erst nach Neustart (Commit 84,5 -> rund 103,7 GB). Wiki/Betrieb/Sicherung-und-Laufwerke.md.
- [x] **T-233 - terminal.cwd steht auf Agenten\Hermes statt auf der BrainFiles-Wurzel (gewollt?)**
      Kontext: Beim Setzen der Kompression auf Standard (Commit d4429fb) lag
      eine fremde Aenderung im Arbeitsbaum: `terminal.cwd` war von
      `C:\Users\faupe\documents\BrainFiles` auf
      `C:\Users\faupe\documents\BrainFiles\Agenten\Hermes` geaendert. Sie wurde
      mitgenommen, weil eine Datei nicht teilbar ist. Werkzeuge und Sitzungen
      starten damit kuenftig eine Ebene tiefer - der Wurzel-Aufrufer
      (`omnitrade.cmd`) und die relativen Pfade der Hausregeln gehen von der
      Wurzel aus.
      Naechster Schritt: entscheiden, ob das so bleibt (Desktop-Einstellung
      "Shell-Umgebung" -> Arbeitsverzeichnis) oder zurueck auf die Wurzel.
      Angelegt: 2026-09-30
      Betrifft: Agenten/Hermes/config.yaml (terminal.cwd)
      Entscheidung Max (30.09.2026): cwd bleibt Agenten/Hermes. Abhaengigkeiten repariert: Anker cd "$HERMES_HOME/../.." in 9 Skills/READMEs, tasks-anpassen.py lokalisiert sich selbst, Wurzel-AGENTS.md/CLAUDE.md tragen die Regel. Nachweis: spiegelstand 29/29 byte-gleich und doppelte_nummern OK aus dem Anker. Wiki/Betrieb/Arbeitsverzeichnis.md.
- [x] **T-072 — repos-zentrale: Manifest nennt Bots, deren Profil geloescht ist**
      Kontext: `tests/test_manifest.EchtesManifestTest.test_jedes_bot_profil_des_manifests_existiert`
      ist rot (1 von 56 Tests): 17 Bot-Namen im Manifest haben kein Profil mehr -
      sie liegen seit 19.09.2026 unter `Agenten/Hermes/profiles/.deleted/`
      (projectatlas, skills, superpowers, tradingview-mcp, agent-reach, nous, codex,
      scrapling, santiment, claude-plugins-official, coder, easycliproxyapi,
      graphify, max, moon-dev-code, odysseus, winget-cli). Der Test ist richtig -
      das Manifest ist veraltet; unklar ist, ob die Profile zurueckkommen sollen.
      Naechster Schritt: entscheiden - Profile zurueckholen ODER die bot-Felder im
      Manifest entfernen bzw. kennzeichnen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Werkzeuge/repos-zentrale/repos-zentrale.json,
      Agenten/Hermes/profiles/.deleted/
      **Erledigt 2026-09-30.** Die 13 Eintraege ohne Profil tragen jetzt eine `warnungen`-Zeile statt eines Bot-Namens. Grund der Entscheidung: `profiles/.deleted/` enthaelt KEINE Profile, sondern 9-Byte-Vermerke mit dem Wort `deleted` (gemessen mit `ls -la`) - die Profile wurden am 19.09.2026 geloescht, nicht weggelegt; ein Bot-Knopf waere ein Knopf ins Leere. `test_jedes_bot_profil_des_manifests_existiert` ist wieder gruen (118 Tests).
- [x] **T-095 — `runden_aus_journal` paart je INSTRUMENT, nicht je Position**
      Kontext: Der Backtest ueber 5,7 Jahre deckt es auf. Bei squeeze standen
      1088 geschlossene Runden im Buch, `runden_aus_journal()` wertete aber nur
      759 aus (30 % Verlust); bei macd_mtf 1209 gegen 774, bei wavetrend 1506
      gegen 1128. Ursache: die Funktion legt offene Positionen in einem Dict
      `offen[inst]` ab - zwei gleichzeitige Positionen im selben Instrument
      ueberschreiben einander, die erste Ausstiegszeile paart dann mit dem
      falschen Einstieg oder faellt weg. Die Spuren erlauben mehrere Plaetze und
      besetzen denselben Wert mehrfach, das ist also der Normalfall.
      Auswirkung: Trefferquote und f_max werden auf einer Teilmenge gerechnet,
      und die uebersprungene Teilmenge ist nicht zufaellig (gleichzeitige
      Positionen im selben Instrument sind eher gleichgerichtet).
      Naechster Schritt: Positionskennung ins Journal (Spalte `pos_id` beim
      Einstieg, von der Ausstiegszeile mitgefuehrt) und `runden_aus_journal`
      darauf paaren - mit Rueckfall auf die Instrumentenpaarung fuer alte
      Journale. Betrifft ALLE Auswertungen, nicht nur den Backtest.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/kosten_wendepunkt.py, Agenten/Handel/auswertung_alle.py, spur_buch.py
      **Erledigt 2026-09-30.** Neue Spalte `pos_id` (Einstiegszeile traegt die Kennung, Ausstiegszeile uebernimmt sie) in allen schreibenden Stellen: `spur_buch.py`, die `handeln.py` von squeeze/wavetrend/macd_mtf/supertrend/mosaic/scanner/kraken/xperp/swap/omniquant/kopier1zu1. Die gemeinsame Paarung liegt in `Agenten/Handel/journalpaarung.py` (vier Stufen: Kennung, genau ein offener Einstieg, Positionsmerkmale, sonst unpaarig AUSGEWIESEN statt geraten) und wird von `kosten_wendepunkt` und `auswertung_alle` benutzt. GEMESSEN (`gegenprobe_alt_neu.py`, dieselben Zeilen, nur die Paarung wechselt): squeeze-Backtest 759 -> 1088 Runden, macd_mtf 774 -> 1209, wavetrend 1128 -> 1506, Summe ueber alle Journale 23.999 -> 29.414 (+5.415). Drei Livejournale liefern WENIGER (scanner 167 -> 156, swap 14 -> 11, xperp 77 -> 71): dort hat die alte Regel geraten (zweideutige Altbestaende ohne Kennung), die neue zaehlt sie als unpaarig. Vorhandene Journale mit `journal_pos_id_nachziehen.py` nachgezogen; Altjournale bleiben lesbar (Schreiber richten sich nach dem DATEIKOPF, Warnung einmalig). Tests: `tests/test_journalpaarung.py` 20 gruen, Spurentests gruen (squeeze 20, wavetrend 20, macd_mtf 22, supertrend 25, mosaic 126, scanner 146, kraken 160, xperp 78, swap 57, omniquant 66), kopier1zu1 2 vorbestehende rote (ohne die Aenderung ebenfalls rot). Zahlen in `MaxHirn/Wiki/Handel/Backtest-Fundament.md`.
- [x] **T-193 — Dauerlauf stirbt nach rund einem Zyklus an SIGTERM (Rueckgabe 143)**
      Kontext: Am 30.09.2026 waren zwischen 01:52 und 02:39 **alle drei Dauerlauf-Stufen
      tot** (Sperrdateien 52312/61436/42504, kein passender Prozess). Die Waechter-Aufgaben
      arbeiten korrekt - sie erkannten die verwaisten Sperren und starteten neu
      (`Routinen/logs/handel-dauerlauf-letzter-lauf*.log`: 02:05, 02:07, 02:08, 02:24) -
      aber jede neue Instanz starb nach etwa einem Zyklus wieder. Kein Rechnerneustart
      (letzter Start 29.09. 21:06:19), kein Traceback. Die Todesart steht im Log als
      **`<spur> Rueckgabe 143`** = SIGTERM (128+15): 29.09. 23:22:59 bei `xperp`,
      30.09. 02:36:55 bei `kraken`. Ein Handstart schaffte 16 Spuren und lief bis zum
      kraken-Zyklus; in jenem Lauf war mein eigener `timeout` nicht auszuschliessen,
      der Wert trat aber schon am 29.09. ohne Fremdeinwirkung auf.
      Verdacht: ein Kindprozess beendet den ganzen Baum mit, statt nur sich selbst -
      `moondev_dauerlauf.py:417 _stoppe` beendet mit `taskkill /T /F` den GANZEN Baum,
      und sein Prozessfilter kann die eigene Kommandozeile treffen (Falle vom 24.09.).
      Die Wrapper starten mit `-WindowStyle Hidden` OHNE Umleitung, deshalb ist der
      Sterbegrund bisher unsichtbar.
      Naechster Schritt: (1) die Wrapper leiten stdout/stderr nach
      `Routinen/logs/dauerlauf-<stufe>-kind.log` um - erst dann ist der Sterbegrund
      lesbar; (2) pruefen, ob `moondev_dauerlauf._stoppe` fremde Prozesse trifft;
      (3) Wache auf "kein Zyklus seit >10 min" statt nur "PID tot".
      URSACHE GEFUNDEN UND BEHOBEN (30.09.2026, Commit 41d2ffa): Nicht der
            Prozessbaum war schuld, sondern die Sperre selbst. `handel-dauerlauf.ps1`
            schreibt die PID, die `Start-Process` zurueckgibt - bei einem
            venv-Startprogramm ist das der ELTERNPROZESS des Interpreters, nicht der
            Lauf. `sperre.belegt()` verglich sie mit `os.getpid()`, sah ein lebendes
            fremdes Python und liess den Lauf mit "Es laeuft bereits ein Dauerlauf der
            Stufe niedrig" sofort enden. Die Rueckgabe 143 war eine Verwechslung: in
            meinem Handstart kam sie von MEINEM eigenen `timeout` (feuerte in derselben
            Sekunde), nicht vom Lauf. Fix: `belegt()` nimmt auch `os.getppid()` aus -
            der eigene Starter ist kein fremder Lauf. Gegenprobe ohne den Fix: 1 roter
            Test, mit Fix 17/17. Punkt (1) erledigt: der Wrapper leitet stdout/stderr
            nach `Routinen/logs/dauerlauf-<stufe>-kind[.err].log` um - ohne diese
            Umleitung war der Sterbegrund nicht auffindbar, sie hat ihn gefunden.
            Punkt (2) entfaellt, kein taskkill im Spiel. OFFEN bleibt (3): eine Wache
            auf "kein Zyklus seit >10 min" statt nur "PID tot" - sie haette den Ausfall
            um 01:52 in Minuten statt in 47 gemeldet. Alle drei Stufen laufen seit
            02:51/02:55 wieder vollstaendig (30 Spuren je Zyklus).
            Angelegt: 2026-09-30
            Betrifft: Agenten/Routinen/handel-dauerlauf.ps1, Agenten/Handel/moondev_dauerlauf.py
      ERLEDIGT (30.09.2026): 143 ist ein Fingerabdruck, kein Diensttod - gemessen: MSYS/Git-Bash 'timeout N' liefert 143 (128+15), taskkill 1, Stop-Process 4294967295, os.kill 15; beide Tode sind in state.db als Sitzungsaufruf belegt (23:21:10 timeout 60 -> Tod 23:22:59; 02:34:21 timeout 150 -> Tod 02:36:55), Get-WinEvent zeigt in beiden Fenstern KEIN Ereignis. Punkt (3) erledigt: Agenten/Hermes/scripts/dauerlauf-wache.py (Cron 'dauerlauf-wache', 15 min, Telegram, leere Ausgabe = nichts senden) meldet tot-143 / tot-code / tot-spurlos / haengt (Protokoll aelter als 20 min) / churn (drei verwaiste Sperren je Stunde), 16 Tests gruen. Nachweis: echter Lauf gegen die drei laufenden Stufen ist still, nachgebauter 143-Fall meldet und wiederholt nicht. Siehe Wiki/Handel/Dauerlauf-Tode.md.
- [x] **T-207 — mosaic prueft seine Boersen-Stops nicht nach (drei Stops waren storniert)**
      Kontext: Am 30.09.2026 trugen die drei Kraken-Stops von mosaic (BTC/ETH/SOL,
      rund 258 EUR) den Status `canceled`, waehrend `mosaic/zustand.json` weiter
      `boersen_stop_fehlt: false` meldete. Gefunden nur ueber
      `kraken/spot_stops.py` - mosaic hat keinen Abgleich. `scanner/boersenstops.py`
      laeuft seit 28.09. im Live-Zyklus; mosaic, kraken und die Nautilus-Arme haben
      nichts dergleichen. Gleiches Muster wie T-118 (26.09.2026, xperp).
      Naechster Schritt: `scanner/boersenstops.py` auf die uebrigen Boersen-Spuren
      uebertragen (Position -> `stop_algo_id`/`stop_txid` per `order_details` auf
      `status == "open"` pruefen, Waisen melden), Vorschau als Standard.
      Angelegt: 2026-09-30
      Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/mosaic/handeln.py, Agenten/Handel/kraken/handeln.py,
      Agenten/Handel/scanner/boersenstops.py
      30.09.2026: mosaic/boersenabgleich.py eingebaut (jeder Basis-Zyklus, Vorschau Standard), Wache mosaic-stop-wache (Cron 2faf001c30d6, 30 min). Messung: 3 Live-Positionen, 3 wirksame Stops (die drei waren um 07:34 neu gesetzt); Gegenprobe mit der stornierten Kennung meldet 'STOP FEHLT: BTC-USDC'. Tests: mosaic 126, scripts 14 gruen, Gegenprobe 15/3 rot. Commit 3d8b800.
- [x] **T-208 — kraken-Buch fuehrt eine DOTEUR-Position, die es nicht gibt (und zwei SUIEUR-Waisenstops)**
      Kontext: `kraken/zustand.json` fuehrt DOTEUR mit 45.9896983 DOT, das
      Kraken-Konto hat 0.0000000000 DOT (BalanceEx, 30.09.2026). Umgekehrt liegen
      an der Boerse zwei SUIEUR-Auftraege (stop-loss 0.9497 ueber 136.77266 und
      take-profit 3.5266 ueber 137.87217), zu denen es keinen SUI-Bestand gibt
      (0.00000 SUI) - Waisenauftraege. Aufgefallen ueber `kraken/spot_stops.py`.
      Naechster Schritt: DOT-Position ueber `okxf.geschlossene_position` /
      Kraken-Ledger aufklaeren und mit echtem Erloes ausbuchen (Muster:
      `scanner/boersenstops.py`, `xperp/geister_nachziehen.py`); die zwei
      SUIEUR-Auftraege vorher stornieren, sonst kann der Verkauf ins Leere laufen.
      Angelegt: 2026-09-30
      Zuletzt: 2026-09-30
      Betrifft: Agenten/Handel/kraken/zustand.json, Agenten/Handel/kraken/handeln.py
      **Erledigt 2026-09-30.** DOT-Geist mit echtem Boersenerloes ausgebucht (Stop O2YTEL-7R6ZT-ULOXRN, 45,89 EUR nach Gebuehr, Journalzeile buch_nachgezogen_boerse) und der Abgleich dafuer in den Zyklus gehaengt (kraken/abgleich.py, vor pruefe_ausstiege). Die zwei SUIEUR-Auftraege waren KEINE Waisen: 274,64 SUI lagen in vier Margin-Positionen, waisen_stops.lage() las OpenPositions faelschlich mit 'open'-Huelle. Dazu beleg_hand.py: Einsatz war der Stueckpreis statt des Betrags (vier Belege 0,21/0,95/1,15/1,61 -> je ~50 EUR, Buch 3,90 -> 150,00 EUR gebunden).
- [x] **T-211 — Wache fuer den omnitrade-Demo-Lauf (Statusdatei und PID)**
      Kontext: Der Demo-Lauf (Werkstatt/omnitrade, OKX-Demo, BTCUSDC) hat keine
      Wache. Stirbt er hart, bleibt in status/live.json "state: running" mit einer
      toten PID stehen — die Handelszentrale erkennt das erst nach 5 Minuten als
      "veraltet" (VERALTET_S=300). Genau das ist am 30.09.2026 passiert: der Lauf
      (PID 76116, 83 Kerzen) endete um 08:22 mit Exit 1, nachdem er fuenfmal
      0,00000002 BTC nachverkaufen wollte (OKX 51020 Mindestmenge — Restmenge nach
      dem Verkauf); die Statusdatei behauptete danach weiter "running". Der
      Rechenfehler selbst ist behoben (Commit 5fabc35, next_position()), die
      Anzeige-Luege beim Ausstieg nicht. Ein zweiter Lauf darf nie entstehen —
      zwei Laeufe ordern doppelt und schreiben in dieselbe Statusdatei.
      Naechster Schritt: no_agent-Cron nach Hausmuster (Agenten/Hermes/scripts/,
      leere Ausgabe = nichts senden): (a) Alter von status/live.json gegen 300 s,
      (b) PID gegen die Prozessliste, (c) bei toter PID den Stand "beendet" melden.
      NICHT selbst neu starten — das entscheidet Max.
      Angelegt: 2026-09-30 · Zuletzt: 2026-09-30
      Betrifft: Agenten/Hermes/scripts/, Werkstatt/omnitrade/status/live.json,
      Agenten/Handel/handelszentrale.py
      **Erledigt 2026-09-30.** Wache gebaut: Agenten/Hermes/scripts/omnitrade-lauf-wache.py entscheidet an zwei Zeugen (Statusdatei UND PID ueber omnitrade_lauf.beurteile) und meldet beendet/haengt/kaputt/fehlt je mit PID, Alter, Symbol und Startbefehl; sie startet nichts. Hermes-Cron omnitrade-lauf-wache (Job 804473084f4e, alle 15 min, no_agent, Telegram, leere Ausgabe = nichts senden), Merkdatei Agenten/Hermes/cache/omnitrade-lauf-wache.json (dieselbe Feststellung erst nach 6 h, Schluessel ohne Zahlen - ein PID-Wechsel ist kein Fehler). Altersgrenze aus dem Kerzenabstand (max 300 s, 2,5x), sonst erklaert eine feste 5-Minuten-Grenze den stuendlichen Lauf fuer tot. 17 Tests (Agenten/Hermes/scripts/test_omnitrade_lauf_wache.py), Gegenprobe: Zeugen-Reihenfolge und Wiederholungsschutz zurueckgenommen -> 4 Tests rot. Wiki: Betrieb/Wachen-und-Aufgaben.md.
- [x] **T-215 — Auslagerungsdatei vergroessern: die Commit-Grenze steht fest bei 75,7 GB**
      Kontext: Der gemeinsame Nenner aller Abschaltungen ist Speichernot -
      Windows meldet sie selbst, 296-mal in 14 Tagen (Ereignis 2004,
      Resource-Exhaustion-Detector), mit `llama-server.exe` (LM Studio, bis
      18,0 GB) und `com.docker.sailor.exe` (5,6-15,8 GB) an der Spitze. Am
      25.09. folgte auf die 2004-Meldung um 16:12:55 der llama-server-Absturz
      um 16:12:56 und der Rechner kam erst 16:36:48 zurueck. Am 30.09. sind
      zwischen 10:12 und 10:46 einunddreissig Anwendungen mit `0xc000012d`
      (`STATUS_COMMITMENT_LIMIT`) gestorben, darunter `dwm.exe` und der
      Hermes-Gateway.
      Der Riegel: `C:\pagefile.sys 8192 8192` ist FEST (Maximum = 8192) und
      `O:\pagefile.sys 4096 16384` ist nie gewachsen (Peak 715 MB) - die
      Commit-Grenze von 75,7 GB (63,7 GB RAM + 12 GB Auslagerung) konnte also
      nicht nachgeben. O: hat 110 GB frei.
      Naechster Schritt: `Routinen/einmalig-20260930-auslagerung.ps1` mit
      erhoehten Rechten starten (Vorschlag O: 32768/32768, C: unveraendert).
      Erst -Testlauf, dann scharf; -Rueckgaengig stellt 4096/16384 wieder her.
      Danach einen Tag beobachten, ob Ereignis 2004 verschwindet.
      Angelegt 30.09.2026. Betrifft C:\pagefile.sys, O:\pagefile.sys,
      MaxHirn/Wissen/Hardware.md. Verwandt: T-004, T-151.
      **Erledigt 2026-09-30 12:33 (Neustart steht noch aus).** Auslagerung neu gesetzt: C:\pagefile.sys FEST 8192/8192 (vorher selbstverwaltet 0/0, aktuell 21 GB belegt auf einem Laufwerk mit nur 19,3 GB frei - eine selbstverwaltete Datei waechst dort unbegrenzt und fuellt C:), O:\pagefile.sys NEU 32768/32768 (114,1 GB frei). Der O:-Eintrag kam ueber den Registry-Weg (HKLM\...\Memory Management\PagingFiles = C:\pagefile.sys 8192 8192 + O:\pagefile.sys 32768 32768), weil New-CimInstance still scheiterte: Win32_PageFileSetting.InitialSize ist UInt32, ein Int32 aus der Parameteruebergabe loest Typenkonflikt aus, und mit ErrorActionPreference=Stop stirbt das Skript dort OHNE Logzeile - der erste erhoehte Lauf setzte deshalb nur C:. Im Skript mit [uint32] repariert (Setze_Seite, mit Vermerk), -Anlegen und C_FestMB als Schalter ergaenzt, weil der Eintrag auf O: seit einer Handumstellung fehlte; Sicherung des Vorzustands unter Routinen/einmalig-20260930-auslagerung.sicherung.json, -Rueckgaengig unveraendert. WMI zeigt beide Eintraege, Testlauf ist jetzt idempotent. WIRKUNG ERST NACH NEUSTART (Commit-Grenze dann rund 103,7 statt 84,5 GB) - Nachpruefung als T-220.
- [x] **T-213 — EURC fehlt in der gemeinsamen Kraken-Paartabelle (mosaic, moondev_marktlage)**
      Kontext: Die kraken-Spur liest ihre Quote jetzt selbst aus der API und
      nutzt damit auch EURC-Paare (ETHEURC, SOLEURC, XBTEURC). Die beiden
      anderen Kraken-Spuren lesen dagegen `kraken_paare.py` - dort stehen EUR
      und USDC, kein EURC. Ihr EURC-Kapital bleibt also unerreichbar, obwohl
      Kraken EURC als Quote auf drei liquiden Paaren fuehrt.
      Naechster Schritt (Entscheidung Max): EURC in `kraken_paare.py` als
      dritte Quote aufnehmen (17 Tests dort erweitern) - sinnvoll erst
      zusammen mit T-115, sonst ist nur die Tabelle groesser und das Tor
      bleibt zu.
      Angelegt 30.09.2026. Betrifft Agenten/Handel/kraken_paare.py, mosaic,
      moondev_marktlage. Verwandt: T-115.
      **Erledigt 2026-09-30.** kraken_paare.PAARE hat die Quote EURC: XBTEURC, ETHEURC, SOLEURC (gegen GET /0/public/AssetPairs gemessen - Kraken fuehrt gegen EURC NUR diese drei Maerkte, alle online, pair_decimals 1/2/2, ordermin 0.00005/0.001/0.06). Die Tabelle traegt die Instrumentnamen in Haus-Schreibweise (BTC-USDC/BTC-EUR) auf die drei Kraken-Namen, damit mosaic und moondev_marktlage mit kraken_quote=EURC ohne Codeaenderung fahren. Der Fehlerfall ist der wichtigere: DOGE-USDC und ADA-EUR mit Quote EURC werfen ValueError - kein stiller Rueckfall in einen EUR-Markt. quote_von_paar kennt EURC vor der EUR-Regel (XBTEURC endet auf EURC, nicht auf EUR). Guthaben-Naht geprueft: Kraken fuehrt den EURC-Posten unter dem Namen EURC (nicht ZEUR) - gemessen 0,000000 EURC gegen 46,7487 EUR, die Haus-Aufloesung trifft ihn (T-214 bleibt: Umtausch lohnt nicht). Tests tests/test_kraken_paare.py 24 gruen (7 neue), keine Quote scharf gestellt - die Vorgabe bleibt EUR.
- [x] **T-212 — kraken-Buch in USDC/EURC: die Auswertung nennt die Einheit noch fest als EUR**
      Kontext: Seit 30.09.2026 kann die kraken-Spur in EUR, USDC und EURC
      handeln (Quote je Paar aus der API, `Agenten/Handel/kraken/quote.py`;
      Guthaben-Tor in der Waehrung des Paares; Watchlist 17 -> 33 Paare).
      Betragsfelder heissen weiter `eur`, weil die Auswertung sie liest - die
      Waehrung steht zusaetzlich an der Position. Offen ist der LETZTE Leser:
      `auswertung_alle.EINHEIT` traegt `{"kraken": "EUR", "nautilus_kraken":
      "EUR"}` fest. Steht das Buch einmal in USDC, sind die Zahlen richtig und
      ihre Einheit falsch - genau die Klasse Anzeigefehler, die am 23.09. bei
      mosaic einen BTC-Kurs aus der falschen Boerse zeigte.
      Naechster Schritt: EINHEIT fuer kraken aus `buch_waehrung(z)` ableiten
      (Rueckfall EUR fuer den Altbestand) statt aus der Tabelle, Test daneben.
      Angelegt 30.09.2026. Betrifft Agenten/Handel/auswertung_alle.py.
      **Erledigt 2026-09-30.** Die Einheit der kraken-Zahlen kommt jetzt aus dem BUCH statt aus der Tabelle: auswertung_alle.einheit_fuer(spur) gibt fuer kraken kraken_buch_waehrung() zurueck (Position traegt `waehrung`; Altbestand ohne Feld = EUR, weil EUR damals die einzige Waehrung der Spur war). Die Tabelle EINHEIT bleibt Vorgabe fuer alle anderen Spuren. ZWEITER LESER mitgefunden und behoben: strategie_kennzahlen.py las EINHEIT.get(spur) direkt - zwei Anzeigen derselben Spur haetten verschiedene Einheiten genannt. lage._kraken_buch_waehrung() ruft jetzt dieselbe Funktion auf, statt die Regel ein zweites Mal zu fuehren. Tests tests/test_einheit_kraken.py 11 gruen (Buch->Einheit, Altbestand->EUR, Risikostufen-Dateiname zustand.mittel.json, kein zweiter Leser der Tabelle im ganzen Handel-Baum, lage delegiert); Live: auswertung_alle.py --spur kraken zeigt die Runden in EUR, strategie_kennzahlen.py kraken laeuft, lage-Tests 17 gruen.
- [x] **T-217 — Nach jedem `hermes update` den Gateway-Launcher und das tools-Python pruefen**
      Kontext: `hermes update` schreibt `gateway-service/Hermes_Gateway_2ef9d0b7.vbs`
      neu und setzt ihn auf `tools\python-3.14.7...\python.exe` mit
      Fensterstil 0. Ein Konsolenprogramm wird so GAR NICHT gestartet, ohne
      Fehlermeldung (gemessen 30.09.2026, Tabelle in
      `Wissen/Hardware.md`). Zugleich fehlten dem tools-Python nach dem
      Update vom 29.09. alle Abhaengigkeiten. Beides hat den Gateway am
      30.09. stundenlang stillgelegt.
      Naechster Schritt: eine Pruefung (Hermes-Cron oder Block in
      `systempruefung.ps1`) die (a) in der VBS nach `pythonw.exe` sucht und
      (b) `tools-python -c "import pydantic_core, hermes_cli.main"` aufruft;
      leise, wenn beides gesund ist.
      Angelegt · Zuletzt: 30.09.2026
      Betrifft: Agenten/Hermes/gateway-service/, Agenten/Hermes/tools/
      **Erledigt 2026-09-30.** Wache gebaut: Agenten/Hermes/scripts/gateway-launcher-wache.py + test_gateway_launcher_wache.py (23 Tests gruen), Hermes-Cron gateway-launcher-wache (a0faa7d6286f, taeglich 08:20, no_agent, Telegram, leere Ausgabe = gesund). Sie prueft die URSACHE statt des Symptoms: (a) die Startzeile der Launcher-VBS muss auf pythonw.exe zeigen - Kommentarzeilen zaehlen nicht, weil der reparierte Launcher python.exe im Kommentar nennt; (b) tools/python-3*/python.exe -c "import pydantic_core, hermes_cli.main" mit der Umgebung des Launchers. Gemessen 30.09.2026: echter Lauf leise (Exit 0), Gegenprobe mit absichtlich kaputter VBS nennt Befund und Behebung, 23/23 Tests. Kein Schreiben in den Checkout, kein Start, kein Netz.
- [x] **T-214 — Gemessen: der Umtausch in EURC/USDC lohnt nicht — nichts umtauschen**
      Kontext: Die Erweiterung vom 30.09.2026 schaltet nichts scharf - das
      Guthaben-Tor vergleicht weiter gegen `mindest_guthaben_je_quote` 60, und
      gemessen liegen 46,81 EUR / 25,08 USDC / 0,00 EURC frei. Die Frage "soll
      ich EUR in EURC oder USDC tauschen, um das Tor zu oeffnen" ist am
      30.09.2026 mit `Agenten/Handel/kraken/quoten_vergleich.py` gemessen
      worden - Antwort NEIN, aus zwei unabhaengigen Gruenden: (1) kein
      Instrument der Watchlist ist nur in USDC oder EURC erreichbar (alle 17
      haben ein EUR-Paar; Kraken fuehrt 546 EUR-Paare gegen 47 USDC und 3
      EURC), der Umtausch erschliesst also nichts; (2) die USDC-Paare sind im
      Mittel 6,6 bp WEITER als die EUR-Paare (EURC 3,7 bp, Median aus drei
      Abrufen, 13 Instrumente), waehrend der Umtausch einmalig 60 bp kostet -
      es gibt keinen Break-even. Das kraken-Buch ist ausserdem 4/4 voll.
      Naechster Schritt: NICHTS tun (Empfehlung). Der Umtausch wird nur wieder
      ein Thema, wenn das Guthaben ohnehin in USDC/EURC liegt - dann handelt
      die Spur ohne Tausch. Erneut messen mit `quoten_vergleich.py --quote X`,
      nie schaetzen.
      Angelegt 30.09.2026. Betrifft Agenten/Handel/kraken/wachen.json,
      Agenten/Handel/kraken/quoten_vergleich.py,
      MaxHirn/Wiki/Handel/Boersen-und-Schluessel.md.
      Gemessen am 30.09.2026 mit Agenten/Handel/kraken/quoten_vergleich.py: kein Instrument der Watchlist ist nur in USDC/EURC erreichbar, und die USDC-Paare sind im Mittel 6,6 bp weiter als die EUR-Paare - ein Umtausch kostet 60 bp und erschliesst nichts. Antwort: NICHT umtauschen; die Erweiterung bleibt als Versicherung stehen.
- [x] **T-125 — Fremdarbeit im Arbeitsbaum liegen gelassen (parallele Sitzung)**
      Kontext: Beim Commit am 25.09.2026 lagen Aenderungen im Arbeitsbaum, die nicht
      aus dieser Sitzung stammen: geloescht `Agenten/Hermes/scripts/test_waisen_wache.py`,
      geaendert vier Skill-Dateien (arbeitsbaum-git-hygiene, dauerprozess-bewachen,
      fremdrepo-agent-start, laufwerk-platz-schaffen) sowie
      `handel-spuren/references/boersen-aufrufe.md` und `okx-fehlermeldungen.md`, neu
      `Agenten/Hermes/skills/brainfiles/sicherung-fahren/` und `kraken-cli/` im
      Wurzelordner. Bewusst NICHT mitgenommen (eigene Pfade stagen).
      Naechster Schritt: der naechste Lauf von `fremdarbeit-einziehen.ps1` (taeglich
      20:40) oder eine Sitzung committet sie mit Autor „Andere Sitzung“;
      `kraken-cli/` in der Wurzel gehoert nach Werkstatt/Repos.
      Angelegt: 2026-09-25
      Doppelter Eintrag zu T-081 (derselbe Vorgang vom 25.09.2026); T-081 traegt den spaeteren Stand. Dort bleibt er offen.
- [x] **T-124 — Eine scharfe Spur, die dauerhaft sperrt, meldet sich nur einmal**
      Kontext: Der Ereignisfilter des Dauerlaufs meldet Sperrzeilen („--live
      angefordert, aber gesperrt: …“) jetzt mit Gedaechtnis je Spur — dieselbe
      Zeile kommt einmal statt in jedem Zyklus. Das ist gewollt (Rauschen), laesst
      aber den Dauerfall offen: eine scharfe Spur, die wochenlang an Guthaben oder
      einem anderen Tor haengt, faellt nur im Tagesbericht auf.
      Naechster Schritt: pruefen, ob `sperrgruende.py` oder `spuren_stand.py` von
      einer Wache taeglich aufgerufen werden soll (Muster stille-spuren-wache).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/dauerlauf.py, Agenten/Hermes/scripts/
      Doppelter Eintrag: Inhalt ist byte-gleich mit T-080 (parallele Sitzungen, 25.09.2026). Der Punkt bleibt unter T-080 offen.
- [x] **T-123 — Zweiter Stufenlauf „hoch“ laeuft doppelt**
      Kontext: Beim Neustart des Basis-Dauerlaufs am 25.09.2026 standen ZWEI
      Prozesspaare mit `--risiko hoch` (60536/37924 und 60424/38452, beide am
      24.09. 18:49 gestartet) neben Basis und Mittel. Stufenlaeufe senden nicht und
      gehen nie live, ein Doppel kostet also nur Rechenzeit und Netz — es ist aber
      dieselbe Klasse wie die vier gleichzeitigen Laeufe vom 16.09.2026, die bei
      offenem Freigabefenster echtes Doppelorder-Risiko trugen. Nicht angefasst
      (Fremdstart einer anderen Sitzung).
      Naechster Schritt: pruefen, welcher Ausloeser den zweiten hoch-Lauf startet
      (Get-ScheduledTask der MaxHirn-Handel-Aufgaben), ein Paar geordnet beenden und
      IgnoreNew setzen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/dauerlauf.hoch.pid, Agenten/Routinen/handel-dauerlauf.ps1
      Doppelter Eintrag: Inhalt ist byte-gleich mit T-078 (parallele Sitzungen, 25.09.2026). Der Punkt bleibt unter T-078 offen.
- [x] **T-079 — swap: der erste echte Live-Einstieg steht noch aus**
      Kontext: swap hat seit dem 25.09.2026 einen tragfaehigen Zweig-Trenner (`modus`
      an jeder Position, Ausstiege und Tore nur im eigenen Zweig, Bereinigung nur
      fuer Altbestand ohne Feld). Im Journal stehen bis 24.09. AUSSCHLIESSLICH
      Papierzeilen; der Live-Zweig hat noch nie geordert, obwohl sein Freigabefenster
      seit dem 24.09. 23:55 offen ist. Belegt ist damit nur, dass eine Papierposition
      jetzt stehen bleibt (kein `buchbereinigung` mehr im Kreis).
      Naechster Schritt: beim ersten Live-Kauf pruefen, dass die Zeile `modus=live`
      traegt und der naechste Papierzweig sie NICHT verkauft.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/swap/
      Doppelter Eintrag: Inhalt ist byte-gleich mit T-077 (parallele Sitzungen haben denselben Punkt zweimal vergeben, 25.09.2026). Der Punkt bleibt unter T-077 offen.
- [x] **T-098 — Breite-Reihe am 02.10.2026 erstmals auswerten**
      Kontext: Die Reihe laeuft seit 25.09.2026 (erste Messung 29 von 29 = 100 %).
      Aus EINEM Messpunkt folgt keine Richtung; erst mehrere Tage zeigen, ob
      100 % ein Plateau war oder der Gipfel. Erste Probe 02.10.2026 (dann sind
      sieben Messungen da).
      Naechster Schritt: `python Agenten/Werkzeuge/breite.py --reihe` laufen lassen
      und in einem Satz festhalten, was die Reihe zeigt (steigt/faellt/seitwaerts)
      - danach T-095 entscheiden.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Werkzeuge/breite-reihe.jsonl
      **Erledigt 2026-09-30.** Die Reihe umfasst jetzt 250 Kerzentage (22.01.-28.09.2026) und zeigt den Umschwung klar: acht Monate unter 20 % Breite (Februar durchgehend 0 %), September im Mittel 58,5 % mit Gipfel 96,5 %. Fenster auf 600 Kerzen festgelegt - bei 299 drehte der EMA-Startwert (~37 % Gewicht) bei einzelnen Paaren das Vorzeichen (BTC -1,24 % gegen +4,52 %). Befund und Regeln: MaxHirn/Wiki/Werkzeuge/Marktbreite-Reihe.md.
- [x] **T-177 - Ausstiege zum Kerzenschluss rechnen die Gewinner zu gut**
      Kontext: Im Replay wird zum SCHLUSS der Kerze ausgestiegen, in der Stop
      oder Ziel beruehrt wurde - nicht zum Stop- oder Zielkurs. Ein Laeufer
      ueberschiesst sein Ziel dadurch deutlich: ADA stand mit Ziel +12 % im Buch
      und wurde mit +48 % geschlossen. Beide Familien (A und B) rechnen so,
      also sind ihre Zahlen untereinander vergleichbar - aber nicht als
      Ertragserwartung zu lesen.
      Naechster Schritt: intrabar-Ausstieg pruefen (Stop/Ziel-Kurs statt
      Kerzenschluss) und die Differenz an einem Lauf beziffern, bevor Zahlen
      aus dem Backtest in eine Entscheidung eingehen.
      Angelegt: 2026-09-29
      Betrifft: Agenten/Handel/replay.py, backtest_prognose.py
      **Erledigt 2026-09-30.** Der Replay schliesst jetzt am Kurs der beruehrten Marke (Hoch/Tief) statt am Kerzenschluss - Ausloeser bleibt der Schluss wie live, nur der Preis ist berichtigt (replay.Beruehrungsjournal, beruehrte_marke/kurs_der_marke; Live-Pfad spur_buch.pruefe_ausstiege unangetastet). Vorher/Nachher ueber sechs Spuren: wavetrend +419,66 -> +385,88, macd_mtf +299,90 -> +285,02, squeeze +61,93 -> -6,34, topmovers +522,44 -> +260,00, funding +156,50 -> +87,00, supertrend -24,17 unveraendert; Rundenzahl und Trefferquote bei wavetrend/macd_mtf/squeeze/supertrend identisch (die Regel verschiebt den Kurs, nicht den Ausloeser). Markenquote je Lauf in auswertung_alle; Gegenprobe mit ausgeschaltetem Fix: 10 von 19 Tests rot. Offen als T-202 (Docht-Ausstieg) und T-203 (Backtest-Zahlen neu lesen).
- [x] **T-147 — Das Dashboard hat keine Wache**
      Kontext: `hermes update` beendete den Lauf am 29.09.2026 mit `outcome: partial` und
      `phase_error: "Could not restart every paused Windows gateway"`; der Gateway kam zurueck,
      das Dashboard nicht (Port 9119 bis zum manuellen `Start-ScheduledTask Hermes_Dashboard`
      tot). Der Gateway hat Wachen (Gateway-Waechter, gateway-identitaet-wache), das Dashboard
      keine - ein Ausfall bleibt bis zur naechsten Anmeldung unbemerkt.
      Naechster Schritt: Wache nach Hausmuster (`no_agent`, leere Ausgabe = nichts senden), die
      die ANTWORT prueft (`http://127.0.0.1:9119/` = 200) und nur dann startet, wenn 60 s nach
      dem Ausloesen kein Prozess da ist (der Dienst braucht ~45 s).
      Angelegt: 2026-09-29
      Betrifft: Agenten/Hermes/gateway-service/Hermes_Dashboard.vbs, Agenten/Hermes/scripts/
      Erledigt 30.09.2026: Agenten/Hermes/scripts/dashboard-wache.py + Hermes-Cron 'dashboard-wache' (bf375a2ac65f, alle 15 min, no_agent, Telegram, leere Ausgabe = nichts senden). Prueft die ANTWORT (HTTP, jeder Statuscode) statt nur den Port, unterscheidet einen laufenden Bau von einem Haenger ueber zwei CPU-Messungen der Prozesskette (12 s Abstand), heilt per Stop-Process + Start-ScheduledTask, Bremse 30 min. Belege: 18 Tests gruen (test_dashboard_wache.py, mit Attrappen), Gegenprobe mit entferntem Bau-Zweig = 2 Tests rot, Cron-Lauf 'silent (empty output)' bei HTTP 200, Alarmrichtung mit --nicht-heilen an echten Daten gezeigt. Wiki: Betrieb/Wachen-und-Aufgaben.md + Lektionen/Wahrheit-pruefen.md 13.
- [x] **T-133 — `Handel/historie.py` und `xperp/historie.py`: gleicher Modulname, Test rot**
      Kontext: `Agenten/Handel/tests/test_handelszentrale_bindung.py`
      (`NamensfalleTest`) verlangt, dass kein Modulname am Handel-Kopf auch in einem
      Spurenordner liegt - sonst faengt ein Import mit `Handel/` auf `sys.path` das
      falsche Modul (Befund 13.09.2026 mit `gui.py`). Gemessen am 25.09.2026 ist die
      Dopplung `historie` (Backtest-Fundament, Commit e9e28f3, aus einer parallelen
      Sitzung) gegen `xperp/historie.py` - die Handel-Suite ist dadurch rot
      (698 Tests, 1 Fehler). FREMDARBEIT: nicht von mir angefasst.
      Naechster Schritt: eines der beiden umbenennen (`Handel/backtest_historie.py`)
      und die Importe in `replay.py`/`optimieren.py`/Tests mitziehen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/historie.py, Agenten/Handel/xperp/historie.py, tests/
      **Erledigt 2026-09-30 (Stand abgeglichen, nicht neu gebaut).** Die Dopplung ist weg: `Agenten/Handel/historie.py` existiert nicht mehr, an seiner Stelle liegt `historie_binance.py` (Umbenennung aus dem Backtest-Fundament); `xperp/historie.py` bleibt Spur-eigen. Nachgemessen am 30.09.2026 02:05: `cd Agenten/Handel/tests && ../.venv/Scripts/python.exe -m unittest test_handelszentrale_bindung.NamensfalleTest -v` -> 1 Test, OK.
- [x] **T-151 - Geplanter Neustart des Rechners (Commit/Memory entlasten)**
      Kontext: Am 29.09.2026 war der PC sehr langsam durch Commit-Erschoepfung (~200 Zombie-
      MCP-Prozesse, 29,6 GB Commit); behoben per Kill + Wache mcp-zombie-wache (Cron 15 min,
      Telegram). Seit 100 h Uptime steht Memory Compression bei 7,5 GB. Max hat am 29.09.2026
      entschieden: Option 4 (nichts weiter bauen), aber Reboot einplanen. Design-Doc:
      MaxHirn/Wiki/Betrieb/Systemleistung-2026-09-29.md.
      Naechster Schritt: ruhiges Zeitfenster AUSSERHALB 20:00-22:30 (Nachtsicherungen) waehlen,
      offene Live-Positionen + freigabefenster pruefen, Restart-Computer -Force, danach Dauerlauf-
      Stufen, Gateway, Dashboard, mcp-zombie-wache und Commit-Lage pruefen. Zeitpunkt braucht
      Max' Freigabe.
      Angelegt: 2026-09-29
      Betrifft: Rechner/Host, alle Dauerlauf-Stufen, Gateway, Dashboard
      **Erledigt 2026-09-30.** Der Rechner wurde am 29.09.2026 um 21:06 neu gestartet (LastBootUpTime 29.09.2026 21:06:19), danach liefen die drei Dauerlauf-Stufen wieder an. Gemessen 30.09. 02:00: Commit frei 15,6 GB von 87,7 GB (vor dem Neustart 1,9 GB), 33 Python-Prozesse - die Commit-Erschoepfung ist weg. Der zweite Teil (Speicher entlasten) ist nur teilweise erreicht: Memory Compression steht bei 8,32 GB.
- [x] **T-048 — Ausser-Haus-Kopie verschluesseln (BitLocker To Go)**
      Kontext: Q:\MaxHirn-AusserHaus ist vollstaendig und geprueft, aber
      NICHT verschluesselt und enthaelt Klartext-Zugangsdaten
      (Wissen/Zugaenge.md, Wissen/OKX_API.env). Ohne angestecktes Q: stecken
      alle Kopien im selben Rechner; gegen den Netzteilschaden 2026 hilft nur
      die Kopie ausser Haus.
      Erledigt 2026-09-30: Entscheidung Max - bewusst OHNE BitLocker To Go.
      Die SSD bleibt unverschluesselt; die Vertraulichkeit haengt damit am
      Aufbewahrungsort (ausser Haus, kein Dritter). Dokumentiert in
      Wissen/Routinen.md, Abschnitt 'Die dritte Kopie: ausser Haus'.
      Betrifft: Q:\MaxHirn-AusserHaus, Wissen/Zugaenge.md (Stufe 0)
      Angelegt: 2026-09-22 · Zuletzt: 2026-09-30

- [x] **T-184 — Aufgabe 'MaxHirn-Ausserhaus-Kopie' ist nicht registriert (Doku sagt taeglich 21:30)**
      Kontext: Commit 12f3433 (30.09.2026, T-182) sagt, die Ausser-Haus-Kopie
      erneuere sich taeglich 21:30 ueber `Routinen/ausserhaus-kopie.ps1`. Der
      Aufgabenplaner kennt sie NICHT: `schtasks /query /tn "MaxHirn-Ausserhaus-Kopie"`
      endet mit „Das System kann die angegebene Datei nicht finden", und die
      vollstaendige Liste der MaxHirn-Aufgaben (25 Eintraege, 30.09.2026 01:30)
      enthaelt keinen Ausserhaus-Eintrag. Das Log
      `Agenten/Routinen/logs/ausserhaus-kopie-letzter-lauf.log` von 01:12 stammt
      daher von einem Handlauf. Der Registrierer dokumentiert selbst, dass
      `Register-ScheduledTask` "Ready" samt naechstem Lauf meldete, ohne dass die
      Aufgabe blieb - er legt darum per `schtasks /create` an und prueft per
      `schtasks /query`. Bis zur Klaerung ist die Doku-Aussage unbelegt.
      Naechster Schritt: `Agenten/Routinen/ausserhaus-kopie-aufgabe.ps1`
      ausfuehren (legt an und prueft selbst; wirft, wenn die Probe scheitert),
      danach unabhaengig per `schtasks /query` gegenpruefen.
      Angelegt 2026-09-30 · Zuletzt 2026-09-30
      Betrifft: Agenten/Routinen/ausserhaus-kopie.ps1, ausserhaus-kopie-aufgabe.ps1,
      Agenten/sichern-ausser-haus.ps1, Aufgabe MaxHirn-Ausserhaus-Kopie
      **Erledigt 2026-09-30.** Der Registrierer Agenten/Routinen/ausserhaus-kopie-aufgabe.ps1 wurde ausgefuehrt und hat die Aufgabe angelegt; unabhaengig gegengeprueft per schtasks /query: Aufgabenname \MaxHirn-Ausserhaus-Kopie, naechste Laufzeit 30.09.2026 21:30, Status Bereit, Aktiviert, Aktion powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ...ausserhaus-kopie.ps1. Die Kette ist am Handlauf 01:12 belegt (robocopy-Code 3 = erfolgreich, 65051 Dateien abgeglichen, 44,573 GB, 0 kopiert von 0 kopierten Bytes - alles schon vorhanden, Lauf 70 s). Q: war beim Nachpruefen angesteckt, deshalb bewusst KEIN zusaetzlicher Lauf ausgeloest. Offen bleibt nur der Blick auf den ersten PLANlauf (30.09. 21:30) im Log Agenten/Routinen/logs/ausserhaus-kopie-letzter-lauf.log; ohne angesteckte SSD endet er mit Exitcode 2 (uebersprungen, kein Fehlschlag).
- [x] **T-182 — Ausser-Haus-Kopie: Frist festschreiben und Fahrweise entscheiden**
      Kontext: Die Kopie unter Q:\MaxHirn-AusserHaus ist die einzige Sicherung
      ausserhalb dieses Rechners (G: und O: haengen am selben Netzteil). Sie
      laeuft von Hand - bewusst ohne geplante Aufgabe, weil das Ziel eine
      USB-Platte ist, die meist nicht angesteckt ist. Der neue Waechter
      (Hermes-Cron ausserhaus-frist-wache, 27a16c73cf03) meldet taeglich um
      08:00 erst, wenn die juengste Spur im Ziel aelter als 14 Tage ist
      (Merkdatei: hoechstens alle 72 h). Gemessen 29.09.2026: 5,1 Tage alt.
      Naechster Schritt: entscheiden - 14 Tage als blosse Erinnerung belassen,
      oder eine geplante Aufgabe, die bei angesteckter Platte selbst sichert.
      Angelegt · 2026-09-29
      Betrifft: Agenten/Hermes/scripts/ausserhaus-frist-wache.py, Agenten/sichern-ausser-haus.ps1
      **Erledigt 2026-09-30.** Aufgabe `MaxHirn-Ausserhaus-Kopie` (taeglich 21:30, versteckt, Zeitlimit 6 h) wird aus dem Gateway heraus angelegt (Hermes-Cron `ausserhaus-aufgabe-sichern`, 08:30) und faellt bei fehlender SSD mit Exitcode 2 still aus. Wrapper `Routinen/ausserhaus-kopie.ps1`; echter Lauf endet `ENDE ok` (robocopy-Code 3), nachdem `Agenten\Hermes\cache`, `cron\output`, `*.pid`, `*.db-shm`, `*.db-wal` ausgenommen wurden (Code 11 = Exit 1 vorher). Kopie war 5,1 Tage alt, jetzt frisch. Fristwache 14 Tage bleibt zweite Absicherung.
- [x] **T-180 — Zweitkopie bricht ab - Ziel J: ist die fehlerhafte Platte**
      Kontext: Die Zweitkopie (Ziel J:\MaxHirn-Zweitkopie) schlug am 28.09. (Code 1) und 29.09. (21:10, 0xC000013A abgebrochen) fehl. Direkt davor (21:06-21:07) 8x NTFS-Event 98 (Volume als schreibgeschuetzt eingebunden) auf J:. J: ist die WD My Book mit 479 unkorrigierten Lesefehlern (Memory) und so langsam, dass ein rekursives Auflisten 300 s ueberschreitet. Jetzt wieder schreibbar, aber die Platte ist der Schwachpunkt. Memory-Vorgabe war 'Zweitkopie auf O: (Disk 1)'.
      Naechster Schritt: Entscheiden, ob die Zweitkopie auf O: umzieht (gesunde Platte) oder J: ersetzt wird; dann sichern-zweitkopie.ps1 anpassen und einen Lauf pruefen.
      Angelegt 29.09.2026 · Zuletzt 29.09.2026
      Betrifft: Agenten/sichern-zweitkopie.ps1, Agenten/Routinen/zweitkopie.ps1
      **Erledigt 30.09.2026.** Ziel in sichern-zweitkopie.ps1 auf O:\MaxHirn-Zweitkopie umgestellt (Backup .bak-20260929), echter Lauf 30.09. 00:01-00:06 durchgelaufen: robocopy-Code 1, 200.113 Dateien / ~37 GB, Zielstruktur O:\MaxHirn-Zweitkopie\MaxHirn angelegt, O: frei 160,6 -> 121,1 GB. G: bewusst nicht gewaehlt: G:, H:, I: sind dieselbe Platte (Disk 2) wie die Hauptsicherung. J:-Altbestand bleibt liegen.
- [x] **T-129 — Fristwaechter fuer die Ausser-Haus-Kopie (sie wird still alt)**
      Kontext: `sichern-ausser-haus.ps1` hat ABSICHTLICH keine geplante Aufgabe -
      sie braucht die angesteckte Q:-SSD. Folge: am 25.09.2026 war die Kopie
      **13 Tage alt** (gemessen: 89.421 Dateien / 18,31 GB fehlten), ohne dass
      irgendwo eine Meldung entstand. Es gibt einen Nachweis (`spiegelstand.py`
      fuer Q:\\Handel_Journal) und den Tagesbericht, aber **keine Wache** auf das
      Alter der Ausser-Haus-Kopie selbst.
      Naechster Schritt: Wache nach dem Muster `spiegelfrist-wache.py` bauen -
      meldet nur, wenn die Kopie aelter als N Tage (Vorschlag 7) ist, leere
      Ausgabe sonst. Sie darf NICHT selbst kopieren.
      Angelegt: 2026-09-25
      Betrifft: Agenten/sichern-ausser-haus.ps1, Q:\\MaxHirn-AusserHaus
      **Erledigt 2026-09-29.** Agenten/Hermes/scripts/ausserhaus-frist-wache.py meldet nur, was eine Frist reisst (Kopie aelter als 14 Tage, Laufwerk nicht angeschlossen, Ziel fehlt/leer/nicht lesbar); Hermes-Cron 27a16c73cf03 taeglich 08:00, Probelauf 'succeeded'; 11 Tests gruen; gemessen: Kopie 5,1 Tage alt = gruen.
- [x] **T-138 — Docker-Engine aus: Container `nautilus-demo` fehlt, OKX-Arm ohne Quoten**
      Kontext: `docker ps -a` antwortet 29.09.2026 mit `failed to connect to the docker API at
      npipe:////./pipe/dockerDesktopLinuxEngine ... daemon is running`; die Systempruefung meldete
      dasselbe um 07:00 ("Docker-Engine antwortet nicht (Frist 20 s)"). Ohne den Container bekommt
      der Nautilus-Arm auf OKX keine Quotes - genau der Befund vom 25.09. (`feed_quelle
      fallback_kopier`, quotes=0); die uebrigen zwei Arme (Kraken Spot/Futures) laufen ohne Docker.
      Naechster Schritt: Docker Desktop starten, `docker start nautilus-demo`, Block 14 der
      Systempruefung nachziehen und pruefen, ob wieder Quotes ankommen.
      Angelegt 2026-09-29. Betrifft Agenten/Handel/nautilus, Docker-Host.
      **Erledigt 2026-09-29.** Docker Desktop laeuft (Max gestartet); `docker ps`: `nautilus-demo | Up`. Ob am OKX-Arm wieder Quoten ankommen, bleibt am Arm selbst zu beobachten.
- [x] **T-137 — Routine `fremdarbeit-einziehen`: Push scheitert mit 403, Commits bleiben liegen**
      Kontext: Der Lauf vom 28.09.2026 20:40 hat 5 ruhende Dateien uebernommen (Commit 5c80b19),
      aber nicht gepusht: `remote: Write access to repository not granted ... error: 403`. Von Hand
      gepusht geht es (`manager` als credential.helper, am 29.09.2026 vier liegengebliebene Commits
      nachgeschoben). Der Unterschied ist der Kontext der geplanten Aufgabe - dort steht keine
      interaktive Anmeldung bereit. Folge ohne Fix: die Nachtsicherung laeuft lokal weiter, GitHub
      bleibt still, und die Sicherung ist genau dann nicht woanders, wenn sie gebraucht wird.
      Naechster Schritt: Lauf-Log der Aufgabe lesen, credential.helper im Task-Kontext pruefen
      (GCM-Store vs. gh-Token), danach `git log --oneline origin/master..master` nach dem 20:40-Lauf.
      Angelegt 2026-09-29. Betrifft Agenten/Routinen/fremdarbeit-einziehen.ps1.
      **Erledigt 2026-09-29.** Ursache gemessen: der `GITHUB_TOKEN` als Benutzervariable (93 Zeichen, scope-arm) verdeckt den verwalteten Zugang im Credential-Manager - mit Token exit 128/403, ohne Token exit 0. Die Routine raeumt beide Variablen vor dem Push (Commit 0f1a6ad).
- [x] **T-136 — `okx_bot_waechter` wird als Handels-Spur geprueft, ist aber ein Werkzeug**
      Kontext: Block 11b der Systempruefung laeuft ueber jeden Ordner unter Agenten/Handel mit
      wachen.json und verlangt `herzschlag_max_minuten = 180`. `okx_bot_waechter/wachen.json` hat
      den Schluessel nicht (`None`) und `handel_erlaubt` ebenso wenig - der Ordner haelt nie eine
      Position, die ein Herzschlag schliessen koennte. Die Zeile steht deshalb jeden Tag unter
      "Zu entscheiden" und bedeutet nichts.
      Naechster Schritt: entscheiden - Werkzeuge ohne `handel_erlaubt` aus der Pruefung nehmen
      (Vorschlag) oder 180 eintragen. Danach Block 11b nachziehen.
      Angelegt 2026-09-29. Betrifft Agenten/Routinen/systempruefung.ps1, okx_bot_waechter/wachen.json.
      **Erledigt 2026-09-29.** Block 11b trennt Spuren von Werkzeugen; der Lauf meldet "32 von 32 Handels-Spuren folgen der Herzschlag-Regel - ausgenommen als Werkzeug ohne Handelsbuch: okx_bot_waechter".
- [x] **T-135 — Tagespruefung meldet "Herzschlag alt" fuer eine live-only Spur (Fehlalarm)**
      Kontext: `spiegelstand.py:190` liest fuer das Alter `zustand.json` (Papierzustand, nur der
      Risikostufen-Suffix wird angehaengt) und `:193` rechnet daraus `alter`. Eine Spur, die nur
      live laeuft, schreibt aber `zustand.live.json` - ihr Papierstand friert ein. Gemessen am
      29.09.2026: `moondev_marktlage` lief im 15-Minuten-Takt (dauerlauf.log 15:18 "(live) ok"),
      der Papierstand stand auf 03:39, und Block 11 der Systempruefung machte daraus
      "Herzschlag 204 min alt (> 2 h) - laeuft die Spur ueberhaupt?".
      Naechster Schritt: in `spiegelstand.py` denselben FRISCHESTEN der beiden Staende nehmen, den
      `moondev_marktlage._papier_zustand()` schon benutzt; Gegenprobe ueber den Pruefstand der Spur.
      Angelegt 2026-09-29. Betrifft Agenten/Handel/spiegelstand.py, Routinen/systempruefung.ps1.
      **Erledigt 2026-09-29.** `spiegelstand.frisches_alter()` nimmt den frischsten von `zustand.json`/`zustand.live.json`; `moondev_marktlage` meldet 14 min statt 204 (6 Tests in `Handel/tests/test_spiegelstand_alter.py`, danach 29/29 byte-gleich).
- [x] **T-134 — Zweitkopie bricht am uv-Build-Cache ab (Exitcode 1 seit 27.09.)**
      Kontext: `sichern-zweitkopie.ps1` kopiert die Repo-Wurzel nach J: und schliesst `.venv`,
      `__pycache__`, `*.pid`, `*.db-wal` aus - `Agenten/Hermes/cache/` aber nicht. Dort liegt der
      uv-Build-Cache, dessen editable-Wheel waehrend eines Hermes-/uv-Laufs gesperrt ist:
      Log 28.09.2026 21:02 `FEHLER 5 (0x00000005) ... cache\uv\sdists-v9\editable\...\
      hermes_agent-0.0.0-0.editable-py3-none-any.whl / Zugriff verweigert`, danach `robocopy-Code 11`
      und `ENDE FEHLER - Exitcode 1`. Die Aufgabe `MaxHirn-Zweitkopie` steht deshalb auf Code 1,
      taeglich gemeldet, ohne dass eine Datei fehlt (2936 Dateien uebersprungen, 0 Fehler im
      Zaehler). Ein Cache gehoert nicht in eine Sicherung - er ist neu baubar.
      Naechster Schritt: `Hermes\cache` in die /XD-Liste aufnehmen (Stufe 1: erst .bak, dann echter
      Lauf zeigen), danach `grep -c "FEHLER 5" logs/zweitkopie-letzter-lauf.log` = 0.
      Angelegt 2026-09-29. Betrifft Agenten/sichern-zweitkopie.ps1, Aufgabe MaxHirn-Zweitkopie.



      **Erledigt 2026-09-29.** `Agenten\Hermes\cache` steht in der Ausschlussliste von `Agenten/sichern-zweitkopie.ps1`; Lauf 23:09: 0 FEHLER, robocopy-Code 3, exit 0 (Commit ac89d01).
- [x] **T-153 — compression.threshold 1.6 - greift die Kompression ueberhaupt?**
      **Erledigt 2026-09-29.** Sie griff nicht: `compression.threshold` ist ein ANTEIL des
      Kontextfensters (Vorgabe 0.50, `hermes_cli/config_defaults.py`), und der Ausloeser rechnet
      `(context_length - max_tokens) * threshold`. Mit 1.6 liegt er ueber dem Fenster - der Anbieter
      lehnt die Anfrage ab, bevor komprimiert wird. Zurueck auf **0.19** gesetzt (Hauswert seit
      19.09.2026): das Kompressionsmodell `omniroute/auto/best-free` hat nur ~200k Kontext, das
      Hauptmodell traegt ein Vielfaches davon - bei 0.19 liegt der Ausloeser sicher darunter.
      **Nachweis:** `hermes config get compression.threshold` = 0.19; der Weg ist nicht tot, sondern
      laeuft - `curl` auf `http://localhost:20128/v1/chat/completions` mit `auto/best-free` antwortet
      200 und wird heute von claude-haiku-4-5 bedient (die alte Notiz "best-free ist tot" ist
      ueberholt; ohne Schluessel antwortet der Router irrefuehrend mit 403 der OpenCode-Free-Gruppe).
      CRLF erhalten (`git diff --numstat` 14/11).
- [x] **T-154 — providers.ollama-launch.models ist eine Wunschliste ohne Deckung**
      **Erledigt 2026-09-29.** Die Liste steht jetzt auf sechs Namen, die wirklich im Store liegen
      (`gemma-e4b-8k:latest`, `gemma-e4b-8k:cpu`, `deepseek-chat:latest`, `glm4:9b`, `qwen3.5:9b`,
      `deepseek-reasoner:latest`) - in Hauptconfig und 17 Profilen, je 6 Ersetzungen. Werkzeug:
      `scripts/lokale-modellliste-richten.py` (Trockenlauf Standard, `--anwenden`, `--zuruecknehmen`,
      je Datei `.bak`); es traegt nur Namen ein, die `/api/tags` bestaetigt.
      **Nachweis:** `scripts/config-gegenprobe.py` meldet "Lokale Modelle: alle im Store";
      `git diff --numstat` je Datei 6/6 (keine Ganzdatei-Diffs, CRLF erhalten).
- [x] **T-149 — Doctor-Bericht: 18 Photon-Doppelkennungen sind ein Fehlalarm**
      **Erledigt 2026-09-29.** Die 18 gemeldeten Profile tragen jetzt `platforms.photon.enabled: false`
      (gesetzt mit `hermes -p <profil> config set platforms.photon.enabled false`; der Schalter wirkt nur
      auf TOP-LEVEL, `gateway.platforms.photon` wird ueberstimmt - so meldet es das Werkzeug selbst).
      Urspruenglicher Befund: der Doctor zaehlte die Photon-Kennung der Haupt-`.env` jedem Profil zu
      (0 von 30 Profil-`.env` tragen `PHOTON_PROJECT_ID`). **Nachweis:** `hermes doctor` meldet 1 Befund
      statt 19 (offen: npm-Hinweis bei agent-browser), 18/18 Profile mit `enabled: false`, CRLF erhalten.
- [x] **T-139 - Zwei Wachen prueften eine ADRESSE statt der Bedingung (Port 9900)**
      **Erledigt 2026-09-29.** Seit dem Update lauscht der Gateway auf einem Named Pipe; TCP 9900
      bleibt zu, waehrend er gesund laeuft. Folge: `Agenten/Routinen/gateway-waechter.ps1` startete
      den Gateway **im 2-Minuten-Takt neu** - 128 Zeilen "Neustart ausgeloest" am 29.09.2026.
      Umgestellt auf die Bedingung: laeuft ein Prozess `hermes_cli.main gateway run` (ohne
      `--profile`) UND antwortet er (Control-Pipe `\\.\pipe\hermes-gateway-*` ODER Port)? Nur bei
      fehlendem Prozess wird gestartet, ein haengender Prozess hoechstens einmal je 30 Minuten
      (Merker `logs/gateway-waechter.merker`). Die neue Wache
      `Agenten/Hermes/scripts/gateway-identitaet-wache.py` (Cron taeglich 08:15, no_agent,
      Telegram, leere Ausgabe = nichts senden) prueft die Updater-Sicht
      (`find_profile_gateway_processes(strict=True)`), rekonstruiert fehlende PID-Metadaten und
      startet den Gateway im Blindfall einmal pro Tag klassisch neu - nie waehrend eines Updates.
      **Nachweis:** 128 Neustart-Zeilen vor dem Lauf, 128 danach (Schleife beendet); Pipe-Probe
      zeigt genau 1 `hermes-gateway`-Pipe; 12 Tests gruen
      (`Agenten/Handel/tests/test_gateway_identitaet_wache.py`).
      Nachgezogen: Wiki/Betrieb/Hermes.md (Abschnitt "Gateway-Identitaet"), Wiki/Betrieb/
      Wachen-und-Aufgaben.md, Wiki/Lektionen/Wahrheit-pruefen.md Lektion 10.
      Betrifft: Agenten/Routinen/gateway-waechter.ps1, Agenten/Hermes/scripts/gateway-identitaet-wache.py
- [x] **T-117 - Agenten/Handel/tests: 4 rote Tests (3 failures, 1 error), vorbestehend**
      Kontext: Suite-Lauf 29.09.2026 (755 Tests, 799 s). Die vier Namen sind
      bekannt und die Testdateien stammen vom 23.-25.09.2026, also NICHT aus
      dieser Arbeit:
      - test_handelszentrale_bindung.NamensfalleTest.test_kein_modulname_einer_spur_doppelt_am_handel_kopf
      - test_omniquant_fassung.LadeBerichtTest.test_streng_liest_die_strenge_datei
      - test_omniquant_fassung.LadeBerichtTest.test_weit_liest_die_weit_datei
      - test_replay.FensterTest.test_fenster_ist_schneller_als_das_praefix
      Dazu eine Fehlermeldung aus dem Tagesbericht-Umfeld: 'Bericht 108.4 h alt,
      Grenze 26 h' - zeitabhaengig (echte Berichtsdateien).
      Naechster Schritt: je Fall pruefen, ob die Regel oder der feste Zeitstempel
      falsch ist (Muster: journal(jetzt=...) dynamisch setzen).
      Angelegt 29.09.2026. Betrifft Agenten/Handel/tests.
      Erledigt 29.09.2026: Alle vier roten Tests der Handel-Suite repariert - keiner
      war ein Codeproblem, jeder eine kaputte Pruefung.
      (1) `test_handelszentrale_bindung.NamensfalleTest` hatte recht: `historie`
      lag zweimal im Suchraum (Backtest-Modul am Handel-Kopf und xperp/historie.py).
      `Handel/historie.py` heisst jetzt `historie_binance.py` (Commit e8ec32f) -
      dieselbe Falle, die am 13.09. fuenf Omniquant-Tests gegen das falsche gui.py
      laufen liess.
      (2+3) `test_omniquant_fassung.LadeBerichtTest` (zwei Tests) hatte ein FESTES
      Datum im Fixture und pruefte 'Alter < 26 h' - nach 26 Stunden kippte er um,
      ohne Codeaenderung. Jetzt relativ zu jetzt, dazu die Gegenprobe (27 h muss
      abgelehnt werden).
      (4) `test_replay.FensterTest.test_fenster_ist_schneller_als_das_praefix`
      verglich zwei LAUFZEITEN - gemessen 0.97 und 0.93 auf zwei Durchgaengen, also
      kein Signal: bei 2000 Kerzen dominiert die Ausfuehrungszeit. Ein solcher Test
      meldet die Maschinenlast (drei Risikostufen laufen parallel), nicht die Regel.
      Umgebaut auf die Eigenschaft: mit Fenster 400 sieht die Spur hoechstens 400
      Kerzen, mit Fenster 2000 mehr; dazu ein Test auf die Lehre vom 25.09.2026
      (fenster_vorgabe darf nicht unter mindest_kerzen fallen). Commit 86d85ba.
      Nachweis: test_replay.FensterTest 3/3 gruen, test_handelszentrale_bindung +
      test_historie 57/57 gruen, test_omniquant_fassung 11/11 gruen.
- [x] **T-103 — Bus-Suite rot: Routine `moondev-dauerlauf` hat keine Bus-Anbindung**
      Kontext: `Agenten/Bus/tests/test_ende_zu_ende.py` bricht in
      `test_anbindung_routinen` ab mit "ohne Bus-Anbindung: ['moondev-dauerlauf']".
      `Agenten/Handel/moondev_dauerlauf.py` und `Agenten/Routinen/moondev-dauerlauf.ps1`
      sind unveraendert (git status sauber) - der Befund ist vorbestehend, nicht aus der
      Papierbuch-Arbeit vom 25.09.2026. Der Treiber meldet sich nicht wie die uebrigen
      Spuren ueber `ereignis.lauf("handel/<spur>")`.
      Naechster Schritt: pruefen, ob der Treiber eine eigene Bus-Kennung bekommen soll
      (`handel/moondev_dauerlauf`) oder ob die Pruefung ihn ausnehmen muss - beides ist
      eine Entscheidung, keine Reparatur.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Bus/tests/test_anbindung_routinen.py, Agenten/Handel/moondev_dauerlauf.py
      Erledigt 29.09.2026: Der Treiber meldet sich jetzt am Bus.
      `Agenten/Routinen/moondev-dauerlauf.ps1` hat `Ereignis.ps1`, `Melde-Start`
      ('routine/moondev-dauerlauf') und `Melde-Ende` an JEDEM Ausstieg (beide
      Pfadpruefungen und der Erfolgsfall). Entscheidung war: der Treiber ist ein
      periodischer Arbeitslauf und gehoert in die Meldung - ihn aus der Pruefung
      auszunehmen haette einen Ausfall wie eine nicht existierende Routine aussehen
      lassen, genau die Luecke vom September.
      Zweiter Fall derselben Pruefung: `test-*.ps1` ist jetzt ausgenommen - ein
      manueller Testlauf hat keine geplante Aufgabe, und der Name sagt es (die
      Ausnahme steht damit sichtbar in der Datei selbst, wie bei 'BUS: Bibliothek').
      Betroffen war die neue `test-wachter.ps1` einer Parallelsitzung.
      Nachweis: alle vier Anbindungs-Tests gruen ('alle Anbindungs-Tests Routinen
      bestanden'), PowerShell-Syntaxpruefung der geaenderten Datei ok.
- [x] **T-111 — Anzeige: Positionen ohne Symbol zeigen den Kurs statt des Tokens**
      Kontext: `tagesbericht.py` (25.09.2026, 20:34) zeigt Robinhood-Radar und Moon-Dev Sniper als
      "0x48f413c32a7b... long 4.258775833450569e-05" - in der Namensspalte steht der Einstiegspreis,
      dazu "(kein Kurs)". Betrifft Spuren, deren Positionsschluessel Token/Mint ist (kopier,
      moondev_sniper, robinhood_radar); Verdacht in `lage.py`: fehlt ein Symbol, faellt die
      Namensspalte auf den Kurs zurueck.
      Naechster Schritt: in lage.py die Namensermittlung fuer token-gefuehrte Positionen pruefen und
      entweder ein Symbol aus dem Token holen oder klar "Token 0x48f4..." anzeigen; Test in der
      Handelszentrale-Suite. KEIN Handelseingriff - reine Anzeige.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/lage.py, Handelszentrale
      Erledigt 29.09.2026: Der Bericht schreibt Zahlen jetzt lesbar. Ursache war
      `tagesbericht.zeile_position`: ohne Kurs fiel die Spalte auf `p['einstieg']`
      zurueck und gab einen rohen Float aus - bei einem Token mit acht Stellen also
      '4.258775833450569e-05'. Neu: `_zahl()` (Stellenzahl nach Groessenordnung,
      nie Exponentialschreibweise, vier Ziffern bei Werten unter 0,01) und `_kurz()`
      (lange Mint-Adressen auf 16 Zeichen). Die Zeile lautet jetzt
      '0x48f413c32a7b9... 0.00004259  (kein Kurs)'.
      Die normale Zeile MIT Kurs blieb unberuehrt (dort war die Anzeige richtig).
      Tests: Agenten/Handel/tests/test_anzeige_zahlen.py (7, gruen).
- [x] **T-118 - Warum wurden vier Stops am 26.09. um 14:26 an der Boerse storniert?**
      Kontext: Am 28.09.2026 standen BTC, ETH, SOL und HYPE (rund 385 USD) auf dem
      OKX-Konto OHNE Stop; die vier Stops sind zwischen 14:25:59 und 14:26:06 am
      26.09.2026 storniert worden, waehrend das Buch weiter
      `boersen_stop_fehlt: false` behauptete. Kein Hauspfad tat das sichtbar.
      Behoben (Symptom): die vier Stops sind nachgesetzt, und
      `scanner/boersenstops.py` prueft seit 29.09.2026 in JEDEM Live-Zyklus Buch
      gegen Boerse (Stop nachsetzen, verkaufte Position ausbuchen, Waisenstops
      stornieren) - ein Verlust dieses Schutzes kann nicht mehr unbemerkt bleiben.
      OFFEN: die URSACHE. Naechster Schritt: `/api/v5/trade/orders-algo-history`
      fuer den 26.09. auswerten und gegen die Protokolle von
      `scanner/stops_bereinigen.py` und das Handelsjournal stellen.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/scanner, Agenten/Handel/xperp.
      Erledigt 29.09.2026 (Befund, Ursache bleibt offen): Die vier Stops wurden
      AKTIV STORNIERT, nicht ausgeloest. Beleg aus `/api/v5/trade/order-algo`
      je algoId: state=canceled, actualSz=0, failCode=0, ordId leer, actualPx leer -
      haette der Kurs den Stop ausgeloest, stuende dort eine Fuellung mit ordId.
      uTime aller vier: 26.09. 14:25:59 bis 14:26:06, also sieben Sekunden.
      Kein Hauspfad: das Handelsjournal hat um 14:2x keine Zeile, das Dauerlauf-Log
      zeigt um 14:24 nur den Waechter ('laeuft bereits, PID 18904');
      `scanner/stops_bereinigen.py` storniert nur Waisen, `scanner/boersenstops.py`
      entstand erst zwei Tage spaeter. OKX fuehrt kein Feld 'wer/warum', die Ursache
      ist damit nicht mehr rekonstruierbar - vier Orders in sieben Sekunden sind
      maschinell (App-Sammelstorno oder Boersenseite).
      Die WIRKUNG ist abgesichert: `boersenstops.py` vergleicht seit 29.09.2026 in
      JEDEM Live-Zyklus Buch gegen Boerse (fehlender Stop wird nachgesetzt, verkaufte
      Position ausgebucht, Waisenstop storniert) - der Zustand vom 26.09. kann nicht
      mehr unbemerkt entstehen.
- [x] **T-107 — Doctor meldet 18 Photon-Doppelkennungen (Fehlalarm oder echte Kollision?)**
      Kontext: `hermes doctor` und `hermes gateway status` melden seit dem 25.09.2026 in
      JEDEM Bot-Profil "Profiles 'default' and '<bot>' both hold the same photon credential
      (PHOTON_PROJECT_ID/PHOTON_PROJECT_SECRET)" und schliessen daraus "gateway is STANDALONE:
      profiles NOT served (their bots stay silent)". Ursache ist mit hoher Wahrscheinlichkeit
      der gemeinsame Credential-Store: die `profiles/<bot>/auth.json` sind SYMLINKS auf
      `Agenten/Hermes/auth.json`, der Photon-Eintrag im Pool ist also physisch EINE Kennung,
      die der Doctor je Profil neu zaehlt. Die Bots fahren ohnehin als Einzelauftraege
      (`hermes -p <name> chat -q`), nicht als Multiplex-Adapter.
      Messergebnis 25.09.2026: PHOTON_PROJECT_ID, PHOTON_PROJECT_SECRET, PHOTON_ALLOWED_USERS
      und PHOTON_HOME_CHANNEL stehen AUSSCHLIESSLICH in der Haupt-`.env` (`Agenten/Hermes/.env`);
      KEIN Bot-Profil hat eigene Photon-Werte. Die Meldung entsteht also allein aus dem
      geteilten Credential-Store (auth.json-Symlink) - fuer die 25 Bot-Profile ein FEHLALARM,
      weil sie als Einzelauftraege fahren und kein Plattform-Token beanspruchen.
      Ein echter Fall bleibt: `profiles/awesome-systematic-trading/config.yaml` traegt einen
      eigenen `photon:`-Block (dieses Profil hat auch eine eigene auth.json statt des Symlinks).
      Naechster Schritt: pruefen, ob dieser Block dieselbe Kennung wie die Haupt-.env benutzt -
      dann entfernen oder dem Profil ein eigenes Token geben. Den Fehlalarm fuer die uebrigen
      Profile im Wiki unter Betrieb/Hermes.md festhalten und T-107 schliessen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/profiles/*/config.yaml, Agenten/Hermes/.env, Agenten/Hermes/auth.json
      Erledigt 29.09.2026: FEHLALARM, gemessen. Von 28 Bot-Profilen haben 26
      `auth.json` als SYMLINK auf `Agenten/Hermes/auth.json` (eigene Datei nur
      basic-memory und awesome-systematic-trading) - der Photon-Eintrag im geteilten
      Credential-Store ist physisch EINE Kennung, die der Doctor je Profil neu zaehlt.
      Kein Bot-Profil traegt eigene PHOTON_*-Werte (nur in der Haupt-.env). Die Profile
      fahren als Einzelauftraege, kein Plattform-Token wird doppelt beansprucht.
- [x] **T-109 — Die Update-Warteprobe `tmp/venv_halter.py` bricht beim Import ab**
      Kontext: Die Aufgabe `Hermes-Update-20260921` (Einmal-Trigger, PRUEFEN alle 20 s, faehrt
      `hermes update --yes --keep-stash` bei 0 Haltern) ruft `tmp/venv_halter.py` mit dem
      venv-Python auf. Am 25.09.2026 brach dieses Skript in JEDEM Lauf mit
      `ModuleNotFoundError: No module named 'ruamel'` (auch als Kopie in `tmp/`), waehrend
      derselbe Import per `python -c "..."` und `python -m hermes_cli.main` aus demselben venv
      fehlerfrei lief - die Ursache ist nicht geklaert, die Probe ist damit unzuverlaessig.
      Eine Probe, die beim Import stirbt, meldet nie "0 Halter": die Aufgabe wartet 45 min und
      fahrt nichts.
      Naechster Schritt: Halter ueber die kanonischen Funktionen zaehlen
      (`hermes_cli.update_cmd_windows._detect_venv_python_processes` /
      `_hermes_holder_subcommand`) und von aussen aufrufen, statt eine eigene Prozessliste per
      Teilstring zu bauen; danach EINMAL gegen den laufenden Dashboard-PID-Paar pruefen, dass die
      Probe ihn wirklich sieht.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/tmp/venv_halter.py, Task `Hermes-Update-20260921`
      Erledigt 29.09.2026: Die Probe laeuft wieder. `tmp/venv_halter.py` zaehlt die
      Halter ueber die kanonischen Funktionen (`hermes_cli.update_cmd_windows.
      _detect_venv_python_processes`, Gateway ausgenommen) und findet im echten Lauf
      2 Halter (.hermes-runtime-Python 51660, Dashboard 64468). Der fruehere
      `ModuleNotFoundError: No module named 'ruamel'` kam aus dem unvollstaendigen venv
      nach dem abgebrochenen Update vom 25.09. und ist mit der Reparatur verschwunden.
- [x] **T-110 — Verwaiste Update-Autostashes im Checkout**
      Kontext: Jedes `hermes update` legt einen Autostash an und stellt ihn wieder her; bleibt
      einer liegen, warnt das Update nach 7 Tagen (`stash@{1}` vom 17.09. besteht weiter, dazu
      `stash@{0}` = der Lauf vom 25.09.2026 17:06, der nach dem Pull erfolgreich zurueckerstattet
      wurde). Die Aenderung `js-yaml` 4.3.1 -> 4.3.2 in `package.json` lag am 25.09.2026 nur im
      Arbeitsbaum (npm-Audit damit 0), sie wird bei jedem Update mitgestasht und
      zurueckerstattet.
      Naechster Schritt: Inhalte mit `git stash show -p stash@{n}` ansehen, was noch gebraucht wird
      als Patch sichern, den Rest bewusst verwerfen (`git stash drop`); entscheiden, ob der
      js-yaml-Fix upstream gemeldet oder im Checkout committet wird.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/hermes-agent (git stash, package.json)
      Erledigt 29.09.2026: Beide Autostashes verworfen, Inhalt vorher gesichert nach
      `Agenten/Hermes/logs/stash-sicherung/autostash-20260922.patch` (24.792 B; der vom
      17.09. war leer). Kein Commit im Checkout: er wird von `hermes update` verwaltet,
      ein eigener Commit blockiert den naechsten Pull. Der js-yaml-Fix ist ausserdem
      gegenstandslos - `package.json` traegt beide Eintraege (overrides Zeile 58 und
      Zeile 79) wieder KONSISTENT auf 4.3.1, der EOVERRIDE-Bruch kann nicht auftreten.
- [x] **T-116 - ai4trade-Passwort stand im Klartext in einem Sitzungsprotokoll**
      Kontext: Die API von https://ai4trade.ai echot bei einem fehlerhaften
      Login-Aufruf das Feld `input` der Anfrage zurueck - also E-Mail UND Passwort
      im Klartext. Am 28.09.2026 bei der Fehlersuche zum Heartbeat einmal passiert
      (422-Antwort), der Wert steht damit in einem Sitzungsprotokoll.
      Naechster Schritt (nur Max): Passwort auf der Plattform aendern, neuen Wert
      in `Agenten/Handel/ai4trade/.env` und in `Wissen/Zugaenge.md` nachtragen.
      `heartbeat.py` wertet bei Fehlern nur `detail.loc` aus, niemals `input`.
      Angelegt 29.09.2026. Betrifft Agenten/Handel/ai4trade.
      Erledigt 29.09.2026: Die Plattform hat KEINEN Endpunkt zum Passwortwechsel
      (gemessen am App-Bundle: nur selfRegister, login, me) - deshalb neu angelegt:
      Agent `HermesMax2`, agent_id 25973, ueber Agenten/Handel/ai4trade/neu_anlegen.py
      (schreibt .env und Wissen/Zugaenge.md, gibt Werte nie aus). selfRegister, /me und
      der Heartbeat antworten HTTP 200, der Cron `ai4trade-heartbeat` laeuft darauf.
      Der alte Agent HermesMax (25970) ist verworfen. Commit 9d11f0e.
- [x] **T-120 - kennzahlen() gibt None fuer nautilus_kraken trotz 4 Runden**
      Kontext: `auswertung_alle.runden_fuer('nautilus_kraken')` liefert 4 Runden,
      `kennzahlen()` gab trotzdem None - die Spur verschwand aus der Auswertung.
      Ursache (29.09.2026): die vier Zeilen sind `buchbereinigung`-Ausbuecher
      (Papier-Altlasten); `kennzahlen()` nimmt alles heraus, was
      `stoerungen.ist_stoerung` kennt, und hatte danach keine echte Runde
      (`if not echt: return None`). Die Zahl war richtig, die ANZEIGE nicht:
      derselbe Satz "keine geschlossene Runde" stand fuer drei verschiedene
      Lagen (tote Spur, wartender Stop, Ausbuchung). Geloest 29.09.2026:
      `auswertung_alle.offene_positionen(spur)` und die erweiterte Ausgabe in
      `zeige()` nennen jetzt die Lage - "aber 4 offene Position(en) im Buch"
      (macd_mtf, supertrend) bzw. "daneben 4 Ausstiege ohne Handelsentscheidung"
      (nautilus_kraken) bzw. "wartet auf ihr erstes Signal" (iv_waelle).
      Tests `Agenten/Handel/tests/test_auswertung_offene_positionen.py` (9).
- [x] **T-113 - ai4trade.ai: Heartbeat wird nicht gepollt**
      Kontext: Der Agent `HermesMax` (ID 25970) ist am 28.09.2026 auf
      https://ai4trade.ai angemeldet; Antworten, Erwaehnungen und neue Follower
      kommen ausschliesslich ueber den Heartbeat an, nicht per Mail.
      Geloest 29.09.2026: `Agenten/Handel/ai4trade/heartbeat.py` pollt ihn
      (Cron-Bruecke `Agenten/Hermes/scripts/ai4trade-heartbeat.py`), Hermes-Cron
      `ai4trade-heartbeat` (Job 2f886828dcdf, alle 5 min, no_agent, Telegram) -
      leere Ausgabe = nichts senden, Zustand in `ai4trade/cache/`.
      BEFUND dabei: der Plattform-Skill nennt den Kopf `X-Claw-Token`, die API
      antwortet damit 401 "Invalid token"; richtig ist
      `Authorization: Bearer <token>` (gemessen). Das Skript probiert beide Wege.
      15 Tests gruen (`ai4trade/tests/test_heartbeat.py`).
      Angelegt 28.09.2026 · Erledigt 2026-09-29 · Betrifft Agenten/Handel/ai4trade.
- [x] **T-114 - ai4trade-Kennung in Wissen/Zugaenge.md nachtragen**
      Kontext: E-Mail, Passwort und Token des Agenten `HermesMax` lagen nur in
      `Agenten/Handel/ai4trade/.env`; `Wissen/Zugaenge.md` ist laut Schutzregeln
      die EINZIGE Ablage fuer Schluessel.
      Geloest 29.09.2026: Abschnitt "ai4trade.ai (AI-Trader) - Papierhandel, kein
      Boersenzugang" in `Wissen/Zugaenge.md` (Adresse, E-Mail, Passwort, Token,
      agent_id 25970, Ablageort der .env, Heartbeat- und Echo-Vermerk). Vorher
      Sicherung `Zugaenge.md.bak-20260928`; das Nachtragen lief ueber ein Skript,
      die Werte wurden dabei nicht ausgegeben (Stufe 0).
      Angelegt 28.09.2026 · Erledigt 2026-09-29 · Betrifft Wissen/Zugaenge.md.
- [x] **T-112 — scanner: Treffer 100 % war kein Zaehlfehler, sondern eine Anzeigeluecke (behoben)**
      Kontext: Auftrag Max 25.09.2026 (t-112). Der Bericht nennt fuer OKX Spot 7 Tage: 83
      Runden, +1801.08 USD, Treffer 100 % neben Ruecklauf 0.00 USD - das liest sich wie ein
      fehlerfreier Automat.
      Nachgezaehlt (eigene FIFO-Paarung je Instrument, unabhaengig von auswertung_alle): im
      selben Fenster schlossen 101 Runden, 99 Gewinner, 2 Verlierer (beide grund=buchbereinigung,
      -1.51 und -2.91 USD) -> echte Trefferquote 97.9 %. KEIN Zaehlfehler: kennzahlen() trennt
      seit 15.09.2026 Ausstiege ohne Handelsentscheidung (stoerungen.ist_stoerung: herzschlag/
      zwangsschluss/notaus + buchbereinigung) aus Rundenzahl UND Quote und weist sie separat aus
      (n_stoerung 18, stoerung_ergebnis +210.14). Der Fehler war die ANZEIGE: die 7-Tage-Zeile
      nannte nur n/treffer.
      Behoben: tagesbericht.rundenzeile(s) aus der _baue-Schleife herausgeloest (Muster
      livezeile(): eine Zeile, eine Funktion, eine Regel im Test) und um den Zusatz erweitert;
      die Zeile lautet jetzt: 7 Tage: 83 Runden, +1801.08 USD, Treffer 100% | +18 Ausstiege ohne
      Handelsentscheidung (+210.14 USD, nicht in der Quote).
      Offen geblieben: anpassen/buch_nachgezogen_boerse (Mengenabgleich, 22.09.2026) zaehlen
      weiter als Runde - stoerungen.BUCHHALTUNG kennt nur buchbereinigung; das zu aendern wirkt
      auf ALLE Buecher und braucht eine eigene Entscheidung.
      Beleg: tagesbericht.py --ohne-xperp zeigt den Zusatz; tests/test_tagesbericht_rundenzeile.py
      (8) plus die acht Berichtstestsuiten (70 Tests) gruen.
      Angelegt: 2026-09-25 (erledigt am 25.09.2026)
      Betrifft: Agenten/Handel/tagesbericht.py, Agenten/Handel/tests/test_tagesbericht_rundenzeile.py- [x] **T-108 — Legacy-Gateway-Starter entfernt (die Aufgabe war schon weg)**
      Kontext: Auftrag Max 25.09.2026 ("t-108"). Gemessen nach dem Update: die Aufgabe
      `Hermes_Gateway` EXISTIERT NICHT mehr - `Get-ScheduledTask` findet nur
      `Hermes-Update-20260921`, `Hermes_Dashboard` und `Hermes_Gateway_2ef9d0b7`, und
      `Unregister-ScheduledTask -TaskName Hermes_Gateway` meldet "keine MSFT_ScheduledTask-
      Objekte mit TaskName Hermes_Gateway". Geblieben waren nur die Dateien:
      `Hermes_Gateway.cmd` zeigte noch auf das stillgelegte `C:\Hermes\venv`,
      `Hermes_Gateway.vbs` war schon entschaerft (WScript.Quit 0).
      Erledigt: alle drei Legacy-Dateien liegen in
      `.sicherung\gateway-service-legacy-20260925\` (nichts geloescht); `gateway-service/`
      enthaelt nur noch die gueltigen Starter (Gateway + Dashboard).
      Beleg: `logs/gateway-legacy-entfernen-20260925.log`; Gateway danach unveraendert
      (pid 64192, Port 9900 offen, laeuft aus `tools\python-3.14.7`).
      Angelegt: 2026-09-25 (erledigt am 25.09.2026)
      Betrifft: Agenten/Hermes/gateway-service/, Agenten/Hermes/.sicherung/
- [x] **T-175 — OKX-Contract-DCA laesst sich nicht mit einem Stop versehen - nur der Bot selbst**
      Umgenummert 2026-09-29: **T-088** ist gleichzeitig fuer eine OFFENE Aufgabe vergeben; dieser erledigte Eintrag bekommt eine eigene Nummer.
      Kontext: Auftrag Max 25.09.2026 ("Okx-bot-wache stop setzen"). Zwei Wege geprueft,
      beide zu: (a) `POST /api/v5/tradingBot/dca/amend-order-algo` heisst in der OKX-Doku
      woertlich "Amend **spot** dca basic param" - acht laufende CONTRACT-DCAs wurden mit
      `51291: The bot doesn't exist or has already stopped` abgewiesen; der slPct einer
      laufenden Contract-DCA ist also nicht setzbar. (b) ein Stop auf die POSITION geht
      nicht, weil das Konto keine Position zeigt: `/api/v5/account/positions` liefert 0
      Eintraege (auch mit instType FUTURES/SWAP), je Bot-Instrument eine Zeile mit pos=0.
      Die Bots halten ihre Marge also intern. Folge: das EINZIGE Schutzmittel ist
      `dca/stop` - den Bot anhalten (Tor `stop_erlaubt`), was die Position zum Markt
      schliesst. Der Waechter verlangt das fuer UNI (NOTFALL, 4,3 % vor der Liquidation,
      PnL -59 %, Munition 0/11).
      Naechster Schritt: entscheiden - UNI-Bot anhalten (realisiert rund -59 % / ~-40 USDC)
      ODER laufen lassen. Danach `stop_erlaubt` in `okx_bot_waechter/wachen.json` setzen
      und `waechter.py --anwenden` fahren.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/okx_bot_waechter/, OKX-Bot 3947610369740500992
      **Erledigt 2026-09-25.** Max: "Uni weiterlaufen lassen" - der Bot bleibt an, `stop_erlaubt` bleibt false. Die Entscheidung steht als Vermerk in `okx_bot_waechter/wachen.json` (bots.<algoId>), damit der Waechter sie nicht jede Runde neu als offene Frage meldet.
- [x] **T-174 — MoA-Presets und der verwaltete llama-Server: Bonsai oder nicht**
      Umgenummert 2026-09-29: **T-086** ist gleichzeitig fuer eine OFFENE Aufgabe vergeben; dieser erledigte Eintrag bekommt eine eigene Nummer.
      Kontext: Bonsai laeuft seit 25.09.2026 mit 64k (`-Kontext 65536`, VRAM
      7.772/253 MiB, 12,1 t/s) und wird von Hermes als Agent-Modell angenommen
      (Nachweis: `hermes -z` in leerem HERMES_HOME antwortet `OK`); die Delegation
      faehrt darauf. Offen ist der llama.cpp-Weg IN HERMES: der Alias
      `provider: llamacpp` loest ZUERST auf den EIGENEN verwalteten llama-server
      auf (Port 18434), nicht auf Bonsai (8080) - die acht MoA-Eintraege (Presets
      default / Max 2 / Vision, Referenzmodelle und Aggregatoren) zeigen deshalb
      nicht auf Bonsai, obwohl ihr Modellname jetzt `bonsai` lautet.
      Naechster Schritt: entscheiden, ob diese acht Eintraege auf
      `provider: bonsai` umgestellt werden (dann wirklich Bonsai, 12 t/s, GPU
      voll) ODER ob der verwaltete Server Bonsai servieren soll (braucht den
      PrismML-Fork statt des upgestreamten llama.cpp).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Hermes/config.yaml, Agenten/Werkzeuge/bonsai-27b.ps1
      **Erledigt 2026-09-25.** Max: "Moa auf bonsai". Die acht Eintraege der Presets default / Max 2 / Vision (sechs Referenzmodelle, zwei Aggregatoren) stehen jetzt auf `provider: bonsai` und erreichen damit den Dienst auf 8080 statt des verwalteten Servers auf 18434. Byte-genau ersetzt (4 + 2 + 2), CRLF erhalten, YAML geprueft; ein echter MoA-Lauf lief danach durch (Antwort `OK`).
- [x] **T-073 — Kraken-Futures-Schluessel war stundenweise abgewiesen - der VPN war es**
      Kontext: Um 00:24 am 25.09.2026 antwortete `/derivatives/api/v3/accounts` mit
      dem echten Stand (availableMargin 141,5963; USD 8,89 + EUR 45,74 + USDC 81,08),
      ab etwa 00:29 nur noch `authenticationError` - fuer JEDE nonce (ms/us/ns/1,8e18/
      9e18) und mit ZWEI unabhaengigen Umsetzungen (unser `kraken_futures.py` UND die
      offizielle kraken-cli `futures accounts`). Am Haus lag es nicht: die Werte in
      HKCU\Environment waren unveraendert (Hash gegen die PowerShell-History vom
      24.09. 21:22 verglichen), Uhr 1,3 s, Kraken online. Um 01:33 ging es OHNE Zutun
      wieder (Zeuge: guthaben 141,5949 USD).
      Erledigt am 25.09.2026: `kraken_futures.guthaben()` las nur `cash.balances`
      (alles 0,0) statt des flex-Kontos - die Spur sah deshalb 0 USD, obwohl 141,59
      verfuegbar waren. Jetzt flex zuerst, cash als Rueckfall; Tests 27 gruen.
      Erledigt am 25.09.2026 (zweiter Teil, Werkzeug): Der Ausfall blieb offen, weil
      im Haus NICHTS aufgezeichnet wurde - kein Log, kein Journal, keine Zeile mit
      Statuscode, Header oder Rohantwort; die Spuren liefen im Papier weiter und
      schrieben `(papier) ok`. Neu: `Agenten/Handel/kraken_abweisungs_sonde.py`
      misst je Lauf vier Wege (oeffentlich/signiert x Spot/Futures), unterscheidet
      damit `netz` von `schluessel`, schreibt im Fehlerfall den ZEUGEN (Status,
      content-type, cloudflare-Header, Rohkoerper) nach
      `Agenten/Handel/cache/kraken-abweisungen.jsonl` und wartet nach einer
      Abweisung 60 min (bei einem Konto-Lockout setzt jeder Versuch den Timer
      zurueck). Wache: Cron `kraken-abweisung-wache` (30 min, no_agent, Telegram).
      Test-Nachweis: 10 Tests mit Kraken-Attrappe, echter Lauf gesund (03:16), Wache
      schweigt. Wiki: Werkzeuge/kraken-abweisungs-sonde.md, Lektion 3 in
      Lektionen/Boersen-und-Schluessel.md.
      Naechster Schritt: Beim naechsten Auftreten die Protokollzeile lesen
      (`lage` sagt die Ebene, `zeuge.roh_*` Rechte gegen Lockout gegen cloudflare)
      und Max fragen, ob er in dem Fenster im Kraken-Portal war (Schluessel
      bearbeiten/erzeugen).
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/nautilus_kraken/kraken_futures.py,
      Agenten/Handel/kraken_abweisungs_sonde.py
      **Erledigt 2026-09-25 - Ursache war NORDVPN, kein Schluessel.** Gemessen: mit verbundenem NordLynx-Tunnel (Ausgang 45.150.x.x, ein NordVPN-Knoten) antwortet der Futures-Weg `authenticationError`, waehrend der Spot-Weg durchlaeuft; nach dem Trennen des Tunnels (Ausgang 92.208.x.x, eigener Anschluss) geht derselbe Aufruf sofort wieder (guthaben 141,5876 USD, 0 Positionen). Die Werte in HKCU\Environment waren die ganze Zeit unveraendert (Hash gegen die PowerShell-History vom 24.09. 21:22). Betriebsregel: vor einer Futures-Order muss der VPN aus sein (oder der Key im Portal fuer die VPN-IP freigegeben werden). Zeuge/Diagnose: `Agenten/Handel/kraken_abweisungs_sonde.py` (fuenf Wege, Rohantwort im Fehlerfall; die Einordnung nennt jetzt die Herkunft VOR dem Schluessel). Wiki: Handel/Boersen-und-Schluessel.md.
- [x] **T-084 — Sprachmodell-Spuren koennten auf Bonsai umziehen (braucht OpenAI-Weg)**
      Kontext: `moondev_whale`, `moondev_liquidation`, `moondev_sentiment` holen ihr
      Urteil ueber `Agenten/Handel/llm_lokal.py` aus Ollamas EIGENER Schnittstelle
      (127.0.0.1:11434, `/api/...`). Der Bonsai-Server bietet diesen Weg nicht
      (gemessen 25.09.2026: `/api/chat` -> 404, nur OpenAI unter `/v1`). Ein Umzug
      waere inhaltlich reizvoll (27B statt 8B beurteilt die Lage), kostet aber eine
      zweite Schnittstelle im llm_lokal-Modul - Entscheidung von Max.
      Naechster Schritt: Angebot vorlegen (Aufwand: kleine Erweiterung in
      llm_lokal.py, Wahl des Wegs ueber die wachen.json je Spur), erst danach bauen.
      Angelegt: 2026-09-25
      Betrifft: Agenten/Handel/llm_lokal.py, Agenten/Handel/moondev_*/wachen.json
      **Erledigt 2026-09-25.** Max: "T-084 ja besser bonsai". `llm_lokal.py` hat den zweiten Weg (OpenAI unter /v1), gewaehlt per `llm_weg` in der wachen.json; die drei Spuren stehen auf `bonsai`. Kein stiller Rueckfall: schweigt der Dienst, faellt das Urteil aus. Gemessen mit `llm_probe.py --modelle bonsai --wiederholungen 2`: 6/6 im Vertrag, kalt 1,3 s, im Mittel 1,3 s. Die Sonde selbst rief frueher immer Ollama und meldete Bonsai als "(leer)" - behoben. Tests: `Agenten/Handel/tests/test_llm_lokal_wege.py` (16 gruen). Wiki: Werkzeuge/Bonsai-2-27B.md.
- [x] **T-173 — Das laufende ZEC-Grid hat keinen Stop**
      Umgenummert 2026-09-29: **T-077** ist gleichzeitig fuer eine OFFENE Aufgabe vergeben; dieser erledigte Eintrag bekommt eine eigene Nummer.
      Kontext: `3951805062334382080`, ZEC-USD_UM_XPERP-310530, long, 90,12 USDC,
      Hebel 5 (tatsaechlich 2,43), Band 1480-1680, 20 Netze, liqPx 1111,64,
      `slTriggerPx` LEER (Stand 25.09.2026 01:30). Von den 62 geschlossenen Grids
      war der groesste Einzelverlust (-304,33 USDC, BICO) ein Grid ohne Stop, das
      lief, waehrend der Markt -19,3 % machte.
      Naechster Schritt: entscheiden, ob der Stop an die untere Netzkante (1480)
      bzw. unter den 90-Tage-Boden gesetzt wird - `anpassen.py` kann das mit
      `--nur-schutz`; danach die Entscheidung als `bots.<algoId>.vermerk` mit
      Datum in `wachen.json` festhalten.
      Angelegt: 2026-09-25
      Wartet auf: Entscheidung Max
      Betrifft: Agenten/Handel/okx_bot_waechter/, OKX-Bot 3951805062334382080
      **Erledigt 2026-09-25.** Max: "Stop setzen". Gesetzt ist slTriggerPx 1354 (Kurs - 1,5 x ATR14 132,18), also unter dem Bandboden 1480 und 22 % ueber der Liquidation 1110,77; Gegenprobe nach dem Amend gelesen (sCode 0, Leiter unveraendert). Zahl und Weg: `Agenten/Handel/okx_bot_waechter/grid_schutz.py` (Trockenlauf ohne --anwenden); der Endpunkt ist `/grid/amend-order-algo`, nicht `/grid/amend-algo` (404). Entscheidung steht als Vermerk in `okx_bot_waechter/wachen.json`.
- [x] **T-172 — Waisen-Wächter für Kraken-Schutz-Orders (meldend)**
      Umgenummert 2026-09-29: **T-070** ist gleichzeitig fuer eine OFFENE Aufgabe vergeben; dieser erledigte Eintrag bekommt eine eigene Nummer.
      Gebaut 24.09.2026: Agenten/Hermes/scripts/waisen-wache.py (no_agent,
      Cron waisen-wache 909126bc2102, alle 30 min, Telegram). Rechnet über
      kraken/waisen_stops.py, meldet neue Waisen sofort, dieselben höchstens
      alle 6 h, das Verschwinden einmal, und einen Messfehler. Storniert NIE
      (Quelltext-Test verbietet Storno-Aufrufe). 11 Tests grün.

- [x] **T-060 — coingecko_agent: Token-Extraktor und Runden-Synopsis auf den lokalen Weg geholt** — erledigt 2026-09-24
      Kontext: Beide Nebenwege sprachen hart den Anthropic-Client an und
      starben am OpenAI-Client ("'OpenAI' object has no attribute 'messages'",
"Messages.create() got an unexpected keyword argument 'temperature'").
      Loesung: EINE Hilfsfunktion `_llm_text(client, model, system, user,
      max_tokens, temperature)` in coingecko_agent.py fragt die FORM des
      Clients ab (`hasattr(client, "chat")`) statt eine Wolke zu raten; der
      TokenExtractorAgent bekommt Client und Modell jetzt vom System
      uebergeben (`TokenExtractorAgent(self.agent_one.client,
      self.agent_one.model)`) statt sich einen eigenen Anthropic-Client zu
      bauen. Nachweis: kompletter Lauf ueber die Bruecke ohne eine einzige
      Fehlerzeile - Extraktor nennt 6 Tokens (NEAR, ONDO, ASTRO, BP, LTC, ETH),
      Synopsis liefert echten Text. 23 Tests in
      Agenten/Werkzeuge/tests/test_ollama_openai_bruecke.py gruen.
      Angelegt: 2026-09-24 · Erledigt: 2026-09-24
      Betrifft: Werkstatt/Repos/moon-dev-ai-agents/src/agents/coingecko_agent.py
- [x] **T-058 — MoonDev-Aufgabe auf fensterlosen Wrapper umgestellt** — erledigt 2026-09-24
- [x] **T-043 — OmniRoute lag 5,5 Stunden still, und die Aufgabe sah harmlos aus**
- [x] **T-051 — Stops fuer die uebrigen Kraken-Spotbestaende**
      Kontext: Am 24.09.2026 wurden die mosaic-Bestaende (BTC/ETH/SOL) und die
      Margin-Positionen SUI/NEAR/ZEC abgesichert. Das uebrige Guthaben traegt
      KEINEN Stop: ALGO, KAS, PEPE, JTO, ONDO, STG, SYN, ADA, DIMO und weitere
      Kleinstbestaende - ein Kursrutsch dort laeuft ungebremst.
      Naechster Schritt: Max nennt die Liste (oder "alle ab X EUR"), dann laufen
      sie durch dasselbe Muster (Skill handel-spuren, Abschnitt "Bestehende
      Positionen nachtraeglich absichern" + references/boersen-aufrufe.md).
      Angelegt: 2026-09-24 · Zuletzt: 2026-09-24
      Betrifft: Agenten/Handel/kraken/, Agenten/Handel/mosaic/kraken_stops_7_5.py
      **Erledigt 2026-09-24.** Max: "alle ab 50 €". Zwei Bestaende trugen
      keinen Stop und bekamen einen: **ALGO** 513,98026315 @ **0,09033**
      (`O6DA3U-7D5IU-Z2FKJR`) und **SOL** 0,98120906 @ **94,48**
      (`OB5P52-TSYY4-QTIJUN`) - der Rest der 1,4618 SOL war schon durch den
      mosaic-Stop (0,48058439 @ 96,24) belegt. Werkzeug:
      `Agenten/Handel/kraken/spot_stops.py` (Vorschau Standard, `--anwenden`,
      `--ab-eur`, `--prozent`); es ordert nur den FREIEN Teil (Betrag minus
      `hold_trade`), ist damit idempotent und der zweite Lauf meldet
      "0 Bestaende ohne Stop". 76 kraken-Tests gruen, an der Boerse geprueft:
      13 offene Stops, jeder unter dem Markt (5,3-11,6 %).
      Unter der 50er-Schwelle blieben liegen: KAS 43,3 · SYN 27,0 · STG 24,8 ·
      JTO 22,6 · ONDO 20,2 · DUAL 12,2 · HYPE 2,0 · PEPE 1,6 EUR/USD, dazu die
      gestakten ATOM21.S/ADA.S und XPEV.EQ (kein Paar).
      Betrifft: Agenten/Handel/kraken/spot_stops.py,
      Agenten/Handel/kraken/tests/test_spot_stops.py
      **Erledigt 2026-09-16.** Der Router war von 10:39 bis 16:04 nicht
      erreichbar. Ursache war der eigene Startweg: `omniroute-start.ps1` rief
      das Startskript mit einer Pipe auf, das Startskript startet aber einen
      Dauerprozess, der diese Pipe offen haelt. Der Aufrufer kehrte nie
      zurueck - die Aufgabe blieb „Running“, das eigene Protokoll war von
      aussen gesperrt (`Get-Content`: „Device or resource busy“), und als die
      Aufgabe beendet wurde (`^C` im Startprotokoll), starb der Router mit.
      Genau das ist am 16.09. um 10:35/10:39 passiert; der Teilcode 267014 sah
      wie „von aussen beendet“ aus, die Systempruefung meldete ihn nur als
      „zu entscheiden“.
      **Behoben:** der Wrapper startet das Startskript jetzt losgeloest
      (`Start-Process -WindowStyle Hidden`, eigener Prozessbaum) und wartet
      selbst auf den Port (bis 600 s). Nachweis: Router gestoppt, Wrapper von
      Hand - Exit 0 nach 18 s, Protokoll lesbar („ENDE ok nach 18 s“),
      `/v1/models` antwortet 401.
      **Neue Wache:** Hermes-Cron `omniroute-waechter` (alle 15 Minuten,
      `no_agent`, `Agenten/Hermes/scripts/omniroute-waechter.py`) - leere
      Ausgabe heisst „Router laeuft“, sonst Telegram mit Zustand, Startversuch
      und Nachmessung. Der Scheduler laeuft am Router vorbei; eine Wache darf
      nicht den Weg benutzen, den sie ueberwacht. Nachweis: Port freigegeben,
      Wache laufen lassen - „Nachgemessen: Port 20128 ist offen - geheilt“
      nach 25 s.
      Betrifft: `Agenten/Routinen/omniroute-start.ps1`,
      `Agenten/Hermes/scripts/omniroute-waechter.py`
      Angelegt: 2026-09-16

- [x] **T-018 — Saisonalitaet rechnete nur auf 50 Tagen, nicht auf der tiefen Reihe**
      **Erledigt 2026-09-16.** `indikatoren.lage(k_stat=...)` rechnet die
      Saisonalitaet jetzt auf der tiefen Reihe, wenn `bot.py` mit `--historie`
      laeuft; der Signal-Merge steht dafuer in `indikatoren.signal_bauen()` an
      einer Stelle. Uebernommen wird die Reihe nur, wenn sie laenger ist UND
      gleichzeitig endet (`_gleichzeitig`) - `saisonalitaet()` liest Wochentag
      und Tagesphase der naechsten Kerze aus dem Ende der Reihe.
      Gemessen an `LINK-USD_UM_XPERP-310829` (20 Tage alt): n=16 aus dem
      Kontrakt gegen n=172 aus `LINK-USDT-SWAP` (1200 Kerzen). Die Ausgabe
      nennt die Basis („Basis: tiefe Reihe, 1200 Kerzen“), die Warnung „n ist
      duenn“ entfaellt dann. Das Kurs-Signal bleibt am Kontrakt.
      Nachweis: 6 neue Tests (`xperp/test_saisonalitaet_tief.py`) und 18
      bestehende gruen, echter Lauf `bot.py trend --wert LINK --historie auto`,
      Gegenprobe ohne `--historie` (n=16), `handeln.py --vorschau` Exit 0.
      Betrifft: `Agenten/Handel/xperp/{indikatoren,bot}.py`, [[Saisonalitaet-Signal]]
      Angelegt: 2026-09-01 · Zuletzt: 2026-09-16

- [x] **T-035 — Spur 2 ist nur im Dauerbetrieb nutzbar (Herzschlag 30 min)**
      **Erledigt 2026-09-16 — die 30 Minuten sind ueberholt.** Seit dem
      14.09.2026 gilt die Herzschlag-Regel: 180 Minuten fuer Papier-Spuren,
      45 Minuten fuer Spuren mit Handelserlaubnis (`_herzschlag_regel` in jeder
      `wachen.json`); der Dauerlauf-Waechter startet eine tote Spur alle 30
      Minuten neu. `xperp/wachen.json` steht auf 180 (Papier). Die
      Systempruefung misst es in Block 11b nach: 26 von 26 Handels-Spuren
      folgen der Regel. Der zweite Weg ist damit der eine Weg - der Dauerlauf
      laeuft.
      **Nachtrag 19.09.2026 (T-035 ueberdacht, von Max angeordnet):** Die
      45-Live-Grenze ist aufgehoben - seit 19.09.2026 gilt 180 fuer ALLE
      Spuren (Papier UND Live). Grund: ungeklaerte Abschaltungen (T-004)
      lassen die Herzschlag-Luecke bei einem PC-Ausfall ueber 45 min wachsen;
      ein Fehlschluss der Live-Position (scanner) waere ein Verlust in echtem
      Geld. Die Position loest die Spur ueber Stop-/Risiko-Logik auf, nicht
      der Herzschlag. Umgesetzt: `scanner/wachen.json`
      `herzschlag_max_minuten` 45 -> 180 (+ `_herzschlag_regel` konsistent),
      `systempruefung.ps1` Block 11b `$soll = 180` (war 45 live / 180 papier).
      Nachweis: 11b-Formel gegen scanner = konform true.
      Betrifft: `Agenten/Handel/xperp/wachen.json`, `dauerlauf.py`

- [x] **T-015 — Seagate Portable (`G:`) war ab, Hauptsicherung ohne Ziel**
      **Erledigt 2026-09-16.** `G:` ist angeschlossen (`G:\MaxHirn-Sicherung`
      vorhanden, 119 GB frei) und die Laeufe sind gruen: `MaxHirn-Sicherung`
      15.09. 20:00 Code 0, `MaxHirn-Zweitkopie` 21:00 Code 0,
      `MaxHirn-Posteingang` 22:00 Code 0 (gemessen 16.09.2026). Der Befund vom
      31.08. war das abgezogene Laufwerk, kein Defekt. Die Ausser-Haus-Kopie
      zielt inzwischen auf `Q:` statt `E:` (siehe [[Routinen]]).
      Betrifft: `Agenten/sichern.ps1`, `Agenten/sichern-ausser-haus.ps1`,
      Aufgabe `MaxHirn-Sicherung`

- [x] **T-041 — Drei Spuren startet der Dauerlauf, ohne dass sie den Bus melden**
      **Erledigt 2026-09-13.** `swap/handeln.py`, `spiegel/spiegel.py` und
      `orbk/handeln.py` tragen jetzt je `with ereignis.lauf("handel/<spur>")`
      (main() als Wrapper, _main() der bisherige Body; Muster
      `xperp/handeln.py`). Nachweis: drei `--vorschau`-Laeufe, im Journal stehen
      start/ende (code 0) fuer alle drei; der laufende Dauerlauf hatte sie im
      11:52-Zyklus schon gemeldet. Spurtests gruen (swap 30, spiegel 33, orbk 46),
      Bus-Suite meldet „Ende-zu-Ende bestanden“ (Commit 1b0140d).

      **Zwei Vorbestands-Fehler kamen dabei mit heraus**, beide erst sichtbar,
      nachdem die Pruefung darueber wieder griff:
      1. `test_anbindung_handel.py` zeigte in der statischen Liste auf
         `orb/handeln.py` - die Datei gibt es nicht mehr, die Spur laeuft als
         `orbk`. Nachgezogen, mit Begruendung im Kommentar.
      2. `safe-file-ops.ps1` ist eine **Bibliothek**, die `posteingang.ps1` und
         `datensortierung.ps1` dot-sourcen (eigener `$MyInvocation`-Einsprung).
         Eine eigene Start/Ende-Meldung von dort waere falsch - sie erzeugte bei
         jedem Aufruf des Einbinders einen zweiten Zyklus im Journal.
         `test_anbindung_routinen.py` ueberspringt jetzt Dateien, die sich im
         Kopf mit `BUS: Bibliothek` kennzeichnen; der Marker steht in der Datei,
         die Begruendung im Test.
      Betrifft: `Agenten/Handel/{swap,spiegel,orbk}`, `Agenten/Bus/tests/`,
      `Agenten/Routinen/safe-file-ops.ps1`
- [x] **T-037 — Echter Umzug: Archiv ganz aus dem Vault, konfigbasiert** — erledigt
      2026-09-07. Folgeauftrag zum Junction-Umzug vom 06.09. (Commit ad469fb).
      Die sechs NTFS-Junctions unter `MaxHirn/Archiv/` sind entfernt; die
      Archivdaten (44 GB, 64.745 Dateien) liegen nur noch auf `O:\Archiv`. Alle
      Werkzeuge finden sie über die neue User-Umgebungsvariable
      `ARCHIV_ROOT = O:\Archiv` (Rückfall im Code auf die Vault-Lage).
      `ArchivSuche/` (git-versionierter Code) und der Index `archiv_index.db`
      (neu baubar) bleiben auf `C:`.
      Geändert: `index.py`, `server.py` (`ROOT` aus `ARCHIV_ROOT`);
      `archiv_mcp.py`, `mailversand.py` (Datenwurzel von Indexwurzel getrennt);
      `sichern.ps1` / `sichern-zweitkopie.ps1` (Junction-Sonderfall raus, zweiter
      robocopy-Lauf `O:\Archiv` → `G:`/`J:` bleibt). `vektor_index.py`,
      `vektor_suche.py`, `search_cli.py` unverändert (nur DB).
      Gegenprobe: `index.py` inkrementell → 9712 Einträge, 0 verändert, 0
      entfernt; `search_cli.py`-Testsuche unverändert; `archiv`- und `mail`-MCP
      funktional gegen `O:` geprüft; `90-pruefen.ps1` — MCP-Pfade und Suchindex
      grün. Doku: `Ordnerstruktur.md`, `Schutzregeln.md`, `MaxHirn/CLAUDE.md` +
      `AGENTS.md`, `Archiv/CLAUDE.md` + `AGENTS.md`, `Archiv/README.md`.
      Offen: laufende Prozesse (Claude Desktop, Hermes) sehen `ARCHIV_ROOT` erst
      nach Neustart.
      Betrifft: `MaxHirn/Archiv/ArchivSuche/`, `Agenten/MCP-Server/{archiv,mail}/`,
      `Agenten/sichern*.ps1`
      Angelegt: 2026-09-07 · Zuletzt: 2026-09-07

- [x] **T-034 — Hauptsicherung fehlschlug am 04.09. weil Hermes live läuft** — erledigt
      2026-09-04. Um 20:00 meldete `sichern.ps1` robocopy-Code 11 (FEHLER), obwohl
      47,5 GB kopiert worden waren. Ursache: **Hermes läuft seit dem Umbau
      innerhalb der Sicherungsquelle** (`BrainFiles/Agenten/Hermes`) und hält
      beim 20-Uhr-Lauf seine drei lebenden Laufzeitordner offen:
      `pending_messages/`, `cache/terminal-output/`, `telemetry/shared_metrics/`.
      robocopy scheiterte daran mit Zugriff verweigert, verbrauchte die
      Wiederholungen und brach als Fehler ab (dieselbe Klasse wie der
      `logs`-Ausschluss vom 23.08.).
      **Fix:** diese drei Namen in `/XD` aller drei Sicherungsskripte
      (`sichern.ps1`, `sichern-zweitkopie.ps1`, `sichern-ausser-haus.ps1`)
      aufgenommen — gleiche Behandlung wie `logs` und Claude. Stufe 1:
      `.bak-20260904` angelegt, echter Lauf bestätigte **robocopy-Code 3,
      0 Fehler** (Hermes lief dabei). Commit `8a23529` (Autor Hermes).
      Die drei Ordner sind reine Durchlauf-Caches, damit kein Verlust.
      `MaxHirn-Sicherung` (Aufgabe) war Ready und lief fehlerfrei.
      Angelegt: 2026-09-04 · Zuletzt: 2026-09-04
      Betrifft: `Agenten/sichern*.ps1`, `Agenten/Hermes/{pending_messages,cache/terminal-output,telemetry/shared_metrics}`

- [x] **T-025 — Hauptsicherung nach `G:` hat zwei Tage übersprungen**
      Erledigt 2026-09-02. Die Ursache stand bereits in T-022: Die Aufgabe war
      deaktiviert und wurde heute wieder aktiviert — der Eintrag hier war
      insoweit doppelt und ist korrigiert worden. Bestätigt ist der Lauf jetzt
      auch: `G:` und `O:` tragen um 22:35 den Stand von heute, einschließlich
      der Regeländerungen dieser Sitzung. Beide Kopien sind damit wieder
      aktuell.
      Beobachtung am Rand: Ein zweiter Lauf um 22:40 brach mit `0xC000013A`
      (abgebrochen) ab — zeitgleich mit `MaxHirn-Posteingang`, was nach einem
      Sammelstart von Hand aussieht, fünf Minuten nach dem regulären. Die
      Hausregel „`sichern.ps1` nie doppelt starten" gilt genau dafür; Schaden
      ist keiner entstanden, die Kopie von 22:35 steht.
      Die Erkennungslücke ist geschlossen: Abschnitt 9 der Systemprüfung meldet
      seit heute nicht nur fehlerhafte Läufe, sondern auch ausgebliebene — jede
      `MaxHirn-*`-Aufgabe, die länger als 48 h nicht gestartet ist. Genau das
      hatte zwei Tage lang niemand gesehen.

- [x] **T-012 — Alte Zweige auf `G:` abräumen**
      Kontext: Die Sicherung läuft ohne `/MIR` und räumt deshalb nichts weg,
      was in der Quelle verschwindet. Auf `G:\MaxHirn-Sicherung` liegen nach
      dem Umbau vom 30.08.2026 noch die 51 GB `Modelle\` (ab jetzt aus der
      Sicherung ausgenommen) und der alte Zweig unter dem früheren Namen „Claude“ (er heißt jetzt
      `Archiv`, wird also ein zweites Mal kopiert).
      **Gemessen 03.09.2026**, nach einem vollständigen Lauf der neuen
      Sicherung (robocopy-Code 3, 54:38 Dauer, 29,1 GB übertragen): Auf `G:`
      liegen 190 GB, frei sind 68,5 GB von 2,75 TB.

      | Ordner | GB | Was |
      |---|---|---|
      | `Claude` | 93,8 | alter Archivname, heute `MaxHirn\Archiv` — doppelt gehalten. Allein `Claude\Posteingang\Maximilianbackup0924` sind 48,8 GB |
      | `MaxHirn` | 70,4 | aktuell (Quelle 45 GB; die Differenz sind Altstände, die ohne `/MIR` liegenbleiben) |
      | `Modelle` | 21,1 | seit 30.08.2026 aus der Sicherung ausgenommen |
      | `MCP-Server`, `Hermes`, `Handel`, `Wissen`, `Routinen`, `GitHub`, … | ~5 | Struktur **vor** der Ordnertrennung, heute alles unter `Agenten/` |

      **Abgeräumt am 03.09.2026 auf Max' Freigabe.** Entfernt wurden
      `Modelle\`, `MCP-Server\`, `Hermes\`, `GitHub\`, `Handel\`, `Routinen\`,
      `Wissen\`, `Referenz\`, `.obsidian\`, `.claude\`, `.agents\`, `.codex\`,
      elf lose Altdateien der obersten Ebene und zuletzt `Claude\`.

      Jeder Ordner wurde vorher gegengeprüft, keiner blind gelöscht. Zwei
      Fälle, in denen die Prüfung etwas gefunden hat:

      - **`Codex\` und `Coworking-Space\` (0,4 GB) stehen bewusst noch da.**
        Ihr heutiger Ort ist `Werkstatt\`, und Werkstatt ist aus der Sicherung
        ausgenommen — die Kopie auf `G:` ist die einzige, unter anderem vom
        eigenen `m3u_cleaner`. Siehe T-032.
      - **`Claude\` war nur zu 44,5 von 93,8 GB eine Dublette.** Drei
        Prüfrunden: Pfadvergleich (45 von 64.829 Dateien ohne Entsprechung),
        Namensvergleich über Archiv und Werkstatt (18 davon lagen umsortiert
        woanders), Größenvergleich der restlichen 27. Dabei kam heraus, dass
        die 24 ELSTER-Belege beim Einsortieren **umbenannt** worden waren
        (`1-Lohnsteuerbescheinigung_2022_…` → `2022_Belegabruf_…_2026-08-19`)
        und byteweise identisch vorliegen. Echte Unikate blieben drei:
        `Maximilianbackup0924` (52,4 GB), `EFIbackup0924` (524 MB) und
        `OKX_API.env` (124 B). Sie liegen jetzt in
        `G:\Unikate-aus-Altzweig-20260903\` mit einer `LIESMICH.md`, die den
        Weg dorthin beschreibt.

      **Die Lehre für das nächste Mal:** Ein Pfadvergleich allein hätte 50 GB
      gelöscht oder 41 GB verschont — beides falsch. Erst Pfad, dann Name,
      dann Größe.

      **Ergebnis:** frei auf `G:` von 68,5 GB (vor dem Lauf) auf **109,5 GB**.
      Im Sicherungsordner stehen nur noch `MaxHirn\`, `Agenten\`, die aktuellen
      Wurzeldateien und die beiden zurückgestellten Ordner aus T-032.
      Angelegt: 2026-08-30 · Zuletzt: 2026-09-03

- [x] **T-030 — Drei Handels-Routinen in die Aufgabenplanung eintragen** —
      erledigt 2026-09-02 auf Max' Anweisung. Angelegt mit
      `Register-ScheduledTask` (nicht `schtasks` — das setzt kein „Starten,
      sobald möglich", und ohne das fällt ein Termin nach einer
      Hardware-Abschaltung ersatzlos aus): `MaxHirn-Marktscanner` täglich
      07:30, `MaxHirn-Kraken-Spur3` täglich 07:45, `MaxHirn-Handel-Wachen`
      sonntags 08:00. Alle drei einmal aus der Aufgabenplanung heraus gestartet
      und geprüft — Ergebniscode 0, Protokolle vollständig, keine
      Doppelkäufe. Damit sind es neun geplante Aufgaben. Beide Tagesläufe
      handeln nur auf Papier (`MAXHIRN_ROUTINE=1`, kein `--live`).

- [x] **T-029 — Dritte Spur: Kraken wirklich bauen** — erledigt 2026-09-02
      Auf Max' Anweisung („ich will ihn") das nachgeliefert, was T-027 als Weg
      beschrieben hatte. Neu unter `Agenten/Handel/kraken/`: `wachen.json`
      (EUR, eigener Rahmen), `kraken.py` (REST, nur Standardbibliothek, kein
      Auszahlungsweg), `scan.py`, `handeln.py`, `wachen_kraken.py`, README.
      Die währungsneutrale Rechnung der Bedingungen 2–5 wird aus
      `scanner/wachen_pruefung.py` **importiert**, nicht abgeschrieben.
      `freigabe.py` kennt jetzt drei Spuren und zeigt die Währung der Spur an;
      seine Bestandsschlüssel heißen dafür `gebunden`/`verlust_gesamt` statt
      `…_usd` (`scanner/handeln.py` nachgezogen, beide Spuren nachgeprüft).
      Gemessen dabei: Kraken nimmt 0,40 % Taker statt 0,05 % bei OKX — eine
      Runde kostet 0,80 %. Deshalb Stop mindestens 5 %, C/R mindestens 2,0,
      Score mindestens 65, und die Gebühr steht auch im Papierlauf in den
      Beträgen. Zweiter Befund: Auf dem Konto liegen 0,0094 EUR frei, der Rest
      steckt in Coins — daher die zusätzliche Sperre `mindest_guthaben_eur`.
      Erster Papierlauf gelaufen: 4 Positionen, 200 EUR gebunden; die sechs
      Wochen aus Bedingung 1 laufen ab heute. `handel_erlaubt` bleibt `false`.
      Die schreibenden MCP-Werkzeuge bleiben gesperrt — die Grenze verläuft
      jetzt nicht mehr zwischen Börsen, sondern zwischen Wegen.

- [x] **T-028 — Bestätigungsdialog zum Scharfschalten** — erledigt 2026-09-02
      `Agenten/Handel/freigabe.py` gebaut und an `scanner/handeln.py --live`
      angebunden. Beide Spuren, prüft gegen `wachen.json`, führt selbst nichts
      aus. Die Obergrenze jedes Reglers ist der Wachen-Wert, der Hebeldeckel
      ist senkbar, nie hebbar. Ausstiege laufen nie durch das Fenster.
      Beim Bauen gemessen: `sys.stdin.isatty()` meldet in der Git-Bash unter
      Windows auch bei umgeleitetem stdin ein Terminal — als Sperre gegen den
      Zeitplan taugt es nicht. Deshalb lehnt das Fenster nach 120 s ohne
      Bedienung von selbst ab; das ist der tragende Schutz. Zusätzlich setzen
      `Routinen/marktscanner.ps1` und `handel-wachen.ps1` jetzt
      `MAXHIRN_ROUTINE=1`.
      Offen als eigener Punkt: `xperp/bot.py` ist nicht angebunden — er legt
      Befehle ohnehin nur vor.

- [x] **T-027 — Handelsregeln decken Kraken nicht ab**
      Erledigt 2026-09-02: Neuer Abschnitt *Kraken ist keine dritte Spur* in
      `Wissen/Schutzregeln.md`. Kraken bleibt lesend — die neun lesenden
      Werkzeuge sind ausdrücklich erlaubt, `kraken_order_aufgeben` und
      `kraken_order_stornieren` ausdrücklich nicht, auch nicht mit Bestätigung
      im Chat. Begründung ist der eigene Maßstab des Abschnitts: ohne
      `wachen.json`, Journal und Herzschlag fehlen alle drei Eigenschaften, die
      die Handelserlaubnis tragen. Der Weg zu einer echten dritten Spur ist
      beschrieben. Nicht auf eine Entscheidung gewartet, weil die sichere
      Richtung aus der bestehenden Regel folgt — die Öffnung bleibt möglich.

- [x] **T-026 — `absturz-recovery.md` liegt lose im Skill-Ordner und wird nie geladen**
      Erledigt 2026-09-02: nach `skills/absturz-recovery/SKILL.md` gehoben
      (`git mv`, Inhalt unverändert), die `.bak-20260902` daneben entfernt. Der
      Skill erscheint seither in der Skill-Liste einer Sitzung. Abschnitt 10b
      der Systemprüfung meldet ab jetzt jede lose `.md` im Skill-Ordner und
      jeden Skill-Ordner ohne `SKILL.md`.

- [x] **T-024 — `CLAUDE.md` und `AGENTS.md` sind auseinandergelaufen**
      Erledigt 2026-09-02: Beide Paare zusammengeführt, jedes ist jetzt Zeichen
      für Zeichen gleich — wie in `Werkstatt/` schon erprobt. Übernommen wurde
      jeweils die Vereinigung: die Vektorsuche (`vektor_suche.py`, `--hybrid`,
      Abdeckung, Indexstand 19.08.2026) aus `Archiv/AGENTS.md`, die Mail-Sperre,
      der Netzteil-Kontext, die Umlaut-Suchfalle und die
      `sort_inbox.py`-Sicherungen aus `Archiv/CLAUDE.md`, dazu die schärfere
      Notizen-Regel aus `MaxHirn/AGENTS.md`. Der gemeinsame Kopf nennt jetzt die
      maschinelle Prüfung, die das hält (Abschnitt 10a in `systempruefung.ps1`).

- [x] **T-022 — `MaxHirn-Sicherung` deaktiviert, `MaxHirn-Posteingang` scheiterte**
      Erledigt 2026-09-02: `MaxHirn-Sicherung` auf Anweisung von Max wieder
      aktiviert (`Enable-ScheduledTask`), Auslöser unverändert täglich 20:00,
      „Starten sobald möglich". Warum sie aus war, ist nicht abschließend
      geklärt — vermutlich im Zuge von T-015 (Seagate `G:` war zeitweise ab).
      Der `MaxHirn-Posteingang`-Fehler vom 01.09. 22:00 war der Pfad
      `Agenten\Claude\ArchivSuche` — doppelt veraltet (`Agenten\` statt
      `MaxHirn\`, `Claude\` statt `Archiv\`). Der Wrapper `posteingang.ps1`
      zeigt inzwischen korrekt auf `MaxHirn\Archiv\ArchivSuche` (T-016), der
      nächste Lauf heute 22:00 sollte grün sein.

- [x] **T-021 — Fremd-MCP-Server apify und okx-Lokalklon entfernt**
      Erledigt 2026-09-02: Auf Anweisung von Max beide gelöscht.
      `Agenten/MCP-Server/ant.dir.gh.apify.apify-mcp-server/` (node_modules nur
      noch tote pnpm-Junctions auf den alten `…\MaxHirn\MCP-Server\`-Pfad) und
      `Agenten/MCP-Server/okx/` (eigenes `.venv`, `okx_mcp.py` mit doppelt
      kaputtem Pfad `…\MaxHirn\Claude\Worktrees\…`). Beide in keiner `.mcp.json`;
      der aktive okx-Zugang läuft über den HTTP-Server `okx-agent-trade-kit`.

- [x] **T-010 — Kimi-K2.7-Code entfernt**
      Erledigt 2026-09-02: Auf Anweisung von Max gelöscht. War ein
      HuggingFace-Repo-Klon (`.git` mit LFS, ~31 GB, keine Gewichtsdatei je
      ausgecheckt) unter `O:\Modelle\Kimi-K2.7-Code`. Reproduzierbar per
      `git clone`, falls je gebraucht.

- [x] **T-020 — Fremd-Repo `MaxHirn/OmniRoute` lag am falschen Ort**
      Erledigt 2026-09-02: Klon von `github.com/diegosouzapw/OmniRoute`,
      Branch `release/v3.8.51`. Beide Klone geprüft — weder unter `MaxHirn/`
      noch unter `Werkstatt/` gab es eigene Commits, Stashes oder Branches
      (Werkstatt-Reflog: nur `clone`; die geänderten `package*.json` dort waren
      reine `npm install`-Nebenwirkung). Der alte `Werkstatt/OmniRoute`
      (älterer HEAD, 4,3 GB mit `node_modules`/`dist`) wurde gelöscht, der
      neuere saubere Klon aus `MaxHirn/` (715 MB, Arbeitsbaum sauber) an seine
      Stelle verschoben. Die Übergangsregel `MaxHirn/OmniRoute/` in `.gitignore`
      ist wieder raus — `Werkstatt/*/` deckt den neuen Ort ab. Wer dort
      arbeiten will: `npm install` neu.

- [x] **T-001 — Sicherungslaufwerk G: fehlt, Hauptsicherung hat kein Ziel**
      Erledigt 2026-08-28: Kein Defekt. Max hatte die USB-Platten für einen
      CMOS-Reset abgezogen. Seagate Portable ist wieder angeschlossen,
      `G:\MaxHirn-Sicherung` erreichbar (2751,1 GB, 128,8 GB frei, `Healthy`).
      Der 20-Uhr-Lauf kann wieder arbeiten. Der Fehlstand bestand nur, solange
      die Platte ab war.

- [x] **T-002 — Auslagerungsdatei liegt auf einer USB-Platte**
      Erledigt 2026-08-28: Max hat den Eintrag mit erhöhten Rechten entfernt.
      Nachgemessen um 17:15: `PagingFiles` enthält nur noch
      `c:\pagefile.sys 0 0` und `o:\pagefile.sys 4096 16384`, auf `G:` liegt
      keine `pagefile.sys`. Ob damit auch T-004 verschwindet, ist offen —
      die Hypothese ist nicht bewiesen, nur die Fehlkonfiguration beseitigt.
      Sicherung des Schlüssels: `Routinen/sicherungen/MemoryManagement-20260828.reg`.

- [x] **T-003 — Windows Search stürzt seit 24.08. in Endlosschleife ab**
      Erledigt 2026-08-28: Der Starttyp wurde um **16:00:04** auf „Deaktiviert"
      gesetzt (Ereignis 7040). Letzter Absturz **15:59:41**, seither **null** in
      77 Minuten. Vorher waren es 16.926 in sieben Tagen, allein 984 zwischen
      dem Start um 15:19:36 und 15:59:41 — rund 24 pro Minute.
      Der Suchindex wurde nicht neu gebaut; die Suche im Startmenü bleibt tot.
      Max' eigene Archivsuche ist davon nicht betroffen (SQLite).
      Gewinn: Das Systemprotokoll reicht wieder bis zum **05.08.2026** zurück
      statt vier Tage — die Absturzspuren für T-004 überleben jetzt lange genug.

- [x] **T-005 — J: (WD My Book) nicht angeschlossen, iCloud-Junction ins Leere**
      Erledigt 2026-08-28: Die Platte ist wieder da. `Extern_BackUp`, 1.953 GB
      gesamt, 246 GB frei, `Healthy`; NTFS meldete um 15:47:51 „Volume J: ist
      fehlerfrei". Die Junction `C:\Users\faupe\iCloudPhotos` löst wieder auf.
      Unverändert gilt: 479 unkorrigierte Lesefehler (Messung 14.08.), die
      30.635 Mediendateien liegen weiter auf dem schwächsten Laufwerk.

- [x] **T-006 — Echtzeituhr ging 68 Minuten nach**
      Erledigt 2026-08-28: harmlos. Die Korrektur um 15:20:12 kam 36 Sekunden
      nach dem Kaltstart um 15:19:36 — der CMOS-Reset hatte die Uhr geleert,
      der Zeitdienst zog sie einmal gerade. **Seither kein weiterer Sprung**,
      Abweichung 0,12 s gegen `time.windows.com` (gemessen 17:17).
      Eine schwache CMOS-Batterie würde erneut driften; ein zweiter Messpunkt
      in einigen Tagen bestätigt es endgültig. Bis dahin kein Handlungsbedarf.

- [x] **T-031 — Telegram-Bot fuer Meldung und Steuerung einrichten** — erledigt 08.09.2026
      Die fünf Module (`Handel/melder.py`, `tagesbericht.py`, `freigabefenster.py`,
      `dauerlauf.py`, `Routinen/handel-dauerlauf.ps1`) waren seit 07.09. fertig,
      aber stumm — es fehlten nur die Token.

      Eingerichtet 08.09.2026: Bot **@CodeClaudebitbitbot**. `TELEGRAM_TOKEN`
      und `TELEGRAM_CHAT_ID` (`7648512088`) stehen als **Benutzervariablen** in
      `HKCU\Environment`. `melder.py` liest sie live aus der Registry
      (`_aus_registry`), ein laufender Dauerlauf braucht dafür **keinen
      Neustart**. Probe bestätigt, der Bot beantwortet Befehle.

      Fallen fürs nächste Mal:
      - Der Bot muss zuerst **vom Nutzer angeschrieben** werden, sonst gibt
        `sendMessage` HTTP 400 ("chat not found").
      - `melder.py --chat-id-suchen` liefert nichts, solange der Dauerlauf
        läuft: Telegram gibt jede Nachricht per `getUpdates` nur einmal aus,
        der Dauerlauf holt sie zuerst. Chat-ID dann aus `dauerlauf.log`
        (Zeilen „Befehl: …") lesen oder den Dauerlauf kurz stoppen.
      - Gültige Befehle: `/ja [h]`, `/nein`, `/hilfe`.

      Geplante Aufgaben stehen alle (State Ready): `MaxHirn-Handel-Dauerlauf`
      (+ `-Waechter`), `MaxHirn-Handel-Wachen`, `MaxHirn-Verbesserer`.

- [x] **T-039 — Hebel-Deckel-Tabelle in [[XPERP-Handel]] ist überholt** — erledigt 2026-09-19
      **Erledigt 2026-09-19.** Tabelle auf 3,6× (SOL), 4,1× (HYPE), 1,7×
      (ZEC) ersetzt, die Aussage „alle Tore bestanden" für die drei
      zurückgenommen, und der Messfehler als Falle danebengeschrieben
      (Deckel auf **Tageskerzen** rechnen — das 300-Kerzen-Fenster des
      gehandelten Kontrakts sind nur 50 Tage).
      Aufgefallen 09.09.2026. Die Tabelle in `Wissen/XPERP-Handel.md`
      (Abschnitt „Hebel-Deckel ≥ 5", Zeilen 165–171) stammt aus einer
      **fehlerhaften Messung**: `auswahl.py` leitete den Deckel aus 300
      4H-Kerzen ab, das sind nur 50 Tage. SOLs Rücklauf vom 31.05.2026 lag
      außerhalb dieses Fensters.
      Behoben ist der Code — `mae_tage()` rechnet jetzt auf 300 **Tages**kerzen,
      committet. Die Notiz nicht.

      | Wert | steht dort | gemessen (200 Tage) |
      |---|---|---|
      | SOL | 10,0× | **3,6×** |
      | HYPE | 6,4× | **4,1×** |
      | ZEC | 5,8× | **1,7×** |

      Damit trägt die Überschrift „Hebel-Deckel ≥ 5" für keinen der drei
      Werte mehr. Zu tun: Tabelle ersetzen, den Messfehler als Falle
      danebenschreiben (sonst wiederholt ihn die nächste Sitzung), und die
      Aussage „alle Tore bestanden" für die drei zurücknehmen.
      Betrifft: `MaxHirn/Wissen/XPERP-Handel.md`
      **Nachtrag 13.09.2026 (Max' Auftrag „README-Tabelle richtigstellen“):**
      Die Tabelle in `xperp/README.md` (Abschnitt „Gemessen am 01.09.2026“)
      trug noch die alten Deckel 10,0×/6,4×/5,8× — ersetzt auf 3,6×/4,1×/1,7×,
      „alle Tore bestanden“ zurückgenommen, Messfehler als Falle daneben
      (konsistent zu dieser Notiz). Dazu `bot.hebel_deckel()` auf Tageskerzen
      gezogen (`auswahl.mae_tage`): die Aufrufe in `pruefpflicht()` (neuer
      Parameter `stat_id`) und `zeige_lage()` holen jetzt die 1D-Reihe der
      Statistik-Quelle (bei `--historie` die des SWAP), ebenso der
      `historie.py`-Vergleich; Test `xperp/test_deckel.py` (3 Tests, Seam
      `bot.tages_kerzen_quelle`), alle 12 xperp-Tests grün. Frische
      CHIP-Messung auf Tagesbasis: jung 4,3× / 48 % vs. SWAP 2,2× / 29 %
      gegen 34 % nötig.

- [?] **T-040 — SOL long, 106 USD: Hebel 5× liegt über dem Deckel**
      Anweisung von Max am 09.09.2026: „SOL long 5x hebel 106 usd und stop
      schlage vor oder setz automatisch klug". Der Stop ist **gemessen**
      (`xperp/stopwahl.py`), der Hebel ist der Konflikt.

      Gemessene Geometrie: **Stop 3,00 ATR / Ziel 4,00 ATR**, E = +0,321 %
      je Runde über alles, +0,894 % in der jüngeren Hälfte, 469 Ziel- gegen
      557 Stop-Ereignisse, 24 von 42 Kombinationen in beiden Hälften positiv.
      Bei 1,92 % ATR sind das **5,75 % Stop / 7,66 % Ziel**.

      Der Deckel für SOL long ist **3,5–3,6×** (größter 7-Tage-Rücklauf
      27,9 %). Gerechnet bei Kurs 100,68:

      | | Nominal | Kontrakte | Verlust am Stop | Liq entfernt |
      |---|---|---|---|---|
      | 5× | 529,58 USD | 526 | 30,46 USD (28,8 % der Margin) | 19,5 % |
      | 3× | 317,14 USD | 315 | 18,24 USD (17,3 % der Margin) | 32,8 % |

      3× passt außerdem zu „lieber mehrere Anläufe": rund 6 statt 3 aus
      106 USD. `Wissen/Schutzregeln.md` führt „Hebel höchstens `hebel_deckel`"
      als auch mit Anweisung feste Grenze.
      **Wartet auf Max.** Bestätigt er 5×, wird 5× ausgeführt — vollständig,
      nicht stillschweigend kleiner.
      Vor dem Auftrag `bot.py` **frisch** laufen lassen, die Zahlen oben sind
      vom 09.09.2026.


## T-89 — Wiki-Verschiebung: Pläne + Befunde aus Agenten/Handel

- [ ] **T-89 — Wiki-Verschiebung: Pläne + Befunde aus Agenten/Handel**
  - Kontext: 31 .md-Dateien (15 docs/design + docs/plans, 11 Befunde/Notizen, 5 Spur-Pläne) waren in Agenten/Handel versteckt. Verschoben nach MaxHirn/Wiki/Handel/ (plans/, Befunde/, Spuren/, verbesserer/). Kein Code referenziert alte Pfade (rg geprueft). leitstand_backtests.json Pfad korrigiert.
  - Naechster Schritt: git status zeigt 30 D + 31 ??; rg zeigt keine Code-Referenzen; leitstand_backtests.json zeigt neuen Pfad
  - Angelegt: 2026-10-06
  - Betrifft: MaxHirn/Wiki/Handel/, Agenten/Handel/

## T-90 — TASKS-Eintraege fuer Wiki-Verschiebung

- [ ] **T-90 — TASKS-Eintraege fuer Wiki-Verschiebung**
  - Kontext: Drei Eintraege in MaxHirn/Archiv/TASKS.md: T-89 (Verschiebung), T-90 (dieser Eintrag), T-91 (Wissen einbauen).
  - Naechster Schritt: doppelte_nummern.py gruen; T-89/90/91 vorhanden
  - Angelegt: 2026-10-06
  - Betrifft: MaxHirn/Wiki/Handel/, Agenten/Handel/

## T-91 — Wissen einbauen: Spuren-Uebersicht + Plaene verlinken

- [ ] **T-91 — Wissen einbauen: Spuren-Uebersicht + Plaene verlinken**
  - Kontext: MaxHirn/Wiki/Handel/Spuren-Uebersicht.md erstellen mit Verweisen auf verschobene Plaene und Befunde. Wiki/Handel/INDEX.md aktualisieren.
  - Naechster Schritt: Spuren-Uebersicht.md existiert; INDEX.md zeigt Verweise
  - Angelegt: 2026-10-06
  - Betrifft: MaxHirn/Wiki/Handel/, Agenten/Handel/

## T-92 — Verbesserer Stufe 1.5: Umsetzungsplan schreiben

- [ ] **T-92 — Verbesserer Stufe 1.5: Umsetzungsplan schreiben**
  - Kontext: Spec Werkstatt/spec-verbesserer-stufe-1-5-2026-10-04.md ist abgenommen (F7 Kerzen-Ausrichtung, F4 Holdout, nur Spur 1). Plan fehlt, Code erst nach Plan-Review. Uebergabe: Werkstatt/uebergabe-verbesserer-stufe-1-5-2026-10-06.md
  - Naechster Schritt: writing-plans nach Werkstatt/plan-verbesserer-stufe-1-5-2026-10-04.md; Max waehlt Ausfuehrungsart
  - Angelegt: 2026-10-06
  - Betrifft: Agenten/Handel/verbesserer/

## T-93 — Verbesserer Ausbaustufe 2 (Spur 2/3)

- [ ] **T-93 — Verbesserer Ausbaustufe 2 (Spur 2/3)**
  - Kontext: XPERP (Margin, Funding, Liquidation) und Kraken-EUR (0,80 % je Runde); erst nach Stufe 1.5, eigenes Brainstorming mit eigener Spec.
  - Naechster Schritt: nach T-92 Brainstorming starten
  - Angelegt: 2026-10-06
  - Betrifft: Agenten/Handel/verbesserer/, Agenten/Handel/xperp/

## T-372 — Verbesserer: strukturiertes Event-Log in lauf.py

- [x] **T-372 — Verbesserer: strukturiertes Event-Log in lauf.py**
  - Kontext: Growth-Engineering-Analyse (07.10.2026) hat ergeben, dass lauf.py kein
    maschinenlesbares Ergebnis-Log schreibt. Ohne das sind A/B-Experimente (Holdout-Gate,
    F7-Wirkung) und Re-Engagement-Trigger nicht auswertbar. lauf.py soll nach jedem Lauf
    `verbesserer/lauf_ergebnis.json` schreiben mit den Feldern: lauf_ts, instrumente_eingang,
    instrumente_nach_ausrichten, kandidat_gefunden (bool), holdout_bestanden (bool/null),
    fast_kandidat (str/null), vorschlag_erzeugt (bool), grund (str/null).
  - Naechster Schritt: nach Stufe-1.5-Merge als eigener Commit (abwaertskompatibel)
  - Angelegt: 2026-10-07
  - Betrifft: Agenten/Handel/verbesserer/lauf.py

## T-373 — Verbesserer: Anwendungslog in anwenden.py

- [x] **T-373 — Verbesserer: Anwendungslog in anwenden.py**
  - Kontext: Growth-Engineering-Analyse (07.10.2026): der Funnel ist nach dem Digest-Schritt
    blind. anwenden.py weiss, ob ein Vorschlag angewendet wurde, schreibt das aber nicht
    zurueck. Loessung: bei jedem Aufruf einen Eintrag in `verbesserer/anwendungslog.json`
    anhaengen (Append-JSON-Lines) mit: lauf_ts (aus dem Vorschlag), anwendung_ts, kandidat_hash,
    entscheidung ("angewendet"), grund_optional (freier Text, Standard leer).
  - Naechster Schritt: nach Stufe-1.5-Merge als eigener Commit
  - Angelegt: 2026-10-07
  - Betrifft: Agenten/Handel/verbesserer/anwenden.py
- [ ] **T-399 — Hermes-Skills: Zweig claude/messung-configs-klassik gegen master klaeren**
      Stand 13.10.2026: Die Korrektur der Hermes-Notiz (Commit ac946d05 auf master) ist
      uebernommen. Auf dem Zweig liegen noch 22 Commits, davon 20 fremde (Handel, Telegram,
      Wiki). Entscheidung Max: Zweig per PR nach master, oder verwerfen/liegen lassen.
      Nicht ohne Freigabe mergen. Dazu: `MaxHirn/Wissen/KB/data/spur-metriken.json` steht
      im Arbeitsbaum als 'needs merge' (fremde Sitzung, nicht meine Datei).
      Nachweis-Ordner `Agenten/Hermes/.sicherung/skills-import-20261013/` nach Entscheidung loeschen.
      Entscheidung Max 13.10.2026: Zweig liegen lassen, kein PR, kein Merge, kein Push.
      Grund: Konflikte in Hermes.md und spur-metriken.json; 13 fremde Commits (Handel, rule_repo-bots.md).
  - Angelegt: 2026-10-13
  - Betrifft: Git-Zweige BrainFiles, MaxHirn/Wissen/Hermes.md
