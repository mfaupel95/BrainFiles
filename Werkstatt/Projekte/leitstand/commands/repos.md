---
description: Listet die Fremd-Repos unter Werkstatt/Repos mit Git-Status, rein lesend
---

Antworte auf Deutsch.

Lies die Ordner unter `Werkstatt/Repos/`. Fuer jeden Klon zeige nur: Name, aktueller Branch, ob uncommittete Aenderungen liegen (`git -C <pfad> status --short`), und das letzte Commit (`git -C <pfad> log -1 --format=%cd %s --date=short`).

Kein `git fetch`, `pull`, `push`, `stash` oder `checkout`. Nur lesen. Ausgabe als kompakte Tabelle.
