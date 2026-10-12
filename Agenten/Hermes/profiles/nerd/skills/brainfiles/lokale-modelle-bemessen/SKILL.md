---
name: lokale-modelle-bemessen
description: "Modelle lokal bemessen: VRAM, Kontext, Laufzeit."
category: brainfiles
---

# Lokale Modelle gegen den VRAM bemessen

## Wann
„Passt Modell X auf die Karte“, „welche Quantisierung“, „wie viel Kontext geht“,
„das Modell ist langsam“, „läuft das noch auf der GPU“, `Out of memory`, oder
wenn ein Modell heruntergeladen oder umgewandelt werden soll. Auch immer dann,
wenn eine Größenangabe aus dem Gedächtnis kommt („12–14B passen knapp“) — sie
ist eine Vermutung und wird nachgerechnet. Auch dann, wenn ein Modell **nicht in
Ollama** laedt: manche Familien (ternar, 1-Bit) verlangen die Laufzeit ihres
Herausgebers — dann wird der Dienst dieser Laufzeit bemessen und gestartet
(`references/llama-server-und-forks.md`), nicht ein Ollama-Modell gebaut.

## Prozedur
1. **Karte und freie Reserve messen**, nicht schätzen:
   `nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv`.
   Auf diesem Rechner lügt WMI (meldet 4 GB für eine 8-GB-Karte) — nvidia-smi
   ist die Wahrheit. Die Belegung **vor** dem Laden ist die Vergleichsbasis.
2. **Laufzeit klaeren — vor allem anderen, wenn das Modell nicht von Ollama
   kommt.** Eine Datei kann in Ollama nicht ladbar sein (sauber abgelehnt) oder
   schlimmer: von einer Laufzeit geladen werden, die die Aktivierung nicht
   beherrscht, und **still Unsinn liefern**. Zuerst die Modellkarte auf die
   geforderte Laufzeit lesen, dann das Paket waehlen, das diese Laufzeit
   erwartet. Ohne diese Pruefung wird eine Messung ueber ein kaputtes Modell
   zur falschen Empfehlung. Details: `references/llama-server-und-forks.md`.
3. **Bestand aufnehmen:** alle `.gguf`-Dateien mit echter Größe auflisten.
   Nicht annehmen, dass ein Name die Parameterzahl nennt — „E4B“ war in
   Wahrheit ein 7,5-Mrd-Modell.
4. **Kopf lesen statt raten:** `scripts/gguf-kopf.py <datei.gguf>` liefert
   Parameter, Blockzahl, KV-Köpfe, Kopfdimensionen, Trainings-Kontext und die
   echten Bits je Parameter. Die Gegenprobe rechnet die Gewichte gegen die
   Dateigröße; weicht sie um mehr als ~1 % ab, stimmt das Bit-Modell nicht.
5. **Rechnen:** Gewichte und KV getrennt, dann erst addieren —
   Formeln, Bitwerte und Grenzwerte in `references/vram-faustregeln.md`.
6. **Messen statt glauben.** Modell mit dem gewünschten Kontext bauen und
   laden, VRAM-Delta gegen die Rechnung stellen, `ollama ps` auf die
   Prozessorverteilung ansehen. Die Rechnung ist die Vorhersage — die Messung
   entscheidet.
7. **Eine Empfehlung:** eine Quantisierungsstufe und ein Kontextwert, mit der
   Zahl, die sie trägt („5,0 GiB bei 100 % GPU“). Keine Optionsliste.

## Regeln (Standing)
- **Der Kontext gehört ins Modelfile, nicht in die Umgebung.**
  `PARAMETER num_ctx <n>` beim Anlegen:
  `ollama create <name> -f Modelfile`. Danach **immer** mit `ollama ps`
  prüfen, dass in der Spalte `CONTEXT` der gewünschte Wert steht — nur was
  dort steht, ist gesetzt. Eine Umgebungsvariable allein ist kein Beleg.
- **Der Trainings-Kontext aus dem Kopf ist kein Betriebswert.** Ohne eigene
  Angabe nimmt Ollama ihn (gemessen: 262144 statt 8192) und zahlt ihn aus dem
  KV-Cache — das ist der größte Einzelhebel, den es hier gibt.
- **Jede Zahl, die einen Kauf oder Download begründet, braucht eine Messung.**
  Eine Empfehlung ohne gemessenen Verbrauch ist eine Schätzung.
- **Der Kontext ist eine TEMPO-Entscheidung, nicht nur eine Speicherfrage.**
  Laeuft die Karte fast voll, bricht die Prompt-Verarbeitung ein, lange bevor
  der Ladevorgang scheitert (gemessen: 8k Kontext → 666 t/s Prompt, 16k bei
  177 MiB Rest → 44 t/s Prompt und 10 statt 32 t/s Erzeugung). Bei knappem
  Speicher den KLEINEREN Kontext nehmen und begruenden — „passt noch" ist kein
  Ziel, „rechnet noch schnell" ist eines.
