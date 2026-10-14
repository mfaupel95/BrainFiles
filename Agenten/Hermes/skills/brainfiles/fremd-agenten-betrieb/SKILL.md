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

## Vor dem Installieren: Anspruch gegen Inhalt pruefen

Ein Repo-Name und eine README versprechen regelmaessig mehr, als im Baum liegt.
Erst zaehlen, dann eine Installation zusagen — die Pruefung kostet zwei Aufrufe:

- `gh api repos/<owner>/<repo>/contents --jq '.[] | .type + "  " + .name'` und
  `gh api repos/<owner>/<repo> --jq '{size_kb:.size, zweig:.default_branch}'`.
  Wenige KB, EIN Commit („Initial commit: Complete …") und die Dateisammlung
  `.env.example` + `docker-compose.yml` + `config.json` + leere Ordner sind die
  Signatur eines Bauplans, nicht eines Systems.
- **`.gitkeep`-Ordner sind kein Code.** Bestehen die Dienstordner nur aus
  `.gitkeep`, existieren die Dienste nicht. Ein `docker-compose.yml`, dessen
  `build.context` auf Ordner ohne `Dockerfile` zeigt, kann gar nicht hochkommen —
  hoch kommen nur die reinen `image:`-Dienste (redis, postgres). `./start.sh`
  ist dann ein Skript, das in einen Abbruch laeuft.
- **Der Name kann ein echtes Einzelstueck enthalten, das nicht im Repo liegt.**
  Namen zerlegen und jeden Teil an seinem eigenen Upstream pruefen: Klon des
  echten Projekts, dann messen (Parameterzahl, Lizenz, Paper/Konferenz,
  Geraetebedarf) und genau das als Ergebnis melden — nicht die Fassade davor.
  Ein leerer Rahmen mit einem klangvollen Namen ist kein Grund, die fehlenden
  Dienste nachzubauen.
- **Ein `.env.example`, das Wallet- oder Boersen-Geheimnisse verlangt**
  (`PRIVATE_KEY`, Broker-Keys, Chain-IDs), gehoert als Befund in die Antwort:
  davon wird nichts verdrahtet, kein Live-Pfad, keine Order ausserhalb der
  Haus-Freigabekette. Auch nicht, wenn die README darum bittet.
- Klon-Konvention (origin=Fork, upstream=Original, shallow) und Bots je Repo:
  Skill `repo-flotte`.

## Nachweis der Anbindung (bevor etwas verdrahtet wird)

- **Den schluessellosen Kernpfad EINMAL echt fahren und die Zahlen nennen** — die
  Testsuite allein belegt die Anbindung nicht. Muster solcher Repos:
  `init` (Zustand/Datenbank) -> Discovery aus einer kostenlosen Liste -> ein
  echter Lese-/Erfassungslauf -> Bericht. Belegte Groessen aus einem solchen Lauf:
  wie viele Objekte gefunden, wie viele echte Datensaetze gelesen, wie viele
  externe Aufrufe, wie viele Fehler. Ein laufender Pfad mit Zahlen schlaegt jede
  Beschreibung des Pfades.
- **Die Status-/`init`-Ausgabe des Repos LESEN und zitieren.** Sie nennt selbst,
  welche Schluessel fehlen und welche Wege dadurch tot sind. Steht dort ein
  Schluessel als „set", heisst das nur vorhanden — ob er traegt, sagt erst ein
  echter Aufruf (siehe „Schluessel messen, nicht annehmen").
- **Erst danach einordnen, was das fuer den Hausbetrieb ist.** Gleicht die Bauart
  einer bestehenden Haus-Spur (z. B. einer Menge bewerteter Wallets nachkaufen),
  ist es ein Kandidat fuer eine PAPIERENE Spur; sonst ein Werkzeug mit Wiki-Seite.
  Die Einordnung als Satz in den Bericht, mit dem Unterschied zur naechsten
  Haus-Spur — nicht als Optionsliste.
- Ein Beobachtungs-/Werkzeug-Repo bringt oft eine eigene `SKILL.md` mit: **nicht
  importieren** (Hausregel `skill-library-sync`), sondern im Wiki dokumentieren.

## Fehlende Schluessel: Ersatz suchen, nicht fragen

Bevor „die restlichen Platzhalter kann nur der Nutzer fuellen" berichtet wird, fuer
JEDEN fehlenden Schluessel einen Ersatzweg pruefen — die Antwort „kann ich nicht"
ist hier keine Antwort. Tabelle, die traegt:

| Platzhalter im Fremd-Repo | Ersatzweg |
|---|---|
| Sprachmodell-Schluessel (`DEEPSEEK_KEY`, `ANTHROPIC_KEY`, `OPENAI_KEY`, `GEMINI_KEY`) | Haus-Bruecke `127.0.0.1:11499` mit `DEEPSEEK_KEY=lokal-ollama` |
| Marktdaten-Schluessel (`COINGECKO_API_KEY`, `BIRDEYE_API_KEY`) | oeffentliche Endpunkte, wo es sie gibt (CoinGecko `/coins/markets` und `market_chart` ohne Schluessel; Birdeye nur mit) |
| `RPC_ENDPOINT` (Helius) | oeffentlicher Chain-RPC |
| Wallet-/Private-Key (`SOLANA_PRIVATE_KEY`) | fuer den Papierlauf nicht noetig — Live-Weg bleibt hinter der Haus-Freigabe (Punkt 7) |
| tote Repo-Quelle (`api.moondev.com`) | KEIN Schluessel hilft; die Quelle ersetzen (Punkt 6) |
| Content-Konten (`TWITTER_*`, `GOOGLE_APPLICATION_CREDENTIALS`, `RESTREAM_*`, `ELEVENLABS_API_KEY`, `GROQ_API_KEY`, `YOUTUBE_API_KEY`) | kein schluesselfreier Ersatz |

- **Ein absichtlich leerer Platzhalter braucht eine Hinweiszeile daneben.**
  Bleibt ein Schluessel leer, weil der oeffentliche Weg traegt, in die `.env` die
  Begruendung schreiben (Zeile, Grund) — sonst liest die naechste Sitzung den
  Zustand als unfertig und fuellt ihn mit einem toten Schluessel (Punkt 9).
- **Die Content-Konten sind kein Betriebsfehler, sondern eine Entscheidung.**
  Im Bericht getrennt von den Handels-Wegen nennen und als Task in
  `MaxHirn/Archiv/TASKS.md` unter `## Offen` eintragen — mit den Namen der
  betroffenen Agenten, nicht als „ein paar Schluessel fehlen".
- **Berichtsform: drei Gruppen statt einer Maengelliste** — gesetzt / bewusst leer
  (mit dem oeffentlichen Weg daneben) / nur ueber Fremdkonto. Wer alles in einen
  Topf „offen" wirft, macht aus einer Entscheidung einen Vorwurf.

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
   - **Ollamas EIGENER `/v1`-Adapter liefert bei Denk-Modellen LEEREN content.**
     Gemessen 24.09.2026 (qwen35-8k, gemma-e4b-8k): `finish_reason: length`, der
     Text steht im Feld `reasoning`, `"think": false` im Body wird dort NICHT
     durchgereicht und der Soft-Switch `/no_think` wirkt ebenfalls nicht. Ein
     Agent auf `/v1` wird damit STUMM statt fehlerhaft. Was traegt: die
     Haus-Bruecke `Agenten/Werkzeuge/ollama-openai-bruecke.py` (127.0.0.1:11499)
     — sie nimmt den OpenAI-Aufruf entgegen und ruft Ollama NATIV mit
     `think:false`; Wache `Agenten/Hermes/scripts/ollama-bruecke-wache.py`
     (Cron, leere Ausgabe = laeuft). In die Repo-.env dann
     `DEEPSEEK_KEY=lokal-ollama` und `DEEPSEEK_BASE_URL=http://127.0.0.1:11499/v1`
     — der Schluessel ist nur ein nicht-leerer Platzhalter, kein Geheimnis.
        - **Das Kontextfenster ist die ZWEITE Stummschaltung.** Ist eine Anfrage
          groesser als das Fenster des lokalen Modells (Vorgabe 8192 Token),
          antwortet Ollama hart mit **HTTP 400** (`request (N tokens) exceeds the
          available context size (8192 tokens)`) — der Fremd-Agent sieht nur
          „503 Ollama nicht erreichbar" und haelt die Bruecke fuer tot, obwohl sie
          gesund ist. Die Bruecke muss deshalb MITRECHNEN: Token schaetzen
          (konservativ ~2,5 Zeichen je Token bei deutschem Text), `num_ctx` in
          Zweierpotenzen bis 32768 anheben und erst darueber kuerzen — und zwar die
          **Mitte** des Textes (Kopf = Anweisung, Ende = frischeste Daten). Kommt
          trotzdem eine `exceeds the available context size`-Antwort, Mitte kuerzen
          und ERNEUT senden (hoechstens drei Versuche) statt 400 durchzureichen:
          der Agent soll eine Antwort bekommen, keinen Verbindungsfehler. Jede
          Kuerzung ins Bruecken-Protokoll schreiben (nur Zahlen, kein Inhalt).
          Messwert: 150k Zeichen (~60k Token) liefen als EIN Aufruf durch, das
          Fenster wurde selbsttaetig angehoben.
   - **Die Bruecke muss BEIDE Formen sprechen, und der Client muss auf SIE
     zeigen.** Fremde Agenten pruefen ihre Verbindung gern ueber die NATIVE
     Ollama-API (`GET /api/tags`, `POST /api/chat`) und melden ohne diese Wege
     `Model type 'ollama' not available`, obwohl die Bruecke gesund ist
     (`/gesundheit` antwortet) — das `OllamaModel` dieses Repos baut seine Basis
     aus `OLLAMA_BASE_URL`, entfernt `/v1` und ruft dann `/api/tags`. Zeigt
     `OLLAMA_BASE_URL` ausserdem auf Ollamas EIGENES `.../v1` statt auf die
     Bruecke, laeuft der Agent bis zum ersten langen Prompt und meldet dort
     „Phase failed", ohne etwas zu schreiben. Beides ist EIN Fehlerbild: die
     Bruecke um `/api/tags` (durchreichen) und `/api/chat` (dieselbe
     Denk-Abschaltung, Antwort in der nativen Feldform `message.content`, `done`,
     `eval_count`) erweitern und die Repo-`.env` auf die Bruecke stellen.
     Gegenprobe je Weg, und die ZEICHENZAHL ist der Beleg (gemessen: 0 Zeichen
     ueber Ollamas `/v1`, `finish_reason: length`; 3603 Zeichen ueber die Bruecke,
     `stop`):
     `curl -s http://127.0.0.1:11499/api/tags | head -c 200` und ein echter
     `/api/chat`-Aufruf mit `think`-Modell.
   - **Der env-Leser gehoert an den AUFRUFORT, nicht in die Konstante.** In
     mehreren Agenten steht `import os` erst NACH der Konstantenzeile
     (`DEEPSEEK_BASE_URL = "https://api.deepseek.com"` ganz oben) - ein
     `os.getenv` dort faellt beim LADEN mit NameError um, bevor irgendetwas
     laeuft (24.09.2026: 5 von 11 Dateien). Muster: Konstante unveraendert
     lassen, Aufrufort `base_url=os.getenv("DEEPSEEK_BASE_URL") or DEEPSEEK_BASE_URL`.
     EIN Muster fuer alle Dateien, sonst raet der Naechste.
   - Der Analyze-Pfad muss `chat.completions.create(...)` nehmen. Agenten mit
     `if "deepseek" in model ... else anthropic` brauchen den Ollama-Zweig
     VOR dem DeepSeek-Zweig — `anthropic.messages.create` ist gegen Ollama
     falsch und faellt erst auf, sobald die Daten laufen.
   - **Eine Umleitung ist erst fertig, wenn JEDER Aufruf im Modul durch sie
     laeuft — Nebenwege bauen sich ihren EIGENEN Client.** Ein Agent hat oft
     mehr als eine LLM-Stelle: Haupturteil plus Extraktor, Synopsis,
     Zusammenfassung. Diese Nebenwege konstruieren ihren Client selbst
     (`TokenExtractorAgent` baute sich einen Anthropic-Client, waehrend der
     Hauptweg schon lokal lief) und sterben am falschen Anbieter, obwohl das
     Haupturteil „repariert" ist — im Log als
     `'OpenAI' object has no attribute 'messages'` bzw.
     `Messages.create() got an unexpected keyword argument 'temperature'`,
     waehrend die Runde weiter „Complete" meldet. Zwei Regeln daraus:
     (a) die FORM des Clients abfragen statt eine Wolke zu raten —
     `hasattr(client, "chat")` → OpenAI-Form, sonst Anthropic-Bloecke, alles in
     EINER Hilfsfunktion (`_llm_text(client, model, system, user, max_tokens,
     temperature) -> str`) mit den vorhandenen Argumenten; (b) den Nebenweg
     Client und Modell vom System UEBERGEBEN lassen
     (`TokenExtractorAgent(agent.client, agent.model)`) statt ihn einen zweiten
     bauen zu lassen. Gegenprobe vor dem Start:
     `grep -n "messages.create\|\.messages\b" <datei>` muss leer sein.
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
6. **Tote Repo-Endpoints ersetzen, nicht reparieren.** ZUERST die DATENQUELLE
   pruefen, dann den Schluessel: ein fehlender Sprachmodell-Schluessel ist
   selten der Blocker. Gemessen 24.09.2026: `api.moondev.com:8000` antwortet
   gar nicht (kein HTTP-Status) - die Agenten, die dort ihre Daten holen
   (whale/funding/liquidation/fundingarb, alles unter `src/agents/api.py`),
   bleiben ohne Daten, egal welcher Schluessel eingetragen wird. Der sniper_agent aus
   moon-dev-ai-agents hing an `api.moondev.com:8000/files/new_token_addresses.csv`
   (tot, kein Zugriff). Ersatz: die oeffentliche Pump.fun-API
   `frontend-api-v3.pump.fun/coins?sort=created_timestamp&order=DESC` liefert
   die neuesten Solana-Launches (kein Schluessel). Die Spalten auf das vom
   Rest des Codes erwartete Schema abbilden (hier: Token Address / Epoch
   Time / Time Found / Birdeye Link), damit nur die eine Funktion angefasst
   wird. Werkstatt ist gitignored - Aenderung per Staging-Kopie in der
   BrainFiles-Wurzel patchen, py_compile + Kurzlauf, dann `cp` zurueck und im
   Fork committen/pushen (voller Klon, origin=Fork).
   - **Dieselbe Schnittstelle, dieselben Spaltennamen, dieselbe REIHENFOLGE.**
     Der Ersatz liegt als eigene Datei neben der toten Quelle (`api_frei.py`),
     Klasse und Methodennamen bleiben gleich, die Agenten tauschen nur die
     IMPORTZEILE (eine Zeile je Agent, mit dem Rueckweg als Kommentar).
     Viele Agenten setzen ihre Spaltennamen selbst per Position
     (`df.columns = ["symbol", "side", ...]`) - eine andere Reihenfolge liefert
     damit STILLE Falschzahlen (Long- und Short-Liquidationen vertauscht) statt
     eines Fehlers.
   - **Nicht jede Methode ist ersetzbar - die nicht ersetzbare gibt `None`
     zurueck, keine Nullen.** Daten, die der tote Dienst selbst erzeugt hat
     (Copybot-Positionen, Folgelisten), haben keine oeffentliche Quelle. `None`
     laesst den Agenten den Zyklus ueberspringen; ein leeres DataFrame mit Nullen
     ist eine erfundene Aussage.
   - **Erst die Quellen messen, dann bauen.** Nicht welcher Dienst fehlt, sondern
     welcher Endpunkt traegt: gemessen sind z. B. Binance `premiumIndex` (alle
     Symbole in EINEM Aufruf) und `openInterest` (je Symbol) brauchbar, der
     Liquidations-Endpunkt von Binance dagegen **404** - dort traegt OKX. Die
     Messung ist ein Aufruf je Kandidat; die Tabelle steht in
     `references/tote-quelle-ersetzen.md`.
   - **Den Beweis je Agent fahren und die ZAHLEN nennen** (Aenderungen gezaehlt,
     Funding-Saetze, USD-Volumen). "Import getauscht" ist kein Nachweis.
   - **Ausgabe ohne `-u` ist kein Beweis.** Ein gestarteter Agent mit
     umgeleitetem stdout zeigt LEERE Logs, weil Python blockweise puffert - wer
     den Prozess nach dem Timeout beendet, verliert alles und schliesst falsch
     auf "Agent erzeugt nichts". `python -u` bzw. `PYTHONUNBUFFERED=1` setzen,
     dann ist die Zeile sofort da.
   - **Vor dem Start JEDEN Key-Namen exportieren, den der Konstruktor prueft** -
     die Agenten verlangen oft mehrere WEITERE (Analyse-Schluessel neben dem
     Datenweg) und brechen VOR der ersten Datenzeile ab, ohne die Datenquelle
     zu beruehren. Dazu die Haus-Bruecke als `*_BASE_URL` fuer jeden dieser
     Schluessel setzen, sonst geht ein "reparierter" Agent gegen den toten
     Wolken-Anbieter.
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

9. **Schluessel messen, nicht annehmen — und tote Schluessel wieder entfernen.**
   Ein gueltiger Schluessel ist noch kein nutzbarer: die Faehigkeit kann im Tarif
   fehlen oder das Guthaben leer sein. Vor dem Eintragen in die Repo-`.env` je
   Kandidat EINEN echten Aufruf fahren und die Antwort LESEN:
   `curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $KEY" https://api.openai.com/v1/models`
   (200 = gueltig) und `https://generativelanguage.googleapis.com/v1beta/models?key=$KEY`
   (Modellnamen auflisten). Gemessene Fallen: Google liefert 200 und listet
   Bildmodelle, antwortet aber bei Bildaufrufen mit `429 RESOURCE_EXHAUSTED …
   free_tier_requests limit: 0` (Bild ist nicht im Gratis-Tarif); OpenAI listet
   `gpt-image-1`, antwortet aber `credit_balance_exhausted`; OpenRouter
   `GET https://openrouter.ai/api/v1/key` zeigt `limit_remaining: 0`.
   - **Ein toter Schluessel in der `.env` ist schaedlicher als keiner**, weil die
     Repos ihren Anbieter nach ANWESENHEIT auswaehlen (Muster `_detect_provider()`:
     erst `OPENAI_API_KEY` → „openai", dann FAL, dann `import diffusers` →
     „local"). Der tote Weg gewinnt und die lokale Kette kommt nie zum Zug.
     Also: Zeile durch eine Hinweiszeile ersetzen (Datum + Grund, kein Wert) und
     den Schluessel dort lassen, wo er herkam. Vorher `_detect_provider()`/
     `get_status()` lesen und die REIHENFOLGE kennen, sonst wirkt die Aenderung nicht.
   - **Der schluessellose Weg ist ein Rechenweg, kein Notbehelf.** Diffusions-
     Ketten (`diffusers` + `torch`) laufen auf der Haus-GPU und kosten nichts.
     Reihenfolge, die traegt: erst pruefen, welcher CUDA-Index fuer die
     gewuenschte torch-Version ueberhaupt ein Wheel hat
     (`curl -s https://download.pytorch.org/whl/<cuNNN>/torch/ | grep -o 'torch-2\.[0-9]*\.[0-9]*%2B<cuNNN>-cp31[0-9]-win_amd64'`),
     dann `pip install --force-reinstall --no-deps --index-url
     https://download.pytorch.org/whl/<cuNNN> torch`, danach
     `pip install diffusers transformers accelerate safetensors` in das
     Repo-venv und `torch.cuda.is_available()` PRUEFEN.
     - **Ein falscher CUDA-Index installiert still die CPU-Variante.**
       `pip install torch` ohne Index holt `2.14.0+cpu`. Der Gegenversuch mit
       `--index-url .../cu130` „installiert" dann nur `torchvision`: pip
       vergleicht `2.14.0+cpu` und `2.14.0+cu130` als GLEICHE Version (lokale
       Versionsanhaenge zaehlen nicht) und laesst das vorhandene stehen. Nur
       `--force-reinstall --no-deps` bewegt es. Symptom: Skript laeuft, aber
       jede Bilderzeugung ist unbrauchbar langsam oder faellt um.
       `torch.version.cuda` und `torch.cuda.is_available()` sind der Beleg,
       nicht die Erfolgsmeldung von pip.
     - Modellwahl gegen den VRAM bemessen (SD-Turbo/SD-2.1-base ≈ 2-5 GB);
       das Repo-Vorgabemodell ist oft das langsamste (30 Schritte bei ~5 GB
       Gewichten). Kleines Turbo-Modell mit 4 Schritten und `guidance_scale: 0`
       nehmen und das Modell im Aufruf explizit setzen; der erste Bildaufruf
       traegt das Modellladen (~25 s), danach Sekunden.
     - Installation und Modelldownload im Hintergrund starten und per
       Notification einsammeln — sie dauern laenger als ein Aufruf erlaubt.
       Beweis ist die Zieldatei PLUS die Kostenzeile des Werkzeugs (`cost_usd: 0.0`).
   - **Schluessel-Ablage: die Sicherung gehoert AUSSERHALB des Repos.** Ein
     Repo, das `*.env` in der `.gitignore` fuehrt, deckt `.env.bak-JJJJMMTT`
     NICHT — die Sicherung mit den Klartext-Schluesseln waere als „untracked"
     im fremden Repo gestanden und beim naechsten `git add` mitgegangen. Nach
     jeder Sicherung `git check-ignore -v <datei>` je Datei pruefen und die
     Kopie in `Agenten/Hermes/.sicherung/` legen.
   - **Bevor ein Dienst als Anbieter eingeplant wird: seine ROUTEN lesen.**
     Aus dem installierten Paket listen, was er ueberhaupt bedient
     (`grep -rhoE '"/v1/[a-z0-9/_-]+"' <site-packages>/<paket>` und
     `grep -rIn 'images/generations\|image_generation' <paket>`). Ein
     Abo-/Proxy-Verteiler mit nur `/v1/messages` + `/v1/models` kann keine
     Bilder liefern, egal welcher Schluessel hinterlegt wird — und ein
     Treffer auf „image" im Paket heisst oft nur *Bild im Prompt*
     (`input_image`), nicht Bilderzeugung. Dieselbe Regel fuer den Zweck:
     erst die Faehigkeitsliste des Pakets, dann die Frage beantworten; ein
     toter oder falsch einsortierter Schluessel aendert nichts an der Faehigkeit.
   - **Gratis-Crowd-Anbieter sind keine zuverlaessige Quelle.** Ein Router, der
     AI-Horde-Modelle anbietet, antwortet korrekt, aber `No Horde workers …` oder
     `queue wait ~1780s … budget 595s left` — vor dem Einplanen die echte
     Warteschlange messen (`https://aihorde.net/api/v2/status/models?type=image`
     listet je Modell die Arbeiterzahl), nicht den Modellkatalog.

## Schleifen, die selbst Backtests starten (conda, Autorenpfade, Beleg)

Research-Automaten dieser Repos („Idee -> Strategie -> Backtest -> Debug ->
Paket") bringen eigene Ausfuehrungswege mit, die hier NICHT tragen. Reihenfolge,
die Zeit spart:

- **`conda run -n <env>` ist auf diesem Rechner kein Weg.** Ohne conda stirbt die
  Schleife beim Ausfuehren des ERZEUGTEN Backtests — und zwar erst NACH der
  Textgenerierung, weshalb sie von aussen „laeuft" aussieht. Vorher messen, was
  ein Backtest ueberhaupt importiert (`grep -h "^import \|^from " *_BT.py | sort -u`):
  sind es nur pandas/numpy/backtesting, ist der venv-Interpreter des Repos der
  richtige Ersatz. EIN Modul mit `interpreter(datei) -> [sys.executable, "-u",
  str(datei)]` neben die Agenten legen und ALLE Aufrufstellen darauf zeigen lassen
  — Sammelstelle, nicht jede Datei einzeln patchen.
- **Die Vorlagen tragen die Pfade des AUTORS** (`/Users/md/Dropbox/.../BTC-USD-15m.csv`).
  Ein erzeugtes Skript mit fremdem Pfad faellt beim Laden um, und der Prompt
  schreibt ihn immer wieder neu. Zwei Stellen: die VORHANDENEN Skripte auf einen
  Pfad relativ zur eigenen Datei umstellen
  (`Path(__file__).resolve().parents[1] / "<datei>"`), und die PROMPT-Vorlage zur
  Laufzeit ersetzen (`PROMPT = PROMPT.replace(<fremder Pfad>, daten_pfad())`).
  Der Laufzeit-Ersatz gehoert NACH die Importe — steht die Zuweisung oberhalb der
  Importe (in diesen Dateien liegen die Prompt-Konstanten VOR dem Importblock),
  faellt das Modul beim Laden mit `NameError` um.
- **Der Beleg ist der Ordner, nicht die Statuszeile.** Nach den ersten Minuten
  muessen im Tagesordner Dateien liegen (`research/<Name>_strategy.txt`,
  `backtests/<Name>_BT.py`). Bleibt er leer, ist die TEXTphase gescheitert — dann
  den Prompt einmal einzeln durch beide Wege schicken (siehe Bruecken-Regel oben)
  und die Zeichenzahl vergleichen, statt am Repo zu schrauben.

## Kennzahlen aus Fremd-Dokumenten sind Prosa, keine Messung

Ein Dokument, das ein Modell geschrieben hat, das auch die Strategie und den
Backtest geschrieben hat, ist kein Ergebnis — auch dann nicht, wenn es wie ein
Bericht aussieht (`FINAL_RESULTS.md`, `RESULTS_10_STRATEGIES.md`, Tabellen mit
Sharpe-Werten). Gegenprobe, die zwei Minuten kostet und den ganzen Ordner
entwertet oder belegt:

1. Ein fertiges `*_BT.py` mit dem venv-Interpreter des Repos starten (`-u`, Log in
   eine Datei, im Hintergrund — ein Durchlauf auf 15m-Kerzen dauert Minuten).
2. Die GEDRUCKTEN Kennzahlen gegen die Doku stellen. Gemessen wichen sie in JEDER
   Zahl ab: andere Tradezahl (3 gegen „834"), Sharpe mit umgekehrtem Vorzeichen,
   ein als „funktionierend" bezeichnetes Skript lief gar nicht (Indicator-Fehler).
3. Immer das Buy-&-Hold-Ergebnis derselben Datei danebenstellen — es steht im
   selben Ausdruck. Ein Verlust von 95 % bei +128 % Buy & Hold ist die Aussage,
   nicht der Verlust allein.

Ergebnis als Befund melden, nie als Strategiebestand uebernehmen. Dasselbe gilt
fuer die Ideenlisten solcher Repos (tausende Modellzeilen, ungeprueft): Steinbruch
fuer Formulierungen, kein Vorrat.

## Externe Agenten vor dem Haus-Waisenputzer schützen (PID-Registrierung)

Wenn externe GUIs (bzw. andere Treiber) Agenten starten, die derselbe Code sind
wie die des Haus-Dauerlaufs, kann der Haus-Waisenputzer diese als fremde
Waisen ansehen und beenden — der Treiber kann nicht unterscheiden, ob ein
laufender Agent von ihm selbst oder von außen startet, wenn er nur die
Prozessliste liest. Die Lösung ist ein **gemeinsamer PID-Registrierungsordner**,
den der externe Agent selbst anlegt:

1. **Registrierungsmodul** (Haus-Code, nicht im Fremd-Repo):
   `<handel>/moondev_reg.py` mit einem Ordner
   `%TEMP%/moondev_agenten/<pid>.moon` je registriertem Prozess. Funktionen:
   `registriere()` (legt die Datei an), `alle_registrierte_pids()` (liest den
   Ordner), `_pid_datei()` (Pfad berechnet).

2. **Haus-Treiber** (`moondev_dauerlauf.py`): `fremde_agenten()` liest
   `alle_registrierte_pids()` und schliesst diese von der Liste der zu
   beendenden Waisen aus — registrierte PIDs koennen also nie beendet werden.

3. **GUI-Agent** (`moongui.py`): nach jedem `subprocess.Popen`-Aufruf (der den
   Agenten startet) _selbst_ `from moondev_reg import registriere; registriere()`
   aufrufen. Ohne diesen Aufruf steht die Agenten-PID im Haus-Ordnner nicht
   und wird vom Waisenputzer beendet.

**Der Treiber muss das HГ¤user-Modul laden**, nicht das GUI-Modul — weil der
Treiber und die GUI in unterschiedlichen Prozessen laufen und das Haus-Modul
nur vom Treiber importiert werden muss (das GUI-Modul bleibt im Fremd-Repo,
das nicht beschrieben wird).

**Gegenprobe**: im Test `_pid_datei()` erstellen und `alle_registrierte_pids()`
liefert sie; `fremde_agenten()` meldet sie nicht als fremd.

**Die Registrierung ist nur die Haus-Seite.** Wenn das Fremd-Repo keine
Registrierung durchfuehrt, schuetzt der Ordner niemanden — und der Waisenputzer
sieht die externen Agenten als Waisen. Entsprechend muss das Fremd-Repo-Patch
(MOONDEV_STARTWEG=gui nach Popen einen `registriere()`-Aufruf) auch eingetragen
werden; Haus-Patch allein genuegt nicht.

Ein Fremd-Repo, das den Prozess mit `Segmentation fault` bzw. `0xC0000005`
(Access Violation) abwirft, verleitet zum Umbau des falschen Teils. Reihenfolge,
die Zeit spart:

- **Sofort `python -X faulthandler <skript> 2>&1 | tail -40`**, und zwar auch
  auf dem HOST (Per-Prozess-Launcher), nicht nur in der Sandbox — sonst haelt
  man einen Umgebungsfehler fuer einen Codefehler. Die Ausgabe nennt Datei und
  Zeile des Absturzes; alles davor ist Raten.
- **Die gepinnte alte Abhaengigkeit im fremden `requirements.txt` ist der
  haeufigere Verdaechtige als das Modell.** Gemessenes Muster: `pandas==2.2.2`
  reisst beim blossen `pd.date_range` den Prozess ab (Python 3.13/Windows) —
  die Vermutung „das Modell ist zu neu fuer die Bibliothek" kostete zwei
  Torch-Neuinstallationen, waehrend der Zeuge in den `pandas`-Code zeigte. Die
  Pins des Repos sind keine Hausregel: `pip install -U <paket>` ist der Fix,
  nicht das Heruntersetzen des Interpreters.
- **Vorher in Stufen proben und jede Stufe mit `flush=True` melden**: Modul
  importieren -> Tokenizer/Modell laden -> Objekt bauen -> rechnen. Der
  Absturzort grenzt die Ursache ein, ohne Debugger.
- **Ausgabe in eine Logdatei schreiben, nicht durch `| grep | tail` schicken.**
  Bei einem harten Abbruch verschluckt die Pipe den Fehlertext; das
  zurueckgebliebene `tcsetattr: Inappropriate ioctl` im Log ist dann das
  einzige Symptom.

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

Repos unter `Werkstatt/` sind Junctions nach O: — `patch`/`write_file`
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
  am Ende loeschen. Werkstatt ist ohnehin komplett `.gitignore`t —
  die CRLF/git-diff-Sorge des ersten Musters entfaellt hier.

## Weiterfuehrend

- Ein GUI-Kontrollzentrum (Tkinter) fuer so ein Repo bauen (Boersendaten,
  Agenten-Start/Stop, Wallet, Doku-Browser) — und warum die Startknoepfe eines
  fremden GUI still sterben: `references/gui-kontrollzentrum.md`.
- Bilder ohne Cloud-Schluessel erzeugen (Anbieter-Triage, CUDA-Wheel, Aufruf
  ueber das Werkzeug des Repos, Sonde sauber halten):
  `references/lokale-bildkette.md`.
- Ein Repo bewertet/urteilt mit einem BEZAHLTEN Sprachmodell und hat einen
  Export/Import-Weg: Urteil lokal auf Ollama faellen, ohne das Fremd-Repo
  anzufassen: `references/bewertung-lokal-statt-api.md` (Werkzeug
  `Agenten/Werkzeuge/fomo_lokal.py` als Vorlage).
- Eine tote Datenquelle des Fremd-Repos durch oeffentliche Endpunkte ersetzen
  (Ersatzmodul mit identischer Schnittstelle, gemessene Endpunkte je Methode,
  was sich NICHT ersetzen laesst): `references/tote-quelle-ersetzen.md`.
- Ein Fremd-Repo mit Pins aus der TensorFlow-1.x-Aera (conda/`python=3.6`-
  Anleitung, `tensorflow.contrib`): auf keinem Host-Python >= 3.9 installierbar —
  Docker-Bild mit legacy-Pinen, Filesharing-Grenze und Volumen-Regeln:
  `references/legacy-docker.md`.

## Abgrenzung

- Forks/Klone anlegen, Bots je Repo, Shallow-Push, Telegram-Anbindung:
  `repo-flotte`
- Haus-Handelsspuren aus solchen Repos bauen: `handel-spuren`
  (Hinweis: SKILL.md ist am Groessenlimit — Ergaenzungen dort verweigert)
