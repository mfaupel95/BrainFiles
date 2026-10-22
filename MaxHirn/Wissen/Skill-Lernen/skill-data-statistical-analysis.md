---
name: skill-data-statistical-analysis
description: Trockenlauf des Skills data:statistical-analysis — Statistik-Referenz für Analysten; Deskriptiv, Trend, Ausreißer, Hypothesentests, Fallstricke; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Korrekte statistische Aussagen aus Daten ableiten — von Lagemaßen bis zu Hypothesentests.

**Wann nutzen:** Immer wenn Metriken verglichen, Trends bewertet oder Signifikanz beurteilt werden soll.

**Lauf:** 2026-10-22, trockenlauf.

**Wichtigste Regel:** Mean + Median immer zusammen berichten — große Differenz = schiefe Verteilung, Mean allein irreführend.

**Lagemaß-Auswahl:**
- Symmetrisch, keine Ausreißer → Mittelwert
- Schief (z. B. Revenue, Session-Dauer) → Median
- Kategorisch / ordinal → Modus

**Ausreißer-Erkennung (Python):**
- IQR-Methode (robust): `Q1 - 1.5*IQR` bis `Q3 + 1.5*IQR`
- Z-Score (normal): `|z| > 3`
- Ausreißer NICHT automatisch entfernen — erst untersuchen (Datenfehler, echte Extreme, andere Population)

**Hypothesentest-Auswahl:**
- 2 Gruppen, Mittelwert → t-Test
- Conversion-Raten → z-Test für Proportionen
- Vorher/Nachher → Paired t-Test
- Nicht-normal, 2 Gruppen → Mann-Whitney U
- 2 Kategorialvariablen → Chi²

**Statistisch signifikant ≠ praktisch bedeutsam** — immer Effektgröße + Konfidenzintervall + Business-Impact berichten.

**Fallstricke (Kurzliste):**
1. Korrelation ≠ Kausalität
2. Multiple Comparisons → Bonferroni
3. Simpson's Paradox → immer segmentweise prüfen
4. Survivorship Bias → fehlende Entitäten mitdenken
5. Falsche Präzision → Bereiche statt exakte Zahlen bei Prognosen
