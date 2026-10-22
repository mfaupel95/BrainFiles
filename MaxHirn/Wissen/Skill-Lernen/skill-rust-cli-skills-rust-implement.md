---
name: skill-rust-cli-skills-rust-implement
description: Trockenlauf des Skills rust-cli-skills:rust-implement - beschreibt, wie eine kleine Änderung am Rust-Teil des Handelsstacks umgesetzt und geprüft würde, am Beispiel der expect-Stellen in quant-planes.
metadata:
  type: reference
---

**Zweck:** Setzt ein klares Verhalten direkt um, im bestehenden Pfad, mit vorhandener Formatierung, Kompilierung und gezielten Tests. Ein Fehler wird vor dem Fix so reproduziert, dass er aus dem gemeldeten Grund fehlschlägt.

**Wann nutzen:** Bei abgegrenzten Änderungen mit klarem Ziel. Nicht für offene Entwurfsfragen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, wie eine kleine Änderung am Rust-Teil umgesetzt und geprüft würde. Kein Code geändert, nichts ausgeführt.

**Ergebnis:**

Ausgangslage (lesend): In `quant-planes/src/main.rs` liest `read_lock()` die Datei `Cargo.lock` eine Ebene über dem Crate. Fehlt die Datei oder ist sie kaputt, bricht das Programm mit `expect` ab, also mit Panic statt mit Fehlermeldung und Exit-Code.

Schritte für die Änderung:
1. **Reproduktion zuerst:** Einen Lauf mit einer fehlenden oder kaputten `Cargo.lock` in einem Testverzeichnis anstoßen. Erwartet: Panic. Dieses Fehlschlagen ist die Grundlage für den Test.
2. **Änderung:** `read_lock()` gibt ein `Result` zurück. `main` und die anderen Aufrufer behandeln den Fehler mit einer Meldung auf stderr und einem festen Exit-Code. Die Abhängigkeiten im Manifest bleiben unberührt.
3. **Prüfung:** Dieselbe Reproduktion muss jetzt eine Meldung und den Exit-Code liefern, keinen Panic. Der normale Lauf mit der echten `Cargo.lock` muss unverändert funktionieren.
4. **Formatierung und Kompilierung:** `cargo fmt --check` und `cargo check` für das betroffene Paket, dazu `--locked`, damit das Lock unverändert bleibt.
5. **Gatter:** `pruefen.ps1` im Projektordner als Abschluss. Es prüft Formatierung, Tests und die Läufe der drei Programme.

Wichtig: Die Kompilierung allein beweist nicht, dass der Fehlerpfad richtig arbeitet. Dafür braucht es Schritt 1 und 3.

**Gelernt:** Ein Fehler, der nie reproduziert wurde, lässt sich nicht als behoben nachweisen. Die Reproduktion vor dem Fix ist der Teil, der bei kleinen Änderungen am häufigsten fehlt.

**Grenzen:** Nicht ausgeführt, kein Code geändert. Die Reihenfolge und die Exit-Codes sind Vorschläge, die vor der Umsetzung mit dem Eigentümer abzustimmen sind.
