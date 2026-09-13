---
id: 20260830-routinen
title: 'Routinen'
tags: [betrieb]
created: 2026-08-25
updated: 2026-09-07
related: [20260830-wiederholbare-aufgaben, 20260831-marktscanner, 20260902-handelsregeln]
summary: 'Welche Abläufe ohne Aufforderung laufen, mit Zeitplan und Protokollort.'
---

# Routinen

Abläufe, die ohne Aufforderung passieren sollen. Eine Routine ist immer ein
vorhandener Skill plus ein Zeitplan.

## Geplant

| Wann | Was | Skill | Status |
|---|---|---|---|
| täglich 09:00 | DCA-Fälligkeit prüfen | `Handel/agent.py check` | **eingeplant** 23.08.2026 — `MaxHirn-DCA-Pruefung` |
| täglich 07:30 | Marktscanner (nur Papier) | `Handel/scanner/scan.py` + `handeln.py --papier` | **eingeplant** 02.09.2026 — `MaxHirn-Marktscanner` |
| täglich 07:45 | Kraken-Spur 3 (nur Papier) | `Handel/kraken/scan.py` + `handeln.py --papier` | **eingeplant** 02.09.2026 — `MaxHirn-Kraken-Spur3` |
| täglich 07:50 | XPERP-Spur 2 (nur Papier) | `Handel/xperp/handeln.py --papier` | **eingeplant** 07.09.2026 — `MaxHirn-XPERP-Spur2` |
| alle 30 Min | Dauerlauf-Wächter (Neustart nach Abschaltung) | `handel-dauerlauf.ps1` | **eingeplant** 07.09.2026 — `MaxHirn-Handel-Dauerlauf-Waechter` |
| sonntags 08:00 | Wachen-Abgleich Spur 1 **und** 3 (Bedingung 5) | `scanner/handeln.py --wachen` + `kraken/handeln.py --wachen` | **eingeplant** 02.09.2026 — `MaxHirn-Handel-Wachen` |
| täglich 20:00 | Sicherung nach `G:` | `sichern.ps1` | **eingeplant** 23.08.2026 — `MaxHirn-Sicherung` |
| täglich 21:00 | Zweitkopie nach `O:` → **Ziel ist J:**, siehe Abschnitt „Zweitkopie“ unten | `sichern-zweitkopie.ps1` | **eingeplant** 23.08.2026 — `MaxHirn-Zweitkopie` |
| täglich 22:00 | Posteingang einsortieren | `posteingang` | **eingeplant** 23.08.2026 — `MaxHirn-Posteingang` |
| täglich 20:00 | Zwischenstand der Textebene | `Routinen/zwischenstand.ps1` | **eingeplant** 25.08.2026 — `MaxHirn-Zwischenstand`. Lief bis 02.09.2026 stündlich, dann auf täglich 20:00 reduziert; zugleich zwei seit der Ordnertrennung (30.08.2026) fällige Fehler behoben — Repo-Wurzel eine Ebene zu flach, und `git add` brach an einem Fremd-Repo im Baum ab. |
| täglich 07:00 | Systemprüfung (Drift-Bericht) | `Routinen/systempruefung.ps1` | **eingeplant** 02.09.2026 — `MaxHirn-Systempruefung`. Sucht nach toten Junctions, doppelten Ollama-Stores, kaputten Pfaden; räumt Eindeutiges selbst auf, meldet den Rest. Bericht: `Routinen/logs/systempruefung-letzter-lauf.md`. Details in [[Systempruefung]]. |
| bei Systemstart | BrainFiles-Bus | `Agenten/Bus/bus.py` | **eingeplant** 10.09.2026 — `BrainFiles-Bus`, registriert über `Agenten/Routinen/bus.ps1`. Meldet Start und Ende aller geplanten Aufgaben, wertet deren Erfolg aus und sichert Fehler auf dem Handy. Ein toter Bus darf niemals einen Lauf abbrechen — alle Erzeuger schreiben lokal ins Journal zurück. |
| dauerhaft, Takt 15 min | Handels-Dauerlauf: Zyklus, Befehle vom Handy, Tagesbericht ab 08:00 | `Handel/dauerlauf.py` | **eingeplant** 07.09.2026 — `MaxHirn-Handel-Dauerlauf` (Anmeldung) + Wächter. `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` seit 07.09.2026 gesetzt, siehe Abschnitt „Der Telegram-Melder" |
| werktags 08:00 | Tagesbriefing | `tagesbriefing` | noch nicht eingeplant |
| werktags 07:15 | Marktüberblick (nur lesen) | `/marktbriefing` über `marktbriefing.ps1` | **Registrierbefehl bereit, Aufgabe noch nicht angelegt** — 07.09.2026, siehe Abschnitt „Marktbriefing" unten |
| freitags 17:00 | Wochenrückblick | `wochenrueckblick` | noch nicht eingeplant |
| bei Anmeldung (+2 Min) | OmniRoute-Router starten, falls er nicht läuft | `Routinen/omniroute-start.ps1` | **eingeplant** 13.09.2026 — `MaxHirn-OmniRoute`. Ohne den Router fällt der Hermes-Provider omniroute aus; jede Agenten-Delegation scheitert dann mit `Connection error`/HTTP 401 — das war nach jedem Neustart der Zustand. Startet nur, wenn Port 20128 frei ist (zwei Instanzen teilen sich `~/.omniroute/storage.sqlite`). Die alten Autostart-Einträge bleiben deaktiviert. |

