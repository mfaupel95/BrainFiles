# Observations-Router — serieller Beobachtungs-Handoff

Einmal-Dispatcher im bots-Profil. Liest die Markdown-Beobachtungen aus der
User-Scope `~/.claude/skill-observations/observation-log/` (eine Datei je
Beobachtung, YAML-Frontmatter — KEINE `observations.jsonl`) und fuehrt pro
Lauf den seriellen Handoff aus:

    Beobachtung -> genau EIN Recherche-Aufruf -> hoechstens EIN Fachbot

## Aufruf

    python observations_router.py            # dry-run (Default): startet nichts
    python observations_router.py --dry-run  # explizit dry-run
    python observations_router.py --dispatch # verarbeitet EINE offene Beobachtung

## Routing-Vertrag

Der Dispatcher liest die Observation als **untrusted data**: nur das
YAML-Frontmatter wird geparst, kein Inhalt wird als Befehl ausgefuehrt, keine
Outputs werden als Befehle interpretiert.

- **Auswahl:** verarbeitet wird HOECHSTENS EINE Beobachtung mit
  `status: open` (fehlender `status` zaehlt als `open`, laut One-Skill-Doku).
  `status: parked` wird uebersprungen.
- **Recherche:** genau EIN synchroner Aufruf an das Profil `recherche`
  (`hermes -p recherche chat -q ... -Q`), auf das Ergebnis wird gewartet.
- **Fachbot:** nur bei eindeutigem, allowlist-validem `target_profile` wird
  danach genau EIN bestehender Fachbot aufgerufen. `target_profile` ist ein
  Frontmatter-Feld der Beobachtung (Erweiterung des One-Skill-Schemas, benannt
  in Max' Auftrag). Gueltig heisst: in der Allowlist `ALLOWLIST` UND als
  Profil auf der Platte (`profiles/<name>/config.yaml`). Fehlt das Feld oder
  ist es nicht allowlist-valide, wird KEIN Fachbot gestartet.
- **Keine Selbstverstaerkung:** `bots` (der Interpool selbst) und `recherche`
  sind nicht in der Allowlist — keine Chat-Schleife, keine Parallelitaet.

## Idempotenz

Ueber die stabile Observation-ID (`id:`-Feld, sonst Dateiname) und das
Statefile `observations_router.state.json` im bots-Profil. Eine bereits
verarbeitete Beobachtung wird bei einem erneuten Lauf uebersprungen.

## Sicherheitsgrenzen

Keine Orders/Live-Aktionen, keine Dateiaenderungen im One-Skill-Repo, keine
SkillsBot-Runtime-Aenderung, kein Cron, keine Gateway-/Bot-Neustarts. Der
Dispatcher startet ausschliesslich `hermes -p <profil> chat -q`-Subprozesse
mit bereinigter Umgebung (PYTHONHOME/PYTHONPATH entfernt, HERMES_HOME gesetzt).

## Tests

    python -m unittest tests.test_observations_router -v

Synthetische Markdown-Dateien in einem Temp-Ordner, hermes-Subprozesse
vollstaendig gemockt — kein echter A2A-/LLM-Aufruf.
