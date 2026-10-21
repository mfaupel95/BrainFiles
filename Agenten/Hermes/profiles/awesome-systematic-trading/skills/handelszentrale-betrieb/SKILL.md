---
description: Use when Handelszentrale starten oder GUI beheben.
name: handelszentrale-betrieb
---

# Handelszentrale-Betrieb

## Was sie ist

`Agenten/Handel/handelszentrale.py` ist die LESE-GUI ueber alle Spuren (Spurliste aus dauerlauf.SPUREN, Positionen, Kerzenchart, Konsole, Kopfzeile mit Dauerlauf-PID und Zyklusalter). Sie schreibt NICHTS - `dauerlauf.py` bleibt der einzige Schreiber. Dieser Vertrag ist per AST-Test erzwungen (`tests/test_handelszentrale_rein_lesend.py`) und in `tests/test_handelszentrale_bindung.py` abgesichert (50 Tests). Wer eine GUI-Erweiterung baut, die Dateien schreibt, bricht den Vertrag.

## Starten und pruefen

1. Start ueber den Wrapper (Autostart-Aufgabe MaxHirn-Handelszentrale, Anmeldung +2 Min): `Routinen/handelszentrale.ps1` - er startet nur, wenn kein Fenster mit Titel `Handelszentrale*` laeuft, sonst meldet er 'Fenster offen' mit PID und Exit 0. Log: `Routinen/logs/handelszentrale-letzter-lauf.log`.
2. Kopfaufruf ohne Fenster: aus dem Handel-Ordner `scanner/.venv/Scripts/python.exe handelszentrale.py --pruefen` - druckt die Ansicht und prueft gegen die echten Dateien.
3. Neustart nur so: Fenster per PID beenden, das den Titel traegt (nicht alle pythonw-Prozesse), dann den Wrapper erneut. Der Wrapper beendet nichts selbst.
4. Fensterposition/Fensterzustand NIE per Screenshot beurteilen - die GUI kann korrekt laufen und trotzdem unsichtbar sein (siehe unten). Autoritativ ist die Geometrie-Abfrage (GetWindowRect, Positiv bei `-32000` = minimiert), fuer gerenderten Inhalt erst nach Sichtbarkeits-Nachweis ein Screenshot.

## Unsichtbares Fenster: Ursache und Fix

Das Fenster kann mit Negativ-Koordinaten (z.B. -1009,-205) starten, wenn es von einem frueheren Monitor-Layout uebernommen wird (abgezogener Zweitmonitor). Der Prozess laeuft, der Titel existiert, aber kein Screenshot zeigt es - als GUI-Fehler gemeldet, ist es in Wirklichkeit alte persistierte Fenstergeometrie. Fix im Programm: `_buero_im_bild()` klemmt die Startposition beim Anlegen gegen den sichtbaren Bildschirm (gegen `winfo_screenwidth/height`, Rueckfall auf Default-Position). Manuell sofort: Fenster per Fenster-Manipulation (resize mit `window_loc`) zurueckholen und die neue Position per GetWindowRect verifizieren.

## Schrift-Option (seit Schrift-Umbau)

- Alle Fonts laufen ueber `schrift(rel=0, fett=False)` mit Basis `SCHRIFT_GROESSE` (Vorgabe 11) - Titel/Konsole/Chart relativ dazu (Konstanten `TITEL`, `TINY`). Kein hart kodiertes `("Consolas", N)` mehr; ein Test (SchriftTest) schlaegt bei hartkodierten Fonts im Quelltext an.
- Option in der Kopfzeile: Combobox `Schrift:` 8-16 pt, wirkt sofort ohne Neustart (setzt `SCHRIFT_GROESSE` und wendet alle registrierten Widget-Fonts neu an).
- Startoption `--schrift N` setzt die gleiche Basis beim Anlauf.
- Neue Widgets mit Font IMMER ueber `schrift()` bauen und in `_registriere_schrift` aufnehmen, sonst folgen sie der Option nicht.

## Python-Falle (argparse + global)

`global SCHRIFT_GROESSE` muss VOR jeder Verwendung des Namens in der Funktion stehen - auch vor Argument-Defaults wie `ap.add_argument(..., default=SCHRIFT_GROESSE)`. Steht das `global` erst nach dem argparse-Block, wirft Python 'name used prior to global declaration' beim Import. Regel: `global`-Deklarationen an den Funktionsanfang, bevor irgendein Ausdruck den Namen liest.

## Wrapper-Falle

Der Wrapper prueft den Fenster-Titel, nicht den Prozess: eine GUI, die minimiert oder off-screen ist, gilt als 'Fenster offen' und verhindert den Neustart. Nach Aenderungen also erst das alte Fenster wirklich beenden, sonst laeuft die alte Version weiter und die Aenderung scheint wirkungslos.
