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
Test-`HERMES_HOME`** (Ablage und Aufräumen: Fallen in references/fallen.md), damit die echte Config
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

---

## Vollstaendiger Abschnitt aus dem SKILL.md-Rumpf

# Fallback-Kette und lokale Provider


Hermes wechselt bei 429/529/503/Verbindungsfehlern auf eine Kette. Sie wird **per
Kommando** verwaltet, nicht per Hand im YAML:

    hermes fallback list     # was gilt (leer = keine Kette)
    hermes fallback remove   # Eintrag entfernen
    hermes fallback clear
    hermes fallback add      # interaktiver Picker — für Menschen, nicht für Agenten

- **`hermes fallback add` ist ein Auswahlmenü und hängt ohne Terminal.** Aus einer
Werkzeugsitzung (windows-mcp/desktop-commander) blockiert es bis ins Zeitlimit. Nicht
verwenden — die Kette mit `hermes config set` schreiben. Der Wert wird als strukturierter
Wert geparst (`hermes_cli/config.py::_coerce_config_set_value` zieht YAML/JSON heran,
sobald der Standardwert des Schlüssels kein String ist):

      hermes config set fallback_providers '[{"provider":"custom","model":"gemma-e4b-8k:latest","base_url":"http://127.0.0.1:11434/v1"}]'

  Danach `hermes fallback list` lesen und die Zahl der Einträge gegen die Absicht zählen.
- **Ein Eintrag ohne `provider` oder `model` wird stillschweigend verworfen**
(`fallback_config.py::_iter_fallback_entries`) — die Kette ist danach kürzer, ohne
Fehlermeldung. Genau deshalb ist der Zähl-Vergleich nach dem Setzen Pflicht.
- **Die Änderung greift ohne Neustart** (`run_config_loaders.py` liest `fallback_providers`
zur Laufzeit neu); ein laufender Agent übernimmt sie beim nächsten Fehlversuch.

- **`fallback_providers` (Liste) ist die führende Ablage, `fallback_model` (Einzelwert)
die Altform**; beide werden gemerged (`hermes_cli/fallback_config.py::get_fallback_chain`),
Reihenfolge = Absicht.
- **Ein Eintrag braucht `provider` und `model`; für ein lokales Modell zusätzlich
`base_url`** (z. B. `http://127.0.0.1:11434/v1`) — ohne `base_url` greift er ins Leere.
Für lokale Endpunkte ist `provider: custom` die portable Angabe: `ollama`, `local`,
`vllm`, `llamacpp`, `llama.cpp` und `llama-cpp` sind Aliase desselben Profils, `hermes
fallback list` zeigt sie alle als `via custom`. Rezept und Befehle:
`siehe oben in dieser Datei`.
- **Der Modellname muss im laufenden Dienst existieren.** `providers.<name>.models` ist
eine Wunschliste und darf veralten (dort stand `gemma4:e4b`, lokal hieß das Modell
`gemma-e4b-8k`). Ein Fallback auf einen nicht existierenden Namen greift nicht, und
niemand merkt es, bis der Primärpfad wirklich ausfällt. Echte Namen am Dienst holen
(`curl -s http://127.0.0.1:11434/api/tags`), nicht aus der Config abschreiben.
  **Gemessen 29.09.2026: es war die GANZE Flotte.** 21 von 22 Profilen trugen
  `qwen35-8k:cpu` in der Kette und `gemma4:26b`/`gemma4:e4b` im Provider-Block — im
  Store lagen nur `gemma-e4b-8k:latest` und `gemma-e4b-8k:cpu`. Werkzeug für den
  Abgleich und die Umstellung: `Agenten/Hermes/scripts/lokale-modellnamen-richten.py`
  (Trockenlauf ohne Argument, `--anwenden`, `--zuruecknehmen`, `--nur-profile`; fragt
  `/api/tags` und ersetzt NUR, wenn der Zielname dort steht — kein Raten). Nachweis
  nach dem Lauf: `git diff --numstat` JE Datei muss 6/6 bzw. 3/3 bzw. 1/1 zeigen,
  dann `hermes -p <profil> fallback list` UND ein echter Aufruf des Modells.
  **Byte-Ersetzung, nicht Textmodus:** der erste Anlauf setzte die Zeilenenden ein
  zweites Mal, aus CRLF wurde CRCRLF und der Diff zeigte die ganze Datei
  (2248/2248). Ein Modellname ist ASCII — `read_bytes()`/`write_bytes()` kann
  Kodierung und Zeilenenden nicht anfassen.
