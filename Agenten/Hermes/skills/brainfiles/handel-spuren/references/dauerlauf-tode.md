# Der Dauerlauf ist gestorben — 143, Churn, spurlos

Wenn im `Agenten/Handel/dauerlauf*.log` eine Zeile `<spur> Rueckgabe 143` steht
oder alle Stufen gleichzeitig stehen, ist die Ursache fast immer eine der drei
hier. **Erst den Rueckgabecode lesen, dann suchen** — er ist ein Fingerabdruck.

## 1. Rueckgabecodes sind Fingerabdruecke (gemessen 30.09.2026)

| Weg | Rueckgabecode |
|---|---|
| `taskkill /T /F`, `taskkill /F` | 1 |
| `Stop-Process -Force` | 4294967295 |
| `os.kill(pid, 15)` | 15 |
| **MSYS-/Git-Bash `timeout N` oder Bash-Job-Abbau** | **143** (= 128+15) |

Folgen daraus:

- **143 = SIGTERM aus einem MSYS-/Cygwin-Kontext.** Windows-Werkzeuge erzeugen
  es nie. Ein Verdacht auf `taskkill /T /F` (z. B. `moondev_dauerlauf._stoppe`)
  ist damit erledigt, ohne ihn zu pruefen.
- **Der Sender sitzt in derselben Shell, die gestartet hat.** Eine zweite
  MSYS-Sitzung kann einen fremden Prozess nicht erreichen — `kill` aus einer
  anderen Bash meldet „LEBT NOCH“. Wer einen fremden Killer sucht, sucht
  vergeblich.
- **Der Aufruf ist belegbar:** `Agenten/Hermes/state.db`, Tabelle `messages`,
  Spalten `session_id, role, tool_name, tool_calls, timestamp` (read-only
  oeffnen: `file:...?mode=ro`). Der Aufruf-Text steht ROH in `tool_calls`; ihn
  mit `json.loads` auf `function.name == 'terminal'` und
  `json.loads(arguments)['command']` auspacken. Die Todeszeit liegt auf die
  Sekunde beim Ablauf des Zeitlimits (`timeout 60` -> 60 s nach dem Start).
- **Die Gegenseite befragen:** `Get-WinEvent` (System + Application) ueber das
  Todesfenster. Kommt kein Ereignis, kam der Tod von aussen; kommt Ereignis
  **2004** („virtueller Speicher unzureichend“), ist es Speicherdruck.

## 2. Die drei Todesarten

- **143** — ein Handstart mit `timeout N` wurde abgeschossen. Die gerade
  laufende Spur stirbt mit (ihr Rueckgabecode steht in der letzten Zeile), der
  Lauf selbst endet unmittelbar danach. **Das ist kein Dienstfehler.**
- **Sofortiger Tod ohne Protokollzeile** — Sperren-Churn: der Wrapper schreibt
  die PID des venv-Startprogramms (der ELTERNPROZESS des Interpreters), der Lauf
  sieht sie als fremden Lauf und endet mit „Es laeuft bereits ein Dauerlauf“.
  Behoben in `sperre.belegt()` (`os.getppid()` ausgenommen). Erkennungsmerkmal:
  im Waechter-Protokoll (`Agenten/Routinen/logs/handel-dauerlauf-letzter-lauf*.log`)
  haeufen sich „verwaiste Sperre“ im Minuten- bis Viertelstundentakt.
- **Spurlos** — kein letzter Eintrag, kein Rueckgabecode, dazu Ereignis 2004.
  Commit-/Speicherdruck; die Auslagerungsdatei bindet die Grenze und wirkt erst
  nach einem Neustart.

## 3. Die Regel fuer jede Sitzung

**Den Dauerlauf nie zur Ansicht mit `timeout N python dauerlauf.py` starten.**

- Ein Handstart nimmt die **echte** Sperre (`dauerlauf[.stufe].pid`) und
  schreibt ins **echte** `dauerlauf.log`.
- Wird er abgeschossen, bleibt eine `Rueckgabe 143`-Zeile stehen, die wie ein
  Diensttod aussieht, und die Sperre bleibt liegen — der naechste Waechter-Takt
  meldet dann „verwaiste Sperre“.
- `--trocken` hilft **nicht**: es heisst nur „nichts senden“, der Lauf nimmt
  trotzdem Sperre und Protokoll.
- Fuer einen Blick in einen Zyklus: `python <spur>/handeln.py --vorschau`
  (schreibt nicht, siehe `references/vorschau-schreibt-nicht.md`).
- Fuer den echten Neustart: `Routinen/handel-dauerlauf.ps1 -Risiko <stufe>`
  (bzw. die geplante Aufgabe) — der Wrapper prueft und schreibt die Sperre.

## 4. Die Wache

`Agenten/Hermes/scripts/dauerlauf-wache.py`, Hermes-Cron `dauerlauf-wache`
(15 min, `no_agent`, Telegram, leere Ausgabe = nichts senden). Je Stufe zwei
Zeugen (Sperrdatei mit Startzeit + Frische des Protokolls), Befunde `tot-143`,
`tot-code`, `tot-spurlos`, `haengt` (Protokoll aelter als 20 min = drei Zyklen),
`churn` (drei „verwaiste Sperre“ in einer Stunde). Sie **beendet und startet
nichts**; ein Befund wird hoechstens alle 6 h wiederholt.

Pruefen: `python Agenten/Hermes/scripts/dauerlauf-wache.py` (leer = gesund) und
`python -m unittest test_dauerlauf_wache -v` (aus `Agenten/Hermes/scripts`).

## 5. Der geplante Neustart: „Beenden und starten“ in EINEM Skript ist halb ausgefuehrt

Ein Neustart aller drei Stufen ist kein Kill, sondern zwei Schritte. Fuellt man
sie in einen Aufruf, kann der erste den zweiten verschlucken — ohne jede
Fehlermeldung, und mit einem Zustand, den der naechste Blick nicht verraet.

- **Ein Prozessfilter trifft die EIGENE Kommandozeile.** Wer per
  `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*dauerlauf.py*' }`
  sammelt und dann `Stop-Process` drauf losgeht, beendet auch die PowerShell, in
  der das Skript laeuft: ihre Kommandozeile enthaelt das Muster. Die Shell stirbt,
  die Zeilen danach (`Start-ScheduledTask`) laufen nie — Ergebnis: **alle drei
  Stufen unten**, die Sperredateien tragen die ALTEN PIDs, und der Aufruf sieht
  aus, als haette er funktioniert. Deshalb: eigene PID ausschliessen
  (`$_.ProcessId -ne $PID`), **zusaetzlich** auf den Prozessnamen filtern
  (`$_.Name -match 'python'`), und im Log niemals auf einen Filter ohne
  PID-Ausschluss setzen.
- **Nach dem Beenden NACHZAEHLEN, nicht die Absicht melden.** Prozesszahl je
  Stufe neu lesen und die drei Sperredateien ansehen. Eine Sperredatei mit
  einer PID, die es nicht mehr gibt, ist der Befund.
- **Start in einem EIGENEN Aufruf.** Das Beenden und das Starten gehoeren in
  getrennte Schritte: was der erste aufloest, darf den zweiten nicht mitnehmen.
- **Der Start gilt erst mit zwei Zeugen:** neue Prozesse mit einer Startzeit
  JENSEITS des Beendens, und eine frische Zykluszeile im `dauerlauf.log` der
  jeweiligen Stufe. Eine Aufgabe im Zustand `Ready` ist kein laufender Lauf.

Merksatz: **ein Neustart, der keine Fehlermeldung hinterlaesst, hat haeufig
nur die Haelfte gemacht.**