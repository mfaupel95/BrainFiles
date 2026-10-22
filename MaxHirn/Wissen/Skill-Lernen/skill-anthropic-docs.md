---
name: skill-anthropic-docs
description: Trockenlauf des Skills anthropic-skills:docs — reiner Weiterleitungs-Skill zum Docs-Connector; ohne verbundenen Docs-MCP nicht ausführbar.
metadata:
  type: reference
---

**Zweck:** Delegiert vollständig an den Docs-Connector (Claude Docs MCP). Eigene Logik: keine. Wenn keine Docs-Tools verfügbar → Fehlermeldung ausgeben.

**Wann nutzen:** Wenn Claude Docs (claude.ai/artifact) Dokumente gelesen oder bearbeitet werden sollen.

**Lauf:** 2026-10-22, nicht-ausführbar — Docs-Connector in dieser Sitzung nicht als lokaler MCP verbunden (nur als claude.ai-Connector verfügbar).

**Ergebnis:** Skill vollständig geladen. ~2 Zeilen Inhalt. Enthält keine eigenständigen Anweisungen außer "folge dem Connector".

**Gelernt:** Manche Skills sind reine Hüllen, die auf MCP-Connectoren zeigen. Wert liegt im Connector, nicht im Skill-Text selbst. Vergleichbar mit `agent-memory:memory-search`.

**Grenzen:** Ohne Docs-Connector wertlos. Kein Fallback-Verhalten definiert außer "say so".
