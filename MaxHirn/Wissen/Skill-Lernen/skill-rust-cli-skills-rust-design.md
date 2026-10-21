---
name: skill-rust-cli-skills-rust-design
description: Trockenlauf des Skills rust-cli-skills:rust-design - bewertet die Aufteilung des Rust-Teils im Handelsstack in Crates nach Zuständigkeit, ohne Code zu ändern.
metadata:
  type: reference
---

**Zweck:** Entwirft nach Zusammenhalt: Jede Regel hat einen natürlichen Ort, und Aufrufer brauchen wenig Wissen über die Umsetzung. Trennt Parsen, Rechnen und Prozessentscheidungen, wenn ihre Verträge verschieden sind. Traits nur für echte Varianten, keine Abstraktion für jede Struktur.

**Wann nutzen:** Beim Schneiden neuer Crates oder Module, bei Umbauten und bei Reviews, ob eine Grenze etwas bringt.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: die Aufteilung in Crates bewerten, Grenzen zwischen Risiko, Strategie, Signal und Plattform. Nichts geändert.

**Ergebnis:**

Bestand (lesend): Im Ordner `Agenten/Handel/nautilus-rust/` gibt es ein Workspace-Manifest mit fünf Crates und einem Risikomodul:
- `omnitrade-risk`
- `quant-alpha`
- `quant-planes`
- `quant-signal`
- `quant-strategy`

Die Namen legen eine Aufteilung nahe, die nicht gelesen wurde. Ob `omnitrade-risk` die Regeln zentral hält oder ob Strategie-Crates Risikoregeln selbst umsetzen, ist nicht geprüft.

Prüffragen für die Grenzen:
1. **Risiko:** Gibt es genau eine Stelle, die Positionsgrößen und Verlustgrenzen entscheidet? Mehrere Stellen mit eigenen Schwellen sind das größte Risiko.
2. **Strategie:** Dürfen Strategie-Crates Risikoregeln ändern? Wenn ja, ist die Grenze nicht eingehalten.
3. **Signal:** Berechnet ein Signal-Crate Preise oder Indikatoren, die dann zweimal berechnet werden? Das führt zu abweichenden Ergebnissen.
4. **Plattform:** Gibt es Schnittstellen zu Börsen oder Dateien an einer Stelle, oder verteilt in allen Crates?

Empfehlung: Die Grenze prüfen, bevor etwas verschoben wird. Eine Abstraktion ist nur gerechtfertigt, wenn sie mindestens zwei Aufrufer hat, die sich unabhängig ändern.

**Gelernt:** Bei einem Handelswerkzeug ist die wichtigste Grenze die zwischen Entscheidung und Ausführung. Die Risikoregeln sind der einzige Ort, der nicht umgangen werden darf.

**Grenzen:** Es wurden nur Crate-Namen und Manifeste gelesen. Der Quellcode der Module ist nicht gelesen, deshalb ist die Bewertung eine Vorprüfung, kein Befund.
