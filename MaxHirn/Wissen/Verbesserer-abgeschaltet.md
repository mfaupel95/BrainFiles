---
name: verbesserer-abgeschaltet
description: Entscheidung vom 2026-10-20, den Verbesserer abzuschalten (Weg C); Aufgaben deaktiviert, Dateien erhalten.
metadata:
  type: project
---

# Verbesserer abgeschaltet

Am 2026-10-20 wurde entschieden, den Verbesserer abzuschalten (Weg C aus der Entscheidung der Sitzung f4e60831).

- Aufgaben `MaxHirn-Verbesserer` (Spur 1) und `MaxHirn-Verbesserer-Spur2` (Spur 2, XPERP) sind deaktiviert, nicht gelöscht.
- Code und Berichte unter `Agenten/Handel/verbesserer/` bleiben erhalten; Vermerk dort in `ABGESCHALTET.md`.
- Der offene Punkt „Universum umbauen“ aus dem Extrakt ist damit entfallen. Der frühere Plan dazu (`plan-verbesserer-universum-2026-10-20.md`) ist überholt.

**Wieder einschalten:** `schtasks /Change /TN "<Aufgabe>" /ENABLE` als Administrator.

**Plan:** `Werkstatt/Projekte/plan-verbesserer-abschalten-2026-10-20.md`.
