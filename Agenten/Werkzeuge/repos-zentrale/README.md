# Zentrale — Repos, Werkstatt und Handel

Ein Fenster fuer **alles, was auf diesem Rechner liegt und startet**: die 46
geklonten Repos unter `Werkstatt/Repos`, die eigenen Projekte und Ablagen unter
`Werkstatt/` und die Handelsspuren samt Werkzeugen unter `Agenten/Handel`.
Ordner oeffnen, Terminal, starten, Bot-Chat, Doku lesen — plus die Angabe, was
fehlt, bevor man es vergebens versucht.

Entstanden am 18.09.2026 als „Repos-Zentrale" fuer `Werkstatt/Repos`; am
30.09.2026 auf drei **Bereiche** erweitert. Spezifikation der ersten Fassung:
`docs/design/2026-09-18-repos-zentrale-design.md`, Plan:
`docs/plans/2026-09-18-repos-zentrale.md`.

## Starten

    cd Agenten\Werkzeuge\repos-zentrale
    .venv\Scripts\pythonw.exe repos_zentrale.py                    # Fenster
    .venv\Scripts\python.exe   repos_zentrale.py --pruefen         # auflisten, kein Fenster
    .venv\Scripts\python.exe   repos_zentrale.py --pruefen --bereich HANDEL
    .venv\Scripts\python.exe   repos_zentrale.py --handel         # Stand aller Spuren
    .venv\Scripts\python.exe   repos_zentrale.py --handel --nur scharf
    .venv\Scripts\python.exe   repos_zentrale.py --test scanner   # --vorschau einer Spur

Die venv ist nur fuer dieses Werkzeug (Python 3.13, Standardbibliothek). Sie
haengt an keiner Repo-venv.

**Scharf geschaltet wird nur im Fenster.** `--handel` und `--test` LESEN nur;
einen Kommandozeilen-Schalter zum Scharfschalten gibt es absichtlich nicht
(Handelsregeln Punkt 3 verlangt dafuer ein Fenster mit Bestaetigungsfeld).
`--pruefbericht` misst alle Projekte (venv, node_modules, Pflichtpfad, Git,
Bot, Port) und schreibt den Bericht nach `logs/` — derselbe Lauf wie der Knopf
„Alles pruefen" im Fenster.

## Die drei Bereiche

| Bereich | Wurzel | Regel, was eine Zeile bekommt |
|---|---|---|
| **REPOS** | `Werkstatt/Repos` | nur Klone mit `.git` |
| **WERKSTATT** | `Werkstatt` + `Werkstatt/Projekte` | jeder Ordner (auch Datenfelder und Ablagen) |
| **HANDEL** | `Agenten/Handel` | jeder Ordner, jede Werkzeugdatei der Wurzel mit eigenem Einstieg **und** die ausdruecklich genannten Werkzeuge in Unterordnern |

Stand 05.10.2026: **222 Zeilen** — 47 REPOS, 22 WERKSTATT, 9 PROJEKTE,
144 HANDEL, davon **135 mit belegtem Startbefehl** (vorher 119; die 16 neuen
tragen einen Lauf vom 05.10.2026 in `logs/`). Ein Startbefehl kommt erst ins
Manifest, wenn er einmal echt gelaufen ist — `fuellen.py --belege` erzeugt den
Beleg, der Pflicht ist.

Die Wurzeln stehen in `quellen.py` (Pfade relativ zur BrainFiles-Wurzel, keine
absoluten Pfade). Gesperrt sind in **jeder** Wurzel Interpreter, Caches und
Editorzustand (`.venv`, `node_modules`, `__pycache__`, `.git`, `cache`, ...) -
als Namensliste, nicht als Muster; sonst traefe eine Sperre ein echtes Projekt.

## Was in Unterordnern liegt: `WERKZEUG_ZUSATZ`

Eine Wurzel wird nur an der **Oberflaeche** durchsucht (plus `Werkstatt/Projekte`
eine Ebene tiefer). Werkzeuge, die neben einer Spur liegen - `okx_bot_waechter/
analyse.py`, `scanner/boersenstops.py`, `kraken/abgleich.py`, die fuenf
`auswertung.py` - waeren damit unsichtbar. Sie stehen deshalb **namentlich** in
`quellen.WERKZEUG_ZUSATZ` (Pfad mit `/`, ohne `..`).

