---
name: wochenrueckblick
description: Wochenabschluss — hält fest, was sich getan hat, räumt Posteingang und Vault auf und aktualisiert die Projektstände. Benutzen bei "Wochenrückblick", "Woche abschließen", "aufräumen", oder als Freitagsroutine.
---

# Wochenrückblick

Zweck: der Vault soll nicht veralten. Einmal pro Woche wird nachgezogen, was
sich geändert hat.

## Ablauf

**1. Was hat sich im Vault getan?**

```powershell
Get-ChildItem "Wissen","Dashboard.md" -Recurse -File |
  Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-7) } |
  Select-Object Name, LastWriteTime
```

**2. Posteingang leeren** — Skill `posteingang` ausführen, falls dort etwas liegt.

**3. [[Projekte]] aktualisieren.** Für jedes aktive Projekt: Stimmt „Stand" noch?
Stimmen die „Nächsten Schritte"? Abgeschlossenes nach „Erledigt" verschieben,
**nicht löschen** — der Kontext ist später wertvoller als die Kürze.

Beim Aktualisieren das Datum absolut schreiben (`Stand (2026-08-08):`).

**4. Verwaiste Notizen finden** — Dateien unter `Wissen/`, auf die nirgends
verlinkt wird. Entweder vom [[Dashboard]] aus verlinken oder bewusst löschen.

**5. Offene Kästchen durchgehen:**

```powershell
Select-String -Path "Wissen\*.md","Dashboard.md" -Pattern "^\s*- \[ \]"
```

Was seit Wochen offen ist, ist entweder erledigt, gestrichen oder war nie eine
echte Aufgabe. Nachfragen statt stehen lassen.

## Ausgeben

```
## Woche bis <Datum>

**Passiert**
- <2–4 Punkte>

**Aktualisiert**
- <welche Notizen ich angefasst habe>

**Braucht deine Entscheidung**
- <offene Punkte, die ich nicht allein klären kann>
```

## Regeln

- Notizen im Vault darf dieser Skill anfassen und aktualisieren — das ist sein Zweck.
- **Dateien im Archiv nicht löschen.** Aufräumen heißt hier: Notizen pflegen.
- Was gelöscht werden soll, vorher benennen und einmal bestätigen lassen.
