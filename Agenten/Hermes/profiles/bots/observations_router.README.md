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
  (`hermes -p recherche chat -q ... -Q`), auf das Ergebnis wird gewartet. Die
  Recherche bekommt den ECHTEN Beobachtungstext (Markdown-Body), klar markiert
  als **UNTRUSTED DATA**, und muss eine streng parsebare JSON-Antwort mit
  `action`/`target_profile` liefern:

      {"action": "route", "target_profile": "<bot-name>"}
      {"action": "ignore"}

- **Fachbot:** das Ziel kommt AUSSCHLIESSLICH aus der Recherche-Antwort,
  NICHT aus dem Frontmatter (das One-Skill-Schema hat kein `target_profile`).
  Nur wenn die Antwort eindeutig, allowlist-valide und auf der Platte ist,
  wird danach genau EIN bestehender Fachbot aufgerufen. Gueltig heisst:
  `target_profile` in der Allowlist `ALLOWLIST` UND als Profil auf der Platte
  (`profiles/<name>/config.yaml`). Erlaubt sind NUR passende Wissens-/Skill-/
  Wartungsprofile (`obsidian-skills`, `gbrain`, `hermes-wartung`,
  `one-skill-to-rule-them-all`); Handels-/Markt- und Live-faehige Profile
  (`jev-trader`, `markt-recherche`) sind bewusst NICHT erlaubt — der Dispatcher
  baut keinen automatischen Pfad zu Handels- oder Live-Befugnissen. Bei
  ungueltiger Antwort (kein JSON, unbekannte `action`, `target_profile` nicht
  allowlist-valide oder nicht auf der Platte) wird KEIN Fachbot gestartet.
  `action: ignore` schliesst sauber ohne Fachbot ab.
- **Keine Selbstverstaerkung:** `recherche` (der Recherche-Schritt selbst) und
  `bots` (der Interpool selbst) sind NICHT in der Fachbot-Allowlist — keine
  Chat-Schleife, keine Parallelitaet.

## Idempotenz

Ueber die stabile Observation-ID (`id:`-Feld, sonst Dateiname) und das
Statefile `observations_router.state.json` im bots-Profil. Eine bereits
verarbeitete Beobachtung wird bei einem erneuten Lauf uebersprungen. Eine
ungueltige Recherche-Antwort wird NICHT als verarbeitet markiert, damit ein
transienter Fehler im naechsten Lauf erneut versucht werden kann.

## Sicherheitsgrenzen

Keine Orders/Live-Aktionen, keine Dateiaenderungen im One-Skill-Repo, keine
SkillsBot-Runtime-Aenderung, kein Cron, keine Gateway-/Bot-Neustarts. Der
Dispatcher startet ausschliesslich `hermes -p <profil> chat -q ... -Q
--toolsets search`-Subprozesse mit bereinigter Umgebung (PYTHONHOME/PYTHONPATH
entfernt, HERMES_HOME gesetzt).

**Read-only-Grenze (technisch erzwungen):** Beide Hermes-Aufrufe (Recherche und
Fachbot) starten mit `--toolsets search`. Damit ist der bereitgestellte
Toolkatalog auf `web_search` begrenzt — die Fachbots haben NUR Websuche
(read-only), kein Toolset-Default und keine Profil-Toolset-Vererbung. Es sind
keine Datei-, Terminal-, Process-, Cron-, Connections- oder Order-Tools
moeglich. Der Router selbst schreibt ausschliesslich seinen Idempotenz-State
(`observations_router.state.json`); er uebergibt nur Text und wertet nur die
Recherche-JSON aus, er verarbeitet keine Outputs des Fachbots als Befehle.

**Prompts bleiben untrusted:** Die Observation wird in beiden Prompts weiterhin
explizit als UNTRUSTED DATA markiert und nie als Systemanweisung behandelt.
Trotz der read-only-Erzwingung wird der Beobachtungstext nicht zu einer
Websuche aufgefordert, falls die Beobachtung privat ist — der Fachbot soll
privat bleibende Inhalte nicht ins Netz tragen.

## Tests

    python -m unittest tests.test_observations_router -v

Synthetische Markdown-Dateien in einem Temp-Ordner, hermes-Subprozesse
vollstaendig gemockt — kein echter A2A-/LLM-Aufruf. Geprueft wird: JSON-Routing
(Ziel aus der Recherche-Antwort), ungueltige Antwort / `target_profile` =
`recherche`/`bots`/`jev-trader`/`markt-recherche` ergibt keinen Fachbot (kein
zweiter Hermes-Prozess), der Beobachtungstext wird als UNTRUSTED DATA
mitgegeben, genau eine Observation pro Lauf, serielle Aufrufreihenfolge,
read-only-Fachbot-Prompt. Zusaetzlich wird der echte `subprocess.Popen`-Aufruf
gemockt und geprueft, dass BEIDE Hermes-Aufrufe (Recherche und Fachbot) die
Kommandoargumente `--toolsets search` enthalten und die Serienreihenfolge
Recherche -> genau EIN Fachbot bleibt.
