# Beschädigte Dateien im Archiv — Gesamtbild

Ein **Netzteildefekt** hat mehrere Festplatten gleichzeitig zerstört. Die
Dateinamen wurden noch geschrieben, die Inhalte gingen mit der Hardware
verloren: Die Dateien sind durchgehend mit `0xFF` gefüllt.

Bis zum 20.08.2026 war nur der PDF-Anteil dokumentiert. Der erste vollständige
Lauf über **alle** Dateitypen zeigt, dass der Schaden deutlich weiter reicht.

## Stand 20.08.2026

Gemessen mit `ArchivSuche/pruefe_signaturen.py` — 62.401 Dateien in 33 Sekunden.

| | Anzahl |
|---|---|
| geprüfte Dateien | 62.401 |
| **zerstört (0xFF)** | **691** |
| zerstört (0x00) | 1 |
| leer (0 Byte) | 42 |
| fremde Signatur (falsche Endung, kein Schaden) | 17 |

### Wo der Schaden sitzt

| Ordner | betroffen |
|---|---|
| `Bilder/` | 494 |
| `Software/` | 86 |
| `Dokumente/` | 83 |
| `Musik/` | 31 |
| `Videos/` | 5 |

### Nach Dateityp

PNG 199 · JPG 149 · HEIC 141 · APK 70 · **PDF 61** · FLAC 21 · PFX 6 ·
OGG 5 · GIF 4 · ODT 4 · CFG 4 · L12 4 · S12 4 · SBK 3 · DWF 3 · AIF 3 ·
FLV 3 · OTF 2 · HEIF 1 · WAV 1 · M4A 1 · EML 1 · GZ 1

## Drei Funde, die vorher nicht dokumentiert waren

### 1. Die ELSTER-Zertifikate sind zerstört

Alle sechs `.pfx`-Dateien unter `Software/icloud 26/` sind mit 0xFF gefüllt —
drei Zertifikate, jeweils doppelt abgelegt:

- `mfaupel_elster_2019(1).pfx`
- `mfaupel_elster_2019(2).pfx`
- `mfaupel_elster_25.11.2025_16.49.pfx`

Das jüngste stammt vom **25.11.2025**, fünf Tage vor der korrigierten
Einkommensteuererklärung vom 30.11.2025. Damit ist belegt, was Max im
Einspruch vom 19.08.2026 geschildert hat: der ELSTER-Zugang ging mit den
Platten verloren, nicht durch Nachlässigkeit.

**Sie bleiben liegen.** Nicht weil sie noch nutzbar wären — sie sind es nicht —
sondern als Beleg. Siehe [[Steuerunterlagen]].

### 2. 31 Musikdateien

21 FLAC, 5 OGG, 3 AIF, 1 WAV, 1 M4A, alle direkt unter `Musik/`. Bisher nirgends
erwähnt. Ob es Zwillinge gibt, ist ungeprüft.

### 3. 70 APK-Dateien

Unter `Software/`. Ersetzbar, da Installationsdateien — kein Handlungsbedarf.

## Korrektur einer früheren Angabe

In `CLAUDE.md` stand, die 494 beschädigten Bilder seien „von 10.359 Bilddateien
insgesamt". Diese Bezugsgröße ist archivweit (heute 10.119, davon 5.277 allein
in `Software/`). Alle 494 Schäden liegen aber unter `Bilder/`, und dort gibt es
nur **2.693 Bilddateien**.

Der Schadensanteil in `Bilder/` beträgt damit **18,3 %**, nicht 4,8 %.

## Rettung 20.08.2026: sechs Dateien zurück

Ein Lauf von `rette_dateien.py` **gegen das Archiv selbst** (ohne externe Platte)
fand acht gleichnamige heile Fassungen. Sechs waren eindeutig und wurden
zurückgespielt, überwiegend CAD-Dateien des Gesellenstücks, die in
`usb Gesellenstück/` doppelt lagen:

`-009.JPG` · `Vorne.png` · `Vinyl-Korpus_Konstruktionsseiten.L12` ·
`Zeichnung-1.S12` · `Zeichnung-1.SBK` · ein Guitar-Pro-Tab

Stand danach: **692 → 686** zerstörte Dateien (nachgeprüft).

**Zwei blieben liegen**, weil mehrere heile Fassungen mit verschiedenem Inhalt
existieren — `Verbindungen.L12` (vier Fassungen, drei davon exakt 602.112 Byte
groß und trotzdem verschieden) und `Verdeckte Linien.L12` (73.728 vs. 32.768
Byte, „Korrektur" gegen „Finaly"). Welche der Bearbeitungsstand ist, der ins
Archiv gehört, entscheidet Max.

