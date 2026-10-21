---
name: skill-agent-protocols-deprecation-and-migration
description: Alten Code sicher entfernen — Entscheidungsrahmen, Migrationsprozess, Strangler/Adapter/Feature-Flag-Muster.
metadata:
  type: reference
---

**Zweck:** Leitfaden zum Entfernen von Code, der seinen Wert nicht mehr rechtfertigt. Kernprinzip: Code ist eine Verbindlichkeit, keine Anlage. Enthält Deprecation-Entscheidungsfragen, Churn-Regel (wer die Infrastruktur deprecatiert, migriert auch die Nutzer), und drei Migrationsmuster (Strangler, Adapter, Feature-Flag).

**Wann nutzen:** Altes System durch neues ersetzen, Feature abschalten, doppelte Implementierungen konsolidieren, Zombie-Code beseitigen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. Enthält Hyrum's Law als Erklärung warum Ankündigungen allein nicht reichen, Advisory vs. Compulsory Deprecation, Migrationsprozess in vier Schritten, Zombie-Code-Definition und Checkliste.

**Gelernt:** Deprecation-Planung beginnt beim Design, nicht erst wenn der Nachfolger fertig ist. Direkt anwendbar: `Agenten/Handel/` enthält mehrere veraltete Dateien (alter DCA-Code, ausgemusterte Scanner-Varianten) — bevor die entfernt werden, müssen aktive Nutzung (Importe, Tests) gemessen und eine Migrationsnotiz angelegt werden.

**Grenzen:** Infrastrukturmigrationen (Datenbankschema, API-Versionierung) werden nur oberflächlich erwähnt. Für Schema-Migrationen ist ein separater DB-Migrations-Skill nötig.
