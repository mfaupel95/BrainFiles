# Fremde Skills vor dem Import scannen (SkillSpector)

Ein Skill aus dem Fundus oder aus `Werkstatt/Repos` ist fremder Text, der dem
Agenten Anweisungen gibt — das Gate vor jedem Uebernehmen.

## Aufruf

Klon in `Werkstatt/skillspector` (NVIDIA, Apache-2.0). Statisch und offline,
Einrichtung: `uv venv --python 3.14 .venv` im Repo, `uv pip install -e .`.

```bash
cd /o/Werkstatt/skillspector
./.venv/Scripts/skillspector.exe scan "C:/Pfad/zum/skill" --no-llm
./.venv/Scripts/skillspector.exe scan "C:/Pfad/zur/sammlung" --no-llm --recursive
```

## Zwei Fallen, die den Lauf still entwerten

- **Junction-Elternteil:** `Error: Refusing to resolve input with a symlinked
  parent`. `Werkstatt/` ist eine Junction auf `O:\`; denselben Pfad ueber das
  **Aufloesungsziel** aufrufen (`/o/Werkstatt/...`), sonst endet der Scan vor
  der ersten Datei. Die `okx-*`-Skills (Junctions auf `~/.agents/skills`) sind
  damit strukturell nicht scanbar — als Luecke ausweisen, nicht als "clean".
- **MSYS-Pfade:** `/c/Users/...` als Argument gibt `Cannot determine input
  type`. Windows-Pfade mit Schraegstrichen uebergeben (`C:/Users/...`).
- **Ein Bericht kann wie „0 Befunde, LOW" aussehen, ohne analysiert zu haben.**
  Immer `analysis_completeness.execution_successful` und `.status` mitlesen.
  Die LLM-Stufe ueber ein lokales 8k-Modell laeuft an, endet aber mit
  `status: failed` / `LengthFinishReasonError` und liefert einen gruenen,
  leeren Bericht.

## Risikowert lesen

Die Zahl beantwortet **„ist das aus unbekannter Hand installierbar?"**, nicht
„ist mein eigener Text gefaehrlich": eigene, dokumentierende Skills landen auf
`100/CRITICAL`, weil sie Installationsbefehle (`curl … | bash`) zitieren und
Referenzen nennen, die lokal nicht aufloesbar sind. Vor jeder Panikmeldung die
Namen der auffaelligen Skills gegen die Ordner der **geladenen** Bibliothek
stellen — ein grosser Teil traegt denselben Namen wie ein laufender Haus-Skill
(`superpowers`, `omni-*`, `claude-code/plugin-dev`).

| Regel | Bedeutung | Im Haus |
|---|---|---|
| AE1 | genannte Referenz nicht aufloesbar | Prueftiefe, keine Gefahr — groesster Einzelposten |
| E1 | externe URL im Text | Doku-Rauschen |
| RP1 | Rollen-/Persona-Anweisung („you are an expert") | Rauschen |
| RA2 | „unerlaubte Persistenz per Cron" | trifft „create a task for" → Rauschen |
| AS3 | liest SKILL.md ANDERER Skills | genau das tun `fundus-zugriff`/`skill-library-sync` gewollt |
| LP3 | keine Tool-Grenzen deklariert, Code nutzt Faehigkeiten | Hygiene: `permissions`/`allowed-tools` nachtragen |
| AR1/AR2/AR3 | „never refuse", „always respond", „no restrictions" | **lesen** — unterdrueckt Widerspruch gegen Hausregeln |
| EA2/EA5 | autonome Entscheidung ohne Mensch, `claude -p --allowedTools` | **lesen** — hier greifen Freigabekette/Regelwerk |
| P5 / YR4 / YR1 | koerperlicher Schaden / Injection-Text / YARA-Treffer | Einzelfall ansehen; Treffer sind Woerter, keine Malware |
| SC8 | mitgelieferter Bytecode (`.pyc`, `__pycache__`) | echter Hygiene-Fund — loeschen |

Die Regelbedeutungen stehen im Quelltext, nicht in der Doku:
`src/skillspector/nodes/analyzers/pattern_defaults.py` — nachschlagen statt
aus der Kennung raten.

## Ganze Bibliotheken scannen

Muster: alle Ordner sammeln, die DIREKT eine `SKILL.md` tragen; byte-identische
per MD5 der `SKILL.md` ueberspringen (Fundus und `Werkstatt/Repos` fuehren
dieselben Skills mehrfach, `copilot-worktrees` kopiert Schwester-Repos); je
Skill ein JSON, dann in Python aggregieren:

```python
subprocess.run([EXE, "scan", str(skill_ordner), "--no-llm", "-f", "json", "-o", out], timeout=300)
```

- `.archive/`, `.git`, `.venv`, `node_modules` auslassen; Ordner unter einem
  Junction-Elternteil vorher aussortieren (`os.path.isjunction` gegen den
  ganzen Elternpfad), sonst zaehlen Fehlschlaege als Befunde.
- 8 Arbeiter (`ThreadPoolExecutor`) sind auf dieser Maschine unauffaellig;
  gemessen 15–30 s je Skill, ~650 Skills ≈ 27 min. Als Hintergrundprozess
  starten und `lauf.log` mitzaehlen statt synchron warten.
- Berichte mit `execution_successful: false` (unaufgeloeste Referenzen) sind
  **unvollstaendig geprueft**, nicht sauber — getrennt ausweisen.
- Ergebnisordner in die Wegwerfzone (`Agenten/Hermes/cache/<zweck>/`), die
  Auswertung als Python-Einzeiler ueber alle JSONs; die Regel-Zaehlungen sind
  die Aussage, nicht der Mittelwert der Risikowerte.

## LLM-Stufe

Nur ueber den lokalen Router fahren, nie ueber ein 8k-Modell:

```bash
SKILLSPECTOR_PROVIDER=openai_compatible \
SKILLSPECTOR_COMPAT_BASE_URL=http://127.0.0.1:20128/v1 \
SKILLSPECTOR_COMPAT_API_KEY="$HERMES_CUSTOM_127_0_0_1_20128_API_KEY" \
SKILLSPECTOR_MODEL=auto/best-coding \
  ./.venv/Scripts/skillspector.exe scan "C:/…/skill" -f json -o bericht.json
```
