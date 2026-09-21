---
name: fremd-agenten-betrieb
description: "Fremd-Agent-Repos ohne bezahlte Schluessel lokal betreiben."
category: brainfiles
---

# Fremd-Agenten-Betrieb

Fremde LLM-/Trading-Agenten-Repos (z. B. moon-dev-ai-agents) verlangen im
Original bezahlte API-Keys. Hausstandard: schluessellos — Urteil vom lokalen
Ollama, Marktdaten ueber oeffentliche API-Endpunkte, Autostart als geplante
Aufgabe. Hier: der Weg vom ersten Startfehler zum laufenden Dauerlaeufer.

## Start (in dieser Reihenfolge)

1. **Als Modul starten, nicht als Skriptpfad.** Scripte, die Paket-Imports
   machen (`import src.config`), nur als `python -m src.agents.<name>` aus dem
   Repo-Root — `python pfad/zu/skript.py` setzt `sys.path[0]` auf das
   Skriptverzeichnis und wirft `ModuleNotFoundError: No module named '<paket>'`.
2. **.env in die Prozessumgebung bringen.** Einzel-Agenten laden Dotenv oft
   nicht (nur der Repo-`main.py` tut das) und werfen hart bei jedem fehlenden
   Key. Beim Start exportieren, CRLF-sicher:
   `export OLLAMA_MODEL=$(grep '^OLLAMA_MODEL=' .env | cut -d= -f2 | tr -d '\r')`
   — ebenso `OLLAMA_BASE_URL`. Fehlt `load_dotenv()` im Skript, hilft ein
   Patch nichts, nur die Umgebung.
3. **Lokales Modell statt Key-Zwang.** OpenAI-SDK gegen Ollama:
   `openai.OpenAI(api_key="ollama", base_url=...)`.
   - base_url MUSS auf `/v1` enden (OpenAI-kompatible API); endet die .env auf
     `/api` (native Ollama-API), schlaegt der Call fehl. Robust:
     `(os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434/v1").replace("/api", "/v1")`.
   - Der Analyze-Pfad muss `chat.completions.create(...)` nehmen. Agenten mit
     `if "deepseek" in model ... else anthropic` brauchen den Ollama-Zweig
     VOR dem DeepSeek-Zweig — `anthropic.messages.create` ist gegen Ollama
     falsch und faellt erst auf, sobald die Daten laufen.
   - `model=` bekommt den OLLAMA-Modellnamen (z. B. `qwen35-8k:latest`),
     nicht den Repo-Modellnamen; `AI_MODEL` entsprechend vorbelegen.
