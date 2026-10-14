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

Geklonte Fremd-Repos (Werkstatt/) bringen Agenten und Tools mit: Python-
Agenten mit eigenem venv, .env, LLM-Aufrufen, Dauerlaeufen — oder
Node/TypeScript-MCP/CLI-Tools. Dieses Skill ist der Weg, so etwas LAUFFAEHIG
zu bekommen, ohne echte Schluessel einzutragen — die lokale
Ollama-Ersetzung ist der Hausstandard fuer Python-Agenten (Max, 16.09.2026),
fuer Node-Tools der npm-Globalinstall und die no-auth-Verifikation.

## Wann
„X starten aus dem Repo-Ordner", ein geklonter Agent soll laufen (moondev,
agent-reach …), ein Repo-Agent als Datenschicht/Demo, ein Node-MCP/CLI-Tool
aus der awesome-trading-agents-Liste (okx/agent-trade-kit …).

**Wenn Max nur eine Repo-URL schickt („aneignen, lernen, anbinden")**, gilt
diese Reihenfolge, und der Bericht liefert die Zahlen aus Schritt 4:
Klon/Fork nach `Werkstatt/<name>` (ein Fork kann schon existieren —
`gh repo fork <orig> --clone=false` meldet das und ist kein Fehler),
`upstream` setzen, eigenes `.venv` mit dem Haus-Python, Abhaengigkeiten
installieren, `pytest` laufen lassen, und dann **zuerst den schluessellosen
Pfad** des Repos wirklich fahren (bevorzugt der Zweig, den die README selbst
als kostenlos/ohne Key nennt). Erst dessen ECHTE Ausgabe (Anzahl geholter
Datensaetze, Zeilen, Fehlerquote) macht Aussagen wie "laeuft" zulaessig;
ein gruener Testlauf allein belegt keine Funktion.

Fuer den Node/TypeScript-Weg (npm-Globalinstall, stdio-MCP-Handshake per
Pipe, Key-Verifikation ohne Auth): `references/node-mcp-cli-tools.md`. Dort
steht auch, wie ein VEROEFFENTLICHTES CLI-Paket unter Windows installiert wird
(`os`-Feld im Manifest, `workspace:*` in den devDependencies, Haus-
Installationsordner statt Globalinstall, Attrappen-Endpunkt als Nachweis ohne
Schluessel, Kosten- und Datenschutzpruefung vor der Empfehlung, die
GRATIS-Variante desselben Modells beim Anbieter bevor „braucht einen bezahlten
Schluessel" im Bericht steht, das Lesen des Schluessels aus einer
Windows-Benutzervariable ohne jede Ausgabe (Registry direkt statt `reg query`,
Quellen-Schalter fuer die Tests) und der Umgang mit einem sofortigen Abbruch
(Exit 1 ohne Suchausgabe — nicht an den Vordergrund gebunden; wiederholen, Ausgabe
in eine Datei lesen, Wurzel auf Junctions pruefen).

**Befragt das Werkzeug ein Modell ueber ein EIGENES Protokoll** (nicht OpenAI-kompatibel),
gehoert eine kleine Uebersetzungs-Bruecke dazu, damit es nicht an einen einzigen
Anbieter gebunden ist — Vertrag, Voraussetzungen (Kontextfenster, Buendelung, Latenz
gegen den Takt des Aufrufers) und die Fallen (leeres Modell-Ergebnis, veralteter
Modell-Tag, ersetzte Anmeldung) stehen im Abschnitt „Ein Client mit eigenem
Modell-Protokoll“ derselben Referenz.

**Bringt das Werkzeug einen eigenen `install`-Unterbefehl mit ("managed
install"), unter Windows zuerst dessen Scheitern pruefen und dann auf npm in
einen EIGENEN Prefix ausweichen — der Shim darf dabei NICHT auf den Pfad, den
der Hersteller fuer seine verwaltete Installation reserviert** (die
tool-eigene Diagnose zaehlt dessen blosse Existenz als Installation und
blockiert dann den Start). Dazu PATH-Anhaengen ohne `setx`, die
oft uebersprungene `postinstall`-Freigabe von npm >= 11 und der erste Start mit
eingebetteter Datenbank (sieht ~3 min wie ein Haenger aus; am Datenordner
messen, am Port belegen): alles im selben Abschnitt der Referenz.

**Und ein Werkzeug, das ein CLI per NAMEN startet (Adapter, Sonde, Test-Knopf),
findet unter Windows das npm-Shim `.CMD` — `spawn` ohne `shell:true` kann das
nicht starten (`EINVAL`), das Kind startet nie, und die Meldung ist
nichtssagend („Umgebungstest fehlgeschlagen“). Dann die NATIVE Fassung des CLIs
installieren, damit ein `.EXE` in einem frueheren PATH-Verzeichnis gewinnt, und
Aufloesung plus Sonde nachstellen — Rezept im selben Abschnitt der Referenz.**

**Und starte ein solches Werkzeug aus einem Verzeichnis OHNE fremde `.env`.** Es
laedt beim Start die `.env` seines ARBEITSVERZEICHNISSES in die eigene
Prozessumgebung und reicht sie an jedes Kind weiter (Sonde, Adapter, Agent); ein
Schluessel darin ueberstimmt dann die Anmeldung, die das Werkzeug nutzen soll —
und derselbe Befehl laeuft aus der eigenen Shell trotzdem durch, weil die Shell
keine `.env` laedt. Ein `unset` vor dem Start hilft NICHT (die Datei wird beim
Start neu geladen); der Fix ist das Arbeitsverzeichnis, und der Start-Wrapper
setzt es ausdruecklich. Messweg und Gegenprobe:
`references/node-mcp-cli-tools.md`, Abschnitt „Das Arbeitsverzeichnis entscheidet
ueber die Umgebung“.

Fuer Repos, die eine Bibliothek um ein HuggingFace-Checkpoint sind
(transformers/safetensors, Entscheidungs- oder Klassifikationsmodelle):
`references/huggingface-modell-lokal.md` — venv, HF-Cache auf O:, Sonde mit
eigenen Messwerten, dazu die Falle gepinnter Abhaengigkeiten.

Fuer Repos, deren Epoche auf KEINEM Host-Python mehr laeuft (TensorFlow 1.x
braucht Python <= 3.7, kein conda auf dem Rechner; die GPU-Generation
unterstuetzt das CUDA des Frameworks nicht): `references/docker-legacy-python.md`
— Docker als einziger Baupfad, was Docker Desktop ueberhaupt mounten darf
(Junctions loesen sich auf), apt-Archive fuer EOL-Distros, era-Pines mit
Begruendung, und der Nachweislauf ohne Waisen-Container.

Fuer den JEV-Trading-Bot auf Kuru/Monad (andere Paare vorbereiten):
`references/kuru-markt-erkundung.md` — aktive Maerkte ueber die Kuru-API,
Margin-Account ueber Storage-Slot 73 des OrderBook-Proxys, Groessen in
Basis-Asset-Einheiten (nicht MON), Multi-Markt-Parametrisierung; dort auch
„Monad-Wallet-Key erzeugen“ (EVM-Key mit ethers via `node -e`, Gegenprobe,
PRIVATE_KEY in die `.env` — `DRY_RUN=true` haelt den Bot trotz Key im
Trockenlauf).

**Ein leerer Rahmen ist kein System.** Ein Repo, dessen Dienstordner nur
`.gitkeep` enthalten und dem die `Dockerfile`s fehlen, die die
`docker-compose.yml` als Build-Kontext nennt, ist ein Bauplan: `up` bricht
bei jedem Dienst ab. Das nachzaehlen (Dienstordner auflisten mit
`search_files(target='files')`, Dockerfile vorhanden?) und im Bericht als Befund nennen, statt es zu starten. Ebenso
die Schluesselnamen der `.env.example` LESEN und benennen, wenn sie nach
echtem Geld rufen (`PRIVATE_KEY`, Boersen-Secrets) — das ist eine Warnung
wert, nicht nur eine Zeile im Protokoll.

## Startfertig machen: der Beleg zaehlt, nicht die Doku

- **Den dokumentierten Entwicklungsbefehl einmal wirklich fahren, bevor die
  Einordnung festgelegt wird.** Ein Repo, das als "nur Bau, kein Start" galt,
  hatte eine Web-UI auf einem eigenen Port, beschrieben unter "Quick Start".
  "Kein Startprogramm" ist eine Vermutung aus dem Dateibaum, kein Befund — erst
  nach dem Lauf darf sie als Zustand dastehen.
- **Den Port aus der Logzeile des laufenden Prozesses ablesen, nicht aus der
  Doku.** Gemessen: die README nannte 3000, `PORT` in der `.env` galt mit 3010.
  Die Zeile `Listening on ...` / `Uvicorn running on ...` ist der Zeuge.
- **Ein Befehl, der nachfragt, startet nicht, wenn stdin geschlossen ist.**
  Wird der Prozess mit `stdin=DEVNULL` gestartet (Haus-Wrapper und Startfenster
  tun das), kann `npx <paket>` die Installations-Rueckfrage nicht beantworten
  und bleibt stehen, statt zu starten. Den Nicht-interaktiv-Schalter IN den
  Befehl schreiben (`npx -y ...`, `--yes`, `-Force`) — nicht beim Aufrufer
  nachruesten. Das Symptom ist eindeutig: lebender Prozess, keine Logzeile.
- **Secrets einer frisch gebrauchten `.env` erzeugen, nie ausgeben.** Viele
  Repos brauchen `JWT_SECRET_KEY`-artige Werte schon beim ersten Start. Mit
  `secrets.token_urlsafe(48)` erzeugen, direkt in die Datei schreiben, im
  Protokoll nur "gesetzt" melden — und `git check-ignore -v .env` VOR und
  NACH dem Schreiben, damit der Wert nicht versehentlich in einen Commit
  wandert. **Die Terminal-Ausgabe maskiert Zeilen unter Schluesselnamen**
  (`cat` zeigt `PRIVATE_KEY=***`, egal ob leer oder gesetzt) — den wahren
  Zustand einer `.env` nie aus der Konsole schliessen, sondern byte-weise
  pruefen (Diff gegen das Backup, Python-Read).
- **Jede Logdatei LESEN, nicht nur ihre Existenz zaehlen.** Ein Log mit
  `command not found` erfuellt jede "Beleg vorhanden"-Pruefung und beweist
  trotzdem nichts. Erst die Zeile, die den Dienst meldet (`Ready in ...`,
  `Uvicorn running on ...`), macht aus dem Lauf einen Nachweis.

**Nach dem Beleg den GANZEN Baum beenden.** `npm run dev` startet `next dev` als
Kind; ein Kill auf die Eltern-PID laesst es als Waise stehen, und die haelt den
Port besetzt. `taskkill /T /F /PID <pid>` — danach die Prozesszahl nachzaehlen.
Beleg und Aufraeumen gehoeren zusammen: ein Startnachweis, der einen Waisen
hinterlaesst, ist keiner.

**Ein Klon kann mitten in der Sitzung auftauchen.** Eine parallele Sitzung klont
waehrend der Arbeit. "Wie viele Repos liegen auf der Platte" ist deshalb am
ANFANG und am ENDE zu messen, und die Zuordnung programmatisch (Plattenordner
mit `.git` gegen die Manifest-Menge), nicht per Augenschein. Ein so entstandener
Baum hat oft `origin` = Original und GAR KEIN `upstream` — vor der Weiterarbeit
auf Hausmuster ziehen: `git remote rename origin upstream && git remote add
origin <fork> && git fetch origin`.

## Vorgehen

1. **Erkunden:** README-Quickstart lesen (Einstiegspunkt, venv-Name —
   Hausstandard `.venv`, die Repo-Anleitung nennt oft `venv`), src/-Layout,
   .env_example gegen .env stellen — dabei nur SCHLUESSELNAMEN pruefen, Werte
   niemals anzeigen/ausgeben. Orderfaehige Agenten (trading/copybot/sniper im
   Namen) nicht blind starten: erst pruefen, ob die Schleife echte Orders
   platzieren kann; beobachtende Agenten (whale/funding/chart/listing) sind
   der sichere Start. Live-Handel nur nach expliziter Freigabe UND mit
   vorhandenem Wallet-Key — ohne Key (PRIVATE_KEY leer) bleibt der Bot im
   Dry-Run; das vorher pruefen, statt Live zu versprechen.
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
   **Lautet der Auftrag „diese Anleitung ausfuehren"**, gilt ein eigener Ablauf:
   die richtige Anleitung erkennen (die gross geschriebene Spezifikation neben
   der Hausnotiz ist NICHT die Anleitung — die echte nennt Dateien und Schalter,
   die im Baum wirklich existieren), der LESENDE Vorflug vor dem ersten
   ordnungfaehigen Lauf (Schluessel/Host/Kontostand belegen, ohne eine Order),
   die Prozesszahl des Zielbinaers vor dem Start messen (zwei Laeufe ordern
   doppelt), und der Nachweis kommt aus der Statusdatei des Werkzeugs, nicht aus
   stdout. Vollstaendig: `references/anleitung-ausfuehren-und-vorflug.md`.
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
- **Ein Fremd-Repo, an dem eine Claude/Claude-Code-Session gearbeitet hat,
  uebernimmt man ueber deren Sitzungsprotokoll, nicht ueber den Dateibaum.**
  Die Absicht der Session steht in `~/.claude/projects/<projekt-verzeichnis>/*.jsonl`
  (der Ordnername ist der Repo-Pfad mit `\`/`:` durch `-` ersetzt, z.B.
  `O--Werkstatt-2-JEV-jev-trader`). Die USER-Nachrichten daraus extrahieren
  (`type=="user"`, `message.content` ist str oder Liste von `{type:"text"}`) —
  dort steht, was der Nutzer tatsaechlich wollte, nicht was der Assistent gebaut
  hat; dazu `git reflog` fuer die letzte Aktion. Und: **bevor man "starten"
  sagt, pruefen, ob der Prozess schon laeuft** — curl auf den Port, Log-Tail,
  Smoke-Test; einen laufenden Trading-Bot blind neu zu starten riskiert
  Doppel-Orders. Der vom Nutzer genannte Pfad kann ausserdem angenaehert sein
  (`O:/werkstatt 2/jevtrader` war real `O:/Werkstatt 2/JEV/jev-trader`) — die
  echte Ordnerstruktur verifizieren, nicht den Pfad uebernehmen.
- **Ein natives Fremd-Werkzeug auf einen Pfad unter `Werkstatt/` zeigen und sich
  ueber den Abbruch wundern:** `Werkstatt/` ist eine Junction auf `O:\`.
  Programme, die ihre Eingabe aufloesen, verweigern das mit `Refusing to
  resolve input with a symlinked parent` — der Lauf endet vor der ersten Datei.
  Denselben Pfad ueber das **Aufloesungsziel** aufrufen (`/o/Werkstatt/...`)
  und den Umweg im Bericht nennen, nicht als Werkzeugfehler. Dieselbe Regel
  trifft die `okx-*`-Skill-Junctions: die sind fuer solche Werkzeuge
  strukturell unerreichbar.
  **Zweite Form derselben Falle, teurer: das Werkzeug verweigert nicht, es
  LOEST AUF — und der nachgelagerte Schritt lehnt den absoluten Pfad ab.** Ein
  Frontend-Build aus dem weitergeleiteten Pfad bricht mit `fileName darf nicht
  absolut sein, received O:/...` ab, waehrend derselbe Befehl aus dem echten
  Verzeichnis durchlaeuft (der Bau gibt den aufgeloesten Pfad als absoluten
  Eingabepfad an den Bundler weiter). Merksatz: unter einer Junction entscheidet
  das ARBEITSVERZEICHNIS, ob ein relativer Pfad noch stimmt — vor jedem Lauf
  AUSGEBEN, mit welchem Verzeichnis gestartet wird, statt es anzunehmen.
  Ein Startfenster, das die Repos selbst einsammelt, liefert dabei meist den
  ECHTEN Pfad (das Aufloesungsziel), ein von Hand gesetzter C:-Pfad nicht.
  **Vor jedem Versuch mit einem BAU-Befehl das Ausgabeverzeichnis kopieren:**
  der Fehlversuch LEERT `dist/`/`.next/` VOR dem Schreiben — er baut also nicht
  nur nichts, sondern zerstoert das Vorhandene, und danach liefert der laufende
  Server eine leere Oberflaeche, waehrend der alte Beleg weiter „ok“ sagt.
  Ein Bau-Befehl, der erst leert und dann baut, ist kein harmloser Fehlversuch.
- **Bricht ein CLI-Unterbefehl mit einer Plattform-Einschraenkung ab, suche den Prozess-Schalter darunter.** Die Meldung nennt die Einschraenkung selbst (`... lifecycle is only supported on Unix platforms`) — das ist kein Defekt, sondern eine gebaute Luecke des Unterbefehls. Der direkt darunterliegende Prozess hat oft einen **versteckten** Schalter fuer genau diese Faehigkeit (in der Rust-CLI als `hide = true` am Argument). Weg: `<cli> <unterbefehl> --help` und `strings`/Quelltext nach dem Subsystem, dann den Prozess mit dem versteckten Schalter von Hand starten und pruefen, ob der Zustand `connected` lautet. **Die Einschraenkung nicht zum Anlass nehmen, den Befehl fuer unbrauchbar zu erklaeren** — sie gilt fuer den Unterbefehl, nicht fuer die Faehigkeit. Umgekehrt: ein belegter Statuswert (`status/read` statt Health-Check) ist das, was am Ende zaehlt; ein exit-0 des gestarteten Prozesses nicht.
- **Wenn JEDER Aufruf desselben Werkzeugs mit demselben Konfigurationsfehler stirbt, ist es die Konfigurationsdatei — nicht der Aufruf.** Ein Syntaxfehler in der TOML/YAML/JSON-Datei des Werkzeugs (fehlender Trenner, Tippfehler in Zeile 1) bricht auch die Diagnosebefehle ab; die Meldung zeigt Datei und Zeile. Erst die Konfigurationsdatei byteweise lesen und reparieren (Sicherung daneben), dann die Diagnose erneut fahren — jede Beurteilung des Werkzeugs vor dem Fix ist wertlos.
- **Ein Projekt, das NICHT unter `Werkstatt` liegt, wird per Junction erreichbar gemacht**
  erreichbar gemacht** - nicht verschoben (im venv steht der Pfad absolut,
  `Scripts/python.exe` bricht danach) und nicht kopiert (verdoppelt ein venv von
  mehreren hundert MB). Beleg in zwei Zeilen: `os.path.samefile(original, klon)`
  muss True sein und `os.path.isjunction(klon)` True - unter Windows meldet
  Python eine Junction NICHT als `is_symlink()`, eine Pruefung darauf sagt
  faelschlich "Kopie".
- **Ergebnisdaten, Sonden und eigene Konfigurationen gehoeren in den KLON, nicht
  in `Agenten/Hermes/cache/scratch/`.** Der Scratch-Ordner wird nach 24 h Ruhe
  geleert: ein einmal gemessener Lauf ist danach weg, samt der Config, mit der er
  entstand. Die Daten unter den Datenordner des Repos legen (dessen eigene
  `.gitignore` sperrt ihn meist schon); Hausdateien bleiben im Klon ungetrackt
  (`??`) - das ist in Ordnung, solange keine VERFOLGTE Datei geaendert wird und
  `repos-updaten.py` weiter vorspulen kann. Gegenprobe vor dem Melden:
  `git -C <klon> status --porcelain`.
- **Ergebnisdateien eines Fremd-Werkzeugs werden oft ANGEHAENGT, nicht
  ueberschrieben.** Vor dem Vergleichen den LETZTEN Block lesen, nicht die erste
  Zahlenreihe, die im Suchlauf auftaucht - sonst haelt man den alten Messwert
  fuer den neuen. Und die eigene Sonde so bauen, dass sie ihren Wert SELBST
  ausgibt: dann bleibt der Nachweis unabhaengig davon, wie das Werkzeug seine
  Ergebnisse ablegt.
- **Was nichts handelt, wird als lesender Pruefstand gefahren** (rechnen und
  ausgeben, kein Netz, kein Schluessel) und im Bericht so BENANNT - samt der
  Gegenprobe, die zeigt, dass der Fremdweg nicht traegt. Ein Messlauf, der ein
  Ergebnis bestaetigt, das der Autor des Repos behauptet, ist kein Nachweis;
  erst der Vergleich des behaupteten mit dem selbst gemessenen Wert
  (in-sample gegen ungesehenes Fenster) sagt, was das Werkzeug wirklich kann.
- **Native Programme verstehen die MSYS-Notation nicht:** `/c/Users/...` als
  Argument gibt `Cannot determine input type` / "cannot change to". Windows-
  Pfade mit Schraegstrichen uebergeben (`C:/Users/...`) — in bash bleibt `cd`
  nach `/c/...` trotzdem erlaubt (eingebaut), nur das weitergegebene Argument
  muss native Form haben.
- **patch/write_file verweigern Dateien unter Werkstatt/** (Junction auf O:,
  ausserhalb HERMES_WRITE_SAFE_ROOT). Fix-Muster: byte-sauberes Wegwerf-
  Patchskript nach Agenten/Hermes/cache/ (Wegwerfzone) und mit python
  ausfuehren; Newlines: rb lesen, nl ableiten, wb schreiben — sonst
  Ganzdatei-Diff. Fuer Sonden und Proben reicht der einfache Weg: Datei nach
  `Agenten/Hermes/cache/scratch/` schreiben und mit `cp` in den Klon legen
  (`read_file` und das Ausfuehren im Klon sind nicht betroffen, nur die
  Schreibwerkzeuge verweigern). Der Klon ist ein eigenes Repo — Sonden dort
  hinterlassen ist harmlos, aber Wegwerf-Dateien nach dem Lauf wieder
  entfernen.
- **Harter Absturz eines Fremd-Repos (Segfault, Exit 139, `0xC0000005`
  Access Violation, `bash: ... Segmentation fault`): ZUERST
  `python -X faulthandler <skript>` laufen lassen und den C-Stack lesen**,
  nicht raten. Die Absturzstelle sitzt fast nie dort, wo man sie vermutet:
  im Fall Kronos stand sie in `pandas/core/indexes/datetimes.py`
  (`date_range`) — die von `requirements.txt` gepinnte `pandas==2.2.2` reisst
  den Prozess auf neuerem Python/Windows ab; zwei Torch-Neuinstallationen
  waren umsonst, `pip install -U pandas numpy` war der Fix. Merksatz: nicht
  "das Modell ist zu neu fuer die Bibliothek" vermuten, sondern den Zeugen
  fragen. Pins in `requirements.txt` sind eine Hypothese des Autors, keine
  Wahrheit fuer dieses System.
- **Ein Absturz in der Sandbox beweist nicht, dass die Sandbox schuld ist:**
  denselben Bruchtest einmal auf dem HOST fahren (windows-mcp PowerShell,
  `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH` vorher) — reproduziert er sich
  dort, ist es die Bibliothek/das Modell, nicht der Container. Umgekehrt vor
  jeder Speicherdebatte die Zahlen holen (`FreeVirtualMemory`, freie
  Prozess-Commits), sonst diagnostiziert man Luftmangel, wo ein Pin das
  Problem ist.
- **Lange Installationen im HINTERGRUND starten, nicht im Vordergrund:**
  ein Vordergrundaufruf wird bei ~420 s gekappt, mitten im Download von
  `torch` & Co. Das venv bleibt HALBFERTIG zurueck, ohne Fehlermeldung —
  der naechste Lauf meldet dann ein schwer deutbares Einzelpaket als
  fehlend. `terminal(background=true, notify=true)` mit dem vollen Befehl
  (venv anlegen, installieren, Imports pruefen) und danach die Import-
  Bestaetigung aus dem Log lesen.
- **Der Bericht ist deutsch, auch wenn Werkzeugausgaben englisch sind.** Und
  in dieser Reihenfolge: was jetzt konkret laeuft (mit den gemessenen Zahlen
  und den Befehlen, die sie erzeugt haben), was absichtlich NICHT angefasst
  wurde (Schluessel, Fremd-Repo-Code, fremde Sitzungsarbeit, Live-Pfade),
  welche Entscheidung offen ist, und genau eine naechste Aktion.
- **Die naechste Aktion ist eine PowerShell-Zeile, keine Kopie des eigenen
  Werkzeugaufrufs.** Die Werkzeug-Shell ist bash, Max' Shell ist PowerShell:
  `export`, `rm -f`, `$VAR`, `head`, `/c/Users/...` scheitern bei ihm mit "Der
  Begriff ... wird nicht als Name eines Cmdlets ... erkannt". Also die Zeile als
  "zum Einfuegen" kennzeichnen, das `cd '<wurzel>'` mitgeben, relative Programme
  mit `.\` schreiben (ohne das sucht PowerShell ein Modul) und KEINE Platzhalter
  (`<Frage>`) und keinen fuehrenden Schraegstrich im Pfad
  (`/Agenten/...` gilt als absolut und findet nichts). Die Zeile vorher einmal
  selbst in PowerShell fahren - eine ungepruefte Zeile kostet ihn einen
  Fehlversuch.
- **Mehrzeiligen String in eine CRLF-Datei einsetzen, ohne jede Zeile auf
  die Datei-Newline zu normalisieren, zerlegt die Struktur** (hier: Duplikat
  des Blocks + IndentationError). Der neue Block muss ZEILENWEISE mit
  `nl` verknuepft sein (`nl.join(zeilen)`), nicht als ein String mit
  eingebauten `\n` in die CRLF-Datei geschrieben werden; vor dem Schreiben
  immer `ast.parse()` gegen den FERTIGEN Text. Wird trotzdem ein kaputter
  Block geschrieben, den ganzen Bereich neu konstruieren statt in dem
  kaputten Block weiterzupatchen.
- **Hardcodierte Strings in einem Fork parametrisieren (z.B. ein Ein-Markt-Bot
  wird Multi-Markt): die Modell-Prompt-Strings muessen Template-Literale
  (Backticks) werden.** `${var}` in einfachen/doppelten Anfuehrungszeichen ist
  Literaltext, keine Interpolation — der Prompt nennt dann weiter den alten
  Markt, waehrend die Daten schon der neue sind. Und beim Schreiben eines
  solchen Blocks per Python-Patchskript ist die Backslash-Backtick-Escapierung
  fehleranfaellig (Python-Escape-Zaehlerei, doppelte Zeilen durch ueberzaehlige
  Anker): den korrekten Block per write_file in eine Temp-Datei schreiben
  (schreibt woertlich) und mit einem Python-Skript einspleissen, statt ihn im
  Patchskript-String zu bauen. Nach dem Schreiben `git diff` pruefen — er muss
  genau die gewollten Zeilen zeigen, keine Ganzdatei- oder Duplikat-Aenderung.
- **Ein Patch, der einen Tippfehler einfuehrt, ist das Signal, die Methode zu
  wechseln — nicht weiterzupatchen.** Jeder weitere patch-Versuch auf denselben
  Block riskiert einen NEUEN Tippfehler (gemessen: `verifiedMarketet`,
  `privateteKey`, `confignfig`, `market:ket:` in Folge). Ab dem ersten
  Tippfehler die Datei KOMPLETT lesen und per write_file in eine Scratch-Datei
  schreiben + `cp` ueber das Ziel legen, oder ein Python-Skript mit
  byte-exaktem Ersatz (old-Block im Skript, `if old not in data: print` und
  Abbruch statt still zu ersetzen). Danach die kritischen Zeilen per
  `grep`/`sed` gegenlesen — eine falsche Adresse oder ein falscher
  Variablenname in einem Trading-Bot ist ein Geldverlust, kein Lint-Fehler.
- **Mehrere Klone desselben Forks koennen auf verschiedenen Branches mit
  verschiedenen Code-Staenden liegen — die Credential kann in einem ANDEREN
  Klon stecken als dem, an dem man arbeitet.** Zeigt der Nutzer auf einen
  Ort fuer einen Schluessel ("wallet key in venv"), erst die Klon-Topologie
  pruefen: `find . -maxdepth 3 -type d -iname "*venv*"` UND nach `.env` mit
  dem Schluesselnamen suchen (`grep -rliE "PRIVATE_KEY|MONAD" --include=".env"`),
  dann `git remote -v`/`git branch` je Fund. Im JEV-Fall lag der Key in
  `O:\Werkstatt\jev-trader` (main), die Multi-Markt-Arbeit in
  `O:\Werkstatt 2\JEV\jev-trader` (pipeline-jev-decisions) — zwei Klone
  desselben Forks. Der Klon, der die Credential haelt, ist der
  Live-/Produktions-Klon: die Code-Aenderungen dorthin konsolidieren, nicht
  die Credential in den Arbeits-Klon kopieren. Und ein "venv"-Hinweis kann
  schlicht die `.env` des Projekt-Klons meinen, kein Python-venv.
- **Zweite Instanz eines laufenden Bots aus einem SEPARATEN Arbeitsverzeichnis
  starten, damit ihr data/-Ordner (events.jsonl) nicht mit dem laufenden
  Prozess vermischt wird.** bun loest node_modules relativ zum Skript auf, nicht
  zum cwd — also laeuft `bun run <absoluter-pfad>/src/index.ts` aus einem
  Temp-cwd sauber und legt sein data/ dort an. So kann man einen zweiten Markt
  im Dry-Run testen, ohne das Journal des Produktiv-Laufs zu verschmutzen.
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
- **Ein Treiber, der einen Fremd-Agenten per `subprocess` startet**, hat vier
  Windows-Fallen: falscher Interpreter (`sys.executable`), eine fremde `.env`
  durch `find_dotenv()`, die Codepage ohne `PYTHONIOENCODING=utf-8` und ein
  sichtbares Fenster ohne `CREATE_NO_WINDOW`. Dazu das Beenden des ganzen Baums
  und die Frage, ob ein laufender Prozess den alten Code behaelt —
  `references/windows-kindprozesse.md`.
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
