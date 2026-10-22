---
name: skill-agent-protocols-planning-and-task-breakdown
description: Aufgaben-Zerlegung in verifizierbare Scheiben — Abhängigkeitsgraph, vertikales Slicing, Aufgabenformat mit Akzeptanzkriterien, Checkpoints.
metadata:
  type: reference
---

**Zweck:** Fünfstufiger Planungsprozess: Plan-Mode (nur lesen) → Abhängigkeitsgraph → vertikale Scheiben → strukturierte Aufgaben mit Akzeptanzkriterien → Checkpoints alle 2–3 Aufgaben. Größentabelle XS–XL; ab L aufbrechen. Parallelisierungsregel: unabhängige Scheiben parallel, Migrationsketten und gemeinsamer Zustand sequenziell.

**Wann nutzen:** Vor jeder Mehrdatei-Implementierung, wenn eine Aufgabe zu groß oder vage wirkt, wenn Parallelisierung geplant wird, und wenn der Plan einem Menschen kommuniziert werden soll.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~3 Seiten. Sehr praxisnah: Markdown-Vorlage für Plan-Dokument und Aufgaben-Format direkt verwendbar.

**Gelernt:** "Und im Aufgabentitel = zwei Aufgaben" — einfache Heuristik. Vertikales Slicing statt horizontalem passt zur BrainFiles-Zweigstrategie: ein Zweig je Feature-Pfad, nicht ein Zweig je Schicht. Plan-Dokument in `Werkstatt/Projekte/` ablegen, weil "Context windows sind endlich — schriftliche Pläne überleben Session-Grenzen und Kompaktierung."

**Grenzen:** Fokus auf Software-Features; für Handels-Strategie-Entwicklung oder Skript-Wartung gilt das Prinzip (Aufgaben mit Akzeptanzkriterien), aber das Markdown-Vorlageformat ist überdimsensioniert.
