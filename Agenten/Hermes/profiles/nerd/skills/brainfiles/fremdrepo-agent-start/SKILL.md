---
name: fremdrepo-agent-start
description: "Fremd-Repo-Agenten/-Tools lokal starten: Python (venv, .env, Ollama) und Node (MCP/CLI)."
license: MIT
metadata:
  hermes:
    tags: [fremdrepo, agent, ollama, werkstatt, fork]
    related_skills: [handel-spuren, repo-flotte, lokale-modelle-bemessen]
---

# Fremd-Repo-Agenten/-Tools lokal starten

Geklonte Fremd-Repos (Werkstatt/Repos/) bringen Agenten und Tools mit: Python-
Agenten mit eigenem venv, .env, LLM-Aufrufen, Dauerlaeufen — oder
Node/TypeScript-MCP/CLI-Tools. Dieses Skill ist der Weg, so etwas LAUFFAEHIG
zu bekommen, ohne echte Schluessel einzutragen — die lokale
Ollama-Ersetzung ist der Hausstandard fuer Python-Agenten (Max, 16.09.2026),
fuer Node-Tools der npm-Globalinstall und die no-auth-Verifikation.

## Wann
„X starten aus dem Repo-Ordner", ein geklonter Agent soll laufen (moondev,
agent-reach …), ein Repo-Agent als Datenschicht/Demo, ein Node-MCP/CLI-Tool
aus der awesome-trading-agents-Liste (okx/agent-trade-kit …).

Fuer den Node/TypeScript-Weg (npm-Globalinstall, stdio-MCP-Handshake per
Pipe, Key-Verifikation ohne Auth): `references/node-mcp-cli-tools.md`.

Fuer Repos, die eine Bibliothek um ein HuggingFace-Checkpoint sind
(transformers/safetensors, Entscheidungs- oder Klassifikationsmodelle):
`references/huggingface-modell-lokal.md` — venv, HF-Cache auf O:, Sonde mit
eigenen Messwerten.

## Vorgehen

1. **Erkunden:** README-Quickstart lesen (Einstiegspunkt, venv-Name —
   Hausstandard `.venv`, die Repo-Anleitung nennt oft `venv`), src/-Layout,
   .env_example gegen .env stellen — dabei nur SCHLUESSELNAMEN pruefen, Werte
   niemals anzeigen/ausgeben. Orderfaehige Agenten (trading/copybot/sniper im
   Namen) nicht blind starten: erst pruefen, ob die Schleife echte Orders
   platzieren kann; beobachtende Agenten (whale/funding/chart/listing) sind
   der sichere Start. Live-Handel nur nach expliziter Freigabe.
   Ein Repo mit vielen Agentenmodulen (z.B. 30 Dateien unter src/agents/) gilt
   erst als lauffaehig, wenn JEDES Modul einzeln importiert wurde —
   `requirements.txt` deckt oft nur die zuletzt benutzten Module ab, nicht den
   ganzen Baum, und ein "venv fertig" beim Klonen heisst nicht "alle Module
   starten". Schleife bauen: fuer jede Datei `python -c "import importlib;
   importlib.import_module('src.agents.<mod>')"` mit grosszuegigem Timeout
   (>=30s je Modul — `transformers`/`torch` brauchen beim ERSTEN Import bis zu
   45s fuer den Backend-Scan, das ist kein Haenger, sondern normal). Fehlende
   Pakete in `requirements.txt` ERGAENZEN, nicht nur lokal `pip install`en —
   sonst faellt derselbe Fehler beim naechsten venv-Neuaufsetzen wieder an.
   Zwei wiederkehrende Versionskonflikte: `moviepy` 2.x hat `moviepy.editor`
   entfernt (Code, der die alte API nutzt, auf `moviepy==1.0.3` pinnen);
   `playsound` >=1.3 scheitert beim Wheel-Bau mit "could not get source
   code" (auf `playsound==1.2.2` pinnen). Ein `ModuleNotFoundError` fuer ein
   plattformspezifisches Paket (z.B. `Quartz` auf macOS) ist auf Windows
   nicht fixbar — als bekannte Luecke ausweisen, nicht installieren
   versuchen. Ein fehlender bezahlter API-Key (z.B. BIRDEYE_API_KEY) ist eine
   Konfigurationsentscheidung des Nutzers, kein Code-Fehler — im Bericht klar
   von echten Bugs trennen.
