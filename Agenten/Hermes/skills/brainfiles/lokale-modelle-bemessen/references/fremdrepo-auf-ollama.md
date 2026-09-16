# Ein fremdes Agenten-Repo auf das lokale Ollama ziehen

Gilt fuer geklonte LLM-Agenten-Repos unter `Werkstatt/Repos/` (z. B.
moon-dev-ai-agents), die ab Werk auf bezahlte Anbieter zeigen. Ziel: die Agenten
laufen ohne einen einzigen Schluessel gegen `127.0.0.1:11434`.

## Reihenfolge

1. **Den Modellpfad im Code suchen, nicht in der Doku.** Typisch sind drei Stellen:
   eine Konstante im Konfigurationsmodul (`AI_MODEL = "claude-…"`), je Agent eigene
   Konstanten (`MODEL_TYPE` / `MODEL_NAME`) und eine Factory, die den Anbieter
   danach auswaehlt, welcher Schluessel in der Umgebung steht.
2. **Modellnamen gegen den Dienst pruefen:** `curl -s -m 5
   http://127.0.0.1:11434/api/tags`. Ein fest verdrahteter Name, den es lokal nicht
   gibt, faellt **nicht beim Start** auf, sondern erst beim ersten Aufruf — dann
   aber in jedem Agenten (Symptom: Modellfehler, kein Absturz).
3. **Standardmodell und Basis-URL aus der Umgebung lesen lassen** (`OLLAMA_MODEL`,
   Rueckfall auf den Hausstandard; `OLLAMA_BASE_URL`, Rueckfall
   `http://localhost:11434/api`) und beides in eine `.env` **ohne Schluessel**
   schreiben — nur lokale Werte, gitignoriert.
4. **Die API-Form nachsehen, nicht annehmen.** Manche Clients sprechen nativ
   (`POST /api/chat` mit `{"model","messages","stream":false,"options":{"temperature"}}`),
   andere den OpenAI-kompatiblen Weg (`/v1/chat/completions` mit Dummy-Key). Ein
   falscher Pfad gibt 404, keinen brauchbaren Hinweis.
5. **Fehlt einem angefragten bezahlten Anbieter der Schluessel, nicht `None`
   liefern, sondern lokal weiterrechnen** — mit gedruckter Zeile („kein <anbieter> -
   lokal weiter mit ollama/…“) und abschaltbar ueber eine Umgebungsvariable. Ein
   stiller Rueckfall waere schlimmer als keiner; ein harter `None`-Rueckfall laesst
   jeden Agenten beim ersten Zugriff scheitern.
6. **Am lebenden System nachweisen, nicht am Import:** ein Skript, das die Factory
   baut, das Standardmodell nennt, EINEN echten Aufruf macht („antworte nur mit
   PONG“ -> `PONG`) und den Rueckfall prueft. Ohne echten Aufruf ist nur die
   Verdrahtung belegt, nicht die Faehigkeit.

## Modellwahl fuer Agenten-Aufrufe auf diesem Rechner

- `qwen35-8k:latest` (3,0 GB) als Standard: passt in die 8 GB VRAM, warm ~1,5 s.
- `qwen36-35b-a3b:8k` (22,7 GB) nur als Ausnahme — laeuft auf CPU/RAM, ein
  Vielfaches langsamer.
- `gemma-e4b-8k` ist schnell, war im Vertragstest (drei Zeilen BUY/SELL/NOTHING)
  aber unzuverlaessig.
- Die Namen kommen aus `curl …/api/tags`; die `-8k`-Namen sind eigene Modelfiles
  mit gesetztem Kontext (siehe SKILL.md, Regel „Der Kontext gehoert ins Modelfile“).

## Nicht anfassen

- **Die Anbieter-Konstanten der Einzelagenten** (bei 40+ Dateien): der Rueckfall in
  der Factory deckt sie ab, und ein Massenersatz macht den Diff unlesbar. Wer einen
  Agenten wirklich fahren will, setzt seine zwei Konstanten einzeln.
- **Schluesselnamen aus `.env_example`** bleiben leer; Zugaenge gehoeren nach
  `Wissen/Zugaenge.md`, nicht in die Repo-`.env`.
- **Das Repo liegt in `Werkstatt/` und wird nicht gesichert:** Aenderungen dort im
  Repo selbst committen und auf den eigenen Fork pushen, sonst sind sie beim
  naechsten Aufraeumen weg. Vorher `git remote -v` pruefen (origin = eigener Fork).
