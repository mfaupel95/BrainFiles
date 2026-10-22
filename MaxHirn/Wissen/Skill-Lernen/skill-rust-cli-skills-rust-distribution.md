---
name: skill-rust-cli-skills-rust-distribution
description: Trockenlauf des Skills rust-cli-skills:rust-distribution - beschreibt, wie die Rust-Programme des Handelsstacks ausgeliefert werden sollten (Release-Build, Windows), ohne Build und ohne Veröffentlichung.
metadata:
  type: reference
---

**Zweck:** Legt fest, welche Nutzer ein Artefakt installieren und ausführen können: Betriebssystem, Architektur, CPU-Basis, Systembibliotheken und Installationsweg. Unterscheidet Quellpaket und vorgebautes Programm. Veröffentlichen, Signieren und Hochladen bleiben beim Eigentümer.

**Wann nutzen:** Vor einer Auslieferung, bei Änderungen am Release-Profil und bei Fragen, ob ein Programm auf einem anderen System startet.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: die Auslieferung der Rust-Programme für Windows beschreiben. Kein Build, keine Veröffentlichung.

**Ergebnis:**

Bestand (lesend): Im Ordner `Agenten/Handel/nautilus-rust/` liegt das Skript `pruefen.ps1`. Es baut das Projekt reproduzierbar, führt Tests aus und lässt die drei Programme einmal laufen. Es endet mit Exit 0 nur, wenn alles sauber ist. Dazu gibt es ein `target`-Verzeichnis mit Build-Ergebnissen. Ein Release-Profil wurde nicht gelesen.

Vorgeschlagene Auslieferung:
1. **Zweck:** Die drei Programme laufen lokal auf dem Handelsrechner. Es gibt keine Veröffentlichung. Der Vertrag ist: Das Programm startet auf diesem System mit diesem Befehl.
2. **Artefakt:** Ein Release-Build aus dem gesperrten `Cargo.lock`, ohne `target-cpu=native`, damit das Programm auf anderen Rechnern mit gleichem Betriebssystem läuft.
3. **Prüfung:** `pruefen.ps1` als Gatter. Danach das gebaute Programm in einem separaten Verzeichnis starten und den Exit-Code prüfen, nicht nur das Vorhandensein der Datei.
4. **Linkage:** Prüfen, welche Laufzeitbibliotheken das Programm braucht. Mit dynamischem Linken unter Windows fehlt bei fremden Rechnern oft die passende Runtime.
5. **Ablage:** Das Artefakt bleibt im Projektordner, nicht in einem Systempfad. Entfernen ersetzt nur das eigene Verzeichnis.

Nicht geprüft: andere Zielplattformen und ältere Windows-Versionen.

**Gelernt:** Ein Build, der auf dem eigenen Rechner läuft, beweist nichts über andere Systeme. Für den Handelsstack reicht ein lokaler Start mit Exit-Code als Nachweis, solange niemand es außerhalb des Rechners einsetzt.

**Grenzen:** Kein Build ausgeführt, kein Release-Profil gelesen. Die Aussage zu Laufzeitbibliotheken ist eine Annahme, die vor einer Auslieferung zu prüfen ist.
