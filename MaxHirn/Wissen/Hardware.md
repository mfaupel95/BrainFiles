---
id: 20260830-hardware
title: 'Hardware'
tags: [hardware]
created: 2026-08-28
updated: 2026-09-06
related: [20260830-hardware-checkliste-d5]
summary: 'Laufwerke des Arbeitsrechners, Plattendiagnose und der ungeklärte Stromausfall.'
---

# Hardware

Laufwerke des Arbeitsrechners und was bei Plattenproblemen zu prüfen ist.
Ein Netzteildefekt hat 2026 mehrere Festplatten gleichzeitig zerstört; die
betroffenen Platten sind ausgebaut. **Das Stromproblem selbst ist damit nicht
erledigt** — siehe „Stromausfälle ohne Bluescreen" unten.

**Warum:** Der Ausfall hat einen halben Arbeitstag gekostet, weil das Symptom
(einfrierender Explorer) nach einem Software- statt einem Hardwareproblem aussah.
Die Diagnosewege unten führen in Minuten zum Ergebnis. Ausserdem ist die
Laufwerkszuordnung Voraussetzung für den Umzug in [[Portabilitaet]].

**Stand:** 2026-09-04 (Claude-Lock-Fehler behoben; vorher 2026-08-30, Absturzanalyse; Laufwerkslage 2026-08-28; Nachmessung 2026-08-19, Ursprungsfassung 2026-08-16)

## Eckdaten des Rechners

Intel Core i9-7940X, MSI X299 GAMING PRO CARBON (MS-7A95), BIOS 1.H0 vom
07.09.2022, 63,7 GB RAM, **NVIDIA GeForce RTX 3060 Ti (8 GB VRAM)**,
Windows 11 Pro Build 26200.

`Win32_VideoController.AdapterRAM` meldet für diese Karte **4 GB** — das ist ein
bekannter Überlauf des 32-Bit-Feldes, nicht die tatsächliche Bestückung. Für
VRAM-Angaben nicht auf WMI verlassen, sondern `nvidia-smi` oder das Modell
heranziehen. 8 GB VRAM entscheiden darüber, welche lokalen KI-Modelle
vollständig auf die GPU passen (7–8B in Q4/Q5 ja, 12–14B knapp, darüber nicht).

## Laufwerke

| Buchstabe | Datenträger | Disk-Nr. | Anschluss | Dateisystem |
|---|---|---|---|---|
| C: | Samsung MZVPV512 NVMe | 0 | intern | NTFS |
| O: | WD WDS100T2B0C NVMe | 1 | intern | NTFS |
| G: H: I: | Seagate Portable | **2** | USB | NTFS |
| J: | WD My Book 1230 | 3 | USB | NTFS |
| E: | Netac MobileDataStar (466 GB) | 4 | USB, nur zeitweise | **exFAT** |

> **Stand 28.08.2026, nach dem CMOS-Reset:** Max hat an diesem Tag das CMOS
> zurückgesetzt und das Mainboard auf Standardeinstellungen gestellt; die
> USB-Platten waren dafür abgezogen. **Seagate Portable ist wieder da**
> (`G:` BackUp 2751,1 GB / 128,8 GB frei, `H:` Music Sync, `I:` Volume, alle
> `Healthy`), `G:\MaxHirn-Sicherung` ist erreichbar — die 20-Uhr-Sicherung
> kann wieder laufen.
>
> **`J:` fehlt weiterhin.** Die WD My Book steht in `Get-PnpDevice` auf
> `Unknown`, `Test-Path J:\` ist `False`. Damit zeigt die Junction
> `C:\Users\faupe\iCloudPhotos` → `J:\iCloudPhotos` ins Leere (geprüft
> 28.08.2026). Das betrifft rund 30.635 Mediendateien; sie sind nicht verloren,
> nur nicht angeschlossen. Ob mit Absicht abgezogen, ist offen —
> `Archiv/TASKS.md`, T-005.
>
> **Merkposten für die Diagnose:** Waren die Platten abgezogen, fehlt `G:` auch
> in der Auslagerung — Windows legt `G:\pagefile.sys` erst beim nächsten Start
> mit angeschlossener Platte wieder an. Ein Protokoll aus so einem Lauf zeigt
> also nicht den Normalzustand.

`E:` ist die Kopie außer Haus und hängt nicht dauerhaft am Rechner. Sie ist als
einzige **exFAT** — beim Sichern dorthin ist `/FFT` Pflicht, sonst schreibt
robocopy jedes Mal alles neu (Begründung in [[Routinen]]).

**G:, H: und I: sind drei Partitionen derselben physischen Platte** (Disk 2,
geprüft 23.08.2026 mit `Get-Partition` + `Get-Disk`). Beim Sichern ist das
entscheidend: Eine zweite Kopie auf H: läge auf demselben Datenträger wie die
Sicherung auf G: — fällt Disk 2 aus, sind beide gleichzeitig weg. Zwei
Laufwerksbuchstaben sind kein zweiter Datenträger.

Deshalb liegt die Zweitkopie seit 23.08.2026 auf **O: (Disk 1)**: Original
(Disk 0), Sicherung (Disk 2) und Zweitkopie (Disk 1) verteilen sich damit auf
drei Platten — siehe [[Routinen]]. **Gegen einen erneuten Netzteilschaden hilft
das nicht**, alle drei stecken im selben Rechner. Eine Kopie außer Haus bleibt
offen.

Nachprüfen:

```powershell
Get-Partition | Where-Object DriveLetter |
  Select-Object DriveLetter, DiskNumber, @{n='Modell';e={(Get-Disk $_.DiskNumber).FriendlyName}}
```

Auf der WD-NVMe liegen zusätzlich fünf Partitionen ohne Laufwerksbuchstaben
(zusammen 375 GB, Typ „Unknown", dem Anschein nach Linux). **Alle Datenträger
sind zu 100 % partitioniert**, nirgends unbelegter Platz — `LargestFreeExtent`
ist überall 0. Eine Partition zu vergrössern setzt also voraus, vorher eine
andere zu verkleinern.

**Nicht mit freiem Speicher verwechseln.** Innerhalb der Volumes ist reichlich
Platz (gemessen 19.08.2026):

| Volume | Frei | Gesamt |
|---|---|---|
| C: | 123,3 GB | 475,1 GB |
| O: Dokumente | **280,9 GB** | 551,9 GB |
| G: BackUp | 157,0 GB | 2751,1 GB |
| H: Music Sync | 488,1 GB | 1856,7 GB |
| J: Extern_BackUp | **270,9 GB** | 1953,1 GB |
| I: Volume | 49,5 GB | 49,6 GB |

Zwei Punkte dazu:

- **J: hat 270,9 GB frei**, nicht mehr 114,2 GB wie am 07.08. Der Papierkorb
  auf J: enthält nur noch 9 Dateien / 0 GB — er **ist geleert**, die am
  07.08.2026 verschobenen 65,51 GB sind real frei. Zusammen mit weiteren
  Aufräumarbeiten sind seither rund 157 GB freigeworden.
- **D: erscheint mit 0 Byte und `Healthy`.** Das ist das **optische Laufwerk**
  (`Win32_LogicalDisk.DriveType = 5`), kein sterbender Datenträger. Nicht mit
  dem Fehlerbild von I: aus dem Netzteildefekt verwechseln — dort war es ein
  Volume vom Typ 3 (feste Platte) mit Grösse 0.

## Netzteildefekt 2026

Ein defektes Netzteil hat mehrere Platten gleichzeitig getötet. Sie sind
ausgebaut. Die Folge für das Archiv steht in
[BESCHAEDIGTE_PDFS.md](../Archiv/BESCHAEDIGTE_PDFS.md): Dateinamen blieben
erhalten, Inhalte sind weg.

### Die alte Laufwerksordnung (Angabe Max, 24.08.2026)

Vor dem Defekt war jede Medienart eine eigene physische Platte mit festem
Buchstaben:

| Buchstabe | Inhalt |
|---|---|
| P: | Bilder |
| M: | Musik |
| F: | Filme |
| D: | Dokumente |
| I: | iCloud |
| S: | Software |

Die Liste ist nicht vollständig — Max nennt „und noch weitere".

**Keiner dieser Buchstaben existiert heute noch in seiner alten Bedeutung.**
`D:` ist inzwischen das optische Laufwerk, `I:` eine Partition der Seagate
Portable; beide Buchstaben wurden neu vergeben. `P:`, `M:`, `F:` und `S:`
kommen im System überhaupt nicht mehr vor (geprüft 24.08.2026).

Zwei Dinge folgen daraus:

- **`I:` war die iCloud-Platte** — also genau das Laufwerk, das beim Defekt mit
  0 Byte Grösse hängen blieb (Ablauf unten). Das heutige `I:` hat damit nichts
  zu tun. Wer die beiden verwechselt, sucht den Fehler an der falschen Platte.
- **Ein Pfad auf `P:`, `M:`, `F:` oder `S:` in einer alten Konfiguration zeigt
  auf verlorene Daten**, nicht auf ein gerade nicht angeschlossenes Laufwerk.
  Solche Pfade laufen still ins Leere, ohne Fehlermeldung.

**Vermutung, nicht belegt:** Die Archivordner `Bilder/`, `Musik/`, `Videos/`,
`Dokumente/` und `Software/` entsprechen dieser Aufteilung. Das würde erklären,
warum der Schaden so ungleich verteilt ist — 494 zerstörte Dateien in `Bilder/`
gegen 5 in `Videos/`, siehe
[BESCHAEDIGTE_DATEIEN.md](../Archiv/BESCHAEDIGTE_DATEIEN.md). Es wären dann
getrennte Platten gewesen, die unterschiedlich stark getroffen wurden. Geprüft
ist das nicht.

### Tote Laufwerkspfade in Konfigurationen (aufgeräumt 24.08.2026)

Eine Suche über Registry, 329 Verknüpfungen, 208 geplante Aufgaben, Autostart,
den Vault, Hermes, 1.126 AppData-Konfigurationsdateien und `Documents` fand
genau **zwei** tote Verweise. Beide zeigten auf `P:`, beide waren
Hintergrundbilder:

| Ort | Wirkung |
|---|---|
| Windows Terminal, `profiles.defaults.backgroundImage` | Bild fehlte, dadurch schlug die darunter gesetzte Hintergrundfarbe `#C21A23` durch — alle Profile wurden unlesbar (Kontrast 3,77 : 1) |
| PowerToys Command Palette, `BackgroundImagePath` | folgenlos, das Bild lädt einfach nicht |

