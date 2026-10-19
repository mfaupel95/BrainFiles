# openmontage lokal: Bildwerkzeuge und Grenzen

Fremd-Repo `Werkstatt/openmontage`, eigener venv mit Python 3.14,
Diffusers/Torch lokal. Alle Cloud-Schluessel sind tot (OpenAI ohne Guthaben,
Google-Bildmodelle ratenlimit, OpenRouter Monatslimit), AI Horde hat
Warteschlange — **lokale Diffusion ist der einzige freie Weg**.

## Bildgenerierung

`tools/graphics/local_diffusion.py`, Modell `stabilityai/sd-turbo` aus dem
HF-Cache, `num_inference_steps=4`, `guidance_scale=0.0` (das Standardmodell
`stable-diffusion-2-1-base` mit 30 Schritten ist auf 8 GB VRAM zu langsam).
Rund 29 s je Bild auf der RTX 3060 Ti. Die Erkennung der Provider-Reihenfolge
nimmt `OPENAI_API_KEY` ZUERST — ein toter Schluessel in der `.env` lenkt auf
den toten Weg (OpenAPI-Key darum ausgetragen, Hinweiszeile bleibt).

Installer-Falle: `pip install torch` ohne Index holt ein CPU-Rad, und
`--index-url cu130` „installiert" nur torchvision, weil pip die CPU-Version
als passend wertet — `--force-reinstall --no-deps` noetig.

## Was der Bildagent daraus macht (und was nicht)

Ein Agent mit diesem Repo baut gern eine Bodennmaske, faehrt 6
Diffusionsvarianten (strength 0.35/0.5/0.65) und meldet dann Erfolg. Der
Output liest sich als Holzoptik mit radialer Perspektive — genau das war der
Befund. Ursachen:

- ein Perspektiv-Mapper mit 3x5 Kacheln und Kanten-Crossfade erzeugt
  Dielenoptik statt quadratischer Fliesen,
- ein Gain auf eine Referenzfarbe zieht das Bild ins Holz,
- die Lichtkarte ohne Glaettung traegt die alte Belagsstruktur hinein.

**Deshalb: das Composite selbst bauen** (siehe `references/` des
Hauptskills), die Diffusionsbilder nur als Materialidee oder als
Alternative im Bericht nennen.

## Eigenes Werkzeug: der Mapper

Rund 120 Zeilen `numpy` + `PIL` reichen:

1. Textur entrahmen und auf eine Kachelgroesse bringen, Kanten crossfaden.
2. `mask` aus der Bodengrenze als Funktion der Spalte, weiche Kante
   (Feather ~20 px).
3. Perspektive: `s` (0 = nah, 1 = fern) aus einer reziproken Tiefe,
   `zu = (x - fp_x) / (w/2) * N_q * (1 - 0.62 * s)`, `zv = s * N_l`.
4. Fugen als dunkles Raster in den Texturkoordinaten (kein Bild-Overlay).
5. Licht: Original-Luminanz, **vorher weichgezeichnet** (`GaussianBlur(24)`),
   als Multiplikator 0.55 + 0.75*rel.
6. Saettigung absenken, Mittelwert auf den Zielton verschieben.
7. `result = orig*(1-mask) + tile*mask` — der Raum ist damit unveraendert.

Gemessen an einem 1440x2560-Flurfoto: 32-48 % geaenderte Pixel (nur der
Boden), Raumwinkel und Tueren pixelweise unveraendert, Fugen perspektivisch
korrekt.

## Abgabe

Ergebnis als PNG (volle Aufloesung) und JPG (Telegram-tauglich) ablegen,
plus ein Detail-Crop. Pfad absolut nennen — `Werkstatt/` ist eine Junction
auf `O:`, der Pfad im Bericht muss dorthin zeigen. Eine Bot-Erfolgsmeldung
erst selbst an einem Bild pruefen, bevor sie weitergegeben wird.