Die eingeplanten laufen über die **Windows-Aufgabenplanung**, nicht über
`/schedule` — Begründung unten. Sie starten nicht das Skript direkt, sondern
einen Wrapper aus `Routinen/`. Seit dem 02.09.2026 sind es **neun**; die drei
Handels-Routinen kamen an diesem Tag dazu und sind je einmal aus der
Aufgabenplanung heraus gelaufen (Ergebniscode 0):

| Aufgabe | Wrapper | Protokoll |
|---|---|---|
| `MaxHirn-Sicherung` | `Routinen/sicherung.ps1` | `Routinen/logs/sicherung-letzter-lauf.log` |
| `MaxHirn-Zweitkopie` | `Routinen/zweitkopie.ps1` | `Routinen/logs/zweitkopie-letzter-lauf.log` |
| `MaxHirn-Posteingang` | `Routinen/posteingang.ps1` | `Routinen/logs/posteingang-letzter-lauf.log` |
| `MaxHirn-DCA-Pruefung` | `Routinen/dca-pruefung.ps1` | `Routinen/logs/dca-letzter-lauf.log` |
| `MaxHirn-Marktscanner` | `Routinen/marktscanner.ps1` | `Routinen/logs/marktscanner-letzter-lauf.log` |
| `MaxHirn-Kraken-Spur3` | `Routinen/kraken-scanner.ps1` | `Routinen/logs/kraken-scanner-letzter-lauf.log` |
| `MaxHirn-Handel-Wachen` | `Routinen/handel-wachen.ps1` | `Routinen/logs/handel-wachen-letzter-lauf.log` |
| `MaxHirn-Zwischenstand` | `Routinen/zwischenstand.ps1` | `Routinen/logs/zwischenstand-letzter-lauf.log` |
| `MaxHirn-Systempruefung` | `Routinen/systempruefung.ps1` (kein Wrapper, protokolliert selbst) | `Routinen/logs/systempruefung-letzter-lauf.md` + `systempruefung-JJJJ-MM-TT.log` |
| `BrainFiles-Bus` | `Agenten/Bus/bus.py` | `Agenten/Bus/journal/JJJJ-MM-TT.jsonl` |
| `MaxHirn-OmniRoute` | `Routinen/omniroute-start.ps1` | `Routinen/logs/omniroute-letzter-lauf.log` |

**Warum es zwei Sicherungen gibt:** `G:`, `H:` und `I:` sind dieselbe physische
Platte (Disk 2, siehe [[Hardware]]). Eine zweite Kopie dort hätte nichts
gewonnen. Die Zweitkopie liegt deshalb auf `O:` (Disk 1) und enthält den
unersetzlichen Teil ohne die Medienlast — 7,1 GB in 13.767 Dateien, gemessen
**8 Sekunden** (intern über NVMe). Videos, Musik, Software und Posteingang
(35,8 GB) bleiben draußen; sie stehen weiterhin in der Hauptsicherung auf `G:`.

## Die Zweitkopie: Ziel ist J:, nicht O:

