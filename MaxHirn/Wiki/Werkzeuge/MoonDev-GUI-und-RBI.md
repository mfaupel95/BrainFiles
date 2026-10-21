---
titel: MoonDev-GUI und die RBI-Schleife
aktualisiert: 2026-09-25
tags: [werkzeug, moondev, backtest, llm]
---

# MoonDev-GUI: was läuft, was nicht, und was die Strategien wirklich wert sind

> **Kernsatz:** Die vier Startknöpfe des RBI-Reiters starteten bisher Prozesse,
> die in der ersten Sekunde starben — und selbst wenn sie laufen, ist das
> Ergebnis der Schleife **kein Beleg**. Die Zahlen in den Strategiesammlungen
> des Repos sind Prosa des Modells; nachgemessen verliert jede getestete
> Strategie 95–97 % gegen +128 % Buy & Hold.

Ort: `Werkstatt/moon-dev-ai-agents`. Start: `.venv\Scripts\pythonw.exe moongui.py`.

## Was das Fenster ist

Ein Startfenster für die Agenten des Repos (Börsen, Wallet, Agenten, **RBI-Swarm**,
LLM-Einstellungen, Strategie-PDFs, READMEs). Der RBI-Reiter ist die
Research-Backtest-Implement-Schleife: Das lokale Modell schreibt aus einer Idee
eine Strategie, dann einen Backtest, dann Korrekturen.

Kennzahlen im Kopf (25.09.2026): 35 Tagesläufe, 2802 Backtest-Dateien,
**4482 offene Ideen** in `ideas.txt`, 60 Subagenten-Definitionen.

## Warum die Knöpfe nichts taten (behoben 25.09.2026)

Drei verschiedene Ursachen, alle beim ersten Blick in `moongui_logs/*.log`
sichtbar — die Meldung „gestartet (PID …)" ist nur der Spawn, kein Erfolg:

| Läufer | Fehler | Ursache |
|---|---|---|
| `rbi_agent`, `rbi_agent_v2`, `rbi_batch_backtester` | `UnicodeEncodeError: 'charmap'` | Das Fenster reichte **kein UTF-8** an die Kinder; die Agents drucken Emojis |
| `rbi_agent_v2_simple` | `OpenAIError: Missing credentials` | `load_dotenv()` im Kind findet `src/.env` VOR der Wurzel-`.env`; `DEEPSEEK_KEY` blieb leer. Außerdem stand dort die **bezahlte** DeepSeek-URL fest im Code |

Behoben in `moongui.py`: eine neue Funktion `kind_umgebung()` gibt jedem Start
`PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`, `OLLAMA_MODEL/BASE_URL` und die Werte
der **Wurzel-`.env`** mit (nur, wo sonst nichts steht). `rbi_agent_v2_simple`
nimmt jetzt `DEEPSEEK_BASE_URL` — also die lokale Brücke
(`Agenten/Werkzeuge/ollama-openai-bruecke.py`, Port 11499) statt der bezahlten API.

**Das Fenster muss dafür einmal neu gestartet werden** — es hält den alten Code
im Speicher.

### Die dritte Ursache: leerer content statt Fehlermeldung

Nach dem UTF-8-Fix startete der Agent, lief bis „Phase 1: Research" — und meldete
dann für **jede** Idee `❌ Research phase failed!`, ohne etwas zu schreiben.
Gemessen am 25.09.2026 mit dem echten Research-Prompt (1340 Zeichen Systemtext):

| Weg | Dauer | content | Feld `reasoning` | finish |
|---|---|---|---|---|
| Ollama `/v1` (Port 11434) | 51,8 s | **0 Zeichen** | ja | `length` |
| Haus-Brücke (Port 11499) | 9,3 s | **3603 Zeichen** | nein | `stop` |

Das Denk-Modell verbrennt das Token-Budget im reasoning-Teil; der sichtbare Text
bleibt leer und der Agent wertet das als Fehlschlag. Genau die Falle, für die die
Brücke gebaut wurde — nur war `OLLAMA_BASE_URL` im Fenster auf **Ollamas eigenes**
`/v1` gesetzt. Jetzt zeigt es auf die Brücke (auch in der Repo-`.env`).