Beide Pfade entfernt, Sicherungen liegen als `settings.json.bak-20260824` neben
den Originalen. Beim Terminal wurden zugleich die Farbschemata ersetzt
(„Lesbar Dunkel" für PowerShell, „Lesbar Neutral" für cmd und Git Bash,
Kontrast 10,5 bzw. 12,9 : 1) und der Fokusmodus abgeschaltet, der Tab- und
Titelleiste ausblendete und damit den Weg zu den Einstellungen versperrte.

Ablauf des sichtbaren Fehlers: Der Explorer fror im Kopiervorgang ein. Laufwerk
I: war als feste Platte angemeldet, meldete aber 0 Byte Grösse und fehlte in den
Datenträger-Leistungsindikatoren. Der `disk`-Treiber protokollierte Event **153**
(E/A an Blockadresse `0x0` wiederholt) für „Datenträger 4" alle zwei Minuten,
je zwei Versuche 21 Sekunden auseinander — 21 s ist das Zeitlimit des
Speichertreibers pro Versuch.

## Wenn der Explorer wieder hängt

1. **`Win32_LogicalDisk` auf Volumes mit 0 Byte prüfen.** Ein Laufwerk vom Typ 3
   (feste Platte) mit Grösse 0 ist der Übeltäter.
2. **Systemprotokoll auf `disk`-Event 153 ansehen.** Fehler **ausschliesslich bei
   LBA `0x0`** heissen: Die Platte kann ihre Partitionstabelle nicht liefern, ist
   also elektrisch tot — kein Dateisystemschaden. Kein `chkdsk`, das verschlimmert
   es. Bei Fehlern über verschiedene LBAs verteilt liegt eher ein Medienschaden vor.
3. **Warteschlangen und Leerlauf gegenprüfen.** Warteschlangen 0 bei 92–100 %
   Leerlauf heisst: kein Durchsatzproblem, sondern reines Blockieren.

Zwei Eigenheiten, die beim Diagnostizieren Zeit sparen:

- Zugriffe auf ein totes Laufwerk hängen in einem **nicht unterbrechbaren
  Kernel-Wartezustand**. `timeout` kann den Prozess nicht abbrechen, auch nicht
  mit kurzer Frist. Ein hängender Befehl ist selbst schon der Befund.
- **Registry und `fsutil fsinfo drives` funktionieren weiter**, weil sie kein
  Geräte-I/O auslösen: `HKLM\SYSTEM\MountedDevices` und
  `HKLM\SYSTEM\CurrentControlSet\Services\disk\Enum`. WMI-Abfragen über Laufwerke
  hängen dagegen mit. Auch der PowerShell-Start hing, während Git Bash sofort
  antwortete — nicht als Shell-Problem fehldeuten.

## Stromausfälle ohne Bluescreen (offen, Stand 2026-08-30)

> **Weiterhin offen. Die Gegenmassnahmen vom 28.08.2026 haben es nicht
> behoben** — seither sind drei weitere Vorfälle hinzugekommen, und der
> Standby-Zusammenhang ist widerlegt. Aktueller Messstand am Ende der Datei:
> „Nachmessung 30.08.2026, 22:20".

Der Rechner geht in unregelmässigen Abständen **schlagartig aus**. Zwölf Vorfälle
in 22 Tagen; die Tabelle hier reicht nur bis zum 28.08., die drei jüngsten
stehen am Dateiende:

> **Korrektur 28.08.2026 — zwei Angaben in diesem Abschnitt waren überholt:**
>
> 1. Hier stand „Fünf Vorfälle in 32 Tagen" und weiter unten, seit dem 16.08.
>    seien keine Kernel-Power-41-Ereignisse mehr aufgetreten. Beides gilt nicht
>    mehr: Am **20.08., 21.08., 27.08. und 28.08.** kamen vier weitere hinzu.
> 2. Als Erkennungsmerkmal stand `SleepInProgress = 0`. Das trifft nur auf die
>    frühen Vorfälle zu. **Seit dem 14.08. haben alle sechs Abstürze
>    `SleepInProgress = 16`** — ein anderer Fingerabdruck, siehe unten.
>
> **Punkt 2 ist am 30.08.2026 widerlegt.** `SleepInProgress` ist bei *allen*
> Vorfällen `0`; die 16 gehörte zum Feld `Checkpoint` und wurde damit
> verwechselt. Die Spalte in der Tabelle unten ist entsprechend falsch
> beschriftet. Richtigstellung, Messbefehl und der Grund, warum der
> Standby-Zusammenhang insgesamt gefallen ist: Abschnitt „Nachmessung
> 30.08.2026" am Dateiende.

> **Korrektur 19.08.2026** (historisch — der Schlusssatz zur Ruhephase
> ist durch die Korrektur darüber überholt): Hier stand „und die Abstände werden kürzer". Das
> trägt die Datenlage nicht. Die beiden Ereignisse am 08.08. liegen 17 Minuten
> auseinander (ein Vorfall mit Sofort-Wiederholung), danach folgen Abstände von
> 3, 3 und 2 Tagen. Seit dem 16.08. sind — Stand 19.08., Prüfung im
> Systemprotokoll ab 01.08. — **keine weiteren Kernel-Power-41-Ereignisse**
> aufgetreten; das sind gut 3 Tage und damit der bislang längste Abstand.
> Kein Grund zur Entwarnung, aber „beschleunigt sich" ist als Befund falsch und
> hätte zu übereilten Maßnahmen verleitet.

| Datum | Uhrzeit | ~~`SleepInProgress`~~ tatsächlich `Checkpoint` | Aufwachen aus S3 davor |
|---|---|---|---|
| 08.08.2026 | 12:28 | 13 | — |
| 08.08.2026 | 12:45 | **0** | — |
| 11.08.2026 | 10:56 | 9 | — |
| 14.08.2026 | 14:57 | **16** | — |
| 16.08.2026 | 11:07 | **16** | — |
| 20.08.2026 | 16:15 | **16** | 16:12:05 → 3 Min |
| 21.08.2026 | 16:18 | **16** | 16:15:10 → 3 Min |
| 27.08.2026 | 18:02 | **16** | 17:58:52 → 3 Min |
| 28.08.2026 | 14:11 | **16** | 14:01:10 → 10 Min |

Alle neun haben `BugcheckCode = 0` und `PowerButtonTimestamp = 0`. Gemessen
28.08.2026 über `(Get-WinEvent -FilterHashtable @{LogName='System'; Id=41}).Properties`.

**Das Muster hat sich verändert.** Die frühen Vorfälle passierten im laufenden
Betrieb. Die vier jüngsten dagegen **3 bis 10 Minuten nach dem Aufwachen aus
dem Standby** — Uhrzeiten der `Kernel-Power`-131-Ereignisse in der letzten
Spalte. Das ist kein Zufallstreffer mehr, sondern ein reproduzierbarer Ablauf.

Erkennungsmerkmal im Systemprotokoll: **Kernel-Power 41 mit `BugcheckCode = 0`**
und `PowerButtonTimestamp = 0`, begleitet von EventLog 6008. Das heisst
ausdrücklich **kein** Betriebssystemabsturz — Windows bekommt vom Ausfall
nichts mit. `Checkpoint` gehört **nicht** in dieses Erkennungsmerkmal: Der Wert
unterschied bis zum 28.08. die beiden Sorten Vorfall (13 und 9 früher,
durchgehend 16 vom 14.08. bis 28.08.), steht seit dem 29.08. aber wieder auf 0,
während die Abstürze weitergehen.

#### Nachtrag 31.08.2026: es geht weiter, und nicht mehr nur nach Standby

Zwei weitere Vorfälle an diesem Tag, beide mit dem oben beschriebenen
Erkennungsmerkmal (`BugcheckCode = 0`, `PowerButtonTimestamp = 0`, dazu
`EventLog 6008`):

| Datum | Uhrzeit | Checkpoint | vorheriges Aufwachen |
|---|---|---|---|
| 31.08.2026 | 17:02:52 | **0** | keines protokolliert |
| 31.08.2026 | 22:56:23 | **0** | keines protokolliert |

**Der Standby-Zusammenhang trägt nicht mehr.** In den 24 Stunden vor dem
Vorfall um 22:56 steht **kein einziges** `Kernel-Power`-131-Ereignis im
Protokoll — der Rechner lief durch. Die Erklärung „3 bis 10 Minuten nach dem
Aufwachen" von oben deckt diese beiden Fälle also nicht ab.

**Zählstand:** 14 Vorfälle in 45 Tagen, davon **5 in den letzten drei Tagen**
(29.08. 11:04 und 13:18, 30.08. 21:01, 31.08. 17:02 und 22:56). Die Frequenz
steigt. Gemessen 31.08.2026, 23:20:

```
Get-WinEvent -FilterHashtable @{LogName='System'; ID=41; StartTime=(Get-Date).AddDays(-45)}
```

**Was der Vorfall um 22:56 gekostet hat:** Er hat einen laufenden
Paket-Installationslauf mitten durchtrennt und ein unvollständiges Hermes-venv
hinterlassen, das sich nach außen gesund meldete — siehe
[[Python-Versionen]]. Das ist der praktische Schaden dieser Abstürze: nicht der
Neustart selbst, sondern was an halbfertigen Zuständen zurückbleibt.

### Auslagerungsdatei auf einer USB-Platte (gefunden 28.08.2026, behoben am selben Tag)

> **Erledigt.** Nachgemessen am 28.08.2026 um 17:15: `PagingFiles` enthält nur
> noch `c:\pagefile.sys 0 0` und `o:\pagefile.sys 4096 16384`, und
> `G:\pagefile.sys` existiert nicht. Der Befund unten ist der Ausgangszustand.

In `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management`
stand unter `PagingFiles`:

```
c:\pagefile.sys 0 0
g:\pagefile.sys 4096 16384
o:\pagefile.sys 4096 16384
```

**`G:` ist die Seagate Portable — eine USB-Platte.** Eine Auslagerungsdatei
gehört dort nicht hin, und zusammen mit S3-Standby ist das ein plausibler
Auslöser für genau das beobachtete Fehlerbild: Im Standby wird die
USB-Anbindung stromlos; greift der Kernel nach dem Aufwachen auf ausgelagerte
Seiten zu, bevor die Platte wieder da ist, folgt ein harter Reset — ohne
Bluescreen und ohne Speicherabbild, weil der Auslagerungspfad selbst betroffen
ist.

