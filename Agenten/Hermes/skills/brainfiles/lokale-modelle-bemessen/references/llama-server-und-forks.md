# Modelle mit eigener Laufzeit (Fork von llama.cpp, llama-server)

Fuer Modelle, die **Ollama nicht laden kann**: ternare, 1-Bit- und andere
Pakete, deren Gewichte in einer rotierten Basis liegen oder deren Typen nur
der Fork des Herausgebers kennt. Hier steht der Weg von „Modell soll lokal
laufen" bis „Dienst antwortet und die Zahl ist gemessen".

## 1. Laufzeit zuerst, dann Gewichte

- **Die Modellkarte nennt die Laufzeit und das passende Paket.** Ein Paket fuer
  den Fork und ein Paket fuer den upgestreamten `llama.cpp` sind zwei Dateien;
  das falsche Paket wird entweder **sauber abgelehnt** (unbekannter Typ) oder
  **ohne Warnung geladen und liefert Unsinn** (bekannter Typ, fehlende
  Aktivierungs-Transformation). Nach einem solchen Lauf ist jede Zahl wertlos.
- **`Ollama` ist kein Ausweichweg.** Es kennt diese Typen nicht; „geht nicht"
  ist hier die richtige Antwort, kein Grund zum Umquantisieren.
- **Vor dem Selbstbauen die Release-Assets pruefen.** Fork-Releases liefern
  fertige Windows-Binaries (`*-bin-win-cuda-<ver>-x64.zip`) **plus** ein
  separates `cudart-…`-Archiv; damit laeuft die Sache ohne cmake, nvcc oder
  CUDA-Toolkit. Erst wenn es fuer die Plattform kein Asset gibt, bauen.
  Beide Archive in EINEN Ordner entpacken (die `.exe` brauchen die
  `cudart64_*.dll` daneben).
- **Kandidaten-Reihenfolge beim Speicher:** zuerst das kleinste Paket, das die
  Karte vollstaendig traegt (dichte Ternar-Packung), und nur wenn es zu gross
  ist oder messbar zu langsam, das groessere Paket mit Teilauslagerung. Die
  Karte darf hier irren — Pakete mit mehr Bit/Parameter haben je nach
  Kartengeneration das **schnellere** Dekodieren. Also messen, nicht glauben.

## 2. Starten (PowerShell auf Windows)

Muster: ein Starter-Skript im Werkzeugordner, Aktionen `start | stopp | status |
log | test`, relative Pfade auf Wurzel-Ebene (`Modelle/…`, kein `C:\Users\…`).

Fallen, jede einzeln erlebt:

- **JSON-Argumente brauchen die Backslash-Form.** `--chat-template-kwargs`
  oder ein anderes JSON-Feld als `'{\"reasoning_effort\":\"medium\"}'`
  uebergeben. Ohne die Backslashes zerlegt der Windows-Argumentparser die
  Anfuehrungszeichen, das Kind bekommt ungueltiges JSON und **beendet sich
  sofort ohne Protokollzeile** — was wie „startet nicht" aussieht, ist ein
  Quoting-Fehler.
- **`Start-Process` braucht `-RedirectStandardOutput` UND `-RedirectStandardError`.**
  Ohne die Umleitung erbt das Kind die Pipe des Aufrufers, und der Aufruf
  kehrt erst zurueck, wenn der Dienst endet — der Werkzeugaufruf laeuft in den
  Timeout, obwohl alles funktioniert.
- **Portprobe nicht mit `Test-NetConnection`.** Das kann in PowerShell 5.1
  minutenlang haengen (Netzwerkinventar). Stattdessen
  `TcpClient.ConnectAsync('127.0.0.1',$port).Wait(1500)`, und danach den Dienst
  selbst fragen (`/props`, `/v1/models`), bis er antwortet — der Startbanner
  ist kein Beleg.
