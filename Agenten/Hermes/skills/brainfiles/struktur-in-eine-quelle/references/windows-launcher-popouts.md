# Fenster hinterlassen: Windows-Terminal, cmd und Wurzel-Aufrufer

Gemessen am 30.09.2026 in `Agenten/Werkzeuge/repos-zentrale`. Der Anlass: acht
sichtbare Fenster, drei davon mit einem `scanner\.venv`-python, in einem lief noch
ein Bot-Chat.

## 1. Die Ursache

`wt.exe` oeffnet bei **jedem** Aufruf ein neues Fenster. Vier Stellen bauten den
Aufruf, drei in `aktionen.py` (`argv_terminal`, `argv_befehl_im_terminal`,
`argv_bot_auftrag`), eine **inline** in `fenster.py` (`bot_chat`) — die inline-
Stelle war die, die beim Suchen zuerst fehlte.

Suchen: `search_files` nach `wt.exe` ueber das ganze Werkzeug, nicht nur in der
Datei, die man schon kennt.

## 2. Der Fix

```python
WT_FENSTER = ("-w", "0")          # Tab im vorhandenen Fenster

def argv_terminal(pfad):
    return ["wt.exe", *WT_FENSTER, "-d", str(pfad)]
```

`-w <nummer|name|new|last>`; `0` = das vorhandene Fenster. Ohne vorhandenes
Fenster legt `wt` eines an — das ist richtig, nicht falsch.

**Gemessen, nicht geglaubt** (`scripts/fenster_zaehlen.ps1`): Fensterzahl 1 →
Aufruf → Fensterzahl 1. Die Doku zu zitieren haette gereicht, bis ein
Windows-Update die Bedeutung aendert; eine Zahl in der Sitzung nicht.

## 3. `/c` statt `/k` — und wohin die Ausgabe geht

`cmd /k` haelt den Tab offen (Ausgabe bleibt lesbar), `cmd /c` schliesst ihn
wieder (kein Popup, Ausgabe weg). Entscheidung Max: **`/c`**, aber die Ausgabe
muss ins Log:

```python
def _cmd_zeile(cmd, log=None):
    teile = [f'"{t}"' if " " in str(t) else str(t) for t in cmd]
    zeile = " ".join(teile)
    if log is not None:
        zeile += f' > "{log}" 2>&1'
    return zeile

def argv_befehl_im_terminal(pfad, cmd, log=None):
    return ["wt.exe", *WT_FENSTER, "-d", str(pfad), "cmd.exe", "/c", _cmd_zeile(cmd, log)]
```

`cmd` bekommt die Zeile als EIN Argument; `>` und `2>&1` versteht cmd selbst.
Tokens mit Leerzeichen werden gequotet (der Logpfad hat fast immer Leerzeichen).

Belegt mit einem echten Lauf: Tab lief, schloss sich, das Log enthielt
`hallo-welt-aus-dem-tab`.

## 4. Ein Bauplatz

Der Bot-Chat bekam eine eigene Funktion (`argv_bot_chat`), damit `fenster.py`
keinen `wt`-Aufruf mehr baut. Zwei Tests halten das fest:

```python
# Jede Zeile mit "wt.exe" muss die Konstante benutzen
if '"wt.exe"' in zeile:
    self.assertIn("*WT_FENSTER", zeile)

# Und die Oberflaeche baut keinen eigenen Aufruf
self.assertNotIn("wt.exe", (HIER / "fenster.py").read_text(encoding="utf-8"))
```

Das ist die Form, die einen **vierten** Bauplatz findet — nicht erst als neues
Fenster.

## 5. Wurzel-Aufrufer (.cmd)

Zwei Windows-Fallen, beide erlebt:

- **PowerShell liest einen relativen Programmpfad nicht.**
  `Agenten\Werkzeuge\...\python.exe x.py` endet mit *"Das Modul 'Agenten' konnte
  nicht geladen werden. Weitere Informationen finden Sie mit 'Import-Module
  Agenten'"* — das sieht wie ein fehlendes Programm aus, ist aber die
  Schreibweise. Richtig: `& ".\Agenten\..."` oder ein absoluter Pfad.
- **Der Nutzer startet in der Wurzel**, die Werkzeuge liegen in Unterordnern.

Deshalb ein Aufrufer in der Wurzel (Muster `omnitrade.cmd`, `bestand.cmd`):

```bat
@echo off
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%Agenten\Werkzeuge\repos-zentrale\.venv\Scripts\python.exe"
if not exist "%PY%" ( echo Fehlt: "%PY%" & exit /b 2 )
"%PY%" "%ROOT%Agenten\Werkzeuge\bestand.py" %*
exit /b %ERRORLEVEL%
```

- `%~dp0` macht ihn aus JEDEM Verzeichnis lauffaehig.
- `%*` reicht Argumente durch (`bestand.cmd --mit-fremd`).
- **CRLF** verwenden: ein mit LF geschriebenes `.cmd` bricht bei `goto`/Labels.
  Nach dem Schreiben pruefen: `b.count(b"\r\n")` muss der Zeilenzahl entsprechen.
- `.gitignore` braucht `!/<name>.cmd`.

## 6. Fenster zaehlen (das Messwerkzeug)

`scripts/fenster_zaehlen.ps1` zaehlt sichtbare Fenster mit Titel und Prozess —
vor dem Klick, nach dem Klick. Drei Fallen stecken darin, alle drei erlebt:

- **`GetWindowTextW` braucht `CharSet = CharSet.Unicode`.** Ohne den Zusatz
  schreibt die W-Funktion UTF-16, .NET marshallt aber ANSI und bricht am ersten
  Null-Byte ab: aus `Claude` wird `C`. Der **Zaehler stimmt dann**, nur die Titel
  sind Ein-Zeichen-Stummel — es sieht wie ein Anzeigefehler aus und ist einer.
- **Im Scriptblock-Delegate geht die Ausgabe verloren.** Was der
  `EnumWindows`-Callback ausgibt, kommt nicht beim Aufrufer an; nur
  Seiteneffekte (eine Liste, `$script:`-Variablen) ueberleben.
- **`Format-Table` rechnet mit der Konsolenbreite.** In einem
  nicht-interaktiven Host (Hermes-`terminal`) wurde die Titelspalte 1 Zeichen
  breit. Feste Formatierung mit `-f` statt `Format-Table`.

Zum Messen selbst: Fensterzahl VOR dem Klick, Klick, Fensterzahl NACH dem Klick.
Nur die Zahl vergleichen — `MainWindowHandle` und `EnumWindows` zaehlen bei
Windows Terminal unterschiedlich (ein Prozess, mehrere Fenster).

## 7. Was NICHT tun

- Keine fremden Fenster schliessen: in einem kann ein Bot-Chat oder eine Sitzung
  laufen. Ein Aufraeum-Knopf fuer Fenster ist bewusst nicht gebaut.
- Prozesse nie per Name beenden, nur per gemerkter PID.
- Die Fensterzahl nicht als "laeuft" deuten: `MainWindowHandle` zaehlt bei
  Windows Terminal anders als `EnumWindows` (ein Prozess, mehrere Fenster).