**Das ist eine begründete Hypothese, kein Beweis.** Dafür spricht der
zeitliche Zusammenhang mit dem Aufwachen bei allen vier jüngsten Vorfällen,
das Fehlen jeder Hardwaremeldung (keine WHEA-Ereignisse, keine `disk`- oder
`Ntfs`-Fehler, beide NVMe `Healthy`) und das Fehlen jedes Dumps. Nicht erklärt
sind die Vorfälle vom 08. und 11.08. ohne Standby-Bezug — es können zwei
Ursachen nebeneinander bestehen, die alte Stromfrage bleibt offen.

Unabhängig von der Absturzfrage ist der Eintrag **falsch konfiguriert** und
gehört entfernt. Aktiv sind ohnehin nur `C:` (9 GB) und `O:` (4 GB); auf `G:`
legt Windows nur dann etwas an, wenn die Platte angeschlossen ist.

**Zur Dumpfrage:** Auf `C:` liegt eine systemverwaltete Auslagerungsdatei
(9 GB bei 63,7 GB RAM), `CrashDumpEnabled = 3` (Kernel-Abbild) ist gesetzt.
Windows *könnte* also bei einem echten Bluescreen ein Abbild schreiben. Dass in
`C:\Windows\Minidump` trotzdem nichts liegt, bleibt damit ein Befund und ist
kein Konfigurationsmangel.

Drei Gegenproben, die den Befund härten:

- **Kein einziges Absturzabbild** in `C:\Windows\Minidump`, kein `MEMORY.DMP`,
  obwohl `CrashDumpEnabled = 3` gesetzt ist. Bei einem echten Bluescreen läge
  dort etwas.
- **Keine WHEA-Logger-Ereignisse** — CPU, RAM und PCIe melden keine Fehler.
- Kein Schnellstart aktiv (`HiberbootEnabled = 0`, Ruhezustand ohnehin
  deaktiviert), der die Abschaltungen verschleiern könnte.

**Der Netzteiltausch ist bereits erfolgt und hat es nicht behoben.** Max hat nach
dem Defekt sein **altes Netzteil wieder eingebaut** — dabei fiel überhaupt erst
auf, dass Platten weggebrochen waren und das Netzteil die Ursache war. Der
Rechner läuft seither auf diesem alten Netzteil, und die Abschaltungen gehen
weiter. „Netzteil tauschen" ist damit als Schritt abgehakt, ohne Erfolg.

Was daraus folgt — der nächste Verdächtige ist nicht mehr *irgendein* Netzteil,
sondern:

1. **Das eingebaute alte Netzteil selbst.** Es ist der ältere von zwei Kandidaten
   und versorgt einen i9-7940X auf X299. Ein Gegentest gehört mit einem
   **bekannt guten, ausreichend dimensionierten** Gerät gemacht, nicht mit einem
   weiteren Altteil.
2. **Stromzufuhr ausserhalb des Netzteils:** Kaltgerätekabel, Steckdosenleiste,
   Wandsteckdose. Billig zu prüfen, deshalb zuerst.
3. **Lastspitzen einzelner Komponenten** und Temperaturen.

**Solange das offen ist:** keine langen Schreibläufe auf die externen Platten
ohne aktuelle Sicherung, und **keine Reparaturinstallation von Windows** — eine
einstündige Installation auf einer Maschine, die alle zwei Tage ausgeht, kann
ein nicht mehr startfähiges System hinterlassen.

## Zustand der Laufwerke (gemessen 2026-08-14)

| Datenträger | Temp | Betriebsstunden | Unkorrigierte Lesefehler | Start-Stopp |
|---|---|---|---|---|
| Seagate Portable (G: H: I:) | 40 °C | 9.323 | **0** | 5.802 |
| WD My Book 1230 (J:) | 43 °C | 14.878 | **479** | 39.501 |
| Samsung NVMe (C:) | 51 °C | — | — | — |
| WD NVMe (O:) | 50 °C | — | — | — |

**Die WD My Book baut ab.** 479 unkorrigierte Lesefehler heisst: Daten, die das
Laufwerk nicht mehr rekonstruieren konnte. Das ist dasselbe Laufwerk, auf das
seit 08.08.2026 die iCloud-Fotomediathek zeigt (siehe unten) und auf dem unter
`MAKS`, `Dokumente\Max`, `Mary Ann` und `Carina` persönliche Unterlagen liegen.
Zusätzlich wird es aktiv als Installationsziel für Spiele beschrieben
(`WindowsApps`, `WpSystem`, `.GamingRoot`) — Dauerschreiblast auf einer Platte
mit Lesefehlern.

