# Ruhende Fremdarbeit automatisch in die Hauptarbeit holen

Rezept fuer den Fall: Hintergrund- und Parallel-Sitzungen schreiben in denselben
Arbeitsbaum, committen aber nicht. Ihre Arbeit steht als `M`/`??` im Baum und bleibt
dort - sichtbar, aber nie in `master`. Der Zwischenstand sichert sie nur auf einen
eigenen Branch; diese Routine holt sie ein zweites Mal ab und schreibt sie nach
`master`. Referenz-Implementierung: `Agenten/Routinen/fremdarbeit-einziehen.ps1`
(Aufgabe `MaxHirn-Fremdarbeit-Einziehen`, taeglich 20:40, also NACH dem Zwischenstand
um 20:00).

## Bauart (das ist der Kern)

- **Eigener Index, damit der Staging-Bereich anderer Sitzungen unberuehrt bleibt:**
  `$env:GIT_INDEX_FILE = .git\fremdarbeit.index` -> `git read-tree <tip>` ->
  `git add -- <pfade>` -> `git write-tree`.
- **Commit ohne HEAD/Arbeitsbaum anzufassen:** `git commit-tree $baum -p $tip -F <msgdatei>`,
  Autor per `GIT_AUTHOR_NAME/EMAIL` = `Andere Sitzung <fremd@local>`,
  Committer = `Routine <routine@localhost>` (die Historie soll nicht behaupten,
  jemand haette die Arbeit getan).
- **`git update-ref refs/heads/master $neu $tip` MIT Alt-Wert.** Das ist der
  Sicherheitsgurt: hat eine andere Sitzung `master` waehrenddessen bewegt, schlaegt
  der Schreibvorgang fehl, statt ihre Commits zu ueberschreiben. Der Lauf endet dann
  als "uebersprungen", nicht als Fehler.
- **Kein `checkout`, `reset`, `stash`, `clean`, kein `merge`.** Es wird nur
  geschrieben. Der Arbeitsbaum ist danach unveraendert (Gegenprobe: `git status`).
- **Nur `master`.** Steht HEAD auf einem anderen Zweig, wird der Lauf uebersprungen.
- **Sperre respektieren:** liegt `.git/index.lock`, wird uebersprungen statt gewartet
  (der Index-Nachtrag braucht sie spaeter und weicht ihr mit Wiederholungen aus).

## Ruhekriterium

- Schwelle 30 Minuten ohne Aenderung (dieselbe wie `arbeitsbaum-pruefen.ps1` und die
  Schutzregeln). Was juenger ist, gehoert einer Sitzung, die gerade schreibt.
- Ein Pfad in einem eingebetteten Repo (`Werkstatt/Repos/*`, `Agenten/Handel/nautilus`)
  wird uebersprungen - dort fuehrt ein anderes `.git` die Versionierung.
- Eine GELOESCHTE Datei hat keine mtime: Ersatzwahrheit ist `LastWriteTime` ihres
  Elternordners (Windows schreibt sie beim Loeschen fort).
- Ignorierte Pfade tauchen in `git status --porcelain` gar nicht auf - die
  `.gitignore`-Whitelist ist damit die zweite Schranke (Zugaenge.md, `.env` usw.).

## Pflicht danach: den normalen Index angleichen

Der eigene Index hat nur die uebernommenen Pfade angefasst; der normale Index kennt den
neuen HEAD nicht. Fuer eine NEU aufgenommene Datei fehlt ihm der Eintrag (`D ` + `??`),
fuer eine geaenderte steht dort der alte Inhalt (`M `) - und ein `git commit` einer
anderen Sitzung ohne Pfadangabe wuerde das zurueckdrehen.

```
Remove-Item Env:\GIT_INDEX_FILE          # sonst schreibt update-index in den falschen Index
foreach ($pfad in $ruhend) {
    $idx = (git ls-files -s -- $pfad)                       # Index-Blob (oder nichts)
    $alt = (git ls-tree $tip -- $pfad)                      # Stand VOR dem Commit
    $neu = (git ls-tree $neuSha -- $pfad)
    if ($idxBlob -ne $altBlob) { continue }                 # fremde Vormerkung: nicht anfassen
    if ($neuBlob) { git update-index --add --cacheinfo "<mode>,$neuBlob,$pfad" }
    elseif ($idxBlob) { git update-index --force-remove -- $pfad }
}
```

Dieselbe Reparatur zu Beginn des NAECHSTEN Laufs ueber die Pfade der letzten eigenen
Uebernahme-Commits (`git log -5 --author=fremd@local --name-only --format=`) - dann
heilt auch ein Lauf, der ohne den Nachtrag beendet wurde. Idempotent.

`git update-index` braucht `.git/index.lock`: in einer Schleife wiederholen
(12 x 5 s), damit die Sperre einer anderen Sitzung nicht den ganzen Lauf kostet.

## Der stille Ausfall: „uebersprungen" heisst nicht „erledigt"

Beide Ausgaenge der Routine, die NICHT uebernehmen, enden mit **Exitcode 0** und
`ENDE uebersprungen` - `Get-ScheduledTaskInfo` zeigt `LastTaskResult: 0`, also Erfolg:

| Skip-Grund | Zeile im Log |
|---|---|
| falscher Arbeitszweig | `ENDE uebersprungen - Arbeitszweig ist '<x>', nicht master` |
| liegende Sperre | `ENDE uebersprungen - .git\index.lock liegt vor (andere Sitzung committet gerade)` |

