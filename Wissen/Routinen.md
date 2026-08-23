# Routinen

Abläufe, die ohne Aufforderung passieren sollen. Eine Routine ist immer ein
vorhandener Skill plus ein Zeitplan.

## Geplant

| Wann | Was | Skill | Status |
|---|---|---|---|
| täglich 09:00 | DCA-Fälligkeit prüfen | `Handel/agent.py check` | **eingeplant** 23.08.2026 — `MaxHirn-DCA-Pruefung` |
| täglich 20:00 | Sicherung nach `G:` | `sichern.ps1` | **eingeplant** 23.08.2026 — `MaxHirn-Sicherung` |
| täglich 21:00 | Zweitkopie nach `O:` | `sichern-zweitkopie.ps1` | **eingeplant** 23.08.2026 — `MaxHirn-Zweitkopie` |
| täglich 22:00 | Posteingang einsortieren | `posteingang` | **eingeplant** 23.08.2026 — `MaxHirn-Posteingang` |
| werktags 08:00 | Tagesbriefing | `tagesbriefing` | noch nicht eingeplant |
| freitags 17:00 | Wochenrückblick | `wochenrueckblick` | noch nicht eingeplant |

Die drei eingeplanten laufen über die **Windows-Aufgabenplanung**, nicht über
`/schedule` — Begründung unten. Sie starten nicht das Skript direkt, sondern
einen Wrapper aus `Routinen/`:

| Aufgabe | Wrapper | Protokoll |
|---|---|---|
| `MaxHirn-Sicherung` | `Routinen/sicherung.ps1` | `Routinen/logs/sicherung-letzter-lauf.log` |
| `MaxHirn-Zweitkopie` | `Routinen/zweitkopie.ps1` | `Routinen/logs/zweitkopie-letzter-lauf.log` |
| `MaxHirn-Posteingang` | `Routinen/posteingang.ps1` | `Routinen/logs/posteingang-letzter-lauf.log` |
| `MaxHirn-DCA-Pruefung` | `Routinen/dca-pruefung.ps1` | `Routinen/logs/dca-letzter-lauf.log` |

**Warum es zwei Sicherungen gibt:** `G:`, `H:` und `I:` sind dieselbe physische
Platte (Disk 2, siehe [[Hardware]]). Eine zweite Kopie dort hätte nichts
gewonnen. Die Zweitkopie liegt deshalb auf `O:` (Disk 1) und enthält den
unersetzlichen Teil ohne die Medienlast — 7,1 GB in 13.767 Dateien, gemessen
**8 Sekunden** (intern über NVMe). Videos, Musik, Software und Posteingang
(35,8 GB) bleiben draußen; sie stehen weiterhin in der Hauptsicherung auf `G:`.

Die Wrapper gibt es aus drei Gründen:

1. **Eine geplante Aufgabe hat kein Fenster.** Ohne Protokoll bliebe ein
   Fehlschlag unbemerkt. Jedes Protokoll enthält genau den letzten Lauf.
2. **Robocopy wirft keine Ausnahme, es meldet über den Exitcode.** Der erste
   Entwurf schrieb „ENDE ok", während die Sicherung mit Code 11 gescheitert war
   (23.08.2026). Der Wrapper prüft jetzt `$LASTEXITCODE` und reicht ihn weiter,
   `sichern.ps1` beendet bei Code ≥ 8 selbst mit `exit 1`.
3. **Sie benutzen `$PSScriptRoot`**, keine absoluten Pfade — der Vault bleibt
   umzugsfähig.

Alle drei sind mit **„Starten, sobald möglich"** angelegt. Das ist wegen der
[[Hardware]]-Abschaltungen wichtig: Ohne diese Einstellung fällt ein verpasster
Termin ersatzlos aus.

**Warum das Protokoll vom Sicherungslauf ausgeschlossen ist:** `Routinen/logs`
liegt im Vault und damit im Sicherungspfad. Robocopy kann die gerade
beschriebene Protokolldatei nicht kopieren und beendet mit Code 11 — deshalb
steht `logs` in der `/XD`-Liste von `sichern.ps1`.

### Nach einem Umzug auf die SSD

Die Wrapper ziehen mit, die **Registrierung nicht** — sie enthält den absoluten
Pfad. Danach also einmal neu anlegen (`Register-ScheduledTask`, Zeiten wie oben).
Prüfen mit `Get-ScheduledTask -TaskName 'MaxHirn-*'`, entfernen mit
`Unregister-ScheduledTask -TaskName 'MaxHirn-Sicherung'`.

## DCA-Prüfung: warum nicht über `/schedule`

`/schedule` legt **Cloud-Agenten** an. Die laufen nicht auf diesem Rechner und
hätten daher weder Zugriff auf `Handel/plan.json` noch auf die
`onchainos`-Anmeldung im lokalen Schlüsselspeicher. Für diese Routine ist die
**Windows-Aufgabenplanung** der richtige Weg:

```powershell
$exe = "$env:USERPROFILE\Documents\BrainFiles\MaxHirn\Handel\.venv\Scripts\python.exe"
$arg = "$env:USERPROFILE\Documents\BrainFiles\MaxHirn\Handel\agent.py check"
schtasks /create /tn "DCA-Faelligkeit" /tr "$exe $arg" /sc daily /st 09:00
```

`check` schweigt, wenn nichts ansteht — eine Routine, die täglich „nichts zu tun"
meldet, wird nach einer Woche ignoriert.

**Die Routine löst nichts aus.** Sie meldet nur Fälligkeit; Quote holen,
vorlegen und ausführen bleibt ein bewusster Schritt von Hand. Das entspricht der
Regel in den globalen Arbeitsanweisungen: aus einem Zeitplan heraus wird nie
gehandelt.

## Einplanen

In einer interaktiven Claude-Code-Sitzung:

```
/schedule
```

Dort Zeitplan und Prompt angeben, z. B. Prompt `/tagesbriefing`, Zeitplan
werktags 08:00. Danach oben in der Tabelle den Status ändern.

## Warum Tagesbriefing und Wochenrückblick noch warten

Die beiden gehören zu einer anderen Sorte als die drei eingeplanten: Sie
**starten eine Claude-Sitzung ohne dich davor**, während Sicherung, Posteingang
und DCA-Prüfung nur ein Skript ausführen und ein Protokoll hinterlassen. Ein
Tagesbriefing um 8 Uhr produziert eine leere Seite, solange [[Profil]] Lücken
hat und Verbindungen aus [[Verbindungen]] nicht authentifiziert sind. Erst
füllen, dann automatisieren.

## Grenzen

- Eine Routine läuft nur, wenn der Rechner an ist. Für echten Dauerbetrieb
  bräuchte es einen Server — bewusst zurückgestellt.
- Routinen, die Mails senden oder öffentlich posten, immer als Entwurf enden
  lassen, nicht als Versand.