**Zweite Brücken-Erweiterung:** Das `OllamaModel` der moon-dev-Agenten spricht die
**native** API (`GET /api/tags`, `POST /api/chat`) und hält die Brücke ohne diese
Wege für tot („Model type 'ollama' not available"). Die Brücke beantwortet sie
jetzt mit — dieselbe Denk-Abschaltung, aber in der Feldform, die diese Agenten
erwarten. Damit ist sie für beide Formen einsetzbar (OpenAI **und** Ollama nativ).

**Nachweis (25.09.2026, 3,5 Minuten Lauf):** Idee 1 → `research/AdaptiveKeltnerBreakout_strategy.txt`,
`backtests/AdaptiveKeltnerBreakout_BT.py`, `backtests_package/…_PKG.py`,
`backtests_final/…_BTFinal.py`; Idee 2 → `research/VIX-DivergenceShort_strategy.txt`,
danach Phase 2. Die erzeugten Skripte nennen den **lokalen** Kurs-Pfad
(`O:\Werkstatt\…\BTC-USD-15m.csv`), nicht mehr den des Autors.

## Die zweite Hälfte war nie verdrahtet: Backtest-Ausführung

Alle Läufer riefen hart `conda run -n tflow python <datei>`. Auf diesem Rechner
gibt es **kein conda** (gemessen), und es braucht auch keins: `pandas`, `numpy`
und `backtesting` liegen im venv des Repos — mehr importiert kein erzeugtes
Backtest-Skript. Außerdem trugen **alle** Prompts und alle 19 fertigen
`*_BT.py` den Kurs-Pfad des Autors (`/Users/md/Dropbox/...`), hier liegt die
Datei unter `src/data/rbi/BTC-USD-15m.csv`.

Behoben: neues Modul `src/agents/backtest_start.py` (`interpreter()`,
`daten_pfad()`), verdrahtet in `backtest_runner`, `rbi_agent`,
`rbi_agent_v2`, `rbi_agent_v2_simple`; die Prompt-Vorlage ersetzt den
Autoren-Pfad zur Laufzeit; die 19 vorhandenen Skripte laden die Kurse über
`Path(__file__).resolve().parents[1]`.

## Was die 10 „funktionierenden" Strategien wirklich leisten

Selbst gemessen am 25.09.2026 mit dem Repo-venv auf den **Original-Kursen des
Repos** (`BTC-USD-15m.csv`, 31.046 Kerzen), Gebührenmodell des Skripts:

| Strategie | laut Doku | gemessen | Trades gemessen | Treffer |
|---|---|---|---|---|
| SimpleMomentumCross | 834 Trades, −92,43 %, Sharpe −47,3 | **−2,11 %**, Sharpe **−1,70** | **3** | 0,0 % |
| RSIMeanReversion | 834 Trades, −92,58 % | **−97,19 %**, Sharpe **−181,0** | 1071 | 25,4 % |
| VolatilityBreakout | „0 Trades" | **−95,09 %**, Sharpe **−89,6** | 928 | 30,7 % |
| DivergenceVolatilityEnhanced („Sharpe 2,14") | 349 Trades, Sharpe 2,14 | **läuft nicht** | — | `RuntimeError: Indicator "swing_lows(L,12)"` |

Buy & Hold auf denselben Daten: **+127,76 %**. Die Zahlen der Doku reproduzieren
sich nicht einmal untereinander (834 gegen 1071 Trades bei derselben Datei) —
sie stammen aus Texten des Modells, nicht aus Läufen.

**Merksatz (dieselbe Regel wie Wiki-Handel-Lektion 13):** Ein Modell, das die
Strategie schreibt, den Backtest schreibt und den Ergebnisbericht schreibt, hat
nichts gemessen. Erst ein Lauf, den man selbst startet, auf Daten, die das
Modell nicht kennt, ist eine Zahl.

## Die 4482 Ideen

`src/data/rbi/ideas.txt`: eine Zeile je Idee, alle verschieden, englischer
Fließtext („A trend-following strategy that enters long when …"). Es sind
**rohe Modellausgaben ohne Prüfung** — die letzte Zeile lautet wörtlich
`test all strategies`. Brauchbar als Steinbruch für Formulierungen, nicht als
Bestand: keine einzige ist gegen Daten geprüft, und die Schleife selbst schreibt
immer neue dazu.

## Aufräum- und Vorsichtsregeln

- `moongui.py` und die Agenten dieses Klons sind **geändert** (kein Commit, kein
  Push): der Klon ist damit „schmutzig" und kann nicht einfach vorgespult
  werden. Vor `repos-updaten.py` entscheiden, ob die Patches bleiben.
- Ein RBI-Durchlauf schreibt neue Dateien in `src/data/rbi/<datum>/` und dauert
  mit dem lokalen 8B-Modell **Minuten bis Stunden je Idee** (CPU, 8k Kontext).
- Prozesswache nicht vergessen: ein `rbi_agent` ist ein eigener Prozess und wird
  vom Haus-Dauerlauf **nicht** verwaltet (der kennt nur `new_or_top` und
  `kraken_agent`).
- Ein RBI-Lauf **schreibt weiter Ideen ab** (Zähler im Fenster), auch wenn eine
  Idee scheitert — 4482 Zeilen sind kein Vorrat, sondern ein Verbrauch.

## Stand 13.10.2026 (Nachtrag)

> **Hinweis:** Ollama ist seit 11.10.2026 deinstalliert. Die Abschnitte oben
> zu `qwen35-8k`, `11434` und `11499` beschreiben den alten Stand. Gültig ist
> der folgende Abschnitt.

- **LLM:** Die Haus-Laufzeit ist der llama-server der Hermes-Runtime
  (127.0.0.1:18434). Der Adapter `Agenten/Werkzeuge/llamacpp-ollama-bruecke.py`
  stellt auf Port 11498 Ollamas native API bereit. Standardmodell der GUI:
  `gemma-4-E4B-it-OBLITERATED-Q8_0` (Testchat am 12.10. abends: „bereit").
  Am Vormittag des 12.10. waren alle Modelle mit Exit 1 gescheitert; die
  Ursache ist nicht geklärt.
- **Agenten-Stopp:** `terminate()` beendete nur den venv-Launcher, der echte
  Interpreter lief weiter. Jetzt beendet `taskkill /T` den ganzen Baum
  (Commit `8b19552`). Die Launcher-Kette ist die Falle: Jeder Agent hat einen
  Launcher und einen Kindprozess.
- **Start:** Die README-Suche per `rglob` lief über `.venv` und `src/data`,
  über zwei Minuten im Hauptthread. Jetzt `os.walk` mit Ausschluss, 0,13 s.
- **Optik:** Doppelte Agentenliste (zweite Treeview-Spalte) und unlesbare
  Dropdowns im clam-Theme behoben (Commit `f53fab6`).
- **Strategie-PDFs:** `moondevonyt/Moon-Dev-Code` nach `mfaupel95/Moon-Dev-Code`
  geforkt, nach `O:\Werkstatt\Moon-Dev-Code` geklont (`upstream` = Original,
  flacher Klon). Der PDF-Tab zeigt die drei Dateien im Ordner `strategy_pdfs`.
  Mehr liefert das Original nicht, auch nicht in der Historie. Die drei
  Dateien sind die Paper aus [[Moon-Dev-Code-Studien]].
- **Web-Suche nach Moon-Dev-Strategie-PDFs:** ohne Treffer. Archiv (9712
  Dateien) und GitHub-Codesuche nach `strategy_pdfs` bringen ebenfalls nichts.
- **Laufende Agenten:** Am 13.10. gestoppt. Vorher liefen `kraken_agent`,
  `sniper_agent` und `trading_agent` seit 16:30 Uhr als verwaiste Prozesse, also
  ohne Verbindung zur GUI. Der Trading-Agent war per
  `Agenten/Handel/moondev_trading_freigabe.json` (`handel_erlaubt=false`) auf
  Papier beschränkt. Der Sniper hat keinen Kaufpfad.
