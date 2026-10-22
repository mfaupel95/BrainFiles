---
name: skill-agent-protocols-source-driven-development
description: Offizielle Dokumentation vor Framework-Code — Stack-Erkennung, Docs fetchen, Quellenangabe im Code, UNVERIFIED-Flag für nicht verifizierbares.
metadata:
  type: reference
---

**Zweck:** Vier-Schritte-Prozess: Stack-Versionen aus package.json/requirements.txt ermitteln → relevante Dokumentationsseite fetchen (nicht Homepage, sondern Deep-Link) → dokumentierte Muster umsetzen → Quellen zitieren (URL-Kommentar im Code). Quellenrangfolge: offizielle Docs > offizieller Blog/Changelog > MDN/Web-Standards. Stack Overflow und Blog-Posts nie als primäre Quellen. Nicht-verifizierbares explizit als UNVERIFIED markieren.

**Wann nutzen:** Jedes Mal vor framework-spezifischem Code aus dem Gedächtnis. Besonders bei Formularen, Routing, Datenabruf, Auth, State-Management — Bereichen wo sich Best Practices schnell ändern.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~3 Seiten. Kernprinzip: Trainings-Daten veralten still — Verifikation ist keine Vorsichtsmaßnahme sondern Pflicht.

**Gelernt:** "Simple tasks with wrong patterns become templates" — besonders relevant für BrainFiles-Skills und Handels-Bausteine die kopiert werden. Konflikt-Muster: wenn Docs vs. bestehender Code divergieren, explizit ansprechen statt still entscheiden. Für Python-Projekte (Handel): dieselbe Logik mit `pyproject.toml`/`requirements.txt` und docs.python.org/pydocs für Pandas, SQLAlchemy etc. UNVERIFIED-Flag ist wertvoller als eine vage Einschränkung ("might be outdated").

**Grenzen:** Setzt WebFetch voraus. In Offline-Umgebungen oder bei sehr alten Bibliotheken ohne gute Online-Docs schwieriger anwendbar. Für PowerShell und PS-Module gibt es keine gleichermaßen strukturierten Deep-Link-Docs.
