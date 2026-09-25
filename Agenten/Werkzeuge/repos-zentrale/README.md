# Repos-Zentrale

Ein Fenster fuer alle Projekte unter `Werkstatt/Repos/`: Ordner oeffnen,
Terminal im Repo, starten, Bot-Chat, Doku lesen — plus die Angabe, was fehlt,
bevor man es vergebens versucht.

Entstanden am 18.09.2026, weil „ich kann die Repos nicht starten" fuenf
verschiedene Dinge bedeutete (Fenster, Prozess, Skript, Bau, Doku) und es fuer
jedes Projekt einen eigenen Weg gab. Spezifikation:
`docs/design/2026-09-18-repos-zentrale-design.md`, Plan:
`docs/plans/2026-09-18-repos-zentrale.md`.

## Starten

    cd Agenten\Werkzeuge\repos-zentrale
    .venv\Scripts\pythonw.exe repos_zentrale.py        # Fenster
    .venv\Scripts\python.exe   repos_zentrale.py --pruefen   # nur auflisten, kein Fenster

Die venv ist nur fuer dieses Werkzeug (Python 3.13, Standardbibliothek). Sie
haengt an keiner Repo-venv.

## Was das Fenster zeigt

Ein Baum mit Gruppenkoepfen:

| Gruppe | Bedeutung |
|---|---|
| **STARTBAR** | Startbefehl ist belegt *und* die Abhaengigkeiten liegen auf der Platte |
| **EINRICHTEN** | Einstieg vorhanden, es fehlt noch etwas (venv, `node_modules`, Binary) |
| **NEU** | Ordner auf der Platte, aber kein Eintrag im Manifest |
| **NUR DOKU** | kein Programm, nur Text/PDF — „starten" heisst hier oeffnen |
| **FEHLT** | Manifest-Eintrag ohne Ordner (z. B. nach dem Loeschen eines Klons) |

Spalten: Art, venv, Bot-Profil (mit `(fehlt)`, wenn das Profil nicht existiert),
letzter Start (aus `logs/`), Hinweis (erst der Grund, sonst die Notiz).

Fuenf Aktionen je Zeile — was nicht geht, ist deaktiviert, nicht kaputt:

1. **Ordner** — Explorer im Repo
2. **Terminal** — `wt.exe`, Arbeitsverzeichnis = Repo
3. **Starten** — der Befehl aus dem Manifest; Ausgabe geht in `logs/`
4. **Bot** — `hermes -p <bot> chat`, Arbeitsverzeichnis = Repo
5. **Doku** — die README des Repos

Dazu **Log oeffnen** (oder Doppelklick auf eine Zeile): zeigt die neueste
Logdatei dieses Repos. Oben ein Suchfeld (trifft Name, Bot, Notiz, Art) und
„Aktualisieren" (liest Platte und Manifest neu).

## Der Bereich „Was dieses Projekt kann"

Unter der Tabelle steht fuer das **ausgewaehlte** Projekt:

- **links ein Textblock**: wozu das Repo da ist (`notiz`), wo es liegt, ob eine
  venv da ist, was noch fehlt („Zu tun: …") und — wenn im Manifest hinterlegt —
  der Ablauf in Worten (`anleitung`). Fehlt er, sagt der Text das ausdruecklich,
  statt etwas zu erfinden.
- **rechts die Befehlsliste**: je Zeile `Was | Befehl | Hinweis`. Die ersten
  Eintraege sind fuer jedes Repo dieselben (Starten, Terminal, Ordner, Doku,
  Bot), danach kommen die Befehle aus dem Manifest (`befehle`).

Drei Knoepfe, alle auf die gewaehlte Zeile bezogen:

| Knopf | Was passiert |
|---|---|
| **Befehl ausfuehren** | oeffnet ein sichtbares Windows-Terminal im Repo-Ordner und fuehrt den Befehl aus (`cmd /k`, damit die Ausgabe stehen bleibt). Zeilen wie „Ordner im Explorer" loesen den gleichnamigen Knopf aus. |
| **Befehl kopieren** | legt die Befehlszeile in die Zwischenablage — zum Einfuegen in ein eigenes Terminal. So lernt man den Weg von Hand. |
| **Bot damit beauftragen** | gibt den Befehl als Auftrag an den Repo-Bot (`hermes -p <bot> chat -q …`): er fuehrt aus und erklaert in drei Saetzen, was herauskam. Nur aktiv, wenn das Profil existiert. |

Das ist der gedachte Weg fuer „ich kenne mich in der Kommandozeile nicht aus":
Projekt waehlen, Befehlszeile lesen, **Bot damit beauftragen** — oder
**Befehl kopieren** und selbst einfuegen.

## Das Manifest

`repos-zentrale.json` ist die **einzige** Stelle, an der ein Startbefehl steht.
Felder je Repo:

    {
      "ordner": "moon-dev-ai-agents",     // wie das Verzeichnis heisst
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
      ]
    }

