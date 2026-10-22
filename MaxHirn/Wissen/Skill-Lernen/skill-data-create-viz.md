---
name: skill-data-create-viz
description: Trockenlauf des Skills data:create-viz — Python-Visualisierungen mit matplotlib/seaborn oder plotly; lokal; kein API-Aufruf; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Publikationsreife Diagramme aus Daten erzeugen; empfiehlt Charttyp wenn nicht angegeben.

**Wann nutzen:** `create-viz <Datenquelle> [Charttyp] [Anweisungen]` — für Reports, Präsentationen, Explorationscharts.

**Lauf:** 2026-10-22, trockenlauf.

**Gelernt — Charttyp-Entscheidungsbaum (Auswahl):**

| Datenverhältnis | Empfehlung |
|---|---|
| Trend über Zeit | Linienchart |
| Kategorienvergleich | Balkenchart (horizontal bei vielen) |
| Komposition | Gestapelter Balken/Fläche (kein Pie >6 Kategorien) |
| Verteilung | Histogramm / Boxplot |
| Korrelation | Scatterplot |
| Ranking | Horizontaler Balken |

**Bibliothek:** matplotlib+seaborn (Standard, statisch) oder plotly (interaktiv auf Anfrage).

**Design-Regeln:** Insight-Titel statt Metric-Titel; Y-Achse bei Balken ab 0; sortiert nach Wert (nicht alphabetisch); colorblind-freundliche Palette; Spines oben/rechts entfernen.

**Grenzen:** Erfordert lauffähige Python-Umgebung (pandas, matplotlib/seaborn); kein Browser-Output ohne plotly.
