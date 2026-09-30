---
name: codebasis-bestand
description: "Use when Codebestand und Fremdcode im Baum gemessen werden."
version: 0.1.0
author: Hermes Agent
platforms: [windows]
license: MIT
metadata:
  hermes:
    tags: [bestand, messung, fremdcode, struktur, werkzeuge]
    related_skills: [trugschluesse, repos-zentrale, fundus-zugriff, arbeitsbaum-git-hygiene]
---

# Bestand messen: wie gross ist unser Code — und was davon ist unserer

Fragen wie "wie gross ist unser Handelssystem", "welche .py gehoeren noch rein",
"stoert das Duplikat" lassen sich nicht schaetzen. Dieser Skill ist der Weg zu
einer Zahl, die man weitergeben kann — und die Grenze, ab der eine Zahl ehrlich
wird: **Fremd-Material liegt mitten im eigenen Baum.**

## When to Use

- "wie gross ist X", "wie viele Dateien/Zeilen hat Y", "was davon ist unserer"
- ein fremdes Projekt oder ein Duplikat im eigenen Baum soll eingeordnet werden
- eine Bestandszahl soll in eine Antwort, ein Design oder eine Aufgabe
- Verdacht auf Doppelungen oder liegengebliebenes Material

Skript dazu: `scripts/bestand.py` (rein lesend, nur Standardbibliothek).

**Don't use for:** Zustand belegen (`trugschluesse`), ein Projekt starten oder
auflisten (`repos-zentrale`), fremde Skill-Sammlungen durchsuchen
(`fundus-zugriff`).

## Die zwei Zahlen (immer beide)

**Fremd** ist Material, das wir nicht pflegen: ein Klon, ein Import, ein
Fremdprojekt. Kriterium ist NICHT Sprache, Groesse oder Qualitaet, sondern die
Frage *aendern wir es, oder benutzen wir es?*

Jede Bestandsantwort nennt deshalb zwei Zahlen: **mit** und **ohne** Fremde —
und die Antwort ist die ohne. Ein fremdes Projekt in einer eigenen Wurzel kann
den Grossteil der Zeilen ausmachen; die rohe Wurzelzahl sagt dann nichts ueber
die eigene Arbeit.

## Procedure

1. **Wurzeln benennen** (relativ zur BrainFiles-Wurzel, keine absoluten Pfade):
   `Agenten/Handel`, `Agenten/Bus`, `Agenten/Werkzeuge`, `Agenten/Routinen`,
   `Agenten/MCP-Server`, `Agenten/Hermes/scripts`. Fremde Baeume ausdruecklich
   ausschliessen (`--ohne`).
2. **Messen** mit `scripts/bestand.py` — Umfang je Bereich, groesste Einzeldateien,
   byte-gleiche Doppelungen, Merker im Code, Testanteil:

   ```
   Agenten/Werkzeuge/repos-zentrale/.venv/Scripts/python.exe \
     Agenten/Hermes/skills/brainfiles/codebasis-bestand/scripts/bestand.py \
     --ohne Agenten/Handel/OpenAlice,Agenten/MCP-Server
   ```

3. **Beide Zahlen in die Antwort** ("ohne Fremde: n Dateien / m Zeilen · mit: N/M").
4. **Herkunft nachsehen, bevor etwas "fremd" heisst** — siehe Fallen. Ein
   falsch einsortierter eigener Ordner ist der teurere Fehler.
5. **Die Grenze an EINER Stelle fuehren.** Wird sie oefter gebraucht, gehoert sie
   in eine Liste mit einem Leser (JSON + Modul, Muster `MCP-Manifest.json` +
   `mcp-sync-check.ps1`) — nicht in den Kopf jeder Auswertung. Die Anzeige
   (Markdown-Tabelle) wird gegen dieselbe Quelle geprueft, sonst entsteht eine
   zweite Wahrheit.

## Fallen

