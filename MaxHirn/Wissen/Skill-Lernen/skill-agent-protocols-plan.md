---
name: skill-agent-protocols-plan
description: Trockenlauf des Skills agent-protocols:plan - skizziert eine Konsistenzprüfung für die Statuswerte im Skill-Lernen-Fortschritt und prüft die aktuelle Datei nur lesend.
metadata:
  type: reference
---

**Zweck:** Zerlegt eine Aufgabe in Schritte mit Abhängigkeiten, Abnahmekriterien und Kontrollpunkten, bevor Code geschrieben wird. Im Plan-Modus wird nichts geändert.

**Wann nutzen:** Vor einer Änderung mit mehreren Schritten, bei unklarer Reihenfolge.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Plan für eine Konsistenzprüfung der Statuswerte in `fortschritt.md` skizzieren. Lesend geprüft, nichts geändert, nichts gespeichert.

**Ergebnis:**

Plan:
1. Wertliste festlegen: `gelaufen`, `trockenlauf`, `nicht-ausführbar`, `nicht-ausführbar (2x)`, `übersprungen`.
2. Jede Datenzeile muss genau vier Spalten haben: Datum, Skill, Status, Notiz oder Grund.
3. Das Datum hat das Format `JJJJ-MM-TT`.
4. Jeder Skill-Name kommt nur einmal vor, außer bei bewusster Dublette.
5. Abbruch: Ein unbekannter Statuswert oder eine falsche Spaltenzahl wird gemeldet, nicht stillschweigend korrigiert.

Prüfbefehl (nur lesend):
`awk -F'|' 'NR>3 && NF>0 {print NR": cells="NF-2" status=["$4"]"}' fortschritt.md`

Lesender Testlauf auf die aktuelle Datei: 23 Datenzeilen, 22 mit vier Spalten und gültigem Status. Eine Zeile (memory-search) hat fünf Spalten, weil der Grund im Statusfeld steht. Das ist der einzige Fehler im Bestand.

**Gelernt:**
- Der Plan-Skill verlangt, Pläne in `tasks/plan.md` und `tasks/todo.md` zu speichern. Die Trockenlauf-Vorgabe hatte Vorrang, deshalb wurde nichts gespeichert.
- Eine Prüfung mit einem einzeiligen Befehl reicht für diese Datei. Ein eigener Testaufbau wäre übertrieben.

**Grenzen:** Der Befehl wurde gegen die aktuelle Datei gelesen, aber nicht als Skript in den Vault gelegt. Die Zeile mit fünf Spalten ist noch nicht korrigiert.
