# Verbesserer abgeschaltet

Stand: 2026-10-20. Entscheidung „Weg C“: Verbesserer abschalten.

Automatische Starts sind deaktiviert, die Dateien bleiben erhalten:

- Windows-Aufgabe `MaxHirn-Verbesserer` (Spur 1): deaktiviert
- Windows-Aufgabe `MaxHirn-Verbesserer-Spur2` (Spur 2, XPERP): deaktiviert

Wieder einschalten: `schtasks /Change /TN "<Aufgabe>" /ENABLE` (als Administrator).

Plan: `Werkstatt/Projekte/plan-verbesserer-abschalten-2026-10-20.md`.