Warum eine Liste und keine Suche: in `Agenten/Handel` liegen unter `OpenAlice/`
**130 Dateien** eines fremden Projekts. Eine rekursive Suche wuerde das Fenster
damit fluten; eine Namensliste ist eine Entscheidung, ein Muster ist eine
Hoffnung.

Was bewusst **nicht** als Zeile erscheint:

- **`OpenAlice/`** - fremdes Projekt mit eigenem Baum (eigene `AGENTS.md` sagt:
  nur lesen, wenn die Aufgabe ausdruecklich OpenAlice betrifft).
- **die 30 `handeln.py` der Spuren** - sie werden vom Dauerlauf gefahren
  (`dauerlauf.py`, Dict `SPUREN`: Ordner, Skript, Interpreter). Was dort steht,
  ist NICHT ueberall `handeln.py`: die meisten Spuren tragen gar kein
  `skript`-Feld und laufen ueber die Vorgabe, aber `nautilus_kraken_futures`
  teilt sich den Ordner `nautilus_kraken` mit dem Spot-Arm und faehrt dort
  `handeln_futures.py` mit dem `nautilus/.venv`-Interpreter. Diese Liste im
  Manifest nachzubauen waere eine **dritte Wahrheit** - dafuer gibt es
  `spuren_stand.py` und `sperrgruende.py`, die jede Spur selbst fragen.

## Strategien und Stufen

Drei Dinge heissen hier "Strategie", und alle drei sind Zeilen im Fenster:

| Art | Wo | Rolle |
|---|---|---|
| **Spuren** | `Agenten/Handel/<spur>/` | `Spur` |
| **Freqtrade-Strategien** | `freqtrade/user_data/strategies/*.py` | `Strategie` |
| **Backtests** | `orb/backtest.py`, `gitter/backtest_gitter.py`, ... | `Backtest` |

Die sechs Freqtrade-Strategien sind **Klassen, keine Programme** - freqtrade
laedt sie, der Bot-Aufsatz steht in `freqtrade/user_data/bots/`. Darum haben sie
keinen Startbefehl, sondern einen Hinweis.

Die **drei Risikostufen** (Basis, mittel, hoch) sind kein eigener Eintrag: es
sind dieselben Spuren mit groesseren Betraegen in eigenen Dateien
(`zustand.mittel.json`, `handelsjournal.hoch.csv`, ...). Sichtbar werden sie
ueber die Befehlsliste der drei Leser:

| Zeile | Befehl | Zeigt |
|---|---|---|
| `spuren_stand.py` | `--nur scharf` | je Spur `haupt/.mittel/.hoch` (Buch) und das Alter |
| `auswertung_alle.py` | `--risiko mittel` \| `hoch` | Kennzahlen der Stufe |
| `spiegelstand.py` | `--risiko mittel` \| `hoch` | Bedingung 4 je Stufe (byte-genau gegen `Q:`) |

Ein eigener Eintrag je Stufe waere irrefuehrend: es gibt nicht drei Laeufe mit
verschiedenen Strategien, sondern einen Betrieb mit drei Groessen.

## Was das Fenster zeigt

Ein Baum mit **drei Ebenen**:

    BEREICH (REPOS · WERKSTATT · HANDEL)
      GRUPPE (STARTBAR · EINRICHTEN · NEU · NUR DOKU · FEHLT)
        Projektzeile

| Gruppe | Bedeutung |
|---|---|
| **STARTBAR** | Startbefehl ist belegt *und* die Abhaengigkeiten liegen auf der Platte |
| **EINRICHTEN** | Einstieg vorhanden, es fehlt noch etwas (venv, `node_modules`, Binary, Startbefehl) |
| **NEU** | Ordner auf der Platte, aber kein Eintrag im Manifest |
| **NUR DOKU** | kein Programm, nur Text oder Daten — „starten" heisst hier oeffnen |
| **FEHLT** | Manifest-Eintrag ohne Ordner (z. B. nach dem Loeschen eines Klons) |

