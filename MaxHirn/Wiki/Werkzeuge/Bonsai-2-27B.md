# Bonsai 2 27B lokal (ternary)

**Kurz:** ein 27B-Modell in 5,95 GB, gebaut fuer llama.cpp. Auf diesem Rechner
laeuft es mit **32 t/s Erzeugung** vollstaendig auf der RTX 3060 Ti — aber nur mit
**8k Kontext**, und damit **nicht als Hermes-Agent-Modell** (Hermes verlangt 64k).
Es ist ein Chat-/Einzelfragen-Modell auf Abruf.

## Was es ist

| Punkt | Wert |
|---|---|
| Herkunft | Prism ML, Release **17.09.2026**, Apache-2.0 |
| Basis | Qwen3.8-27B, Architektur unveraendert (Hybrid Attention ~75 % linear) |
| Gewichte | ternar {-1,0,+1}, FP16-Gruppenskala je 128, **1,75 Bit/Parameter** |
| Dateien | `PTQ1_0` 5,95 GB (dicht) · `PQ2_0` 7,21 GB (2-Bit-Slots) · F16 53,8 GB |
| Kontext | 262.144 Token im Kopf; FP16-KV = 64 KiB/Token |
| Denken | ja, Vorgabe `xhigh`; `medium` fuer kurze Antworten |
| Vision | optionaler mmproj 0,63 GB (Q8_0) — **nicht** heruntergeladen |

Die Gewichte liegen in einer **rotierenden Basis** (Hadamard). Nur der
PrismML-Fork von llama.cpp wendet die passende Aktivierung an. Ein
**upgestreamtes llama.cpp laedt `Q2_0` ohne Warnung und liefert Unsinn**; die
Dateien `PTQ1_0`/`PQ2_0` lehnt es sauber ab. **Ollama kann sie nicht laden.**

## Was hier liegt

| Teil | Pfad |
|---|---|
| Laufzeit (Fork) | `Modelle/llama-prism/bin` — Release `prism-b10735-842b188`, `bin-win-cuda-12.4-x64` + `cudart-…-12.4` |
| Gewichte | `Modelle/GGUF/Ternary-Bonsai-2-27B-PTQ1_0.gguf` (5,95 GB, 25.09.2026) |
| Starter | `Agenten/Werkzeuge/bonsai-27b.ps1` |
| Protokoll | `%LOCALAPPDATA%\Temp\bonsai-27b-server.log` |
| Hermes-Provider | `providers.bonsai` in `Agenten/Hermes/config.yaml` (Port 8080) |

```powershell
cd Agenten\Werkzeuge
.\bonsai-27b.ps1 -Aktion start      # entlaedt Ollama aus dem VRAM, startet, wartet auf Antwort
.\bonsai-27b.ps1 -Aktion test       # echter Aufruf, nennt t/s
.\bonsai-27b.ps1 -Aktion status     # Prozess, Port, VRAM
.\bonsai-27b.ps1 -Aktion stopp
```

Der Dienst ist OpenAI-kompatibel: `http://127.0.0.1:8080/v1/chat/completions`.
Ein **Ollama-Pfad (`/api/chat`) fehlt** in diesem Bau — `llm_lokal.py` (die
Sprachmodell-Spuren) erreicht ihn damit nicht.

## Gemessen (25.09.2026, RTX 3060 Ti 8 GB, Treiber 616.92)

| Kontext | -ngl | Erzeugung | Prompt | VRAM belegt/frei |
|---|---|---|---|---|
| 8192 | 99 | **31,7 t/s** | **666 t/s** (1.942 T in 2,9 s) | 7.703 / 322 MiB |
| 16384 | 99 | 10,3–12,6 t/s | 10–44 t/s | 7.848 / 177 MiB |

Der grosse Kontext **frisst den Speicher, den die Prompt-Verarbeitung braucht** —
mehr Kontext war hier nicht schneller, sondern viermal langsamer. Deshalb ist
8192 die Vorgabe des Starters.

## Die harte Grenze: kein Hermes-Agent-Modell

`hermes -z … --provider bonsai -m bonsai` bricht ab mit:

> Model bonsai has a context window of 8,192 tokens, which is below the minimum
> 64,000 required by Hermes Agent.

64k braeuchten 4 GiB KV **plus** 5,5 GiB Gewichte = 9,5 GiB — auf einer 8-GB-Karte
unmoeglich. Der Provider steht trotzdem in der Config: fuer API-Kunden ist der
Dienst nutzbar, und der Agent scheitert mit einer klaren Meldung statt still.

Nutzbar ist es fuer: eigene Skripte, Einzelfragen, zusammenfassen, uebersetzen,
Bilder (mit mmproj), Vergleichsmessungen gegen kleinere lokale Modelle.

