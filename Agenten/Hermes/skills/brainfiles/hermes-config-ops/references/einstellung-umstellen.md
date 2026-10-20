# Eine Einstellung umstellen - mit Beleg und ohne Kollateralschaden

Anlass: "stell X auf Y um", "nimm Z raus", nach dem Ausfall eines Dienstes.
Beispiel vom 29.09.2026: die MoA-Presets `Max 2` und `Vision` hatten `bonsai` als
Aggregator - dort laeuft die ganze Werkzeugschleife, nicht nur eine Beratung -
und der Dienst antwortete nicht.

## Reihenfolge

1. **Zustand LESEN, nicht erinnern.** `hermes moa list`, `hermes config get <block>`,
   `hermes fallback list`. Der Befehl zeigt, was gilt; die Datei zeigt, was gemeint war.
2. **Das Ziel gegen die Wirklichkeit pruefen - es muss es GEBEN.**
   `POST /api/show {"model":"<name>"}` gegen Ollama liefert `*.context_length` und
   `*.parameter_count`; ein offener Port; eine vorhandene Datei. Der Name allein ist keine
   Zusage (siehe Falle 1).
3. **Blast radius bestimmen.** `search_files` nach dem alten Wert in Hauptconfig UND
   `profiles/*/config.yaml`. Zwei Treffer je Datei sind normal (`api:` und `base_url:`);
   20 Profile heissen 40 Stellen - wer eine uebersieht, laesst eine halbe Umstellung zurueck.
   Bei einem Aux-Auftrag ist der Radius kleiner als die Flotte: `grep -l '^auxiliary:'
   profiles/*/config.yaml` zaehlt nur die Profile MIT Block - ein Profil ohne Block hat den
   Standard schon und darf nicht angefasst werden.
4. **Byte-sicher aendern** (Muster unten): Vorkommen ZAEHLEN, `yaml.safe_load` VOR dem
   Schreiben, Sicherung anlegen, danach CR == LF und `git diff --numstat` pruefen.
5. **Nachweis fahren:** der Hermes-Befehl zeigt das Neue (`hermes moa list`),
   `hermes config check` exit 0, `git diff --numstat` N/N.
6. **Was stehen BLEIBT** (bewusst):
   - ein toter Eintrag in einer Fallback-Kette - er faellt durch und greift wieder,
     sobald der Dienst laeuft;
   - der `providers.<dienst>`-Block des abgeschalteten Dienstes (sonst ist ein
     spaeterer Start eine Neuverkabelung);
   - Kommentare und Presets, die nichts mit der Umstellung zu tun haben.
7. **Buchhaltung:** offenen Task auf erledigt setzen MIT Nachweis, Fremdarbeit liegen
   lassen, committen, pushen.

## Auf den Standard zuruecknehmen: `unset` statt Wert setzen

