---
name: skill-anthropic-xlsx
description: Trockenlauf des Skills anthropic-skills:xlsx — openpyxl/pandas/markitdown für Excel-Dateien; recalc.py-Pflicht, Formel-Fallstricke, Finanmodell-Konventionen.
metadata:
  type: reference
---

**Zweck:** Excel-Dateien (.xlsx/.xlsm) erstellen, bearbeiten, lesen, analysieren. Vollständige Formel- und Formatierungsunterstützung mit LibreOffice-Recalculation.

**Wann nutzen:** Immer wenn .xlsx-Dateien erzeugt oder bearbeitet werden sollen. Kein API-Zugriff nötig.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~4 Seiten. Detailliert, sehr viele Fallstricke.

**Gelernt — Tool-Auswahl:**

| Aufgabe | Bestes Tool |
|---|---|
| Erstellen/Bearbeiten mit Formeln/Formatierung | `openpyxl` |
| Bulk-Daten rein/raus | `pandas` (read_excel, to_excel) |
| Schneller Blick | `markitdown file.xlsx` — kein Zellkoordinaten! |
| Modell lesen (Formeln + Werte) | zwei `load_workbook`-Pässe |

**Kritische Fallstricke:**
- `recalc.py output.xlsx` IMMER nach Schreiben ausführen — openpyxl schreibt Formeln ohne gecachte Werte → alles liest `None` zurück
- `data_only=True` + speichern = alle Formeln verloren (nur lesen, nie speichern!)
- `data_only=True` auf frisch geschriebene Datei → `None` überall (erst recalc)
- Merged Cells: nur Top-Left beschreiben
- `.xlsm`: `keep_vba=True` nötig sonst Makros weg
- **Post-2007-Funktionen:** `_xlfn.TEXTJOIN`, `_xlfn.IFS` etc. brauchen Prefix
- **NIE `XLOOKUP`, `XMATCH`, `SORT`, `FILTER`, `UNIQUE`, `SEQUENCE`** — LibreOffice kann sie nicht auswerten; stattdessen `INDEX`/`MATCH`
- Formel von LibreOffice nicht geparsed → wird **kleingeschrieben** zurückgeschrieben

**Finanzmodell-Konventionen (Standard):**
- Blau = hartcodierte Inputs; Schwarz = Formeln; Grün = Sheet-Links; Rot = Datei-Links; Gelb = Key Assumptions
- Zahlen: `$#,##0` mit Einheit im Header; Nullen als `-`; negative in Klammern; % als `0.0%` **als Dezimalbruch** (0.15 → 15.0%, NICHT 15 → 1500.0%!)
- Jede Annahme in eigener beschrifteter Zelle, Formeln referenzieren per `$B$6` nicht als Literal

**Grenzen:** recalc.py braucht LibreOffice. Externe Links (andere .xlsx) verlieren gecachte Werte beim openpyxl-Speichern.
