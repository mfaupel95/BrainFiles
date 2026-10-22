---
name: skill-anthropic-mcp-builder
description: Trockenlauf des Skills anthropic-skills:mcp-builder — vollständiger 4-Phasen-Entwicklungsguide für MCP-Server (TypeScript-first); API-Coverage vs. Workflow-Tools, SDK v1 vs. v2, Evaluations-Framework.
metadata:
  type: reference
---

**Zweck:** MCP-Server von Grund auf entwickeln — von der Planung über Implementierung und Tests bis zu Evaluierungsfragen. Empfohlener Stack: TypeScript + Streamable HTTP (remote) oder stdio (lokal).

**Wann nutzen:** Wenn ein neuer MCP-Server gebaut oder ein bestehender erweitert werden soll. Nicht für Konfiguration bestehender Server → dafür `local-ai-config-doctor`.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~5 Seiten. Gut strukturierter Entwicklungs-Workflow, viele externe Referenzdokumente.

**Gelernt — 4 Phasen:**

1. **Research & Planning** — MCP-Spec lesen (sitemap.xml → spezifische .md-Seiten), SDK-Wahl (v2 = `@modelcontextprotocol/server` für neue Projekte; v1 = `@modelcontextprotocol/sdk` nur für Bestandsprojekte, Migration per `npx @modelcontextprotocol/codemod@latest v1-to-v2 .`), API-Coverage vs. Workflow-Tools abwägen (bei Unsicherheit: Coverage-first)

2. **Implementierung** — Zod (TS) / Pydantic (Py) für Input-Schemas, `outputSchema` + `structuredContent` für strukturierte Ausgaben, Tool-Annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`), konsistente Präfixe (z. B. `github_create_issue`)

3. **Review & Test** — `npm run build`, v2-Self-Check-Skript, MCP Inspector (`npx @modelcontextprotocol/inspector`)

4. **Evaluations** — 10 Fragen erstellen: unabhängig, read-only, komplex (mehrere Tool-Calls), realistisch, verifizierbarer Einzelwert, zeitstabil. XML-Format. Erst Fragen, dann Antworten selbst verifizieren.

**Wichtige Design-Regeln:**
- Actionable Error Messages: Fehlermeldungen sollen auf Lösungen zeigen
- Responsegröße klein halten: agenten profitieren von fokussierten, paginierten Ergebnissen
- v1 und v2 nicht mischen (unterschiedliche Import-Pfade)
- Streamable HTTP für Remote (stateless JSON), stdio für lokal

**Grenzen:** Braucht WebFetch für SDK-Docs (externe URLs). Referenzdateien `reference/mcp_best_practices.md`, `reference/node_mcp_server_v2.md`, `reference/python_mcp_server.md`, `reference/evaluation.md` im Skill-Verzeichnis. Kein fertiger Code — gibt Struktur und Muster, Implementation liegt beim Nutzer.
