# OpenMontage (Video- und Bilderzeugung)

Agentisches Videoproduktions-System, liegt als Klon in
`Werkstatt/Repos/openmontage`. Eigenes `.venv` (Python 3.14). Rendert Videos
ueber Remotion, Bilder ueber austauschbare Anbieter.

## Was ohne jeden Schluessel laeuft

`render_demo.py` fahrt drei Demo-Videos aus Remotion-Komponenten (animierte
Diagramme, Text, Datenvisualisierung) - kein Anbieter, keine Kosten.
Nachweis 22.09.2026: 3 MP4s (3,5 / 4,0 / 4,1 MB) in
`projects/demos/renders/`. Voraussetzung `node`, `npx`, `ffmpeg` - alle drei
vorhanden.

## Bilderzeugung: welcher Weg traegt

Die `.env` im Repo ist die einzige Stelle, an der Anbieter haengen. Stand
22.09.2026 gemessen, jeder Schluessel **echt getestet**:

| Schluessel | Befund |
|---|---|
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | gueltig, Bildmodelle vorhanden (`gemini-2.5-flash-image`, `gemini-3-pro-image`) - Bildaufruf aber **429, Gratis-Tarif-Limit 0** |
| `OPENAI_API_KEY` | gueltig, `gpt-image-1` freigeschaltet - **"no credits remaining"** |
| `OPENROUTER_API_KEY` | Monatslimit erschoepft (`limit_remaining: 0`) |
| AI Horde ueber den lokalen Router | funktioniert technisch, aber Warteschlange ~1780 s |
| ComfyUI | nicht installiert |

**Der tragende Weg ist die lokale Diffusion** (`tools/graphics/local_diffusion.py`)
auf der RTX 3060 Ti: kein Schluessel, keine Kosten. Pakete
`torch torchvision diffusers transformers accelerate safetensors` im Repo-venv,
Modell `stabilityai/sd-turbo` (4 Schritte, ~2,5 GB, passt in 8 GB VRAM).
Das Werkzeug kann `width`/`height`/`seed`/`num_inference_steps`/`guidance_scale`
als Eingaben - fuer sd-turbo gehoeren `num_inference_steps: 4` und
`guidance_scale: 0.0` dazu.

`image_gen` waehlt seinen Anbieter selbst (`_detect_provider`): erst
`OPENAI_API_KEY`, dann `FAL_KEY`, dann lokale Diffusion, wenn `diffusers`
importierbar ist. **Ein toter Schluessel in der `.env` lenkt es auf den toten
Weg** - der OpenAI-Schluessel wurde deshalb wieder ausgetragen (Hinweiszeile in
der `.env`), der Google-Schluessel blieb (fuer Text brauchbar).

## Fallen

- **CUDA-Wheel wird still uebersprungen.** `pip install torch` ohne
  Index-Angabe holt das CPU-Wheel (`2.14.0+cpu`, `torch.cuda.is_available()`
  False). Der zweite Versuch mit `--index-url .../whl/cu130` installierte nur
  `torchvision`: pip vergleicht `2.14.0+cpu` und `2.14.0+cu130` als **gleich**
  (lokale Versionsanhänge zaehlen nicht) und laesst das vorhandene stehen.
  Richtig: `--force-reinstall --no-deps --index-url .../whl/cu130 torch`.
- Welcher CUDA-Index ein Wheel hat, haengt von der torch-Version ab - cu124
  hatte fuer 2.14.0 **nichts**. Vorher pruefen, nicht raten.
- Das Standardmodell des Werkzeugs ist `stabilityai/stable-diffusion-2-1-base`
  mit 30 Schritten - auf 8 GB VRAM langsam; sd-turbo ist der bessere Start.

## Sicherung

`.env` vor jeder Aenderung kopieren (`.env.bak-JJJJMMTT`). Schluesselwerte
niemals ausgeben - nur Name und Laenge pruefen.
