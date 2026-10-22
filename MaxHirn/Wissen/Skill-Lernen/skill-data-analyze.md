---
name: skill-data-analyze
description: Trockenlauf des Skills data:analyze — beantwortet Datenfragen von schnellem Lookup bis Forschungsbericht; MCP-Warehouse oder User-Daten; lokal; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Datenfragen beantworten — von einzelnem Kennwert bis zum formalen Bericht.

**Wann nutzen:** `analyze <Frage>` — bei allen datengetriebenen Fragen, egal ob Warehouse angebunden oder Daten manuell eingefügt werden.

**Lauf:** 2026-10-22, trockenlauf.

**Gelernt — 3 Komplexitätsstufen:**

| Stufe | Beispiel | Ausgabe |
|---|---|---|
| Quick answer | „Wie viele User letzte Woche?" | Zahl + Query |
| Full analysis | „Was treibt den Conversion-Drop?" | Insight + Tabellen/Charts |
| Formal report | „Quarterly Business Review" | Executive Summary + Methodik + Empfehlungen |

**6-Schritt-Workflow:** Frage verstehen → Daten holen → Analysieren → Validieren (Rowcount, Nulls, Größenordnung, Trend) → Präsentieren → Visualisieren (verweist auf `data-visualization`-Skill).

**Wenn kein Warehouse:** Nutzer liefert CSV/Excel/Query-Ergebnis; alternativ SQL-Query schreiben den Nutzer selbst ausführen lässt.

**Grenzen:** Kein eigener MCP-Zugriff ohne angebundenen Warehouse-Server; Visualisierungslogik in separatem `data:data-visualization`-Skill.
