---
name: disk-space-triage
category: software-development
description: Find what fills a critically-low disk on Windows.
version: 1.0.0
author: Hermes Agent
license: proprietary
metadata:
  hermes:
    tags: [disk, storage, docker, windows]
    related_skills: [systematic-debugging]
---

# Disk-Space-Triage (Windows, grosse Laufwerke, Docker)

## When to Use

Ein Laufwerk ist kritisch voll (z. B. `O:` unter der Warnschwelle) und du musst
den Verursacher finden — aus einer Systemdiagnose, einer Wache oder einer
Fehlermeldung. Ziel: den **aktiven Schreiber** identifizieren, nicht nur den
groessten Ordner — ein statischer grosser Ordner ist nicht das, was die Platte
jetzt auffrisst.

## Erst die Messung stabilisieren

Eine einzelne Lesezeit kann ein **transienter Spike** sein (grosse Temp-/Pagefile-
Schreibaktion, ein Build, ein Download), kein Dauerzustand. Ein Lauf meldet
`1,8 GB frei`, Minuten spaeter sind es `78 GB` — die 1,8 waren der Spike. Vor jeder
Aussage "Platte voll" zweimal messen (`Get-PSDrive <L> | Select Free/Used`) und den
Trend ueber ein paar Minuten nehmen, nicht einen Moment.

## `du` laeuft auf riesigen Laufwerken in den Timeout

`du -sh` ueber ein 500+ GB Laufwerk (oder ueber Junctions auf `O:`) haengt >120 s.
Nicht darauf warten. Stattdessen PowerShell pro Top-Level-Ordner:

```powershell
Get-ChildItem 'O:\' -Directory | ForEach-Object {
  $s = (Get-ChildItem $_.FullName -Recurse -File -Force -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
  '{0,-28} {1,8:N1} GB' -f $_.Name, ($s/1GB)
}
```

## Den AKTIVEN Schreiber finden (nicht den groessten Ordner)

Der groesste Ordner ist oft statisch (eine alte Kopie). Was die Platte JETZT füllt,
ist die Datei, die in den letzten ~2 h geschrieben wurde und gross ist:

```powershell
$cut = (Get-Date).AddHours(-2)
Get-ChildItem 'O:\' -Recurse -File -Force -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -gt $cut -and $_.FullName -notmatch 'pagefile|System Volume' } |
  Sort-Object Length -Descending | Select-Object -First 15 |
  ForEach-Object { '{0}  {1,9:N1} MB  {2}' -f $_.LastWriteTime.ToString('MM-dd HH:mm'), ($_.Length/1MB), $_.FullName }
```

Die groesste frisch geschriebene Datei ist der Verursacher. Ein statischer grosser
Ordner (z. B. eine `*-Zweitkopie` von gestern) ist NICHT der aktive Schreiber —
separat als Freigabe-Kandidat melden, nicht als Ursache.

## PowerShell vom Hermes-Terminal: nie mit `$_` inline, immer als .ps1-Datei