Gilt, wenn das Ziel der VORGABEWERT ist ("ueberall auto", "nimm die Uebersteuerung
raus"). Ein Wert, der den Standard ausspricht, ist eine zweite Wahrheit: er muss in
jeder Datei gepflegt werden, kann veralten und macht aus einem Default eine
Einstellung.

    hermes config unset auxiliary.compression            # Hauptprofil
    hermes -p <profil> config unset auxiliary.compression # je Profil

Danach gilt der Standard aus `config_defaults.py` (`provider: auto`, `model: ""` =
Hauptmodell). Pruefen, dass die Aufloesung greift - nicht, dass der Block weg ist:

    hermes config get auxiliary.compression   # provider: auto / model: ''
    hermes config check                       # exit 0

Je Datei dieselbe Leiter wie bei jeder Massenaenderung:

1. `.bak-JJJJMMTT` in `cache/scratch/` (Stufe 1).
2. Restblock-Suche, die den Block INNERHALB von `auxiliary:` findet - nicht irgendwo:
   `sed -n '/^auxiliary:/,/^[a-z]/p' <datei> | grep '^  compression:'` muss leer sein.
   Ein `grep -c compression:` zaehlt sonst den gleichnamigen TOP-LEVEL-Block
   (`compression: enabled/threshold`) mit und meldet faelschlich Reste.
3. `git diff --numstat` JE Datei: erwartet sind wenige Zeilen (3/4 bis 6/10 fuer einen
   entfernten Vier-Zeilen-Block). Der Ueberhang ist die vom Config-Schreiber
   VEREINHEITLICHTE Einrueckung verschachtelter Listen (die `models:`-Liste eines
   Providers bekommt zwei Spaces mehr) - inhaltlich nichts, aber es sieht nach mehr aus
   als der eigenen Aenderung. Hunderte Zeilen heissen dagegen gekippte Zeilenenden.
4. Kommentarverlust zaehlen: `grep -cE '^-[[:space:]]*#' <diff>` muss 0 sein (bzw. gleich
   der Zahl der `+`-Kommentarzeilen) - `hermes config set`/`unset` schreibt die ganze
   Datei neu und kann den Doku-Schluss abschneiden.
5. Zeilenenden: `b.count(b'\n') == b.count(b'\r\n')` in den ROHEN Bytes (Hausformat CRLF).

**Wirkung nicht ueberversprechen.** Belegt ist die AUFLOESUNG des Standards; ein echter
Kompressionslauf ist der haertere Beleg und bleibt ein eigener Schritt. Eine LAUFENDE
Sitzung kann ihren bereits aufgeloesten Aux-Client behalten - die Aenderung greift in
neuen Sitzungen, nicht mitten in der alten.

## Eine .env-Variable setzen: wirkt erst nach dem Neustart

Anders als `config.yaml` wird `.env` **einmal beim Prozessstart** gelesen
(`load_hermes_dotenv()` auf Modulebene in `cli.py` bzw. im Gateway-Bootstrap).
Ein laufendes Gateway, ein Cron-Job und eine offene Sitzung tragen den alten
Stand im `os.environ` - die Datei kann richtig sein und die Wirkung fehlt
trotzdem. "Steht drin" ist deshalb kein Beleg.

1. **Erst suchen, WO der Wert gelesen wird.** `search_files` nach dem
   Variablennamen im Checkout: Modul plus die Doku-Tabelle
   `website/docs/reference/environment-variables.md`. Ein Eigenbau ohne
   dokumentierte Stelle gehoert nach config.yaml oder in einen Code-Schalter,
   nicht in die `.env`.
2. Zeile anhaengen (Muster unten), Zeilenenden und Sicherung mitpruefen.
3. **Zweiseitiger Gegentest im Haus-Interpreter**, nicht "Zeile vorhanden":
   dieselbe Funktion ohne und mit der Variable aufrufen.

   ```python
   import os, sys; sys.path.insert(0, "hermes-agent")
   os.environ.pop("HERMES_DISABLE_FILE_STATE_GUARD", None)
   from tools import file_state
   print(file_state.guard_disabled())          # False
   os.environ["HERMES_DISABLE_FILE_STATE_GUARD"] = "1"
   print(file_state.guard_disabled())          # True
   ```
   Beide Werte nennen. Ein einzelnes `True` belegt nur, dass die Variable
   gelesen wird - nicht, dass das Haus sie auswertet.
4. **Wirkung ehrlich eingrenzen.** Ein `export` in der eigenen Shell gilt fuer
   `terminal`, nicht fuer den Agentenprozess. Gateway: Neustart ueber die
   Aufgabensteuerung; Cron und Subagenten: der aufrufende Prozess. Fehlt der
   Satz "wirkt ab dem naechsten Neustart, nicht in dieser Sitzung" im Bericht,
   ist die Meldung irrefuehrend.

**Muster: eine Zeile anhaengen, ohne die Datei zu kippen**

```python
roh = open(p, "rb").read()
nl = b"\r\n" if roh.count(b"\r\n") == roh.count(b"\n") else b"\n"
neu = roh + (b"" if roh.endswith(nl) else nl) + b"NAME=1" + nl
assert neu != roh and len(neu) > len(roh)
shutil.copy2(p, p + ".bak-" + stamp)          # VOR dem Schreiben anlegen
open(p, "wb").write(neu)                      # Inhalt VORHER fertig bauen
```

Die Haus-.env ist CRLF; ein Anhaengen mit `\n` macht eine gemischte Datei.
Hermes liest beides, jedes Skript, das auf Zeilenenden prueft, nicht.

**Einen Schutzschalter abzuschalten heisst: die Kosten benennen — und erst messen, ob er das ueberhaupt loest.** Die Abschaltung wirkt still. `HERMES_DISABLE_FILE_STATE_GUARD=1` schaltet die Pruefung "Datei seit dem Lesen geaendert" auf `write_file` ab (`tools/file_tools_write_guards.py::_stale_overwrite_blocker()` liefert dann `None`) - und trifft damit genau die Schreibvorgaenge, gegen die sie gerichtet war: parallele Sitzungen und Subagenten. `patch` ist gar nicht betroffen. Beim Setzen benennen: `patch` und `read_file` bevorzugen, und TASKS.md, config.yaml und die wachen.json sind die riskanten Pfade.

**Der Reichweiten-Test kommt VOR dem Setzen, nicht danach.** Der naheliegende Wunsch ist „die anderen Sitzungen sollen meine Datei nicht ueberschreiben" — und genau den loest das Abschalten NICHT. `FileStateRegistry` ist laut eigenem Docstring **prozessweit**, nicht sitzungsweit: alle Telegram-Sitzungen, Background-Delegationen und Cron in EINEM Gateway teilen sie. Was sie nicht sieht, sind ANDERE PROZESSE — Bot-Profile, Kanban-Worker, eine zweite Hermes-CLI, eine parallele Claude-Sitzung. Also die Frage stellen: **welcher Konflikt stoert mich, und liegt sein Schreibvorgang im selben Prozess?** Trifft die Stoerung eine andere Maschine, loest Abschalten sie nicht, kostet aber den Schutz genau dort, wo er im Haus wirkt. Die Antwort auf „anderes loesen" ist dann Besitz pro Bereich, nicht Guard aus — nicht aufheben, was man behalten will.

**Ein Schutzschalter wird NICHT spekulativ gesetzt.** Reihenfolge: (1) den Mechanismus messen (welche Datei liest die Variable, was liefert die Aufrufstelle damit), (2) dem Nutzer die Kosten und den Reichweiten-Test nennen, (3) auf die Freigabe warten. Wer statt dessen zuerst in die `.env` schreibt und danach fragt, hat dem laufenden System eine Aenderung untergeschoben — und muss sie zuruecknehmen. Max sagt dann regelmaessig „warte damit" und verlangt den Beleg, dass die Schutzlage unveraendert ist.

**Das Zuruecknehmen ist byteweise zu belegen, nicht zu behaupten.** Aus der eigenen Zeile die Sicherung zurueckspielen und HASHEN vergleichen, nicht Zeilenenden zaehlen:

```python
roh = open(p, "rb").read(); neu = open(p + ".bak-" + stamp, "rb").read()
assert b"NAME" in roh and b"NAME" not in neu          # die Zeile ist wirklich drin
neu_alt = roh[:-(len(b"NAME=1") + len(nl))]           # Zeile + Zeilenende ab
assert neu_alt == neu, "Restweichen - nicht zurueckspielen"
open(p, "wb").write(neu)                             # Inhalt VORHER geprueft
assert hashlib.sha256(open(p,"rb").read()).hexdigest() == hashlib.sha256(neu).hexdigest()
```

`open(p,"wb").write(alt)` schreibt die Datei SOFORT leer und der Vergleich danach laeuft gegen 0 Byte — der Inhalt muss vor der Datei geprueft sein. Zusaetzlich im Bericht: dass die Abschaltung am laufenden Gateway ohnehin nichts geaendert hat (die Datei wird erst beim Start gelesen), damit niemand einen Neustart als noetig missversteht.

## Byte-sicheres Muster (Konfigdatei)

```python
roh = CFG.read_bytes()
nl = "\r\n" if b"\r\n" in roh else "\n"          # Endungen des IST-Zustands uebernehmen
text = roh.decode("utf-8")
if text.count(ALT) != 2: raise SystemExit("Zaehlung stimmt nicht")   # VOR dem Ersetzen
neu = text.replace(ALT, NEU)
assert yaml.safe_load(neu)["moa"]["presets"]["Vision"]["aggregator"] == {"provider": "ollama-launch", "model": "gemma-e4b-8k:latest"}
shutil.copy2(CFG, CFG.with_name(f"config.yaml.bak-moa-{stamp}"))
CFG.write_bytes(neu.encode("utf-8"))
nach = CFG.read_bytes(); assert nach.count(b"\r") == nach.count(b"\n")
```

Die Zaehlung ist kein Formalismus: derselbe Block steht mehrfach mit UNTERSCHIEDLICHER
Einrueckung im selben Block (`      aggregator:` in zwei Presets, `  aggregator:` top-level).
Ohne Zaehlung trifft der Ersatz die falsche Stelle oder alle.

### Blindes `lines.index()` trifft die FALSCHE Stelle - ab dem Anker suchen

`config.yaml` ist eine Blattdatei, kein AST; Zeilenindizes sind billig, aber die
Anker-Zeile kommt oft MEHRFACH vor. `lines.index("  aggregator:")` findet das
ERSTE Vorkommen im ganzen Dokument - auch dann, wenn der Preset, den man
ersetzen will, weit hinten steht. Das Ergebnis ist kein Syntaxfehler: der Block
wird an der falschen Stelle eingesetzt, die Datei parst weiterhin, und die
Gegenprobe schlaegt erst an einer Stelle fehl, an der man nicht gesucht hat.

```python
# FALSCH: global suchen
i = lines.index("    Max 2:")
j = lines.index("  aggregator:")

# RICHTIG: ab dem gesuchten Anker suchen + Nachbarzeile als Zeuge
i = lines.index("    Max 2:")
j = next(k for k in range(i, len(lines)) if lines[k] == "  aggregator:")
assert lines[j + 1].strip() == "provider: nous", lines[j + 1]
```

Drei Regeln dazu, die zusammen gehoeren:

1. **Ab dem Anker suchen**, nicht vom Dateianfang - `next(k for k in range(i, ...))`.
2. **Jede Blockgrenze mit der Nachbarzeile belegen**, nicht nur mit der
   Fundstelle: `assert lines[ende] == "<erwartete Zeile>"` fuer Anfang UND Ende.
   Eine Assertion, die erst beim DRITTEN Mal traf, war jeweils ein um eine Zeile
   verschobener 1-basierter Index - 0-basierte Indizes in den Skript-Notizen,
   1-basierte in `assert`-Zeilen sind die Fehlerquelle.
3. **Vor dem Schreiben gegenlesen**, was der neue Block an der Zielstelle tut:
   `yaml.safe_load(neu)` muss die neuen Werte zeigen. Ein Block, der an der
   falschen Stelle landet, laesst die Werte dort KORREKT aussehen, wenn man nur
   den Block selbst prueft.

Ein Duplikat-Schluessel als Zusatzprobe: `assert "- provider: bonsai" not in text`
faengt einen Rest, den eine Uebersicht ueber Objektnamen (statt ueber Zeilen)
verpasst, weil der Kommentar das Wort noch nennt.

### Drei Fehler, die derselbe Byte-Pfad ein zweites Mal produziert

Alle drei entstehen **vor** dem Schreiben, werden aber erst danach teuer - und
zwei davon schreiben trotzdem.

1. **Ein Kommentar als YAML-Schluessel ist eine erfundene Einstellung.**
   Wer eine Erklaerung anlegen will, schreibt leicht
   `delegation_fallback_note: >` plus Text. YAML parst das anstandslos, der
   Schluessel erscheint in jeder Config-Ansicht und in jedem Dashboard als
   Einstellung, die es nicht gibt, und ein spaeterer Leser (oder der Nutzer in
   den Einstellungen) sucht vergeblich nach ihrem Schalter. Erklaerungen gehoeren
   an die Stelle, die sie erklaeren - als `#`-Kommentar INNERHALB des Blocks, den
   sie erklaeren, nicht als eigener Schluessel daneben.

2. **`ALT` ist ein Praefix von `NEU` - die Abwesenheitspruefung ist dann
   widerspruechlich.** Nach `neu = text.replace(ALT, NEU)` mit
   `assert ALT not in neu` schlaegt der Lauf fehl, obwohl die Ersetzung
   funktioniert hat: `NEU` enthaelt `ALT` als Anfang. Richtig ist, auf das zu
   pruefen, was die Ersetzung bewirkt hat: `assert neu.count("  telegram:") == 1`,
   nicht `assert ALT not in neu`.

3. **Die Zeilenend-Gegenprobe schlaegt auch fehl, wenn nur die ERSAETZUNGS-
   Literale falsch sind.** `count(b"\r\n") == count(b"\n")` setzt voraus, dass
   die eingefuegten Bloecke dieselbe Form haben wie die Datei. Ist die Datei LF
   und kommt ein CRLF-Literal hinein, meldet die Probe "Zeilenenden gemischt" -
   aber die Datei war vorher einwandfrei. Also **die Form aus der Datei ableiten
   und die Literale daran anpassen** (`nl = "\r\n" if ... else "\n"`, jede
   Zeile `rstrip("\r")` nach dem Split), statt die Probe am Ende zu haben. Wer
   die Probe anstelle dieser Reihenfolge benutzt, sucht den Fehler in der
   Datei, die er selbst gerade geschrieben hat.

Faellt eine dieser Pruefungen an, ist die Frage immer: **ist die Datei kaputt
oder mein Skript?** Nicht die Datei "reparieren", sondern das Skript richten und
den Lauf wiederholen - sonst schreibt man eine zweite Korrektur in eine bereits
kaputte Datei.

## Fallen

- **Ein zu kleines `max_tokens` macht ein Denkmodell stumm - und den Pruefer blind.**
  Bei `max_tokens: 90` lieferten `gemma-e4b-8k:latest`, `gemma-e4b-8k:cpu` und
  `deepseek-chat:latest` ueber Ollamas `/v1` LEEREN `content` (`finish_reason: length`,
  Text im Feld `reasoning`); mit `max_tokens: 2000` kam bei allen dreien sauberer
  `content` (`finish_reason: stop`). Der Befund war ein Artefakt der Sonde - gemeldet
  haette er eine Massenreparatur an 20 Profilen ausgeloest. Immer mit betriebsnahen
  Parametern messen und eine Auffaelligkeit mit anderen Parametern gegentesten.
- **Eine leere Pipe wird zum JSON-Fehler und sieht wie ein Dienstproblem aus.**
  `/usr/bin/env time -f "%es" curl ... | python -c json.load` scheitert in MSYS, weil
  `/usr/bin/time` dort NICHT existiert: curl laeuft nie, die Pipe ist leer, und der
  Fehler lautet `JSONDecodeError: Expecting value: line 1 column 1 (char 0)` - also
  genau wie eine stumme Gegenstelle. Erst die Rohantwort ohne Pipe ansehen, dann urteilen.
  Fuer die Dauer `start=$(date +%s)` und `$(( $(date +%s) - start ))` nehmen.
- **MoA laesst sich headless ueber `--provider moa` fahren.** `hermes moa` kennt nur
  `list`/`configure`/`delete` und `/moa <prompt>` nur in einer interaktiven Sitzung -
  der Einzeiler aber:
  `hermes chat --oneshot -q "Antworte in genau einem Wort: MARKE" --provider moa`
  fährt Berater, Aggregator und Synthese vollstaendig und nennt Dauer und
  Referenzzaehler. Das ist der Beleg, den eine reine Aggregations-Sonde nicht liefert
  (die belegt die Kette bis zum Modell, nicht die Werkzeugschleife).
  **Antwort danach aus `state.db` lesen**, nicht aus dem Terminal-Bild:
  `select role, content from messages where session_id=?` - dort steht, was
  wirklich gespeichert wurde.
- **Ein doppelt eingefuegtes Feld ist wirkungslos.** Im JSON/YAML gewinnt der LETZTE
  Schluessel; nach dem Einfuegen `json.loads`/`yaml.safe_load` gegenpruefen, sonst steht
  die gewollte Aenderung im Diff und gilt trotzdem nicht.
- **`hermes config set` akzeptiert einen Key, den der Laufzeit-Leser nicht liest.**
  `agent.max_tokens` wird gespeichert (mit Warnung "not a recognized config key"), aber
  der Haupt-Agent bekommt es nie — der Runtime-Resolver baut kein `max_tokens` ins
  Agent-Dict. Der funktionierende Weg fuer eine Antwortlaengen-Grenze ist
  `model.request_overrides.max_tokens`: `request_overrides` wird direkt in die
  API-Kwargs eingebaut (`agent/chat_completion_helpers.py:626`
  `api_kwargs.update(params["request_overrides"])`). Vor dem Setzen pruefen, ob der
  Key ein Runtime-Leser hat (`rg -n '"<key>"' hermes_cli/config_defaults.py` UND
  `rg -n '<key>' --glob '!tests' .`), nicht nur ob `config set` ihn annimmt. Ein
  gespeicherter, ungelernter Key ist eine tote Einstellung, die wie Absicht aussieht.

## Belegmuster (29.09.2026)

```
hermes moa list            -> Aggregator: ollama-launch:gemma-e4b-8k:latest (Max 2, Vision)
hermes config check        -> exit 0
git diff --numstat         -> 7  7  Agenten/Hermes/config.yaml   (CR 2453 == LF 2453)
POST 127.0.0.1:11434/v1/chat/completions  -> finish stop, content 206 Zeichen, 19 s
```

Der Zustand vorher gehoert in den Bericht: `bonsai` als Aggregator, Port 8081 zu.
Und der verbleibende offene Punkt ebenso (bonsai bleibt an Stelle 2 der
Delegations-Fallbacks) - eine Umstellung, die ihren Rest verschweigt, ist keine.

## Belegmuster (Ruecknahme auf den Standard, 30.09.2026)

```
vorher: Hauptprofil omniroute/auto/best-free; 6 Profile auto/best-fast|-free
9 Dateien beruehrt (Hauptprofil + 8 Profile), 22 Profile + Hauptprofil ohne Block
je Datei: numstat 3/4 bis 6/10 (Ueberhang = vereinheitlichte Listen-Einrueckung)
CRLF == Zeilen in allen 9 Dateien, 0 verlorene Kommentarzeilen
after: hermes config get auxiliary.compression -> provider: auto / model: ''
       hermes config check -> exit 0
```

---

## Vollstaendiger Abschnitt aus dem SKILL.md-Rumpf

# Eine Einstellung umstellen


Reihenfolge: Zustand LESEN (`hermes moa list`, `config get`) -> das ZIEL gegen die
Wirklichkeit pruefen (es muss es geben: `/api/show` fuer Kontext und Parameter,
offener Port) -> Blast radius (`search_files` nach dem alten Wert in Hauptconfig UND
`profiles/*/config.yaml`) -> byte-sicher aendern (Vorkommen zaehlen, `yaml.safe_load`
VOR dem Schreiben, `.bak`, danach CR == LF und `git diff --numstat`) -> Nachweis
(`hermes moa list`, `config check` exit 0) -> Buchhaltung.

Zwei Regeln, die den Unterschied machen:

- **Messen mit betriebsnahen Parametern.** Ein zu kleines `max_tokens` macht ein
  Denkmodell stumm (leerer `content`, Text in `reasoning`) - am 29.09.2026 sah das nach
  einem Defekt in 20 Profilen aus und war ein Artefakt der eigenen Sonde.
- **Eine leere Pipe ist kein Befund.** Fehlt das Messwerkzeug (`/usr/bin/time` gibt es
  in MSYS nicht), laeuft der Aufruf nie, und der JSON-Fehler sieht wie eine stumme
  Gegenstelle aus.

Vollstaendig mit Muster und Fallen: `siehe oben in dieser Datei`.
