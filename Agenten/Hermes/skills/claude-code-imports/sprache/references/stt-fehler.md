# Typische Verhörer der deutschen Spracherkennung

Nur korrigieren, wenn der Kontext eindeutig ist. Im Zweifel den Rohtext stehen lassen —
eine falsche „Korrektur" ist schlimmer als ein unsauberer Begriff.

## Technische Begriffe

| Gehört | Gemeint |
|---|---|
| pi ton, peiton, phyton | Python |
| powershell, power schell, power shell | PowerShell |
| kommandozeile, command line | Terminal / Shell |
| gitt, git hub, github | Git / GitHub |
| jason, dschejson | JSON |
| index pi, index punkt pi | `index.py` |
| sort inbox, sortinbox | `sort_inbox.py` |
| search cli, sörtsch sieelai | `search_cli.py` |
| markdown, mark down | Markdown |
| repo, repository, repositorium | Repository |
| terminal, thermal | Terminal |
| pfad, fad | Pfad |
| skript, script, schrift | Skript |
| o see ar, okr, o c r | OCR |
| pi di ef, pdf | PDF |
| exif, exiv | EXIF |
| venv, we env, virtual enf | `.venv` |

## Archiv-Begriffe (dieses Projekt)

| Gehört | Gemeint |
|---|---|
| posteingang, post eingang, poste ingang | `Posteingang/` |
| archivsuche, archiv suche | `ArchivSuche/` |
| dokumente, documente | `Dokumente/` |
| elster, elstar, elster zertifikat | ELSTER-Zertifikat (`.pfx`) |
| iCloud, ei cloud, ai cloud | iCloud |
| index, indeks | Index / Suchindex |
| einsortieren, ein sortieren | einsortieren |

## Zusammengesetzte Wörter

Die Erkennung trennt deutsche Komposita gern fälschlich. Wieder zusammenziehen, wenn ein
gängiges Wort entsteht: „Datei Namen" → Dateinamen, „Ordner Struktur" → Ordnerstruktur,
„Such Begriff" → Suchbegriff, „Sicherungs Kopie" → Sicherungskopie.

Umgekehrt gilt: Wenn zwei Wörter zusammengeschrieben wurden, die getrennt gehören
(„machdas"), trennen.

## Zahlen und Größen

- „drei komma fünf" → 3,5
- „zwanzig gigabyte" → 20 GB
- „zweitausendfünfundzwanzig" im Datumskontext → 2025
- „drei uhr" → 15:00 nur, wenn der Kontext Nachmittag nahelegt; sonst offen lassen.

## Was nicht korrigiert wird

- Umgangssprache und Dialekt, solange die Bedeutung klar ist. „Mach mir das mal weg"
  bleibt sinngemäß erhalten — es wird als Auftrag formuliert, nicht als Hochdeutsch-Übung.
- Eigennamen, Ordner- und Dateinamen, die nicht in dieser Liste stehen und nicht
  offensichtlich verhört sind. Lieber im Dateisystem nachsehen als raten.