- **Ein lokales Modell als Agent-/Delegations-Modell ist meist teuer, nicht gratis.**
  Die 64k-Grenze ist nur die erste Huerde; die zweite ist das VORSPIEL. Ein
  Subagent schickt einen grossen System-Prompt, und ein Modell mit ~85 t/s
  Prompt-Verarbeitung braucht dafuer Minuten, bevor das erste Wort kommt:
  derselbe Ein-Wort-Auftrag kostete auf einem lokalen 27B **343 s** gegen
  **13,9 s** auf dem Cloud-Modell — Faktor 25, und der Kontext waechst im Lauf
  weiter. Solche Modelle taugen fuer kurze, einzelne Fragen und Skripte, nicht
  fuer Zuege mit Werkzeugen. Der traegbare Aufbau ist: schnelles Modell VORN,
  lokales Modell als ERSTER RUECKFALL (`delegation.fallback_providers`), damit
  die Arbeit lokal weiterlaeuft, wenn die Cloud klemmt.
  **Gemessen wird das mit einem ECHTEN Subagenten-Lauf**, nicht mit einem
  Chat-Aufruf gegen den Dienst — nur der Lauf zeigt das Vorspiel. Die Reihenfolge
  belegt man mit zwei Laeufen desselben Auftrags und nennt beide Zeiten.
- **Hermes verlangt mindestens 64k Kontext je Modell.** Ein Modell darunter
  ist als **Dienst** nutzbar (Skripte, Einzelfragen, API), aber nie als
  Agent-Modell: `hermes -z … -m <modell>` bricht mit klarer Meldung ab.
  **„Auf 8 GB geht kein 64k" ist eine ANNAHME, keine Messung** — die KV-Groesse
  haengt an der ARCHITEKTUR, nicht nur an der Gewichtsmenge: ein
  Hybrid-Attention-Modell (nur ein Teil der Schichten voll aufmerksam) traegt
  64k neben 5,5 GB Gewichten auf einer 8-GB-Karte. Gemessen (27B ternar,
  `-c 65536 -fa on`): VRAM 7.772/253 MiB **frei**, 12 t/s Erzeugung, 85 t/s
  Prompt — gegen 32 t/s bei 8k Kontext. Vor der Empfehlung „nur als Dienst"
  deshalb den 64k-Lauf WIRKLICH starten und VRAM + Tempo messen; erst wenn er
  nicht hochkommt, ist der Dienst-Weg die Antwort.
  **Die Kontextangabe gehoert danach als VORGABE in den Starter** (`-c 65536`),
  sonst faellt der Agent-Weg beim naechsten Start still auf 8k zurueck und
  Hermes lehnt das Modell wieder ab — und fuer reine Chat-Aufrufe den kleineren
  Wert als Schalter daneben stehen lassen (dort ist 8k schneller).
- **Den Agent-Weg in einem FRISCHEN `HERMES_HOME` nachweisen.** Ein Lauf gegen
  das laufende Profil beweist nichts: `hermes -z` nimmt dort die letzte Sitzung
  mit auf, und ein langer Verlauf meldet „This conversation has grown too long
  for <modell> to read" — das ist die SITZUNG, nicht das Modell. Rezept: ein
  leeres Verzeichnis mit einer `config.yaml`, die NUR den Provider-Block des
  Dienstes und `model: {default, provider}` traegt, dann
  `HERMES_HOME=<verzeichnis> hermes -z "Antworte mit genau einem Wort: OK"`.
  Fehlt der `providers:`-Block, antwortet die CLI `Unknown provider '<name>'`
  — das ist der fehlende Block, kein Modellfehler. Erst wenn dieser Lauf
  antwortet, ist der Agent-Weg belegt (und der Nachweis gehoert in die
  Wiki-Seite des Modells).
- **Die 64k-Grenze laesst sich nicht ueber den Router umgehen.** Ein kleines
  lokales Modell als Ziel einer Router-Kennung (`auto/best-coding` o. ae.)
  einzutragen liefert es den CLIENTS aus — und die pruefen weiterhin selbst,
  bevor sie ein Modell benutzen. Jeder Client auf dieser Kennung (Bots,
  Delegation) stirbt dann mit derselben Kontext-Meldung, statt das Modell zu
  nutzen. Richtig: eine EIGENE, ausdruecklich waehlbare Kennung fuer das kleine
  Modell, und die Coding-Kombos bleiben auf Modellen mit >=64k. Vor jeder
  Router-Umstellung fragen, WER die Kennung zieht — "Standard-Coding-Modell"
  heisst in diesem Haus eine Kennung, die viele Clients teilen.

