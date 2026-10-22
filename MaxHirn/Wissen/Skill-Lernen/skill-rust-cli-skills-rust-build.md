---
name: skill-rust-cli-skills-rust-build
description: Trockenlauf des Skills rust-cli-skills:rust-build - beschreibt, wie der Rust-Teil des Handelsstacks gebaut und geprüft würde, ohne cargo auszuführen.
metadata:
  type: reference
---

**Zweck:** Erklärt, welche Cargo-Schicht einen Build-Befund erzeugt (Auflösung und Features, Compiler-Kompatibilität, Linken, Profil, Paketierung), und bestimmt die Prüfung danach. Ändert Abhängigkeiten nur, soweit die Aufgabe es verlangt.

**Wann nutzen:** Bei Build-Fehlern, bei Abhängigkeits- oder Feature-Änderungen und bei Profiländerungen für Größe oder Laufzeit.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, wie der Rust-Teil des Handelsstacks geprüft würde, ohne cargo zu starten. Nichts geändert.

**Ergebnis:**

Bestand (lesend): Im Ordner `Agenten/Handel/nautilus-rust/` liegen das Workspace-Manifest und mehrere Crates: `omnitrade-risk`, `quant-alpha`, `quant-planes`, `quant-signal`, `quant-strategy`.

Prüfplan, vor jedem Befehl lesend:
1. Workspace-Manifest: Mitglieder, Pfadabhängigkeiten, Profile (vor allem `release`: LTO, codegen-units, panic). Profile gelten nur auf Workspace-Ebene.
2. `Cargo.lock`: vorhanden und unverändert lassen. Reproduzierbarkeit verlangt `--locked`.
3. Toolchain-Datei, falls vorhanden, und `rust-version`. Der Host-Compiler beweist nichts über den Mindest-Compiler.
4. Feature-Pfade: Welches Crate aktiviert welches Feature, auch transitiv. Ein deaktiviertes Default-Feature auf einer Kante bleibt aktiv, wenn eine andere Abhängigkeit es einschaltet.
5. Befehle, danach, nicht jetzt: `cargo metadata --locked` zur Graphprüfung, `cargo check --workspace --locked` für Kompilierung, `cargo clippy` gemäß Lint-Regeln, `cargo test` nur für die betroffenen Crates.

Fallen unter Windows:
- **Linker:** MSVC- und GNU-Toolchain liefern unterschiedliche Ergebnisse. Ein Host-Build zeigt nicht, ob das Linken auf dem Zielsystem klappt.
- **Systembibliotheken:** Crates mit nativen Abhängigkeiten brauchen auf Windows eigene Installationen.
- **Feature-Kombinationen:** `--all-features` grün heißt nicht, dass der Standardpfad läuft.
- **Build-Skripte und Makros:** Sie laufen beim Bauen mit und gehören zur Vertrauensprüfung.

**Gelernt:** Ein Build-Skill ist nur sinnvoll, wenn er die Schicht des Fehlers benennt, bevor er Abhängigkeiten ändert. Die Warnung, dass ein Host-Build keine Zielplattform beweist, gilt auch für den Handelsstack.

**Grenzen:** Kein cargo ausgeführt, keine Ausgabe gesehen. Der Befehlsplan ist nicht gegen den Bestand gelaufen, und die Profile und Features der einzelnen Crates sind nicht gelesen.
