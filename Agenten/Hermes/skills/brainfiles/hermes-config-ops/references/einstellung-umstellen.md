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
- **Kein headless-Lauf fuer MoA.** `hermes moa` kennt nur `list`, `configure`, `delete`;
  `/moa <prompt>` gibt es nur in einer interaktiven Sitzung. Den Aggregator deshalb
  direkt mit einem ECHTEN Aggregationsauftrag rufen (Systemzeile + drei
  Referenzantworten + Verdichtungsauftrag) und `content` gegen `reasoning` messen -
  das belegt die Kette bis zum Modell, aber nicht die Werkzeugschleife.
- **Ein doppelt eingefuegtes Feld ist wirkungslos.** Im JSON/YAML gewinnt der LETZTE
  Schluessel; nach dem Einfuegen `json.loads`/`yaml.safe_load` gegenpruefen, sonst steht
  die gewollte Aenderung im Diff und gilt trotzdem nicht.

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
