---
name: skill-data-build-dashboard
description: Trockenlauf des Skills data:build-dashboard — erzeugt selbständige interaktive HTML-Dashboards mit Chart.js; lokal; kein API-Aufruf; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Interaktives, browserfähiges HTML-Dashboard aus Daten bauen — KPI-Karten, Charts, Filter, sortierbare Tabellen, kein Server nötig.

**Wann nutzen:** `build-dashboard <Beschreibung> [Datenquelle]` — für Berichte, Metriken-Überblicke, Teamdashboards.

**Lauf:** 2026-10-22, trockenlauf.

**Gelernt — 7-Schritt-Workflow:**
1. Anforderungen verstehen (Zweck, Audience, Metriken, Filter)
2. Daten holen (Warehouse-MCP, Paste, CSV oder Beispieldaten)
3. Layout entwerfen (KPI-Karten oben, Charts mitte, Tabelle unten)
4. HTML bauen (Chart.js v4.5.1 via CDN, eingebettetes JSON)
5. Charttypen implementieren (Line, Bar, Doughnut, Mixed)
6. Interaktivität (Dropdown-Filter, Datumspicker, sortierbare Tabelle)
7. Speichern + Browser öffnen

**Performance-Grenzen:**

| Datenmenge | Vorgehen |
|---|---|
| <1.000 Zeilen | Direkt einbetten |
| 1.000–10.000 | Pre-aggregieren |
| >100.000 | Nicht geeignet → BI-Tool |

**Design-System:** CSS-Variablen (Farben, Spacing, Radius); responsive Grid; Druckstile.

**Grenzen:** Snapshot-Dashboard (kein Echtzeit); für echte Echtzeit BI-Tool empfohlen.
