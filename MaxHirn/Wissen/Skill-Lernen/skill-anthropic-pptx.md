---
name: skill-anthropic-pptx
description: Trockenlauf des Skills anthropic-skills:pptx — pptxgenjs-basierter PowerPoint-Erstellungs-Guide mit Structured-Decks, Design-Regeln und QA-Pipeline; viele kritische Fallstricke.
metadata:
  type: reference
---

**Zweck:** `.pptx`-Dateien erstellen (pptxgenjs), bearbeiten (unzip→XML→zip), lesen (markitdown) und konvertieren. Vollständiger Design-Guide und QA-Pipeline.

**Wann nutzen:** PowerPoint-Datei erzeugen oder bearbeiten. Wenn eine Slides-Artifact-Type verfügbar ist und kein .pptx gewünscht → dorthin statt zu diesem Skill.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~15 Seiten. Einer der längsten und detailliertesten Skills. Sehr viele Fallstricke.

**Gelernt — Kritische Fallstricke pptxgenjs:**
- `pres.layout` VOR erstem `addSlide` setzen — Standard ist 10"×5.625", Shapes außerhalb werden lautlos geschrieben
- Hex-Farben: niemals `#`-Präfix, niemals 8 Ziffern (Alpha) → Datei korrupt
- Options-Objekte werden in-place mutiert → niemals dasselbe Objekt für zwei `add*`-Calls teilen
- `shadow.offset` muss ≥ 0 sein; nach oben: `angle: 270` + positiver Offset
- `letterSpacing` ignoriert → `charSpacing` verwenden
- Listen: `bullet: true` pro Item, `breakLine: true` auf jedem Item außer dem letzten
- Combo-Charts mit `secondaryValAxis` brauchen zwingend `valAxes` + `catAxes` (zwei Einträge je) → sonst Datei korrupt
- Nach `writeFile()`: immer `python scripts/office/validate.py` laufen lassen
- Fonts: **niemals Aptos** (kein Fallback). Sichere Fonts (QA-zuverlässig): Arial, Calibri, Cambria, Times New Roman. QA-unzuverlässig (abweichende Breiten): Georgia, Trebuchet MS, Impact, Garamond

**Structured Decks (Pflicht für neue Decks):**
1. THEME-Objekt definieren (Farben, Fonts)
2. Sections: `pres.addSection` vor erstem Slide der Section
3. Layouts: je ein `defineSlideMaster()` pro Slide-Typ
4. Placeholder-Befüllung statt absoluter Positionierung
5. `writeFile()` → dann `applyTheme()` (pptxgenjs kann keine Theme-Farben direkt schreiben)

**QA-Pipeline (alle Schritte Pflicht):**
1. `markitdown output.pptx` — Inhalt prüfen, Placeholder-Reste suchen
2. `python scripts/office/validate.py output.pptx [--original src.pptx]`
3. `soffice → PDF → pdftoppm -jpeg -r 150` → alle Slide-Bilder inspizieren

**Design-Regeln (wichtigste):**
- Kein Text-only: jedes Slide braucht ein visuelles Element
- Keine Accent-Linien unter Titeln (AI-Erkennungsmerkmal)
- Keine dekorativen Farbbalken/-streifen (AI-Erkennungsmerkmal)
- Kein Standard-Blau, kein Beige/Creme als Default
- `thumbnail.py` immer mit zweitem Argument (Name) aufrufen — sonst überschreiben sich Grids

**Grenzen:** Sandbox benötigt LibreOffice + pdftoppm für QA. `python-pptx` hat Einschränkungen: keine Slide-Duplikation, keine SVG/EMF-Bilder, Formatierung geht bei `text_frame.text = ...` verloren.
