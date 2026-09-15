# Fallback-Kette: aufbauen und belegen

## Was Hermes liest

`hermes_cli/fallback_config.py::get_fallback_chain` merged zwei Schlüssel:

- `fallback_providers` — Liste, führend, Reihenfolge zählt.
- `fallback_model` — Altform (Einzelwert), wird nur angehängt, wenn er auf dasselbe
  Ziel zeigt nicht schon in der Liste steht. In einer frischen Config steht er nur als
  auskommentierter Beispielblock am Dateiende.

`fallback_providers: []` ist der Zustand nach Setup-/Update-Läufen — eine Kette, die
vorher im Arbeitsbaum stand, kann dabei verschwunden sein. Auslöser sind Lauf
(`hermes setup`, `hermes update`, `hermes fallback clear`) und Speichern aus der App.

## Eintrag für ein lokales Modell

Ein lokaler Provider ist kein Sonderfall: derselbe Name wie im `providers:`-Block,
plus `base_url`.

```yaml
fallback_providers:
  - provider: custom
    model: gemma-e4b-8k:latest
    base_url: http://127.0.0.1:11434/v1
```

Regel: **`base_url` mitgeben**, auch wenn der Provider-Block sie schon hat — der Eintrag
wird eigenständig aufgelöst. Ein Eintrag ohne erreichbares Ziel fällt still durch.

`custom` ist der mitgelieferte Profilname für **jeden** lokalen OpenAI-kompatiblen
Endpunkt (`plugins/model-providers/custom/`); `ollama`, `local`, `vllm`, `llamacpp`,
`llama.cpp` und `llama-cpp` sind Aliase desselben Profils. `provider: llamacpp` und
`provider: custom` sind dasselbe — `hermes fallback list` zeigt beide als `via custom`.
Der transportable Eintrag nennt `custom` plus `base_url`, nicht einen Blocknamen aus
`providers:`.

## Felder eines Eintrags

`fallback_config.py::_iter_fallback_entries` behält nur Einträge, deren **`provider` und
`model` nicht leer** sind; `base_url` wird um den Schlussschrägstrich gekürzt. Als
Zugangsdaten gelten `api_key` (inline) oder `key_env`/`api_key_env` (Variablenname, über
den Secret-Scope aufgelöst). Ein lokaler Dienst braucht keinen Schlüssel: bleiben beide
leer, fällt die Auflösung auf die reguläre Zugangsdaten-Suche zurück, und Ollama
ignoriert den Wert ohnehin.

## Schreiben ohne Picker

`hermes fallback add` ist ein Auswahlmenü und hängt in einer Werkzeugsitzung. Stattdessen
die Liste als strukturierten Wert setzen — `config set` parst YAML/JSON, wenn der
Standardwert des Schlüssels kein String ist:

```powershell
hermes config set fallback_providers '[{"provider":"custom","model":"gemma-e4b-8k:latest","base_url":"http://127.0.0.1:11434/v1"}]'
```

Ein Wert, der nicht sauber parst, wird als **String** gespeichert und von den
`isinstance`-geprüften Lesern ignoriert. Deshalb nach jedem Setzen `hermes fallback list`
lesen und die Zahl der Einträge gegen die Absicht zählen — ein stillschweigend
verworfener Eintrag sieht sonst wie Erfolg aus. Die Änderung greift ohne Neustart
(`run_config_loaders.py` liest die Kette zur Laufzeit neu).

## Beleg-Rezept (in dieser Reihenfolge)

1. **Was gilt:** `hermes fallback list` — das ist die Wahrheit, nicht `grep` in der YAML.
   Aber nur bei **gesetztem `HERMES_HOME`**: ohne die Variable liest der Befehl
   `%LOCALAPPDATA%\hermes\config.yaml` und meldet „No fallback providers configured",
   obwohl die Kette in `Agenten\Hermes\config.yaml` steht.
2. **Was der Dienst wirklich anbietet:**
   `curl -s http://127.0.0.1:11434/api/tags` — Namen, Quantisierung, Größe und
   `capabilities` (`tools`/`thinking` müssen dabei sein, sonst kann das Modell die
   Werkzeugaufrufe der Kette nicht fahren).
   Warnung: `curl` ohne `-m` kann hängen, wenn der Dienst nicht läuft — immer mit
   Timeout aufrufen.
