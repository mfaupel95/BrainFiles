---
name: skill-rust-cli-skills-rust-io
description: Trockenlauf des Skills rust-cli-skills:rust-io - beschreibt, wie Ein- und Ausgabe im Rust-Teil des Handelsstacks geprüft werden sollte (stdout, stderr, Dateien, Pufferung, Fehler bei Pipes).
metadata:
  type: reference
---

**Zweck:** Verfolgt Bytes von der Quelle bis zum Verbraucher, einschließlich dessen, was zwischen den Schritten gepuffert bleiben muss. Unterscheidet kurze Lesevorgänge von EOF und Puffergrenzen von Satzgrenzen. Fehler werden nicht still in Erfolg verwandelt.

**Wann nutzen:** Beim Ändern der Ausgabe, beim Lesen wachsender Eingaben und bei Pipes, deren Gegenstelle früh schließt.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, wie Ein- und Ausgabe im Rust-Teil geprüft werden sollte. Nichts geändert, nichts ausgeführt.

**Ergebnis:**

Bestand (lesend): Die Ausgabe läuft in allen drei Programmen über `println!` und `eprintln!`. Gefunden wurden:
- `quant-alpha/src/main.rs:93` und `:105`: `println!`-Blöcke für Ergebnisse.
- `quant-planes/src/main.rs:76`: `println!` für den Erfolgsfall und `:80` `eprintln!` für Verstöße.
- `quant-strategy/src/main.rs:82` bis `:116`: viele `println!`-Zeilen, teils mit Befundtexten.

Die Programme schreiben also auf stdout, ohne einen gepufferten Schreiber. `println!` leert den Puffer bei Zeilenende und ist für kurze Ausgaben unkritisch. Bei einer frühen Schließung der Pipe, etwa durch `| head`, kann `println!` mit einem Panic abbrechen, weil Rust `BrokenPipe` nicht still abfängt. Ob das hier vorkommt, ist nicht geprüft.

Vorgeschlagene Prüfung:
1. **Normaler Lauf:** Ausgabe auf stdout, Diagnose auf stderr, Exit-Code 0 bei Erfolg.
2. **Umgeleitet in eine Datei:** Die Ausgabe ist vollständig, der Zeilenumbruch am Ende fehlt nicht.
3. **Früh geschlossene Pipe:** `quant-strategy | head -n 1` als Test. Erwartet ist entweder ein sauberer Abbruch oder ein definierter Fehlercode. Ein Panic zählt als Fehler.
4. **Fehler beim Schreiben** einer Ergebnisdatei muss zu einem Exit-Code ungleich 0 führen.

Wenn Ausgabe in Dateien wächst, erst dann `BufWriter` mit einem expliziten Abschluss. Ein Drop ohne Flush verschluckt Fehler.

Keine Durchsatzmessung, solange Durchsatz nicht Teil der Aussage ist.

**Gelernt:** Bei einem Programm, das Skripte aufrufen, ist der Umgang mit früh geschlossenen Pipes Teil des Vertrags, auch wenn der Normalfall funktioniert.

**Grenzen:** Nur die Stellen der Ausgabe per Textsuche gefunden. Eingabe wurde nicht gelesen, weil dort keine Treffer für `read_line` oder `lines()` vorkamen. Die Pipe-Prüfung ist nicht ausgeführt.
