# Design: Atlas-Tab in der Repos-Zentrale (Teilprojekt C)

- Datum: 2026-09-19
- Status: zur Freigabe
- Basis: Brainstorming 19.09.2026, genehmigt A1 → B1 → C1
- Abhaengt von: Teilprojekt A (Atlas fuer die Repos)
- Abgrenzung: C (GUI-Tab). A (Atlas anlegen) und B (Auskunft) sind
  eigene Zyklen.

## Zweck

Die Repos-Zentrale (`Agenten/Werkzeuge/repos-zentrale/`) ist das eine
Fenster fuer alle Repos unter `Werkstatt/`. Sie zeigt heute Start,
Bot, Doku — aber nicht, ob ein Repo eine ProjectAtlas-Karte hat und wie
gross sie ist. C ergaenzt einen **Atlas-Tab**: je Repo Index-Status und
DB-Groesse, plus ein Suchfeld „welche Datei fuer X“, dessen Treffer die
Datei im Explorer oeffnen. Damit beantwortet die Zentrale die
Zustaendigkeitsfrage direkt im Fenster, ohne dass man die CLI kennt.

## Ist-Zustand (gemessen 19.09.2026)

- `fenster.py` baut eine einzelne `ttk.Treeview` (kein Notebook), fuenf
  Aktionen je Zeile, Suchfeld oben, „Aktualisieren“-Knopf. Anzeigelogik
  als reine Funktionen (pruefbar ohne Fenster), `Fenster`-Klasse baut nur
  zusammen. Worker-Threads fuer Start (`_starten_im_hintergrund`),
  Ergebnisse ueber `root.after(0, ...)`.
- `scan.py` liest die Platte, `manifest.py` das Manifest, `aktionen.py`
  die Startbefehle. Tests unter `tests/` (kein Test startet einen echten
  Prozess; Fenstertest baut die Oberflaeche unsichtbar auf).
- ProjectAtlas-Karten liegen je Repo unter `<repo>/.projectatlas/`
  (`projectatlas.db` + `-wal`/`-shm`). Status = Datei vorhanden + Groesse;
  `scan.status` steht im Init-JSON unter `Agenten/Werkzeuge/projectatlas/logs/`.

## Entscheidungen

1. **Ein neuer Tab im bestehenden Fenster, kein zweites Fenster.** Die
   Zentrale wird auf `ttk.Notebook` umgestellt: Tab 1 = bestehende
   Repo-Liste (unveraendert), Tab 2 = Atlas. Das Muster aus
   `gui-kontrollzentrum.md` (Worker-Thread + Queue, Widgets nie aus
   Fremd-Thread) gilt nur fuer den neuen Tab.
2. **Atlas-Status je Repo aus der Platte lesen** (`.projectatlas/
   projectatlas.db` vorhanden + Groesse), nicht aus den Init-Logs — die
   Platte ist die Wahrheit, die Logs sind nur der Beleg des letzten Laufs.
   Repos ohne Karte erscheinen als „kein Atlas“.
3. **Suchfeld „welche Datei fuer X“** fragt die CLI
   (`projectatlas --format json files "<begriff>"`) im Worker-Thread,
   Ergebnisliste im Tab; Doppelklick oeffnet die Datei im Explorer
   (bestehendes `aktionen.doku_oeffnen`-Muster). Nur Repos mit Karte
   sind durchsuchbar; ohne Karte deaktiviert.
4. **Kein Schreiben in fremde Repos** — der Tab liest nur (Status,
   Groesse, Suche). Kein `init` aus dem Fenster (das macht A/`indexieren.sh`).
5. **Anzeigelogik als reine Funktionen** wie im Bestand: Atlas-Status
   und Suchtreffer sind ohne Fenster pruefbar; die `Fenster`-Klasse baut
   nur zusammen.

## Umfang C

**In** (Abnahmekriterien):

1. `ttk.Notebook` mit zwei Tabs; Tab 1 (Repo-Liste) funktional
   unveraendert, alle bestehenden Tests gruen.
2. Atlas-Tab: je Repo Zeile mit Name, Atlas-Status (ja/nein), DB-Groesse
   (MB), letzter Init (aus Logzeit). Sortierung: kartiert zuerst.
3. Suchfeld + Ergebnisliste; Doppelklick oeffnet die Datei. Nur Repos
   mit Karte durchsuchbar.
4. Tests: `tests/test_atlas_tab.py` — Status-Logik (Karte da/fehlt,
   Groesse), Suchtreffer-Aufbereitung, Tab-Aufbau unsichtbar. Kein Test
   startet einen echten Prozess oder ruft die CLI.
5. Doku: `repos-zentrale/README.md` um den Atlas-Tab ergaenzen.

**Nicht in C** (bewusst):

- Kein `init`/Rescan aus dem Fenster (gehoert zu A).
- Kein Schreiben in Repos, keine Zweck-Kuration im Fenster.
- Keine Anbindung an die Haus-Spuren (das ist B).
- Kein Watcher-Status (nur Standard-Atlas omnitrade wird beobachtet).

## Massnahmen gegen gemessene Fallen

| Falle | Massnahme |
|---|---|
| CLI-Aufruf blockiert GUI | Suche im Worker-Thread, Ergebnis ueber Queue/`root.after`. |
| Karte gross (codex 1,9 GB) | Groesse in MB anzeigen, nicht laden; nur `stat` auf die DB. |
| `-wal`/`-shm` aendern sich | Status prueft nur die Haupt-DB (`projectatlas.db`), nicht die Neben-Dateien. |
| Repo ohne Karte | Zeile „kein Atlas“, Suche deaktiviert — kein Fehler. |
| Fenstertest | Tab baut unsichtbar auf (`withdraw`), wie im Bestand. |

## Nachweis (am Ende von C)

```
cd Agenten/Werkzeuge/repos-zentrale
.venv\Scripts\python.exe -m unittest discover -s tests -v   # alle gruen
.venv\Scripts\python.exe repos_zentrale.py --pruefen        # laeuft, Atlas-Status je Repo
```

## Betroffene Dateien (Aenderung)

- `fenster.py` — Notebook + Atlas-Tab.
- Neu: `atlas_tab.py` (Tab-Logik, reine Funktionen + Widget-Aufbau),
  `tests/test_atlas_tab.py`.
- `README.md` — Atlas-Tab dokumentieren.
- Neu: diese Datei unter `docs/design/2026-09-19-atlas-tab-design.md`.