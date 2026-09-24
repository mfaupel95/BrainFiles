# Lokale Bildkette statt bezahlter Bild-API

Fuer den Fall: ein Fremd-Repo (Video-/Bild-/Agentenwerkzeug) will Bilder
erzeugen, alle Cloud-Schluessel des Hauses tragen aber nicht. Hier steht der
gemessene Ablauf und die Anbieter-Triage.

## 1. Anbieter-Triage (jeden Kandidaten EINEN echten Aufruf kosten lassen)

| Pruefung | Aufruf | Traegt wenn |
|---|---|---|
| Schluessel gueltig? | `curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $K" https://api.openai.com/v1/models` | 200 |
| Bildmodelle vorhanden? | derselbe Aufruf, `tr '{' '\n' | grep -oE '"id": *"[^"]*"' | grep -i image` | `gpt-image-1` o. ae. in der Liste |
| Google-Faehigkeit | `curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$K"` | Modellnamen `*-image*` |
| Guthaben/Limit | `curl -s -H "Authorization: Bearer $K" https://openrouter.ai/api/v1/key` | `limit_remaining` > 0 |
| Gratis-Crowd | `curl -s https://aihorde.net/api/v2/status/models?type=image` | Arbeiterzahl je Modell, nicht der Katalog |

Gemessen toedlich trotz 200: Google `429 … free_tier_requests limit: 0`,
OpenAI `credit_balance_exhausted`, OpenRouter `limit_remaining: 0`,
AI Horde `queue wait ~1780s … budget 595s left`. Erst der Fehlertext des
ECHTEN Aufrufs entscheidet, nicht die Modellliste.

## 2. Lokale Diffusion in das Repo-venv

1. CUDA-Index fuer die Ziel-torch-Version suchen (siehe SKILL.md, Punkt 9) -
   ein Index ohne Wheel fuer diese Version laesst pip still scheitern.
2. `pip install --force-reinstall --no-deps --index-url .../whl/<cuNNN> torch`
3. `pip install diffusers transformers accelerate safetensors`
4. Modell vorab laden, ohne torch zu importieren:
   `python -c "from huggingface_hub import snapshot_download; print(snapshot_download('stabilityai/sd-turbo'))"`
5. Beleg: `torch.cuda.is_available()` True, dann ein echter Bildaufruf.

## 3. Aufruf und Beleg

Ueber das WERKZEUG des Repos aufrufen, nicht ueber ein Eigenbau-Skript - sonst
beweist man die eigene Nachbildung. Muster (Sonde im Haus-Cache, gegen das
Repo-venv gestartet):

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools.graphics.local_diffusion import LocalDiffusion
r = LocalDiffusion().execute({
    "prompt": "...", "negative_prompt": "text, watermark, blurry",
    "model": "stabilityai/sd-turbo",     # Vorgabe des Repos ist langsamer
    "num_inference_steps": 4, "guidance_scale": 0.0,
    "width": 512, "height": 512, "seed": 1234,
    "output_path": str(ZIEL),
})
```

Beleg ist der ToolResult (`success: true`, `cost_usd: 0.0`, `duration_seconds`)
plus die existierende Datei mit Groesse. Das Bild vor dem Weiterreichen mit
`vision_analyze` ansehen - ein Turbo-Modell mit falscher Schritt-/Fuehrungszahl
liefert sonst bereitwillig Rauschen, das wie ein Erfolg aussieht.

## 4. Sonden sauber halten

Die Sonde liegt in `Agenten/Hermes/cache/scratch/` und wird zum Lauf in den
Repo-Ordner kopiert (`cp` + Repo-venv starten, weil die Importe des Repos ein
Repo-Arbeitsverzeichnis brauchen). Nach dem Lauf die Kopie aus dem Repo
ENTFERNEN und mit `git status --porcelain` pruefen, dass nur die erwartete
Sicherung als untracked uebrig bleibt.

## 5. Wenn der Nutzer fragt, ob ein Abo/Proxy das uebernehmen kann

Ein Verteiler fuer Chat-Abos (Claude-/Codex-Pools) liefert nur, was seine
Routen hergeben (`/v1/messages`, `/v1/models`). Antwort in DREI Teilen:
(1) die gemessenen Routen des Dienstes, (2) die gemessene Aussage des echten
Bildaufrufs, (3) was tatsaechlich traegt (lokale Kette laeuft schon; Cloud nur
mit Guthaben/Abrechnung). Keine Zusage ohne Aufruf.

Ist der Verteiler ein OpenAI-kompatibler Router (Haus: OmniRoute, Port 20128),
gilt zusaetzlich: dass er `/v1/images/generations` bedient, heisst NICHT, dass
hinter der Route ein Bildanbieter steht. Die Modellliste ist der LiteLLM-Katalog
und fuehrt Bildmodelle fuer Anbieter ohne Konto. Vor jeder Zusage gegen die
echten `provider_connections` joinen und die Verdrahtung mit einem Aufruf
belegen, dessen `OPENAI_BASE_URL` nur in der Prozessumgebung des Testlaufs
steht — Details in `omniroute-betrieb`.
