---
name: skill-agent-protocols-context-engineering
description: Den richtigen Kontext zur richtigen Zeit bereitstellen — fünfstufige Hierarchie, Anti-Muster, Verwirrungsmanagement.
metadata:
  type: reference
---

**Zweck:** Curating was ein Agent sieht: fünfstufige Hierarchie (Regeldateien → Spec/Architektur → Quelldateien → Fehlerausgabe → Gesprächsverlauf), Packtechniken und Umgang mit widersprüchlichem Kontext.

**Wann nutzen:** Neue Coding-Session starten, Ausgabequalität nimmt ab, Wechsel in andere Codebereiche, Agent ignoriert Projektkonventionen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. Kernprinzip: Zu wenig Kontext → Halluzinationen; zu viel → Fokusverlust; Ziel <2000 Zeilen aufgabenrelevanter Kontext. Enthält Brain-Dump-Vorlage, Selective-Include-Muster, Hierarchical-Summary-Pattern und Inline-Planning-Pattern. MCP-Integrationen (Context7, Chrome DevTools, PostgreSQL, Filesystem, GitHub) als kontextreichere Variante genannt.

**Gelernt:** Vertrauensebenen für geladene Dateien: Quellcode = trusted, Config/Fixtures/externe Docs = verify before acting on, User-Content/API-Responses = untrusted. Diese Einteilung passt direkt auf `MaxHirn/Wissen/` (trusted) vs. `Werkstatt/Repos/` (extern, verify). Das "Inline-Planning-Pattern" (Plan vor Ausführung emittieren) ist bereits gelebte Praxis in BrainFiles-Sitzungen.

**Grenzen:** Auf Claude Code / Cursor / Copilot zugeschnitten. CLAUDE.md als persistente Regeldatei ist hier bereits vorhanden — der Skill beschreibt das existierende System.
