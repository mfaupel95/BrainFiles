---
name: skill-data-explore-data
description: Trockenlauf des Skills data:explore-data — vollständiges Datenprofil einer Tabelle oder Datei; Qualitätsbewertung, Muster-Erkennung, Schema-Dokumentation; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Einen unbekannten Datensatz schnell verstehen — Struktur, Qualität, Muster, Beziehungen — bevor eine eigentliche Analyse beginnt.

**Wann nutzen:** `explore-data <tabelle_oder_datei>` — immer als erster Schritt bei neuen Daten, vor dem Schreiben von Abfragen.

**Lauf:** 2026-10-22, trockenlauf.

**7-Schritt-Workflow:**
1. Datei/Tabelle laden (Warehouse-MCP oder Upload)
2. Struktur verstehen (Grain, PK, Zeitraum)
3. Profil generieren (Null-Rate, Distinct, Top-Values, Verteilung)
4. Datenqualitätsprobleme markieren
5. Beziehungen und Muster entdecken
6. Beste Dimensionen/Metriken vorschlagen
7. 3–5 Folgeanalysen empfehlen

**Spalten-Klassifikation:**
- Identifier, Dimension, Metric, Temporal, Text, Boolean, Structural

**Qualitäts-Ampel:**
- Grün: >99% nicht-null | Gelb: 95–99% | Orange: 80–95% | Rot: <80%

**Red Flags:** Placeholder-Werte (0, -1, 999999, „N/A"), runde Zahlen (Schätzung), Zukunftsdaten in Historik, negative Werte wo positiv erwartet.

**Muster-Erkennung:** Normal/Rechtsskew/Bimodal-Verteilungen; Trend/Saisonalität/Change-Points bei Zeitreihen; Korrelationsmatrix (|r|>0.7 markieren).

**Grenzen:** Bei >100M Zeilen wird Sampling verwendet; ohne Warehouse-MCP nur Datei-Upload oder manuelle Schema-Beschreibung möglich.