3. **Dass der Pfad trägt:** ein echter Aufruf über die OpenAI-Schnittstelle mit kleiner
   Antwortgrenze:

   ```
   curl -s -m 120 http://127.0.0.1:11434/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"<name>","messages":[{"role":"user","content":"Antworte nur mit: BEREIT"}],"max_tokens":8,"stream":false}'
   ```

   Kommt die feste Antwort zurück, steht der **Transport** — mehr nicht: dieser Aufruf geht
   am Agenten vorbei. Ein Eintrag in der YAML ist ebenso wenig ein Beleg. Dass die Kette
   wirklich **übergibt**, belegt erst der Funktionstest unten.

## Dass die Kette wirklich übergibt (Funktionstest)

Ohne Primärausfall läuft die Kette nie. Also den Ausfall erzwingen — in einem **eigenen
Test-`HERMES_HOME`** (Ablage und Aufräumen: Fallen in SKILL.md), damit die echte Config
unberührt bleibt:

1. `home/config.yaml` anlegen: Primär auf einen toten lokalen Endpunkt
   (`provider: custom`, `base_url: http://127.0.0.1:9/v1`). Bewusst `custom`, weil dieses
   Profil **ohne Schlüssel** auskommt (`env_vars=()`)
   und der Lauf deshalb nicht an einer fehlenden Anmeldung scheitert — ein Cloud-Primär
   bricht vorher mit „not logged into … Portal" ab, und der Test erreicht die Kette nie.
   Dazu `agent.api_max_retries: 1` (sonst dauert das Fehlschlagen lange) und die zu
   prüfende `fallback_providers`-Liste.
2. `HERMES_HOME=<testhome> python -m hermes_cli.main -z "Antworte mit genau einem Wort: <marke>"`
   — kommt die Marke zurück, hat der lokale Dienst geantwortet.
3. **Kontrolllauf mit falschem Fallback-Modell** (`model: gibt-es-nicht:latest`): erwartet
   wird der Fehler des lokalen Dienstes (`HTTP 404: model … not found`). Erst dieser
   Kontrast beweist, dass die Antwort über den **Fallback-Pfad** kam und nicht von
   irgendwo sonst — ohne ihn ist der Erfolgslauf nicht unterscheidbar von „irgendein
   Provider hat geantwortet".
4. **Dritten Zeugen lesen:** das Protokoll des Dienstes (`%LOCALAPPDATA%\Ollama\server.log`)
   — dort steht die Anfrage für genau dieses Modell mit Zeitstempel im Testfenster, klar
   unterscheidbar von früheren Aufrufen.

Erst damit ist „der lokale Fallback funktioniert" eine belegte Aussage: Primär fällt aus,
Kette greift, richtiges Modell antwortet, falsches Modell scheitert.

## Fallen

- **Veraltete Modellnamen im Provider-Block.** `providers.<name>.models` wird nicht
  gegen den Dienst geprüft. Ein Name, den es lokal nicht gibt, macht den Fallback
  unwirksam, ohne Fehlermeldung im Normalbetrieb.
- **Zweiter lokaler Zweig (llama.cpp-Laufzeit).** Unter `Agenten/Hermes/runtimes/llamacpp/`
  können die Binärdateien entpackt vorliegen (`b*/cuda/llama-server.exe`), während
  `presets.ini` 0 Bytes hat — dann ist **kein Modell gebunden** und der Zweig kann nichts
  bedienen. Vor dem Eintragen prüfen, ob die Laufzeit ein Modell lädt; die GGUF-Gewichte
  liegen getrennt unter `Modelle\*.gguf` bzw. `Modelle\GGUF\`.
- **Passen die Gewichte überhaupt?** Vor jeder Empfehlung „lokales Modell als Fallback"
  gegen den VRAM bemessen (Skill `lokale-modelle-bemessen`) — eine Datei von 15 GB
  bedeutet auf einer 8-GB-Karte CPU-Auslagerung, also Sekunden statt Millisekunden.
- **Abgebrochene Sitzungen als Quelle.** Eine Sitzung, die mitten im Turn endete, kann
  behauptet haben, die Kette sei gesetzt. Diese Behauptung ist kein Beleg; siehe
  `git log -S` und die Vorher-Kopien unter `backups/config/` und `state-snapshots/`.
