# Design-System der Desktop-Fenster (Stand 30.09.2026)

Gegenstand: `Agenten/Handel/handelszentrale.py`,
`Agenten/Werkzeuge/repos-zentrale/repos_zentrale.py` (+ `fenster.py`) und
`leitstelle.py`. **`leitstelle.py` existiert weder im Arbeitsbaum noch in einem
Git-Zweig noch im Dateisystem dieser Session** - vermutlich unversioniert auf
Max' PC. Es ist hier nicht bewertet; Abschnitt "Offen" beachten.

Technik aller Fenster: Tkinter/ttk, Theme `clam`, dunkel. Palette ist
Catppuccin Mocha. Die Palette steht **heute doppelt** (plus `omniquant/gui.py`
als Vorbild) - jede Abweichung ist ein Wartungsfehler.

## 1. Farb-Tokens

| Token | Hex | Rolle |
|---|---|---|
| `bg` | `#1e1e2e` | Fensterfläche, Frames, Labels |
| `blatt` | `#181825` | Datenfläche: Treeview, Eingabefelder, Chart |
| `gitter` | `#313244` | Trennlinien, Tabellenkopf, Ausgewähltes (repos-zentrale) |
| `text` | `#cdd6f4` | Fließtext |
| `matt` | `#a6adc8` | Nebeninfo, Achsen, Fußzeile |
| `akzent` | `#89b4fa` | Tabellenkopf-Schrift, Gruppentitel, aktiver Tab |
| `gruen` | `#a6e3a1` | Erfolg / Gewinn / long |
| `rot` | `#f38ba8` | Fehler / Verlust / short |
| `gelb` | `#f9e2af` | Warnung / Aufmerksamkeit |
| `zellgruen` | `#1b4d3e` | Zellhintergrund positiv (nur handelszentrale) |
| `zellrot` | `#5c1f2b` | Zellhintergrund negativ (nur handelszentrale) |
| *(roh)* `#45475a` | | Auswahl/aktiver Tab in handelszentrale - **kein Token** |

Regel: Farbe trägt Bedeutung (grün/rot/gelb = Zustand), nie Dekoration.
Zustand nie **nur** über Farbe - immer zusätzlich Text (`STARTBAR`, `FEHLT`,
Vorzeichen bei Zahlen).

## 2. Typografie

- Schrift: `Consolas` (Festbreite, damit Zahlenspalten fluchten).
- **Eine** Basisgröße `SCHRIFT_GROESSE = 11`; alles andere relativ über
  `schrift(rel, fett)`. Grund: Befund "zu klein/unleserlich" (30.09.2026) -
  10 pt war zu klein.

| Stufe | rel | Verwendung |
|---|---|---|
| `TITEL` | +3 | Fensterkopf |
| Basis | 0 | Tabellen, Labels, Buttons, Eingaben |
| `KLEIN` | -1 | Konsole, Fußzeile |
| `TINY` | -2 | Chart-Beschriftung |

Tabellenkopf: Basis + fett, Farbe `akzent`. Zeilenhöhe **`max(18, Basis*2)`** -
sonst werden Buchstaben angeschnitten.

## 3. Pflicht-Verhalten

1. **DPI:** `dpi_bewusst()` (`SetProcessDpiAwareness(1)`) vor dem ersten
   `Tk()`, sonst wird das Bild auf 150-%-Monitoren gestreckt und unscharf.
   Fehlertolerant (`except Exception`).
2. **Fenster im Bild:** Start-Position prüfen; liegt das Fenster nach
   Monitor-Abzug außerhalb (Rand 60 px), auf `+80+60` setzen
   (`_buero_im_bild` in handelszentrale).
3. **Schrift zentral setzen:** `st.configure(".", ...)`; Einzel-Widgets nur
   für Abweichungen (Größe/fett).
4. **Anzeigelogik rein:** Deutung/Rechnung in fensterlosen Funktionen, damit
   testbar (`test_fensterzeilen.py`, `test_handelszentrale_*`).
5. **Rein lesend, wo zugesagt:** handelszentrale schreibt nichts (Test
   `test_handelszentrale_rein_lesend.py`).

## 4. Komponenten

| Komponente | Ist-Stand |
|---|---|
| Tabelle | `ttk.Treeview`, `blatt`-Grund, Kopf `gitter`/`akzent`, Auswahl `gitter` (repos) bzw. `#45475a` (handel) |
| Tabs | `TNotebook`, Tab `gitter`, aktiv `akzent` auf `#45475a` |
| Gruppen | Titel in Versalien (`STARTBAR`, `EINRICHTEN`, `NEU`, `NUR DOKU`, `FEHLT`) plus einzeilige Erklärung |
| Chart | Canvas auf `blatt`, Gitter `gitter`, Achsen `matt`, `TINY` |
| Eingaben | `ttk.Entry/Combobox`, Schrift Basis |

## 5. Abweichungen (Ist -> Soll)

| # | Befund | Soll |
|---|---|---|
| 1 | `FARBEN`, `schrift()`, `SCHRIFT_*` in beiden Dateien kopiert (repos-zentrale-Kommentar bestätigt: "dieselbe Schrift wie handelszentrale") | Ein Modul `fenster_design.py` (Tokens, `schrift`, `dpi_bewusst`, `stil_anwenden(style)`); beide importieren |
| 2 | `#313244` und `#45475a` in handelszentrale roh statt Token (Zeilen ~819-826) | Token `gitter` bzw. neues Token `auswahl = #45475a` |
| 3 | `dpi_bewusst()` nur in repos-zentrale | In handelszentrale prüfen, ob sie es ebenfalls braucht |
| 4 | `SCHRIFT_GROESSE` als `global` mutiert | Bei Auslagerung als Zustand der Design-Instanz, nicht Modul-Global |
| 5 | Schrift-Umschalter (8-16) nur in handelszentrale | Entscheiden, ob repos-zentrale ihn erhält |

## 6. Umsetzungsweg (nicht ausgeführt)

Risikoarm: erst `fenster_design.py` mit **identischen** Werten anlegen, dann
je Datei den Block ersetzen (gezielter Ersatz, Diff ansehen - Versionierte
Textdateien nie neu schreiben, LF/CRLF), danach Tests:
`Agenten/Handel/tests/`, `Agenten/Werkzeuge/repos-zentrale/tests/`. Ablage
wegen der gemeinsamen Nutzung unter `Agenten/Werkzeuge/`; der Import-Pfad
(beide Verzeichnisse liegen nicht im selben Paket) ist die eigentliche
Designfrage und vor dem Umbau zu klären.

## Offen

- `leitstelle.py`: Datei bereitstellen, dann Abgleich der Tokens in Abschnitt 1-3.
- `omniquant/gui.py` (Namensgeber der Palette) liegt ebenfalls nicht im Repo.
