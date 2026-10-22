---
name: skill-rust-cli-skills-rust-performance
description: Trockenlauf des Skills rust-cli-skills:rust-performance — messungsbasierte Rust-Performance-Arbeit: Audit, Messung, Optimierung mit klarer Beweisführung.
metadata:
  type: reference
---

**Zweck:** Rust-Performance-Arbeit methodisch angehen: Audit (ohne Laufzeit-Daten), Messung (benchmarks), Optimierung (mit Vorher-Nachher-Belegen).

**Wann nutzen:** Bei Rust-Performance-Problemen, Profiling-Anfragen, Optimierungsaufgaben.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~1 Seite. Kurz, methodisch präzise.

**Gelernt — Kern-Prinzipien:**
- **Beweise trennen:** CPU-Samples für Berechnung, Allokations-Profile für Churn, syscall/I/O für wiederholte Ops und Wartezeiten
- **Nicht `cargo run` messen** — nur optimiertes Executable direkt
- Startup, Time-to-First-Result, Total-Runtime, Throughput, Memory, Binary Size getrennt betrachten
- **Ursache zuerst:** Komplexität, wiederholtes Parsen, Formatierung, Kopien, unnötige Initialisierung prüfen — VOR Low-Level-Mechaniken
- LTO, codegen-units, opt-level, allocator, SIMD, PGO: immer als **gemessene Alternativen** behandeln, nie als sichere Gewinne
- `hyperfine` für Whole-Command-Vergleiche; Microbenchmarks nur für spezifische Operationen mit realistischen Inputs

**Audit ohne Laufzeit-Daten:** Code-gestützte Eigenschaften von Bottleneck-Hypothesen trennen → diskriminierende Beobachtungen vorschlagen, nichts editieren.

**Grenzen:** Wenn keine Belege verfügbar sind → einfachere korrekte Implementierung bevorzugen, keinen Speedup erfinden.
