---
name: skill-agent-protocols-build
description: Trockenlauf des Skills agent-protocols:build - beschreibt den Build-Ablauf für eine kleine Änderung an skill-lernen, ohne Dateien zu ändern.
metadata:
  type: reference
---

**Zweck:** Führt eine Aufgabe in kleinen Schritten aus: Akzeptanzkriterien lesen, Kontext laden, Test schreiben, Implementierung, Regressionslauf, Build, Commit, Aufgabe abhaken. Bei Fehlern greift der Debugging-Ablauf.

**Wann nutzen:** Bei Änderungen an Code mit Tests und Build.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, wie der Build-Ablauf für eine Statusregel in `skill-lernen/SKILL.md` aussähe, und welche Prüfschritte sinnvoll wären. Keine Dateien geändert, nichts committet.

**Ergebnis:** Der Ablauf passt nur eingeschränkt. Für eine Textregel in einem Skill gibt es keine Tests und keinen Build. Der sinnvolle Ablauf wäre:
1. Akzeptanzkriterium: Die neue Regel ist in `SKILL.md` benannt und der Status steht in der festen Wertliste.
2. Kontext: `SKILL.md` und das Format in `fortschritt.md` lesen.
3. Test-Ersatz: Eine Beispielzeile mit dem neuen Status gegen die Wertliste prüfen, zum Beispiel mit einer Suche in der Tabelle.
4. Änderung per gezieltem Edit, nicht per Rewrite.
5. Regressionsersatz: Alle bestehenden Zeilen in `fortschritt.md` gegen die Wertliste prüfen.
6. Build: entfällt.
7. Commit: nur auf ausdrückliche Anweisung.

**Gelernt:** Der Build-Skill setzt Tests und einen Build voraus. Bei reinen Textdateien ist die Prüfung eine Konsistenzprüfung gegen eine feste Wertliste. Der Skill selbst hat dazu keinen Schritt.

**Grenzen:** Der geladene Skill-Text enthielt Schritte, die Dateien ändern und committen (Aufgabe aus einem Plan abarbeiten, Commit). Die Trockenlauf-Vorgabe hatte Vorrang. Diese Schritte wurden nicht ausgeführt.