**Korrektur des Ziels am 07.09.2026.** Der Kopf des Skripts
`sichern-zweitkopie.ps1` sagt „nach O:“, die Tabelle oben auch — **das
tatsächliche Ziel ist `J:\\MaxHirn-Zweitkopie`** (Zeile `$ziel = 'J:\\MaxHirn-Zweitkopie'`),
und das ist gewollt: J: ist die externe WD-My-Book-Sicherungsplatte, auf der
die Zweitkopie physisch getrennt von G: liegt. Die Notizen in
[[Dashboard]]/[[Routinen]], die „O:“ nennten, bezogen sich auf den früheren
Zustand. **O: ist seit dem 06.09.2026 durch die Archiv-Junctions belegt** und
steht für die Zweitkopie nicht mehr zur Verfügung.

Der Lauf vom 06.09.2026 21:07 (robocopy-Code 3, 635 „Extras“) war daher kein
Fehler: Das Skript lief zum ersten Mal gegen das J:-Ziel und räumte dort
(155 MB) Altbestand weg. Der Zielpfad in Code und Kommentar bleibt J:.

**Was das für die Routine bedeutet:**

| | |
|---|---|
| Ziel | `J:\\MaxHirn-Zweitkopie` (gewollt, bestätigt 07.09.2026) |
| Warum nicht O: | O: ist seit 06.09.2026 durch Archiv-Junctions belegt |
| Achtung | J: (WD My Book) hat 479 unkorrigierte Lesefehler — siehe [[Hardware]]. Die Zweitkopie liegt damit auf einer angeschlagenen Platte. |

## Die dritte Kopie: außer Haus, von Hand

`sichern-ausser-haus.ps1` → `E:\MaxHirn-AusserHaus` (Netac MobileDataStar,
Disk 4, 466 GB). **Sie steht bewusst nicht in der Tabelle oben und ist keine
geplante Aufgabe.** Eine Kopie, die dauerhaft am Rechner hängt, ist keine Kopie
außer Haus — genau der Fall, gegen den sie schützt, ist der Netzteilschaden,
der 2026 mehrere Platten gleichzeitig getötet hat.

Ablauf: SSD anstecken → Skript aufrufen → „Hardware sicher entfernen" →
außer Haus bringen. Sie nimmt **alles** mit (46,2 GB, 91.400 Dateien), nicht
nur den Kern; Platz ist genug.

**exFAT braucht `/FFT`.** `E:` ist exFAT formatiert, und exFAT speichert
Zeitstempel in 2-Sekunden-Schritten, NTFS in 100-Nanosekunden-Schritten. Ohne
`/FFT` gilt jede Datei bei jedem Lauf als verändert, und es würden jedes Mal
46 GB neu geschrieben statt nur der Unterschied. Für den laufenden Vault wäre
exFAT ungeeignet (siehe [[Portabilitaet]]), für eine reine Kopie ist es
unproblematisch — es läuft keine Datenbank darauf.

⚠️ **Auf der SSD liegen Klartext-Zugangsdaten** (`Wissen/Zugaenge.md`). Eine Platte außer Haus kann verloren gehen oder gestohlen
werden — anders als eine im Rechner. Ohne BitLocker To Go liest das jeder, der
sie findet. Siehe [[Zugaenge]] und [[Passwoerter-Quarantaene]].

`OKX_API.env` steht seit dem 12.09.2026 nicht mehr in dieser Aufzählung: die
Datei lag im Archiv-Posteingang und wurde bei jedem Lauf mitkopiert, dazu lag
eine zweite Fassung auf `J:`. Beide Streukkopien sind weg; die Datei liegt jetzt
in `Wissen/OKX_API.env` neben der Schlüsselablage. Dass sie damit auf derselben
Platte außer Haus steht, ist hingenommen: dieselben Schlüssel stehen in
`Zugaenge.md` ohnehin im Klartext.

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

## Marktscanner: warum die Routine nur Papier handelt

Der [[Marktscanner]] darf als einziger Agent im Rahmen fester Grenzen selbst
handeln (Ausnahme in [[Schutzregeln]]). Die **Routine** nutzt das nicht:
`marktscanner.ps1` ruft `handeln.py` ohne `--live` auf. Scharfhandel bleibt ein
bewusster Aufruf von Hand — dieselbe Regel wie bei der DCA-Prüfung, aus einem
Zeitplan heraus wird nie echtes Geld bewegt. Die Routine liefert also täglich
die Rangliste und einen Papier-Handelseintrag; mehr nicht.

