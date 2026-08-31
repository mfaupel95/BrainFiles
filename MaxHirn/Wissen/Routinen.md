---
id: 20260830-routinen
title: 'Routinen'
tags: [betrieb]
created: 2026-08-25
updated: 2026-08-25
related: [20260830-wiederholbare-aufgaben]
summary: 'Welche Abläufe ohne Aufforderung laufen, mit Zeitplan und Protokollort.'
---

# Routinen

Abläufe, die ohne Aufforderung passieren sollen. Eine Routine ist immer ein
vorhandener Skill plus ein Zeitplan.

## Geplant

| Wann | Was | Skill | Status |
|---|---|---|---|
| täglich 09:00 | DCA-Fälligkeit prüfen | `Handel/agent.py check` | **eingeplant** 23.08.2026 — `MaxHirn-DCA-Pruefung` |
| täglich 07:30 | Marktscanner (nur Papier) | `Handel/scanner/scan.py` + `handeln.py --papier` | **noch nicht eingeplant** — Wrapper `Routinen/marktscanner.ps1` steht |
| täglich 20:00 | Sicherung nach `G:` | `sichern.ps1` | **eingeplant** 23.08.2026 — `MaxHirn-Sicherung` |
| täglich 21:00 | Zweitkopie nach `O:` | `sichern-zweitkopie.ps1` | **eingeplant** 23.08.2026 — `MaxHirn-Zweitkopie` |
| täglich 22:00 | Posteingang einsortieren | `posteingang` | **eingeplant** 23.08.2026 — `MaxHirn-Posteingang` |
| stündlich | Zwischenstand der Textebene | `Routinen/zwischenstand.ps1` | **eingeplant** 25.08.2026 — `MaxHirn-Zwischenstand` |
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
| (noch offen) Marktscanner | `Routinen/marktscanner.ps1` | `Routinen/logs/marktscanner-letzter-lauf.log` |
| `MaxHirn-Zwischenstand` | `Routinen/zwischenstand.ps1` | `Routinen/logs/zwischenstand-letzter-lauf.log` |

**Warum es zwei Sicherungen gibt:** `G:`, `H:` und `I:` sind dieselbe physische
Platte (Disk 2, siehe [[Hardware]]). Eine zweite Kopie dort hätte nichts
gewonnen. Die Zweitkopie liegt deshalb auf `O:` (Disk 1) und enthält den
unersetzlichen Teil ohne die Medienlast — 7,1 GB in 13.767 Dateien, gemessen
**8 Sekunden** (intern über NVMe). Videos, Musik, Software und Posteingang
(35,8 GB) bleiben draußen; sie stehen weiterhin in der Hauptsicherung auf `G:`.

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

⚠️ **Auf der SSD liegen Klartext-Zugangsdaten** (`Wissen/Zugaenge.md`,
`OKX_API.env`). Eine Platte außer Haus kann verloren gehen oder gestohlen
werden — anders als eine im Rechner. Ohne BitLocker To Go liest das jeder, der
sie findet. Siehe [[Zugaenge]] und [[Passwoerter-Quarantaene]].

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

Einplanen (wenn gewünscht), interaktiv per Aufgabenplanung:

```powershell
$exe = "$env:USERPROFILE\Documents\BrainFiles\Agenten\Routinen\marktscanner.ps1"
schtasks /create /tn "MaxHirn-Marktscanner" /sc daily /st 07:30 `
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
