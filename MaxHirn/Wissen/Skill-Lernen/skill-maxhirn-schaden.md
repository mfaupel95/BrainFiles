---
name: skill-maxhirn-schaden
description: Trockenlauf des Skills MaxHirn:schaden - prüft Dateien auf zerstörten Inhalt (0xFF-Füllbytes, leere Dateien); hier auf die Lernnotizen angewendet, keine Auffälligkeit gefunden.
metadata:
  type: reference
---

**Zweck:** Findet Dateien, deren Namen geschrieben wurden, deren Inhalt aber durch einen Defekt mit 0xFF gefüllt ist. Rettet, wenn es intakte Zwillinge gibt. Zerstörte Dateien werden nie gelöscht.

**Wann nutzen:** Bei Dateien, die sich nicht öffnen lassen, leer wirken oder nach einem Plattenproblem auffallen.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: die Lernnotizen auf zerstörten Inhalt prüfen. Keine Datei verändert, nichts zurückgespielt.

**Ergebnis:**

Prüfung (lesend) über alle Lernnotizen unter `MaxHirn/Wissen/Skill-Lernen/`:
- **Leere Dateien:** 0
- **Dateien mit 0xFF-Bytes:** 0
- **Dateien, die nicht als UTF-8 lesbar sind:** 0

Alle Notizen sind danach unauffällig. Die Prüfung ist eine Stichprobe über den Inhalt, kein Signaturtest wie im Skill, weil die Notizen Textdateien sind.

Der Skill ist für Archivdateien mit Dateisignatur gebaut (Fotos, Videos, PDFs). Für Markdown-Notizen ist die Signaturprüfung nicht nötig. Die Füllbyte-Prüfung trifft trotzdem zu, und sie war hier unauffällig.

Wichtig: Das Ergebnis gilt nur für die Lernnotizen. Die Frage, ob der Index oder der Fortschritt beschädigt ist, ist damit nicht beantwortet, auch wenn die Stichprobe dort ebenfalls passte (nicht gesondert geprüft).

**Gelernt:** Für Textdateien ist eine Prüfung auf 0xFF und Nullbytes der schnellste Test. Eine Notiz mit zerstörtem Inhalt würde beim Lesen als Zeichenmüll auffallen, bevor die Prüfung nötig wäre.

**Grenzen:** Nur die Lernnotizen geprüft. Die Dateien `INDEX.md` und `fortschritt.md` sind außerhalb des Skill-Bereichs und wurden nicht untersucht.
