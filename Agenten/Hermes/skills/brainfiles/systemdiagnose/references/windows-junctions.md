# Windows-Junctions im BrainFiles-Baum

## Karte
`Werkstatt` → `O:\Werkstatt` und `Modelle` → `O:\Modelle` sind Junctions
(physisch auf O:); ausserdem `O:\Wiki` → `MaxHirn\Wiki`, einzelne
`Werkstatt\*`-Verweise und die sieben `Agenten\Hermes\skills\okx-*`.
`Werkstatt` ist die einzige, die bereits ZWEIMAL zerstoert wurde: dann ist
`BrainFiles\Werkstatt` ein ECHTER Ordner (meist eine Teilkopie des O:-Inhalts),
`LinkType` leer, `Attributes` nur `Directory`.

## Symptome (jede einzeln beobachtet)
- `fremd.py` meldet auf einmal ALLE `Werkstatt/...`-Eintraege „Ordner liegt
  nicht auf der Platte" — nicht Eintraege nachtragen, erst die Junction pruefen.
- `konfig-doktor-<datum>.md` taucht an der Werkstatt-Wurzel auf — der Schreiber
  lief durch den echten Ordner.
- `omnitrade.cmd` meldet „keine Statusdatei", Repos-zentrale zeigt FEHLT —
  Folge derselben Ursache.
- Eintraegezahl von `Werkstatt` weicht von `O:\Werkstatt` ab.
- Die Teilkopie enthaelt oft selbst eine `Repos`-Junction zurueck auf
  `O:\Werkstatt` — eine teilweise Rekonstruktion, die den wichtigsten
  Teil wiederherstellt, den Rest aber als echten Ordner liegen laesst. Vor dem
  Loeschen des Elternordners JEDES Kind auf `LinkType` pruefen.

## Pruefen
```powershell
(Get-Item 'Werkstatt' -Force) | Select-Object LinkType, Target, Attributes
(Get-ChildItem 'Werkstatt' -Force | Measure-Object).Count   # gegen O:\Werkstatt
```
Falle beim Pruefen: ein ECHTER Ordner hat `LinkType = $null`, nicht `''` — ein
`if ($w.LinkType -eq '')` laeuft still NICHT (`$null -eq ''` ist False) und
versteckt den Rest der Pruefung. Auf `$null` pruefen oder `LinkType` direkt
ausgeben und lesen.

## Reparatur — verlustfrei, in dieser Reihenfolge
1. Rettungskopie VOR jeder Loeschung:
   `robocopy 'Werkstatt' 'O:\Werkstatt-Rettung-JJJJMMTT' /E /XJ /R:1 /W:1 /MT:16`
   (`/XJ` ueberspringt Junctions — die eingebettete Repos-Junction wird nicht
   doppelt kopiert).
2. Eingebettete Junctions einzeln als LINK loesen:
   `[System.IO.Directory]::Delete('C:\...\Werkstatt')` — loescht nur den
   Link, das Ziel bleibt unberuehrt. `cmd /c rmdir` funktioniert aus der
   bash/MSYS-Shell NICHT (startet cmd interaktiv, Banner, kein Effekt);
   `Remove-Item` auf eine Junction wirft in PS 5.1 eine `NullReferenceException`.
   Ein rekursives Loeschen des Elternordners MIT eingebetteter Junction ist
   genau der Fall, in dem aeltere PowerShell-Versionen ins Ziel hineinloeschen.
3. Einzigartige Wurzel-Dokumente nach O: mergen:
   `robocopy 'Werkstatt' 'O:\Werkstatt' *.md *.txt *.jsonl /R:1 /W:1`
   (kopiert nur Wurzeldateien).
4. Echten Ordner entfernen: `Remove-Item -LiteralPath 'Werkstatt' -Recurse -Force`.
   Destruktiv: im Approval-Terminal EIGENER Aufruf (der Bestaetigungsdialog
   gehoert VOR den Schritt, nicht in eine Kette damit gebuendelt), vorher
   ansagen. Der Lauf kann MITTENDRIN abbrechen, wenn ein Unterordner von einem
   anderen Prozess gehalten wird (AV-/Indexer-Scan, eine laufende Sitzung mit
   cwd dort) — `IOException`, `-ErrorAction Stop` stoppt dann. Das ist meist
   transient: eine Retry-Schleife (bis 6 Versuche, 8 s Abstand) raeumt den Rest
   ab. Vorher pruefen, ob ein ECHTER Prozess den Pfad haelt
   (`Get-CimInstance Win32_Process` auf die Kommandozeile) — ein laufender
   Bot/Worker mit cwd dort ist kein transientes Schloss, sondern Arbeit.
5. Junction neu: `New-Item -ItemType Junction -Path 'Werkstatt' -Target 'O:\Werkstatt'`.
6. Verifikation (alle drei): `LinkType = Junction`, Eintraegezahl == `O:\Werkstatt`,
   `Test-Path 'Werkstatt\omnitrade\Cargo.toml'` und Repos erreichbar; danach
   `git status` unveraendert.

NIE `rm -rf` auf einen Junction-Kandidaten aus bash (das Verhalten ist unklar);
PowerShell `Remove-Item -LiteralPath` oder `cmd /c rmdir` nehmen.

## Sicherung und Wache
Laeuft eine Kopie, deren Quelle die Junction kreuzt, waehrend sie zerstoert ist,
sichert robocopy die Teilkopie ohne jede Meldung — die LinkType-Pruefung gehoert
VOR jeden Backup-Start. Eine automatisierte Junction-Wache existiert nicht
(`konfig-doktor.ps1` kennt LAUFZEIT-JUNCTION-* als KRITISCH, laeuft aber nur auf
Ansage); Kandidat: Hermes-Cron, taeglich `LinkType` von Werkstatt/Modelle, leere
Ausgabe = gesund.