4. **Pro-Endpoints ersetzen, nicht kaufen.** Fehler 10005
   („limited to PRO API subscribers") = Endpoint exklusiv; oeffentliche
   Alternative suchen. Oft existiert der oeffentliche Weg schon im Haus
   (Agenten/Handel/moondev_daten.py: `/coins/markets`; UA-Pflicht siehe
   Punkt 6). Oeffentliche Rate-Limits einrechnen:
   Kandidaten auf `head(3)` begrenzen, `DELAY` ~10-12 s, bei 429 15 s warten
   und einmal wiederholen. Ein- und Ausgabespalten an die Erwartung des
   Codes angleichen (`rename`: current_price→usd, ...), sonst crasht die
   CSV-Zusammenfassung am Schema — Summary zusaetzlich try/except-kapseln.
   Alte Ergebnis-CSVs aus dem Repo-Klon haben ein fremdes Schema: loeschen
   (`git rm -f`), damit der neue Header frisch entsteht.
5. **Unicode unter Windows-Aufgabenplanung.** Vom PowerShell-Wrapper
   gestartet, laeuft Python unter cp1252 und bricht beim ersten Emoji-print
   mit `UnicodeEncodeError: 'charmap'` ab (aus git-bash lief es, weil MSYS
   UTF-8 setzt). VOR `Start-Process`
   `$env:PYTHONIOENCODING='utf-8'` setzen.
6. **Tote Repo-Endpoints ersetzen, nicht reparieren.** Der sniper_agent aus
   moon-dev-ai-agents hing an `api.moondev.com:8000/files/new_token_addresses.csv`
   (tot, kein Zugriff). Ersatz: die oeffentliche Pump.fun-API
   `frontend-api-v3.pump.fun/coins?sort=created_timestamp&order=DESC` liefert
   die neuesten Solana-Launches (kein Schluessel). Die Spalten auf das vom
   Rest des Codes erwartete Schema abbilden (hier: Token Address / Epoch
   Time / Time Found / Birdeye Link), damit nur die eine Funktion angefasst
   wird. Werkstatt/Repos ist gitignored - Aenderung per Staging-Kopie in der
   BrainFiles-Wurzel patchen, py_compile + Kurzlauf, dann `cp` zurueck und im
   Fork committen/pushen (voller Klon, origin=Fork).
7. **Two-key trading agents: run them paper with the live path gated.** Ein
   LLM-Trading-Agent verlangt oft ZWEI getrennte bezahlte Abhaengigkeiten:
   einen Marktdaten-Provider (Birdeye) UND eine Ausfuehrungs-Wallet
   (Solana). Der minimale, schluessellose Umbau — Papier lauffaehig, Live-
   Weg eingebaut aber gesperrt:
   - **Key-abhaengige Imports lazy machen.** Manche Module verweigern schon
     den IMPORT hart (ein fehlender `BIRDEYE_API_KEY` wirft `ValueError` beim
     `import nice_funcs`), nicht erst den Aufruf — der Agent startet dann
     ohne Key nie. Key-abhaengige `from ... import ...` hinter einer
     `_lade()`-Funktion ziehen, die NUR bei Live-Freigabe triggert; der
     Papier-Modus braucht sie nicht. Wo es geht, einen lokalen Papier-
     Ersatz (leeres Dict) bereitstellen statt den Import zu erzwingen.
   - **Marktdaten-Schritt schuetzen.** `collect_all_tokens()`-Zug
     try/except-kapseln; bei fehlendem Provider leeres Dict -> der Agent
     entscheidet NOTHING, kein Abbruch.
   - **JEDE echte Order hinter die Haus-Freigabedatei.** `ai_entry`/`chunk_kill`/`market_buy`
     sind echte Wallet-Orders. VOR jeden Aufruf gesperrt einbauen: eine
     Haus-Datei ausserhalb des Repos (z. B. `Agenten/Handel/<agent>_freigabe.json`
     mit `{"handel_erlaubt": false}`) steuert den Live-Weg; fehlt sie oder
     ist false, protokollieren die Aufrufe nur (`continue`). Der Repo-Klon
     traegt die Freigabe nie. Das ist ein DISTINKTER Modus vom „Endpoint
     ersetzen": die echten Order-Aufrufe bleiben im Code, sind aber an die
     Haus-Freigabe gekettet statt an einen anderen Endpoint gespiegelt.
   - **Die Sperre muss VOR dem Provider-Zugriff stehen, nicht daneben.**
     `n.get_token_balance_usd()` (n=Provider, lazy=None ohne Key) crasht
     BEVOR eine nachgelagerte Papier-Sperre greift. Die Freigabe-Sperre
     (`if PAPIER or not _freigabe_erlaubt(): ... continue`) gehoert an den
     ANFANG der Schleife, vor jeden `n.`-Zugriff — nicht erst vor den
     Order-Aufruf. Sonst faellt der Agent ohne Key auf jeder Zeile um.
   - **think:false gegen qwen35 ist NUR ueber die native API moeglich.**
     Ein Denk-Modell (qwen35) liefert ueber den OpenAI-/v1-Adapter einen
     LEEREN content (`'_'`), egal ob `extra_body={'think': False}` gesetzt
     wird — Ollama reicht den Parameter dort nicht durch. Der einzig
     funktionierende Weg ist der native POST an `http://127.0.0.1:11434/api/chat`
     (kein /v1) mit `{"think": false, "options": {...}}` im JSON-Body,
     Antwort `roh["message"]["content"]` (Haus-Muster `llm_lokal.py`).
     Verdrächtig: leere content + stille 0.50-Antwort = Adapter schluckt
     think. Als Modul-Import `import urllib.request`.
     - **Marktdaten-Ersatz: OHLCV als Indikatoren-Summary, nicht als rohe
       Kerzen.** Ein Agent, dessen Analyse-Provider (Birdeye) fehlt, faellt
       sonst immer NOTHING. Es reicht nicht, Listing-Metadaten (Marktwert/
       Liquiditaet) zu liefern — der Prompt will MA20/MA40/RSI/Volume. Die
       oeffentliche `swap-api.pump.fun/v2/coins/<mint>/candles?interval=1h&
       createdTs=<now_ms>` liefert echte OHLCV-Kerzen ohne Schluessel. Aber
       rohe Kerzen IN den Prompt zu schreiben sprengt den Kontext (48 Kerzen
       x 6 Felder ≈ 10k Zeichen > 8k qwen35-8k → HTTP 400). Richtig:
       Indikatoren deterministisch IM CODE rechnen (MA20/MA40, RSI14,
       Kurs-zu-MA, Volumen-Trend; Haus-Muster `llm_lokal.py` „Indikatoren
       rechnen, Modell urteilt") und nur die kompakte Summary + letzte 8
       Kerzen ans Modell geben. Analyse und Allocation muessen dieselben
       Tokens sehen (fest konfigurierte MONITORED_TOKENS, tote mit 0 Kerzen
       uebersprungen) — nicht Analyse auf frische Launches, Allocation auf
       die Konfigurationsliste.
       - **Pump.fun-Token-Auswahl fuer einen Trader.** `coins?sort=created_timestamp&
       order=DESC` liefert NUR brandneue 0h-Launches (zu jung fuer OHLCV).
       Etablierte, liquide Tokens: `coins?offset=..&limit=200&sort=market_cap&
       order=DESC` (erlaubte sort: created_timestamp, market_cap,
       ath_market_cap, reply_count, last_reply, last_trade_timestamp).
       OHLCV via `swap-api.pump.fun/v2/coins/<mint>/candles?interval=1h&
       createdTs=<now_ms>`; nur Tokens mit >=40 Kerzen nehmen (MA20/MA40
       brauchen Historie), tote (0 Kerzen) ueberspringen. `real_sol_reserves`
       ist in Bonding-Curve-Einheit, /1e6 = echte SOL. KEIN Feld liquidity".
       Der Metadaten-Einzelendpoint `/coins/<mint>?details=true` ist 404 -
       Symbol-Map stattdessen aus der coins-Liste bauen.
       - **subprocess.PIPE schluckt die Agenten-Ausgabe still.** Ein Dauerlauf-
       Driver, der Kinder mit `stdout=subprocess.PIPE` startet und die Pipe
       NIE liest (nur `stderr` beim Absturz), verliert die komplette
       Analyse-/Empfehlungs-Ausgabe ins Nichts — die Empfehlungen einer
       Papier-Spur sind dann unsichtbar. Fix: pro Kind eine angehaengte
       Log-Datei oeffnen und `stdout=<datei>, stderr=subprocess.STDOUT`
       uebergeben; der Absturz-Tail liest dieselbe Datei (tail 1500). So
       landen Urteile dauerhaft auf der Platte UND sind beim Absturz lesbar.
   - **Haus-Ordner als Umgebungsvariable an Kinder injizieren.** Ein
     Agent, der in den Haus-Ordner schreiben soll (CSV-Export der
     Empfehlungen), kann den echten Pfad nicht zuverlaessig selbst
     ableiten (sein `__file__` liegt im Repo-Klon, Freigabe-/Pfad-
     Berechnungen landen im falschen Ordner). Der Dauerlauf-Driver
     injiziert `MOONDEV_HAUS_DIR=<HIER>` (der Agenten-Ordner) in die
     Kind-Umgebung; der Agent schreibt dort und faellt zurueck auf eine
     relative Herleitung. Verifiziert im echten Lauf: 5 Tokens mit voller
     Begruendung in `<haus>/moondev_trading_empfehlungen.csv`.
8. **Oeffentliche Boersen-/Markt-APIs per urllib ansprechen.** OKX, Kraken
   und Binance weisen einen fehlenden oder generischen User-Agent mit 403
   ab — ein voller Browser-UA-String (z. B.
   `Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/126.0 Safari/537.36`)
   ist Pflicht, gilt fuer alle drei Boersen und fuer CoinGecko gleichermassen.
   Bei POST mit JSON-Body (Solana-RPC, Kraken-Private-Endpoints) zusaetzlich
   `Content-Type: application/json` EXPLIZIT setzen — urllib schickt ihn
   nicht automatisch mit, sonst `415 Unsupported Media Type`.

## Autostart als geplante Aufgabe

- Wrapper nach `Agenten/Routinen/` (Bus-Meldungen `Melde-Start`/`Melde-Ende`,
  Log nach `logs/`, Ein-Instanz-Sperre per CommandLine-Match statt PID-Datei,
  `Start-Process` mit `-RedirectStandardOutput`/`-Error` auf GETRENNTE Dateien
  — dieselbe Datei fuer beides schlaegt fehl).
- **Registrieren braucht Elevation.** `Register-ScheduledTask` und
  `schtasks /Create` scheitern aus der Agent-Session mit 0x80070005 (kein
  interaktives Benutzer-Token). Muster: einmaliges Setup-Skript per
  `Start-Process powershell -Verb RunAs -WindowStyle Hidden -File <setup.ps1>`
  ausloesen (UAC-Dialog, der Nutzer klickt), danach READEND pruefen
  (`Get-ScheduledTask`). Bei Handy-Fernsteuerung nicht blind lostreten.
- Settings, die einen Dauerlaeufer am Leben halten:
  `-ExecutionTimeLimit ([TimeSpan]::Zero)` — der Default (72 h) beendet ihn;
  `-MultipleInstances IgnoreNew`; Trigger `AtLogOn` mit
  `$trigger.Delay='PT2M'`; Aktion mit `-WindowStyle Hidden`.
- Verifizieren statt glauben: Prozess lebt (CommandLine-Match), Wrapper-Log
  endet mit „ENDE ok", Agent-Log hat frischen Inhalt, Ausgabedateien tragen
  neue Zeitstempel. Ein erfolgreicher Start-Process beweist nichts.

## Werkstatt-Schreibzugriff

Repos unter `Werkstatt/Repos/` sind Junctions nach O: — `patch`/`write_file`
verweigern dort mit „outside HERMES_WRITE_SAFE_ROOT". Zwei Muster, je nach
Aufgabe:

- **Chirurgischer Einzeiler in einer bestehenden, versionsrelevanten Datei:**
  Wegwerfskript unter `Agenten/Hermes/cache/` (innerhalb der Root) ablegen,
  ausfuehren, loeschen. Skriptmuster: Roh-Bytes lesen, Zeilenende aus der
  Datei ableiten (CRLF pruefen) und beim Schreiben beibehalten, exakte
  Zeilen-Bloecke ersetzen (Treffer muss exakt 1 sein), danach `py_compile`
  + `git diff --stat` als Pruefung. Nie eine Textdatei per Rewrite neu
  schreiben (LF/CRLF). Fuer MEHR als eine Stelle: alle Ersetzungen als
  EIN skriptgepruefter Batch schreiben, NICHT verschachtelte `patch`-Aufrufe
  stapeln — `patch` driftet bei `\n` (Escape-drift) und stapelt Tippfehler
  (\(`messagese`, doppelte `if`-Keywords, falsche Einrueckung) in mehreren
  Runden auf. Der `assert text.count(alt)==1`-Waechter faengt einen falschen
  Block SOFORT statt eine zerschnittene Datei zu hinterlassen; bei
  Treffer 0 die Datei mit `read_file` neu lesen und das Muster am ECHTEN
  Text ausrichten, nicht daran weiterraten.
- **Neue Datei anlegen oder mehrfach iterieren (z. B. ein GUI-Skript):**
  einfacher per Staging-Kopie — Datei ganz normal mit `write_file`/`patch`
  an einem Pfad INNERHALB der Safe-Root (z. B. direkt in der BrainFiles-
  Wurzel) anlegen/aendern, nach jeder Aenderung per
  `terminal("cp <staging-pfad> <Werkstatt-Zielpfad>")` synchronisieren und
  dort mit `py_compile` sowie einem echten Kurzlauf pruefen. Staging-Datei
  am Ende loeschen. Werkstatt/Repos ist ohnehin komplett `.gitignore`t —
  die CRLF/git-diff-Sorge des ersten Musters entfaellt hier.

## Weiterfuehrend

- Ein GUI-Kontrollzentrum (Tkinter) fuer so ein Repo bauen (Boersendaten,
  Agenten-Start/Stop, Wallet, Doku-Browser): `references/gui-kontrollzentrum.md`.

## Abgrenzung

- Forks/Klone anlegen, Bots je Repo, Shallow-Push, Telegram-Anbindung:
  `repo-flotte`
- Haus-Handelsspuren aus solchen Repos bauen: `handel-spuren`
  (Hinweis: SKILL.md ist am Groessenlimit — Ergaenzungen dort verweigert)
