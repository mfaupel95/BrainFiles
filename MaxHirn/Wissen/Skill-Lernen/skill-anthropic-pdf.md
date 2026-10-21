---
name: skill-anthropic-pdf
description: Trockenlauf des Skills anthropic-skills:pdf — Python-PDF-Toolkit (pypdf, pdfplumber, reportlab) mit CLI-Tools; Quick Reference für Merge/Split/Text/Tabellen/Erstellen/OCR/Formulare.
metadata:
  type: reference
---

**Zweck:** PDF-Operationen in Python und CLI — Zusammenführen, Aufteilen, Text/Tabellen extrahieren, neue PDFs erstellen, OCR für gescannte PDFs, Passwortschutz, Wasserzeichen, Formulare füllen.

**Wann nutzen:** Immer wenn PDFs programmatisch verarbeitet werden sollen. Kein API-Zugriff nötig.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~4 Seiten. Praktische Rezeptsammlung, kein Design-Overhead.

**Gelernt — Toolauswahl:**

| Aufgabe | Bestes Tool |
|---|---|
| Merge/Split/Rotate/Metadaten | `pypdf` (`PdfReader`, `PdfWriter`) |
| Text mit Layout / Tabellen extrahieren | `pdfplumber` |
| PDFs neu erstellen | `reportlab` (Canvas oder Platypus) |
| CLI-Merge/-Split/-Rotate | `qpdf` |
| CLI-Textextraktion | `pdftotext` (poppler-utils) |
| OCR gescannter PDFs | `pytesseract` + `pdf2image` |
| Formulare füllen | `pdf-lib` (JS) oder `pypdf` → siehe FORMS.md |

**Wichtige Fallstricke:**
- **ReportLab: keine Unicode-Subskript/Superskript-Zeichen** (₀₁₂…, ⁰¹²…) — werden als schwarze Kästchen gerendert. Stattdessen: `<sub>` und `<super>` XML-Tags in `Paragraph`-Objekten
- OCR: erst PDF → Bilder (`pdf2image`), dann `pytesseract.image_to_string(image)`
- Tabellen als DataFrame: `pd.DataFrame(table[1:], columns=table[0])` nach `pdfplumber`-Extraktion

**Referenzen im Skill-Verzeichnis:** `REFERENCE.md` (pypdfium2, JavaScript pdf-lib), `FORMS.md` (Formular-Ausfüllen).

**Grenzen:** Rein lokal, kein Cloud-Dienst. pytesseract braucht Tesseract-Installation. pdf2image braucht Poppler. pdftk nur wenn verfügbar.
