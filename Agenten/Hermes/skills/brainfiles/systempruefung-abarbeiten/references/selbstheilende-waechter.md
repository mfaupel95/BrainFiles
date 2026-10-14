# Selbstheilende Waechter in Block 9 — getestetes Rezept (14.10.2026, Commit 3f6b556f)

Ausgang: MaxHirn-Gateway-Waechter war deaktiviert (12.10. 17:43, nach einer
Neustart-Serie); Block 9 meldete das im Morgenbericht, reparierte aber nicht.
8 h spaeter kam der Gateway-Ausfall (13.10. 18:13-23:06, Code 75
Liveness-Watchdog) — ein deaktivierter Waechter ist schutzloser Betrieb, und
Report-only ist kein Schutz. Wichtig vor jedem Bauen: **im bestehenden Bericht
nachsehen, ob der Check existiert** — er existierte; es fehlte nur die
Reparatur. Nie behaupten "es gibt keinen Check".

## Das Muster in systempruefung.ps1, Block 9 (ASCII-Kommentare, Hauskonvention)

- `$kritischeWaechter` — Waechter, die NIE deaktiviert sein duerfen (Stand
  14.10.2026: Gateway-Waechter, Basis-Dauerlauf, Dauerlauf-Waechter). Kommentar
  daneben nennt den Anlass mit Datum.
- Im Zweig `if ($t.State -eq 'Disabled')` bleibt die Reihenfolge: erst
  `$gewolltDeaktiviert` (Allowlist, bleibt unangetastet), dann
  `elseif ($t.TaskName -in $kritischeWaechter)` (Selbstheilung), sonst
  `Entscheiden`. Ein gewollt deaktivierter Task wird NIE angefight.
- Selbstheilung: EAP lokal auf Continue (der Wrapper hat `'Stop'` —
  `& schtasks ... 2>&1` bricht sonst als NativeCommandError ab),
  `try { $r = & schtasks /Change /TN $t.TaskName /ENABLE 2>&1; if ($LASTEXITCODE -eq 0) { Getan ... } else { Entscheiden ... } } catch { Entscheiden } finally { $altEAP zurueck }`.
- Meldeform (im Log belegt):
  `[erledigt]  Kritischer Waechter <Name> war deaktiviert - wieder aktiviert (schtasks /Change /ENABLE).`

## Warum schtasks und nicht Enable-ScheduledTask

`Enable-ScheduledTask` antwortet mit 0x80070005 (Zugriff verweigert), auch
fuer einen Limited/faupe-Task (Principal RunLevel=Limited, LogonType
Interactive). `schtasks /Change /TN <name> /ENABLE` laeuft ohne Erhoehung
(Exit 0). Python/PowerShell-Autoheilung im user-Kontext MUSS schtasks.exe
nutzen; die Aufgabenplanung erlaubt das Aendern des Aktiv-Zustands, aber nicht
jede Cmdlet-API.

## Test ohne Risiko — der Weg mit Wegwerf-Task (GARANTIERT nichts kaputt)

1. **Berichte sichern** (der Testlauf ueberschreibt sie):
   `Copy-Item Agenten\Routinen\logs\systempruefung-letzter-lauf.md .bak-test -Force`
   und ebenso `systempruefung-<heute>.md` + `systempruefung-<heute>.log`.
2. **Wegwerf-Task anlegen und deaktivieren:**
   `schtasks /Create /TN 'MaxHirn-WaechterTest' /TR 'powershell.exe -NoProfile -Command exit 0' /SC ONCE /ST 23:59 /F`
   `schtasks /Change /TN 'MaxHirn-WaechterTest' /DISABLE`
3. **Testnamen temporaer in die Liste** (deutlich markiert):
   `$kritischeWaechter = @('MaxHirn-Gateway-Waechter', 'MaxHirn-WaechterTest')   # TEST-EINTRAG`
4. **Lauf im Hintergrund** (voll laeuft ~150 s):
   `powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/systempruefung.ps1 -NurPruefen > cache/scratch/log 2>&1`
   mit `background=true, notify=true` — nie im Vordergrund mit 400-s-Timeout warten.
