---
titel: Hermes-Wartung
bereich: Werkzeuge
stand: 2026-09-30
tags: [hermes, update, gateway, wartung]
---

# Hermes-Wartung (`hermes update`)

Ein Update holt dreistellig viele Commits, baut TUI, Web-UI und die
Desktop-App neu und startet dabei den Gateway neu. Es dauert 20 bis 30
Minuten und darf **nicht** im Vordergrund eines Chat-Werkzeugaufrufs laufen —
der Neustart reißt den Aufrufer ab.

## Ablauf, der trägt

1. **Checkout sauber machen.** Fremdes im Arbeitsbaum zuerst committen
   (`Andere Sitzung <fremd@local>`), sonst nimmt der Reset es aus dem Zweig.
2. **Losgelöst starten** — PowerShell-Skript über `Start-Process -WindowStyle
   Hidden`, das selbst `BEFORE_HEAD`, die Ausgabe, `AFTER_HEAD`, den Abstand
   zu `origin/main` und `EXIT` in eine Logdatei schreibt
   (`Agenten/Hermes/logs/update-<datum>.log`).
3. **Log lesen, nicht raten.** Die Zahlen am Ende sind der Beleg.
4. **Dienste nachziehen** (siehe Fallen).
5. **`hermes doctor`** gegenprüfen — harte Fehler sind `✗`, alles andere ist
   eine fehlende optionale Integration und kein Ausfall.

## Fallen (gemessen am 29./30.09.2026)

- **`EXIT 1` heißt nicht „nichts passiert".** Beide Läufe meldeten 1, obwohl
  Code gepullt, alles gebaut und installiert war. Der Grund stand im Log:
  `RuntimeError: Could not restart every paused Windows gateway`. Immer erst
  `AFTER_HEAD` und den Abstand prüfen, dann den Dienst.
- **Der Gateway-Task hat einen neuen Namen.** `Hermes_Gateway` gibt es nicht
  mehr; gültig ist **`Hermes_Gateway_2ef9d0b7`** (`Get-ScheduledTask |
  Where TaskName -like '*ermes*'`). `Start-ScheduledTask` darauf, danach
  braucht der Port 9900 **50 bis 90 Sekunden**, bis er `200` liefert — vorher
  antwortet er mit `000`, und das ist noch kein Fehler.
- **Nach dem Lauf sind ALLE Werkzeuge blockiert.** Die Abhängigkeits-
  Installation für 23 Profile startet über hundert `python.exe` im
  Sekundentakt; `terminal`, `read_file` und die MCP-Werkzeuge laufen in
  420-Sekunden-Timeouts, auch bei `echo test`. Das ist Last, kein Defekt — es
  heilt von selbst (beobachtet: rund zwei Stunden). **Nicht** den Rechner neu
  starten, **nicht** Hermes abschießen.
- **Committete Fremdarbeit nimmt der Reset aus dem Zweig.** Der Lauf rettet
  sie als `refs/hermes-update-backups/diverged-main-<zeit>-<sha>` und sagt es
  im Log. Zurückholen ohne den Live-Checkout umzuschreiben:
  `git show <ref>:<pfad> > <pfad>` — `git restore` im Checkout ist gesperrt.
  **Untracked** Dateien werden dagegen gestasht und automatisch
  zurückgeholt (`Restoring local changes`).
- **Die Logdatei ist gemischt kodiert.** PowerShell-`*>>` schreibt UTF-16,
  die eigenen Zeilen UTF-8. Lesbar mit `tr -d '\000' < log` oder
  `read_bytes().replace(b'\x00', b'').decode('utf-8', 'replace')`.
- **`hermes update --check` ist unzuverlässig** und kann selbst nach einem
  Lauf in einen Zeitablauf laufen. Maßgeblich sind
  `git rev-list --count HEAD..origin/main` und `hermes --version`
  („Up to date").

## Stand

- 29.09.2026 abends: Lauf 1 holte 203 Commits, Lauf 2 holte 1841 Commits
  (mit `pyproject.toml` und `uv.lock`). Danach `HEAD ca705dbf7e`, Gateway und
  Dashboard auf `200`, `hermes --version` meldet „Up to date".
- Offen: 14 Orphan-Aliase (`<profil>.bat` für Profile, die nicht mehr
  existieren), ein lokaler `Dockerfile`-Unterschied im Checkout.
