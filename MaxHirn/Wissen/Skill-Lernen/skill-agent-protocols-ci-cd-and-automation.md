---
name: skill-agent-protocols-ci-cd-and-automation
description: CI/CD-Pipeline aufbauen und warten — Quality Gates, GitHub Actions, Deployment-Strategien, Rollback.
metadata:
  type: reference
---

**Zweck:** Beschreibt das vollständige CI/CD-Muster für Webprojekte: Quality-Gate-Pipeline (Lint → Typecheck → Tests → Build → Security → Bundle), GitHub-Actions-Konfiguration, Preview-Deployments, Feature-Flags, Staged Rollouts und Rollback.

**Wann nutzen:** Neues Projekt einrichten, CI-Pipeline anpassen, Deployment-Automatisierung aufbauen, CI-Fehler debuggen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht, was der Skill leistet. Kein GitHub-Actions-Projekt vorhanden.

**Ergebnis:** Skill vollständig geladen. Enthält vollständige YAML-Vorlagen für einfache Pipeline, Datenbank-Integration, E2E-Tests (Playwright), Dependabot und manuellen Rollback. Kern-Prinzip: Kein Gate überspringen; Fehler beheben, nicht deaktivieren.

**Gelernt:** Der Skill deckt auch den Rückkopplungskreis Agent→CI ab: CI-Fehlerausgabe direkt an den Agenten übergeben, der dann lokal repariert und neu pusht. Für BrainFiles nicht direkt anwendbar (kein Web-Build-Schritt), aber das Muster `wachen-Skript → Fehlerlog → Korrektur` ist dasselbe wie bei den Handelstests.

**Grenzen:** Ausschließlich auf Node/npm/GitHub-Actions zugeschnitten. PowerShell-Routinen, Python-venvs und Kraken-API-Verbindungen kommen nicht vor.
