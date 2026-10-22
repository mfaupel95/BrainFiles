---
name: skill-anthropic-docx
description: Trockenlauf des Skills anthropic-skills:docx — Word-Dokumente erstellen (docx-npm), bearbeiten (unzip+XML), lesen (pandoc), mit Redlining, Kommentaren und LibreOffice-Verifikation.
metadata:
  type: reference
---

**Zweck:** Vollständiges Werkzeug für .docx-Dateien: Erstellen (docx npm, vorinstalliert), Bearbeiten (unzip→XML→zip), Lesen (pandoc -t markdown), Redlining (Tracked Changes), Kommentare (6 XML-Dateien via scripts/comment.py). Verifikation via LibreOffice → PDF → pdftoppm → Read.

**Wann nutzen:** Wenn explizit Word/.docx gewünscht, Tracked Changes gebraucht werden, oder eine .docx-Vorlage bearbeitet werden soll. Wenn Claude Docs verfügbar ist und kein Word-spezifisches Feature gebraucht wird: Docs statt docx nutzen (Skill prüft das selbst).

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~4 Seiten. Enthält Gotchas-Tabelle, Edit-Workflow, Tracked-Changes-Regeln, Kommentar-Helper-Syntax.

**Gelernt:** Wichtige Fallen (Gotchas):
- Seitengröße: Standard A4, US Letter explizit setzen (12240×15840 DXA)
- Tabellen: `columnWidths` UND `width` pro Zelle in DXA (PERCENTAGE bricht in Google Docs)
- `ShadingType.SOLID` → schwarz; immer `CLEAR` nutzen
- `PageBreak` muss in `Paragraph` eingebettet sein
- `\n` verboten — eigene `Paragraph`-Elemente
- Docx-Dateien können Symlinks enthalten → `find unpacked -type l -delete` nach unzip (Sicherheit!)
- `merge_runs.py` ist nötig weil Word Text auf viele Runs aufteilt → Suche findet Phrasen nicht

**Grenzen:** `docx-js` kann keine bestehenden Dateien öffnen — nur ZIP+XML-Bearbeitung für Edits. LibreOffice muss installiert sein für Verifikation.