Regeln, die der Code durchsetzt:

- **`start` und `einrichten` sind argv-Listen**, keine Shell-Zeichenketten
  (kein `shell=True`, keine Zeichenketten-Injektion). Ein relativer
  Programmname wird gegen den Repo-Ordner aufgeloest — Windows wuerde ihn sonst
  gegen das Arbeitsverzeichnis des Aufrufers suchen und nicht finden.
- Ein **Befehl kommt erst ins Manifest, wenn er einmal echt gelaufen ist**
  (Log in `logs/`). Nennt der Test `tests/test_manifest_gegenprobe.py` einen
  Startbefehl ohne Logbeleg, ist die Regel verletzt.
- **Kein Eintrag ohne Ordner** heisst nicht „Repos unsichtbar": was auf der
  Platte liegt und keinen Eintrag hat, erscheint als **NEU**.
- Die **Platte schlaegt das Manifest** beim Zustand: venv, `node_modules`,
  README und Pflichtdateien werden live geprueft.

## Ein neues Repo aufnehmen

1. Manifest-Eintrag ergaenzen: `ordner`, `art`, `bot`, `notiz`.
2. Pruefen: `.venv\Scripts\python.exe -m unittest discover -s tests` und
   `python repos_zentrale.py --pruefen` — der neue Klon muss in einer der
   Gruppen auftauchen, nicht verschwinden.
3. Erst wenn der Startbefehl einmal echt gelaufen ist, ihn als `start`
   eintragen (die Logdatei entsteht dabei von selbst).

## Befehle und Anleitung nachtragen

Fuer die Anzeige braucht ein Repo **keinen** Eintrag — die allgemeinen Zeilen
(Starten, Terminal, Ordner, Doku, Bot) entstehen aus Platte und Manifest von
selbst. Eigenes kommt dazu, sobald man den Weg einmal gegangen ist:

1. Befehl **einmal wirklich laufen lassen** (Hausregel: kein Befehl ins
   Manifest, der nie lief). Die Zeile notieren, die funktioniert hat.
2. In `repos-zentrale.json` beim Eintrag ergaenzen:

       "anleitung": "Was das Repo tut und in welcher Reihenfolge man es anfasst.",
       "befehle": [
         {"was": "Kanalbericht", "cmd": [".venv\\Scripts\\agent-reach.exe", "doctor"],
          "hinweis": "dauert 20 s"}
       ]

   `cmd` ist eine **argv-Liste** wie `start` — keine Shell-Zeichenkette, keine
   Pipes. Der Titel `was` erscheint in der Liste, `hinweis` daneben.
3. Fenster neu oeffnen (das Manifest wird beim Aufbau gelesen).

Ein Befehl ohne `cmd` wird still uebergangen — ein Tippfehler nimmt also nicht
die ganze Liste mit, er fehlt nur. Fehlerhafte `befehle` stehen als Hinweis in
der Zeile, sie machen das Repo **nicht** un-startbar.

Wer nichts eintragen will: Der Knopf **Bot damit beauftragen** erledigt denselben
Zweck — der Repo-Bot kennt sein Repository und kann einen Befehl ausfuehren und
erklaeren.

## Was die Zentrale absichtlich nicht tut

- Sie schreibt **nicht** in fremde Repos. Ausnahme: der ausdrueckliche
  Einrichtungsbefehl (`npm install`) auf Klick.
- Sie liest **keine** `.env`-Dateien und zeigt keine Schluesselwerte.
- Sie **raet keinen** Startbefehl und meldet **kein** „laeuft" aus
  Prozessnamen — angezeigt werden Exit-Code und Logzeit.
- Sie beendet **nichts** per Prozessname (nur per gemerkter PID).
- Sie startet **nichts** automatisch im Hintergrund; ohne Klick passiert nichts.

## Tests

    cd Agenten\Werkzeuge\repos-zentrale
    .venv\Scripts\python.exe -m unittest discover -s tests -v

Kein Test startet einen echten Prozess: `subprocess.Popen`, `os.startfile` und
die Starter sind ersetzt, geprueft wird die Kommandozeile. Der Fenstertest baut
die Oberflaeche wirklich auf, aber unsichtbar (`withdraw`).

## Verwandtes

- `Agenten\Werkzeuge\repos-launcher.ps1` — Massenweg: oeffnet alle Repos in
  Windows Terminal oder VSCode (`-Mode Terminal|Tui|Gui`). Fehlt ein Werkzeug,
  wird es genannt und der Modus uebersprungen, statt abzubrechen.
- `Agenten\Hermes\profiles\<bot>\` — ein Hermes-Bot je Repo (28 Stueck).
- Telegram: `/bots` und `/bot NAME NACHRICHT` (SkillsBot) fuer den Zugriff
  unterwegs.
