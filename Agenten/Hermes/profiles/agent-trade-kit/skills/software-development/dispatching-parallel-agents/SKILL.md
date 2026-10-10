---
name: dispatching-parallel-agents
description: "Use when 2+ independent tasks: dispatch parallel subagents."
---

# Dispatching Parallel Agents

## Ueberblick
Statt mehrere unabhaengige Probleme nacheinander zu untersuchen (Testdateien, Subsysteme, Bugs mit verschiedenen Ursachen), delegiert man jedes an einen eigenen Subagenten mit isoliertem Kontext. Das haelt den eigenen Kontext sauber und laesst Ermittlungen gleichzeitig laufen.

**Kernprinzip:** Ein Subagent pro unabhaengiger Problemdomaene, parallel.

## Wann einsetzen
- 3+ Testdateien scheitern an verschiedenen Ursachen
- Mehrere Subsysteme unabhaengig kaputt
- Jedes Problem ohne Kontext der anderen verstehbar
- Kein geteilter Zustand zwischen den Ermittlungen

**Nicht einsetzen, wenn:**
- Verwandte Fehler (ein Fix koennte mehrere beheben) - erst zusammen untersuchen
- Volles Systemverstaendnis noetig
- Subagenten wuerden sich stoeren (gleiche Dateien, gleiche Ressourcen)
- Exploratives Debugging, wenn noch unklar ist, was kaputt ist

## Ablauf
1. **Unabhaengige Domaenen identifizieren.** Nach "was ist kaputt" gruppieren. Wenn ein Fix in einer Domaene die andere beruehrt, sind sie nicht unabhaengig.
2. **Fokussierte Agent-Briefe erstellen.** Jeder Subagent bekommt:
   - Spezifischen Scope: eine Testdatei / ein Subsystem
   - Klares Ziel: "mach diese Tests gruen"
   - Constraints: "anderen Code nicht anfassen"
   - Erwartete Ausgabe: Zusammenfassung von Befund und Fix
3. **Parallel dispatchen.** Mehrere delegate_task-Aufrufe in derselben Antwort laufen parallel; ein Aufruf pro Antwort = sequenziell. Briefe beim Dispatchen vollstaendig formulieren.
4. **Review und Integration.** Wenn die Subagenten zurueckkommen: jede Zusammenfassung lesen, Konflikte pruefen (haben zwei dieselbe Datei geaendert?), volle Testsuite laufen, alle Aenderungen integrieren und stichprobenartig auf systematische Fehler der Subagenten pruefen.

## Agent-Prompt-Struktur
Gute Briefe sind:
1. **Fokussiert** - eine klare Problemdomaene
2. **Selbsttragend** - aller Kontext im Brief (Fehlermeldungen, Testnamen, Dateipfade); der Subagent erbt nichts aus deiner Session
3. **Konkret in der Ausgabe** - "Return: Zusammenfassung von Befund und Fix"

Kurzvorlage:
```
Fix die 3 scheiternden Tests in <pfad>/<datei>.test.ts:
<Test 1: Erwartung>
<Test 2: Erwartung>
Das sind Timing-/Race-Probleme. Aufgabe:
1. Testdatei lesen und verstehen, was jeder Test prueft
2. Ursache ermitteln (Timing oder echter Bug?)
3. Fix - keine bloesse Timeout-Erhoehung; Ereignis-Warten statt fester Pausen
Constraints: Produktionscode nicht anfassen.
Return: Zusammenfassung von Befund und Fix.
```

## Haeufige Fehler
- Zu breit ("Fix alle Tests") -> Subagent verliert sich. Besser: eine Datei, ein Scope.
- Ohne Kontext ("Fix den Race-Condition-Bug") -> Fehlermeldungen und Testnamen einbetten.
- Ohne Constraints -> Subagent refaktorisiert alles. "Nur Tests anfassen" / "Produktionscode unveraendert".
- Vage Ausgabe ("Fix es") -> "Return: Ursache und was geaendert wurde".

## Verifikation nach Rueckkehr
1. Jede Zusammenfassung lesen und verstehen
2. Konflikte pruefen: haben Subagenten denselben Code editiert?
3. Volle Testsuite laufen, damit alle Fixes zusammen funktionieren
4. Stichproben: Begehen die Subagenten denselben systematischen Fehler?

Adaptiert aus obra/superpowers (Fork mfaupel95/superpowers), 16.09.2026.
