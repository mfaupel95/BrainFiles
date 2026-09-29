# Windows: Kindprozesse eines Treibers richtig starten

Wenn ein Haus-Treiber einen Fremd-Agenten per `subprocess` startet, entscheidet
sich an vier Stellen, ob der Agent laeuft oder stumm scheitert. Alle vier sind
unabhaengig vom jeweiligen Repo.

## 1. Interpreter: nie `sys.executable` durchreichen

`sys.executable` ist der Interpreter des TREIBERS (z.B. ein Haus-venv), nicht der
des Fremd-Repos — und dem fehlen dessen Pakete (`ModuleNotFoundError: requests`,
`pandas`, `openai`). Den Pfad zum Repo-eigenen `.venv/Scripts/python.exe` FEST im
Treiber eintragen.

Dieselbe Regel gilt fuer relative Programmpfade: Windows loest `argv[0]` gegen das
Arbeitsverzeichnis des AUFRUFERS auf, nicht gegen das `cwd` des Kindes. Vor dem
Start jeden relativen Programmpfad gegen `cwd` aufloesen und eine ABSOLUTE Liste
uebergeben.

## 2. `.env`: selbst lesen statt `load_dotenv()` im Kind

`load_dotenv()` ohne Pfad sucht per `find_dotenv()` AUFWAERTS ab dem Modulordner
(z.B. `src/agents/`) und findet dabei eine NAEHERE, fremde `.env` — die eigenen
Zugangsdaten eines anderen Teilsystems im selben Repo — statt der beabsichtigten
Root-`.env`. Die gesuchte Variable bleibt leer, ohne Fehlermeldung beim Laden
selbst, und der Agent scheitert erst spaeter an ganz anderer Stelle.

Ein Treiber darf sich darauf nicht verlassen: die Root-`.env` selbst lesen und
die benoetigten Variablen VOR dem Start in die Subprozess-Umgebung setzen.
`load_dotenv()` ueberschreibt bereits gesetzte Variablen per Vorgabe nicht
(`override=False`), die Vorgabe gewinnt also.

## 3. Kodierung: `PYTHONIOENCODING=utf-8`

Ueber `subprocess.PIPE` (kein echtes Konsolenfenster) faellt Python auf die
Windows-Codepage zurueck und stirbt am ersten Emoji oder Sonderzeichen
(`UnicodeEncodeError`). Gilt genauso, wenn ein PYTHON-Treiber den Agenten startet,
nicht nur bei einem PowerShell-Wrapper. `PYTHONIOENCODING=utf-8` in die
Subprozess-Umgebung setzen, bevor der Kindprozess startet.

## 4. Fenster: `creationflags=CREATE_NO_WINDOW`

Eine Konsolen-CLI aus einem Hintergrund-/Agent-Prozess oeffnet auf Windows bei
JEDEM Aufruf ein sichtbares Fenster, wenn `subprocess.run` kein
`creationflags=subprocess.CREATE_NO_WINDOW` setzt. `-WindowStyle Hidden` im
PowerShell-Wrapper versteckt nur die eigene Shell, NICHT die Kinder — das Flag
gehoert in den subprocess-Call selbst:

```python
creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
```

## 5. Beenden: immer der ganze Baum

`npm run dev` startet `next dev` als KIND. Ein Kill auf die Eltern-PID laesst es
als Waise stehen, und die haelt den Port besetzt (Symptom: "Port belegt" beim
naechsten Start, obwohl der Treiber beendet wurde). `taskkill /T /F /PID <pid>`
beendet den Baum — danach die Prozesszahl NACHZAEHLEN, statt dem Exitcode zu
glauben.

Vor dem Beenden eines Live-Prozesses `freigabe_fenster.json` pruefen und nur per
PID beenden, nie per Prozessname.

## Nach einem Fix: laeuft der ALTE Code weiter?

Ein schon laufender Hintergrundprozess nutzt den alten Code weiter. Vor der
Erfolgsmeldung pruefen, wann der Treiberprozess gestartet wurde. Uebernommen wird
der Fix nur durch einen Neustart (bei Live-Trading-Prozessen vorher Rueckfrage)
oder durch die naechste getrennte Aufgabe — Scheduled Task oder Cron startet
frisch. Bei Spur-Skripten, die der Dauerlauf JEDEN Zyklus als Kindprozess startet,
wirkt die Aenderung dagegen sofort; nur der Treiber selbst braucht einen Neustart.
