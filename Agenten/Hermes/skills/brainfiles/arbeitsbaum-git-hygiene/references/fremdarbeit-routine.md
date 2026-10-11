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
- **Viele Pfade: `git add` NICHT ueber die Kommandozeile.** Ab einigen hundert
  ruhenden Dateien (gemessen: 2044 Profil-Skill-Pfade) sprengt `git add -- $ruhend`
  die Windows-32k-Grenze und scheitert mit dem irrefuehrenden `Der Dateiname oder
  die Erweiterung ist zu lang` (WinError 206 - Prozess-Startfehler, nicht
  Pfadlaenge). Loesung in der Routine seit 11.10.2026: Pfade NUL-getrennt nach
  `.git\fremdarbeit-pfade.txt` schreiben, dann
  `git add --pathspec-from-file=<pfad> --pathspec-file-nul` (git >= 2.25).
  Gegenprobe in einem Wegwerf-Klon (2044 Pfade staged, Exit 0), nie am echten Baum.
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

## Von Hand committen, waehrend FREMDE Dateien vorgemerkt sind

Der Normalfall im Mehrsitzungsbetrieb: `git diff --cached --numstat` zeigt neben den
eigenen Pfaden fremde (eine Karten-Worker-Sitzung hat ihre Dateien schon `git add`-et).
Dann ist `git add <eigene>` + `git commit` OHNE Pfadangabe falsch - der Commit nimmt den
ganzen Index mit und die fremde Arbeit landet unter der eigenen Meldung.

Richtig ist derselbe Griff wie in der Routine, nur von Hand: eigener Index aus HEAD,
darauf nur die eigenen Pfade, committen.

```bash
cd <wurzel>
export GIT_INDEX_FILE="C:/Users/faupe/Documents/BrainFiles/.git/index.eigen-$$"
git read-tree HEAD
git add <eigene pfade>
git diff --cached --numstat      # LESEN: nur die eigenen Pfade
GIT_INDEX_FILE=$GIT_INDEX_FILE git commit -q -m "..."
rm -f "$GIT_INDEX_FILE"; unset GIT_INDEX_FILE
git status --porcelain | head  # die fremde Vormerkung steht unveraendert weiter da
```

- **`GIT_INDEX_FILE` braucht einen NATIVEN Pfad.** Mit dem MSYS-Pfad aus `$PWD`
  (`/c/Users/...`) bricht git als natives Programm ab: `fatal: Unable to create
  '…/index.eigen-<pid>.lock': No such file or directory` - der Index wird gar nicht
  erst angelegt, und der naechste `git add` schreibt in den normalen Index. Also
  `C:/Users/...` schreiben (die Wurzel ausgeben lassen, nicht zusammensetzen).
- **Die eigene Indexdatei danach loeschen** (`rm -f`), sonst bleibt sie im `.git`
  liegen und die naechste Sitzung sucht darin herum.
- **Den fremden Eintrag NICHT wegnehmen** (kein `git reset`, kein
  `git restore --staged`): die andere Sitzung committet gleich selbst, und ihr
  fehlender Index-Eintrag laesst ihre Datei im Baum liegen - der Commit der anderen
  Sitzung laeuft leer (`nothing to commit`) oder nimmt etwas anderes mit.
- Nach dem Commit bleiben die eigenen Pfade im NORMALEN Index vorgemerkt, jetzt aber
  inhaltsgleich mit HEAD - der fremde Eintrag ist damit der einzige Unterschied, und
  `git status --porcelain` zeigt genau ihn (`A ` in Spalte 1). Das ist die Gegenprobe,
  dass der Handgriff nichts Fremdes angefasst hat.

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

## Wache: den stillen Ausfall melden (`sperren-wache.py`)

Ein Nachweis ist keine Wache - niemand ruft ihn von selbst auf. Referenz:
`Agenten/Hermes/scripts/sperren-wache.py`, Cron `sperren-wache` (`da82ced995e1`,
alle 60 min, `no_agent`, `deliver: telegram`), Test `test_sperren_wache.py`.

Geprueft werden in EINEM Lauf drei Dinge (jedes einzeln war schon ein Ausfall):

| Pruefung | Wie | Warum nicht anders |
|---|---|---|
| `.git/index.lock` aelter als `FRIST_MIN` 10 | `REPOS` = BrainFiles + `Agenten/Handel/nautilus` | die Sperre ist das Symptom, nicht die Ursache |
| letzte ENDE-Zeile des Fremdarbeit-Logs enthaelt `uebersprungen` | `skip_zeile()` liest rueckwaerts bis zur ersten `ENDE`-Zeile | das Log wird bei JEDEM Lauf ueberschrieben - nur hier sichtbar |
| ZUWACHS der `index.lock.verwaist-*` | `_verwaist_gesamt` im Merker, gemeldet nur die Differenz | der Bestand allein ist kein Befund (sonst Alarm bei der Einrichtung) |

Bauart-Regeln, die aus Fehlern stammen:

- **Prozessabfrage filtern, nicht zaehlen.** `Get-CimInstance Win32_Process -Filter
  "Name='git.exe'"` mit `Where-Object { $_.CommandLine -notlike '*fsmonitor*' }`.
  `git fsmonitor--daemon` laeuft dauerhaft; die blosse Anzahl beweist keine parallele
  Sitzung. Ist die Zahl `0`, sagt die Meldung "kein echter git-Prozess" - bei
  `unbekannt` (Abfrage gescheitert) wird NICHTS behauptet.
- **Pfade zur LAUFZEIT aus dem Modul lesen, nicht als Default-Argument binden.**
  `def skip_zeile(log=FREMDARBEIT_LOG)` wertet den Pfad beim Import aus; ein Test kann
  ihn danach nicht mehr umbiegen, und die Tests laufen ins Leere (drei Fehlschlage in
  einem Lauf). Richtig: `def skip_zeile(log=None): log = FREMDARBEIT_LOG if log is None else log`.
- **Schluessel der Entdopplung ist der Text VOR dem Doppelpunkt** (Repo- bzw.
  Herkunftsname), nicht die ganze Zeile: "liegt seit 25 min" und "liegt seit 90 min"
  sind DIESELBE Feststellung, sonst waere eine liegende Sperre ein Alarm je Lauf.
  Wiederholung nach 6 h.
- **Den Merker immer schreiben**, auch im stillen Fall - sonst ist der Bestand beim
  naechsten Lauf wieder unbekannt und der Zuwachs nicht messbar.
- **`--frist 0` und `--alle` sind die Abnahmewerkzeuge:** `--frist 0` zeigt die
  Alarmrichtung an einer echten Sperre, `--alle` nennt den geprueften Umfang
  ("2 Repository(s) geprueft, 22 weggeraeumte Sperren im Bestand").
- **Die Wache raeumt nichts weg und committet nichts** - ein Waechter, der selbst
  eingreift, verdeckt den Befund. Test dafuer: `test_wache_raeumt_nichts_weg` prueft
  nach dem Lauf, dass die Sperre noch liegt.

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
