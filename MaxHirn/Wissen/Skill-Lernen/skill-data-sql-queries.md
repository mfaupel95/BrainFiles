---
name: skill-data-sql-queries
description: Trockenlauf des Skills data:sql-queries — SQL-Referenz für alle großen Warehouse-Dialekte (PostgreSQL, Snowflake, BigQuery, Redshift, Databricks); Pattern-Bibliothek; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Korrektes, performantes SQL über alle großen Warehouses schreiben — Dialektunterschiede nachschlagen, Muster kopieren.

**Wann nutzen:** Immer wenn Dialekt-spezifische Syntax unsicher ist oder ein Standardmuster (Cohort, Funnel, Dedup) gebraucht wird.

**Lauf:** 2026-10-22, trockenlauf.

**Dialekt-Unterschiede (Kernauswahl):**

| Funktion | PostgreSQL | Snowflake | BigQuery | Redshift | Databricks |
|---|---|---|---|---|---|
| Aktuelles Datum | `CURRENT_DATE` | `CURRENT_DATE()` | `CURRENT_DATE()` | `CURRENT_DATE` | `CURRENT_DATE()` |
| Datumsaddition | `+ INTERVAL '7 days'` | `DATEADD(day,7,col)` | `DATE_ADD(col,INTERVAL 7 DAY)` | `DATEADD(day,7,col)` | `DATE_ADD(col,7)` |
| Trunken | `DATE_TRUNC('month',col)` | `DATE_TRUNC('month',col)` | `DATE_TRUNC(col,MONTH)` | `DATE_TRUNC('month',col)` | `DATE_TRUNC('MONTH',col)` |
| Case-insensitiv Like | `ILIKE` | `ILIKE` | `LOWER() LIKE` | `ILIKE` | — |
| Division sicher | `NULLIF(d,0)` | `NULLIF(d,0)` | `SAFE_DIVIDE(n,d)` | `NULLIF(d,0)` | `NULLIF(d,0)` |

**Pattern-Bibliothek:**
- **Dedup:** `ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC)` → `WHERE rn=1`
- **Funnel:** `MAX(CASE WHEN event='x' THEN 1 ELSE 0 END)` pro Step, dann prozentual
- **Cohort-Retention:** Cohort-Monat + Activity-Monat → CASE WHEN offset je Periode
- **Running Total:** `SUM(val) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)`
- **% of Total:** `val / SUM(val) OVER (PARTITION BY kategorie)`

**CTE-Regel:** Immer für Lesbarkeit — Base → Metriken → Zusammenfassung.

**Performance je Dialect:**
- BigQuery: Partition-Filter Pflicht (kostenpflichtig pro Byte), kein `SELECT *`
- Snowflake: Clustering-Keys statt Indizes; `RESULT_SCAN(LAST_QUERY_ID())`
- Redshift: DISTKEY/SORTKEY für Join-Performance
- PostgreSQL: `EXPLAIN ANALYZE`; `EXISTS` statt `IN` bei Subqueries