Spalten: **Projekt · Art · Rolle · Bot · letzter Start · Handel · Hinweis**.

- **Rolle** ordnet ein, was das ist (Spur, Werkzeug, Modell, MCP-Server, Ablage).
- **Bot** zeigt das Hermes-Profil und `(fehlt)`, wenn es keines gibt.
- **letzter Start** kommt aus dem neuesten Log in `logs/`.
- **Handel** steht nur bei Handels-Spuren: `scharf` (Orderweg vorhanden UND
  `handel_erlaubt=true`) oder `Papier`.
- **Hinweis** nennt erst den Grund (was fehlt), sonst die Notiz.

Die **Kopfzeile** traegt Titel, Summenzeile und die Skalierung; darunter liegt
die **Filterzeile** (Suchfeld, Bereich, Gruppe, „Filter aus") und eine Reihe
**Filterchips**. Unter dem Baum stehen zwei **Karten**: links „Was dieses
Projekt kann", rechts der **Handelsteil**.

Oben: Bereichsauswahl, Suchfeld (trifft Name, Rolle, Bot, Notiz, Pfad)
und „Aktualisieren". Der Baum faerbt nur nach Zustand — `FEHLT` rot, `NEU`
und Zeilen mit Grund gelb — und sagt den Zustand zusaetzlich als Text.

Tasten: **F5** aktualisieren, **Strg+F** Suchfeld, **Eingabe** starten,
**Doppelklick** startet (wenn belegt), sonst oeffnet es den Ordner.

Fuenf Aktionen je Zeile — was nicht geht, ist deaktiviert, nicht kaputt:

1. **Ordner** — Explorer; bei einer Werkzeugdatei wird die Datei markiert
2. **Terminal** — `wt.exe`, Arbeitsverzeichnis = Projekt
3. **Starten** — der Befehl aus dem Manifest; Ausgabe geht in `logs/`
4. **Bot** — `hermes -p <bot> chat`, Arbeitsverzeichnis = Projekt
5. **Doku** — die README des Projekts

Dazu **Log oeffnen** (der Startbeleg) und **Wiki** (die Hausdoku zu diesem
Werkzeug).

## Filter

Zwei Arten, beide UND-verknuepft:

- **Suchfeld** — trifft Ordnername, Rolle, Bot, Notiz, Art und Pfad.
- **Bereich** und **Gruppe** — als Auswahl.
- **Filterchips** — `auffaellig`, `startbar`, `mit Start`, `mit Bot`, `fremd`,
  `nur Handel`, `nur Spuren`, `scharf`. Wer zwei Chips anmacht, bekommt die
  **Schnittmenge** (nicht die Vereinigung): „nur Handel" + „auffaellig" zeigt
  die auffaelligen Zeilen im Handelsbereich.

„Filter aus" setzt Suchtext, Bereich, Gruppe und alle Chips zurueck.

## Skalierung

Drei Regler in der Kopfzeile, alle gemerkt (siehe `einstellungen.json`):

| Regler | Wirkung | Tasten |
|---|---|---|
| **Schrift** | 8–16 pt; skaliert Tabelle, Knoepfe, Karten und Zeilenhoehe gemeinsam | `Strg +` / `Strg -` / `Strg 0`, `Strg-Mausrad` |
| **Dichte** | `kompakt` / `normal` / `gross` — aendert NUR den Zeilenabstand, nicht die Schrift | — |
| **Fenster** | `klein` / `mittel` / `gross` / `bildschirm` — Vorgaben, auf den Bildschirm begrenzt | — |

Die gemerkten Werte liegen in `Agenten/Werkzeuge/repos-zentrale/einstellungen.json`
(**Laufzeitstand, nicht versioniert** — er aendert sich bei jedem Chip-Klick).

## Runde Ecken

Tk/ttk zeichnet Rechtecke. `rund.py` zeichnet die Ecken deshalb selbst:
`ecken_punkte()` rechnet den Umriss, `RunderKnopf` und `Karte` zeichnen damit
Knoepfe und Flaechen. Die Karten liegen in einem `tk.PanedWindow` (Teilung
ziehbar). Das **Fenster selbst** bekommt seine runden Ecken vom System:
`rund.fenster_ecken()` setzt `DWMWA_WINDOW_CORNER_PREFERENCE` (Windows 11);
auf Windows 10 bleibt es eckig, und das ist kein Fehler.

## Handelsteil: Testen und Scharfschalten

Sichtbar, sobald eine **Handels-Spur** gewaehlt ist (Ordner aus
`dauerlauf.SPUREN`). Die Karte zeigt:

- **Kopfzeile** — Spur, Orderweg (`haus`/`fremd`/`keiner`), `handel_erlaubt`,
  `freigabe.erfuellt`, Zeitfenster, Buch, Zyklusalter, `AUTO_FREIGABE`.
- **Checkliste** — dieselben Punkte wie `Wiki/Handel/Gates-und-Freigabe.md`.
  Was die Spur selbst prueft (Guthaben, Schluesselrechte), steht ausdruecklich
  als `?` darin — eine geratene Aussage waere schlimmer als eine fehlende.
- **Vorschau testen (F9)** — faehrt `<spur>/handeln.py --vorschau` **mit**
  `MAXHIRN_ROUTINE=1` (so ruft der Dauerlauf seine Spuren; ohne die Variable
  haelt sich die Spur fuer eine Sitzung am Bildschirm und wartet auf eine
  Freigabe, die niemand geben kann). Rein lesend, Ausgabe in die Karte und nach
  `logs/<spur>-vorschau-*.log`. Frist 240 s, der Lauf blockiert das Fenster nicht.
- **Stand neu lesen** — liest Buch, Fenster und Schalter der Spuren neu
  (`spuren_stand.py`, rein lesend, im Hintergrund).
- **Scharf schalten … (F10)** — oeffnet ein eigenes Fenster (siehe unten).
- **Entschaerfen** — `handel_erlaubt` auf `false`, nach Rueckfrage.

### Das Scharfschalten-Fenster

Es ordert nicht. Es schaltet einen Schalter — und zwar nach der Hausregel
(Handelsregeln Punkt 3: *von Hand, in einem Fenster, das die Werte zeigt, sie
aendern laesst und ein Feld zum Bestaetigen hat*):

1. **Checkliste** mit dem Stand (rein lesend).
2. **Herzschlag** auf 180 — Pflichtfeld, wenn der Wert darunter steht: wer live
   geht, muss einen PC-Ausfall ueberleben.
3. **`freigabe.erfuellt`** — nur auf ausdrueckliches Ankreuzen. Ohne den Haken
   passiert nichts, auch mit `handel_erlaubt=true`.
4. **Bestaetigung** — kann die Spur danach wirklich ordern (Orderweg vorhanden
   UND Haken gesetzt), muss der **Spurname getippt** werden. Sonst genuegt ein
   Haken „Ich habe die Werte gelesen".
5. **Geschrieben** wird gezielt im Text (nie per `json.dump`): Sicherung
   `wachen.json.bak-JJJJMMTT` (nur die erste des Tages), Wertersatz, datierte
   Notiz `_scharfgeschaltet`, dann Gegenprobe per `json.loads` UND Vergleich
   jedes Wertes. Stimmt etwas nicht, wird NICHTS geschrieben. Belegzeile in
   `logs/handel-schalter-JJJJMMTT.log`.

## Der Bereich „Was dieses Projekt kann"

Unter der Tabelle steht fuer das **ausgewaehlte** Projekt:

- **links ein Textblock**: Bereich und Rolle, wozu es da ist (`notiz`), wo es
  liegt, ob eine venv da ist, was noch fehlt („Zu tun: …") und — wenn hinterlegt
  — der Ablauf in Worten (`anleitung`). Fehlt er, sagt der Text das ausdruecklich,
  statt etwas zu erfinden.
- **rechts die Befehlsliste**: je Zeile `Was | Befehl | Hinweis`. Die ersten
  Eintraege sind fuer jedes Projekt dieselben (Starten, Terminal, Ordner, Doku,
  Bot), danach kommen die Befehle aus dem Manifest (`befehle`).

Drei Knoepfe, alle auf die gewaehlte Zeile bezogen:

| Knopf | Was passiert |
|---|---|
| **Befehl ausfuehren** | oeffnet ein sichtbares Windows-Terminal im Projektordner und fuehrt den Befehl aus (`cmd /k`, damit die Ausgabe stehen bleibt). Zeilen wie „Ordner im Explorer" loesen den gleichnamigen Knopf aus. |
| **Befehl kopieren** | legt die Befehlszeile in die Zwischenablage — zum Einfuegen in ein eigenes Terminal. So lernt man den Weg von Hand. |
| **Bot damit beauftragen** | gibt den Befehl als Auftrag an den Bot (`hermes -p <bot> chat -q …`): er fuehrt aus und erklaert in drei Saetzen, was herauskam. Nur aktiv, wenn das Profil existiert. |

## Das Manifest

`repos-zentrale.json` ist die **einzige** Stelle, an der ein Startbefehl steht.
Felder je Projekt:

    {
      "ordner": "moon-dev-ai-agents",     // Anzeigename
      "wurzel": "repos",                   // "repos" (Vorgabe), "werkstatt", "projekte", "handel"
      "pfad": "moon-dev-ai-agents",        // Pfad INNERHALB der Wurzel (Vorgabe: ordner)
      "rolle": "Werkzeug",                 // Klartext-Rolle fuer die Spalte
      "art": "python",                     // nur Anzeige, wird sonst aus der Platte gelesen
      "gruppe": "doku",                    // optional: erzwingt NUR DOKU
      "start": [".venv\\Scripts\\pythonw.exe", "moongui.py"],
      "einrichten": ["npm", "install"],    // was fehlt, wenn Abhaengigkeiten fehlen
      "bauen": ["cargo", "build", "--release"],
      "venv_pflicht": true,                // Start nur, wenn eine venv da ist
      "node_modules_pflicht": true,        // Start nur, wenn node_modules da ist
      "pfad_pflicht": "target\\release\\x.exe",   // Datei, ohne die der Start nicht geht
      "bot": "moon-dev-agents",            // Hermes-Profil (klein geschrieben)
      "notiz": "Herzstueck",
      "anleitung": "Erst X, dann Y.",       // Klartext-Ablauf fuer den Detailbereich
      "befehle": [                          // anklickbare Befehle, je {was, cmd, hinweis}
        {"was": "Pruefstand zeigen", "cmd": [".venv\\Scripts\\python.exe", "pruefstand.py"],
         "hinweis": "zwei Sekunden"}
      ],
      "warnungen": ["Bot-Profil 'x' wurde am 19.09.2026 entfernt"]
    }

Der **Schluessel eines Eintrags ist das Paar (wurzel, pfad)** — so darf
`OmniRoute` einmal unter `Werkstatt/` und einmal unter `Werkstatt/Projekte/`
stehen, ohne dass die beiden sich verdecken.

Regeln, die der Code durchsetzt:

- **`start` und `einrichten` sind argv-Listen**, keine Shell-Zeichenketten
  (kein `shell=True`, keine Zeichenketten-Injektion). Ein relativer
  Programmname wird gegen den Projektordner aufgeloest — Windows wuerde ihn sonst
  gegen das Arbeitsverzeichnis des Aufrufers suchen und nicht finden.
- Ein **Befehl kommt erst ins Manifest, wenn er einmal echt gelaufen ist**
  (Log in `logs/`). Nennt der Test `tests/test_manifest_gegenprobe.py` einen
  Startbefehl ohne Logbeleg, ist die Regel verletzt.
- **Kein Eintrag ohne Ordner** heisst nicht „unsichtbar": was auf der Platte
  liegt und keinen Eintrag hat, erscheint als **NEU**.
- Die **Platte schlaegt das Manifest** beim Zustand: venv, `node_modules`,
  README und Pflichtdateien werden live geprueft.
- Ein **Bot ohne Profil** ist ein Knopf ins Leere: der Test
  `test_jedes_bot_profil_des_manifests_existiert` laesst keinen stehen.

## Fuellen: die Wurzeln aufnehmen

`fuellen.py` traegt ein, was auf der Platte liegt und noch fehlt — Notiz und Art
kommen aus dem Projekt **selbst** (README-Ueberschrift, sonst Modul-Docstring),
Rolle und Startbefehle aus der kuratierten Tabelle im Skript.

    .venv\Scripts\python.exe fuellen.py                  # Trockenlauf
    .venv\Scripts\python.exe fuellen.py --anwenden       # schreiben (Sicherung .bak-JJJJMMTT)
    .venv\Scripts\python.exe fuellen.py --belege         # jeden Start ohne Beleg einmal ausfuehren
    .venv\Scripts\python.exe fuellen.py --auffrischen --anwenden   # nur fehlende Felder nachtragen

Drei Regeln dabei:

1. **Vorhandene Eintraege bleiben unangetastet.** Handarbeit wird nie
   ueberschrieben; Nachzutragen ist Sache von `--auffrischen` (und auch dort
   nur, was leer ist).
2. **Kein geratener Startbefehl.** Der Hilfe-Start (`<datei> --help`) gibt es
   nur fuer Dateien in `HILFE_VERIFIZIERT` — also fuer die, deren Aufruf einmal
   wirklich gelaufen ist. Eine neue Datei erscheint als Zeile **ohne**
   Startbefehl; das ist der ehrliche Zustand.
3. **Kein Start hinterlaesst einen Prozess.** `--belege` wartet auf jeden Lauf
   (Frist 90 s) und schreibt den Exit-Code in dasselbe Log.

## Ein neues Projekt aufnehmen

1. Ordner/Klon anlegen — er erscheint sofort als **NEU** (ohne Eintrag).
2. `fuellen.py --anwenden` ergaenzen, was fehlt (Notiz, Art, Rolle).
3. Den Startbefehl **einmal echt laufen lassen**, dann als `start` eintragen;
   `fuellen.py --belege` legt den Logbeleg dazu.
4. Pruefen: `.venv\Scripts\python.exe -m unittest discover -s tests` und
   `python repos_zentrale.py --pruefen`.

## Messen statt schauen

`messprobe.py` baut das Fenster, misst jede Spaltenbreite gegen die Schrift und
sagt, ob ein Text abgeschnitten wird:

    .venv\Scripts\python.exe messprobe.py

Hintergrund: mit `dpi_bewusst()` setzt Tk Schrift in Geraetepixeln — auf einem
125-%-Monitor braucht ein 41-Zeichen-Hinweis 410 px. Deshalb sind die
Spaltenbreiten kein fester Wert, sondern werden aus der **wirklichen**
Baumbreite und dem DPI-Faktor gerechnet (`fenster.spaltenbreiten`): erst
schrumpfen die Nebenspalten, dann die Projektspalte, zuletzt der Hinweis; die
Restbreite bekommt der Hinweis. `stretch=False` auf jeder Spalte ist Pflicht —
sonst verteilt Tk die Breite selbst und die Rechnung gilt nicht.

Farben, Schrift und Abstaende kommen aus `Agenten/Werkzeuge/fenster_design.py`
(dieselbe Quelle wie `handelszentrale.py` und `leitstand.py`), beschrieben in
`Werkstatt/design-system-fenster-2026-09-30.md`.

## Fremd-Material: benannt und nicht mitgezaehlt

Fremd-Material liegt **mitten in eigenen Ordnern** — allen voran
`Agenten/Handel/OpenAlice` mit 482 Dateien und 513.266 Zeilen (81 % aller Zeilen
in `Agenten/Handel`). Damit „unser Code" eine Zahl mit Bedeutung hat, gibt es
**eine Quelle**: `Agenten/FREMD-Liste.json`, gelesen von
`Agenten/Werkzeuge/fremd.py` (Python) und per `ConvertFrom-Json` von PowerShell.
Die lesbare Fassung ist `Agenten/FREMD.md`, das Bestandswerkzeug ist
`Agenten/Werkzeuge/bestand.py`.

| | Dateien | Zeilen |
|---|---|---|
| eigener Code (Vorgabe) | **831** | **173.481** |
| mit Fremd-Material | 11.489 | 4,2 Mio. |

Die Zentrale macht daraus drei Dinge:

1. Eine fremde Zeile traegt die Rolle aus der Liste (oder die eigene, genauere)
   und einen Hinweis `fremd: <Regel> (<Herkunft>)` in der Statuszeile.
2. Die Kopfzeile nennt die Zahl: `200 Zeilen · REPOS 46 · … · 63 fremd`.
3. **Gruppiert wird sie nicht anders** — fremd heisst nicht kaputt. Eine
   Papierspur bleibt STARTBAR, ein Klon ohne Startbefehl bleibt EINRICHTEN.

Fremdes wird sichtbar gemacht, nicht weggeraeumt: kein Umbenennen, kein
Verschieben, kein Loeschen. Pruefen mit

    python Agenten\Werkzeuge\fremd.py --pruefen
    python Agenten\Werkzeuge\bestand.py --mit-fremd

## Terminal-Fenster: ein Tab statt viele Fenster

`wt.exe` oeffnet je Aufruf ein **neues** Fenster — acht Klicks, acht Fenster
(gemessen am 30.09.2026: acht sichtbare Fenster, drei davon mit einem
`scanner\.venv`-python). Deshalb traegt **jeder** Terminal-Aufruf `-w 0`: der
Aufruf landet als **Tab im vorhandenen Fenster** (Fensterzahl 1 → 1, Probe
`Agenten\Hermes\cache\scratch\wt_probe.ps1`). Nachgemessen statt geglaubt.

Dazu drei Festlegungen:

- **Befehl ausfuehren** nutzt `cmd /c` (Entscheidung Max): der Tab schliesst sich
  danach selbst. Damit die Ausgabe trotzdem da ist, wird sie **zusaetzlich ins
  Log** umgeleitet (`logs\<ordner>-befehl-<zeit>.log`) und der Pfad steht in der
  Statuszeile.
- **Bot-Chat** nutzt `argv_bot_chat` in `aktionen.py` — frueher stand der Aufruf
  inline in `fenster.py`, also ohne Fensterwahl. Ein Test prueft, dass
  `fenster.py` kein `wt.exe` mehr enthaelt: **ein Bauplatz**.
- **Der Start** (langer Prozess) bleibt ohne Fenster — Ausgabe ins Log.

## Pflege: einrichten, bauen, pruefen, reparieren

Der Reiter **„Einrichten · Reparatur"** der rechten Karte (`pflege.py`) misst den
Zustand eines Projekts und fuehrt den fehlenden Handgriff aus.

| Knopf | Was passiert |
|---|---|
| **Pruefen (F7)** | misst: `venv` (laeuft ihr `python.exe`?), `node_modules`, Pflichtpfad, Git-Zweig/Aenderungen/Rueckstand, README, Bot-Profil, Port. Rein lesend, Ergebnis in der Karte. |
| **Einrichten** | fuehrt die Schritte aus, die im Manifest stehen (`einrichten` bzw. `einrichten_kette`) — sonst die, die sich aus den Dateien des Projekts ergeben. |
| **Bauen** | dasselbe fuer `bauen`/`bauen_kette` bzw. `Cargo.toml`, `go.mod`, `npm run build`, `Makefile`. |
| **Alles pruefen** | misst alle Zeilen des aktuellen Filters und schreibt `logs/pruefbericht-JJJJMMTT-HHMM.log`. |

**Ein Vorschlag ist kein geratener Befehl.** Er entsteht aus einer Datei, die im
Projekt wirklich liegt:

| Datei im Projekt | Vorschlag |
|---|---|
| `requirements.txt` | `python -m venv .venv` (nur wenn sie fehlt), dann `pip install -r` |
| `pyproject.toml` / `setup.py` | `pip install -e .` |
| `package.json` | `npm install` / `npm run build` (nur mit `scripts.build`) |
| `Cargo.toml` | `cargo build --release` |
| `go.mod` | `go build ./...` |
| `Makefile` | `make` |

Fehlt jeder Anhaltspunkt, sagt die Karte das — und der Knopf ist aus. Kein
Befehl wird erfunden.

**Ein Befehl wird erst nach einem erfolgreichen Lauf belegt.** Laeuft
„Einrichten" mit Exit-Code 0 durch und stand noch nichts im Manifest, traegt
`pflege.eintragen()` den Befehl ein — mit Sicherung
`repos-zentrale.bak-JJJJMMTT.json` und datierter Notiz
`_einrichten_belegt`/`_einrichten_kette_belegt`. Mehrere Schritte landen als
**Kette** (`einrichten_kette`: Liste von argv-Listen), nie als Shell-Zeile.

**Repariert wird nicht blind.** Eine `.venv`, deren `python.exe` nicht mehr
startet, wird als solche BENANNT („startet nicht") statt mit `pip install`
traktiert; der Vorschlag lautet dort `python -m venv --clear`. Ein Projekt mit
Aenderungen im Baum wird gemeldet, nicht angefasst; der Vorschlag fuer
Rueckstand ist der vorhandene Weg (`repos-updaten.py --nur <ordner>`).

## Was die Zentrale absichtlich nicht tut

- Sie schreibt **nicht** in fremde Projekte. Ausnahme: der ausdrueckliche
  Einrichtungsbefehl (`npm install`) auf Klick.
- Sie liest **keine** `.env`-Dateien und zeigt keine Schluesselwerte.
- Sie **raet keinen** Startbefehl und meldet **kein** „laeuft" aus
  Prozessnamen — angezeigt werden Exit-Code und Logzeit.
- Sie beendet **nichts** per Prozessname (nur per gemerkter PID).
- Sie startet **nichts** automatisch im Hintergrund; ohne Klick passiert nichts.
- Sie **loescht nichts** und veroeffentlicht nichts: die Pflege kennt kein
  `git reset`, kein `git push`, kein `rm`. Ein Projekt mit Aenderungen im Baum
  wird gemeldet, nicht angefasst.
- Sie **ordert nichts** und **schaltet live nur im Fenster**: `handel_erlaubt`
  laesst sich ausschliesslich ueber das Scharfschalten-Fenster setzen, nie per
  Kommandozeile, Chat oder A2A. Das Fenster ordert selbst nichts — es aendert
  einen Wert in `wachen.json` und belegt es.
- Sie **entschaerft** nur `handel_erlaubt`. `freigabe.erfuellt` bleibt stehen —
  das ist eine Entscheidung von Hand und wird nicht als Nebenwirkung
  zurueckgenommen.
- Sie zeigt **keine** Dateien der Wurzeln, die keine Werkzeuge sind: in
  `Agenten/Handel` liegen 91 `.py`-Dateien, aber nur die mit eigenem Einstieg
  UND Argumentliste werden eine Zeile. Ein halbfertiges Skript soll das Fenster
  nicht fluten.

## Tests

    cd Agenten\Werkzeuge\repos-zentrale
    .venv\Scripts\python.exe -m unittest discover -s tests -v

Stand 30.09.2026: **296 Tests, alle gruen** (vorher 137). Kein Test startet
einen echten Prozess: `subprocess.Popen`, `os.startfile` und
die Starter sind ersetzt, geprueft wird die Kommandozeile. Der Fenstertest baut
die Oberflaeche wirklich auf, aber unsichtbar (`withdraw`).

## Verwandtes

- `Agenten\Werkzeuge\repos-launcher.ps1` — Massenweg: oeffnet alle Repos in
  Windows Terminal oder VSCode (`-Mode Terminal|Tui|Gui`).
- `Agenten\Hermes\profiles\<bot>\` — ein Hermes-Bot je Repo.
- `Agenten\Handel\handelszentrale.py` — das lesende Fenster ueber die
  Handelsspuren (Positionen, Kurse, Konsole); `Agenten\Handel\leitstand.py` ist
  das grosse Ueberwachungs- und Backtest-Fenster.
- Telegram: `/bots` und `/bot NAME NACHRICHT` (SkillsBot) fuer den Zugriff
  unterwegs.