- **Was in der Config steht, ist kein Beleg für das, was gilt** — `hermes fallback list`
fragen. Und eine Aussage aus einer abgebrochenen Sitzung („die Kette steht doch schon
drin") nie übernehmen, sondern am lebenden System nachprüfen.
- **Ein Zustand, der nie committet wurde, existiert in Git nicht:** `git log -S "<schlüssel>"`
findet ihn nicht, obwohl er im Arbeitsbaum stand. Vor „das war nie da" die Vorher-Kopien
lesen: `Agenten/Hermes/backups/config/config.yaml.pre-setup.*` und
`Agenten/Hermes/state-snapshots/*/config.yaml` — dort steht die Fassung vor Setup- und
update-Läufen, oft der einzige Ort, an dem eine per Hand gesetzte Kette erhalten ist
(`hermes update` schreibt die Config neu).
- **Für den lokalen Modellordner gibt es keine Umgebungsvariable.** Wer eine sucht
(analog zu `OLLAMA_MODELS`), sucht vergeblich: `local_runtime/bootstrap.py::models_dir()`
liest `get_default_hermes_root() / "models"` — also `%LOCALAPPDATA%\hermes\models`, wenn
`HERMES_HOME` ungesetzt ist, sonst `HERMES_HOME\models`. Mit dem hier üblichen
`HERMES_HOME = …\Agenten\Hermes` zeigt der Pfad damit **in die Sicherungsquelle**; dort
gehört keine Junction auf die Modellplatte hin (`laufwerk-platz-schaffen`). Vor jedem
Umräumen prüfen, ob der Verbraucher überhaupt läuft: bei `local_runtime.enabled: false`
liest den Ordner niemand, und die Gewichtsdateien sind dann nur belegter Platz.
- **Ein ungueltiger Ketten-Eintrag in einem PROFIL wird als BLOCK entfernt, nicht per
`hermes config set`.** `config set` kann keinen Listeneintrag einzeln aendern (und schneidet
den Kommentar-Schluss ab). Richtig ist ein byte-genauer Blockschnitt: die Zeile
`fallback_providers:` in Spalte 0 plus die eingerueckten Folgezeilen entfernen, die Datei
VORHER und NACHHER mit `yaml.safe_load` parsen und asserten, dass alles AUSSERHALB des
Blocks gleich geblieben ist (`{k: v for k, v in vorher.items() if k != schluessel} ==
nachher`) — damit ist "nur die Kette entfernt" bewiesen und nicht gehofft. Eine
eingerueckte Kette (z. B. unter `delegation:`) bleibt stehen; `fallback_providers: []`
ist bereits sauber (leere Liste ist falsy — nicht "leer" mit "fehlt" verwechseln, die
Erkennung ueber `grep` findet beide Formen). Werkzeug:
`Agenten/Hermes/scripts/bot-rueckfallkette-bereinigen.py`.
- **Eine Kette, deren erster Eintrag denselben Dienst nennt wie das Hauptmodell, ist
keine Reserve.** Faellt dieser Dienst aus, scheitert der erste Eintrag genauso, und erst
der zweite entscheidet den Fehlertext. Reserve ist nur, was auf einen ANDEREN
erreichbaren Dienst zeigt — sonst lieber ehrlich gar keine Kette (die Fehlermeldung des
Primaerpfads ist dann sichtbar).
- **Ein Profil kann die Kette NUR unter `delegation:` tragen — dann hat es gar keine.**
Ein `fallback_providers:` mit Einrueckung (typisch unter `delegation:`) ist die
Subagenten-Kette und keine Reserve fuer den Hauptlauf. Erst `grep -n "^fallback_providers:"`
(Spalte 0!) entscheidet, ob die Wurzel-Kette existiert; `grep -l fallback` findet beide
Formen und taugt nicht als Beleg. Fehlt sie, den Block vor einem Wurzel-Schluessel
einfuegen — und den RICHTIGEN waehlen: nicht jedes Profil hat `toolsets:` (ein
Wartungsprofil hatte nur `providers/terminal/model/plugins`), also den ersten
vorhandenen Wurzel-Schluessel nehmen und vorher per Byte-Vergleich zeigen, dass nur
der Block dazukam.
- **Der Eintrag braucht den Provider-Block IM Profil.** Ein Bot-Profil, das
`providers.<name>` nicht kennt (frisch angelegte Profile haben nur `omniroute`), kann
den Namen nicht aufloesen — den Block (api/base_url/model/name) mit einsetzen, sonst
zeigt die Kette auf einen Namen, den nur andere Profile kennen.
- **Ein GEPINNTES Kind erbt die Hauptkette nicht - es hat dann gar keine.**
  `scoped_fallback_chain` gibt einem Besitzer mit eigenem Provider, Endpunkt
  oder Modell die geerbte Kette NICHT mit: der Betreiber hat die Route gewaehlt,
  und ein Ketteneintrag ist ein anderer Provider. Ein Profil, das
  `delegation.provider` oder `delegation.model` setzt und KEINE eigene
  `delegation.fallback_providers` mitbringt, hat damit fuer seine Subagenten
  keinen Rueckfall - das ist der Befund, nicht die Modellwahl. Die Diagnose ist
  eine Kreuzung ueber die Flotte: `delegation.provider` gesetzt UND
  `delegation.fallback_providers` fehlt. Beim Umstellen die eigenen
  Einstellungen, die nicht zur Verdrahtung gehoeren (`max_iterations`,
  `reasoning_effort`, `max_concurrent_children`), im Block erhalten.
- **Eine lokale Reserve gehoert als ERSTER Eintrag in die Kette, die alten bleiben dahinter.**
Der Zweck ist, den Ausfall des Primärpfads ohne fremde Abhaengigkeit zu ueberbruecken — steht
die lokale Adresse hinten, entscheidet zuerst der (moeglicherweise genauso tote) Cloud-Eintrag
davor. Praktisch: den `fallback_providers:`-Block der Profil-Config ersetzen (Zeile in Spalte 0
plus eingerueckte Folgezeilen), die vorhandenen Eintraege unveraendert dahinter wieder einsetzen,
neuen Block vor dem Schreiben mit `yaml.safe_load` parsen und `rest == vorher` ausserhalb des
Blocks asserten. Danach **je Profil** `hermes -p <name> fallback list` lesen (nicht nur die
Datei): die Ausgabe nennt `Primary:` und die numerierte Kette — nur sie zeigt, was gilt, und
nur so faellt auf, wenn ein Profil gar keine Wurzel-Kette hatte.
- **Der lokale Rueckfall traegt nur bei freiem Commit.** Ein Profil mit gesetzter Kette ist noch
kein Nachweis: das Modell muss laden, und ein Modelllader scheitert an einer erschoepften
Commit-Grenze auch bei reichlich freiem RAM (Symptomkatalog und Messbefehle:
`dauerprozess-bewachen`). Nach dem Setzen den
Endpunkt einmal wirklich rufen (`POST <base_url>/chat/completions`) — nicht nur die Config lesen.
- **Eine konfigurierte Kette ist kein Beleg — das Modell muss LADEN.** Nach dem Setzen
nicht nur `hermes fallback list` lesen, sondern den Endpunkt wirklich rufen
(`POST <base_url>/chat/completions` mit dem eingetragenen Modellnamen; ein leeres
`content` bei gesetztem `reasoning` ist normal, solange die Antwort kommt). Schlaegt
der Modellstart fehl, ist die Ursache oft NICHT der Speicher des Modells: zuerst das
COMMIT-Limit pruefen (`Win32_OperatingSystem.FreeVirtualMemory` gegen
`TotalVirtualMemorySize`) — bei reichlich freiem RAM kann das Commit trotzdem fast
aufgebraucht sein (viele Prozesse reservieren), und dann scheitert jede
Puffer-Anforderung des Laders unabhaengig von der Modellgroesse. Erst danach ueber
Modellwahl oder Ollama-Einstellungen nachdenken.
- **Massenänderung ueber viele Profile: Trockenlauf ist der Standard.** Ein Werkzeug fuer
solche Aenderungen zeigt ohne Argument, was es taete, schreibt nur mit `--anwenden`, legt
je Profil `.bak-JJJJMMTT` an und nimmt mit `--zuruecknehmen` zurueck; es nennt je
uebersprungenes Profil den GRUND (eigene Anmeldung, lokaler Provider, schon umgestellt)
und ist idempotent, damit ein Abbruch mittendrin einfach neu gestartet werden kann.
Muster: `Agenten/Hermes/scripts/bot-modell-auf-router.py` und
`profil-kanaele-bereinigen.py`.
