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

## Fundus und Repos (22.09.2026)

Zweiter Lauf, dieselbe Schleife, 1231 Skill-Ordner gefunden, nach MD5 der
`SKILL.md` bleiben **654** (Fundus `C:\Users\faupe\Documents\GitHub` + `O:\Werkstatt\Repos`;
Fundus und Repos fuehren viele Skills doppelt, `copilot-worktrees` kopiert die
Schwester-Repos). 27 min, 8 parallel. Ergebnis:
`Agenten/Hermes/cache/skillspector-fundus/`, Werkzeuge `cache/scratch/skillspector-fundus*.py`.

| Kennzahl | Wert |
|---|---|
| LOW / MEDIUM / HIGH / CRITICAL | 478 / 82 / 47 / 47 |
| Empfehlung SAFE / CAUTION / DO_NOT_INSTALL | 81 / 479 / **94** |
| Skills, die ausfuehrbaren Code mitbringen | 68 |
| Lauf fehlgeschlagen (`execution_successful: false`) | 17 |

**Befund, der zaehlt:** **54 der 94 `DO_NOT_INSTALL` tragen denselben Ordnernamen
wie ein Skill der GELADENEN Bibliothek** — darunter `superpowers` (brainstorming,
subagent-driven-development, systematic-debugging), die `omni-*`-Skills und
`claude-code/plugin-dev`. Die Empfehlung ist ein Filter fuer NEUE Importe, kein
Urteil ueber die eigene Bibliothek.

Was die Regeln wirklich bedeuten (aus `src/skillspector/nodes/analyzers/pattern_defaults.py`):

| Regel | Bedeutung | Haus-Lage |
|---|---|---|
| E1 | externe URL im Text | 581 Treffer = Doku-Rauschen |
| RP1 | Rollen-/Persona-Anweisung („you are an expert") | 436 = Rauschen |
| AS3 | liest SKILL.md ANDERER Skills | 220 — genau das tun `fundus-zugriff` und `skill-library-sync` gewollt |
| RA2 | „unerlaubte Persistenz per Cron" | trifft „create a task for" → Rauschen |
| EA2/EA5 | autonome Entscheidungen ohne Mensch, `claude -p --allowedTools` | **lesen** — hier greifen Hausregeln/Freigabekette |
| AR1/AR2/AR3 | „never refuse", „always respond", „no restrictions" | Marktplatz-Skills; der Grund, sie nicht zu laden |
| P5 | Inhalt, der zu koerperlichem Schaden anleiten kann | `one-skill-to-rule-them-all` („kill someone") |
| YR4 | Prompt-Injection-Text | `receipts`: „model; ignore previous instructions" |
| YR1 | YARA-Signatur | `okx-agentic-wallet`: „Send / transfer native, ERC-20, SPL, BTC" — genau der Job eines Wallet-Skills |
| SSRF2 | Anfrage an loopback | `openmontage`-Skills (lokaler Dienst) |
| LP3 | keine Tool-Grenzen deklariert, Code nutzt Faehigkeiten | Hygiene: `permissions`/`allowed-tools` nachtragen |
| PE1 | `permissions: *` | `kraken-cli/skills/kraken-autonomy-levels` |

**Nie importieren:** `one-skill-to-rule-them-all`(-main) und
`copilot-worktrees/.../superpowers-*` sind absichtlich gegen Regeln gebaut
(AR2/AR3/P5/YR1) — im Fundus zu Recht ungeladen.

## Bot-Profile und Struktur (22./23.09.2026)

Dritter Lauf ueber die **geladenen** Bibliotheken der Bot-Profile
(`profiles/<bot>/skills`, nach Hash-Dedupe **278** Skills, 20 min). Die 20
Profile tragen weithin dieselben Skills — ohne Dedupe waeren es 1389.
Ergebnis: `cache/skillspector-bots/`.

| Kennzahl | Wert |
|---|---|
| LOW / MEDIUM / HIGH / CRITICAL | 190 / 35 / 26 / 27 |
| SAFE / CAUTION / DO_NOT_INSTALL | 5 / 220 / 53 |
| mit ausfuehrbarem Code | 53 |
| Lauf fehlgeschlagen | 8 |

Echt und behoben: **SC8** — `hermes-config-ops/scripts/__pycache__/` lag als
Bytecode in zwei Profilkopien; alle 8 `__pycache__` unter `skills/` und
`profiles/` geloescht. Sonst dieselben Rauschklassen wie im Fundus
(E1 302 = URLs, PE3 141 = Doku ueber Schluessel, RP1 75 = „du bist ein Experte",
RA2 68 = „create a task for"). Was zu LESEN bleibt: EA5/EA2 in
`autonomous-ai-agents/claude-code` und `codex` (`claude -p … --allowedTools`,
`codex exec --sandbox danger-full-access`) — Anleitungen zum schrankenlosen
Lauf, in jedem der Profile.

### Struktur schlanker — was gemacht wurde

| Eingriff | Vorher | Nachher | Beleg |
|---|---|---|---|
| `profiles/caveman/checkpoints` (`hermes -p caveman checkpoints clear -f`) | 10,6 GB | 0 B | `checkpoints status`, C: 41 → 52 GB frei |
| `.hub/index-cache/*.json` in 19 Bot-Profilen (Cache der Skill-Registry) | 707 MB | 0,4 MB | Hauptbibliothek bewusst behalten |
| 686 inhaltsgleiche Skill-Ordner in den Profilen → Junction auf `Agenten/Hermes/skills/<...>` | 1389 Ordner, 20,9 MB Kopien | 686 Junctions | Trockenlauf + `skills list` aller 21 Profile VOR/NACH identisch |

Werkzeug: `Agenten/Hermes/scripts/skill-kopien-verknuepfen.py`
(Trockenlauf Standard, `--anwenden`, `--zuruecknehmen` aus
`<profil>/skills/.sicherung-junctions/`; Manifest `cache/skill-junctions.json`).
Verglichen wird der GANZE Ordner (jede Datei), nicht nur die SKILL.md — sonst
ginge eine abweichende Referenzdatei verloren. **Lehre:** `Werkstatt` ist eine
Junction, deshalb braucht SkillSpector `O:\...`; fuer die Skill-Prüfung ist das
ohne Belang.

**Nicht angefasst, weil es Qualitaet kostet oder Backup ist:** die 753
profil-eigenen Skills (u. a. `nerd` mit 166 Skills ≈ 5.891 Token je Anfrage —
der einzige echte Token-Brocken), `.archive` (70–80 Skills je Profil),
`.curator_backups` (11–13 MB je Profil), `lsp` (29–52 MB je Profil),
`checkpoints` der uebrigen Profile (0,2–231 MB, echtes Rollback).

## Offen

- **Nicht gescannt:** `Werkstatt/security-skills-claude-code` (10),
  `MaxHirn/optional-skills` (1). Nicht scanbar: die `okx-*`-Junctions.
- 17 Berichte im Fundus-, 8 im Bot- und 3 im Bibliothekslauf sind fehlgeschlagen
  (unaufgeloeste Referenzen) — dort ist die Pruefung nur teilweise gelaufen.
- Falschmeldungen einmal als **Baseline** einsperren (`skillspector baseline`),
  dann zeigen Wiederholungslaeufe nur noch NEUES.
- Wiederholung als Routine/Wache ist noch nicht verdrahtet.