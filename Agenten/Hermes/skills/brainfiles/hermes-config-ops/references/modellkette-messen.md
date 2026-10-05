# Modellkette messen, dann setzen (Hauptmodell, MoA, auxiliary)

Anlass: "Desktop optimal einrichten", "bestmoegliche Hilfsmodelle", "welches Modell
soll wo laufen". Das Ergebnis ist eine gemessene Kette, keine Empfehlungsliste -
jeder Kandidat wird einmal wirklich gerufen, bevor er in die Datei wandert.

## Kernsatz

**Ein Modellname in einer Config ist eine Behauptung ueber zwei Dinge: dass es
antwortet und dass sein Fenster passt.** HTTP 200 belegt nur das erste, und ein
Denkmodell kann mit HTTP 200 und leerem `content` antworten. Beides gehoert vor
das Setzen gemessen, nicht nachher.

## Schritt 1 - Fenster aus dem Code, nicht aus dem Namen

Nicht raten und nicht aus dem Modellnamen ableiten. Der Loader weiss es:

```bash
cd Agenten/Hermes/hermes-agent && ./venv/Scripts/python.exe - <<'EOF'
import sys; sys.path.insert(0, '.')
from agent.model_metadata import get_model_context_length as g
for m in ("<kandidat>", ...):
    try: print(f"{m:45s}", g(m))
    except Exception as e: print(m, "ERR", e)
EOF
```

