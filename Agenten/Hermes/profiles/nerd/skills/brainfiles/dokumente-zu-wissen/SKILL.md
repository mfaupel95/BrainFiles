---
name: dokumente-zu-wissen
description: Use when PDFs/Dokumente zu Wissen-Notizen werden.
---

# Dokumente lesen und als Wissen-Notiz aufnehmen

Max legt gelesene Paper/PDFs/Dokumente als Markdown-Notiz unter `MaxHirn/Wissen/` ab
(statt sie nur zu lesen). Diese Notiz ist die dauerhafte Erkenntnis; das Original bleibt
im Repo/Archiv. Ablauf in dieser Reihenfolge.

## 1. PDFs extrahieren (Windows)

`pdftotext -layout` (poppler) auf jede PDF, Ausgabe als `.txt` neben die PDF:

```bash
cd <ordner> && for f in *.pdf; do pdftotext -layout "$f" "${f%.pdf}.txt"; done
```

**FALLE (kostete Zeit):** pdftotext auf Windows schreibt **Latin-1/ISO-8859**, nicht
UTF-8. `read_file` verweigert die Datei dann als "Binary file". NICHT raten, dass es
UTF-16LE ist (iconv -f UTF-16LE erzeugt nur Muell). Fix:

```bash
iconv -f ISO-8859-1 -t UTF-8 datei.txt > datei-utf8.txt
```

Danach ist die Datei mit `read_file` lesbar. `file datei.txt` zeigt vorher
"ISO-8859 text" — das ist der Hinweis, nicht "binary".

## 2. Kernaussagen gezielt lesen, nicht alles

Paper sind lang; die Essenz steckt in Abstract + Conclusions. Nicht die ganze Datei
lesen:

- Abstract: `sed -n '/^Abstract/,/^Keywords/p' datei.txt`
- Conclusions: `grep -n -i conclusion datei.txt` und den Abschnitt ab der Zeilennummer lesen
- Methodik/Architektur nur bei Bedarf: `grep -n -iE "<schluesselbegriff>" datei.txt`

## 3. Notiz schreiben

- Pfad: `MaxHirn/Wissen/<Thema>.md` (LF-Zeilenenden, `[[Wikilinks]]` zu verwandten Notizen).
- Struktur: je Dokument ein Abschnitt mit Kernaussage, dann ein **Fazit fuer den Betrieb**
  (Bezug zum eigenen Handels-/KI-Betrieb), dann Verwandt-Zeile.
- **Kritische Einordnung immer dazuschreiben**: Backtest-Renditen ohne Kostenmodell sind
  Papier-Rendite; In-Sample-Ergebnisse sind kein Rezept. Kein Code/Parameter aus einem
  Paper uebernehmen, ohne es als Strategie zu pruefen.
- Vor dem Schreiben `MaxHirn/Wissen/Schutzregeln.md` lesen (Pflicht bei jedem
  schreibenden Zugriff). Eine NEUE Notiz anlegen ist im Rahmen; Widerspruch zu
  Bestehendem erst zurueckfragen.

## 4. INDEX-Registry nachziehen (Pflicht)

Jede neue Wissen-Notiz braucht einen Eintrag in `MaxHirn/Wissen/INDEX.md` (Registry,
Format `- \`id\` — **Titel** — \`Wissen/Datei.md\` — Kurzbeschreibung`). Ohne den
Eintrag ist die Notiz im Vault nicht auffindbar. Nach dem Anlegen der Notiz den
passenden Abschnitt in INDEX.md per `patch` ergaenzen.

## 5. Committen

Nur eigene Pfade stagen (nie `git add -A` — fremde Arbeitsbaum-Aenderungen liegen
lassen), Autor `--author="Hermes <hermes@local>"`, dann pushen.

```bash
git add MaxHirn/Wissen/<Notiz>.md MaxHirn/Wissen/INDEX.md
git commit -m "docs(wissen): <Thema> - <kurz>" --author="Hermes <hermes@local>"
git push origin master
```

## Fallen

- `read_file` auf einer Latin-1-PDF-Extraktion meldet "Binary file" — das ist KEIN
  kaputtes PDF, nur die Kodierung. Erst iconv, dann lesen.
- Nicht raten, welche Kodierung pdftotext ausgibt — `file` sagt es (ISO-8859).
- Eine neue Notiz ohne INDEX-Eintrag ist im Vault unsichtbar.
- Backtest-Zahlen aus Papern nie als belegte Strategie verkaufen; Kostenmodell und
  Out-of-Sample fehlen meist.
