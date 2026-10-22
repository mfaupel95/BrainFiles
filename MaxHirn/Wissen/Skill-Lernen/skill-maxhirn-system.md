---
name: skill-maxhirn-system
description: Trockenlauf des Skills MaxHirn:system - beschreibt gezielte Windows-Abfragen (Stromverlust, Plattenfehler, Dienstabstürze), die den Lern-Ablauf beeinträchtigen könnten; ohne Abfragen auszuführen.
metadata:
  type: reference
---

**Zweck:** Gezielte Diagnose statt Rundumscan. Prüft Neustarts und Stromverlust, Plattenfehler, Hardwarefehler und Dienstabstürze. Vor jeder Änderung wird bestätigt, und Eingriffe kommen als umkehrbare Skripte.

**Wann nutzen:** Bei Abstürzen, Hängern, nicht erkannten Geräten oder abstürzenden Diensten.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, welche Befunde den Lern-Ablauf beeinträchtigen könnten und welche Abfragen dafür gezielt wären. Keine Abfrage ausgeführt, nichts verändert.

**Ergebnis:**

Befunde, die den Lern-Ablauf treffen könnten:
1. **Stromverlust oder Neustart während eines Laufs.** Ereignis 41 ohne vorheriges 1001 ist das Leitsignal. Ein Neustart mitten im Lauf lässt eine halbe Notiz oder einen unvollständigen Fortschritt zurück.
2. **Plattenfehler auf dem Laufwerk des Vaults.** Ereignisse 153 und 140 zeigen E/A-Probleme. Eine Notiz, die auf einer fehlerhaften Stelle liegt, kann beim Lesen fehlschlagen oder still verfälscht werden.
3. **Dienstabstürze.** Ein Dienst, der ständig abstürzt, kann das Systemprotokoll so überschreiben, dass Vorfälle nicht mehr nachweisbar sind. Vorher prüfen, wie weit das Protokoll zurückreicht.
4. **Speicher.** Der Ablauf läuft als Sitzung. Speicherdruck durch andere Prozesse kann Läufe abbrechen. Das überschneidet sich mit dem Befund der Docker-Kaskade.

Gezielte Abfragen (laut Skill, nicht ausgeführt):
- Neustarts: Ereignisse 41 und 6008 der letzten 30 Tage
- Plattenfehler: Ereignisse 153, 140 aus den Quellen `disk`, `Ntfs`, `volmgr` der letzten 7 Tage
- Hardwarefehler: Quelle `WHEA-Logger` der letzten 30 Tage
- Dienstabstürze: Ereignisse 7023, 7031, 7034 der letzten 7 Tage
- Reichweite des Protokolls zuerst prüfen: die älteste Protokollzeile

Der Skill verlangt Ansage vor jeder Änderung. Für den Lern-Ablauf ist das nicht nötig, weil er nichts am System ändert.

**Gelernt:** Ein Lauf, der bei einem Absturz halb fertig bleibt, braucht eine Prüfung der Notizen danach, nicht nur des Systems. Die Prüfung der Reichweite des Protokolls ist vor jeder Schlussfolgerung zu machen, sonst liest man eine Lücke als Beweis.

**Grenzen:** Nur beschrieben. Keine Abfrage ausgeführt, keine Ereignisse gelesen, keine Aussage über den tatsächlichen Zustand der Platten oder Dienste.