Die Zweig-Pruefung steht VOR der Sperrenpruefung - beim Auswerten die Zeile lesen, nicht
den Exitcode. Gemessen 24.09.2026: Skip am 23.09. 20:40 wegen einer verwaisten Sperre,
danach 44 Dateien bis zu 44 h im Baum; ein Handlauf holte 51 ruhende Dateien in 64 s
(Commit `aae26a9`, gepusht).

**Das Log wird bei jedem Lauf ueberschrieben** (`"=== Lauf …" | Set-Content $log`), es
ist also ein Einzellauf-Protokoll, keine Historie. Den Skip-Grund sofort lesen; fuer die
Vergangenheit nur `git log --oneline --author=fremd@local` (was wurde wann geholt) und der
Tagesbericht („N uncommittete Datei(en) aelter als 1 h") heranziehen.

### Von Hand nachziehen (Ablauf)

1. Sperre pruefen: Groesse, Alter, `Get-CimInstance Win32_Process -Filter "Name='git.exe'"`
   ohne `fsmonitor` filtern. 0 Byte + kein echter Prozess = verwaist ->
   `[System.IO.File]::Move($quell, $ziel)` (ZWEI Argumente), Zielname mit Zeitstempel,
   danach `Test-Path` auf BEIDE Pfade.
2. `powershell -NoProfile -ExecutionPolicy Bypass -File Agenten\Routinen\fremdarbeit-einziehen.ps1 -Testlauf`
   -> zeigt `TESTLAUF - es wuerde uebernommen (n)` und `IN ARBEIT - bleibt liegen (m)`.
3. Derselbe Aufruf OHNE `-Testlauf` (`-NichtPushen` nur, wenn der Push bewusst ausbleibt).
4. Belege: `git show --stat <sha>` (Autor `Andere Sitzung <fremd@local>`, Dateizahl),
   `git log --oneline origin/master..HEAD` (leer = gepusht), `git status --porcelain`.

### Was nach dem Lauf ABSICHTLICH stehen bleibt

- **Frische Dateien** (< Schwelle, Standard 30 min): gehoeren einer Sitzung, die gerade
  schreibt. Im Testlauf als `IN ARBEIT` ausgewiesen.
- **Fremd vorgemerkte Index-Eintraege** (`A `/`M ` in `git status --porcelain`): die
  Routine meldet `(fremd vorgemerkt bleibt: …)` - eine frische Vormerkung einer anderen
  Sitzung wird nie ueberschrieben.
- **Loeschungen mit frischem Elternordner** und alles unter `Werkstatt/`.

Ein Lauf ist also NICHT daran zu messen, dass der Baum leer ist, sondern dass die eigenen
uebernommenen Pfade aus `git status` verschwunden sind.

### Die Zahl ist eine Momentaufnahme

Gemessen am 24.09.2026: 34 -> 44 -> 51 ruhende Dateien in etwa 30 Minuten, waehrend eine
parallele Sitzung schrieb. Die Testlauf-Liste kann beim echten Lauf schon ueberholt sein -
richtig ist, dass die Routine den Stand SELBST unmittelbar vor dem Commit frisch liest
(`git status --porcelain` im Skript), und im Bericht die Zahl aus dem Commit
(`git show --stat`), nicht die aus dem Testlauf.

## Nachweis - zweistufig, nie nur am echten Baum

1. **Funktionstest in einem Temp-Repo** (`Agenten/Bus/tests/test_fremdarbeit_einziehen.py`):
   Kopie der Routine in `<tmp>/Agenten/Routinen/` und `Ereignis.ps1` nach
   `<tmp>/Agenten/Bus/` (die Routine sucht `$wurzel` zwei Ebenen ueber `$PSScriptRoot`
   und bindet den Bus dort ein - so laeuft das ORIGINAL ohne Testschalter), Basis-Commit,
   bare Origin, dann die Lagen einzeln: geaenderte, neue, geloeschte und bereits
   vorgemerkte Datei uebernehmen; eine FRISCHE muss liegen bleiben; eine Loeschung mit
   frischem Elternordner muss liegen bleiben; `-Testlauf` schreibt nichts; vorhandene
   `.git/index.lock` haelt den Lauf an; Phantom-Eintrag wird ohne neuen Commit
   nachgezogen. Assertions mit `git log/show/status/ls-files` und dem bare-Origin -
   nicht gegen die Ausgabe des Skripts.
2. **Ein Lauf am echten Baum** mit `-Testlauf` (zeigt die Einteilung ruhend/in Arbeit)
   und danach ein echter Lauf; Belege: `git show --stat HEAD`, `git status --porcelain`
   ohne `D `/`??`-Paar, `git diff --cached` leer fuer die uebernommenen Pfade.

## Aufgabe registrieren

Registrierer `Routinen/fremdarbeit-einziehen-aufgabe.ps1` (Hausname `<name>-aufgabe.ps1`),
der die XML einer bewaehrten Aufgabe spiegelt (`Export-ScheduledTask -TaskName
'MaxHirn-Zwischenstand'` -> Aktionsargumente und `<StartBoundary>` ersetzen ->
`Register-ScheduledTask -TaskName <neu> -Xml $xml -Force`). Der Registrierer enthaelt
`Register-ScheduledTask` und kein `Melde-Start`, deshalb ueberspringt
`test_anbindung_routinen.py` ihn automatisch (kein `einmalig-`-Praefix noetig).
Abnahme ueber die Aufgabenplanung: `Start-ScheduledTask`, dann muss
`Get-ScheduledTaskInfo` `LastTaskResult: 0` zeigen und `NextRunTime` die erwartete Zeit.
