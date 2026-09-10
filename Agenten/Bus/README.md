# Telegram-Bus – Zentraler Meldedienst für BrainFiles

Der Bus sammelt Meldungen aller automatisierten Routinen und Fehler und leitet sie an konfigurierte Endpunkte (z. B. Telegram) weiter. Er läuft als dauerhafter Hintergrunddienst und stellt sicher, dass kein Lauf unbemerkt bleibt – selbst wenn der Bus selbst ausfällt, führen die Routinen ihre Arbeit unverändert fort (Kerngarantie: *ein toter Bus darf niemals einen Lauf abbrechen*).

## Dateien

- `bus.py` – Hauptdienst (Python, nutzt Standardbibliothek)
- `Ereignis.ps1` – PowerShell-Schnittstelle für Routinen (Melde-Start / Melde-Ende)
- `journal/` – Lokales JSON-Journal (Unterordner: `entered/`, `acknowledged/`)
- `test_*` – Unit‑ und Ende-zu-Ende‑Tests (ausführbar mit `python tests/test_*.py`)
- `test_ende_zu_ende.py` – Gesamtsystemtest (simuliert Bus, Sprecher, Journal)
- `Routinen/bus.ps1` – Registriert den Bus als geplante Aufgabe „BrainFiles-Bus“

## Nutzung

- **Manueller Start:** `python bus.py` (zeigt Hilfe und startet den Dienst im Vordergrund)
- **Als Systemdienst:** `Routinen/bus.ps1` einmal als Administrator ausführen → legt die Aufgabe „BrainFiles-Bus“ an (startet bei jedem Systemstart, restartet bei Fehler)
- **Journal einsehen:** Die Dateien unter `Agenten/Bus/journal/entered/` enthalten die ungeacknowledgten Meldungen; nach erfolgreichem Versand werden sie nach `acknowledged/` verschoben.
- **Tests laufen:** `cd Agenten/Bus && python tests/test_ende_zu_ende.py` → sollte „Ende-zu-Ende bestanden“ ausgeben.

## Wichtig

Ein toter Bus darf niemals einen Lauf abbrechen: Alle Routinen rufen `Melde-Start` zu Beginn und `Melde-Ende` vor jedem `exit`. Fällt der Bus aus, schreiben sie weiterhin ins lokale Journal und führen ihre eigentliche Logik aus – nur die Weiterleitung fehlt. Sobald der Bus wieder läuft, werden die nachgetragenen Einträge versendet.

**Abruf und Steuerung sind Teilprojekt 2, Deutung ist Teilprojekt 3** – hier liegt ausschließlich der zuverlässige Transport von Meldungen.