Die `terminal`-Shell auf diesem Host ist git-bash. Eine inline-PowerShell
(`powershell.exe -Command "...$_..."") wird dort zerlegt, sobald sie `$_`,
`{n=...;e={[math]::Round($_.Free/1GB)}}`-Ausdruecke oder andere `$`-Tokens
traegt — MSYS interpretiert `$_`/`$(`/Pfade im -Command-String als eigene
Substitution (Fehlermeldung: "Unerwartetes Token", "wird gesucht"). Das bricht
Mess-, Pruef- und Kompaktschritte zuverlaessig. Fix: jede PowerShell, die `$_`
benutzt (Get-PSDrive-Free-Berechnung, Get-ChildItem-Summen, jede
ForEach-Object-Transformation), **in eine `.ps1`-Datei schreiben** (write_file,
utf-8) und mit `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ...`
aufrufen. Inline-`-Command` nur fuer `$`-freie Einzeiler.

## Docker Desktop: `docker_data.vhdx` waechst unbegrenzt

Docker Desktop legt sein WSL-Disk-Image unter `O:\Modelle\DockerDesktopWSL\disk\docker_data.vhdx`
(oder `...\main\ext4.vhdx`). Es waechst mit jedem Container-Image/-Daten und ist ein
haeufiger stiller O:-Verbraucher — 28 GB und wachsend, waehrend die Images nur ~23 GB
belegen.

- `docker system df` zeigt, was belegt und was reclaimable ist.
- `docker system prune -f` (ohne `-a`) entfernt nur gestoppte Container + dangling
  Images — das ist oft nur ~50 MB. Die ungenutzten Images (12+ GB) brauchen `-a`,
  was auch Images ohne laufenden Container trifft (kann benoetigte Images fuer
  nicht-aktive Spuren entfernen) — nur mit Freigabe.
- **Der vhdx schrumpft nicht von selbst.** Prune befreit Platz im Image, aber die
  Datei bleibt gross; erst eine Kompaktierung (Docker Desktop "Compact disk" /
  `Optimize-VHD`) gibt den Platz wirklich an die Platte zurueck.
- **`wsl --shutdown` haelt das `docker-desktop`-vhdx NICHT frei** — der
  Docker-Daemon startet die Distro im selben Atemzug wieder (`docker ps` zeigt
  die Container weiter "up"). Die Distro gezielt beenden:
  `wsl --terminate docker-desktop`, danach `wsl -l -v` auf ``Stopped`` pruefen,
  erst dann ist das vhdx ungemountet und kompaktierbar.
- **`Optimize-VHD -Path <vhdx> -Mode Full` braucht eine elevated (Admin-) Shell**;
  aus einer normalen Shell schlaegt es mit "nicht die erforderliche Berechtigung
  ... Administrator". `wsl --manage <distro> --set-sparse true` ist dagegen
  absichtlich deaktiviert (Datenbeschaeidigungs-Waechter) und laesst sich nur mit
  `--allow-unsafe` erzwingen — nicht tun. Der adminfreie Weg existiert nicht;
  die Kompaktierung gehoert in ein Admin-Terminal (Befehl dem User geben).
- **Ein Container mit `RestartPolicy=unless-stopped` kommt nach einem expliziten
  `docker stop <name>` NICHT selbst wieder hoch** — der manuelle Stop setzt den
  Zustand auf "gestoppt" und ueberstimmt die Policy. Nach so einem Stop (oder
  nach `wsl --terminate`) die Handels/Demo-Container namentlich wieder starten:
  `docker start nautilus-demo`, und nur per `docker ps` als ``Up`` bestaetigen.
  Erst nach `docker stop` verliert man den automatischen Restart bewusst; wer
  Kerne herunterfaeren will, stoppt die Distro (`wsl --terminate`), nicht den
  einzelnen Container.

## Loeschen nur auf ausdrueckliche Anweisung

Einen grossen Ordner, den du nicht erzeugt hast (Backup, Zweitkopie, Cache), nie
ohne Freigabe loeschen - auch wenn die Platte kritisch ist. Befund + Groesse +
Redundanz-Vermutung vortragen und das OK abwarten. `docker system prune -a` und
eine Pagefile-Verschiebung ebenso nur nach Freigabe.

## Windows-Reservierungsnamen (`nul`) blockieren das Loeschen

Eine Kopie mit einem `nul`-Eintrag (NTFS-Reservierungsname) bricht `Remove-Item
-Recurse` mit "Unzulaessige Funktion" ab und `cmd rmdir` mit "Syntax falsch"
(Pfad-Komposition wird gemangled). `\?\`-Präfix in Python/`os.remove` liefert
FileNotFoundError. Der zuverlaessige Weg ist `ctypes.windll.kernel32.DeleteFileW`
mit dem `\?\`-Pfad, aus einer Pythondatei heraus (Factory liefert `\?\` intakt),
nicht ueber die mehrschichtig gequotete Shell:

```python
import ctypes
ok = ctypes.windll.kernel32.DeleteFileW(r"\\?\O:\MaxHirn-Zweitkopie\nul")
# False => Fehler; ist es ein Unterordner, RemoveDirectoryW statt DeleteFileW
```

Erst die normalen Dateien via `Remove-Item`, den Reserved-Eintrag zuletzt als
Datei/Ordner pruefen (ist es ein Ordner, RemoveDirectoryW). Shell-Uebergabe
mangelt Backslashes (Drive `\?\O` wird gesucht); Datei vermeidet das (Befund
13.10.2026: 32,7-GB-Zweitkopie mit `nul`).

## Archiv-Relokation: Ordner auf HDD verschieben und Junction legen

Um einen grossen Kaltdaten-Ordner von `O:` (voll) auf eine HDD (`G:`) zu bringen,
ohne absolute Pfade zu brechen: `robocopy O:\Archiv G:\Archiv /E /COPY:DAT
/R:2 /W:1 /MT:16` als Hintergrundjob (44 GB dauern Minuten; `/LOG:` fuers
Protokoll), Groesse byte-gleich verifizieren (`Get-ChildItem ... |
Measure-Object -Sum`), dann Quelle `Remove-Item -Recurse` und
`New-Item -ItemType Junction -Path O:\Archiv -Target G:\Archiv`. Der Pfad
`O:\Archiv` bleibt danach transparent (Bilder/Dokumente/... + Schreibzugriff
pruefen). Robocopy-Exit 1 = erfolgreich kopiert (0-7 sind Erfolg).
Robocopy vorher nicht mit timeout=60 im Vordergrund starten - das killt das
Handle nach 60 s, der Kopiervorgang haengt dann unzuverlaessig; mit
`background=true, notify=true` laufen lassen.

## Kaltdaten von der SSD auf die HDD umziehen (statt Pagefile anfassen)

Max' Vorzug bei einer vollen SSD: **Archiv-/Kaltdaten auf die grossen HDDs
verschieben, nicht das Pagefile verlegen oder C: zum System-Ordner machen.**
Das Pagefile auf einem ebenfalls knappen C: bringt nichts; der Umzug kalter Daten
gibt echten, dauerhaften Platz.

Ablauf (robocopy + Junction, damit Pfade gueltig bleiben):

```powershell
# 1. Ziel-Laufwerke pruefen: Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3'
#    (HDD mit viel frei waehlen, z. B. ein BackUp-Laufwerk).
# 2. Kopieren (Junction-Ziel darf noch nicht existieren):
robocopy "O:\Archiv" "G:\Archiv" /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /MT:16 /NFL /NDL /NP /LOG:...
#    Als background=true + notify=true starten — 30+ GB dauert Minuten bis
#    Viertelstunde, ein Foreground-Timeout kappt das Handle und stoppt den Lauf.
#    robocopy-Exit 0-7 ist Erfolg; /NFL /NDL /NP halten die Ausgabe klein.
# 3. Nach Erfolg Quell-Inhalt und Ziel Groesse/Anzahl gegenpruefen.
# 4. Quellordner entfernen und durch Junction ersetzen:
New-Item -ItemType Junction -Path "O:\Archiv" -Target "G:\Archiv"
#    (vorher das Original loeschen; sonst schlaegt der Junction fehl)
# Der alte Pfad bleibt damit absolut gueltig — absolute Pfade in Configs/Skripten
# brechen NICHT, der Umzug ist transparent.
```

## Windows-Reservierungsnamen (`nul`, `aux`, `con`, ...) loeschen

Ein Ordner, der eine Datei mit einem Windows-Reservierungsnamen enthaelt (z. B.
`nul`), laesst sich nicht mit `Remove-Item -Recurse` entfernen — es bricht mit
"Unzulaessige Funktion"/"Das Laufwerk wurde nicht gefunden" ab und der Rest bleibt.
PowerShell/`cmd rmdir` mit `\\?\`-Praefix ebenso scheitern oft an der
Shell-Escape-Ebene (bash -> powershell -> cmd verdreifacht die Backslashes).
Der zuverlaessige Weg: Win32-API ueber ctypes, `DeleteFileW` mit dem
extended-length-Pfad `\\?\O:\Pfad\nul` in einer .py (nicht per heredoc-Escaping,
sondern als Datei):

```python
import ctypes
ok = ctypes.windll.kernel32.DeleteFileW(r"\\?\O:\MaxHirn-Zweitkopie\nul")
print('ok' if ok else 'Fehler', ctypes.get_last_error())
```

Wenn `DeleteFileW` scheitert, ist der Eintrag ein Verzeichnis — dann
`RemoveDirectoryW` auf denselben Pfad. Nach dem Entfernen ist der verwaiste
Leerordner normal loeschbar.