**Eingeplant am 02.09.2026** als `MaxHirn-Marktscanner`, täglich 07:30. Zum
Wiederanlegen nach einem Umzug:

```powershell
$exe = "$env:USERPROFILE\Documents\BrainFiles\Agenten\Routinen\marktscanner.ps1"
schtasks /create /tn "MaxHirn-Marktscanner" /sc daily /st 07:30 `
  /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$exe`""
```

`schtasks` setzt **kein** „Starten, sobald möglich" — die drei Handels-Aufgaben
sind deshalb mit `Register-ScheduledTask` und
`New-ScheduledTaskSettingsSet -StartWhenAvailable` angelegt. Ohne das fällt ein
verpasster Termin nach einer [[Hardware]]-Abschaltung ersatzlos aus.

### Wachen-Abgleich: die fünf Bedingungen für unbeaufsichtigten Betrieb

[[Schutzregeln]] bindet den automatischen Handel seit dem 01.09.2026 an fünf
messbare Bedingungen. Vier davon prüft `handeln.py` bei **jedem** Lauf mit
(Freigabe, Drawdown-Ratsche, Herzschlag-Notausstieg, Journal-Spiegelung); die
fünfte — der rollierende Erwartungswert über die letzten 30 Runden — braucht
einen eigenen, selteneren Lauf, damit ein einzelner schlechter Tag die Spur
nicht sofort abschaltet. Dafür `handel-wachen.ps1`, **eingeplant am 02.09.2026**
als `MaxHirn-Handel-Wachen`, sonntags 08:00:

```powershell
$exe = "$env:USERPROFILE\Documents\BrainFiles\Agenten\Routinen\handel-wachen.ps1"
schtasks /create /tn "MaxHirn-Handel-Wachen" /sc weekly /d SUN /st 08:00 `
  /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$exe`""
```

Der Lauf legt `handel_erlaubt` **nie** auf `true` — er schließt die Sperre nur,
wenn der Erwartungswert negativ oder der Kill-Switch erreicht ist. Scharfschalten
bleibt ein Schritt von Hand. Der `xperp`-Bot hat kein Gegenstück: er führt nichts
aus und kein Journal, `bot.py wachen` zeigt nur die hinterlegten Grenzen.

Seit 02.09.2026 deckt derselbe Wrapper **beide** Live-Spuren ab: erst
`scanner/handeln.py --wachen`, dann `kraken/handeln.py --wachen`, jede mit
ihrer eigenen `wachen.json` und ihrer eigenen Währung. Ein zweiter Zeitplan ist
dafür nicht nötig.

### Der Dauerlauf — 24/7, aber nicht scharf

Angelegt am 03.09.2026 auf Max' Anweisung. `handel-dauerlauf.ps1` startet
`Handel/dauerlauf.py`: Befehle vom Handy sofort, ein Zyklus alle 15 Minuten,
Tagesbericht einmal täglich ab 08:00. **Er ersetzt die Tagesroutinen nicht**,
er legt sich darüber — `marktscanner.ps1` und `kraken-scanner.ps1` bleiben
unverändert.

**Auch dieser Zeitplan legt keinen Schalter um.** Ohne offenes Zeitfenster aus
[[Handelsregeln]] läuft jeder Zyklus als Papierhandel. Freigegeben wird per
Telegram, auf Anfrage, höchstens 24 Stunden.

Zwei Auslöser, weil die Kernel-Power-41-Abschaltungen aus [[Hardware]] den
Rechner ohne Vorwarnung mitnehmen: einer bei der Anmeldung, einer alle
30 Minuten als Wächter. Der zweite prüft `dauerlauf.pid` und endet sofort,
wenn schon einer läuft — zwei Dauerläufe auf demselben Telegram-Token nehmen
sich gegenseitig die Nachrichten weg (Telegram antwortet dem zweiten Abrufer
mit 409).

**Eingeplant am 07.09.2026** als `MaxHirn-Handel-Dauerlauf` (bei Anmeldung)
und `MaxHirn-Handel-Dauerlauf-Waechter` (alle 30 Minuten):

