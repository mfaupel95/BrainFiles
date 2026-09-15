---
name: lokale-modelle-ollama
description: Use when sizing local LLMs (Ollama/GGUF) or VRAM on Max' PC.
---

# Lokale Modelle / Ollama / VRAM

Gemessene Zahlen statt Katalogwerten: das Setup (RTX 3060 Ti, 8 GiB) und die
folgenden Lektionen stammen aus Messungen am 11.09.2026.

## Kontext ist der einzige grosse Hebel

`OLLAMA_CONTEXT_LENGTH` als Umgebungsvariable wird in Ollama 0.34 **ignoriert**:
der Server laedt trotzdem den Trainings-Kontext der Datei (bis 262144) und
splittet das Modell auf CPU (bis 4x langsamer, gemessen 18 statt 76 Token/s).
Wirksam ist nur `PARAMETER num_ctx <n>` im Modelfile (oder `options.num_ctx`
je Anfrage). Nie dem Standard vertrauen: der KV-Cache waechst unbemerkt mit dem
Kontext, und der Kontext entscheidet, ob ein Modell auf die GPU passt.

## Messen statt rechnen

- nvidia-smi-Delta misst nur VRAM. Die Wahrheit steht im Server-Log
  `%LOCALAPPDATA%\Ollama\server*.log`: `CUDA0 model buffer size`,
  `KV buffer size`, `offloaded N/N layers to GPU`.
- Die Log-Datei ist waehrend einer Sitzung gesperrt: erst nach TEMP kopieren,
  dann lesen (`Copy-Item` + `[System.IO.File]::ReadAllLines`).
- Eine Groessenrechnung aus dem GGUF-Kopf (Parameter x Bits) kann massiv
  danebenliegen: bei gemma-4-E4B ("E4B" = effektiv ~4,5 Mrd) sind nur
  4.788 MiB geladen, obwohl die Datei 8,03 GB hat - unbenutzte Tensoren
  (MTP o. ae.). Auch die KV-Formel (n_layer x n_kv_head x head_dim x ctx)
  ueberschaetzt dort stark: gemessen 1,0 GiB bei 65.536 statt 5,6 GiB
  gerechnet. Bei unbekannter Architektur immer laden und messen.
- Verlaesslicher ist die Gegenprobe: Vorhersage gegen echte Dateigroesse
  (GGUF-Kopf parsen, Bits je Parameter aus den Tensortypen) - stimmte bei
  Qwen3.5-4B auf 0,4 %.

## Max' Setup (Stand 11.09.2026)

- Grundlast mit offenen Apps ~2,5-3,4 GiB (4K-Desktop + Browser + Electron).
  Gemessen: gemma-e4b-8k (Q8_0) laeuft 100 % GPU bis 65.536 Kontext
  (~38-43 Token/s, ~5 GiB); bei 131.072 Splitting 51/49, 22,5 Token/s.
- Ollama-Store liegt unter `O:\Modelle\Ollama\Store` (Junction von
  `C:\...\BrainFiles\Modelle`). Modelle im Bestand: `gemma-e4b-8k`,
  `qwen35-8k`. `ollama ps` zeigt den angeforderten Kontext, nicht immer die
  echte Belegung.
- Benutzervariablen gesetzt: `OLLAMA_KV_CACHE_TYPE=q8_0`,
  `OLLAMA_FLASH_ATTENTION=1` (KV-Effekt bei 8k Kontext gemessen klein:
  ~93 MiB statt der gerechneten 483 MiB - kein grosser Hebel).

## Prozessumgebungs-Falle

Ein frisch gestarteter Prozess erbt die Umgebung des **Starts**-Prozesses,
nicht die Registry. Nach `[Environment]::SetEnvironmentVariable(...,'User')`
Variablen beim Neustart explizit in der Startumgebung setzen
(`$env:OLLAMA_...=...` vor `Start-Process`), sonst wirken sie scheinbar nicht.
