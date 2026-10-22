---
name: skill-rust-cli-skills-rust-concurrency
description: Trockenlauf des Skills rust-cli-skills:rust-concurrency - prüft lesend, wo der Rust-Teil des Handelsstacks Nebenläufigkeit nutzt, und nennt die wahrscheinlichsten Fehler.
metadata:
  type: reference
---

**Zweck:** Klärt für jede nebenläufige Arbeit, wer sie annimmt, Fehler beobachtet, Abbruch anfordert und auf Abschluss wartet. Unterscheidet CPU-Parallelität von Wartearbeit und prüft Begrenzungen von Warteschlangen und Ergebnissen.

**Wann nutzen:** Beim Einführen oder Ändern von Threads, async-Code, Kanälen oder geteiltem Zustand, und bei Hängern oder verlorenen Fehlern.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: lesend prüfen, wo Nebenläufigkeit im Rust-Teil vorkommen könnte, und die wahrscheinlichsten Fehler nennen. Nichts geändert, nichts ausgeführt.

**Ergebnis:**

Bestand (lesend): In den `.rs`-Dateien unter `Agenten/Handel/nautilus-rust/` findet sich kein Vorkommen von `std::thread`, `tokio`, `mpsc`, `Mutex`, `Arc<` oder `rayon`. In den `Cargo.toml`-Dateien gibt es keine Abhängigkeit auf `tokio` oder `rayon`. Der Rust-Teil ist also nach dieser Suche sequenziell.

Die Suche umfasst nur die Crates unter `nautilus-rust`. Nebenläufigkeit in der Python-Seite des Handels oder in Nautilus selbst ist nicht geprüft.

Wahrscheinlichste Fehler, falls Nebenläufigkeit später hinzukommt:
1. **Verschluckte Fehler:** Ein Thread-`JoinHandle`, der nie gelesen wird, verschluckt Panics.
2. **Unbegrenzte Warteschlangen:** Ein schneller Erzeuger und ein langsamer Verbraucher füllen den Speicher.
3. **Sperre über Wartestellen:** Ein `MutexGuard` bleibt über einen blockierenden Aufruf oder `.await` gehalten.
4. **Nicht abbrechbare Arbeit:** `spawn_blocking` läuft nach Abbruch des Task-Handles weiter.

**Gelernt:** Eine Suche nach Schlüsselwörtern ist ein schneller Befund, aber kein Beweis. Sie zeigt, dass die Crates keine erkennbare Nebenläufigkeit haben. Sie zeigt nicht, dass es keine gibt.

**Grenzen:** Lesend, auf Schlüsselwörter beschränkt. Keine Ausführung und keine Prüfung der Abhängigkeitsbäume über `cargo tree`.
