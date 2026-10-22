---
name: skill-maxhirn-vergleich
description: Trockenlauf des Skills MaxHirn:vergleich - Ordner vergleichen und zusammenführen, Duplikate erkennen; hier auf die Dubletten im Lern-Ablauf angewendet, ohne Vergleich auszuführen.
metadata:
  type: reference
---

**Zweck:** Vergleicht Ordner über mehrere Laufwerke, findet Duplikate und führt verstreute Bestände zusammen. Löschen erst nach Verifikation, für persönliche Inhalte gilt die Löschsperre.

**Wann nutzen:** Bei doppelten Dateien, bei „was liegt nur auf G:“ und vor dem Aufräumen eines Laufwerks.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, welche Dubletten der Lern-Ablauf erzeugt und wie man sie erkennt. Kein Vergleich ausgeführt, nichts gelöscht.

**Ergebnis:**

Zählung (lesend, schnell):
- **Fortschritt** `Werkstatt/Projekte/skill-lernen/fortschritt.md`: 175 Datenzeilen, davon 6 Skill-Namen doppelt.
- **Index** `MaxHirn/Wissen/INDEX.md`: 4 Notiz-IDs doppelt.
- **Lernnotizen** `MaxHirn/Wissen/Skill-Lernen/`: 143 Dateien. Die Anzahl liegt über den Fortschrittszeilen mit Notizpfad, weil mehrere Sitzungen Notizen angelegt haben.

Was die Dubletten bedeuten:
- Eine Skill-Doppelung im Fortschritt entsteht, wenn zwei Sitzungen denselben Skill laufen ließen. Das ist ein Protokollfehler, kein Datenverlust, weil beide Zeilen auf dieselbe Notiz zeigen oder die zweite die erste überschreibt.
- Eine Index-Doppelung ist gefährlicher: Zwei Zeilen mit derselben ID verweisen auf dieselbe Notiz, und der Vault-Prüfer meldet sie als fehlerhaft.
- Dateien mit gleichem Inhalt in unterschiedlichen Namen lassen sich nicht mit Name und Größe erkennen. Bei Textdateien ist der Hash die verlässliche Prüfung.

Zu erkennen mit dem Skill: Der Vergleich ist für Binärdaten gebaut. Für Textnotizen würde ein Hash-Vergleich die Frage beantworten, ob zwei Notizen identisch sind. Eine Doppelung im Protokoll braucht dagegen eine Zeilenprüfung, keinen Dateivergleich.

Keine Löschung nötig: Die Doppelungen im Fortschritt sind Protokollzeilen, die Index-Doppelungen müssten bereinigt werden, die Notizen bleiben.

**Gelernt:** Ein Protokoll und ein Verzeichnis haben verschiedene Doppelungen. Der Vergleichs-Skill ist für Verzeichnisse gebaut und deckt das Protokoll nicht ab.

**Grenzen:** Gezählt, nicht verglichen. Die sechs doppelten Skill-Namen und die vier doppelten IDs sind nicht einzeln geprüft, und die Ursache ist nur vermutet.