## Pitfalls
- **Dienstaufrufe mit Zeitgrenze fahren, nie blank.** `ollama list` bzw. `curl` gegen
einen nicht laufenden Dienst blockieren bis zum Werkzeug-Timeout (180 s) und verbrennen
den ganzen Schritt: `timeout 20 ollama list`, `curl -s -m 5 http://127.0.0.1:11434/api/tags`.
Und die Namen, Quantisierung und `capabilities` (`tools`/`thinking`) **am Dienst** abfragen,
nicht aus `config.yaml` oder dem Gedächtnis — ein Provider-Block darf veraltete
Modellnamen führen, ohne dass es auffällt.
- **Ladungsdeltas sind nur bei sauberer Grundlast vergleichbar.** Vor dem
  Messen entladen (`ollama stop <name>`), dann warten, bis der Speicher
  nachweislich zurück ist (`ollama ps` leer und nvidia-smi auf Grundlast) —
  sonst misst man das Vorgängermodell mit, und der zweite Wert ist zu klein.
  Bei verunreinigter Basis die Messung wiederholen, nicht interpretieren.
- **`ollama ps` entscheidet über „läuft auf der GPU“.** `100% GPU` ist das
  Ziel; eine Aufteilung wie `42%/58% CPU/GPU` erklärt Langsamkeit besser als
  jede Quantisierungsstufe, und der Kontext ist meist die Ursache.
- **Nicht aus der Dateigröße auf den VRAM-Bedarf schließen.** Gemessen kann
  deutlich weniger im VRAM landen als die Datei groß ist (Treiber/mmap) — eine
  Vorhersage „passt nicht“ ist erst widerlegt, wenn sie gemessen wurde. Die
  Datenmenge bleibt real, die Verteilung ist offen; das gehört als offener
  Punkt in den Bericht, nicht als Behauptung in die Empfehlung.
- **Die Aktivierungsseite (A4/A6) spart keine Gigabyte.** Sie greift nur den
  Rechenpuffer, Größenordnung einige hundert MB. Für „passt es“ zählen allein
  Gewichtsstufe und KV-Cache.
- **Kontext verdoppeln verdoppelt den KV.** Bei kleiner KV-Kopfzahl ist der
  KV der Deckel, nicht die Quantisierung — ein langer Trainings-Kontext ist
  dann unerreichbar, egal wie klein die Gewichte sind.
- **Der Import eines vorhandenen GGUF als Ollama-Modell ist billig** (Kopie im
  Store, kein Download) und der schnellste Weg zu einer belastbaren Messung.
  Aufräumen danach mit `ollama rm <name>`.
- **Den eigenen llama.cpp-Dienst NICHT ueber `provider: llamacpp` anschliessen.**
Hermes loest diesen Alias ZUERST auf seinen eigenen verwalteten llama-server
auf (State-Datei, eigener Port, upgestreamte Bauart) und erst danach auf einen
gefundenen fremden llama-server (Probelauf u. a. auf 8080). Ein Eintrag
`provider: llamacpp` mit dem Namen des eigenen Modells landet also bei einem
ANDEREN Dienst, der dieses Modell nicht fuehrt — und ein Fork-Build, der die
Gewichte gar nicht laden kann, liefert dort still etwas anderes. Fuer den
eigenen Dienst einen EIGENEN Provider-Block anlegen (`providers.<name>` mit
`api`/`base_url` auf Host und Port, `default_model`) und den ueberall nennen;
vor der Aussage "laueft ueber llamacpp" den aufgeloesten Endpunkt ausgeben
lassen, statt es aus der Config zu schliessen.
- **`/v1/models` zeigt den Dateipfad als Modellnamen, wenn kein Alias gesetzt ist.**
Ein Starter ohne `--alias` laesst Clients den ganzen GGUF-Pfad anfragen; mit
`--alias <kurzname>` meldet der Dienst den kurzen Namen. llama.cpp nimmt zwar
jeden Namen an, aber ein falscher Name in einer Config ist eine zweite Wahrheit,
die niemand nachzieht. Bei
  einem MoE (z.B. GLM-5.3-Flash: 320B gesamt / 18B aktiv je Token) muessen
  saemtliche Experten-Gewichte in RAM/VRAM liegen, obwohl nur ein Bruchteil je
  Token rechnet — die „18B aktiv“-Angabe ist KEIN Speicherbedarf. Vor dem
  Bemessen die GESAMT-Parameterzahl pruefen; „flash“ im Namen heisst nicht
  klein. Und der Engpass ist RAM + VRAM, nie das Disk-Budget: eine 200-GB-SSD
  entscheidet nicht, ob ein 320B-Modell laeuft — 63 GB RAM tun das.
