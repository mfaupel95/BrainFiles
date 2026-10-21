---
name: skill-agent-protocols-code-simplification
description: Code vereinfachen ohne Verhalten zu ändern — fünf Prinzipien, konkrete Muster und inkrementeller Prozess.
metadata:
  type: reference
---

**Zweck:** Anleitung zum Vereinfachen von Code nach dem Motto "einfacher zu verstehen, nicht kürzer". Fünf Prinzipien: Verhalten exakt erhalten, Projektkonventionen folgen, Klarheit über Cleverness, Balance halten, Scope begrenzen.

**Wann nutzen:** Nach einer fertigen Feature-Implementierung, bei Review-Kommentaren zu Komplexität, beim Refactoring unter Zeitdruck entstandenen Codes. Nicht benutzen, wenn der Code schon klar ist oder kurz vor einem Totalrewrite steht.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht. Kein Zielcode vorhanden.

**Ergebnis:** Skill vollständig geladen. Enthält Signaltabellen für strukturelle Komplexität (tiefe Verschachtelung, lange Funktionen, verschachtelte Ternaries, Boolean-Flags), Namensgebung (generische Namen, Abkürzungen) und Redundanz (duplizierte Logik, toter Code). Sprachspezifische Beispiele: TypeScript/JS, Python, React/JSX.

**Gelernt:** Chesterton's Fence als expliziter Schritt: erst verstehen warum der Code so ist, dann ändern. Regel der 500 Zeilen: ab 500 betroffenen Zeilen Automatisierung (codemods, sed, AST-Transforms) statt manueller Bearbeitung. Refactoring immer in separatem Commit/PR von Feature-Arbeit trennen.

**Grenzen:** Auf TypeScript/JS/Python/React zugeschnitten. PowerShell- und Python-venv-spezifische Vereinfachungen kommen nicht vor.
