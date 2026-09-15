# Abnahme am laufenden Bus

Befehle für den echten Rechner (Windows). Nützlich für die vier Punkte der Spec,
und immer dann, wenn ein Lauf gemeldet oder bezweifelt wird.

## Wo die Belege liegen

| Frage | Beleg |
|---|---|
| Läuft der Bus? | `Agenten/Bus/bus.json` → `port`; `Test-NetConnection 127.0.0.1 -Port <port>`; `Agenten/Bus/bus.pid` |
| Was ist gemeldet worden? | `Agenten/Bus/journal/JJJJ-MM-TT.jsonl`, gelesen über `journal.lesen()` |
| Hat der Bus eine Zeile gesehen? | ID in `Agenten/Bus/stand.json`, Feld `ids` |
| Lief die geplante Aufgabe? | `Get-ScheduledTaskInfo` → `LastRunTime`, `LastTaskResult` |

`LastTaskResult`: `0` = sauber beendet, `267009` (0x41301) = läuft gerade,
`3221225786` (0xC000013A) = von außen beendet (Kill, Herunterfahren, Absturz).

## 1. Alle Komponenten melden Start und Ende

```powershell
$p = 'Agenten\Bus\journal\' + (Get-Date -f 'yyyy-MM-dd') + '.jsonl'
$j = Get-Content $p | ForEach-Object { $_ | ConvertFrom-Json }
$j | Where-Object was -eq 'ende' | Group-Object wer | Sort-Object Name
($j | Where-Object { $_.was -eq 'ende' -and $_.code -ne 0 }).Count
```

Ein angefangener Tag ist kein abgenommener Tag — erst nach vollem Tageslauf
urteilen. Fehlt eine Routine, zuerst `Get-ScheduledTaskInfo` der zugehörigen
Aufgabe ansehen, dann erst den Bus verdächtigen (siehe Fehlercodes oben). Eine
Routine ohne eigene geplante Aufgabe meldet grundsätzlich nie.

## 2. Erzwungener Fehler, binnen einer Minute

```powershell
cd Agenten\Bus
python -c "import sys; sys.path.insert(0,'.'); import ereignis, journal; ereignis.melden(journal.neu('routine/probe','ende',code=9,dauer_s=1))"
```

Die Zeile steht im Journal. Ob der Bus sie verarbeitet hat, zeigt die Probe-ID in
`stand.json`; dass sie meldewürdig war, zeigt die Bewertung:

```powershell
python -c "import sys; sys.path.insert(0,'.'); import auffaellig, journal; j=[x for x in journal.lesen() if x['wer']=='routine/probe' and x['was']=='ende']; print(auffaellig.bewerte(j[-1], j, auffaellig.regeln()))"
```

Erwartet: `Ergebniscode 9`. Die Sichtprüfung auf dem Handy kann nur Max liefern.

## 3. Toter Bus bricht keinen Lauf ab

```powershell
Stop-ScheduledTask -TaskName 'BrainFiles-Bus'
Test-NetConnection 127.0.0.1 -Port 8787 -InformationLevel Quiet   # muss False sein
powershell -NoProfile -ExecutionPolicy Bypass -File Agenten\Routinen\wissen-index-pruefen.ps1
```

Beides muss zutreffen: Exit 0 der Routine **und** `start`/`ende` im Journal. Danach
den Bus starten und das Nachholen belegen — es darf keine Journal-ID mehr offen
sein:

```powershell
Start-ScheduledTask -TaskName 'BrainFiles-Bus'
cd Agenten\Bus
python -c "import sys, json; sys.path.insert(0,'.'); import journal; d=json.load(open('stand.json')); ids=set(d['ids']); print('ungelesen:', len([x for x in journal.lesen() if x['id'] not in ids]))"
```

## 4. Tagesmeldung gegen das Journal

```powershell
python -c "import sys; sys.path.insert(0,'.'); import auffaellig, sprecher; print(sprecher.Sprecher(None, auffaellig.regeln()).tagesmeldung())"
```

Der Melder darf `None` sein: `tagesmeldung()` liest nur das Journal. Die Summen
müssen den `ende`-Zeilen des Tages entsprechen.

## Fallen

- **Nichts Großes in die Ausgabe prügeln.** `stand.json` hält die IDs aller
gesehenen Zeilen und wird bei voller Ausgabe abgeschnitten; nur Zählwerte oder ein
`in`-Ergebnis drucken.
- **Aufgabenplanung braucht erhöhte Rechte**, sobald `-RunLevel Highest` im Spiel
ist: Das Registrierungsskript kann eine nicht erhöhte Sitzung nicht ausführen — Max
tut es einmal von Hand, danach wird nur lesend geprüft.
- **Der Bus lädt seine Module beim Start.** Nach Änderungen an `sprecher.py` oder
`auffaellig.py` neu starten, sonst prüft man den alten Stand. Ein Schwall alter
Meldungen direkt nach dem Start ist `nachholen()` bis zum Stunden-Deckel, kein
neuer Fehler.
