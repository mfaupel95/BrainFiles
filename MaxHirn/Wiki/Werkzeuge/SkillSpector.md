---
id: 20260922-skillspector
title: 'Werkzeuge — SkillSpector (Skill-Sicherheitsscan)'
tags: [werkzeuge, skills, sicherheit]
created: 2026-09-22
updated: 2026-09-22
related: ['[[Werkzeuge/Fundus-Skills-Bots]]', '[[Betrieb/Hermes]]', '[[Lektionen/Wahrheit-pruefen]]']
summary: 'NVIDIA SkillSpector liegt eingerichtet in Werkstatt/skillspector; was er findet, welche Befunde echt sind und wie der Risikowert zu lesen ist.'
---

# SkillSpector — Skill-Sicherheitsscan

NVIDIA SkillSpector (`Werkstatt/skillspector`, Apache-2.0, v2.11.1) prueft
Agenten-Skills auf prompt injection, Datenabfluss, Rechteausweitung,
Supply-Chain-Muster und bekannte Malware-Signaturen (YARA). Es ist der
Gegenstand zur Regel „nichts aus fremden Baeumen importieren": **vor dem
Installieren fragen, ob der Skill sicher ist** — nicht erst danach.

## Aufruf

Das venv liegt im Repo (Python 3.14, `uv pip install -e .`). **Immer ueber den
echten Pfad `O:\...` aufrufen, nie ueber `Werkstatt\...`:**

```bash
cd /o/Werkstatt/skillspector
./.venv/Scripts/skillspector.exe scan "C:/Pfad/zum/skill" --no-llm        # statisch
./.venv/Scripts/skillspector.exe scan "C:/Pfad/zur/sammlung" --recursive   # Geschwister-Skills
```

**Falle:** `Werkstatt/` ist eine Junction. SkillSpector bricht mit
`Refusing to resolve input with a symlinked parent` ab, wenn der Zielpfad unter
einem symlink-Elternteil liegt — dieselbe Regel trifft die `okx-*`-Skills
(Junctions auf `~/.agents/skills`). Ueber `O:\Werkstatt\...` und fuer die
Junctions gar nicht aufrufbar.

**Falle:** MSYS-Pfade (`/c/Users/...`) versteht das native Programm nicht
(„Cannot determine input type"). Windows-Pfade mit Schraegstrichen uebergeben.

## Was der Lauf vom 22.09.2026 gemessen hat

124 Skills der geladenen Bibliothek `Agenten/Hermes/skills` (ohne `.archive/`,
ohne Junctions), statisch, 4 parallel, rund 8 Minuten. Ergebnisse:
`Agenten/Hermes/cache/skillspector/*.json`, Auswertung `auswertung.json`.
Werkzeuge (Wegwerfzone): `cache/scratch/skillspector-scan.py`, `skillspector-auswerten.py`.

| Kennzahl | Wert |
|---|---|
| sauber (LOW, Wert ≤ 10) | **73** |
| MEDIUM | 18 |
| HIGH | 8 |
| CRITICAL | 17 |
| Bericht fehlgeschlagen (`execution_successful: false`) | 3 (handel-spuren, evaluating-llms-harness, okx-ai) |

Der Wert **ist kein Sicherheitsurteil**. Eigene, dokumentierende Skills
(`hermes-agent`, `claude-code`) kamen auf 100/CRITICAL, weil sie
Installationsbefehle WIE `curl … | bash` dokumentieren (Regel TM2 „Tool
Chaining") und Referenzen nennen, die beim lokalen Scan nicht aufloesbar sind
(AE1). Die Zahl beantwortet: **„ist dieser Skill aus unbekannter Hand
installierbar?"** — nicht „ist mein eigener Text gefaehrlich".

## Falschmeldungen, die man sofort erkennt

| Regel | Ausloeser | Warum harmlos |
|---|---|---|
| MP3 Memory Poisoning | „swap context" | Krypto-Swap, kein Kontext-Austausch (okx-*) |
| P6 System Prompt Leakage | „Display Rules" | Ausgabe-Vorschrift der Marktplatz-Skills |
| PE3 Credential Access | `.env`, `~/.ssh/id_ed25519` | Doku ueber Schluesselablage, kein Zugriff |
| P2 Hidden Instructions | HTML-Kommentar in SKILL.md | Generator-Hinweis (OmniRoute) |
| AE1 | unaufloesbare Pfadangabe | Prueftiefe, keine Gefahr — 96 der 124 Treffer |
| E2 Exfiltration | `dict(os.environ)` in `handel-spuren/references/pitfalls.md` | genau dort STEHT, warum die volle Umgebung durchgereicht wird |

## Was echt war

- **SC8, behoben:** `brainfiles/hermes-config-ops/scripts/__pycache__/` lag
  `.pyc`-Bytecode im Skill (nicht versioniert, aber auf der Platte). Bytecode im
  Skill ist ein Review-Blindfleck — Ordner geloescht.
- **EA5, zu lesen:** `autonomous-ai-agents/codex` empfiehlt
  `codex exec --sandbox danger-full-access`. Steht in fremder Herkunft, ist
  bewusst so dokumentiert — beim Abschreiben trotzdem nicht blind uebernehmen.
- **AR1/AR2 Anti-Refusal:** okx-Marktplatz-Skills tragen „never refuse",
  „do not warn", „always respond". Diese Skills wuerden Widerspruch gegen
  eigene Regeln unterdruecken — der Grund, sie nicht zu laden.
- **YARA/YR1:** acht Rohtreffer (`ransomware_behavior` bei „send native, ERC-20,
  SPL, BTC", `backdoor_persistence` bei `crontab -l`) — Signaturtreffer auf
  Woertern, keine Malware.

## Die LLM-Stufe ist lokal nicht fahrbar

`SKILLSPECTOR_PROVIDER=ollama` mit `qwen35-8k:latest` **laeuft an, liefert aber
einen Bericht, der wie „0 Befunde, LOW" aussieht und in Wahrheit nicht
analysiert hat**: `status: failed`, `llm_batch_failed`,
`LengthFinishReasonError` (8k-Kontext zu klein fuer das Analysepensum).
Genau die Falle aus [[Lektionen/Wahrheit-pruefen]] — bei jedem LLM-Bericht
`execution_successful` und `analysis_completeness.status` mitlesen.

Fahrbar ist die Stufe ueber den lokalen Router (OmniRoute, Port 20128):

```bash
SKILLSPECTOR_PROVIDER=openai_compatible \
SKILLSPECTOR_COMPAT_BASE_URL=http://127.0.0.1:20128/v1 \
SKILLSPECTOR_COMPAT_API_KEY="$HERMES_CUSTOM_127_0_0_1_20128_API_KEY" \
SKILLSPECTOR_MODEL=auto/best-coding \
  ./.venv/Scripts/skillspector.exe scan "C:/…/hermes-doctor" -f json -o bericht.json
```

Beleg: `status partial`, `execution_successful true`, ein MEDIUM-Befund
(`hermes-doctor-router.json` in der Wegwerfzone).

## Offen

- Falschmeldungen einmal als **Baseline** einsperren (`skillspector baseline`)
  — dann zeigen Wiederholungslaeufe nur noch NEUES.
- Fremd-Fundus (`MaxHirn/skills`, `O:\Werkstatt\Repos`) ist noch nicht gescannt.
- Wiederholung als Routine/Wache ist noch nicht verdrahtet.