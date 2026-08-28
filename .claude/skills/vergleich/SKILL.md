---
name: vergleich
description: Vergleicht Ordner über mehrere Laufwerke, findet Duplikate und führt verstreute Bestände zusammen — auch Musik über akustischen Fingerabdruck. Benutzen bei "vergleiche die Ordner", "Duplikate", "doppelte Dateien", "was liegt nur auf G:", "führe zusammen", "kann das weg", "räum das Laufwerk auf", "ist das schon woanders".
---

# Ordner vergleichen und zusammenführen

Es gibt zwei fertige Werkzeuge dafür. **Kein Ad-hoc-Skript schreiben** — die
Fallen unten sind darin bereits behandelt.

## 1. Vergleichen

```
cd ArchivSuche
.venv\Scripts\python.exe ordner_abgleich.py vergleich "G:\Documents" "J:\Dokumente\Documents"
```

Zeigt je Paar: nur hier, nur dort, gemeinsam — und schreibt eine Ergebnisdatei
für den nächsten Schritt. Beliebig viele Ordner sind möglich.

## 2. Zusammenführen

```
.venv\Scripts\python.exe ordner_abgleich.py zusammenfuehren ZIEL QUELLE --dry-run
```

Kopiert, was es nur in QUELLE gibt, unter Erhalt der Ordnerstruktur. Verifiziert
danach **Dateizahl und Gesamtgröße**. Erst mit `--loeschen` wird QUELLE geleert —
und nur nach erfolgreicher Verifikation. **Immer zuerst `--dry-run`.**

## 3. Musik

Gleiche Aufnahme, anderer Name, anderes Format, andere Bitrate — Name und Größe
versagen hier vollständig. Deshalb akustischer Fingerabdruck:

```
.venv\Scripts\python.exe musik_zusammenfuehren.py analyse "G:\Musik" --limit 20
```

`zusammenfuehren --ziel X` erzeugt pro Gruppe eine verlustfreie AIFF mit den
besten Metadaten; unterlegene Kopien wandern in Quarantäne, nichts wird
unwiderruflich gelöscht. Der AcoustID-Schlüssel steht in [[Zugaenge]].

## 4. Die vier Fallen

**PowerShell zum Erfassen, Python zum Vergleichen.** Jeder `stat()`-Aufruf ist
unter Windows ein eigener Systemaufruf. Dieselben 65.939 Dateien: Python hing
stundenlang, `Get-ChildItem -Recurse -File` brauchte **6,5 Sekunden**. Die
Skripte machen das bereits richtig — bei eigenen Auswertungen genauso vorgehen.

**Name + Größe ist kein Beweis.** Bei Formaten mit fester Split-Größe
(`.vob`, `.ifo`, `.bup`, `.iso`, `.img`) schneidet der Container unabhängig vom
Inhalt an festen Grenzen, typisch 1 GiB. Vier verschiedene
Vorlesungsaufzeichnungen hatten identischen Namen **und** identische Größe
(1024,0 MB) und waren per Hash völlig verschieden. Bei solchen Endungen immer
`Get-FileHash` gegenprüfen. Bei beliebigen Binärdateien mit krummer Byte-Größe
ist Name + Größe dagegen zuverlässig.

**Umlaute: NFC gegen NFD.** Von macOS stammende Dateinamen sind zerlegt
gespeichert; ohne Normalisierung gelten identische Dateien als fehlend. Die
Skripte normalisieren auf NFC.

**Massenlöschung über robocopy.** `robocopy <leerer_Ordner> <ziel> /MIR` ist bei
großen Bäumen deutlich schneller als `Remove-Item -Recurse -Force`. Danach mit
`Test-Path` in einem **eigenen, einfachen Aufruf** gegenprüfen — eine
Erfolgsmeldung eines Löschbefehls ist kein Nachweis.

## 5. Grenzen

Löschen ist erst nach Verifikation erlaubt, und für persönliche Inhalte
(`Dokumente/`, `Bilder/`, `Videos/`, `Musik/`, unsortierter `Posteingang/`,
Schlüssel- und Zertifikatsdateien) gilt die Löschsperre aus [[Schutzregeln]]
weiter: Soll dort etwas weg, wandert es nach `Posteingang/_zu_loeschen/`.

Geht es nicht um Duplikate, sondern um **inhaltlich zerstörte** Dateien
(0xFF-Füllbytes nach dem Netzteildefekt), ist der Skill `schaden` zuständig.

Das Ergebnis eines Laufs — welche Laufwerke verglichen, was gefunden — gehört in
die passende Notiz, nicht in die Chatantwort.