```powershell
$exe = "$env:USERPROFILE\Documents\BrainFiles\Agenten\Routinen\handel-dauerlauf.ps1"
schtasks /create /tn "MaxHirn-Handel-Dauerlauf" /sc onlogon `
  /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$exe`""
schtasks /create /tn "MaxHirn-Handel-Dauerlauf-Waechter" /sc minute /mo 30 `
  /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$exe`""
```

Der Wächter prüft `dauerlauf.pid` und endet sofort, wenn schon einer läuft;
nach einem Kernel-Power-41-Neustart ([[Hardware]]) startet er den Dauerlauf
wieder. Der Dauerlauf selbst läuft seit 06.09.2026 17:37 (PID 55000, Takt
15 min) und protokolliert in `Routinen/logs/handel-dauerlauf-letzter-lauf.log`.

### Der Telegram-Melder — eine Quelle, nicht zwei

Seit 07.09.2026 sind `TELEGRAM_TOKEN` und `TELEGRAM_CHAT_ID` als
Benutzervariablen gesetzt; ein Testversand an den Gruppenchat ist angekommen.
Damit sendet der Dauerlauf, was er ohnehin konnte.

**Der Tagesbericht braucht keine eigene Aufgabe.** `dauerlauf.py` prüft in
jedem Durchlauf, ob heute schon ein Bericht raus ist, und sendet ihn beim
ersten Durchlauf ab 8 Uhr selbst (`dauerlauf.py`, Abschnitt „Tagesbericht
faellig?"). Am 07.09.2026 wurde daneben eine zweite Aufgabe
`Tagesbericht-Telegram` angelegt, die dasselbe um 08:00 getan hätte — sie ist
noch am selben Tag wieder entfernt worden. **Zwei Quellen für denselben Bericht
sind kein doppelter Schutz, sondern zwei Stellen, an denen er falsch werden
kann.** Wer den Bericht ändern will, ändert `tagesbericht.py`.

**Ein Neustart nach dem Setzen ist nicht nötig — `melder.py` löst das selbst.**
Eine per `setx` oder `SetEnvironmentVariable(…, "User")` gesetzte Variable
erreicht laufende Prozesse nicht; `melder.py` liest deshalb bei **jedem**
Aufruf zuerst `os.environ` und fällt dann auf `HKCU:\Environment` zurück
(`_aus_registry`, denselben Umweg gehen `okxf.py`, `okx.py` und `kraken.py`).
Der laufende Prozess greift die neuen Werte also innerhalb eines Taktes von
selbst ab.

Das ist am 07.09.2026 im Protokoll zu sehen: Der Dauerlauf startete 23:24:11
mit „Melder nicht eingerichtet" — zu dem Zeitpunkt stimmte das —, und ab
23:29:54 nahm derselbe Prozess Befehle aus dem Chat entgegen, ohne dass er
neu gestartet worden wäre. **Die Startzeile ist eine Momentaufnahme, kein
Dauerzustand;** wer sie als „der Melder läuft nicht" liest, startet einen
Handelsprozess ohne Grund neu.

⚠️ **Der Bot-Token stand beim Einrichten im Klartext in Shell-Befehlen.** Am
07.09.2026 wurde er mehrfach direkt in Aufrufe geschrieben, statt einmal
gesetzt und danach nur noch als `$env:TELEGRAM_TOKEN` referenziert zu werden.
Nachgemessen am selben Tag, wo er tatsächlich gelandet ist:

| Ort | Vorkommen |
|---|---|
| PowerShell-History (`ConsoleHost_history.txt`) | **0** — PSReadLine schreibt nur interaktiv Getipptes, keine Tool-Aufrufe |
| `BrainFiles/` und damit die Sicherungen auf `G:` und `J:` | **0** |
| Sitzungsprotokoll unter `~/.claude/projects/*.jsonl` | 11, in einer Datei |

**Die Sicherungen sind sauber, und das ist der Punkt, auf den es ankommt.**
Ein Schlüssel, der in den Vault gerät, wandert mit jedem Lauf auf zwei weitere
Platten und ist dort praktisch nicht mehr einzufangen; ein Schlüssel im
Sitzungsprotokoll liegt in einer einzigen Datei im Benutzerprofil, die nicht
gesichert wird ([[KI-Ablagen-im-Benutzerordner]]).

Rotieren bleibt trotzdem der saubere Abschluss — `/revoke` bei BotFather,
danach `setx TELEGRAM_TOKEN`, kein Neustart nötig. Es kostet zehn Sekunden und
macht jede verbliebene Kopie wertlos. Der Schaden wäre ohnehin begrenzt: Mit
dem Token kann man in den Gruppenchat schreiben und mitlesen, aber
Handelsbefehle nimmt der Dauerlauf nur von `TELEGRAM_CHAT_ID` an, und Geld
bewegt keiner damit.

**Die Lehre ist nicht „Token nie anfassen", sondern: einmal setzen, danach nur
noch referenzieren.** `melder.py` liest ihn ohnehin selbst aus der Registry —
er hätte nie in einen Aufruf gehört.

### Kraken-Spur 3: derselbe Zuschnitt, andere Börse

Seit 02.09.2026 gibt es eine dritte bewachte Spur ([[Handelsregeln]]):
Kraken, Spot, nur Long, in EUR. Auch sie handelt aus dem Zeitplan heraus **nur
auf Papier** — `kraken-scanner.ps1` ruft `handeln.py` ohne `--live`, und selbst
mit `--live` blieben mehrere Sperren zu. **Eingeplant am 02.09.2026** als
`MaxHirn-Kraken-Spur3`, eine Viertelstunde nach dem Marktscanner, damit sich
die beiden Läufe nicht überschneiden:

```powershell
$exe = "$env:USERPROFILE\Documents\BrainFiles\Agenten\Routinen\kraken-scanner.ps1"
schtasks /create /tn "MaxHirn-Kraken-Spur3" /sc daily /st 07:45 `
  /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$exe`""
```

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

## Zwischenstand: warum stündlich und auf einem eigenen Branch

Die vier Sicherungen oben halten alle nur den **jetzigen** Stand, und Git hält
nur, was **committet** ist. Zwischen dem Schreiben einer Datei und ihrem Commit
liegt ein Fenster, in dem die Arbeit nirgends gesichert ist — bei mehreren
gleichzeitigen Sitzungen (Claude-Chats, Hermes) ist genau das das Risiko, siehe
[[Schutzregeln]], Abschnitt „Mehrere Sitzungen gleichzeitig".

`Routinen/zwischenstand.ps1` schließt dieses Fenster, ohne etwas anzufassen,
woran gerade jemand arbeitet:

- **Eigener Index** über `GIT_INDEX_FILE`. Eine Sitzung, die gerade selektiv
  `git add` gemacht hat, verliert ihre Vormerkung nicht.
- **Commit über `git commit-tree`** direkt auf den Branch `zwischenstand`.
  `HEAD`, `master` und der Arbeitsbaum werden nie angefasst.
- **Kein `checkout`, `reset`, `stash` oder `clean`.** Es wird ausschließlich
  geschrieben, nie verworfen.
- Ändert sich nichts, entsteht auch kein Commit.

Gemessen am ersten echten Lauf (25.08.2026): **4 Sekunden**, `HEAD`, `master`,
Arbeitsbaum und der normale Index (per SHA-256 verglichen) blieben unverändert.
Der Lauf sicherte 61 Zeilen an `Wissen/Hermes.md`, die eine andere Sitzung
uncommittet liegen hatte, sowie ein noch unversioniertes Skript.

**Autor der Commits ist `Routine Zwischenstand`**, nicht Max und kein Agent —
die Historie soll nicht behaupten, jemand hätte diese Arbeit getan.

Eine Datei zurückholen:

```
git log --oneline zwischenstand
git checkout <commit> -- <pfad>
```

Der Branch wächst mit jedem Lauf. Aufräumen, wenn er stört:
`git update-ref -d refs/heads/zwischenstand` — die Commits sind danach nicht
mehr erreichbar und verschwinden bei der nächsten Garbage Collection.

**Zugangsdaten sind nicht betroffen:** Die `.gitignore` ist eine Whitelist,
`Zugaenge.md`, `.env`, `.pem`, `.pfx`, `.p12`, `.kdbx` und `*_key.txt` bleiben
auch hier draußen. Geprüft am 25.08.2026 gegen den ersten Zwischenstand-Commit.

## Grenzen

- Eine Routine läuft nur, wenn der Rechner an ist. Für echten Dauerbetrieb
  bräuchte es einen Server — bewusst zurückgestellt.
- Routinen, die Mails senden oder öffentlich posten, immer als Entwurf enden
  lassen, nicht als Versand.
