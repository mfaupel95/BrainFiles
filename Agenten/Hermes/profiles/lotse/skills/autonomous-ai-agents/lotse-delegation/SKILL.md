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
2. Auftrag abschicken. Ein Bot: `env -u PYTHONHOME -u PYTHONPATH hermes -p <bot> chat -q "<auftrag>" > <log> 2>&1` mit `background=true, notify=true` - nie im Vordergrund (siehe Pitfall). Das `env -u` ist Pflicht, sonst bricht `hermes.exe` mit `Fatal Python error: init_import_site` ab. Kaltstart 30-60 s ist normal.
3. Antwort lesen und berichten. Erst dann ist der Auftrag erledigt.

## Pitfalls

- **Kurzer Prompt.** Ein langer `-q`-Text sprengt die Windows-Kommandozeile: `env: 'hermes': Argument list too long`. Halte den `-q`-Text auf wenige Saetze und verweise auf Dateien (Belegpfade, Scratch-Logs) statt deren Inhalt einzubetten.
- **Bot-Aufrufe gehoeren IMMER in den Hintergrund - ab dem ersten Versuch.** Auch `lotse-route.py --an` blockiert wie der direkte `hermes -p ... chat -q ...`-Aufruf; ein Foreground-Timeout (schon 60 s) reisst den Bot mitten in der Arbeit ab, verschwendet den Kaltstart und liefert keinen Zwischenstand. Nie erst "schnell im Vordergrund testen" - sofort `... > <log> 2>&1` mit `background=true, notify=true` starten und den Log lesen/pollen. Echte Diagnose braucht oft mehr als 7 min, laenger als der Foreground-Deckel (420-600 s).
- **Nicht selbst arbeiten.** Eigene Recherche ueber den Auftragsgegenstand - Verzeichnisse lesen, Werkzeuge des Fachgebiets starten, zaehlen, vergleichen, ein Fachergebnis formulieren - ist die Arbeit des Ziels. Auch ein Trockenlauf ist Ausfuehrung.
- **Scope-Mismatch beim Bot.** Repo-Bots suchen standardmaessig nur in ihrem eigenen Repo (z. B. `Werkstatt/kraken-cli`). Nennt der Nutzer einen Pfad aus einem anderen Baum (z. B. `Agenten/Handel/nautilus`), verweise explizit auf diesen Pfad im Prompt - sonst findet der Bot die Begriffe nicht und meldet irrlicherweise "nicht vorhanden". Formulierung: "nicht <bot-name> gemeint; Ursache in <pfad> (Python). Suche dort nach <begriffen>."
- **Generische Bot-Beschreibung.** `--liste` zeigt bei Repo-Bots oft nur "betreut Werkstatt/<repo>" - welches Repo wirklich gemeint ist, steht in `Agenten/Hermes/profiles/<bot>/config.yaml` unter `terminal.cwd`. Vor dem Abschicken nachsehen (das ist Zielsuche, kein Selbst-Arbeiten), sonst landet der Auftrag beim Bot des falschen Repos - dieselbe Beschreibung tragen mehrere Profile.
- **Aber die Belege des Ziels lesen.** Ein Auftrag ist erst erledigt, wenn die Antwort des Ziels vorliegt; "weitergeleitet" ohne Rueckmeldung ist keine Erledigung. Bots legen ihre Belege unter `Agenten/Hermes/profiles/<bot>/cache/scratch/` ab (Skripte, Logs, CSV) - lies die Logs dort, um dem Nutzer Verursacher + Beleg zu berichten.
- **Kein Ziel gefunden:** das naechstliegende Werkzeug oder den Skill nennen und EINE Frage stellen ("Soll ich das abschicken?"). Nennen ist Delegation, selbst starten nicht.

## References

- `references/konsolenfenster-diagnose.md` - wiederkehrender Auftrag "cmd-Popup ist zurueck": wie der sichtbare Konsolenfenster-Erzeuger gefunden wird und was man `hermes-wartung` als Brief mitgibt.
- `references/moon-dev-bots.md` - Moon-Dev-Profile -> Start-Repo (config.yaml cwd), Repos mit "moon" im Namen, Ort der moon-dev-gui (moongui.py).
