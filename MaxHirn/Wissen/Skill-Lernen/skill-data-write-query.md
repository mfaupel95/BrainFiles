---
name: skill-data-write-query
description: Trockenlauf des Skills data:write-query — SQL aus natürlicher Sprache schreiben; dialektspezifisch; CTE-First; Performance-optimiert; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** SQL-Abfragen aus freier Beschreibung erzeugen — korrekt, lesbar, dialektgerecht.

**Wann nutzen:** `write-query <Beschreibung>` — wenn eine SQL-Frage gestellt wird ohne bekannte Tabellennamen oder wenn schnell ein Muster gebraucht wird.

**Lauf:** 2026-10-22, trockenlauf.

**6-Schritt-Workflow:**
1. Anfrage parsen (Output-Spalten, Filter, Aggregation, Joins, Sortierung, Limit)
2. SQL-Dialekt klären (PostgreSQL, Snowflake, BigQuery, Redshift, Databricks, MySQL, MSSQL, DuckDB, SQLite)
3. Schema erkunden (wenn Warehouse-MCP verbunden)
4. Query schreiben (CTE-First, kein `SELECT *`, früh filtern)
5. Query präsentieren + Erklärung pro CTE
6. Ausführung anbieten (wenn verbunden)

**CTE-Namensregel:** Beschreibend (`daily_signups`, nicht `cte1`); ein CTE pro logischer Transformation.

**Performance-Regeln:**
- Kein `SELECT *`
- Partition-Filter immer zuerst (BigQuery/Snowflake)
- `EXISTS` statt `IN` bei großen Subqueries
- JOIN-Typ korrekt (kein LEFT JOIN wo INNER korrekt)
- Korrelierte Subqueries vermeiden

**Unterschied zu data:sql-queries:** write-query ist der ausführende Skill (schreibt auf Anfrage), sql-queries ist die Dialekt-Referenzbibliothek.
