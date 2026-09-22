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