## Fallen (alle erlebt)

- **Denken zaehlt gegen `max_tokens`.** Mit `max_tokens: 250` und dem Denkmodell
  kommt eine **leere** Antwort zurueck (`finish_reason: length`). Mindestens 1024,
  besser 2048 setzen, oder `reasoning_effort: "medium"`.
- **`reasoning_effort: "high"` gibt HTTP 500** — erlaubt sind `low`, `medium`,
  `xhigh`.
- **Start aus PowerShell:** die JSON-Argumente muessen als `{\"reasoning_effort\":\"medium\"}`
  ankommen. Ohne die Backslashes zerlegt der Windows-Argumentparser die
  Anfuehrungszeichen und der Server **beendet sich sofort ohne Protokollzeile**.
- **`Start-Process` braucht `-RedirectStandardOutput` UND `-RedirectStandardError`**,
  sonst haengt der Aufrufer an der Pipe des Kindes.
- **`Test-NetConnection` in PowerShell 5.1 kann minutenlang haengen** — der Starter
  prueft den Port per `TcpClient.ConnectAsync(…).Wait(1500)`.
- **Der Dienst und Ollama teilen sich die Karte.** Vor dem Start entlaedt der
  Starter die Ollama-Modelle (sie laden beim naechsten Aufruf neu, notfalls auf
  der CPU); mit `-OllamaBehalten` bleibt das aus. Die Sprachmodell-Spuren des
  Handels fahren `qwen35-8k:cpu` und laufen deshalb **weiter**, waehrend Bonsai
  die GPU haelt.
- **`hermes config set` ist fuer diese Config verboten** — es schneidet den
  Kommentar-Schluss ab und schreibt LF. Der Provider wurde mit
  `Agenten/Hermes/scripts/bonsai-provider-einbauen.py` byte-genau eingefuegt
  (Trockenlauf ohne Argument, `--anwenden`, `--zuruecknehmen`).

## Offen

- **`PQ2_0`** (7,21 GB) ist ungemessen. Die PrismML-Karte nennt es auf
  Ampere-Karten (diese 3060 Ti ist Ampere) beim Dekodieren **schneller** als
  `PTQ1_0`, verlangt aber Teilauslagerung, weil es nicht mehr in den VRAM passt.
- **Vision** (mmproj 0,63 GB) ist nicht geladen — kostet VRAM, das hier fehlt.
- **Vision** (mmproj) — siehe T-083; **`PQ2_0`** — siehe T-082.

## Sprachmodell-Spuren laufen auf Bonsai (25.09.2026, T-084)

`moondev_whale`, `moondev_liquidation` und `moondev_sentiment` holen ihr Urteil
seit dem 25.09.2026 hier ab (27B statt 4,3B). `llm_lokal.py` hat dafuer einen
zweiten Weg bekommen; gewaehlt wird er je Spur in der `wachen.json`:

| Feld | Wirkung |
|---|---|
| `llm_weg: "bonsai"` | OpenAI unter `127.0.0.1:8080/v1` (dieser Dienst) |
| `llm_weg: "ollama"` | Ollamas `/api/chat` (`think:false`, wie bisher) |

Ohne das Feld entscheidet der Modellname (`bonsai…` oder ein `.gguf`-Pfad -> Bonsai).
Es gibt **absichtlich keinen stillen Rueckfall**: laeuft der Dienst nicht, faellt
das Urteil aus und die Spur handelt nicht — statt heimlich auf ein kleineres
Modell zu wechseln.

Gemessen mit `Handel/llm_probe.py --modelle bonsai` (drei echte Marktbilder):

| Groesse | Wert |
|---|---|
| Vertragstreue | **3/3** (BUY 75 % / SELL 65 % / SELL 65 %) |
| Dauer | kalt 3,4 s, im Mittel **2,9 s** |
| Koerper | `reasoning_effort: "none"` und `max_tokens: 512` |

**Der Denk-Schalter gehoert in den Koerper:** mit `reasoning_effort: "none"`
antwortete Bonsai in 1,5 s mit 25 Token, ohne die Angabe in 8,7 s mit 236 Token —
und mit einem kleinen `max_tokens` kommt eine LEERE Antwort zurueck, weil das
Denken das Kontingent frisst.

**Falle, die die Sonde selbst hatte:** `llm_probe.py` rief `_echte_anfrage` direkt
und damit IMMER Ollama — ein Modell auf dem zweiten Weg konnte sie nicht messen
und meldete es als „(leer) 0/6, 0,0 s". Jetzt fragt sie `llm.weg_aus` und
uebersetzt den Denk-Schalter je Weg (Ollama `num_predict`, Bonsai
`reasoning_effort`). **Wer messen will, muss denselben Weg nehmen wie der Betrieb.**