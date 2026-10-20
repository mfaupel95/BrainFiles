# Desktop-Backend-Arbeitsverzeichnis

## Woher der Desktop sein cwd nimmt

Der Hermes-Desktop-Backend (`hermes serve --port 0`, vom Electron-Main gespawnt)
startet NICHT im `terminal.cwd` der config.yaml. Sein Arbeitsverzeichnis kommt
aus `resolveHermesCwd()` in `apps/desktop/dist/electron-main.mjs`, in dieser
Reihenfolge (erster existierender Kandidat gewinnt):

1. `readDefaultProjectDir()` — liest `%APPDATA%\Roaming\Hermes\project-dir.json`
   (Feld `dir`). **Das ist die erste und damit massgebliche Quelle.**
2. `HERMES_DESKTOP_CWD` (Umgebungsvariable)
3. `INIT_CWD` (nur ungepackt)
4. `process.cwd()` (nur ungepackt)
5. `SOURCE_REPO_ROOT` (nur ungepackt)
6. `app.getPath("home")`

`project-dir.json` ist die Datei, die die Desktop-App unter
Einstellungen → Projektordner schreibt. Steht dort ein falscher Ordner, laeuft
JEDE Desktop-Session dort — auch wenn `terminal.cwd` korrekt ist.

## Symptom

Desktop-Session startet im falschen Ordner (z. B. `BrainFiles\.worktrees`
statt `BrainFiles`), waehrend CLI/TUI/Gateway korrekt in `Agenten\Hermes`
starten. Der Desktop liest eine ANDERE Quelle als die uebrigen Wege.

## Fix

`%APPDATA%\Roaming\Hermes\project-dir.json` auf die gewuenschte Wurzel setzen:

```json
{ "dir": "C:\\Users\\faupe\\Documents\\BrainFiles" }
```

Wirkt beim naechsten Desktop-Start (Datei wird beim Boot gelesen). Kein
Gateway-Neustart noetig, kein `hermes config set`.

## Diagnose-Reihenfolge (nicht den Prozess-CWD auslesen)

Die Frage "in welchem Ordner laeuft der Desktop-Backend" beantwortet die
Konfigurationsdatei, die ihn bestimmt — nicht ein PEB-/Handle-Prozess-CWD-Probe.
Ein NtQueryInformationProcess-PEB-Read ist auf Windows fragil (Offsets,
Berechtigungen, 32/64-Bit) und kostet mehrere Fehlversuche. Stattdessen:

1. `project-dir.json` lesen (die erste Quelle von `resolveHermesCwd()`).
2. `HERMES_DESKTOP_CWD` in der Prozessumgebung pruefen.
3. `logs/desktop.log` nach `Starting Hermes backend via ...` — nennt den
   Backend-Pfad, nicht das cwd; als Beleg fuer den Backend-Ursprung nutzbar.

## Kanban-Worktrees sind davon unabhaengig

Kanban-Projekt-Worktrees gehen nach `<repo>/.worktrees/<task-id>`
(`hermes_cli/kanban_db.py`), unabhaengig vom Desktop-cwd. Ein falsches
`project-dir.json` verschiebt also NICHT die Worktrees — es verschiebt nur den
Startordner der Desktop-Sessions. Beides getrennt pruefen.

## Gateway-Gesundheit: served ≠ connected

`gateway_state.json` fuehrt `served_profiles` (alle Profile, die der Gateway
bedienen KANN) und `platforms` (die tatsaechlich verbundenen Kanaele). Ein
Profil in `served_profiles` OHNE `platforms`-Eintrag ist normal — es hat
schlicht keine Plattform-Credentials (kein Telegram-Token, kein a2a). Das ist
kein "Bot-Gateway down". Gesund heisst: alle `platforms.*.state == connected`
und der Gateway-Prozess lebt. SSH-Gateway separat: `sshd`-Dienst + Port 22
lauschend + Eintrag in `%APPDATA%\Roaming\Hermes\connections.json`.
