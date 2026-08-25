# Hardware

Laufwerke des Arbeitsrechners und was bei Plattenproblemen zu prüfen ist.
Ein Netzteildefekt hat 2026 mehrere Festplatten gleichzeitig zerstört; die
betroffenen Platten sind ausgebaut. **Das Stromproblem selbst ist damit nicht
erledigt** — siehe „Stromausfälle ohne Bluescreen" unten.

**Warum:** Der Ausfall hat einen halben Arbeitstag gekostet, weil das Symptom
(einfrierender Explorer) nach einem Software- statt einem Hardwareproblem aussah.
Die Diagnosewege unten führen in Minuten zum Ergebnis. Ausserdem ist die
Laufwerkszuordnung Voraussetzung für den Umzug in [[Portabilitaet]].

**Stand:** 2026-08-19 (Nachmessung; Ursprungsfassung 2026-08-16)

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
[BESCHAEDIGTE_PDFS.md](../Claude/BESCHAEDIGTE_PDFS.md): Dateinamen blieben
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
[BESCHAEDIGTE_DATEIEN.md](../Claude/BESCHAEDIGTE_DATEIEN.md). Es wären dann
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

## Stromausfälle ohne Bluescreen (offen, Stand 2026-08-16)

Der Rechner geht in unregelmässigen Abständen **schlagartig aus**. Fünf Vorfälle
in 32 Tagen:

> **Korrektur 19.08.2026:** Hier stand „und die Abstände werden kürzer". Das
> trägt die Datenlage nicht. Die beiden Ereignisse am 08.08. liegen 17 Minuten
> auseinander (ein Vorfall mit Sofort-Wiederholung), danach folgen Abstände von
> 3, 3 und 2 Tagen. Seit dem 16.08. sind — Stand 19.08., Prüfung im
> Systemprotokoll ab 01.08. — **keine weiteren Kernel-Power-41-Ereignisse**
> aufgetreten; das sind gut 3 Tage und damit der bislang längste Abstand.
> Kein Grund zur Entwarnung, aber „beschleunigt sich" ist als Befund falsch und
> hätte zu übereilten Maßnahmen verleitet.

| Datum | Uhrzeit |
|---|---|
| 08.08.2026 | 12:28 |
| 08.08.2026 | 12:45 |
| 11.08.2026 | 10:56 |
| 14.08.2026 | 14:57 |
| 16.08.2026 | 11:05 |

Erkennungsmerkmal im Systemprotokoll: **Kernel-Power 41 mit `BugcheckCode = 0`**,
`PowerButtonTimestamp = 0`, `SleepInProgress = 0`, begleitet von EventLog 6008.
Das heisst ausdrücklich **kein** Betriebssystemabsturz — Windows bekommt vom
Ausfall nichts mit, weil der Strom vorher weg ist.

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
Datei**: `Claude\Posteingang\Maximilianbackup0924`, 52.428.800.000 Bytes
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
| ~~`Claude\Dokumente\Privat\Bitlocker\firefox.csv`~~ | **erledigt 23.08.2026 — in Quarantäne verschoben** |
| ~~`Claude\Software\icloud 26\firefox.csv`~~ | **erledigt 23.08.2026 — in Quarantäne verschoben** |
| `Claude\Software\Linux\Unraid\config\ssh\ssh_host_{rsa,ed25519,ecdsa}_key` | **private SSH-Hostschlüssel des Unraid-Servers** |
| `Claude\Software\Linux\Unraid\config\{passwd,shadow,smbpasswd,secrets.tdb}` | Benutzer- und Samba-Hashes |
| `Claude\Worktrees\investment\OKX_API.env` | API-Zugangsdaten im Klartext |
| `Claude\ArchivSuche\acoustid_key.txt` | 0 Byte, leer — kann weg |
| `Claude\Software\Linux\Unraid\config\plugins\unbalanced\unbalanced.env` | prüfen |

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
läuft (`Claude/ArchivSuche`) und nicht über den Windows-Index. Betroffen sind
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
