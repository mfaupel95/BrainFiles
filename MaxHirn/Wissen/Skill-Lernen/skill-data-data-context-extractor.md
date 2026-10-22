---
name: skill-data-data-context-extractor
description: Trockenlauf des Skills data:data-context-extractor — Meta-Skill zum Destillieren firmenspezifischen Datenwissens aus Analysten und Generieren eines maßgeschneiderten data-analyst-Skills; kein DB-Zugriff nötig; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Firmenspezifisches Datenwissen in einen wiederverwendbaren Skill destillieren — entweder von Grund auf (Bootstrap) oder durch Ergänzung eines bestehenden Skills (Iteration).

**Wann nutzen:** Wenn eine neue Datenumgebung (Warehouse, Domäne) erschlossen werden soll und ein maßgeschneiderter Analyse-Skill fehlt.

**Lauf:** 2026-10-22, trockenlauf.

**Zwei Modi:**

| Modus | Wann | Ablauf |
|---|---|---|
| Bootstrap | Neuer Skill von Null | DB-Discovery → 5 Kernfragen → Skill-Struktur generieren → Zippen |
| Iteration | Bestehender Skill, Lücke gefunden | Lücke identifizieren → Tabellen erkunden → Referenzdatei ergänzen → Neupaket |

**5 Kernfragen (Bootstrap, nacheinander):**
1. Entitäts-Disambiguierung — „Was meint ihr mit 'User'?"
2. Primär-IDs — „Wie identifiziert ihr eine [Entität]?"
3. Key Metrics — „Welche 2-3 Metriken fragt ihr am häufigsten ab?"
4. Data Hygiene — „Was wird immer rausgefiltert?"
5. Common Gotchas — „Welche Fehler machen neue Analysten typisch?"

**Ausgabe-Struktur:**
```
[company]-data-analyst/
├── SKILL.md
└── references/
    ├── entities.md
    ├── metrics.md
    ├── tables/[domain].md
    └── dashboards.json (optional)
```

**Grenzen:** Erfordert Zugang zu einem Warehouse-MCP oder manuelle Dateneingabe; ohne Daten nur ein Interview-Gerüst.