## Rettung 20.08.2026, zweiter Durchgang: Laufwerk O:

**O: war die ganze Zeit eingebunden** — eine M.2-SSD im Slot M2_1, 271 GB belegt,
355.659 Dateien. Die Angabe „O: war nicht eingebunden" stammte aus dem Stand vom
08.08.2026 und wurde seither ungeprüft weitergetragen.

Der Lauf brauchte **66 Sekunden** und brachte **42 Dateien** zurück:
40 in `Bilder/`, 2 in `Software/`. Mehrdeutig war keine einzige.

Stand danach: **686 → 644** zerstörte Dateien, in `Bilder/` von 494 auf **452**.

**Keine Dokumente dabei.** Die 61 zerstörten PDFs — darunter zehn Rechnungen und
das Einladungsschreiben zur Meisterprüfung — haben auch auf O: keine intakte
Fassung. Von 686 Zielen fanden sich 639 nur in bereits zerstörter Form wieder,
was die alte Erfahrung bestätigt: Namensgleichheit sagt fast nichts.

## Nachprüfung 08.09.2026: nach dem Umzug auf `O:\Archiv`

Das Archiv liegt seit dem 07.09.2026 physisch auf `O:\Archiv`. Erster
`pruefe_signaturen.py`-Lauf gegen den neuen Ort — 64.456 Dateien:

| | Anzahl |
|---|---|
| zerstört (0xFF) | **644** |
| leer (0 Byte) | 42 |
| fremde Signatur (kein Schaden) | 17 |

**Unverändert gegenüber dem Stand nach der O:-Rettung vom 20.08.2026.** Der
Umzug (robocopy) hat keinen neuen Schaden gebracht und keinen alten geheilt.
HEIC 104 · PNG 196 · JPG 147 · APK 70 · PDF 61 · FLAC 21 · PFX 6 — die
PDF-Lage ist unberührt.

`pruefe_signaturen.py` und `rette_dateien.py` lösten den Archivpfad bis hierher
relativ zum Skript auf und hätten nach dem Umzug die fast leere alte Vault-Lage
geprüft — ein Fehlbefund „0 Schäden". Beide lesen jetzt `ARCHIV_ROOT` mit
Rückfall auf die alte Lage (Commit `0905541`). Aufruf unverändert.

Offen bleibt die Zwillingssuche auf **C:, G:, H:, I:, J:** — dort wurde zuletzt
am 08.08.2026 geprüft, mit dem alten Verfahren ohne Hash-Vergleich.

## Getrennt davon: der Index kann HEIC nicht lesen

Der Indexlauf nach der Rettung meldete 19 Fehler. Die Dateien sind **in
Ordnung** — geprüft, `ftyp`-Kennung vorhanden. Dem Indexer fehlt lediglich
`pillow-heif`, um HEIC zu öffnen.

Betroffen sind archivweit **149 HEIC-Dateien** (Teil von 498
`UnidentifiedImageError` insgesamt). Folge: Aus diesen Fotos werden keine
Metadaten und kein Text gezogen — sie sind nur über den Dateinamen auffindbar.
Kein Datenverlust, aber eine Lücke in der Suche.

## Was als Nächstes zu tun wäre

- [ ] Die zwei mehrdeutigen L12-Dateien entscheiden
- [ ] `pillow-heif` nachinstallieren, damit 149 HEIC-Fotos durchsuchbar werden
      (Installation — vorher ansagen)
- [ ] Die verbleibenden 452 Bilder gegen weitere Datenträger prüfen (G:, H:, J:
      wurden am 08.08.2026 geprüft, aber mit dem alten Verfahren)
- [ ] Laufwerk **O:** erneut einbinden; dort wurde zuletzt gerettet
- [ ] Die 31 Musikdateien gegen eine vorhandene Musiksammlung abgleichen

Auf **C:, G:, H:, I: und J:** wurde am 08.08.2026 nichts gefunden — allerdings
mit dem alten Verfahren und ohne die Hash-Prüfung von heute.
**Namensgleichheit genügt nicht**: von 261 namensgleichen Kandidaten waren 220
selbst zerstört.

## Details zu den PDFs

Die 61 verbleibenden PDFs sind einzeln aufgeführt in
[BESCHAEDIGTE_PDFS.md](BESCHAEDIGTE_PDFS.md) — mit Rettungsgeschichte,
Fundorten und der Liste dessen, was endgültig fehlt.

**Stand:** 2026-09-08 (Nachprüfung nach O:-Umzug; Schadenszahlen seit
2026-08-20 unverändert) · Werkzeug: `ArchivSuche/pruefe_signaturen.py` ·
Skill: `schaden`