- **Prozesssuche nach Programmnamen greift zu weit.** Auf dem Rechner kann
ein ZWEITER Server desselben Programms laufen (z. B. von Hermes verwaltete
Laufzeit auf eigenem Port). Beim Pruefen „laeuft mein Dienst?" nach der
  **Kommandozeile** filtern (eigener Laufzeitpfad bzw. eigener Port), sonst
  haelt man den fremden Server fuer den eigenen und stoppt/startet falsch.
- **Vor dem Start fremden VRAM freigeben.** `ollama ps` lesen und die geladenen
  Modelle mit `ollama stop <name>` entladen (sie laden beim naechsten Aufruf
  neu, notfalls auf der CPU). Sonst scheitert die Zuweisung oder der Dienst
  landet halb im RAM. Ein solcher Schritt gehoert sichtbar in die Ausgabe des
  Starters, damit klar ist, wer die Karte raeumt.

## 3. Denk-Modelle

- **Das Denken zaehlt gegen `max_tokens`.** Ein knappes Limit (einige hundert)
  endet mitten im Gedankengang: Antwort leer, `finish_reason: length`. Immer
  grosszuegig anfragen (ab ~1024, besser 2048) oder die Denkstufe senken.
- **Erlaubte Denkstufen am Modell pruefen.** Manche Vorlagen kennen
  `low|medium|xhigh`, aber kein `high` und antworten darauf mit HTTP 500.
  Unbekannte Stufe = Fehler, nicht „wird ignoriert".
- **Denken ausschalten ist der Hebel fuer kurze Urteile.** Fuer Spuren, die
  drei Zeilen liefern sollen, `reasoning_effort: none` bzw. `think:false`
  setzen — sonst zahlt man Sekunden fuer Text, der weggeworfen wird.

## 4. Nachweis, der zaehlt

1. `/props` lesen: dort steht die **tatsaechliche** `n_ctx` und die Slotzahl.
2. Einen echten Aufruf gegen `/v1/chat/completions` mit langem Prompt (einige
   hundert bis tausend Token) fahren und das `timings`-Objekt auswerten:
   `prompt_per_second` getrennt von `predicted_per_second`. Ein Kurz-Prompt
   misst nur den festen Overhead (zweistellige t/s-Werte sind dort normal und
   bedeuten nichts).
3. VRAM **waehrend** der Nutzung mit `nvidia-smi` ablesen und die Restreserve
   nennen. Ein Modell „passt" nur, wenn nach dem Laden noch Luft bleibt.
4. Ergebnis in Wiki/Werkzeuge/<modell>.md festhalten: Pfad der Laufzeit, Pfad
   der Gewichte, gemessene t/s je Kontext, Reserve, Grenzen, Fallen.

## 5. Anschliessen an Hermes

- Der Dienst ist OpenAI-kompatibel (`/v1`); ein Provider-Block in der
  `config.yaml` (api/base_url/default_model/model) genuegt.
- **Die 64k-Grenze des Agenten pruefen, bevor der Provider angelegt wird.**
  Ein Modell mit kleinem Kontext ist ein Dienst fuer Skripte, kein
  Agent-Modell; der Provider bleibt trotzdem sinnvoll (klare Fehlermeldung
  statt stiller Fehlkonfiguration), aber die Empfehlung muss das sagen.
- **Config nicht mit `hermes config set` aendern**, wenn der Kommentar-Schluss
  und CRLF erhalten bleiben sollen: kleiner Einfuegesatz mit Sicherung,
  Trockenlauf als Standard (`scripts`-Muster in `Agenten/Hermes/scripts/`),
  danach Zeilenzahl und `git diff --numstat` pruefen.
- **Fehlt die Schnittstelle, die die eigenen Spuren sprechen, ist das ein
  offener Punkt, nicht ein Detail.** Haus-Spuren, die ein Modell ueber die
  native Ollama-API (`/api/…`) befragen, erreichen einen `llama-server` nicht
  (kein `/api/chat`) — als Aufgabe notieren, nicht im Nebenbei umbauen.
