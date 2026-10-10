---
name: lotse-delegation
description: Route Lotse requests to the right bot, then read back.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [delegation, routing, bots, lotse]
    category: autonomous-ai-agents
---

# Lotse: Auftrag verstehen, delegieren, Antwort lesen

Lotse fuehrt Auftraege NICHT selbst aus. Er sucht das Ziel, schickt den Auftrag ab und berichtet die Antwort. Diese Skill regelt das Abschicken und das Zuruecklesen.

## When to Use

Jeder eingehende Auftrag in der lotse-Sitzung: der Nutzer beschreibt ein Ziel, Lotse sucht den passenden Bot oder das Werkzeug und schickt den Auftrag ab.

## Ablauf

1. Zielsuche ist die erste Handlung: `python Agenten/Werkzeuge/lotse-route.py --suche "<stichwort>"`. Fuer einen Ueberblick `--liste` (Bots mit Beschreibung, Werkzeuge, Skills).
2. Auftrag abschicken. Ein Bot: `env -u PYTHONHOME -u PYTHONPATH hermes -p <bot> chat -q "<auftrag>"`. Das `env -u` ist Pflicht, sonst bricht `hermes.exe` mit `Fatal Python error: init_import_site` ab. Kaltstart 30-60 s ist normal.
3. Antwort lesen und berichten. Erst dann ist der Auftrag erledigt.

## Pitfalls

- **Kurzer Prompt.** Ein langer `-q`-Text sprengt die Windows-Kommandozeile: `env: 'hermes': Argument list too long`. Halte den `-q`-Text auf wenige Saetze und verweise auf Dateien (Belegpfade, Scratch-Logs) statt deren Inhalt einzubetten.
- **Lange Bots in den Hintergrund.** Ein Bot, der echte Diagnose faehrt, braucht oft mehr als 7 min - laenger als der Foreground-Terminal-Deckel (420-600 s). Starte `hermes -p ... chat -q ... > <log> 2>&1` mit `background=true, notify=true`, dann den Log lesen/pollen. Sonst reisst der Timeout den Bot mitten in der Arbeit ab, und du siehst nur einen halben Zwischenstand.
- **Nicht selbst arbeiten.** Eigene Recherche ueber den Auftragsgegenstand - Verzeichnisse lesen, Werkzeuge des Fachgebiets starten, zaehlen, vergleichen, ein Fachergebnis formulieren - ist die Arbeit des Ziels. Auch ein Trockenlauf ist Ausfuehrung.
- **Aber die Belege des Ziels lesen.** Ein Auftrag ist erst erledigt, wenn die Antwort des Ziels vorliegt; "weitergeleitet" ohne Rueckmeldung ist keine Erledigung. Bots legen ihre Belege unter `Agenten/Hermes/profiles/<bot>/cache/scratch/` ab (Skripte, Logs, CSV) - lies die Logs dort, um dem Nutzer Verursacher + Beleg zu berichten.
- **Kein Ziel gefunden:** das naechstliegende Werkzeug oder den Skill nennen und EINE Frage stellen ("Soll ich das abschicken?"). Nennen ist Delegation, selbst starten nicht.

## References

- `references/konsolenfenster-diagnose.md` - wiederkehrender Auftrag "cmd-Popup ist zurueck": wie der sichtbare Konsolenfenster-Erzeuger gefunden wird und was man `hermes-wartung` als Brief mitgibt.