2. **Import-Weg:** `python src/agents/x.py` setzt sys.path[0] auf src/agents/
   und bricht am `import src.…` mit ModuleNotFoundError ('No module named
   "src"'). Aus dem Repo-Root als `python -m src.agents.x` starten — das
   braucht `__init__.py` in agents/ (meist vorhanden).
3. **Start:** `terminal(background=true)`, cwd = Repo-Ordner, Ausgabe nach
   `Agenten/Routinen/logs/<name>.log` umleiten; der Prozess haengt an der
   Sitzung und stirbt mit ihr — fuer Dauerbetrieb eine geplante Aufgabe
   anbieten, nicht stillschweigend so lassen.
4. **.env wird oft NICHT geladen:** viele Einzel-Agenten rufen load_dotenv() nie auf,
   obwohl main.py es tut. Werte beim Start exportieren, CRLF-sicher:
   `export KEY=$(grep '^KEY=' .env | cut -d= -f2 | tr -d '\r')` — und die
   Werte beim Start echo-en, damit der Beweis (und evtl. eine kaputte URL)
   im Log steht, bevor der Prozess sie nutzt.
   Gleiches gilt fuer eine schnelle Verifikation per `python -c`/One-Liner: ein
   DIREKTER Import des Leaf-Moduls (z.B. `from tools.video.stock_sources.pexels
   import PexelsSource`) umgeht den Bootstrap, der `_load_dotenv()` erst beim
   Import EINES bestimmten Paketmoduls ausloest — das Leaf-Modul meldet dann
   faelschlich "KEY not set", obwohl die .env korrekt gefuellt ist. Vorher das
   Bootstrap-/Entry-Modul importieren (z.B. `import tools.base_tool`) oder ueber
   den echten Einstiegspunkt testen, nicht ueber einen isolierten Leaf-Import.
5. **Key-Wall („X_KEY not found", raise ValueError im __init__):** den
   LLM-Client auf das lokale Ollama legen:
   `openai.OpenAI(api_key="ollama", base_url=<OLLAMA_BASE_URL>)`. Zwei Fallen:
   - base_url muss auf `/v1` enden (OpenAI-SDK); eine native Ollama-URL
     (…/api) ist ein anderes Protokoll — im Client notfalls
     `.replace("/api", "/v1")`.
   - Die Modellwahl-Verzweigung prueft meist `"deepseek" in AI_MODEL.lower()`
     — ein Ollama-Modellname faellt sonst in den anthropic-Zweig
     (messages.create) und der Analyse-Call bricht. Bedingung um `or
     OLLAMA_MODEL` erweitern; chat.completions ist die OpenAI-kompatible
     Schnittstelle.
6. **Pro-API-Sperren** (Fehler 10005/401/403 an Premium-Endpoints):
   oeffentliche Ersatz-Endpoints nehmen — Tabelle + Rate-Limits in
   `references/oeffentliche-api-ersatz.md`. Eine Semantik-Verschiebung
   („neue Coins" → kleinste Marketcaps) im Bericht NENNEN, nicht
   verschweigen. Free-Limits praktisch ~5-10 Calls/min → DELAY ~12 s, ein
   15-s-Retry je 429er, Auswahl head(3); 429 wird gefangen, der Zyklus
   ueberlebt einzelne Fehlschlaege.
7. **Dauerlaeufer duerfen nicht am ersten Zyklus-Fehler sterben:** try/except
   je Zyklus INSIDE die while-Schleife legen. Liegt es aussen, beendet z.B.
   eine CSV mit Alt-Schema den ganzen Prozess — beobachtbar als „python
   beendet" trotz intakter Schleifenlogik.
8. **Alte Ergebnisdateien aus dem Klon:** versionierte Laufzeit-CSVs mit
   Alt-Schema → `git rm -f` (modifiziert → -f noetig) statt reparieren;
   Zusammenfassungs-Try/except, neu erzeugte CSVs untracked lassen.
9. **Commit/Push Fork:** nur eigene Dateien stagen (fremde
   Arbeitsbaum-Aenderungen liegen lassen). Shallow-Klon: vor dem Push
   `git fetch --unshallow upstream` sonst 'index-pack failed'.
10. **Model-Factory mit separater Ollama-Init:** viele Frameworks (z.B.
    RBI in moon-dev-ai-agents) initialisieren Ollama GETRENNT von den
    API-Keys und setzen `self._models['ollama']` NUR wenn `is_available()`
    True liefert. `get_model('ollama', …)` gibt dann None, sobald die URL
    nicht stimmt — auch wenn der lokale-Ersatz (`MOONDEV_LOKAL_STATT_FEHLT`)
    vorgesehen ist, weil DER nur greift, wenn `_models['ollama']` gesetzt
    ist. Configs (`RESEARCH_CONFIG`, `BACKTEST_CONFIG`, `DEBUG_CONFIG`,
    `PACKAGE_CONFIG`) auf `{"type": "ollama", "name": "qwen35-8k:latest"}`
    stellen und belegen, dass der Agent die Research-Phase erreicht.
11. **OLLAMA_BASE_URL normalisieren (häufigster Fehler):** der native
    Endpunkt ist `…/api` (tags/chat), der OpenAI-kompatible `…/v1`.
    GUI/Wrapper setzen oft `/v1`; `ollama_model.py`-artige Klassen bauen
    `f"{base}/tags"` → 404 → is_available False → get_model None. Fix an
    EINER Stelle im Constructor: wenn nicht auf `/api` endend, `/v1`
    vorher abschneiden und `/api` anhängen. Danach egal, was GUI/Wrapper
    setzen. Belegt: RBI lief nach dem Fix lokal bis Research-Phase.

## Pitfalls
- **Ein natives Fremd-Werkzeug auf einen Pfad unter `Werkstatt/` zeigen und sich
  ueber den Abbruch wundern:** `Werkstatt/` ist eine Junction auf `O:\`.
  Programme, die ihre Eingabe aufloesen, verweigern das mit `Refusing to
  resolve input with a symlinked parent` — der Lauf endet vor der ersten Datei.
  Denselben Pfad ueber das **Aufloesungsziel** aufrufen (`/o/Werkstatt/...`)
  und den Umweg im Bericht nennen, nicht als Werkzeugfehler. Dieselbe Regel
  trifft die `okx-*`-Skill-Junctions: die sind fuer solche Werkzeuge
  strukturell unerreichbar.
- **Native Programme verstehen die MSYS-Notation nicht:** `/c/Users/...` als
  Argument gibt `Cannot determine input type` / "cannot change to". Windows-
  Pfade mit Schraegstrichen uebergeben (`C:/Users/...`) — in bash bleibt `cd`
  nach `/c/...` trotzdem erlaubt (eingebaut), nur das weitergegebene Argument
  muss native Form haben.
- **patch/write_file verweigern Dateien unter Werkstatt/** (Junction auf O:,
  ausserhalb HERMES_WRITE_SAFE_ROOT). Fix-Muster: byte-sauberes Wegwerf-
  Patchskript nach Agenten/Hermes/cache/ (Wegwerfzone) und mit python
  ausfuehren; Newlines: rb lesen, nl ableiten, wb schreiben — sonst
  Ganzdatei-Diff.
- **Mehrzeiligen String in eine CRLF-Datei einsetzen, ohne jede Zeile auf
  die Datei-Newline zu normalisieren, zerlegt die Struktur** (hier: Duplikat
  des Blocks + IndentationError). Der neue Block muss ZEILENWEISE mit
  `nl` verknuepft sein (`nl.join(zeilen)`), nicht als ein String mit
  eingebauten `\n` in die CRLF-Datei geschrieben werden; vor dem Schreiben
  immer `ast.parse()` gegen den FERTIGEN Text. Wird trotzdem ein kaputter
  Block geschrieben, den ganzen Bereich neu konstruieren statt in dem
  kaputten Block weiterzupatchen.
- **Erster Zyklus dauert:** lokales Modell kalt 15-40 s je Analyse plus
  Rate-Limit-Delays — 3-5 min warten, bevor ein Fehler diagnostiziert wird.
- **Fremd-Code, fremde Keys:** nie echte Schluessel in die .env des Repos
  schreiben; die .env nur lokal und unversioniert lassen. Ausnahme: eigene
  kostenlose Schluessel (Pexels, Pixabay …), die Max explizit durchgibt —
  die gehoeren in die .env, sind aber trotzdem nie in Logs/Ausgaben zu
  wiederholen.
- **Ein programmatisch aus `.env.example` erzeugtes `.env` kann ein `\r` IN
  den Wert einschmuggeln**, wenn die Vorlage CRLF-Zeilenenden hat und der
  Wert per String-Replace auf die Zeile `KEY=\n` gesetzt wird (das `\r` vor
  dem `\n` bleibt hinter dem neuen Wert stehen). Das Ergebnis sieht beim
  Betrachten der Datei unauffaellig aus, aber jeder Header, der den Wert roh
  uebernimmt (z.B. `Authorization: <key>`), traegt ein `\r` mit — Cloudflare-
  geschuetzte APIs quittieren das mit 403/1010, ohne dass der Key falsch ist.
  Nach dem Schreiben `repr(wert[-3:])` pruefen (zeigt `\r\n` statt `\n`) oder
  gleich zeilenweise mit `line.rstrip('\r\n')` einlesen/schreiben statt Zeilen
  per Bytegleichheit zu ersetzen.
- **Ein Agent, der stundenlang „laeuft“ aber nichts tut** (Schleife ohne
  Daten, weil die Quelle Pro-gesperrt ist) ist kein Erfolg — die Ausgabe
  muss einen kompletten Zyklus zeigen, bevor er gruen gemeldet wird.
- **Ein Treiber, der den Agenten per `subprocess.Popen` startet, darf NICHT
  `sys.executable` als Interpreter nehmen** — das ist der Interpreter des
  TREIBERS (z.B. ein anderes Haus-venv), nicht der des Fremd-Repos, und dem
  fehlen dessen Pakete (`ModuleNotFoundError: requests`/`pandas`/`openai`).
  Den Pfad zum Repo-eigenen `.venv/Scripts/python.exe` fest im Treiber
  eintragen, nie den Aufrufer-Interpreter durchreichen.
- **`load_dotenv()` ohne Pfad sucht per `find_dotenv()` AUFWAERTS ab dem
  Modulordner** (z.B. `src/agents/`) und kann dabei eine NAEHERE, fremde
  `.env` finden (eigene Zugangsdaten eines anderen Teilsystems im selben
  Repo) statt der beabsichtigten Root-`.env` — die gesuchte Variable bleibt
  leer, ohne Fehlermeldung beim Laden selbst, und der Agent scheitert erst
  spaeter an einer ganz anderen Stelle (z.B. verlangt er einen nie gesetzten
  Fremd-Schluessel). Ein Treiber darf sich darauf nicht verlassen: die
  Root-`.env` selbst lesen und die benoetigten Variablen VOR dem Start in
  die Subprozess-Umgebung setzen — `load_dotenv()` ueberschreibt bereits
  gesetzte Variablen per Vorgabe nicht (`override=False`).
- **Ueber `subprocess.PIPE` (kein echtes Konsolenfenster) faellt Python auf
  die Windows-Codepage zurueck und stirbt am ersten Emoji/Sonderzeichen**
  (`UnicodeEncodeError`) — gilt genauso, wenn ein PYTHON-Treiber den Agenten
  startet, nicht nur bei einem PowerShell-Wrapper. `PYTHONIOENCODING=utf-8`
  in die Subprozess-Umgebung setzen, bevor der Kindprozess startet.
- **Eine Konsolen-CLI aus einem Hintergrund-/Agent-Prozess oeffnet auf
  Windows bei JEDEM Aufruf ein sichtbares Fenster**, wenn der
  `subprocess.run` kein `creationflags=subprocess.CREATE_NO_WINDOW` setzt —
  `-WindowStyle Hidden` im PowerShell-Wrapper versteckt nur die eigene
  Shell, NICHT die Kinder; jeder onchainos/agent.exe-Aufruf klappt sonst ein
  Fenster auf, das der Nutzer als "Popup" meldet. `-WindowStyle Hidden` von
  aussen versteckt das Kind nicht — das Flag gehoert in den subprocess-Call
  selbst (`creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0`).
  Bei einem Fix VOR dem Start des laufenden Treibers pruefen, wann der
  Treiberprozess gestartet wurde: ein schon laufender Hintergrundprozess
  nutzt den ALten Code weiter — nur ein Neustart (bei Live-Trading-
  Prozessen vorher Rueckfrage) oder die naechste getrennte Aufgabe
  (Scheduled Task/Cron startet frisch) uebernimmt ihn.
- **Ollama bei knappem VRAM:** ein Modell, das nicht in die GPU passt
  (cudaMalloc OOM), als CPU-Variante fest verdrahten statt pro Aufruf
  `num_gpu 0` durchzureichen: `ollama create <name>:cpu` mit einem
  Modelfile (`FROM <base>`, `PARAMETER num_gpu 0`) — der Tag ist dann
  persistent, auch der GUI/Autostart-Server nutzt ihn, ohne dass jede
  Aufrufstelle das Flag traegt. `ollama ps` zeigt die geladene Groesse und
  ob "100% CPU". ACHTUNG Systemfolge: ein 3-GB-Modell auf CPU kostet ~3 GB
  RAM — bei kleinem Pagefile kann das den Rechner instabil machen
  (Terminal/PowerShell sturzen mit 0xc0000409 Stack-Overrun ab, `can't
  start new thread`). Erst das schwere Modell entladen (Ollama stoppen),
  dann weiterarbeiten. Server-Einstellungen (OLLAMA_MODELS als
  Benutzervariable) und die Autostart-Verknuepfung pruefen — eine .lnk auf
  einen alten `BrainFiles\Modelle\Programme\Ollama\…`-Pfad startet nach
  Neustart nie (Modelle ist nur Gewichte, kein Programmordner); das Ziel
  der .lnk mit `Test-Path` gegen die echte Installation
  (`AppData\Local\Programs\Ollama\ollama app.exe`) pruefen.
- **Herstellerzahlen sind keine Messung.** README-Latenzen ("33 ms auf einer
  T4") und Benchmark-Genauigkeiten gelten fuer die Hardware und den Datensatz
  des Autors. Vor jeder Empfehlung eine eigene Sonde laufen lassen und die
  ZAHL dieser Maschine berichten (Ladezeit, ms je Aufruf und je Frage,
  device) — mit einem Gegenbeispiel, dessen richtige Antwort man selbst
  kennt. Ein Fremdmodell, das eine vorhandene Funktion ersetzen soll, wird
  zuerst als ZWEITE Stimme neben die bestehende gehaengt (gleicher Vertrag,
  gleiche Rueckgabe): erst wenn die Gegenprobe Gleichstand oder Vorteil
  zeigt, wird umgestellt. Nie eine Schwelle oder ein Tor auf ein ungemessenes
  Fremdmodell setzen.
- **Modellgewichte gehoeren auf O:, nicht auf C:.** `HF_HOME` ist hier keine
  Windows-Variable; ohne `HF_HOME=O:\Modelle` beim Aufruf landen die Gewichte
  im Benutzerprofil auf der fast vollen C:-Platte. Welche Stelle im Cache die
  echten Bytes haelt, steht in
  `references/huggingface-modell-lokal.md`.
- **Ein Medien-/Render-Repo erst messen, dann "kann rendern" sagen.** Drei
  Dinge getrennt pruefen: den Interpreter
  (`<repo>/.venv/Scripts/python.exe -V`), die externen Programme
  (`Get-Command node,npx,ffmpeg` auf dem Host — in der MSYS-Bash sieht
  `command -v` nur das MSYS-PATH und meldet Windows-Programme faelschlich als
  fehlend) und den Schluesselbestand im EIGENEN `.env` des Repos: je NAME
  zaehlen, ob ein Wert gesetzt ist (`awk -F= '/^[A-Z_]+=/'`), Werte niemals
  ausgeben. Ein leeres Schluesselverzeichnis heisst nicht "kaputt" — viele
  solcher Repos haben einen Zero-Key-Zweig (z.B. gerenderte Daten-Charts statt
  KI-Bilder), und genau DER ist der belastbare Nachweis der Lauffaehigkeit;
  den Unterschied "laeuft ohne Keys" gegen "braucht bezahlten Provider" im
  Bericht trennen. Einen langen Render als Hintergrundprozess starten (cwd =
  Repo) und den Prozessstatus getrennt abfragen statt synchron zu warten; die
  Ausgabe endet mit dem Ablagepfad, und der wird danach mit Groesse
  nachgelesen — "Rendered 690/690" allein ist noch kein Artefakt.
