---
name: schaden
description: Prüft Dateien im Archiv auf zerstörten Inhalt (Füllbytes nach dem Netzteildefekt), sucht intakte Zwillinge auf anderen Laufwerken und spielt sie zurück. Benutzen bei "kaputte Dateien", "beschädigt", "lässt sich nicht öffnen", "0xFF", "leeres PDF", "Bild ist schwarz", "was ist noch heil", oder wenn eine Datei im Archiv unerwartet keinen Inhalt hat.
---

# Beschädigte Dateien finden und retten

Ein Netzteildefekt hat mehrere Platten gleichzeitig zerstört. Die **Dateinamen
wurden noch geschrieben, die Inhalte nicht** — solche Dateien sind durchgehend
mit `0xFF` gefüllt. Sie sehen im Explorer normal aus, haben eine plausible
Größe und lassen sich anklicken. Erst beim Öffnen fällt es auf.

## 1. Prüfen

```
cd ArchivSuche
.venv\Scripts\python.exe pruefe_signaturen.py
```

Ohne Argument das ganze Archiv, sonst ein Unterordner (`pruefe_signaturen.py Bilder`).
Die Ausgabe ist eine Zusammenfassung; `--details` listet jede Datei einzeln,
`--csv datei.csv` schreibt eine Liste zum Weiterverarbeiten.

Gemessen: **62.401 Dateien in 33 Sekunden**. Es gibt keinen Grund, hier zu
stichproben.

## 2. Die drei Fallstricke

**„Beginnt mit FF" ist die falsche Prüfung.** Ein intaktes JPEG beginnt selbst
mit `FF D8 FF`. Wer nur das erste Byte ansieht, hält jedes gesunde Foto für
zerstört. Das Skript prüft deshalb, ob die ersten **4096 Bytes durchgehend
denselben Wert** haben.

**Nicht jedes Format beginnt bei Byte 0.** HEIC, HEIF, MP4, MOV und M4A haben
in den ersten vier Bytes die Boxlänge; die Kennung `ftyp` steht erst ab
Offset 4. Wer stur die ersten vier Bytes vergleicht, meldet Fehlalarm.

**Namensgleichheit genügt nicht.** Von 261 namensgleichen Rettungskandidaten
waren **220 selbst mit 0xFF gefüllt** (geprüft 08.08.2026). Jeder Fund wird
vor dem Zurückspielen geprüft — sonst überschreibt man eine Leiche mit einer
anderen.

## 3. Der Befund ist endungsunabhängig

Die Füllbyte-Prüfung läuft **vor** der Signaturprüfung. Deshalb findet das
Skript auch Schäden in Formaten, die es gar nicht kennt. `ungeprueft` in der
Ausgabe heißt: Signatur nicht validiert, aber **nachweislich nicht gefüllt**.

`fremde_signatur` ist kein Schaden, sondern meist eine falsche Endung — ein PNG,
das `.jpg` heißt. Vor dem Aufregen die Datei ansehen.

## 4. Retten

```
.venv\Scripts\python.exe rette_dateien.py O:\
```

Sucht zu jeder zerstörten Datei gleichnamige Kandidaten im angegebenen Pfad,
prüft **jeden einzelnen** und meldet vier Gruppen: eindeutig rettbar,
mehrdeutig, nur kaputte Funde, kein Kandidat. **Ohne `--uebernehmen` wird
nichts geschrieben.**

Das Einlesen läuft über PowerShell `Get-ChildItem`, nicht über Python — auf
externen Platten ist das der Unterschied zwischen Sekunden und Stunden.
Dateinamen werden vor dem Vergleich auf **NFC normalisiert**, sonst gelten
Umlaut-Dateien von macOS als nicht vorhanden.

**Mehrdeutig heißt: Finger weg.** Liegen mehrere heile Fassungen mit
unterschiedlichem **SHA1** vor, entscheidet Max, welche die richtige ist —
das Skript übernimmt sie nicht. Größe ist dabei kein Kriterium: bei
`Verbindungen.L12` waren drei Kandidaten exakt 602.112 Byte groß und trotzdem
inhaltlich verschieden.

Nach dem Übernehmen prüft das Skript jede Datei erneut und meldet, wenn sie
immer noch zerstört ist. Danach `index.py` laufen lassen, sonst bleibt sie
unauffindbar.

**Laufwerksangaben immer selbst prüfen**, nie aus der Doku übernehmen:

```powershell
Get-PSDrive -PSProvider FileSystem | Select-Object Name, Free, Used
```

Am 20.08.2026 stand in der Doku „O: war nicht eingebunden" — tatsächlich ist es
eine M.2-SSD im Mainboard und war die ganze Zeit da. Der Lauf, der deshalb zwölf
Tage unterblieb, brachte in 66 Sekunden **42 Dateien** zurück.

**Stand der Suche:** O: durchsucht (42 gerettet, keine Dokumente). Innerhalb des
Archivs selbst 6 gerettet, 2 mehrdeutig liegen geblieben. C:, G:, H:, I:, J:
wurden am 08.08.2026 geprüft — mit dem alten Verfahren, ohne Hash-Vergleich.

## 5. Platzhalter bleiben liegen

**Zerstörte Dateien werden nicht gelöscht.** Sie sind der einzige Hinweis
darauf, *welches* Dokument fehlt — bei zehn Rechnungen und dem
Einladungsschreiben zur Meisterprüfung ist der Name die ganze Information.

Ausnahme: Liegt im Archiv nachweislich ein **intakter Zwilling** derselben
Datei, darf der Platzhalter weg. Nachweis heißt Inhaltsvergleich, nicht
Namensvergleich.

## Regeln

- **Zertifikate und Schlüssel nie anfassen** (`.pfx`, `.p12`, `.pem`, `.key`,
  `.kdbx`). Auch zerstörte nicht: sie belegen, dass der Zugang verloren ging.
- Zahlen aus einem Lauf gehören in `Archiv/BESCHAEDIGTE_DATEIEN.md`, nicht in die
  Chatantwort. Sie veralten sonst still.
- Keine Reparaturversuche an gefüllten Dateien. Bei 0xFF ist nichts da, was
  sich reparieren ließe — nur Zurückspielen hilft.
- Vor dem Überschreiben einer vorhandenen Datei deren Zustand prüfen. Eine
  intakte Fassung darf nie von einem Fund überschrieben werden.
