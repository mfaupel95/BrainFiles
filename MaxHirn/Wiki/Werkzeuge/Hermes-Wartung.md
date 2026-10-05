---
titel: Hermes-Wartung
bereich: Werkzeuge
stand: 2026-10-05
tags: [hermes, update, gateway, wartung, sessions]
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
  Where TaskName -like '*ermes*'`). `Start-ScheduledTask` darauf.
- **Einen laufenden Gateway erkennt man nicht am Port und nicht am
  Prozessnamen.** Gemessen am 30.09.2026: Der Start bis `Gateway running
  with 13 platform(s)` dauert **rund fünf Minuten** (vorher lauscht nichts,
  `curl` auf 9900 liefert `000` und `Get-NetTCPConnection` findet nichts —
  alles kein Fehler). Und der Prozess läuft als
  `tools\python-3.14.7…\python.exe`, seine Kommandozeile enthält **nicht**
  `gateway run`; ein Filter darauf meldet fälschlich „kein Gateway".
  Verlässlich ist allein **`hermes gateway status`** (zeigt PID, Ports
  `9900`/`8644` und die Webhook-URLs je Profil) — und die Gegenprobe
  `hermes gateway run`, das bei laufendem Gateway mit „✓ The host gateway
  already serves profile 'default' … PID <n>“ antwortet statt zu starten.
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

## Wirkung (30.09.2026)

Das Update auf `f42f579cf8` enthielt
`fix(cli,desktop): hide every console-subsystem child spawn on Windows`.
Max meldet danach: **das Fenster-Flackern ist momentan nicht da.** Das ist
eine Momentaufnahme, kein Dauerbeweis — tritt es wieder auf, ist die erste
Frage, welche Sitzung gerade ein Konsolen-Kind startet, und der zweite Blick
gilt `HERMES_DESKTOP_CDP_PORT` plus `dev-cdp.ts`: ein **packaged** Build
öffnet nie einen CDP-Port, dort ist keine Live-DOM zu lesen.

## Stand

- 29.09.2026 abends: Lauf 1 holte 203 Commits, Lauf 2 holte 1841 Commits
  (mit `pyproject.toml` und `uv.lock`). Danach `HEAD ca705dbf7e`, Gateway und
  Dashboard auf `200`, `hermes --version` meldet „Up to date".
- Offen: 14 Orphan-Aliase (`<profil>.bat` für Profile, die nicht mehr
  existieren), ein lokaler `Dockerfile`-Unterschied im Checkout.


## Der Launcher: `pythonw.exe`, nicht `python.exe` (30.09.2026)

Der Launcher `gateway-service/Hermes_Gateway_2ef9d0b7.vbs` wird von
`hermes update` **neu geschrieben** und dabei auf
`tools\python-3.14.7...\python.exe` gesetzt. Das ist aus zwei Gruenden ein
Fehler:

1. `WScript.Shell.Run` mit Fensterstil 0 startet ein **Konsolen**programm gar
   nicht - kein Prozess, keine Fehlermeldung. Der Gateway kann so nie starten
   (gemessen, siehe Lektion 11 in `Lektionen/Windows-Umgebung.md`). Richtig ist
   `pythonw.exe`.
2. Nach jedem Update ist zu pruefen, ob das `tools`-Python seine
   Abhaengigkeiten noch hat:
   `tools\python-3.14.7...\python.exe -c "import pydantic_core, hermes_cli.main"`
   -> `ModuleNotFoundError` heisst, die Installation ist unvollstaendig.
   Nachziehen: `tools\python-3.14.7...\python.exe -m pip install -e hermes-agent`.

Beides zusammen hat am 30.09.2026 den Gateway stundenlang stillgelegt: er starb
an der Speichernot und konnte nicht neu starten, waehrend der Waechter alle
zwei Minuten erfolglos "Neustart ausgeloest" protokollierte.

**Nach jedem Update also zwei Handgriffe:** Launcher-Zeile auf `pythonw.exe`
pruefen, und die Import-Probe des `tools`-Python. Ein Gateway, der laeuft,
meldet sich in `Agenten/Hermes/gateway_state.json` mit `gateway_state:
running` und allen vier Plattformen `connected`.

## Sitzungsspeicher aufraeumen (05.10.2026)

**Regel: `hermes sessions archive` ist weich ausblenden, nicht loeschen.** Es
setzt nur `sessions.archived = 1` — die Sitzung ist aus den Listen weg, aber
voll rueckrufbar. Wer `archived` zaehlt, glaubt, es sei schon weg. Gemessen:
`state.db` 856 MB am 05.10.2026.

Vor dem Lauf ueber `file:…?mode=ro` messen (nie mit Schreibzugriff, waehrend
Agenten darauf laufen): Sessions gesamt/archiviert, Nachrichten in
archivierten, und die beiden Ausnahmen, die einen Prune **nicht** ueberleben:

- `hidden = 1` (Bot-Chat-Zeilen) — der Prune sieht nur `archived`
- `pinned = 1` — der Pin ist der dauerhafte Keep-Haken

Also **vorher** beide mit `hermes sessions pin <id>` sichern (der Pin gilt dann
auch fuer die automatische Archiv-Umlaufregel). `--include-pinned` wuerde sie
mitloeschen — das ist eine Entscheidung von Max, keine Voreinstelle des
Werkzeugs.

Sicherung ueber die **SQLite-Backup-API**, nicht `shutil.copy`: die Datei ist
offen (WAL), und ein Kopieren waehrend des Checkpoints liefert Zufallsdaten.

Merksatz: `sessions/request_dump_*.json` ist eine **andere** Sache (Debug-Dumps,
Groessenordnung zig MB) und wird von keinem Prune beruehrt — wer die Zahl an
`du -sh sessions` misst, misst die Dumps.
