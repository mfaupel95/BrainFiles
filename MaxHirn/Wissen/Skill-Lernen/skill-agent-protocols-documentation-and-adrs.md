---
name: skill-agent-protocols-documentation-and-adrs
description: Entscheidungen dokumentieren statt Code — ADR-Vorlage, Inline-Kommentare nur für das Warum, README-Struktur.
metadata:
  type: reference
---

**Zweck:** Anleitung für wertvolle Dokumentation: ADRs (Architecture Decision Records) für große Entscheidungen, Inline-Kommentare nur für das *Warum* (nie das *Was*), API-Dokumentation, README-Aufbau und Changelog-Pflege.

**Wann nutzen:** Architekturentscheidung treffen, API hinzufügen, Feature shippen, neues Teammitglied onboarden, dieselbe Erklärung wiederholt geben.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ADR-Template mit Status-Lifecycle (Proposed→Accepted→Superseded/Deprecated), Speicherort `docs/decisions/` mit Nummerierung. Abschnitt "Dokumentation für Agenten" hebt hervor: CLAUDE.md, Spec-Dateien und ADRs helfen Agenten, Entscheidungen nicht neu zu treffen.

**Gelernt:** Der Skill bestätigt das bestehende BrainFiles-Muster: CLAUDE.md ist die persistente Regeldatei, Wiki/ speichert Entscheidungskontext (entspricht ADRs). Der Vault fehlt nur die explizite Nummerierung und das Status-Feld — das wäre ein einfacher Verbesserungsschritt für `MaxHirn/Wiki/`.

**Grenzen:** Auf TypeScript/OpenAPI-Projekte zugeschnitten. Für PowerShell-Skripte und Python-Werkzeuge gibt es kein direktes Äquivalent zu JSDoc — dort leisten kurze Kommentarblöcke am Skriptkopf und Einträge in `Wiki/` dasselbe.
