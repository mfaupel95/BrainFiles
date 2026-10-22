---
name: skill-maxhirn-wochenrueckblick
description: Trockenlauf des Skills MaxHirn:wochenrueckblick — wöchentliche Vault-Pflege in 5 Schritten; Vault nicht veralten lassen; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Vault wöchentlich nachziehen — Projekte, verwaiste Notizen, offene Punkte.

**Lauf:** 2026-10-22, trockenlauf.

**5 Schritte:**
1. **Geänderte Dateien:** `Get-ChildItem "Wissen","Dashboard.md" -Recurse | Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-7) }`
2. **Posteingang leeren:** Skill `posteingang`
3. **Projekte aktualisieren:** Stand, nächste Schritte, abgeschlossenes nach „Erledigt" — **nicht löschen** (Datum absolut: `Stand (2026-08-08):`)
4. **Verwaiste Notizen finden:** Dateien in `Wissen/` ohne Verlinkung → Dashboard-Link oder bewusst löschen
5. **Offene Kästchen:** `Select-String -Path "Wissen\*.md" -Pattern "^\s*- \[ \]"` → seit Wochen offen = erledigt/gestrichen/nie echt

**Ausgabeformat:**
```
## Woche bis <Datum>
**Passiert** — 2–4 Punkte
**Aktualisiert** — welche Notizen
**Braucht deine Entscheidung** — offene Punkte
```

**Regel:** Dateien im Archiv nie löschen. Was gelöscht werden soll: erst benennen, dann bestätigen lassen.
