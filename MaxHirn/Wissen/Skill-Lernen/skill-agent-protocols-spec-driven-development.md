---
name: skill-agent-protocols-spec-driven-development
description: Strukturierte Spezifikation vor Code — vier Phasen mit menschlicher Freigabe, sechs Pflichtbereiche, Annahmen explizit machen, lebendiges Dokument.
metadata:
  type: reference
---

**Zweck:** Vier-Phasen-Gate-Workflow: Specify → Plan → Tasks → Implement, jede Phase mit Mensch-Review. Spec-Vorlage mit sechs Pflichtbereichen: Objective, Commands, Projektstruktur, Code-Stil (Beispiel besser als Beschreibung), Teststrategie, Grenzen (Always/Ask/Never). Annahmen explizit nennen bevor mit dem Schreiben begonnen wird. Vage Anforderungen als Akzeptanzkriterien umformulieren.

**Wann nutzen:** Neues Projekt oder Feature, mehrdeutige Anforderungen, mehrere Dateien betroffen, Architekturentscheidungen, Aufgabe über 30 Minuten. Nicht bei einzeiligen Fixes oder unzweideutigen Änderungen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~3 Seiten. Direkt anwendbar auf Werkstatt-Projekte: Spec nach `Werkstatt/Projekte/<name>/spec.md`.

**Gelernt:** "Annahmen sind die gefährlichste Form von Missverständnissen" — Annahmen-Block vor dem ersten Spec-Satz schreiben. "Requirements as success criteria" — statt "mach das Dashboard schneller": LCP < 2,5 s, CLS < 0,1. Spec versioniert committen, in PR-Beschreibung verlinken. Passt zum BrainFiles-Prinzip "aus jedem Anwendungsfall eine wiederholbare Aufgabe".

**Grenzen:** Prozess-Skill ohne eigene Tools. Für Einzel-Skript-Wartung (Routinen, Handelsskripte) ist die sechsteilige Vorlage zu schwer — Zwei-Zeilen-Spec (Ziel + Akzeptanzkriterium) genügt laut Skill selbst.