Achtung: Ein Name, den der Loader nicht kennt, liefert eine **Fallback-Zahl mit
Warnung** auf stdout ("Could not determine context length ... falling back to
256,000") - das ist KEIN Treffer, sondern eine Vermutung. Unbekannte Namen im
Vergleich gegen einen bekannten Nachbarn (`...-pro` gegen `...-flash`) pruefen.

Fuer lokale Modelle ist der Dienst die Wahrheit und der Modellname im `config`
kann veraltet sein:

```bash
curl -s -m 6 -X POST http://127.0.0.1:11434/api/show -d '{"model":"<name>"}' \
 | python -c "import sys,json; d=json.load(sys.stdin)['model_info']; print([v for k,v in d.items() if 'context' in k][:1])"
```

Der Schluessel heisst nicht `context_length`: je nach Familie `gemma4.context_length`,
`llama.context_length`, ... - nach dem Muster `context` filtern statt einen festen
Namen zu raten.

## Schritt 2 - einmal wirklich rufen (der entscheidende Schritt)

Ein Aufruf ueber den echten Endpunkt mit dem echten Schluessel, mit
**betriebsnahen Parametern**. Der Nous-Weg:

```python
import json, time, urllib.request
d = json.load(open("auth.json", encoding="utf-8"))
key = d["credential_pool"]["nous"][0]["agent_key"]
base = d["credential_pool"]["nous"][0]["inference_base_url"].rstrip("/")
body = json.dumps({"model": m, "messages": [{"role": "user", "content": "Antworte mit genau dem Wort OK."}],
                   "max_tokens": 2000}).encode()
req = urllib.request.Request(base + "/chat/completions", data=body,
    headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
```

Drei Dinge aus der Antwort lesen, nicht zwei:

1. **HTTP-Status** - 404 heisst "dieser Name existiert beim Provider nicht", nicht
   "Provider kaputt". Ein 404 ist ein Befund fuer die Auswahlliste, kein Defekt.
2. **`choices[0].message.content`** - **leer heisst stumm, nicht defekt.** Das ist
   der Normalfall fuer Denkmodelle bei kleinem `max_tokens` (`finish_reason: length`,
   der Text steht im Feld `reasoning`). Ein leerer Inhalt ist nur dann ein Befund,
   wenn dieselbe Sonde ein anderes Modell mit gleichem `max_tokens` sauber antworten
   sieht - der Vergleich, nicht der Einzelwert entscheidet.
3. **Sekunden** - die Antwortzeit gehoert in die Notiz, weil sie die Wahl des
   Aggregators und der Einzeiler-Aufgaben begruendet.

Der Schluessel kommt aus dem Credential-Pool in `auth.json`, nicht aus `.env` und
nicht als Kommandozeilenargument - ein Schluessel auf der Kommandozeile landet im
Protokoll.

## Schritt 3 - die Rechnung, die man beim Setzen anstellt

Jeder Pfad hat eine **Rolle**, und die Rollen sind nicht austauschbar:

| Rolle | Wie oft pro Turn | Fenster | Anspruch |
|---|---|---|---|
| Aggregator (MoA) | in JEDEM Werkzeugschritt, traegt fast die Kosten | maximal | das beste Modell |
| Hauptmodell | jedes Werkzeugschritt | maximal | das beste Modell |
| `auxiliary.compression` | ab und zu | sehr gross | grosses Fenster Pflicht |
| `auxiliary.kanban_decomposer` | selten | mittel | JSON-faehig |
| `approval`, `title_generation`, `memory_query_rewrite`, `skills_hub`, `mcp`, `curator` | **pro Aktion** | klein | das guenstigste belastbare |

Die Zeile, die am meisten Geld kostet und am wenigsten auffaellt:
`provider: auto` in einem `auxiliary`-Block **erbt das Hauptmodell**. Ein
Einzeiler, der das Hauptmodell erbt, zahlt pro Session den Preis des teuersten
Modells. Umgestellt wird auf ein schnell gemessenes kleines Modell.

## Schritt 4 - setzen, byte-sicher, mit toten Schaltern

Der Schreibweg ist derselbe wie bei jeder anderen Config-Aenderung
(references/einstellung-umstellen.md), mit zwei Zusätzen:

- **Tote Schalter vorher suchen.** Ein Schluessel, den `hermes moa list` nicht
  anzeigt und den die Preset-Normalisierung (`hermes_cli/moa_config.py::
  _normalize_preset`) nicht kennt, wird nie gelesen. Ein gesetzter Wert, den kein
  Leser liest, ist eine zweite Wahrheit: er wandert mit und veraltet. Vor dem
  Entfernen den Leser suchen - nicht raten, dass er tot ist, weil er nichts tut.
- **Der Aggregator ist nicht die Beraterliste.** Beide tragen `provider`/`model`,
  aber nur der Aggregator ist das handelnde Modell. Ein lokales, kleines Modell
  im Aggregator-Feld ist kein "günstiger Berater" - es ist das Modell, das jeden
  Werkzeugschritt fährt.

## Schritt 5 - das Block-Ersetzen in YAML ohne Index-Falle

MehrereBloecke einer grossen YAML-Datei in EINEM Skript aendern. Der Ablauf ist
bewaehrt; die Falle ist der Anker.

```python
lines = raw.decode("utf-8").replace("\r\n", "\n").split("\n")
BLOCKS = [(start, end, neue_zeilen), ...]      # 1-basiert, inklusive
for start, end, new in sorted(BLOCKS, key=lambda b: -b[0]):   # von hinten
    lines[start-1:end] = new
neu = NL.join(lines)                              # NL aus dem IST-Zustand
cfg = yaml.safe_load(neu)                         # GEGENPRUEFEN VOR dem Schreiben
assert cfg["x"]["y"] == erwartet
```

Drei Regeln dazu:

- **Von hinten anwenden** (`key=lambda b: -b[0]`), sonst verschieben sich die
  spaeteren Zeilennummern der noch offenen Bloecke.
- **`assert` auf den Zeileninhalt VOR dem Ersetzen, nicht auf die Zeilennummer
  allein.** Ein Skript mit `assert lines[668] == "..."` faengt den Versatz beim
  allerersten Block und benennt die richtige Zeile - ohne das trifft der Ersatz
  still die falsche Stelle und der Bericht nennt eine erfundene Zeilenzahl.
- **Der Anker darf NICHT der erste Treffer eines Mehrfachtreffers sein.**
  `"  aggregator:"` steht in `moa:` zweimal: eingerueckt im Preset und als
  flache Kompatibilitaets-Ausgabe. `lines.index(...)` findet das erste und
  haette beim Ersetzen den halben Dateianfang doppelt eingefuegt. Ab dem
  gesuchten Preset-Namen suchen (`next(k for k in range(i, len(lines)) if
  lines[k] == ...)`) und den Nachbarzeileninhalt mitasserten.
- **`yaml.safe_load` auf das Ergebnis, nicht auf einen Rundenlauf.** Ein
  doppelt eingefuegter Schluessel gewinnt der LETZTE, die Datei sieht richtig
  aus und der Wert gilt trotzdem nicht.

Nach dem Schreiben: `git diff --numstat` je Datei (ein Ganzdatei-Diff bedeutet
gekippte Zeilenenden), `grep -cE '^-[[:space:]]*#'` auf dem Diff = 0 (keine
verlorene Kommentarzeile) und `raw.count(b"\r\n") == raw.count(b"\n")`.

## Nachweisstufen: verdrahtet ist nicht belegt

Nach dem Setzen gibt es zwei Stufen, und sie werden getrennt gemeldet:

| Stufe | Wie belegt | Was sie traegt |
|---|---|---|
| **verdrahtet** | die Aufloesungsfunktion selbst aufrufen, z.B. `auto_cache_ttl_for_source(<source>)` und `effective_cache_ttl(<wert>, model=..., provider=...)`; `config get` zeigt den Wert | der Wert ist richtig gesetzt und der Leser nimmt ihn |
| **belegt** | ein Lauf zeigt die Wirkung im Messwert | die Wirkung |

Die Falle ist der Attributionsfehler: ein Prompt-Cache mit 100 % Read-Anteil
ueber 29 Aufrufe in 8,7 Minuten belegt den Cache, aber **nicht** die 1h-Stufe —
der Unterschied faellt erst bei einer Pause ueber 5 Minuten mit identischem
Prefix auf. Ohne diese Luecke bleiben beide Stufen gleich aussehen. Wenn Stufe
2 fehlt, steht das im Bericht als offener Beleg mit der Angabe, welcher Lauf
ihm liefert (hier: "6 Minuten Pause, dann eine Frage"), statt als Erfolg.

Der Gegenbefund gehoert genauso in den Bericht: liest man NUR die
Sammelzaehler einer Sitzung (`cache_read_tokens` gegen `input_tokens`), sieht
man 1662 % Read-Anteil und schliesst daraus auf alles. Der Zaehler sammelt
ueber die ganze Sitzung, ein Turn dauert Sekunden - er sagt nichts ueber eine
einzelne Anfrage. Der belastbare Wert steht **pro API-Aufruf** im Log:

```
grep "API call #" logs/agent.log | tail -40
```

Dort steht `cache=<read>/<prompt> (<pct>%)` je Aufruf. Erst diese Zeilen
gegen die Zeitstempel sortieren und Pausen > 5 min suchen - erst dann ist die
Tier-Frage beantwortbar.

## Beleg

- `hermes moa list` zeigt die geänderten Presets (Aggregator-Zeile je Preset).
- `hermes config check` exit 0.
- `hermes config get <schluessel>` je geändertem Schlüssel.
- **Ein echter Lauf durch den geänderten Pfad.** MoA headless messbar:
  `hermes chat --oneshot -q "Antworte in genau einem Wort: MARKE" --provider moa`
  (Dauer und Referenzzaehler im Output). Der Hauptlauf ohne `--provider`.
  Antwort danach aus `state.db` lesen, nicht aus dem Terminal-Bild:
  `select role, content from messages where session_id=?` — dort steht, was
  tatsaechlich gespeichert wurde.
- **Ein Aufruf, der auf dem Fallback endet, belegt den Aggregator NICHT.** Nach dem
  MoA-Lauf die Fehlschlagspur prüfen, nicht die Antwort:
  `grep -E "provider=moa|moa_aggregator" logs/agent.log` und die Zeilen danach lesen.
  Retries, die den Aggregator nie erreichen, hinterlassen als einzige Spur einen
  Fallback-Aufruf mit gutem Cache-Anteil - der sieht wie Erfolg aus und ist es nicht.
  Ein Preset gilt erst als funktionierend, wenn ein Turn den Aggregator
  **vollendet** hat (Ausführen des Fallbacks noch zählen, siehe die Maskierungsregel
  in references/config-gegenprobe.md).

## Wo der Renderer eine gesetzte Config-Wirkung beweist

Eine App-spezifische Einstellung ist belegt, sobald der **Prozess** sie traegt,
nicht sobald die Datei sie enthaelt. Fuer den Desktop z.B. `renderer_max_old_space_mb`:
der Renderer muss beim Start mit `--js-flags=--max-old-space-size=<wert>` laufen.

```
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='Hermes.exe'\" |
  Where-Object { \$_.CommandLine -match 'max-old-space' } | Select-Object ProcessId,CommandLine | Format-List"
```

Entweder steht die Flag-Zeile im Kommandozeilen-Text des Prozesses, der nach
dem Neustart gestartet wurde, oder die Einstellung ist nicht angekommen. Die
ehrliche Kontrollfrage ist dabei immer: hat nach dem Neustart ueberhaupt ein
Turn durch den geaenderten Pfad gelaufen? Eine neue Sitzung ohne Turn belegt den
Prozess, nicht die Wirkung.

**Die Prozessliste zaehlen ist nicht dasselbe wie das Flag zuordnen.** Mehrere
Prozesse desselben Namens (Electron-Launcher, Renderer, Helper - oft ein Dutzend
Eintraege mit demselben `Name`) lassen die richtige Zeile im Rauschen verschwinden.
Deshalb **die Zuordnung filtern, nicht die Liste lesen**:

```
Where-Object { \$_.CommandLine -match 'max-old-space' }
```

Ergaenzend die **Startzeit** mitschreiben (`CreationDate`) und gegen den
Neustartzeitpunkt halten: eine Zeile mit passendem Text, aber altem
`CreationDate` ist ein Prozess von VOR der Aenderung und beweist nichts. Beide
Filter zusammen sind der Beleg; jeder allein liefert eine Fehlmoeglichkeit in
beide Richtungen - zu viel Treffer (falscher Prozess) oder zu wenige (der
gesuchte Prozess war nicht neu).

**Zahlen aus Sammelzaehlern sind keine Wirkung** - das gilt fuer jeden
Sitzungs-Summenwert, nicht nur fuer den Cache: eine Session kann 700 Aufrufe
zusammengezaehlt haben und trotzdem nie durch den geaenderten Pfad gelaufen sein.
Fuer den Nachweis einer geaenderten Route ist der Einzelaufruf die Einheit, die
zaehlt (siehe die Logzeilen oben).