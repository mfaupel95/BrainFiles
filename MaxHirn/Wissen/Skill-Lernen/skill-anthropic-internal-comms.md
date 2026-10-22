---
name: skill-anthropic-internal-comms
description: Trockenlauf des Skills anthropic-skills:internal-comms — Dispatcher für interne Unternehmenskommunikation (3P-Updates, Newsletter, FAQ, Status-Reports); lädt je nach Typ eine Beispiel-Datei.
metadata:
  type: reference
---

**Zweck:** Dispatcher für interne Kommunikation. Identifiziert den Kommunikationstyp und lädt die passende Vorlage aus `examples/`: 3P-Updates, Company-Newsletter, FAQ-Antworten, General-Comms.

**Wann nutzen:** Für interne Unternehmens-Texte: Fortschritts-/Plan-/Problem-Updates, Newsletters, FAQs, Status-Reports, Leadership-Updates, Incident-Reports.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~1 Seite. Reiner Dispatcher — eigene Logik minimal. Wert liegt in den `examples/`-Dateien.

**Gelernt:** Skill-Struktur "Dispatcher + Beispiel-Dateien" ist ein wiederkehrendes Muster (ähnlich wie security-and-hardening mit `references/`). Die eigentlichen Regeln stehen nicht im Skill-Text, sondern in externen Dateien, die zur Laufzeit gelesen werden.

**Grenzen:** Ohne Zugriff auf `examples/`-Dateien nur ein Gerüst. Kein Fallback-Verhalten für unbekannte Kommunikationstypen (→ Nachfrage).
