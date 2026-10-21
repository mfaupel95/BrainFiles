---
name: skill-agent-protocols-internationalization-and-localization
description: Mehrsprachigkeit von Anfang an — String-Extraktion, ICU-Pluralisierung, RTL-Layout, Pseudo-Lokalisierung als CI-Gate.
metadata:
  type: reference
---

**Zweck:** Sechsstufiger i18n/l10n-Prozess: Oberflächen inventarisieren → Strings extrahieren (stabile Keys, ICU MessageFormat) → Layout für Texterweiterung (DE ~30% länger als EN) → Locale-Daten (UTC-Speicherung, lokale Formatierung) → Quality Gates (Pseudo-Lokalisierung in CI) → API-Strategie (Accept-Language oder Client-seitige Auflösung).

**Wann nutzen:** Zweite Sprache hinzufügen, hartkodierte Strings in Komponenten, RTL-Sprachen, locale-sensitive Sortierung.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. Kompakter Skill (~1,5 Seiten). Pseudo-Lokalisierung als CI-Check war neu — Strings verlängern und Akzente hinzufügen um Clipping zu finden, ohne echte Übersetzung.

**Gelernt:** "Keine String-Konkatenation für Sätze" — Übersetzer brauchen vollständige Sätze mit Platzhaltern. Direkt auf Artifact-Arbeit anwendbar: falls Artifacts jemals mehrsprachig werden, RTL-Layout mit `margin-inline-start` statt `margin-left` von Anfang an. BrainFiles selbst ist einsprachig (DE), dieser Skill daher niedrige direkte Priorität.

**Grenzen:** Web/React-fokussiert. Für PowerShell-Skripte und Python-CLIs gelten nur die Datum/Zahl-Formatierungsregeln (immer `datetime`-Objekte mit Timezone-Info, nie manuelle Separatoren).