Am 07./08.08.2026 traten ausserdem **1.157 `disk`-Warnungen 153** und 15
`Ntfs`-140-Meldungen („Gerät-Zeitüberschreitung", Seagate Portable, USB) auf,
zeitgleich mit dem Rettungsscan über G:, H:, I:, J:, O:. Seither nichts mehr,
und die Seagate zeigt 0 unkorrigierte Fehler — also eher Last- oder
USB-Energiespar-bedingt als ein Medienschaden.

### Dateisystemprüfung 16.08.2026 (`chkdsk /scan`, nur lesend)

| Laufwerk | Ergebnis | Fehlerhafte Sektoren | Dauer |
|---|---|---|---|
| G: BackUp | sauber, keine Probleme | **0 KB** | 2,5 Min |
| H: Music Sync | **Fehler, „müssen offline behoben werden"** | **0 KB** | 2,2 Min |
| J: Extern_BackUp | `chkdsk` meldete „RAW" — **nicht reproduziert** | — | — |

**0 KB fehlerhafte Sektoren heisst: kein Medienschaden.** Die Fehler auf H: sind
beschädigte NTFS-Verwaltungsdaten, wie sie unsaubere Abschaltungen erzeugen — die
Stromausfälle oben hinterlassen also bereits Spuren. Behebung mit
`chkdsk H: /spotfix` (kurz, gezielt, hängt das Volume nur Sekunden aus — **nicht**
zu verwechseln mit einem vollen `chkdsk /f`).

Zur RAW-Meldung auf J:: `Get-Volume` zeigte unmittelbar danach NTFS/`Healthy`,
Dateien waren normal lesbar, und im Systemprotokoll steht für den Zeitpunkt
**kein** `disk`-153 und kein `Ntfs`-140. Ursache ungeklärt, Verdacht auf einen
einmaligen Zugriffsaussetzer. Nicht als Datenverlust fehldeuten.

Beim Systemstart nach dem Stromausfall vom 16.08.2026 hat Windows um 11:07 alle
Volumes geprüft (C:, O:, G:, H:, I:, J:) und jedes per `Ntfs`-98 als „fehlerfrei"
gemeldet.

### Was beim USB-Thema schon geprüft ist

**Energiesparen scheidet als Ursache aus** (geprüft 16.08.2026): Das aktive
Schema ist „Ultimative Leistung", selektives USB-Energiesparen steht im
Netzbetrieb auf *Deaktiviert*, „Festplatte ausschalten nach" auf 0 (nie). Die
1.157 Zeitüberschreitungen vom 07./08.08. kamen von echter Last auf der
USB-Brücke, nicht vom Stromsparen. Diese Einstellungen also nicht erneut prüfen.

Die Zeugnisse und Bewerbungsunterlagen aus `J:\MAKS` sind im Archiv gespiegelt
(`Dokumente\Privat\Bewerbung`, `Dokumente\Gewerblich\Maks Sound`).

## Sicherung des Vaults

**Seit 16.08.2026 liegt eine vollständige Kopie auf `G:\MaxHirn-Sicherung`.**
Vorher existierten Vault und Archiv ausschliesslich auf C: — bei einem Rechner
mit unangekündigten Stromausfällen die grösste Einzellücke.

| | |
|---|---|
| Quelle | `C:\Users\faupe\Documents\BrainFiles\MaxHirn` |
| Ziel | `G:\MaxHirn-Sicherung` (Seagate Portable, USB) |
| Umfang | 188.105 Dateien, 93,08 GB |
| Geprüft | Dateizahl und Bytes auf beiden Seiten identisch, Differenz 0 |
| Dauer | **8 h 54 min** bei 3,3 MB/s |

### Nachmessung 19.08.2026 — Quelle und Sicherung stimmen nicht mehr überein

| | Dateien | Bytes | GiB |
|---|---|---|---|
| Sicherung `G:\MaxHirn-Sicherung` | 188.102 | 99.944.953.562 | **93,08** |
| Quelle `MaxHirn\` heute | 188.214 | 47.100.417.109 | **43,87** |

Nahezu gleiche Dateizahl, halbe Datenmenge. Die Ursache ist **eine einzige
Datei**: `Archiv\Posteingang\Maximilianbackup0924`, 52.428.800.000 Bytes
(**48,83 GiB**). Sie steckt noch in der Sicherung, ist aber aus der Quelle
verschwunden. 93,08 − 48,83 = 44,25 GiB, gegen 43,87 GiB heute — der Rest ist
normale Fluktuation (+112 Dateien). Damit ist auch die „48,83 GB in 8 Minuten"-
Durchsatzmessung weiter unten dieselbe Datei.

**Folge:** Von diesem 48,8-GB-Abbild existiert nur noch die Kopie auf G:. Der
Sicherungsbefehl arbeitet ohne `/MIR` und löscht nichts, sie bleibt also
erhalten — aber sie liegt einfach, auf einer USB-Platte am selben Rechner.
Wenn das Abbild noch gebraucht wird, gehört es an einen zweiten Ort; wenn nicht,
kann es weg und die Sicherung schrumpft um über die Hälfte.

**Für künftige Prüfungen:** „Dateizahl und Bytes identisch" taugt nur unmittelbar
nach dem Lauf. Ohne `/MIR` ist die Sicherung additiv — sie wächst gegenüber der
Quelle und divergiert planmäßig. Nicht als Fehler lesen.

### Auffrischen: `sichern.ps1` (seit 19.08.2026)

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\faupe\Documents\BrainFiles\MaxHirn\sichern.ps1"
powershell -ExecutionPolicy Bypass -File "...\sichern.ps1" -NurPruefen   # nur die Zugangsdaten-Pruefung
```

Das Skript prüft erst auf Klartext-Zugangsdaten und kopiert dann. Es ersetzt den
früheren nackten robocopy-Aufruf, der weiter unten dokumentiert war.

**Ausschlüsse:** `GitHub .venv __pycache__ node_modules .git`. Gemessen
19.08.2026 sind das **119.095 der 188.214 Dateien (63 %)**, aber nur
**2,2 der 43,9 GB (5 %)**. Da der Durchsatz an der Dateizahl hängt und nicht an
der Datenmenge, ist das der wirksamste Hebel. Alles Ausgeschlossene ist aus Git
bzw. `pip` reproduzierbar.

**Erster Lauf mit Ausschlüssen (19.08.2026, 20:37):** 69.173 statt 188.214
Dateien durchsucht, 158 geänderte Dateien / 245 MB kopiert, **48 Sekunden**,
robocopy-Code 3 (Erfolg). Der Vergleich zu „8 h 54 min" hinkt — das war der
Erstlauf mit allem; hier zählt, dass ein Tageslauf jetzt unter einer Minute
bleibt.

Der frühere Befehl, falls das Skript einmal nicht zur Hand ist:

```
robocopy "C:\Users\faupe\Documents\BrainFiles\MaxHirn" "G:\MaxHirn-Sicherung" /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL /XD GitHub .venv __pycache__ node_modules .git
```

**Die Dauer realistisch einplanen.** 93 GB klingen nach einer knappen Stunde, es
sind aber knapp neun — 188.000 überwiegend kleine Dateien über USB laufen mit
rund 3 MB/s, nicht mit der Nenngeschwindigkeit der Schnittstelle. Ein
Auffrischungslauf ist deutlich schneller, weil nur Änderungen übertragen werden.

Grenze dieser Sicherung: Sie hängt am selben Rechner und teilt dessen Risiko.
Sie ersetzt keine Kopie ausser Haus.

**Vor jeder Vollsicherung auf Klartext-Zugangsdaten prüfen.** Eine Vollkopie
nimmt alles mit — auch Passwortexporte, die dann zusätzlich auf einer externen,
transportablen Platte liegen. Beim Erstlauf am 16.08.2026 wanderten so drei
Klartextdateien mit (zwei Chrome-CSV-Exporte, eine alte HTM-Datei); sie wurden am
19.08.2026 in Quelle **und** Sicherung gelöscht. Prüfbefehl vor dem nächsten Lauf:

```
Get-ChildItem <Vault> -Recurse -File -Force |
  Where-Object { $_.Name -match '(?i)passw|zugangsdaten|credentials|api.?key|token|secret|zugaenge|\.env' -or $_.Extension -in '.csv','.htm' }
```

**Dieses Muster ist überholt — die Prüfung steckt jetzt in `sichern.ps1`.**
Zwei Lehren aus dem 19.08.2026:

1. Die ursprüngliche Fassung hätte eine Datei namens `API_Keys.md` nicht
   gefunden. Ein Muster, das nur deutsche Wörter kennt, greift bei englisch
   benannten Schlüsseldateien nicht.
2. Die naheliegende Erweiterung um `key|token|secret` lieferte **über 140
   Fehltreffer** — Guitar-Pro-Tabs mit „Secret" im Songtitel, Blender-Doku über
   „Keying", jede `.csv` aus `Handel\daten`. Ein Prüfbefehl, dessen Ergebnis man
   durchblättern muss, wird nicht benutzt. `sichern.ps1` prüft deshalb gegen
   präzise Dateinamensmuster und meldete **12 Treffer, alle relevant**.

### Befund vom 19.08.2026 — noch offen

| Datei | Bewertung |
|---|---|
| ~~`Archiv\Dokumente\Privat\Bitlocker\firefox.csv`~~ | **erledigt 23.08.2026 — in Quarantäne verschoben** |
| ~~`Archiv\Software\icloud 26\firefox.csv`~~ | **erledigt 23.08.2026 — in Quarantäne verschoben** |
| `Archiv\Software\Linux\Unraid\config\ssh\ssh_host_{rsa,ed25519,ecdsa}_key` | **private SSH-Hostschlüssel des Unraid-Servers** |
| `Archiv\Software\Linux\Unraid\config\{passwd,shadow,smbpasswd,secrets.tdb}` | Benutzer- und Samba-Hashes |
| ~~`Werkstatt\Worktrees\investment\OKX_API.env`~~ | **erledigt 12.09.2026 — Datei liegt in `Wissen\OKX_API.env` neben der Schlüsselablage; die Streukkopien im Archiv-Posteingang und auf `J:` sind entfernt** |
| ~~`Archiv\ArchivSuche\acoustid_key.txt`~~ | **erledigt 12.09.2026 — enthält einen 11 Byte langen AcoustID-Schlüssel, keinen Leerrest. Das Werkzeug liest ihn über `--acoustid-key` oder `ACOUSTID_KEY`; die Datei ist die Ablage des Werts und steht deshalb in der Zugangsdaten-Prüfung als bewusst.** |
| `Archiv\Software\Linux\Unraid\config\plugins\unbalanced\unbalanced.env` | prüfen |

Der Eintrag weiter oben, am 19.08.2026 seien „drei Klartextdateien in Quelle und
Sicherung gelöscht" worden, betraf **Chrome**-Exporte. Die Firefox-Exporte waren
davon unberührt und lagen weiterhin in Quelle **und** Sicherung. Das alte
Prüfmuster konnte `firefox.csv` nicht finden.

### Quarantäne statt Löschen (23.08.2026)

Alle vier Firefox-Kopien liegen seit 23.08.2026 in

    C:\Users\faupe\Zugangsdaten-Quarantaene\

**Bewusst außerhalb des Vaults** — alles unterhalb von `MaxHirn\` wandert bei
jeder Sicherung wieder auf die externe Platte, und genau das war das Problem.
Verschoben, nicht gelöscht: Wiederherstellung bleibt möglich, bis Max entschieden
hat.

| Datei | Herkunft | mtime |
|---|---|---|
| `firefox_Quelle_Bitlocker_20260823.csv` | Vault, `Dokumente\Privat\Bitlocker` | 23.09.2020 |
| `firefox_Quelle_icloud26_20260823.csv` | Vault, `Software\icloud 26` | 07.04.2023 |
| `firefox_Sicherung_Bitlocker_20260823.csv` | G:, gleicher Pfad | 23.09.2020 |
| `firefox_Sicherung_icloud26_20260823.csv` | G:, gleicher Pfad | 07.04.2023 |

**Alle vier sind byteidentisch:** 16.245 Bytes, SHA-256 beginnt bei allen mit
`06A07F0C17797932`. Es ist also **ein** Export in vier Kopien, trotz
unterschiedlicher Zeitstempel — die mtimes stammen vom jeweiligen Kopiervorgang,
nicht von einem erneuten Export.

**Was noch zu tun ist:** Die Datei ist von 2020 bzw. 2023. Passwörter aus einem
so alten Klartextexport, die heute noch gelten, gehören geändert — nicht nur die
Datei gelöscht. Danach die Quarantäne leeren.

Die restlichen Positionen der Tabelle sind unberührt — Max entscheidet je Position.

Zugangsdaten gehören nach [[Zugaenge]] oder in die Windows-Benutzervariablen,
nicht in Projekt- oder Softwareordner.

Verschlüsselte Ablagen (`PW.kdbx`, `PW2.kdbx`) und die ELSTER-Zertifikate
(`.pfx`) sind unproblematisch und bleiben. Nur Klartext ist das Problem.

**Beim Löschen solcher Dateien nicht über Textpfade gehen.** Zwei der sechs
Kopien hiessen `Chrome-Passwörter.csv` in **zerlegter** Unicode-Form (NFD);
`Remove-Item -LiteralPath` mit zusammengesetztem „ö" meldete „Pfad existiert
nicht", obwohl `Get-ChildItem` sie gefunden hatte. Lösung: die Dateiobjekte aus
`Get-ChildItem` direkt mit `.Delete()` verwenden, statt Pfade als Zeichenketten
weiterzureichen. Git Bash konnte diese Namen gar nicht öffnen.

**Durchsatz hängt an der Dateizahl, nicht an der Datenmenge.** Gemessen auf
derselben USB-Anbindung: 93 GB in 188.105 Dateien → **3,3 MB/s** (8 h 54 min);
eine einzelne Datei von 48,83 GB → **102 MB/s** (8 min). Weder Platte noch
Schnittstelle sind langsam — viele kleine Dateien sind es.

### Nebenbefund aus dem Sicherungslauf

**Neun Stunden Dauerlast über USB erzeugten null Datenträgerfehler** — kein
`disk`-153, kein `Ntfs`-140 — und der Rechner lief dabei durch, ohne Kernel-Power
41. Zwei Schlüsse:

- Die 1.157 Zeitüberschreitungen vom 07./08.08. lassen sich **nicht** mit „USB
  unter Last" erklären. 572 davon entfielen auf „Datenträger 4" an Blockadresse
  `0x0` — die sterbende Platte, heute nicht mehr angeschlossen.
- Die Stromausfälle werden **nicht durch dauerhaft hohe Last ausgelöst**. Das
  spricht eher für Lastwechsel oder einen Wackelkontakt als für ein schlicht zu
  schwaches Netzteil.

## Windows Search stillgelegt (Stand 2026-08-16)

> **Seit dem 28.08.2026, 16:00:04 hält die Stilllegung wieder** — diesmal über
> den Starttyp: `Get-Service WSearch` → `StartType = Disabled`, `Status =
> Stopped`. Letzter Absturz um 15:59:41, seither null in 77 Minuten (gemessen
> 17:16). Zahlen und Folgen in „Nachmessung 28.08.2026, 17:15" am Dateiende.
>
> **Überholt seit 25.08.2026 — die Stilllegung hielt nicht, und sie war
> am 28.08.2026 bis 16:00 aufgehoben.** Nachgemessen an diesem Tag:
> `Get-Service WSearch` → `StartType = Automatic`, `Status = Stopped`. Im
> Systemprotokoll stehen allein für den 28.08. **815** Abstürze (ID 7034),
> davor 1.229 am 27.08., 1.269 am 26.08. und 1.487 am 25.08.; der jüngste
> Eintrag lag beim Messen 2 Minuten zurück. Der Puffer reicht nur noch bis zum
> 24.08. zurück — **das Protokoll überschreibt sich alle vier Tage selbst und
> vernichtet damit die Spuren der Abstürze oben.** Das ist der eigentliche
> Schaden dieses Fehlers, nicht die fehlende Suche.
>
> Ergaenzung 28.08.: Die Fehlermeldung lautet unverändert „Das System kann den
> angegebenen Pfad nicht finden", `SetupCompletedSuccessfully = 0`, und eine
> `Windows.edb` existiert nicht. Der Datenordner
> `C:\ProgramData\Microsoft\Search\Data` ist zwar vorhanden, aber leer.
>
> Früherer Stand vom 25.08.2026: `HKLM\SYSTEM\CurrentControlSet\Services\WSearch`
> → `Start = 2`
> (**Automatisch**), nicht 4 (Deaktiviert). Folge: Die Absturzzyklen laufen
> wieder. Im Systemprotokoll stehen für die letzten 7 Tage **16.111**
> WSearch-Dienstereignisse — 8.054 × ID 7023 (Dienst mit Fehler beendet),
> 8.024 × ID 7034 (unerwartet beendet), jüngstes am 25.08.2026 21:32. Das sind
> rund **1.150 Fehlstarts pro Tag**, etwa alle 75 Sekunden. Das Protokoll füllt
> sich erneut: 27,1 von 64 MB.
>
> Wer den Starttyp zurückgestellt hat, ist **nicht geklärt** — in Frage kommen
> ein Windows-Update oder die DISM-Reparatur; belegt ist keines von beidem.
> Nötig, um es wieder abzustellen (als Administrator):
> `Set-Service WSearch -StartupType Disabled`
>
> **Ein `Start-Service WSearch` ist ausdrücklich falsch** — es widerspricht der
> Entscheidung unten. Der Starttyp gehört auf Deaktiviert, nicht der Dienst
> gestartet.

`WSearch` steht bewusst auf **Deaktiviert**. Grund: Der Dienst stürzte ab dem
05.08.2026 alle ~29 Sekunden ab und startete neu — **27.414 Zyklen in 9,2 Tagen**,
danach nochmals rund 1.260. Das hat das Systemprotokoll (damals 20 MB, umlaufend)
restlos überschrieben; Ereignisse vor dem 05.08.2026 sind verloren. Das Protokoll
steht deshalb jetzt auf 64 MB.

Fehlerbild: `0x80070003` („Pfad nicht gefunden") und `0x80070660`. In der Registry
unter `HKLM\SOFTWARE\Microsoft\Windows Search` ist `SetupCompletedSuccessfully = 0`,
die Schlüssel `CatalogNames` und `CatalogList\…\SystemIndex` sind **leer**. Der
Dienst löscht bei jedem Versuch sein Datenverzeichnis und scheitert, bevor er
`Applications\Windows` darunter anlegen kann.

Was **nicht** hilft (alles geprüft): Ordner von Hand anlegen, Rechte setzen,
Zähler zurücksetzen, Umgebungsvariablen — die sind in Ordnung. `DISM
/RestoreHealth` fand zwar echten Schaden am Komponentenspeicher und hat ihn
repariert (danach `sfc` sauber), **die Suche blieb aber defekt**. Nützlicher
Nebeneffekt: Seither installiert Windows Update wieder erfolgreich, nachdem
zuvor drei Updates scheiterten (`0x80073D02`, `0x8024200B`).

Offener Lösungsweg: **In-Place-Reparaturinstallation** (Windows-11-ISO,
`setup.exe`, „Dateien und Apps behalten"). Blockiert durch die Stromausfälle
oben — erst Netzteil, dann Installation.

Praktisch verschmerzbar, weil die Dateisuche über das eigene Archivwerkzeug
läuft (`Archiv/ArchivSuche`) und nicht über den Windows-Index. Betroffen sind
Startmenü-Dateitreffer und die Outlook-Suche.

## Onboard-Netzwerkkarte defekt (nicht reparierbar)

`Intel(R) Ethernet Connection (2) I219-V` meldet im Geräte-Manager `Error`, der
Adapter steht auf `Not Present`. Das Treiberprotokoll `e1dexpress` nennt am
06.08.2026 den Grund: **ID 25 „The MAC address on the network adapter is
invalid"**, dazu ID 24 „Unable to start the network adapter".

**Nicht durch Nachtragen der MAC zu beheben.** Die Adresse liegt im NVM des
Mainboard-Chips; ist diese Region beschädigt, hilft kein Eintragen von aussen.
Die Karte ist defekt, nicht falsch konfiguriert — also keine Zeit mit
Treiberneuinstallation oder Intel-Werkzeugen verbrennen.

Praktisch folgenlos: Das Netz läuft über den `Realtek USB GbE Family Controller`
(1 Gbit/s).

**Die Karte ist bereits deaktiviert — hier ist nichts mehr zu tun.** Geprüft am
16.08.2026: Problemcode `CM_PROB_DISABLED`, „This device is disabled. (Code 22)".

Wichtig zum Lesen von Befunden: **`Get-PnpDevice` meldet für abgeschaltete Geräte
`Status = Error`.** Das ist die Bezeichnung für „aus", keine Störung — im
Geräte-Manager erscheint ein Pfeil nach unten, kein Warndreieck. Wer nur auf
`Status -eq 'Error'` filtert, hält deaktivierte Geräte fälschlich für defekt.
Immer zusätzlich `Problem` bzw. `ProblemDescription` abfragen.

Ganz aus der Geräteliste verschwindet die Karte nur, wenn Onboard-LAN im BIOS
abgeschaltet wird. Rein kosmetisch.

## iCloud Photos

Die Junction `C:\Users\faupe\iCloudPhotos` zeigt seit 08.08.2026 auf
`J:\iCloudPhotos`. Vorher zeigte sie auf I:, das mit 49,6 GB zu klein ist: Die
Bibliothek umfasst 30.635 Mediendateien, geschätzt rund 140 GB.

**iCloud für Windows 15.9 kann keine reduzierten Kopien.** Der Fotos-Dialog kennt
nur `PhotosToggle`, `PhotosFolderSelection`, `AlbumsToggle`, `HEIFCheckBox`,
`HDRCheckBox`, `EnableNTFS` — eine Option „Speicher optimieren" wie unter iOS und
macOS gibt es nicht. Es werden immer Originale geladen, der Platz muss also real
vorhanden sein. `HEIFCheckBox` aktiv lassen: Ohne sie wandelt iCloud HEIC in JPEG
um, und das wird grösser statt kleiner.

Weil das Ziel ein USB-Laufwerk ist, kehrt das Explorer-Problem zurück, falls die
WD My Book abgezogen wird oder ausfällt. Ein internes Ziel wäre robuster, dort
ist aber kein Platz frei.

**Das ist seit 2026-08-14 keine theoretische Sorge mehr:** Genau diese Platte
zeigt 479 unkorrigierte Lesefehler (siehe „Zustand der Laufwerke"). Die
Mediathek mit 30.635 Dateien liegt damit auf dem schwächsten Laufwerk im System.

## Nachmessung 28.08.2026, 17:15 — Stand nach den drei Eingriffen

Gemessen 17:15–17:17, Rechner lief seit dem Start um **15:19:36** (1 h 56 min).
Drei der vier offenen Systempunkte sind damit erledigt, einer bleibt offen.

| Punkt | Stand | Messwert |
|---|---|---|
| Auslagerungsdatei auf `G:` | **behoben** | `PagingFiles` enthält nur noch `c:\pagefile.sys 0 0` und `o:\pagefile.sys 4096 16384`; `G:\pagefile.sys` existiert nicht |
| Windows Search | **stillgelegt** | Starttyp am 28.08. um **16:00:04** auf „Deaktiviert" gesetzt (Ereignis 7040), letzter Absturz **15:59:41** |
| `J:` (WD My Book) | **wieder da** | `Extern_BackUp`, 1.953 GB, davon 246 GB frei, `Healthy`; Junction `C:\Users\faupe\iCloudPhotos` löst wieder auf |
| Echtzeituhr | **erklärt** | −0,120 s gegen `time.windows.com` (zwei Proben, 17:17:22 und 17:17:24) |
| Abstürze ohne Bluescreen | **offen** | seit dem Start kein Kernel-Power 41 — aber 1 h 56 min ohne einen einzigen Standby-Zyklus sagen nichts |

### Was das Abschalten von Windows Search gebracht hat

Der Dienst stürzte in sieben Tagen **16.926-mal** ab (dazu 8 Ereignisse unter dem
Namen `WSearch` und eines der Funktionssuche-Ressourcenveröffentlichung).
Allein zwischen dem Start um 15:19:36 und 15:59:41 waren es **984** — rund
**24 Abstürze pro Minute**. Seit 16:00:04 steht der Zähler bei **null**,
gemessen über 77 Minuten.

Sichtbare Folge: **Das Systemprotokoll reicht wieder bis zum 05.08.2026, 19:39
zurück** statt nur vier Tage. Genau das war der eigentliche Schaden — die
Absturzspuren wurden schneller überschrieben, als sie auswertbar waren.

### Die Echtzeituhr geht wieder richtig

Die 68-Minuten-Korrektur fand am 28.08. um **15:20:12** statt, also 36 Sekunden
nach dem Kaltstart um 15:19:36. Das passt zum CMOS-Reset: Der leert die RTC, der
Zeitdienst zieht sie beim ersten Start einmal gerade. **Seither kein weiterer
Sprung**, und die Abweichung liegt bei 0,12 Sekunden. Ein defekter
Uhrenbaustein oder eine leere CMOS-Batterie würde erneut driften — beides ist
damit vorerst ausgeschlossen, aber nicht bewiesen: Ein zweiter Messpunkt in
einigen Tagen entscheidet es.

### Negativbefunde (geprüft, war es nicht)

- **WHEA-Logger: 0 Ereignisse in 30 Tagen.** Keine Fehler auf CPU-, RAM- oder
  PCIe-Ebene. Diese Ebene ist damit zum wiederholten Mal ausgeschlossen.
- **Keine Plattenfehler.** Von `disk`, `Microsoft-Windows-Ntfs` und `volmgr`
  kamen in sieben Tagen nur 40 Ereignisse der ID **98** — allesamt
  Informationen der Bauart „Volume `J:` ist fehlerfrei". Kein einziges 153
  (wiederholter E/A-Fehler) und kein 140 (NTFS-Warnung).
- **Kernel-Power 41 unverändert neun Stück** seit dem 08.08., der letzte am
  28.08. um 14:11:19 — **vor** den Eingriffen. Ob sie ausbleiben, ist noch
  nicht messbar.

### Was jetzt gemessen werden muss

Der Nachweis für T-004 hängt an einem einzigen Ereignis: **einem Standby-Zyklus
ohne anschliessenden Reset.** Vier der neun Abstürze kamen 3–10 Minuten nach dem
Aufwachen aus S3. Solange der Rechner durchläuft, beweist Ruhe gar nichts.
Aussagekräftig wird es erst nach etwa fünf Standby-Zyklen oder zehn
absturzfreien Tagen — je nachdem, was zuerst eintritt.

### Zwischenstand 28.08.2026, 23:07 — Beobachtung zählt noch bei null Zyklen

Rechner läuft seit dem Start um 15:19:36 durch, **7,8 Stunden ohne Unterbrechung**.

| Messgrösse | Wert |
|---|---|
| Kernel-Power 41 seit dem Start | **0** (unverändert neun seit 08.08., letzter 28.08. um 14:11:19) |
| Standby-Zyklen seit dem Start (Kernel-Power 42/107) | **0** — der Rechner war kein einziges Mal im Standby |
| `WSearch`-Abstürze seit dem Start | **0** (vorher 24 pro Minute) |
| WHEA-Ereignisse, 30 Tage | **0** |
| `disk`/`Ntfs`/`volmgr`, 7 Tage | 46 × ID **98**, alle „Volume ist fehlerfrei" — kein 153, kein 140 |

**Die Ruhe beweist weiterhin nichts.** Ohne einen einzigen S3-Zyklus ist die
Bedingung, unter der vier der neun Abstürze auftraten, gar nicht eingetreten.
Der Zähler, auf den es ankommt, steht bei 0 von 5.

Die 46 Ereignisse der ID 98 sind dieselbe harmlose Sorte wie die 40 vom
17:15-Stand — Schattenkopie-Volumes, die sich selbst als fehlerfrei melden.
Der Anstieg ist kein Signal.

## Nachmessung 30.08.2026, 22:20 — die Beobachtung ist entschieden, negativ

Die am 28.08. um 16:00 gestartete Beobachtung ist **beendet, ohne dass der
Zähler je fünf Standby-Zyklen erreicht hat.** Sie musste nicht auslaufen: der
Rechner ist in der Zwischenzeit dreimal ausgegangen.

| Echter Zeitpunkt (aus 6008) | Kernel-Power 41 protokolliert | Vorlauf |
|---|---|---|
| 29.08.2026 10:45:10 | 11:04:47 | nach Beobachtungsstart |
| 29.08.2026 13:17:14 | 13:18:39 | 2,5 h nach dem vorigen |
| 30.08.2026 20:59:55 | 21:01:21 | 31,7 h nach dem vorigen |

**Damit sind es zwölf Vorfälle seit dem 08.08., nicht neun.** Die Zählung
„neun" stammt vom 28.08. und war ab dem 29.08. überholt.

### Standby scheidet als Ursache aus

Seit dem **28.08.2026, 06:46** hat der Rechner **keinen einzigen Standby-Zyklus**
mehr gehabt (kein Kernel-Power 42/107). Die drei neuen Abstürze fielen also in
eine Phase völlig ohne Standby — und traten trotzdem auf. Der Ablauf „3–10
Minuten nach dem Aufwachen aus S3", der die vier Vorfälle vom 20.–28.08.
verband, ist als **Begleiterscheinung entlarvt, nicht als Ursache**.

Das zeigt sich auch im Fingerabdruck der Ereignisse selbst:

| Datum | `Checkpoint` | `ConnectedStandbyInProgress` | `SystemSleepTransitionsToOn` |
|---|---|---|---|
| 14.08.–28.08. (sieben Stück) | **16** | teils true | **1** |
| 29.08. 11:04 | **0** | false | **0** |
| 29.08. 13:18 | **0** | false | **0** |
| 30.08. 21:01 | **0** | false | **0** |

Die Gegenmassnahmen vom 28.08. haben den Standby-Fingerabdruck also tatsächlich
beseitigt — die Abschaltungen gehen davon unbeeindruckt weiter, jetzt sogar
**dichter**: drei in zwei Tagen gegen sieben in den vierzehn Tagen davor.

### Korrektur: `SleepInProgress = 16` hat es nie gegeben

Die bisherige Notiz führte `SleepInProgress = 16` als Fingerabdruck der
jüngeren Vorfälle. **Das war eine Verwechslung.** Im Rohdatensatz eines 41ers
stehen beide Felder untereinander:

```
SleepInProgress = 0
...
Checkpoint = 16
```

`SleepInProgress` ist bei **allen zwölf** Vorfällen `0`, von 08.08. bis heute.
Der Wert 16 gehörte immer zu `Checkpoint`. Wer die Felder über
`.Properties[n]` per Index ausliest statt über den Namen, greift leicht daneben
— deshalb hier der Weg, der stimmt:

```powershell
Get-WinEvent -FilterHashtable @{LogName='System';Id=41;StartTime=(Get-Date).AddDays(-30)} |
  ForEach-Object { $x=[xml]$_.ToXml(); $d=@{}
    foreach($e in $x.Event.EventData.Data){$d[$e.Name]=$e.'#text'}
    "{0} | Chk={1} | Sleep={2}" -f $_.TimeCreated,$d['Checkpoint'],$d['SleepInProgress'] }
```

### Negativbefunde, erneut bestätigt (30.08.2026)

- **WHEA-Logger: 0 Ereignisse in 30 Tagen.** CPU, RAM, PCIe melden weiterhin nichts.
- **Keine Plattenfehler.** Von `disk`, `Ntfs`, `volmgr` in sieben Tagen nur
  73 × ID 98 („Volume ist fehlerfrei"). Kein 153, kein 140.
- **Kein Speicherabbild.** Weder `MEMORY.DMP` noch etwas in `C:\Windows\Minidump`.
- **Windows Search hält still.** Dienst `Stopped`/`Disabled`, **null** Abstürze
  seit dem 28.08. 16:00. Die 15.062 Einträge im 7-Tage-Fenster stammen
  sämtlich aus der Zeit davor. Als Absturzursache war der Dienst damit
  ohnehin ausgeschieden — er lief bei den drei neuen Vorfällen gar nicht.
- **Stille bis zur letzten Sekunde.** In den drei Minuten vor dem Abschalten am
  30.08. um 20:59:55 steht in System- und Anwendungsprotokoll **ein einziger**
  Eintrag (Configuration-Change-Monitor, 20:57:56). Kein Dienst, kein Treiber,
  keine Warnung. Ein Softwareabsturz hinterlässt so etwas nicht.

### Was daraus folgt

Der Standby-Zweig ist abgeschlossen. Von der Verdächtigenliste im Abschnitt
„Netzteildefekt 2026" bleiben die Punkte, die noch **nie geprüft** wurden:

1. **Stromzufuhr ausserhalb des Netzteils** — Kaltgerätekabel, Steckdosenleiste,
   Wandsteckdose. Billig, schnell, und noch offen. Deshalb zuerst.
2. **Das eingebaute alte Netzteil selbst**, gegengetestet mit einem bekannt
   guten, ausreichend dimensionierten Gerät — nicht mit einem weiteren Altteil.

Beides sind Handgriffe an der Hardware und damit Max' Sache. Nach dem Muster
aus Abschnitt „Bevor etwas verändert wird" gilt: **einen nach dem anderen**,
sonst ist hinterher unbekannt, welcher gewirkt hat. Bei einem Abstand von
zuletzt 2,5 bis 32 Stunden zeigt sich innerhalb von zwei bis drei Tagen, ob ein
Eingriff etwas gebracht hat.

### Nachgemessen wird mit dem Skript, nicht von Hand

`Routinen/absturz-nachmessen.ps1` fasst genau die Abfragen zusammen, die hier
zum Ergebnis gefuehrt haben — Protokollreichweite, echte Absturzzeitpunkte aus
6008, den Fingerabdruck der 41er, Standby-Zyklen und die Negativbefunde. Nur
lesend, keine Adminrechte noetig:

```powershell
powershell -ExecutionPolicy Bypass -File Routinenbsturz-nachmessen.ps1
```

Es liest die Ereignisfelder ueber ihren **Namen** aus, nicht ueber
`.Properties[n]` — der Indexzugriff war die Ursache der
`SleepInProgress`-Verwechslung oben.

## Monitore und PowerToys PowerDisplay (aus PowerToys-Report 02.09.2026)

Zwei Bildschirme, **beide direkt an DisplayPort** (VideoOutputTechnology 10):

| Windows | EDID-Kennung | echtes Modell (WMI) | Anzeige in Windows | DDC/CI |
|---|---|---|---|---|
| DISPLAY1 | `ACR0460` | Acer XB281HK | echtes Monitorprofil | **funktioniert** |
| DISPLAY2 | `ACI27A8` | **ASUS MG278** | „Generic PnP Monitor" | **antwortet nicht** |

**PowerDisplay steuert nur den XB281HK.** Für ihn liest das Modul die DDC/CI-Fähigkeiten
sauber aus und merkt sie sich in `PowerDisplay/monitor_state.json` (Helligkeit = VCP-Code
`0x10`, Kontrast = VCP-Code `0x12`). Die **ASUS MG278** liefert nach drei Versuchen eine
leere Capability-Zeichenkette; PowerDisplay verwirft sie mit
`monitor ignored — capabilities unavailable`.

**Unabhängig von PowerToys nachgestellt** (02.09.2026) mit
`Agenten/Routinen/monitor-ddc-pruefen.ps1` — direkte `dxva2.dll`-Abfrage:
- XB281HK: Capability-String + Helligkeit (0/70/100) kommen zurück.
- MG278: schon `GetCapabilitiesStringLength` schlägt fehl, Win32-Fehler
  **`0xC0262582`** (`ERROR_GRAPHICS_DDCCI_VCP_NOT_SUPPORTED`). Auch ein roher
  `GetMonitorBrightness` scheitert. Der Monitor führt DDC/CI schlicht nicht aus.

Das ist **kein PowerToys-Fehler** und über Software nicht umgehbar — jedes Werkzeug
(`ControlMyMonitor`, `Monitorian`, …) bekommt denselben Fehler. Fix liegt am Monitor:

1. MG278-OSD: **Menu → System Setup → DDC/CI → On**. Häufigste Ursache.
2. Hilft das nicht: MG278 ~30 s komplett vom Strom (nicht Standby), DP-Kabel
   prüfen/tauschen, anderen DP-Eingang am Monitor probieren.
3. Danach `monitor-ddc-pruefen.ps1` erneut laufen lassen; antwortet die MG278,
   in PowerToys → PowerDisplay „Monitore aktualisieren".

`WmiController: WMI DiscoverMonitors failed: WDM specific return code: 4200` bei jedem
Start ist **erwartbar** — die WMI-Helligkeitsklasse gibt es nur für Notebook-Panels, nicht
für externe Desktop-Monitore. Kein Fehler.

### Negativbefunde aus demselben Report

- **Kein Absturz.** Alle `EventViewer-PowerToys.*.exe.xml` sind 0 Byte — keine
  WER-Fehlereinträge für irgendeinen PowerToys-Prozess. Runner startete am 02.09. um
  00:56 sauber (elevated), Report um 16:12 gezogen.
- **PowerToys Run**, dutzende `System.IO.FileNotFoundException` für UWP-Logo-Dateien
  (`AppleInc.iCloud`, `Microsoft.Copilot`, …): von PowerToys selbst als
  „can be ignored" markiert. Rauschen, kein Defekt.
- **FancyZones** `Process path is empty` ×30: kosmetisch.
- **CmdPal**: Startfehler und fehlende `favorites.json`/`history.json` betrafen
  zwei **Fremd-Erweiterungen** (Aria2 Extension, Colors for Command Palette),
  nicht den PowerToys-Kern. Beide am 02.09.2026 entfernt
  (`Routinen/einmalig-20260902-cmdpal-erweiterungen-entfernen.ps1`); Neu-
  installation über den Microsoft Store jederzeit möglich.
- **AppXDeploymentServer**: ein `winget`-Upgrade von „CurrencyConverter for Command
  Palette" scheiterte am 30.08. mit `0x80073D02`, weil die alte Version noch lief.
  Einmalig, folgenlos.

## Claude Desktop Lock-Fehler (2026-09-02 22:40)

**Problem:** Sicherung schlug mit Code `3221225786` fehl.

**Ursache:** `0xC0000006` = `STATUS_CONFLICT_WITH_LOCK`. Die Sicherungsroutine
(`sichern.ps1`) versuchte, Vault-Dateien zu sperren und zu kopieren, während
Claude Desktop selbst noch offen war und eigene Locks auf den Dateien hielt.
Beide Prozesse blockierten sich gegenseitig.

**Fehlerursache:** Das Sicherungsskript hatte keine Schutzmaßnahme gegen parallel
laufende Claude-Instanzen — eine Folge der Mehrfachsitzungen-Regel aus
[[Schutzregeln]].

**Reparatur am 04.09.2026:**
- `sichern.ps1` um Abschnitt „2) Claude Desktop beenden" erweitert
- Vor der robocopy-Sicherung wird Claude (falls offen) beendet und
  mindestens 30 Sekunden gewartet
- Bei Timeout wird mit Warnung weitergecopy trotzdem versucht
- Hinweismeldung im Fehlerfall aufgenommen, die auf dieses Problem hinweist

**Messung:** Fehlercode 3221225786 sollte damit nicht mehr vorkommen. 

**Verwandt:** [[Schutzregeln]] (Mehrfach-Sitzungen), [[Hardware-Checkliste-D5]] (Schrittfolge D5/Kernel-Power 41), `Agenten/sichern.ps1` (Implementierung)

## Nachmessung 30.09.2026 — der gemeinsame Nenner der Abschaltungen

**Kurzfassung:** Die Abschaltungen sind keine Stromausfaelle im engeren Sinn,
sondern die Folge von **Speichernot**. Windows meldet sie selbst, 296-mal in 14
Tagen (Ereignis 2004, `Resource-Exhaustion-Detector`). Die beiden Verursacher
stehen in fast jeder dieser Meldungen an der Spitze: **`llama-server.exe`**
(LM Studio, bis 18,0 GB) und **`com.docker.sailor.exe`** (Docker Desktop,
dauerhaft 5,6-15,8 GB).

### Stand von T-004

21-mal Ereignis 41 seit 08.08.2026 (am 30.08. waren es 12), 19-mal mit 6008.
Die letzte Abschaltung war am **25.09.2026, 16:12**; seit dem Neustart am
29.09. 21:06 lief der Rechner 13,8 h ohne Abschaltung.

**Alle 18 belegten Abschaltzeiten liegen zwischen 10:45 und 00:30 Uhr** —
12:31, 14:56, 11:05, 16:13, 16:16, 18:00, 14:16, 10:45, 13:17, 20:59, 16:57,
22:55, 16:33, 23:40, 16:41, 00:30, 13:12, 16:12. Keine einzige nachts, sechs
im Fenster 16:00-17:00. **Damit ist "passiert im Leerlauf" endgueltig
ausgeschlossen** — es passiert unter Last.

### Zwei Abschaltungen mit belegter Kette

| Datum | Letztes Systemschreiben (6008) | Ereignis 2004 | Start danach |
|---|---|---|---|
| 24.09.2026 | 13:12:06 | 13:27:23 und 13:27:37 (`svchost.exe` 6,4 GB) | 13:32:24 |
| 25.09.2026 | 16:12:25 | 16:12:55 (`llama-server.exe` 18,0 GB) | 16:36:48 |

Am 25.09. folgt auf die 2004-Meldung um 16:12:55 der Absturz von
`llama-server.exe` um **16:12:56** — eine Sekunde spaeter — und der Rechner kam
erst um 16:36:48 zurueck.

**Die 6008-Zeit ist nicht der Todeszeitpunkt**, sondern das letzte Schreiben ins
Systemprotokoll. Am 24.09. lief die Maschine danach noch mindestens 15 Minuten
weiter (2004 um 13:27) — das Protokoll stand still, die Maschine nicht. Wer die
6008-Zeit als Absturzzeit liest, sucht im falschen Fenster.

### Die llama-server-Abstuerze sind Folge, nicht Ursache

13 von 14 `llama-server.exe`-Abstuerzen der letzten 8 Tage liegen **innerhalb
von 15 Minuten um ein 2004-Ereignis**. Fehlercode `0xc0000409`
(`STATUS_STACK_BUFFER_OVERRUN` = `__fastfail`), Modul `ucrtbase.dll`, immer
derselbe Offset `0xa527e` — auch bei `python.exe`. Das ist kein Fehler in
llama.cpp, sondern die C-Laufzeit, die bei fehlgeschlagener Anforderung
abortiert. Betroffen ist der mitgelieferte Server aus
`C:\Users\faupe\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.47.0`.

### Die harte Grenze: 75,7 GB, und warum sie nicht wachsen konnte

```
Commit-Grenze        75,7 GB   (63,7 GB RAM + 8 GB C: + 4 GB O:)
C:\pagefile.sys      8192 / 8192    <- FEST, kann NICHT wachsen
O:\pagefile.sys      4096 / 16384   <- gewachsen ist sie nie
Peak-Auslastung      652 MB (C:) und 715 MB (O:)
```

Die Auslagerungsdateien sind praktisch unbenutzt, **weil sie nicht wachsen
konnten**. Die Commit-Grenze stand damit bei 75,7 GB fest.

Beleg fuer die Folge: am **30.09.2026 zwischen 10:12 und 10:46** sind in 35
Minuten **31 Anwendungen abgestuerzt** — `chrome_proxy.exe`, `WerFault.exe` und
`python.exe` mit `0xc000012d` (`STATUS_COMMITMENT_LIMIT`), dazu PowerShell mit
`OutOfMemoryException`, `Hermes.exe`, `chrome.exe`, `python.exe` (3x),
**`dwm.exe`** (der Bildschirm flackert, wenn der Compositor neu startet),
`Docker Desktop` (10x in 8 Minuten), `claude.exe`, `LogiOverlay`, `es2utility`,
`WindowsTerminal`. Neun verschiedene, voneinander unabhaengige Programme in
einer halben Stunde sind kein Softwarefehler.

### Was am 30.09.2026 zusaetzlich messbar war

- **Der Hermes-Gateway ist an derselben Speichernot gestorben.**
  `gateway_state.json` nennt PID 34732, `gateway_state: starting`,
  `restart_requested: true`, `updated_at 08:44:02 UTC` (= 10:44 CEST) — der
  Prozess existiert nicht, kein Prozess mit `gateway`-Kommandozeile, Ports 8644
  und 9900 sind frei. Der Waechter lief um 10:57:54 mit Ergebnis 0 und **hat ihn
  nicht geheilt**: er liest `gateway_state: starting` als "laeuft gerade an" und
  wartet. Eine tote PID im Zustand `starting` ist ein blinder Fleck.
- **Auch nicht erreichbar:** OmniRoute (20128) und der Bonsai-Server (8080).
  Ollama (11434) und der Bus (8787) laufen.
- **Energiesparplan ist "Energiesparmodus"** (`a1841308-...`). Auf einem
  Arbeitsrechner mit i9-7940X ungewoehnlich — nicht geaendert, nur notiert.

### Laufwerksordnung: die Tabelle oben ist ueberholt

| | 19.08.2026 notiert | 30.09.2026 gemessen |
|---|---|---|
| J: WD My Book | Disk 3, frei 270,9 GB | **Disk 4**, frei 174,6 GB |
| Q: SanDisk | Disk 3 (ausser Haus) | **Disk 3** |
| E: Netac | Disk 4 | nicht angeschlossen |

J: hat in sechs Wochen rund 96 GB dazubekommen. Die 479 unkorrigierten
Lesefehler bleiben; **eine neue** `disk`-153-Meldung am 24.09. 15:16:57 auf
Disk 4 (LBA `0x176635f8` = rund 187 GB) — **nicht LBA 0**, also kein elektrisch
toter Datentraeger, sondern ein wiederholter E/A-Versuch auf der bekannten
Platte.

### Negativbefunde (geprueft, war es nicht)

- **0** WHEA-Logger-Ereignisse in 30 Tagen — CPU/RAM/PCIe sauber.
- **0** Speicherdiagnose-Befunde.
- **0** Ereignisse 51/7/11/55 (Platten-/Dateisystemfehler) in 30 Tagen.
- **1** `disk`-153 in 30 Tagen (siehe oben), **0** volmgr.
- GPU 50 Grad, 54,86 W von 220 W, 0 % Auslastung, 1129 von 8192 MiB belegt.
  `nvlddmkm` 7x Id 13 und 4x Id 153 in 30 Tagen — beobachtet, kein Muster.
- Treiber 617.14 (am 22.09. war es 616.92).

**Offen:** die Commit-Grenze ist die einzige Groesse, die sich ohne Hardware
aendern laesst und die direkt auf beide Abschaltungen wirkt (T-215); der
Energiesparplan ist ein zweiter, unabhaengiger Verdacht (T-216).


## Gateway-Ausfall 30.09.2026 — der Launcher konnte gar nichts starten

Drei Dinge kamen zusammen; das erste ist die Speichernot (Abschnitt oben),
das zweite ein Fehler im Startweg, das dritte ein Rueckschritt durch eine
automatische Sammel-Routine.

### Der Gateway starb an der Speichernot

Der Gateway schreibt seinen eigenen Lebenslauf. Der Eintrag beim naechsten
Start lautet woertlich:

    Previous gateway life (pid=34732, started_at=2026-09-30T08:40:29Z)
    exited UNCLEANLY (no exit path ran - SIGKILL / OOM / VM death ...)
    last_heartbeat_at=2026-09-30T08:03:29Z

Ab 10:33 versuchte der Waechter `MaxHirn-Gateway-Waechter` alle zwei Minuten
einen Neustart ("kein Gateway-Prozess - Neustart ausgeloest") - und es
passierte nichts. Das ist das eigentliche Raetsel gewesen.

### Der Startweg: `WScript.Shell.Run` mit Fensterstil 0 startet keine Konsolenprogramme

Gemessen mit zwei Proben aus `cscript` heraus (`WScript.Shell.Run`):

| Ziel                    | Fensterstil | Prozess entsteht? |
|-------------------------|-------------|-------------------|
| `cmd /c echo ...`       | 0 (versteckt) | **nein**        |
| `cmd /c echo ...`       | 2           | nein              |
| `cmd /c echo ...`       | 3           | ja                |
| `cmd /c echo ...`       | 7           | nein              |
| `cmd /c echo ...`       | 8           | ja                |
| `python.exe` (Konsole)  | 0           | **nein**          |
| `python.exe` (Konsole)  | 1           | ja                |
| `pythonw.exe` (GUI)     | 0           | **ja**            |

In den Nein-Faellen meldet `sh.Run` **keinen Fehler** - der Aufruf kehrt sauber
zurueck, der Prozess entsteht nicht. `sh.Exec` und das FileSystemObject
arbeiten normal, es trifft also nur diesen einen Weg.

Die Launcher-Zeile lautete
`...\python.exe -m hermes_cli.main gateway run", 0, False` und konnte deshalb
nie etwas starten. Sie steht jetzt auf `pythonw.exe` (GUI-Programm, laeuft mit
Stil 0 versteckt). Der Waechter suchte zugleich hart nach `Name='python.exe'`
und `ProcessName -eq 'python'` - er haette einen gesunden pythonw-Gateway
nicht gesehen und im Zwei-Minuten-Takt weiter neu gestartet (dieselbe
Fehlerklasse wie die 148 Neustarts vom 29.09.2026). Beide Stellen sind
mitgezogen.

Nachweis des Erfolgs: 11:32:35 startete der Launcher, 11:32:42 folgte der
Kindprozess, 11:33:03 meldet `gateway_state.json` `running` mit allen vier
Plattformen (a2a, telegram, photon, webhook) und zehn Bot-Peers; ein
Waechterlauf danach schrieb keine Zeile mehr.

### Warum die Reparatur vom Vortag weg war

Um **22:15 am 29.09.** hatte eine Sitzung den Launcher bewusst auf
`hermes-agent\venv\Scripts\python.exe` umgestellt, mit der Begruendung
"tools-Python hat keine Deps als Einstieg". Um **03:20 am 30.09.** hat die
Routine `fremdarbeit-einziehen` eine **aeltere Fassung derselben Datei** aus
dem Arbeitsbaum committet (Autor "Andere Sitzung <fremd@local>") und damit die
Reparatur stillschweigend zurueckgenommen. Die Routine holt bewusst alles, was
laenger als 30 Minuten uncommittet liegt - eine Datei, die nur noch ALT im
Arbeitsbaum steht, ist fuer sie von einer neuen Aenderung nicht zu
unterscheiden.

Zusaetzlich fehlten im `tools`-Python wieder alle Abhaengigkeiten (der
Update-Lauf vom 29.09. hatte sie entfernt). Nachgeholt mit
`tools\python-3.14.7...\python.exe -m pip install -e hermes-agent`; danach
importieren **beide** Wege `pydantic_core 2.46.4` - das `tools`-Python und
`hermes-agent\venv`, das ohnehin auf dasselbe Programm zeigt.

### Negativbefunde derselben Pruefung

- **Keine ASR-Regeln** in Windows Defender (`AttackSurfaceReductionRules_Ids`
  leer), **kein** Controlled Folder Access, Echtzeitschutz an. Defender
  blockiert den Skriptwirt also nicht - die Ursache liegt allein im Fensterstil.
- **`Get-ScheduledTask -TaskName <name>` findet vorhandene Aufgaben nicht**
  (erneut bestaetigt); verlaesslich sind `schtasks /query` und die
  Aufzaehlung mit `Get-ScheduledTask | Where-Object TaskName -like '*Gateway*'`.

## 30.09.2026 - node.exe 0xc000012d, Explorer stuerzt ab

- **Ursache: Commit-Limit erschoepft, nicht node.exe.** Ein Amok-`grep.exe`
  (`grep -o -E (de|ger):\{[^}]{0,4000} i18n-ChK_h4a4.js`, gestartet 14:10 aus
  `Agenten/Hermes/tools/git-.../usr/bin`) hielt 62,6 GB virtuellen Speicher.
  Frei: 1,2 von 108 GB. 0xc000012d = STATUS_COMMITMENT_LIMIT; jeder neue
  Prozess (node, Explorer) scheitert beim Start.
- **Behebung:** Prozess beendet, danach 43 GB frei. Kein Systemeingriff.
- **Geprueft, war es nicht:** Auslagerungsdatei (C:\pagefile.sys, 43,5 GB,
  Spitze 5,8 GB, manuell verwaltet).
- **Gleiches Muster frueher am Tag:** Ereignis 2004 (virtueller Speicher
  unzureichend) 09:59-10:15, dreimal; Verursacher `com.docker.sailor.exe`
  (14,7 GB) und `llama-server.exe` (7 GB). Docker lief bei der Pruefung nicht.
- **Schnellcheck bei 0xc000012d:** `(Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory`
  und `Get-Process | sort PagedMemorySize64 -desc | select -first 5`.

## 30.09.2026 - C: entlastet (34 -> 69 GB frei)

- Hermes.alt-20260916 (3,6 GB) nach Werkstatt/Ausgemustert/c-entlasten-20260930; npm-Cache geleert (pnpm-Store-DB defekt, unberuehrt).
- `.cache/huggingface` (15 GB) und `.docker/models` (6,5 GB) nach O:/Modelle/_von-c, Junctions zurueck. Robocopy /MOVE laesst Symlinks liegen: neu angelegt.
- Cinebench und PictureGuide (Store) entfernt. Docker lief dabei weiter (Shutdown griff nicht).
- Rueckweg: Agenten/Routinen/einmalig-20260930-c-entlasten.ps1 -Rueckgaengig. Offen (Admin): Docker-VHD verkleinern, Auslagerung auf O:.

## 30.09.2026 - Doppeltes bereinigt

- Gemma-GGUF und Ollama-Blob (7,5 GB): GGUF durch NTFS-Hardlink auf den Blob ersetzt, O: +7,5 GB. Nicht `ollama rm`: drei Modelle teilen den Blob.
- Wurzel-.bak und nul-Datei nach Werkstatt/Ausgemustert/wurzel-bak-20260930.
- Sieben saubere Zweitklone aus Documents/GitHub nach Werkstatt/Ausgemustert/klon-doppel-20260930 (Repos/ bleibt fuehrend). Dreckige Klone (EasyCLIProxyAPI) unberuehrt.
- Offen: Windows11-"(Kopie)"-Ordner (11 identisch, Maximilian und Native Instruments weichen ab, je ~1,3 GB), Repos/kraken-cli 3,4 GB.
- C: frei aktuell ca. 84 GB.

## 05.10.2026 - Sicherung nach G: und Platte Q: geprueft

- **G: (MaxHirn-Sicherung):** Agenten, MaxHirn/Wissen und MaxHirn/Archiv stehen drauf, Stand 04.10. 20:07. Dateizahlen Bilder, Dokumente, Musik, Protokolle, Videos gleich der Quelle O:\Archiv; Posteingang 277 zu 276 (Quelle neuer geleert). Software nicht gezaehlt (54.964 Dateien).
- **Luecke:** Lauf 22:30 am 04.10. endete mit 267014 (vom Planer beendet), das Protokoll hat nur die Kopfzeile. Aufgabe: Limit 3 h, MultipleInstances=IgnoreNew; der 20:00-Lauf lief vermutlich noch, als 22:30 startete. Naechster Lauf 05.10. 20:00. Archiv-Stand seit 04.10. nicht mehr nachgezogen.
- **Q: (SanDisk Portable SSD, exFAT, Disk 3):** Platte Healthy, Volume meldet Warning / Full Repair Needed. Ereignis 11 (Controllerfehler) und viele 153 am 12.09. - passt zu Kabel/Port-Problem. Zuverlaessigkeitszaehler ohne Adminrechte nicht lesbar.
- **Offen:** `chkdsk Q: /scan` mit Admin, danach ggf. `/f` - vorher mit H: abgleichen. Nicht ohne Max' Freigabe reparieren.

### Nachtrag 09.10.2026 - Q: geprueft, Dateisystem sauber

- `chkdsk Q:` (nur lesend, Volume `musik_lib`, exFAT): keine Probleme, 0 KB in fehlerhaften Sektoren, 568.360 Dateien, 107.691 Ordner, 120 GB frei. Das Warning "Full Repair Needed" ist ein gesetztes Dirty-Bit nach dem Controllerfehler vom 12.09., kein Dateisystemschaden. `chkdsk /scan` geht auf exFAT nicht (Momentaufnahmefehler), `/f` ist nicht noetig.
- Q: ist das Original der Musikbibliothek (1,63 TB) und hat KEINE Kopie: `robocopy /L` gegen H: ergab 568.358 von 568.360 Dateien als fehlend. H: ist eine andere Ablage.
- Platz fuer eine Vollkopie fehlt: G: 504 GB, H: 488 GB, J: 185 GB frei. G:, H: und I: liegen alle auf der einen Seagate (Disk 2) - Sicherung und Zweitablage haengen an derselben Platte.
- Offen: Q: braucht eine zweite Platte (ab 2 TB) oder eine Teilsicherung. Dirty-Bit loest sich beim naechsten sauberen Auswerfen/Anmelden; sonst `chkdsk Q: /f` - jetzt gefahrlos, weil nichts zu reparieren ist.