5. **Im Log suchen:** die `[erledigt]`-Zeile von oben mit dem Testnamen.
6. **Rueckbau IN DIESER Reihenfolge:** TEST-EINTRAG entfernen →
   `schtasks /Delete /TN 'MaxHirn-WaechterTest' /F` → `.bak-test`-Dateien per
   Move-Item zurueckschieben → Scratch-Log loeschen → `git diff --numstat`
   muss wieder die gewollte Zeilenzahl zeigen (hier 23/1). Unabhaengig vom
   Rueckbau verifizieren, dass die Tagesberichte wieder die echten sind.

## Syntaxpruefung vor dem Lauf

```
powershell -NoProfile -Command "$f='Agenten/Routinen/systempruefung.ps1'; $errs=$null; [System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path $f), [ref]$null, [ref]$errs) | Out-Null; if ($errs.Count -eq 0) { 'Syntax OK' } else { $errs | ForEach-Object Message; exit 1 }"
```

## Commit

Eigener Index, weil parallel gestagte Dateien sonst mitgenommen werden
(`GIT_INDEX_FILE` → `git read-tree HEAD` → `git add <nur die .ps1>` →
`git commit -F <msg>` mit C:-Pfad), danach `unset GIT_INDEX_FILE` +
`git add <die .ps1>` im echten Index; `git status --porcelain -- <datei>` leer.

## Gemessene Fallen

- bash (MSYS) frisst Backslashes im `-File`-Pfad: `Agenten\Routinen\x.ps1`
  wird zu `AgentenRoutinenx.ps1` (Fehler "Argument ist nicht vorhanden").
  Immer mit Schraegstrichen aufrufen: `-File 'Agenten/Routinen/systempruefung.ps1'`.
- Der erste Vordergrund-Versuch (400-s-Timeout) lief in den Timeout, der
  Hintergrundlauf schaffte es in 150 s — Laufzeit haengt an der Maschinenlast
  (Block 5 wandert den Baum), also nie auf die Sekunde warten.
- Wegwerf-Task NIE vergessen zu loeschen: ein stehengebliebener
  `MaxHirn-WaechterTest` wuerde in jedem weiteren Bericht als Aufgabe
auchen und "entschieden" werden.
- `schtasks /Query` zeigt den deaktivierten Zustand lokalisiert als
  "Nicht zutreffend" — kein Fehler, nur die deutsche Schedule-Statusmeldung.

## Was in die kritische Liste gehoert (Auswahlregel)

- **Ein Neustart des Ziels darf KEINE Sicherheits-Gates umgehen.** Der
  Dauerlauf respektiert handel_erlaubt/Freigabefenster/Kill — ein Auto-Start
  stellt nur die Ueberwachung wieder her, das ist der Grund fuer die Aufnahme
  von Basis-Dauerlauf + -Waechter (14.10.2026).
- **Dokumentiert abgeschaltete Stufen bleiben in der Allowlist**
  (`$gewolltDeaktiviert`): ein gewolltes Abschalten wird nie angefight
  (Mittel-Waechter, Mittel-Stufe dokumentiert abgeschaltet).
- **Vor der Aufnahme Ist-Zustand messen** (Task-State, laeuft der Prozess,
  letzte Zyklen im Log) — die Aufnahme ist Versicherung, keine Reparatur.
- **Verifikation einer LISTEN-Erweiterung** (kein Mechanismus-Umbau): Syntax
  + voller Lauf, erwartet `0 erledigt` bei allen Ready — der Auto-Zweig feuert
  nicht = kein Churn, keine falschen Meldungen. Der Wegwerf-Task-Test ist nur
  fuer Umbauten am Mechanismus noetig.

## Uebertragbar auf

- Jeden Waechter, der NIE deaktiviert sein darf (Gateway, Dauerlauf-Waechter,
  Bus).
- Jede Aenderung an einem Pruef-Skript, das Scheduled Tasks anfasst — immer
  ueber den Wegwerf-Task-Weg testen, nie am echten Waechter.