- **`rglob` und `find ... -exec cat` laufen in die venvs.** Beide brauchen
  Minuten bis in den Timeout. Richtig ist `os.walk` mit geschnittenen Ordnern:
  `.venv`, `venv`, `__pycache__`, `node_modules`, `.git`, `.archive`, `cache`,
  `site-packages`, `tools`, `.previous-python*`, `dist`, `build`, `target`.
- **Eine frische EIGENE Spur sieht fremd aus.** Keine Tests, ungetrackt (`??`),
  unbekannter Name. Herkunft klaeren: Zeitstempel, `git log -1 -- <pfad>`,
  `git status --porcelain <pfad>`, Eintrag im Verbraucher (`dauerlauf.SPUREN`),
  Basis des Codes (Import im Kopf). Erst danach "fremd" sagen.
- **Fremde Klone enthalten riesige Einzeldateien und tausende Kopien.** Eine
  Datei mit sechsstelliger Zeilenzahl oder 38 byte-gleiche `candidate.py` sind
  Merkmale eines fremden Baums, kein Befund ueber unseren Code. Doppelungen
  deshalb erst nach dem Ausschluss der Fremdbaeume lesen.
- **Merker (TODO/FIXME/HACK) in fremden Baeumen zaehlen nicht als unsere Schuld.**
  Erst ohne Fremde zaehlen, dann urteilen.
- **Zahlen sind Momentaufnahmen.** Wurzel, Ausschluesse und Datum mitnennen; eine
  Zahl ohne ihre Grenzen ist nicht nachpruefbar.
- **Ein Duplikat ist erst dann ein Problem, wenn es gelesen wird.** Ein
  eingefrorener Spiegel, den niemand liest und der keine Geheimnisse traegt,
  stoert nur als zweite Wahrheit im Suchweg — dann gehoert er BENANNT (Rolle +
  Herkunft), nicht geloescht.
- **Neu hinzugekommenes Fremd-Material MUSS eingetragen werden, sonst zaehlt es
  als eigener Code.** Ein frisch installiertes Fremdpaket (z. B. `node_modules`
  eines npm-Pakets im eigenen Werkzeugordner) oder ein neuer Klon gehoert in
  `Agenten/FREMD-Liste.json` UND in die Tabelle `Agenten/FREMD.md` (ein Test
  vergleicht die Pfadmengen beider — nur eine Seite zu aendern wird rot).
  Danach `python Agenten/Werkzeuge/fremd.py --pruefen` (muss "gesund" sagen) und
  die Tests `python -m unittest discover -s Agenten/Werkzeuge/tests -t
  Agenten/Werkzeuge/tests`. Die Regeln der Liste: Pfad relativ zur Wurzel mit
  `/`, ohne `..` und Laufwerksbuchstaben, kein Eintrag in einem anderen Eintrag,
  nie eine eigene Wurzel, und der Ordner muss auf der Platte liegen.
  Die Grenze gilt NUR fuer den fremden Teil: der eigene Aufrufer, das README und
  der Test neben dem Paket bleiben eigener Code.

## Verifikation

- Die Summe der Bereiche muss die Gesamtzahl ergeben — eine Zahl, die nicht
  aufgeht, ist ein Filterfehler.
- Eine Stichprobe mit einem zweiten Weg nachzaehlen (`wc -l` auf einen kleinen
  Ordner, `git ls-files | wc -l` fuer den versionierten Teil).
- Vor einer Aussage ueber Duplikate: **zwei** gleiche Dateien zeigen und die
  Herkunft nennen. Eine Gruppe ohne Herkunft ist ein Verdacht.

## Verwandtes

- `trugschluesse` — belegt statt vermutet; dort steht die Regel, warum eine
  Herkunftsaussage einen Zeugen braucht.
- `repos-zentrale` — zeigt fremd/eigen als Rolle im Startfenster.
- `fundus-zugriff` — fremde Skill-Sammlungen finden und einordnen.
