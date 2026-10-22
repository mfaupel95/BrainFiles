---
name: skill-maxhirn-posteingang
description: Trockenlauf des Skills MaxHirn:posteingang - zählt die Dateien im Posteingang des Archivs (288 Dateien) und beschreibt, was der Sortierlauf täte; ohne Dateien zu öffnen oder zu bewegen.
metadata:
  type: reference
---

**Zweck:** Bringt neue Dateien aus dem Posteingang an ihren Platz im Archiv. Sortiert über ein Skript, Rest von Hand. Sensible Dateien werden nie automatisch verschoben.

**Wann nutzen:** Wenn im Posteingang Dateien liegen oder Max um Aufräumen bittet.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: den Posteingang zählen und beschreiben, was der Skill damit täte. Keine Datei geöffnet oder verschoben, kein Testlauf des Sortierskripts.

**Ergebnis:**

Bestand (lesend): Im Posteingang des Archivs liegen **288 Dateien**. Der Pfad ist `O:\Archiv\Posteingang`, nicht der Ordner unter `MaxHirn/Archiv`. Die Umgebungsvariable `ARCHIV_ROOT` zeigt auf `O:\Archiv`, und der Skill nutzt sie.

Die ersten Einträge sind ein Ordner `AKAI MPK MINI Mk2` mit einem Firmware-Update. Darin liegen ein macOS-Programmpaket mit Unterdateien, eine Binärdatei `.bin` und Dokumente. Der Inhalt eines Programmpakets ist kein Dokument, das sortiert werden sollte. Das Skript würde es als Ganzes behandeln, wenn der Ordner einer Regel entspricht. Ob das der Fall ist, ist nicht geprüft.

Was der Skill täte:
1. Zählen, leer prüfen. Hier nicht leer.
2. Bei mehr als einigen Dutzend Dateien ein Testlauf des Sortierskripts. 288 gilt als mehr als einige Dutzend, also Testlauf vorgesehen.
3. Sortieren, Ausgabe kurz halten.
4. Rest von Hand, Dateien einzeln prüfen, nicht nach Namen raten.
5. Index aktualisieren.

Besonderheit des Bestands: Ein Firmware-Paket für ein Musikgerät gehört eher in die Kategorie Musik oder Geräte, nicht Dokumente. Die Zuordnung ist eine Entscheidung für den Lauf, nicht für diesen Trockenlauf.

**Gelernt:** Die Zahl 288 zeigt, dass der Posteingang zu groß für einen Blindlauf ist. Ein Testlauf ist hier Pflicht, damit das Skript nicht unbemerkt Programmpakete auseinanderreißt.

**Grenzen:** Gezählt, nicht gelesen. Die Herkunft der Dateien und ob sie schon im Archiv stehen, ist nicht geprüft. Der Testlauf des Sortierskripts wurde nicht ausgeführt.