- **`localhost` und `127.0.0.1` sind auf diesem Rechner NICHT dieselbe
  Ollama-Instanz.** `localhost` löst auf `::1` (IPv6) auf, wo eine ZWEITE,
  modell-lose Instanz lauschen kann — ein Aufruf gegen
  `http://localhost:11434/api/generate` mit einem installierten Modell liefert
  dann `404 model not found`, obwohl `ollama list`/`curl 127.0.0.1:11434/api/tags`
  das Modell zeigt (die Abfrage traf zufällig die richtige Instanz, der Aufruf
  die falsche). Jeden Ollama-Client fest auf `127.0.0.1` eintragen, nie
  `localhost`. Bei einem 404 „model not found“ für ein nachweislich
  installiertes Modell zuerst `localhost` und `127.0.0.1` EINZELN gegen
  `/api/tags` UND `/api/generate` testen, bevor am Modellnamen gesucht wird.
 - **CUDA OOM ist nicht das Ende — ein Modell, das nicht in den FREIEN VRAM passt
 (andere Prozesse halten den Rest der Karte), laeuft als CPU-Tag weiter.**
 Modelfile `FROM <name>:latest` + `PARAMETER num_gpu 0` + `ollama create
 <name>:cpu`. Fuer kurze Einzel-Antworten (Handels-LLM-Spurs, CPU warm ~8 s)
 voll tragfaehig; GPU erst freiräumen, wenn man WEISS, was den VRAM haelt
 (`nvidia-smi --query-compute-apps`), statt das Modell in einen halb vollen
 Speicher zu zwingen.
 - **`/api/tags` leer, obwohl Modelle installiert sind: der Server sieht einen
 ANDEREN Modelle-Ordner.** Er erbt nur Windows-Benutzervariablen, nicht in einer
 bash-Session exportierte. `OLLAMA_MODELS` muss in `HKCU\Environment` stehen
 (`reg add`/`setx`), dann den SERVER NEU starten — ein laufender Server behaelt
 den alten leeren Wert. Und die Autostart-Verknuepfung (Startup-Ordner) muss auf
 eine EXISTIERENDE Binary zeigen (`Test-Path` auf das Ziel), sonst startet der
 Server nie; beide Symptome zusammen lesen sich wie "kein Modell da".

- **Der verwaltete llama-server (18434) traegt seinen API-Key in der eigenen
  Kommandozeile.** Probeaufrufe an ihn (Modell laden, Completion testen)
  brauchen den Key — er steht als `--api-key <32 Zeichen>` in der
  CommandLine des Prozesses: `(Get-CimInstance Win32_Process | Where-Object {
  $_.Name -eq 'llama-server.exe' -and $_.CommandLine -match '<port>' })
  .CommandLine` parsen und NUR im Request-Header verwenden, nie ausgeben.
  `401 "Invalid API Key"` OHNE Key ist kein Todesbeweis, sondern Beweis,
  dass der Server lebt — erst mit Key erneut testen. Welche Modellnamen der
  Server fuehrt, steht in `runtimes/llamacpp/presets.ini` (Presets, nicht
  freie Pfade): ein Name daraus (z.B. `gemma-4-E4B-it-OBLITERATED-Q8_0`)
  laedt autoload, `--load-mode dio` entlaedt nach Inaktivitaet.
## References
- `references/vram-faustregeln.md` — Formeln, Bitwerte je Stufe, gemessene
  Werte dieses Rechners und die Grenzwerte für 8 GB VRAM.
- `scripts/gguf-kopf.py` — liest den GGUF-Kopf und rechnet Gewichte je Stufe
  und KV je Kontext. Aufruf: `python scripts/gguf-kopf.py <datei> [--kontext N]`.
- `references/llama-server-und-forks.md` — Modelle, die Ollama NICHT laden
  kann: die Laufzeit ihres Herausgebers (llama.cpp-Fork) holen, den Dienst aus
  PowerShell starten, die Fallen dabei (Argument-Quoting, Ausgabe-Umleitung,
  Portprobe, Denk-Modelle) und was von einer solchen Spur erwartet werden darf.
- `references/fremdrepo-auf-ollama.md` — ein fremdes Agenten-Repo (Werkstatt-Klon)
  ohne Schluessel auf das lokale Ollama ziehen: Modellpfad im Code finden,
  Standardmodell und Basis-URL aus der Umgebung, Rueckfall statt `None`, Nachweis
  mit einem echten Aufruf.
