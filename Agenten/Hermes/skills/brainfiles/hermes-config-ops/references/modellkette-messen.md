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

## Beleg

- `hermes moa list` zeigt die geänderten Presets (Aggregator-Zeile je Preset).
- `hermes config check` exit 0.
- `hermes config get <schluessel>` je geändertem Schlüssel.
- **Ein echter Lauf durch den geänderten Pfad.** MoA headless messbar:
  `hermes chat --oneshot -q "Antworte in genau einem Wort: MARKE" --provider moa`
  (Dauer und Referenzzaehler im Output). Der Hauptlauf ohne `--provider`.
  Antwort danach aus `state.db` lesen, nicht aus dem Terminal-Bild:
  `select role, content from messages where session_id=?` - dort steht, was
  tatsaechlich gespeichert wurde.