---
name: skill-data-data-visualization
description: Trockenlauf des Skills data:data-visualization — umfassende Referenz für Chartauswahl, Python-Code-Muster (matplotlib/seaborn/plotly), Designprinzipien und Barrierefreiheit; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Vollständige Referenz für Datenvisualisierung — von Chartauswahl über Python-Code bis Accessibility-Checkliste.

**Wann nutzen:** Wenn ein konkreter Chart erstellt werden soll und Charttyp, Code-Muster oder Design-Entscheidungen gebraucht werden. Umfassender als `data:create-viz`.

**Lauf:** 2026-10-22, trockenlauf.

**Chartauswahl-Kurzreferenz:**

| Datenverhältnis | Empfehlung | Vermeiden |
|---|---|---|
| Trend über Zeit | Linienchart | — |
| Kategorienvergleich | Vertikaler Balken | Pie (>6 Kategorien) |
| Ranking | Horizontaler Balken | 3D-Charts (immer) |
| Komposition | Gestapelter Balken / Treemap | Dual-Achsen (Vorsicht) |
| Verteilung | Histogramm / Boxplot | — |
| Korrelation 2 Var. | Scatter | — |
| Korrelation viele | Heatmap | — |
| Geo | Choropleth-Karte | — |

**Code-Muster (Python, matplotlib+seaborn):**
- Setup: `plt.style.use('seaborn-v0_8-whitegrid')`, colorblind-Palette `#4C72B0`/`#DD8452`/…
- Linienchart, Balkenchart (sortiert!), Histogramm mit Mean/Median, Heatmap, Small Multiples
- Hilfsfunktion `format_number()` für K/M/B-Kürzel
- Interaktiv: `plotly.express` → `.write_html()`

**3 Kernregeln:**
1. Balken immer bei 0 beginnen — nie ausschneiden
2. Titel beschreibt die Erkenntnis, nicht das Datenelement
3. Kategorien nach Wert sortieren, nicht alphabetisch

**Accessibility-Checkliste:** Chart ohne Farbe nutzbar; Text ≥10pt; Achsen mit Einheit beschriftet; Datenquelle + Datumsbereich angegeben; Legende nicht über Daten.

**Unterschied zu data:create-viz:** Tiefere Referenz (mehr Charttypen, Accessibility-Abschnitt, Nicht-verwenden-Regeln); create-viz ist der ausführende Skill, data-visualization ist die Designbibliothek.
